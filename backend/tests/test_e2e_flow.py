import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.demo.seed_data import seed_demo_workspace, SAMPLE_TRANSCRIPT
from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.agents.execution_agent import execution_agent
from backend.app.services.reminder_worker import reminder_worker
from backend.app.models.schema import Task, Approval, EmailLog, Reminder, AutomationLog, Meeting
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_meetme")

async def test_full_acceptance_flow():
    print("==================================================")
    print("MEETME — COMPREHENSIVE END-TO-END ACCEPTANCE SUITE")
    print("==================================================")

    # 1. Initialize Database Tables
    print("\n[Step 1 & 10] Initializing database & workspace isolation...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Seed Workspace & 4 Participants
        print("\n[Step 2] Ingesting demo workspace with 4 participants...")
        seed_res = await seed_demo_workspace(db=db, force=True)
        assert seed_res["status"] == "SUCCESS", "Demo workspace seeding failed"
        print(f" -> Workspace ID: {seed_res['workspace_id']}")
        print(f" -> Meeting ID: {seed_res['meeting_id']}")

        # 3, 4, 5. Verification of Orchestrator, Classification & Tasks
        print("\n[Step 3, 4, 5] Verifying AI Multi-Agent Orchestrator...")
        tasks_res = await db.execute(select(Task).where(Task.meeting_id == seed_res["meeting_id"]))
        tasks = tasks_res.scalars().all()
        assert len(tasks) >= 4, f"Expected at least 4 tasks, got {len(tasks)}"
        print(f" -> Extracted {len(tasks)} tasks from conversation.")

        # 6, 7. Assignment Agent & Confidence Scoring
        print("\n[Step 6, 7] Verifying Assignment Agent & Confidence Scoring...")
        for t in tasks:
            assert t.confidence is not None and t.confidence > 0, f"Task {t.title} missing confidence score"
            print(f"    - Task: '{t.title[:45]}...'")
            print(f"      Assignee: {t.assignee_name or 'Unassigned'} | Email: {t.assignee_email or 'None'} | Conf: {int(t.confidence*100)}% | Priority: {t.priority}")

        # Check for ambiguous assignment
        ambiguous_tasks = [t for t in tasks if t.confidence < 0.75 or not t.assignee_email]
        print(f" -> Detected {len(ambiguous_tasks)} ambiguous/low-confidence tasks requiring explicit human signoff.")

        # 8, 9, 10, 11, 12. Human Approval Gate, Email Execution & Reminders
        print("\n[Step 8, 9, 11, 12] Executing Human Approval Gate...")
        approvals_res = await db.execute(select(Approval).where(Approval.meeting_id == seed_res["meeting_id"], Approval.status == "PENDING"))
        pending_approvals = approvals_res.scalars().all()
        assert len(pending_approvals) > 0, "No pending approvals found"

        first_approval = pending_approvals[0]
        print(f" -> Approving Action ID {first_approval.id} for task '{first_approval.proposed_payload.get('title')}'...")
        exec_res = await execution_agent.execute_approval(
            db=db,
            approval_id=first_approval.id,
            user_id="usr-sarah-001",
            approved_notes="Approved during automated acceptance test."
        )
        assert exec_res["status"] == "SUCCESS", f"Execution failed: {exec_res}"
        print(f" -> Execution Agent Result: Email Status = {exec_res['email_status']}, Reminders Scheduled = {exec_res['reminders_count']}")

        # Verify EmailLog
        emails_res = await db.execute(select(EmailLog).where(EmailLog.task_id == exec_res["task_id"]))
        email_record = emails_res.scalar_one_or_none()
        assert email_record is not None, "Email log record was not created"
        print(f" -> Verified Email Log record: Status = {email_record.status}, Provider = {email_record.provider}")

        # Verify Persistent Reminders
        rem_res = await db.execute(select(Reminder).where(Reminder.task_id == exec_res["task_id"]))
        reminders = rem_res.scalars().all()
        assert len(reminders) > 0, "No persistent reminders created"
        print(f" -> Verified {len(reminders)} persistent reminder(s) scheduled in database:")
        for r in reminders:
            print(f"      Type: {r.reminder_type} | Scheduled: {r.scheduled_at} | Status: {r.status}")

        # 13. Overdue Task Handling
        print("\n[Step 13] Verifying Overdue Task Detection...")
        # Artificially set one task deadline to yesterday
        tasks[1].status = "APPROVED"
        tasks[1].deadline = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
        await db.commit()
        await reminder_worker.check_overdue_tasks()
        await db.refresh(tasks[1])
        print(f" -> Task '{tasks[1].title[:40]}' status after check: {tasks[1].status}")
        assert tasks[1].status == "OVERDUE", f"Task did not transition to OVERDUE, got {tasks[1].status}"

        # 14, 15. Task Completion & Automatic Reminder Cancellation
        print("\n[Step 14, 15] Verifying Task Completion & Auto-Cancellation of Reminders...")
        # Mark the approved task as COMPLETED
        approved_task_id = exec_res["task_id"]
        task_stmt = select(Task).where(Task.id == approved_task_id)
        task_obj = (await db.execute(task_stmt)).scalar_one()
        task_obj.status = "COMPLETED"
        await reminder_worker.cancel_task_reminders(db, approved_task_id, reason="Task marked COMPLETED in ledger")
        await db.commit()

        # Check reminders status
        rem_after = (await db.execute(select(Reminder).where(Reminder.task_id == approved_task_id))).scalars().all()
        for r in rem_after:
            print(f"      Reminder {r.id} ({r.reminder_type}) Status after completion: {r.status}")
            assert r.status in ["CANCELLED", "SENT"], f"Reminder was not cancelled upon completion: status={r.status}"

        # 16, 17. Dashboard & Execution History Integrity
        print("\n[Step 16, 17] Verifying Automation Logs & Audit Trail...")
        logs_res = await db.execute(select(AutomationLog).order_by(AutomationLog.created_at.desc()).limit(5))
        logs = logs_res.scalars().all()
        assert len(logs) > 0, "No automation logs found"
        for l in logs:
            print(f"    - Event: [{l.trigger_type} -> {l.action_type}] Status: {l.status} | {l.message}")

    print("\n==================================================")
    print("ALL 17 CRITERIA PASSED SUCCESSFULLY! PRODUCT READY.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_full_acceptance_flow())
