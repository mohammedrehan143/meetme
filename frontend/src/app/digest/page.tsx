"use client";

import React, { useEffect, useState } from "react";
import { 
  FileText, 
  Mail, 
  Send, 
  RotateCw, 
  User, 
  Calendar, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  Check, 
  Eye, 
  Sparkles,
  ShieldCheck,
  ListTodo
} from "lucide-react";
import { api } from "@/lib/api";
import { WeeklyDigest, TeamMember } from "@/lib/types";

export default function WeeklyDigestPage() {
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<string>("");
  const [digests, setDigests] = useState<WeeklyDigest[]>([]);
  const [activeDigest, setActiveDigest] = useState<WeeklyDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedMemberId) {
      loadDigestsForMember(selectedMemberId);
    }
  }, [selectedMemberId]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [teamData, allDigests] = await Promise.all([
        api.getTeam(),
        api.getDigests()
      ]);
      setTeam(teamData || []);
      setDigests(allDigests || []);

      if (teamData && teamData.length > 0) {
        setSelectedMemberId(teamData[0].id);
      }
      if (allDigests && allDigests.length > 0) {
        setActiveDigest(allDigests[0]);
      }
    } catch (err) {
      console.error("Failed to load initial digest data:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadDigestsForMember = async (memberId: string) => {
    try {
      const memberDigests = await api.getDigests(memberId);
      setDigests(memberDigests || []);
      if (memberDigests && memberDigests.length > 0) {
        setActiveDigest(memberDigests[0]);
      } else {
        setActiveDigest(null);
      }
    } catch (err) {
      console.error("Failed to load digests for member:", err);
    }
  };

  const handleGenerateDigest = async () => {
    setGenerating(true);
    try {
      const result = await api.generateDigests({
        member_id: selectedMemberId || undefined,
        period_days: 7,
        dispatch_email_now: false
      });
      alert(`Weekly digest generated successfully! (${result.generated_count || 1} digest created)`);
      if (selectedMemberId) {
        await loadDigestsForMember(selectedMemberId);
      } else {
        await loadInitialData();
      }
    } catch (err: any) {
      alert(`Digest generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleSendDigestEmail = async (digestId: string) => {
    const currentMember = team.find(m => m.id === selectedMemberId);
    const targetEmail = prompt(
      "Confirm destination email address for this personalized weekly digest:",
      currentMember?.email || ""
    );
    if (!targetEmail) return;

    setSending(true);
    try {
      await api.sendDigest(digestId, targetEmail);
      alert(`Weekly digest dispatched successfully to ${targetEmail}!`);
      if (selectedMemberId) {
        await loadDigestsForMember(selectedMemberId);
      }
    } catch (err: any) {
      alert(`Dispatch failed: ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const selectedMember = team.find(m => m.id === selectedMemberId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText size={20} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Personalized Weekly Digest</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Automated member-specific intelligence report dispatched every Monday at 9:00 AM.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerateDigest}
            disabled={generating}
            className="px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Sparkles size={13} />
            <span>{generating ? "Generating..." : "Generate Fresh Digest"}</span>
          </button>

          <button
            onClick={loadInitialData}
            disabled={loading}
            className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary text-xs"
            title="Refresh"
          >
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Privacy Isolation Notice */}
      <div className="p-3 bg-bg-card border border-border-subtle rounded flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 text-accent-neon">
          <ShieldCheck size={16} />
          <span>Strict Member Privacy Guarantee</span>
        </div>
        <span className="text-text-muted text-[11px]">
          Digests only contain tasks and decisions explicitly assigned to or involving the recipient.
        </span>
      </div>

      {/* Member Selector Bar */}
      <div className="p-4 bg-bg-card rounded-lg border border-border-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <User size={16} className="text-accent-orange" />
          <div>
            <span className="text-xs font-mono text-text-muted uppercase tracking-wider block">
              Viewing Digest For Member
            </span>
            <select
              value={selectedMemberId}
              onChange={(e) => setSelectedMemberId(e.target.value)}
              className="bg-bg-elevated border border-border-subtle rounded px-3 py-1 text-sm font-semibold text-text-primary focus:outline-none focus:border-accent-orange mt-0.5"
            >
              {team.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.email}) - {m.role}
                </option>
              ))}
            </select>
          </div>
        </div>

        {activeDigest && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleSendDigestEmail(activeDigest.id)}
              disabled={sending}
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange/20 border border-accent-orange/40 text-accent-orange hover:bg-accent-orange hover:text-black flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Send size={13} />
              <span>{activeDigest.status === "SENT" ? "Re-send Digest Email" : "Send Digest via Brevo"}</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Digest View */}
      {activeDigest ? (
        <div className="space-y-6">
          {/* KPI Cards Row */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-4 bg-bg-card rounded border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono text-text-muted uppercase">Assigned</span>
              <div className="text-xl font-bold font-mono text-text-primary">
                {activeDigest.metrics?.assigned_count ?? 0}
              </div>
            </div>

            <div className="p-4 bg-bg-card rounded border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono text-accent-neon uppercase">Completed</span>
              <div className="text-xl font-bold font-mono text-accent-neon">
                {activeDigest.metrics?.completed_count ?? 0}
              </div>
            </div>

            <div className="p-4 bg-bg-card rounded border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono text-blue-400 uppercase">In Progress</span>
              <div className="text-xl font-bold font-mono text-blue-400">
                {activeDigest.metrics?.in_progress_count ?? 0}
              </div>
            </div>

            <div className="p-4 bg-bg-card rounded border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono text-red-400 uppercase">Overdue</span>
              <div className="text-xl font-bold font-mono text-red-400">
                {activeDigest.metrics?.overdue_count ?? 0}
              </div>
            </div>

            <div className="p-4 bg-bg-card rounded border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono text-accent-orange uppercase">Upcoming</span>
              <div className="text-xl font-bold font-mono text-accent-orange">
                {activeDigest.metrics?.upcoming_deadlines_count ?? 0}
              </div>
            </div>
          </div>

          {/* Digest Content Preview */}
          <div className="bg-bg-card rounded-lg border border-border-subtle p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border-subtle text-xs font-mono">
              <div>
                <strong className="text-text-primary font-bold">Period: </strong>
                <span className="text-text-secondary">{activeDigest.period_start} to {activeDigest.period_end}</span>
              </div>
              <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                activeDigest.status === "SENT" ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-secondary"
              }`}>
                {activeDigest.status} {activeDigest.email_sent_at && `(${new Date(activeDigest.email_sent_at).toLocaleDateString()})`}
              </span>
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider font-mono flex items-center gap-1.5">
                <ListTodo size={14} className="text-accent-orange" />
                <span>Assigned Tasks &amp; Commitments Breakdown</span>
              </h3>

              <div className="divide-y divide-border-subtle rounded border border-border-subtle overflow-hidden">
                {(!activeDigest.tasks_summary || activeDigest.tasks_summary.length === 0) ? (
                  <div className="p-8 text-center text-xs text-text-muted">
                    No active tasks assigned to this member during this reporting period.
                  </div>
                ) : (
                  activeDigest.tasks_summary.map((task, idx) => (
                    <div key={idx} className="p-3 hover:bg-bg-elevated/40 flex items-center justify-between gap-4 text-xs">
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                          task.priority === "HIGH" || task.priority === "URGENT" 
                            ? "bg-accent-orange/20 text-accent-orange" 
                            : "bg-bg-elevated text-text-secondary"
                        }`}>
                          {task.priority}
                        </span>
                        <span className="font-semibold text-text-primary">{task.title}</span>
                      </div>

                      <div className="flex items-center gap-3 font-mono text-[11px] text-text-muted shrink-0">
                        <span>Due: {task.deadline || "TBD"}</span>
                        <span className={`px-1.5 py-0.5 rounded ${
                          task.status === "COMPLETED" ? "bg-accent-neon/20 text-accent-neon" :
                          task.status === "OVERDUE" ? "bg-red-500/20 text-red-400" :
                          "bg-bg-elevated text-text-secondary"
                        }`}>
                          {task.status}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-16 text-center bg-bg-card rounded-lg border border-border-subtle space-y-3">
          <FileText size={32} className="mx-auto text-text-muted" />
          <h3 className="text-sm font-bold text-text-primary">No Digest Generated Yet</h3>
          <p className="text-xs text-text-secondary max-w-sm mx-auto">
            Click &quot;Generate Fresh Digest&quot; above to compile this week&apos;s personalized status report for {selectedMember?.full_name || "the selected member"}.
          </p>
        </div>
      )}

      {/* Digest History Table */}
      <div className="rounded-lg bg-bg-card border border-border-subtle overflow-hidden">
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono">
          <span className="font-semibold text-text-primary uppercase tracking-wider">
            Digest Archive &amp; Dispatch History ({digests.length})
          </span>
          <span className="text-text-muted">Weekly Dispatch Records</span>
        </div>

        <div className="divide-y divide-border-subtle">
          {digests.length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted">
              No historical digests on record.
            </div>
          ) : (
            digests.map((d) => (
              <div 
                key={d.id} 
                onClick={() => setActiveDigest(d)}
                className={`p-3.5 hover:bg-bg-elevated/40 cursor-pointer transition-colors flex items-center justify-between text-xs ${
                  activeDigest?.id === d.id ? "bg-accent-orange/5 border-l-2 border-accent-orange" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-text-primary">{d.member_name}</span>
                  <span className="text-text-muted font-mono text-[11px]">
                    {d.period_start} &rarr; {d.period_end}
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono text-[11px]">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    d.status === "SENT" ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-secondary"
                  }`}>
                    {d.status}
                  </span>
                  <span className="text-text-muted">
                    {new Date(d.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
