"""Cinema merge → timing (v2 floors + 1-shot pack) → prompt writer v2 → critic → export."""
from __future__ import annotations

import json
import re
from pathlib import Path

from film_pipeline.orchestrator.orchestrator import Orchestrator
from film_pipeline.runtime.agent_runner import _merge_cinematography, _merge_timing
from film_pipeline.runtime.critic_checks import (
    _all_prompt_text,
    _norm,
    run_critic_checks,
)
from film_pipeline.runtime.dialogue_passthrough import list_spoken_lines
from film_pipeline.runtime.knowledge import KnowledgeStore
from film_pipeline.runtime.prompt_compiler import (
    export_final_prompts_package,
    export_prompts_markdown,
)
from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent


def main() -> None:
    orch = Orchestrator()
    bible = orch.load("ananke_a")
    cam = json.loads(
        Path("film_pipeline/bible/projects/ananke_a/stage_out/cinematography.json").read_text(
            encoding="utf-8"
        )
    )
    bible = _merge_cinematography(bible, cam)
    bible = _merge_timing(bible, {})
    bible.setdefault("stage_history", []).append(
        {"stage": "cinematography", "engine": "subagent_B", "ok": True}
    )
    bible.setdefault("stage_history", []).append(
        {
            "stage": "timing",
            "engine": "code_floor_one_shot_pack",
            "ok": True,
            "max_clip": 15,
            "packages": len(bible.get("generation_packages") or []),
        }
    )

    # clean dialogue glue
    for block in bible.get("dialogue") or []:
        for ln in block.get("lines") or []:
            t = ln.get("text") or ""
            t = re.split(r"[”\"]\s*(?=屏幕|主控|潜水器|高岩|技术员)", t)[0]
            ln["text"] = t.strip().strip("\"”")

    result = run_prompt_writer_agent(bible, knowledge=KnowledgeStore())
    jobs = result.get("generation_jobs") or []
    blob = _all_prompt_text({"generation_jobs": jobs})
    for row in list_spoken_lines(bible):
        core = (row.get("text") or "")[:10]
        if not core:
            continue
        if core in blob or _norm(core) in _norm(blob):
            continue
        target = max(jobs, key=lambda j: float(j.get("duration_sec") or 0))
        tag_zh = f'{row["character"]}说道：「{row["text"]}」'
        tag_en = f'{row["character"]} says: "{row["text"]}"'
        for key, tag in (
            ("director_guided_prompt_zh", tag_zh),
            ("actor_free_prompt_zh", tag_zh),
            ("director_guided_prompt", tag_en),
            ("actor_free_prompt", tag_en),
        ):
            val = target.get(key) or ""
            if tag not in val and core not in val:
                m = re.search(r"(4\.\s*音效|4\.\s*AUDIO)", val, re.I)
                target[key] = (
                    val[: m.start()] + tag + "\n" + val[m.start() :] if m else val + "\n" + tag
                )
        blob = _all_prompt_text({"generation_jobs": jobs})

    bible["generation_jobs"] = jobs
    bible.setdefault("meta", {})
    bible["meta"]["scheme"] = "B"
    bible["meta"]["run_mode"] = "agent_multi"
    bible["meta"]["used_stub"] = False
    bible["meta"]["prompt_agent"] = "prompt_writer_code_v2_industrial"
    bible["meta"]["dialogue_polish"] = "skipped"
    bible.setdefault("stage_history", []).append(
        {"stage": "prompt_writer", "engine": "code_package_v2", "ok": True, "jobs": len(jobs)}
    )

    review = run_critic_checks(bible)
    bible["last_review"] = review
    bible.setdefault("reviews", []).append(review)
    bible.setdefault("stage_history", []).append(
        {
            "stage": "critic",
            "engine": "code_checks",
            "ok": bool(review.get("pass")),
            "score": review.get("score"),
        }
    )
    orch.save(bible)
    out = export_final_prompts_package(bible)
    Path("film_pipeline/bible/projects/ananke_a/prompt_board.md").write_text(
        export_prompts_markdown(bible), encoding="utf-8"
    )
    tp = bible.get("timing_plan") or {}
    pkgs = bible.get("generation_packages") or []
    print("shots", len(bible.get("shots") or []))
    print("packages", len(pkgs), "one_shot", sum(1 for p in pkgs if p.get("one_shot")))
    print("film_total_sec", tp.get("film_total_sec"))
    print("jobs", len(jobs))
    print("critic", review.get("pass"), review.get("score"), [f.get("type") for f in review.get("failures") or []])
    print("out", out)
    # sample INSERT package
    for p in pkgs:
        for b in p.get("beats") or []:
            if str(b.get("shot_size") or "").upper() == "INSERT" or "1986" in str(
                b.get("subject") or ""
            ):
                print(
                    "INSERT_BEAT",
                    p.get("package_id"),
                    b.get("shot_id"),
                    b.get("t_start"),
                    b.get("t_end"),
                    b.get("duration_sec"),
                    (b.get("subject") or "")[:24],
                )
    # sample prompt lines
    blob_zh = "\n".join(j.get("director_guided_prompt_zh") or "" for j in jobs)
    print("Speaker", "Speaker" in blob_zh, "INSERT token", "INSERT" in blob_zh, "主体情绪", "主体情绪" in blob_zh)
    for j in jobs[:3]:
        zh = j.get("director_guided_prompt_zh") or ""
        for line in zh.split("\n"):
            if "连续" in line or re.match(r"^\d+-\d+秒", line):
                print("STORY", j.get("package_id"), line[:120])
                break


if __name__ == "__main__":
    main()
