"""HTTP clients for OpenAI-compatible and Anthropic chat APIs.

Only the Python standard library plus ``requests`` is used, so the assistant
stays lightweight enough for Streamlit Cloud.  Responses are streamed token by
token; there is no fallback to a canned answer when the request fails.
"""

from __future__ import annotations

import json
import random
from time import sleep as _sleep
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator

import requests

from src.assistant.config import LLMConfig, LLMConfigurationError

ANTHROPIC_VERSION = "2023-06-01"
_MAX_ERROR_BODY = 600
MAX_TRANSIENT_RETRIES = 3
RETRYABLE_STATUS_CODES = frozenset({500, 503})
RETRY_BASE_SECONDS = 0.5
RETRY_MAX_SECONDS = 8.0


class LLMRequestError(RuntimeError):
    """Raised when the provider request fails or returns an invalid response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _content_text(content: Any) -> str:
    """Normalize text content from string or content-part lists."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _validate_messages(messages: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "")).strip()
        content = _content_text(message.get("content", "")).strip()
        if role not in {"system", "user", "assistant"} or not content:
            continue
        cleaned.append({"role": role, "content": content})
    if not any(message["role"] == "user" for message in cleaned):
        raise LLMRequestError("The conversation does not contain a user message.")
    return cleaned


def _anthropic_payload(messages: Iterable[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    cleaned = _validate_messages(messages)
    system_parts = [message["content"] for message in cleaned if message["role"] == "system"]
    conversation: list[dict[str, str]] = []
    for message in cleaned:
        if message["role"] == "system":
            continue
        if conversation and conversation[-1]["role"] == message["role"]:
            conversation[-1]["content"] += "\n\n" + message["content"]
        else:
            conversation.append({"role": message["role"], "content": message["content"]})
    while conversation and conversation[0]["role"] != "user":
        conversation.pop(0)
    if not conversation:
        raise LLMRequestError("The conversation does not contain a user message.")
    return "\n\n".join(system_parts), conversation


def _headers(config: LLMConfig) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "User-Agent": "AI-RESILIENCE-assistant/2.0",
    }
    if config.kind == "anthropic":
        headers["x-api-key"] = config.api_key
        headers["anthropic-version"] = ANTHROPIC_VERSION
    else:
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers["X-Title"] = "AI RESILIENCE"
    return headers


def _endpoint(config: LLMConfig) -> str:
    if config.kind == "anthropic":
        return f"{config.base_url}/v1/messages"
    return f"{config.base_url}/chat/completions"


def _payload(config: LLMConfig, messages: Iterable[dict[str, Any]]) -> dict[str, Any]:
    if config.kind == "anthropic":
        system, conversation = _anthropic_payload(messages)
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": conversation,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }
        if system:
            payload["system"] = system
        return payload
    return {
        "model": config.model,
        "messages": _validate_messages(messages),
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "top_p": config.top_p,
        "stream": True,
    }


def _error_message(response: requests.Response, *, secret: str = "") -> str:
    body = ""
    try:
        body = response.text[:_MAX_ERROR_BODY]
    except Exception:
        pass
    detail = ""
    try:
        parsed = json.loads(body)
        error = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(error, dict):
            detail = str(error.get("message") or error.get("type") or "")
            if not detail and isinstance(error.get("details"), list):
                detail = "; ".join(
                    str(item.get("reason") or item.get("description") or "")
                    for item in error["details"]
                    if isinstance(item, dict)
                ).strip("; ")
        elif isinstance(parsed, dict):
            detail = str(parsed.get("message") or "")
    except (json.JSONDecodeError, TypeError):
        detail = body.strip()
    if secret:
        detail = detail.replace(secret, "[REDACTED]")
        body = body.replace(secret, "[REDACTED]")
    if not detail:
        detail = body.strip()
    if not detail:
        detail = "The provider returned an error without a message."
    return detail


def _retry_delay(response: requests.Response | None, retry_number: int) -> float:
    """Return Retry-After when valid, otherwise exponential backoff plus jitter."""
    retry_after = response.headers.get("Retry-After", "").strip() if response is not None else ""
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), RETRY_MAX_SECONDS))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, min((retry_at - datetime.now(timezone.utc)).total_seconds(), RETRY_MAX_SECONDS))
            except (TypeError, ValueError, OverflowError):
                pass
    exponential = min(RETRY_BASE_SECONDS * (2 ** max(retry_number - 1, 0)), RETRY_MAX_SECONDS)
    return exponential + random.uniform(0.0, min(0.25, exponential / 2))


def _openai_delta(event: dict[str, Any]) -> str:
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0] if isinstance(choices[0], dict) else {}
    delta = choice.get("delta")
    if isinstance(delta, dict):
        text = _content_text(delta.get("content"))
        if text:
            return text
    message = choice.get("message")
    if isinstance(message, dict):
        return _content_text(message.get("content"))
    return ""


def _anthropic_delta(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    if event_type == "content_block_delta":
        delta = event.get("delta")
        if isinstance(delta, dict) and delta.get("type") in {None, "text_delta"}:
            text = delta.get("text")
            if isinstance(text, str):
                return text
    if event_type == "content_block_start":
        block = event.get("content_block")
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            return block["text"]
    return ""


def _iter_sse_events(response: requests.Response) -> Iterator[dict[str, Any]]:
    for raw_line in response.iter_lines(decode_unicode=False):
        if not raw_line:
            continue
        line = raw_line.decode("utf-8").strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            if data == "[DONE]":
                return
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def stream_chat(messages: Iterable[dict[str, Any]], config: LLMConfig) -> Iterator[str]:
    """Stream generated text from the configured provider.

    Raises ``LLMConfigurationError`` before any network call when the config is
    unusable, and ``LLMRequestError`` for HTTP, timeout or protocol failures.
    """
    if not config.configured:
        raise LLMConfigurationError(
            "The language model is not configured. Add an API key before chatting."
        )

    payload = _payload(config, messages)
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        try:
            response = requests.post(
                _endpoint(config),
                headers=_headers(config),
                json=payload,
                stream=True,
                timeout=(10, config.timeout),
            )
        except requests.exceptions.Timeout as exc:
            if attempt < MAX_TRANSIENT_RETRIES:
                _sleep(_retry_delay(None, attempt + 1))
                continue
            raise LLMRequestError(
                f"{config.provider} was temporarily unavailable after {MAX_TRANSIENT_RETRIES} retries "
                "because the request timed out. Please wait and try again, or increase LLM_TIMEOUT."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LLMRequestError(f"Could not reach the language-model provider: {exc}") from exc

        with response:
            if response.status_code >= 400:
                detail = _error_message(response, secret=config.api_key)
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_TRANSIENT_RETRIES:
                    _sleep(_retry_delay(response, attempt + 1))
                    continue
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise LLMRequestError(
                        f"{config.provider} is temporarily unavailable after {MAX_TRANSIENT_RETRIES} retries "
                        f"(HTTP {response.status_code}). Please wait and try again. {detail}",
                        status_code=response.status_code,
                    )
                raise LLMRequestError(
                    f"{config.provider} returned HTTP {response.status_code}: {detail}",
                    status_code=response.status_code,
                )

            produced = False
            try:
                for event in _iter_sse_events(response):
                    if config.kind == "anthropic":
                        if event.get("type") == "error":
                            error = event.get("error")
                            detail = error.get("message") if isinstance(error, dict) else str(error)
                            raise LLMRequestError(f"Anthropic stream error: {detail}")
                        text = _anthropic_delta(event)
                    else:
                        text = _openai_delta(event)
                    if text:
                        produced = True
                        yield text
            except requests.exceptions.RequestException as exc:
                raise LLMRequestError(f"The response stream was interrupted: {exc}") from exc

            if not produced:
                raise LLMRequestError(
                    "The provider returned no text. Check the model name, quota and provider status."
                )
            return


def chat(messages: Iterable[dict[str, Any]], config: LLMConfig) -> str:
    """Collect a streamed response into one string."""
    return "".join(stream_chat(messages, config))


__all__ = ["LLMRequestError", "chat", "stream_chat"]
