"""Smoke-check the deployed Streamlit app health and HTML shell.

A passing check proves only that the configured endpoint responds. It does not
prove model-data freshness, correct predictions, or scientific validity.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def _get(url: str, timeout: float) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "AI-RESILIENCE-deployment-smoke/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read(2_000_000).decode("utf-8", errors="replace")


def verify_deployment(
    base_url: str,
    *,
    attempts: int = 1,
    delay_seconds: float = 0.0,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Deployment URL must be an absolute HTTPS URL.")
    if attempts < 1 or timeout_seconds <= 0 or delay_seconds < 0:
        raise ValueError("attempts and timeout must be positive; delay cannot be negative.")

    health_url = f"{base_url}/_stcore/health"
    root_url = f"{base_url}/"
    last_error = "not attempted"
    health_status: int | None = None
    root_status: int | None = None
    for attempt in range(1, attempts + 1):
        try:
            health_status, health_body = _get(health_url, timeout_seconds)
            root_status, root_body = _get(root_url, timeout_seconds)
            health_ok = health_status == 200 and "ok" in health_body.casefold()
            root_ok = root_status == 200 and "streamlit" in root_body.casefold()
            if health_ok and root_ok:
                return {
                    "passed": True,
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                    "host": parsed.netloc,
                    "attempts_used": attempt,
                    "health_status": health_status,
                    "root_status": root_status,
                    "health_check": "passed",
                    "application_shell": "passed",
                    "scope": "HTTP deployment smoke check only; no model inference or scientific validation.",
                }
            last_error = (
                f"health endpoint status/body check failed ({health_status}); "
                f"application root status/shell check failed ({root_status})"
            )
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < attempts and delay_seconds:
            time.sleep(delay_seconds)

    return {
        "passed": False,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": parsed.netloc,
        "attempts_used": attempts,
        "health_status": health_status,
        "root_status": root_status,
        "health_check": "failed",
        "application_shell": "failed",
        "last_error": last_error,
        "scope": "HTTP deployment smoke check only; no model inference or scientific validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AI_RESILIENCE_APP_URL", "https://ai-resilience-team.streamlit.app"))
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--output", type=Path, default=Path("reports/live_deployment_smoke.json"))
    args = parser.parse_args()

    result = verify_deployment(
        args.url,
        attempts=args.attempts,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
