"""
Prompt Writer Agent — final stage: FilmBible → generation_jobs.

Product:
  - Pack multiple shots into one model generation (≤15/30s) with timeline storyboard
  - Model cuts internally for smoother flow; new package only when over cap
  - EN + ZH both generation-ready, auto line-wrapped
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from film_pipeline.paths import SKILLS_DIR
from film_pipeline.runtime.knowledge import KnowledgeStore
from film_pipeline.runtime.llm import LLMClient
from film_pipeline.runtime.package_prompt_writer import write_package_prompts
from film_pipeline.runtime.performance import enrich_shots_with_performance
from film_pipeline.runtime.prompt_compiler import (
    compile_motion_prompt,
    compile_negative_prompt,
    compile_visual_prompt,
    compile_zh_summary,
)
from film_pipeline.runtime.prompt_writer import (
    format_prompt_for_delivery,
    write_final_prompts_for_clip,
)
from film_pipeline.runtime.shot_locale import ensure_bible_english_slots
from film_pipeline.runtime.timing import pack_shots_into_generation_packages


AGENT_NAME = "prompt_writer"


def load_prompt_writer_skill(skills_dir: Path | None = None) -> str:
    root = skills_dir or SKILLS_DIR
    for name in ("prompt_writer", "generator"):
        path = root / name / "SKILL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "You are the prompt writer agent."


def run_prompt_writer_agent(
    bible: dict[str, Any],
    llm: LLMClient | None = None,
    knowledge: KnowledgeStore | None = None,
    skills_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Prefer generation_packages (timeline multi-beat).
    Fallback: per-shot clips if packages missing.
    """
    llm = llm or LLMClient()
    knowledge = knowledge or KnowledgeStore()
    ensure_bible_english_slots(bible)
    if any(not s.get("performance") for s in bible.get("shots") or []):
        enrich_shots_with_performance(bible)

    style_id = (bible.get("meta") or {}).get("style_pack", "neo_noir")
    try:
        style_pack = knowledge.style_pack(style_id)
    except Exception:
        style_pack = {"label": style_id}

    max_clip = float(
        (bible.get("timing_plan") or {}).get("max_clip_sec")
        or (bible.get("meta") or {}).get("max_clip_sec")
        or 30
    )

    packages = bible.get("generation_packages")
    if not packages:
        packages = pack_shots_into_generation_packages(
            bible.get("shots") or [], max_clip_sec=max_clip
        )
        bible["generation_packages"] = packages

    jobs: list[dict[str, Any]] = []
    if packages:
        for pkg in packages:
            written = write_package_prompts(bible, pkg, style_pack=style_pack)
            # optional LLM polish later — offline package writer is product path
            if (
                not llm.dry_run
                and llm.api_key
                and False  # package LLM polish reserved
            ):
                pass
            first = (pkg.get("beats") or [{}])[0]
            shot_like = {
                "shot_id": first.get("shot_id"),
                "scene_id": first.get("scene_id"),
                "shot_size": first.get("shot_size"),
                "camera": first.get("camera"),
                "look": first.get("look"),
                "emotion": first.get("emotion"),
                "dramatic_beat": first.get("dramatic_beat"),
                "subject": first.get("subject"),
            }
            visual = compile_visual_prompt(bible, shot_like, style_pack)
            negative = compile_negative_prompt(bible, shot_like)
            motion = compile_motion_prompt(shot_like, clip=None)
            dur = float(pkg.get("duration_sec") or 0)
            jobs.append(
                {
                    "shot_id": first.get("shot_id"),
                    "clip_id": pkg.get("package_id"),
                    "package_id": pkg.get("package_id"),
                    "scene_id": first.get("scene_id"),
                    "shot_ids": pkg.get("shot_ids") or [],
                    "beats": pkg.get("beats") or [],
                    "actor_free_prompt": format_prompt_for_delivery(
                        written["actor_free_prompt"]
                    ),
                    "director_guided_prompt": format_prompt_for_delivery(
                        written["director_guided_prompt"]
                    ),
                    "actor_free_prompt_en": format_prompt_for_delivery(
                        written["actor_free_prompt"]
                    ),
                    "director_guided_prompt_en": format_prompt_for_delivery(
                        written["director_guided_prompt"]
                    ),
                    "actor_free_prompt_zh": format_prompt_for_delivery(
                        written["actor_free_prompt_zh"]
                    ),
                    "director_guided_prompt_zh": format_prompt_for_delivery(
                        written["director_guided_prompt_zh"]
                    ),
                    "visual_prompt": visual,
                    "motion_prompt": motion,
                    "master_prompt": f"{visual}\n\n[Motion / I2V]\n{motion}",
                    "negative_prompt": negative,
                    "zh_director_summary": (
                        f"生成段 {pkg.get('package_id')} · {dur}s · "
                        f"含镜 {', '.join(pkg.get('shot_ids') or [])} · 段内时间轴分镜"
                    ),
                    "duration_sec": dur,
                    "max_clip_sec": max_clip,
                    "timeline_start_sec": 0.0,
                    "timeline_end_sec": dur,
                    "stitch": "package",
                    "internal_cut": True,
                    "prompt_writer": written.get("writer"),
                    "agent": AGENT_NAME,
                    "sources": {
                        "package_id": pkg.get("package_id"),
                        "shot_ids": pkg.get("shot_ids"),
                        "beats": [
                            {
                                "shot_id": b.get("shot_id"),
                                "t_start": b.get("t_start"),
                                "t_end": b.get("t_end"),
                                "linked_dialogue": b.get("linked_dialogue"),
                            }
                            for b in (pkg.get("beats") or [])
                        ],
                    },
                    "downgrades": [],
                }
            )
    else:
        # legacy per-shot fallback
        for shot in bible.get("shots") or []:
            clips = shot.get("generation_clips") or [
                {
                    "clip_id": f"{shot.get('shot_id')}_c01",
                    "duration_sec": shot.get("duration_sec") or 3.5,
                    "stitch": "single",
                }
            ]
            visual = compile_visual_prompt(bible, shot, style_pack)
            negative = compile_negative_prompt(bible, shot)
            for clip in clips:
                written = write_final_prompts_for_clip(
                    bible, shot, clip=clip, style_pack=style_pack, llm=llm
                )
                jobs.append(
                    {
                        "shot_id": shot.get("shot_id"),
                        "clip_id": clip.get("clip_id"),
                        "scene_id": shot.get("scene_id"),
                        "actor_free_prompt": written["actor_free_prompt"],
                        "director_guided_prompt": written["director_guided_prompt"],
                        "actor_free_prompt_en": written["actor_free_prompt"],
                        "director_guided_prompt_en": written["director_guided_prompt"],
                        "actor_free_prompt_zh": written.get("actor_free_prompt_zh") or "",
                        "director_guided_prompt_zh": written.get(
                            "director_guided_prompt_zh"
                        )
                        or "",
                        "visual_prompt": visual,
                        "motion_prompt": compile_motion_prompt(shot, clip=clip),
                        "negative_prompt": negative,
                        "zh_director_summary": compile_zh_summary(shot, clip),
                        "duration_sec": clip.get("duration_sec"),
                        "stitch": clip.get("stitch"),
                        "prompt_writer": written.get("writer"),
                        "agent": AGENT_NAME,
                        "sources": {"linked_dialogue": shot.get("linked_dialogue")},
                        "downgrades": [],
                    }
                )

    # duration stats on bible
    plan = bible.setdefault("timing_plan", {})
    plan["generation_package_count"] = len(packages or [])
    plan["generation_job_count"] = len(jobs)
    plan["generation_total_sec"] = round(
        sum(float(j.get("duration_sec") or 0) for j in jobs), 2
    )
    plan["film_total_sec"] = plan.get("film_total_sec") or round(
        sum(float(s.get("duration_sec") or 0) for s in bible.get("shots") or []), 2
    )
    plan["film_total_min"] = round(float(plan["film_total_sec"]) / 60.0, 2)

    # schema only allows generation_jobs (+ agent); packages live on bible via timing
    return {"generation_jobs": jobs, "agent": AGENT_NAME}
