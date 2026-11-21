import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.schema import (
    Meeting, MeetingTranscript, Task, Approval, WorkspaceMember, AgentRun, AutomationLog
)
from backend.app.agents.transcription_agent import transcription_agent
from backend.app.agents.task_agent import task_agent
from backend.app.agents.assignment_agent import assignment_agent
from backend.app.agents.decision_agent import decision_agent
from backend.app.agents.risk_agent import risk_agent
from backend.app.agents.email_agent import email_agent

logger = logging.getLogger("meetme.orchestrator")

class OrchestratorAgent:
    """
    Central Orchestrator coordinating specialized agents, validating schemas,
    and enforcing human approval gates before any execution.
    """
    async def process_meeting_transcript(
        self,
        db: AsyncSession,
        meeting_id: str,
        transcript_text: str,
        workspace_id: str
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Starting orchestration pipeline for meeting {meeting_id}")

        # 1. Fetch meeting
        meeting_stmt = select(Meeting).where(Meeting.id == meeting_id)
        meeting_res = await db.execute(meeting_stmt)
        meeting = meeting_res.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found.")

        meeting.status = "PROCESSING"
        await db.commit()

        # 2. Fetch workspace members
        members_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        members_res = await db.execute(members_stmt)
        members = members_res.scalars().all()
        members_dict = [
            {"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role, "title": m.title}
            for m in members
        ]

        # Step 1: Transcription Analysis Agent
        classified_segments = await transcription_agent.analyze(transcript_text, context=meeting.title)

        # Store segments into MeetingTranscript
        saved_transcripts = []
        for seg in classified_segments:
            tr = MeetingTranscript(
                meeting_id=meeting_id,
                speaker_name=seg.get("speaker", "Speaker"),
                text=seg.get("text", ""),
                timestamp_formatted=seg.get("timestamp", "00:00:00"),
                classification=seg.get("classification", "GENERAL_DISCUSSION"),
                confidence=seg.get("confidence", 0.9),
                raw_json=seg
            )
            db.add(tr)
            saved_transcripts.append(tr)

        await db.flush()

        # Step 2: Task Extraction Agent
        raw_tasks = await task_agent.extract_tasks(transcript_text, classified_segments)

        # Step 3: Assignment Agent
        assigned_tasks = assignment_agent.match_assignments(raw_tasks, members_dict)

        # Step 4: Decision & Risk Agents
        decisions_data = await decision_agent.extract_decisions(transcript_text)
        risks_data = await risk_agent.analyze_risks(transcript_text, assigned_tasks)

        # Step 5: Persist Tasks & Create Mandatory Approvals
        created_tasks = []
        created_approvals = []

        for t in assigned_tasks:
            # Check for existing duplicate task
            task_title = t.get("title", "")
            dup_check = select(Task).where(
                Task.meeting_id == meeting_id,
                Task.title == task_title
            )
            dup_res = await db.execute(dup_check)
            existing_task = dup_res.scalar_one_or_none()

            if existing_task:
                # Update existing task instead of duplicating
                existing_task.description = t.get("description", existing_task.description)
                existing_task.deadline = t.get("deadline", existing_task.deadline)
                existing_task.priority = t.get("priority", existing_task.priority)
                existing_task.confidence = t.get("confidence", existing_task.confidence)
                continue

            # Build proposed email content via EmailAgent
            proposed_email = email_agent.generate_task_assignment_email(
                task=t,
                meeting_title=meeting.title,
                workspace_name="Engineering Workspace"
            )

            task_obj = Task(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                title=t.get("title", "Untitled Task"),
                description=t.get("description"),
                assignee_id=t.get("assignee_id"),
                assignee_name=t.get("assignee_name"),
                assignee_email=t.get("assignee_email"),
                deadline=t.get("deadline"),
                priority=t.get("priority", "MEDIUM"),
                dependencies=t.get("dependencies", []),
                confidence=t.get("confidence", 0.9),
                classification_type=t.get("classification_type", "EXPLICIT"),
                status="AWAITING_APPROVAL",
                evidence_quote=t.get("evidence")
            )
            db.add(task_obj)
            await db.flush() # get task_obj.id

            # Create Approval record
            approval = Approval(
                workspace_id=workspace_id,
                task_id=task_obj.id,
                meeting_id=meeting_id,
                status="PENDING",
                proposed_payload={
                    "title": task_obj.title,
                    "description": task_obj.description,
                    "assignee_id": task_obj.assignee_id,
                    "assignee_name": task_obj.assignee_name,
                    "assignee_email": task_obj.assignee_email,
                    "deadline": task_obj.deadline,
                    "priority": task_obj.priority,
                    "confidence": task_obj.confidence,
                    "evidence_quote": task_obj.evidence_quote,
                    "email_content": proposed_email,
                    "meeting_title": meeting.title,
                    "requires_clarification": t.get("requires_human_clarification", False)
                }
            )
            db.add(approval)
            created_tasks.append(task_obj)
            created_approvals.append(approval)

        # Step 6: Generate Executive Summary & Update Meeting Record
        decisions_list = decisions_data.get("decisions", [])
        blockers_list = risks_data.get("blockers", [])

        summary_points = [
            f"Extracted {len(created_tasks)} actionable items and {len(decisions_list)} key architectural decisions.",
            f"Identified {len(blockers_list)} operational blocker(s)." if blockers_list else "No active blockers identified.",
            f"All action items routed to the Approval Center pending human authorization."
        ]
        summary_text = " ".join(summary_points)

        meeting.summary = summary_text
        meeting.key_decisions = decisions_list
        meeting.status = "COMPLETED"

        # Record Agent Run Metrics
        latency = int((time.time() - start_time) * 1000)
        agent_run = AgentRun(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            agent_name="MEETME Orchestrator",
            status="COMPLETED",
            latency_ms=latency,
            input_summary=f"{len(transcript_text)} chars of meeting transcript",
            output_data={
                "tasks_extracted": len(created_tasks),
                "decisions": len(decisions_list),
                "blockers": len(blockers_list),
                "approvals_created": len(created_approvals),
                "segments_classified": len(classified_segments)
            }
        )
        db.add(agent_run)

        # Log automation event
        auto_log = AutomationLog(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            trigger_type="MEETING_PROCESSED",
            action_type="ORCHESTRATION_COMPLETE",
            payload={
                "tasks_count": len(created_tasks),
                "approvals_count": len(created_approvals)
            },
            status="SUCCESS",
            message=f"Meeting '{meeting.title}' processed in {latency}ms. {len(created_approvals)} approvals ready."
        )
        db.add(auto_log)

        await db.commit()
        await db.refresh(meeting)

        logger.info(f"Orchestration complete for meeting {meeting_id} in {latency}ms.")
        return {
            "status": "COMPLETED",
            "meeting_id": meeting_id,
            "tasks_count": len(created_tasks),
            "decisions_count": len(decisions_list),
            "blockers_count": len(blockers_list),
            "approvals_count": len(created_approvals),
            "latency_ms": latency
        }

orchestrator_agent = OrchestratorAgent()
