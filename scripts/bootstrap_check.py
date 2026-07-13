"""Quick sanity check without pytest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FILM_PIPELINE_DRY_RUN", "1")

from film_pipeline.orchestrator.pipeline import Pipeline
from film_pipeline.paths import EXAMPLES_DIR


def main() -> int:
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    bible = Pipeline().run_all(project_id="bootstrap", script=script, max_clip_sec=30)
    print("shots:", len(bible.get("shots") or []))
    print("look:", (bible.get("look_bible") or {}).get("film_look", {}).get("key"))
    print("review:", bible.get("last_review"))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
