"""Natural-language final prompt writer (AI or offline plain)."""

from __future__ import annotations

from film_pipeline.runtime.prompt_writer import (
    build_contract_brief,
    write_final_prompts_for_clip,
    write_prompts_offline,
)

_BANNED = [
    "来自 Look",
    "摄影执行",
    "打光服务",
    "不为炫技",
    "一切为剧情",
    "不要硬加人脸",
    "no forced human faces",
    "same as previous",
    "as above",
    "continue from last",
    "同上",
    "接上一段",
    "知识库",
    "服务 beat",
    "LOOK / GRADE (from",
]


def _assert_clean(text: str) -> None:
    low = text.lower()
    for b in _BANNED:
        assert b.lower() not in low, f"banned phrase leaked: {b}"


def test_offline_writer_four_part_format():
    bible = {
        "meta": {"style_pack": "neo_noir"},
        "story": {"logline": "Deep-dive crew races a corporate deadline under pressure."},
        "scenes": [{"scene_id": "S01", "location": "turbid deep ocean near research sub"}],
        "dialogue": [],
        "look_bible": {
            "film_look": {
                "key": "low_key_neo_noir",
                "contrast": "high",
                "palette": ["cold_cyan_shadow", "warm_practical_key"],
                "saturation": "controlled_low",
                "motivation": "亲密空间被知情权撕裂：暖实用光 vs 冷阴影",
            },
            "scene_looks": [
                {
                    "scene_id": "S01",
                    "base_tone": "low_key",
                    "contrast": "high",
                    "color": "cold_cyan, sick_green_optional",
                    "emotion_arc_in_tone": "中灰日常 → 低调高反差对质",
                    "forbidden": ["bright_sitcom"],
                }
            ],
        },
    }
    shot = {
        "shot_id": "S01_T01",
        "scene_id": "S01",
        "dramatic_beat": "漆黑深水：模糊物体下沉",
        "dramatic_beat_en": "Pitch-black deep water: unreadable mass sinks",
        "subject": "污浊深水中的物体",
        "subject_en": "unreadable mass in turbid black water",
        "shot_size": "EWS",
        "duration_sec": 6,
        "emotion": {"primary": "dread", "intensity": 0.5},
        "camera": {
            "body": "ARRI Alexa 35 (virtual style anchor)",
            "lens_mm": 35,
            "angle": "eye_level",
            "movement": {
                "type": "Creep In",
                "zh": "缓推",
                "prompt_en": "creepy slow push in on sleeping figure, horror",
            },
        },
        "look": {
            "tone": "low_key",
            "contrast": "high",
            "key_light": "可选底光或硬侧光，深阴影",
            "color_temp": "冷青或病态绿可选",
            "grade_intent": "controlled blacks, protect facial detail",
        },
        "look_intent": "low_key high contrast, protect face, crush periphery",
    }
    out = write_prompts_offline(build_contract_brief(bible, shot))
    free = out["actor_free_prompt"]
    guided = out["director_guided_prompt"]
    assert "1. SUBJECT:" in free
    assert "2. CAMERA GEAR" in free
    assert "3. STORYLINE:" in free
    assert "4. AUDIO:" in free
    assert "Pitch-black" in free or "unreadable mass" in free
    assert "sleeping figure" not in guided.lower()
    assert "horror" not in guided.lower()
    assert "cold cyan" in guided.lower() or "contrast" in guided.lower()
    assert "key light" in guided.lower() or "Light and grade" in guided
    assert "No music" in free or "no music" in free.lower()
    assert "No subtitles" in free or "no subtitles" in free.lower()
    # self-contained context
    assert "Story world" in free or "Setting" in free or "deep" in free.lower()
    _assert_clean(free)
    _assert_clean(guided)
    _assert_clean(out["director_guided_prompt_zh"])
    assert "1. 指定主体" in out["actor_free_prompt_zh"]
    assert "不要音乐" in out["director_guided_prompt_zh"]
    assert "看懂用" not in out["actor_free_prompt_zh"]
    assert "非主投喂" not in out["director_guided_prompt_zh"]
    assert out["director_guided_prompt"].count("\n") >= 3
    assert out["director_guided_prompt_zh"].count("\n") >= 3


def test_submarine_ws_no_facial_performance_no_music():
    """Regression: env plate must not get dread face template + song title."""
    bible = {
        "meta": {"style_pack": "neo_noir"},
        "story": {"logline": "Ananke and Gao Yan dive toward a locked fault."},
        "dialogue": [
            {
                "scene_id": "S01",
                "lines": [{"character": "高岩", "text": "成本核算。", "delivery": "冷"}],
            }
        ],
        "look_bible": {
            "film_look": {
                "key": "low_key_neo_noir",
                "contrast": "high",
                "palette": ["cold_cyan_shadow"],
            },
            "scene_looks": [{"scene_id": "S01", "base_tone": "low_key"}],
        },
    }
    shot = {
        "shot_id": "S01_T02",
        "scene_id": "S01",
        "dramatic_beat": "萨克斯 What a Wonderful World 画外响起，推向小型勘探潜艇",
        "dramatic_beat_en": (
            "Saxophone What a Wonderful World rises off-screen; "
            "slow push toward a small exploration submarine"
        ),
        "subject": "深眸号小型勘探潜艇外轮廓与金属微动",
        "subject_en": "mini exploration sub silhouette with slow heavy metal micro-motion",
        "shot_size": "WS",
        "duration_sec": 5.7,
        "emotion": {"primary": "dread", "intensity": 0.5},
        "camera": {
            "lens_mm": 35,
            "movement": {"type": "Dutch Angle", "zh": "荷兰角", "prompt_en": "dutch angle"},
        },
        "look": {"tone": "low_key", "color_temp": "cold near-black"},
        "performance": {
            "physiology_zh": "瞳孔扩大，眼白暴露增多",
            "physiology_en": "pupils enlarge, more eye white",
            "micro_actions": ["重心后移"],
            "micro_actions_en": ["weight shifts back"],
        },
    }
    out = write_prompts_offline(build_contract_brief(bible, shot))
    guided = out["director_guided_prompt"]
    guided_zh = out["director_guided_prompt_zh"]
    assert "pupils" not in guided.lower()
    assert "瞳孔" not in guided_zh
    assert "Wonderful World" not in guided
    assert "萨克斯" not in guided_zh
    assert "No music" in guided or "no music" in guided.lower()
    assert "materials" in guided.lower() or "environment" in guided.lower()
    _assert_clean(guided)
    _assert_clean(guided_zh)


def test_subject_uses_image_ref_cards():
    """SUBJECT must be 图1/Image1 who-what, 图2 scene, not a bare noun phrase only."""
    bible = {
        "meta": {"style_pack": "neo_noir"},
        "story": {"logline": "Deep dive under pressure."},
        "scenes": [
            {
                "scene_id": "S01",
                "setting": "深眸号小型勘探潜艇舱内",
            }
        ],
        "characters": [{"id": "A", "name": "高岩"}],
        "asset_bible": {
            "characters": [
                {
                    "name": "高岩",
                    "consistency_anchors": ["dark coat", "tired eyes"],
                }
            ],
            "props": [],
            "sets": [
                {
                    "name": "深眸号小型勘探潜艇舱内",
                    "consistency_anchors": ["titanium walls", "holo consoles"],
                }
            ],
        },
        "dialogue": [],
        "look_bible": {"film_look": {"key": "low_key", "contrast": "high", "palette": []}},
    }
    # geometry on speaker — was the bad one-liner subject
    shot = {
        "shot_id": "S01_T15",
        "scene_id": "S01",
        "dramatic_beat": "几何随提问变形",
        "dramatic_beat_en": "geometry morphs with the question",
        "subject": "音箱显示屏上的变形几何",
        "subject_en": "morphing irregular geometry on speaker display",
        "shot_size": "INSERT",
        "duration_sec": 2.5,
        "emotion": {"primary": "revelation"},
        "camera": {"lens_mm": 50, "movement": {"type": "Static Locked-Off", "zh": "固定"}},
        "look": {"tone": "low_key"},
    }
    out = write_prompts_offline(build_contract_brief(bible, shot))
    en = out["director_guided_prompt"]
    zh = out["director_guided_prompt_zh"]
    # minimal cards only
    assert "Image 1 is" in en
    assert "Image 2 is" in en
    assert "图1是" in zh
    assert "图2是" in zh
    assert "who/what" not in en.lower()
    assert "是谁/是什么" not in zh
    assert "本镜画面焦点" not in zh
    assert "speaker" in en.lower() or "音箱" in zh or "示波" in zh
    _assert_clean(en)
    _assert_clean(zh)


def test_no_previous_prompt_reference():
    brief = build_contract_brief(
        {
            "meta": {"style_pack": "neo_noir"},
            "story": {"logline": "Test logline for context."},
            "dialogue": [],
            "look_bible": {"film_look": {"key": "low_key", "contrast": "high", "palette": []}},
        },
        {
            "shot_id": "S01_T04",
            "scene_id": "S01",
            "dramatic_beat_en": "Ananke log continues",
            "dramatic_beat": "日志继续",
            "subject_en": "oscilloscope speaker",
            "subject": "示波器音箱",
            "shot_size": "CU",
            "duration_sec": 30,
            "emotion": {"primary": "suspicion"},
            "camera": {"lens_mm": 50, "movement": {"type": "Static Locked-Off", "zh": "固定"}},
            "look": {"tone": "low_key"},
        },
        clip={"clip_id": "S01_T04_c02", "duration_sec": 30, "stitch": "continue"},
    )
    out = write_prompts_offline(brief)
    blob = out["director_guided_prompt"] + out["director_guided_prompt_zh"]
    assert "previous" not in blob.lower()
    assert "同上" not in blob
    assert "接上" not in blob
    # Soft-wrap may insert newlines; check keyword continuity without relying on one line
    guided = out["director_guided_prompt"].replace("\n", " ")
    assert "same subject identity" in guided


def test_write_final_offline_path(monkeypatch):
    monkeypatch.setenv("FILM_PIPELINE_DRY_RUN", "1")
    bible = {
        "meta": {"style_pack": "neo_noir"},
        "story": {"logline": "Meaning vs cost accounting."},
        "dialogue": [],
        "look_bible": {},
    }
    shot = {
        "shot_id": "S01_T14",
        "dramatic_beat_en": "Gao Yan challenges Ananke about meaning",
        "dramatic_beat": "高岩诘问意义",
        "subject_en": "Gao Yan eyes and geothermal numbers",
        "subject": "高岩眼睛与地热数字",
        "shot_size": "CU",
        "duration_sec": 15,
        "emotion": {"primary": "revelation", "intensity": 0.8},
        "camera": {
            "lens_mm": 50,
            "movement": {"type": "Dolly In", "zh": "推镜"},
        },
        "look": {"tone": "low_key"},
        "linked_dialogue": ["成本核算。"],
        "performance": {
            "physiology_en": "tight jaw, tired eyes",
            "micro_actions_en": ["taps book page"],
            "gaze_en": "on console numbers",
        },
    }
    bible["dialogue"] = [
        {
            "scene_id": "S01",
            "lines": [
                {"character": "高岩", "text": "成本核算。", "delivery": "冰冷"},
            ],
        }
    ]
    shot["scene_id"] = "S01"
    out = write_final_prompts_for_clip(bible, shot, prefer_llm=True)
    assert out["writer"] in {"offline_plain", "offline_fallback"}
    assert "1. SUBJECT:" in out["director_guided_prompt"]
    assert "Gao Yan" in out["director_guided_prompt"] or "challenges" in out["director_guided_prompt"]
    assert "成本核算" in out["director_guided_prompt"]
    assert "SFX only" in out["director_guided_prompt"] or "SFX" in out["director_guided_prompt"]
    _assert_clean(out["director_guided_prompt"])
    _assert_clean(out["director_guided_prompt_zh"])
