"""SQLAlchemy 2.0 async engine and session factory.

All application database access must go through the AsyncSession obtained
via the get_db dependency (see dependencies.py).  Direct use of the engine
outside of Alembic migrations is discouraged.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # asyncpg default pool size is 5; respect configured limits.
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
