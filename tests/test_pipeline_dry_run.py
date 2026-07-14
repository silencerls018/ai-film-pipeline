from __future__ import annotations

from film_pipeline.orchestrator import Orchestrator, ProductionBrief, MAIN_STAGES
from film_pipeline.orchestrator.pipeline import Pipeline
from film_pipeline.paths import EXAMPLES_DIR, PROJECTS_DIR, SKILLS_DIR
from film_pipeline.runtime.validate import load_schema


def test_full_pipeline_dry_run(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_demo",
        title="test_demo",
        max_clip_sec=30,
        style_pack="neo_noir",
        run_main_track=True,
        run_asset_track=True,
    )
    bible = Orchestrator().run_production(brief, script)

    assert bible["production_brief"]["max_clip_sec"] == 30
    assert bible["meta"]["commander"] == "orchestrator"
    assert bible["meta"]["max_clip_sec"] == 30
    assert bible["story"]["logline"]
    assert bible["scenes"]
    assert bible["dialogue"]
    assert len(bible["shots"]) >= 3
    assert bible["look_bible"]["film_look"]["key"]
    assert all("camera" in s and "look" in s for s in bible["shots"])
    assert bible["timing_plan"]["max_clip_sec"] == 30
    assert bible["generation_jobs"]
    job0 = bible["generation_jobs"][0]
    assert job0.get("actor_free_prompt")
    assert job0.get("director_guided_prompt")
    # Main prompts are English content (no pipeline meta noise)
    assert job0.get("actor_free_prompt")
    assert job0.get("director_guided_prompt")
    assert "跳过对白" not in job0["director_guided_prompt"]
    assert "禁止比喻修辞" not in (job0.get("director_guided_prompt_zh") or "")
    assert "shot bias" not in job0["director_guided_prompt"].lower()
    # Chinese is auxiliary reading aid
    assert job0.get("actor_free_prompt_zh")
    assert job0.get("director_guided_prompt_zh")
    assert any(s.get("performance") for s in bible["shots"])
    assert bible["asset_bible"]
    assert bible["asset_bible"]["characters"]
    assert bible["task_log"]
    stages_done = [t["stage"] for t in bible["task_log"] if t["status"] == "done"]
    assert "dramaturg" in stages_done
    assert "asset" in stages_done
    assert "generator" in stages_done
    assert bible["last_review"]["pass"] is True
    assert (PROJECTS_DIR / "test_demo" / "prompt_board.md").exists()
    board = (PROJECTS_DIR / "test_demo" / "prompt_board.md").read_text(encoding="utf-8")
    assert "英文主稿" in board and "中文对照" in board
    assert (PROJECTS_DIR / "test_demo" / "production_brief.json").exists()
    assert (PROJECTS_DIR / "test_demo" / "asset_board.md").exists()


def test_pipeline_compat_wrapper(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    bible = Pipeline().run_all(
        project_id="test_compat",
        script=script,
        max_clip_sec=15,
        run_asset_track=False,
    )
    assert bible["meta"]["max_clip_sec"] == 15
    assert bible.get("asset_bible") in (None, {})
    # no asset ticket
    assert not any(t["stage"] == "asset" for t in bible.get("task_log") or [])


def test_run_with_15s_cap(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_15s",
        title="test_15s",
        max_clip_sec=15,
        run_asset_track=True,
    )
    bible = Orchestrator().run_production(brief, script)
    assert bible["timing_plan"]["max_clip_sec"] == 15
    for s in bible["shots"]:
        for c in s["generation_clips"]:
            assert c["duration_sec"] <= 15 + 1e-6


def test_assets_only_rerun(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_assets_later",
        title="x",
        max_clip_sec=30,
        run_asset_track=False,
    )
    orch = Orchestrator()
    bible = orch.run_production(brief, script)
    assert not bible.get("asset_bible")
    bible = orch.run_asset_track(bible)
    assert bible["asset_bible"]["characters"]
    # image_refs empty — swappable
    assert bible["asset_bible"]["characters"][0]["image_refs"] == []


def test_split_when_over_cap():
    from film_pipeline.runtime.timing import split_into_clips

    clips = split_into_clips(75, max_clip_sec=30, min_clip_sec=2, overlap_sec=0.5, shot_id="S01_T99")
    assert len(clips) >= 3
    assert all(c["duration_sec"] <= 30 for c in clips)


def test_clip_profile_normalize():
    from film_pipeline.runtime.clip_profile import normalize_max_clip, profile_for_max_clip

    assert normalize_max_clip(15) == 15
    assert profile_for_max_clip(30) == "max_30s"


def test_skill_schemas_exist():
    for stage in list(MAIN_STAGES) + ["asset", "timing"]:
        # timing is in MAIN_STAGES
        skill = SKILLS_DIR / stage / "SKILL.md"
        schema = SKILLS_DIR / stage / "schema.json"
        assert skill.exists(), stage
        assert schema.exists(), stage
        load_schema(schema)


def test_org_chart_text():
    from film_pipeline.orchestrator.task_ticket import describe_org_chart

    text = describe_org_chart()
    assert "Orchestrator" in text
    assert "assets" in text


def test_three_view_template_in_assets(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_three_view",
        title="x",
        max_clip_sec=30,
        run_asset_track=True,
        run_dialogue_polish=False,
    )
    bible = Orchestrator(log=lambda m: None).run_production(brief, script)
    chars = (bible.get("asset_bible") or {}).get("characters") or []
    assert chars
    sp = chars[0].get("sheet_prompt") or ""
    assert "50" in sp and ("LEFT SIDE" in sp or "left half" in sp.lower())
    assert "Ethnicity" in sp or "race" in sp.lower()
    assert "black rectangular" in sp.lower() or "censor" in sp.lower()
    assert "facial close-up" in sp.lower() or "Facial Close-Up" in sp
    # no negative prompt per user request
    assert (chars[0].get("negative_prompt") or "") == ""
    assert chars[0].get("sheet_prompt_zh_summary")
    assert chars[0].get("ethnicity")


def test_skip_dialogue_polish(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="test_no_dialogue_polish",
        title="x",
        max_clip_sec=30,
        run_asset_track=False,
        run_dialogue_polish=False,
    )
    bible = Orchestrator(log=lambda m: None).run_production(brief, script)
    assert bible["meta"].get("dialogue_polish") == "skipped" or any(
        (d.get("polish_skipped") for d in bible.get("dialogue") or [])
    )
    # original wording should survive (not the polished stub rewrite)
    texts = " ".join(
        ln.get("text", "")
        for block in bible.get("dialogue") or []
        for ln in block.get("lines") or []
    )
    assert "信封被动过了" in texts or "你早就看过了" in texts
    hist = bible.get("stage_history") or []
    assert any(h.get("status") == "skipped_polish" for h in hist)
    # pipeline still finishes prompts
    assert bible.get("generation_jobs")
