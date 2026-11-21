"use client";

import React, { useEffect, useState } from "react";
import { 
  Layers, 
  CheckCircle2, 
  XCircle, 
  ExternalLink, 
  RotateCw, 
  ShieldCheck, 
  Key, 
  FolderGit2, 
  AtSign, 
  Globe, 
  Check, 
  Trash2,
  AlertTriangle
} from "lucide-react";
import { api } from "@/lib/api";
import { ExternalIssueSync } from "@/lib/types";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<any>({ jira: null, github: null });
  const [activity, setActivity] = useState<ExternalIssueSync[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingJira, setSavingJira] = useState(false);
  const [savingGitHub, setSavingGitHub] = useState(false);

  // Jira Form State
  const [jiraDomain, setJiraDomain] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraProjectKey, setJiraProjectKey] = useState("PROJ");
  const [jiraIssueType, setJiraIssueType] = useState("Task");

  // GitHub Form State
  const [githubToken, setGithubToken] = useState("");
  const [githubRepo, setGithubRepo] = useState("");

  useEffect(() => {
    loadIntegrationsData();
  }, []);

  const loadIntegrationsData = async () => {
    setLoading(true);
    try {
      const [integrationsData, activityData] = await Promise.all([
        api.getIntegrations(),
        api.getIntegrationActivity()
      ]);
      setIntegrations(integrationsData || { jira: null, github: null });
      setActivity(activityData || []);

      if (integrationsData?.jira?.is_connected) {
        setJiraDomain(integrationsData.jira.base_url || "");
        setJiraEmail(integrationsData.jira.account_name || "");
        setJiraProjectKey(integrationsData.jira.project_or_repo || "PROJ");
      }
      if (integrationsData?.github?.is_connected) {
        setGithubRepo(integrationsData.github.project_or_repo || "");
      }
    } catch (err) {
      console.error("Failed to load integrations data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectJira = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingJira(true);
    try {
      await api.connectJira({
        domain: jiraDomain,
        email: jiraEmail,
        api_token: jiraToken,
        project_key: jiraProjectKey,
        issue_type: jiraIssueType
      });
      alert("Jira Cloud integration connected successfully!");
      setJiraToken("");
      await loadIntegrationsData();
    } catch (err: any) {
      alert(`Jira connection failed: ${err.message}`);
    } finally {
      setSavingJira(false);
    }
  };

  const handleDisconnectJira = async () => {
    if (!confirm("Are you sure you want to disconnect Jira Cloud?")) return;
    try {
      await api.disconnectJira();
      await loadIntegrationsData();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    }
  };

  const handleConnectGitHub = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingGitHub(true);
    try {
      await api.connectGitHub({
        token: githubToken,
        repo: githubRepo
      });
      alert("GitHub integration connected successfully!");
      setGithubToken("");
      await loadIntegrationsData();
    } catch (err: any) {
      alert(`GitHub connection failed: ${err.message}`);
    } finally {
      setSavingGitHub(false);
    }
  };

  const handleDisconnectGitHub = async () => {
    if (!confirm("Are you sure you want to disconnect GitHub?")) return;
    try {
      await api.disconnectGitHub();
      await loadIntegrationsData();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    }
  };

  const isJiraConnected = integrations?.jira?.is_connected;
  const isGithubConnected = integrations?.github?.is_connected;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers size={20} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Integration Hub</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Connect external project trackers. Approved MEETME action items can automatically sync to Jira and GitHub.
          </p>
        </div>

        <button
          onClick={loadIntegrationsData}
          disabled={loading}
          className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary flex items-center gap-1.5 text-xs font-mono"
        >
          <RotateCw size={13} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Global Human Approval Notice */}
      <div className="p-3.5 bg-accent-orange/10 border border-accent-orange/30 rounded flex items-start gap-3 text-xs">
        <ShieldCheck size={18} className="text-accent-orange shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-accent-orange font-mono uppercase tracking-wider block">
            Global Human Approval Gate Enforced
          </strong>
          <p className="text-text-secondary">
            No issues or updates are dispatched to external trackers automatically. Every task must be approved in the Approval Centre before Jira or GitHub issue creation executes.
          </p>
        </div>
      </div>

      {/* Integration Configuration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* JIRA CARD */}
        <div className="p-5 bg-bg-card rounded-lg border border-border-subtle space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-blue-600/20 text-blue-400 font-bold flex items-center justify-center font-mono text-xs border border-blue-500/30">
                JIRA
              </div>
              <div>
                <h3 className="text-sm font-bold text-text-primary">Jira Cloud</h3>
                <span className="text-[10px] font-mono text-text-muted">Atlassian Cloud REST API v3</span>
              </div>
            </div>

            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded flex items-center gap-1 ${
              isJiraConnected 
                ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30" 
                : "bg-bg-elevated text-text-muted"
            }`}>
              {isJiraConnected ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
              <span>{isJiraConnected ? "CONNECTED" : "NOT CONNECTED"}</span>
            </span>
          </div>

          <form onSubmit={handleConnectJira} className="space-y-3 text-xs">
            <div>
              <label className="text-text-secondary block mb-1 font-mono">Jira Domain (Atlassian Host)</label>
              <div className="relative">
                <Globe size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
                <input
                  type="text"
                  placeholder="e.g. your-company.atlassian.net"
                  value={jiraDomain}
                  onChange={(e) => setJiraDomain(e.target.value)}
                  required
                  className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-text-secondary block mb-1 font-mono">User Email</label>
              <div className="relative">
                <AtSign size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
                <input
                  type="email"
                  placeholder="e.g. dev@company.com"
                  value={jiraEmail}
                  onChange={(e) => setJiraEmail(e.target.value)}
                  required
                  className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-text-secondary block mb-1 font-mono">
                API Token {isJiraConnected && <span className="text-text-muted">(Leave empty to keep existing)</span>}
              </label>
              <div className="relative">
                <Key size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
                <input
                  type="password"
                  placeholder={isJiraConnected ? "••••••••••••••••" : "Paste Jira API Token"}
                  value={jiraToken}
                  onChange={(e) => setJiraToken(e.target.value)}
                  required={!isJiraConnected}
                  className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-text-secondary block mb-1 font-mono">Project Key</label>
                <input
                  type="text"
                  placeholder="e.g. PROJ"
                  value={jiraProjectKey}
                  onChange={(e) => setJiraProjectKey(e.target.value)}
                  required
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs uppercase"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1 font-mono">Default Issue Type</label>
                <select
                  value={jiraIssueType}
                  onChange={(e) => setJiraIssueType(e.target.value)}
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                >
                  <option value="Task">Task</option>
                  <option value="Story">Story</option>
                  <option value="Bug">Bug</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
              {isJiraConnected ? (
                <button
                  type="button"
                  onClick={handleDisconnectJira}
                  className="px-3 py-1.5 rounded text-xs text-red-400 hover:text-red-300 bg-red-500/10 border border-red-500/20 flex items-center gap-1.5 transition-colors"
                >
                  <Trash2 size={12} />
                  <span>Disconnect</span>
                </button>
              ) : <div />}

              <button
                type="submit"
                disabled={savingJira}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Check size={13} />
                <span>{isJiraConnected ? "Update Jira Credentials" : "Connect Jira Cloud"}</span>
              </button>
            </div>
          </form>
        </div>

        {/* GITHUB CARD */}
        <div className="p-5 bg-bg-card rounded-lg border border-border-subtle space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-purple-600/20 text-purple-400 font-bold flex items-center justify-center font-mono text-xs border border-purple-500/30">
                GH
              </div>
              <div>
                <h3 className="text-sm font-bold text-text-primary">GitHub Issues</h3>
                <span className="text-[10px] font-mono text-text-muted">GitHub REST API v3</span>
              </div>
            </div>

            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded flex items-center gap-1 ${
              isGithubConnected 
                ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30" 
                : "bg-bg-elevated text-text-muted"
            }`}>
              {isGithubConnected ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
              <span>{isGithubConnected ? "CONNECTED" : "NOT CONNECTED"}</span>
            </span>
          </div>

          <form onSubmit={handleConnectGitHub} className="space-y-3 text-xs">
            <div>
              <label className="text-text-secondary block mb-1 font-mono">
                Personal Access Token (PAT) {isGithubConnected && <span className="text-text-muted">(Leave empty to keep existing)</span>}
              </label>
              <div className="relative">
                <Key size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
                <input
                  type="password"
                  placeholder={isGithubConnected ? "••••••••••••••••" : "Paste GitHub PAT (repo scope)"}
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  required={!isGithubConnected}
                  className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                />
              </div>
              <span className="text-[10px] text-text-muted block mt-0.5 font-mono">
                Requires &apos;repo&apos; or &apos;public_repo&apos; scope to create issues.
              </span>
            </div>

            <div>
              <label className="text-text-secondary block mb-1 font-mono">Target Repository (owner/repo)</label>
              <div className="relative">
                <FolderGit2 size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
                <input
                  type="text"
                  placeholder="e.g. mohammedrehan143/meetme"
                  value={githubRepo}
                  onChange={(e) => setGithubRepo(e.target.value)}
                  required
                  className="w-full bg-bg-elevated border border-border-subtle rounded pl-8 pr-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent-orange text-xs"
                />
              </div>
            </div>

            <div className="p-3 bg-bg-elevated rounded border border-border-subtle text-[11px] text-text-secondary space-y-1">
              <strong className="text-text-primary font-mono block">Automated Issue Mapping</strong>
              <p>Approved tasks will be created with priority labels, assigned owners, and full meeting transcript evidence links in the markdown body.</p>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
              {isGithubConnected ? (
                <button
                  type="button"
                  onClick={handleDisconnectGitHub}
                  className="px-3 py-1.5 rounded text-xs text-red-400 hover:text-red-300 bg-red-500/10 border border-red-500/20 flex items-center gap-1.5 transition-colors"
                >
                  <Trash2 size={12} />
                  <span>Disconnect</span>
                </button>
              ) : <div />}

              <button
                type="submit"
                disabled={savingGitHub}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Check size={13} />
                <span>{isGithubConnected ? "Update GitHub Credentials" : "Connect GitHub"}</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Synced Issues / Activity Table */}
      <div className="rounded-lg bg-bg-card border border-border-subtle overflow-hidden">
        <div className="p-3 bg-bg-secondary border-b border-border-subtle flex items-center justify-between text-xs font-mono">
          <span className="font-semibold text-text-primary uppercase tracking-wider">
            External Sync Activity Log ({activity.length})
          </span>
          <span className="text-text-muted">Jira &amp; GitHub Synced Issues</span>
        </div>

        <div className="divide-y divide-border-subtle">
          {activity.length === 0 ? (
            <div className="p-12 text-center text-xs text-text-muted">
              No issues synced to external trackers yet. Connect an integration and approve tasks to sync.
            </div>
          ) : (
            activity.map((item) => (
              <div key={item.id} className="p-3.5 hover:bg-bg-elevated/40 transition-colors flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                    item.platform === "JIRA" 
                      ? "bg-blue-600/20 text-blue-400 border border-blue-500/30" 
                      : "bg-purple-600/20 text-purple-400 border border-purple-500/30"
                  }`}>
                    {item.platform}
                  </span>

                  <div>
                    <a
                      href={item.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono font-bold text-text-primary hover:text-accent-orange flex items-center gap-1"
                    >
                      <span>{item.external_key}</span>
                      <ExternalLink size={11} className="text-text-muted" />
                    </a>
                    <span className="text-text-muted text-[11px] font-mono block">
                      Task ID: {item.task_id}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono text-text-muted">
                  <span className="px-1.5 py-0.5 text-[9px] rounded bg-accent-neon/20 text-accent-neon">
                    {item.status}
                  </span>
                  <span>{item.last_synced_at ? new Date(item.last_synced_at).toLocaleString() : "Recently"}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
