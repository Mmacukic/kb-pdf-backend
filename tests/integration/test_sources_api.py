from datetime import datetime, timezone

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def test_get_sources_returns_pdf_and_blog_sources(client, authenticate_as_user, monkeypatch):
    async def fake_list_knowledge_sources(current_user):
        return [
            {
                "id": "pdf-1",
                "type": "pdf",
                "filename": "handbook.pdf",
                "title": "handbook.pdf",
                "url": None,
                "status": "indexed",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "chunks_count": 3,
            },
            {
                "id": "blog-1",
                "type": "blog",
                "filename": None,
                "title": "Article",
                "url": "https://example.com/article",
                "status": "indexed",
                "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "chunks_count": 2,
            },
        ]

    monkeypatch.setattr(
        "app.api.routes.sources.list_knowledge_sources",
        fake_list_knowledge_sources,
    )

    response = client.get("/sources")

    assert response.status_code == 200
    assert [source["type"] for source in response.json()] == ["pdf", "blog"]


def test_regular_user_cannot_create_blog_source(client, regular_user, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: regular_user

    async def noop_log_file_action(**kwargs):
        return None

    monkeypatch.setattr("app.api.deps.log_file_action", noop_log_file_action)

    response = client.post(
        "/sources/blog",
        json={"url": "https://example.com/article"},
    )

    assert response.status_code == 403


def test_admin_can_create_blog_source(client, authenticate_as_admin, monkeypatch):
    async def fake_add_blog_source(url, current_user, background_tasks):
        return {
            "id": "blog-1",
            "type": "blog",
            "title": url,
            "url": url,
            "status": "pending",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "chunks_count": 0,
        }

    monkeypatch.setattr("app.api.routes.sources.add_blog_source", fake_add_blog_source)

    response = client.post(
        "/sources/blog",
        json={"url": "https://example.com/article"},
    )

    assert response.status_code == 201
    assert response.json()["type"] == "blog"
    assert response.json()["status"] == "pending"


def test_admin_can_delete_blog_source(client, authenticate_as_admin, monkeypatch):
    async def fake_remove_blog_source(source_id, current_user, background_tasks):
        return {
            "message": "Blog source deleted successfully",
            "blog_source_id": source_id,
        }

    monkeypatch.setattr("app.api.routes.sources.remove_blog_source", fake_remove_blog_source)

    response = client.delete("/sources/blog/blog-1")

    assert response.status_code == 200
    assert response.json()["blog_source_id"] == "blog-1"
