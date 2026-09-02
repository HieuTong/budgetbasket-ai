import os
from functools import lru_cache


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/budgetbasket")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./data/faiss_index")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
