from __future__ import annotations

import re
from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore


def _chars_from_script(script: str) -> list[dict[str, str]]:
    names = re.findall(r"^[\u4e00-\u9fffA-Za-z]{1,8}$", script, flags=re.M)
    # Prefer explicit 人物 lines and ALLCAPS / bare name dialogue headers
    found: list[str] = []
    for line in script.splitlines():
        s = line.strip()
        if not s or s.startswith("---") or s.startswith("标题") or s.startswith("类型"):
            continue
        if "—" in s or "-" in s:
            name = re.split(r"[—\-]", s, maxsplit=1)[0].strip()
            if 1 <= len(name) <= 8 and name not in found:
                found.append(name)
        elif re.fullmatch(r"[\u4e00-\u9fffA-Za-z]{1,8}", s) and s not in found:
            # dialogue speaker headers like 林安 / 周宁
            if s not in {"雨敲窗", "第一场"}:
                found.append(s)
    if not found:
        found = ["A", "B"]
    chars = []
    for i, name in enumerate(found[:6]):
        chars.append(
            {
                "id": chr(ord("A") + i),
                "name": name,
                "want": "保护自己的位置与真相边界",
                "need": "面对关系中的诚实",
                "arc": "从克制到摊牌",
                "voice": "短句、克制、少形容词",
            }
        )
    return chars


def stub_dramaturg(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    script = bible.get("source_script", "")
    return {
        "story": {
            "logline": "一次被拆开的信封，逼出亲密关系里被推迟的真相。",
            "theme": "亲密中的知情权与被排除感",
            "acts": [
                {"name": "I", "summary": "发现异常 → 对质 → 关系裂口暴露"},
            ],
        },
        "characters": _chars_from_script(script),
        "scenes": [
            {
                "scene_id": "S01",
                "setting": "夜·公寓客厅·雨",
                "summary": "林安发现信封被动过，与周宁对质。",
                "dramatic_function": "揭示裂痕 / 关系反转起点",
                "emotion": {
                    "start": "calm",
                    "end": "oppression",
                    "peak": 0.85,
                    "primary": "suspicion",
                },
            }
        ],
    }


def stub_dialogue(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    return {
        "dialogue": [
            {
                "scene_id": "S01",
                "lines": [
                    {
                        "character": "周宁",
                        "text": "怎么还不睡？雨这么大。",
                        "function": "atmosphere",
                        "subtext": "用日常口吻靠近，试探气氛",
                        "delivery": "轻、带一点关心的笑",
                    },
                    {
                        "character": "林安",
                        "text": "信封被动过了。",
                        "function": "reveal",
                        "subtext": "不是闲聊，是下战书",
                        "delivery": "平、不抬头",
                    },
                    {
                        "character": "周宁",
                        "text": "什么信封？你不是说公司的文件吗。",
                        "function": "mislead",
                        "subtext": "装不知情，把话题推回安全区",
                        "delivery": "略快，笑意发紧",
                    },
                    {
                        "character": "林安",
                        "text": "我走之前封口是齐的。你早就看过了。",
                        "function": "reveal",
                        "subtext": "确认被排除在真相外",
                        "delivery": "抬眼，停在「早就」",
                    },
                    {
                        "character": "周宁",
                        "text": "有些事……不是现在这样问的。",
                        "function": "relationship",
                        "subtext": "承认有事，但拒绝对等知情",
                        "delivery": "笑容塌一半",
                    },
                    {
                        "character": "林安",
                        "text": "我不是在问。先把灯关了。",
                        "function": "advance",
                        "subtext": "用黑暗剥夺对方的表演空间",
                        "delivery": "更轻，更冷",
                    },
                ],
                "silence_beats_ms": [800, 1200, 1500],
            }
        ]
    }


def stub_director(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    scene_id = "S01"
    if bible.get("scenes"):
        scene_id = bible["scenes"][0]["scene_id"]
    shots = [
        {
            "shot_id": f"{scene_id}_T01",
            "scene_id": scene_id,
            "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
            "emotion": {"primary": "calm", "intensity": 0.3},
            "shot_size": "WS",
            "subject": "客厅、台灯、茶几上的信封",
            "whose_pov": "objective",
            "edit_intent": "建立空间与不安物件",
            "camera_draft": "static wide",
        },
        {
            "shot_id": f"{scene_id}_T02",
            "scene_id": scene_id,
            "dramatic_beat": "信封封口胶已翘起（信息）",
            "emotion": {"primary": "suspicion", "intensity": 0.55},
            "shot_size": "INSERT",
            "subject": "信封封口细节",
            "edit_intent": "用细节植入怀疑",
            "camera_draft": "macro insert",
        },
        {
            "shot_id": f"{scene_id}_T03",
            "scene_id": scene_id,
            "dramatic_beat": "林安不抬头说出信封被动过",
            "emotion": {"primary": "suspicion", "intensity": 0.65},
            "shot_size": "MCU",
            "subject": "林安上半身与茶几",
            "whose_pov": "林安",
            "edit_intent": "压住情绪，信息优先",
            "linked_dialogue": ["信封被动过了。"],
        },
        {
            "shot_id": f"{scene_id}_T04",
            "scene_id": scene_id,
            "dramatic_beat": "周宁心虚地反问",
            "emotion": {"primary": "suspicion", "intensity": 0.6},
            "shot_size": "MS",
            "subject": "周宁从厨房方向进入画框",
            "edit_intent": "正反打建立对峙",
            "linked_dialogue": ["什么信封？你不是说公司的文件吗。"],
        },
        {
            "shot_id": f"{scene_id}_T05",
            "scene_id": scene_id,
            "dramatic_beat": "林安抬眼确认：你早就看过了",
            "emotion": {"primary": "revelation", "intensity": 0.85},
            "shot_size": "CU",
            "subject": "林安眼睛与微表情",
            "edit_intent": "揭示落点，给反应空间",
            "linked_dialogue": ["你早就看过了。"],
        },
        {
            "shot_id": f"{scene_id}_T06",
            "scene_id": scene_id,
            "dramatic_beat": "周宁笑容塌陷",
            "emotion": {"primary": "oppression", "intensity": 0.8},
            "shot_size": "MCU",
            "subject": "周宁半边脸落在台灯里",
            "edit_intent": "反应镜头承载崩溃",
        },
        {
            "shot_id": f"{scene_id}_T07",
            "scene_id": scene_id,
            "dramatic_beat": "关灯前的最后通牒感",
            "emotion": {"primary": "oppression", "intensity": 0.9},
            "shot_size": "MS",
            "subject": "两人与即将熄灭的台灯",
            "edit_intent": "收场，导向黑暗",
            "linked_dialogue": ["先把灯关了。"],
        },
    ]
    return {"shots": shots}


def stub_look(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    pack = kb.get("style_pack") or {}
    film_look = pack.get("film_look") or {
        "key": "low_key_neo_noir",
        "contrast": "high",
        "palette": ["cold_cyan_shadow", "warm_practical_key"],
        "saturation": "controlled_low",
    }
    film_look = {
        **film_look,
        "motivation": "亲密空间被知情权撕裂：暖实用光 vs 冷阴影",
    }
    scene_looks = []
    for scene in bible.get("scenes") or [{"scene_id": "S01"}]:
        primary = (scene.get("emotion") or {}).get("primary") or scene.get("emotion", {}).get(
            "end", "suspicion"
        )
        look_rules = KnowledgeStore().emotion_look(str(primary))
        scene_looks.append(
            {
                "scene_id": scene["scene_id"],
                "base_tone": (look_rules.get("tone") or ["low_key"])[0],
                "contrast": (look_rules.get("contrast") or ["high"])[0],
                "color": ", ".join(look_rules.get("palette") or film_look.get("palette", [])),
                "emotion_arc_in_tone": "中灰日常 → 低调高反差对质",
                "forbidden": look_rules.get("avoid") or pack.get("forbidden") or [],
            }
        )
    intents = []
    for shot in bible.get("shots") or []:
        if shot.get("emotion", {}).get("primary") in {"revelation", "oppression"}:
            intents.append(
                {
                    "shot_id": shot["shot_id"],
                    "look_intent": "low_key high contrast, protect face, crush periphery",
                    "motivation": "真相落地时空间变硬，人物仍可读",
                }
            )
    return {"look_bible": {"film_look": film_look, "scene_looks": scene_looks}, "shot_look_intents": intents}


def stub_cinematography(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    store = KnowledgeStore()
    pack = kb.get("style_pack") or {}
    habits = pack.get("camera_habits") or {}
    prefer_lenses = habits.get("prefer_lenses_mm") or [40, 50]
    scene_look_map = {
        s["scene_id"]: s for s in (bible.get("look_bible") or {}).get("scene_looks") or []
    }
    patches = []
    for shot in bible.get("shots") or []:
        emo = (shot.get("emotion") or {}).get("primary", "suspicion")
        cam_rules = store.emotion_camera(str(emo))
        look_rules = store.emotion_look(str(emo))
        scene_look = scene_look_map.get(shot.get("scene_id", ""), {})
        # Prefer Excel-imported catalog move
        catalog_move = store.pick_move_for_emotion(str(emo))
        if catalog_move:
            move = catalog_move.get("en") or catalog_move.get("id") or "static hold"
            move_prompt = catalog_move.get("prompt_en") or move
            move_id = catalog_move.get("id")
            move_zh = catalog_move.get("zh")
        else:
            move = (cam_rules.get("preferred_moves") or ["static_hold"])[0]
            move_prompt = str(move)
            move_id = None
            move_zh = None
        avoid = set(habits.get("avoid_moves") or [])
        if move in avoid and habits.get("prefer_moves"):
            move = habits["prefer_moves"][0]
            move_prompt = move
        angle = (cam_rules.get("preferred_angles") or ["eye_level"])[0]
        lenses = cam_rules.get("lens_mm") or prefer_lenses
        lens = lenses[0] if lenses else 40
        if prefer_lenses and lens not in prefer_lenses:
            lens = prefer_lenses[0]
        tone = scene_look.get("base_tone") or (look_rules.get("tone") or ["low_key"])[0]
        speed = "very_slow"
        ml = str(move).lower()
        if any(k in ml for k in ("static", "locked", "hold")):
            speed = "none"
        elif any(k in ml for k in ("whip", "crash", "snap")):
            speed = "fast"
        # Lighting from director performance plan / emotion lighting table
        perf = shot.get("performance") or {}
        light_plan = (perf.get("lighting_plan") or {}) if isinstance(perf, dict) else {}
        light_table = light_plan.get("look_table") or {}
        key_light = (
            light_plan.get("key")
            or light_table.get("sources", [None])[0]
            or "soft side key from practical lamp"
        )
        if isinstance(key_light, list):
            key_light = key_light[0] if key_light else "soft side key"
        color_temp = (
            light_plan.get("color")
            or light_table.get("color_temp")
            or scene_look.get("color")
            or "cool fill / warm practical"
        )
        fill_ratio = "1:8" if emo in {"oppression", "revelation", "dread"} else "1:4"
        if "half" in str(light_plan.get("ratio", "")).lower() or "high" in str(
            light_plan.get("ratio", "")
        ).lower():
            fill_ratio = "1:8"
        patches.append(
            {
                "shot_id": shot["shot_id"],
                "duration_sec": 3.5 if shot.get("shot_size") != "INSERT" else 2.0,
                "camera": {
                    "body": "ARRI Alexa 35 (virtual style anchor)",
                    "lens_mm": lens,
                    "t_stop": "T2.0",
                    "shot_size": shot.get("shot_size", "MS"),
                    "angle": angle,
                    "height": "chest" if shot.get("shot_size") in {"MCU", "CU"} else "eye",
                    "movement": {
                        "type": move,
                        "catalog_id": move_id,
                        "zh": move_zh,
                        "prompt_en": move_prompt,
                        "speed": speed,
                        "motivation": (
                            f"服务 beat「{shot.get('dramatic_beat', '')}」与情绪 {emo}："
                            f"知识库运镜「{move_zh or move}」/ {angle}，配合表演与灯光"
                        ),
                    },
                    "composition": "rule_of_thirds, protect eyeline",
                    "focus": "eyes sharp" if shot.get("shot_size") in {"MCU", "CU"} else "subject sharp",
                },
                "look": {
                    "tone": tone,
                    "contrast": scene_look.get("contrast")
                    or (look_rules.get("contrast") or ["high"])[0],
                    "key_light": key_light,
                    "fill_ratio": fill_ratio,
                    "color_temp": color_temp,
                    "grade_intent": "controlled blacks, protect facial detail",
                    "motivation": (
                        f"影调跟随情绪 {emo}；"
                        f"{light_plan.get('motivation') or light_table.get('face') or '服务情节氛围'}；"
                        f"场次 base_tone={tone}"
                    ),
                },
            }
        )
    return {"shot_patches": patches}


def stub_asset(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    """
    Casting / three-view prompts per 三视图.skill:
    left face close-up + right front/back/side with black face censor boxes.
    """
    from film_pipeline.runtime.three_view import (
        build_character_sheet_prompt,
        build_prop_sheet_prompt,
        build_set_sheet_prompt,
    )

    style = (bible.get("meta") or {}).get("style_pack", "neo_noir")
    pack = dict((kb or {}).get("style_pack") or {})
    pack.setdefault("id", style)

    chars = []
    for c in bible.get("characters") or []:
        name = c.get("name") or c.get("id") or "Character"
        aid = f"char_{(c.get('id') or name).lower()}"
        built = build_character_sheet_prompt(c, style_pack=pack)
        vars_ = built.get("template_vars") or {}
        chars.append(
            {
                "asset_id": aid,
                "name": name,
                "type": "character",
                "role": c.get("want") or "principal",
                "consistency_anchors": [
                    f"identity: {name}",
                    f"voice/energy: {c.get('voice') or 'restrained'}",
                    vars_.get("HAIR_STYLE_AND_COLOR", "consistent hair"),
                    (vars_.get("CLOTHING_DESCRIPTION") or "consistent wardrobe")[:100],
                    "same identity left close-up and right full-body views",
                ],
                "views": built.get("views")
                or ["face_closeup_left", "full_front", "full_back", "full_side"],
                "sheet_prompt": built["sheet_prompt"],
                "negative_prompt": "",
                "sheet_prompt_zh_summary": built.get("sheet_prompt_zh_summary"),
                "ethnicity": built.get("ethnicity"),
                "image_size_hint": built.get("image_size_hint"),
                "image_refs": [],
                "style_notes": (
                    f"Template: 三视图 左50%大脸+人种; style={style}; image_refs swappable."
                ),
            }
        )

    env_prop = build_prop_sheet_prompt(
        "kraft paper envelope with slightly lifted glue seal",
        ["kraft paper", "lifted seal", "tea-table scale"],
    )
    props = [
        {
            "asset_id": "prop_envelope",
            "name": "牛皮纸信封",
            "type": "prop",
            "role": "plot object",
            "consistency_anchors": ["kraft paper", "lifted glue seal", "tea-table scale"],
            "views": ["top", "side", "three_quarter"],
            "sheet_prompt": env_prop["sheet_prompt"],
            "negative_prompt": "",
            "sheet_prompt_zh_summary": env_prop.get("sheet_prompt_zh_summary"),
            "image_refs": [],
        }
    ]

    sets = []
    for sc in bible.get("scenes") or []:
        sid = sc.get("scene_id") or "S01"
        setting = sc.get("setting") or "interior"
        built = build_set_sheet_prompt(
            setting, [setting, "fixed furniture layout", "practical lamp"]
        )
        sets.append(
            {
                "asset_id": f"set_{str(sid).lower()}",
                "name": setting,
                "type": "set",
                "role": sc.get("dramatic_function") or "location",
                "consistency_anchors": [
                    setting,
                    "fixed furniture layout",
                    "practical lamp placement",
                ],
                "views": ["master_wide", "left", "right", "detail_corner"],
                "sheet_prompt": built["sheet_prompt"],
                "negative_prompt": "",
                "sheet_prompt_zh_summary": built.get("sheet_prompt_zh_summary"),
                "image_refs": [],
            }
        )
    if not sets:
        built = build_set_sheet_prompt("apartment living room night rain")
        sets.append(
            {
                "asset_id": "set_apartment_living",
                "name": "公寓客厅",
                "type": "set",
                "consistency_anchors": ["sofa", "tea table", "window rain"],
                "views": ["master_wide", "left", "right"],
                "sheet_prompt": built["sheet_prompt"],
                "negative_prompt": "",
                "sheet_prompt_zh_summary": built.get("sheet_prompt_zh_summary"),
                "image_refs": [],
            }
        )

    return {
        "asset_bible": {
            "characters": chars,
            "props": props,
            "sets": sets,
            "notes": (
                "Character sheets follow 三视图.skill: EN primary; "
                "zh_summary for reading; image_refs empty until user generates."
            ),
        }
    }


def stub_timing(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    from film_pipeline.runtime.timing import apply_timing_plan

    profile = (bible.get("meta") or {}).get("model_profile")
    apply_timing_plan(bible, model_profile=profile)
    return {
        "timing_plan": bible.get("timing_plan") or {},
        "shot_timings": [
            {
                "shot_id": s.get("shot_id"),
                "duration_sec": s.get("duration_sec"),
                "timing": s.get("timing"),
                "generation_clips": s.get("generation_clips") or [],
            }
            for s in bible.get("shots") or []
        ],
    }


def stub_generator(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    """Final stage: compile all FilmBible decisions into model-ready prompts."""
    from film_pipeline.runtime.prompt_compiler import compile_generation_jobs

    style_pack = kb.get("style_pack") if isinstance(kb, dict) else None
    return {"generation_jobs": compile_generation_jobs(bible, style_pack=style_pack)}


def stub_critic(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    shots = bible.get("shots") or []
    if not shots:
        failures.append(
            {
                "type": "missing_shots",
                "reason": "没有镜头，需要导演分镜",
                "reroute_to": "director",
            }
        )
    if not bible.get("look_bible"):
        failures.append(
            {
                "type": "missing_look",
                "reason": "缺少 look_bible 影调",
                "reroute_to": "look",
            }
        )
    if not bible.get("timing_plan"):
        failures.append(
            {
                "type": "missing_timing",
                "reason": "缺少 timing_plan（台词/运镜时长未核算）",
                "reroute_to": "timing",
            }
        )
    for shot in shots:
        cam = shot.get("camera") or {}
        mov = cam.get("movement") or {}
        look = shot.get("look") or {}
        if not mov.get("motivation"):
            failures.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "type": "movement_motivation",
                    "reason": "运镜缺少 motivation",
                    "reroute_to": "cinematography",
                }
            )
        if not look.get("motivation"):
            failures.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "type": "look_motivation",
                    "reason": "影调缺少 motivation",
                    "reroute_to": "cinematography",
                }
            )
        if not shot.get("duration_sec"):
            failures.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "type": "missing_duration",
                    "reason": "缺少 duration_sec",
                    "reroute_to": "timing",
                }
            )
        max_clip = (shot.get("timing") or {}).get("max_clip_sec") or (
            (bible.get("timing_plan") or {}).get("max_clip_sec")
        )
        for clip in shot.get("generation_clips") or []:
            if max_clip and float(clip.get("duration_sec") or 0) > float(max_clip) + 1e-6:
                failures.append(
                    {
                        "shot_id": shot.get("shot_id"),
                        "type": "clip_over_cap",
                        "reason": f"clip {clip.get('clip_id')} 超过模型上限 {max_clip}s",
                        "reroute_to": "timing",
                    }
                )
    # jobs may be per-clip now
    job_keys = set()
    for j in bible.get("generation_jobs") or []:
        job_keys.add(j.get("clip_id") or j.get("shot_id"))
    for shot in shots:
        clips = shot.get("generation_clips") or [{"clip_id": shot.get("shot_id")}]
        for clip in clips:
            cid = clip.get("clip_id") if isinstance(clip, dict) else shot.get("shot_id")
            if cid not in job_keys and shot.get("shot_id") not in job_keys:
                failures.append(
                    {
                        "shot_id": shot.get("shot_id"),
                        "type": "missing_generation_job",
                        "reason": f"缺少生成任务 clip={cid}",
                        "reroute_to": "generator",
                    }
                )
                break
    score = max(0.0, 1.0 - 0.08 * len(failures))
    return {
        "review": {
            "pass": len(failures) == 0,
            "score": round(score, 2),
            "summary": "结构完整" if not failures else f"发现 {len(failures)} 个问题",
            "failures": failures,
        }
    }


STUBS = {
    "dramaturg": stub_dramaturg,
    "dialogue": stub_dialogue,
    "director": stub_director,
    "look": stub_look,
    "cinematography": stub_cinematography,
    "timing": stub_timing,
    "generator": stub_generator,
    "critic": stub_critic,
    "asset": stub_asset,
}
