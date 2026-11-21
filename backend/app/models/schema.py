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
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action_category = Column(String(50), default="EMAIL_DISPATCH") # EMAIL_DISPATCH, JIRA_ISSUE_CREATE, GITHUB_ISSUE_CREATE, SLACK_NOTIFICATION, DECISION_RESOLUTION
    target_platform = Column(String(50), default="EMAIL") # EMAIL, JIRA, GITHUB, SLACK
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
    task_ids = Column(JSON, default=list)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    recipient = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False, index=True)
    email_type = Column(String(50), default="TASK_ASSIGNMENT") # TASK_ASSIGNMENT, CONSOLIDATED_REMINDER, PRE_DEADLINE, DEADLINE_DAY, OVERDUE, MEETING_SUMMARY
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, SENT, FAILED, QUEUED_DEV
    provider = Column(String(50), default="Gmail SMTP")
    message_id = Column(String(255), nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    task_ids = Column(JSON, default=list)
    recipient = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False)
    reminder_type = Column(String(50), default="PRE_DEADLINE") # PRE_DEADLINE, DEADLINE_DAY, OVERDUE, CONSOLIDATED
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="PENDING") # PENDING, SENT, CANCELLED, FAILED
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    idempotency_key = Column(String(255), nullable=True, index=True)
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

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key = Column(String(50), nullable=False, default="PROJ") # e.g. PROJ, ENG
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    category = Column(String(50), default="TECHNICAL") # TECHNICAL, ARCHITECTURE, PRODUCT, PROCESS, TIMELINE
    status = Column(String(50), default="ACTIVE") # ACTIVE, SUPERSEDED, CONFLICTED, OBSOLETE
    decided_by_name = Column(String(255), nullable=True)
    decided_by_id = Column(String(36), nullable=True)
    evidence_quote = Column(Text, nullable=True)
    superseded_by_id = Column(String(36), ForeignKey("decisions.id"), nullable=True)
    confidence = Column(Float, default=0.90)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Commitment(Base):
    __tablename__ = "commitments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String(36), ForeignKey("workspace_members.id"), nullable=True)
    assignee_name = Column(String(255), nullable=False)
    assignee_email = Column(String(255), nullable=False)
    original_deadline = Column(String(50), nullable=True)
    current_deadline = Column(String(50), nullable=True)
    status = Column(String(50), default="IN_PROGRESS") # PENDING, IN_PROGRESS, COMPLETED, OVERDUE, DELAYED
    delay_count = Column(Integer, default=0)
    blockers = Column(JSON, default=list)
    completion_evidence = Column(Text, nullable=True)
    related_meeting_ids = Column(JSON, default=list)
    confidence = Column(Float, default=0.90)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DecisionConflict(Base):
    __tablename__ = "decision_conflicts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    previous_decision_id = Column(String(36), ForeignKey("decisions.id"), nullable=True, index=True)
    new_decision_id = Column(String(36), ForeignKey("decisions.id"), nullable=True, index=True)
    previous_meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    new_meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    conflict_type = Column(String(50), default="DIRECT_CONTRADICTION") 
    # DIRECT_CONTRADICTION, TECHNICAL_REVERSAL, REQUIREMENT_CONFLICT, DEADLINE_CHANGE, REFINEMENT
    explanation = Column(Text, nullable=False)
    confidence = Column(Float, default=0.90)
    suggested_resolution = Column(Text, nullable=True)
    status = Column(String(50), default="UNRESOLVED") # UNRESOLVED, ACCEPTED_NEW, RETAINED_PREVIOUS, MANUAL_EDIT
    source_evidence_prev = Column(Text, nullable=True)
    source_evidence_new = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DecisionResolution(Base):
    __tablename__ = "decision_resolutions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conflict_id = Column(String(36), ForeignKey("decision_conflicts.id"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    resolved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action_taken = Column(String(50), nullable=False) # ACCEPT_NEW, RETAIN_PREVIOUS, MANUAL_EDIT, MARK_UNRESOLVED
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, default=datetime.utcnow)

class MemoryRelationship(Base):
    __tablename__ = "memory_relationships"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False) # DECISION, COMMITMENT, TASK, MEETING
    source_id = Column(String(36), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(36), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False) # SUPERSEDES, DEPENDS_ON, CONFLICTS_WITH, DERIVED_FROM, REFINES
    created_at = Column(DateTime, default=datetime.utcnow)

class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False) # DECISION, COMMITMENT, TRANSCRIPT
    memory_id = Column(String(36), nullable=False, index=True)
    content_text = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=True) # Float list vector for cosine similarity search
    created_at = Column(DateTime, default=datetime.utcnow)

class ExternalIntegration(Base):
    __tablename__ = "external_integrations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False) # JIRA, GITHUB, SLACK
    is_active = Column(Boolean, default=False)
    credentials_encrypted = Column(JSON, default=dict) # e.g. api_token, domain, email, pat
    config = Column(JSON, default=dict) # e.g. project_key, repo_name, issue_type, labels
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExternalIssueSync(Base):
    __tablename__ = "external_issue_syncs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    approval_id = Column(String(36), ForeignKey("approvals.id"), nullable=True, index=True)
    provider = Column(String(50), nullable=False) # JIRA, GITHUB
    external_id = Column(String(255), nullable=True)
    external_key_or_number = Column(String(255), nullable=True) # e.g. PROJ-101 or #42
    external_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="CREATED") # CREATED, SYNCED, CLOSED, FAILED
    idempotency_key = Column(String(255), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    member_id = Column(String(36), ForeignKey("workspace_members.id"), nullable=True, index=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), default="Team Member")
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    content_json = Column(JSON, default=dict)
    html_body = Column(Text, nullable=False)
    status = Column(String(50), default="GENERATED") # GENERATED, SENT, FAILED
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
