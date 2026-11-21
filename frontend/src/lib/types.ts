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
  task_id: string;
  meeting_id?: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED";
  proposed_payload: {
    title: string;
    description?: string;
    assignee_id?: string;
    assignee_name?: string;
    assignee_email?: string;
    deadline?: string;
    priority: Priority;
    confidence: number;
    evidence_quote?: string;
    email_content?: {
      subject: string;
      html: string;
      text: string;
    };
    meeting_title?: string;
    requires_clarification?: boolean;
  };
  approved_payload?: any;
  approved_recipient?: string;
  approval_notes?: string;
  approved_at?: string;
  created_at: string;
}

export interface EmailLog {
  id: string;
  task_id?: string;
  recipient: string;
  email_address: string;
  subject: string;
  body_html: string;
  body_text?: string;
  status: "PENDING" | "SENT" | "FAILED" | "QUEUED_LOCAL";
  provider: string;
  provider_message_id?: string;
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
