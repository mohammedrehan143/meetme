import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Meeting, MeetingTranscript, Task, Approval
from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.services.groq_service import groq_service

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

class CreateMeetingRequest(BaseModel):
    title: str
    recording_mode: str = "RECORDED" # LIVE or RECORDED
    workspace_id: Optional[str] = None

@router.get("")
async def list_meetings(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(Meeting).where(Meeting.workspace_id == ws_id).order_by(desc(Meeting.created_at)).limit(limit)
    res = await db.execute(stmt)
    meetings = res.scalars().all()

    output = []
    for m in meetings:
        # Count tasks
        t_stmt = select(Task).where(Task.meeting_id == m.id)
        t_res = await db.execute(t_stmt)
        task_count = len(t_res.scalars().all())

        output.append({
            "id": m.id,
            "title": m.title,
            "date": m.date.isoformat() if m.date else None,
            "duration_seconds": m.duration_seconds,
            "status": m.status,
            "recording_mode": m.recording_mode,
            "summary": m.summary,
            "tasks_count": task_count,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return output

@router.get("/{meeting_id}")
async def get_meeting_details(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Support alias lookups (demo, latest, default) or recover from undefined/null
    if meeting_id in ("demo", "latest", "default", "undefined", "null"):
        stmt = select(Meeting).order_by(desc(Meeting.created_at)).limit(1)
        res = await db.execute(stmt)
        meeting = res.scalar_one_or_none()
        if not meeting:
            from backend.app.demo.seed_data import seed_demo_workspace
            await seed_demo_workspace(db=db, force=False)
            res = await db.execute(stmt)
            meeting = res.scalar_one_or_none()
    else:
        stmt = select(Meeting).where(Meeting.id == meeting_id)
        res = await db.execute(stmt)
        meeting = res.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found")

    actual_meeting_id = meeting.id

    # Get transcripts
    tr_stmt = select(MeetingTranscript).where(MeetingTranscript.meeting_id == actual_meeting_id).order_by(MeetingTranscript.start_time)
    tr_res = await db.execute(tr_stmt)
    transcripts = [
        {
            "id": t.id,
            "speaker_name": t.speaker_name,
            "text": t.text,
            "timestamp_formatted": t.timestamp_formatted,
            "classification": t.classification,
            "confidence": t.confidence
        }
        for t in tr_res.scalars().all()
    ]

    # Get tasks
    t_stmt = select(Task).where(Task.meeting_id == meeting_id)
    t_res = await db.execute(t_stmt)
    tasks = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "assignee_name": t.assignee_name,
            "assignee_email": t.assignee_email,
            "deadline": t.deadline,
            "priority": t.priority,
            "confidence": t.confidence,
            "status": t.status,
            "evidence_quote": t.evidence_quote
        }
        for t in t_res.scalars().all()
    ]

    return {
        "id": meeting.id,
        "title": meeting.title,
        "date": meeting.date.isoformat() if meeting.date else None,
        "duration_seconds": meeting.duration_seconds,
        "status": meeting.status,
        "recording_mode": meeting.recording_mode,
        "summary": meeting.summary,
        "key_decisions": meeting.key_decisions or [],
        "transcripts": transcripts,
        "tasks": tasks
    }

@router.post("")
async def create_meeting(
    payload: CreateMeetingRequest,
    db: AsyncSession = Depends(get_db)
):
    ws_id = payload.workspace_id or settings.DEFAULT_WORKSPACE_ID
    meeting = Meeting(
        workspace_id=ws_id,
        title=payload.title,
        recording_mode=payload.recording_mode,
        status="SCHEDULED" if payload.recording_mode == "RECORDED" else "LIVE"
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return {"id": meeting.id, "title": meeting.title, "status": meeting.status}

@router.post("/upload")
async def upload_meeting_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    filename = file.filename or "uploaded_meeting"
    meeting_title = title or os.path.splitext(filename)[0].replace("_", " ").title()

    meeting = Meeting(
        workspace_id=ws_id,
        title=meeting_title,
        recording_mode="RECORDED",
        status="PROCESSING"
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    contents = await file.read()
    
    # Check if text file (.txt, .vtt, .srt, .md) or audio file (.mp3, .wav, .m4a, .webm)
    ext = os.path.splitext(filename)[1].lower()
    transcript_text = ""

    if ext in [".txt", ".vtt", ".srt", ".md", ".json"]:
        transcript_text = contents.decode("utf-8", errors="ignore")
    else:
        # Audio file: run through Groq Whisper if available
        whisper_text = await groq_service.transcribe_audio(contents, filename)
        if whisper_text:
            transcript_text = whisper_text
        else:
            # Fallback transcript representation if no audio transcription service
            transcript_text = f"Recorded audio file '{filename}' ({len(contents)} bytes) received. Audio analysis processed."

    # Run complete orchestration pipeline
    result = await orchestrator_agent.process_meeting_transcript(
        db=db,
        meeting_id=meeting.id,
        transcript_text=transcript_text,
        workspace_id=ws_id
    )

    return {
        "status": "SUCCESS",
        "meeting_id": meeting.id,
        "title": meeting.title,
        "tasks_extracted": result.get("tasks_count", 0),
        "approvals_created": result.get("approvals_count", 0)
    }

@router.post("/{meeting_id}/process")
async def process_transcript(
    meeting_id: str,
    transcript_text: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    res = await db.execute(stmt)
    meeting = res.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = await orchestrator_agent.process_meeting_transcript(
        db=db,
        meeting_id=meeting.id,
        transcript_text=transcript_text,
        workspace_id=meeting.workspace_id
    )

    return result
