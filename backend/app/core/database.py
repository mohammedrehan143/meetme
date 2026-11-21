from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from backend.app.core.config import settings
import logging

logger = logging.getLogger("meetme.database")

# Handle Supabase vs Local SQLite URLs
raw_url = settings.DATABASE_URL.strip()

# Handle placeholder password gracefully
if "[YOUR-PASSWORD]" in raw_url or "yourpassword" in raw_url:
    logger.warning("Supabase DATABASE_URL contains placeholder '[YOUR-PASSWORD]'. Using local Async SQLite until password is provided in .env.")
    raw_url = "sqlite+aiosqlite:///./meetme.db"

# Normalize postgres URL schemes to asyncpg
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+asyncpg://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args = {}
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if "sqlite" in raw_url:
    connect_args["check_same_thread"] = False
else:
    # Supabase PostgreSQL Configuration
    # 1. Statement cache must be 0 for Supabase PgBouncer (Transaction Pooler port 6543)
    connect_args["statement_cache_size"] = 0
    
    # 2. Recycle connections after 300s to avoid stale cloud connections
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

    # 3. Clean query params like sslmode that asyncpg expects via connect_args or SSLContext
    if "?" in raw_url:
        parsed = urlparse(raw_url)
        query_params = parse_qs(parsed.query)
        # Remove sslmode or other incompatible query args from URL
        if "sslmode" in query_params:
            del query_params["sslmode"]
        
        new_query = urlencode(query_params, doseq=True)
        raw_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

from sqlalchemy import event

engine = create_async_engine(
    raw_url,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable foreign keys for SQLite sessions
if "sqlite" in raw_url.lower():
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite column migration helper if tables existed prior to migration
        if "sqlite" in raw_url.lower():
            for tbl, col, col_type in [
                ("approvals", "action_category", "VARCHAR(50) DEFAULT 'TASK_EXECUTION'"),
                ("approvals", "target_platform", "VARCHAR(50) DEFAULT 'EMAIL'"),
                ("approvals", "user_id", "VARCHAR(36)"),
                ("email_logs", "task_ids", "TEXT"),
                ("email_logs", "email_type", "VARCHAR(50)"),
                ("email_logs", "message_id", "VARCHAR(255)"),
                ("email_logs", "idempotency_key", "VARCHAR(255)"),
                ("email_logs", "retry_count", "INTEGER DEFAULT 0"),
                ("email_logs", "scheduled_at", "TIMESTAMP"),
                ("reminders", "task_ids", "TEXT")
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}"))
                except Exception:
                    pass
    logger.info("Database tables verified/created successfully.")
