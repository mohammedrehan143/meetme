import asyncio
import os
import sys
import uuid
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import select

from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.schema import Workspace, Task, Approval, EmailLog, Reminder, AutomationLog
from backend.app.services.email_service import GmailSMTPService, email_service
from backend.app.agents.execution_agent import execution_agent
from backend.app.agents.email_agent import email_agent
from backend.app.services.reminder_worker import ReminderWorker, reminder_worker

async def run_all_tests():
    print("=" * 70)
    print("MEETME — GMAIL SMTP & CONSOLIDATED REMINDERS ACCEPTANCE TEST SUITE")
    print("=" * 70)

    await init_db()
    email_service.resend_api_key = None
    email_service.brevo_api_key = None

    ws_id = "ws-smtp-test-001"
    async with AsyncSessionLocal() as db:
        ws_stmt = select(Workspace).where(Workspace.id == ws_id)
        ws_res = await db.execute(ws_stmt)
        if not ws_res.scalar_one_or_none():
            ws = Workspace(id=ws_id, name="Gmail SMTP Test Workspace", slug="smtp-test-org")
            db.add(ws)
            await db.commit()

    # --------------------------------------------------------------------------
    # TEST 1: Native Gmail SMTP Engine & STARTTLS Connection Handler
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Native Gmail SMTP Engine & STARTTLS Handshake...")
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server
        mock_server.__enter__.return_value = mock_server

        # Test connection check with credentials
        test_svc = GmailSMTPService()
        test_svc.resend_api_key = None
        test_svc.brevo_api_key = None
        test_svc.email = "testsender@gmail.com"
        test_svc.password = "abcd efgh ijkl mnop"
        
        conn_res = test_svc.test_connection()
        assert conn_res["success"] is True, f"Connection test failed: {conn_res}"
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("testsender@gmail.com", "abcd efgh ijkl mnop")
        print("  -> STARTTLS handshake and login verified successfully.")

        # Test sending an email via SMTP
        send_res = await test_svc.send_email(
            to="recipient@example.com",
            subject="MEETME Action Item",
            html="<p>Test HTML</p>",
            text="Test Text",
            recipient_name="Alex River",
            email_type="TASK_ASSIGNMENT",
            task_ids=["task-001"],
            idempotency_key="test_key_001"
        )
        assert send_res["success"] is True
        assert send_res["provider"] == "Gmail SMTP"
        assert send_res["status"] == "SENT"
        assert send_res["id"] is not None
        mock_server.send_message.assert_called_once()
        print(f"  -> Email dispatched via smtplib: Message-ID = {send_res['id']}")

    # --------------------------------------------------------------------------
    # TEST 2: Task Approval & Task Assignment Email Dispatch
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Task Approval Dispatches Assignment Email...")
    t2_uuid = uuid.uuid4().hex[:8]
    test_task_id = f"task-approval-{t2_uuid}"
    test_approval_id = f"appr-{t2_uuid}"

    async with AsyncSessionLocal() as db:
        task = Task(
            id=test_task_id,
            workspace_id=ws_id,
            title="Implement OAuth authentication flow",
            description="Set up Google OAuth and session management",
            assignee_name="Elena Rostova",
            assignee_email="elena@company.com",
            deadline="2026-11-28",
            priority="HIGH",
            evidence_quote="Elena: I will implement the OAuth flow by Nov 28.",
            status="AWAITING_APPROVAL"
        )
        db.add(task)
        approval = Approval(
            id=test_approval_id,
            workspace_id=ws_id,
            task_id=task.id,
            status="PENDING",
            proposed_payload={
                "title": task.title,
                "description": task.description,
                "assignee_name": task.assignee_name,
                "assignee_email": task.assignee_email,
                "deadline": task.deadline,
                "priority": task.priority
            }
        )
        db.add(approval)
        await db.commit()

        exec_res = await execution_agent.execute_approval(
            db=db,
            approval_id=approval.id,
            approved_notes="Approved for sprint execution."
        )
        assert exec_res["status"] == "SUCCESS"
        assert exec_res["task_status"] == "APPROVED"
        print(f"  -> Approval executed: Task Status = {exec_res['task_status']}")

        # Verify EmailLog record
        email_log_stmt = select(EmailLog).where(EmailLog.task_id == task.id)
        email_log_res = await db.execute(email_log_stmt)
        email_log = email_log_res.scalar_one_or_none()
        assert email_log is not None, "EmailLog record not created"
        assert email_log.email_address == "elena@company.com"
        assert email_log.provider in ["Gmail SMTP", "Gmail SMTP (Simulated)"]
        assert email_log.email_type == "TASK_ASSIGNMENT"
        assert task.id in email_log.task_ids
        print(f"  -> EmailLog verified: Type = {email_log.email_type}, Provider = {email_log.provider}, Recipient = {email_log.recipient}")

    # --------------------------------------------------------------------------
    # TEST 3: Consolidated Emails (10 tasks assigned to 4 people -> exactly 4 emails)
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Consolidated Reminders: 10 Tasks to 4 People -> Exactly 4 Emails...")
    async with AsyncSessionLocal() as db:
        # Define 4 team members with a total of 10 tasks
        # Rahul: 4 tasks (due tomorrow)
        # Arjun: 3 tasks (due tomorrow)
        # Rehan: 2 tasks (due tomorrow)
        # Elena: 1 task (due tomorrow)
        # Total = 10 tasks!
        team_assignments = [
            ("Rahul Sharma", "rahul@company.com", 4),
            ("Arjun Patel", "arjun@company.com", 3),
            ("Rehan Khan", "rehan@company.com", 2),
            ("Elena Rostova", "elena@company.com", 1),
        ]

        now = datetime.utcnow()
        scheduled_time = now - timedelta(minutes=5) # eligible for dispatch now
        all_created_reminders = []
        created_task_ids = []

        for name, email_addr, task_count in team_assignments:
            for idx in range(task_count):
                t_id = f"task-cons-{name[:3].lower()}-{idx}-{int(now.timestamp())}"
                t = Task(
                    id=t_id,
                    workspace_id=ws_id,
                    title=f"{name} Deliverable #{idx+1}",
                    description=f"Action item #{idx+1} for {name}",
                    assignee_name=name,
                    assignee_email=email_addr,
                    deadline="2026-11-25",
                    priority="HIGH",
                    status="APPROVED"
                )
                db.add(t)
                created_task_ids.append(t_id)

                rem = Reminder(
                    workspace_id=ws_id,
                    task_id=t_id,
                    task_ids=[t_id],
                    recipient=name,
                    email_address=email_addr,
                    reminder_type="PRE_DEADLINE",
                    scheduled_at=scheduled_time,
                    status="PENDING",
                    retry_count=0
                )
                db.add(rem)
                all_created_reminders.append(rem)

        await db.commit()
        assert len(created_task_ids) == 10, f"Expected 10 tasks, created {len(created_task_ids)}"
        print(f"  -> Created 10 tasks across 4 assignees with scheduled PRE_DEADLINE reminders.")

        # Capture count of email logs before processing
        pre_email_count = len((await db.execute(select(EmailLog).where(EmailLog.workspace_id == ws_id))).scalars().all())

        # Run the reminder worker processor
        await reminder_worker.process_pending_reminders()

        # Expire session cache to ensure fresh read from database
        db.expire_all()

        # Capture count of email logs after processing
        post_emails = (await db.execute(select(EmailLog).where(EmailLog.workspace_id == ws_id))).scalars().all()
        new_emails = post_emails[pre_email_count:]

        # CRITICAL ASSERTION: Exactly 4 emails generated for 10 tasks across 4 people!
        print(f"  -> New emails dispatched by reminder worker: {len(new_emails)}")
        assert len(new_emails) == 4, f"CRITICAL FAIL: Expected exactly 4 emails for 4 recipients, got {len(new_emails)}!"

        # Verify each email's recipient and task grouping
        for em in new_emails:
            print(f"    - Recipient: {em.recipient} ({em.email_address}) | Type: {em.email_type} | Tasks linked: {len(em.task_ids)}")
            if len(em.task_ids) > 1:
                assert em.email_type.startswith("CONSOLIDATED_"), f"Multi-task email should be CONSOLIDATED, got {em.email_type}"
                assert "DIGEST" in em.subject.upper(), f"Expected DIGEST in subject, got {em.subject}"

        # Verify all 10 reminders are now SENT
        updated_rems = (await db.execute(select(Reminder).where(Reminder.task_id.in_(created_task_ids)))).scalars().all()
        for r in updated_rems:
            print(f"      Reminder {r.id}: Task {r.task_id} -> Status = {r.status}, Error = {r.last_error}")
        assert all(r.status == "SENT" for r in updated_rems), f"Not all 10 reminders were marked as SENT! Statuses: {[r.status for r in updated_rems]}"
        print("  -> Verified: Exactly 4 consolidated emails generated and all 10 reminders updated to SENT.")

    # --------------------------------------------------------------------------
    # TEST 4: Multi-tier Reminder Scheduling (24h pre-deadline, deadline day, overdue)
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Multi-tier Automated Reminder Scheduling...")
    async with AsyncSessionLocal() as db:
        rem_stmt = select(Reminder).where(Reminder.task_id == test_task_id)
        rems = (await db.execute(rem_stmt)).scalars().all()
        types = [r.reminder_type for r in rems]
        assert "PRE_DEADLINE" in types, "PRE_DEADLINE reminder missing"
        assert "DEADLINE_DAY" in types, "DEADLINE_DAY reminder missing"
        assert "OVERDUE" in types, "OVERDUE reminder missing"
        print(f"  -> Verified reminder tiers scheduled: {types}")

    # --------------------------------------------------------------------------
    # TEST 5: Recovery After Simulated Backend Restarts
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Reminder Worker Recovery Across Backend Restarts...")
    t5_uuid = uuid.uuid4().hex[:8]
    reboot_task_id = f"task-reboot-{t5_uuid}"
    reboot_rem_id = f"rem-reboot-{t5_uuid}"

    async with AsyncSessionLocal() as db:
        # Insert a pending reminder simulating a shutdown while it was queued
        reboot_task = Task(
            id=reboot_task_id,
            workspace_id=ws_id,
            title="Database recovery verification task",
            assignee_name="Marcus Vance",
            assignee_email="marcus@company.com",
            deadline="2026-11-30",
            status="APPROVED"
        )
        db.add(reboot_task)
        reboot_rem = Reminder(
            id=reboot_rem_id,
            workspace_id=ws_id,
            task_id=reboot_task.id,
            task_ids=[reboot_task.id],
            recipient="Marcus Vance",
            email_address="marcus@company.com",
            reminder_type="PRE_DEADLINE",
            scheduled_at=datetime.utcnow() - timedelta(minutes=1),
            status="PENDING"
        )
        db.add(reboot_rem)
        await db.commit()

    # Simulate backend restart: create completely fresh ReminderWorker instance
    new_worker = ReminderWorker()
    await new_worker.process_pending_reminders()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Reminder).where(Reminder.id == reboot_rem_id))
        reboot_check = res.scalar_one_or_none()
        assert reboot_check is not None
        assert reboot_check.status == "SENT", f"Expected SENT after recovery, got {reboot_check.status}"
        print(f"  -> Fresh ReminderWorker successfully recovered and executed persisted reminder: Status = {reboot_check.status}")

    # --------------------------------------------------------------------------
    # TEST 6: Complete Task Cancels Future Reminders
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Completing a Task Immediately Cancels Future Reminders...")
    t6_uuid = uuid.uuid4().hex[:8]
    cancel_task_id = f"task-cancel-{t6_uuid}"

    async with AsyncSessionLocal() as db:
        cancel_task = Task(
            id=cancel_task_id,
            workspace_id=ws_id,
            title="Task to be completed early",
            assignee_name="Elena Rostova",
            assignee_email="elena@company.com",
            deadline="2026-12-05",
            status="APPROVED"
        )
        db.add(cancel_task)
        for r_type in ["PRE_DEADLINE", "DEADLINE_DAY", "OVERDUE"]:
            r = Reminder(
                workspace_id=ws_id,
                task_id=cancel_task.id,
                task_ids=[cancel_task.id],
                recipient="Elena Rostova",
                email_address="elena@company.com",
                reminder_type=r_type,
                scheduled_at=datetime.utcnow() + timedelta(days=5),
                status="PENDING"
            )
            db.add(r)
        await db.commit()

        # Mark task COMPLETED and call cancel_task_reminders
        cancelled_count = await reminder_worker.cancel_task_reminders(db, cancel_task.id, reason="Task marked COMPLETED")
        assert cancelled_count == 3, f"Expected 3 cancelled reminders, got {cancelled_count}"

        # Verify reminders in DB
        cancelled_rems = (await db.execute(select(Reminder).where(Reminder.task_id == cancel_task.id))).scalars().all()
        assert all(r.status == "CANCELLED" for r in cancelled_rems)
        print(f"  -> Cancelled {len(cancelled_rems)} pending reminders when task was completed.")

    # --------------------------------------------------------------------------
    # TEST 7: Changing a Deadline Recalculates Reminder Schedules
    # --------------------------------------------------------------------------
    print("\n[TEST 7] Changing Task Deadline Recalculates Reminder Schedules...")
    t7_uuid = uuid.uuid4().hex[:8]
    recalc_task_id = f"task-recalc-{t7_uuid}"

    async with AsyncSessionLocal() as db:
        recalc_task = Task(
            id=recalc_task_id,
            workspace_id=ws_id,
            title="Task with shifting deadline",
            assignee_name="Rahul Sharma",
            assignee_email="rahul@company.com",
            deadline="2026-11-25",
            status="APPROVED"
        )
        db.add(recalc_task)
        rem_pre = Reminder(
            workspace_id=ws_id,
            task_id=recalc_task.id,
            recipient="Rahul Sharma",
            email_address="rahul@company.com",
            reminder_type="PRE_DEADLINE",
            scheduled_at=datetime(2026, 11, 24, 9, 0),
            status="PENDING"
        )
        rem_day = Reminder(
            workspace_id=ws_id,
            task_id=recalc_task.id,
            recipient="Rahul Sharma",
            email_address="rahul@company.com",
            reminder_type="DEADLINE_DAY",
            scheduled_at=datetime(2026, 11, 25, 9, 0),
            status="PENDING"
        )
        db.add(rem_pre)
        db.add(rem_day)
        await db.commit()

        # Update deadline to 2026-12-10
        updated = await reminder_worker.recalculate_task_reminders(db, recalc_task.id, "2026-12-10")
        assert updated == 2, f"Expected 2 updated reminders, got {updated}"

        await db.refresh(rem_pre)
        await db.refresh(rem_day)
        assert rem_day.scheduled_at == datetime(2026, 12, 10, 9, 0), f"Unexpected deadline day schedule: {rem_day.scheduled_at}"
        assert rem_pre.scheduled_at == datetime(2026, 12, 9, 9, 0), f"Unexpected pre-deadline schedule: {rem_pre.scheduled_at}"
        print(f"  -> Successfully recalculated reminder schedules to new target: {rem_pre.scheduled_at} and {rem_day.scheduled_at}")

    # --------------------------------------------------------------------------
    # TEST 8: SMTP Failure Handling & Exponential Backoff
    # --------------------------------------------------------------------------
    print("\n[TEST 8] SMTP Failure & Exponential Backoff Retries...")
    t8_uuid = uuid.uuid4().hex[:8]
    fail_task_id = f"task-fail-{t8_uuid}"
    fail_rem_id = f"rem-fail-{t8_uuid}"

    async with AsyncSessionLocal() as db:
        fail_task = Task(
            id=fail_task_id,
            workspace_id=ws_id,
            title="Task testing SMTP retry logic",
            assignee_name="Arjun Patel",
            assignee_email="arjun@company.com",
            deadline="2026-11-26",
            status="APPROVED"
        )
        db.add(fail_task)
        fail_rem = Reminder(
            id=fail_rem_id,
            workspace_id=ws_id,
            task_id=fail_task.id,
            task_ids=[fail_task.id],
            recipient="Arjun Patel",
            email_address="arjun@company.com",
            reminder_type="PRE_DEADLINE",
            scheduled_at=datetime.utcnow() - timedelta(minutes=1),
            status="PENDING",
            retry_count=0
        )
        db.add(fail_rem)
        await db.commit()

    # Simulate SMTP failure
    with patch.object(email_service, "send_email", return_value={"success": False, "status": "FAILED", "error": "SMTP server connection timed out"}):
        await reminder_worker.process_pending_reminders()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Reminder).where(Reminder.id == fail_rem_id))
        r = res.scalar_one()
        assert r.retry_count == 1, f"Expected retry_count=1, got {r.retry_count}"
        assert r.status == "PENDING", f"Expected still PENDING for retry, got {r.status}"
        assert r.scheduled_at > datetime.utcnow(), "Scheduled time was not backed off"
        print(f"  -> Verified retry backoff: retry_count = {r.retry_count}, next attempt scheduled at = {r.scheduled_at}")

        # Simulate 2 more failures to trigger FAILED state
        r.scheduled_at = datetime.utcnow() - timedelta(minutes=1)
        r.retry_count = 2
        await db.commit()

    with patch.object(email_service, "send_email", return_value={"success": False, "status": "FAILED", "error": "SMTP server connection timed out"}):
        await reminder_worker.process_pending_reminders()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Reminder).where(Reminder.id == fail_rem_id))
        r = res.scalar_one()
        assert r.retry_count >= 3
        assert r.status == "FAILED", f"Expected FAILED after 3 retries, got {r.status}"
        print(f"  -> Verified max retries reached: Status = {r.status}, Retry Count = {r.retry_count}")

    # --------------------------------------------------------------------------
    # TEST 9: Duplicate Prevention via Idempotency Keys
    # --------------------------------------------------------------------------
    print("\n[TEST 9] Duplicate Email Prevention via Idempotency...")
    async with AsyncSessionLocal() as db:
        idemp_key = "idemp_test_unique_key_999"
        
        # First send
        res1 = await email_service.send_email(
            to="someone@example.com",
            subject="Action Item",
            html="<p>Test</p>",
            idempotency_key=idemp_key,
            workspace_id=ws_id,
            db=db
        )
        assert res1["success"] is True
        print(f"  -> First dispatch: status = {res1['status']}")

        # Second send with identical key
        res2 = await email_service.send_email(
            to="someone@example.com",
            subject="Action Item",
            html="<p>Test</p>",
            idempotency_key=idemp_key,
            workspace_id=ws_id,
            db=db
        )
        assert res2["status"] == "ALREADY_SENT", f"Expected ALREADY_SENT, got {res2['status']}"
        print(f"  -> Second dispatch prevented duplicate: status = {res2['status']}")

    # --------------------------------------------------------------------------
    # TEST 10: Email Activity Audit & Schema Verification
    # --------------------------------------------------------------------------
    print("\n[TEST 10] Email Audit Trail & Activity Schema...")
    from backend.app.api.emails import list_emails
    async with AsyncSessionLocal() as db:
        logs = await list_emails(workspace_id=ws_id, limit=20, db=db)
        assert len(logs) > 0, "No email logs found"
        for log in logs[:3]:
            assert "id" in log
            assert "task_ids" in log
            assert "email_type" in log
            assert "recipient" in log
            assert "email_address" in log
            assert "provider" in log
            assert "status" in log
            print(f"  -> Verified Log: Subject = '{log['subject'][:35]}...' | Provider = {log['provider']} | Status = {log['status']}")

    print("\n" + "=" * 70)
    print("ALL 10 GMAIL SMTP & CONSOLIDATED REMINDER TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
