"""Database configuration and session management."""

from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# Import settings from main config
from app.core.config import settings

def ensure_async_database_url(url: str) -> str:
    """Ensure database URL has async driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

def get_sync_database_url(url: str) -> str:
    """Convert database URL to sync URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif url.startswith("postgresql://"):
        return url
    return url


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy 2.0 models."""
    pass


# Get async and sync database URLs
async_database_url = ensure_async_database_url(settings.DATABASE_URL)
sync_database_url = get_sync_database_url(settings.DATABASE_URL)

# Create async SQLAlchemy engine
async_engine: AsyncEngine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query logging
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create synchronous SQLAlchemy engine (for workers and scripts)
sync_engine: Engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query logging
)

# Create synchronous session factory
SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: SQLAlchemy async database session

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a synchronous database session.

    Yields:
        Session: SQLAlchemy synchronous database session

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_sync_db)):
            return db.query(Item).all()
    """
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Backward compatibility aliases for code that hasn't been migrated to async yet
engine = sync_engine
SessionLocal = SyncSessionLocal
get_db = get_sync_db
