import { 
  Meeting, Task, Approval, EmailLog, Reminder, TeamMember, AnalyticsData, NotificationItem 
} from "./types";

export const PRODUCTION_API_URL = "https://meetme-8r0u.onrender.com/api";
export const PRODUCTION_WS_URL = "wss://meetme-8r0u.onrender.com";

// In production or when deployed on Vercel, directly connect to the live Render backend
const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL?.trim() || 
  PRODUCTION_API_URL
).replace(/\/+$/, "");

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
    return fetchJson(`${API_BASE}/settings/test-smtp`, { method: "POST" });
  },
  async seedDemo(force: boolean = false): Promise<any> {
    return fetchJson(`${API_BASE}/demo/seed?force=${force}`, { method: "POST" });
  },
  async getNotifications(): Promise<NotificationItem[]> {
    return fetchJson<NotificationItem[]>(`${API_BASE}/notifications`);
  },
  async markNotificationRead(id: string): Promise<any> {
    return fetchJson(`${API_BASE}/notifications/${id}/read`, { method: "POST" });
  }
};
