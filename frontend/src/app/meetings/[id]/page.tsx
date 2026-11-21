"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  Calendar, 
  Clock, 
  ShieldCheck, 
  CheckSquare, 
  Sparkles, 
  MessageSquare,
  ArrowRight
} from "lucide-react";
import { api } from "@/lib/api";
import { Meeting } from "@/lib/types";

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"TRANSCRIPT" | "TASKS" | "DECISIONS">("TRANSCRIPT");

  useEffect(() => {
    if (id) {
      loadMeeting();
    }
  }, [id]);

  const loadMeeting = async () => {
    setLoading(true);
    try {
      const data = await api.getMeeting(id);
      setMeeting(data);
    } catch (err) {
      console.error("Failed to load meeting details:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-text-muted">
        Loading meeting intelligence report...
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="p-12 text-center text-xs text-text-muted space-y-3">
        <p>Meeting not found.</p>
        <button
          onClick={() => router.push("/meetings")}
          className="px-3 py-1.5 bg-bg-card border border-border-subtle rounded text-xs text-text-primary"
        >
          Return to Meeting Archives
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & Title */}
      <div className="space-y-3 pb-3 border-b border-border-subtle">
        <Link
          href="/meetings"
          className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary font-mono transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Meetings</span>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-text-primary">{meeting.title}</h1>
              <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded ${
                meeting.status === "COMPLETED" ? "bg-accent-neon/20 text-accent-neon" : "bg-accent-orange/20 text-accent-orange"
              }`}>
                {meeting.status}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-text-muted font-mono mt-1">
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                {meeting.date ? new Date(meeting.date).toLocaleString() : "Recent"}
              </span>
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {Math.round(meeting.duration_seconds / 60)} minutes
              </span>
              <span>Mode: {meeting.recording_mode}</span>
            </div>
          </div>

          <Link
            href="/approvals"
            className="px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 self-start sm:self-auto"
          >
            <span>Review Approvals Gate</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>

      {/* Executive Summary Card */}
      {meeting.summary && (
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-accent-neon" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
              Executive AI Synthesis
            </h3>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed font-sans">
            {meeting.summary}
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border-subtle text-xs">
        <button
          onClick={() => setActiveTab("TRANSCRIPT")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "TRANSCRIPT"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <MessageSquare size={13} />
          <span>Full Transcript ({meeting.transcripts?.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab("TASKS")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "TASKS"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <CheckSquare size={13} />
          <span>Extracted Tasks ({meeting.tasks?.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab("DECISIONS")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "DECISIONS"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Sparkles size={13} />
          <span>Decisions Log ({meeting.key_decisions?.length || 0})</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "TRANSCRIPT" && (
        <div className="rounded bg-bg-card border border-border-subtle divide-y divide-border-subtle">
          {(meeting.transcripts || []).length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted">No transcript segments recorded.</div>
          ) : (
            (meeting.transcripts || []).map((seg) => (
              <div key={seg.id} className="p-3.5 hover:bg-bg-elevated/30 transition-colors text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-primary">{seg.speaker_name}</span>
                    <span className="text-[10px] font-mono text-text-muted">{seg.timestamp_formatted}</span>
                  </div>
                  <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                    seg.classification === "TASK" ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30" :
                    seg.classification === "DECISION" ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30" :
                    seg.classification === "BLOCKER" ? "bg-red-500/20 text-red-400 border border-red-500/30" :
                    "bg-bg-card text-text-muted border border-border-subtle"
                  }`}>
                    {seg.classification}
                  </span>
                </div>
                <p className="text-text-primary leading-relaxed text-xs">{seg.text}</p>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "TASKS" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(meeting.tasks || []).length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted col-span-2">No tasks extracted.</div>
          ) : (
            (meeting.tasks || []).map((task) => (
              <div key={task.id} className="p-4 rounded bg-bg-card border border-border-subtle space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text-primary">{task.title}</span>
                  <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                    task.priority === "URGENT" || task.priority === "HIGH" ? "bg-accent-orange/20 text-accent-orange" : "bg-bg-elevated text-text-secondary"
                  }`}>
                    {task.priority}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-text-secondary space-y-0.5">
                  <div>Assignee: <strong className="text-text-primary">{task.assignee_name || "Unassigned"}</strong></div>
                  <div>Email: <strong className="text-text-primary">{task.assignee_email || "N/A"}</strong></div>
                  <div>Deadline: <strong className="text-accent-orange">{task.deadline || "TBD"}</strong></div>
                </div>
                {task.evidence_quote && (
                  <p className="text-[11px] text-text-muted italic border-l-2 border-accent-orange pl-2">
                    &ldquo;{task.evidence_quote}&rdquo;
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "DECISIONS" && (
        <div className="space-y-3">
          {(meeting.key_decisions || []).length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted">No decisions recorded.</div>
          ) : (
            (meeting.key_decisions || []).map((dec: any, idx: number) => (
              <div key={idx} className="p-4 rounded bg-bg-card border border-border-subtle space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-text-primary">{dec.title}</h4>
                  <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-accent-neon/20 text-accent-neon">
                    {dec.status || "APPROVED"}
                  </span>
                </div>
                <p className="text-text-secondary text-xs">{dec.summary}</p>
                {dec.evidence && (
                  <p className="text-[11px] text-text-muted italic pt-1">&ldquo;{dec.evidence}&rdquo;</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
