# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Speaking Test System (AI 口语测评系统) - A full-stack application for evaluating spoken English using Qwen AI models. The system includes student-facing test interfaces, parent report viewing, and teacher admin dashboards.

## Development Commands

### Backend (Python/FastAPI)

```bash
cd backend

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure API keys and database

# Run development server (API only)
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000

# Run all services (API + Workers + Redis + RabbitMQ) - macOS only
./scripts/dev.sh

# Run individual workers
python scripts/part1_worker.py
python scripts/part2_worker.py
python scripts/interpretation_worker.py
python scripts/dlq_worker.py

# Tests
pytest                           # Run all tests
pytest tests/test_auth.py        # Run single test file
pytest -k "test_login"           # Run tests matching pattern
pytest --cov=src                 # Run with coverage

# API docs available at http://localhost:8000/docs
```

### Frontend (React/Vite/TypeScript)

Each frontend app is independent with its own package.json:

```bash
# Student H5 (Port 3001)
cd frontend/student-h5 && npm install && npm run dev

# Parent H5 (Port 3000)
cd frontend/parent-h5 && npm install && npm run dev

# Teacher Web (Port 5173)
cd frontend/teacher-web && npm install && npm run dev
npm run lint  # ESLint (teacher-web only)
npm run build # Build for production
```

## Architecture

### Backend: Clean Architecture (Hexagonal)

```
backend/src/
├── domain/           # Core business entities & port interfaces
│   ├── entities/     # Domain models (pure Python, no framework deps)
│   └── ports/        # Repository interfaces
├── use_cases/        # Application business logic
│   ├── evaluate_part1.py    # Word/phrase reading evaluation
│   ├── evaluate_part2.py    # Q&A dialogue evaluation
│   ├── evaluate_interpretation.py  # AI report generation
│   └── parent_report.py     # Report data assembly
├── adapters/         # External world implementations
│   ├── controllers/  # FastAPI routers (HTTP layer)
│   ├── gateways/     # External APIs (Qwen AI, OSS, CRM, Email)
│   └── repositories/ # SQLAlchemy models & DB access
└── infrastructure/   # Framework & config
    ├── main.py       # FastAPI app entry point
    ├── config.py     # Environment settings (pydantic-settings)
    ├── database.py   # AsyncPG connection pool
    └── queue_service.py  # RabbitMQ task queues
```

### Async Processing Flow

Evaluation tasks are processed asynchronously via RabbitMQ:

1. **API receives audio upload** → Stores in OSS → Enqueues task
2. **Worker consumes task** → Downloads audio → Calls Qwen API → Updates DB
3. **Dead Letter Queue (DLQ)** → Failed tasks after 3 retries → Marks test as `failed`

Queue names: `part1_evaluation_tasks`, `part2_evaluation_tasks`, `interpretation_tasks`

### Key External Integrations

- **Qwen AI**: `qwen3-omni-flash` for audio evaluation, `qwen-plus` for text analysis
- **Aliyun OSS**: Audio file storage
- **RabbitMQ**: Task queue with dead letter handling
- **PostgreSQL**: Primary data store (async via asyncpg)
- **Redis**: Rate limiting (optional, falls back to memory)

### Frontend Structure

- **student-h5**: Mobile-first test interface (audio recording, gamified UI)
- **parent-h5**: Report viewer with radar charts and AI feedback
- **teacher-web**: Admin dashboard with analytics, student management, cost tracking

All frontends use: React 19, Vite 6, TypeScript, Tailwind CSS

## Key Patterns

### Database Session

```python
from src.infrastructure.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...
```

### Testing

Tests use SQLite in-memory with fixtures from `backend/tests/conftest.py`:
- `client` - AsyncClient with test DB
- `auth_teacher` / `auth_admin` - Auth mocking fixtures
- `user_factory` - Create test users with custom roles

### Configuration

All settings via environment variables, defined in `src/infrastructure/config.py`. Copy `.env.example` to `.env` for local development. Critical production settings:
- `JWT_SECRET_KEY` - Must change from default
- `COOKIE_SECURE=true` - Required for HTTPS
- `DEBUG=false` - Disables dev-only features
