"""
Prompt Compiler — final stage logic.

Merges FilmBible fields into executable prompts for image/video models.
This is deterministic assembly (template + fields), not free-form invention.
"""

from __future__ import annotations

from typing import Any


def _char_index(bible: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in bible.get("characters") or []:
        name = c.get("name") or c.get("id")
        if name:
            out[str(name)] = c
            if c.get("id"):
                out[str(c["id"])] = c
    return out


def _dialogue_for_shot(bible: dict[str, Any], shot: dict[str, Any]) -> list[dict[str, Any]]:
    linked = shot.get("linked_dialogue") or []
    scene_id = shot.get("scene_id")
    lines: list[dict[str, Any]] = []
    for block in bible.get("dialogue") or []:
        if scene_id and block.get("scene_id") != scene_id:
            continue
        for line in block.get("lines") or []:
            text = line.get("text") or ""
            if linked:
                if any(t in text or text in t for t in linked):
                    lines.append(line)
            # if no linked list, only attach for MCU/CU with whose_pov match later
    if not lines and linked:
        # fuzzy: any line whose text equals linked entry
        for block in bible.get("dialogue") or []:
            for line in block.get("lines") or []:
                if line.get("text") in linked:
                    lines.append(line)
    return lines


def _scene_look(bible: dict[str, Any], scene_id: str | None) -> dict[str, Any]:
    for s in (bible.get("look_bible") or {}).get("scene_looks") or []:
        if s.get("scene_id") == scene_id:
            return s
    return {}


def _film_look(bible: dict[str, Any]) -> dict[str, Any]:
    return (bible.get("look_bible") or {}).get("film_look") or {}


def compile_visual_prompt(bible: dict[str, Any], shot: dict[str, Any], style_pack: dict[str, Any] | None = None) -> str:
    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    film = _film_look(bible)
    scene_look = _scene_look(bible, shot.get("scene_id"))
    style_id = (bible.get("meta") or {}).get("style_pack", "")
    pack_label = (style_pack or {}).get("label") or style_id

    parts: list[str] = [
        "Cinematic still frame from a narrative short film.",
        f"Shot size: {shot.get('shot_size') or cam.get('shot_size') or 'MS'}.",
        f"Subject: {shot.get('subject') or 'scene'}.",
        f"Dramatic beat: {shot.get('dramatic_beat') or 'n/a'}.",
    ]

    emo = shot.get("emotion") or {}
    if emo.get("primary"):
        parts.append(
            f"Emotional intent: {emo.get('primary')}"
            + (f" (intensity {emo.get('intensity')})" if emo.get("intensity") is not None else "")
            + "."
        )

    # Camera language
    cam_bits = []
    if cam.get("body"):
        cam_bits.append(f"camera body feel: {cam['body']}")
    if cam.get("lens_mm"):
        cam_bits.append(f"{cam['lens_mm']}mm lens")
    if cam.get("t_stop"):
        cam_bits.append(str(cam["t_stop"]))
    if cam.get("angle"):
        cam_bits.append(f"angle: {cam['angle']}")
    if cam.get("height"):
        cam_bits.append(f"height: {cam['height']}")
    if cam.get("composition"):
        cam_bits.append(f"composition: {cam['composition']}")
    if cam.get("focus"):
        cam_bits.append(f"focus: {cam['focus']}")
    if cam_bits:
        parts.append("Camera: " + ", ".join(cam_bits) + ".")

    mov = cam.get("movement") or {}
    if mov.get("type") or mov.get("prompt_en"):
        # Prefer Excel-catalog English prompt fragment when present
        if mov.get("prompt_en"):
            parts.append(f"Camera movement: {mov.get('prompt_en')}.")
        else:
            parts.append(
                f"Camera move planned for video: {mov.get('type')}"
                + (f", speed {mov.get('speed')}" if mov.get("speed") else "")
                + "."
            )
        if mov.get("motivation"):
            parts.append(f"Move motivation: {mov.get('motivation')}.")
        if mov.get("zh"):
            parts.append(f"Move (zh): {mov.get('zh')}.")

    # Look / grade
    look_bits = []
    tone = look.get("tone") or scene_look.get("base_tone") or film.get("key")
    if tone:
        look_bits.append(f"tonal key: {tone}")
    contrast = look.get("contrast") or scene_look.get("contrast") or film.get("contrast")
    if contrast:
        look_bits.append(f"contrast: {contrast}")
    if look.get("key_light"):
        look_bits.append(f"key light: {look['key_light']}")
    if look.get("fill_ratio"):
        look_bits.append(f"fill ratio: {look['fill_ratio']}")
    color = look.get("color_temp") or scene_look.get("color")
    if color:
        look_bits.append(f"color: {color}")
    if look.get("grade_intent"):
        look_bits.append(f"grade: {look['grade_intent']}")
    palette = film.get("palette") or []
    if palette:
        look_bits.append("palette: " + ", ".join(palette))
    if film.get("saturation"):
        look_bits.append(f"saturation: {film['saturation']}")
    if look_bits:
        parts.append("Look: " + "; ".join(look_bits) + ".")
    if look.get("motivation"):
        parts.append(f"Look motivation: {look['motivation']}.")

    if pack_label:
        parts.append(f"Style pack: {pack_label}.")

    # Optional casting / set anchors (ids only — swap image_refs anytime)
    ab = bible.get("asset_bible") or {}
    char_ids = [c.get("asset_id") for c in (ab.get("characters") or []) if c.get("asset_id")]
    if char_ids:
        parts.append(
            "Character consistency: match casting sheets "
            + ", ".join(char_ids)
            + " (use external reference images if provided; do not invent new faces)."
        )
    set_ids = [s.get("asset_id") for s in (ab.get("sets") or []) if s.get("asset_id")]
    if set_ids:
        parts.append("Location consistency: match set sheets " + ", ".join(set_ids) + ".")

    # Dialogue / performance (for image: facial acting cue only)
    for line in _dialogue_for_shot(bible, shot)[:2]:
        delivery = line.get("delivery") or ""
        subtext = line.get("subtext") or ""
        parts.append(
            f"Performance cue ({line.get('character')}): saying 「{line.get('text')}」"
            + (f"; delivery: {delivery}" if delivery else "")
            + (f"; subtext: {subtext}" if subtext else "")
            + "."
        )

    parts.append(
        "Photoreal, coherent anatomy, filmic color science, no watermark, no subtitles, no UI."
    )
    return " ".join(parts)


def compile_motion_prompt(
    shot: dict[str, Any],
    clip: dict[str, Any] | None = None,
) -> str:
    cam = shot.get("camera") or {}
    mov = cam.get("movement") or {}
    mtype = mov.get("type") or "static_hold"
    speed = mov.get("speed") or "normal"
    motivation = mov.get("motivation") or ""
    prompt_en = mov.get("prompt_en") or ""
    if clip and clip.get("duration_sec") is not None:
        duration = clip["duration_sec"]
    else:
        duration = shot.get("duration_sec") or 4
    bits = [
        f"Camera movement: {prompt_en or mtype}.",
        f"Move name: {mtype}.",
        f"Speed: {speed}.",
        f"Duration exactly about {duration} seconds (do not exceed model clip limit).",
        "Keep subject identity and lighting continuous.",
        "Natural physics, subtle film grain ok.",
    ]
    if motivation:
        bits.insert(3, f"Motivation: {motivation}.")
    if clip and clip.get("stitch") in {"continue", "last"}:
        bits.append(
            f"Continuation segment {clip.get('index')}: match end frame of previous clip; "
            f"overlap ~{clip.get('overlap_prev_sec', 0.5)}s for stitch."
        )
    if shot.get("shot_size") in {"CU", "ECU", "MCU"}:
        bits.append("Preserve facial micro-expressions; avoid face morphing.")
    # Pace dialogue inside this clip window when applicable
    timing = shot.get("timing") or {}
    dlg = timing.get("components") or {}
    if dlg.get("dialogue_sec"):
        bits.append(
            f"Allow time for spoken line (~{dlg.get('dialogue_sec')}s of speech in full shot timeline)."
        )
    return " ".join(bits)


def compile_negative_prompt(bible: dict[str, Any], shot: dict[str, Any]) -> str:
    base = [
        "cartoon",
        "anime",
        "lowres",
        "blurry face",
        "extra fingers",
        "deformed hands",
        "text",
        "watermark",
        "logo",
        "subtitles",
        "split screen",
        "collage",
        "overexposed skin",
        "underexposed unreadable face",
    ]
    scene_look = _scene_look(bible, shot.get("scene_id"))
    for ban in scene_look.get("forbidden") or []:
        base.append(str(ban).replace("_", " "))
    film = _film_look(bible)
    # style pack forbids are often on pack; scene may copy them
    return ", ".join(dict.fromkeys(base))


def compile_master_prompt(
    bible: dict[str, Any],
    shot: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
    clip: dict[str, Any] | None = None,
) -> str:
    """Single block combining visual + motion for models that take one prompt."""
    visual = compile_visual_prompt(bible, shot, style_pack)
    motion = compile_motion_prompt(shot, clip=clip)
    return f"{visual}\n\n[Motion / I2V]\n{motion}"


def compile_zh_summary(shot: dict[str, Any], clip: dict[str, Any] | None = None) -> str:
    """Human-readable Chinese director summary (not for all model backends)."""
    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    mov = cam.get("movement") or {}
    base = (
        f"【{shot.get('shot_id')}】{shot.get('dramatic_beat', '')}；"
        f"景别{shot.get('shot_size')}；"
        f"{cam.get('lens_mm', '?')}mm；角度{cam.get('angle', '?')}；"
        f"运镜{mov.get('type', '固定')}（{mov.get('motivation', '')}）；"
        f"影调{look.get('tone', '?')}/{look.get('contrast', '?')}；"
        f"主体：{shot.get('subject', '')}；"
        f"需要时长{shot.get('duration_sec', '?')}s"
    )
    if clip:
        base += (
            f"；本段clip {clip.get('clip_id')} "
            f"{clip.get('duration_sec')}s "
            f"[{clip.get('timeline_start_sec')}→{clip.get('timeline_end_sec')}] "
            f"stitch={clip.get('stitch')}"
        )
    return base


def compile_generation_jobs(bible: dict[str, Any], style_pack: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    One API job per generation clip (not merely per shot).
    Each job includes TWO final prompt versions:
      - actor_free_prompt: emotion tags only (actor improvises)
      - director_guided_prompt: performance + shot + move + light unified
    """
    from film_pipeline.runtime.performance import (
        compile_actor_free_prompt,
        compile_director_guided_prompt,
        enrich_shots_with_performance,
    )

    # Ensure performance packages exist even if director stage was skipped
    if any(not s.get("performance") for s in bible.get("shots") or []):
        enrich_shots_with_performance(bible)

    jobs: list[dict[str, Any]] = []
    max_clip = (bible.get("timing_plan") or {}).get("max_clip_sec")
    for shot in bible.get("shots") or []:
        clips = shot.get("generation_clips") or [
            {
                "clip_id": f"{shot.get('shot_id')}_c01",
                "index": 1,
                "duration_sec": shot.get("duration_sec") or 3.5,
                "timeline_start_sec": 0.0,
                "timeline_end_sec": shot.get("duration_sec") or 3.5,
                "stitch": "single",
                "role": "full_shot",
            }
        ]
        visual = compile_visual_prompt(bible, shot, style_pack)
        negative = compile_negative_prompt(bible, shot)
        for clip in clips:
            dur = float(clip.get("duration_sec") or shot.get("duration_sec") or 3.5)
            if max_clip is not None:
                dur = min(dur, float(max_clip))
            motion = compile_motion_prompt(shot, clip=clip)
            master = compile_master_prompt(bible, shot, style_pack, clip=clip)
            from film_pipeline.runtime.performance import (
                compile_actor_free_prompt_en,
                compile_actor_free_prompt_zh,
                compile_director_guided_prompt_en,
                compile_director_guided_prompt_zh,
            )

            # 主：全英文（生成用）  辅：全中文（阅读对照）
            actor_free_en = compile_actor_free_prompt_en(shot, clip=clip)
            director_guided_en = compile_director_guided_prompt_en(
                bible, shot, style_pack=style_pack, clip=clip
            )
            actor_free_zh = compile_actor_free_prompt_zh(shot, clip=clip)
            director_guided_zh = compile_director_guided_prompt_zh(
                bible, shot, style_pack=style_pack, clip=clip
            )
            jobs.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "clip_id": clip.get("clip_id"),
                    "scene_id": shot.get("scene_id"),
                    "visual_prompt": visual,
                    "motion_prompt": motion,
                    "master_prompt": master,
                    # 主产品：英文（复制去视频模型）
                    "actor_free_prompt": actor_free_en,
                    "director_guided_prompt": director_guided_en,
                    "actor_free_prompt_en": actor_free_en,
                    "director_guided_prompt_en": director_guided_en,
                    # 辅助：中文对照（帮你看懂内容）
                    "actor_free_prompt_zh": actor_free_zh,
                    "director_guided_prompt_zh": director_guided_zh,
                    "negative_prompt": negative,
                    "zh_director_summary": compile_zh_summary(shot, clip),
                    "duration_sec": dur,
                    "timeline_start_sec": clip.get("timeline_start_sec"),
                    "timeline_end_sec": clip.get("timeline_end_sec"),
                    "stitch": clip.get("stitch"),
                    "extend_from_clip": clip.get("extend_from_clip"),
                    "sources": {
                        "dramatic_beat": shot.get("dramatic_beat"),
                        "shot_size": shot.get("shot_size"),
                        "emotion": shot.get("emotion"),
                        "performance": shot.get("performance"),
                        "camera": shot.get("camera"),
                        "look": shot.get("look"),
                        "linked_dialogue": shot.get("linked_dialogue"),
                        "timing": shot.get("timing"),
                        "clip": clip,
                    },
                    "downgrades": [],
                }
            )
    return jobs


def export_prompts_markdown(bible: dict[str, Any]) -> str:
    """Export all compiled prompts as a readable markdown board."""
    lines = [
        f"# Prompt Board — {((bible.get('meta') or {}).get('title') or 'untitled')}",
        "",
        f"Style: `{(bible.get('meta') or {}).get('style_pack')}`",
        "",
    ]
    story = bible.get("story") or {}
    if story.get("logline"):
        lines += [f"> {story['logline']}", ""]

    plan = bible.get("timing_plan") or {}
    if plan:
        lines += [
            f"Max clip: **{plan.get('max_clip_sec')}s** · "
            f"Film total: **{plan.get('film_total_sec')}s**",
            "",
        ]

    lines += [
        "## 提示词说明",
        "",
        "- **主语言：英文**（`actor_free_prompt` / `director_guided_prompt`）→ 复制去视频模型",
        "- **辅助：中文对照**（`*_zh`）→ 只帮你看懂内容，不是主生成稿",
        "- ① 演员自由发挥版：只给情绪词  ② 导演指导版：表演+景别+运镜+灯光",
        "",
    ]

    for job in bible.get("generation_jobs") or compile_generation_jobs(bible):
        title = job.get("clip_id") or job.get("shot_id")
        lines += [
            f"## {title}",
            "",
            f"**镜头摘要（中文）:** {job.get('zh_director_summary', '')}",
            "",
            f"- 时长: `{job.get('duration_sec')}s` · 拼接: `{job.get('stitch')}`",
            "",
            "### ① 演员自由发挥版 — 英文主稿（生成用）",
            "```",
            job.get("actor_free_prompt") or job.get("actor_free_prompt_en") or "",
            "```",
            "",
            "#### 中文对照（辅助理解，不优先投喂）",
            "```",
            job.get("actor_free_prompt_zh") or "",
            "```",
            "",
            "### ② 导演指导版 — 英文主稿（生成用）",
            "```",
            job.get("director_guided_prompt")
            or job.get("director_guided_prompt_en")
            or "",
            "```",
            "",
            "#### 中文对照（辅助理解，不优先投喂）",
            "```",
            job.get("director_guided_prompt_zh") or "",
            "```",
            "",
            "### 技术层 visual / motion / negative",
            "```",
            "visual: " + (job.get("visual_prompt") or "")[:400],
            "",
            "motion: " + (job.get("motion_prompt") or ""),
            "",
            "negative: " + (job.get("negative_prompt") or ""),
            "```",
            "",
        ]
    return "\n".join(lines)
