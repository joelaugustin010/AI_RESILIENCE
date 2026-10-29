"""Keep snapshot-backed integration tests explicit and safe for clean CI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parent
RUN_LOCAL_RESEARCH_TESTS = "AI_RESILIENCE_RUN_LOCAL_RESEARCH_TESTS"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip research snapshot checks unless requested and all inputs exist."""
    enabled = os.environ.get(RUN_LOCAL_RESEARCH_TESTS, "").strip().casefold() in {
        "1", "true", "yes", "on"
    }
    for item in items:
        marker = item.get_closest_marker("local_research")
        if marker is None:
            continue

        required_paths = [REPOSITORY_ROOT / Path(str(path)) for path in marker.args]
        escaped = [
            path for path in required_paths
            if not path.resolve().is_relative_to(REPOSITORY_ROOT)
        ]
        if escaped:
            item.add_marker(pytest.mark.skip(reason="invalid local_research fixture path"))
            continue

        missing = [path for path in required_paths if not path.is_file()]
        if missing:
            reason = "local research integration unavailable; missing: " + ", ".join(
                path.relative_to(REPOSITORY_ROOT).as_posix() for path in missing
            )
        elif not enabled:
            reason = (
                "requires optional locally acquired research snapshots; set "
                f"{RUN_LOCAL_RESEARCH_TESTS}=1 to run when licensed snapshots are available"
            )
        else:
            continue
        item.add_marker(pytest.mark.skip(reason=reason))
