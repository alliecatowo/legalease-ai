"""
Application Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "LegalEase"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://legalease:legalease@localhost:5432/legalease"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "legalease_documents"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "legalease"
    MINIO_SECURE: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Ollama (Local LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_SUMMARIZATION: str = "llama3.1:7b"
    OLLAMA_MODEL_TAGGING: str = "llama3.1:7b"
    OLLAMA_MODEL_SPEAKER_INFERENCE: str = "llama3.1:latest"  # Model for speaker name inference
    OLLAMA_REQUEST_TIMEOUT: int = 300  # 5 minutes for large models

    # Transcription Settings
    WHISPER_MODEL: str = "auto"  # auto, tiny, base, small, medium, large
    WHISPER_BATCH_SIZE: int = 0  # 0 = auto-calculate based on VRAM
    ENABLE_DIARIZATION: bool = True
    DIARIZATION_MIN_SPEAKERS: int = 2
    DIARIZATION_MAX_SPEAKERS: int = 5  # Reduced from 10 for faster diarization
    PYANNOTE_MODEL: str = "pyannote/speaker-diarization-3.1"

    # Speaker Name Inference Settings
    ENABLE_SPEAKER_NAME_INFERENCE: bool = True  # Use LLM to infer speaker names
    OLLAMA_MAX_CONCURRENT_REQUESTS: int = 1  # Limit concurrent Ollama requests (prevents RAM exhaustion)

    # Worker Settings
    CELERY_WORKER_CONCURRENCY: str = "auto"  # auto, or explicit number
    CELERY_WORKER_AUTOSCALE: str = "4,1"  # max,min - adapts to load
    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = 8_000_000  # 8GB (in KB), restart worker after
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour hard limit
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3000  # 50 min soft limit

    # Neo4j (Knowledge Graph)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Identity & Auth
    # KEYCLOAK_PUBLIC_URL: Public-facing URL for Keycloak (used in token issuer validation)
    # This is the URL that Keycloak advertises in tokens (matches KEYCLOAK_HOSTNAME)
    KEYCLOAK_PUBLIC_URL: str = "https://auth.localhost"

    # KEYCLOAK_INTERNAL_URL: Internal container-to-container URL for fetching JWKS
    # Used by backend to communicate with Keycloak within the Docker network
    KEYCLOAK_INTERNAL_URL: str = "http://keycloak:8080"

    # KEYCLOAK_BASE_URL: Legacy/alias for internal URL, kept for backwards compatibility
    # New code should use KEYCLOAK_INTERNAL_URL instead
    KEYCLOAK_BASE_URL: str = "http://keycloak:8080"

    KEYCLOAK_REALM: str = "legalease"
    KEYCLOAK_BACKEND_CLIENT_ID: str = "fastapi-backend"
    KEYCLOAK_BACKEND_CLIENT_SECRET: str = "change-me"
    KEYCLOAK_JWKS_CACHE_SECONDS: int = 300
    KEYCLOAK_TIMEOUT_SECONDS: int = 5
    KEYCLOAK_AUDIENCE: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
