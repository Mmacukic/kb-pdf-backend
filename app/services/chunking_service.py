import re

from app.core.config import settings


try:
    import tiktoken
except ImportError:
    tiktoken = None


def _get_token_encoder():
    if tiktoken is None:
        return None

    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def _token_count(text: str, encoder) -> int:
    if encoder is None:
        return max(1, len(text) // 4)

    return len(encoder.encode(text))


def _split_text_units(text: str) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    units = []

    for paragraph in paragraphs:
        if len(paragraph) <= 1000:
            units.append(paragraph)
            continue

        units.extend(
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
            if sentence.strip()
        )

    return units


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None
) -> list[str]:
    actual_chunk_size = chunk_size or settings.rag_chunk_size
    actual_overlap = overlap or settings.rag_chunk_overlap

    normalized_text = re.sub(r"[ \t]+", " ", text).strip()

    if not normalized_text:
        return []

    encoder = _get_token_encoder()
    units = _split_text_units(normalized_text)
    chunks = []
    current_units = []
    current_size = 0

    for unit in units:
        unit_size = _token_count(unit, encoder)

        if current_units and current_size + unit_size > actual_chunk_size:
            chunks.append("\n\n".join(current_units).strip())

            overlap_units = []
            overlap_size = 0

            for previous_unit in reversed(current_units):
                previous_size = _token_count(previous_unit, encoder)

                if overlap_size + previous_size > actual_overlap:
                    break

                overlap_units.insert(0, previous_unit)
                overlap_size += previous_size

            current_units = overlap_units
            current_size = overlap_size

        current_units.append(unit)
        current_size += unit_size

    if current_units:
        chunks.append("\n\n".join(current_units).strip())

    return chunks
