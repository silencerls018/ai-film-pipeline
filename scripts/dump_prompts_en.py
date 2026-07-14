"""Dump English final prompts (main) + Chinese reading aid for a project."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
project = sys.argv[1] if len(sys.argv) > 1 else "deep_dive_cli"
only_c01 = "--all-clips" not in sys.argv

bible_path = ROOT / "film_pipeline" / "bible" / "projects" / project / "film_bible.json"
b = json.loads(bible_path.read_text(encoding="utf-8"))
jobs = b.get("generation_jobs") or []

print(f"project: {b.get('meta', {}).get('project_id')}")
print(f"title:   {b.get('meta', {}).get('title')}")
print(f"logline: {(b.get('story') or {}).get('logline')}")
print(f"agent:   {b.get('meta', {}).get('prompt_agent')}")
print(f"max_clip:{b.get('meta', {}).get('max_clip_sec')}")
print(f"jobs:    {len(jobs)}")
print()

shown = set()
for j in jobs:
    sid = j.get("shot_id") or ""
    cid = j.get("clip_id") or ""
    if only_c01:
        if sid in shown:
            continue
        if not cid.endswith("c01"):
            continue
        shown.add(sid)

    print("=" * 72)
    print(f"{cid}  {j.get('duration_sec')}s  stitch={j.get('stitch')}  agent={j.get('agent')}  writer={j.get('prompt_writer')}")
    print()
    print("### EN actor_free (MAIN)")
    print(j.get("actor_free_prompt") or "")
    print()
    print("### ZH actor_free (read aid only)")
    print(j.get("actor_free_prompt_zh") or "")
    print()
    print("### EN director_guided (MAIN)")
    print(j.get("director_guided_prompt") or "")
    print()
    print("### ZH director_guided (read aid only)")
    print(j.get("director_guided_prompt_zh") or "")
    print()

board = Path("film_pipeline/bible/projects") / project / "prompt_board.md"
if board.exists():
    desk = Path.home() / "Desktop" / "深眸号_最终提示词_可读版.md"
    try:
        shutil.copy2(board, desk)
        print(f"copied -> {desk}")
    except Exception as e:
        print("copy failed:", e)
