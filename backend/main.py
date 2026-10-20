from fastapi import FastAPI,Request
from app.infrastructure.mysql import create_engine, create_mysql_session_factory
from app.infrastructure.redis import create_redis_client
from app.core.config import settings
from app.infrastructure.llm import create_llm_client, create_embedding_client
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.api.user import router as user_router
from app.api.resumes import router as resumes_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    mysql_engine = create_engine(settings)
    app.state.mysql_session_factory = create_mysql_session_factory(mysql_engine)
    app.state.redis_client = create_redis_client(settings)
    app.state.llm_client = create_llm_client(settings)
    app.state.embedding_client = create_embedding_client(settings)
    try:
        yield
    finally:
        await mysql_engine.dispose()
        await app.state.redis_client.aclose()
        await app.state.llm_client.close()
        await app.state.embedding_client.close()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check(request: Request):
    async with app.state.mysql_session_factory() as session:
        await session.execute(text("SELECT 1"))
    pong = await request.app.state.redis_client.ping()
    return {"mysql": "ok", "redis": pong}

app.include_router(user_router)
app.include_router(resumes_router)