import sys
import os

# Robust sys.path resolution for all cloud platforms (Render, Vercel, Docker)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_repo_root = os.path.dirname(_backend_dir)
for _p in [_repo_root, _backend_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.services.reminder_worker import reminder_worker
from backend.app.demo.seed_data import seed_demo_workspace
from backend.app.api import (
    meetings, live, tasks, approvals, emails, reminders, analytics, team, settings as app_settings
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("meetme")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing MEETME backend engine...")
    try:
        await init_db()

        # Seed demo workspace if not seeded
        async with AsyncSessionLocal() as db:
            await seed_demo_workspace(db=db, force=False)
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")

    # Start persistent reminder worker
    await reminder_worker.start()
    logger.info("MEETME platform ready. Meetings in. Execution out.")

    yield

    # Shutdown
    logger.info("Shutting down reminder background worker...")
    await reminder_worker.stop()

app = FastAPI(
    title=settings.APP_NAME,
    description="MEETME — AI Meeting Intelligence and Autonomous Execution Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration supporting Vercel and local deployments
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if not origins or "*" in origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(meetings.router)
app.include_router(live.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(emails.router)
app.include_router(reminders.router)
app.include_router(analytics.router)
app.include_router(team.router)
app.include_router(app_settings.router)

@app.get("/")
@app.get("/api/health")
async def health_check():
    is_supabase = "supabase" in settings.DATABASE_URL.lower() or "postgres" in settings.DATABASE_URL.lower()
    return {
        "status": "HEALTHY",
        "service": "MEETME Autonomous Platform",
        "philosophy": "MEETINGS IN. EXECUTION OUT.",
        "environment": settings.APP_ENV,
        "database_type": "Supabase PostgreSQL" if is_supabase else "Async SQLite",
        "groq_configured": bool(settings.GROQ_API_KEY),
        "smtp_configured": bool(settings.SMTP_EMAIL and settings.SMTP_PASSWORD),
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=port, reload=settings.DEBUG)
