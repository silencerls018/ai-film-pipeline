"""
Timing Planner — budget dialogue, holds, and camera moves under model clip caps.

Key ideas:
1. A *scene* can be minutes long; a *generation clip* cannot exceed model max
   (default 30s, configurable per profile).
2. Each shot's needed duration is estimated from:
   dialogue reading time + silence beats + movement minimum + pre/post holds.
3. If a shot needs longer than max_clip_sec, split into ordered clips with
   stitch metadata (for later concat / extend).
4. Director should prefer multi-shot coverage; this planner enforces physics
   of speech and motion so prompts request honest durations.
"""

from __future__ import annotations

import math
import re
from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore


def _load_timing_kb(store: KnowledgeStore | None = None) -> dict[str, Any]:
    store = store or KnowledgeStore()
    return {
        "models": store.load_json("timing/model_limits.json"),
        "speech": store.load_json("timing/speaking_rates.json"),
        "moves": store.load_json("timing/move_durations.json"),
        "holds": store.load_json("timing/holds.json"),
    }


def detect_lang(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    return "en"


def estimate_line_sec(text: str, delivery: str | None = None, speech: dict | None = None) -> float:
    speech = speech or _load_timing_kb()["speech"]
    text = (text or "").strip()
    if not text:
        return 0.0

    lang = detect_lang(text)
    pace = "normal"
    d = (delivery or "").lower()
    if any(k in d for k in ("慢", "压", "轻声", "slow", "whisper", "pause")):
        pace = "dramatic"
    elif any(k in d for k in ("快", "急", "fast", "rush")):
        pace = "fast"

    if lang == "zh":
        cfg = speech["zh"]
        rate_key = {
            "normal": "chars_per_sec_normal",
            "dramatic": "chars_per_sec_dramatic",
            "fast": "chars_per_sec_fast",
            "slow": "chars_per_sec_slow",
        }.get(pace, "chars_per_sec_normal")
        # count CJK + alnum roughly as speaking units
        chars = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))
        base = chars / max(cfg.get(rate_key, 4.0), 0.5)
        pause = 0.0
        for p, sec in (cfg.get("punctuation_pause_sec") or {}).items():
            pause += text.count(p) * float(sec)
        return max(float(cfg.get("min_line_sec", 0.8)), base + pause)

    # English fallback
    cfg = speech["en"]
    words = max(1, len(re.findall(r"[A-Za-z0-9']+", text)))
    rate = {
        "normal": cfg.get("words_per_sec_normal", 2.5),
        "dramatic": cfg.get("words_per_sec_dramatic", 1.5),
        "fast": cfg.get("words_per_sec_normal", 2.5) * 1.3,
        "slow": cfg.get("words_per_sec_slow", 1.8),
    }.get(pace, 2.5)
    return max(float(cfg.get("min_line_sec", 0.8)), words / max(rate, 0.5))


def dialogue_lines_for_shot(bible: dict[str, Any], shot: dict[str, Any]) -> list[dict[str, Any]]:
    linked = shot.get("linked_dialogue") or []
    scene_id = shot.get("scene_id")
    matched: list[dict[str, Any]] = []
    for block in bible.get("dialogue") or []:
        if scene_id and block.get("scene_id") != scene_id:
            continue
        silence = block.get("silence_beats_ms") or []
        for i, line in enumerate(block.get("lines") or []):
            text = line.get("text") or ""
            if linked:
                if any(t in text or text in t for t in linked):
                    item = dict(line)
                    if i < len(silence):
                        item["_silence_after_ms"] = silence[i]
                    matched.append(item)
            # If shot has no linked dialogue, only attach for reaction/coverage
            # when shot size is dialogue-friendly and whose_pov matches speaker — skip auto dump
    if not matched and linked:
        for block in bible.get("dialogue") or []:
            for line in block.get("lines") or []:
                if line.get("text") in linked:
                    matched.append(dict(line))
    return matched


def estimate_dialogue_bundle_sec(
    lines: list[dict[str, Any]], speech: dict[str, Any]
) -> tuple[float, list[dict[str, Any]]]:
    gap = float(speech.get("breath_gap_between_lines_sec", 0.25))
    total = 0.0
    breakdown: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        sec = estimate_line_sec(line.get("text") or "", line.get("delivery"), speech)
        silence_ms = line.get("_silence_after_ms")
        silence_sec = (float(silence_ms) / 1000.0) if silence_ms is not None else 0.0
        if i < len(lines) - 1:
            silence_sec = max(silence_sec, gap)
        total += sec + silence_sec
        breakdown.append(
            {
                "character": line.get("character"),
                "text": line.get("text"),
                "speak_sec": round(sec, 2),
                "silence_after_sec": round(silence_sec, 2),
            }
        )
    return total, breakdown


def move_budget_sec(shot: dict[str, Any], moves: dict[str, Any]) -> float:
    cam = shot.get("camera") or {}
    mov = cam.get("movement") or {}
    mtype = (mov.get("type") or "static_hold").strip()
    speed = (mov.get("speed") or "").lower()
    # Exact key, slug, or fuzzy contains (Excel names like "Slow Dolly In")
    rule = moves.get(mtype) or moves.get("default")
    if rule is None or rule is moves.get("default"):
        key_l = mtype.lower().replace(" ", "_")
        for k, v in moves.items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            if k.lower() == key_l or key_l in k.lower() or k.lower() in key_l:
                rule = v
                break
            en = str(v.get("en") or "").lower()
            if en and (en == mtype.lower() or mtype.lower() in en):
                rule = v
                break
    if not isinstance(rule, dict):
        rule = {"min_sec": 2.0, "preferred_sec": 3.5}
    # Heuristic for catalog free-text moves not in move_durations.json
    ml = mtype.lower()
    if "preferred_sec" not in rule or rule is moves.get("default"):
        if any(x in ml for x in ("static", "locked", "hold", "freeze")):
            rule = {"min_sec": 1.5, "preferred_sec": 2.5}
        elif any(x in ml for x in ("dolly", "push", "truck", "crane", "orbit", "arc")):
            rule = {"min_sec": 3.5, "preferred_sec": 5.0}
        elif any(x in ml for x in ("whip", "crash", "snap", "shake")):
            rule = {"min_sec": 1.0, "preferred_sec": 1.8}
        elif any(x in ml for x in ("pan", "tilt", "roll")):
            rule = {"min_sec": 2.0, "preferred_sec": 3.5}
    sec = float(rule.get("preferred_sec", rule.get("min_sec", 3.0)))
    if "very_slow" in speed or speed == "very_slow":
        sec *= 1.25
    elif speed in {"fast", "quick"}:
        sec = max(float(rule.get("min_sec", 1.5)), sec * 0.7)
    return sec


def hold_budget_sec(shot: dict[str, Any], holds: dict[str, Any], has_dialogue: bool) -> tuple[float, float]:
    pre = float(holds.get("pre_roll_sec", 0.4))
    post = float(holds.get("default_tail_hold_sec", 0.5))
    size = shot.get("shot_size") or ""
    if size == "INSERT":
        pre = 0.2
        post = 0.2
    if has_dialogue:
        post = max(post, float(holds.get("post_line_reaction_sec", 0.6)))
    emo = (shot.get("emotion") or {}).get("primary") or ""
    if emo in {"grief", "oppression", "revelation", "dread"}:
        post += 0.4
    return pre, post


def estimate_shot_timing(
    bible: dict[str, Any],
    shot: dict[str, Any],
    kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kb = kb or _load_timing_kb()
    speech, moves, holds = kb["speech"], kb["moves"], kb["holds"]
    lines = dialogue_lines_for_shot(bible, shot)
    dialogue_sec, line_break = estimate_dialogue_bundle_sec(lines, speech)
    move_sec = move_budget_sec(shot, moves)
    pre, post = hold_budget_sec(shot, holds, has_dialogue=bool(lines))

    size = shot.get("shot_size") or ""
    if size == "INSERT" and not lines:
        # inserts are short; motion still applies lightly
        total = max(
            float(holds.get("insert_preferred_sec", 2.0)),
            min(move_sec, float(holds.get("insert_preferred_sec", 2.0)) + 0.5),
        )
        components = {
            "pre_roll_sec": 0.15,
            "dialogue_sec": 0.0,
            "move_sec": round(min(move_sec, total), 2),
            "post_hold_sec": 0.15,
            "method": "insert_short",
        }
    elif lines:
        # For dialogue coverage: duration must cover speech; move runs in parallel
        # but slow moves need at least their min window overlapping the line.
        parallel = max(dialogue_sec, move_sec)
        total = pre + parallel + post
        components = {
            "pre_roll_sec": round(pre, 2),
            "dialogue_sec": round(dialogue_sec, 2),
            "move_sec": round(move_sec, 2),
            "post_hold_sec": round(post, 2),
            "method": "max(dialogue, move) + holds",
        }
    else:
        # pure visual / reaction
        total = pre + move_sec + post
        components = {
            "pre_roll_sec": round(pre, 2),
            "dialogue_sec": 0.0,
            "move_sec": round(move_sec, 2),
            "post_hold_sec": round(post, 2),
            "method": "move + holds",
        }

    return {
        "needed_sec": round(total, 2),
        "components": components,
        "dialogue_lines": line_break,
        "linked_line_count": len(lines),
    }


def split_into_clips(
    needed_sec: float,
    max_clip_sec: float,
    min_clip_sec: float,
    overlap_sec: float,
    shot_id: str,
) -> list[dict[str, Any]]:
    """Split a long needed duration into ordered clips ≤ max_clip_sec."""
    needed_sec = max(needed_sec, min_clip_sec)
    if needed_sec <= max_clip_sec:
        return [
            {
                "clip_id": f"{shot_id}_c01",
                "index": 1,
                "duration_sec": round(needed_sec, 2),
                "timeline_start_sec": 0.0,
                "timeline_end_sec": round(needed_sec, 2),
                "stitch": "single",
                "role": "full_shot",
            }
        ]

    clips: list[dict[str, Any]] = []
    # Effective advance per clip after overlap
    step = max(max_clip_sec - overlap_sec, min_clip_sec)
    t = 0.0
    idx = 1
    while t < needed_sec - 1e-6:
        remaining = needed_sec - t
        dur = min(max_clip_sec, remaining)
        if dur < min_clip_sec and clips:
            # absorb tiny tail into previous by extending if possible
            prev = clips[-1]
            extra = needed_sec - prev["timeline_start_sec"]
            if extra <= max_clip_sec:
                prev["duration_sec"] = round(extra, 2)
                prev["timeline_end_sec"] = round(needed_sec, 2)
                prev["stitch"] = "extended_tail"
                break
        clip = {
            "clip_id": f"{shot_id}_c{idx:02d}",
            "index": idx,
            "duration_sec": round(dur, 2),
            "timeline_start_sec": round(t, 2),
            "timeline_end_sec": round(t + dur, 2),
            "stitch": "first" if idx == 1 else "continue",
            "overlap_prev_sec": overlap_sec if idx > 1 else 0.0,
            "role": "segment",
            "extend_from_clip": clips[-1]["clip_id"] if clips else None,
        }
        clips.append(clip)
        if t + dur >= needed_sec - 1e-6:
            break
        t += step
        idx += 1
        if idx > 40:
            break
    if clips:
        clips[-1]["stitch"] = "last" if len(clips) > 1 else "single"
        if len(clips) > 1:
            clips[0]["stitch"] = "first"
    return clips


def apply_timing_plan(
    bible: dict[str, Any],
    model_profile: str | None = None,
    store: KnowledgeStore | None = None,
) -> dict[str, Any]:
    """
    Mutates shots with timing + clips; writes bible['timing_plan'].
    Returns the same bible.
    """
    store = store or KnowledgeStore()
    kb = _load_timing_kb(store)
    models = kb["models"]
    meta = bible.get("meta") or {}
    # User must have chosen 15 or 30 before pipeline work (stored on meta).
    from film_pipeline.runtime.clip_profile import (
        max_clip_from_profile,
        normalize_max_clip,
        profile_for_max_clip,
    )

    if meta.get("max_clip_sec") is not None:
        max_clip_i = normalize_max_clip(meta["max_clip_sec"])
        profile_id = profile_for_max_clip(max_clip_i)
    else:
        profile_id = (
            model_profile
            or meta.get("model_profile")
            or models.get("default_model_profile")
            or "max_30s"
        )
        max_clip_i = max_clip_from_profile(profile_id) or 30
        max_clip_i = normalize_max_clip(max_clip_i)
        profile_id = profile_for_max_clip(max_clip_i)

    profile = (models.get("profiles") or {}).get(profile_id) or {
        "max_clip_sec": max_clip_i,
        "min_clip_sec": 2,
        "preferred_clip_sec": 6 if max_clip_i == 15 else 8,
    }
    max_clip = float(profile.get("max_clip_sec", max_clip_i))
    min_clip = float(profile.get("min_clip_sec", 2))
    preferred = float(profile.get("preferred_clip_sec", 6 if max_clip_i == 15 else 8))
    overlap = float(kb["holds"].get("overlap_stitch_sec", 0.5))

    scene_totals: dict[str, float] = {}
    warnings: list[dict[str, Any]] = []
    shot_rows: list[dict[str, Any]] = []

    for shot in bible.get("shots") or []:
        est = estimate_shot_timing(bible, shot, kb)
        needed = float(est["needed_sec"])
        # Soft prefer not to design single shots absurdly long for AI:
        # if needed > max and no dialogue forcing it, clamp move-heavy shots
        # still split rather than silently cut speech.
        clips = split_into_clips(
            needed_sec=needed,
            max_clip_sec=max_clip,
            min_clip_sec=min_clip,
            overlap_sec=overlap,
            shot_id=str(shot.get("shot_id") or "SHOT"),
        )
        # generation duration for primary clip request
        primary_dur = clips[0]["duration_sec"] if clips else needed
        shot["duration_sec"] = round(needed, 2)
        shot["timing"] = {
            **est,
            "model_profile": profile_id,
            "max_clip_sec": max_clip,
            "preferred_clip_sec": preferred,
            "fits_single_clip": len(clips) == 1,
            "clip_count": len(clips),
        }
        shot["generation_clips"] = clips

        if len(clips) > 1:
            warnings.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "type": "split_for_model_cap",
                    "message": (
                        f"需要 {needed}s，超过单 clip 上限 {max_clip}s，"
                        f"已拆成 {len(clips)} 段，成片需拼接/extend"
                    ),
                }
            )
        if needed > preferred * 1.5 and len(clips) == 1:
            warnings.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "type": "long_for_ai_stability",
                    "message": (
                        f"单镜 {needed}s 偏长，虽未超 cap，建议导演拆成正反打/反应镜以提高生成稳定性"
                    ),
                }
            )

        sid = shot.get("scene_id") or "UNKNOWN"
        scene_totals[sid] = round(scene_totals.get(sid, 0.0) + needed, 2)
        shot_rows.append(
            {
                "shot_id": shot.get("shot_id"),
                "scene_id": sid,
                "needed_sec": needed,
                "clip_count": len(clips),
                "dialogue_sec": est["components"].get("dialogue_sec"),
                "move_sec": est["components"].get("move_sec"),
            }
        )

    total_film = round(sum(scene_totals.values()), 2)
    bible["timing_plan"] = {
        "model_profile": profile_id,
        "max_clip_sec": max_clip,
        "min_clip_sec": min_clip,
        "preferred_clip_sec": preferred,
        "scene_totals_sec": scene_totals,
        "film_total_sec": total_film,
        "film_total_min": round(total_film / 60.0, 2),
        "shots": shot_rows,
        "warnings": warnings,
        "rules": {
            "dialogue_and_move": "并行取 max(台词时长, 运镜最小时长) + 头尾留白",
            "scene_vs_clip": "场次可很长；每个 generation clip ≤ max_clip_sec",
            "split": "单镜超时 → generation_clips[] 顺序生成再拼接",
        },
    }
    meta = bible.setdefault("meta", {})
    meta["model_profile"] = profile_id
    meta["max_clip_sec"] = int(max_clip)
    return bible


def format_timing_report(bible: dict[str, Any]) -> str:
    plan = bible.get("timing_plan") or {}
    lines = [
        f"# Timing Plan — {(bible.get('meta') or {}).get('title', '')}",
        "",
        f"- Model profile: `{plan.get('model_profile')}`",
        f"- Max clip: **{plan.get('max_clip_sec')}s**",
        f"- Preferred clip: {plan.get('preferred_clip_sec')}s",
        f"- Film total: **{plan.get('film_total_sec')}s** ({plan.get('film_total_min')} min)",
        "",
        "## Scene totals",
    ]
    for sid, sec in (plan.get("scene_totals_sec") or {}).items():
        lines.append(f"- {sid}: {sec}s")
    lines += ["", "## Shots", ""]
    for shot in bible.get("shots") or []:
        t = shot.get("timing") or {}
        comp = t.get("components") or {}
        lines.append(
            f"### {shot.get('shot_id')} — {shot.get('duration_sec')}s "
            f"({t.get('clip_count', 1)} clip(s))"
        )
        lines.append(
            f"- dialogue={comp.get('dialogue_sec')}s, move={comp.get('move_sec')}s, "
            f"pre={comp.get('pre_roll_sec')}s, post={comp.get('post_hold_sec')}s"
        )
        for c in shot.get("generation_clips") or []:
            lines.append(
                f"  - `{c.get('clip_id')}` {c.get('duration_sec')}s "
                f"[{c.get('timeline_start_sec')}→{c.get('timeline_end_sec')}] "
                f"stitch={c.get('stitch')}"
            )
        lines.append("")
    if plan.get("warnings"):
        lines += ["## Warnings", ""]
        for w in plan["warnings"]:
            lines.append(f"- **{w.get('shot_id')}** [{w.get('type')}]: {w.get('message')}")
    return "\n".join(lines)
