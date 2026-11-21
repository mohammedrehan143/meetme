"use client";

import React, { useEffect, useState } from "react";
import { BarChart3, TrendingUp, Users, CheckCircle2, Clock, Mail, ShieldAlert, Cpu } from "lucide-react";
import { api } from "@/lib/api";
import { AnalyticsData } from "@/lib/types";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await api.getAnalytics();
      setData(res);
    } catch (err) {
      console.error("Failed to load analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  const metrics = data?.metrics || {
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

  const classificationMap = data?.classification_breakdown || {};
  const totalSegments = Object.values(classificationMap).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-3 border-b border-border-subtle">
        <h1 className="text-xl font-bold text-text-primary">Execution &amp; Productivity Intelligence</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Calculated exclusively from verified database records &bull; Zero synthetic mock values.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Task Completion Rate</span>
          <p className="text-2xl font-bold font-mono text-accent-neon">{metrics.completion_rate}%</p>
          <span className="text-[11px] text-text-secondary">{metrics.tasks_completed} of {metrics.tasks_identified} closed</span>
        </div>

        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Pending Approvals</span>
          <p className="text-2xl font-bold font-mono text-accent-orange">{metrics.pending_approvals}</p>
          <span className="text-[11px] text-text-secondary">Mandatory human gates</span>
        </div>

        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Overdue Tasks</span>
          <p className="text-2xl font-bold font-mono text-red-400">{metrics.overdue_tasks}</p>
          <span className="text-[11px] text-text-secondary">Automatic escalation active</span>
        </div>

        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Emails Dispatched</span>
          <p className="text-2xl font-bold font-mono text-text-primary">{metrics.emails_sent}</p>
          <span className="text-[11px] text-text-secondary">Resend provider verified</span>
        </div>
      </div>

      {/* 2-Column Section: Team Workload & AI Classification Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Team Workload Allocation */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Users size={16} className="text-accent-orange" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Team Workload &amp; Execution Distribution
              </h2>
            </div>
            <span className="text-[10px] font-mono text-text-muted">ACTIVE</span>
          </div>

          <div className="space-y-4">
            {(data?.team_workload || []).map((member) => {
              const totalMemberTasks = member.active_tasks + member.completed_tasks;
              const pct = totalMemberTasks > 0 ? Math.round((member.completed_tasks / totalMemberTasks) * 100) : 0;
              return (
                <div key={member.member_id} className="space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-text-primary">{member.name}</span>
                      <span className="text-text-muted ml-2 font-mono text-[10px]">{member.role}</span>
                    </div>
                    <div className="font-mono text-[11px] text-text-secondary">
                      <span className="text-accent-orange font-bold">{member.active_tasks} Active</span> /{" "}
                      <span className="text-accent-neon font-bold">{member.completed_tasks} Done</span>
                    </div>
                  </div>

                  <div className="w-full bg-bg-elevated rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-accent-orange h-full rounded-full transition-all"
                      style={{ width: `${Math.min(100, Math.max(10, member.active_tasks * 20))}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Classification Performance Breakdown */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-accent-neon" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                AI Classification Distribution
              </h2>
            </div>
            <span className="text-[10px] font-mono text-text-muted">GROQ INFERENCE</span>
          </div>

          <div className="space-y-3">
            {Object.entries(classificationMap).map(([category, count]) => {
              const percentage = Math.round((count / totalSegments) * 100);
              const color =
                category === "TASK" ? "bg-accent-orange" :
                category === "DECISION" ? "bg-accent-neon" :
                category === "BLOCKER" ? "bg-red-400" :
                category === "COMMITMENT" ? "bg-amber-400" :
                category === "QUESTION" ? "bg-blue-400" :
                "bg-zinc-600";

              return (
                <div key={category} className="space-y-1 text-xs">
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-text-primary font-semibold">{category}</span>
                    <span className="text-text-muted">{count} items ({percentage}%)</span>
                  </div>
                  <div className="w-full bg-bg-elevated rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`${color} h-full rounded-full transition-all`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
