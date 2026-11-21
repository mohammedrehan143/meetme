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
        "smtp": {
            "is_configured": email_service.is_configured,
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "email": settings.SMTP_EMAIL or "",
            "masked_password": mask_key(settings.SMTP_PASSWORD),
            "from_name": settings.SMTP_FROM_NAME,
            "provider": "Gmail SMTP"
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
async def test_smtp_connection():
    """
    Validates Gmail SMTP authentication via STARTTLS on port 587.
    """
    result = email_service.test_connection()
    return result

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
