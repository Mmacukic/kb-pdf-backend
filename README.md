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

## Chat Session Memory

Chat supports short-term, session-level memory for simple conversational facts such as the user's first name. The memory is stored in MongoDB in the `chat_sessions` collection and is scoped by both authenticated user and `session_id`.

The frontend should send the same `session_id` for related chat messages. If a chat request omits `session_id`, the backend generates one and returns it in the chat response. Reuse that returned value on the next message in the same conversation.

Example HTTP flow:

```json
{
  "message": "Ja se zovem Marcel",
  "session_id": "session-123"
}
```

The assistant stores `memory.user_name = "Marcel"` for that session and skips RAG. A later request with the same `session_id`:

```json
{
  "message": "Kako se ja zovem?",
  "session_id": "session-123"
}
```

returns an answer from session memory and also skips RAG. Knowledge-base questions continue through the existing PDF/blog retrieval pipeline and remain grounded in retrieved indexed context.

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

## Health Endpoints

- `GET /health`: liveness check. Returns `200` when the FastAPI process is running.
- `GET /health/ready`: readiness check. Returns `200` when MongoDB, MinIO, and Qdrant are reachable; returns `503` when one or more dependencies are unavailable.

Healthy readiness response:

```json
{
  "status": "ok",
  "checks": {
    "mongo": "ok",
    "minio": "ok",
    "qdrant": "ok"
  }
}
```

Degraded readiness response:

```json
{
  "status": "degraded",
  "checks": {
    "mongo": "ok",
    "minio": "ok",
    "qdrant": "error"
  }
}
```
