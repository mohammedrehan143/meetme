import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.schema import Task, Approval, EmailLog, Reminder, AutomationLog, Notification
from backend.app.services.resend_service import resend_service
from backend.app.agents.email_agent import email_agent

logger = logging.getLogger("meetme.agents.execution")

class ExecutionAgent:
    """
    Executes approved actions with strict human authorization.
    Never sends emails or creates external schedules without verified approval.
    """
    async def execute_approval(
        self,
        db: AsyncSession,
        approval_id: str,
        user_id: Optional[str] = None,
        custom_payload: Optional[Dict[str, Any]] = None,
        approved_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Fetch approval record
        stmt = select(Approval).where(Approval.id == approval_id)
        res = await db.execute(stmt)
        approval = res.scalar_one_or_none()

        if not approval:
            raise ValueError(f"Approval {approval_id} not found.")

        if approval.status == "APPROVED":
            return {"status": "ALREADY_APPROVED", "message": "This approval was already executed."}

        # 2. Fetch associated task
        task_stmt = select(Task).where(Task.id == approval.task_id)
        task_res = await db.execute(task_stmt)
        task = task_res.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {approval.task_id} not found.")

        payload = custom_payload or approval.proposed_payload or {}

        # 3. Update task with approved/modified fields
        if "title" in payload:
            task.title = payload["title"]
        if "description" in payload:
            task.description = payload["description"]
        if "assignee_name" in payload:
            task.assignee_name = payload["assignee_name"]
        if "assignee_email" in payload:
            task.assignee_email = payload["assignee_email"]
        if "assignee_id" in payload:
            task.assignee_id = payload["assignee_id"]
        if "deadline" in payload:
            task.deadline = payload["deadline"]
        if "priority" in payload:
            task.priority = payload["priority"]

        task.status = "APPROVED"
        task.updated_at = datetime.utcnow()

        # 4. Update approval record
        approval.status = "APPROVED"
        approval.approved_payload = payload
        approval.approved_recipient = task.assignee_email
        approval.approval_notes = approved_notes or "Approved by user"
        approval.approved_at = datetime.utcnow()
        if user_id:
            approval.user_id = user_id

        # 5. Generate and Send Email
        email_sent = False
        email_id = None
        email_status = "SKIPPED"
        error_msg = None

        if task.assignee_email:
            email_content = payload.get("email_content")
            if not email_content:
                email_content = email_agent.generate_task_assignment_email(
                    task={
                        "title": task.title,
                        "description": task.description,
                        "assignee_name": task.assignee_name,
                        "deadline": task.deadline,
                        "priority": task.priority,
                        "evidence_quote": task.evidence_quote,
                    },
                    meeting_title=payload.get("meeting_title", "Sprint Execution Meeting")
                )

            email_res = await resend_service.send_email(
                to=task.assignee_email,
                subject=email_content.get("subject", f"Action Item Assigned: {task.title}"),
                html=email_content.get("html", "<p>Task Assigned</p>"),
                text=email_content.get("text", "")
            )

            email_status = email_res.get("status", "FAILED")
            email_id = email_res.get("id")
            error_msg = email_res.get("error")
            email_sent = email_res.get("success", False)

            # Persist EmailLog
            email_log = EmailLog(
                workspace_id=task.workspace_id,
                task_id=task.id,
                meeting_id=task.meeting_id,
                recipient=task.assignee_name or "Team Member",
                email_address=task.assignee_email,
                subject=email_content.get("subject", f"Action Item Assigned: {task.title}"),
                body_html=email_content.get("html", ""),
                body_text=email_content.get("text", ""),
                status=email_status,
                provider=email_res.get("provider", "Resend"),
                provider_message_id=email_id,
                error_message=error_msg,
                sent_at=datetime.utcnow() if email_sent else None
            )
            db.add(email_log)

        # 6. Schedule persistent reminders
        # Deadline calculation
        scheduled_reminders = []
        if task.deadline and task.assignee_email:
            try:
                # Parse deadline (YYYY-MM-DD)
                d_date = datetime.strptime(task.deadline, "%Y-%m-%d")
                
                # Pre-deadline reminder (24 hours before 9:00 AM of deadline day)
                pre_reminder_time = d_date - timedelta(days=1, hours=15) # e.g. previous day
                if pre_reminder_time < datetime.utcnow():
                    pre_reminder_time = datetime.utcnow() + timedelta(minutes=5) # immediate demo or 5 mins

                rem1 = Reminder(
                    workspace_id=task.workspace_id,
                    task_id=task.id,
                    recipient=task.assignee_name or "Team Member",
                    email_address=task.assignee_email,
                    reminder_type="PRE_DEADLINE",
                    scheduled_at=pre_reminder_time,
                    status="PENDING"
                )
                db.add(rem1)
                scheduled_reminders.append("PRE_DEADLINE")

                # Deadline day reminder
                rem2 = Reminder(
                    workspace_id=task.workspace_id,
                    task_id=task.id,
                    recipient=task.assignee_name or "Team Member",
                    email_address=task.assignee_email,
                    reminder_type="DEADLINE_DAY",
                    scheduled_at=d_date + timedelta(hours=9), # 9am deadline day
                    status="PENDING"
                )
                db.add(rem2)
                scheduled_reminders.append("DEADLINE_DAY")
            except Exception as e:
                logger.warning(f"Could not parse deadline '{task.deadline}' for reminder schedule: {e}")

        # 7. Log automation action
        auto_log = AutomationLog(
            workspace_id=task.workspace_id,
            meeting_id=task.meeting_id,
            task_id=task.id,
            trigger_type="HUMAN_APPROVAL",
            action_type="EXECUTE_ASSIGNMENT",
            payload={
                "task_id": task.id,
                "email_sent": email_sent,
                "email_status": email_status,
                "reminders_scheduled": scheduled_reminders
            },
            status="SUCCESS" if (email_sent or not task.assignee_email) else "PARTIAL",
            message=f"Task '{task.title}' approved. Email status: {email_status}. Reminders: {len(scheduled_reminders)}"
        )
        db.add(auto_log)

        # 8. Notification
        notif = Notification(
            workspace_id=task.workspace_id,
            user_id=user_id,
            title="Task Executed",
            message=f"'{task.title}' was approved and dispatched to {task.assignee_email or 'unassigned'}.",
            type="SUCCESS",
            link=f"/tasks"
        )
        db.add(notif)

        await db.commit()
        await db.refresh(task)

        return {
            "status": "SUCCESS",
            "task_id": task.id,
            "task_status": task.status,
            "email_status": email_status,
            "email_id": email_id,
            "reminders_count": len(scheduled_reminders)
        }

execution_agent = ExecutionAgent()
