"""Director-owned performance + dual prompt builders."""

from __future__ import annotations

from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore

_EMOTION_ZH = {
    "calm": "平静",
    "suspicion": "怀疑/紧绷",
    "oppression": "压迫",
    "revelation": "揭示/震惊",
    "intimacy": "亲密",
    "grief": "悲伤",
    "dread": "恐惧/惊悚",
}


def _intensity_bucket(intensity: float | None) -> str:
    if intensity is None:
        return "mid"
    try:
        v = float(intensity)
    except (TypeError, ValueError):
        return "mid"
    if v < 0.4:
        return "low"
    if v > 0.75:
        return "high"
    return "mid"


def load_performance_kb(store: KnowledgeStore | None = None) -> dict[str, Any]:
    store = store or KnowledgeStore()
    return {
        "physics": store.try_load_ai_json("director/performance_physics.json") or {},
        "trinity": store.try_load_ai_json("director/shot_performance_lighting.json") or {},
        "lighting": store.try_load_ai_json("look/lighting_for_emotion.json") or {},
        "dual": store.try_load_ai_json("director/dual_prompt_policy.json") or {},
    }


def resolve_emotion(shot: dict[str, Any], store: KnowledgeStore | None = None) -> str:
    store = store or KnowledgeStore()
    raw = (shot.get("emotion") or {}).get("primary") or "suspicion"
    return store.normalize_emotion(str(raw))


def build_shot_performance(
    shot: dict[str, Any],
    store: KnowledgeStore | None = None,
) -> dict[str, Any]:
    """Attach director performance package for one shot (FilmBible field)."""
    store = store or KnowledgeStore()
    kb = load_performance_kb(store)
    emo = resolve_emotion(shot, store)
    phys_root = (kb.get("physics") or {}).get("by_emotion") or {}
    phys = phys_root.get(emo) or phys_root.get("suspicion") or {}
    trinity = ((kb.get("trinity") or {}).get("by_emotion") or {}).get(emo) or {}
    light = ((kb.get("lighting") or {}).get("by_emotion") or {}).get(emo) or {}
    intensity = (shot.get("emotion") or {}).get("intensity")
    bucket = _intensity_bucket(intensity if isinstance(intensity, (int, float)) else None)
    scale = (phys.get("intensity_scale") or {}).get(bucket, bucket)

    scale_en = (phys.get("intensity_scale_en") or {}).get(bucket, bucket)
    return {
        "emotion": emo,
        "intensity_bucket": bucket,
        "intensity_label_zh": scale,
        "intensity_label_en": scale_en,
        "actor_free_tags": list(phys.get("actor_free_tags") or [emo]),
        "physiology_zh": phys.get("physiology_zh") or "",
        "physiology_en": phys.get("physiology_en") or "",
        "micro_actions": list(phys.get("micro_actions") or []),
        "micro_actions_en": list(phys.get("micro_actions_en") or []),
        "gaze": phys.get("gaze") or "",
        "gaze_en": phys.get("gaze_en") or "",
        "voice_hint": phys.get("voice_hint") or "",
        "voice_hint_en": phys.get("voice_hint_en") or "",
        "shot_bias": list(trinity.get("shot_bias") or []),
        "move_bias": list(trinity.get("move_bias") or []),
        "lighting_plan": {
            **(trinity.get("lighting") or {}),
            "look_table": light,
        },
        "director_note": (
            f"情绪{_EMOTION_ZH.get(emo, emo)}/{scale}：表演生理 + 景别偏向{trinity.get('shot_bias')} + "
            f"运镜偏向{trinity.get('move_bias')} + 灯光服务于「"
            f"{(trinity.get('lighting') or {}).get('motivation', '情绪氛围')}」"
        ),
        "director_note_en": (
            f"Emotion {emo}/{scale_en}: performance + shot bias {trinity.get('shot_bias')} + "
            f"move bias {trinity.get('move_bias')} + light for "
            f"「{(trinity.get('lighting') or {}).get('motivation', 'mood')}」"
        ),
    }


def enrich_shots_with_performance(bible: dict[str, Any]) -> dict[str, Any]:
    store = KnowledgeStore()
    for shot in bible.get("shots") or []:
        shot["performance"] = build_shot_performance(shot, store)
    return bible


_SHOT_SIZE_ZH = {
    "EWS": "大远景",
    "WS": "全景/远景",
    "FS": "全身景",
    "MS": "中景",
    "MCU": "中近景",
    "CU": "特写",
    "ECU": "大特写",
    "INSERT": "插入镜头",
}

_ANGLE_ZH = {
    "eye_level": "平视",
    "eye_level_tight": "平视偏紧",
    "slight_low": "略仰",
    "slight_high": "略俯",
    "low": "低机位仰拍",
    "high": "高机位俯拍",
    "dutch": "荷兰角（倾斜）",
    "dutch_rare": "荷兰角（慎用）",
}

_TAG_ZH = {
    "calm": "平静",
    "composed": "克制沉着",
    "neutral breath": "呼吸平稳",
    "soft presence": "柔和存在感",
    "suspicious": "怀疑",
    "tense": "紧绷",
    "wary": "戒备",
    "alert": "警觉",
    "oppressed": "受压",
    "cornered": "被逼到绝境",
    "heavy pressure": "沉重压迫",
    "no exit": "无路可退",
    "shock": "震惊",
    "realization": "恍然大悟",
    "stunned": "呆住",
    "truth lands": "真相落地",
    "intimate": "亲密",
    "tender": "温柔",
    "close": "靠近",
    "vulnerable soft": "柔软脆弱",
    "grief": "悲伤",
    "sorrow": "哀伤",
    "heartbroken": "心碎",
    "heavy loss": "沉重失落",
    "dread": "恐惧预感",
    "fear": "害怕",
    "terror": "惊恐",
    "freeze": "僵住",
}


def _shot_size_zh(code: str | None) -> str:
    c = code or "MS"
    return f"{_SHOT_SIZE_ZH.get(c, c)}（{c}）"


def _angle_zh(angle: str | None) -> str:
    a = angle or "eye_level"
    return _ANGLE_ZH.get(a, a)


def _tags_zh(tags: list[str]) -> str:
    out = []
    for t in tags:
        out.append(_TAG_ZH.get(t, _TAG_ZH.get(t.lower(), t)))
    return "、".join(out)


def compile_actor_free_prompt(shot: dict[str, Any], clip: dict[str, Any] | None = None) -> str:
    """主提示词：演员自由发挥版 · 全英文（用于生成）。"""
    return compile_actor_free_prompt_en(shot, clip)


def _is_pipeline_meta(text: str | None) -> bool:
    """Process notes that must NOT appear in generation prompts."""
    if not text or not str(text).strip():
        return True
    t = str(text)
    markers = (
        "跳过对白",
        "保留原剧本",
        "passthrough",
        "按原剧本自然表演",
        "polish_skipped",
        "shot bias",
        "move bias",
        "服务 beat",
        "知识库运镜",
        "配合表演与灯光",
    )
    return any(m in t for m in markers)


def _usable_dialogue_lines(bible: dict[str, Any], shot: dict[str, Any]) -> list[dict[str, Any]]:
    from film_pipeline.runtime.prompt_compiler import _dialogue_for_shot

    out = []
    for line in _dialogue_for_shot(bible, shot)[:2]:
        text = (line.get("text") or "").strip()
        if not text or _is_pipeline_meta(text):
            continue
        out.append(line)
    return out


def compile_actor_free_prompt_zh(shot: dict[str, Any], clip: dict[str, Any] | None = None) -> str:
    """中文对照：只写内容，不写流程说明。"""
    perf = shot.get("performance") or build_shot_performance(shot)
    tags = _tags_zh(list(perf.get("actor_free_tags") or [perf.get("emotion", "tense")]))
    emo = perf.get("emotion")
    emo_zh = _EMOTION_ZH.get(str(emo), str(emo))
    label = perf.get("intensity_label_zh") or ""
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    size = shot.get("shot_size") or "MS"
    parts = [
        f"戏：{shot.get('dramatic_beat') or '无'}。",
        f"情绪：{tags}（{emo_zh}，{label}）。",
        f"景别：{_shot_size_zh(size)}，约 {dur} 秒。",
        f"主体：{shot.get('subject') or '人物'}。",
        "表演自由发挥，不规定具体肌肉动作。",
    ]
    cam = shot.get("camera") or {}
    if cam.get("lens_mm"):
        parts.append(f"镜头约 {cam.get('lens_mm')}mm，{_angle_zh(cam.get('angle'))}。")
    parts.append("写实电影，无字幕水印。")
    return "".join(parts)


def compile_director_guided_prompt(
    bible: dict[str, Any],
    shot: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
    clip: dict[str, Any] | None = None,
) -> str:
    """主提示词：导演指导版 · 全英文（用于生成）。"""
    return compile_director_guided_prompt_en(bible, shot, style_pack=style_pack, clip=clip)


def compile_director_guided_prompt_en(
    bible: dict[str, Any],
    shot: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
    clip: dict[str, Any] | None = None,
) -> str:
    """Director-guided English prompt — content only, no pipeline meta."""
    from film_pipeline.runtime.prompt_compiler import _film_look, _scene_look

    perf = shot.get("performance") or build_shot_performance(shot)
    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    mov = cam.get("movement") or {}
    light_plan = perf.get("lighting_plan") or {}
    look_table = light_plan.get("look_table") or {}
    film = _film_look(bible)
    scene_look = _scene_look(bible, shot.get("scene_id"))
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    pack_label = (style_pack or {}).get("label") or (bible.get("meta") or {}).get(
        "style_pack", ""
    )
    size = shot.get("shot_size") or cam.get("shot_size") or "MS"
    is_insert = str(size).upper() == "INSERT"

    lines: list[str] = [
        f"{shot.get('dramatic_beat') or 'Scene'}.",
        f"{size} shot, about {dur} seconds.",
        f"Subject: {shot.get('subject') or 'scene'}.",
    ]

    # Human performance only when not a pure object insert
    if not is_insert:
        lines.append(
            f"Performance: {perf.get('emotion')} "
            f"({perf.get('intensity_label_en') or 'mid'})."
        )
        if perf.get("physiology_en"):
            lines.append(perf["physiology_en"] + ".")
        micros = perf.get("micro_actions_en") or []
        if micros:
            lines.append("Micro-actions: " + "; ".join(micros) + ".")
        if perf.get("gaze_en"):
            lines.append(f"Gaze: {perf['gaze_en']}.")
        if perf.get("voice_hint_en"):
            lines.append(f"Voice: {perf['voice_hint_en']}.")

    if cam.get("lens_mm"):
        lines.append(
            f"Camera: {cam.get('lens_mm')}mm, {cam.get('angle') or 'eye_level'}, "
            f"{cam.get('height') or 'eye'} height."
        )
    # Prefer clean catalog English only (no Chinese motivation dump)
    if mov.get("prompt_en") and not _is_pipeline_meta(mov.get("prompt_en")):
        lines.append(f"Camera move: {mov['prompt_en']}.")
    elif mov.get("type") and not _is_pipeline_meta(str(mov.get("type"))):
        sp = mov.get("speed")
        lines.append(
            f"Camera move: {mov.get('type')}"
            + (f", {sp}" if sp and sp not in ("none", "null") else "")
            + "."
        )

    light_bits = []
    for src_key in ("key", "ratio", "color"):
        val = light_plan.get(src_key)
        if val and not _is_pipeline_meta(str(val)):
            # Prefer English if mixed; keep short visual light description
            light_bits.append(str(val))
    if look.get("key_light") and not _is_pipeline_meta(str(look.get("key_light"))):
        light_bits.append(str(look["key_light"]))
    if look_table.get("face"):
        light_bits.append(str(look_table["face"]))
    tone = look.get("tone") or scene_look.get("base_tone")
    if tone:
        light_bits.append(f"{tone} tonal key")
    if film.get("palette"):
        light_bits.append("palette " + ", ".join(film["palette"]))
    if light_bits:
        lines.append("Lighting: " + "; ".join(dict.fromkeys(light_bits)) + ".")

    if pack_label:
        lines.append(f"{pack_label} cinematic look.")

    for line in _usable_dialogue_lines(bible, shot):
        chunk = f'{line.get("character")} says: "{line.get("text")}"'
        delivery = line.get("delivery")
        subtext = line.get("subtext")
        if delivery and not _is_pipeline_meta(str(delivery)):
            chunk += f", delivery: {delivery}"
        if subtext and not _is_pipeline_meta(str(subtext)):
            chunk += f", subtext: {subtext}"
        lines.append(chunk + ".")

    lines.append(
        "Photoreal cinematic film, coherent anatomy, continuous identity, "
        "no subtitles, no watermark, no UI."
    )
    return " ".join(lines)


def compile_director_guided_prompt_zh(
    bible: dict[str, Any],
    shot: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
    clip: dict[str, Any] | None = None,
) -> str:
    """
    导演指导版 · 全中文：
    戏 + 表演生理 + 景别 + 运镜 + 灯光一体；禁止文学修辞与精确毫米角度表演描述。
    """
    from film_pipeline.runtime.prompt_compiler import (
        _dialogue_for_shot,
        _film_look,
        _scene_look,
    )

    perf = shot.get("performance") or build_shot_performance(shot)
    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    mov = cam.get("movement") or {}
    light_plan = perf.get("lighting_plan") or {}
    look_table = light_plan.get("look_table") or {}
    film = _film_look(bible)
    scene_look = _scene_look(bible, shot.get("scene_id"))
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    style_id = (bible.get("meta") or {}).get("style_pack", "")
    pack_label = (style_pack or {}).get("label") or style_id
    emo = perf.get("emotion")
    emo_zh = _EMOTION_ZH.get(str(emo), str(emo))
    size = shot.get("shot_size") or cam.get("shot_size") or "MS"

    is_insert = str(size).upper() == "INSERT"
    lines: list[str] = [
        f"戏：{shot.get('dramatic_beat') or '无'}。",
        f"景别：{_shot_size_zh(str(size))}，约 {dur} 秒。",
        f"主体：{shot.get('subject') or '场景'}。",
    ]

    if not is_insert:
        lines.append(
            f"表演：{emo_zh}，{perf.get('intensity_label_zh') or '中'}。"
        )
        if perf.get("physiology_zh"):
            lines.append(f"身体：{perf['physiology_zh']}。")
        if perf.get("micro_actions"):
            lines.append("微动作：" + "；".join(perf["micro_actions"]) + "。")
        if perf.get("gaze"):
            lines.append(f"视线：{perf['gaze']}。")
        if perf.get("voice_hint"):
            lines.append(f"声音：{perf['voice_hint']}。")

    if cam.get("lens_mm"):
        lines.append(
            f"镜头约 {cam['lens_mm']}mm，{_angle_zh(str(cam.get('angle')))}。"
        )

    move_zh = mov.get("zh") or mov.get("type") or ""
    if mov.get("prompt_en") and not _is_pipeline_meta(mov.get("prompt_en")):
        lines.append(f"运镜：{move_zh or '见英文'}（{mov['prompt_en']}）。")
    elif move_zh and not _is_pipeline_meta(str(move_zh)):
        lines.append(f"运镜：{move_zh}。")

    light_bits = []
    for k, lab in (("key", "主光"), ("ratio", "明暗"), ("color", "色彩")):
        if light_plan.get(k) and not _is_pipeline_meta(str(light_plan.get(k))):
            light_bits.append(f"{lab}{light_plan[k]}")
    if look_table.get("face"):
        light_bits.append(str(look_table["face"]))
    tone = look.get("tone") or scene_look.get("base_tone")
    if tone:
        light_bits.append(f"影调{tone}")
    if light_bits:
        lines.append("灯光：" + "；".join(light_bits) + "。")
    if pack_label:
        lines.append(f"风格：{pack_label}。")

    for line in _usable_dialogue_lines(bible, shot):
        chunk = f"{line.get('character')}说：「{line.get('text')}」"
        if line.get("delivery") and not _is_pipeline_meta(str(line.get("delivery"))):
            chunk += f"（{line.get('delivery')}）"
        lines.append(chunk + "。")

    lines.append("写实电影，身份连续，无字幕水印。")
    return "".join(lines)


def compile_actor_free_prompt_en(shot: dict[str, Any], clip: dict[str, Any] | None = None) -> str:
    """English actor-free main prompt — content only."""
    perf = shot.get("performance") or build_shot_performance(shot)
    tags = ", ".join(perf.get("actor_free_tags") or [perf.get("emotion", "tense")])
    emo = perf.get("emotion")
    label = perf.get("intensity_label_en") or ""
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    size = shot.get("shot_size") or "MS"
    parts = [
        f"{shot.get('dramatic_beat') or 'Scene'}.",
        f"Emotion (free performance): {tags} ({emo}, {label}).",
        f"{size}, about {dur}s.",
        f"Subject: {shot.get('subject') or 'character'}.",
        "Do not prescribe exact facial muscle choreography.",
    ]
    cam = shot.get("camera") or {}
    if cam.get("lens_mm"):
        parts.append(f"{cam.get('lens_mm')}mm, {cam.get('angle', 'eye_level')}.")
    parts.append("Photoreal cinematic film, no subtitles, no watermark.")
    return " ".join(parts)
