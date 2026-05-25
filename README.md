# Knowledge Base PDF Backend

FastAPI backend for a managed knowledge base with JWT auth, role-based PDF management, blog URL ingestion, vector retrieval, and HTTP/WebSocket chat.

## Stack

- FastAPI
- MongoDB for users, source metadata, and action logs
- MinIO for PDF object storage
- Qdrant for indexed PDF/blog chunks
- OpenAI for embeddings and chat answers
- Dockerfile and docker-compose support

## Architecture

The backend is organized as a small layered FastAPI application:

- `app/main.py`: application startup, CORS, router registration, and service initialization.
- `app/api/routes/`: HTTP and WebSocket route handlers for auth, documents, sources, blogs, health checks, and chat.
- `app/api/deps.py`: shared FastAPI dependencies such as authenticated user lookup and role checks.
- `app/schemas/`: Pydantic request and response models.
- `app/services/`: business workflows for authentication, PDF handling, blog ingestion, chunking, embedding, RAG indexing/querying, storage, and logging.
- `app/repositories/`: database/vector-store access for MongoDB and Qdrant.
- `app/db/`: MongoDB client lifecycle.
- `app/core/`: settings and security helpers.

Runtime services:

- MongoDB stores users, PDF/blog metadata, extracted blog text, action logs, and short-term chat session memory.
- MinIO stores uploaded PDF bytes.
- Qdrant stores vector embeddings for PDF and blog chunks.
- OpenAI is used for embeddings and chat completion when chat/RAG features are exercised.

Startup flow:

1. Connect to MongoDB.
2. Seed the default admin/user accounts from environment variables.
3. Ensure the Qdrant collection exists.
4. Create MongoDB indexes for documents, blog sources, and chat sessions.
5. Ensure the MinIO bucket exists.

Ingestion flow:

1. Admin uploads a PDF or submits a blog URL.
2. The source metadata is stored in MongoDB.
3. PDF bytes are stored in MinIO, or blog HTML is fetched and extracted.
4. Text is chunked, embedded, and upserted to Qdrant.
5. Users can retrieve the indexed context through HTTP or WebSocket chat.

## Running

Prerequisites:

- Docker Engine with Docker Compose v2
- Python 3.12 if running without Docker

Docker:

```bash
cp .env.example .env
docker compose up --build
```

The API will be available at:

- `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- MinIO console: `http://127.0.0.1:9001`
- Qdrant dashboard: `http://127.0.0.1:6333/dashboard`


