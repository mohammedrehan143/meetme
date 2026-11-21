from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import WeeklyDigest, WorkspaceMember
from backend.app.services.digest_service import digest_service

router = APIRouter(prefix="/api/digest", tags=["digest"])

class GenerateDigestRequest(BaseModel):
    member_id: Optional[str] = None
    period_days: int = 7
    dispatch_email_now: bool = False

@router.get("")
async def list_digests(
    workspace_id: Optional[str] = None,
    member_id: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(WeeklyDigest).where(WeeklyDigest.workspace_id == ws_id)
    if member_id:
        stmt = stmt.where(WeeklyDigest.member_id == member_id)
    stmt = stmt.order_by(desc(WeeklyDigest.created_at)).limit(limit)
    res = await db.execute(stmt)
    digests = res.scalars().all()

    return [
        {
            "id": d.id,
            "workspace_id": d.workspace_id,
            "member_id": d.member_id,
            "recipient_name": d.recipient_name,
            "recipient_email": d.recipient_email,
            "period_start": d.period_start.strftime("%Y-%m-%d"),
            "period_end": d.period_end.strftime("%Y-%m-%d"),
            "status": d.status,
            "metrics": d.content_json.get("metrics", {}) if d.content_json else {},
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in digests
    ]

@router.get("/{digest_id}")
async def get_digest(
    digest_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WeeklyDigest).where(WeeklyDigest.id == digest_id)
    res = await db.execute(stmt)
    digest = res.scalar_one_or_none()
    if not digest:
        raise HTTPException(status_code=404, detail="Weekly digest not found")

    return {
        "id": digest.id,
        "workspace_id": digest.workspace_id,
        "member_id": digest.member_id,
        "recipient_name": digest.recipient_name,
        "recipient_email": digest.recipient_email,
        "period_start": digest.period_start.strftime("%Y-%m-%d"),
        "period_end": digest.period_end.strftime("%Y-%m-%d"),
        "status": digest.status,
        "metrics": digest.content_json.get("metrics", {}) if digest.content_json else {},
        "content": digest.content_json,
        "html_body": digest.html_body,
        "sent_at": digest.sent_at.isoformat() if digest.sent_at else None,
        "created_at": digest.created_at.isoformat() if digest.created_at else None
    }

@router.post("/generate")
async def generate_digests(
    payload: GenerateDigestRequest,
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    
    # 1. Fetch target members
    if payload.member_id:
        m_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.id == payload.member_id
        )
    else:
        m_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)
    
    m_res = await db.execute(m_stmt)
    members = m_res.scalars().all()

    if not members:
        return {"status": "SUCCESS", "message": "No workspace members found to generate digests for.", "generated_count": 0}

    generated = []
    for member in members:
        d = await digest_service.generate_member_digest(
            db=db,
            workspace_id=ws_id,
            member=member,
            period_days=payload.period_days
        )
        if payload.dispatch_email_now:
            await digest_service.send_digest(db=db, digest_id=d.id)
        generated.append({
            "id": d.id,
            "member_id": member.id,
            "member_name": member.full_name,
            "member_email": member.email,
            "status": d.status
        })

    return {
        "status": "SUCCESS",
        "generated_count": len(generated),
        "digests": generated
    }

class SendDigestRequest(BaseModel):
    recipient_email: Optional[str] = None

@router.post("/{digest_id}/send")
async def send_digest_endpoint(
    digest_id: str,
    payload: Optional[SendDigestRequest] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        custom_email = payload.recipient_email if payload else None
        res = await digest_service.send_digest(db=db, digest_id=digest_id, custom_recipient_email=custom_email)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
