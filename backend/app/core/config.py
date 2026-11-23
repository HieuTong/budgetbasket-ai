import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# Resolve the backend-local .env from the source tree rather than the process
# working directory. This keeps CLI tools (Alembic, seed loaders, tests) and the
# API consistent when they are invoked from different directories.
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:pass@localhost:5432/budgetbasket"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
    # Which model server the assistant talks to. "gemini" uses the Gemini API.
    # "openai" uses any OpenAI-compatible server (vLLM, SGLang, Ollama, hosted APIs)
    # at LLM_BASE_URL, e.g. http://localhost:8000/v1. LLM_MODEL names the model either way.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./data/faiss_index")
    # Signs login tokens. No default on purpose: a known default would let anyone forge tokens.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    ACCESS_TOKEN_MINUTES: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
    # The seeded account that "Try the demo" signs visitors into.
    DEMO_USER_ID: int = int(os.getenv("DEMO_USER_ID", "1"))
    DEMO_TOKEN_MINUTES: int = int(os.getenv("DEMO_TOKEN_MINUTES", "30"))
    # Rate limits. The chat limits protect the paid model quota; the auth limit slows
    # password guessing. The daily cap is shared by everyone, as a hard ceiling on spend.
    CHAT_REQUESTS_PER_MINUTE: int = int(os.getenv("CHAT_REQUESTS_PER_MINUTE", "10"))
    CHAT_REQUESTS_PER_DAY: int = int(os.getenv("CHAT_REQUESTS_PER_DAY", "300"))
    AUTH_REQUESTS_PER_MINUTE: int = int(os.getenv("AUTH_REQUESTS_PER_MINUTE", "10"))
    # How many proxies sit in front of the app and add to X-Forwarded-For.
    # 0 (local) uses the direct connection address. Set it for the hosting platform.
    TRUSTED_PROXY_HOPS: int = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
