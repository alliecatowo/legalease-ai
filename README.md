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

- Docker Engine 24.0+ with Docker Compose V2
- Minimum 8GB RAM (16GB recommended)
- 20GB available disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AlliecatOwO/legalease-ai.git
   cd legalease-ai
   ```

2. **Start all services**
   ```bash
   docker compose up -d
   ```

3. **Initialize the platform**
   ```bash
   # Pull Ollama models
   docker compose exec ollama ollama pull llama3.1
   docker compose exec ollama ollama pull nomic-embed-text

   # Run database migrations
   docker compose exec backend alembic upgrade head

   # Setup storage and vector DB
   docker compose exec backend python -m app.scripts.setup_storage
   docker compose exec backend python -m app.scripts.setup_qdrant
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

### View Logs
```bash
docker compose logs -f              # All services
docker compose logs -f backend      # Specific service
```

### Run Tests
```bash
docker compose exec backend pytest -v --cov=app
docker compose exec frontend pnpm test
```

### Database Migrations
```bash
docker compose exec backend alembic revision --autogenerate -m "description"
docker compose exec backend alembic upgrade head
```

### Hot Reload
Both frontend and backend support hot reload in development mode. Code changes trigger automatic rebuilds.

---

## 🐛 Troubleshooting

<details>
<summary><b>Services won't start</b></summary>

Check logs and disk space:
```bash
docker compose logs
df -h
```

Reset everything:
```bash
docker compose down -v
docker system prune -a
docker compose up -d
```
</details>

<details>
<summary><b>Database connection issues</b></summary>

Check PostgreSQL health:
```bash
docker compose ps postgres
docker compose logs postgres
```

Reset database:
```bash
docker compose down
docker volume rm legalease-postgres-data
docker compose up -d postgres
docker compose exec backend alembic upgrade head
```
</details>

<details>
<summary><b>Out of memory</b></summary>

Increase Docker memory limit in Docker Desktop settings, or adjust service limits in `docker-compose.yml`.
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
