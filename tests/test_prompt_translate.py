"""English final prompt is source of truth; Chinese is faithful mirror."""

from __future__ import annotations

from film_pipeline.runtime.prompt_translate import (
    translate_prompt_en_to_zh,
    zh_covers_en_markers,
)
from film_pipeline.runtime.performance import (
    compile_actor_free_prompt_en,
    compile_actor_free_prompt_zh,
    compile_director_guided_prompt_en,
    compile_director_guided_prompt_zh,
)


def test_translate_preserves_dialogue_and_numbers():
    en = (
        'MCU shot, about 7.65 seconds. Subject: 林安眼睛. '
        'Lin says: "你早就看过了。". Photoreal cinematic film, no subtitles, no watermark.'
    )
    zh = translate_prompt_en_to_zh(en)
    assert "【中文对照·忠实翻译英文终稿】" in zh
    assert "你早就看过了。" in zh
    assert "7.65" in zh
    assert "林安眼睛" in zh
    assert "中近景（MCU）" in zh or "MCU" in zh
    assert not zh_covers_en_markers(en, zh)


def test_zh_is_derived_from_en_not_parallel_rewrite():
    shot = {
        "shot_id": "S01_T01",
        "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
        "dramatic_beat_en": (
            "Rainy-night living room establish: sealed envelope centered on the coffee table"
        ),
        "shot_size": "WS",
        "subject": "客厅、台灯、茶几上的信封",
        "subject_en": "living room, table lamp, envelope on the coffee table",
        "duration_sec": 3.4,
        "emotion": {"primary": "calm", "intensity": 0.3},
        "camera": {"lens_mm": 35, "angle": "eye_level"},
        "performance": {
            "emotion": "calm",
            "intensity_label_en": "relaxed",
            "actor_free_tags": ["calm", "composed", "neutral breath"],
        },
    }
    en = compile_actor_free_prompt_en(shot)
    zh = compile_actor_free_prompt_zh(shot)
    # Same function chain: zh mirrors this exact en
    assert translate_prompt_en_to_zh(en) == zh
    assert "Rainy-night" in en
    assert "3.4" in zh
    assert "35" in zh
    missing = zh_covers_en_markers(en, zh)
    assert missing == [], f"ZH missing EN markers: {missing}"


def test_director_guided_zh_mirrors_en():
    bible = {
        "meta": {"style_pack": "neo_noir"},
        "look_bible": {
            "film_look": {"key": "low_key", "palette": ["cold_cyan_shadow"]},
            "scene_looks": [],
        },
        "dialogue": [
            {
                "scene_id": "S01",
                "lines": [
                    {
                        "character": "林安",
                        "text": "信封被动过了。",
                        "delivery": "",
                        "subtext": "",
                    }
                ],
            }
        ],
    }
    shot = {
        "shot_id": "S01_T03",
        "scene_id": "S01",
        "dramatic_beat": "林安不抬头说出信封被动过",
        "dramatic_beat_en": (
            "Lin An, without looking up, states the envelope has been tampered with"
        ),
        "shot_size": "MCU",
        "subject": "林安上半身与茶几",
        "subject_en": "Lin An upper body and the coffee table",
        "duration_sec": 8.5,
        "emotion": {"primary": "suspicion", "intensity": 0.65},
        "linked_dialogue": ["信封被动过了。"],
        "camera": {
            "lens_mm": 35,
            "angle": "eye_level",
            "height": "chest",
            "movement": {
                "type": "Creep In",
                "speed": "very_slow",
                "prompt_en": "slow push in",
            },
        },
        "look": {"tone": "low_key", "key_light": "soft side key"},
        "performance": {
            "emotion": "suspicion",
            "intensity_label_en": "clear wariness",
            "physiology_en": "brows slightly drawn, jaw lightly clenched",
            "micro_actions_en": ["small swallow"],
            "gaze_en": "probing eye contact",
            "voice_hint_en": "low voice, slightly slow",
            "lighting_plan": {
                "key": "side key",
                "ratio": "half shadow",
                "color": "cool fill",
                "look_table": {"face": "half lit"},
            },
        },
    }
    en = compile_director_guided_prompt_en(bible, shot, style_pack={"label": "Neo Noir"})
    zh = compile_director_guided_prompt_zh(bible, shot, style_pack={"label": "Neo Noir"})
    assert translate_prompt_en_to_zh(en) == zh
    assert "信封被动过了。" in zh
    assert "8.5" in zh
    # Must not invent parallel template slogans removed from EN path
    assert "禁止比喻修辞" not in zh
    assert "跳过对白" not in zh
    missing = zh_covers_en_markers(en, zh)
    assert missing == [], f"ZH missing EN markers: {missing}"


def test_empty_en_yields_empty_zh():
    assert translate_prompt_en_to_zh("") == ""
    assert translate_prompt_en_to_zh("   ") == ""
