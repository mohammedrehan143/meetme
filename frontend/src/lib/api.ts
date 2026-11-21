import { 
  Meeting, Task, Approval, EmailLog, Reminder, TeamMember, AnalyticsData, NotificationItem 
} from "./types";

export const PRODUCTION_API_URL = "https://meetme-8r0u.onrender.com/api";
export const PRODUCTION_WS_URL = "wss://meetme-8r0u.onrender.com";

function resolveApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!envUrl) return PRODUCTION_API_URL;
  let clean = envUrl.replace(/\/+$/, "");
  // Ensure the base URL includes /api so endpoints like /meetings, /tasks map correctly
  if (!clean.endsWith("/api") && !clean.endsWith("/v1")) {
    clean = `${clean}/api`;
  }
  return clean;
}

const API_BASE = resolveApiBase();

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    }
  });
  if (!res.ok) {
    let errorDetail = "API Request failed";
    try {
      const err = await res.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = res.statusText;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Meetings
  async getMeetings(): Promise<Meeting[]> {
    return fetchJson<Meeting[]>(`${API_BASE}/meetings`);
  },
  async getMeeting(id: string): Promise<Meeting> {
    return fetchJson<Meeting>(`${API_BASE}/meetings/${id}`);
  },
  async createMeeting(title: string, recordingMode: string = "RECORDED"): Promise<{ id: string }> {
    return fetchJson<{ id: string }>(`${API_BASE}/meetings`, {
      method: "POST",
      body: JSON.stringify({ title, recording_mode: recordingMode })
    });
  },
  async uploadMeeting(formData: FormData): Promise<any> {
    const res = await fetch(`${API_BASE}/meetings/upload`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },

  // Tasks
  async getTasks(params?: { status?: string; priority?: string; search?: string }): Promise<Task[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.priority) query.append("priority", params.priority);
    if (params?.search) query.append("search", params.search);
    return fetchJson<Task[]>(`${API_BASE}/tasks?${query.toString()}`);
  },
  async getTask(id: string): Promise<Task> {
    return fetchJson<Task>(`${API_BASE}/tasks/${id}`);
  },
  async updateTask(id: string, updates: Partial<Task>): Promise<any> {
    return fetchJson(`${API_BASE}/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates)
    });
  },
  async completeTask(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/tasks/${id}/complete`, { method: "POST" });
  },
  async deleteTask(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/tasks/${id}`, { method: "DELETE" });
  },

  // Approvals
  async getApprovals(status?: string): Promise<Approval[]> {
    const query = status ? `?status=${status}` : "";
    return fetchJson<Approval[]>(`${API_BASE}/approvals${query}`);
  },
  async approveAction(id: string, customPayload?: any, notes?: string): Promise<any> {
    return fetchJson(`${API_BASE}/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ custom_payload: customPayload, approval_notes: notes })
    });
  },
  async dispatchApprovalEmail(id: string, toEmail: string, recipientName?: string): Promise<any> {
    return fetchJson(`${API_BASE}/approvals/${id}/dispatch-email`, {
      method: "POST",
      body: JSON.stringify({ to_email: toEmail, recipient_name: recipientName })
    });
  },
  async batchApprove(ids: string[]): Promise<any> {
    return fetchJson(`${API_BASE}/approvals/batch-approve`, {
      method: "POST",
      body: JSON.stringify({ approval_ids: ids })
    });
  },
  async rejectAction(id: string, reason?: string): Promise<any> {
    return fetchJson(`${API_BASE}/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason })
    });
  },

  // Emails
  async getEmails(): Promise<EmailLog[]> {
    return fetchJson<EmailLog[]>(`${API_BASE}/emails`);
  },
  async sendEmail(data: {
    to_email: string;
    recipient_name?: string;
    subject: string;
    message: string;
    email_type?: string;
  }): Promise<any> {
    return fetchJson(`${API_BASE}/emails/send`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  async retryEmail(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/emails/${id}/retry`, { method: "POST" });
  },

  // Reminders
  async getReminders(status?: string): Promise<Reminder[]> {
    const query = status ? `?status=${status}` : "";
    return fetchJson<Reminder[]>(`${API_BASE}/reminders${query}`);
  },
  async cancelReminder(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/reminders/${id}/cancel`, { method: "POST" });
  },
  async triggerRemindersNow(): Promise<any> {
    return fetchJson(`${API_BASE}/reminders/process-now`, { method: "POST" });
  },

  // Analytics
  async getAnalytics(): Promise<AnalyticsData> {
    return fetchJson<AnalyticsData>(`${API_BASE}/analytics`);
  },

  // Team
  async getTeam(): Promise<TeamMember[]> {
    return fetchJson<TeamMember[]>(`${API_BASE}/team`);
  },
  async createTeamMember(member: { full_name: string; email: string; role: string; title: string }): Promise<any> {
    return fetchJson(`${API_BASE}/team`, {
      method: "POST",
      body: JSON.stringify(member)
    });
  },

  // Settings & Notifications
  async getSettings(): Promise<any> {
    return fetchJson(`${API_BASE}/settings`);
  },
  async updateSettings(settings: any): Promise<any> {
    return fetchJson(`${API_BASE}/settings`, {
      method: "POST",
      body: JSON.stringify(settings)
    });
  },
  async testSmtp(): Promise<any> {
    return fetchJson(`${API_BASE}/settings/test-email`, { method: "POST" });
  },
  async testEmailConnection(): Promise<any> {
    return fetchJson(`${API_BASE}/settings/test-email`, { method: "POST" });
  },
  async testEmailDispatch(toEmail: string, recipientName?: string): Promise<any> {
    return fetchJson(`${API_BASE}/settings/test-dispatch`, {
      method: "POST",
      body: JSON.stringify({ to_email: toEmail, recipient_name: recipientName })
    });
  },
  async seedDemo(force: boolean = false): Promise<any> {
    return fetchJson(`${API_BASE}/demo/seed?force=${force}`, { method: "POST" });
  },
  async getNotifications(): Promise<NotificationItem[]> {
    return fetchJson<NotificationItem[]>(`${API_BASE}/notifications`);
  },
  async markNotificationRead(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/notifications/${id}/read`, { method: "POST" });
  },

  // Cross-Meeting Memory Engine
  async getDecisions(params?: { status?: string; category?: string; search?: string }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.category) query.append("category", params.category);
    if (params?.search) query.append("search", params.search);
    return fetchJson<any[]>(`${API_BASE}/memory/decisions?${query.toString()}`);
  },
  async getCommitments(params?: { status?: string; assignee_name?: string; is_delayed?: boolean }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.assignee_name) query.append("assignee_name", params.assignee_name);
    if (params?.is_delayed !== undefined) query.append("is_delayed", String(params.is_delayed));
    return fetchJson<any[]>(`${API_BASE}/memory/commitments?${query.toString()}`);
  },
  async getConflicts(status?: string): Promise<any[]> {
    const query = status ? `?status=${status}` : "";
    return fetchJson<any[]>(`${API_BASE}/memory/conflicts${query}`);
  },
  async resolveConflict(conflictId: string, action: string, notes?: string, customDecisionPayload?: any): Promise<any> {
    return fetchJson(`${API_BASE}/memory/conflicts/${conflictId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ action, notes, custom_decision_payload: customDecisionPayload })
    });
  },

  // External Integrations (Jira & GitHub)
  async getIntegrations(): Promise<any> {
    return fetchJson(`${API_BASE}/integrations`);
  },
  async connectJira(data: { domain: string; email: string; api_token: string; project_key?: string; issue_type?: string }): Promise<any> {
    return fetchJson(`${API_BASE}/integrations/jira/connect`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  },
  async disconnectJira(): Promise<any> {
    return fetchJson(`${API_BASE}/integrations/jira/disconnect`, { method: "POST" });
  },
  async connectGitHub(data: { token: string; repo: string }): Promise<any> {
    return fetchJson(`${API_BASE}/integrations/github/connect`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  },
  async disconnectGitHub(): Promise<any> {
    return fetchJson(`${API_BASE}/integrations/github/disconnect`, { method: "POST" });
  },
  async getIntegrationActivity(): Promise<any[]> {
    return fetchJson<any[]>(`${API_BASE}/integrations/activity`);
  },

  // Personalized Weekly Digest
  async getDigests(memberId?: string): Promise<any[]> {
    const query = memberId ? `?member_id=${memberId}` : "";
    return fetchJson<any[]>(`${API_BASE}/digest${query}`);
  },
  async getDigest(digestId: string): Promise<any> {
    return fetchJson(`${API_BASE}/digest/${digestId}`);
  },
  async generateDigests(data: { member_id?: string; period_days?: number; dispatch_email_now?: boolean }): Promise<any> {
    return fetchJson(`${API_BASE}/digest/generate`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  },
  async sendDigest(digestId: string): Promise<any> {
    return fetchJson(`${API_BASE}/digest/${digestId}/send`, { method: "POST" });
  }
};
