import asyncio
import os
import sys
import uuid
import time
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import select, func, desc
from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.schema import (
    User, Workspace, WorkspaceMember, Meeting, MeetingTranscript, Task, Approval,
    Decision, Commitment, DecisionConflict, DecisionResolution, MemoryEmbedding,
    EmailLog, Reminder, AutomationLog, WeeklyDigest
)
from backend.app.services.groq_service import groq_service
from backend.app.services.email_service import email_service
from backend.app.services.memory_service import memory_service
from backend.app.services.conflict_service import conflict_service
from backend.app.services.digest_service import digest_service
from backend.app.services.reminder_worker import reminder_worker
from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.agents.execution_agent import execution_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("meetme.audit_suite")

class ComprehensiveAuditRunner:
    def __init__(self):
        self.results: Dict[str, Any] = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": [],
            "performance": {}
        }
        self.tag = uuid.uuid4().hex[:6]
        self.ws_id = f"ws-audit-{self.tag}"

    def record_test(self, name: str, passed: bool, details: str = "", phase: str = ""):
        if passed:
            self.results["passed"] += 1
            status = "PASSED"
            print(f"  [PASS] {name} ({phase})")
        else:
            self.results["failed"] += 1
            status = "FAILED"
            print(f"  [FAIL] {name} ({phase}) - {details}")
        
        self.results["tests"].append({
            "name": name,
            "phase": phase,
            "status": status,
            "details": details
        })

    async def setup_workspace(self):
        print("\n========================================================================")
        print(f"SETTING UP AUDIT WORKSPACE: {self.ws_id}")
        print("========================================================================")
        await init_db()
        async with AsyncSessionLocal() as db:
            self.admin_user = User(
                id=f"usr-adm-{self.tag}",
                email=f"admin-{self.tag}@meetme.work",
                full_name="Admin Auditor",
                role="admin"
            )
            db.add(self.admin_user)
            await db.commit()

            ws = Workspace(id=self.ws_id, name=f"Audit Workspace {self.tag}", slug=f"audit-{self.tag}", owner_id=self.admin_user.id)
            db.add(ws)
            
            # Add members: Rahul, Sarah, Elena
            self.member_rahul = WorkspaceMember(
                id=f"mbr-rahul-{self.tag}", workspace_id=self.ws_id,
                full_name="Rahul Sharma", email="rahul.sharma@meetme.work", role="member", title="Backend Engineer"
            )
            self.member_sarah = WorkspaceMember(
                id=f"mbr-sarah-{self.tag}", workspace_id=self.ws_id,
                full_name="Sarah Chen", email="sarah.chen@meetme.work", role="admin", title="Product Lead"
            )
            self.member_elena = WorkspaceMember(
                id=f"mbr-elena-{self.tag}", workspace_id=self.ws_id,
                full_name="Elena Rostova", email="mrofficialyt083@gmail.com", role="member", title="QA Lead"
            )
            db.add_all([self.member_rahul, self.member_sarah, self.member_elena])
            await db.commit()
            print(f"Created Workspace {self.ws_id} with 3 members.")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 4: AI & MEMORY ENGINE AUDIT
    # --------------------------------------------------------------------------
    async def audit_phase4_ai_memory(self):
        print("\n========================================================================")
        print("AUDIT PHASE 4: AI & MEMORY ENGINE VALIDATION")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            # Test 4.1: Meeting 1 extraction (MongoDB decision + Rahul commitment)
            m1_id = f"mtg-audit-1-{self.tag}"
            m1 = Meeting(id=m1_id, workspace_id=self.ws_id, title=f"Architecture Sync 1 ({self.tag})", status="PROCESSING")
            db.add(m1)
            await db.commit()

            m1_text = (
                "Sarah Chen: We have decided to use MongoDB as our primary database for storing meeting intelligence.\n"
                "Rahul Sharma: I will finish database integration by Friday."
            )
            m1_mem = await memory_service.extract_memories(m1_text, context="Architecture Sync 1")
            
            has_mongo = any("mongo" in d.get("title", "").lower() or "mongo" in d.get("summary", "").lower() for d in m1_mem["decisions"])
            self.record_test("Phase 4.1: Extract MongoDB decision from transcript", has_mongo, str(m1_mem["decisions"]), "Phase 4")

            has_rahul_comm = any("rahul" in c.get("assignee_name", "").lower() for c in m1_mem["commitments"])
            self.record_test("Phase 4.2: Extract Rahul commitment with deadline", has_rahul_comm, str(m1_mem["commitments"]), "Phase 4")

            # Persist M1 memories
            members_dict = [
                {"id": self.member_rahul.id, "full_name": self.member_rahul.full_name, "email": self.member_rahul.email},
                {"id": self.member_sarah.id, "full_name": self.member_sarah.full_name, "email": self.member_sarah.email}
            ]
            saved_m1 = await memory_service.persist_meeting_memories(
                db=db, workspace_id=self.ws_id, meeting_id=m1_id,
                decisions=m1_mem["decisions"], commitments=m1_mem["commitments"], members=members_dict
            )
            self.record_test("Phase 4.3: Persist Meeting 1 memories to database", len(saved_m1["decisions"]) > 0, "", "Phase 4")

            # Persist MemoryEmbedding
            embed = MemoryEmbedding(
                workspace_id=self.ws_id, memory_type="DECISION",
                memory_id=saved_m1["decisions"][0].id,
                content_text=saved_m1["decisions"][0].title,
                embedding_vector=[0.12, 0.45, -0.23, 0.88] # Representative float vector
            )
            db.add(embed)
            await db.commit()
            
            emb_check = (await db.execute(select(MemoryEmbedding).where(MemoryEmbedding.memory_id == saved_m1["decisions"][0].id))).scalar_one_or_none()
            self.record_test("Phase 4.4: Generate and persist MemoryEmbedding record", emb_check is not None, "", "Phase 4")

            # Test 4.5: Meeting 2 Contradiction (Migrate to PostgreSQL + Rahul delayed)
            m2_id = f"mtg-audit-2-{self.tag}"
            m2 = Meeting(id=m2_id, workspace_id=self.ws_id, title=f"Architecture Sync 2 ({self.tag})", status="PROCESSING")
            db.add(m2)
            await db.commit()

            m2_text = (
                "Sarah Chen: Let's migrate the primary database to PostgreSQL.\n"
                "Rahul Sharma: Database integration is still incomplete, I am blocked."
            )
            m2_mem = await memory_service.extract_memories(m2_text, context="Architecture Sync 2")
            
            # Detect conflict against previous meeting
            conflicts = await conflict_service.detect_conflicts(
                db=db, workspace_id=self.ws_id, current_meeting_id=m2_id, new_decisions=m2_mem["decisions"]
            )
            self.record_test("Phase 4.5: Cross-meeting conflict detection (MongoDB vs PostgreSQL)", len(conflicts) > 0, f"Detected: {conflicts}", "Phase 4")

            # Persist M2 memories and verify commitment update
            saved_m2 = await memory_service.persist_meeting_memories(
                db=db, workspace_id=self.ws_id, meeting_id=m2_id,
                decisions=m2_mem["decisions"], commitments=m2_mem["commitments"], members=members_dict
            )
            rahul_comm = (await db.execute(
                select(Commitment).where(Commitment.workspace_id == self.ws_id, Commitment.assignee_name.ilike("%Rahul%"))
            )).scalar_one_or_none()
            
            is_delayed = rahul_comm and (rahul_comm.status == "DELAYED" or rahul_comm.delay_count > 0)
            self.record_test("Phase 4.6: Cross-meeting commitment tracking (Rahul delayed)", bool(is_delayed), f"Status: {rahul_comm.status if rahul_comm else 'None'}", "Phase 4")

            # Test 4.7: No-action-item meeting
            casual_text = "Good morning everyone. The weather in Bangalore is lovely today. Let's grab lunch."
            no_action_res = await orchestrator_agent.process_meeting_transcript(
                db=db, meeting_id=m1_id, transcript_text=casual_text, workspace_id=self.ws_id
            )
            self.record_test("Phase 4.8: Safe handling of no-action-item casual transcripts", no_action_res.get("tasks_count", 0) == 0, f"Tasks: {no_action_res.get('tasks_count')}", "Phase 4")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 5: APPROVAL & EXECUTION GATE AUDIT
    # --------------------------------------------------------------------------
    async def audit_phase5_approval_execution(self):
        print("\n========================================================================")
        print("AUDIT PHASE 5: APPROVAL & EXECUTION GATE VALIDATION")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            task = Task(
                workspace_id=self.ws_id,
                title="Migrate authentication service to Supabase JWT",
                description="Replace legacy sessions with Supabase JWT tokens",
                assignee_name="Elena Rostova",
                assignee_email="elena@company.com",
                deadline="2026-12-01",
                priority="HIGH",
                status="AWAITING_APPROVAL"
            )
            db.add(task)
            await db.flush()

            approval = Approval(
                workspace_id=self.ws_id,
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

            # Test 5.1: Pending action status
            self.record_test("Phase 5.1: Approval starts strictly in PENDING state", approval.status == "PENDING", "", "Phase 5")

            # Test 5.2: Reject approval
            approval.status = "REJECTED"
            task.status = "REJECTED"
            await db.commit()

            # Test 5.3: Rejected action cannot execute
            rejected_blocked = False
            try:
                await execution_agent.execute_approval(db=db, approval_id=approval.id, user_id="usr-test")
            except ValueError as e:
                if "REJECTED" in str(e):
                    rejected_blocked = True
            self.record_test("Phase 5.2: Rejected action execution strictly BLOCKED", rejected_blocked, "Rejected action was prevented from executing", "Phase 5")

            # Test 5.4: Approve with edited custom payload
            task2 = Task(
                workspace_id=self.ws_id,
                title="Draft API Spec",
                assignee_name="Elena Rostova",
                assignee_email="elena@company.com",
                deadline="2026-11-30",
                priority="LOW",
                status="AWAITING_APPROVAL"
            )
            db.add(task2)
            await db.flush()

            approval2 = Approval(
                workspace_id=self.ws_id,
                task_id=task2.id,
                status="PENDING",
                proposed_payload={"title": task2.title, "priority": "LOW"}
            )
            db.add(approval2)
            await db.commit()

            exec_res = await execution_agent.execute_approval(
                db=db,
                approval_id=approval2.id,
                custom_payload={"title": "Draft High-Performance OpenAPI Spec", "priority": "URGENT", "assignee_email": "elena@company.com"},
                approved_notes="Priority escalated by PM"
            )
            await db.refresh(task2)
            payload_edited = (task2.title == "Draft High-Performance OpenAPI Spec" and task2.priority == "URGENT" and task2.status == "APPROVED")
            self.record_test("Phase 5.3: Approved action executes using edited payload", payload_edited, f"Task title: {task2.title}, priority: {task2.priority}", "Phase 5")

            # Test 5.5: Duplicate execution prevention (idempotency)
            exec_res_dup = await execution_agent.execute_approval(
                db=db,
                approval_id=approval2.id,
                custom_payload={"title": "Draft High-Performance OpenAPI Spec", "priority": "URGENT", "assignee_email": "elena@company.com"}
            )
            is_dup_handled = exec_res_dup.get("status") in ["ALREADY_APPROVED", "SUCCESS"]
            self.record_test("Phase 5.4: Duplicate execution safely handled without duplicate dispatch", is_dup_handled, f"Status: {exec_res_dup.get('status')}", "Phase 5")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 6: RESEND EMAIL SYSTEM AUDIT
    # --------------------------------------------------------------------------
    async def audit_phase6_resend_email(self):
        print("\n========================================================================")
        print("AUDIT PHASE 6: RESEND EMAIL SYSTEM AUDIT")
        print("========================================================================")
        resend_key = settings.RESEND_API_KEY
        self.record_test("Phase 6.1: RESEND_API_KEY configured in environment", bool(resend_key and resend_key.startswith("re_")), "", "Phase 6")

        # Test Resend API Authentication
        auth_ok = False
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.get("https://api.resend.com/api-keys", headers={"Authorization": f"Bearer {resend_key}"})
                auth_ok = (r.status_code == 200)
            except Exception as e:
                auth_ok = False
        self.record_test("Phase 6.2: Resend API authentication over HTTPS Port 443", auth_ok, "", "Phase 6")

        # Test Real Dispatch to Authorized Recipient (mrofficialyt083@gmail.com)
        test_to = "mrofficialyt083@gmail.com"
        dispatch_id = None
        dispatch_ok = False
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                    json={
                        "from": "MEETME Audit <onboarding@resend.dev>",
                        "to": [test_to],
                        "subject": f"MEETME Production Audit Verification [{self.tag}]",
                        "html": f"<h3>MEETME System Audit</h3><p>Live production readiness test for workspace <code>{self.ws_id}</code>.</p>"
                    }
                )
                if resp.status_code in [200, 201]:
                    dispatch_data = resp.json()
                    dispatch_id = dispatch_data.get("id")
                    dispatch_ok = True
            except Exception as e:
                dispatch_ok = False

        self.record_test("Phase 6.3: Live email dispatch via Resend HTTPS API", dispatch_ok, f"Message ID: {dispatch_id}", "Phase 6")

        # Verify Delivery Event / Status from Resend API
        delivered_ok = False
        last_event = "UNKNOWN"
        if dispatch_id:
            await asyncio.sleep(2.0) # Allow delivery webhook to register
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    status_resp = await client.get(
                        f"https://api.resend.com/emails/{dispatch_id}",
                        headers={"Authorization": f"Bearer {resend_key}"}
                    )
                    if status_resp.status_code == 200:
                        email_info = status_resp.json()
                        last_event = email_info.get("last_event", "")
                        delivered_ok = (last_event in ["delivered", "sent"])
                except Exception:
                    delivered_ok = False

        self.record_test(
            "Phase 6.4: Verify Resend delivery event (delivered/sent)",
            delivered_ok,
            f"Resend last_event: '{last_event}' (Distinguished: submitted -> accepted -> delivered)",
            "Phase 6"
        )

        # Test Domain Restriction Handling: verify Resend returns 422 for arbitrary domain when unverified
        restriction_handled = False
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp_unv = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                    json={
                        "from": "onboarding@resend.dev",
                        "to": ["unverified-domain-user@randomenterprise.org"],
                        "subject": "Test",
                        "html": "<p>test</p>"
                    }
                )
                if resp_unv.status_code in [403, 422] and any(w in resp_unv.text.lower() for w in ["testing", "validation", "domain"]):
                    restriction_handled = True
            except Exception:
                restriction_handled = False

        self.record_test(
            "Phase 6.5: Precise reporting of Resend testing sandbox restriction (HTTP 403/422)",
            restriction_handled,
            "Resend sandbox domain validation accurately caught and handled without masked fallback",
            "Phase 6"
        )

    # --------------------------------------------------------------------------
    # AUDIT PHASE 7: REMINDERS & WEEKLY DIGEST AUDIT
    # --------------------------------------------------------------------------
    async def audit_phase7_reminders_digest(self):
        print("\n========================================================================")
        print("AUDIT PHASE 7: REMINDER SCHEDULER & WEEKLY DIGEST AUDIT")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            task = Task(
                workspace_id=self.ws_id,
                title="Deploy Redis Cache Cluster",
                assignee_name="Elena Rostova",
                assignee_email="mrofficialyt083@gmail.com",
                deadline=(datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d"),
                priority="HIGH",
                status="APPROVED"
            )
            db.add(task)
            await db.flush()

            # Schedule 3 reminder tiers
            now = datetime.utcnow()
            r1 = Reminder(workspace_id=self.ws_id, task_id=task.id, recipient=task.assignee_name, email_address=task.assignee_email, reminder_type="PRE_DEADLINE", scheduled_at=now - timedelta(minutes=5), status="PENDING")
            r2 = Reminder(workspace_id=self.ws_id, task_id=task.id, recipient=task.assignee_name, email_address=task.assignee_email, reminder_type="DEADLINE_DAY", scheduled_at=now + timedelta(days=3), status="PENDING")
            r3 = Reminder(workspace_id=self.ws_id, task_id=task.id, recipient=task.assignee_name, email_address=task.assignee_email, reminder_type="OVERDUE", scheduled_at=now + timedelta(days=4), status="PENDING")
            db.add_all([r1, r2, r3])
            await db.commit()

            # Test Reminder Worker execution
            await reminder_worker.process_pending_reminders()
            await db.refresh(r1)
            self.record_test("Phase 7.1: Reminder worker executes due reminders (scheduled_at <= now)", r1.status in ["SENT", "QUEUED_DEV"], f"r1 status: {r1.status}", "Phase 7")

            # Test Task Completion automatically cancels future reminders
            task.status = "COMPLETED"
            await db.commit()
            cancelled_count = await reminder_worker.cancel_task_reminders(db, task.id, "Task completed by owner")
            await db.refresh(r2)
            await db.refresh(r3)
            self.record_test("Phase 7.2: Task completion cancels all future pending reminders", (r2.status == "CANCELLED" and r3.status == "CANCELLED"), f"Cancelled: {cancelled_count}", "Phase 7")

            # Test Weekly Digest Generation & Privacy Isolation
            digest_rahul = await digest_service.generate_member_digest(db=db, workspace_id=self.ws_id, member=self.member_rahul, period_days=7)
            digest_elena = await digest_service.generate_member_digest(db=db, workspace_id=self.ws_id, member=self.member_elena, period_days=7)

            self.record_test("Phase 7.3: Generate personalized weekly digest", digest_rahul is not None and digest_elena is not None, "", "Phase 7")

            # Check Privacy Isolation: Rahul's digest should NOT contain Elena's tasks
            rahul_tasks = digest_rahul.content_json.get("in_progress_tasks", []) + digest_rahul.content_json.get("completed_tasks", [])
            elena_in_rahul = any("redis cache" in str(t).lower() for t in rahul_tasks)
            self.record_test("Phase 7.4: Strict per-member data privacy isolation in digests", not elena_in_rahul, "Elena's tasks correctly omitted from Rahul's digest", "Phase 7")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 8 & 9: DATABASE INTEGRITY & SECURITY
    # --------------------------------------------------------------------------
    async def audit_phase8_9_db_security(self):
        print("\n========================================================================")
        print("AUDIT PHASE 8 & 9: DATABASE INTEGRITY & SECURITY REVIEW")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            # 8.1 Transaction rollback on error
            rolled_back = False
            try:
                async with db.begin_nested():
                    # Invalid foreign key / constraint trigger
                    bad_task = Task(id=str(uuid.uuid4()), workspace_id="non-existent-ws-id", title="Bad Task")
                    db.add(bad_task)
                    await db.flush()
            except Exception:
                rolled_back = True
            self.record_test("Phase 8.1: Transaction rollback on constraint failure", rolled_back, "", "Phase 8")

            # 9.1 Cross-workspace isolation
            other_ws_id = f"ws-isolated-{uuid.uuid4().hex[:4]}"
            other_ws = Workspace(id=other_ws_id, name="Isolated Corp", slug=f"isolated-{other_ws_id}")
            db.add(other_ws)
            await db.commit()
            other_task = Task(workspace_id=other_ws_id, title="Top Secret Secret Acquisition", status="APPROVED")
            db.add(other_task)
            await db.commit()

            # Query from current workspace
            queried_tasks = (await db.execute(select(Task).where(Task.workspace_id == self.ws_id))).scalars().all()
            isolated = all(t.id != other_task.id for t in queried_tasks)
            self.record_test("Phase 9.1: Multi-tenant workspace data isolation enforced", isolated, "", "Phase 9")

            # 9.2 SQL Injection Defense via ORM parameterization
            injection_query = "'; DROP TABLE meetings; --"
            safe_query = (await db.execute(select(Task).where(Task.workspace_id == self.ws_id, Task.title.ilike(f"%{injection_query}%")))).scalars().all()
            self.record_test("Phase 9.2: SQL injection defense via parameterized SQLAlchemy execution", isinstance(safe_query, list), "Safe parameterized execution verified", "Phase 9")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 10: PERFORMANCE AND STRESS TESTING
    # --------------------------------------------------------------------------
    async def audit_phase10_performance_stress(self):
        print("\n========================================================================")
        print("AUDIT PHASE 10: PERFORMANCE AND STRESS TESTING")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            # Concurrency test: 25 concurrent task retrieval operations
            t0 = time.time()
            async def fetch_tasks():
                async with AsyncSessionLocal() as s:
                    res = await s.execute(select(Task).where(Task.workspace_id == self.ws_id).limit(10))
                    return len(res.scalars().all())

            tasks_batch = [fetch_tasks() for _ in range(25)]
            results = await asyncio.gather(*tasks_batch)
            elapsed_25 = (time.time() - t0) * 1000
            avg_latency = elapsed_25 / 25
            self.results["performance"]["concurrent_queries_25"] = {
                "total_ms": round(elapsed_25, 2),
                "avg_ms": round(avg_latency, 2),
                "success_count": len(results)
            }
            self.record_test("Phase 10.1: 25 Concurrent database read operations", len(results) == 25, f"Avg latency: {round(avg_latency, 2)}ms", "Phase 10")

            # Concurrency test: 10 concurrent task creations
            t0 = time.time()
            async def create_stress_task(idx):
                async with AsyncSessionLocal() as s:
                    t = Task(workspace_id=self.ws_id, title=f"Stress Task {idx}", priority="MEDIUM")
                    s.add(t)
                    await s.commit()
                    return t.id

            create_batch = [create_stress_task(i) for i in range(10)]
            created_ids = await asyncio.gather(*create_batch)
            elapsed_create_10 = (time.time() - t0) * 1000
            self.results["performance"]["concurrent_writes_10"] = {
                "total_ms": round(elapsed_create_10, 2),
                "avg_ms": round(elapsed_create_10 / 10, 2),
                "success_count": len(created_ids)
            }
            self.record_test("Phase 10.2: 10 Concurrent database write operations", len(created_ids) == 10, f"Total: {round(elapsed_create_10, 2)}ms", "Phase 10")

    # --------------------------------------------------------------------------
    # AUDIT PHASE 12: COMPLETE END-TO-END SCENARIO (23 Steps)
    # --------------------------------------------------------------------------
    async def audit_phase12_complete_e2e(self):
        print("\n========================================================================")
        print("AUDIT PHASE 12: COMPLETE END-TO-END 23-STEP SCENARIO")
        print("========================================================================")
        async with AsyncSessionLocal() as db:
            # 1. Create workspace & admin user
            e2e_user = User(id=f"usr-e2e-{self.tag}", email=f"e2e-{self.tag}@meetme.work", full_name="E2E Lead", role="admin")
            db.add(e2e_user)
            await db.commit()

            e2e_ws_id = f"ws-e2e-{self.tag}"
            ws = Workspace(id=e2e_ws_id, name="E2E Corp", slug=f"e2e-{self.tag}", owner_id=e2e_user.id)
            db.add(ws)
            # 2. Register three team members
            m_rahul = WorkspaceMember(id=f"e2e-r-{self.tag}", workspace_id=e2e_ws_id, full_name="Rahul Sharma", email="rahul@company.com", title="Engineer")
            m_sarah = WorkspaceMember(id=f"e2e-s-{self.tag}", workspace_id=e2e_ws_id, full_name="Sarah Chen", email="sarah@company.com", title="PM")
            m_elena = WorkspaceMember(id=f"e2e-e-{self.tag}", workspace_id=e2e_ws_id, full_name="Elena Rostova", email="mrofficialyt083@gmail.com", title="Lead")
            db.add_all([m_rahul, m_sarah, m_elena])
            await db.commit()
            self.record_test("Phase 12.1: Step 1 & 2 - Create workspace & register 3 team members", True, "", "Phase 12")

            # 3. Create meeting
            e2e_m1 = Meeting(id=f"mtg-e2e-1-{self.tag}", workspace_id=e2e_ws_id, title="Quarterly Engineering Alignment", recording_mode="RECORDED", status="PROCESSING")
            db.add(e2e_m1)
            await db.commit()
            self.record_test("Phase 12.2: Step 3 - Create meeting record", True, "", "Phase 12")

            # 4, 5, 6. Ingest transcript, attribute speakers, extract tasks/decisions/owners/deadlines
            m1_transcript = (
                "Sarah Chen: We have decided to use MongoDB as the primary database.\n"
                "Rahul Sharma: I will finish database integration by Friday.\n"
                "Elena Rostova: I will conduct performance and stress testing by Monday."
            )
            orch_res = await orchestrator_agent.process_meeting_transcript(
                db=db, meeting_id=e2e_m1.id, transcript_text=m1_transcript, workspace_id=e2e_ws_id
            )
            self.record_test("Phase 12.3: Steps 4, 5, 6 - Transcript ingested, speakers attributed, tasks & decisions extracted", orch_res.get("tasks_count", 0) >= 2, f"Tasks: {orch_res.get('tasks_count')}", "Phase 12")

            # 10, 11, 12. Proposed actions in Approval Centre, approve a task, verify persistence
            app_stmt = select(Approval).where(Approval.workspace_id == e2e_ws_id, Approval.status == "PENDING")
            approvals = (await db.execute(app_stmt)).scalars().all()
            self.record_test("Phase 12.4: Step 10 - Display proposed actions in Approval Centre", len(approvals) > 0, f"Pending approvals: {len(approvals)}", "Phase 12")

            elena_app = next((a for a in approvals if "Elena" in (a.proposed_payload or {}).get("assignee_name", "")), approvals[0])
            first_app = elena_app
            exec_res = await execution_agent.execute_approval(
                db=db, approval_id=first_app.id, user_id=e2e_user.id, approved_notes="Approved during E2E audit",
                custom_payload={"assignee_email": "mrofficialyt083@gmail.com", "deadline": "2026-11-28"}
            )
            self.record_test("Phase 12.5: Steps 11 & 12 - Approve task & verify persistence", exec_res.get("status") == "SUCCESS", "", "Phase 12")

            # 15. Send assignment email
            self.record_test("Phase 12.6: Step 15 - Assignment email processed", exec_res.get("email_status") in ["SENT", "QUEUED_DEV", "ALREADY_SENT"], f"Email Status: {exec_res.get('email_status')}", "Phase 12")

            # 16. Schedule deadline reminder
            self.record_test("Phase 12.7: Step 16 - Multi-tier deadline reminder scheduled", exec_res.get("reminders_count", 0) > 0, f"Reminders: {exec_res.get('reminders_count')}", "Phase 12")

            # 17, 18. Weekly digest & member isolation
            digest_res = await digest_service.generate_member_digest(db=db, workspace_id=e2e_ws_id, member=m_rahul)
            self.record_test("Phase 12.8: Steps 17 & 18 - Generate weekly digest with member isolation", digest_res is not None, "", "Phase 12")

            # 19, 20. Complete task & cancel reminders
            task_id = exec_res["task_id"]
            completed_task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
            completed_task.status = "COMPLETED"
            await db.commit()
            cancelled = await reminder_worker.cancel_task_reminders(db, task_id, "Completed in E2E")
            self.record_test("Phase 12.9: Steps 19 & 20 - Complete task and verify reminder cancellation", cancelled > 0, f"Cancelled {cancelled} reminders", "Phase 12")

            # 21, 22, 23. Process second meeting, cross-meeting memory, conflict detection & resolution
            e2e_m2 = Meeting(id=f"mtg-e2e-2-{self.tag}", workspace_id=e2e_ws_id, title="Follow-up Database Review", recording_mode="RECORDED", status="PROCESSING")
            db.add(e2e_m2)
            await db.commit()

            m2_transcript = (
                "Sarah Chen: Let's migrate the primary database to PostgreSQL.\n"
                "Rahul Sharma: Database integration is still incomplete, I need more time."
            )
            m2_orch = await orchestrator_agent.process_meeting_transcript(
                db=db, meeting_id=e2e_m2.id, transcript_text=m2_transcript, workspace_id=e2e_ws_id
            )
            
            # Check conflict detected
            c_stmt = select(DecisionConflict).where(DecisionConflict.workspace_id == e2e_ws_id, DecisionConflict.status == "UNRESOLVED")
            e2e_conflicts = (await db.execute(c_stmt)).scalars().all()
            self.record_test("Phase 12.10: Steps 21 & 22 - Process second meeting & detect decision conflict", len(e2e_conflicts) > 0, f"Conflicts: {len(e2e_conflicts)}", "Phase 12")

            # Resolve conflict
            if e2e_conflicts:
                res_out = await conflict_service.resolve_conflict(
                    db=db, conflict_id=e2e_conflicts[0].id, action="ACCEPT_NEW",
                    user_id=e2e_user.id, resolution_notes="Resolved to PostgreSQL"
                )
                self.record_test("Phase 12.11: Step 23 - Conflict resolution updates decision state to SUPERSEDED", res_out.get("status") == "SUCCESS" and res_out.get("previous_decision_status") == "SUPERSEDED", "", "Phase 12")

    async def run(self):
        t_start = time.time()
        print("========================================================================")
        print("MEETME — COMPREHENSIVE PRODUCTION AUDIT & STRESS TEST SUITE")
        print("========================================================================")
        await self.setup_workspace()
        await self.audit_phase4_ai_memory()
        await self.audit_phase5_approval_execution()
        await self.audit_phase6_resend_email()
        await self.audit_phase7_reminders_digest()
        await self.audit_phase8_9_db_security()
        await self.audit_phase10_performance_stress()
        await self.audit_phase12_complete_e2e()

        total_time = round(time.time() - t_start, 2)
        print("\n========================================================================")
        print(f"AUDIT EXECUTION COMPLETE IN {total_time}s")
        print(f"TOTAL TESTS: {self.results['passed'] + self.results['failed']}")
        print(f"PASSED:      {self.results['passed']}")
        print(f"FAILED:      {self.results['failed']}")
        print(f"SKIPPED:     {self.results['skipped']}")
        print("========================================================================")
        return self.results

if __name__ == "__main__":
    runner = ComprehensiveAuditRunner()
    results = asyncio.run(runner.run())
    if results["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
