from app.services.intent_service import (
    Intent,
    classify_intent,
    extract_user_name,
)


def test_classify_memory_updates_and_extract_names():
    assert classify_intent("Ja se zovem Marcel") == Intent.MEMORY_UPDATE
    assert classify_intent("zovem se ana") == Intent.MEMORY_UPDATE
    assert classify_intent("Moje ime je Ivan") == Intent.MEMORY_UPDATE

    assert extract_user_name("Ja se zovem Marcel") == "Marcel"
    assert extract_user_name("zovem se ana") == "Ana"
    assert extract_user_name("Moje ime je Ivan") == "Ivan"


def test_classify_memory_queries_and_small_talk():
    assert classify_intent("Kako se ja zovem?") == Intent.MEMORY_QUERY
    assert classify_intent("Kako se zovem?") == Intent.MEMORY_QUERY
    assert classify_intent("Koje je moje ime?") == Intent.MEMORY_QUERY
    assert classify_intent("Znaš li moje ime?") == Intent.MEMORY_QUERY
    assert classify_intent("Kako mi je ime?") == Intent.MEMORY_QUERY
    assert classify_intent("Bok") == Intent.SMALL_TALK


def test_classify_rag_query_by_default():
    assert classify_intent("What are the backend technical requirements?") == Intent.RAG_QUERY
