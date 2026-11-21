"use client";

import React, { useEffect, useState } from "react";
import { Settings, Cpu, Mail, Database, RefreshCw, CheckCircle2, AlertTriangle, ShieldCheck, Key, ExternalLink, Send, Zap } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<any | null>(null);
  const [groqKey, setGroqKey] = useState("");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");

  // Gemini State
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-pro");
  
  // Resend Cloud HTTP API State (Port 443 - Recommended for Render)
  const [resendApiKey, setResendApiKey] = useState("");
  const [resendFromEmail, setResendFromEmail] = useState("MEETME Platform <onboarding@resend.dev>");
  const [testEmailRecipient, setTestEmailRecipient] = useState("25ug1byai034@bmsit.in");
  const [testingEmail, setTestingEmail] = useState(false);
  const [dispatchingTest, setDispatchingTest] = useState(false);
  const [emailTestResult, setEmailTestResult] = useState<{ success: boolean; message?: string; error?: string; provider?: string } | null>(null);
  const [dispatchTestResult, setDispatchTestResult] = useState<{ success: boolean; message?: string; error?: string; provider?: string; id?: string } | null>(null);

  // Gmail SMTP State
  const [smtpEmail, setSmtpEmail] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpFromName, setSmtpFromName] = useState("MEETME Intelligence");

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setConfig(data);
      if (data?.groq?.model) setGroqModel(data.groq.model);
      if (data?.gemini?.model) setGeminiModel(data.gemini.model);
      if (data?.resend?.from_email) setResendFromEmail(data.resend.from_email);
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
        gemini_api_key: geminiKey.trim() || undefined,
        gemini_model: geminiModel,
        resend_api_key: resendApiKey.trim() || undefined,
        resend_from_email: resendFromEmail.trim() || undefined,
        smtp_email: smtpEmail.trim() || undefined,
        smtp_password: smtpPassword.trim() || undefined,
        smtp_host: smtpHost.trim() || undefined,
        smtp_port: Number(smtpPort) || undefined,
        smtp_from_name: smtpFromName.trim() || undefined,
      });
      setMessage("Configuration updated successfully.");
      setGroqKey("");
      setGeminiKey("");
      setResendApiKey("");
      setSmtpPassword("");
      await loadSettings();
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestEmailConnection = async () => {
    setTestingEmail(true);
    setEmailTestResult(null);
    try {
      const res = await api.testEmailConnection();
      setEmailTestResult(res);
    } catch (err: any) {
      setEmailTestResult({
        success: false,
        error: err.message || "Failed to test email connection."
      });
    } finally {
      setTestingEmail(false);
    }
  };

  const handleSendTestDispatch = async () => {
    if (!testEmailRecipient.trim()) {
      alert("Please enter a destination email address.");
      return;
    }
    setDispatchingTest(true);
    setDispatchTestResult(null);
    try {
      const res = await api.testEmailDispatch(testEmailRecipient.trim());
      setDispatchTestResult(res);
    } catch (err: any) {
      setDispatchTestResult({
        success: false,
        error: err.message || "Failed to dispatch test email."
      });
    } finally {
      setDispatchingTest(false);
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

        {/* Google Gemini AI Engine Settings */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-accent-neon" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Google Gemini Engine (Deep Reasoning &amp; Long-Context Synthesis)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.gemini?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.gemini?.is_configured ? "GEMINI ACTIVE" : "STANDBY / OPTIONAL"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-text-secondary block mb-1">
                Gemini API Key {config?.gemini?.is_configured && `(Current: ${config.gemini.masked_key})`}
              </label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Powers deep implicit task extraction, 2M context window analysis, and multi-speaker disambiguation.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">Gemini Model</label>
              <select
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              >
                <option value="gemini-1.5-pro">gemini-1.5-pro (Recommended for Complex Analysis)</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash (High Speed &amp; Low Latency)</option>
                <option value="gemini-2.0-flash-exp">gemini-2.0-flash-exp (Experimental)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Resend HTTP Email Engine (Recommended for Render & Cloud Deployments) */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-accent-neon" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Resend Cloud HTTP Email Service (Port 443 HTTPS - Render Compatible)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.resend?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.resend?.is_configured ? "RESEND ACTIVE (PORT 443)" : "STANDBY / RECOMMENDED FOR RENDER"}
            </span>
          </div>

          <div className="p-3 bg-accent-orange/10 border border-accent-orange/20 rounded text-[11px] text-text-secondary leading-relaxed">
            <strong className="text-accent-orange font-semibold">Render Free Tier Network Requirement: </strong>
            Render cloud containers strictly drop outbound raw TCP connections on SMTP ports 25, 465, and 587. 
            Resend dispatches emails via REST API over standard HTTPS (Port 443), ensuring reliable delivery without firewall blocks.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-text-secondary block mb-1">
                Resend API Key {config?.resend?.is_configured && `(Current: ${config.resend.masked_key})`}
              </label>
              <input
                type="password"
                value={resendApiKey}
                onChange={(e) => setResendApiKey(e.target.value)}
                placeholder="re_..."
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Free tier gives 3,000 emails/month at resend.com (no credit card required).
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">Sender Address (From)</label>
              <input
                type="text"
                value={resendFromEmail}
                onChange={(e) => setResendFromEmail(e.target.value)}
                placeholder="MEETME Platform <onboarding@resend.dev>"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                Use <code className="text-accent-neon">onboarding@resend.dev</code> for immediate testing, or your verified domain.
              </span>
            </div>
          </div>

          {/* Test Provider Connection & Live Test Dispatch */}
          <div className="pt-3 border-t border-border-subtle space-y-3">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleTestEmailConnection}
                  disabled={testingEmail}
                  className="px-3.5 py-1.5 rounded text-xs font-semibold bg-bg-elevated border border-border-subtle hover:border-accent-neon text-text-primary flex items-center gap-2 disabled:opacity-50 transition-colors"
                >
                  <ShieldCheck size={14} className={testingEmail ? "animate-spin text-accent-neon" : "text-accent-neon"} />
                  <span>{testingEmail ? "Verifying Provider Connection..." : "Test Active Email Connection"}</span>
                </button>

                {emailTestResult && (
                  <span className={`text-xs font-mono px-2.5 py-1 rounded border ${
                    emailTestResult.success
                      ? "bg-accent-neon/15 text-accent-neon border-accent-neon/30"
                      : "bg-red-500/15 text-red-400 border-red-500/30"
                  }`}>
                    {emailTestResult.success ? (emailTestResult.message || "Connection verified") : emailTestResult.error}
                  </span>
                )}
              </div>

              <a
                href="https://resend.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-accent-orange hover:underline flex items-center gap-1 font-mono"
              >
                <span>Get free API Key at resend.com</span>
                <ExternalLink size={11} />
              </a>
            </div>

            {/* Test Email Dispatch to Destination */}
            <div className="p-3 bg-bg-elevated rounded border border-border-subtle flex flex-col sm:flex-row items-start sm:items-center gap-2">
              <span className="text-xs font-mono text-text-secondary whitespace-nowrap">Send Live Test:</span>
              <input
                type="email"
                value={testEmailRecipient}
                onChange={(e) => setTestEmailRecipient(e.target.value)}
                placeholder="25ug1byai034@bmsit.in"
                className="flex-1 bg-bg-card border border-border-subtle rounded px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <button
                type="button"
                onClick={handleSendTestDispatch}
                disabled={dispatchingTest}
                className="px-3 py-1 rounded text-xs font-semibold bg-accent-neon text-black hover:bg-accent-neon/90 flex items-center gap-1.5 disabled:opacity-50 transition-colors whitespace-nowrap"
              >
                <Send size={12} className={dispatchingTest ? "animate-spin" : ""} />
                <span>{dispatchingTest ? "Dispatching..." : "Send Test Email"}</span>
              </button>
            </div>

            {dispatchTestResult && (
              <div className={`p-2.5 rounded text-xs font-mono border ${
                dispatchTestResult.success
                  ? "bg-accent-neon/10 border-accent-neon/30 text-accent-neon"
                  : "bg-red-500/10 border-red-500/30 text-red-400"
              }`}>
                {dispatchTestResult.success 
                  ? `Delivered successfully! Provider: ${dispatchTestResult.provider || "Resend"}. Message ID: ${dispatchTestResult.id || "OK"}`
                  : `Dispatch failed: ${dispatchTestResult.error || "Unknown error"}`}
              </div>
            )}
          </div>
        </div>

        {/* Native Gmail SMTP Settings (Local / Non-Blocked Environments) */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Mail size={16} className="text-text-muted" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Native Gmail SMTP Service (Fallback / Local Dev)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.smtp?.is_configured ? "bg-bg-elevated text-text-primary" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.smtp?.is_configured ? "GMAIL SMTP CONFIGURED" : "NOT CONFIGURED"}
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
            </div>

            <div>
              <label className="text-text-secondary block mb-1">
                Google App Password {config?.smtp?.is_configured && `(Current: ${config.smtp.masked_password})`}
              </label>
              <input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="16-character app password"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
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
