"""Run the real LLM-backed assistant against the eight acceptance questions.

This script makes live API calls and therefore requires credentials:

    export LLM_PROVIDER=groq
    export LLM_MODEL=openai/gpt-oss-20b
    export LLM_API_KEY=...
    python3 scripts/test_disaster_assistant_live.py

It exits with status 2 when no credential is configured, so it never pretends
the integration was tested.  Add ``--json`` for machine-readable output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assistant.chat import chat_once  # noqa: E402
from src.assistant.config import load_config  # noqa: E402
from src.assistant.llm import LLMRequestError  # noqa: E402

QUESTIONS = [
    "What causes flooding in Kochi?",
    "Explain how industrial pollution affects human health.",
    "What is the difference between a flood and urban waterlogging?",
    "How can hospitals prepare for landslides?",
    "Explain disaster mitigation to a 10-year-old.",
    "What can our AI_RESILIENCE application do?",
    "Which of those points matters most for a hospital during a flood?",
    "Who won the 2018 FIFA World Cup?",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON results")
    args = parser.parse_args()

    config = load_config()
    if not config.configured:
        print(
            "SKIPPED: no LLM credential is configured. Set LLM_API_KEY "
            "(and optionally LLM_PROVIDER / LLM_MODEL) before running a live test.",
            file=sys.stderr,
        )
        return 2

    history: list[dict] = []
    results = []
    for index, question in enumerate(QUESTIONS, start=1):
        try:
            result = chat_once(question, history)
        except LLMRequestError as exc:
            print(f"[{index}] FAILED: {exc}", file=sys.stderr)
            return 1
        answer = result["answer"].strip()
        if not answer:
            print(f"[{index}] FAILED: empty answer", file=sys.stderr)
            return 1
        results.append(
            {
                "question": question,
                "answer": answer,
                "sources": result["sources"],
                "evidence": [item["id"] for item in result["evidence"]],
                "provider": result["provider"],
                "model": result["model"],
            }
        )
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
        )
        if not args.json:
            print("=" * 78)
            print(f"[{index}] {question}")
            print("-" * 78)
            print(answer)
            if result["evidence"]:
                print(f"\nGrounding records: {', '.join(item['id'] for item in result['evidence'])}")
            print()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 78)
        print(
            f"LIVE CHECK COMPLETE: {len(results)} generated answers from "
            f"{config.provider} / {config.model}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
