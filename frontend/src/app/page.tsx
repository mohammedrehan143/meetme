"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Radio, 
  Upload, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  Check, 
  X, 
  Mail, 
  TrendingUp, 
  AlertTriangle, 
  Info,
  Calendar,
  Layers
} from "lucide-react";
import { api } from "@/lib/api";
import { AnalyticsData, Meeting, Task, Approval } from "@/lib/types";

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);
  const [upcomingTasks, setUpcomingTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [analyticsData, meetingsData, approvalsData, tasksData] = await Promise.all([
        api.getAnalytics(),
        api.getMeetings(),
        api.getApprovals("PENDING"),
        api.getTasks({ status: "APPROVED" })
      ]);
      setAnalytics(analyticsData);
      setMeetings(meetingsData.slice(0, 5));
      setPendingApprovals(approvalsData.slice(0, 4));
      setUpcomingTasks(tasksData.slice(0, 5));
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickApprove = async (approvalId: string) => {
    setApprovingId(approvalId);
    try {
      await api.approveAction(approvalId);
      await loadDashboardData();
    } catch (err) {
      console.error("Approval error:", err);
    } finally {
      setApprovingId(null);
    }
  };

  const metrics = analytics?.metrics || {
    total_meetings: 0,
    meetings_processed: 0,
    tasks_identified: 0,
    tasks_completed: 0,
    pending_approvals: 0,
    overdue_tasks: 0,
    emails_sent: 0,
    upcoming_deadlines: 0,
    completion_rate: 0
  };

  const metricCards = [
    { label: "Total Meetings", value: metrics.total_meetings, sub: `${metrics.meetings_processed} Processed` },
    { label: "Tasks Identified", value: metrics.tasks_identified, sub: `${metrics.completion_rate}% Completed`, accent: "text-accent-neon" },
    { label: "Pending Approvals", value: metrics.pending_approvals, sub: "Requires human signoff", accent: metrics.pending_approvals > 0 ? "text-accent-orange" : "text-text-primary" },
    { label: "Overdue Tasks", value: metrics.overdue_tasks, sub: "Reminders active", accent: metrics.overdue_tasks > 0 ? "text-red-400" : "text-text-primary" },
    { label: "Emails Dispatched", value: metrics.emails_sent, sub: "Via Gmail SMTP Engine" },
    { label: "Upcoming Deadlines", value: metrics.upcoming_deadlines, sub: "Next 7 Days" },
  ];

  return (
    <div className="space-y-6">
      {/* Top Welcome & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border-subtle">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-text-primary">Executive Intelligence Command</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Real-time pipeline: Meetings in &rarr; Autonomous execution out.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/recorded"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-bg-card border border-border-subtle hover:border-border-strong text-text-primary rounded text-xs font-medium transition-colors"
          >
            <Upload size={13} />
            <span>Upload Meeting</span>
          </Link>
          <Link
            href="/live"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent-orange text-black font-semibold rounded text-xs hover:bg-accent-orange-hover transition-colors"
          >
            <Radio size={13} />
            <span>Start Live Meeting</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {metricCards.map((m, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded bg-bg-card border border-border-subtle flex flex-col justify-between"
          >
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-secondary">{m.label}</span>
            <div className="my-2">
              <span className={`text-2xl font-bold font-mono ${m.accent || "text-text-primary"}`}>
                {m.value}
              </span>
            </div>
            <span className="text-[10px] text-text-muted font-mono">{m.sub}</span>
          </div>
        ))}
      </div>

      {/* Main Grid: Approvals Gate & Recent Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Section B: Pending Approvals (Mandatory Human Signoff) */}
        <div className="lg:col-span-2 rounded bg-bg-card border border-border-subtle flex flex-col">
          <div className="p-4 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert size={16} className="text-accent-orange" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Pending Execution Approvals
              </h2>
            </div>
            <Link
              href="/approvals"
              className="text-[11px] text-accent-orange hover:underline font-mono flex items-center gap-1"
            >
              <span>View All ({metrics.pending_approvals})</span>
              <ArrowRight size={11} />
            </Link>
          </div>

          <div className="divide-y divide-border-subtle p-2">
            {pendingApprovals.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No tasks awaiting approval. All action items executed or clear.
              </div>
            ) : (
              pendingApprovals.map((app) => {
                const payload = app.proposed_payload || {};
                return (
                  <div key={app.id} className="p-3 hover:bg-bg-elevated/40 rounded transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                          payload.priority === "URGENT" || payload.priority === "HIGH" 
                            ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30"
                            : "bg-bg-elevated text-text-secondary border border-border-subtle"
                        }`}>
                          {payload.priority}
                        </span>
                        <h3 className="text-xs font-semibold text-text-primary">{payload.title}</h3>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-text-secondary font-mono">
                        <span>Assignee: <strong className="text-text-primary">{payload.assignee_name || "Unassigned"}</strong></span>
                        <span>Deadline: <strong className="text-text-primary">{payload.deadline || "TBD"}</strong></span>
                        <span>Confidence: <strong className="text-accent-neon">{Math.round((payload.confidence || 0.9) * 100)}%</strong></span>
                      </div>
                      {payload.evidence_quote && (
                        <p className="text-[11px] text-text-muted italic line-clamp-1">
                          &ldquo;{payload.evidence_quote}&rdquo;
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <Link
                        href={`/approvals?id=${app.id}`}
                        className="px-2.5 py-1 text-[11px] font-medium bg-bg-elevated text-text-primary border border-border-subtle hover:border-border-strong rounded"
                      >
                        Review
                      </Link>
                      <button
                        onClick={() => handleQuickApprove(app.id)}
                        disabled={approvingId === app.id}
                        className="px-3 py-1 text-[11px] font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover rounded flex items-center gap-1 transition-colors disabled:opacity-50"
                      >
                        <Check size={12} />
                        <span>{approvingId === app.id ? "Executing..." : "Approve"}</span>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Section F: AI Autonomous Insights */}
        <div className="rounded bg-bg-card border border-border-subtle flex flex-col">
          <div className="p-4 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-accent-neon" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Autonomous AI Insights
              </h2>
            </div>
            <span className="text-[10px] font-mono text-accent-neon">LIVE DB</span>
          </div>

          <div className="p-4 space-y-3">
            {(analytics?.ai_insights || []).map((insight, idx) => (
              <div
                key={idx}
                className="p-3 rounded bg-bg-elevated border border-border-subtle text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text-primary">{insight.title}</span>
                  <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
                    insight.type === "ACTION_REQUIRED" ? "bg-accent-orange/20 text-accent-orange" :
                    insight.type === "WARNING" ? "bg-red-500/20 text-red-400" :
                    "bg-accent-neon/15 text-accent-neon"
                  }`}>
                    {insight.type}
                  </span>
                </div>
                <p className="text-text-secondary text-[11px] leading-relaxed">
                  {insight.message}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second Row: Recent Meetings & Automation Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Section A: Recent Meetings */}
        <div className="lg:col-span-2 rounded bg-bg-card border border-border-subtle flex flex-col">
          <div className="p-4 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar size={16} className="text-text-secondary" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Recent Ingested Meetings
              </h2>
            </div>
            <Link
              href="/meetings"
              className="text-[11px] text-text-secondary hover:text-text-primary font-mono flex items-center gap-1"
            >
              <span>View History</span>
              <ArrowRight size={11} />
            </Link>
          </div>

          <div className="divide-y divide-border-subtle">
            {meetings.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No meetings recorded yet.
              </div>
            ) : (
              meetings.map((m) => (
                <Link
                  key={m.id}
                  href={`/meetings/${m.id}`}
                  className="p-3.5 flex items-center justify-between hover:bg-bg-elevated/40 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-text-primary">{m.title}</span>
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono rounded ${
                        m.status === "COMPLETED" ? "bg-accent-neon/20 text-accent-neon" :
                        m.status === "LIVE" ? "bg-accent-orange/20 text-accent-orange animate-pulse" :
                        "bg-bg-elevated text-text-secondary"
                      }`}>
                        {m.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-text-muted font-mono">
                      <span>{m.recording_mode}</span>
                      <span>{Math.round(m.duration_seconds / 60)} mins</span>
                      <span>{m.tasks_count} Tasks Extracted</span>
                    </div>
                  </div>
                  <ArrowRight size={14} className="text-text-secondary" />
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Section D: Automation Activity Log */}
        <div className="rounded bg-bg-card border border-border-subtle flex flex-col">
          <div className="p-4 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mail size={16} className="text-accent-orange" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Execution Activity
              </h2>
            </div>
            <Link
              href="/automations"
              className="text-[11px] text-text-secondary hover:text-text-primary font-mono flex items-center gap-1"
            >
              <span>Audit Logs</span>
              <ArrowRight size={11} />
            </Link>
          </div>

          <div className="p-3 divide-y divide-border-subtle">
            {(analytics?.automation_activity || []).length === 0 ? (
              <div className="p-6 text-center text-xs text-text-muted">
                No automation logs recorded.
              </div>
            ) : (
              (analytics?.automation_activity || []).map((a) => (
                <div key={a.id} className="py-2.5 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-accent-orange font-semibold">
                      {a.action_type}
                    </span>
                    <span className="text-[9px] font-mono text-accent-neon">
                      {a.status}
                    </span>
                  </div>
                  <p className="text-text-secondary text-[11px] leading-snug">{a.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
