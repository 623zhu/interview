from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine, 
    create_async_engine,
    async_sessionmaker)

from app.core.config import Settings

def create_base_url(settings: Settings) -> URL:
    return URL.create(
        "mysql+asyncmy",
        username=settings.mysql_user,
        password=settings.mysql_password,
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database
    )

def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        create_base_url(settings),
        pool_pre_ping=True,
        )


def create_mysql_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)