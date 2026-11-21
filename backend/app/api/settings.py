import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Notification, Workspace
from backend.app.demo.seed_data import seed_demo_workspace
from backend.app.services.email_service import email_service

router = APIRouter(tags=["settings"])

class UpdateSettingsRequest(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    resend_api_key: Optional[str] = None
    resend_from_email: Optional[str] = None
    brevo_api_key: Optional[str] = None
    brevo_from_email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_name: Optional[str] = None

@router.get("/api/settings")
async def get_settings():
    def mask_key(k: Optional[str]) -> str:
        if not k:
            return "Not Configured"
        if len(k) < 8:
            return "********"
        return f"{k[:3]}...{k[-3:]}"

    return {
        "app_name": settings.APP_NAME,
        "app_env": settings.APP_ENV,
        "database_url": "Async SQLite / Supabase PostgreSQL Compatible",
        "active_email_provider": email_service.active_provider,
        "groq": {
            "is_configured": bool(settings.GROQ_API_KEY),
            "masked_key": mask_key(settings.GROQ_API_KEY),
            "model": settings.GROQ_MODEL,
            "whisper_model": settings.GROQ_WHISPER_MODEL
        },
        "gemini": {
            "is_configured": bool(settings.GEMINI_API_KEY),
            "masked_key": mask_key(settings.GEMINI_API_KEY),
            "model": settings.GEMINI_MODEL
        },
        "brevo": {
            "is_configured": email_service.is_brevo_configured,
            "masked_key": mask_key(settings.BREVO_API_KEY),
            "from_email": settings.BREVO_FROM_EMAIL or "mrofficialyt083@gmail.com",
            "port": 443,
            "protocol": "HTTPS REST API (Sends to all inboxes without custom domain)"
        },
        "resend": {
            "is_configured": email_service.is_resend_configured,
            "masked_key": mask_key(settings.RESEND_API_KEY),
            "from_email": settings.RESEND_FROM_EMAIL or "MEETME Platform <onboarding@resend.dev>",
            "port": 443,
            "protocol": "HTTPS REST API (Render Free Tier Compatible)"
        },
        "smtp": {
            "is_configured": email_service.is_smtp_configured,
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "email": settings.SMTP_EMAIL or "",
            "masked_password": mask_key(settings.SMTP_PASSWORD),
            "from_name": settings.SMTP_FROM_NAME,
            "provider": "Gmail SMTP (STARTTLS / SSL)"
        },
        "default_workspace_id": settings.DEFAULT_WORKSPACE_ID
    }
            "masked_password": mask_key(settings.SMTP_PASSWORD),
            "from_name": settings.SMTP_FROM_NAME,
            "provider": "Gmail SMTP (STARTTLS / SSL)"
        },
        "default_workspace_id": settings.DEFAULT_WORKSPACE_ID
    }

@router.post("/api/settings")
async def update_settings(payload: UpdateSettingsRequest):
    if payload.groq_api_key is not None:
        settings.GROQ_API_KEY = payload.groq_api_key
        os.environ["GROQ_API_KEY"] = payload.groq_api_key
    if payload.groq_model is not None:
        settings.GROQ_MODEL = payload.groq_model

    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key
        os.environ["GEMINI_API_KEY"] = payload.gemini_api_key
        from backend.app.services.gemini_service import gemini_service
        gemini_service.api_key = payload.gemini_api_key
    if payload.gemini_model is not None:
        settings.GEMINI_MODEL = payload.gemini_model
        from backend.app.services.gemini_service import gemini_service
        gemini_service.model = payload.gemini_model

    if payload.resend_api_key is not None:
        settings.RESEND_API_KEY = payload.resend_api_key
        email_service.resend_api_key = payload.resend_api_key
        os.environ["RESEND_API_KEY"] = payload.resend_api_key
    if payload.resend_from_email is not None:
        settings.RESEND_FROM_EMAIL = payload.resend_from_email
        email_service.resend_from_email = payload.resend_from_email
        os.environ["RESEND_FROM_EMAIL"] = payload.resend_from_email

    if payload.brevo_api_key is not None:
        settings.BREVO_API_KEY = payload.brevo_api_key
        email_service.brevo_api_key = payload.brevo_api_key
        os.environ["BREVO_API_KEY"] = payload.brevo_api_key
    if payload.brevo_from_email is not None:
        settings.BREVO_FROM_EMAIL = payload.brevo_from_email
        email_service.brevo_from_email = payload.brevo_from_email
        os.environ["BREVO_FROM_EMAIL"] = payload.brevo_from_email

    if payload.smtp_host is not None:
        settings.SMTP_HOST = payload.smtp_host
        email_service.host = payload.smtp_host
    if payload.smtp_port is not None:
        settings.SMTP_PORT = payload.smtp_port
        email_service.port = payload.smtp_port
    if payload.smtp_email is not None:
        settings.SMTP_EMAIL = payload.smtp_email
        email_service.email = payload.smtp_email
        os.environ["SMTP_EMAIL"] = payload.smtp_email
    if payload.smtp_password is not None:
        settings.SMTP_PASSWORD = payload.smtp_password
        email_service.password = payload.smtp_password
        os.environ["SMTP_PASSWORD"] = payload.smtp_password
    if payload.smtp_from_name is not None:
        settings.SMTP_FROM_NAME = payload.smtp_from_name
        email_service.from_name = payload.smtp_from_name

    return {"status": "SUCCESS", "message": "Settings updated successfully."}

@router.post("/api/settings/test-smtp")
@router.post("/api/settings/test-email")
async def test_email_connection():
    """
    Validates active email transport (Resend HTTPS API over port 443 or Gmail SMTP).
    """
    import asyncio
    try:
        result = await asyncio.wait_for(asyncio.to_thread(email_service.test_connection), timeout=10.0)
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Email connection test timed out (10s limit). If using Gmail SMTP on Render Free Tier, outbound ports 25/465/587 are blocked. Use Resend HTTPS API instead."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Email connection test failed: {str(e)}"
        }

class TestDispatchRequest(BaseModel):
    to_email: str = "25ug1byai034@bmsit.in"
    recipient_name: Optional[str] = "Rehan"

@router.post("/api/settings/test-dispatch")
async def test_email_dispatch(payload: TestDispatchRequest):
    """
    Sends an actual test email to verify live delivery via Resend or Gmail SMTP.
    """
    subject = "MEETME Platform - Email Delivery Verification"
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0D0D0D; color: #E5E5E5; border: 1px solid #262626; border-radius: 8px; overflow: hidden;">
        <div style="background: #141414; padding: 20px 24px; border-bottom: 1px solid #262626; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-size: 16px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.5px;">MEETME <span style="color: #FF7900;">PLATFORM</span></div>
            <div style="font-size: 10px; font-family: monospace; background: rgba(182, 255, 0, 0.15); color: #B6FF00; padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(182, 255, 0, 0.3);">DELIVERY TEST</div>
        </div>
        <div style="padding: 24px;">
            <h2 style="font-size: 18px; color: #FFFFFF; margin-top: 0; margin-bottom: 12px;">Email Integration Verified</h2>
            <p style="font-size: 14px; line-height: 1.6; color: #A3A3A3; margin-bottom: 20px;">
                Hello <strong>{payload.recipient_name or payload.to_email}</strong>,<br><br>
                This confirms that your MEETME email delivery engine is successfully configured and communicating over standard HTTPS Port 443 via Resend.
            </p>
            <div style="background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 6px; padding: 16px; margin-bottom: 20px; font-family: monospace; font-size: 12px;">
                <div style="color: #737373; margin-bottom: 6px;">INTEGRATION DETAILS</div>
                <div style="color: #E5E5E5;">Provider: <span style="color: #B6FF00;">{email_service.active_provider}</span></div>
                <div style="color: #E5E5E5;">Recipient: <span style="color: #FFFFFF;">{payload.to_email}</span></div>
                <div style="color: #E5E5E5;">Render Compatible: <span style="color: #B6FF00;">YES (Port 443 HTTPS)</span></div>
            </div>
            <p style="font-size: 12px; color: #737373; margin: 0;">
                All approved action items and reminder schedules will now be dispatched to this inbox reliably.
            </p>
        </div>
    </div>
    """
    text_content = f"Hello {payload.recipient_name or payload.to_email},\n\nThis confirms your MEETME email delivery engine is working ({email_service.active_provider})."
    
    res = await email_service.send_email(
        to=payload.to_email,
        subject=subject,
        html=html_content,
        text=text_content,
        recipient_name=payload.recipient_name,
        email_type="TEST_DISPATCH"
    )
    return res

@router.post("/api/demo/seed")
async def seed_demo(
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    try:
        res = await seed_demo_workspace(db=db, force=force)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed demo workspace: {str(e)}")

@router.post("/api/demo/wipe")
@router.get("/api/demo/wipe")
async def wipe_demo(db: AsyncSession = Depends(get_db)):
    """
    Cleans demo meetings, tasks, and fake demo team members from the database.
    """
    try:
        from backend.app.models.schema import (
            User, Workspace, WorkspaceMember, Meeting, MeetingTranscript,
            Speaker, Task, TaskDependency, Approval, EmailLog, Reminder,
            AutomationLog, AgentRun, Notification
        )
        from sqlalchemy import delete

        demo_meeting_ids = ["mtg-demo-001"]
        m_stmt = select(Meeting.id).where(Meeting.id.in_(demo_meeting_ids) | Meeting.title.ilike("%demo%") | Meeting.title.ilike("%Sprint Execution%"))
        found_m_ids = (await db.execute(m_stmt)).scalars().all()
        all_target_meeting_ids = list(set(demo_meeting_ids + list(found_m_ids)))

        if all_target_meeting_ids:
            t_stmt = select(Task.id).where(Task.meeting_id.in_(all_target_meeting_ids))
            t_ids = (await db.execute(t_stmt)).scalars().all()

            if t_ids:
                await db.execute(delete(Reminder).where(Reminder.task_id.in_(t_ids)))
                await db.execute(delete(Approval).where(Approval.task_id.in_(t_ids)))
                await db.execute(delete(TaskDependency).where(TaskDependency.task_id.in_(t_ids)))
                await db.execute(delete(Task).where(Task.id.in_(t_ids)))

            await db.execute(delete(MeetingTranscript).where(MeetingTranscript.meeting_id.in_(all_target_meeting_ids)))
            await db.execute(delete(Speaker).where(Speaker.meeting_id.in_(all_target_meeting_ids)))
            await db.execute(delete(AgentRun).where(AgentRun.meeting_id.in_(all_target_meeting_ids)))
            await db.execute(delete(Meeting).where(Meeting.id.in_(all_target_meeting_ids)))

        demo_emails = [
            "sarah.chen@meetme.work", "rahul.sharma@meetme.work",
            "elena.rostova@meetme.work", "marcus.vance@meetme.work"
        ]
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.email.in_(demo_emails)))
        await db.execute(delete(User).where(User.email.in_(demo_emails)))
        await db.commit()

        return {"status": "SUCCESS", "message": "Demo data wiped cleanly from database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to wipe demo data: {str(e)}")

@router.get("/api/notifications")
async def list_notifications(
    workspace_id: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(Notification).where(Notification.workspace_id == ws_id).order_by(desc(Notification.created_at)).limit(limit)
    res = await db.execute(stmt)
    notifications = res.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]

@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Notification).where(Notification.id == notification_id)
    res = await db.execute(stmt)
    notif = res.scalar_one_or_none()
    if notif:
        notif.is_read = True
        await db.commit()
    return {"status": "OK"}
