#!/bin/bash
set -e

echo "Running Alembic migrations..."
cd /home/Allie/develop/legalease/backend

# Check if PostgreSQL is available
echo "Checking PostgreSQL connection..."
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_USER=${POSTGRES_USER:-legalease}

# Wait for PostgreSQL to be ready
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ PostgreSQL is not available after $MAX_RETRIES attempts"
        echo "Please ensure PostgreSQL is running:"
        echo "  docker-compose up -d postgres"
        exit 1
    fi

    echo "Waiting for PostgreSQL... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

# Run migrations
echo ""
echo "Running migrations..."
alembic upgrade head

echo ""
echo "✅ Migrations complete"
echo ""
echo "To create a new migration:"
echo "  alembic revision --autogenerate -m 'description'"
