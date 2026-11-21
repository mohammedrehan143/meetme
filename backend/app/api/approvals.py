import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Approval, Task, Meeting
from backend.app.agents.execution_agent import execution_agent

logger = logging.getLogger("meetme.api.approvals")

router = APIRouter(prefix="/api/approvals", tags=["approvals"])

class ApproveRequest(BaseModel):
    custom_payload: Optional[Dict[str, Any]] = None
    approval_notes: Optional[str] = None
    user_id: Optional[str] = None

class BatchApproveRequest(BaseModel):
    approval_ids: List[str]
    user_id: Optional[str] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = None
    user_id: Optional[str] = None

class DispatchEmailRequest(BaseModel):
    to_email: str
    recipient_name: Optional[str] = None
    user_id: Optional[str] = None

@router.get("")
async def list_approvals(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None, # PENDING, APPROVED, REJECTED
    db: AsyncSession = Depends(get_db)
):
    if workspace_id:
        query = select(Approval).where(Approval.workspace_id == workspace_id)
    else:
        query = select(Approval)
    if status:
        query = query.where(Approval.status == status)
    query = query.order_by(desc(Approval.created_at))

    res = await db.execute(query)
    approvals = res.scalars().all()

    output = []
    for app in approvals:
        output.append({
            "id": app.id,
            "task_id": app.task_id,
            "meeting_id": app.meeting_id,
            "status": app.status,
            "proposed_payload": app.proposed_payload,
            "approved_payload": app.approved_payload,
            "approved_recipient": app.approved_recipient,
            "approval_notes": app.approval_notes,
            "approved_at": app.approved_at.isoformat() if app.approved_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None
        })

    return output

@router.post("/{approval_id}/approve")
async def approve_single(
    approval_id: str,
    payload: ApproveRequest = Body(default=ApproveRequest()),
    db: AsyncSession = Depends(get_db)
):
    user_id = payload.user_id or settings.DEFAULT_USER_ID
    try:
        result = await execution_agent.execute_approval(
            db=db,
            approval_id=approval_id,
            user_id=user_id,
            custom_payload=payload.custom_payload,
            approved_notes=payload.approval_notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Execution error for approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@router.post("/batch-approve")
async def batch_approve(
    payload: BatchApproveRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = payload.user_id or settings.DEFAULT_USER_ID
    results = []
    for app_id in payload.approval_ids:
        try:
            res = await execution_agent.execute_approval(
                db=db,
                approval_id=app_id,
                user_id=user_id
            )
            results.append({"approval_id": app_id, "status": "APPROVED", "detail": res})
        except Exception as e:
            results.append({"approval_id": app_id, "status": "FAILED", "error": str(e)})

    return {"results": results, "total": len(results)}

@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    payload: RejectRequest = Body(default=RejectRequest()),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Approval).where(Approval.id == approval_id)
    res = await db.execute(stmt)
    approval = res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "REJECTED"
    approval.approval_notes = payload.reason or "Rejected by reviewer"
    approval.approved_at = datetime.utcnow()
    approval.user_id = payload.user_id or settings.DEFAULT_USER_ID

    # Also update Task status to REJECTED
    task_stmt = select(Task).where(Task.id == approval.task_id)
    task_res = await db.execute(task_stmt)
    task = task_res.scalar_one_or_none()
    if task:
        task.status = "REJECTED"
        task.updated_at = datetime.utcnow()

    await db.commit()
    return {"status": "REJECTED", "approval_id": approval.id}

@router.post("/{approval_id}/dispatch-email")
async def dispatch_approval_email(
    approval_id: str,
    payload: DispatchEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Approval).where(Approval.id == approval_id)
    res = await db.execute(stmt)
    approval = res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    user_id = payload.user_id or settings.DEFAULT_USER_ID
    clean_email = payload.to_email.strip()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address specified.")

    base_payload = approval.approved_payload or approval.proposed_payload or {}
    custom_payload = {
        **base_payload,
        "assignee_email": clean_email,
    }
    if payload.recipient_name:
        custom_payload["assignee_name"] = payload.recipient_name

    try:
        result = await execution_agent.execute_approval(
            db=db,
            approval_id=approval_id,
            user_id=user_id,
            custom_payload=custom_payload,
            approved_notes=f"Email dispatched to {clean_email}"
        )
        return result
    except Exception as e:
        logger.error(f"Error dispatching email for approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
