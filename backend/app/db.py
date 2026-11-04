"""Kết nối cơ sở dữ liệu với SQLAlchemy async."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Engine async — tự động dùng SQLite hay PostgreSQL theo DATABASE_URL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # Với SQLite cần check_same_thread=False
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Lớp base cho tất cả SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
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
        if "sqlite" in settings.database_url:
            def _sync_sqlite_columns(sync_conn):
                from sqlalchemy import text
                user_cols = [r[1] for r in sync_conn.execute(text("PRAGMA table_info(users)")).fetchall()]
                if user_cols and "credit_balance" not in user_cols:
                    sync_conn.execute(text("ALTER TABLE users ADD COLUMN credit_balance INTEGER NOT NULL DEFAULT 10000"))
                    if "credits" in user_cols:
                        sync_conn.execute(text("UPDATE users SET credit_balance = credits WHERE credit_balance IS NULL OR credit_balance = 0"))

                tx_cols = [r[1] for r in sync_conn.execute(text("PRAGMA table_info(credit_transactions)")).fetchall()]
                if tx_cols:
                    if "type" not in tx_cols:
                        sync_conn.execute(text("ALTER TABLE credit_transactions ADD COLUMN type VARCHAR(30) NOT NULL DEFAULT 'usage'"))
                    if "ref_id" not in tx_cols:
                        sync_conn.execute(text("ALTER TABLE credit_transactions ADD COLUMN ref_id VARCHAR(100)"))

            await conn.run_sync(_sync_sqlite_columns)
