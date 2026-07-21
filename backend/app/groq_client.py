from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache
def get_groq_client() -> OpenAI:
    """Lazily built so the app can boot before GROQ_API_KEY is configured."""
    return OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
