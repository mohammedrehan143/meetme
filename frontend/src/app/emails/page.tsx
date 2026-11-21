"use client";

import React, { useEffect, useState } from "react";
import { Mail, CheckCircle2, AlertTriangle, RotateCw, Eye, X, Send, Layers, Clock, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { EmailLog } from "@/lib/types";

export default function EmailActivityPage() {
  const [emails, setEmails] = useState<EmailLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewEmail, setPreviewEmail] = useState<EmailLog | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  // Compose / Send Email State
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [toEmail, setToEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => {
    loadEmails();
  }, []);

  const loadEmails = async () => {
    setLoading(true);
    try {
      const data = await api.getEmails();
      setEmails(data);
    } catch (err) {
      console.error("Failed to load emails:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!toEmail.trim() || !subject.trim() || !message.trim()) {
      setSendError("Please specify destination email, subject, and message content.");
      return;
    }
    setSending(true);
    setSendError(null);
    setSendSuccess(null);
    try {
      await api.sendEmail({
        to_email: toEmail.trim(),
        recipient_name: recipientName.trim() || undefined,
        subject: subject.trim(),
        message: message.trim(),
      });
      setSendSuccess(`Email successfully delivered to ${toEmail.trim()} via Gmail SMTP!`);
      setToEmail("");
      setRecipientName("");
      setSubject("");
      setMessage("");
      await loadEmails();
      setTimeout(() => {
        setShowComposeModal(false);
        setSendSuccess(null);
      }, 2500);
    } catch (err: any) {
      setSendError(err.message || "Failed to dispatch email");
    } finally {
      setSending(false);
    }
  };

  const handleRetry = async (id: string) => {
    setRetryingId(id);
    try {
      await api.retryEmail(id);
      await loadEmails();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setRetryingId(null);
    }
  };

  const totalSent = emails.filter((e) => e.status === "SENT").length;
  const totalFailed = emails.filter((e) => e.status === "FAILED").length;
  const totalConsolidated = emails.filter((e) => e.email_type?.startsWith("CONSOLIDATED_") || (e.task_ids && e.task_ids.length > 1)).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Mail size={18} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Email Execution Audit Log</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Full audit log of task notifications, consolidated digests, and reminders dispatched via Native Gmail SMTP.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setShowComposeModal(true);
              setSendError(null);
              setSendSuccess(null);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover transition-colors"
          >
            <Send size={13} />
            <span>Send Email</span>
          </button>
          <button
            onClick={loadEmails}
            className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
            title="Refresh"
          >
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Total Dispatched</span>
          <p className="text-2xl font-bold font-mono text-accent-neon">{totalSent}</p>
          <span className="text-[11px] text-text-secondary">Delivered via Gmail SMTP</span>
        </div>
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Consolidated Digests</span>
          <p className="text-2xl font-bold font-mono text-accent-orange">{totalConsolidated}</p>
          <span className="text-[11px] text-text-secondary">Multi-task grouped emails</span>
        </div>
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Failed Sends</span>
          <p className="text-2xl font-bold font-mono text-red-400">{totalFailed}</p>
          <span className="text-[11px] text-text-secondary">Exponential backoff active</span>
        </div>
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-1">
          <span className="text-[10px] font-mono text-text-muted uppercase">Native Provider</span>
          <p className="text-sm font-bold font-mono text-text-primary flex items-center gap-1.5 pt-1.5">
            <ShieldCheck size={16} className="text-accent-neon" />
            <span>Gmail SMTP (587)</span>
          </p>
          <span className="text-[11px] text-text-secondary">STARTTLS Authenticated</span>
        </div>
      </div>

      {/* Emails Table */}
      <div className="rounded bg-bg-card border border-border-subtle overflow-hidden">
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono text-text-muted">
          <span>Recipient, Subject &amp; Related Tasks</span>
          <span>Status &amp; Message ID</span>
        </div>

        <div className="divide-y divide-border-subtle">
          {emails.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted">
              No emails sent or queued yet.
            </div>
          ) : (
            emails.map((e) => {
              const isSuccess = e.status === "SENT";
              const isQueued = e.status === "QUEUED_LOCAL" || e.status === "QUEUED_DEV";
              const isFailed = e.status === "FAILED";
              const taskCount = e.task_ids ? e.task_ids.length : e.task_id ? 1 : 0;
              const isConsolidated = e.email_type?.startsWith("CONSOLIDATED_") || taskCount > 1;

              return (
                <div
                  key={e.id}
                  className="p-4 hover:bg-bg-elevated/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1.5 max-w-xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <strong className="text-text-primary">{e.subject}</strong>
                      
                      {e.email_type && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-bg-elevated text-text-secondary border border-border-subtle">
                          {e.email_type}
                        </span>
                      )}

                      {isConsolidated && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-accent-orange/20 text-accent-orange border border-accent-orange/30 flex items-center gap-1">
                          <Layers size={10} />
                          <span>Consolidated ({taskCount} Tasks)</span>
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-text-secondary font-mono text-[11px]">
                      <span>To: <strong className="text-text-primary">{e.recipient}</strong> ({e.email_address})</span>
                      <span>Provider: <strong className="text-text-primary">{e.provider || "Gmail SMTP"}</strong></span>
                      {e.sent_at && (
                        <span className="flex items-center gap-1">
                          <Clock size={11} className="text-text-muted" />
                          <span>Sent: {new Date(e.sent_at).toLocaleTimeString()} ({new Date(e.sent_at).toLocaleDateString()})</span>
                        </span>
                      )}
                    </div>

                    {e.error_message && (
                      <p className="text-[11px] text-red-400 italic">
                        Error: {e.error_message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center font-mono text-xs">
                    <div className="text-right">
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        isSuccess ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30" :
                        isQueued ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" :
                        "bg-red-500/20 text-red-400 border border-red-500/30"
                      }`}>
                        {e.status}
                      </span>
                      {e.message_id && (
                        <div className="text-[9px] text-text-muted mt-1 truncate max-w-[140px]" title={e.message_id}>
                          {e.message_id}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => setPreviewEmail(e)}
                      className="px-2.5 py-1 text-[11px] font-medium bg-bg-elevated border border-border-subtle hover:border-border-strong text-text-primary rounded flex items-center gap-1"
                    >
                      <Eye size={12} />
                      <span>Preview</span>
                    </button>

                    {isFailed && (
                      <button
                        onClick={() => handleRetry(e.id)}
                        disabled={retryingId === e.id}
                        className="px-2.5 py-1 text-[11px] font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover rounded flex items-center gap-1 disabled:opacity-50"
                      >
                        <RotateCw size={11} className={retryingId === e.id ? "animate-spin" : ""} />
                        <span>Retry</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* HTML Email Preview Modal */}
      {previewEmail && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-bg-card border border-border-subtle rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Mail size={16} className="text-accent-orange" />
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Gmail SMTP Dispatch Audit Payload
                </h3>
              </div>
              <button
                onClick={() => setPreviewEmail(null)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="text-xs space-y-2">
              <div className="p-2.5 bg-bg-elevated rounded border border-border-subtle font-mono text-[11px] space-y-1">
                <div><span className="text-text-muted">To: </span><strong className="text-text-primary">{previewEmail.recipient} &lt;{previewEmail.email_address}&gt;</strong></div>
                <div><span className="text-text-muted">Subject: </span><strong className="text-text-primary">{previewEmail.subject}</strong></div>
                <div><span className="text-text-muted">Message ID: </span><strong className="text-text-primary">{previewEmail.message_id || previewEmail.provider_message_id || "N/A"}</strong></div>
                {previewEmail.idempotency_key && (
                  <div><span className="text-text-muted">Idempotency Key: </span><span className="text-text-secondary">{previewEmail.idempotency_key}</span></div>
                )}
              </div>

              <div
                className="p-4 bg-[#090909] rounded border border-border-subtle overflow-y-auto max-h-[50vh]"
                dangerouslySetInnerHTML={{ __html: previewEmail.body_html }}
              />
            </div>

            <div className="flex justify-end pt-3 border-t border-border-subtle">
              <button
                onClick={() => setPreviewEmail(null)}
                className="px-4 py-1.5 rounded text-xs font-medium bg-bg-elevated text-text-primary"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send Custom Email Modal */}
      {showComposeModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-bg-card border border-border-subtle rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Send size={16} className="text-accent-orange" />
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Dispatch Custom Email via Native Gmail SMTP
                </h3>
              </div>
              <button
                onClick={() => setShowComposeModal(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            {sendSuccess && (
              <div className="p-3 bg-accent-neon/10 border border-accent-neon/30 text-accent-neon text-xs rounded flex items-center gap-2">
                <CheckCircle2 size={14} />
                <span>{sendSuccess}</span>
              </div>
            )}

            {sendError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertTriangle size={14} />
                <span>{sendError}</span>
              </div>
            )}

            <form onSubmit={handleSendEmail} className="space-y-3 text-xs">
              <div>
                <label className="text-text-secondary block mb-1 font-medium">
                  Destination Email Address <span className="text-accent-orange">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={toEmail}
                  onChange={(e) => setToEmail(e.target.value)}
                  placeholder="e.g. 25ug1byai034@bmsit.in"
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
                />
              </div>

              <div>
                <label className="text-text-secondary block mb-1 font-medium">
                  Recipient Name (Optional)
                </label>
                <input
                  type="text"
                  value={recipientName}
                  onChange={(e) => setRecipientName(e.target.value)}
                  placeholder="e.g. Lead Engineer / Participant"
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>

              <div>
                <label className="text-text-secondary block mb-1 font-medium">
                  Email Subject <span className="text-accent-orange">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. [MEETME] Task Assignment & Delivery Schedule"
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>

              <div>
                <label className="text-text-secondary block mb-1 font-medium">
                  Message Content <span className="text-accent-orange">*</span>
                </label>
                <textarea
                  required
                  rows={5}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type your message, task details, or meeting summary here..."
                  className="w-full bg-bg-elevated border border-border-subtle rounded p-3 text-text-primary focus:outline-none focus:border-accent-orange leading-relaxed"
                />
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-border-subtle">
                <span className="text-[10px] font-mono text-text-muted">Engine: Gmail SMTP STARTTLS (587)</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowComposeModal(false)}
                    className="px-3 py-1.5 rounded text-xs text-text-secondary hover:text-text-primary bg-bg-elevated"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={sending}
                    className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 disabled:opacity-50 transition-colors"
                  >
                    <Send size={12} className={sending ? "animate-spin" : ""} />
                    <span>{sending ? "Delivering via SMTP..." : "Send Email"}</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
