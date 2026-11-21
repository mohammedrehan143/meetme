from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import ExternalIntegration, ExternalIssueSync
from backend.app.services.jira_service import jira_service
from backend.app.services.github_service import github_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

class JiraConnectRequest(BaseModel):
    domain: str
    email: str
    api_token: str
    project_key: str = "PROJ"
    issue_type: str = "Task"

class GitHubConnectRequest(BaseModel):
    token: str
    repo: str # e.g. "mohammedrehan143/meetme"

@router.get("")
async def get_integrations(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(ExternalIntegration).where(ExternalIntegration.workspace_id == ws_id)
    res = await db.execute(stmt)
    integrations = res.scalars().all()

    by_provider = {i.provider: i for i in integrations}

    jira_int = by_provider.get("JIRA")
    github_int = by_provider.get("GITHUB")

    def mask(s: Optional[str]) -> str:
        if not s:
            return ""
        if len(s) < 8:
            return "********"
        return f"{s[:4]}...{s[-4:]}"

    return {
        "jira": {
            "is_connected": bool(jira_int and jira_int.is_active),
            "domain": jira_int.credentials_encrypted.get("domain", "") if (jira_int and jira_int.credentials_encrypted) else "",
            "email": jira_int.credentials_encrypted.get("email", "") if (jira_int and jira_int.credentials_encrypted) else "",
            "masked_token": mask(jira_int.credentials_encrypted.get("api_token", "")) if (jira_int and jira_int.credentials_encrypted) else "",
            "project_key": jira_int.config.get("project_key", "PROJ") if (jira_int and jira_int.config) else "PROJ",
            "issue_type": jira_int.config.get("issue_type", "Task") if (jira_int and jira_int.config) else "Task",
            "last_sync_at": jira_int.last_sync_at.isoformat() if (jira_int and jira_int.last_sync_at) else None
        },
        "github": {
            "is_connected": bool(github_int and github_int.is_active),
            "repo": github_int.config.get("repo", "") if (github_int and github_int.config) else "",
            "masked_token": mask(github_int.credentials_encrypted.get("token", "")) if (github_int and github_int.credentials_encrypted) else "",
            "last_sync_at": github_int.last_sync_at.isoformat() if (github_int and github_int.last_sync_at) else None
        }
    }

@router.post("/jira/connect")
async def connect_jira(
    payload: JiraConnectRequest,
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID

    # Validate live with Jira Cloud REST API
    test_res = await jira_service.test_connection(payload.domain, payload.email, payload.api_token)
    if not test_res.get("success"):
        raise HTTPException(status_code=400, detail=test_res.get("error", "Failed to connect to Jira."))

    # Upsert integration record
    stmt = select(ExternalIntegration).where(
        ExternalIntegration.workspace_id == ws_id,
        ExternalIntegration.provider == "JIRA"
    )
    res = await db.execute(stmt)
    jira_int = res.scalar_one_or_none()

    creds = {
        "domain": payload.domain,
        "email": payload.email,
        "api_token": payload.api_token
    }
    conf = {
        "project_key": payload.project_key.upper(),
        "issue_type": payload.issue_type
    }

    if jira_int:
        jira_int.is_active = True
        jira_int.credentials_encrypted = creds
        jira_int.config = conf
        jira_int.last_sync_at = datetime.utcnow()
    else:
        jira_int = ExternalIntegration(
            workspace_id=ws_id,
            provider="JIRA",
            is_active=True,
            credentials_encrypted=creds,
            config=conf,
            last_sync_at=datetime.utcnow()
        )
        db.add(jira_int)

    await db.commit()
    return {
        "status": "SUCCESS",
        "message": f"Successfully connected to Jira Cloud ({payload.domain}).",
        "display_name": test_res.get("display_name")
    }

@router.post("/jira/disconnect")
async def disconnect_jira(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(ExternalIntegration).where(
        ExternalIntegration.workspace_id == ws_id,
        ExternalIntegration.provider == "JIRA"
    )
    res = await db.execute(stmt)
    jira_int = res.scalar_one_or_none()
    if jira_int:
        jira_int.is_active = False
        jira_int.credentials_encrypted = {}
        await db.commit()
    return {"status": "SUCCESS", "message": "Jira integration disconnected."}

@router.post("/github/connect")
async def connect_github(
    payload: GitHubConnectRequest,
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID

    # Validate live with GitHub REST API
    test_res = await github_service.test_connection(payload.token, payload.repo)
    if not test_res.get("success"):
        raise HTTPException(status_code=400, detail=test_res.get("error", "Failed to connect to GitHub."))

    stmt = select(ExternalIntegration).where(
        ExternalIntegration.workspace_id == ws_id,
        ExternalIntegration.provider == "GITHUB"
    )
    res = await db.execute(stmt)
    github_int = res.scalar_one_or_none()

    creds = {"token": payload.token}
    conf = {"repo": test_res.get("repo", payload.repo)}

    if github_int:
        github_int.is_active = True
        github_int.credentials_encrypted = creds
        github_int.config = conf
        github_int.last_sync_at = datetime.utcnow()
    else:
        github_int = ExternalIntegration(
            workspace_id=ws_id,
            provider="GITHUB",
            is_active=True,
            credentials_encrypted=creds,
            config=conf,
            last_sync_at=datetime.utcnow()
        )
        db.add(github_int)

    await db.commit()
    return {
        "status": "SUCCESS",
        "message": f"Successfully connected to GitHub ({conf['repo']}).",
        "repo": conf["repo"]
    }

@router.post("/github/disconnect")
async def disconnect_github(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(ExternalIntegration).where(
        ExternalIntegration.workspace_id == ws_id,
        ExternalIntegration.provider == "GITHUB"
    )
    res = await db.execute(stmt)
    github_int = res.scalar_one_or_none()
    if github_int:
        github_int.is_active = False
        github_int.credentials_encrypted = {}
        await db.commit()
    return {"status": "SUCCESS", "message": "GitHub integration disconnected."}

@router.get("/activity")
async def get_integration_activity(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(ExternalIssueSync).where(
        ExternalIssueSync.workspace_id == ws_id
    ).order_by(desc(ExternalIssueSync.created_at)).limit(limit)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "approval_id": r.approval_id,
            "provider": r.provider,
            "external_id": r.external_id,
            "external_key_or_number": r.external_key_or_number,
            "external_url": r.external_url,
            "title": r.title,
            "status": r.status,
            "error_message": r.error_message,
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
