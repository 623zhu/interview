from openai import AsyncOpenAI
from app.core.config import Settings

def create_llm_client(settings:Settings)->AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )