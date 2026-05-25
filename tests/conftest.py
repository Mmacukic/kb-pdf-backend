import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


os.environ.setdefault("APP_NAME", "Knowledge Base API")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "knowledge_base_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("USER_USERNAME", "user")
os.environ.setdefault("USER_PASSWORD", "user123")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("MINIO_BUCKET_NAME", "pdf-documents")
os.environ.setdefault("MINIO_SECURE", "false")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


from app.api.deps import get_current_user, require_admin
from app.main import app
from app.schemas.auth import CurrentUser


@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(username="admin", role="admin")


@pytest.fixture
def regular_user() -> CurrentUser:
    return CurrentUser(username="user", role="user")


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticate_as_admin(admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    return admin_user


@pytest.fixture
def authenticate_as_user(regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user
    return regular_user
