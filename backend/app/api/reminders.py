from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Reminder, Task
from backend.app.services.reminder_worker import reminder_worker

router = APIRouter(prefix="/api/reminders", tags=["reminders"])

@router.get("")
async def list_reminders(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    query = select(Reminder).where(Reminder.workspace_id == ws_id)
    if status:
        query = query.where(Reminder.status == status)
    query = query.order_by(desc(Reminder.scheduled_at)).limit(limit)

    res = await db.execute(query)
    reminders = res.scalars().all()

    output = []
    for r in reminders:
        # Get task title
        t_stmt = select(Task.title).where(Task.id == r.task_id)
        t_res = await db.execute(t_stmt)
        task_title = t_res.scalar_one_or_none() or "Unknown Task"

        output.append({
            "id": r.id,
            "task_id": r.task_id,
            "task_title": task_title,
            "recipient": r.recipient,
            "email_address": r.email_address,
            "reminder_type": r.reminder_type,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "status": r.status,
            "retry_count": r.retry_count,
            "last_error": r.last_error,
            "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return output

@router.post("/{reminder_id}/cancel")
async def cancel_reminder(reminder_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Reminder).where(Reminder.id == reminder_id)
    res = await db.execute(stmt)
    rem = res.scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")

    rem.status = "CANCELLED"
    rem.last_error = "Manually cancelled by user."
    await db.commit()
    return {"status": "CANCELLED", "reminder_id": reminder_id}

@router.post("/process-now")
async def trigger_reminder_worker_now():
    """Manually triggers the background worker loop immediately."""
    await reminder_worker.process_pending_reminders()
    await reminder_worker.check_overdue_tasks()
    return {"status": "SUCCESS", "message": "Triggered reminder worker."}
