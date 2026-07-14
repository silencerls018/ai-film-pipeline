from __future__ import annotations

import re
from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore


def _script_is_deep_dive(script: str) -> bool:
    """User submarine / Ananke / Gao Yan script (desktop case)."""
    s = script or ""
    return ("Ananke" in s or "Anake" in s) and (
        "高岩" in s or "深眸" in s or "热液" in s or "深水" in s
    )


def _deep_dive_shots(scene_id: str = "S01") -> list[dict[str, Any]]:
    """Load director shots from offline case pack (same as scripts/run_deep_dive_case)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "run_deep_dive_case.py"
    spec = importlib.util.spec_from_file_location("run_deep_dive_case", path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    shots = mod._shots()
    for sh in shots:
        sh["scene_id"] = scene_id
        sid = sh.get("shot_id") or ""
        # rewrite shot_id prefix to match scene
        if "_T" in sid:
            sh["shot_id"] = f"{scene_id}_T{sid.split('_T', 1)[1]}"
    return shots


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
    if _script_is_deep_dive(script):
        return {
            "story": {
                "logline": (
                    "漆黑深水中，AI 日志 Ananke 与高工高岩驶向第一现实闭锁断层；"
                    "董事会的成本核算撞上人类对意义的诘问。"
                ),
                "theme": "绝对有序机器 vs 人类寻找意义 / 公司风险核算 vs 敬畏",
                "acts": [
                    {
                        "name": "I",
                        "summary": "深水建立 → 舱内日常 → Ananke 日志 → 高岩哲学对峙",
                    }
                ],
            },
            "characters": [
                {
                    "id": "A",
                    "name": "高岩",
                    "want": "带船员活过热液走廊",
                    "need": "拒绝纯成本账簿道德",
                    "arc": "从实验室冷声到公开哲学诘问",
                    "voice": "平稳、冰冷、实验室腔",
                },
                {
                    "id": "B",
                    "name": "Ananke",
                    "want": "07 号核心准时入账",
                    "need": "维持系统秩序的礼貌嗓音",
                    "arc": "平直日志 → 成本核算话术",
                    "voice": "无起伏、机械、儒雅磁性电波音",
                },
                {
                    "id": "C",
                    "name": "技术员A",
                    "want": "熬过 314 天倒计时",
                    "need": "想家",
                    "arc": "沉默忙活",
                    "voice": "无对白",
                },
                {
                    "id": "D",
                    "name": "技术员B",
                    "want": "校准液压应急总线",
                    "need": "把活干完",
                    "arc": "沉默忙活",
                    "voice": "无对白",
                },
            ],
            "scenes": [
                {
                    "scene_id": "S01",
                    "setting": "绝对深度·污浊深水 → 深眸号小型勘探潜艇舱内",
                    "summary": "下潜建立、舱内三层光、Ananke 日志、人间痕迹、高岩 vs Ananke",
                    "dramatic_function": "建立世界观 + 主题种子（秩序 vs 意义）",
                    "emotion": {
                        "start": "dread",
                        "end": "revelation",
                        "peak": 0.85,
                        "primary": "dread",
                    },
                }
            ],
        }
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
    script = bible.get("source_script") or ""
    if _script_is_deep_dive(script):
        shots = _deep_dive_shots(scene_id)
        if shots:
            # Director output is dramatic layer; camera/look filled by later stages.
            dramatic_only = []
            for sh in shots:
                item: dict[str, Any] = {
                    "shot_id": sh["shot_id"],
                    "scene_id": sh.get("scene_id") or scene_id,
                    "dramatic_beat": sh.get("dramatic_beat") or "",
                    "dramatic_beat_en": sh.get("dramatic_beat_en") or "",
                    "emotion": sh.get("emotion") or {"primary": "suspicion"},
                    "shot_size": sh.get("shot_size") or "MS",
                    "subject": sh.get("subject") or "",
                    "subject_en": sh.get("subject_en") or "",
                    "edit_intent": sh.get("edit_intent") or "cover",
                }
                if sh.get("whose_pov"):
                    item["whose_pov"] = sh["whose_pov"]
                if sh.get("linked_dialogue"):
                    item["linked_dialogue"] = list(sh["linked_dialogue"])
                cam_type = (sh.get("camera") or {}).get("movement", {}).get("type")
                if cam_type:
                    item["camera_draft"] = cam_type
                dramatic_only.append(item)
            return {"shots": dramatic_only}
    shots = [
        {
            "shot_id": f"{scene_id}_T01",
            "scene_id": scene_id,
            "dramatic_beat": "雨夜客厅建立：信封在茶几中央",
            "dramatic_beat_en": (
                "Rainy-night living room establish: sealed envelope centered on the coffee table"
            ),
            "emotion": {"primary": "calm", "intensity": 0.3},
            "shot_size": "WS",
            "subject": "客厅、台灯、茶几上的信封",
            "subject_en": "living room, table lamp, envelope on the coffee table",
            "whose_pov": "objective",
            "edit_intent": "建立空间与不安物件",
            "camera_draft": "static wide",
        },
        {
            "shot_id": f"{scene_id}_T02",
            "scene_id": scene_id,
            "dramatic_beat": "信封封口胶已翘起（信息）",
            "dramatic_beat_en": (
                "Insert detail: envelope seal adhesive already lifted (information plant)"
            ),
            "emotion": {"primary": "suspicion", "intensity": 0.55},
            "shot_size": "INSERT",
            "subject": "信封封口细节",
            "subject_en": "close detail of the envelope seal",
            "edit_intent": "用细节植入怀疑",
            "camera_draft": "macro insert",
        },
        {
            "shot_id": f"{scene_id}_T03",
            "scene_id": scene_id,
            "dramatic_beat": "林安不抬头说出信封被动过",
            "dramatic_beat_en": (
                "Lin An, without looking up, states the envelope has been tampered with"
            ),
            "emotion": {"primary": "suspicion", "intensity": 0.65},
            "shot_size": "MCU",
            "subject": "林安上半身与茶几",
            "subject_en": "Lin An upper body and the coffee table",
            "whose_pov": "林安",
            "edit_intent": "压住情绪，信息优先",
            "linked_dialogue": ["信封被动过了。"],
        },
        {
            "shot_id": f"{scene_id}_T04",
            "scene_id": scene_id,
            "dramatic_beat": "周宁心虚地反问",
            "dramatic_beat_en": "Zhou Ning asks back, defensive and uneasy",
            "emotion": {"primary": "suspicion", "intensity": 0.6},
            "shot_size": "MS",
            "subject": "周宁从厨房方向进入画框",
            "subject_en": "Zhou Ning entering frame from the kitchen direction",
            "edit_intent": "正反打建立对峙",
            "linked_dialogue": ["什么信封？你不是说公司的文件吗。"],
        },
        {
            "shot_id": f"{scene_id}_T05",
            "scene_id": scene_id,
            "dramatic_beat": "林安抬眼确认：你早就看过了",
            "dramatic_beat_en": "Lin An looks up and confirms: you already read it",
            "emotion": {"primary": "revelation", "intensity": 0.85},
            "shot_size": "CU",
            "subject": "林安眼睛与微表情",
            "subject_en": "Lin An's eyes and micro-expressions",
            "edit_intent": "揭示落点，给反应空间",
            "linked_dialogue": ["你早就看过了。"],
        },
        {
            "shot_id": f"{scene_id}_T06",
            "scene_id": scene_id,
            "dramatic_beat": "周宁笑容塌陷",
            "dramatic_beat_en": "Zhou Ning's smile collapses",
            "emotion": {"primary": "oppression", "intensity": 0.8},
            "shot_size": "MCU",
            "subject": "周宁半边脸落在台灯里",
            "subject_en": "half of Zhou Ning's face caught in the lamp light",
            "edit_intent": "反应镜头承载崩溃",
        },
        {
            "shot_id": f"{scene_id}_T07",
            "scene_id": scene_id,
            "dramatic_beat": "关灯前的最后通牒感",
            "dramatic_beat_en": "Final ultimatum beat before the lamp goes dark",
            "emotion": {"primary": "oppression", "intensity": 0.9},
            "shot_size": "MS",
            "subject": "两人与即将熄灭的台灯",
            "subject_en": "both characters and the lamp about to go out",
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
    from film_pipeline.runtime.shot_locale import is_environment_or_object_shot

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
        env_plate = is_environment_or_object_shot(shot)
        size = str(shot.get("shot_size") or "MS").upper()

        # Strategy matrix + catalog: subject-aware pick (INSERT/env never get face-acting moves)
        subject_class = store.infer_subject_class(
            size,
            str(shot.get("subject") or shot.get("subject_en") or ""),
            env_or_object=env_plate,
        )
        catalog_move = store.pick_move_for_emotion(
            str(emo),
            shot_size=size,
            subject_class=subject_class,
            env_or_object=env_plate,
        )
        if catalog_move and not env_plate and size not in {"EWS", "WS", "INSERT"}:
            move = catalog_move.get("en") or catalog_move.get("id") or "static hold"
            move_prompt = catalog_move.get("prompt_en") or move
            move_id = catalog_move.get("id")
            move_zh = catalog_move.get("zh")
        elif catalog_move and (env_plate or size in {"EWS", "WS", "INSERT"}):
            # Still use strategy-filtered catalog when safe (static/creep/push)
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
            # Prefer first non-static habit move
            for pm in habits.get("prefer_moves") or []:
                if not any(t in str(pm).lower() for t in ("static", "locked")):
                    move = pm
                    move_prompt = str(pm)
                    break
            else:
                move = habits["prefer_moves"][0]
                move_prompt = move

        # House style: angled camera (no pure eye_level default)
        habit_angles = habits.get("prefer_angles") or []
        angle, height = store.pick_angle_for_emotion(
            str(emo),
            shot_size=size,
            subject_class=subject_class,
            env_or_object=env_plate,
        )
        if habit_angles and habits.get("avoid_pure_eye_level", True):
            angle = str(habit_angles[0])
            if "low" in angle:
                height = "hip_to_chest" if "slight" in angle else "knee_to_hip"
            elif "high" in angle:
                height = "above_eye"
            elif "dutch" in angle:
                height = "eye_to_chest_canted"

        ml = f"{move} {move_prompt}".lower()
        bad = any(k in ml for k in ("villain", "horror", "sleeping", "crash", "whip"))
        # Dutch is allowed with motivation (suspicion/oppression/dread)
        if "dutch" in ml and emo not in {"dread", "suspicion", "oppression"}:
            bad = True
        beat_blob = f"{shot.get('dramatic_beat_en') or ''} {shot.get('dramatic_beat') or ''}"
        wants_push = "push" in beat_blob.lower() or "推" in beat_blob
        if bad:
            if size == "INSERT" or env_plate:
                move, move_zh, move_prompt = (
                    "Slow Push In",
                    "缓推",
                    "very slow push-in on subject detail",
                )
            elif wants_push:
                move, move_zh, move_prompt = (
                    "Creep In",
                    "缓推",
                    "very slow motivated push-in",
                )
            else:
                move, move_zh, move_prompt = (
                    "Micro Drift",
                    "微漂",
                    "subtle floating micro drift, living camera",
                )
            move_id = None

        # Replace pure static with gentle motion unless brief forces locked
        ml2 = f"{move} {move_prompt}".lower()
        if any(k in ml2 for k in ("static", "locked-off", "locked off")) and not any(
            k in beat_blob.lower() for k in ("locked", "static", "固定", "锁")
        ):
            if size == "INSERT":
                move, move_zh, move_prompt = (
                    "Slow Push In",
                    "缓推",
                    "very slow push-in on the object detail",
                )
            elif env_plate or size in {"EWS", "WS"}:
                move, move_zh, move_prompt = (
                    "Slow Pan",
                    "慢摇",
                    "slow pan across the environment, cinematic",
                )
            else:
                move, move_zh, move_prompt = (
                    "Micro Drift",
                    "微漂",
                    "subtle floating micro drift, living camera",
                )
            move_id = None

        lenses = cam_rules.get("lens_mm") or prefer_lenses
        lens = lenses[0] if lenses else 40
        if prefer_lenses and lens not in prefer_lenses:
            lens = prefer_lenses[0]
        if env_plate and size in {"EWS", "WS"}:
            lens = 35

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
        grade = (
            "controlled blacks, material detail"
            if env_plate
            else "controlled blacks, protect facial detail"
        )
        focus = (
            "subject sharp"
            if env_plate or size not in {"MCU", "CU", "ECU"}
            else "eyes sharp"
        )
        composition = (
            "centered or rule-of-thirds on subject mass, no forced eyeline"
            if env_plate
            else "rule_of_thirds, protect eyeline"
        )
        motivation = (
            f"环境/建立镜：带角度机位({angle})，慢速运动服务 beat，不炫技；情绪 {emo}"
            if env_plate
            else (
                f"服务 beat「{shot.get('dramatic_beat', '')}」与情绪 {emo}："
                f"运镜「{move_zh or move}」+ 角度「{angle}」(非纯平视默认)，配合表演与灯光"
            )
        )
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
                    "height": height
                    if height
                    else (
                        "chest"
                        if shot.get("shot_size") in {"MCU", "CU"} and not env_plate
                        else "above_eye"
                    ),
                    "movement": {
                        "type": move,
                        "catalog_id": move_id,
                        "zh": move_zh,
                        "prompt_en": move_prompt,
                        "speed": speed,
                        "motivation": motivation,
                    },
                    "composition": composition,
                    "focus": focus,
                },
                "look": {
                    "tone": tone,
                    "contrast": scene_look.get("contrast")
                    or (look_rules.get("contrast") or ["high"])[0],
                    "key_light": key_light,
                    "fill_ratio": fill_ratio,
                    "color_temp": color_temp,
                    "grade_intent": grade,
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
    """Prompt Writer Agent offline path (dedicated agent, not other stages)."""
    from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent

    return run_prompt_writer_agent(bible)


def stub_critic(bible: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic critic: structure + **dialogue coverage vs source script**.
    Must fail if spoken lines are missing from dialogue[] or generation_jobs.
    """
    from film_pipeline.runtime.critic_checks import run_critic_checks

    review = run_critic_checks(bible)
    failures: list[dict[str, Any]] = list(review.get("failures") or [])
    shots = bible.get("shots") or []

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

    # Jobs may be generation packages (cover many shot_ids) or per-clip
    job_keys = set()
    covered_shots = set()
    for j in bible.get("generation_jobs") or []:
        job_keys.add(j.get("clip_id") or j.get("package_id") or j.get("shot_id"))
        for sid in j.get("shot_ids") or []:
            covered_shots.add(sid)
        if j.get("shot_id"):
            covered_shots.add(j.get("shot_id"))
        for beat in j.get("beats") or []:
            if beat.get("shot_id"):
                covered_shots.add(beat.get("shot_id"))
    for shot in shots:
        sid = shot.get("shot_id")
        if sid in covered_shots:
            continue
        clips = shot.get("generation_clips") or [{"clip_id": sid}]
        ok = False
        for clip in clips:
            cid = clip.get("clip_id") if isinstance(clip, dict) else sid
            if cid in job_keys or sid in job_keys:
                ok = True
                break
        if not ok:
            failures.append(
                {
                    "shot_id": sid,
                    "type": "missing_generation_job",
                    "reason": f"镜头 {sid} 未包含在任何生成段/提示词 job 中",
                    "reroute_to": "generator",
                }
            )

    # schema requires type/reason/reroute_to; errors fail pass, warns do not
    clean: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for f in failures:
        item = {
            "type": str(f.get("type") or "check_failed"),
            "reason": str(f.get("reason") or f.get("message") or "质检失败"),
            "reroute_to": str(f.get("reroute_to") or "generator"),
        }
        if f.get("shot_id"):
            item["shot_id"] = f["shot_id"]
        clean.append(item)
        if f.get("severity") != "warn":
            errors.append(item)
    score = max(0.0, 1.0 - 0.12 * len(errors))
    reroute = errors[0]["reroute_to"] if errors else None
    return {
        "review": {
            "pass": len(errors) == 0,
            "score": round(score, 2),
            "summary": (
                "结构与对白覆盖通过"
                if not errors
                else f"发现 {len(errors)} 个问题（含对白覆盖）"
            ),
            "failures": clean,
            "reroute_to": reroute,
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
