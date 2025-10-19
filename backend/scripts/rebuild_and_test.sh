#!/bin/bash
set -e

echo "🔧 Rebuilding Docker containers with new dependencies..."
cd /home/Allie/develop/legalease

# Check for Gemini API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set. VLM features will be disabled."
    echo "   Set it: export GOOGLE_API_KEY=your_key_here"
fi

# Stop existing containers
docker compose down

# Rebuild with no cache for clean build
docker compose build --no-cache

# Start services
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker compose ps

# Check worker logs for any immediate errors
echo "📋 Worker logs (last 50 lines):"
docker compose logs --tail=50 worker

echo "✅ Rebuild complete! Services running."
echo "   Backend: http://localhost:8000/docs"
echo "   Frontend: http://localhost:3000"
