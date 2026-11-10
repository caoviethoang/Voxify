"""Kết nối cơ sở dữ liệu với SQLAlchemy async."""
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

is_sqlite = "sqlite" in settings.database_url
is_memory = ":memory:" in settings.database_url

connect_args = {"check_same_thread": False, "timeout": 60.0} if is_sqlite else {}
pool_kwargs = {}
if is_memory:
    from sqlalchemy.pool import StaticPool
    pool_kwargs["poolclass"] = StaticPool

# Engine async — tự động dùng SQLite hay PostgreSQL theo DATABASE_URL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    query_cache_size=0,
    **pool_kwargs,
)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        if not is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Lớp base cho tất cả SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI — cung cấp database session theo request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Tạo tất cả bảng (dùng khi dev, production dùng Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Nếu là SQLite, tự động bổ sung cột thiếu mà create_all không hỗ trợ cho bảng có sẵn
        if is_sqlite:
            def _sync_sqlite_columns(sync_conn):
                from sqlalchemy import text
                if not is_memory:
                    sync_conn.execute(text("PRAGMA journal_mode=WAL"))
                    sync_conn.execute(text("PRAGMA busy_timeout=5000"))
                user_cols = [r[1] for r in sync_conn.execute(text("PRAGMA table_info(users)")).fetchall()]
                if user_cols and "credit_balance" not in user_cols:
                    sync_conn.execute(text("ALTER TABLE users ADD COLUMN credit_balance INTEGER NOT NULL DEFAULT 10000"))
                    if "credits" in user_cols:
                        sync_conn.execute(text("UPDATE users SET credit_balance = credits WHERE credit_balance IS NULL OR credit_balance = 0"))
                if user_cols and "subscription_tier" not in user_cols:
                    sync_conn.execute(text("ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(50) NOT NULL DEFAULT 'free'"))

                tx_cols = [r[1] for r in sync_conn.execute(text("PRAGMA table_info(credit_transactions)")).fetchall()]
                if tx_cols:
                    if "type" not in tx_cols:
                        sync_conn.execute(text("ALTER TABLE credit_transactions ADD COLUMN type VARCHAR(30) NOT NULL DEFAULT 'usage'"))
                    if "ref_id" not in tx_cols:
                        sync_conn.execute(text("ALTER TABLE credit_transactions ADD COLUMN ref_id VARCHAR(100)"))

                gen_cols = [r[1] for r in sync_conn.execute(text("PRAGMA table_info(generations)")).fetchall()]
                if gen_cols:
                    if "status" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'done'"))
                    if "progress" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN progress INTEGER NOT NULL DEFAULT 100"))
                    if "duration" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN duration REAL NOT NULL DEFAULT 0.0"))
                    if "format" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN format VARCHAR(10) NOT NULL DEFAULT 'mp3'"))
                    if "credit_used" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN credit_used INTEGER NOT NULL DEFAULT 0"))
                    if "error_message" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN error_message TEXT"))
                    if "srt_path" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN srt_path VARCHAR(500)"))
                    if "vtt_path" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN vtt_path VARCHAR(500)"))
                    if "updated_at" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN updated_at TIMESTAMP"))
                        sync_conn.execute(text("UPDATE generations SET updated_at = created_at WHERE updated_at IS NULL"))
                    if "title" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN title VARCHAR(200)"))
                    if "webhook_url" not in gen_cols:
                        sync_conn.execute(text("ALTER TABLE generations ADD COLUMN webhook_url VARCHAR(500)"))

            await conn.run_sync(_sync_sqlite_columns)
