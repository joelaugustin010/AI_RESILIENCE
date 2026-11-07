"""Configuration for the LLM-backed disaster assistant.

Secrets are read from environment variables first and then from Streamlit
secrets (``st.secrets``), so the same code works locally and on Streamlit
Cloud.  API keys are never written to disk or displayed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_PROVIDER = "groq"

# Providers that expose an OpenAI-compatible /chat/completions endpoint are
# handled by one client.  Anthropic uses its native /v1/messages API.
PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": ("OPENAI_API_KEY",),
        "requires_key": True,
        "kind": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-3-5-haiku-latest",
        "key_env": ("ANTHROPIC_API_KEY",),
        "requires_key": True,
        "kind": "anthropic",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b",
        "key_env": ("GROQ_API_KEY",),
        "requires_key": True,
        "kind": "openai",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "key_env": ("OPENROUTER_API_KEY",),
        "requires_key": True,
        "kind": "openai",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "key_env": ("TOGETHER_API_KEY",),
        "requires_key": True,
        "kind": "openai",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-3.8-flash",
        "key_env": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "requires_key": True,
        "kind": "openai",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "key_env": (),
        "requires_key": False,
        "kind": "openai",
    },
}

# ``openai_compatible`` is a documented escape hatch for self-hosted gateways,
# vLLM, LM Studio, or any other OpenAI-compatible endpoint.
CUSTOM_PROVIDER = "openai_compatible"


class LLMConfigurationError(RuntimeError):
    """Raised when the assistant cannot be used because configuration is missing."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    max_tokens: int
    timeout: float
    top_p: float
    kind: str
    requires_key: bool

    @property
    def configured(self) -> bool:
        if not self.model or not self.base_url:
            return False
        return bool(self.api_key) or not self.requires_key

    def public_status(self) -> dict[str, Any]:
        """Return display-safe metadata.  The API key is never included."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "configured": self.configured,
            "requires_key": self.requires_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


def _secret_section() -> Mapping[str, Any]:
    try:
        import streamlit as st

        secrets = st.secrets
        section = secrets.get("llm", {})
        if isinstance(section, Mapping):
            return section
    except Exception:
        pass
    return {}


def _lookup(*names: str) -> str:
    """Read the first non-empty value from environment or Streamlit secrets."""
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    section = _secret_section()
    for name in names:
        # Streamlit Cloud documentation conventionally uses a compact [llm]
        # section, e.g. ``[llm] api_key = ...`` rather than environment-style
        # names.  Accept both forms while retaining environment precedence.
        compact = name[4:] if name.startswith("LLM_") else name
        for key in (name, name.lower(), compact, compact.lower()):
            if key in section:
                value = section[key]
                if value is not None and str(value).strip():
                    return str(value).strip()
    try:
        import streamlit as st

        for name in names:
            compact = name[4:] if name.startswith("LLM_") else name
            for key in (name, name.lower(), compact, compact.lower()):
                if key in st.secrets:
                    value = st.secrets[key]
                    if value is not None and str(value).strip():
                        return str(value).strip()
    except Exception:
        pass
    return ""


def _as_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = _lookup(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise LLMConfigurationError(f"{name} must be a number, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise LLMConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _as_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = _lookup(name)
    if not raw:
        return default
    try:
        value = int(float(raw))
    except ValueError as exc:
        raise LLMConfigurationError(f"{name} must be an integer, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise LLMConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


def load_config() -> LLMConfig:
    """Resolve configuration from environment variables and Streamlit secrets.

    Environment names use ``LLM_*`` plus the provider's conventional key name
    (for example ``OPENAI_API_KEY`` or ``ANTHROPIC_API_KEY``).
    """
    provider = (_lookup("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().casefold()
    if provider == CUSTOM_PROVIDER:
        defaults: dict[str, Any] = {
            "base_url": "",
            "model": "",
            "key_env": (),
            "requires_key": False,
            "kind": "openai",
        }
    elif provider in PROVIDER_DEFAULTS:
        defaults = PROVIDER_DEFAULTS[provider]
    else:
        supported = ", ".join(sorted([*PROVIDER_DEFAULTS, CUSTOM_PROVIDER]))
        raise LLMConfigurationError(
            f"Unsupported LLM_PROVIDER {provider!r}. Choose one of: {supported}."
        )

    base_url = _lookup("LLM_BASE_URL") or str(defaults["base_url"])
    model = _lookup("LLM_MODEL") or str(defaults["model"])
    api_key = _lookup("LLM_API_KEY", *tuple(defaults["key_env"]))

    if provider == CUSTOM_PROVIDER:
        if not base_url:
            raise LLMConfigurationError(
                "LLM_BASE_URL is required when LLM_PROVIDER=openai_compatible."
            )
        if not model:
            raise LLMConfigurationError(
                "LLM_MODEL is required when LLM_PROVIDER=openai_compatible."
            )

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        temperature=_as_float("LLM_TEMPERATURE", 0.3, 0.0, 2.0),
        max_tokens=_as_int("LLM_MAX_TOKENS", 1200, 64, 8192),
        timeout=_as_float("LLM_TIMEOUT", 90.0, 5.0, 300.0),
        top_p=_as_float("LLM_TOP_P", 1.0, 0.01, 1.0),
        kind=str(defaults["kind"]),
        requires_key=bool(defaults["requires_key"]),
    )


def require_config() -> LLMConfig:
    """Return a usable config or raise a helpful configuration error."""
    config = load_config()
    if not config.configured:
        raise LLMConfigurationError(
            "No LLM API key is configured. Set LLM_API_KEY (or the provider-specific "
            "key such as OPENAI_API_KEY / ANTHROPIC_API_KEY) and retry."
        )
    return config


def configuration_help() -> str:
    """Return Markdown instructions for configuring the assistant."""
    return """### Configure the language model

The assistant needs an API key before it can generate answers. It never ships
with a key and never pretends a request succeeded.

**Local shell (environment variables)**

```bash
export LLM_PROVIDER=groq
export LLM_MODEL=openai/gpt-oss-20b
export LLM_API_KEY=your-api-key
# optional: export LLM_BASE_URL=https://api.groq.com/openai/v1
```

**Streamlit Cloud (app Secrets)**

```toml
[llm]
provider = "groq"
model = "openai/gpt-oss-20b"
api_key = "your-api-key"
```

Restart the app after changing secrets.

**Other providers**

- `anthropic` — `ANTHROPIC_API_KEY`, default `claude-3-5-haiku-latest`
- `groq` — `GROQ_API_KEY`, default `openai/gpt-oss-20b`
- `openrouter` — `OPENROUTER_API_KEY`
- `together` — `TOGETHER_API_KEY`
- `gemini` — `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `ollama` — local OpenAI-compatible server, no key required
- `openai_compatible` — set `LLM_BASE_URL` and `LLM_MODEL` for any gateway

Provider and model are configurable; `LLM_API_KEY` overrides the
provider-specific key variable. Optional tuning: `LLM_TEMPERATURE`,
`LLM_MAX_TOKENS`, `LLM_TIMEOUT`, `LLM_TOP_P`.
"""


__all__ = [
    "CUSTOM_PROVIDER",
    "DEFAULT_PROVIDER",
    "LLMConfig",
    "LLMConfigurationError",
    "PROVIDER_DEFAULTS",
    "configuration_help",
    "load_config",
    "require_config",
]
