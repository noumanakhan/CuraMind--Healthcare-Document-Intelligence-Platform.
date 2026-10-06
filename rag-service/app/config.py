import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_RAG_ROOT = os.path.dirname(_CURRENT_DIR)
_ENV_PATHS = [
    ".env",
    os.path.join(_RAG_ROOT, ".env"),
    os.path.join(os.path.dirname(_RAG_ROOT), "rag-service", ".env"),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "CuraMind RAG Service"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8001

    # Database Configuration (Pure PostgreSQL)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "curamind_rag"
    POSTGRES_DSN: Optional[str] = None
    USE_IN_MEMORY_FALLBACK: bool = True  # True if postgres not reachable (for test / standalone execution)

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "mock"  # "mock" | "gemini" | "openai" | "anthropic" | "fastembed"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # LLM Provider Configuration
    LLM_PROVIDER: str = "mock"  # "mock" | "gemini" | "anthropic" | "openai" | "apinex"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None          # Alias for GEMINI_API_KEY
    GEMINI_MODEL: str = "gemini-3.8-flash"
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    # OpenAI-compatible / APInex endpoint override
    # Set LLM_PROVIDER=openai and LLM_BASE_URL=<your-endpoint> to use any
    # OpenAI-compatible API (APInex, Azure OpenAI, local vLLM, etc.)
    LLM_API_KEY: Optional[str] = None            # Overrides OPENAI_API_KEY when set
    LLM_BASE_URL: Optional[str] = None           # e.g. "https://api.apinex.com/v1"

    # OCR Provider Configuration
    OCR_PROVIDER: str = "mock"  # "mock" | "tesseract"

    # Retrieval & Safety Limits
    MAX_RETRIEVED_CHUNKS: int = 8
    MIN_SIMILARITY_SCORE: float = 0.40
    MAX_RESPONSE_TOKENS: int = 1000
    RATE_LIMIT_RAG_PER_MINUTE: int = 30
    RATE_LIMIT_COMPARE_PER_MINUTE: int = 30

    # JWT & RBAC Configuration
    JWT_SECRET: str = "dev-insecure-secret-key-change-in-production-min-32-chars-long"
    JWT_ALGORITHM: str = "HS256"

    @property
    def get_postgres_dsn(self) -> str:
        if self.POSTGRES_DSN:
            return self.POSTGRES_DSN
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
