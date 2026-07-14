#!/usr/bin/env python3
"""Nightly knowledge upgrade for the virtual crew (Orchestrator).

Intended for Windows Task Scheduler / cron at 23:00:

  python scripts/daily_knowledge_update.py --force

Uses Wikipedia public summaries (no API key). Writes:
  knowledge/ai/<role>/web_digest/YYYY-MM-DD.json
  knowledge/ai/<role>/web_digest/latest.json
  knowledge/.daily_update_state.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from film_pipeline.runtime.knowledge_updater import run_daily_knowledge_update  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Orchestrator daily knowledge update")
    p.add_argument("--force", action="store_true", help="Ignore same-day skip")
    args = p.parse_args()
    report = run_daily_knowledge_update(force=args.force, log=print)
    if report.get("skipped"):
        print("skipped:", report.get("reason"))
        return 0
    print("done total_ok=", report.get("total_ok"), "date=", report.get("local_date"))
    return 0 if int(report.get("total_ok") or 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
