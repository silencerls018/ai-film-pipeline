"""Dedicated prompt_writer agent owns final prompts."""

from __future__ import annotations

from film_pipeline.runtime.prompt_writer_agent import (
    AGENT_NAME,
    run_prompt_writer_agent,
)
from film_pipeline.paths import SKILLS_DIR


def test_prompt_writer_skill_exists():
    assert (SKILLS_DIR / "prompt_writer" / "SKILL.md").exists()
    assert (SKILLS_DIR / "prompt_writer" / "schema.json").exists()


def test_agent_writes_jobs_with_agent_tag(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    bible = {
        "meta": {"style_pack": "neo_noir", "project_id": "t"},
        "dialogue": [],
        "look_bible": {"film_look": {"key": "low_key", "palette": []}},
        "timing_plan": {"max_clip_sec": 30},
        "shots": [
            {
                "shot_id": "S01_T01",
                "scene_id": "S01",
                "dramatic_beat": "深水",
                "dramatic_beat_en": "Deep water push-in",
                "subject": "物体",
                "subject_en": "sinking mass",
                "shot_size": "EWS",
                "duration_sec": 6,
                "emotion": {"primary": "dread", "intensity": 0.5},
                "camera": {
                    "lens_mm": 35,
                    "angle": "eye_level",
                    "movement": {"type": "Creep In", "zh": "缓推", "prompt_en": "slow push"},
                },
                "look": {"tone": "low_key"},
                "generation_clips": [
                    {
                        "clip_id": "S01_T01_c01",
                        "duration_sec": 6,
                        "timeline_start_sec": 0,
                        "timeline_end_sec": 6,
                        "stitch": "single",
                    }
                ],
            }
        ],
    }
    out = run_prompt_writer_agent(bible)
    assert out["agent"] == AGENT_NAME
    jobs = out["generation_jobs"]
    assert len(jobs) == 1
    assert jobs[0]["agent"] == AGENT_NAME
    assert jobs[0]["actor_free_prompt"]
    assert jobs[0]["director_guided_prompt"]
    zh = jobs[0]["director_guided_prompt_zh"]
    # ZH is feedable product (not reading-aid only); package timeline or four-part body
    assert "指定主体" in zh or "故事线" in zh
    assert "看懂" not in zh  # no legacy reading-aid banner


def test_pipeline_uses_prompt_agent(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    from film_pipeline.orchestrator import Orchestrator, ProductionBrief
    from film_pipeline.paths import EXAMPLES_DIR

    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_prompt_agent",
        title="test_prompt_agent",
        max_clip_sec=30,
        run_asset_track=False,
    )
    bible = Orchestrator(log=lambda m: None).run_production(brief, script)
    assert bible.get("meta", {}).get("prompt_agent") == "prompt_writer"
    assert all(j.get("agent") == "prompt_writer" for j in bible.get("generation_jobs") or [])
