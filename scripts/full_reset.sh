#!/bin/bash
set -e

echo "🔥 FULL DATABASE RESET - This will delete ALL data"
echo "⚠️  This will remove:"
echo "   - PostgreSQL database"
echo "   - Qdrant vector store"
echo "   - Redis cache"
echo "   - MinIO object storage"
echo "   - Neo4j graph database"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

echo "📦 Stopping all services..."
docker compose down

echo "🗑️  Removing data volumes..."
docker volume rm legalease_postgres_data || true
docker volume rm legalease_qdrant_data || true
docker volume rm legalease_redis_data || true
docker volume rm legalease_minio_data || true
docker volume rm legalease_neo4j_data || true
docker volume rm legalease_neo4j_logs || true

echo "🚀 Starting infrastructure services..."
docker compose up -d postgres redis qdrant minio neo4j

echo "⏳ Waiting for services to be ready (15 seconds)..."
sleep 15

echo "📝 Running database migrations..."
docker compose exec backend alembic upgrade head

echo "🌱 Seeding database with real PDFs..."
docker compose exec backend python scripts/seed_with_real_pdfs.py --clear-db

echo ""
echo "✅ Reset complete!"
echo "🎉 Database has been reset and seeded with real legal documents"
echo ""
echo "Next steps:"
echo "  1. Start all services: make up"
echo "  2. Open frontend: http://localhost:3000"
echo "  3. Test search functionality"
