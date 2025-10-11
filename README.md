# LegalEase AI

<div align="center">

[![License](https://img.shields.io/github/license/AlliecatOwO/legalease-ai?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/AlliecatOwO/legalease-ai?style=flat-square)](https://github.com/AlliecatOwO/legalease-ai/stargazers)
[![Issues](https://img.shields.io/github/issues/AlliecatOwO/legalease-ai?style=flat-square)](https://github.com/AlliecatOwO/legalease-ai/issues)
[![Last Commit](https://img.shields.io/github/last-commit/AlliecatOwO/legalease-ai?style=flat-square)](https://github.com/AlliecatOwO/legalease-ai/commits)

[![FastAPI](https://img.shields.io/badge/FastAPI-109989?logo=fastapi&logoColor=white&style=flat-square)](#tech-stack)
[![Nuxt](https://img.shields.io/badge/Nuxt_4-00DC82?logo=nuxt.js&logoColor=white&style=flat-square)](#tech-stack)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?logo=python&logoColor=white&style=flat-square)](#tech-stack)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=flat-square)](#tech-stack)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white&style=flat-square)](#tech-stack)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?logo=neo4j&logoColor=white&style=flat-square)](#tech-stack)
[![Qdrant](https://img.shields.io/badge/Qdrant-FF4D4D?style=flat-square)](#tech-stack)
[![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat-square)](#tech-stack)

**World-class AI-powered legal document search and analysis platform**

Self-hosted • Privacy-first • No external APIs • Fully local AI

[Features](#-features) • [Quick Start](#-quick-start) • [Demo](#-demo) • [Tech Stack](#-tech-stack)

</div>

---

## 📺 Demo

![LegalEase Demo](./frontend/app/assets/demo.gif)

---

## ✨ Features

### 🔍 **Hybrid Search Engine**
Lightning-fast hybrid search combining BM25 keyword matching with semantic vector search. Click results to jump directly to highlighted sections in PDFs. Sub-100ms latency for instant results.

### 📁 **Smart Case Management**
Organize documents into cases with load/unload capabilities. Bulk upload with drag-and-drop, automatic processing pipelines, and real-time status tracking.

### 🎙️ **AI Transcription**
70x real-time transcription with speaker diarization and word-level timestamps. Export to DOCX, SRT/VTT, or JSON. Process 1 hour of audio in ~50 seconds.

### 🤖 **AI-Powered Analysis**
- **Auto-Summarization**: LLM-generated document and transcript summaries
- **Entity Extraction**: Identify parties, dates, amounts, citations using GLiNER + LexNLP
- **Smart Tagging**: Automatic document categorization and metadata extraction
- **Knowledge Graphs**: Visualize entity relationships and citation networks with Neo4j

### 🎨 **Modern UI**
Built with Nuxt 4 and Nuxt UI 4. Native PDF viewer with search highlighting, responsive design, dark/light modes, and real-time updates.

### 🔒 **Privacy & Security**
100% local processing with no external APIs. All data stays on your infrastructure. Uses local Ollama models (Llama 3.1). Complete control over PostgreSQL, MinIO, and Qdrant storage.

---

## 🚀 Quick Start

### Prerequisites

- [mise](https://mise.jdx.dev/) - Dev tools, environments, and task runner
- Docker Engine 24.0+ with Docker Compose V2
- Minimum 8GB RAM (16GB recommended)
- 20GB available disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AlliecatOwO/legalease-ai.git
   cd legalease-ai
   ```

2. **Install mise** (if not already installed)
   ```bash
   curl https://mise.run | sh
   ```

3. **Start all services and initialize**
   ```bash
   mise run setup
   ```

   This single command will:
   - Start all Docker services
   - Pull Ollama AI models
   - Run database migrations

   Or run steps individually:
   ```bash
   mise run up              # Start all services
   mise run setup:models    # Download AI models
   mise run migrate         # Run database migrations
   ```

4. **Access the platform**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (legalease / legalease_dev_secret)
   - Neo4j Browser: http://localhost:7474 (neo4j / legalease_dev)

---

## 🏗️ Tech Stack

### Frontend
- **Nuxt 4** - Vue.js framework with server-side rendering
- **Nuxt UI 4** - Beautiful, accessible UI components
- **Cytoscape.js** - Knowledge graph visualization
- **PDF.js** - Native PDF rendering

### Backend
- **FastAPI** - Modern Python API framework
- **Celery** - Distributed task processing
- **SQLAlchemy** - Database ORM
- **Alembic** - Database migrations

### AI/ML
- **Ollama** - Local LLM inference (Llama 3.1 70B)
- **Sentence Transformers** - Text embeddings
- **GLiNER** - Named entity recognition
- **LexNLP** - Legal text analysis
- **Docling** - Document parsing with bounding boxes
- **Faster-Whisper** - Speech-to-text transcription

### Data Storage
- **PostgreSQL** - Relational database
- **Qdrant** - Vector database for semantic search
- **MinIO** - S3-compatible object storage
- **Neo4j** - Graph database for entity relationships
- **Redis** - Cache and message broker

---

## 📊 Performance

| Metric | Target |
|--------|--------|
| Search Latency (p95) | <100ms |
| Document Processing | <1 min per 100-page PDF |
| Transcription Speed | ~70x real-time |
| UI Frame Rate | 60fps (16ms) |
| Memory Usage | <8GB RAM |
| Storage Overhead | ~2x original file size |

---

## 🔧 Development

### Common Commands

```bash
# Start/stop services
mise run up                  # Start all services
mise run down                # Stop all services
mise run restart             # Restart services
mise run rebuild             # Rebuild and restart
mise run clean               # Stop and remove all data
mise run ps                  # Check service status

# View logs
mise run logs                # All services
mise run logs:backend        # Backend only
mise run logs:worker         # Worker only
mise run logs:frontend       # Frontend only

# Database operations
mise run migrate             # Run migrations
mise run migrate:create      # Create new migration (use DESCRIPTION env var)
mise run migrate:down        # Rollback one migration
mise run migrate:history     # View migration history
mise run psql                # Open PostgreSQL shell

# Testing
mise run test                # Run tests
mise run test:cov            # Run tests with coverage

# Shell access
mise run shell               # Backend container shell
mise run shell:frontend      # Frontend container shell

# Data seeding
mise run seed                # Seed with real PDFs
mise run seed:clear          # Clear and reseed database
```

### Local Development (without Docker)

```bash
# Frontend
mise run dev-frontend

# Backend
mise run dev-backend

# Worker
mise run dev-worker
```

### Available Tasks

Run `mise tasks` to see all available tasks with descriptions.

---

## 🐛 Troubleshooting

<details>
<summary><b>Services won't start</b></summary>

Check logs and disk space:
```bash
mise run logs
df -h
```

Reset everything:
```bash
mise run clean
docker system prune -a
mise run up
```
</details>

<details>
<summary><b>Database connection issues</b></summary>

Check PostgreSQL health:
```bash
mise run ps
mise run logs:backend
```

Reset database:
```bash
mise run clean
mise run up
mise run migrate
```
</details>

<details>
<summary><b>Out of memory</b></summary>

Increase Docker memory limit in Docker Desktop settings, or adjust service limits in `docker-compose.yml`.
</details>

<details>
<summary><b>mise not found</b></summary>

Install mise:
```bash
curl https://mise.run | sh
```

Or use your package manager:
```bash
# macOS
brew install mise

# Ubuntu/Debian
apt install mise

# Arch Linux
pacman -S mise
```

After installation, activate it in your shell:
```bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc  # for bash
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc    # for zsh
```
</details>

---

## 🎯 Roadmap

- [ ] Multi-tenant support with user authentication
- [ ] Advanced citation network analysis
- [ ] Custom LLM model fine-tuning
- [ ] Collaborative case sharing
- [ ] Mobile app (iOS/Android)
- [ ] OCR for scanned documents
- [ ] Legal research AI assistant

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with amazing open-source technologies:
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Qdrant](https://qdrant.tech/) - Vector similarity search
- [Nuxt](https://nuxt.com/) - Vue.js framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Neo4j](https://neo4j.com/) - Graph database platform

---

<div align="center">
Made with ❤️ by <a href="https://github.com/AlliecatOwO">AlliecatOwO</a>
</div>
