import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="member") # admin, member, viewer
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), default="member") # admin, member, guest
    title = Column(String(100), default="Team Member")
    created_at = Column(DateTime, default=datetime.utcnow)

class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, default=0)
    status = Column(String(50), default="SCHEDULED") # SCHEDULED, LIVE, PROCESSING, COMPLETED, FAILED
    audio_url = Column(String(500), nullable=True)
    recording_mode = Column(String(50), default="RECORDED") # LIVE, RECORDED
    summary = Column(Text, nullable=True)
    key_decisions = Column(JSON, default=list)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transcripts = relationship("MeetingTranscript", back_populates="meeting", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="meeting", cascade="all, delete-orphan")

class MeetingTranscript(Base):
    __tablename__ = "meeting_transcripts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    speaker_id = Column(String(36), nullable=True)
    speaker_name = Column(String(255), default="Unknown Speaker")
    text = Column(Text, nullable=False)
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, default=0.0)
    timestamp_formatted = Column(String(50), default="00:00:00")
    confidence = Column(Float, default=1.0)
    classification = Column(String(50), default="GENERAL_DISCUSSION") 
    # TASK, DECISION, COMMITMENT, QUESTION, BLOCKER, GENERAL_DISCUSSION, IRRELEVANT
    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="transcripts")

class Speaker(Base):
    __tablename__ = "speakers"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    detected_voice_id = Column(String(100), nullable=True)
    mapped_member_id = Column(String(36), ForeignKey("workspace_members.id"), nullable=True)
    confidence = Column(Float, default=0.85)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True, index=True)
    transcript_id = Column(String(36), ForeignKey("meeting_transcripts.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String(36), ForeignKey("workspace_members.id"), nullable=True)
    assignee_name = Column(String(255), nullable=True)
    assignee_email = Column(String(255), nullable=True)
    deadline = Column(String(50), nullable=True) # ISO Date string or format YYYY-MM-DD
    priority = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH, URGENT
    dependencies = Column(JSON, default=list) # List of dependency strings or task IDs
    confidence = Column(Float, default=0.90)
    classification_type = Column(String(20), default="EXPLICIT") # EXPLICIT or INFERRED
    status = Column(String(50), default="AWAITING_APPROVAL")
    # DETECTED, AWAITING_APPROVAL, APPROVED, ASSIGNED, IN_PROGRESS, COMPLETED, OVERDUE, REJECTED
    evidence_quote = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="tasks")

class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    proposed_payload = Column(JSON, nullable=False)
    approved_payload = Column(JSON, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, MODIFIED
    approved_recipient = Column(String(255), nullable=True)
    approval_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    recipient = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, SENT, FAILED, QUEUED_LOCAL
    provider = Column(String(50), default="Resend")
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False)
    reminder_type = Column(String(50), default="PRE_DEADLINE") # PRE_DEADLINE, DEADLINE_DAY, OVERDUE
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="PENDING") # PENDING, SENT, CANCELLED, FAILED
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AutomationLog(Base):
    __tablename__ = "automation_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
    trigger_type = Column(String(100), nullable=False) # e.g., TASK_APPROVED, DEADLINE_REACHED, TASK_COMPLETED
    action_type = Column(String(100), nullable=False)  # e.g., SEND_EMAIL, SCHEDULE_REMINDER, CANCEL_REMINDER
    payload = Column(JSON, nullable=True)
    status = Column(String(50), default="SUCCESS") # SUCCESS, FAILURE, SKIPPED
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True, index=True)
    agent_name = Column(String(100), nullable=False) # Transcription Analysis, Task Extraction, etc.
    status = Column(String(50), default="COMPLETED") # RUNNING, COMPLETED, FAILED
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    input_summary = Column(Text, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO") # INFO, WARNING, SUCCESS, ACTION_REQUIRED
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
