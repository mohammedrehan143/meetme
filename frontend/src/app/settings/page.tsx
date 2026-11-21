"use client";

import React, { useEffect, useState } from "react";
import { Settings, Cpu, Mail, Database, RefreshCw, CheckCircle2, ShieldCheck, Key } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<any | null>(null);
  const [groqKey, setGroqKey] = useState("");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");
  const [resendKey, setResendKey] = useState("");
  const [resendFrom, setResendFrom] = useState("MEETME <onboarding@resend.dev>");
  const [saving, setSaving] = useState(false);
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
      if (data?.resend?.from_email) setResendFrom(data.resend.from_email);
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
        resend_api_key: resendKey.trim() || undefined,
        resend_from_email: resendFrom.trim() || undefined,
      });
      setMessage("Configuration updated successfully.");
      setGroqKey("");
      setResendKey("");
      await loadSettings();
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
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
      setMessage(`Demo workspace seeded successfully! Ingested ${res.orchestration?.tasks_count} tasks.`);
    } catch (err: any) {
      alert(`Seed failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="pb-3 border-b border-border-subtle">
        <h1 className="text-xl font-bold text-text-primary">System &amp; Workspace Configuration</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          AI inference provider keys, email execution credentials, and demo simulation controls.
        </p>
      </div>

      {message && (
        <div className="p-3.5 rounded bg-accent-neon/15 border border-accent-neon/30 text-accent-neon text-xs flex items-center gap-2">
          <CheckCircle2 size={15} />
          <span>{message}</span>
        </div>
      )}

      {/* Demo Seed Section */}
      <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
              Demo Workspace Ingestion
            </h3>
            <p className="text-xs text-text-secondary">
              Instantly re-seed the workspace with Sarah Chen, Rahul Sharma, Elena Rostova, and Marcus Vance. 
              Executes the full multi-agent orchestrator pipeline on the architecture transcript.
            </p>
          </div>

          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="px-4 py-2 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover disabled:opacity-50 flex items-center gap-1.5 shrink-0 transition-colors"
          >
            <RefreshCw size={13} className={seeding ? "animate-spin" : ""} />
            <span>{seeding ? "Orchestrating..." : "Reset & Seed Demo"}</span>
          </button>
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Groq Settings */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-accent-orange" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Groq AI Inference Configuration (Primary Engine)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.groq?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.groq?.is_configured ? "ACTIVE KEY LOADED" : "LOCAL PIPELINE ACTIVE"}
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
                Leave empty to retain existing key. System falls back gracefully if not configured.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">Groq Model Identifier</label>
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

        {/* Resend Email Settings */}
        <div className="p-5 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Mail size={16} className="text-accent-neon" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Email Provider Configuration (Resend Engine)
              </h3>
            </div>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
              config?.resend?.is_configured ? "bg-accent-neon/20 text-accent-neon" : "bg-bg-elevated text-text-muted"
            }`}>
              {config?.resend?.is_configured ? "RESEND ACTIVE" : "LOCAL QUEUE MODE"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-text-secondary block mb-1">
                Resend API Key {config?.resend?.is_configured && `(Current: ${config.resend.masked_key})`}
              </label>
              <input
                type="password"
                value={resendKey}
                onChange={(e) => setResendKey(e.target.value)}
                placeholder="re_..."
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
              <span className="text-[10px] text-text-muted mt-1 block">
                If omitted, emails are queued locally and logged in the Email Audit Log.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1">Sender Email Address</label>
              <input
                type="text"
                value={resendFrom}
                onChange={(e) => setResendFrom(e.target.value)}
                placeholder="MEETME <onboarding@resend.dev>"
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange font-mono"
              />
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
