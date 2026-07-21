from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb"

    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    JWT_SECRET_KEY: str = "change-this-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Comma-separated allowed browser origins (used verbatim in production).
    # In development any localhost port is allowed instead — Next.js silently moves to
    # 3001+ when 3000 is taken, which otherwise breaks every request with a CORS error.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Models
    EMBEDDING_DIM: int = 3072
    GROQ_SYNTHESIS_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"

    # Retrieval / chunking
    PARENT_CHUNK_SIZE: int = 2000
    PARENT_CHUNK_OVERLAP: int = 200
    CHILD_CHUNK_SIZE: int = 500
    CHILD_CHUNK_OVERLAP: int = 100
    DEFAULT_TOP_K: int = 5

    # Cost tracking — approximate Groq blended $/1M tokens (free tier = $0, shown for reference)
    COST_PER_1M_TOKENS_USD: float = 0.0

    # Evaluation gate (CI fails below this faithfulness)
    FAITHFULNESS_GATE: float = 0.8

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
