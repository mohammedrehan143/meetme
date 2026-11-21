import logging
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.schema import (
    User, Workspace, WorkspaceMember, Meeting, MeetingTranscript,
    Task, Approval, EmailLog, Reminder, AutomationLog, AgentRun, Notification
)
from backend.app.agents.orchestrator import orchestrator_agent

logger = logging.getLogger("meetme.demo.seed")

SAMPLE_TRANSCRIPT = """[00:00:15] Sarah Chen: Good morning everyone. Welcome to our sprint execution alignment for MEETME. Today our focus is getting the live meeting engine, the Groq multi-agent orchestration, and the persistent execution pipeline completely dialed in.
[00:00:48] Sarah Chen: Let's do a fast status sweep. Rahul, where are we on the frontend live meeting capture interface?
[00:01:05] Rahul Sharma: On the frontend, the dual audio capture using getDisplayMedia for tab audio and getUserMedia for the microphone is hooked up with Web Audio API. I will complete the frontend implementation and responsive UI by November 27.
[00:01:42] Rahul Sharma: However, we do have one blocker: browser tab audio sharing requires the user to explicitly select the tab and check the 'Share tab audio' checkbox. If they don't, we need graceful UI fallback instructions.
[00:02:15] Sarah Chen: That is a critical observation. Let's make sure the interface has unambiguous visual indicators for recording consent and tab audio permission guides.
[00:02:35] Sarah Chen: Elena, how is the backend and AI agent pipeline shaping up?
[00:02:50] Elena Rostova: We finalized the decision to use Groq as our primary inference engine with LLaMA-3.3-70b-versatile and Whisper-large-v3 for sub-second latency. I will implement the FastAPI backend and Groq multi-agent orchestration pipeline by November 25.
[00:03:25] Elena Rostova: In addition, I will integrate the Gmail SMTP email execution and persistent reminder worker by November 26 so that approved tasks trigger automated assignment emails and persistent reminders.
[00:03:55] Sarah Chen: Fantastic. That brings us to our core governance rule: human approval is mandatory before any email execution or external notification occurs. No rogue AI actions.
[00:04:18] Marcus Vance: I agree 100%. On the verification front, I will develop the end-to-end test suite and WebSocket stress tests by November 28.
[00:04:45] Sarah Chen: Perfect. I will prepare the executive demo walkthrough and launch narrative by November 29.
[00:05:10] Marcus Vance: One question: someone needs to audit workspace security and browser tab audio permissions before we go live.
[00:05:32] Sarah Chen: That's a great point. We definitely need someone to review security and permission limits before release. Let's flag that for immediate assignment.
[00:05:58] Sarah Chen: Also, who will lead the enterprise compliance and SOC2 prep after the hackathon?
[00:06:15] Elena Rostova: Let's defer that unresolved question until post-hackathon roadmap planning.
[00:06:30] Sarah Chen: Agreed. Let's execute on these commitments and sync tomorrow. Thanks team!"""

async def seed_demo_workspace(db: AsyncSession, force: bool = False):
    # 1. Users setup
    user_definitions = [
        {"id": "usr-sarah-001", "email": "sarah.chen@meetme.work", "full_name": "Sarah Chen", "role": "admin"},
        {"id": "usr-rahul-002", "email": "rahul.sharma@meetme.work", "full_name": "Rahul Sharma", "role": "member"},
        {"id": "usr-elena-003", "email": "elena.rostova@meetme.work", "full_name": "Elena Rostova", "role": "member"},
        {"id": "usr-marcus-004", "email": "marcus.vance@meetme.work", "full_name": "Marcus Vance", "role": "member"},
    ]

    for u_def in user_definitions:
        existing_u = (await db.execute(select(User).where(User.id == u_def["id"]))).scalar_one_or_none()
        if not existing_u:
            # Check by email as well
            by_email = (await db.execute(select(User).where(User.email == u_def["email"]))).scalar_one_or_none()
            if not by_email:
                db.add(User(**u_def))
    await db.flush()

    # 2. Workspace setup
    workspace = (await db.execute(select(Workspace).where(Workspace.id == "ws-demo-001"))).scalar_one_or_none()
    if not workspace:
        workspace = Workspace(
            id="ws-demo-001",
            name="MEETME Core Engineering",
            slug="meetme-core",
            owner_id="usr-sarah-001"
        )
        db.add(workspace)
        await db.flush()
    elif not force:
        logger.info("Demo workspace already exists. Skipping seed.")
        return {"status": "SKIPPED", "message": "Demo data already initialized."}

    # 3. Workspace Members setup
    member_definitions = [
        {"id": "mem-sarah-001", "workspace_id": workspace.id, "user_id": "usr-sarah-001", "full_name": "Sarah Chen", "email": "sarah.chen@meetme.work", "role": "admin", "title": "Head of Product"},
        {"id": "mem-rahul-002", "workspace_id": workspace.id, "user_id": "usr-rahul-002", "full_name": "Rahul Sharma", "email": "rahul.sharma@meetme.work", "role": "member", "title": "Lead Frontend Architect"},
        {"id": "mem-elena-003", "workspace_id": workspace.id, "user_id": "usr-elena-003", "full_name": "Elena Rostova", "email": "elena.rostova@meetme.work", "role": "member", "title": "Principal AI & Backend Engineer"},
        {"id": "mem-marcus-004", "workspace_id": workspace.id, "user_id": "usr-marcus-004", "full_name": "Marcus Vance", "email": "marcus.vance@meetme.work", "role": "member", "title": "QA Lead & DevOps"},
    ]

    for m_def in member_definitions:
        existing_m = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.id == m_def["id"]))).scalar_one_or_none()
        if not existing_m:
            db.add(WorkspaceMember(**m_def))
    await db.flush()

    # If force=True, clean up prior demo meetings, tasks, approvals, reminders
    if force:
        await db.execute(delete(Reminder).where(Reminder.workspace_id == workspace.id))
        await db.execute(delete(EmailLog).where(EmailLog.workspace_id == workspace.id))
        await db.execute(delete(Approval).where(Approval.workspace_id == workspace.id))
        await db.execute(delete(Task).where(Task.workspace_id == workspace.id))
        await db.execute(delete(MeetingTranscript))
        await db.execute(delete(Meeting).where(Meeting.workspace_id == workspace.id))
        await db.commit()

    # 4. Create Demo Meeting
    meeting = Meeting(
        id="mtg-demo-001",
        workspace_id=workspace.id,
        title="Sprint Execution & Architecture Alignment",
        date=datetime.utcnow() - timedelta(hours=2),
        duration_seconds=1080, # 18 mins
        status="SCHEDULED",
        recording_mode="RECORDED",
        created_by="usr-sarah-001"
    )
    db.add(meeting)
    await db.commit()

    # 5. Run full Orchestration Pipeline on the sample transcript
    orchestration_result = await orchestrator_agent.process_meeting_transcript(
        db=db,
        meeting_id=meeting.id,
        transcript_text=SAMPLE_TRANSCRIPT,
        workspace_id=workspace.id
    )

    # 6. Add initial notifications
    notif1 = Notification(
        workspace_id=workspace.id,
        user_id="usr-sarah-001",
        title="Meeting Ingested",
        message="Sprint Execution & Architecture Alignment transcript processed. Action items identified.",
        type="INFO",
        link=f"/meetings/{meeting.id}"
    )
    notif2 = Notification(
        workspace_id=workspace.id,
        user_id="usr-sarah-001",
        title="Pending Approvals",
        message="Action items awaiting human verification before email dispatch.",
        type="ACTION_REQUIRED",
        link="/approvals"
    )
    db.add(notif1)
    db.add(notif2)
    await db.commit()

    logger.info("Demo workspace successfully seeded.")
    return {
        "status": "SUCCESS",
        "workspace_id": workspace.id,
        "meeting_id": meeting.id,
        "orchestration": orchestration_result
    }
