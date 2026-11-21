import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.schema import Reminder, Task, EmailLog, AutomationLog, Notification
from backend.app.services.email_service import email_service
from backend.app.agents.email_agent import email_agent

logger = logging.getLogger("meetme.reminder_worker")

class ReminderWorker:
    def __init__(self):
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Reminder background worker started with Gmail SMTP & consolidated scheduling.")

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
        logger.info(f"Cancelled {len(reminders)} pending reminders for task {task_id}: {reason}")
        return len(reminders)

    async def recalculate_task_reminders(self, db: AsyncSession, task_id: str, new_deadline_str: str) -> int:
        """
        Recalculates scheduled timestamps for all pending reminders when a task's deadline changes.
        """
        stmt = select(Reminder).where(
            Reminder.task_id == task_id,
            Reminder.status == "PENDING"
        )
        res = await db.execute(stmt)
        reminders = res.scalars().all()
        if not reminders:
            return 0

        try:
            d_date = datetime.strptime(new_deadline_str, "%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Invalid deadline string '{new_deadline_str}' for recalculation: {e}")
            return 0

        now = datetime.utcnow()
        updated_count = 0
        for rem in reminders:
            if rem.reminder_type == "PRE_DEADLINE":
                new_scheduled = d_date - timedelta(days=1) + timedelta(hours=9)
                if new_scheduled < now:
                    new_scheduled = now + timedelta(minutes=5)
                rem.scheduled_at = new_scheduled
                updated_count += 1
            elif rem.reminder_type == "DEADLINE_DAY":
                new_scheduled = d_date + timedelta(hours=9)
                if new_scheduled < now:
                    new_scheduled = now + timedelta(minutes=10)
                rem.scheduled_at = new_scheduled
                updated_count += 1
            elif rem.reminder_type == "OVERDUE":
                new_scheduled = d_date + timedelta(days=1, hours=9)
                rem.scheduled_at = new_scheduled
                updated_count += 1

        if updated_count > 0:
            auto_log = AutomationLog(
                workspace_id=reminders[0].workspace_id,
                task_id=task_id,
                trigger_type="DEADLINE_UPDATED",
                action_type="RECALCULATE_REMINDERS",
                payload={"task_id": task_id, "new_deadline": new_deadline_str, "reminders_updated": updated_count},
                status="SUCCESS",
                message=f"Recalculated {updated_count} reminder schedules for task '{task_id}' with new deadline {new_deadline_str}."
            )
            db.add(auto_log)
            await db.commit()
            logger.info(f"Successfully recalculated {updated_count} reminders for task {task_id} to new deadline {new_deadline_str}.")

        return updated_count

    async def _worker_loop(self):
        while self.is_running:
            try:
                await self.process_pending_reminders()
                await self.check_overdue_tasks()
            except Exception as e:
                logger.error(f"Error in reminder worker loop: {e}", exc_info=True)
            
            await asyncio.sleep(15) # Check every 15 seconds

    async def process_pending_reminders(self):
        """
        Processes pending reminders whose scheduled_at <= now.
        Groups reminders by (email_address, reminder_type) to send CONSOLIDATED digest emails
        when multiple tasks are due for the same recipient under the same trigger.
        """
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            stmt = select(Reminder).where(
                Reminder.status == "PENDING",
                Reminder.scheduled_at <= now
            ).limit(50)

            res = await db.execute(stmt)
            all_pending = res.scalars().all()

            if not all_pending:
                return

            # Group by (email_address, reminder_type)
            groups: Dict[Tuple[str, str], List[Tuple[Reminder, Task]]] = defaultdict(list)

            for rem in all_pending:
                try:
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

                    groups[(rem.email_address, rem.reminder_type)].append((rem, task))
                except Exception as ex:
                    logger.error(f"Error validating reminder {rem.id}: {ex}")
                    rem.retry_count += 1
                    rem.last_error = str(ex)

            # Now process grouped reminders
            for (email_addr, rem_type), items in groups.items():
                if not items:
                    continue

                recipient_name = items[0][0].recipient or "Team Member"
                workspace_id = items[0][0].workspace_id

                # SINGLE TASK REMINDER
                if len(items) == 1:
                    rem, task = items[0]
                    email_data = email_agent.generate_single_reminder_email(
                        task={
                            "id": task.id,
                            "title": task.title,
                            "assignee_name": recipient_name,
                            "deadline": task.deadline,
                            "priority": task.priority,
                            "description": task.description
                        },
                        reminder_type=rem_type
                    )

                    idempotency_key = f"reminder_{rem.id}_{rem.scheduled_at.isoformat()}"

                    send_res = await email_service.send_email(
                        to=email_addr,
                        subject=email_data["subject"],
                        html=email_data["html"],
                        text=email_data["text"],
                        recipient_name=recipient_name,
                        email_type=f"REMINDER_{rem_type}",
                        task_ids=[task.id],
                        idempotency_key=idempotency_key
                    )

                    is_success = send_res.get("success", False)
                    email_status = send_res.get("status", "SENT" if is_success else "FAILED")
                    msg_id = send_res.get("id")
                    err_msg = send_res.get("error")

                    if is_success:
                        rem.status = "SENT"
                        rem.executed_at = datetime.utcnow()
                        rem.last_error = None
                        logger.info(f"Dispatched single reminder {rem.id} ({rem_type}) to {email_addr}.")
                    else:
                        rem.retry_count += 1
                        rem.last_error = err_msg or "Unknown dispatch failure"
                        if rem.retry_count >= 3:
                            rem.status = "FAILED"
                        else:
                            # Exponential backoff: reschedule for 2^retry_count minutes
                            rem.scheduled_at = datetime.utcnow() + timedelta(minutes=2 ** rem.retry_count)

                    # Persist EmailLog
                    email_log = EmailLog(
                        workspace_id=workspace_id,
                        task_id=task.id,
                        task_ids=[task.id],
                        recipient=recipient_name,
                        email_address=email_addr,
                        email_type=f"REMINDER_{rem_type}",
                        subject=email_data["subject"],
                        body_html=email_data["html"],
                        body_text=email_data["text"],
                        status=email_status,
                        provider=send_res.get("provider", "Gmail SMTP"),
                        message_id=msg_id,
                        provider_message_id=msg_id,
                        idempotency_key=idempotency_key,
                        error_message=err_msg,
                        retry_count=rem.retry_count,
                        sent_at=datetime.utcnow() if is_success else None
                    )
                    db.add(email_log)

                    auto_log = AutomationLog(
                        workspace_id=workspace_id,
                        task_id=task.id,
                        trigger_type="SCHEDULED_REMINDER_TRIGGER",
                        action_type=f"SEND_{rem_type}_EMAIL",
                        payload={"reminder_id": rem.id, "email_address": email_addr, "provider": "Gmail SMTP"},
                        status="SUCCESS" if is_success else "FAILED",
                        message=f"{rem_type} reminder sent to {email_addr} for '{task.title}'."
                    )
                    db.add(auto_log)

                # CONSOLIDATED MULTI-TASK DIGEST EMAIL
                else:
                    task_list = [
                        {
                            "id": t.id,
                            "title": t.title,
                            "deadline": t.deadline or "Approaching",
                            "priority": t.priority or "MEDIUM",
                            "description": t.description or ""
                        }
                        for _, t in items
                    ]
                    task_ids = [t.id for _, t in items]

                    email_data = email_agent.generate_consolidated_reminder_email(
                        recipient_name=recipient_name,
                        tasks=task_list,
                        reminder_type=rem_type
                    )

                    date_tag = now.strftime("%Y%m%d%H")
                    idempotency_key = f"consolidated_{email_addr}_{rem_type}_{date_tag}"

                    send_res = await email_service.send_email(
                        to=email_addr,
                        subject=email_data["subject"],
                        html=email_data["html"],
                        text=email_data["text"],
                        recipient_name=recipient_name,
                        email_type=f"CONSOLIDATED_{rem_type}",
                        task_ids=task_ids,
                        idempotency_key=idempotency_key
                    )

                    is_success = send_res.get("success", False)
                    email_status = send_res.get("status", "SENT" if is_success else "FAILED")
                    msg_id = send_res.get("id")
                    err_msg = send_res.get("error")

                    for rem, task in items:
                        if is_success:
                            rem.status = "SENT"
                            rem.executed_at = datetime.utcnow()
                            rem.last_error = None
                        else:
                            rem.retry_count += 1
                            rem.last_error = err_msg or "Consolidated send failure"
                            if rem.retry_count >= 3:
                                rem.status = "FAILED"
                            else:
                                rem.scheduled_at = datetime.utcnow() + timedelta(minutes=2 ** rem.retry_count)

                    # Persist single consolidated EmailLog
                    email_log = EmailLog(
                        workspace_id=workspace_id,
                        task_id=task_ids[0] if task_ids else None,
                        task_ids=task_ids,
                        recipient=recipient_name,
                        email_address=email_addr,
                        email_type=f"CONSOLIDATED_{rem_type}",
                        subject=email_data["subject"],
                        body_html=email_data["html"],
                        body_text=email_data["text"],
                        status=email_status,
                        provider=send_res.get("provider", "Gmail SMTP"),
                        message_id=msg_id,
                        provider_message_id=msg_id,
                        idempotency_key=idempotency_key,
                        error_message=err_msg,
                        retry_count=items[0][0].retry_count,
                        sent_at=datetime.utcnow() if is_success else None
                    )
                    db.add(email_log)

                    auto_log = AutomationLog(
                        workspace_id=workspace_id,
                        trigger_type="CONSOLIDATED_REMINDER_TRIGGER",
                        action_type=f"SEND_CONSOLIDATED_{rem_type}_EMAIL",
                        payload={
                            "email_address": email_addr,
                            "task_count": len(items),
                            "task_ids": task_ids,
                            "provider": "Gmail SMTP"
                        },
                        status="SUCCESS" if is_success else "FAILED",
                        message=f"Consolidated {rem_type} digest ({len(items)} tasks) sent to {email_addr} via Gmail SMTP."
                    )
                    db.add(auto_log)
                    logger.info(f"Dispatched consolidated {rem_type} digest with {len(items)} tasks to {email_addr}.")

            await db.commit()

    async def check_overdue_tasks(self):
        """
        Scans for tasks whose deadline has elapsed and transitions status to OVERDUE.
        Ensures overdue reminders exist for newly overdue tasks.
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
                    # Create an overdue reminder scheduled for immediate dispatch
                    overdue_rem = Reminder(
                        workspace_id=task.workspace_id,
                        task_id=task.id,
                        task_ids=[task.id],
                        recipient=task.assignee_name or "Team Member",
                        email_address=task.assignee_email,
                        reminder_type="OVERDUE",
                        scheduled_at=datetime.utcnow(),
                        status="PENDING",
                        retry_count=0
                    )
                    db.add(overdue_rem)

            await db.commit()

reminder_worker = ReminderWorker()
