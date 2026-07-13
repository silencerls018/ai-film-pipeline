from __future__ import annotations

from pathlib import Path

from film_pipeline.orchestrator.pipeline import Pipeline
from film_pipeline.paths import EXAMPLES_DIR
from film_pipeline.runtime.validate import load_schema, validate_against_schema
from film_pipeline.paths import SKILLS_DIR


def test_full_pipeline_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    # isolate project writes into package projects dir is fine for demo id
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    pipe = Pipeline()
    bible = pipe.run_all(
        project_id="test_demo",
        script=script,
        style_pack="neo_noir",
        max_clip_sec=30,
    )

    assert bible["meta"]["max_clip_sec"] == 30
    assert bible["meta"]["model_profile"] == "max_30s"
    assert bible["story"]["logline"]
    assert bible["scenes"]
    assert bible["dialogue"]
    assert len(bible["shots"]) >= 3
    assert bible["look_bible"]["film_look"]["key"]
    assert all("camera" in s and "look" in s for s in bible["shots"])
    assert all((s["camera"].get("movement") or {}).get("motivation") for s in bible["shots"])
    assert all((s["look"] or {}).get("motivation") for s in bible["shots"])
    assert bible["timing_plan"]
    assert bible["timing_plan"]["max_clip_sec"] == 30
    assert all(s.get("duration_sec") for s in bible["shots"])
    assert all(s.get("generation_clips") for s in bible["shots"])
    for s in bible["shots"]:
        for c in s["generation_clips"]:
            assert c["duration_sec"] <= 30 + 1e-6

    assert bible["generation_jobs"]
    job0 = bible["generation_jobs"][0]
    assert job0.get("visual_prompt")
    assert job0.get("motion_prompt")
    assert job0.get("master_prompt")
    assert job0.get("negative_prompt")
    assert job0.get("duration_sec") is not None
    assert "mm" in job0["visual_prompt"] or "lens" in job0["visual_prompt"].lower()
    assert "last_review" in bible
    assert bible["last_review"]["pass"] is True

    from film_pipeline.paths import PROJECTS_DIR

    board = PROJECTS_DIR / "test_demo" / "prompt_board.md"
    assert board.exists()
    text = board.read_text(encoding="utf-8")
    assert "Visual prompt" in text
    assert (PROJECTS_DIR / "test_demo" / "timing_plan.md").exists()


def test_split_when_over_cap():
    from film_pipeline.runtime.timing import split_into_clips

    clips = split_into_clips(75, max_clip_sec=30, min_clip_sec=2, overlap_sec=0.5, shot_id="S01_T99")
    assert len(clips) >= 3
    assert all(c["duration_sec"] <= 30 for c in clips)
    assert clips[0]["stitch"] == "first"
    assert clips[-1]["stitch"] == "last"

    clips15 = split_into_clips(40, max_clip_sec=15, min_clip_sec=2, overlap_sec=0.5, shot_id="S01_T88")
    assert len(clips15) >= 3
    assert all(c["duration_sec"] <= 15 for c in clips15)


def test_run_with_15s_cap(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    bible = Pipeline().run_all(
        project_id="test_15s",
        script=script,
        max_clip_sec=15,
    )
    assert bible["meta"]["max_clip_sec"] == 15
    assert bible["timing_plan"]["max_clip_sec"] == 15
    for s in bible["shots"]:
        for c in s["generation_clips"]:
            assert c["duration_sec"] <= 15 + 1e-6


def test_clip_profile_normalize():
    from film_pipeline.runtime.clip_profile import normalize_max_clip, profile_for_max_clip

    assert normalize_max_clip(15) == 15
    assert normalize_max_clip("30") == 30
    assert profile_for_max_clip(15) == "max_15s"
    assert profile_for_max_clip(30) == "max_30s"
    try:
        normalize_max_clip(10)
        assert False, "should reject 10"
    except ValueError:
        pass


def test_dialogue_duration_zh():
    from film_pipeline.runtime.timing import estimate_line_sec

    sec = estimate_line_sec("你早就看过了。", delivery="抬眼，停在早就")
    assert 1.0 <= sec <= 6.0


def test_skill_schemas_exist():
    for stage in [
        "dramaturg",
        "dialogue",
        "director",
        "look",
        "cinematography",
        "timing",
        "generator",
        "critic",
    ]:
        skill = SKILLS_DIR / stage / "SKILL.md"
        schema = SKILLS_DIR / stage / "schema.json"
        assert skill.exists(), stage
        assert schema.exists(), stage
        load_schema(schema)
