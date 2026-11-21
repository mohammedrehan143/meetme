import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.schema import Reminder, Task, EmailLog, AutomationLog, Notification
from backend.app.services.resend_service import resend_service
from backend.app.agents.email_agent import email_agent

logger = logging.getLogger("meetme.reminder_worker")

class ReminderWorker:
    def __init__(self):
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Reminder background worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Reminder background worker stopped.")

    async def cancel_task_reminders(self, db: AsyncSession, task_id: str, reason: str = "Task completed"):
        """
        Immediately cancels all pending future reminders associated with a completed or rejected task.
        """
        stmt = select(Reminder).where(
            Reminder.task_id == task_id,
            Reminder.status == "PENDING"
        )
        res = await db.execute(stmt)
        reminders = res.scalars().all()
        for rem in reminders:
            rem.status = "CANCELLED"
            rem.last_error = reason
        await db.commit()
        return len(reminders)

    async def _worker_loop(self):
        while self.is_running:
            try:
                await self.process_pending_reminders()
                await self.check_overdue_tasks()
            except Exception as e:
                logger.error(f"Error in reminder worker loop: {e}", exc_info=True)
            
            await asyncio.sleep(15) # Check every 15 seconds

    async def process_pending_reminders(self):
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            stmt = select(Reminder).where(
                Reminder.status == "PENDING",
                Reminder.scheduled_at <= now
            ).limit(20)

            res = await db.execute(stmt)
            reminders = res.scalars().all()

            for rem in reminders:
                try:
                    # 1. Check associated task
                    task_stmt = select(Task).where(Task.id == rem.task_id)
                    task_res = await db.execute(task_stmt)
                    task = task_res.scalar_one_or_none()

                    if not task:
                        rem.status = "CANCELLED"
                        rem.last_error = "Associated task no longer exists."
                        continue

                    # Cancel reminder if task is already completed or rejected
                    if task.status in ["COMPLETED", "REJECTED"]:
                        rem.status = "CANCELLED"
                        rem.last_error = f"Task is {task.status}."
                        logger.info(f"Cancelled reminder {rem.id} because task {task.id} is {task.status}.")
                        
                        auto_log = AutomationLog(
                            workspace_id=rem.workspace_id,
                            task_id=task.id,
                            trigger_type="TASK_COMPLETED",
                            action_type="CANCEL_REMINDER",
                            payload={"reminder_id": rem.id, "reason": f"Task {task.status}"},
                            status="SUCCESS",
                            message=f"Auto-cancelled reminder for '{task.title}'."
                        )
                        db.add(auto_log)
                        continue

                    # 2. Generate email
                    email_data = email_agent.generate_reminder_email(
                        task={
                            "title": task.title,
                            "assignee_name": rem.recipient,
                            "deadline": task.deadline
                        },
                        reminder_type=rem.reminder_type
                    )

                    # 3. Send via Resend service
                    send_res = await resend_service.send_email(
                        to=rem.email_address,
                        subject=email_data["subject"],
                        html=email_data["html"],
                        text=email_data["text"]
                    )

                    if send_res.get("success"):
                        rem.status = "SENT"
                        rem.executed_at = datetime.utcnow()
                        rem.last_error = None
                        logger.info(f"Dispatched reminder {rem.id} ({rem.reminder_type}) to {rem.email_address}.")
                    else:
                        rem.retry_count += 1
                        rem.last_error = send_res.get("error", "Unknown dispatch failure")
                        if rem.retry_count >= 3:
                            rem.status = "FAILED"
                        else:
                            # Exponential backoff: reschedule for 2 minutes * retry_count
                            rem.scheduled_at = datetime.utcnow() + timedelta(minutes=2 * rem.retry_count)

                    # 4. Log to EmailLog and AutomationLog
                    email_log = EmailLog(
                        workspace_id=rem.workspace_id,
                        task_id=task.id,
                        recipient=rem.recipient,
                        email_address=rem.email_address,
                        subject=email_data["subject"],
                        body_html=email_data["html"],
                        body_text=email_data["text"],
                        status=send_res.get("status", "SENT"),
                        provider=send_res.get("provider", "Resend"),
                        provider_message_id=send_res.get("id"),
                        error_message=send_res.get("error"),
                        sent_at=datetime.utcnow() if send_res.get("success") else None
                    )
                    db.add(email_log)

                    auto_log = AutomationLog(
                        workspace_id=rem.workspace_id,
                        task_id=task.id,
                        trigger_type="SCHEDULED_REMINDER_TRIGGER",
                        action_type=f"SEND_{rem.reminder_type}_EMAIL",
                        payload={"reminder_id": rem.id, "email_address": rem.email_address},
                        status="SUCCESS" if send_res.get("success") else "FAILED",
                        message=f"{rem.reminder_type} sent to {rem.email_address} for task '{task.title}'."
                    )
                    db.add(auto_log)

                except Exception as ex:
                    logger.error(f"Error executing reminder {rem.id}: {ex}")
                    rem.retry_count += 1
                    rem.last_error = str(ex)

            await db.commit()

    async def check_overdue_tasks(self):
        """
        Scans for tasks whose deadline has elapsed and transitions status to OVERDUE.
        """
        async with AsyncSessionLocal() as db:
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            stmt = select(Task).where(
                Task.status.in_(["APPROVED", "ASSIGNED", "IN_PROGRESS"]),
                Task.deadline.isnot(None),
                Task.deadline < today_str
            )
            res = await db.execute(stmt)
            overdue_tasks = res.scalars().all()

            for task in overdue_tasks:
                task.status = "OVERDUE"
                
                # Check if an OVERDUE reminder already exists
                rem_stmt = select(Reminder).where(
                    Reminder.task_id == task.id,
                    Reminder.reminder_type == "OVERDUE"
                )
                rem_res = await db.execute(rem_stmt)
                if not rem_res.scalar_one_or_none() and task.assignee_email:
                    # Create an immediate overdue reminder
                    overdue_rem = Reminder(
                        workspace_id=task.workspace_id,
                        task_id=task.id,
                        recipient=task.assignee_name or "Team Member",
                        email_address=task.assignee_email,
                        reminder_type="OVERDUE",
                        scheduled_at=datetime.utcnow(),
                        status="PENDING"
                    )
                    db.add(overdue_rem)

            await db.commit()

reminder_worker = ReminderWorker()
