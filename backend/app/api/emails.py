from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import EmailLog
from backend.app.services.resend_service import resend_service

router = APIRouter(prefix="/api/emails", tags=["emails"])

@router.get("")
async def list_emails(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(EmailLog).where(EmailLog.workspace_id == ws_id).order_by(desc(EmailLog.created_at)).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": log.id,
            "task_id": log.task_id,
            "recipient": log.recipient,
            "email_address": log.email_address,
            "subject": log.subject,
            "body_html": log.body_html,
            "body_text": log.body_text,
            "status": log.status,
            "provider": log.provider,
            "provider_message_id": log.provider_message_id,
            "error_message": log.error_message,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]

@router.post("/{email_id}/retry")
async def retry_email(email_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EmailLog).where(EmailLog.id == email_id)
    res = await db.execute(stmt)
    log = res.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Email record not found")

    send_res = await resend_service.send_email(
        to=log.email_address,
        subject=log.subject,
        html=log.body_html,
        text=log.body_text
    )

    if send_res.get("success"):
        log.status = send_res.get("status", "SENT")
        log.provider_message_id = send_res.get("id")
        log.sent_at = datetime.utcnow()
        log.error_message = None
    else:
        log.status = "FAILED"
        log.error_message = send_res.get("error", "Retry failed")

    await db.commit()
    return {"status": log.status, "email_id": log.id}
