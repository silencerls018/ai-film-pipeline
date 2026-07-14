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
    from film_pipeline.runtime.shot_locale import (
        ensure_shot_english_slots,
        is_environment_or_object_shot,
    )

    store = KnowledgeStore()
    for shot in bible.get("shots") or []:
        ensure_shot_english_slots(shot)
        if is_environment_or_object_shot(shot):
            # No facial/dread physiology on submarine / prop / insert plates
            emo = resolve_emotion(shot, store)
            shot["performance"] = {
                "emotion": emo,
                "intensity_bucket": "mid",
                "intensity_label_zh": "环境/物件镜",
                "intensity_label_en": "environment plate",
                "actor_free_tags": [emo, "environment"],
                "physiology_zh": "",
                "physiology_en": "",
                "micro_actions": [],
                "micro_actions_en": [],
                "gaze": "",
                "gaze_en": "",
                "voice_hint": "",
                "voice_hint_en": "",
                "shot_bias": [],
                "move_bias": [],
                "lighting_plan": build_shot_performance(shot, store).get("lighting_plan")
                or {},
                "director_note": "环境/物件镜：禁止人脸生理表演模板",
                "director_note_en": "Environment/object plate: no facial performance template",
                "skip_facial_performance": True,
            }
        else:
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
    """中文对照：由英文终稿忠实翻译（不再并行另写一套）。"""
    from film_pipeline.runtime.prompt_translate import translate_prompt_en_to_zh

    return translate_prompt_en_to_zh(compile_actor_free_prompt_en(shot, clip))


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
    from film_pipeline.runtime.shot_locale import (
        ensure_shot_english_slots,
        has_cjk,
        resolve_dramatic_beat_en,
        resolve_subject_en,
    )

    ensure_shot_english_slots(shot)
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
    beat_en = resolve_dramatic_beat_en(shot)
    subject_en = resolve_subject_en(shot)

    lines: list[str] = [
        f"{beat_en}.",
        f"{size} shot, about {dur} seconds.",
        f"Subject: {subject_en}.",
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
        if val and not _is_pipeline_meta(str(val)) and not has_cjk(str(val)):
            light_bits.append(str(val))
    if look.get("key_light") and not _is_pipeline_meta(str(look.get("key_light"))):
        kl = str(look["key_light"])
        if not has_cjk(kl):
            light_bits.append(kl)
    face = look_table.get("face")
    if face and not has_cjk(str(face)):
        light_bits.append(str(face))
    # Always keep machine-stable tonal / palette codes in EN draft
    tone = look.get("tone") or scene_look.get("base_tone")
    if tone:
        light_bits.append(f"{tone} tonal key")
    if film.get("palette"):
        light_bits.append("palette " + ", ".join(film["palette"]))
    if not light_bits:
        light_bits.append("motivated practical light, face readable")
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
    """中文对照：由英文终稿忠实翻译（不再并行另写一套）。"""
    from film_pipeline.runtime.prompt_translate import translate_prompt_en_to_zh

    return translate_prompt_en_to_zh(
        compile_director_guided_prompt_en(
            bible, shot, style_pack=style_pack, clip=clip
        )
    )


def compile_actor_free_prompt_en(shot: dict[str, Any], clip: dict[str, Any] | None = None) -> str:
    """English actor-free main prompt — content only (EN slots, not Chinese beats)."""
    from film_pipeline.runtime.shot_locale import (
        ensure_shot_english_slots,
        resolve_dramatic_beat_en,
        resolve_subject_en,
    )

    ensure_shot_english_slots(shot)
    perf = shot.get("performance") or build_shot_performance(shot)
    tags = ", ".join(perf.get("actor_free_tags") or [perf.get("emotion", "tense")])
    emo = perf.get("emotion")
    label = perf.get("intensity_label_en") or ""
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    size = shot.get("shot_size") or "MS"
    parts = [
        f"{resolve_dramatic_beat_en(shot)}.",
        f"Emotion (free performance): {tags} ({emo}, {label}).",
        f"{size}, about {dur}s.",
        f"Subject: {resolve_subject_en(shot)}.",
        "Do not prescribe exact facial muscle choreography.",
    ]
    cam = shot.get("camera") or {}
    if cam.get("lens_mm"):
        parts.append(f"{cam.get('lens_mm')}mm, {cam.get('angle', 'eye_level')}.")
    parts.append("Photoreal cinematic film, no subtitles, no watermark.")
    return " ".join(parts)
