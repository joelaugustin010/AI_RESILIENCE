"""Tests for the LLM-backed assistant, RAG, streaming and honest failures.

The provider tests use a local fake HTTP server that speaks the same SSE
protocol as OpenAI-compatible and Anthropic APIs.  They verify the real client
code path without requiring a paid credential.  Live model quality must be
checked separately with ``scripts/test_disaster_assistant_live.py``.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from src.assistant import config as assistant_config
from src.assistant import llm as assistant_llm
from src.assistant.chat import (
    assistant_status,
    build_messages,
    chat_once,
    prepare_reply,
)
from src.assistant.config import LLMConfigurationError, load_config
from src.assistant.knowledge import load_knowledge
from src.assistant.llm import LLMRequestError
from src.assistant.rag import collect_sources, format_context, retrieve

ENV_KEYS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "LLM_TIMEOUT",
    "LLM_TOP_P",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "TOGETHER_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)


@pytest.fixture(autouse=True)
def clean_llm_environment(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(assistant_config, "_secret_section", lambda: {})
    yield


@pytest.fixture
def fake_llm():
    """Start a local fake provider that streams OpenAI/Anthropic SSE events."""

    class Handler(BaseHTTPRequestHandler):
        requests_log: list[dict] = []
        status = 200
        status_sequence: list[int] = []
        retry_after = ""
        error_body = {"error": {"message": "Invalid API key"}}
        openai_chunks = ["Kochi ", "flooding ", "is driven by ", "heavy rainfall."]
        anthropic_chunks = ["Kochi ", "flooding ", "is driven by ", "heavy rainfall."]

        def log_message(self, *args):  # silence test output
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {}
            type(self).requests_log.append(
                {
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": body,
                }
            )
            response_status = (
                type(self).status_sequence.pop(0)
                if type(self).status_sequence
                else type(self).status
            )
            if response_status >= 400:
                payload = json.dumps(type(self).error_body).encode("utf-8")
                self.send_response(response_status)
                self.send_header("Content-Type", "application/json")
                if type(self).retry_after:
                    self.send_header("Retry-After", type(self).retry_after)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                self.close_connection = True
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if self.path.endswith("/messages"):
                for text in type(self).anthropic_chunks:
                    event = {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": text},
                    }
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(
                    f"data: {json.dumps({'type': 'message_stop'})}\n\n".encode("utf-8")
                )
            else:
                for text in type(self).openai_chunks:
                    event = {"choices": [{"delta": {"content": text}}]}
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(
            base_url=f"http://127.0.0.1:{server.server_port}",
            openai_base_url=f"http://127.0.0.1:{server.server_port}/v1",
            handler=Handler,
            requests=Handler.requests_log,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _configure_openai(monkeypatch, fake_llm, model="fake-model"):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", fake_llm.openai_base_url)
    monkeypatch.setenv("LLM_MODEL", model)


def _configure_groq(monkeypatch, fake_llm, model="openai/gpt-oss-20b"):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_BASE_URL", fake_llm.openai_base_url)
    monkeypatch.setenv("LLM_MODEL", model)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_clear_configuration_error():
    cfg = load_config()
    assert cfg.configured is False
    with pytest.raises(LLMConfigurationError, match="LLM_API_KEY"):
        chat_once("What causes flooding in Kochi?")


def test_status_explains_missing_configuration_without_exposing_secrets(monkeypatch):
    status = assistant_status()
    assert status["configured"] is False
    assert "LLM_API_KEY" in status["help"]

    monkeypatch.setenv("LLM_API_KEY", "super-secret-test-key")
    configured = assistant_status()
    assert configured["configured"] is True
    assert "super-secret-test-key" not in json.dumps(configured)


def test_provider_and_model_are_configurable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    cfg = load_config()
    assert cfg.provider == "groq"
    assert cfg.model == "custom-model"
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert cfg.configured is True


def test_groq_is_the_default_provider_and_uses_supported_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    cfg = load_config()
    assert cfg.provider == "groq"
    assert cfg.model == "openai/gpt-oss-20b"
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert cfg.configured is True


def test_streamlit_llm_section_uses_documented_compact_secret_names(monkeypatch):
    monkeypatch.setattr(
        assistant_config,
        "_secret_section",
        lambda: {"provider": "groq", "model": "secret-model", "api_key": "gsk-test"},
    )
    cfg = load_config()
    assert cfg.provider == "groq"
    assert cfg.model == "secret-model"
    assert cfg.api_key == "gsk-test"
    assert cfg.configured is True


# ---------------------------------------------------------------------------
# Real HTTP client paths (fake local provider)
# ---------------------------------------------------------------------------


def test_openai_compatible_streaming_generates_dynamic_text(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    result = chat_once("What causes flooding in Kochi?")
    assert result["answer"] == "Kochi flooding is driven by heavy rainfall."
    assert result["provider"] == "openai"
    assert result["model"] == "fake-model"

    request = fake_llm.requests[-1]
    assert request["path"] == "/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["body"]["model"] == "fake-model"
    assert request["body"]["stream"] is True
    roles = [message["role"] for message in request["body"]["messages"]]
    assert roles[0] == "system"
    assert roles[-1] == "user"
    assert request["body"]["messages"][-1]["content"] == "What causes flooding in Kochi?"


def test_streaming_preserves_utf8_punctuation(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    fake_llm.handler.openai_chunks = ["it’s ", "June–September ", "and “text”"]

    result = chat_once("Return a Unicode sentence.")

    assert result["answer"] == "it’s June–September and “text”"


def test_groq_streaming_preserves_rag_and_source_attribution(monkeypatch, fake_llm):
    _configure_groq(monkeypatch, fake_llm)
    result = chat_once("What does the Ernakulam flood probability estimate mean?")
    assert result["answer"]
    assert result["provider"] == "groq"
    assert result["model"] == "openai/gpt-oss-20b"
    assert result["evidence"]
    assert result["sources"]
    request = fake_llm.requests[-1]
    assert request["path"] == "/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer gsk-test"
    assert any("Retrieved project evidence" in message["content"] for message in request["body"]["messages"])


def test_anthropic_native_streaming_format(monkeypatch, fake_llm):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setenv("LLM_BASE_URL", fake_llm.base_url)
    monkeypatch.setenv("LLM_MODEL", "claude-test")
    result = chat_once("Explain hospital preparedness.")
    assert result["answer"] == "Kochi flooding is driven by heavy rainfall."

    request = fake_llm.requests[-1]
    assert request["path"] == "/v1/messages"
    assert request["headers"]["x-api-key"] == "anthropic-test-key"
    assert request["headers"]["anthropic-version"]
    assert request["body"]["system"]
    assert request["body"]["messages"][-1]["role"] == "user"
    assert all(message["role"] != "system" for message in request["body"]["messages"])


def test_conversation_history_is_sent_for_follow_up(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    history = [
        {"role": "user", "content": "How can hospitals prepare for landslides?"},
        {"role": "assistant", "content": "They should review access routes and backup power."},
    ]
    result = chat_once("What about during the monsoon?", history=history)
    assert result["answer"]
    request = fake_llm.requests[-1]
    contents = [message["content"] for message in request["body"]["messages"]]
    assert "How can hospitals prepare for landslides?" in contents
    assert "What about during the monsoon?" in contents


def test_provider_error_is_surfaced_without_canned_answer(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    fake_llm.handler.status = 401
    fake_llm.handler.error_body = {"error": {"message": "Invalid API key"}}
    with pytest.raises(LLMRequestError) as excinfo:
        chat_once("What causes flooding in Kochi?")
    assert excinfo.value.status_code == 401
    assert "401" in str(excinfo.value)
    assert "Invalid API key" in str(excinfo.value)


def test_transient_503_and_500_are_retried_then_stream_success(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    fake_llm.handler.status_sequence = [503, 500, 200]
    fake_llm.handler.error_body = {
        "error": {"code": 503, "message": "Google service temporarily unavailable", "status": "UNAVAILABLE"}
    }
    delays: list[float] = []
    monkeypatch.setattr(assistant_llm, "_sleep", delays.append)

    result = chat_once("What causes flooding in Kochi?")

    assert result["answer"] == "Kochi flooding is driven by heavy rainfall."
    assert len(fake_llm.requests) == 3
    assert len(delays) == 2
    assert all(delay >= 0 for delay in delays)


def test_retry_after_is_honored_for_transient_failure(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    fake_llm.handler.status_sequence = [503, 200]
    fake_llm.handler.retry_after = "0.01"
    delays: list[float] = []
    monkeypatch.setattr(assistant_llm, "_sleep", delays.append)

    result = chat_once("Explain hospital preparedness.")

    assert result["answer"]
    assert delays == [0.01]


def test_request_timeout_is_retried_then_succeeds(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    original_post = assistant_llm.requests.post
    calls = 0
    delays: list[float] = []

    def flaky_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise assistant_llm.requests.exceptions.Timeout("temporary timeout")
        return original_post(*args, **kwargs)

    monkeypatch.setattr(assistant_llm.requests, "post", flaky_post)
    monkeypatch.setattr(assistant_llm, "_sleep", delays.append)

    result = chat_once("Explain hospital preparedness.")

    assert result["answer"]
    assert calls == 2
    assert len(delays) == 1


def test_transient_failure_after_retry_budget_has_clear_message(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    fake_llm.handler.status = 503
    fake_llm.handler.error_body = {
        "error": {"code": 503, "message": "Google service temporarily unavailable", "status": "UNAVAILABLE"}
    }
    monkeypatch.setattr(assistant_llm, "_sleep", lambda _: None)

    with pytest.raises(LLMRequestError, match="temporarily unavailable after 3 retries") as excinfo:
        chat_once("What causes flooding in Kochi?")
    assert excinfo.value.status_code == 503
    assert "Google service temporarily unavailable" in str(excinfo.value)


def test_streaming_preserves_chunk_boundaries(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    plan = prepare_reply("What causes flooding in Kochi?")
    chunks = list(plan.stream())
    assert chunks == ["Kochi ", "flooding ", "is driven by ", "heavy rainfall."]
    assert "".join(chunks) == "Kochi flooding is driven by heavy rainfall."


# ---------------------------------------------------------------------------
# RAG grounding
# ---------------------------------------------------------------------------


def test_rag_retrieves_reviewed_project_evidence_and_sources():
    evidence = retrieve("What does the Ernakulam district flood probability estimate mean?")
    assert evidence
    assert any("probab" in (item.title + item.text).casefold() for item in evidence)
    sources = collect_sources(evidence)
    assert sources
    assert all(source["url"].startswith("https://") for source in sources)
    context = format_context(evidence)
    assert "Evidence status" in context
    assert "[1]" in context


def test_rag_finds_air_quality_module_evidence():
    evidence = retrieve("How old is the KSPCB air quality data in this project?")
    assert evidence
    assert any("air" in (item.title + item.text).casefold() for item in evidence)


def test_build_messages_contains_system_rag_and_history():
    evidence = retrieve("What are the warning signs of a landslide?")
    messages = build_messages(
        "How should hospitals prepare?",
        [{"role": "user", "content": "Tell me about landslides."}],
        evidence,
    )
    assert messages[0]["role"] == "system"
    assert "Disaster Intelligence Assistant" in messages[0]["content"]
    assert any("Retrieved project evidence" in message["content"] for message in messages)
    assert messages[-1] == {"role": "user", "content": "How should hospitals prepare?"}
    assert any(message["content"] == "Tell me about landslides." for message in messages)


ACCEPTANCE_QUESTIONS = [
    "What causes flooding in Kochi?",
    "Explain how industrial pollution affects human health.",
    "What is the difference between a flood and urban waterlogging?",
    "How can hospitals prepare for landslides?",
    "Explain disaster mitigation to a 10-year-old.",
    "What can our AI_RESILIENCE application do?",
    "Which of those points matters most for a hospital during a flood?",
    "Who won the 2018 FIFA World Cup?",
]


def test_all_acceptance_questions_reach_the_llm(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    history: list[dict] = []
    for question in ACCEPTANCE_QUESTIONS:
        result = chat_once(question, history)
        assert result["answer"]
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["answer"]},
            ]
        )
    assert len(fake_llm.requests) == len(ACCEPTANCE_QUESTIONS)
    # The seventh question is a follow-up; the request must carry earlier turns.
    follow_up_contents = [
        message["content"] for message in fake_llm.requests[6]["body"]["messages"]
    ]
    assert ACCEPTANCE_QUESTIONS[3] in follow_up_contents
    assert ACCEPTANCE_QUESTIONS[6] in follow_up_contents


def test_empty_question_is_rejected(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    with pytest.raises(ValueError, match="Enter a question"):
        prepare_reply("   ")


def test_page_streams_generated_answer_and_grounding(monkeypatch, fake_llm):
    _configure_openai(monkeypatch, fake_llm)
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    page = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "app_pages"
        / "disaster_assistant.py"
    )
    app = streamlit_testing.AppTest.from_file(str(page), default_timeout=30).run()
    app.chat_input[0].set_value("What causes flooding in Kochi?").run()
    assert not app.exception
    messages = app.session_state["assistant_messages"]
    assert messages[0]["content"] == "What causes flooding in Kochi?"
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "Kochi flooding is driven by heavy rainfall."
    assert messages[-1]["sources"]
    assert fake_llm.requests[-1]["body"]["messages"][-1]["content"] == "What causes flooding in Kochi?"


def test_page_disables_chat_when_not_configured():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    page = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "app_pages"
        / "disaster_assistant.py"
    )
    app = streamlit_testing.AppTest.from_file(str(page), default_timeout=30).run()
    assert not app.exception
    warnings = "\n".join(str(item.value) for item in app.warning)
    assert "no api key" in warnings.casefold() or "not configured" in warnings.casefold()
    assert "disabled" in " ".join(str(item.value) for item in app.markdown).casefold()


# ---------------------------------------------------------------------------
# Knowledge provenance
# ---------------------------------------------------------------------------


def test_reviewed_sources_are_https_and_ids_unique():
    topics = load_knowledge()
    ids = [topic["id"] for topic in topics]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 9
    for topic in topics:
        assert topic["sources"]
        assert all(source["url"].startswith("https://") for source in topic["sources"])
