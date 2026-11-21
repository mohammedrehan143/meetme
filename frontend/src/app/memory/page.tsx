"use client";

import React, { useEffect, useState } from "react";
import { 
  Brain, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  RotateCw, 
  Search, 
  Filter, 
  ArrowRight, 
  Check, 
  X, 
  Edit3, 
  Layers, 
  Calendar, 
  User, 
  GitCompare, 
  FileText,
  History,
  AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { Decision, Commitment, DecisionConflict } from "@/lib/types";

export default function MemoryDashboardPage() {
  const [activeTab, setActiveTab] = useState<"decisions" | "conflicts" | "commitments" | "timeline">("conflicts");
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [conflicts, setConflicts] = useState<DecisionConflict[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [decisionCategory, setDecisionCategory] = useState<string>("ALL");
  const [decisionStatus, setDecisionStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [commitmentAssignee, setCommitmentAssignee] = useState<string>("ALL");
  const [commitmentStatus, setCommitmentStatus] = useState<string>("ALL");

  // Conflict Resolution Modal
  const [resolvingConflict, setResolvingConflict] = useState<DecisionConflict | null>(null);
  const [editResolutionNotes, setEditResolutionNotes] = useState<string>("");
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);

  useEffect(() => {
    loadAllMemoryData();
  }, []);

  const loadAllMemoryData = async () => {
    setLoading(true);
    try {
      const [decData, comData, confData] = await Promise.all([
        api.getDecisions(),
        api.getCommitments(),
        api.getConflicts()
      ]);
      setDecisions(decData || []);
      setCommitments(comData || []);
      setConflicts(confData || []);
    } catch (err) {
      console.error("Failed to load memory data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolveConflict = async (conflictId: string, action: string, notes?: string) => {
    setActionInProgress(true);
    try {
      await api.resolveConflict(conflictId, action, notes || editResolutionNotes);
      setResolvingConflict(null);
      setEditResolutionNotes("");
      await loadAllMemoryData();
    } catch (err: any) {
      alert(`Conflict resolution failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  // Filtered lists
  const filteredDecisions = decisions.filter(d => {
    if (decisionCategory !== "ALL" && d.category !== decisionCategory) return false;
    if (decisionStatus !== "ALL" && d.status !== decisionStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (d.title || "").toLowerCase().includes(q);
      const matchDesc = (d.description || "").toLowerCase().includes(q);
      const matchBy = (d.decided_by || "").toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchBy) return false;
    }
    return true;
  });

  const uniqueAssignees = Array.from(new Set(commitments.map(c => c.assignee_name).filter(Boolean))) as string[];

  const filteredCommitments = commitments.filter(c => {
    if (commitmentAssignee !== "ALL" && c.assignee_name !== commitmentAssignee) return false;
    if (commitmentStatus !== "ALL" && c.status !== commitmentStatus) return false;
    return true;
  });

  const pendingConflictsCount = conflicts.filter(c => c.status === "DETECTED" || c.status === "UNRESOLVED").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Brain size={20} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Cross-Meeting Memory Engine</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Persistent intelligence across meetings: decision history, conflict detection, and commitment tracking.
          </p>
        </div>

        <button
          onClick={loadAllMemoryData}
          disabled={loading}
          className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary flex items-center gap-1.5 text-xs font-mono"
          title="Refresh memory store"
        >
          <RotateCw size={13} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border-subtle text-xs">
        <button
          onClick={() => setActiveTab("conflicts")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "conflicts"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <AlertTriangle size={14} />
          <span>Conflict Centre</span>
          {pendingConflictsCount > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-accent-orange text-black ml-1">
              {pendingConflictsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("decisions")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "decisions"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <CheckCircle2 size={14} />
          <span>Decision History ({decisions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("commitments")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "commitments"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Clock size={14} />
          <span>Commitment Tracker ({commitments.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === "timeline"
              ? "border-accent-orange text-accent-orange"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <History size={14} />
          <span>Project Memory Timeline</span>
        </button>
      </div>

      {/* TAB 1: CONFLICT CENTRE */}
      {activeTab === "conflicts" && (
        <div className="space-y-4">
          <div className="p-3 bg-bg-card rounded border border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCompare size={16} className="text-accent-orange" />
              <span className="text-xs font-semibold text-text-primary uppercase font-mono tracking-wider">
                Active Contradictions &amp; Technical Reversals
              </span>
            </div>
            <span className="text-[11px] font-mono text-text-muted">
              {pendingConflictsCount} pending human resolution
            </span>
          </div>

          {conflicts.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted bg-bg-card rounded border border-border-subtle">
              No decision conflicts detected across meetings. Decisions are currently consistent.
            </div>
          ) : (
            <div className="space-y-4">
              {conflicts.map((conf) => {
                const isPending = conf.status === "DETECTED" || conf.status === "UNRESOLVED";
                return (
                  <div 
                    key={conf.id} 
                    className={`p-5 rounded-lg border bg-bg-card transition-all ${
                      isPending ? "border-accent-orange/40 shadow-sm" : "border-border-subtle opacity-80"
                    }`}
                  >
                    {/* Header info */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border-subtle">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-accent-orange/20 text-accent-orange border border-accent-orange/30">
                          {conf.conflict_type}
                        </span>
                        <span className="text-xs font-mono text-text-secondary">
                          Confidence: <strong className="text-accent-neon">{Math.round((conf.confidence || 0.85) * 100)}%</strong>
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                        conf.status === "ACCEPTED_NEW" ? "bg-accent-neon/20 text-accent-neon" :
                        conf.status === "RETAINED_PREVIOUS" ? "bg-yellow-500/20 text-yellow-300" :
                        conf.status === "DETECTED" ? "bg-red-500/20 text-red-400" : "bg-bg-elevated text-text-secondary"
                      }`}>
                        {conf.status}
                      </span>
                    </div>

                    {/* Side-by-side comparison cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
                      {/* Previous Decision */}
                      <div className="p-3.5 bg-bg-elevated/50 rounded border border-border-subtle flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between text-[11px] font-mono text-text-muted mb-1.5">
                            <span className="uppercase tracking-wider font-semibold text-text-secondary">Previous Decision</span>
                            <span>{conf.previous_decision?.date || "Historical"}</span>
                          </div>
                          <h4 className="text-xs font-bold text-text-primary">
                            {conf.previous_decision?.title || "Previous Specification"}
                          </h4>
                          <p className="text-xs text-text-secondary mt-1">
                            {conf.previous_decision?.description}
                          </p>
                        </div>
                        {conf.previous_decision?.source_transcript_quote && (
                          <div className="mt-3 p-2 bg-[#090909] border-l-2 border-text-muted rounded-r text-[10px] text-text-muted italic">
                            &ldquo;{conf.previous_decision.source_transcript_quote}&rdquo;
                          </div>
                        )}
                      </div>

                      {/* New Conflicting Decision */}
                      <div className="p-3.5 bg-accent-orange/5 rounded border border-accent-orange/30 flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between text-[11px] font-mono text-accent-orange mb-1.5">
                            <span className="uppercase tracking-wider font-semibold">New Proposed Decision</span>
                            <span>{conf.new_decision?.date || "Current Meeting"}</span>
                          </div>
                          <h4 className="text-xs font-bold text-text-primary">
                            {conf.new_decision?.title || "New Proposed Direction"}
                          </h4>
                          <p className="text-xs text-text-secondary mt-1">
                            {conf.new_decision?.description}
                          </p>
                        </div>
                        {conf.new_decision?.source_transcript_quote && (
                          <div className="mt-3 p-2 bg-[#090909] border-l-2 border-accent-orange rounded-r text-[10px] text-text-muted italic">
                            &ldquo;{conf.new_decision.source_transcript_quote}&rdquo;
                          </div>
                        )}
                      </div>
                    </div>

                    {/* AI Explanation & Suggested Resolution */}
                    <div className="p-3 bg-bg-elevated rounded border border-border-subtle space-y-1.5 text-xs">
                      <div className="flex items-center gap-1.5 text-accent-orange font-semibold font-mono text-[11px]">
                        <Brain size={13} />
                        <span>AI Analysis &amp; Contradiction Rationale</span>
                      </div>
                      <p className="text-text-primary text-xs leading-relaxed">
                        {conf.explanation}
                      </p>
                      {conf.suggested_resolution && (
                        <div className="text-[11px] text-text-secondary pt-1 border-t border-border-subtle font-mono">
                          <strong className="text-accent-neon">Recommendation: </strong>
                          {conf.suggested_resolution}
                        </div>
                      )}
                    </div>

                    {/* Action Buttons for Pending Conflict */}
                    {isPending && (
                      <div className="flex flex-wrap items-center justify-end gap-2 pt-4 border-t border-border-subtle mt-4">
                        <button
                          onClick={() => handleResolveConflict(conf.id, "RETAIN_PREVIOUS")}
                          disabled={actionInProgress}
                          className="px-3 py-1.5 text-xs font-semibold rounded bg-bg-elevated border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          title="Reject the new decision and keep the previous historical decision active"
                        >
                          <X size={12} className="text-red-400" />
                          <span>Retain Previous Decision</span>
                        </button>

                        <button
                          onClick={() => {
                            setResolvingConflict(conf);
                            setEditResolutionNotes(conf.suggested_resolution || "");
                          }}
                          disabled={actionInProgress}
                          className="px-3 py-1.5 text-xs font-semibold rounded bg-bg-elevated border border-border-subtle hover:border-border-strong text-text-primary flex items-center gap-1.5 transition-colors"
                        >
                          <Edit3 size={12} className="text-accent-orange" />
                          <span>Edit Resolution</span>
                        </button>

                        <button
                          onClick={() => handleResolveConflict(conf.id, "ACCEPT_NEW")}
                          disabled={actionInProgress}
                          className="px-4 py-1.5 text-xs font-semibold rounded bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          title="Accept new decision, automatically superseding previous decision with audit trail"
                        >
                          <Check size={13} />
                          <span>Accept New (Supersede Previous)</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: DECISION HISTORY */}
      {activeTab === "decisions" && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="p-3 bg-bg-card rounded border border-border-subtle flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs">
            {/* Search */}
            <div className="relative flex-1">
              <Search size={14} className="absolute left-2.5 top-2.5 text-text-muted" />
              <input
                type="text"
                placeholder="Search decisions by title, keyword, or decision maker..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-orange"
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex items-center gap-2">
              <select
                value={decisionCategory}
                onChange={(e) => setDecisionCategory(e.target.value)}
                className="bg-bg-elevated border border-border-subtle rounded px-2.5 py-1.5 text-text-primary font-mono"
              >
                <option value="ALL">All Categories</option>
                <option value="TECHNICAL">TECHNICAL</option>
                <option value="PRODUCT">PRODUCT</option>
                <option value="ORGANIZATIONAL">ORGANIZATIONAL</option>
                <option value="REQUIREMENT">REQUIREMENT</option>
              </select>

              <select
                value={decisionStatus}
                onChange={(e) => setDecisionStatus(e.target.value)}
                className="bg-bg-elevated border border-border-subtle rounded px-2.5 py-1.5 text-text-primary font-mono"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="SUPERSEDED">SUPERSEDED</option>
                <option value="PROPOSED">PROPOSED</option>
              </select>
            </div>
          </div>

          {/* Decisions List */}
          <div className="rounded bg-bg-card border border-border-subtle divide-y divide-border-subtle">
            {filteredDecisions.length === 0 ? (
              <div className="p-12 text-center text-xs text-text-muted">
                No decisions found matching the specified filters.
              </div>
            ) : (
              filteredDecisions.map((dec) => (
                <div key={dec.id} className="p-4 hover:bg-bg-elevated/40 transition-colors space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold rounded bg-bg-elevated text-text-secondary border border-border-subtle">
                        {dec.category}
                      </span>
                      <h3 className="text-sm font-semibold text-text-primary">{dec.title}</h3>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded ${
                        dec.status === "ACTIVE" ? "bg-accent-neon/20 text-accent-neon" :
                        dec.status === "SUPERSEDED" ? "bg-text-muted/20 text-text-muted line-through" :
                        "bg-bg-elevated text-text-secondary"
                      }`}>
                        {dec.status}
                      </span>
                      <span className="text-[10px] font-mono text-accent-neon">
                        {Math.round((dec.confidence || 0.9) * 100)}% conf
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-text-secondary">{dec.description}</p>

                  <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-text-muted pt-1">
                    {dec.decided_by && (
                      <div className="flex items-center gap-1">
                        <User size={11} />
                        <span>Decided by: <strong className="text-text-primary">{dec.decided_by}</strong></span>
                      </div>
                    )}
                    {dec.date && (
                      <div className="flex items-center gap-1">
                        <Calendar size={11} />
                        <span>Date: <strong>{dec.date}</strong></span>
                      </div>
                    )}
                  </div>

                  {dec.source_transcript_quote && (
                    <div className="text-[11px] text-text-muted italic bg-bg-elevated/60 border-l-2 border-accent-orange px-2.5 py-1.5 rounded-r mt-2">
                      &ldquo;{dec.source_transcript_quote}&rdquo;
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 3: COMMITMENT TRACKER */}
      {activeTab === "commitments" && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="p-3 bg-bg-card rounded border border-border-subtle flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs">
            <span className="font-semibold text-text-primary uppercase tracking-wider font-mono">
              Promises &amp; Commitments Across Meetings
            </span>

            <div className="flex items-center gap-2">
              <select
                value={commitmentAssignee}
                onChange={(e) => setCommitmentAssignee(e.target.value)}
                className="bg-bg-elevated border border-border-subtle rounded px-2.5 py-1.5 text-text-primary font-mono text-xs"
              >
                <option value="ALL">All Assignees</option>
                {uniqueAssignees.map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>

              <select
                value={commitmentStatus}
                onChange={(e) => setCommitmentStatus(e.target.value)}
                className="bg-bg-elevated border border-border-subtle rounded px-2.5 py-1.5 text-text-primary font-mono text-xs"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">OPEN</option>
                <option value="DELAYED">DELAYED</option>
                <option value="OVERDUE">OVERDUE</option>
                <option value="COMPLETED">COMPLETED</option>
              </select>
            </div>
          </div>

          {/* Commitments List */}
          <div className="rounded bg-bg-card border border-border-subtle divide-y divide-border-subtle">
            {filteredCommitments.length === 0 ? (
              <div className="p-12 text-center text-xs text-text-muted">
                No commitments recorded across meetings.
              </div>
            ) : (
              filteredCommitments.map((com) => {
                const isDelayed = (com.delay_count || 0) > 0 || com.status === "DELAYED";
                return (
                  <div key={com.id} className="p-4 hover:bg-bg-elevated/40 transition-colors space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-text-primary">
                          {com.assignee_name || "Unassigned"}
                        </span>
                        <ArrowRight size={12} className="text-text-muted" />
                        <h4 className="text-xs font-semibold text-text-primary">{com.description}</h4>
                      </div>

                      <div className="flex items-center gap-2">
                        {isDelayed && (
                          <span className="px-2 py-0.5 text-[9px] font-mono font-bold rounded bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                            DELAYED {com.delay_count > 0 ? `(${com.delay_count}x)` : ""}
                          </span>
                        )}

                        <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded ${
                          com.status === "COMPLETED" ? "bg-accent-neon/20 text-accent-neon" :
                          com.status === "OVERDUE" ? "bg-red-500/20 text-red-400" :
                          com.status === "DELAYED" ? "bg-yellow-500/20 text-yellow-300" :
                          "bg-accent-orange/20 text-accent-orange"
                        }`}>
                          {com.status}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-text-secondary pt-1">
                      <div>
                        Deadline: <strong className="text-accent-orange">{com.deadline || "TBD"}</strong>
                        {com.original_deadline && com.original_deadline !== com.deadline && (
                          <span className="text-text-muted ml-1 line-through">
                            (was {com.original_deadline})
                          </span>
                        )}
                      </div>
                      <div>
                        Confidence: <strong className="text-accent-neon">{Math.round((com.confidence || 0.9) * 100)}%</strong>
                      </div>
                    </div>

                    {com.unresolved_blockers && (
                      <div className="text-[11px] text-red-400 bg-red-500/10 border border-red-500/20 px-2.5 py-1.5 rounded flex items-center gap-1.5">
                        <AlertCircle size={12} className="shrink-0" />
                        <span>Blocker: {com.unresolved_blockers}</span>
                      </div>
                    )}

                    {com.completion_evidence && (
                      <div className="text-[11px] text-accent-neon bg-accent-neon/10 border border-accent-neon/20 px-2.5 py-1.5 rounded flex items-center gap-1.5">
                        <CheckCircle2 size={12} className="shrink-0" />
                        <span>Completion Evidence: {com.completion_evidence}</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* TAB 4: PROJECT MEMORY TIMELINE */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          <div className="p-3 bg-bg-card rounded border border-border-subtle flex items-center justify-between">
            <span className="font-semibold text-text-primary uppercase tracking-wider font-mono text-xs">
              Chronological Project Evolution &amp; Decision Stream
            </span>
            <span className="text-text-muted font-mono text-[11px]">
              {decisions.length + commitments.length} Total Memory Anchors
            </span>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border-subtle">
            {decisions.slice(0, 15).map((dec, idx) => (
              <div key={dec.id} className="relative group">
                <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-accent-orange ring-4 ring-bg-secondary" />
                <div className="p-4 bg-bg-card rounded border border-border-subtle group-hover:border-border-strong transition-colors space-y-1">
                  <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
                    <span className="text-accent-orange font-bold uppercase">{dec.category} DECISION</span>
                    <span>{dec.date || "Recorded Meeting"}</span>
                  </div>
                  <h4 className="text-xs font-bold text-text-primary">{dec.title}</h4>
                  <p className="text-xs text-text-secondary">{dec.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Resolution Modal */}
      {resolvingConflict && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-bg-card border border-border-subtle rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider font-mono">
                Custom Resolution For Decision Conflict
              </h3>
              <button
                onClick={() => setResolvingConflict(null)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-text-secondary block mb-1 font-semibold">Resolution Audit Notes / Custom Decision</label>
                <textarea
                  rows={4}
                  value={editResolutionNotes}
                  onChange={(e) => setEditResolutionNotes(e.target.value)}
                  placeholder="Enter manual resolution notes, consensus statement, or modified architecture decision..."
                  className="w-full bg-bg-elevated border border-border-subtle rounded p-2.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono text-xs"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-border-subtle">
              <button
                onClick={() => setResolvingConflict(null)}
                className="px-3 py-1.5 rounded text-xs text-text-secondary hover:text-text-primary bg-bg-elevated"
              >
                Cancel
              </button>
              <button
                onClick={() => handleResolveConflict(resolvingConflict.id, "MANUAL_EDIT", editResolutionNotes)}
                disabled={actionInProgress}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover"
              >
                Submit Manual Resolution
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
