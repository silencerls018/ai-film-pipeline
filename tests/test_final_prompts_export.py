"""Final prompts go to outputs/<project_name>/."""

from __future__ import annotations

from film_pipeline.paths import FINAL_PROMPTS_ROOT, final_prompts_dir, sanitize_project_id
from film_pipeline.runtime.prompt_compiler import export_final_prompts_package


def test_sanitize_and_path():
    assert sanitize_project_id("user_ananke") == "user_ananke"
    assert ".." not in sanitize_project_id("../evil")
    p = final_prompts_dir("user_ananke")
    assert p == FINAL_PROMPTS_ROOT / "user_ananke"
    assert p.name == "user_ananke"


def test_export_package_layout(tmp_path):
    bible = {
        "meta": {
            "project_id": "demo_export",
            "title": "demo_export",
            "style_pack": "neo_noir",
            "max_clip_sec": 15,
            "film_total_sec": 42.5,
        },
        "story": {"logline": "test"},
        "timing_plan": {
            "max_clip_sec": 15,
            "film_total_sec": 42.5,
            "generation_total_sec": 45.0,
            "generation_package_count": 3,
        },
        "generation_jobs": [
            {
                "shot_id": "S01_T01",
                "clip_id": "S01_T01_c01",
                "actor_free_prompt": "FREE EN",
                "director_guided_prompt": "GUIDED EN",
                "actor_free_prompt_zh": "自由中文",
                "director_guided_prompt_zh": "导演中文",
                "duration_sec": 5,
                "stitch": "single",
                "zh_director_summary": "摘要",
            }
        ],
        "asset_bible": {
            "characters": [
                {
                    "asset_id": "char_a",
                    "name": "苏檀",
                    "type": "character",
                    "sheet_prompt": "SHEET EN SU TAN",
                    "sheet_prompt_zh_summary": "苏檀三视图说明",
                    "consistency_anchors": ["a"],
                    "image_refs": [],
                }
            ],
            "props": [
                {
                    "asset_id": "prop_lolly",
                    "name": "棒棒糖",
                    "type": "prop",
                    "sheet_prompt": "LOLLY SHEET",
                    "image_refs": [],
                }
            ],
            "sets": [],
        },
    }
    root = export_final_prompts_package(bible, dest=tmp_path / "demo_export")
    assert root.name == "demo_export"
    assert (root / "prompt_board.md").exists()
    assert (root / "README.txt").exists()
    guided_out = (root / "clips" / "S01_T01_c01_director_guided.en.txt").read_text(
        encoding="utf-8"
    )
    assert "GUIDED EN" in guided_out
    assert "FREE EN" in (root / "clips" / "S01_T01_c01_actor_free.en.txt").read_text(
        encoding="utf-8"
    )
    # assets always in delivery folder
    assert (root / "assets" / "asset_board.md").exists()
    assert (root / "assets" / "asset_bible.json").exists()
    assert "苏檀" in (root / "assets" / "asset_board.md").read_text(encoding="utf-8")
    char_sheets = list((root / "assets" / "characters").glob("*_sheet.en.txt"))
    assert char_sheets
    assert "SHEET EN SU TAN" in char_sheets[0].read_text(encoding="utf-8")
    assert (root / "assets" / "props").exists()
    readme = (root / "README.txt").read_text(encoding="utf-8")
    assert "assets/" in readme
    board = (root / "prompt_board.md").read_text(encoding="utf-8")
    assert "电影最终时长" in board
    assert "42.5" in board
