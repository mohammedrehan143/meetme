from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Task, Reminder, AutomationLog

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None # LOW, MEDIUM, HIGH, URGENT
    status: Optional[str] = None # DETECTED, AWAITING_APPROVAL, APPROVED, ASSIGNED, IN_PROGRESS, COMPLETED, OVERDUE, REJECTED

@router.get("")
async def list_tasks(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    query = select(Task).where(Task.workspace_id == ws_id)

    if status and status != "ALL":
        query = query.where(Task.status == status)
    if priority and priority != "ALL":
        query = query.where(Task.priority == priority)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(Task.title.ilike(search_filter) | Task.description.ilike(search_filter))

    query = query.order_by(desc(Task.created_at))
    res = await db.execute(query)
    tasks = res.scalars().all()

    return [
        {
            "id": t.id,
            "meeting_id": t.meeting_id,
            "title": t.title,
            "description": t.description,
            "assignee_id": t.assignee_id,
            "assignee_name": t.assignee_name,
            "assignee_email": t.assignee_email,
            "deadline": t.deadline,
            "priority": t.priority,
            "confidence": t.confidence,
            "classification_type": t.classification_type,
            "status": t.status,
            "evidence_quote": t.evidence_quote,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        }
        for t in tasks
    ]

@router.get("/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Fetch reminders for this task
    rem_stmt = select(Reminder).where(Reminder.task_id == task_id)
    rem_res = await db.execute(rem_stmt)
    reminders = [
        {
            "id": r.id,
            "reminder_type": r.reminder_type,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "status": r.status
        }
        for r in rem_res.scalars().all()
    ]

    return {
        "id": task.id,
        "meeting_id": task.meeting_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "assignee_name": task.assignee_name,
        "assignee_email": task.assignee_email,
        "deadline": task.deadline,
        "priority": task.priority,
        "confidence": task.confidence,
        "classification_type": task.classification_type,
        "status": task.status,
        "evidence_quote": task.evidence_quote,
        "reminders": reminders,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }

@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    payload: UpdateTaskRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Task).where(Task.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status
    old_deadline = task.deadline
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.assignee_id is not None:
        task.assignee_id = payload.assignee_id
    if payload.assignee_name is not None:
        task.assignee_name = payload.assignee_name
    if payload.assignee_email is not None:
        task.assignee_email = payload.assignee_email
    if payload.deadline is not None:
        task.deadline = payload.deadline
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status

    task.updated_at = datetime.utcnow()

    # If deadline updated and changed, recalculate pending reminders
    if payload.deadline is not None and payload.deadline != old_deadline:
        from backend.app.services.reminder_worker import reminder_worker
        await reminder_worker.recalculate_task_reminders(db, task.id, payload.deadline)

    # If status transitioned to COMPLETED or REJECTED, automatically cancel pending reminders!
    if task.status in ["COMPLETED", "REJECTED"] and old_status not in ["COMPLETED", "REJECTED"]:
        from backend.app.services.reminder_worker import reminder_worker
        await reminder_worker.cancel_task_reminders(db, task.id, reason=f"Task marked {task.status}")

        auto_log = AutomationLog(
            workspace_id=task.workspace_id,
            task_id=task.id,
            trigger_type="STATUS_CHANGE",
            action_type="CANCEL_REMINDERS",
            payload={"task_id": task.id, "new_status": task.status},
            status="SUCCESS",
            message=f"Task '{task.title}' marked {task.status}. Pending reminders cancelled."
        )
        db.add(auto_log)

    await db.commit()
    await db.refresh(task)
    return {"status": "SUCCESS", "task_id": task.id, "task_status": task.status}

@router.post("/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    return await update_task(task_id, UpdateTaskRequest(status="COMPLETED"), db)

@router.delete("/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return {"status": "DELETED", "task_id": task_id}
