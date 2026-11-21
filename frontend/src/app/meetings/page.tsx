"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { History, Calendar, Clock, ArrowRight, CheckCircle2, Radio, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { Meeting } from "@/lib/types";

export default function MeetingHistoryPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    setLoading(true);
    try {
      const data = await api.getMeetings();
      setMeetings(data);
    } catch (err) {
      console.error("Failed to load meetings:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-4">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Meeting Intelligence Archives</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Ingested meetings, structured transcripts, extracted action items, and decision logs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/recorded"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-bg-card border border-border-subtle hover:border-border-strong text-text-primary rounded text-xs font-medium transition-colors"
          >
            <Upload size={13} />
            <span>Upload Recording</span>
          </Link>
          <Link
            href="/live"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent-orange text-black font-semibold rounded text-xs hover:bg-accent-orange-hover transition-colors"
          >
            <Radio size={13} />
            <span>Start Live Sync</span>
          </Link>
        </div>
      </div>

      <div className="rounded bg-bg-card border border-border-subtle divide-y divide-border-subtle">
        {meetings.length === 0 ? (
          <div className="p-12 text-center text-xs text-text-muted space-y-2">
            <History size={24} className="mx-auto text-text-muted" />
            <p>No meetings found in this workspace.</p>
          </div>
        ) : (
          meetings.map((m) => (
            <Link
              key={m.id}
              href={`/meetings/${m.id}`}
              className="p-4 flex items-center justify-between hover:bg-bg-elevated/40 transition-colors"
            >
              <div className="space-y-1.5">
                <div className="flex items-center gap-2.5">
                  <span className="text-sm font-semibold text-text-primary">{m.title}</span>
                  <span
                    className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded ${
                      m.status === "COMPLETED"
                        ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30"
                        : m.status === "LIVE"
                        ? "bg-accent-orange/20 text-accent-orange animate-pulse"
                        : "bg-bg-elevated text-text-secondary"
                    }`}
                  >
                    {m.status}
                  </span>
                  <span className="text-[10px] font-mono text-text-muted uppercase px-1.5 py-0.5 rounded bg-bg-elevated">
                    {m.recording_mode}
                  </span>
                </div>

                {m.summary && (
                  <p className="text-xs text-text-secondary line-clamp-1 max-w-2xl leading-relaxed">
                    {m.summary}
                  </p>
                )}

                <div className="flex items-center gap-4 text-[11px] text-text-muted font-mono">
                  <span className="flex items-center gap-1">
                    <Calendar size={12} />
                    {m.date ? new Date(m.date).toLocaleDateString() : "Recent"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {Math.round(m.duration_seconds / 60)} mins
                  </span>
                  <span className="text-accent-orange font-semibold">
                    {m.tasks_count} Action Items Extracted
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-text-secondary hover:text-text-primary text-xs font-mono">
                <span>View Intelligence</span>
                <ArrowRight size={13} />
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
