"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  Radio, 
  Mic, 
  MicOff, 
  Pause, 
  Play, 
  Square, 
  CheckCircle2, 
  AlertTriangle, 
  Volume2, 
  ShieldCheck, 
  Layers, 
  Clock, 
  CheckSquare, 
  HelpCircle,
  Sparkles
} from "lucide-react";
import { useAudioCapture } from "@/hooks/useAudioCapture";
import { api } from "@/lib/api";

interface LiveSegment {
  speaker: string;
  text: string;
  timestamp: string;
  classification: string;
}

interface DetectedTask {
  title: string;
  assignee?: string;
  priority: string;
  deadline?: string;
}

interface DetectedDecision {
  title: string;
  summary: string;
}

export default function LiveMeetingPage() {
  const router = useRouter();
  const [meetingTitle, setMeetingTitle] = useState("Live Execution Sync");
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [consentAcknowledged, setConsentAcknowledged] = useState(false);
  const [captureTabAudio, setCaptureTabAudio] = useState(true);
  const [transcriptSegments, setTranscriptSegments] = useState<LiveSegment[]>([]);
  const [detectedTasks, setDetectedTasks] = useState<DetectedTask[]>([]);
  const [detectedDecisions, setDetectedDecisions] = useState<DetectedDecision[]>([]);
  const [simulatedSpeakers] = useState(["Sarah Chen", "Rahul Sharma", "Elena Rostova", "Marcus Vance"]);
  const [speakerIndex, setSpeakerIndex] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  const handleAudioChunk = (blob: Blob) => {
    // When a 4-second audio chunk is generated:
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send status or chunk marker
    }
  };

  const {
    state: audioState,
    startCapture,
    stopCapture,
    pauseCapture,
    resumeCapture,
    toggleMicMute,
  } = useAudioCapture(handleAudioChunk);

  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcriptSegments]);

  // Connect WebSocket when meeting starts
  const connectWebSocket = (mtgId: string) => {
    let wsUrl = `ws://127.0.0.1:8000/ws/live-meeting/${mtgId}`;
    if (process.env.NEXT_PUBLIC_WS_URL) {
      wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/live-meeting/${mtgId}`;
    } else if (process.env.NEXT_PUBLIC_API_URL) {
      const clean = process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws").replace(/\/api\/?$/, "");
      wsUrl = `${clean}/ws/live-meeting/${mtgId}`;
    } else if (typeof window !== "undefined" && !window.location.origin.includes("localhost")) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${proto}//${window.location.host}/ws/live-meeting/${mtgId}`;
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setWsConnected(true);
      console.log("Connected to Live Meeting WebSocket");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "LIVE_TRANSCRIPT_SEGMENT") {
          setTranscriptSegments((prev) => [
            ...prev,
            {
              speaker: msg.speaker,
              text: msg.text,
              timestamp: msg.timestamp,
              classification: msg.classification,
            },
          ]);

          if (msg.detected_task) {
            setDetectedTasks((prev) => [...prev, msg.detected_task]);
          }
          if (msg.detected_decision) {
            setDetectedDecisions((prev) => [...prev, msg.detected_decision]);
          }
        }
      } catch (err) {
        console.error("WS Parse error:", err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log("Live Meeting WebSocket closed");
    };

    wsRef.current = ws;
  };

  const handleStartMeeting = async () => {
    if (!consentAcknowledged) {
      alert("Please confirm participant consent before recording.");
      return;
    }

    try {
      // 1. Create meeting in database
      const created = await api.createMeeting(meetingTitle, "LIVE");
      setMeetingId(created.id);

      // 2. Start WebSocket
      connectWebSocket(created.id);

      // 3. Start Audio Capture (getDisplayMedia + getUserMedia)
      await startCapture(captureTabAudio);

      // Seed initial greeting segment
      setTimeout(() => {
        sendTranscriptSegment(
          "Sarah Chen",
          "Meeting started. Let's align on sprint tasks and finalize assignments.",
          "00:00:03"
        );
      }, 2000);

    } catch (err: any) {
      alert(`Could not start meeting: ${err.message}`);
    }
  };

  const handleEndMeeting = async () => {
    stopCapture();
    if (wsRef.current) {
      wsRef.current.close();
    }

    if (meetingId) {
      // Send all collected transcript lines to orchestrator for full task extraction and approvals
      const fullText = transcriptSegments
        .map((s) => `[${s.timestamp}] ${s.speaker}: ${s.text}`)
        .join("\n");

      try {
        const formData = new FormData();
        const blob = new Blob([fullText], { type: "text/plain" });
        formData.append("file", blob, `${meetingTitle}.txt`);
        formData.append("title", meetingTitle);

        await api.uploadMeeting(formData);
        router.push("/approvals");
      } catch (err) {
        console.error("End meeting upload error:", err);
        router.push("/meetings");
      }
    }
  };

  // Helper to send transcript chunk through WebSocket
  const sendTranscriptSegment = (speaker: string, text: string, timestamp?: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const ts = timestamp || formatDuration(audioState.durationSeconds);
      wsRef.current.send(
        JSON.stringify({
          type: "TRANSCRIPT_CHUNK",
          speaker,
          text,
          timestamp: ts,
        })
      );
    }
  };

  const [manualInput, setManualInput] = useState("");
  const handleSendManual = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualInput.trim()) return;
    const currentSpeaker = simulatedSpeakers[speakerIndex % simulatedSpeakers.length];
    sendTranscriptSegment(currentSpeaker, manualInput.trim());
    setManualInput("");
    setSpeakerIndex((s) => s + 1);
  };

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border-subtle gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-accent-orange animate-pulse"></span>
            <input
              type="text"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
              disabled={audioState.isRecording}
              className="bg-transparent font-bold text-lg text-text-primary focus:outline-none focus:border-b border-accent-orange transition-colors"
            />
          </div>
          <p className="text-xs text-text-secondary">
            Dual-stream audio capture &bull; Real-time AI classification &bull; Instant task detection
          </p>
        </div>

        {/* Live Meeting Controls */}
        <div className="flex items-center gap-2">
          {!audioState.isRecording ? (
            <button
              onClick={handleStartMeeting}
              className="flex items-center gap-1.5 px-4 py-2 bg-accent-orange text-black font-semibold rounded text-xs hover:bg-accent-orange-hover transition-colors shadow-sm"
            >
              <Radio size={14} />
              <span>Start Live Meeting</span>
            </button>
          ) : (
            <>
              <button
                onClick={toggleMicMute}
                className={`p-2 rounded text-xs border transition-colors ${
                  audioState.isMicMuted
                    ? "bg-red-500/20 text-red-400 border-red-500/30"
                    : "bg-bg-card text-text-primary border-border-subtle hover:border-border-strong"
                }`}
                title={audioState.isMicMuted ? "Unmute Mic" : "Mute Mic"}
              >
                {audioState.isMicMuted ? <MicOff size={15} /> : <Mic size={15} />}
              </button>

              {audioState.isPaused ? (
                <button
                  onClick={resumeCapture}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-bg-card border border-border-subtle text-accent-neon hover:border-accent-neon flex items-center gap-1.5"
                >
                  <Play size={13} />
                  <span>Resume</span>
                </button>
              ) : (
                <button
                  onClick={pauseCapture}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-bg-card border border-border-subtle text-text-primary hover:border-border-strong flex items-center gap-1.5"
                >
                  <Pause size={13} />
                  <span>Pause</span>
                </button>
              )}

              <button
                onClick={handleEndMeeting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded text-xs transition-colors"
              >
                <Square size={13} />
                <span>End Meeting</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Consent & Permission Banner */}
      {!audioState.isRecording && (
        <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-3">
          <div className="flex items-start gap-2.5">
            <ShieldCheck size={18} className="text-accent-neon shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-text-primary">Participant Consent & Browser Audio Capture Requirements</h4>
              <p className="text-[11px] text-text-secondary leading-relaxed">
                MEETME captures microphone audio and browser tab audio via Web Audio API. 
                When prompted by your browser, select the meeting tab (e.g., Google Meet, Zoom Web, or Teams) and ensure 
                <strong className="text-text-primary font-mono"> &quot;Share tab audio&quot; </strong> is checked.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-border-subtle text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={captureTabAudio}
                onChange={(e) => setCaptureTabAudio(e.target.checked)}
                className="accent-accent-orange rounded"
              />
              <span className="text-text-secondary">Capture browser tab audio (alongside microphone)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consentAcknowledged}
                onChange={(e) => setConsentAcknowledged(e.target.checked)}
                className="accent-accent-orange rounded"
              />
              <span className="text-text-primary font-medium">All participants have consented to AI recording</span>
            </label>
          </div>
        </div>
      )}

      {/* Live Status Indicators Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded bg-bg-card border border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={15} className="text-text-secondary" />
            <span className="text-xs font-mono text-text-secondary">Duration</span>
          </div>
          <span className="font-mono font-bold text-sm text-text-primary">
            {formatDuration(audioState.durationSeconds)}
          </span>
        </div>

        <div className="p-3 rounded bg-bg-card border border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio size={15} className={audioState.isRecording ? "text-accent-orange" : "text-text-muted"} />
            <span className="text-xs font-mono text-text-secondary">Stream Mode</span>
          </div>
          <span className={`text-xs font-mono font-bold ${
            audioState.isRecording ? "text-accent-orange animate-pulse" : "text-text-muted"
          }`}>
            {audioState.isRecording ? (audioState.isPaused ? "PAUSED" : "LIVE CAPTURE") : "STANDBY"}
          </span>
        </div>

        <div className="p-3 rounded bg-bg-card border border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Mic size={15} className={audioState.isMicMuted ? "text-red-400" : "text-accent-neon"} />
            <span className="text-xs font-mono text-text-secondary">Mic & Tab</span>
          </div>
          <span className="text-xs font-mono font-bold text-accent-neon">
            {audioState.isRecording ? (audioState.hasTabAudio ? "DUAL MIX" : "MIC ONLY") : "STANDBY"}
          </span>
        </div>

        <div className="p-3 rounded bg-bg-card border border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers size={15} className="text-text-secondary" />
            <span className="text-xs font-mono text-text-secondary">WebSocket</span>
          </div>
          <span className={`text-xs font-mono font-bold ${wsConnected ? "text-accent-neon" : "text-text-muted"}`}>
            {wsConnected ? "CONNECTED" : "OFFLINE"}
          </span>
        </div>
      </div>

      {/* Main Live Workspace: 2-Column Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Streaming Transcript Feed */}
        <div className="lg:col-span-2 rounded bg-bg-card border border-border-subtle flex flex-col h-[520px]">
          <div className="p-3.5 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-neon animate-pulse"></div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Real-Time Transcript Feed
              </h3>
            </div>
            <span className="text-[10px] font-mono text-text-muted">
              {transcriptSegments.length} Segments
            </span>
          </div>

          {/* Transcript Scroll Area */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 font-sans">
            {transcriptSegments.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-text-muted space-y-2">
                <Volume2 size={24} className="text-text-muted" />
                <p className="text-xs">
                  {audioState.isRecording
                    ? "Listening to conversation... Speaking turns will appear here with instant AI classification."
                    : "Start the meeting to initiate audio capture and real-time transcription."}
                </p>
              </div>
            ) : (
              transcriptSegments.map((seg, idx) => (
                <div key={idx} className="p-3 rounded bg-bg-elevated/70 border border-border-subtle text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text-primary">{seg.speaker}</span>
                      <span className="text-[10px] font-mono text-text-muted">{seg.timestamp}</span>
                    </div>
                    <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${
                      seg.classification === "TASK" ? "bg-accent-orange/20 text-accent-orange border border-accent-orange/30" :
                      seg.classification === "DECISION" ? "bg-accent-neon/20 text-accent-neon border border-accent-neon/30" :
                      seg.classification === "BLOCKER" ? "bg-red-500/20 text-red-400 border border-red-500/30" :
                      "bg-bg-card text-text-muted border border-border-subtle"
                    }`}>
                      {seg.classification}
                    </span>
                  </div>
                  <p className="text-text-primary leading-relaxed text-xs">{seg.text}</p>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>

          {/* Live Simulated / Quick Speech Input */}
          <form onSubmit={handleSendManual} className="p-3 border-t border-border-subtle bg-bg-secondary flex gap-2">
            <div className="text-[11px] font-mono text-text-muted self-center shrink-0">
              Speaker: <strong className="text-text-primary">{simulatedSpeakers[speakerIndex % simulatedSpeakers.length]}</strong>
            </div>
            <input
              type="text"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Inject speech segment or transcribe chunk..."
              className="flex-1 bg-bg-card border border-border-subtle rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
            />
            <button
              type="submit"
              disabled={!audioState.isRecording}
              className="px-3 py-1.5 bg-bg-elevated border border-border-subtle hover:border-accent-orange text-xs text-text-primary rounded disabled:opacity-40"
            >
              Inject Segment
            </button>
          </form>
        </div>

        {/* Right 1 Col: Live Detected Actions & Decisions */}
        <div className="space-y-4">
          {/* Live Tasks Detected */}
          <div className="rounded bg-bg-card border border-border-subtle p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2">
              <div className="flex items-center gap-1.5">
                <CheckSquare size={14} className="text-accent-orange" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Live Detected Tasks ({detectedTasks.length})
                </h4>
              </div>
              <span className="text-[9px] font-mono text-accent-orange">STREAMING</span>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto">
              {detectedTasks.length === 0 ? (
                <p className="text-[11px] text-text-muted text-center py-4">
                  No action items identified yet. Tasks spoken during meeting will trigger here.
                </p>
              ) : (
                detectedTasks.map((t, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-bg-elevated border border-border-subtle text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-text-primary">{t.title}</span>
                      <span className="text-[9px] font-mono text-accent-orange font-bold">{t.priority}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-text-secondary font-mono">
                      <span>Owner: {t.assignee || "Pending"}</span>
                      {t.deadline && <span>Due: {t.deadline}</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Live Decisions Detected */}
          <div className="rounded bg-bg-card border border-border-subtle p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2">
              <div className="flex items-center gap-1.5">
                <Sparkles size={14} className="text-accent-neon" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Live Decisions ({detectedDecisions.length})
                </h4>
              </div>
              <span className="text-[9px] font-mono text-accent-neon">STREAMING</span>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto">
              {detectedDecisions.length === 0 ? (
                <p className="text-[11px] text-text-muted text-center py-4">
                  Decisions agreed upon during conversation will be recorded here.
                </p>
              ) : (
                detectedDecisions.map((d, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-bg-elevated border border-border-subtle text-xs space-y-1">
                    <span className="font-semibold text-text-primary">{d.title}</span>
                    <p className="text-[11px] text-text-secondary">{d.summary}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
