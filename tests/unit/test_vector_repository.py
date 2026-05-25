from qdrant_client.models import Filter

from app.repositories.vector_repository import (
    build_source_filter,
    build_source_types_filter,
)


def test_build_source_filter_includes_source_id_and_version():
    vector_filter = build_source_filter(
        source_type="pdf",
        source_id="document-id",
        version=3,
    )

    assert isinstance(vector_filter, Filter)
    assert len(vector_filter.must) == 3


def test_build_source_types_filter_returns_none_without_source_types():
    assert build_source_types_filter(None) is None
    assert build_source_types_filter([]) is None


def test_build_source_types_filter_uses_should_conditions():
    vector_filter = build_source_types_filter(["pdf", "blog"])

    assert isinstance(vector_filter, Filter)
    assert len(vector_filter.should) == 2
