"""Session-scoped shared project store for the two mitigation workspaces.

Projects are shared across Streamlit pages in one active user session. This is
not a database and does not promise persistence across browser sessions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, MutableMapping
from uuid import uuid4

STORE_KEY = "mitigation_studio_projects"
SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_projects(session_state: MutableMapping[str, Any]) -> list[dict[str, Any]]:
    """Return independent copies of saved studio projects, newest first."""
    store = session_state.get(STORE_KEY, {})
    if not isinstance(store, dict):
        return []
    projects = [deepcopy(value) for value in store.values() if isinstance(value, dict)]
    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)


def get_project(session_state: MutableMapping[str, Any], project_id: str) -> dict[str, Any] | None:
    """Return a project copy by stable ID."""
    store = session_state.get(STORE_KEY, {})
    project = store.get(str(project_id)) if isinstance(store, dict) else None
    return deepcopy(project) if isinstance(project, dict) else None


def save_project(
    session_state: MutableMapping[str, Any],
    payload: dict[str, Any],
    *,
    project_id: str | None = None,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Create or revision-check and update a project without mutating caller data."""
    store = session_state.setdefault(STORE_KEY, {})
    if not isinstance(store, dict):
        raise ValueError("The mitigation project store is invalid; reload the app before saving.")

    existing = store.get(str(project_id)) if project_id else None
    if project_id and existing is None:
        raise ValueError("This project is no longer in the session store. Save it as a new project.")
    if existing is not None and expected_revision is not None:
        actual_revision = int(existing.get("revision", 1))
        if actual_revision != int(expected_revision):
            raise ValueError(
                "This project changed after it was opened. Reopen the latest version before saving."
            )

    now = _now()
    saved = deepcopy(payload)
    saved.update({
        "schema_version": SCHEMA_VERSION,
        "project_id": str(project_id or uuid4()),
        "revision": int(existing.get("revision", 0)) + 1 if existing else 1,
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
    })
    store[saved["project_id"]] = deepcopy(saved)
    return deepcopy(saved)
