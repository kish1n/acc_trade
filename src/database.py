from typing import AsyncGenerator
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import settings

async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
)

async_session_factory = async_sessionmaker(async_engine)

class Base(DeclarativeBase):
    pass

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


