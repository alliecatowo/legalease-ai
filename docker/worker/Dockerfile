# Base stage with Python 3.11
FROM python:3.11-slim AS base

# Install system dependencies (no CUDA - PyTorch bundles it)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Development stage
FROM base AS development

# Install all dependencies including worker-specific dependencies
RUN uv sync --group worker

# Copy application code
COPY backend/ ./

# Create cache directory for models
RUN mkdir -p /root/.cache

# Set library path for PyTorch's bundled NVIDIA CUDA libraries
ENV LD_LIBRARY_PATH=/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cublas/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusparse/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cufft/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/curand/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusolver/lib

# Create CuDNN library symlinks for version compatibility
RUN for lib_dir in cudnn cublas cuda_runtime cusparse cufft curand cusolver; do \
        cd /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib 2>/dev/null && \
        for f in *.so.9 2>/dev/null; do \
            [ -f "$f" ] && ln -sf "$f" "${f}.1.0" && ln -sf "$f" "${f}.1"; \
        done || true; \
    done

# Start Celery worker
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

# Production dependencies stage
FROM base AS dependencies

# Install production dependencies with worker group
RUN uv sync --no-dev --group worker

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies (no CUDA - PyTorch bundles it)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    git \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application code
COPY backend/ ./

# Create non-root user
RUN useradd -m -u 1000 legalease && \
    mkdir -p /home/legalease/.cache && \
    chown -R legalease:legalease /app /home/legalease/.cache

USER legalease

# Set cache directory
ENV HOME=/home/legalease

# Set library path for PyTorch's bundled NVIDIA CUDA libraries
ENV LD_LIBRARY_PATH=/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cublas/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusparse/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cufft/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/curand/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusolver/lib

# Create CuDNN library symlinks for version compatibility
RUN for lib_dir in cudnn cublas cuda_runtime cusparse cufft curand cusolver; do \
        cd /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib 2>/dev/null && \
        for f in *.so.9 2>/dev/null; do \
            [ -f "$f" ] && ln -sf "$f" "${f}.1.0" && ln -sf "$f" "${f}.1"; \
        done || true; \
    done

# Start Celery worker with optimized settings
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100"]
