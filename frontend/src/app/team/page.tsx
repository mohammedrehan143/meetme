"use client";

import React, { useEffect, useState } from "react";
import { Users, UserPlus, Mail, Shield, CheckCircle2, RotateCw, X } from "lucide-react";
import { api } from "@/lib/api";
import { TeamMember } from "@/lib/types";

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [title, setTitle] = useState("Team Member");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadMembers();
  }, []);

  const loadMembers = async () => {
    setLoading(true);
    try {
      const data = await api.getTeam();
      setMembers(data);
    } catch (err) {
      console.error("Failed to load members:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setSaving(true);
    try {
      await api.createTeamMember({
        full_name: name.trim(),
        email: email.trim(),
        role,
        title: title.trim() || "Team Member",
      });
      setShowInviteModal(false);
      setName("");
      setEmail("");
      setTitle("Team Member");
      await loadMembers();
    } catch (err: any) {
      alert(`Could not add member: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users size={18} className="text-accent-orange" />
            <h1 className="text-xl font-bold text-text-primary">Workspace Team &amp; Speaker Registry</h1>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Verified team members for speaker diarization matching, task ownership assignment, and email dispatches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover transition-colors"
          >
            <UserPlus size={13} />
            <span>Add Member</span>
          </button>
          <button
            onClick={loadMembers}
            className="p-1.5 rounded bg-bg-card border border-border-subtle hover:border-border-strong text-text-secondary hover:text-text-primary"
            title="Refresh"
          >
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Members Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {members.map((m) => (
          <div
            key={m.id}
            className="p-4 rounded bg-bg-card border border-border-subtle hover:border-border-strong transition-colors space-y-3"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded bg-bg-elevated border border-border-subtle flex items-center justify-center font-mono font-bold text-xs text-accent-orange">
                  {m.full_name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">{m.full_name}</h3>
                  <p className="text-xs text-text-secondary">{m.title}</p>
                </div>
              </div>

              <span
                className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded uppercase ${
                  m.role === "admin"
                    ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30"
                    : "bg-bg-elevated text-text-secondary border border-border-subtle"
                }`}
              >
                {m.role}
              </span>
            </div>

            <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-xs font-mono text-text-secondary">
              <div className="flex items-center gap-1 text-text-primary">
                <Mail size={12} className="text-text-muted" />
                <span>{m.email}</span>
              </div>
              <div>
                Tasks: <strong className="text-accent-orange">{m.tasks_count}</strong> ({m.completed_tasks} done)
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleCreateMember}
            className="bg-bg-card border border-border-subtle rounded-lg max-w-md w-full p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                Add Team Member to Registry
              </h3>
              <button
                type="button"
                onClick={() => setShowInviteModal(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-text-secondary block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Mercer"
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>

              <div>
                <label className="text-text-secondary block mb-1">Verified Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. alex@meetme.work"
                  className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-text-secondary block mb-1">Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Staff Engineer"
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                  />
                </div>
                <div>
                  <label className="text-text-secondary block mb-1">Role</label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-orange"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-border-subtle">
              <button
                type="button"
                onClick={() => setShowInviteModal(false)}
                className="px-3 py-1.5 rounded text-xs text-text-secondary hover:text-text-primary bg-bg-elevated"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover"
              >
                {saving ? "Adding..." : "Add Member"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
