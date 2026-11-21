"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  CheckSquare, 
  Search, 
  Filter, 
  Calendar, 
  User, 
  CheckCircle2, 
  Clock, 
  Trash2, 
  ExternalLink,
  RotateCw,
  AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { Task } from "@/lib/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [completingId, setCompletingId] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await api.getTasks({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        priority: priorityFilter === "ALL" ? undefined : priorityFilter,
        search: search.trim() || undefined
      });
      setTasks(data);
    } catch (err) {
      console.error("Failed to load tasks:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadTasks();
  };

  const handleMarkComplete = async (taskId: string) => {
    setCompletingId(taskId);
    try {
      await api.completeTask(taskId);
      await loadTasks();
    } catch (err: any) {
      alert(`Could not complete task: ${err.message}`);
    } finally {
      setCompletingId(null);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
      await api.deleteTask(taskId);
      await loadTasks();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const viewTabs = [
    { label: "All Tasks", value: "ALL" },
    { label: "Pending Approval", value: "AWAITING_APPROVAL" },
    { label: "Approved / Active", value: "APPROVED" },
    { label: "In Progress", value: "IN_PROGRESS" },
    { label: "Completed", value: "COMPLETED" },
    { label: "Overdue", value: "OVERDUE" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Execution Tasks Ledger</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Structured action items, verified ownership, completion states, and automated reminder bindings.
          </p>
        </div>
        <button
          onClick={loadTasks}
          className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
          title="Refresh tasks"
        >
          <RotateCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle text-xs">
        {viewTabs.map((t) => (
          <button
            key={t.value}
            onClick={() => setStatusFilter(t.value)}
            className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 ${
              statusFilter === t.value
                ? "border-accent-orange text-accent-orange"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Search & Priority Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-bg-card p-3 rounded border border-border-subtle">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter tasks by keyword or owner..."
            className="w-full bg-bg-elevated border border-border-subtle rounded py-1.5 pl-8 pr-3 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
          />
        </form>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <span className="text-xs font-mono text-text-muted">Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-bg-elevated border border-border-subtle rounded px-2.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
          >
            <option value="ALL">All Priorities</option>
            <option value="URGENT">URGENT</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Tasks Table / Card List */}
      <div className="rounded bg-bg-card border border-border-subtle divide-y divide-border-subtle">
        {tasks.length === 0 ? (
          <div className="p-12 text-center text-xs text-text-muted">
            No tasks found in this view.
          </div>
        ) : (
          tasks.map((task) => {
            const isCompleted = task.status === "COMPLETED";
            const isOverdue = task.status === "OVERDUE";

            return (
              <div
                key={task.id}
                className={`p-4 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-bg-elevated/30 ${
                  isCompleted ? "opacity-60 bg-bg-primary/40" : ""
                }`}
              >
                {/* Left: Checkbox & Info */}
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                        task.priority === "URGENT" || task.priority === "HIGH"
                          ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30"
                          : "bg-bg-elevated text-text-secondary border border-border-subtle"
                      }`}
                    >
                      {task.priority}
                    </span>

                    <h3 className={`text-sm font-semibold ${isCompleted ? "line-through text-text-secondary" : "text-text-primary"}`}>
                      {task.title}
                    </h3>

                    <span
                      className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                        isCompleted
                          ? "bg-accent-neon/20 text-accent-neon"
                          : isOverdue
                          ? "bg-red-500/20 text-red-400"
                          : task.status === "APPROVED"
                          ? "bg-accent-neon/15 text-accent-neon"
                          : "bg-bg-elevated text-text-muted"
                      }`}
                    >
                      {task.status}
                    </span>
                  </div>

                  {/* Metadata */}
                  <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-text-secondary">
                    <div className="flex items-center gap-1">
                      <User size={12} />
                      <span>Assignee: <strong className="text-text-primary">{task.assignee_name || "Unassigned"}</strong></span>
                    </div>
                    {task.assignee_email && (
                      <span className="text-text-muted">&bull; {task.assignee_email}</span>
                    )}
                    <div className="flex items-center gap-1">
                      <Calendar size={12} />
                      <span>Deadline: <strong className={isOverdue ? "text-red-400" : "text-accent-orange"}>{task.deadline || "TBD"}</strong></span>
                    </div>
                  </div>

                  {/* Evidence Quote */}
                  {task.evidence_quote && (
                    <div className="text-[11px] text-text-muted italic border-l-2 border-accent-orange/60 pl-2">
                      &ldquo;{task.evidence_quote}&rdquo;
                    </div>
                  )}
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                  {task.meeting_id && (
                    <Link
                      href={`/meetings/${task.meeting_id}`}
                      className="p-1.5 text-xs text-text-muted hover:text-text-primary rounded hover:bg-bg-elevated"
                      title="View Source Meeting"
                    >
                      <ExternalLink size={14} />
                    </Link>
                  )}

                  {!isCompleted && (
                    <button
                      onClick={() => handleMarkComplete(task.id)}
                      disabled={completingId === task.id}
                      className="px-3 py-1 text-xs font-semibold bg-bg-elevated border border-border-subtle hover:border-accent-neon text-accent-neon rounded flex items-center gap-1 transition-colors"
                      title="Mark task completed and cancel future reminders"
                    >
                      <CheckCircle2 size={13} />
                      <span>{completingId === task.id ? "Updating..." : "Mark Complete"}</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(task.id)}
                    className="p-1.5 text-xs text-text-muted hover:text-red-400 rounded hover:bg-bg-elevated transition-colors"
                    title="Delete task"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
