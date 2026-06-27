"""FastAPI dependency providers.

Keep this module thin — only DI wiring, no business logic.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession scoped to a single HTTP request.

    The session is automatically closed after the response is sent.
    Callers should not commit inside request handlers; commit is the
    responsibility of service/repository calls, not routers.
    """
    async with AsyncSessionLocal() as session:
        yield session
