"""Run the full StudioOps workflow from the command line.

    python -m backend.tools.run_e2e_research
    python -m backend.tools.run_e2e_research --title "Lagos After Dark" --genre "Crime Thriller"

Performs real Parallel searches, and real Gemini calls when credentials are
present. Prints progress as it happens and writes the report to outputs/reports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Dict

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from backend.agent.workflow import ResearchFailure, run_studioops
from backend.integrations.gemini_client import GeminiClient
from backend.models.brief import ProjectBrief
from backend.tools.report_store import save_report

DEMO_BRIEF = {
    "title": "Lagos After Dark",
    "description": (
        "A contemporary Nigerian crime thriller series set in Lagos, following a "
        "detective investigating corruption inside the city's nightlife economy. "
        "Aimed at young adults in Nigeria and the African diaspora, for streaming "
        "distribution with international festival potential."
    ),
    "format": "Series",
    "genre": "Crime Thriller",
    "target_audience": "Young adults, Nigeria and African diaspora",
    "geography": "Nigeria / Africa",
    "research_questions": [
        "What are comparable recent Nigerian or African crime thrillers and how did they perform?",
        "Which streaming platforms are commissioning African scripted content?",
        "Which production companies and Lagos locations are relevant?",
    ],
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run StudioOps end-to-end.")
    parser.add_argument("--title")
    parser.add_argument("--description")
    parser.add_argument("--format")
    parser.add_argument("--genre")
    parser.add_argument("--geography")
    parser.add_argument("--audience")
    parser.add_argument("--quiet", action="store_true", help="Suppress library logs")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )

    # Windows consoles default to cp1252 and would fail on the arrows/marks below.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

    data: Dict[str, Any] = dict(DEMO_BRIEF)
    if args.title:
        data["title"] = args.title
        data["research_questions"] = []
    if args.description:
        data["description"] = args.description
    if args.format:
        data["format"] = args.format
    if args.genre:
        data["genre"] = args.genre
    if args.geography:
        data["geography"] = args.geography
    if args.audience:
        data["target_audience"] = args.audience

    brief = ProjectBrief(**data)

    status = GeminiClient().status
    print(f"\nGemini: {'READY' if status.configured else 'NOT CONFIGURED'} — {status.detail}")
    print(f"Brief: {brief.title} ({brief.genre}, {brief.geography})\n")
    print("-" * 72)

    async def on_progress(event: Dict[str, Any]) -> None:
        marker = {"active": "⟳", "done": "✓", "error": "✗", "info": "·"}.get(
            event.get("status", ""), "·"
        )
        print(f"  {marker} [{event.get('stage'):<10}] {event.get('message')}")

    try:
        response = await run_studioops(brief, on_progress=on_progress)
    except ResearchFailure as exc:
        print(f"\nFAILED at stage '{exc.stage}': {exc}")
        return 1

    payload = response.model_dump()
    names = save_report(payload)

    report = payload["report"]
    meta = payload["research_metadata"]

    print("-" * 72)
    print(f"\nStatus: {payload['status']}")
    print(f"Planner: {meta['planner']}  Synthesizer: {meta['synthesizer']}")
    print(
        f"Queries: {meta['queries_run']} run, {meta['queries_failed']} failed · "
        f"{meta['sources_reviewed']} results → {meta['unique_sources']} unique sources"
    )
    print(f"Duration: {meta['total_duration_ms']} ms")
    print(f"\nEXECUTIVE SUMMARY\n{report['executive_summary']}\n")

    counts = {
        "comparables": len(report["comparable_titles"]),
        "market signals": len(report["market_signals"]),
        "audience insights": len(report["audience_insights"]),
        "competitive": len(report["competitive_landscape"]),
        "opportunities": len(report["production_opportunities"]),
        "risks": len(report["risks"]),
        "next steps": len(report["next_steps"]),
        "sources": len(report["sources"]),
    }
    print("SECTIONS: " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    if report["evidence_gaps"]:
        print("\nEVIDENCE GAPS")
        for gap in report["evidence_gaps"]:
            print(f"  - {gap}")

    if meta["warnings"]:
        print("\nWARNINGS")
        for warning in meta["warnings"]:
            print(f"  - {warning}")

    print(f"\nSaved: outputs/reports/{names['md']}")
    print(f"       outputs/reports/{names['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
