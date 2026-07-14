"""Keep original script dialogue without polish (user skipped dialogue stage)."""

from __future__ import annotations

import re
from typing import Any


# Stage-direction / meta lines (not spoken dialogue)
_SKIP_LINE_PREFIXES = (
    "△",
    "【",
    "标题",
    "类型",
    "人物：",
    "人物:",
    "---",
)


def _is_scene_header(s: str) -> bool:
    # 1-1 黄金岛户外 日 外
    if re.match(r"^\d+-\d+\s+", s):
        return True
    if re.match(r"^第.+场", s):
        return True
    return False


def _speaker_start(s: str) -> tuple[str, str, str] | None:
    """
    Parse dialogue openers. Returns (speaker, delivery_note, rest_text) or None.

    Supports:
      导演：（诧异）她？怎么搞定？
      苏檀（OS）：……
      赵凛：条件不错
      副导演：听说他们……（压低声音）是高中时期的青梅竹马。
    """
    s = (s or "").strip()
    if not s:
        return None

    # Name（notes）：rest   e.g. 苏檀（OS）：……  /  Ananke（画外）：……
    m = re.match(
        r"^([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff·]{0,15}?)"
        r"\s*[（(]([^）)]{0,40})[）)]\s*[：:]\s*(.*)$",
        s,
    )
    if m:
        return m.group(1).strip(), (m.group(2) or "").strip(), (m.group(3) or "").strip()

    # Name：rest  — rest may start with （括注）
    m2 = re.match(
        r"^([A-Za-z\u4e00-\u9fff]{1,12})\s*[：:]\s*(.*)$",
        s,
    )
    if m2 and len(s) <= 200:
        name = m2.group(1).strip()
        rest = (m2.group(2) or "").strip()
        if name.startswith("第") and ("场" in name or "集" in name):
            return None
        if name in {"人物", "场景", "时间", "地点"}:
            return None
        delivery = ""
        # peel leading （诧异） as delivery
        m_del = re.match(r"^[（(]([^）)]{1,30})[）)]\s*(.*)$", rest)
        if m_del:
            delivery = m_del.group(1).strip()
            rest = (m_del.group(2) or "").strip()
        return name, delivery, rest

    # Name alone on line (classic screenplay): next lines are dialogue
    # 周宁
    # 怎么还不睡？
    m3 = re.fullmatch(
        r"([A-Za-z\u4e00-\u9fff]{1,12})(?:\s*[（(][^）)]{0,20}[）)])?",
        s,
    )
    if m3 and len(s) <= 24 and not any(ch in s for ch in "。！？!?，,"):
        name = m3.group(1).strip()
        if name.startswith("第") and ("场" in name or "集" in name):
            return None
        if name in {"人物", "场景", "时间", "地点", "标题", "类型"}:
            return None
        # Name（OS） alone
        m_note = re.fullmatch(
            r"([A-Za-z\u4e00-\u9fff]{1,12})\s*[（(]([^）)]{0,20})[）)]",
            s,
        )
        if m_note:
            return m_note.group(1).strip(), (m_note.group(2) or "").strip(), ""
        return name, "", ""

    return None


def _clean_dialogue_text(text: str) -> str:
    t = (text or "").strip()
    # drop accidental stage-direction tails glued by bad parsers
    t = re.split(r"[△【]", t, maxsplit=1)[0].strip()
    for a, b in (('"', '"'), ("“", "”"), ("「", "」"), ("『", "』")):
        if t.startswith(a) and t.endswith(b) and len(t) >= 2:
            t = t[len(a) : -len(b)].strip()
    return t.strip(" \t\"'“”「」")


def _guess_scene_id(s: str, scenes: list[dict[str, Any]], default: str) -> str | None:
    """If line is a scene header matching scenes, return scene_id."""
    m = re.match(r"^(\d+)-(\d+)\s+", s)
    if m:
        # map 1-1 -> S01, 1-2 -> S02 if scenes ordered
        idx = int(m.group(2)) - 1
        if 0 <= idx < len(scenes):
            return str(scenes[idx].get("scene_id") or default)
        return f"S{int(m.group(2)):02d}"
    return None


def extract_raw_dialogue(bible: dict[str, Any]) -> dict[str, Any]:
    """
    Build dialogue[] from source_script as-is (no rewrite).
    Used when ProductionBrief.run_dialogue_polish is False.
    """
    script = bible.get("source_script") or ""
    scenes = bible.get("scenes") or []
    default_scene = scenes[0]["scene_id"] if scenes else "S01"

    # scene_id -> lines
    by_scene: dict[str, list[dict[str, Any]]] = {}
    current_scene = default_scene
    current_speaker: str | None = None
    current_delivery = ""
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_speaker, current_delivery
        if current_speaker and buf:
            text = _clean_dialogue_text("".join(buf))
            # discard pure stage junk / too long dumps
            if text and not text.startswith("△") and len(text) < 400:
                # skip fake speakers
                if current_speaker not in {"人物", "第一集", "1", "NARRATION"}:
                    entry = {
                        "character": current_speaker,
                        "text": text,
                        "function": "advance",
                        "subtext": "（跳过对白精修：保留原剧本措辞）",
                        "delivery": current_delivery or "按原剧本自然表演",
                    }
                    by_scene.setdefault(current_scene, []).append(entry)
        buf = []
        current_delivery = ""

    for raw in script.splitlines():
        s = raw.strip()
        if not s:
            continue

        # scene switch
        sid = _guess_scene_id(s, scenes, default_scene)
        if sid:
            flush()
            current_speaker = None
            current_scene = sid
            continue

        if _is_scene_header(s):
            flush()
            current_speaker = None
            continue

        if any(s.startswith(p) for p in _SKIP_LINE_PREFIXES):
            # stage direction ends any open speaker block
            flush()
            current_speaker = None
            continue

        # pure paren acting note under an open speaker (classic format)
        if (s.startswith("（") or s.startswith("(")) and "：" not in s and ":" not in s:
            if current_speaker and not buf:
                # （没有抬头） before dialogue text — treat as delivery
                inner = re.match(r"^[（(]([^）)]+)[）)]\s*$", s)
                if inner:
                    current_delivery = inner.group(1).strip() or current_delivery
                    continue
            if current_speaker and buf:
                # mid-dialogue stage note — skip, keep speaker
                continue
            flush()
            current_speaker = None
            continue

        sp = _speaker_start(s)
        if sp:
            name, delivery, rest = sp
            # Name alone opens speaker without flushing into empty
            if current_speaker and current_speaker != name:
                flush()
            elif current_speaker == name and rest:
                flush()
            current_speaker = name
            if delivery:
                current_delivery = delivery
            if rest:
                buf.append(rest)
            continue

        # continuation / dialogue body under open speaker
        if current_speaker and not s.startswith("△"):
            # stage-direction prose ending a block (no quotes)
            if re.match(r"^[\u4e00-\u9fff]{2,8}的", s) and "：" not in s and len(s) > 20:
                # e.g. 周宁的笑容塌了一半…
                flush()
                current_speaker = None
                continue
            buf.append(s)
            continue

        flush()
        current_speaker = None

    flush()

    blocks: list[dict[str, Any]] = []
    order = [str(sc.get("scene_id")) for sc in scenes] if scenes else list(by_scene.keys())
    seen = set()
    for sid in order:
        if sid in by_scene and sid not in seen:
            blocks.append(
                {
                    "scene_id": sid,
                    "lines": by_scene[sid],
                    "silence_beats_ms": [],
                    "polish_skipped": True,
                }
            )
            seen.add(sid)
    for sid, lines in by_scene.items():
        if sid not in seen:
            blocks.append(
                {
                    "scene_id": sid,
                    "lines": lines,
                    "silence_beats_ms": [],
                    "polish_skipped": True,
                }
            )

    if not blocks:
        blocks = [
            {
                "scene_id": default_scene,
                "lines": [
                    {
                        "character": "NARRATION",
                        "text": "（本剧本无可解析对白行，请检查格式或开启对白精修）",
                        "function": "atmosphere",
                        "subtext": "passthrough empty",
                        "delivery": "无",
                    }
                ],
                "silence_beats_ms": [],
                "polish_skipped": True,
            }
        ]

    return {"dialogue": blocks}


def apply_dialogue_passthrough(bible: dict[str, Any]) -> dict[str, Any]:
    out = extract_raw_dialogue(bible)
    bible["dialogue"] = out["dialogue"]
    bible.setdefault("meta", {})["dialogue_polish"] = "skipped"
    return bible


def list_spoken_lines(bible: dict[str, Any]) -> list[dict[str, str]]:
    """Flat list of character+text from dialogue[] for coverage checks."""
    rows: list[dict[str, str]] = []
    for blk in bible.get("dialogue") or []:
        for ln in blk.get("lines") or []:
            text = (ln.get("text") or "").strip()
            char = (ln.get("character") or "").strip()
            if text and char and char != "NARRATION":
                rows.append({"character": char, "text": text, "scene_id": str(blk.get("scene_id") or "")})
    return rows
