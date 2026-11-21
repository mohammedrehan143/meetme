-- ============================================================================
-- MEETME MIGRATION 003: Cross-Meeting Memory Engine, Conflict Detection,
-- Integrations Hub (Jira/GitHub), and Personalized Weekly Digests
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 0. SCHEMA REPAIR FOR APPROVALS (nullable task_id for decision resolutions & notifications)
ALTER TABLE approvals ALTER COLUMN task_id DROP NOT NULL;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS action_category VARCHAR(50) DEFAULT 'EMAIL_DISPATCH';
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS target_platform VARCHAR(50) DEFAULT 'EMAIL';

-- 1. PROJECTS
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(50) NOT NULL DEFAULT 'PROJ',
    description TEXT,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. DECISIONS
CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    context TEXT,
    category VARCHAR(50) DEFAULT 'TECHNICAL', -- TECHNICAL, ARCHITECTURE, PRODUCT, PROCESS, TIMELINE
    status VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, SUPERSEDED, CONFLICTED, OBSOLETE
    decided_by_name VARCHAR(255),
    decided_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    evidence_quote TEXT,
    superseded_by_id UUID REFERENCES decisions(id) ON DELETE SET NULL,
    confidence NUMERIC DEFAULT 0.90,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. COMMITMENTS
CREATE TABLE IF NOT EXISTS commitments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID REFERENCES workspace_members(id) ON DELETE SET NULL,
    assignee_name VARCHAR(255) NOT NULL,
    assignee_email VARCHAR(255) NOT NULL,
    original_deadline VARCHAR(50),
    current_deadline VARCHAR(50),
    status VARCHAR(50) DEFAULT 'IN_PROGRESS', -- PENDING, IN_PROGRESS, COMPLETED, OVERDUE, DELAYED
    delay_count INTEGER DEFAULT 0,
    blockers JSONB DEFAULT '[]'::jsonb,
    completion_evidence TEXT,
    related_meeting_ids JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC DEFAULT 0.90,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. DECISION CONFLICTS
CREATE TABLE IF NOT EXISTS decision_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    previous_decision_id UUID REFERENCES decisions(id) ON DELETE CASCADE,
    new_decision_id UUID REFERENCES decisions(id) ON DELETE SET NULL,
    previous_meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    new_meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    conflict_type VARCHAR(50) DEFAULT 'DIRECT_CONTRADICTION',
    explanation TEXT NOT NULL,
    confidence NUMERIC DEFAULT 0.90,
    suggested_resolution TEXT,
    status VARCHAR(50) DEFAULT 'UNRESOLVED', -- UNRESOLVED, ACCEPTED_NEW, RETAINED_PREVIOUS, MANUAL_EDIT
    source_evidence_prev TEXT,
    source_evidence_new TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. DECISION RESOLUTIONS
CREATE TABLE IF NOT EXISTS decision_resolutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID REFERENCES decision_conflicts(id) ON DELETE CASCADE NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    resolved_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_taken VARCHAR(50) NOT NULL, -- ACCEPT_NEW, RETAIN_PREVIOUS, MANUAL_EDIT, MARK_UNRESOLVED
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. MEMORY RELATIONSHIPS
CREATE TABLE IF NOT EXISTS memory_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(36) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL, -- SUPERSEDES, DEPENDS_ON, CONFLICTS_WITH, DERIVED_FROM, REFINES
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. MEMORY EMBEDDINGS
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    memory_id VARCHAR(36) NOT NULL,
    content_text TEXT NOT NULL,
    embedding_vector JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. EXTERNAL INTEGRATIONS
CREATE TABLE IF NOT EXISTS external_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    provider VARCHAR(50) NOT NULL, -- JIRA, GITHUB, SLACK
    is_active BOOLEAN DEFAULT FALSE,
    credentials_encrypted JSONB DEFAULT '{}'::jsonb,
    config JSONB DEFAULT '{}'::jsonb,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 9. EXTERNAL ISSUE SYNCS
CREATE TABLE IF NOT EXISTS external_issue_syncs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    approval_id UUID REFERENCES approvals(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    external_key_or_number VARCHAR(255),
    external_url VARCHAR(500),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'CREATED',
    idempotency_key VARCHAR(255),
    error_message TEXT,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 10. WEEKLY DIGESTS
CREATE TABLE IF NOT EXISTS weekly_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    member_id UUID REFERENCES workspace_members(id) ON DELETE SET NULL,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255) DEFAULT 'Team Member',
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    content_json JSONB DEFAULT '{}'::jsonb,
    html_body TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'GENERATED',
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_decisions_workspace ON decisions(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_decisions_meeting ON decisions(meeting_id);
CREATE INDEX IF NOT EXISTS idx_commitments_assignee ON commitments(workspace_id, assignee_name, status);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON decision_conflicts(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_memory_relationships_source ON memory_relationships(source_id, source_type);
CREATE INDEX IF NOT EXISTS idx_memory_relationships_target ON memory_relationships(target_id, target_type);
CREATE INDEX IF NOT EXISTS idx_external_integrations_provider ON external_integrations(workspace_id, provider);
CREATE INDEX IF NOT EXISTS idx_external_issue_syncs_task ON external_issue_syncs(task_id);
CREATE INDEX IF NOT EXISTS idx_weekly_digests_member ON weekly_digests(workspace_id, member_id);

-- Row Level Security (RLS)
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_conflicts ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_resolutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_issue_syncs ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_digests ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    CREATE POLICY "Allow authenticated read-write for decisions" ON decisions FOR ALL USING (true);
    CREATE POLICY "Allow authenticated read-write for commitments" ON commitments FOR ALL USING (true);
    CREATE POLICY "Allow authenticated read-write for conflicts" ON decision_conflicts FOR ALL USING (true);
    CREATE POLICY "Allow authenticated read-write for resolutions" ON decision_resolutions FOR ALL USING (true);
    CREATE POLICY "Allow authenticated read-write for digests" ON weekly_digests FOR ALL USING (true);
    CREATE POLICY "Allow authenticated read-write for integrations" ON external_integrations FOR ALL USING (true);
EXCEPTION WHEN others THEN
    NULL;
END $$;
