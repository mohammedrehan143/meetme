from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import EmailLog
from backend.app.services.email_service import email_service

router = APIRouter(prefix="/api/emails", tags=["emails"])

class SendEmailRequest(BaseModel):
    to_email: str
    recipient_name: Optional[str] = None
    subject: str
    message: str
    email_type: str = "MANUAL_DISPATCH"
    workspace_id: Optional[str] = None

@router.get("")
async def list_emails(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    if workspace_id:
        stmt = select(EmailLog).where(EmailLog.workspace_id == workspace_id).order_by(desc(EmailLog.created_at)).limit(limit)
    else:
        stmt = select(EmailLog).order_by(desc(EmailLog.created_at)).limit(limit)
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

@router.post("/send")
@router.post("")
async def send_custom_email(
    payload: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sends an email to a specific destination email address using native Gmail SMTP.
    Logs the email in the audit table.
    """
    if not payload.to_email or "@" not in payload.to_email:
        raise HTTPException(status_code=400, detail="A valid recipient email address is required.")

    ws_id = payload.workspace_id or settings.DEFAULT_WORKSPACE_ID

    # Format dark-themed RFC-compliant HTML email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 24px; background-color: #0c0c0c; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
      <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #141414; border: 1px solid #262626; border-radius: 8px; overflow: hidden;">
        <tr>
          <td style="padding: 24px 32px; background-color: #181818; border-bottom: 2px solid #FF7900;">
            <table width="100%" border="0" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size: 22px; font-weight: 800; color: #FF7900; letter-spacing: -0.5px;">MEETME</span>
                  <span style="font-size: 11px; color: #888; margin-left: 8px; text-transform: uppercase; letter-spacing: 1.5px;">Intelligence</span>
                </td>
                <td align="right">
                  <span style="font-size: 10px; font-family: monospace; color: #B6FF00; background-color: rgba(182, 255, 0, 0.1); border: 1px solid rgba(182, 255, 0, 0.3); padding: 4px 8px; border-radius: 4px;">VERIFIED DISPATCH</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding: 32px;">
            <h2 style="font-size: 17px; font-weight: 700; color: #ffffff; margin: 0 0 16px 0;">{payload.subject}</h2>
            <div style="font-size: 14px; line-height: 1.7; color: #d4d4d4; margin-bottom: 24px; white-space: pre-wrap;">{payload.message}</div>
            
            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #1b1b1b; border: 1px solid #2d2d2d; border-radius: 6px;">
              <tr>
                <td style="padding: 12px 16px;">
                  <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding: 3px 0; font-size: 11px; font-family: monospace; color: #737373;">Destination:</td>
                      <td style="padding: 3px 0; font-size: 11px; font-family: monospace; color: #FF7900; font-weight: 600;">{payload.to_email}</td>
                    </tr>
                    <tr>
                      <td style="padding: 3px 0; font-size: 11px; font-family: monospace; color: #737373;">Dispatched At:</td>
                      <td style="padding: 3px 0; font-size: 11px; font-family: monospace; color: #a3a3a3;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding: 16px 32px; background-color: #101010; border-top: 1px solid #222222; text-align: center;">
            <p style="font-size: 11px; color: #525252; margin: 0;">MEETME Platform &bull; Meetings in. Execution out.</p>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    res = await email_service.send_email(
        to=payload.to_email,
        subject=payload.subject,
        html=html_content,
        text=payload.message,
        recipient_name=payload.recipient_name or "Team Member",
        email_type=payload.email_type,
        workspace_id=ws_id,
        db=db
    )

    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to dispatch email via Gmail SMTP"))

    return {
        "status": "SENT",
        "message_id": res.get("id"),
        "recipient": payload.to_email,
        "subject": payload.subject,
        "provider": "Gmail SMTP"
    }
