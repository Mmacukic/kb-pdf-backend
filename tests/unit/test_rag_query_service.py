import asyncio

from app.services import rag_query_service


def test_filter_approved_indexed_chunks_removes_stale_and_unapproved_sources(monkeypatch):
    async def fake_get_document_by_id(document_id: str):
        documents = {
            "current": {
                "indexing_status": "indexed",
                "current_version": 2,
                "approved": True,
            },
            "old": {
                "indexing_status": "indexed",
                "current_version": 2,
                "approved": True,
            },
            "pending": {
                "indexing_status": "pending",
                "current_version": 1,
                "approved": True,
            },
            "unapproved": {
                "indexing_status": "indexed",
                "current_version": 1,
                "approved": False,
            },
        }
        return documents.get(document_id)

    async def fake_get_blog_source_by_id(source_id: str):
        blogs = {
            "blog": {"indexing_status": "indexed", "approved": True},
            "failed": {"indexing_status": "failed", "approved": True},
            "hidden": {"indexing_status": "indexed", "approved": False},
        }
        return blogs.get(source_id)

    monkeypatch.setattr(rag_query_service, "get_document_by_id", fake_get_document_by_id)
    monkeypatch.setattr(rag_query_service, "get_blog_source_by_id", fake_get_blog_source_by_id)

    chunks = [
        {"source_type": "pdf", "source_id": "current", "version": 2},
        {"source_type": "pdf", "source_id": "old", "version": 1},
        {"source_type": "pdf", "source_id": "pending", "version": 1},
        {"source_type": "pdf", "source_id": "unapproved", "version": 1},
        {"source_type": "blog", "source_id": "blog"},
        {"source_type": "blog", "source_id": "failed"},
        {"source_type": "blog", "source_id": "hidden"},
        {"source_type": "blog", "source_id": "missing"},
    ]

    filtered = asyncio.run(rag_query_service.filter_approved_indexed_chunks(chunks))

    assert filtered == [
        {"source_type": "pdf", "source_id": "current", "version": 2},
        {"source_type": "blog", "source_id": "blog"},
    ]
