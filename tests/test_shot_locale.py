"""English generation slots must not dump Chinese beats into EN main drafts."""

from __future__ import annotations

import re

from film_pipeline.runtime.performance import (
    compile_actor_free_prompt_en,
    compile_director_guided_prompt_en,
)
from film_pipeline.runtime.shot_locale import (
    ensure_shot_english_slots,
    has_cjk,
    resolve_dramatic_beat_en,
    resolve_subject_en,
)

_CJK = re.compile(r"[\u4e00-\u9fff]")


def test_resolve_prefers_en_fields():
    shot = {
        "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
        "dramatic_beat_en": "Rainy-night living room establish",
        "subject": "客厅、台灯、茶几上的信封",
        "subject_en": "living room, lamp, envelope",
    }
    assert resolve_dramatic_beat_en(shot) == "Rainy-night living room establish"
    assert resolve_subject_en(shot) == "living room, lamp, envelope"


def test_map_fills_when_en_missing():
    shot = {
        "dramatic_beat": "周宁笑容塌陷",
        "subject": "周宁半边脸落在台灯里",
    }
    ensure_shot_english_slots(shot)
    assert not has_cjk(shot["dramatic_beat_en"])
    assert not has_cjk(shot["subject_en"])
    assert "Zhou Ning" in shot["dramatic_beat_en"]


def test_actor_free_en_has_no_cjk_for_sample_beat():
    shot = {
        "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
        "dramatic_beat_en": (
            "Rainy-night living room establish: sealed envelope centered on the coffee table"
        ),
        "subject": "客厅、台灯、茶几上的信封",
        "subject_en": "living room, table lamp, envelope on the coffee table",
        "shot_size": "WS",
        "duration_sec": 3.4,
        "emotion": {"primary": "calm", "intensity": 0.3},
        "camera": {"lens_mm": 35, "angle": "eye_level"},
        "performance": {
            "emotion": "calm",
            "intensity_label_en": "relaxed",
            "actor_free_tags": ["calm", "composed"],
        },
    }
    en = compile_actor_free_prompt_en(shot)
    assert not _CJK.search(en), en
    assert en.startswith("Rainy-night")
    assert "living room, table lamp" in en


def test_director_guided_uses_en_beat_not_zh():
    bible = {"meta": {"style_pack": "neo_noir"}, "look_bible": {"film_look": {}}, "dialogue": []}
    shot = {
        "shot_id": "S01_T01",
        "scene_id": "S01",
        "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
        "dramatic_beat_en": "Rainy-night living room establish",
        "subject": "客厅",
        "subject_en": "living room",
        "shot_size": "WS",
        "duration_sec": 3.4,
        "camera": {"lens_mm": 35, "angle": "eye_level", "height": "eye", "movement": {}},
        "look": {"tone": "low_key"},
        "performance": {
            "emotion": "calm",
            "intensity_label_en": "relaxed",
            "physiology_en": "steady breath",
            "micro_actions_en": [],
            "lighting_plan": {"key": "soft side key", "look_table": {}},
        },
    }
    en = compile_director_guided_prompt_en(bible, shot)
    assert "雨夜" not in en
    assert "Rainy-night" in en
    assert "living room" in en
