"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
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
  const [consentAcknowledged, setConsentAcknowledged] = useState(true);
  const [captureTabAudio, setCaptureTabAudio] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [transcriptSegments, setTranscriptSegments] = useState<LiveSegment[]>([]);
  const [detectedTasks, setDetectedTasks] = useState<DetectedTask[]>([]);
  const [detectedDecisions, setDetectedDecisions] = useState<DetectedDecision[]>([]);
  const [activeSpeaker, setActiveSpeaker] = useState("Speaker");
  const [teamMembers, setTeamMembers] = useState<string[]>([]);
  const activeSpeakerRef = useRef("Speaker");

  useEffect(() => {
    activeSpeakerRef.current = activeSpeaker;
  }, [activeSpeaker]);

  useEffect(() => {
    const fetchTeam = async () => {
      try {
        const team = await api.getTeam();
        if (team && team.length > 0) {
          const names = team.map((m) => m.full_name);
          setTeamMembers(names);
          setActiveSpeaker(names[0]);
          activeSpeakerRef.current = names[0];
        }
      } catch {
        // ignore
      }
    };
    fetchTeam();
  }, []);

  const wsRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);

  const startSpeechRecognition = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.log("Web Speech API not available in this browser. You can type or paste segments manually.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        const lastIdx = event.results.length - 1;
        const result = event.results[lastIdx];
        if (result && result.isFinal) {
          const transcriptText = result[0].transcript.trim();
          if (transcriptText) {
            sendTranscriptSegment(activeSpeakerRef.current || "Speaker", transcriptText);
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition notice:", event.error);
      };

      recognition.onend = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          try {
            recognition.start();
          } catch {}
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (e) {
      console.warn("Speech recognition notice:", e);
    }
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
  };

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
    let wsUrl = `wss://meetme-8r0u.onrender.com/ws/live-meeting/${mtgId}`;
    if (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL.trim() !== "") {
      wsUrl = `${process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "")}/ws/live-meeting/${mtgId}`;
    } else if (typeof window !== "undefined" && window.location.protocol === "http:" && window.location.hostname === "localhost" && process.env.NEXT_PUBLIC_API_URL?.includes("127.0.0.1")) {
      wsUrl = `ws://127.0.0.1:8000/ws/live-meeting/${mtgId}`;
    }

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        console.log("Connected to Live Meeting WebSocket:", wsUrl);
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

      ws.onerror = (err) => {
        console.warn("Live Meeting WebSocket warning:", err);
      };

      wsRef.current = ws;
    } catch (e) {
      console.warn("Could not open WebSocket, falling back to local state:", e);
    }
  };

  const handleStartMeeting = async () => {
    setErrorMessage(null);
    if (!consentAcknowledged) {
      setErrorMessage("Please acknowledge participant consent before recording audio.");
      return;
    }

    try {
      // 1. Create meeting in database
      const created = await api.createMeeting(meetingTitle, "LIVE");
      setMeetingId(created.id);

      // 2. Start WebSocket
      connectWebSocket(created.id);

      // 3. Start Audio Capture (getDisplayMedia for Google Meet tab + getUserMedia)
      await startCapture(captureTabAudio);

      // 4. Start Real-time Speech-to-Text Recognition
      startSpeechRecognition();

    } catch (err: any) {
      console.error("Start meeting error:", err);
      setErrorMessage(err.message || "Could not start meeting.");
    }
  };

  const handleEndMeeting = async () => {
    stopCapture();
    stopSpeechRecognition();
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
    sendTranscriptSegment(activeSpeaker.trim() || "Speaker", manualInput.trim());
    setManualInput("");
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

      {/* Error / Alert Notification Banner */}
      {errorMessage && (
        <div className="p-3.5 rounded bg-red-950/40 border border-red-500/40 text-red-200 text-xs flex items-start justify-between gap-3 animate-fade-in">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-white">Live Capture Notice:</span>
              <p className="text-[11px] text-red-200/90 leading-relaxed">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-red-400 hover:text-white text-xs font-mono px-2 py-0.5 rounded bg-red-900/40"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Google Meet & Screen Audio Capture Guide Banner */}
      {!audioState.isRecording && (
        <div className="p-4 rounded bg-bg-card border border-accent-orange/30 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <ShieldCheck size={18} className="text-accent-neon shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-text-primary">
                  How to Hook into an Active Google Meet / Zoom Call
                </h4>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Web browsers require explicit permission to capture audio from other tabs. Follow these 3 steps:
                </p>
              </div>
            </div>
            <Link
              href="/recorded"
              className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-accent-orange hover:underline whitespace-nowrap"
            >
              <span>Have transcript / notes? Paste here &rarr;</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1 text-xs">
            <div className="p-2.5 rounded bg-bg-elevated/60 border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono font-bold text-accent-orange">STEP 1</span>
              <p className="text-[11px] text-text-primary font-medium">Click &quot;Start Live Meeting&quot;</p>
              <p className="text-[10px] text-text-muted">Initiates dual-stream audio session and cloud multi-agent listener.</p>
            </div>
            <div className="p-2.5 rounded bg-bg-elevated/60 border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono font-bold text-accent-neon">STEP 2</span>
              <p className="text-[11px] text-text-primary font-medium">Select &quot;Chrome Tab&quot;</p>
              <p className="text-[10px] text-text-muted">In Chrome&apos;s system popup, choose your active Google Meet tab.</p>
            </div>
            <div className="p-2.5 rounded bg-bg-elevated/60 border border-border-subtle space-y-1">
              <span className="text-[10px] font-mono font-bold text-accent-orange">STEP 3</span>
              <p className="text-[11px] text-text-primary font-medium">Check &quot;Also share tab audio&quot;</p>
              <p className="text-[10px] text-text-muted">Toggle the audio checkbox at the bottom-left of Chrome&apos;s modal and click Share.</p>
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
              <span className="text-text-secondary">Capture browser tab audio (Google Meet remote participants)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consentAcknowledged}
                onChange={(e) => setConsentAcknowledged(e.target.checked)}
                className="accent-accent-orange rounded"
              />
              <span className="text-text-primary font-medium">All meeting participants consent to AI action extraction</span>
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

          {/* Quick Speech / Transcript Segment Input */}
          <form onSubmit={handleSendManual} className="p-3 border-t border-border-subtle bg-bg-secondary flex flex-wrap sm:flex-nowrap items-center gap-2">
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-[11px] font-mono text-text-muted">Speaker:</span>
              {teamMembers.length > 0 ? (
                <select
                  value={activeSpeaker}
                  onChange={(e) => setActiveSpeaker(e.target.value)}
                  className="bg-bg-card border border-border-subtle rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-accent-orange font-mono"
                >
                  {teamMembers.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                  <option value="Speaker">Other Speaker</option>
                </select>
              ) : (
                <input
                  type="text"
                  value={activeSpeaker}
                  onChange={(e) => setActiveSpeaker(e.target.value)}
                  placeholder="Speaker"
                  className="w-24 bg-bg-card border border-border-subtle rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-accent-orange font-mono"
                />
              )}
            </div>
            <input
              type="text"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Inject speech segment or transcribe chunk..."
              className="flex-1 min-w-[200px] bg-bg-card border border-border-subtle rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
            />
            <button
              type="submit"
              disabled={!audioState.isRecording}
              className="px-3 py-1.5 bg-bg-elevated border border-border-subtle hover:border-accent-orange text-xs text-text-primary rounded disabled:opacity-40 transition-colors"
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
