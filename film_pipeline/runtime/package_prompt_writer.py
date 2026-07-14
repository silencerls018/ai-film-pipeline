"""
Write one generation job per package: multi-beat timeline inside max_clip.

Model cuts internally (0-2s / 3-12s / …) — smoother than one-shot-one-job.
"""

from __future__ import annotations

from typing import Any

import re

from film_pipeline.runtime.prompt_writer import (
    MAX_DIALOGUE_LINES_PER_SHOT,
    format_prompt_for_delivery,
    format_subject_refs_en,
    format_subject_refs_zh,
    _build_subject_image_refs,
    _compose_look_blocks,
    _ATMOSPHERE_EN,
    _ATMOSPHERE_ZH,
    _SIZE_EN,
    _SIZE_ZH,
    _clean_move_en,
    _clean_move_zh,
)
from film_pipeline.runtime.shot_locale import (
    has_cjk,
    resolve_dramatic_beat_en,
    resolve_dramatic_beat_zh,
    resolve_subject_en,
    resolve_subject_zh,
)


def _dialogue_for_beat(bible: dict[str, Any], beat: dict[str, Any]) -> list[dict[str, str]]:
    linked = [str(t).strip() for t in (beat.get("linked_dialogue") or []) if str(t).strip()]
    if not linked:
        return []
    scene_id = beat.get("scene_id")
    catalog = []
    for block in bible.get("dialogue") or []:
        if scene_id and block.get("scene_id") != scene_id:
            continue
        for line in block.get("lines") or []:
            text = (line.get("text") or "").strip()
            char = str(line.get("character") or "").strip()
            if not text or char in {"NARRATION", "画外"}:
                continue
            catalog.append(
                {
                    "character": char,
                    "text": text,
                    "delivery": str(line.get("delivery") or "")[:80],
                }
            )
    out = []
    for t in linked:
        for ln in catalog:
            if t in ln["text"] or ln["text"] in t:
                out.append(ln)
                break
        else:
            out.append({"character": "Speaker", "text": t, "delivery": ""})
    # dedupe
    seen = set()
    uniq = []
    for ln in out:
        k = (ln["character"], ln["text"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(ln)
    return uniq[:MAX_DIALOGUE_LINES_PER_SHOT]


def _format_range(a: float, b: float, *, lang: str = "zh") -> str:
    def _s(x: float) -> str:
        if abs(x - int(x)) < 1e-6:
            return str(int(x))
        return f"{x:.1f}".rstrip("0").rstrip(".")

    if lang == "en":
        return f"{_s(a)}-{_s(b)}s"
    return f"{_s(a)}-{_s(b)}秒"


def write_package_prompts(
    bible: dict[str, Any],
    package: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Build EN+ZH four-part prompts with internal timeline storyboard."""
    beats = package.get("beats") or []
    max_clip = float(package.get("max_clip_sec") or 15)
    total = float(package.get("duration_sec") or 0)
    style = (style_pack or {}).get("label") or (bible.get("meta") or {}).get("style_pack") or "cinematic"

    # Merge subjects from all beats for 图X cards
    fake_shot = {
        "shot_id": package.get("package_id"),
        "scene_id": (beats[0].get("scene_id") if beats else None),
        "subject": "、".join(
            str(b.get("subject") or "") for b in beats if b.get("subject")
        )[:80],
        "subject_en": ", ".join(
            str(b.get("subject_en") or "") for b in beats if b.get("subject_en")
        )[:120],
        "shot_size": beats[0].get("shot_size") if beats else "MS",
        "dramatic_beat": " / ".join(
            str(b.get("dramatic_beat") or "") for b in beats[:4]
        ),
        "dramatic_beat_en": " / ".join(
            str(b.get("dramatic_beat_en") or "") for b in beats[:4]
        ),
        "camera": (beats[0].get("camera") if beats else {}) or {},
        "look": (beats[0].get("look") if beats else {}) or {},
        "emotion": (beats[0].get("emotion") if beats else {}) or {},
        "linked_dialogue": [],
    }
    for b in beats:
        for t in b.get("linked_dialogue") or []:
            if t not in fake_shot["linked_dialogue"]:
                fake_shot["linked_dialogue"].append(t)

    refs = _build_subject_image_refs(bible, fake_shot)
    # Prefer short multi-subject labels from package beats
    if len(beats) >= 2:
        # rebuild simple refs: people + first set
        names_zh = []
        names_en = []
        for b in beats:
            sz = str(b.get("subject") or "")
            se = str(b.get("subject_en") or sz)
            for part in re_split_names(sz):
                if part and part not in names_zh:
                    names_zh.append(part)
            for part in re_split_names(se):
                if part and part not in names_en:
                    names_en.append(part)
        # keep first 4 as 图X
        if names_zh or names_en:
            refs = []
            nmax = max(len(names_zh), len(names_en), 1)
            for i in range(min(4, nmax)):
                nz = names_zh[i] if i < len(names_zh) else (names_en[i] if i < len(names_en) else f"主体{i+1}")
                ne = names_en[i] if i < len(names_en) else ""
                if not ne or has_cjk(ne):
                    ne = f"subject {i+1}"
                refs.append(
                    {
                        "role_en": "subject",
                        "role_zh": "主体",
                        "name_en": ne,
                        "name_zh": nz if not has_cjk(nz) or True else nz,
                        "detail_en": "",
                        "detail_zh": "",
                    }
                )

    # EN subject line must not mix CJK (video models / test contract)
    refs_en = []
    for i, r in enumerate(refs or []):
        ne = r.get("name_en") or f"subject {i+1}"
        if has_cjk(ne):
            ne = f"subject {i+1}"
        refs_en.append({**r, "name_en": ne})
    sub_en = format_subject_refs_en(refs_en or refs)
    sub_zh = format_subject_refs_zh(refs)

    # Camera: summarize from first beat + note internal cuts
    cam0 = (beats[0].get("camera") if beats else {}) or {}
    body = cam0.get("body") or "ARRI Alexa 35 (virtual cinematic look)"
    lens = cam0.get("lens_mm") or 35
    tstop = cam0.get("t_stop") or cam0.get("aperture") or "T2.0"
    gear_en = (
        f"{body}; {lens}mm, {tstop}; photoreal cinema. "
        f"Duration about {total:.0f}s (max {max_clip:.0f}s)."
    )
    gear_zh = (
        f"{body}；{lens}mm，{tstop}；写实电影。"
        f"本段约 {total:.0f} 秒（不超过 {max_clip:.0f} 秒）。"
    )

    look_blocks = _compose_look_blocks(
        bible,
        {
            "look": (beats[0].get("look") if beats else {}) or {},
            "scene_id": beats[0].get("scene_id") if beats else None,
            "performance": (beats[0].get("performance") if beats else {}) or {},
        },
        ((beats[0].get("performance") or {}).get("lighting_plan") if beats else {}) or {},
        object_shot=False,
    )
    light_en = look_blocks.get("look_block_en") or ""
    light_zh = look_blocks.get("look_block_zh") or ""

    # Timeline beats
    lines_en = []
    lines_en_free = []
    lines_zh = []
    for b in beats:
        a, e = float(b.get("t_start") or 0), float(b.get("t_end") or 0)
        rng_zh = _format_range(a, e, lang="zh")
        rng_en = _format_range(a, e, lang="en")
        beat_zh = b.get("dramatic_beat") or resolve_dramatic_beat_zh(b) or "动作"
        beat_en = b.get("dramatic_beat_en") or resolve_dramatic_beat_en(b) or "action"
        if has_cjk(beat_en):
            beat_en = "dramatic action"
        subj_zh = b.get("subject") or resolve_subject_zh(b) or ""
        subj_en = b.get("subject_en") or resolve_subject_en(b) or "subject"
        if has_cjk(subj_en):
            subj_en = "on-screen subject"
        size = b.get("shot_size") or ""
        size_en = _SIZE_EN.get(str(size), str(size))
        size_zh = _SIZE_ZH.get(str(size), str(size))
        emo = (b.get("emotion") or {}).get("primary") or ""
        atmos_en = _ATMOSPHERE_EN.get(str(emo), str(emo) if not has_cjk(str(emo)) else "tense")
        atmos_zh = _ATMOSPHERE_ZH.get(str(emo), str(emo))
        cam = b.get("camera") or {}
        move_en = _clean_move_en(cam)
        move_zh = _clean_move_zh(cam)
        dlg = _dialogue_for_beat(bible, b)
        # EN prompts: keep exact Chinese dialogue in quotes (common for CN models);
        # also provide romanized speaker labels without CJK outside quotes when needed.
        dlg_en_parts = []
        for d in dlg:
            ch = d["character"]
            # keep Chinese character name as in script (models handling CN dialogue expect it)
            deliv = d.get("delivery") or ""
            if deliv and deliv not in {"按原剧本自然表演", ""} and not has_cjk(deliv):
                dlg_en_parts.append(f'{ch} ({deliv}) says: "{d["text"]}"')
            else:
                dlg_en_parts.append(f'{ch} says: "{d["text"]}"')
        dlg_en = " ".join(dlg_en_parts)
        dlg_zh = "".join(
            f'{d["character"]}'
            + (f'（{d["delivery"]}）' if d.get("delivery") and d["delivery"] not in {"按原剧本自然表演", ""} else "")
            + f'说：「{d["text"]}」'
            for d in dlg
        )
        # Match product sample: "0-2秒，动作…主体1（情绪：…）"
        lines_en.append(
            f"{rng_en}, {beat_en}; focus {subj_en}; framing {size_en}, {move_en}; "
            f"mood {atmos_en}"
            + (f"; dialogue: {dlg_en}" if dlg_en else "")
            + "."
        )
        # free-EN: no CJK glyphs (some pipelines require pure EN free prompts)
        dlg_en_ascii = ""
        if dlg:
            dlg_en_ascii = " ".join(
                f'{i+1}) speaker delivers line' for i, _ in enumerate(dlg)
            )
        lines_en_free.append(
            f"{rng_en}, {beat_en}; focus {subj_en}; framing {size_en}, {move_en}; "
            f"mood {atmos_en}"
            + (f"; spoken exchange present ({dlg_en_ascii})" if dlg else "")
            + "."
        )
        lines_zh.append(
            f"{rng_zh}，{beat_zh}，画面主体：{subj_zh}，景别{size_zh}，运镜{move_zh}，"
            f"主体情绪：{atmos_zh}"
            + (f"，台词：{dlg_zh}" if dlg_zh else "")
            + "。"
        )

    # Strip CJK from EN light block if any leaked
    light_en_clean = light_en
    if has_cjk(light_en_clean):
        light_en_clean = re.sub(r"[\u4e00-\u9fff]+", " ", light_en_clean)
        light_en_clean = re.sub(r"\s+", " ", light_en_clean).strip()

    # Closing: look + this segment duration only (no pipeline meta for the video model)
    close_en = (
        f"{light_en_clean} Overall look: {style}; soft readable light, clear subject IDs, "
        f"smooth cuts, natural flow. Duration {total}s."
    )
    close_zh = (
        f"{light_zh}整体画面氛围：{style}；光影细腻，节奏张弛有度，"
        f"镜头切换流畅，突出主体辨识度，自然流畅有质感。"
        f"本段时长 {total} 秒。"
    )
    # Just the timeline — like the product sample (0-2s / 3-12s / …). No "model cuts" meta.
    story_en = "\n".join(lines_en) + f"\n{close_en}"
    story_zh = "故事线为：\n" + "\n".join(lines_zh) + f"\n{close_zh}"
    story_en_free = "\n".join(lines_en_free) + f"\n{close_en}"
    story_zh_free = "故事线为：\n" + "\n".join(lines_zh) + f"\n{close_zh}"

    sfx_en = (
        "SFX only: diegetic action and environment; clear dialogue when present. "
        "No music, no score, no BGM. No subtitles, no watermark, no UI."
    )
    sfx_zh = (
        "只保留音效：环境与动作声；有对白则口型与声线清晰。"
        "不要配乐、不要BGM。不要字幕、不要水印、不要界面文字。"
    )

    free_en = format_prompt_for_delivery(
        f"1. SUBJECT: {sub_en}\n"
        f"2. CAMERA GEAR & PARAMETERS: {gear_en}\n"
        f"3. STORYLINE: {story_en_free}\n"
        f"4. AUDIO: {sfx_en}"
    )
    guided_en = format_prompt_for_delivery(
        f"1. SUBJECT: {sub_en}\n"
        f"2. CAMERA GEAR & PARAMETERS: {gear_en}\n"
        f"3. STORYLINE: {story_en}\n"
        f"4. AUDIO: {sfx_en}"
    )
    free_zh = format_prompt_for_delivery(
        f"1. 指定主体：{sub_zh}\n"
        f"2. 摄影设备与参数：{gear_zh}\n"
        f"3. 故事线：{story_zh_free}\n"
        f"4. 音效：{sfx_zh}"
    )
    guided_zh = format_prompt_for_delivery(
        f"1. 指定主体：{sub_zh}\n"
        f"2. 摄影设备与参数：{gear_zh}\n"
        f"3. 故事线：{story_zh}\n"
        f"4. 音效：{sfx_zh}"
    )

    return {
        "actor_free_prompt": free_en,
        "director_guided_prompt": guided_en,
        "actor_free_prompt_zh": free_zh,
        "director_guided_prompt_zh": guided_zh,
        "writer": "package_timeline",
    }


def re_split_names(s: str) -> list[str]:
    s = (s or "").strip()
    if not s:
        return []
    parts = re.split(r"[、，,/]|和|与|及", s)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) <= 24]
