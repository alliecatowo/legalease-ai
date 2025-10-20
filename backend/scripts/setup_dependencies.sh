#!/bin/bash
set -e

echo "Installing Python dependencies..."
cd /home/Allie/develop/legalease/backend

# Use uv to sync dependencies
echo "Running uv sync..."
uv sync

echo ""
echo "Verifying critical packages..."
echo "================================"

# Verify critical packages
python -c "import haystack; print(f'✓ Haystack: {haystack.__version__}')" || echo "✗ Haystack: FAILED"
python -c "import langgraph; print(f'✓ LangGraph: {langgraph.__version__}')" || echo "✗ LangGraph: FAILED"
python -c "import temporalio; print(f'✓ Temporal: {temporalio.__version__}')" || echo "✗ Temporal: FAILED"
python -c "from opensearchpy import AsyncOpenSearch; print('✓ OpenSearch: OK')" || echo "✗ OpenSearch: FAILED"
python -c "from qdrant_client import AsyncQdrantClient; print('✓ Qdrant: OK')" || echo "✗ Qdrant: FAILED"
python -c "from neo4j import AsyncGraphDatabase; print('✓ Neo4j: OK')" || echo "✗ Neo4j: FAILED"
python -c "import fastapi; print(f'✓ FastAPI: {fastapi.__version__}')" || echo "✗ FastAPI: FAILED"
python -c "import sqlalchemy; print(f'✓ SQLAlchemy: {sqlalchemy.__version__}')" || echo "✗ SQLAlchemy: FAILED"
python -c "import alembic; print(f'✓ Alembic: {alembic.__version__}')" || echo "✗ Alembic: FAILED"

echo ""
echo "================================"
echo "✅ Dependencies installed successfully"
