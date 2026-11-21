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

                # Run fast classification
                analysis = await transcription_agent.analyze(f"{speaker}: {text}")
                seg = analysis[0] if analysis else {
                    "classification": "GENERAL_DISCUSSION",
                    "confidence": 0.85
                }

                classification = seg.get("classification", "GENERAL_DISCUSSION")

                # Persist to database
                async with AsyncSessionLocal() as db:
                    tr = MeetingTranscript(
                        meeting_id=meeting_id,
                        speaker_name=speaker,
                        text=text,
                        timestamp_formatted=timestamp,
                        classification=classification,
                        confidence=seg.get("confidence", 0.9)
                    )
                    db.add(tr)

                    # If classification is TASK or DECISION, extract structured item on the fly!
                    detected_task = None
                    if classification in ["TASK", "COMMITMENT"]:
                        tasks = await task_agent.extract_tasks(f"{speaker}: {text}")
                        if tasks:
                            detected_task = tasks[0]

                    detected_decision = None
                    if classification == "DECISION":
                        decisions = await decision_agent.extract_decisions(f"{speaker}: {text}")
                        if decisions.get("decisions"):
                            detected_decision = decisions["decisions"][0]

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
