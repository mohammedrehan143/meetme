"use client";

import React, { useEffect, useState } from "react";
import { Settings, Cpu, Mail, Database, RefreshCw, CheckCircle2, AlertTriangle, ShieldCheck, Key, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<any | null>(null);
  const [groqKey, setGroqKey] = useState("");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");
  
  // Gmail SMTP State
  const [smtpEmail, setSmtpEmail] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpFromName, setSmtpFromName] = useState("MEETME Intelligence");

  const [saving, setSaving] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);
  const [smtpTestResult, setSmtpTestResult] = useState<{ success: boolean; message?: string; error?: string } | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setConfig(data);
      if (data?.groq?.model) setGroqModel(data.groq.model);
      if (data?.smtp?.email) setSmtpEmail(data.smtp.email);
      if (data?.smtp?.host) setSmtpHost(data.smtp.host);
      if (data?.smtp?.port) setSmtpPort(data.smtp.port);
      if (data?.smtp?.from_name) setSmtpFromName(data.smtp.from_name);
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.updateSettings({
        groq_api_key: groqKey.trim() || undefined,
        groq_model: groqModel,
        smtp_email: smtpEmail.trim() || undefined,
        smtp_password: smtpPassword.trim() || undefined,
        smtp_host: smtpHost.trim() || undefined,
        smtp_port: Number(smtpPort) || undefined,
        smtp_from_name: smtpFromName.trim() || undefined,
      });
      setMessage("Configuration updated successfully.");
      setGroqKey("");
      setSmtpPassword("");
      await loadSettings();
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    setTestingSmtp(true);
    setSmtpTestResult(null);
    try {
      const res = await api.testSmtp();
      setSmtpTestResult(res);
    } catch (err: any) {
      setSmtpTestResult({
        success: false,
        error: err.message || "Failed to test SMTP connection."
      });
    } finally {
      setTestingSmtp(false);
    }
  };

  const handleSeedDemo = async () => {
    if (!confirm("Reset and re-seed the demo workspace? This will ingest the demo meeting and re-run all AI agents.")) {
      return;
    }
    setSeeding(true);
    setMessage(null);
    try {
      const res = await api.seedDemo(true);
      setMessage(`Demo workspace seeded successfully! Processed ${res.tasks_count} tasks and ${res.approvals_count} approvals.`);
    } catch (err: any) {
      alert(`Demo reset failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <Settings size={18} className="text-accent-orange" />
          <h1 className="text-xl font-bold text-text-primary">System &amp; Integration Settings</h1>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-accent-neon/10 border border-accent-neon/30 text-accent-neon text-xs rounded flex items-center gap-2">
          <CheckCircle2 size={14} />
          <span>{message}</span>
        </div>
      )}

      {/* Demo Seeding & Reset Section */}
      <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
              Executive Demo Workspace
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Reset the local workspace and execute the full multi-agent pipeline with verified sample transcripts.
            </p>
          </div>
          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="px-3.5 py-1.5 rounded text-xs font-semibold bg-bg-elevated border border-border-subtle hover:border-accent-orange text-text-primary flex items-center gap-2 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={13} className={seeding ? "animate-spin text-accent-orange" : ""} />
            <span>{seeding ? "Executing Multi-Agent Pipeline..." : "Reset & Seed Demo"}</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Groq Engine Settings */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-accent-orange" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Groq AI Inference Engine (LPU Acceleration)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.groq?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.groq?.is_configured ? "GROQ ACTIVE" : "HEURISTIC FALLBACK MODE"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-text-secondary block mb-1">
                Groq API Key {config?.groq?.is_configured && `(Current: ${config.groq.masked_key})`}
              </label>
              <input
                type="password"
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder="gsk_..."
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Powers real-time Whisper transcription and sub-second multi-agent orchestration.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">LLM Model</label>
              <select
                value={groqModel}
                onChange={(e) => setGroqModel(e.target.value)}
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              >
                <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
                <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Ultra Fast)</option>
                <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
              </select>
              <span className="text-[10px] text-text-muted mt-1 block">
                Whisper model: {config?.groq?.whisper_model || "whisper-large-v3"}
              </span>
            </div>
          </div>
        </div>

        {/* Native Gmail SMTP Settings */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Mail size={16} className="text-accent-neon" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Native Gmail SMTP Email Service (STARTTLS Port 587)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.smtp?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.smtp?.is_configured ? "GMAIL SMTP ACTIVE" : "DEV / LOCAL QUEUE MODE"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-text-secondary block mb-1">Gmail Address (Sender)</label>
              <input
                type="email"
                value={smtpEmail}
                onChange={(e) => setSmtpEmail(e.target.value)}
                placeholder="yourmail@gmail.com"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Primary Gmail or Google Workspace address.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">
                Google App Password {config?.smtp?.is_configured && `(Current: ${config.smtp.masked_password})`}
              </label>
              <input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="16-character app password (e.g. abcd efgh ijkl mnop)"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Generated from Google Account &rarr; Security &rarr; 2-Step Verification &rarr; App Passwords.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">SMTP Host</label>
              <input
                type="text"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="smtp.gmail.com"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
            </div>

            <div>
              <label className="text-text-secondary block mb-1">SMTP Port &amp; Display Name</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={smtpPort}
                  onChange={(e) => setSmtpPort(Number(e.target.value))}
                  placeholder="587"
                  className="w-24 bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
                />
                <input
                  type="text"
                  value={smtpFromName}
                  onChange={(e) => setSmtpFromName(e.target.value)}
                  placeholder="MEETME Intelligence"
                  className="flex-1 bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>
            </div>
          </div>

          {/* Test SMTP Connection Action & Status */}
          <div className="pt-2 border-t border-border-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleTestSmtp}
                disabled={testingSmtp}
                className="px-3.5 py-1.5 rounded text-xs font-semibold bg-bg-elevated border border-border-subtle hover:border-accent-neon text-text-primary flex items-center gap-2 disabled:opacity-50 transition-colors"
              >
                <ShieldCheck size={14} className={testingSmtp ? "animate-spin text-accent-neon" : "text-accent-neon"} />
                <span>{testingSmtp ? "Testing STARTTLS Handshake..." : "Test Gmail SMTP Connection"}</span>
              </button>

              {smtpTestResult && (
                <span className={`text-xs font-mono px-2.5 py-1 rounded border ${
                  smtpTestResult.success
                    ? "bg-accent-neon/15 text-accent-neon border-accent-neon/30"
                    : "bg-red-500/15 text-red-400 border-red-500/30"
                }`}>
                  {smtpTestResult.success ? smtpTestResult.message : smtpTestResult.error}
                </span>
              )}
            </div>

            <a
              href="https://myaccount.google.com/apppasswords"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] text-accent-orange hover:underline flex items-center gap-1 font-mono"
            >
              <span>How to generate a Google App Password</span>
              <ExternalLink size={11} />
            </a>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving Changes..." : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  );
}
