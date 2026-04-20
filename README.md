# DocMind — Intelligent Document Q&A Platform

A production-grade RAG platform for uploading documents, asking natural language questions, and getting accurate, context-grounded answers powered by local LLMs.

## Quick Start

```bash
# Start all services
docker-compose up --build

# Pull an LLM model (in another terminal)
docker exec -it docmind-ollama-1 ollama pull llama3.2
docker exec -it docmind-ollama-1 ollama pull nomic-embed-text
```

## Access

| Service | URL |
|---------|-----|
| App (via nginx) | http://localhost:8080 |
| Frontend (direct) | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

## Default Credentials

- **Admin**: admin@docmind.local / admin123

## Architecture

- **Backend**: FastAPI + Celery + LangChain text splitters
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Vector DB**: ChromaDB
- **Relational DB**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **LLM**: Ollama (llama3.2, mistral, etc.)
- **Reverse Proxy**: Nginx

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Register |
| POST | /api/v1/auth/login | Login (JWT) |
| POST | /api/v1/auth/refresh | Refresh token |
| GET | /api/v1/auth/me | Current user |
| POST | /api/v1/documents/upload | Upload document |
| GET | /api/v1/documents | List documents |
| DELETE | /api/v1/documents/{id} | Delete document |
| POST | /api/v1/chat | Chat (non-streaming) |
| POST | /api/v1/chat/stream | Chat (SSE streaming) |
| GET | /api/v1/chat/history | List conversations |
| POST | /api/v1/chat/feedback | Submit feedback |
| GET | /api/v1/admin/stats | Admin stats |
| GET | /api/v1/admin/users | List users (admin) |
| GET | /api/v1/admin/models | List Ollama models |

## Project Structure

```
docmind/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models/              # ORM models (User, Document, Chat, APIKey)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # RAG engine, LLM, embeddings, doc processor
│   │   ├── tasks/               # Celery async ingestion
│   │   └── middleware/          # Auth (JWT), request logging
│   ├── alembic/                 # DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (chat, documents, settings, admin)
│   │   ├── components/          # UI components (chat, documents, sidebar)
│   │   ├── hooks/               # React Query hooks
│   │   ├── lib/                 # API client, utilities
│   │   ├── stores/              # Zustand stores (auth, chat, theme)
│   │   └── types/               # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml           # 8 services
├── nginx.conf                   # Reverse proxy config
└── README.md
```
