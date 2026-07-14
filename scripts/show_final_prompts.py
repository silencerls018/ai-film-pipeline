"""Show final prompts for a project (English main + Chinese reading aid)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
project = sys.argv[1] if len(sys.argv) > 1 else "deep_dive_cli"
shot_filter = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

bible_path = ROOT / "film_pipeline" / "bible" / "projects" / project / "film_bible.json"
if not bible_path.exists():
    print(f"Not found: {bible_path}")
    sys.exit(1)

bible = json.loads(bible_path.read_text(encoding="utf-8"))
jobs = bible.get("generation_jobs") or []

print(f"project: {bible.get('meta', {}).get('project_id')}")
print(f"title:   {bible.get('meta', {}).get('title')}")
print(f"logline: {(bible.get('story') or {}).get('logline')}")
print(f"agent:   {bible.get('meta', {}).get('prompt_agent')}")
print(f"jobs:    {len(jobs)}")
print()

shown_shots: set[str] = set()
for job in jobs:
    sid = job.get("shot_id") or ""
    cid = job.get("clip_id") or ""
    if shot_filter is not None and sid not in shot_filter:
        continue
    # default: first clip of each shot only, unless filter is clips
    if shot_filter is None:
        if sid in shown_shots:
            continue
        if not cid.endswith("c01"):
            continue
        shown_shots.add(sid)

    print("=" * 72)
    print(f"SHOT {sid}  clip={cid}  duration={job.get('duration_sec')}s  stitch={job.get('stitch')}")
    print(f"writer={job.get('prompt_writer')}  agent={job.get('agent')}")
    print()
    print("### EN actor_free (main)")
    print(job.get("actor_free_prompt") or "")
    print()
    print("### ZH actor_free (read-only aid)")
    print(job.get("actor_free_prompt_zh") or "")
    print()
    print("### EN director_guided (main)")
    print(job.get("director_guided_prompt") or "")
    print()
    print("### ZH director_guided (read-only aid)")
    print(job.get("director_guided_prompt_zh") or "")
    print()
