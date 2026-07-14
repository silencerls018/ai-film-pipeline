"""
Write one generation job per package: multi-beat timeline inside max_clip.

Industrial rules for storyline text:
  - Integer seconds only
  - One visible action per short window (≤3s)
  - Dialogue must fit the window; never invent "Speaker"
  - No pipeline jargon (INSERT / 景别码 / 主体情绪键)
  - No music titles
"""

from __future__ import annotations

import re
from typing import Any

from film_pipeline.runtime.prompt_writer import (
    MAX_DIALOGUE_LINES_PER_SHOT,
    format_prompt_for_delivery,
    format_subject_refs_en,
    format_subject_refs_zh,
    _build_subject_image_refs,
    _compose_look_blocks,
    _clean_move_en,
    _clean_move_zh,
)
from film_pipeline.runtime.shot_locale import (
    has_cjk,
    resolve_dramatic_beat_en,
    resolve_dramatic_beat_zh,
    resolve_subject_en,
    resolve_subject_zh,
    strip_music_mentions,
)

# Spoken Chinese ≈ 3.5–4.5 chars/sec; keep conservative budget for video models
_CHARS_PER_SEC_ZH = 3.5
_WORDS_PER_SEC_EN = 2.2

_PIPELINE_JARGON_RE = re.compile(
    r"INSERT|ECU|MCU|EWS|(?<![A-Za-z])WS(?![A-Za-z])|(?<![A-Za-z])MS(?![A-Za-z])|(?<![A-Za-z])CU(?![A-Za-z])|"
    r"景别|插入细节镜头|主体情绪|画面主体：|dramatic_beat|shot_size|"
    r"linked_dialogue|FilmBible|知识库|Look岗|摄影执行|"
    r"镜头组|特写：",
    re.I,
)

_KNOWN_SPEAKERS = (
    "技术员A",
    "技术员B",
    "Ananke",
    "Anake",
    "高岩",
    "大刘",
)


def _sec_int(x: float | int | None) -> int:
    try:
        return max(0, int(round(float(x or 0))))
    except (TypeError, ValueError):
        return 0


def _format_range(a: float, b: float, *, lang: str = "zh") -> str:
    ia, ib = _sec_int(a), _sec_int(b)
    if ib < ia:
        ib = ia
    # Ensure at least 1s span for readability when equal after round
    if ib == ia and ib > 0:
        pass
    if lang == "en":
        return f"{ia}-{ib}s"
    return f"{ia}-{ib}秒"


def _window_sec(a: float, b: float) -> int:
    ia, ib = _sec_int(a), _sec_int(b)
    return max(1, ib - ia) if ib > ia else max(1, ib or 1)


def _strip_pipeline_jargon(text: str) -> str:
    s = _PIPELINE_JARGON_RE.sub("", text or "")
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"[，,]{2,}", "，", s)
    return s.strip(" ，,.;；")


def _strip_spoken_narration(text: str, *, lang: str = "zh") -> str:
    """Remove 'Ananke称…' / 'X说道' style narration from visual beats."""
    s = text or ""
    if lang == "zh":
        s = re.sub(
            r"(技术员A|技术员B|Ananke|Anake|高岩)[（(][^）)]*[）)]?"
            r"(称|说|道|断言|低声|嘶吼|问)[^。；;]*[。；;]?",
            "",
            s,
        )
        s = re.sub(r"(称|说道|低声说|断言)[：:]?「[^」]*」", "", s)
        s = re.sub(r"(称|说道)[：:]?[^，。；]{4,}", "", s)
    else:
        s = re.sub(
            r"\b(Ananke|Gao Yan|Tech(?:nician)?\s*[AB]?)\b[^.]{0,40}\b(says|states|claims)\b[^.]*\.?",
            "",
            s,
            flags=re.I,
        )
    return re.sub(r"\s{2,}", " ", s).strip(" ，,.;；")


def _clip_for_window(text: str, window_sec: int, *, lang: str = "zh") -> str:
    """Hard budget: short windows only keep one short clause."""
    s = strip_music_mentions(text, lang=lang)
    s = _strip_pipeline_jargon(s)
    if window_sec <= 3:
        s = _strip_spoken_narration(s, lang=lang)
    s = re.sub(r"\s+", " ", (s or "").strip())
    if not s:
        return s

    if window_sec <= 2:
        max_chars = 26 if lang == "zh" else 44
    elif window_sec <= 3:
        max_chars = 36 if lang == "zh" else 64
    elif window_sec <= 5:
        max_chars = int(window_sec * (_CHARS_PER_SEC_ZH if lang == "zh" else 8))
    else:
        max_chars = int(window_sec * (_CHARS_PER_SEC_ZH if lang == "zh" else 10))
        max_chars = min(max_chars, 120 if lang == "zh" else 180)

    if len(s) <= max_chars:
        return s

    # Prefer cut at punctuation
    cut = s[:max_chars]
    for sep in ("。", "；", "！", "？", "…", ";", ".", "!", "?", "，", ","):
        i = cut.rfind(sep)
        if i >= max(8, max_chars // 3):
            return cut[: i + (0 if sep in "，," else 1)].strip(" ，,")
    return cut.rstrip(" ，,") + ("…" if lang == "zh" else "...")


def _parse_linked_line(raw: str) -> tuple[str, str]:
    """Return (character, text). Never returns Speaker."""
    t = (raw or "").strip()
    if not t:
        return "", ""
    # Character：text / Character: text
    m = re.match(
        r"^(技术员A|技术员B|Ananke|Anake|高岩|大刘|[A-Za-z\u4e00-\u9fff]{1,12})"
        r"\s*[：:]\s*(.+)$",
        t,
        re.S,
    )
    if m:
        sp, body = m.group(1).strip(), m.group(2).strip()
        if sp == "Anake":
            sp = "Ananke"
        if sp in {"Speaker", "NARRATION", "画外", "特写"} or sp.startswith("镜头"):
            return "", body
        return sp, body
    # Infer speaker from known names inside string
    for sp in _KNOWN_SPEAKERS:
        if t.startswith(sp):
            rest = t[len(sp) :].lstrip(" ：:")
            return ("Ananke" if sp == "Anake" else sp), rest or t
    return "", t


def _dialogue_for_beat(
    bible: dict[str, Any], beat: dict[str, Any], *, window_sec: int
) -> list[dict[str, str]]:
    linked = [str(t).strip() for t in (beat.get("linked_dialogue") or []) if str(t).strip()]
    if not linked:
        return []

    # Short windows: do not force full dialogue (can't be spoken)
    if window_sec <= 2:
        return []

    catalog: list[dict[str, str]] = []
    scene_id = beat.get("scene_id")
    blocks = bible.get("dialogue") or []
    # Prefer matching scene, else all blocks (passthrough often uses sc_all)
    ordered = []
    for block in blocks:
        if scene_id and block.get("scene_id") == scene_id:
            ordered.insert(0, block)
        else:
            ordered.append(block)
    for block in ordered or blocks:
        for line in block.get("lines") or []:
            text = (line.get("text") or "").strip()
            char = str(line.get("character") or "").strip()
            if not text or char in {"NARRATION", "画外", "Speaker", "特写"}:
                continue
            if char.startswith("镜头"):
                continue
            if char == "Anake":
                char = "Ananke"
            catalog.append(
                {
                    "character": char,
                    "text": text,
                    "delivery": str(line.get("delivery") or "")[:60],
                }
            )

    def _clean_line_text(text: str) -> str:
        t = (text or "").strip()
        # drop stage glue after closing quote / period
        t = re.split(
            r"[”\"]\s*(?=屏幕|主控|潜水器|高岩|技术员|强光|整片|音箱|对讲)",
            t,
            maxsplit=1,
        )[0].strip()
        t = re.split(
            r"(?<=[。！？])\s*(?=屏幕|主控|潜水器|强光|整片|音箱显示器)",
            t,
            maxsplit=1,
        )[0].strip()
        return t.strip(" \t\"'“”「」")

    out: list[dict[str, str]] = []
    # NEVER truncate script dialogue. Chinese stays Chinese, full sentence.
    # Only omit on ultra-short visual windows (≤2s); timing should give dialogue plates ≥4s.
    for raw in linked:
        sp, body = _parse_linked_line(raw)
        body = _clean_line_text(body)
        hit: dict[str, str] | None = None
        for ln in catalog:
            lt = _clean_line_text(ln["text"])
            if body and (body in lt or lt in body or body[:16] in lt):
                hit = {**ln, "text": lt}
                break
            if sp and ln["character"] == sp and body and body[:12] in lt:
                hit = {**ln, "text": lt}
                break
        if not hit:
            if not body:
                continue
            if not sp:
                subj = str(beat.get("subject") or "")
                for name in _KNOWN_SPEAKERS:
                    if name in subj or name in body[:20]:
                        sp = "Ananke" if name == "Anake" else name
                        break
            if not sp:
                continue
            hit = {"character": sp, "text": body, "delivery": ""}
            for ln in catalog:
                lt = _clean_line_text(ln["text"])
                if ln["character"] == sp and (
                    body in lt or lt in body or body[:20] in lt
                ):
                    hit = {**ln, "text": lt}
                    break

        text = _clean_line_text(hit.get("text") or "")
        if not text:
            continue
        if window_sec <= 2:
            # pure flash plate — do not put speech (park upstream)
            continue

        out.append(
            {
                "character": hit["character"],
                "text": text,  # FULL original Chinese — no "…"
                "delivery": hit.get("delivery") or "",
            }
        )
        if len(out) >= MAX_DIALOGUE_LINES_PER_SHOT:
            break
    return out


def _size_as_visible_zh(size: str) -> str:
    m = {
        "EWS": "极远全景",
        "WS": "全景",
        "FS": "全身",
        "MS": "中景",
        "MCU": "中近景",
        "CU": "近景",
        "ECU": "大特写",
        "INSERT": "细节特写",
    }
    return m.get(str(size).upper(), "")


def _size_as_visible_en(size: str) -> str:
    m = {
        "EWS": "extreme wide",
        "WS": "wide shot",
        "FS": "full body",
        "MS": "medium shot",
        "MCU": "medium close-up",
        "CU": "close-up",
        "ECU": "extreme close-up",
        "INSERT": "detail insert",
    }
    return m.get(str(size).upper(), "")


def _compose_beat_zh(
    *,
    window_sec: int,
    beat_zh: str,
    subj_zh: str,
    size: str,
    move_zh: str,
    dlg: list[dict[str, str]],
) -> str:
    """
    Natural Chinese storyline clause for one window.
    Short window → one visible action only.
    """
    action = _clip_for_window(beat_zh, window_sec, lang="zh")
    # ≤3s: pure visible plate only — no leftover narration fragments
    if window_sec <= 3 and subj_zh:
        size_vis = _size_as_visible_zh(size)
        move = (move_zh or "").strip()
        move = re.sub(r"(static|locked|hold|固定机位)", "微移", move, flags=re.I)
        parts = []
        if size_vis:
            parts.append(f"{size_vis}扫过{subj_zh}" if window_sec <= 2 else f"{size_vis}对着{subj_zh}")
        else:
            parts.append(f"画面是{subj_zh}")
        if move and move not in {"", "—", "-"}:
            parts.append(move)
        # do NOT append residual beat text on ≤3s (source of Ananke/INSERT junk)
        line = "，".join(p for p in parts if p)
    else:
        size_vis = _size_as_visible_zh(size)
        move = (move_zh or "").strip()
        chunks = [action] if action else []
        if subj_zh and subj_zh not in (action or ""):
            chunks.append(f"焦点在{subj_zh}")
        if size_vis:
            chunks.append(size_vis)
        if move:
            chunks.append(move)
        line = "，".join(chunks)

    if dlg and window_sec > 2:
        dparts = []
        for d in dlg:
            ch = d["character"]
            tx = d["text"]
            dparts.append(f"{ch}说道：「{tx}」")
        line = line.rstrip("。，;； ") + "。" + "".join(dparts)
    else:
        line = line.rstrip("。，;； ") + "。"

    line = re.sub(r"[。]{2,}", "。", line)
    line = re.sub(r"，。", "。", line)
    line = re.sub(r"。，", "。", line)
    line = re.sub(r"，{2,}", "，", line)
    line = re.sub(r"；，", "；", line)
    return line


def _format_dlg_en(dlg: list[dict[str, str]]) -> str:
    """English track keeps Chinese dialogue text (script language)."""
    parts = []
    for d in dlg:
        ch = d["character"]
        tx = d["text"]
        parts.append(f'{ch} says: "{tx}"')
    return " ".join(parts)


def _compose_beat_en(
    *,
    window_sec: int,
    beat_en: str,
    subj_en: str,
    size: str,
    move_en: str,
    dlg: list[dict[str, str]],
) -> str:
    action = _clip_for_window(beat_en, window_sec, lang="en")
    size_vis = _size_as_visible_en(size)
    move = (move_en or "").strip()
    if window_sec <= 3:
        bits = []
        if size_vis:
            bits.append(size_vis)
        if subj_en:
            bits.append(f"on {subj_en}")
        if move:
            bits.append(move)
        if action:
            bits.append(action)
        line = ", ".join(bits)
    else:
        bits = [action] if action else []
        if subj_en:
            bits.append(f"focus on {subj_en}")
        if size_vis:
            bits.append(size_vis)
        if move:
            bits.append(move)
        line = "; ".join(bits)

    if dlg and window_sec > 2:
        line = line.rstrip(". ") + ". " + _format_dlg_en(dlg)
    if line and line[-1] not in ".!?\"":
        line += "."
    return line


def write_package_prompts(
    bible: dict[str, Any],
    package: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Build EN+ZH four-part prompts with internal timeline storyboard."""
    beats = package.get("beats") or []
    max_clip = _sec_int(package.get("max_clip_sec") or 15)
    total = _sec_int(package.get("duration_sec") or 0)
    if total <= 0 and beats:
        total = _sec_int((beats[-1].get("t_end") if beats else 0) or 0)
    style = (style_pack or {}).get("label") or (bible.get("meta") or {}).get("style_pack") or "cinematic"

    fake_shot = {
        "shot_id": package.get("package_id"),
        "scene_id": (beats[0].get("scene_id") if beats else None),
        "subject": "、".join(str(b.get("subject") or "") for b in beats if b.get("subject"))[:80],
        "subject_en": ", ".join(
            str(b.get("subject_en") or "") for b in beats if b.get("subject_en")
        )[:120],
        "shot_size": beats[0].get("shot_size") if beats else "MS",
        "dramatic_beat": " / ".join(str(b.get("dramatic_beat") or "") for b in beats[:4]),
        "dramatic_beat_en": " / ".join(str(b.get("dramatic_beat_en") or "") for b in beats[:4]),
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
    if len(beats) >= 2:
        names_zh: list[str] = []
        names_en: list[str] = []
        for b in beats:
            for part in re_split_names(str(b.get("subject") or "")):
                if part and part not in names_zh:
                    names_zh.append(part)
            for part in re_split_names(str(b.get("subject_en") or b.get("subject") or "")):
                if part and part not in names_en:
                    names_en.append(part)
        if names_zh or names_en:
            refs = []
            nmax = max(len(names_zh), len(names_en), 1)
            for i in range(min(4, nmax)):
                nz = names_zh[i] if i < len(names_zh) else (
                    names_en[i] if i < len(names_en) else f"主体{i+1}"
                )
                ne = names_en[i] if i < len(names_en) else ""
                if not ne or has_cjk(ne):
                    ne = f"subject {i+1}"
                refs.append(
                    {
                        "role_en": "subject",
                        "role_zh": "主体",
                        "name_en": ne,
                        "name_zh": nz,
                        "detail_en": "",
                        "detail_zh": "",
                    }
                )

    refs_en = []
    for i, r in enumerate(refs or []):
        ne = r.get("name_en") or f"subject {i+1}"
        if has_cjk(ne):
            ne = f"subject {i+1}"
        refs_en.append({**r, "name_en": ne})
    sub_en = format_subject_refs_en(refs_en or refs)
    sub_zh = format_subject_refs_zh(refs)

    cam0 = (beats[0].get("camera") if beats else {}) or {}
    body = cam0.get("body") or "ARRI Alexa 35 (virtual cinematic look)"
    lens = cam0.get("lens_mm") or 35
    tstop = cam0.get("t_stop") or cam0.get("aperture") or "T2.0"
    # Angle from first beat (no pure eye_level forced here — already on contract)
    angle = cam0.get("angle") or "slight_low"
    height = cam0.get("height") or ""
    gear_en = (
        f"{body}; {lens}mm, {tstop}; angle {angle}"
        + (f", height {height}" if height else "")
        + f"; photoreal cinema. Duration about {total}s (max {max_clip}s)."
    )
    gear_zh = (
        f"{body}；{lens}mm，{tstop}；机位角度{angle}"
        + (f"，高度{height}" if height else "")
        + f"；写实电影。本段约 {total} 秒（不超过 {max_clip} 秒）。"
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

    # One beat → only its own linked_dialogue (no cross-shot inject ever)
    prepared: list[dict[str, Any]] = []
    for b in beats:
        a, e = float(b.get("t_start") or 0), float(b.get("t_end") or 0)
        w = _window_sec(a, e)
        # one-shot packages use full package duration as window for dialogue
        if len(beats) == 1:
            w = max(w, total if total > 0 else w)
        dlg = _dialogue_for_beat(bible, b, window_sec=w)
        prepared.append({"b": b, "a": a, "e": e, "w": w, "dlg": dlg})

    lines_en: list[str] = []
    lines_en_free: list[str] = []
    lines_zh: list[str] = []
    for p in prepared:
        b, a, e, w, dlg = p["b"], p["a"], p["e"], p["w"], p["dlg"]
        rng_zh = _format_range(a, e, lang="zh")
        rng_en = _format_range(a, e, lang="en")

        beat_zh = strip_music_mentions(
            b.get("dramatic_beat") or resolve_dramatic_beat_zh(b) or "动作推进",
            lang="zh",
        )
        beat_en = strip_music_mentions(
            b.get("dramatic_beat_en") or resolve_dramatic_beat_en(b) or "action continues",
            lang="en",
        )
        if has_cjk(beat_en):
            beat_en = "on-screen action continues"
        if w <= 3:
            beat_zh = _strip_spoken_narration(beat_zh, lang="zh")
            beat_en = _strip_spoken_narration(beat_en, lang="en")

        subj_zh = str(b.get("subject") or resolve_subject_zh(b) or "").strip()
        subj_en = str(b.get("subject_en") or resolve_subject_en(b) or "subject").strip()
        if has_cjk(subj_en):
            subj_en = "on-screen subject"

        size = str(b.get("shot_size") or "")
        cam = b.get("camera") or {}
        move_en = _clean_move_en(cam)
        move_zh = _clean_move_zh(cam)

        line_zh = _compose_beat_zh(
            window_sec=w,
            beat_zh=beat_zh,
            subj_zh=subj_zh,
            size=size,
            move_zh=move_zh,
            dlg=dlg,
        )
        line_en = _compose_beat_en(
            window_sec=w,
            beat_en=beat_en,
            subj_en=subj_en,
            size=size,
            move_en=move_en,
            dlg=dlg,
        )
        # Free EN: English stage directions; dialogue remains Chinese (script language)
        line_en_free = _compose_beat_en(
            window_sec=w,
            beat_en=beat_en,
            subj_en=subj_en,
            size=size,
            move_en=move_en,
            dlg=dlg,  # same full Chinese lines — do NOT strip to "spoken line"
        )

        # Single-shot package: continuous take language, not fake multi-cut table
        if len(prepared) == 1 and w >= 3:
            lines_zh.append(f"连续约 {w} 秒：{line_zh}")
            lines_en.append(f"Continuous ~{w}s: {line_en}")
            lines_en_free.append(f"Continuous ~{w}s: {line_en_free}")
        else:
            lines_zh.append(f"{rng_zh}，{line_zh}")
            lines_en.append(f"{rng_en}, {line_en}")
            lines_en_free.append(f"{rng_en}, {line_en_free}")

    light_en_clean = light_en
    if has_cjk(light_en_clean):
        light_en_clean = re.sub(r"[\u4e00-\u9fff]+", " ", light_en_clean)
        light_en_clean = re.sub(r"\s+", " ", light_en_clean).strip()

    # Lighting & mood lead the visual close (emotion atmosphere before style label)
    close_en = (
        f"{light_en_clean} "
        f"Overall cinematic mood for this take: {style}; keep lighting emotion-readable; "
        f"subjects clear; natural motion. Duration {total} seconds."
    )
    close_zh = (
        f"{light_zh}"
        f"本段整体氛围服务情绪与戏剧，风格气质：{style}；"
        f"光影优先于炫技，主体清楚，运动自然。"
        f"本段时长 {total} 秒。"
    )

    # Storyline first (action), then emphatic lighting block, then duration already in close
    story_en = "\n".join(lines_en) + f"\n{close_en}"
    story_zh = "\n".join(lines_zh) + f"\n{close_zh}"
    story_en_free = "\n".join(lines_en_free) + f"\n{close_en}"
    story_zh_free = "\n".join(lines_zh) + f"\n{close_zh}"

    sfx_en = (
        "SFX only: diegetic action and environment; clear dialogue when present. "
        "No music, no score, no BGM. No subtitles, no watermark, no UI."
    )
    sfx_zh = (
        "只保留有源音效：环境与动作声；有对白则声线清晰。"
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
        "writer": "package_timeline_v2_industrial",
    }


def re_split_names(s: str) -> list[str]:
    s = (s or "").strip()
    if not s:
        return []
    parts = re.split(r"[、，,/]|和|与|及", s)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) <= 24]
