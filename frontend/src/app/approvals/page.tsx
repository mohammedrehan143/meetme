"use client";

import React, { useEffect, useState } from "react";
import { 
  ShieldAlert, 
  Check, 
  X, 
  Edit3, 
  Mail, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Layers, 
  RotateCw,
  Eye,
  Calendar,
  UserCheck,
  Send
} from "lucide-react";
import { api } from "@/lib/api";
import { Approval } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("PENDING");
  
  // Destination emails keyed by approval ID
  const [destinationEmails, setDestinationEmails] = useState<Record<string, string>>({});

  // Modal for Edit & Approve
  const [editingApproval, setEditingApproval] = useState<Approval | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAssigneeName, setEditAssigneeName] = useState("");
  const [editAssigneeEmail, setEditAssigneeEmail] = useState("");
  const [editDeadline, setEditDeadline] = useState("");
  const [editPriority, setEditPriority] = useState<string>("MEDIUM");
  const [editNotes, setEditNotes] = useState("");
  const [previewEmailModal, setPreviewEmailModal] = useState<any | null>(null);

  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    loadApprovals();
  }, [statusFilter]);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const data = await api.getApprovals(statusFilter === "ALL" ? undefined : statusFilter);
      setApprovals(data);
      setSelectedIds([]);
      // Prepopulate destination emails map
      const initialMap: Record<string, string> = {};
      data.forEach((app) => {
        const p = app.proposed_payload || {};
        const email = p.assignee_email || app.approved_recipient;
        if (email) initialMap[app.id] = email;
      });
      setDestinationEmails((prev) => ({ ...initialMap, ...prev }));
    } catch (err) {
      console.error("Failed to load approvals:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(approvals.filter((a) => a.status === "PENDING").map((a) => a.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleApproveSingle = async (app: Approval) => {
    const p = app.proposed_payload || {};
    let targetEmail = (destinationEmails[app.id] || p.assignee_email || "").trim();

    // If destination email is empty, prompt the user so it is NEVER silently skipped!
    if (!targetEmail) {
      const entered = window.prompt(
        `Please specify the destination email address to receive this task assignment:\n"${p.title || 'Task'}"`,
        "25ug1byai034@bmsit.in"
      );
      if (entered === null) {
        // User cancelled, abort approval
        return;
      }
      targetEmail = entered.trim();
      if (targetEmail) {
        setDestinationEmails((prev) => ({ ...prev, [app.id]: targetEmail }));
      }
    }

    setExecuting(true);
    try {
      const customPayload = {
        ...p,
        assignee_email: targetEmail || undefined,
      };
      await api.approveAction(app.id, customPayload, "Approved with verified destination email");
      await loadApprovals();
    } catch (err: any) {
      alert(`Approval execution failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleSendEmailNow = async (app: Approval) => {
    const p = app.proposed_payload || {};
    let targetEmail = (destinationEmails[app.id] || p.assignee_email || app.approved_recipient || "").trim();

    if (!targetEmail) {
      const entered = window.prompt(
        `Enter destination email address to dispatch task assignment:\n"${p.title || 'Task'}"`,
        "25ug1byai034@bmsit.in"
      );
      if (!entered || !entered.trim()) return;
      targetEmail = entered.trim();
      setDestinationEmails((prev) => ({ ...prev, [app.id]: targetEmail }));
    }

    setExecuting(true);
    try {
      await api.dispatchApprovalEmail(app.id, targetEmail, p.assignee_name);
      alert(`Assignment email successfully dispatched to ${targetEmail} via Gmail SMTP!`);
      await loadApprovals();
    } catch (err: any) {
      alert(`Email dispatch failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleApproveBatch = async () => {
    if (selectedIds.length === 0) return;
    setExecuting(true);
    try {
      await api.batchApprove(selectedIds);
      await loadApprovals();
    } catch (err: any) {
      alert(`Batch execution failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleRejectSingle = async (approvalId: string) => {
    const reason = prompt("Optional rejection reason:") || undefined;
    setExecuting(true);
    try {
      await api.rejectAction(approvalId, reason);
      await loadApprovals();
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const openEditModal = (approval: Approval) => {
    const p = approval.proposed_payload || {};
    setEditingApproval(approval);
    setEditTitle(p.title || "");
    setEditAssigneeName(p.assignee_name || "");
    setEditAssigneeEmail(destinationEmails[approval.id] || p.assignee_email || approval.approved_recipient || "");
    setEditDeadline(p.deadline || "");
    setEditPriority(p.priority || "MEDIUM");
    setEditNotes("");
  };

  const handleSaveAndApprove = async () => {
    if (!editingApproval) return;
    setExecuting(true);
    try {
      const customPayload = {
        ...editingApproval.proposed_payload,
        title: editTitle,
        assignee_name: editAssigneeName,
        assignee_email: editAssigneeEmail,
        deadline: editDeadline,
        priority: editPriority,
      };

      await api.approveAction(editingApproval.id, customPayload, editNotes || "Edited and approved by user");
      setEditingApproval(null);
      await loadApprovals();
    } catch (err: any) {
      alert(`Execution failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const pendingCount = approvals.filter((a) => a.status === "PENDING").length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Human Approval Gate</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Strict human verification mandatory before task assignment email dispatch or reminder scheduling.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {selectedIds.length > 0 && (
            <button
              onClick={handleApproveBatch}
              disabled={executing}
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Check size={13} />
              <span>Approve Selected ({selectedIds.length})</span>
            </button>
          )}

          {pendingCount > 0 && selectedIds.length === 0 && (
            <button
              onClick={async () => {
                const allPending = approvals.filter((a) => a.status === "PENDING").map((a) => a.id);
                setExecuting(true);
                try {
                  await api.batchApprove(allPending);
                  await loadApprovals();
                } catch (err: any) {
                  alert(`Execution failed: ${err.message}`);
                } finally {
                  setExecuting(false);
                }
              }}
              disabled={executing}
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Check size={13} />
              <span>Approve All Pending ({pendingCount})</span>
            </button>
          )}

          <button
            onClick={loadApprovals}
            className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
            title="Refresh"
          >
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-border-subtle text-xs">
        {["PENDING", "APPROVED", "REJECTED", "ALL"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`pb-2.5 px-3 font-semibold transition-colors border-b-2 ${
              statusFilter === st
                ? "border-accent-orange text-accent-orange"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {st} {st === "PENDING" && `(${pendingCount})`}
          </button>
        ))}
      </div>

      {/* Main List Table */}
      <div className="rounded bg-bg-card border border-border-subtle overflow-hidden">
        {/* Table Header */}
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono text-text-muted">
          <div className="flex items-center gap-3">
            {statusFilter === "PENDING" && (
              <input
                type="checkbox"
                onChange={handleSelectAll}
                checked={selectedIds.length > 0 && selectedIds.length === pendingCount}
                className="accent-accent-orange rounded"
              />
            )}
            <span className="uppercase tracking-wider">Proposed Action & Transcript Evidence</span>
          </div>
          <span className="uppercase tracking-wider hidden sm:block">Confidence & Actions</span>
        </div>

        {/* Approvals Items */}
        <div className="divide-y divide-border-subtle">
          {approvals.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted">
              No approvals found matching filter &quot;{statusFilter}&quot;.
            </div>
          ) : (
            approvals.map((app) => {
              const p = app.proposed_payload || {};
              const isSelected = selectedIds.includes(app.id);
              const isPending = app.status === "PENDING";
              const isLowConfidence = (p.confidence || 0.9) < 0.75 || p.requires_clarification;

              return (
                <div
                  key={app.id}
                  className={`p-4 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                    isSelected ? "bg-accent-orange/5" : "hover:bg-bg-elevated/40"
                  }`}
                >
                  {/* Left Column: Task Info & Evidence */}
                  <div className="flex items-start gap-3 flex-1">
                    {isPending && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(app.id)}
                        className="accent-accent-orange rounded mt-1 shrink-0"
                      />
                    )}

                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                            p.priority === "URGENT" || p.priority === "HIGH"
                              ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30"
                              : "bg-bg-elevated text-text-secondary border border-border-subtle"
                          }`}
                        >
                          {p.priority}
                        </span>

                        <h3 className="text-sm font-semibold text-text-primary">{p.title}</h3>

                        {isLowConfidence && (
                          <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold rounded bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 flex items-center gap-1">
                            <AlertTriangle size={10} />
                            <span>HUMAN CLARIFICATION REQUIRED</span>
                          </span>
                        )}

                        <span
                          className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                            app.status === "APPROVED"
                              ? "bg-accent-neon/20 text-accent-neon"
                              : app.status === "REJECTED"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-bg-elevated text-text-secondary"
                          }`}
                        >
                          {app.status}
                        </span>
                      </div>

                      {/* Metadata Row */}
                      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-text-secondary">
                        <div>
                          Assignee:{" "}
                          <strong className="text-text-primary">
                            {p.assignee_name || "Unassigned"}
                          </strong>
                        </div>
                        <div>
                          Deadline: <strong className="text-accent-orange">{p.deadline || "TBD"}</strong>
                        </div>
                        <div>
                          Confidence:{" "}
                          <strong className={isLowConfidence ? "text-yellow-400" : "text-accent-neon"}>
                            {Math.round((p.confidence || 0.9) * 100)}%
                          </strong>
                        </div>
                        {app.approved_recipient && (
                          <div className="text-accent-neon flex items-center gap-1">
                            <CheckCircle2 size={11} />
                            <span>Sent to: {app.approved_recipient}</span>
                          </div>
                        )}
                      </div>

                      {/* Destination Email Inline Row */}
                      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border-subtle/50 text-xs">
                        <span className="text-text-muted font-mono flex items-center gap-1">
                          <Mail size={12} className="text-accent-orange shrink-0" />
                          <span className="font-semibold text-text-secondary">Destination Email:</span>
                        </span>
                        <input
                          type="email"
                          value={destinationEmails[app.id] ?? (p.assignee_email || app.approved_recipient || "")}
                          onChange={(e) => setDestinationEmails({ ...destinationEmails, [app.id]: e.target.value })}
                          placeholder="e.g. 25ug1byai034@bmsit.in"
                          className="bg-bg-elevated border border-border-subtle focus:border-accent-orange rounded px-2.5 py-1 text-xs text-text-primary font-mono w-60 sm:w-80"
                        />
                        {app.status === "APPROVED" && (
                          <button
                            onClick={() => handleSendEmailNow(app)}
                            disabled={executing}
                            className="px-2.5 py-1 text-xs font-semibold bg-accent-orange/20 border border-accent-orange/40 text-accent-orange hover:bg-accent-orange hover:text-black rounded flex items-center gap-1 transition-colors"
                            title="Dispatch assignment email via Gmail SMTP"
                          >
                            <Send size={11} />
                            <span>{app.approved_recipient ? "Re-send Email" : "Send Email Now"}</span>
                          </button>
                        )}
                      </div>

                      {/* Evidence Quote */}
                      {p.evidence_quote && (
                        <div className="text-[11px] text-text-muted italic bg-bg-elevated/60 border-l-2 border-accent-orange px-2.5 py-1.5 rounded-r">
                          &ldquo;{p.evidence_quote}&rdquo;
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Actions */}
                  <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                    {p.email_content && (
                      <button
                        onClick={() => setPreviewEmailModal(p.email_content)}
                        className="px-2.5 py-1 text-xs font-medium bg-bg-elevated border border-border-subtle hover:border-border-strong text-text-primary rounded flex items-center gap-1"
                        title="Preview generated Gmail SMTP email template"
                      >
                        <Eye size={12} />
                        <span>Email Preview</span>
                      </button>
                    )}

                    {isPending && (
                      <>
                        <button
                          onClick={() => openEditModal(app)}
                          className="px-2.5 py-1 text-xs font-medium bg-bg-elevated border border-border-subtle hover:border-border-strong text-text-primary rounded flex items-center gap-1"
                          title="Edit task parameters before approving"
                        >
                          <Edit3 size={12} />
                          <span>Edit &amp; Approve</span>
                        </button>

                        <button
                          onClick={() => handleRejectSingle(app.id)}
                          disabled={executing}
                          className="p-1.5 text-xs text-red-400 hover:text-red-300 rounded hover:bg-bg-elevated border border-transparent hover:border-red-500/20"
                          title="Reject proposal"
                        >
                          <X size={14} />
                        </button>

                        <button
                          onClick={() => handleApproveSingle(app)}
                          disabled={executing}
                          className="px-3 py-1 text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover rounded flex items-center gap-1 transition-colors disabled:opacity-50"
                        >
                          <Check size={12} />
                          <span>Approve &amp; Send</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Edit & Approve Modal */}
      {editingApproval && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-bg-card border border-border-subtle rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                Edit Proposed Action Before Approval
              </h3>
              <button
                onClick={() => setEditingApproval(null)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-text-secondary block mb-1">Task Title</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-text-secondary block mb-1">Assignee Name</label>
                  <input
                    type="text"
                    value={editAssigneeName}
                    onChange={(e) => setEditAssigneeName(e.target.value)}
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                  />
                </div>
                <div>
                  <label className="text-text-secondary block mb-1 font-medium">
                    Destination Email Address <span className="text-accent-orange">*</span>
                  </label>
                  <input
                    type="email"
                    value={editAssigneeEmail}
                    onChange={(e) => setEditAssigneeEmail(e.target.value)}
                    placeholder="e.g. 25ug1byai034@bmsit.in"
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
                  />
                  <span className="text-[10px] text-text-muted mt-0.5 block">
                    Task assignments and reminders will be delivered to this email address via Gmail SMTP upon approval.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-text-secondary block mb-1">Deadline (YYYY-MM-DD)</label>
                  <input
                    type="text"
                    value={editDeadline}
                    onChange={(e) => setEditDeadline(e.target.value)}
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                  />
                </div>
                <div>
                  <label className="text-text-secondary block mb-1">Priority</label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value)}
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="URGENT">URGENT</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-text-secondary block mb-1">Approval Notes</label>
                <input
                  type="text"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="e.g. Verified with Sarah during sync."
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-border-subtle">
              <button
                onClick={() => setEditingApproval(null)}
                className="px-3 py-1.5 rounded text-xs text-text-secondary hover:text-text-primary bg-bg-elevated"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAndApprove}
                disabled={executing}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover"
              >
                Save &amp; Execute Approval
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Email Preview Modal */}
      {previewEmailModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-bg-card border border-border-subtle rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Mail size={16} className="text-accent-orange" />
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Gmail SMTP Email Template Preview
                </h3>
              </div>
              <button
                onClick={() => setPreviewEmailModal(null)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="text-xs space-y-2">
              <div className="p-2 bg-bg-elevated rounded border border-border-subtle font-mono text-[11px]">
                <span className="text-text-muted">Subject: </span>
                <strong className="text-text-primary">{previewEmailModal.subject}</strong>
              </div>

              <div
                className="p-4 bg-[#090909] rounded border border-border-subtle overflow-y-auto max-h-[50vh]"
                dangerouslySetInnerHTML={{ __html: previewEmailModal.html }}
              />
            </div>

            <div className="flex justify-end pt-3 border-t border-border-subtle">
              <button
                onClick={() => setPreviewEmailModal(null)}
                className="px-4 py-1.5 rounded text-xs font-medium bg-bg-elevated text-text-primary"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
