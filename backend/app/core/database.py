from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from backend.app.core.config import settings
import logging

logger = logging.getLogger("meetme.database")

# Handle Supabase vs Local SQLite URLs
raw_url = settings.DATABASE_URL.strip()

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

engine = create_async_engine(
    raw_url,
    connect_args=connect_args,
    **engine_kwargs
)

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created successfully.")
