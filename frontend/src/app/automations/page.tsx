"use client";

import React, { useEffect, useState } from "react";
import { 
  Cpu, 
  Clock, 
  Play, 
  RotateCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Calendar, 
  Mail,
  Zap
} from "lucide-react";
import { api } from "@/lib/api";
import { Reminder } from "@/lib/types";

export default function AutomationsPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggeringWorker, setTriggeringWorker] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  useEffect(() => {
    loadReminders();
  }, [statusFilter]);

  const loadReminders = async () => {
    setLoading(true);
    try {
      const data = await api.getReminders(statusFilter === "ALL" ? undefined : statusFilter);
      setReminders(data);
    } catch (err) {
      console.error("Failed to load reminders:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelReminder = async (id: string) => {
    try {
      await api.cancelReminder(id);
      await loadReminders();
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    }
  };

  const handleTriggerWorkerNow = async () => {
    setTriggeringWorker(true);
    try {
      await api.triggerRemindersNow();
      await loadReminders();
      alert("Triggered background reminder worker evaluation successfully.");
    } catch (err: any) {
      alert(`Worker execution error: ${err.message}`);
    } finally {
      setTriggeringWorker(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu size={18} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Autonomous Execution Engine</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Persistent database-backed reminder schedules &bull; Background queue &bull; Auto-cancellation on completion.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerWorkerNow}
            disabled={triggeringWorker}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover disabled:opacity-50 transition-colors"
          >
            <Zap size={13} />
            <span>{triggeringWorker ? "Evaluating..." : "Run Worker Cycle Now"}</span>
          </button>
          <button
            onClick={loadReminders}
            className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
            title="Refresh"
          >
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Engine Architecture Callout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3.5 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono uppercase text-accent-neon font-bold">Persistence</span>
          <p className="text-xs text-text-secondary leading-snug">
            All reminders are stored in the database. Never lost on server restart or container recycling.
          </p>
        </div>
        <div className="p-3.5 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono uppercase text-accent-orange font-bold">Auto-Cancellation</span>
          <p className="text-xs text-text-secondary leading-snug">
            When a task is marked &quot;Completed&quot; in the Task Ledger, pending reminders are immediately cancelled.
          </p>
        </div>
        <div className="p-3.5 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono uppercase text-accent-neon font-bold">Idempotency &amp; Backoff</span>
          <p className="text-xs text-text-secondary leading-snug">
            Failed dispatches retry with exponential backoff up to 3 times before failing safely without spam.
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-border-subtle text-xs">
        {["ALL", "PENDING", "SENT", "CANCELLED", "FAILED"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 ${
              statusFilter === st
                ? "border-accent-orange text-accent-orange"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Reminders Table */}
      <div className="rounded bg-bg-card border border-border-subtle overflow-hidden">
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono text-text-muted">
          <span>Target Task &amp; Recipient</span>
          <span>Scheduled Time &amp; Status</span>
        </div>

        <div className="divide-y divide-border-subtle">
          {reminders.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted">
              No reminders found with status &quot;{statusFilter}&quot;.
            </div>
          ) : (
            reminders.map((rem) => {
              const isPending = rem.status === "PENDING";
              return (
                <div
                  key={rem.id}
                  className="p-4 hover:bg-bg-elevated/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                        rem.reminder_type === "OVERDUE" ? "bg-red-500/20 text-red-400" :
                        rem.reminder_type === "DEADLINE_DAY" ? "bg-accent-orange/20 text-accent-orange" :
                        "bg-accent-neon/20 text-accent-neon"
                      }`}>
                        {rem.reminder_type}
                      </span>
                      <strong className="text-text-primary">{rem.task_title || "Action Item"}</strong>
                    </div>

                    <div className="flex items-center gap-3 text-text-secondary font-mono text-[11px]">
                      <span>Recipient: <strong className="text-text-primary">{rem.recipient}</strong></span>
                      <span>Email: <strong className="text-text-primary">{rem.email_address}</strong></span>
                    </div>

                    {rem.last_error && (
                      <p className="text-[11px] text-red-400 italic">
                        Note: {rem.last_error}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center font-mono text-xs">
                    <div className="text-right">
                      <div className="text-text-primary">
                        {rem.scheduled_at ? new Date(rem.scheduled_at).toLocaleString() : "TBD"}
                      </div>
                      <span className={`text-[10px] font-bold ${
                        rem.status === "SENT" ? "text-accent-neon" :
                        rem.status === "CANCELLED" ? "text-text-muted line-through" :
                        rem.status === "FAILED" ? "text-red-400" :
                        "text-accent-orange animate-pulse"
                      }`}>
                        {rem.status}
                      </span>
                    </div>

                    {isPending && (
                      <button
                        onClick={() => handleCancelReminder(rem.id)}
                        className="px-2.5 py-1 text-[11px] font-medium bg-bg-elevated border border-border-subtle hover:border-red-500/40 text-red-400 rounded transition-colors"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
