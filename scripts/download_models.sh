#!/bin/bash
set -e

echo "========================================="
echo "  Downloading AI Models for LegalEase"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Ollama is running
echo "Checking Ollama availability..."
if ! curl -s http://localhost:11434/api/version &> /dev/null; then
    echo -e "${RED}Error: Ollama is not running${NC}"
    echo "Please start Ollama with: docker compose up -d ollama"
    echo "Or start the Ollama service if running locally"
    exit 1
fi
echo -e "${GREEN}Ollama is running${NC}"
echo ""

# Pull LLaMA 3.1 70B model for general legal reasoning
echo "Downloading LLaMA 3.1:70B (this may take a while)..."
echo "This model is used for general legal reasoning and document analysis"
ollama pull llama3.1:70b
echo -e "${GREEN}LLaMA 3.1:70B downloaded${NC}"
echo ""

# Pull NuExtract model for structured data extraction
echo "Downloading NuExtract..."
echo "This model is used for extracting structured information from legal documents"
ollama pull nuextract
echo -e "${GREEN}NuExtract downloaded${NC}"
echo ""

# Pull LLaVA model for video/image analysis
echo "Downloading LLaVA:13B for video analysis..."
echo "This model is used for analyzing video evidence and visual content"
ollama pull llava:13b
echo -e "${GREEN}LLaVA:13B downloaded${NC}"
echo ""

# Download Whisper models for audio transcription
echo "Downloading Whisper models for audio transcription..."
echo "Checking for Whisper installation..."

# Create models directory if it doesn't exist
mkdir -p models/whisper

# Download Whisper models using Python
python3 << 'PYTHON_SCRIPT'
import sys
import os

try:
    import whisper
    print("Whisper is already installed")
except ImportError:
    print("Whisper not found. Installing...")
    os.system("pip install openai-whisper")
    import whisper

print("\nDownloading Whisper base model...")
model = whisper.load_model("base", download_root="models/whisper")
print("Whisper base model downloaded successfully")

print("\nDownloading Whisper medium model for better accuracy...")
model = whisper.load_model("medium", download_root="models/whisper")
print("Whisper medium model downloaded successfully")

PYTHON_SCRIPT

echo -e "${GREEN}Whisper models downloaded${NC}"
echo ""

# Download BGE embedding model
echo "Downloading BGE-base-en embedding model..."
echo "This model is used for semantic search and document similarity"

# Create embeddings directory
mkdir -p models/embeddings

# Download embedding model using Python
python3 << 'PYTHON_SCRIPT'
import sys
import os

try:
    from sentence_transformers import SentenceTransformer
    print("sentence-transformers is already installed")
except ImportError:
    print("sentence-transformers not found. Installing...")
    os.system("pip install sentence-transformers")
    from sentence_transformers import SentenceTransformer

print("\nDownloading BGE-base-en embedding model...")
model = SentenceTransformer('BAAI/bge-base-en-v1.5', cache_folder="models/embeddings")
print("BGE-base-en model downloaded successfully")

# Test the model
print("\nTesting embedding model...")
embeddings = model.encode(["This is a test sentence"])
print(f"Embedding dimension: {len(embeddings[0])}")
print("Embedding model is working correctly")

PYTHON_SCRIPT

echo -e "${GREEN}BGE-base-en embedding model downloaded${NC}"
echo ""

# Download additional legal-specific model (optional)
echo -e "${YELLOW}Would you like to download additional legal-specific models? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Downloading additional legal models..."

    # Download legal-specific embedding model
    python3 << 'PYTHON_SCRIPT'
from sentence_transformers import SentenceTransformer
import os

print("Downloading legal-bert embedding model...")
model = SentenceTransformer('nlpaueb/legal-bert-base-uncased', cache_folder="models/embeddings")
print("Legal-BERT model downloaded successfully")

PYTHON_SCRIPT

    echo -e "${GREEN}Additional legal models downloaded${NC}"
else
    echo "Skipping additional legal models"
fi

echo ""
echo "========================================="
echo -e "${GREEN}  All models downloaded successfully!${NC}"
echo "========================================="
echo ""
echo "Downloaded models:"
echo "  - LLaMA 3.1:70B (Ollama)"
echo "  - NuExtract (Ollama)"
echo "  - LLaVA:13B (Ollama)"
echo "  - Whisper base & medium (local)"
echo "  - BGE-base-en embeddings (local)"
echo ""
echo "Models are stored in:"
echo "  - Ollama models: ~/.ollama/models (or Docker volume)"
echo "  - Whisper models: ./models/whisper"
echo "  - Embedding models: ./models/embeddings"
echo ""
echo "You can now start using LegalEase with AI capabilities!"
