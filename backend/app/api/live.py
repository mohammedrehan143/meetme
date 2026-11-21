import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.schema import Meeting, MeetingTranscript, Task, WorkspaceMember
from backend.app.agents.transcription_agent import transcription_agent
from backend.app.agents.task_agent import task_agent
from backend.app.agents.decision_agent import decision_agent
from backend.app.agents.assignment_agent import assignment_agent

logger = logging.getLogger("meetme.api.live")

router = APIRouter(tags=["live"])

class ConnectionManager:
    def __init__(self):
        # meeting_id -> list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = []
        self.active_connections[meeting_id].append(websocket)
        logger.info(f"WebSocket client connected to meeting {meeting_id}")

    def disconnect(self, meeting_id: str, websocket: WebSocket):
        if meeting_id in self.active_connections:
            if websocket in self.active_connections[meeting_id]:
                self.active_connections[meeting_id].remove(websocket)
            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]
        logger.info(f"WebSocket client disconnected from meeting {meeting_id}")

    async def broadcast(self, meeting_id: str, message: Dict[str, Any]):
        if meeting_id in self.active_connections:
            dead_sockets = []
            for connection in self.active_connections[meeting_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_sockets.append(connection)
            for dead in dead_sockets:
                self.disconnect(meeting_id, dead)

manager = ConnectionManager()

@router.websocket("/ws/live-meeting/{meeting_id}")
@router.websocket("/api/ws/live-meeting/{meeting_id}")
async def websocket_live_meeting(websocket: WebSocket, meeting_id: str):
    await manager.connect(meeting_id, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except Exception:
                continue

            event_type = data.get("type")

            if event_type == "TRANSCRIPT_CHUNK":
                text = data.get("text", "").strip()
                speaker = data.get("speaker", "Speaker")
                timestamp = data.get("timestamp", "00:00:00")
                
                if not text:
                    continue

                # Run fast transcription analysis
                analysis = await transcription_agent.analyze(f"{speaker}: {text}")
                seg = analysis[0] if analysis else {
                    "classification": "GENERAL_DISCUSSION",
                    "confidence": 0.85
                }

                classification = seg.get("classification", "GENERAL_DISCUSSION")

                # Try task extraction to see if an action item or assignment was directed to someone
                tasks = await task_agent.extract_tasks(f"{speaker}: {text}")
                detected_task = tasks[0] if tasks else None

                if detected_task:
                    classification = "TASK"

                detected_decision = None
                if classification == "DECISION":
                    decisions = await decision_agent.extract_decisions(f"{speaker}: {text}")
                    if decisions.get("decisions"):
                        detected_decision = decisions["decisions"][0]

                # Persist to database
                async with AsyncSessionLocal() as db:
                    # Get meeting to find workspace_id
                    stmt_m = select(Meeting).where(Meeting.id == meeting_id)
                    res_m = await db.execute(stmt_m)
                    mtg = res_m.scalar_one_or_none()
                    ws_id = mtg.workspace_id if mtg else "ws-demo-001"

                    # If task detected, resolve assignee against workspace members
                    if detected_task:
                        m_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)
                        m_res = await db.execute(m_stmt)
                        members = m_res.scalars().all()
                        members_dict = [
                            {"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role, "title": m.title}
                            for m in members
                        ]
                        assigned_tasks = assignment_agent.match_assignments([detected_task], members_dict)
                        if assigned_tasks:
                            detected_task = assigned_tasks[0]
                            # Display friendly assignee
                            detected_task["assignee"] = detected_task.get("assignee_name") or detected_task.get("assignee")

                        # Persist task in database if not duplicate
                        t_title = detected_task.get("title", "")
                        if t_title:
                            dup_stmt = select(Task).where(Task.meeting_id == meeting_id, Task.title == t_title)
                            dup_res = await db.execute(dup_stmt)
                            existing_t = dup_res.scalar_one_or_none()
                            if not existing_t:
                                new_t = Task(
                                    workspace_id=ws_id,
                                    meeting_id=meeting_id,
                                    title=t_title,
                                    description=detected_task.get("description"),
                                    assignee_id=detected_task.get("assignee_id"),
                                    assignee_name=detected_task.get("assignee_name"),
                                    assignee_email=detected_task.get("assignee_email"),
                                    deadline=detected_task.get("deadline"),
                                    priority=detected_task.get("priority", "MEDIUM"),
                                    dependencies=detected_task.get("dependencies", []),
                                    confidence=detected_task.get("confidence", 0.92),
                                    classification_type=detected_task.get("classification_type", "EXPLICIT"),
                                    status="AWAITING_APPROVAL"
                                )
                                db.add(new_t)

                    tr = MeetingTranscript(
                        meeting_id=meeting_id,
                        speaker_name=speaker,
                        text=text,
                        timestamp_formatted=timestamp,
                        classification=classification,
                        confidence=seg.get("confidence", 0.9)
                    )
                    db.add(tr)
                    await db.commit()

                # Broadcast live event to all connected clients
                await manager.broadcast(meeting_id, {
                    "type": "LIVE_TRANSCRIPT_SEGMENT",
                    "speaker": speaker,
                    "text": text,
                    "timestamp": timestamp,
                    "classification": classification,
                    "detected_task": detected_task,
                    "detected_decision": detected_decision
                })

            elif event_type == "AUDIO_CHUNK":
                audio_base64 = data.get("audio_data")
                timestamp = data.get("timestamp", "00:00:00")
                speaker = data.get("speaker", "Meeting Participant")

                if audio_base64:
                    import base64
                    try:
                        audio_bytes = base64.b64decode(audio_base64)
                        from backend.app.services.groq_service import groq_service
                        transcribed_text = await groq_service.transcribe_audio(audio_bytes, filename=f"chunk_{meeting_id}.webm")
                        if transcribed_text and len(transcribed_text.strip()) > 2:
                            text = transcribed_text.strip()
                            logger.info(f"Whisper transcribed tab/mic audio chunk: '{text}'")

                            # Run fast transcription analysis
                            analysis = await transcription_agent.analyze(f"{speaker}: {text}")
                            seg = analysis[0] if analysis else {
                                "classification": "GENERAL_DISCUSSION",
                                "confidence": 0.85
                            }
                            classification = seg.get("classification", "GENERAL_DISCUSSION")

                            # Try task extraction
                            tasks = await task_agent.extract_tasks(f"{speaker}: {text}")
                            detected_task = tasks[0] if tasks else None
                            if detected_task:
                                classification = "TASK"

                            detected_decision = None
                            if classification == "DECISION":
                                decisions = await decision_agent.extract_decisions(f"{speaker}: {text}")
                                if decisions.get("decisions"):
                                    detected_decision = decisions["decisions"][0]

                            async with AsyncSessionLocal() as db:
                                stmt_m = select(Meeting).where(Meeting.id == meeting_id)
                                res_m = await db.execute(stmt_m)
                                mtg = res_m.scalar_one_or_none()
                                ws_id = mtg.workspace_id if mtg else "ws-demo-001"

                                if detected_task:
                                    m_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)
                                    m_res = await db.execute(m_stmt)
                                    members = m_res.scalars().all()
                                    members_dict = [
                                        {"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role, "title": m.title}
                                        for m in members
                                    ]
                                    assigned_tasks = assignment_agent.match_assignments([detected_task], members_dict)
                                    if assigned_tasks:
                                        detected_task = assigned_tasks[0]
                                        detected_task["assignee"] = detected_task.get("assignee_name") or detected_task.get("assignee")

                                    t_title = detected_task.get("title", "")
                                    if t_title:
                                        dup_stmt = select(Task).where(Task.meeting_id == meeting_id, Task.title == t_title)
                                        dup_res = await db.execute(dup_stmt)
                                        if not dup_res.scalar_one_or_none():
                                            db.add(Task(
                                                workspace_id=ws_id,
                                                meeting_id=meeting_id,
                                                title=t_title,
                                                description=detected_task.get("description"),
                                                assignee_id=detected_task.get("assignee_id"),
                                                assignee_name=detected_task.get("assignee_name"),
                                                assignee_email=detected_task.get("assignee_email"),
                                                deadline=detected_task.get("deadline"),
                                                priority=detected_task.get("priority", "MEDIUM"),
                                                dependencies=detected_task.get("dependencies", []),
                                                confidence=detected_task.get("confidence", 0.92),
                                                classification_type=detected_task.get("classification_type", "EXPLICIT"),
                                                status="AWAITING_APPROVAL"
                                            ))

                                tr = MeetingTranscript(
                                    meeting_id=meeting_id,
                                    speaker_name=speaker,
                                    text=text,
                                    timestamp_formatted=timestamp,
                                    classification=classification,
                                    confidence=seg.get("confidence", 0.9)
                                )
                                db.add(tr)
                                await db.commit()

                            await manager.broadcast(meeting_id, {
                                "type": "LIVE_TRANSCRIPT_SEGMENT",
                                "speaker": speaker,
                                "text": text,
                                "timestamp": timestamp,
                                "classification": classification,
                                "detected_task": detected_task,
                                "detected_decision": detected_decision
                            })
                    except Exception as e:
                        logger.error(f"Error processing AUDIO_CHUNK: {e}")

            elif event_type == "STATUS_UPDATE":
                status = data.get("status", "LIVE")
                duration = data.get("duration", 0)

                async with AsyncSessionLocal() as db:
                    stmt = select(Meeting).where(Meeting.id == meeting_id)
                    res = await db.execute(stmt)
                    mtg = res.scalar_one_or_none()
                    if mtg:
                        mtg.status = status
                        mtg.duration_seconds = duration
                        await db.commit()

                await manager.broadcast(meeting_id, {
                    "type": "MEETING_STATUS_CHANGED",
                    "status": status,
                    "duration": duration
                })

    except WebSocketDisconnect:
        manager.disconnect(meeting_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error in meeting {meeting_id}: {e}")
        manager.disconnect(meeting_id, websocket)
