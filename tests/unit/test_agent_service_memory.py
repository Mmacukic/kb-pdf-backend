import asyncio

from app.schemas.auth import CurrentUser
from app.services import agent_service


def run(coro):
    return asyncio.run(coro)


class MemoryHarness:
    def __init__(self):
        self.memory_by_session = {}
        self.messages = []
        self.rag_calls = []

    async def get_session_memory(self, session_id, user_id):
        return self.memory_by_session.setdefault((session_id, user_id), {})

    async def save_user_name(self, session_id, user_id, user_name):
        self.memory_by_session.setdefault((session_id, user_id), {})["user_name"] = user_name

    async def save_chat_exchange(self, session_id, user_id, user_message, assistant_message):
        self.messages.append({
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
        })

    async def answer_question_with_rag(self, question, current_user):
        self.rag_calls.append(question)
        return {
            "answer": f"RAG answer for {question}",
            "sources": [
                {
                    "source_type": "pdf",
                    "source_id": "pdf-1",
                    "title": "requirements.pdf",
                    "url": None,
                    "chunk_index": 0,
                    "version": 1,
                    "score": 0.9,
                }
            ],
        }


def patch_agent_memory(monkeypatch, harness):
    async def noop_log_file_action(**kwargs):
        return None

    monkeypatch.setattr(agent_service, "get_session_memory", harness.get_session_memory)
    monkeypatch.setattr(agent_service, "save_user_name", harness.save_user_name)
    monkeypatch.setattr(agent_service, "save_chat_exchange", harness.save_chat_exchange)
    monkeypatch.setattr(
        agent_service,
        "answer_question_with_rag",
        harness.answer_question_with_rag,
    )
    monkeypatch.setattr(agent_service, "log_file_action", noop_log_file_action)


def test_memory_update_saves_name_and_skips_rag(monkeypatch):
    harness = MemoryHarness()
    patch_agent_memory(monkeypatch, harness)

    response = run(agent_service.chat_with_agent(
        message="Ja se zovem Marcel",
        session_id="session-1",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert harness.memory_by_session[("session-1", "user")]["user_name"] == "Marcel"
    assert "Bok Marcel" in response["answer"]
    assert response["session_id"] == "session-1"
    assert harness.rag_calls == []
    assert response["trace"][0]["message"] == "Intent detected: memory_update"
    assert response["trace"][-1]["status"] == "skipped"


def test_memory_query_reads_name_from_same_session_and_skips_rag(monkeypatch):
    harness = MemoryHarness()
    harness.memory_by_session[("session-1", "user")] = {"user_name": "Marcel"}
    patch_agent_memory(monkeypatch, harness)

    response = run(agent_service.chat_with_agent(
        message="Kako se ja zovem?",
        session_id="session-1",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert response["answer"] == "Zoveš se Marcel."
    assert harness.rag_calls == []
    assert response["trace"][0]["message"] == "Intent detected: memory_query"


def test_memory_query_without_name_in_new_session_skips_rag(monkeypatch):
    harness = MemoryHarness()
    patch_agent_memory(monkeypatch, harness)

    response = run(agent_service.chat_with_agent(
        message="Kako se ja zovem?",
        session_id="session-2",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert response["answer"] == "Još mi nisi rekao kako se zoveš."
    assert harness.rag_calls == []
    assert response["trace"][1]["message"] == "No user_name in session memory"


def test_rag_query_calls_existing_rag_pipeline(monkeypatch):
    harness = MemoryHarness()
    patch_agent_memory(monkeypatch, harness)

    response = run(agent_service.chat_with_agent(
        message="What are the backend technical requirements?",
        session_id="session-1",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert harness.rag_calls == ["What are the backend technical requirements?"]
    assert response["answer"] == "RAG answer for What are the backend technical requirements?"
    assert response["sources"][0]["source_id"] == "pdf-1"
    assert response["trace"][0]["message"] == "Intent detected: rag_query"


def test_rag_query_marks_trace_empty_when_no_sources(monkeypatch):
    harness = MemoryHarness()
    patch_agent_memory(monkeypatch, harness)

    async def answer_without_sources(question, current_user):
        return {
            "answer": "I could not find any indexed PDF or blog content to answer from.",
            "sources": [],
        }

    monkeypatch.setattr(
        agent_service,
        "answer_question_with_rag",
        answer_without_sources,
    )

    response = run(agent_service.chat_with_agent(
        message="What is missing?",
        session_id="session-1",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert response["sources"] == []
    assert response["trace"][1]["status"] == "empty"


def test_small_talk_skips_rag(monkeypatch):
    harness = MemoryHarness()
    patch_agent_memory(monkeypatch, harness)

    response = run(agent_service.chat_with_agent(
        message="Bok",
        session_id="session-1",
        current_user=CurrentUser(username="user", role="user"),
    ))

    assert response["answer"] == "Bok! Kako ti mogu pomoći?"
    assert harness.rag_calls == []
    assert response["trace"][0]["message"] == "Intent detected: small_talk"
