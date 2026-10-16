from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import NotConfigured, get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def sessionmaker() -> async_sessionmaker[AsyncSession]:
    url = get_settings().async_database_url
    if not url:
        raise NotConfigured("Database non configurato: imposta DATABASE_URL nel backend")
    engine = create_async_engine(url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with sessionmaker()() as session:
        yield session
