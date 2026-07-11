from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings


settings = get_settings()

engine = create_engine(settings.db.url, echo=settings.debug)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── 异步引擎（trading / ai 模块使用）──
# psycopg2 是同步驱动，异步需替换为 asyncpg
_async_url = settings.db.url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
async_engine = create_async_engine(_async_url, echo=settings.debug, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session