"""Print a few generation jobs for human review."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
project = sys.argv[1] if len(sys.argv) > 1 else "case_demo"
path = ROOT / "film_pipeline" / "bible" / "projects" / project / "film_bible.json"
bible = json.loads(path.read_text(encoding="utf-8"))
want = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else {"S01_T01", "S01_T05"}

for job in bible.get("generation_jobs") or []:
    if job.get("shot_id") not in want:
        continue
    print("=" * 72)
    print(f"## {job.get('clip_id')} | {job.get('duration_sec')}s | stitch={job.get('stitch')}")
    print()
    print("### 1) actor_free EN")
    print(job.get("actor_free_prompt") or "")
    print()
    print("### 1) actor_free ZH (faithful)")
    print(job.get("actor_free_prompt_zh") or "")
    print()
    print("### 2) director_guided EN")
    print(job.get("director_guided_prompt") or "")
    print()
    print("### 2) director_guided ZH (faithful)")
    print(job.get("director_guided_prompt_zh") or "")
    print()
