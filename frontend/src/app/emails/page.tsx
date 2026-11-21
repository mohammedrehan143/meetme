"use client";

import React, { useEffect, useState } from "react";
import { Mail, CheckCircle2, AlertTriangle, RotateCw, Eye, X, Send } from "lucide-react";
import { api } from "@/lib/api";
import { EmailLog } from "@/lib/types";

export default function EmailActivityPage() {
  const [emails, setEmails] = useState<EmailLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewEmail, setPreviewEmail] = useState<EmailLog | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

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
            Full audit log of task notifications, reminders, and executive summaries dispatched via Resend.
          </p>
        </div>

        <button
          onClick={loadEmails}
          className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
          title="Refresh"
        >
          <RotateCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Emails Table */}
      <div className="rounded bg-bg-card border border-border-subtle overflow-hidden">
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono text-text-muted">
          <span>Recipient &amp; Subject</span>
          <span>Status &amp; Provider Message ID</span>
        </div>

        <div className="divide-y divide-border-subtle">
          {emails.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted">
              No emails sent or queued yet.
            </div>
          ) : (
            emails.map((e) => {
              const isSuccess = e.status === "SENT";
              const isQueued = e.status === "QUEUED_LOCAL";
              const isFailed = e.status === "FAILED";

              return (
                <div
                  key={e.id}
                  className="p-4 hover:bg-bg-elevated/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <strong className="text-text-primary">{e.subject}</strong>
                    </div>

                    <div className="flex items-center gap-3 text-text-secondary font-mono text-[11px]">
                      <span>To: <strong className="text-text-primary">{e.recipient}</strong> ({e.email_address})</span>
                      <span>Provider: <strong className="text-text-primary">{e.provider}</strong></span>
                      {e.sent_at && <span>Sent: {new Date(e.sent_at).toLocaleTimeString()}</span>}
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
                      {e.provider_message_id && (
                        <div className="text-[9px] text-text-muted mt-1 truncate max-w-[120px]">
                          {e.provider_message_id}
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
                  Email Dispatch Audit Payload
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
    </div>
  );
}
