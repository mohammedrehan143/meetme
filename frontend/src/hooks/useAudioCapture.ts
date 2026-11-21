"use client";

import { useState, useRef, useCallback } from "react";

export interface AudioCaptureState {
  isRecording: boolean;
  isPaused: boolean;
  isMicMuted: boolean;
  hasTabAudio: boolean;
  hasMicAudio: boolean;
  tabAudioLevel: number;
  micAudioLevel: number;
  durationSeconds: number;
  error: string | null;
}

export function useAudioCapture(onAudioChunk?: (blob: Blob) => void) {
  const [state, setState] = useState<AudioCaptureState>({
    isRecording: false,
    isPaused: false,
    isMicMuted: false,
    hasTabAudio: false,
    hasMicAudio: false,
    tabAudioLevel: 0,
    micAudioLevel: 0,
    durationSeconds: 0,
    error: null,
  });

  const micStreamRef = useRef<MediaStream | null>(null);
  const tabStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const startCapture = useCallback(async (captureTabAudio: boolean = true) => {
    setState((prev) => ({ ...prev, error: null }));

    try {
      // 1. Microphone capture
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      micStreamRef.current = micStream;

      // 2. Tab audio capture (getDisplayMedia)
      let tabStream: MediaStream | null = null;
      let hasTab = false;

      if (captureTabAudio && navigator.mediaDevices.getDisplayMedia) {
        try {
          tabStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: true, // Requires user to share audio
          });
          
          // Verify audio tracks exist in tab stream
          const audioTracks = tabStream.getAudioTracks();
          if (audioTracks.length > 0) {
            hasTab = true;
            tabStreamRef.current = tabStream;
          } else {
            console.warn("No audio track detected in screen/tab capture. Microphone only.");
          }
        } catch (tabErr) {
          console.warn("Tab audio permission dismissed or not granted, continuing with mic:", tabErr);
        }
      }

      // 3. Web Audio API Mixing
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioCtx();
      audioContextRef.current = audioContext;

      const destination = audioContext.createMediaStreamDestination();

      // Connect mic
      const micSource = audioContext.createMediaStreamSource(micStream);
      const micGain = audioContext.createGain();
      micSource.connect(micGain);
      micGain.connect(destination);

      // Connect tab if present
      let tabGain: GainNode | null = null;
      if (tabStream && hasTab) {
        const tabSource = audioContext.createMediaStreamSource(tabStream);
        tabGain = audioContext.createGain();
        tabSource.connect(tabGain);
        tabGain.connect(destination);
      }

      // 4. MediaRecorder on mixed stream
      const mixedStream = destination.stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const mediaRecorder = new MediaRecorder(mixedStream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && onAudioChunk) {
          onAudioChunk(event.data);
        }
      };

      // Emit chunk every 4 seconds for real-time transcription
      mediaRecorder.start(4000);

      // Timer
      let seconds = 0;
      timerRef.current = setInterval(() => {
        seconds++;
        setState((prev) => ({ ...prev, durationSeconds: seconds }));
      }, 1000);

      setState({
        isRecording: true,
        isPaused: false,
        isMicMuted: false,
        hasTabAudio: hasTab,
        hasMicAudio: true,
        tabAudioLevel: 0.5,
        micAudioLevel: 0.7,
        durationSeconds: 0,
        error: null,
      });

    } catch (err: any) {
      console.error("Audio capture failed:", err);
      setState((prev) => ({
        ...prev,
        isRecording: false,
        error: err.message || "Failed to access microphone or tab audio.",
      }));
    }
  }, [onAudioChunk]);

  const toggleMicMute = useCallback(() => {
    if (micStreamRef.current) {
      const audioTrack = micStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setState((prev) => ({ ...prev, isMicMuted: !audioTrack.enabled }));
      }
    }
  }, []);

  const pauseCapture = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause();
      if (timerRef.current) clearInterval(timerRef.current);
      setState((prev) => ({ ...prev, isPaused: true }));
    }
  }, []);

  const resumeCapture = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume();
      timerRef.current = setInterval(() => {
        setState((prev) => ({ ...prev, durationSeconds: prev.durationSeconds + 1 }));
      }, 1000);
      setState((prev) => ({ ...prev, isPaused: false }));
    }
  }, []);

  const stopCapture = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (tabStreamRef.current) {
      tabStreamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }

    setState((prev) => ({
      ...prev,
      isRecording: false,
      isPaused: false,
    }));
  }, []);

  return {
    state,
    startCapture,
    stopCapture,
    pauseCapture,
    resumeCapture,
    toggleMicMute,
  };
}
