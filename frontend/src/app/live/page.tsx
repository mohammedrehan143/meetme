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

// Instant keyword-based live classifier
function classifyLiveText(text: string): {
  classification: "TASK" | "DECISION" | "BLOCKER" | "QUESTION" | "IRRELEVANT" | "GENERAL_DISCUSSION";
  detectedTask?: DetectedTask;
  detectedDecision?: DetectedDecision;
} {
  const lower = text.toLowerCase().trim();

  // 1. Task keyword detection
  const isTask = (
    /(?:assigned to|assign to|assigning to|assign this to|assigning this to|task for|action item|todo:|task:|action item for|please finish|please complete|please implement|please review|please deploy|please fix|please build|please test|please update|please prepare|please create|please configure|please audit|please handle|please write|take care of|take ownership|will complete|i will build|need to implement|responsible for|you are assigned|you're assigned|your task is|can you please|could you please|can you handle|could you handle|can you deploy|could you deploy|can you fix|could you fix|can you review|could you review|can you test|could you test|will handle)\b/i.test(text) ||
    /^(?:hey\s+)?[A-Za-z]+(?:,\s*|\s*:\s*|\s+)(?:please|can you|could you|would you|you need to|you should|you take|take\s+care|work\s+on|handle|fix|implement|deploy|review|test|build|write|create|update)\b/i.test(text) ||
    /\b[A-Za-z]+\s+(?:is assigned to|is responsible for|will handle|will deploy|will build|will implement|will test|will review)\b/i.test(text)
  );

  if (isTask) {
    let assignee: string | undefined = undefined;
    const subjMatch = text.match(/\b([A-Za-z]+)\s+(?:is assigned to|is responsible for|will handle|will deploy|will build)\b/i);
    const assignMatch = text.match(/(?:assigned to|assign to|assigning to|assign this to|task for)\s+([A-Za-z0-9_\(\)\.\-]+)/i);
    const addrMatch = text.match(/^(?:hey\s+)?([A-Za-z]+)(?:,\s*|\s*:\s*|\s+)(?:please|can you|could you|you|handle|fix|implement|deploy|review|test|build)/i);
    const trailMatch = text.match(/(?:can you|could you|please)\s+.*?[,\s]+([A-Za-z]+)\??$/i);

    if (subjMatch) assignee = subjMatch[1];
    else if (assignMatch && !["anyone", "someone", "tbd", "unassigned", "the", "a"].includes(assignMatch[1].toLowerCase())) assignee = assignMatch[1];
    else if (addrMatch && !["anyone", "someone", "everyone", "today", "tomorrow"].includes(addrMatch[1].toLowerCase())) assignee = addrMatch[1];
    else if (trailMatch && !["please", "asap", "today", "tomorrow"].includes(trailMatch[1].toLowerCase())) assignee = trailMatch[1];

    let clean = text
      .replace(/^(?:\[?[\d:]+\]?\s*)?(?:[A-Za-z0-9_\s\(\)\.\-]+?:\s*)?/, "")
      .replace(/^(?:hey\s+[A-Za-z]+[,\s]+|[A-Za-z]+,\s*|[A-Za-z]+:\s*)/i, "")
      .replace(/^(?:assign(?:ed|ing)?\s+(?:(?:this\s+)?(?:task|action\s+item)\s+)?to\s+[A-Za-z0-9_\(\)\.\-]+(?:\s*:\s*|\s+to\s+|\s+for\s+|\s+)?|[A-Za-z0-9_\(\)\.\-]+\s+is\s+assigned\s+to\s+)/i, "")
      .replace(/^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|would\s+you\s+(?:please\s+)?|i\s+will\s+|i'll\s+|need\s+to\s+|action\s+item:?\s*)/i, "")
      .replace(/,\s*[A-Za-z]+\s*\?$/, "")
      .trim();

    if (clean.length > 3) {
      clean = clean[0].toUpperCase() + clean.slice(1);
    } else {
      clean = text;
    }

    const deadlineMatch = text.match(/\bby\s+([a-zA-Z]+|\d{4}-\d{2}-\d{2})\b/i);

    return {
      classification: "TASK",
      detectedTask: {
        title: clean,
        assignee,
        priority: /(?:urgent|asap|blocker|today|critical)/i.test(text) ? "HIGH" : "MEDIUM",
        deadline: deadlineMatch ? deadlineMatch[0] : undefined
      }
    };
  }

  // 2. Decision detection
  if (/(?:decided|we decided|decision is|approved the|agreed to|we will go with|conclusion is|finalized that)\b/i.test(text)) {
    return {
      classification: "DECISION",
      detectedDecision: {
        title: text.length > 50 ? text.slice(0, 47) + "..." : text,
        summary: text
      }
    };
  }

  // 3. Blocker detection
  if (/(?:blocked on|waiting for|blocker|stuck because|cannot proceed|dependency issue|we are blocked)\b/i.test(text)) {
    return { classification: "BLOCKER" };
  }

  // 4. Irrelevant / banter
  if (/(?:hello everyone|hi all|good morning|see you guys|bye|thanks everyone)\b/i.test(text)) {
    return { classification: "IRRELEVANT" };
  }

  // 5. Default
  return { classification: "GENERAL_DISCUSSION" };
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
  const [speechActive, setSpeechActive] = useState(false);
  const speechActiveRef = useRef(false);

  const startSpeechRecognition = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setErrorMessage("Web Speech API is not supported in this browser. Please use Chrome/Edge or inject segments with the quick buttons below.");
      return;
    }

    try {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setSpeechActive(true);
        speechActiveRef.current = true;
      };

      recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          if (result && result.isFinal) {
            const transcriptText = result[0].transcript.trim();
            if (transcriptText) {
              sendTranscriptSegment(activeSpeakerRef.current || "Speaker", transcriptText);
            }
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === "not-allowed") {
          setErrorMessage("Microphone access denied for speech recognition. Please allow microphone in browser address bar.");
          setSpeechActive(false);
          speechActiveRef.current = false;
        }
      };

      recognition.onend = () => {
        if (speechActiveRef.current) {
          try {
            recognition.start();
          } catch {
            setTimeout(() => {
              if (speechActiveRef.current) {
                try { recognition.start(); } catch {}
              }
            }, 600);
          }
        } else {
          setSpeechActive(false);
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
      setSpeechActive(true);
      speechActiveRef.current = true;
    } catch (e: any) {
      console.warn("Speech recognition start notice:", e);
      setErrorMessage("Speech recognition start notice: " + (e.message || String(e)));
    }
  };

  const stopSpeechRecognition = () => {
    speechActiveRef.current = false;
    setSpeechActive(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
  };

  const toggleSpeechRecognition = () => {
    if (speechActive) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  };

  const handleAudioChunk = (blob: Blob) => {
    // Transmit tab & mixed audio chunk (when user wears earphones and shares Google Meet tab)
    if (blob && blob.size > 1000 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Data = (reader.result as string)?.split(",")[1];
          if (base64Data && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                type: "AUDIO_CHUNK",
                speaker: activeSpeakerRef.current || "Speaker",
                timestamp: formatDuration(audioState.durationSeconds),
                audio_data: base64Data,
              })
            );
          }
        };
        reader.readAsDataURL(blob);
      } catch (e) {
        console.warn("Could not encode audio chunk:", e);
      }
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
    let wsUrl = `ws://localhost:8000/ws/live-meeting/${mtgId}`;
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      if (host === "localhost" || host === "127.0.0.1") {
        wsUrl = `ws://${host}:8000/ws/live-meeting/${mtgId}`;
      } else if (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL.trim() !== "") {
        wsUrl = `${process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "")}/ws/live-meeting/${mtgId}`;
      }
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
            // Update / enrich detected tasks from backend
            if (msg.detected_task) {
              setDetectedTasks((prev) => {
                const matchIdx = prev.findIndex(
                  (t) => t.title.toLowerCase() === msg.detected_task.title?.toLowerCase()
                );
                if (matchIdx >= 0) {
                  const updated = [...prev];
                  updated[matchIdx] = { ...updated[matchIdx], ...msg.detected_task };
                  return updated;
                }
                return [...prev, msg.detected_task];
              });
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
      let createdId = meetingId;
      if (!createdId) {
        try {
          const created = await api.createMeeting(meetingTitle, "LIVE");
          createdId = created.id;
          setMeetingId(createdId);
        } catch {
          createdId = `mtg-${Date.now()}`;
          setMeetingId(createdId);
        }
      }

      // 1. Connect WebSocket
      connectWebSocket(createdId);

      // 2. Start Real-time Speech-to-Text Recognition immediately
      startSpeechRecognition();

      // 3. Start Audio Capture (Microphone + optional tab audio)
      try {
        await startCapture(captureTabAudio);
      } catch (audioErr: any) {
        console.warn("Tab/Mic audio notice (Speech recognition is active):", audioErr.message);
      }

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
      const fullText = transcriptSegments
        .map((s) => `[${s.timestamp}] ${s.speaker}: ${s.text}`)
        .join("\n");

      try {
        await api.processMeeting(meetingId, fullText);
        router.push("/approvals");
      } catch (err) {
        console.error("End meeting process error:", err);
        router.push("/meetings");
      }
    }
  };

  // Helper to send transcript chunk through WebSocket with instant client-side keyword classification
  const sendTranscriptSegment = (speaker: string, text: string, timestamp?: string) => {
    if (!text.trim()) return;
    const ts = timestamp || formatDuration(audioState.durationSeconds);

    // 1. Instant keyword-based categorization
    const { classification, detectedTask, detectedDecision } = classifyLiveText(text);

    // 2. Instant local UI update
    setTranscriptSegments((prev) => [
      ...prev,
      {
        speaker,
        text,
        timestamp: ts,
        classification,
      },
    ]);

    if (detectedTask) {
      setDetectedTasks((prev) => {
        if (prev.some((t) => t.title.toLowerCase() === detectedTask.title.toLowerCase())) {
          return prev;
        }
        return [...prev, detectedTask];
      });
    }

    if (detectedDecision) {
      setDetectedDecisions((prev) => [...prev, detectedDecision]);
    }

    // 3. Forward to backend WebSocket if connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
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
          {/* Real-time Speech-to-Text Toggle */}
          <button
            type="button"
            onClick={toggleSpeechRecognition}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold border transition-all ${
              speechActive
                ? "bg-accent-neon/20 text-accent-neon border-accent-neon/50 shadow-sm"
                : "bg-bg-card text-text-secondary border-border-subtle hover:border-border-strong hover:text-text-primary"
            }`}
            title="Toggle speech recognition"
          >
            <Mic size={14} className={speechActive ? "text-accent-neon animate-pulse" : "text-text-muted"} />
            <span>{speechActive ? "🎙️ STT: Listening..." : "🎙️ STT: Start Speech"}</span>
          </button>

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

          {/* Quick Response & Task Triggers Bar */}
          <div className="p-2.5 bg-bg-secondary border-t border-border-subtle space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-accent-orange uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles size={12} /> Quick Responses & Task Triggers:
              </span>
              <span className="text-[9px] font-mono text-text-muted">Click to instantly test task categorization</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { label: "⚡ Rahul: Deploy frontend", text: "Rahul, please deploy the frontend by Friday", type: "task" },
                { label: "⚡ Alex: Review PR", text: "Assigning this task to Alex: review the pull request", type: "task" },
                { label: "⚡ Elena: Build migration", text: "Elena, can you please build the database migration?", type: "task" },
                { label: "⚡ Marcus: Run QA tests", text: "Marcus, please run the end-to-end test suite today", type: "task" },
                { label: "⚡ David: Load balancer", text: "David is assigned to configure the load balancer", type: "task" },
                { label: "💬 Discussion: Roadmap", text: "Let's review the quarterly product roadmap and team bandwidth", type: "general" },
                { label: "🎯 Decision: Groq engine", text: "We decided to use Groq for sub-second agent inference", type: "decision" },
                { label: "🛑 Blocker: Credentials", text: "We are blocked waiting for deployment cloud credentials", type: "blocker" },
              ].map((item, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    sendTranscriptSegment(activeSpeakerRef.current || "Speaker", item.text);
                  }}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-full border transition-all ${
                    item.type === "task"
                      ? "bg-accent-orange/15 border-accent-orange/40 text-accent-orange hover:bg-accent-orange/25"
                      : item.type === "decision"
                      ? "bg-accent-neon/15 border-accent-neon/40 text-accent-neon hover:bg-accent-neon/25"
                      : item.type === "blocker"
                      ? "bg-red-500/15 border-red-500/40 text-red-400 hover:bg-red-500/25"
                      : "bg-bg-card border-border-subtle text-text-secondary hover:text-text-primary hover:border-border-strong"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Speech / Transcript Segment Input */}
          <form onSubmit={handleSendManual} className="p-3 border-t border-border-subtle bg-bg-card flex flex-wrap sm:flex-nowrap items-center gap-2">
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
              placeholder="Type speech segment (e.g. 'Rahul, please deploy the backend')..."
              className="flex-1 min-w-[200px] bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
            />
            <button
              type="submit"
              className="px-3.5 py-1.5 bg-accent-orange text-black font-semibold hover:bg-accent-orange-hover text-xs rounded transition-colors shadow-sm"
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
