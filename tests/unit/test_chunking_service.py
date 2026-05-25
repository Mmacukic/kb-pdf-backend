from app.services.chunking_service import chunk_text


def test_chunk_text_preserves_paragraph_boundaries_when_possible():
    text = (
        "First paragraph has a complete idea.\n\n"
        "Second paragraph has another complete idea.\n\n"
        "Third paragraph closes the example."
    )

    chunks = chunk_text(text, chunk_size=14, overlap=0)

    assert len(chunks) > 1
    assert "First paragraph has a complete idea." in chunks[0]
    assert all(chunk.strip() == chunk for chunk in chunks)


def test_chunk_text_returns_empty_list_for_blank_input():
    assert chunk_text("  \n\n  ") == []
