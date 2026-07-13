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
    bible = pipe.run_all(project_id="test_demo", script=script, style_pack="neo_noir")

    assert bible["story"]["logline"]
    assert bible["scenes"]
    assert bible["dialogue"]
    assert len(bible["shots"]) >= 3
    assert bible["look_bible"]["film_look"]["key"]
    assert all("camera" in s and "look" in s for s in bible["shots"])
    assert all((s["camera"].get("movement") or {}).get("motivation") for s in bible["shots"])
    assert all((s["look"] or {}).get("motivation") for s in bible["shots"])
    assert bible["generation_jobs"]
    job0 = bible["generation_jobs"][0]
    assert job0.get("visual_prompt")
    assert job0.get("motion_prompt")
    assert job0.get("master_prompt")
    assert job0.get("negative_prompt")
    assert "mm" in job0["visual_prompt"] or "lens" in job0["visual_prompt"].lower()
    assert "last_review" in bible
    assert bible["last_review"]["pass"] is True

    from film_pipeline.paths import PROJECTS_DIR

    board = PROJECTS_DIR / "test_demo" / "prompt_board.md"
    assert board.exists()
    text = board.read_text(encoding="utf-8")
    assert "Visual prompt" in text


def test_skill_schemas_exist():
    for stage in [
        "dramaturg",
        "dialogue",
        "director",
        "look",
        "cinematography",
        "generator",
        "critic",
    ]:
        skill = SKILLS_DIR / stage / "SKILL.md"
        schema = SKILLS_DIR / stage / "schema.json"
        assert skill.exists(), stage
        assert schema.exists(), stage
        load_schema(schema)
