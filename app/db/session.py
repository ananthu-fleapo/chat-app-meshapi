"""
FastAPI dependency: yields a per-request AsyncSession.

Usage
-----
    async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
        ...

The session is committed on clean exit and rolled back on any exception.
The `async with` on the session factory handles final cleanup (close).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
