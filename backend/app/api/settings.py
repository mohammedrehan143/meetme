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

router = APIRouter(tags=["settings"])

class UpdateSettingsRequest(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    resend_api_key: Optional[str] = None
    resend_from_email: Optional[str] = None

@router.get("/api/settings")
async def get_settings():
    def mask_key(k: Optional[str]) -> str:
        if not k:
            return "Not Configured"
        if len(k) < 8:
            return "********"
        return f"{k[:4]}...{k[-4:]}"

    return {
        "app_name": settings.APP_NAME,
        "app_env": settings.APP_ENV,
        "database_url": "Async SQLite / Supabase Compatible",
        "groq": {
            "is_configured": bool(settings.GROQ_API_KEY),
            "masked_key": mask_key(settings.GROQ_API_KEY),
            "model": settings.GROQ_MODEL,
            "whisper_model": settings.GROQ_WHISPER_MODEL
        },
        "resend": {
            "is_configured": bool(settings.RESEND_API_KEY),
            "masked_key": mask_key(settings.RESEND_API_KEY),
            "from_email": settings.RESEND_FROM_EMAIL
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
    if payload.resend_api_key is not None:
        settings.RESEND_API_KEY = payload.resend_api_key
        os.environ["RESEND_API_KEY"] = payload.resend_api_key
    if payload.resend_from_email is not None:
        settings.RESEND_FROM_EMAIL = payload.resend_from_email

    return {"status": "SUCCESS", "message": "Settings updated successfully."}

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
    return {"status": "SUCCESS"}
