# MEETME — Production Deployment Guide
## Supabase Database + Render Backend + Vercel Frontend

This guide details how to deploy MEETME to production in under 10 minutes using:
1. **Supabase** for PostgreSQL Database & Storage
2. **Render** for FastAPI Python Backend & Background Workers
3. **Vercel** for Next.js TypeScript Frontend

---

## 1. Supabase Database Configuration

### Step 1.1: Create a Supabase Project
1. Log in to [Supabase](https://supabase.com) and create a new project (e.g. `meetme-prod`).
2. Note your database password and project reference URL.

### Step 1.2: Run Database Schema Migrations
1. In the Supabase Dashboard, navigate to the **SQL Editor** on the left menu.
2. Open or copy the contents of `backend/migrations/001_initial_schema.sql`.
3. Paste the SQL script and click **Run**.
4. This creates all 14 production tables (`workspaces`, `users`, `workspace_members`, `meetings`, `meeting_transcripts`, `tasks`, `approvals`, `email_logs`, `reminders`, `automation_logs`, `agent_runs`, etc.) with high-performance indexes.

### Step 1.3: Retrieve Connection Strings
1. In Supabase, go to **Project Settings** &rarr; **Database**.
2. Under **Connection string**, select **URI**.
3. Choose **Transaction Pooler** (recommended for Render & serverless, port `6543`) or **Direct Connection** (port `5432`).
4. Copy the connection string. Replace `[YOUR-PASSWORD]` with your actual Supabase database password.
   *Example Transaction Pooler:*
   ```text
   postgresql+asyncpg://postgres.yourprojectref:yourpassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
   *(Note: The MEETME backend automatically converts `postgres://` or `postgresql://` to `postgresql+asyncpg://` and disables statement caching for Supabase PgBouncer compatibility).*

---

## 2. Deploying Backend to Render

### Option A: One-Click via Render Blueprint (`render.yaml`)
1. Push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New** &rarr; **Blueprint**.
3. Connect your GitHub repository.
4. Render automatically reads `render.yaml` and configures the `meetme-backend` web service.

### Option B: Manual Web Service Setup
1. In Render Dashboard, click **New** &rarr; **Web Service**.
2. Select your repository.
3. Configure settings:
   - **Name:** `meetme-backend`
   - **Region:** Choose region closest to your Supabase project (e.g., Oregon or Frankfurt).
   - **Branch:** `main`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/api/health`
4. Add **Environment Variables** in Render:
   | Key | Value / Example | Note |
   |---|---|---|
   | `DATABASE_URL` | `postgresql+asyncpg://postgres.ref:pass@pooler.supabase.com:6543/postgres` | Your Supabase connection string |
   | `SUPABASE_URL` | `https://your-project.supabase.co` | Supabase API URL |
   | `SUPABASE_ANON_KEY` | `eyJ...` | Supabase Anon Key |
   | `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Supabase Service Role Key |
   | `GROQ_API_KEY` | `gsk_...` | Groq API Key |
   | `GROQ_MODEL` | `llama-3.3-70b-versatile` | Supported fast model |
   | `SMTP_HOST` | `smtp.gmail.com` | Native Gmail SMTP Host |
   | `SMTP_PORT` | `587` | STARTTLS Port |
   | `SMTP_EMAIL` | `yourcompany@gmail.com` | Gmail sender address |
   | `SMTP_PASSWORD` | `xxxx xxxx xxxx xxxx` | 16-character Google App Password |
   | `SMTP_FROM_NAME` | `MEETME Intelligence` | Display sender name |
   | `APP_FRONTEND_URL` | `https://your-frontend.vercel.app` | Frontend URL for email task links |
   | `CORS_ORIGINS` | `*` or `https://your-frontend.vercel.app` | Allows Vercel frontend |
   | `PYTHONPATH` | `.` | Python module resolver |
   | `APP_ENV` | `production` | Production mode |

5. Click **Create Web Service**.
6. Once deployed, note your Render backend URL:
   `https://meetme-8r0u.onrender.com`

---

## 3. Deploying Frontend to Vercel

1. Log in to [Vercel](https://vercel.com) and click **Add New** &rarr; **Project**.
2. Import your GitHub repository.
3. In **Project Settings**:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click `Edit` and select `frontend` (or leave root if using root `vercel.json`).
4. In **Environment Variables**, add:
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://meetme-backend.onrender.com/api` |
   | `NEXT_PUBLIC_WS_URL` | `wss://meetme-backend.onrender.com` |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `your-anon-key` |

5. Click **Deploy**.
6. Vercel will build and deploy the Next.js frontend to `https://meetme-app.vercel.app`.

---

## 4. Verification & Testing

1. Open your Vercel frontend URL:
   - Check that the dashboard loads live metrics from Supabase.
   - Navigate to **Settings** &rarr; click **Reset & Seed Demo** to verify database write and agent pipeline execution.
2. Navigate to **Approvals**:
   - Verify pending approvals are loaded from Supabase.
   - Click **Approve** on a task and check the Gmail SMTP dispatch and reminder creation.
3. Navigate to **Live Meeting**:
   - Verify WebSocket connection to the Render backend (`CONNECTED`).
   - Start recording and verify dual-stream audio capture and live streaming classification.
