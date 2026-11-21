# MEETME — AI Meeting Intelligence & Autonomous Execution Platform
> **"MEETINGS IN. EXECUTION OUT."**

MEETME is an intelligent execution platform that listens to meetings, understands conversations in real time, classifies dialogue, extracts action items and decisions, maps responsibilities with confidence scoring, enforces mandatory human approval, dispatches assignment emails via Resend, and manages persistent automated reminder cycles.

---

## Architecture Overview

```
LIVE OR RECORDED MEETING
       │
       ▼
AUDIO CAPTURE ENGINE (Web Audio API Dual-Stream Mixer: getDisplayMedia + getUserMedia)
       │
       ▼
STREAMING TRANSCRIPTION (Groq Whisper-large-v3 API / WebSocket Pipeline)
       │
       ▼
CENTRAL ORCHESTRATOR AGENT
  ├── Transcription Analysis Agent (Speaker turns & multi-class tagger)
  ├── Task Extraction Agent (Title, description, priority, deadline, quotes)
  ├── Assignment Agent (Team directory matching & confidence scoring)
  ├── Decision & Risk Agent (Finalized policies, blockers, dependencies)
  └── Email Agent (Executive-grade HTML assignment & reminder templates)
       │
       ▼
MANDATORY HUMAN APPROVAL GATE (Audit, edit parameters, inspect diff & evidence)
       │
       ▼
EXECUTION AGENT
  ├── Database Persistence (Supabase PostgreSQL / Async SQLite)
  ├── Email Automation (Resend API execution & audit logs)
  └── Persistent Reminder Worker (Background job queue, retry backoff, auto-cancellation on completion)
```

---

## Design System & Visual Identity

MEETME adheres to a strict, dark-mode, enterprise productivity aesthetic inspired by Linear and Stripe:
- **Primary Background:** `#090909`
- **Secondary Background:** `#111111`
- **Card Background:** `#191919`
- **Elevated Background:** `#202020`
- **Primary Accent:** `#FF7900` (Orange — Primary CTAs, active navigation, key status highlights)
- **Secondary Accent:** `#B6FF00` (Neon Green — Successful executions, live telemetry, completed items)
- **Primary Text:** `#FFFFFF`
- **Secondary Text:** `#A0A0A0`
- **Borders:** `#303030`
- **Strict Guidelines:** Zero emojis, zero decorative Unicode symbols, crisp typography, small-radius cards (`rounded-md`), and Lucide functional icons only.

---

## Key Modules

### 1. Live Meeting Engine (`/live`)
- Real-time browser audio capture via Web Audio API mixing:
  - **Tab Audio (`getDisplayMedia`):** Captures incoming remote participants (Google Meet, Zoom, Teams).
  - **Microphone Audio (`getUserMedia`):** Captures local speaker even when wearing headphones.
- Live WebSocket streaming (`/ws/live-meeting/{meeting_id}`).
- Real-time classification stream: `TASK`, `DECISION`, `COMMITMENT`, `QUESTION`, `BLOCKER`, `GENERAL_DISCUSSION`.
- Instant task and decision extraction cards streaming alongside the meeting.
- Full participant consent verification banner.

### 2. Recorded Meeting Ingestion (`/recorded`)
- Drag-and-drop ingestion of MP3, WAV, M4A, WEBM, TXT, VTT, SRT files.
- Audio file validation, upload progress telemetry, and orchestrator execution.

### 3. Human Approval Gate (`/approvals`)
- **No rogue autonomous actions:** External emails and schedules cannot execute without explicit human signoff.
- Multi-select batch approval, Approve All, or individual review.
- **Edit & Approve:** Inspect transcript quotes, modify assignees, adjust deadlines or priority, and preview/edit the generated email HTML before dispatching.
- Low-confidence assignments (< 75%) flagged with unambiguous clarification warnings.

### 4. Task Management Ledger (`/tasks`)
- Real-time filtering: *All Tasks, Pending Approval, Active, In Progress, Completed, Overdue*.
- Full traceability to original conversation audio timestamps and evidence quotes.
- Mark complete workflow automatically cancels all pending reminders for that task.

### 5. Persistent Reminder Engine (`/automations`)
- Reliable background worker running every 15 seconds.
- Persisted in database: recovers seamlessly across backend restarts.
- Automatic escalation for overdue tasks.
- Idempotency and exponential backoff retry on transient provider errors.

### 6. Email Execution & Audit (`/emails`)
- Integrated with Resend API for transactional email delivery.
- Includes local test mode queue logging when credentials are not configured.
- Inspect full HTML and plaintext delivery payloads and retry failed sends.

### 7. Executive Productivity Analytics (`/analytics`)
- Task completion rates, team workload allocation charts, and AI classification distribution calculated directly from verified database rows.

### 8. Team & Speaker Registry (`/team`)
- Manage verified workspace members and emails for deterministic assignment mapping.

---

## Quickstart Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 1. Backend Setup
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start FastAPI backend server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend initializes the database schema, seeds the 4-participant demo workspace (`MEETME Core Engineering`), and starts the persistent reminder background worker.

### 2. Frontend Setup
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Environment Configuration

Create a `.env` file in the root or `backend/` directory:

```env
# AI Providers
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_WHISPER_MODEL=whisper-large-v3

# Email Provider
RESEND_API_KEY=re_your_resend_api_key_here
RESEND_FROM_EMAIL=MEETME <onboarding@resend.dev>

# Database (Default: Async SQLite, or Supabase PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./meetme.db
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-key
```

*Note: If `GROQ_API_KEY` or `RESEND_API_KEY` are omitted, MEETME automatically uses its deterministic heuristic parsing engine and local email audit queue, allowing full end-to-end testing without external API credentials.*

---

## Running the Automated Acceptance Test

Run the comprehensive end-to-end acceptance test suite verifying all 17 criteria:

```bash
.\venv\Scripts\python backend/tests/test_e2e_flow.py
```
