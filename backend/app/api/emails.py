from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import EmailLog
from backend.app.services.email_service import email_service

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
            "task_ids": log.task_ids or ([log.task_id] if log.task_id else []),
            "email_type": log.email_type,
            "recipient": log.recipient,
            "email_address": log.email_address,
            "subject": log.subject,
            "body_html": log.body_html,
            "body_text": log.body_text,
            "status": log.status,
            "provider": log.provider or "Gmail SMTP",
            "message_id": log.message_id or log.provider_message_id,
            "provider_message_id": log.provider_message_id,
            "idempotency_key": log.idempotency_key,
            "retry_count": log.retry_count or 0,
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

    send_res = await email_service.send_email(
        to=log.email_address,
        subject=log.subject,
        html=log.body_html,
        text=log.body_text,
        recipient_name=log.recipient,
        email_type=log.email_type or "RETRY",
        task_ids=log.task_ids or ([log.task_id] if log.task_id else []),
        idempotency_key=f"retry_{log.id}_{datetime.utcnow().timestamp()}"
    )

    if send_res.get("success"):
        log.status = send_res.get("status", "SENT")
        log.provider = send_res.get("provider", "Gmail SMTP")
        log.provider_message_id = send_res.get("id")
        log.message_id = send_res.get("id")
        log.sent_at = datetime.utcnow()
        log.error_message = None
        log.retry_count = (log.retry_count or 0) + 1
    else:
        log.status = "FAILED"
        log.error_message = send_res.get("error", "Gmail SMTP retry failed")
        log.retry_count = (log.retry_count or 0) + 1

    await db.commit()
    return {"status": log.status, "email_id": log.id, "error": log.error_message}
