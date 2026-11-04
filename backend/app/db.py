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
