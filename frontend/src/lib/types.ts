export type TaskStatus = 
  | "DETECTED" 
  | "AWAITING_APPROVAL" 
  | "APPROVED" 
  | "ASSIGNED" 
  | "IN_PROGRESS" 
  | "COMPLETED" 
  | "OVERDUE" 
  | "REJECTED";

export type Priority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type ClassificationType = 
  | "TASK" 
  | "DECISION" 
  | "COMMITMENT" 
  | "QUESTION" 
  | "BLOCKER" 
  | "GENERAL_DISCUSSION" 
  | "IRRELEVANT";

export interface Task {
  id: string;
  meeting_id?: string;
  title: string;
  description?: string;
  assignee_id?: string;
  assignee_name?: string;
  assignee_email?: string;
  deadline?: string;
  priority: Priority;
  confidence: number;
  classification_type: "EXPLICIT" | "INFERRED";
  status: TaskStatus;
  evidence_quote?: string;
  created_at: string;
  updated_at?: string;
}

export interface Meeting {
  id: string;
  title: string;
  date: string;
  duration_seconds: number;
  status: "SCHEDULED" | "LIVE" | "PROCESSING" | "COMPLETED" | "FAILED";
  recording_mode: "LIVE" | "RECORDED";
  summary?: string;
  tasks_count: number;
  created_at: string;
  key_decisions?: any[];
  transcripts?: TranscriptSegment[];
  tasks?: Task[];
}

export interface TranscriptSegment {
  id: string;
  speaker_name: string;
  text: string;
  timestamp_formatted: string;
  classification: ClassificationType;
  confidence: number;
}

export interface Approval {
  id: string;
  task_id?: string;
  meeting_id?: string;
  action_category?: "TASK_EXECUTION" | "EMAIL_DISPATCH" | "JIRA_ISSUE_CREATE" | "GITHUB_ISSUE_CREATE" | "DECISION_RESOLUTION";
  target_platform?: "INTERNAL" | "EMAIL" | "JIRA" | "GITHUB";
  status: "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED";
  proposed_payload: any;
  approved_payload?: any;
  approved_recipient?: string;
  approval_notes?: string;
  approved_at?: string;
  created_at: string;
}

export interface EmailLog {
  id: string;
  task_id?: string;
  task_ids?: string[];
  email_type?: string;
  recipient: string;
  email_address: string;
  subject: string;
  body_html: string;
  body_text?: string;
  status: "PENDING" | "SENT" | "FAILED" | "QUEUED_LOCAL" | "ALREADY_SENT" | "QUEUED_DEV";
  provider: string;
  message_id?: string;
  provider_message_id?: string;
  idempotency_key?: string;
  retry_count?: number;
  error_message?: string;
  sent_at?: string;
  created_at: string;
}

export interface Reminder {
  id: string;
  task_id: string;
  task_title?: string;
  recipient: string;
  email_address: string;
  reminder_type: "PRE_DEADLINE" | "DEADLINE_DAY" | "OVERDUE";
  scheduled_at: string;
  status: "PENDING" | "SENT" | "CANCELLED" | "FAILED";
  retry_count: number;
  last_error?: string;
  executed_at?: string;
  created_at: string;
}

export interface TeamMember {
  id: string;
  full_name: string;
  email: string;
  role: string;
  title: string;
  tasks_count: number;
  completed_tasks: number;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: "INFO" | "WARNING" | "SUCCESS" | "ACTION_REQUIRED";
  link?: string;
  is_read: boolean;
  created_at: string;
}

export interface AnalyticsData {
  metrics: {
    total_meetings: number;
    meetings_processed: number;
    tasks_identified: number;
    tasks_completed: number;
    pending_approvals: number;
    overdue_tasks: number;
    emails_sent: number;
    upcoming_deadlines: number;
    completion_rate: number;
  };
  team_workload: Array<{
    member_id: string;
    name: string;
    role: string;
    active_tasks: number;
    completed_tasks: number;
  }>;
  classification_breakdown: Record<string, number>;
  automation_activity: Array<{
    id: string;
    trigger_type: string;
    action_type: string;
    message: string;
    status: string;
    created_at: string;
  }>;
  ai_insights: Array<{
    type: "INFO" | "WARNING" | "SUCCESS" | "ACTION_REQUIRED";
    title: string;
    message: string;
  }>;
}

export interface Decision {
  id: string;
  workspace_id?: string;
  project_id?: string;
  meeting_id?: string;
  title: string;
  category: "TECHNICAL" | "PRODUCT" | "ORGANIZATIONAL" | "REQUIREMENT";
  description: string;
  decided_by?: string;
  date?: string;
  status: "ACTIVE" | "SUPERSEDED" | "PROPOSED" | "REVERTED";
  superseded_by_id?: string;
  confidence: number;
  source_transcript_quote?: string;
  created_at: string;
}

export interface Commitment {
  id: string;
  workspace_id?: string;
  project_id?: string;
  meeting_id?: string;
  assignee_id?: string;
  assignee_name?: string;
  description: string;
  deadline?: string;
  original_deadline?: string;
  status: "OPEN" | "IN_PROGRESS" | "COMPLETED" | "DELAYED" | "OVERDUE" | "CANCELLED";
  delay_count: number;
  unresolved_blockers?: string;
  completion_evidence?: string;
  confidence: number;
  created_at: string;
}

export interface DecisionConflict {
  id: string;
  workspace_id?: string;
  previous_decision_id: string;
  new_decision_id: string;
  conflict_type: "DIRECT_CONTRADICTION" | "TECHNICAL_REVERSAL" | "REQUIREMENT_CONFLICT" | "DEADLINE_SHIFT" | "REFINEMENT";
  explanation: string;
  confidence: number;
  suggested_resolution?: string;
  status: "DETECTED" | "ACCEPTED_NEW" | "RETAINED_PREVIOUS" | "MANUAL_EDIT" | "UNRESOLVED";
  previous_decision?: Decision;
  new_decision?: Decision;
  created_at: string;
}

export interface ExternalIntegration {
  platform: "JIRA" | "GITHUB";
  is_connected: boolean;
  account_name?: string;
  project_or_repo?: string;
  base_url?: string;
  last_sync_at?: string;
}

export interface ExternalIssueSync {
  id: string;
  task_id: string;
  platform: "JIRA" | "GITHUB";
  external_id: string;
  external_key: string;
  external_url: string;
  status: string;
  last_synced_at: string;
  created_at: string;
}

export interface WeeklyDigest {
  id: string;
  member_id: string;
  member_name: string;
  member_email: string;
  period_start: string;
  period_end: string;
  metrics: {
    assigned_count: number;
    completed_count: number;
    in_progress_count: number;
    overdue_count: number;
    upcoming_deadlines_count: number;
  };
  tasks_summary: Array<{
    title: string;
    status: string;
    priority: string;
    deadline?: string;
  }>;
  status: "GENERATED" | "SENT" | "FAILED";
  email_sent_at?: string;
  created_at: string;
}

