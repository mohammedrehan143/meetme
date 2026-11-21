-- MEETME Database Schema for Supabase PostgreSQL
-- Real-time AI Meeting Intelligence and Execution Platform

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    avatar_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. WORKSPACES
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. WORKSPACE MEMBERS
CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    title VARCHAR(100) DEFAULT 'Team Member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. MEETINGS
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(255) NOT NULL,
    date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'SCHEDULED', -- SCHEDULED, LIVE, PROCESSING, COMPLETED, FAILED
    audio_url VARCHAR(500),
    recording_mode VARCHAR(50) DEFAULT 'RECORDED', -- LIVE, RECORDED
    summary TEXT,
    key_decisions JSONB DEFAULT '[]'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. MEETING TRANSCRIPTS
CREATE TABLE IF NOT EXISTS meeting_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE NOT NULL,
    speaker_id VARCHAR(36),
    speaker_name VARCHAR(255) DEFAULT 'Unknown Speaker',
    text TEXT NOT NULL,
    start_time NUMERIC DEFAULT 0.0,
    end_time NUMERIC DEFAULT 0.0,
    timestamp_formatted VARCHAR(50) DEFAULT '00:00:00',
    confidence NUMERIC DEFAULT 1.0,
    classification VARCHAR(50) DEFAULT 'GENERAL_DISCUSSION', -- TASK, DECISION, COMMITMENT, QUESTION, BLOCKER, GENERAL_DISCUSSION, IRRELEVANT
    raw_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. SPEAKERS
CREATE TABLE IF NOT EXISTS speakers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    detected_voice_id VARCHAR(100),
    mapped_member_id UUID REFERENCES workspace_members(id) ON DELETE SET NULL,
    confidence NUMERIC DEFAULT 0.85,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. TASKS
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    transcript_id UUID REFERENCES meeting_transcripts(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID REFERENCES workspace_members(id) ON DELETE SET NULL,
    assignee_name VARCHAR(255),
    assignee_email VARCHAR(255),
    deadline VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, URGENT
    dependencies JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC DEFAULT 0.90,
    classification_type VARCHAR(20) DEFAULT 'EXPLICIT', -- EXPLICIT, INFERRED
    status VARCHAR(50) DEFAULT 'AWAITING_APPROVAL', -- DETECTED, AWAITING_APPROVAL, APPROVED, ASSIGNED, IN_PROGRESS, COMPLETED, OVERDUE, REJECTED
    evidence_quote TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. TASK DEPENDENCIES
CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 9. APPROVALS
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    proposed_payload JSONB NOT NULL,
    approved_payload JSONB,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, MODIFIED
    approved_recipient VARCHAR(255),
    approval_notes TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 10. EMAIL LOGS
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    recipient VARCHAR(255) NOT NULL,
    email_address VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, SENT, FAILED, QUEUED_LOCAL
    provider VARCHAR(50) DEFAULT 'Resend',
    provider_message_id VARCHAR(255),
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 11. REMINDERS
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    email_address VARCHAR(255) NOT NULL,
    reminder_type VARCHAR(50) DEFAULT 'PRE_DEADLINE', -- PRE_DEADLINE, DEADLINE_DAY, OVERDUE
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, SENT, CANCELLED, FAILED
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 12. AUTOMATION LOGS
CREATE TABLE IF NOT EXISTS automation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    trigger_type VARCHAR(100) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    payload JSONB,
    status VARCHAR(50) DEFAULT 'SUCCESS',
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 13. AGENT RUNS
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'COMPLETED',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    input_summary TEXT,
    output_data JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 14. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'INFO',
    link VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_id ON meeting_transcripts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_tasks_workspace_status ON tasks(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_meeting_id ON tasks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_approvals_workspace_status ON approvals(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_status ON reminders(scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_email_logs_workspace ON email_logs(workspace_id);
