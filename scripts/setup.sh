#!/bin/bash
set -e

echo "========================================="
echo "  LegalEase Development Environment Setup"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if mise is installed
echo "Checking for mise..."
if ! command -v mise &> /dev/null; then
    echo -e "${RED}Error: mise is not installed${NC}"
    echo "Please install mise first:"
    echo "  curl https://mise.run | sh"
    echo "Or visit: https://mise.jdx.dev/getting-started.html"
    exit 1
fi
echo -e "${GREEN}mise is installed${NC}"
echo ""

# Install project tools via mise
echo "Installing project tools (Node.js, pnpm, Python, Poetry)..."
mise install
echo -e "${GREEN}Tools installed successfully${NC}"
echo ""

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Check if Docker is running
echo "Checking Docker..."
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}Docker is running${NC}"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}Warning: docker-compose.yml not found${NC}"
    echo "Skipping Docker services startup"
else
    # Start Docker services
    echo "Starting Docker services (PostgreSQL, Redis, Qdrant, MinIO, Neo4j, Ollama)..."
    docker compose up -d
    echo -e "${GREEN}Docker services started${NC}"
    echo ""

    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 10
fi

# Install frontend dependencies
if [ -d "frontend" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    pnpm install
    cd ..
    echo -e "${GREEN}Frontend dependencies installed${NC}"
    echo ""
else
    echo -e "${YELLOW}Warning: frontend directory not found${NC}"
fi

# Install backend dependencies
if [ -d "backend" ]; then
    echo "Installing backend dependencies..."
    cd backend
    poetry install
    cd ..
    echo -e "${GREEN}Backend dependencies installed${NC}"
    echo ""
else
    echo -e "${YELLOW}Warning: backend directory not found${NC}"
fi

# Run database initialization
if [ -f "scripts/init_db.py" ]; then
    echo "Initializing database..."
    python scripts/init_db.py
    echo -e "${GREEN}Database initialized${NC}"
    echo ""
else
    echo -e "${YELLOW}Warning: scripts/init_db.py not found${NC}"
    echo "Skipping database initialization"
fi

# Run database migrations
if [ -d "backend/alembic" ]; then
    echo "Running database migrations..."
    cd backend
    poetry run alembic upgrade head
    cd ..
    echo -e "${GREEN}Database migrations completed${NC}"
    echo ""
else
    echo -e "${YELLOW}Warning: Alembic migrations not found${NC}"
    echo "Skipping migrations"
fi

# Download AI models
echo -e "${YELLOW}Would you like to download AI models now? This may take a while. (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    if [ -f "scripts/download_models.sh" ]; then
        echo "Downloading AI models..."
        ./scripts/download_models.sh
        echo -e "${GREEN}Models downloaded${NC}"
        echo ""
    else
        echo -e "${YELLOW}Warning: scripts/download_models.sh not found${NC}"
        echo "You can download models later with: mise run download-models"
    fi
else
    echo "Skipping model download. You can download later with: mise run download-models"
    echo ""
fi

# Success message
echo ""
echo "========================================="
echo -e "${GREEN}  Setup completed successfully!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and update values:"
echo "     cp .env.example .env"
echo ""
echo "  2. Start the development servers:"
echo "     mise run dev-frontend   # Frontend (Nuxt)"
echo "     mise run dev-backend    # Backend (FastAPI)"
echo "     mise run dev-worker     # Celery worker"
echo ""
echo "  3. Access the application:"
echo "     Frontend: http://localhost:3000"
echo "     Backend API: http://localhost:8000"
echo "     API Docs: http://localhost:8000/docs"
echo ""
echo "  4. Manage Docker services:"
echo "     mise run up      # Start services"
echo "     mise run down    # Stop services"
echo "     mise run logs    # View logs"
echo ""
echo "  5. Database migrations:"
echo "     mise run db-migrate   # Apply migrations"
echo "     mise run db-rollback  # Rollback one migration"
echo ""
echo "Happy coding!"
