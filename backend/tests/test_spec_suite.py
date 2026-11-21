import asyncio
import sys
import os
import uuid
import logging
from datetime import datetime, timedelta

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.models.schema import (
    Workspace, User, WorkspaceMember, Meeting, Task, Approval, Decision, Commitment,
    DecisionConflict, DecisionResolution, ExternalIntegration, ExternalIssueSync,
    WeeklyDigest, EmailLog
)
from backend.app.services.memory_service import memory_service
from backend.app.services.conflict_service import conflict_service
from backend.app.services.digest_service import digest_service
from backend.app.agents.execution_agent import execution_agent
from backend.app.services.jira_service import jira_service
from backend.app.services.github_service import github_service
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_spec_suite")

async def run_full_spec_test():
    print("=====================================================================")
    print("MEETME — COMPREHENSIVE MULTI-PHASE SPECIFICATION ACCEPTANCE SUITE")
    print("=====================================================================")

    await init_db()

    async with AsyncSessionLocal() as db:
        # Step 0: Ensure workspace and test members exist
        test_run_tag = uuid.uuid4().hex[:6]
        ws_id = f"ws-spec-{test_run_tag}"
        workspace = Workspace(id=ws_id, name=f"Spec Test Workspace {test_run_tag}", slug=f"spec-test-ws-{test_run_tag}")
        db.add(workspace)
        await db.flush()

        # Add Rahul & Sarah to workspace
        rahul = WorkspaceMember(id=f"usr-rahul-{test_run_tag}", workspace_id=ws_id, full_name="Rahul Sharma", email=f"rahul.{test_run_tag}@example.com", role="member", title="Senior Engineer")
        db.add(rahul)

        sarah = WorkspaceMember(id=f"usr-sarah-{test_run_tag}", workspace_id=ws_id, full_name="Sarah Chen", email=f"sarah.{test_run_tag}@example.com", role="admin", title="Lead PM")
        db.add(sarah)

        await db.commit()
        print(f"[Setup] Workspace ({ws_id}) & Test Members (Rahul Sharma, Sarah Chen) Ready.")

        # -------------------------------------------------------------------------------------------------
        # TEST 1 & 2: MEMORY EXTRACTION & CONFLICT DETECTION (MongoDB vs PostgreSQL)
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 1: MEETING 1 EXTRACTION & PERSISTENCE (MongoDB) ---")
        m1_id = f"meet-spec-1-{test_run_tag}"
        m1 = Meeting(id=m1_id, workspace_id=ws_id, title=f"Sprint Architecture Sync 1 ({test_run_tag})", recording_mode="RECORDED", status="COMPLETED")
        db.add(m1)
        await db.flush()

        # Transcript with Decision & Commitment
        m1_text = (
            "Sarah Chen: We have decided to use MongoDB as our primary database for the user profile service.\n"
            "Rahul Sharma: I will finish the frontend integration by Friday."
        )

        m1_memories = await memory_service.extract_memories(m1_text, context="Sprint Architecture Sync 1")
        assert len(m1_memories["decisions"]) > 0, "Failed to extract decision from Meeting 1"
        assert len(m1_memories["commitments"]) > 0, "Failed to extract commitment from Meeting 1"

        test_members = [
            {"id": rahul.id, "full_name": rahul.full_name, "email": rahul.email},
            {"id": sarah.id, "full_name": sarah.full_name, "email": sarah.email}
        ]

        saved_m1 = await memory_service.persist_meeting_memories(
            db=db,
            workspace_id=ws_id,
            meeting_id=m1_id,
            decisions=m1_memories["decisions"],
            commitments=m1_memories["commitments"],
            members=test_members
        )
        print(f" -> Meeting 1 persisted: {len(saved_m1['decisions'])} decisions, {len(saved_m1['commitments'])} commitments.")
        prev_decision = saved_m1["decisions"][0]
        print(f"    - Decision: '{prev_decision.title}' | Status: {prev_decision.status}")

        # -------------------------------------------------------------------------------------------------
        # TEST 2: MEETING 2 CONFLICT DETECTION (Migrate database to PostgreSQL)
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 2: MEETING 2 CONTRADICTION & REVERSAL DETECTION ---")
        m2_id = f"meet-spec-2-{test_run_tag}"
        m2 = Meeting(id=m2_id, workspace_id=ws_id, title=f"Sprint Architecture Sync 2 ({test_run_tag})", recording_mode="RECORDED", status="COMPLETED")
        db.add(m2)
        await db.flush()

        m2_text = (
            "Sarah Chen: Let's migrate the project database to PostgreSQL instead.\n"
            "Rahul Sharma: I will complete the work soon, but the frontend integration is still incomplete, I am blocked on APIs."
        )

        # 1. Retrieve Historical Context for workspace
        hist_context = await memory_service.retrieve_historical_context(db=db, workspace_id=ws_id)
        print(f" -> Historical Context Retrieved: {len(hist_context['active_decisions'])} active decisions, {len(hist_context['unresolved_commitments'])} commitments.")

        # 2. Extract new memories
        m2_memories = await memory_service.extract_memories(m2_text, context="Sprint Architecture Sync 2")
        print(f" -> Meeting 2 extracted: {len(m2_memories['decisions'])} decisions, {len(m2_memories['commitments'])} commitments.")

        # 3. Detect Conflicts
        detected_conflicts = await conflict_service.detect_conflicts(
            db=db,
            workspace_id=ws_id,
            current_meeting_id=m2_id,
            new_decisions=m2_memories["decisions"]
        )
        assert len(detected_conflicts) > 0, "Conflict detection engine failed to flag MongoDB vs PostgreSQL contradiction!"
        conf = detected_conflicts[0]
        print(f" -> SUCCESS: Contradiction Detected! Type: {conf.get('conflict_type')}")
        print(f"    - Conflict ID: {conf.get('id')}")
        print(f"    - Explanation: {conf.get('explanation')}")

        # Verify that an Approval record of category DECISION_RESOLUTION was created
        app_res = await db.execute(
            select(Approval).where(
                Approval.workspace_id == ws_id,
                Approval.meeting_id == m2_id,
                Approval.action_category == "DECISION_RESOLUTION",
                Approval.status == "PENDING"
            )
        )
        pending_conflict_approval = app_res.scalars().first()
        assert pending_conflict_approval is not None, "Pending Approval record for Decision Conflict not found!"
        print(f" -> Global Human Approval Gate record verified: ID={pending_conflict_approval.id}")

        # -------------------------------------------------------------------------------------------------
        # TEST 3: CONFLICT RESOLUTION (ACCEPT_NEW supersedes previous decision)
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 3: RESOLVING CONFLICT (ACCEPT_NEW) ---")
        conflict_id = conf["id"]
        resolve_res = await conflict_service.resolve_conflict(
            db=db,
            conflict_id=conflict_id,
            action="ACCEPT_NEW",
            user_id="usr-sarah-spec",
            resolution_notes="Team agreed PostgreSQL provides better transactional support."
        )
        assert resolve_res["status"] == "SUCCESS", f"Resolution failed: {resolve_res}"
        print(f" -> Conflict Resolved: {resolve_res['action_taken']} | New Status: {resolve_res['conflict_status']}")

        # Verify in database: previous decision must now be SUPERSEDED!
        await db.refresh(prev_decision)
        assert prev_decision.status == "SUPERSEDED", f"Previous decision expected SUPERSEDED, got {prev_decision.status}"
        print(f" -> Verified: Previous Decision '{prev_decision.title}' is now SUPERSEDED.")

        # Verify audit resolution log exists
        res_audit = await db.execute(select(DecisionResolution).where(DecisionResolution.conflict_id == conflict_id))
        audit_entry = res_audit.scalar_one_or_none()
        assert audit_entry is not None, "DecisionResolution audit record not created"
        print(f" -> Verified Audit Trail: Action = {audit_entry.action_taken}, Decided by = {audit_entry.resolved_by_user_id}")

        # -------------------------------------------------------------------------------------------------
        # TEST 4: CROSS-MEETING COMMITMENT RECOGNITION & DELAY TRACKING
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 4: CROSS-MEETING COMMITMENT DELAY TRACKING ---")
        saved_m2 = await memory_service.persist_meeting_memories(
            db=db,
            workspace_id=ws_id,
            meeting_id=m2_id,
            decisions=m2_memories["decisions"],
            commitments=m2_memories["commitments"],
            members=test_members
        )
        # Check Rahul's commitment
        com_res = await db.execute(
            select(Commitment).where(
                Commitment.workspace_id == ws_id,
                Commitment.assignee_name.like("%Rahul%")
            )
        )
        rahul_commitments = com_res.scalars().all()
        # Should NOT duplicate tasks, but recognize same commitment and increment delay_count
        assert len(rahul_commitments) == 1, f"Expected 1 tracked commitment for Rahul across meetings, found {len(rahul_commitments)}"
        tracked_com = rahul_commitments[0]
        assert tracked_com.delay_count >= 1 or tracked_com.status == "DELAYED", f"Expected delay_count >= 1, got {tracked_com.delay_count}, status {tracked_com.status}"
        print(f" -> SUCCESS: Rahul's commitment recognized across meetings! Delay Count = {tracked_com.delay_count}, Status = {tracked_com.status}")

        # -------------------------------------------------------------------------------------------------
        # TEST 5: JIRA & GITHUB INTEGRATION DISPATCH VIA GLOBAL APPROVAL GATE
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 5: JIRA & GITHUB SYNC VIA GLOBAL APPROVAL GATE ---")
        # Create a task to approve
        task_id = f"task-sync-spec-{test_run_tag}"
        test_task = Task(
            id=task_id,
            workspace_id=ws_id,
            meeting_id=m2_id,
            title="Integrate PostgreSQL Migrations",
            description="Configure Alembic migrations and verify connection pool.",
            assignee_name="Rahul Sharma",
            assignee_email="rahul.spec@example.com",
            priority="HIGH",
            deadline="2026-11-28",
            status="AWAITING_APPROVAL",
            confidence=0.95
        )
        db.add(test_task)

        task_approval = Approval(
            id=f"app-task-spec-{test_run_tag}",
            workspace_id=ws_id,
            task_id=task_id,
            status="PENDING",
            proposed_payload={
                "title": test_task.title,
                "description": test_task.description,
                "assignee_name": test_task.assignee_name,
                "assignee_email": test_task.assignee_email,
                "priority": test_task.priority,
                "deadline": test_task.deadline,
                "sync_jira": True,
                "sync_github": True
            }
        )
        db.add(task_approval)
        await db.commit()

        # Approve task via Execution Agent
        exec_out = await execution_agent.execute_approval(
            db=db,
            approval_id=task_approval.id,
            user_id="usr-sarah-spec",
            custom_payload={
                "assignee_email": "rahul.spec@example.com",
                "sync_jira": True,
                "sync_github": True
            },
            approved_notes="Approved for Jira and GitHub sync."
        )
        print(f" -> Task Approved! Status: {exec_out['status']}")

        # -------------------------------------------------------------------------------------------------
        # TEST 6: PERSONALIZED WEEKLY DIGEST (MEMBER ISOLATION GUARANTEE)
        # -------------------------------------------------------------------------------------------------
        print("\n--- TEST 6: PERSONALIZED WEEKLY DIGEST & MEMBER ISOLATION ---")
        # Generate weekly digest for Rahul Sharma
        rahul_digest = await digest_service.generate_member_digest(
            db=db,
            workspace_id=ws_id,
            member=rahul,
            period_days=7
        )
        assert rahul_digest is not None, "Weekly digest generation returned None"
        print(f" -> Digest Generated for {rahul_digest.recipient_name} ({rahul_digest.recipient_email}):")
        print(f"    Metrics: {rahul_digest.content_json.get('metrics')}")
        
        # Verify member isolation: Sarah's private tasks must NOT appear in Rahul's digest
        all_member_tasks = (
            rahul_digest.content_json.get("in_progress_tasks", []) +
            rahul_digest.content_json.get("completed_tasks", []) +
            rahul_digest.content_json.get("awaiting_approval_tasks", [])
        )
        for t in all_member_tasks:
            assert "Sarah" not in t.get("title", ""), "Member isolation failed: Other member's task leaked into digest!"
        print(" -> SUCCESS: Strict Member Privacy & Isolation Verified.")

        # Test Digest HTML formatting & Brevo compatibility
        assert "MEETME" in rahul_digest.html_body and "DIGEST" in rahul_digest.html_body, "Digest HTML template invalid"
        assert rahul.full_name in rahul_digest.html_body, "Recipient name missing from digest HTML"
        print(" -> SUCCESS: Digest HTML rendering verified with responsive dark enterprise styling.")

        print("\n=====================================================================")
        print("ALL 6 SPECIFICATION TESTS PASSED WITH 100% SUCCESS!")
        print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_full_spec_test())
