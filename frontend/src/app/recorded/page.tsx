"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileAudio, FileText, CheckCircle2, AlertTriangle, ArrowRight, Loader2, Sparkles, Clipboard } from "lucide-react";
import { api } from "@/lib/api";

export default function RecordedMeetingPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"upload" | "paste">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState("");
  const [title, setTitle] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (selectedFile: File) => {
    setError(null);
    const validExtensions = [".mp3", ".wav", ".m4a", ".webm", ".txt", ".vtt", ".srt", ".json", ".md"];
    const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();
    
    if (!validExtensions.includes(ext)) {
      setError(`Unsupported file type '${ext}'. Please upload MP3, WAV, M4A, WEBM, or TXT transcript.`);
      return;
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setError("File exceeds maximum allowed size of 100 MB.");
      return;
    }

    setFile(selectedFile);
    if (!title) {
      setTitle(selectedFile.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " "));
    }
  };

  const handleProcess = async () => {
    let fileToUpload: File | null = file;

    if (activeTab === "paste") {
      if (!pastedText.trim()) {
        setError("Please enter or paste meeting transcript text.");
        return;
      }
      const meetingName = title.trim() || "Meeting Transcript";
      const blob = new Blob([pastedText], { type: "text/plain" });
      fileToUpload = new File([blob], `${meetingName.replace(/\s+/g, "_")}.txt`, { type: "text/plain" });
    } else {
      if (!fileToUpload) {
        setError("Please select an audio or transcript file to upload.");
        return;
      }
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(20);
    setProcessingStatus("Submitting to MEETME Multi-Agent Orchestrator...");

    try {
      const formData = new FormData();
      formData.append("file", fileToUpload);
      formData.append("title", title || fileToUpload.name.replace(/\.[^/.]+$/, ""));

      setUploadProgress(50);
      setProcessingStatus("Extracting tasks, mapping assignees & confidence scoring...");

      const res = await api.uploadMeeting(formData);
      setUploadProgress(100);
      setProcessingStatus("Tasks extracted and approvals generated.");
      setResult(res);

    } catch (err: any) {
      setError(err.message || "Failed to process meeting.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="pb-3 border-b border-border-subtle">
        <h1 className="text-xl font-bold text-text-primary">Ingest Recorded Meeting or Transcript</h1>
        <p className="text-xs text-text-secondary mt-1">
          Upload audio recording, drop a transcript file, or paste raw meeting notes to trigger autonomous task extraction.
        </p>
      </div>

      {!result ? (
        <div className="space-y-6">
          {/* Tab Selector */}
          <div className="flex border-b border-border-subtle gap-2">
            <button
              onClick={() => { setActiveTab("upload"); setError(null); }}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === "upload"
                  ? "border-accent-orange text-accent-orange"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              <FileAudio size={14} />
              <span>Upload Audio or Document</span>
            </button>
            <button
              onClick={() => { setActiveTab("paste"); setError(null); }}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === "paste"
                  ? "border-accent-orange text-accent-orange"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              <FileText size={14} />
              <span>Paste Transcript / Notes</span>
            </button>
          </div>

          {activeTab === "upload" ? (
            /* File Upload Drag & Drop Area */
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer flex flex-col items-center justify-center space-y-3 ${
                dragActive
                  ? "border-accent-orange bg-accent-orange/5"
                  : "border-border-subtle hover:border-border-strong bg-bg-card"
              }`}
              onClick={() => document.getElementById("file-upload-input")?.click()}
            >
              <input
                id="file-upload-input"
                type="file"
                onChange={handleFileChange}
                accept=".mp3,.wav,.m4a,.webm,.txt,.vtt,.srt,.json,.md"
                className="hidden"
              />

              <div className="w-12 h-12 rounded-full bg-bg-elevated flex items-center justify-center text-accent-orange border border-border-subtle">
                <Upload size={20} />
              </div>

              <div className="space-y-1">
                <p className="text-xs font-semibold text-text-primary">
                  {file ? file.name : "Drag and drop meeting audio or transcript file"}
                </p>
                <p className="text-[11px] text-text-secondary">
                  Supported formats: MP3, WAV, M4A, WEBM, TXT, VTT, SRT (up to 100MB)
                </p>
              </div>

              {file && (
                <div className="flex items-center gap-2 text-xs font-mono text-accent-neon bg-accent-neon/10 px-3 py-1 rounded">
                  <CheckCircle2 size={13} />
                  <span>Selected: {(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
              )}
            </div>
          ) : (
            /* Paste Transcript Text Area */
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-text-primary">
                  Meeting Dialogue / Notes
                </label>
              </div>

              <textarea
                rows={10}
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste meeting transcript or dialogue notes here...&#10;&#10;e.g.&#10;[00:00:15] Alex: Let's do a fast sync on project deliverables.&#10;[00:00:40] Sam: I will complete the frontend layout by Friday.&#10;[00:01:10] Taylor: I will finalize the backend API and send out the schema."
                className="w-full bg-bg-elevated border border-border-subtle rounded p-3 text-xs text-text-primary font-mono focus:outline-none focus:border-accent-orange leading-relaxed"
              />
            </div>
          )}

          {/* Meeting Title Input */}
          <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-2">
            <label className="text-xs font-medium text-text-primary block">
              Meeting Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q4 Infrastructure Architecture Alignment"
              className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-orange"
            />
          </div>

          {error && (
            <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle size={15} />
              <span>{error}</span>
            </div>
          )}

          {isUploading && (
            <div className="p-4 rounded bg-bg-card border border-border-subtle space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">{processingStatus}</span>
                <span className="font-mono text-accent-orange">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-bg-elevated rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-accent-orange h-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              onClick={() => router.push("/")}
              className="px-4 py-2 rounded text-xs font-medium bg-bg-elevated border border-border-subtle text-text-secondary hover:text-text-primary"
            >
              Cancel
            </button>
            <button
              onClick={handleProcess}
              disabled={(activeTab === "upload" && !file) || (activeTab === "paste" && !pastedText.trim()) || isUploading}
              className="px-5 py-2 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover disabled:opacity-50 flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Processing Pipeline...</span>
                </>
              ) : (
                <>
                  <span>Extract Tasks &amp; Generate Approvals</span>
                  <ArrowRight size={13} />
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Processing Complete Report */
        <div className="p-6 rounded bg-bg-card border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 text-accent-neon">
            <CheckCircle2 size={20} />
            <h2 className="text-sm font-bold uppercase tracking-wider">
              Meeting Ingested &amp; Analyzed Successfully
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-xs">
            <div className="p-3 bg-bg-elevated rounded border border-border-subtle">
              <span className="text-text-muted text-[10px] uppercase">Meeting</span>
              <p className="text-text-primary font-bold mt-1">{result.title}</p>
            </div>
            <div className="p-3 bg-bg-elevated rounded border border-border-subtle">
              <span className="text-text-muted text-[10px] uppercase">Tasks Extracted</span>
              <p className="text-accent-orange font-bold mt-1">{result.tasks_extracted}</p>
            </div>
            <div className="p-3 bg-bg-elevated rounded border border-border-subtle">
              <span className="text-text-muted text-[10px] uppercase">Approvals Queued</span>
              <p className="text-accent-neon font-bold mt-1">{result.approvals_created}</p>
            </div>
          </div>

          <p className="text-xs text-text-secondary leading-relaxed">
            All extracted action items have been mapped to workspace members and staged in the Approval Center. 
            Execution and email dispatch will occur upon your human review and approval.
          </p>

          <div className="flex justify-end gap-3 pt-3 border-t border-border-subtle">
            <button
              onClick={() => { setResult(null); setFile(null); setPastedText(""); setTitle(""); }}
              className="px-3 py-1.5 rounded text-xs font-medium bg-bg-elevated border border-border-subtle text-text-secondary hover:text-text-primary"
            >
              Ingest Another
            </button>
            <button
              onClick={() => router.push(`/meetings/${result.meeting_id}`)}
              className="px-3 py-1.5 rounded text-xs font-medium bg-bg-card border border-border-subtle text-text-primary hover:border-border-strong"
            >
              View Meeting Report
            </button>
            <button
              onClick={() => router.push("/approvals")}
              className="px-4 py-1.5 rounded text-xs font-semibold bg-accent-orange text-black hover:bg-accent-orange-hover flex items-center gap-1.5"
            >
              <span>Review Approvals</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
