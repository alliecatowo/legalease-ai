"""
Application Configuration
"""
from typing import Optional
from pydantic import Field, field_validator, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with comprehensive service configurations"""

    # ==================== Application Settings ====================
    APP_NAME: str = "LegalEase"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ==================== Database Settings ====================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://legalease:legalease_dev@localhost:5432/legalease",
        description="PostgreSQL database connection URL"
    )

    # ==================== Redis Settings ====================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and messaging"
    )

    # ==================== Qdrant Vector Database Settings ====================
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = Field(default=6333, gt=0, lt=65536)
    QDRANT_COLLECTION: str = "legalease_documents"

    # ==================== OpenSearch Settings ====================
    OPENSEARCH_URL: str = Field(
        default="http://localhost:9200",
        description="OpenSearch cluster URL for full-text search and analytics"
    )
    OPENSEARCH_INDEX_PREFIX: str = Field(
        default="legalease",
        description="Prefix for all OpenSearch indices"
    )
    OPENSEARCH_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="OpenSearch request timeout in seconds"
    )
    OPENSEARCH_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts for OpenSearch operations"
    )

    # ==================== MinIO Object Storage Settings ====================
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "legalease"
    MINIO_SECRET_KEY: str = "legalease_dev_secret"
    MINIO_BUCKET: str = "legalease"
    MINIO_SECURE: bool = False

    # ==================== Celery Task Queue Settings ====================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )

    # ==================== Temporal Workflow Engine Settings ====================
    TEMPORAL_HOST: str = Field(
        default="localhost:7233",
        description="Temporal server host and port"
    )
    TEMPORAL_NAMESPACE: str = Field(
        default="legalease",
        description="Temporal namespace for workflow isolation"
    )
    TEMPORAL_TASK_QUEUE: str = Field(
        default="legalease-research",
        description="Temporal task queue name for research workflows"
    )
    TEMPORAL_WORKFLOW_EXECUTION_TIMEOUT: int = Field(
        default=14400,
        gt=0,
        description="Maximum workflow execution timeout in seconds (4 hours)"
    )

    # ==================== Ollama LLM Settings ====================
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    OLLAMA_MODEL_SUMMARIZATION: str = "llama3.1:7b"
    OLLAMA_MODEL_TAGGING: str = "llama3.1:7b"
    OLLAMA_MODEL_SPEAKER_INFERENCE: str = "llama3.1:latest"
    OLLAMA_REQUEST_TIMEOUT: int = Field(
        default=300,
        gt=0,
        description="Ollama request timeout in seconds"
    )
    OLLAMA_MAX_CONCURRENT_REQUESTS: int = Field(
        default=1,
        ge=1,
        description="Maximum concurrent Ollama requests to prevent resource exhaustion"
    )

    # ==================== Haystack Pipeline Settings ====================
    HAYSTACK_LOGGING_LEVEL: str = Field(
        default="INFO",
        description="Logging level for Haystack pipelines"
    )
    HAYSTACK_TELEMETRY_ENABLED: bool = Field(
        default=False,
        description="Enable Haystack telemetry and usage analytics"
    )

    # ==================== Transcription Settings ====================
    WHISPER_MODEL: str = Field(
        default="auto",
        description="Whisper model size (auto, tiny, base, small, medium, large)"
    )
    WHISPER_BATCH_SIZE: int = Field(
        default=0,
        ge=0,
        description="Batch size for Whisper (0 = auto-calculate based on VRAM)"
    )
    ENABLE_DIARIZATION: bool = True
    DIARIZATION_MIN_SPEAKERS: int = Field(default=2, ge=1)
    DIARIZATION_MAX_SPEAKERS: int = Field(default=5, ge=1)
    PYANNOTE_MODEL: str = "pyannote/speaker-diarization-3.1"

    # ==================== Speaker Name Inference Settings ====================
    ENABLE_SPEAKER_NAME_INFERENCE: bool = Field(
        default=True,
        description="Use LLM to infer speaker names from transcript context"
    )

    # ==================== Worker Settings ====================
    CELERY_WORKER_CONCURRENCY: str = Field(
        default="auto",
        description="Celery worker concurrency (auto or explicit number)"
    )
    CELERY_WORKER_AUTOSCALE: str = Field(
        default="4,1",
        description="Celery worker autoscale settings (max,min)"
    )
    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = Field(
        default=8_000_000,
        gt=0,
        description="Maximum memory per worker child in KB (8GB)"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=3600,
        gt=0,
        description="Hard time limit for Celery tasks in seconds"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=3000,
        gt=0,
        description="Soft time limit for Celery tasks in seconds"
    )

    # ==================== Neo4j Knowledge Graph Settings ====================
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j database URI"
    )
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "legalease_dev"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum connection pool size for Neo4j"
    )
    NEO4J_CONNECTION_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Neo4j connection timeout in seconds"
    )
    NEO4J_MAX_TRANSACTION_RETRY_TIME: int = Field(
        default=30,
        gt=0,
        description="Maximum time to retry failed transactions in seconds"
    )

    # ==================== Research Agent Settings ====================
    RESEARCH_MAX_CONCURRENT_AGENTS: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Maximum number of concurrent research agents"
    )
    RESEARCH_DEFAULT_TIMEOUT: int = Field(
        default=14400,
        gt=0,
        description="Default research task timeout in seconds (4 hours)"
    )
    RESEARCH_CHECKPOINT_INTERVAL: int = Field(
        default=300,
        gt=0,
        description="Interval for saving research checkpoints in seconds (5 minutes)"
    )
    RESEARCH_MAX_FINDINGS_PER_SOURCE: int = Field(
        default=100,
        ge=1,
        description="Maximum number of findings to extract per source"
    )

    # ==================== Security Settings ====================
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        description="Secret key for JWT token generation and encryption"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        gt=0,
        description="JWT access token expiration time in minutes"
    )

    # ==================== Validators ====================
    @field_validator("OPENSEARCH_URL", "QDRANT_URL", "OLLAMA_BASE_URL")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URLs are properly formatted"""
        if not v:
            raise ValueError("URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {v}")
        return v

    @field_validator("DIARIZATION_MAX_SPEAKERS")
    @classmethod
    def validate_max_speakers(cls, v: int, info) -> int:
        """Ensure max speakers is greater than or equal to min speakers"""
        # Note: can't access other fields during validation in Pydantic v2
        # This validation happens at the field level
        if v < 1:
            raise ValueError("Maximum speakers must be at least 1")
        return v

    @field_validator("NEO4J_MAX_CONNECTION_POOL_SIZE")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Ensure connection pool size is reasonable"""
        if v < 1:
            raise ValueError("Connection pool size must be at least 1")
        if v > 1000:
            raise ValueError("Connection pool size too large (max: 1000)")
        return v

    @field_validator("RESEARCH_MAX_CONCURRENT_AGENTS")
    @classmethod
    def validate_concurrent_agents(cls, v: int) -> int:
        """Ensure concurrent agents setting is reasonable"""
        if v < 1:
            raise ValueError("Must allow at least 1 concurrent agent")
        if v > 20:
            raise ValueError("Too many concurrent agents (max: 20)")
        return v

    @field_validator("TEMPORAL_HOST")
    @classmethod
    def validate_temporal_host(cls, v: str) -> str:
        """Validate Temporal host format"""
        if not v:
            raise ValueError("Temporal host cannot be empty")
        if ":" not in v:
            raise ValueError("Temporal host must include port (e.g., localhost:7233)")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
