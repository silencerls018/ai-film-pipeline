"""
Prompt Compiler — final stage logic.

Merges FilmBible fields into executable prompts for image/video models.
This is deterministic assembly (template + fields), not free-form invention.
"""

from __future__ import annotations

import html
import re
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
    from film_pipeline.runtime.shot_locale import (
        ensure_shot_english_slots,
        resolve_dramatic_beat_en,
        resolve_subject_en,
    )

    ensure_shot_english_slots(shot)
    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    film = _film_look(bible)
    scene_look = _scene_look(bible, shot.get("scene_id"))
    style_id = (bible.get("meta") or {}).get("style_pack", "")
    pack_label = (style_pack or {}).get("label") or style_id

    parts: list[str] = [
        "Cinematic still frame from a narrative short film.",
        f"Shot size: {shot.get('shot_size') or cam.get('shot_size') or 'MS'}.",
        f"Subject: {resolve_subject_en(shot)}.",
        f"Dramatic beat: {resolve_dramatic_beat_en(shot)}.",
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
    from film_pipeline.runtime.shot_locale import (
        resolve_dramatic_beat_zh,
        resolve_subject_zh,
    )

    cam = shot.get("camera") or {}
    look = shot.get("look") or {}
    mov = cam.get("movement") or {}
    base = (
        f"【{shot.get('shot_id')}】{resolve_dramatic_beat_zh(shot)}；"
        f"景别{shot.get('shot_size')}；"
        f"{cam.get('lens_mm', '?')}mm；角度{cam.get('angle', '?')}；"
        f"运镜{mov.get('type', '固定')}（{mov.get('motivation', '')}）；"
        f"影调{look.get('tone', '?')}/{look.get('contrast', '?')}；"
        f"主体：{resolve_subject_zh(shot)}；"
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
    Back-compat entry: run the dedicated Prompt Writer Agent and return jobs.

    Prefer: film_pipeline.runtime.prompt_writer_agent.run_prompt_writer_agent
    """
    from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent

    # style_pack arg kept for API compatibility; agent loads style from bible meta
    _ = style_pack
    return run_prompt_writer_agent(bible).get("generation_jobs") or []


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
        "- **中文 / 英文均为成品**：都可直接复制投喂视频模型",
        "- ① 演员自由发挥版  ② 导演指导版（更具体）",
        "- 四段结构已**自动换行**，无需横向拖动阅读",
        "- 需要**一键复制按钮**：请打开同目录 `prompt_board.html`（浏览器打开）",
        "- 终稿由 **Prompt Writer** 根据 FilmBible 合同撰写",
        "",
    ]

    from film_pipeline.runtime.prompt_writer import format_prompt_for_delivery

    for job in bible.get("generation_jobs") or compile_generation_jobs(bible):
        title = job.get("clip_id") or job.get("shot_id")
        free_en = format_prompt_for_delivery(
            job.get("actor_free_prompt") or job.get("actor_free_prompt_en") or ""
        )
        free_zh = format_prompt_for_delivery(job.get("actor_free_prompt_zh") or "")
        guided_en = format_prompt_for_delivery(
            job.get("director_guided_prompt")
            or job.get("director_guided_prompt_en")
            or ""
        )
        guided_zh = format_prompt_for_delivery(
            job.get("director_guided_prompt_zh") or ""
        )
        lines += [
            f"## {title}",
            "",
            f"**镜头摘要:** {job.get('zh_director_summary', '')}",
            "",
            f"- 时长: `{job.get('duration_sec')}s` · 拼接: `{job.get('stitch')}`",
            "",
            "### ① 演员自由发挥 · 英文（可直接投喂）",
            "```text",
            free_en.rstrip(),
            "```",
            "",
            "### ① 演员自由发挥 · 中文（可直接投喂）",
            "```text",
            free_zh.rstrip(),
            "```",
            "",
            "### ② 导演指导 · 英文（可直接投喂）",
            "```text",
            guided_en.rstrip(),
            "```",
            "",
            "### ② 导演指导 · 中文（可直接投喂）",
            "```text",
            guided_zh.rstrip(),
            "```",
            "",
            "### 技术层 visual / motion / negative",
            "```text",
            format_prompt_for_delivery(
                "visual: "
                + (job.get("visual_prompt") or "")[:400]
                + "\n\nmotion: "
                + (job.get("motion_prompt") or "")
                + "\n\nnegative: "
                + (job.get("negative_prompt") or "")
            ).rstrip(),
            "```",
            "",
        ]

    lines += _film_duration_stats_markdown(bible)
    return "\n".join(lines)


def _film_duration_stats(bible: dict[str, Any]) -> dict[str, Any]:
    plan = bible.get("timing_plan") or {}
    meta = bible.get("meta") or {}
    jobs_list = bible.get("generation_jobs") or []
    film_total = plan.get("film_total_sec") or meta.get("film_total_sec")
    if film_total is None:
        film_total = round(
            sum(float(s.get("duration_sec") or 0) for s in (bible.get("shots") or [])),
            2,
        )
    gen_total = plan.get("generation_total_sec")
    if gen_total is None:
        gen_total = round(sum(float(j.get("duration_sec") or 0) for j in jobs_list), 2)
    max_clip = plan.get("max_clip_sec") or meta.get("max_clip_sec") or 30
    pkg_n = plan.get("generation_package_count") or len(
        bible.get("generation_packages") or jobs_list
    )
    return {
        "film_total": film_total,
        "gen_total": gen_total,
        "max_clip": max_clip,
        "pkg_n": pkg_n,
        "film_min": round(float(film_total) / 60.0, 2),
        "gen_min": round(float(gen_total) / 60.0, 2),
    }


def _film_duration_stats_markdown(bible: dict[str, Any]) -> list[str]:
    s = _film_duration_stats(bible)
    return [
        "---",
        "",
        "## 电影最终时长统计",
        "",
        f"- **电影最终时长**：`{s['film_total']}` 秒（约 `{s['film_min']}` 分钟）← 戏剧分镜合计",
        f"- **成片预估（按生成段拼接）**：`{s['gen_total']}` 秒（约 `{s['gen_min']}` 分钟）",
        f"- **模型单段上限**：`{s['max_clip']}` 秒（用户选 15 或 30；**不是**整片上限）",
        f"- **生成段数**：`{s['pkg_n']}` 段（每段 ≤ 上限；段内用 0–2秒 / 3–12秒… 时间轴，模型自行切镜更流畅）",
        f"- **生成请求总时长**：`{s['gen_total']}` 秒",
        "",
        "> **规则**：15/30 = 单次生成天花板。段内把分镜写成时间轴即可，模型自己切镜更顺；"
        "只有累计时长已经「到底」塞不进上限时，才开下一段生成。",
        "",
    ]


def _html_copy_block(block_id: str, label: str, body: str) -> str:
    """One prompt card: label + copy button + pre-wrapped body."""
    safe_body = html.escape(body or "", quote=False)
    safe_label = html.escape(label, quote=True)
    return (
        f'<div class="prompt-card">\n'
        f'  <div class="prompt-toolbar">\n'
        f'    <span class="prompt-label">{safe_label}</span>\n'
        f'    <button type="button" class="copy-btn" data-target="{html.escape(block_id, quote=True)}"'
        f' onclick="copyPrompt(this)">复制</button>\n'
        f"  </div>\n"
        f'  <pre class="prompt-body" id="{html.escape(block_id, quote=True)}">{safe_body}</pre>\n'
        f"</div>\n"
    )


def export_prompts_html(bible: dict[str, Any]) -> str:
    """
    Browser-friendly prompt board with one-click copy buttons.
    All prompt bodies use white-space: pre-wrap (auto wrap, no horizontal drag).
    """
    from film_pipeline.runtime.prompt_writer import format_prompt_for_delivery

    meta = bible.get("meta") or {}
    title = str(meta.get("title") or "untitled")
    style = str(meta.get("style_pack") or "")
    story = bible.get("story") or {}
    plan = bible.get("timing_plan") or {}
    stats = _film_duration_stats(bible)

    jobs = list(bible.get("generation_jobs") or [])
    if not jobs:
        try:
            jobs = compile_generation_jobs(bible) if bible.get("shots") else []
        except Exception:
            jobs = []

    parts: list[str] = []
    parts.append(
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Prompt Board — {html.escape(title)}</title>
<style>
  :root {{
    --bg: #0f1419;
    --card: #1a2332;
    --border: #2d3a4d;
    --text: #e7ecf3;
    --muted: #9aa7b8;
    --accent: #3d8bfd;
    --ok: #3dd68c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px 64px;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; }}
  h1 {{ font-size: 1.45rem; margin: 0 0 8px; }}
  h2 {{ font-size: 1.15rem; margin: 28px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  .meta, .hint {{ color: var(--muted); font-size: 0.92rem; }}
  .hint {{ margin: 12px 0 20px; padding: 12px 14px; background: var(--card); border-radius: 8px; border: 1px solid var(--border); }}
  .logline {{ color: var(--muted); font-style: italic; margin: 8px 0 16px; }}
  .clip {{ margin-bottom: 28px; }}
  .clip-meta {{ color: var(--muted); font-size: 0.88rem; margin-bottom: 10px; }}
  .prompt-card {{
    margin: 10px 0 14px; border: 1px solid var(--border); border-radius: 10px;
    background: var(--card); overflow: hidden;
  }}
  .prompt-toolbar {{
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 8px 12px; border-bottom: 1px solid var(--border); background: #121a26;
  }}
  .prompt-label {{ font-size: 0.9rem; color: var(--muted); }}
  .copy-btn {{
    flex-shrink: 0; cursor: pointer; border: 1px solid var(--accent);
    background: transparent; color: var(--accent); border-radius: 6px;
    padding: 4px 12px; font-size: 0.85rem;
  }}
  .copy-btn:hover {{ background: rgba(61,139,253,0.12); }}
  .copy-btn.copied {{ border-color: var(--ok); color: var(--ok); }}
  /* auto wrap — never force horizontal scroll for long prompts */
  .prompt-body {{
    margin: 0; padding: 12px 14px; font-size: 0.88rem;
    font-family: ui-monospace, "Cascadia Code", "Consolas", monospace;
    white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word;
    max-width: 100%; overflow-x: hidden; color: var(--text);
  }}
  .stats {{ margin-top: 36px; padding: 16px; border: 1px solid var(--border); border-radius: 10px; background: var(--card); }}
  .stats ul {{ margin: 8px 0 0; padding-left: 1.2em; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
<h1>Prompt Board — {html.escape(title)}</h1>
<p class="meta">Style: <code>{html.escape(style)}</code>
 · Max clip: <strong>{html.escape(str(plan.get("max_clip_sec") or stats["max_clip"]))}s</strong>
 · Film total: <strong>{html.escape(str(stats["film_total"]))}s</strong></p>
"""
    )
    if story.get("logline"):
        parts.append(f'<p class="logline">{html.escape(str(story["logline"]))}</p>\n')

    parts.append(
        '<div class="hint">'
        "<strong>用法：</strong>每段提示词右上角点「复制」即可投喂视频模型。"
        "中英均为成品。正文已自动换行（soft-wrap + pre-wrap），无需横向拖动。"
        "同目录还有 <code>prompt_board.md</code> 与 <code>clips/*.txt</code>。"
        "</div>\n"
    )

    # TOC
    if jobs:
        parts.append('<p class="meta"><strong>目录</strong> · ')
        toc_bits = []
        for i, job in enumerate(jobs):
            cid = str(job.get("clip_id") or job.get("shot_id") or f"clip_{i}")
            toc_bits.append(f'<a href="#clip-{html.escape(cid, quote=True)}">{html.escape(cid)}</a>')
        parts.append(" · ".join(toc_bits))
        parts.append("</p>\n")

    for i, job in enumerate(jobs):
        cid = str(job.get("clip_id") or job.get("shot_id") or f"clip_{i}")
        free_en = format_prompt_for_delivery(
            job.get("actor_free_prompt") or job.get("actor_free_prompt_en") or ""
        )
        free_zh = format_prompt_for_delivery(job.get("actor_free_prompt_zh") or "")
        guided_en = format_prompt_for_delivery(
            job.get("director_guided_prompt")
            or job.get("director_guided_prompt_en")
            or ""
        )
        guided_zh = format_prompt_for_delivery(
            job.get("director_guided_prompt_zh") or ""
        )
        tech = format_prompt_for_delivery(
            "visual: "
            + (job.get("visual_prompt") or "")[:400]
            + "\n\nmotion: "
            + (job.get("motion_prompt") or "")
            + "\n\nnegative: "
            + (job.get("negative_prompt") or "")
        )
        safe_cid = re.sub(r"[^A-Za-z0-9_\-]", "_", cid)
        summary = html.escape(str(job.get("zh_director_summary") or ""))
        dur = html.escape(str(job.get("duration_sec") or ""))
        stitch = html.escape(str(job.get("stitch") or ""))

        parts.append(f'<section class="clip" id="clip-{html.escape(cid, quote=True)}">\n')
        parts.append(f"<h2>{html.escape(cid)}</h2>\n")
        if summary:
            parts.append(f'<p class="clip-meta"><strong>镜头摘要:</strong> {summary}</p>\n')
        parts.append(
            f'<p class="clip-meta">时长: <code>{dur}s</code> · 拼接: <code>{stitch}</code></p>\n'
        )
        parts.append(
            _html_copy_block(f"{safe_cid}_free_en", "① 演员自由发挥 · 英文（可直接投喂）", free_en)
        )
        parts.append(
            _html_copy_block(f"{safe_cid}_free_zh", "① 演员自由发挥 · 中文（可直接投喂）", free_zh)
        )
        parts.append(
            _html_copy_block(f"{safe_cid}_guided_en", "② 导演指导 · 英文（可直接投喂）", guided_en)
        )
        parts.append(
            _html_copy_block(f"{safe_cid}_guided_zh", "② 导演指导 · 中文（可直接投喂）", guided_zh)
        )
        parts.append(
            _html_copy_block(f"{safe_cid}_tech", "技术层 visual / motion / negative", tech)
        )
        parts.append("</section>\n")

    parts.append(
        f"""
<div class="stats">
  <h2>电影最终时长统计</h2>
  <ul>
    <li><strong>电影最终时长</strong>：{html.escape(str(stats["film_total"]))} 秒（约 {html.escape(str(stats["film_min"]))} 分钟）← 戏剧分镜合计</li>
    <li><strong>成片预估（按生成段拼接）</strong>：{html.escape(str(stats["gen_total"]))} 秒（约 {html.escape(str(stats["gen_min"]))} 分钟）</li>
    <li><strong>模型单段上限</strong>：{html.escape(str(stats["max_clip"]))} 秒（不是整片上限）</li>
    <li><strong>生成段数</strong>：{html.escape(str(stats["pkg_n"]))} 段</li>
    <li><strong>生成请求总时长</strong>：{html.escape(str(stats["gen_total"]))} 秒</li>
  </ul>
</div>
</div>
<script>
async function copyPrompt(btn) {{
  const id = btn.getAttribute("data-target");
  const el = document.getElementById(id);
  if (!el) return;
  const text = el.innerText || el.textContent || "";
  try {{
    await navigator.clipboard.writeText(text);
  }} catch (e) {{
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }}
  const old = btn.textContent;
  btn.textContent = "已复制";
  btn.classList.add("copied");
  setTimeout(function () {{
    btn.textContent = old || "复制";
    btn.classList.remove("copied");
  }}, 1600);
}}
</script>
</body>
</html>
"""
    )
    return "".join(parts)


def export_asset_board_markdown(bible: dict[str, Any]) -> str:
    """Human-readable asset board (characters / props / sets sheet prompts)."""
    ab = bible.get("asset_bible") or {}
    lines = [
        f"# Asset Board — {(bible.get('meta') or {}).get('title', '')}",
        "",
        "三视图/设定提示词（可随时换 image_refs，不影响主链镜头合同）",
        "",
    ]
    for section, key in [
        ("Characters", "characters"),
        ("Props", "props"),
        ("Sets", "sets"),
    ]:
        items = ab.get(key) or []
        if not items:
            continue
        lines.append(f"## {section}")
        lines.append("")
        for it in items:
            lines.append(f"### {it.get('asset_id')} — {it.get('name', '')}")
            lines.append(f"- type: {it.get('type')}")
            lines.append(f"- anchors: {it.get('consistency_anchors')}")
            if it.get("image_size_hint"):
                lines.append(f"- size hint: {it.get('image_size_hint')}")
            lines.append("")
            if it.get("sheet_prompt_zh_summary"):
                lines.append("**中文说明（辅助）**")
                lines.append("")
                lines.append(it.get("sheet_prompt_zh_summary") or "")
                lines.append("")
            lines.append("**sheet_prompt（英文主稿 · 生图用）**")
            lines.append("```")
            lines.append(it.get("sheet_prompt") or "")
            lines.append("```")
            lines.append("")
            refs = it.get("image_refs") or []
            lines.append(f"- image_refs: {refs if refs else '（空，可稍后替换）'}")
            lines.append("")
    return "\n".join(lines)


def _safe_asset_filename(asset_id: str, name: str) -> str:
    raw = f"{asset_id}_{name}".strip("_") or "asset"
    return re.sub(r'[<>:"/\\|?*\s]+', "_", raw)[:80]


def export_assets_into_dir(bible: dict[str, Any], root: Any) -> Any:
    """
    Write asset delivery under outputs/<project>/assets/ :
      assets/asset_board.md
      assets/characters/<id>_sheet.en.txt
      assets/props/...
      assets/sets/...
      assets/asset_bible.json
    """
    from pathlib import Path

    root = Path(root)
    ab = bible.get("asset_bible")
    if not ab:
        return root

    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "asset_board.md").write_text(
        export_asset_board_markdown(bible), encoding="utf-8"
    )
    (assets_dir / "asset_bible.json").write_text(
        __import__("json").dumps(ab, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for kind, folder in (
        ("characters", "characters"),
        ("props", "props"),
        ("sets", "sets"),
    ):
        items = ab.get(kind) or []
        if not items:
            continue
        sub = assets_dir / folder
        sub.mkdir(parents=True, exist_ok=True)
        for it in items:
            safe = _safe_asset_filename(
                str(it.get("asset_id") or "asset"),
                str(it.get("name") or ""),
            )
            sheet = (it.get("sheet_prompt") or "").strip()
            zh = (it.get("sheet_prompt_zh_summary") or "").strip()
            (sub / f"{safe}_sheet.en.txt").write_text(sheet, encoding="utf-8")
            if zh:
                (sub / f"{safe}_sheet.zh.txt").write_text(zh, encoding="utf-8")
    return assets_dir


def export_final_prompts_package(bible: dict[str, Any], dest: Any = None) -> Any:
    """
    Write delivery package into a folder named after the project.

    Layout:
      outputs/<project_id>/
        prompt_board.md          # shot prompts board (auto-wrapped)
        prompt_board.html        # same board + one-click copy buttons
        clips/                   # per-clip video prompts (auto-wrapped)
        assets/                  # ALWAYS when asset_bible present
          asset_board.md
          asset_bible.json
          characters|props|sets/*_sheet.en.txt
        README.txt
    """
    from pathlib import Path

    from film_pipeline.paths import ensure_final_prompts_dir, sanitize_project_id

    meta = bible.get("meta") or {}
    project_id = sanitize_project_id(
        str(meta.get("project_id") or meta.get("title") or "untitled")
    )
    root = Path(dest) if dest is not None else ensure_final_prompts_dir(project_id)
    root.mkdir(parents=True, exist_ok=True)

    jobs = list(bible.get("generation_jobs") or [])
    if not jobs:
        try:
            jobs = compile_generation_jobs(bible) if bible.get("shots") else []
        except Exception:
            jobs = []

    if jobs:
        clips_dir = root / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        board = export_prompts_markdown(bible)
        (root / "prompt_board.md").write_text(board, encoding="utf-8")
        board_html = export_prompts_html(bible)
        (root / "prompt_board.html").write_text(board_html, encoding="utf-8")
        for job in jobs:
            cid = str(job.get("clip_id") or job.get("shot_id") or "clip")
            safe = re.sub(r'[<>:"/\\|?*]', "_", cid)
            from film_pipeline.runtime.prompt_writer import format_prompt_for_delivery

            free_en = format_prompt_for_delivery(
                job.get("actor_free_prompt") or job.get("actor_free_prompt_en") or ""
            )
            guided_en = format_prompt_for_delivery(
                job.get("director_guided_prompt")
                or job.get("director_guided_prompt_en")
                or ""
            )
            free_zh = format_prompt_for_delivery(job.get("actor_free_prompt_zh") or "")
            guided_zh = format_prompt_for_delivery(
                job.get("director_guided_prompt_zh") or ""
            )
            # UTF-8 text with real newlines (auto wrap) — open in any editor, no horizontal drag
            (clips_dir / f"{safe}_actor_free.en.txt").write_text(free_en, encoding="utf-8")
            (clips_dir / f"{safe}_director_guided.en.txt").write_text(
                guided_en, encoding="utf-8"
            )
            (clips_dir / f"{safe}_actor_free.zh.txt").write_text(free_zh, encoding="utf-8")
            (clips_dir / f"{safe}_director_guided.zh.txt").write_text(
                guided_zh, encoding="utf-8"
            )

    # Assets always land in the same project delivery folder when present
    has_assets = bool(bible.get("asset_bible"))
    if has_assets:
        export_assets_into_dir(bible, root)

    readme_lines = [
        f"项目：{project_id}",
        f"标题：{meta.get('title') or project_id}",
        "",
        "本文件夹 = 项目交付目录（文件夹名 = 项目名）",
        "",
    ]
    if jobs:
        readme_lines += [
            "prompt_board.html   — 浏览器打开：每段提示词带「复制」按钮 + 自动换行",
            "prompt_board.md     — 镜头最终提示词板（中英均可投喂，已自动换行）",
            "clips/              — 每镜 clip 纯文本（已自动换行，适合脚本/编辑器）",
            "  *_director_guided.en.txt  — 英文导演版（可直接投喂）",
            "  *_director_guided.zh.txt  — 中文导演版（可直接投喂）",
            "  *_actor_free.en.txt       — 英文自由发挥版",
            "  *_actor_free.zh.txt       — 中文自由发挥版",
            "",
            "每段 clip/package 为 ≤15/30s 的生成请求；段内时间轴分镜，模型自行切镜。",
            "全片时长统计见 prompt_board.md / .html 文末。",
            "",
        ]
    if has_assets:
        readme_lines += [
            "assets/             — 资产设定提示词（必进交付）",
            "  asset_board.md    — 人读总板",
            "  asset_bible.json  — 完整 JSON",
            "  characters/       — 人物三视图 sheet（英文主稿）",
            "  props/            — 道具设定",
            "  sets/             — 场景设定",
            "",
        ]
    readme_lines += [
        "内部状态仍在 film_pipeline/bible/projects/<项目名>/",
        "",
    ]
    (root / "README.txt").write_text("\n".join(readme_lines), encoding="utf-8")
    return root
