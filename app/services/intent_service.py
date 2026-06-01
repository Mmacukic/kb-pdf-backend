import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    MEMORY_UPDATE = "memory_update"
    MEMORY_QUERY = "memory_query"
    SMALL_TALK = "small_talk"
    RAG_QUERY = "rag_query"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    user_name: str | None = None


NAME_PATTERNS = [
    re.compile(
        r"\b(?:ja\s+se\s+zovem|zovem\s+se|moje\s+ime\s+je)\s+"
        r"(?P<name>[A-Za-zÀ-ž]+)",
        re.IGNORECASE,
    )
]

MEMORY_QUERY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bkako\s+se\s+(?:ja\s+)?zovem\b",
        r"\bkoje\s+je\s+moje\s+ime\b",
        r"\bznaš\s+li\s+moje\s+ime\b",
        r"\bznas\s+li\s+moje\s+ime\b",
        r"\bkako\s+mi\s+je\s+ime\b",
    ]
]

SMALL_TALK_MESSAGES = {
    "bok",
    "hej",
    "pozdrav",
    "hi",
    "hello",
    "halo",
    "dobar dan",
    "dobro jutro",
    "dobra večer",
    "dobra vecer",
}


def normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip().lower()


def classify_intent(message: str) -> Intent:
    return classify_message(message).intent


def classify_message(message: str) -> IntentResult:
    normalized_message = normalize_message(message)
    user_name = extract_user_name(message)

    if user_name:
        return IntentResult(
            intent=Intent.MEMORY_UPDATE,
            user_name=user_name
        )

    if any(pattern.search(normalized_message) for pattern in MEMORY_QUERY_PATTERNS):
        return IntentResult(intent=Intent.MEMORY_QUERY)

    if normalized_message.rstrip("!.?") in SMALL_TALK_MESSAGES:
        return IntentResult(intent=Intent.SMALL_TALK)

    return IntentResult(intent=Intent.RAG_QUERY)


def extract_user_name(message: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(message.strip())

        if match is None:
            continue

        name = match.group("name").strip(" .,!?:;")

        if name:
            return name[:1].upper() + name[1:].lower()

    return None
