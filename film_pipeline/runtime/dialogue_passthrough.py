"""Keep original script dialogue without polish (user skipped dialogue stage)."""

from __future__ import annotations

import re
from typing import Any


def extract_raw_dialogue(bible: dict[str, Any]) -> dict[str, Any]:
    """
    Build dialogue[] from source_script as-is (no rewrite).
    Used when ProductionBrief.run_dialogue_polish is False.
    """
    script = bible.get("source_script") or ""
    scenes = bible.get("scenes") or []
    scene_id = scenes[0]["scene_id"] if scenes else "S01"

    lines: list[dict[str, Any]] = []
    current_speaker: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_speaker
        if current_speaker and buf:
            text = "".join(buf).strip()
            if text:
                lines.append(
                    {
                        "character": current_speaker,
                        "text": text,
                        "function": "advance",
                        "subtext": "（跳过对白精修：保留原剧本措辞）",
                        "delivery": "按原剧本自然表演",
                    }
                )
        buf = []

    for raw in script.splitlines():
        s = raw.strip()
        if not s or s.startswith("---") or s.startswith("标题") or s.startswith("类型"):
            continue
        # character header: short name alone, or 林安（动作）
        m = re.fullmatch(r"([\u4e00-\u9fffA-Za-z]{1,12})(?:\s*[（(].*[）)])?", s)
        if m and len(s) <= 20 and not any(ch in s for ch in "。！？，、；："):
            # avoid treating scene headers as speakers
            if s.startswith("第") and "场" in s:
                continue
            if "夜" in s and "·" in s:
                continue
            flush()
            current_speaker = m.group(1)
            continue
        # parenthetical acting note under character
        if current_speaker and (s.startswith("（") or s.startswith("(")):
            continue
        if current_speaker:
            buf.append(s)
        # else stage direction — skip

    flush()

    if not lines:
        # fallback: one atmosphere line so director still has structure
        lines = [
            {
                "character": "NARRATION",
                "text": "（本剧本无可解析对白行，请检查格式或开启对白精修）",
                "function": "atmosphere",
                "subtext": "passthrough empty",
                "delivery": "无",
            }
        ]

    return {
        "dialogue": [
            {
                "scene_id": scene_id,
                "lines": lines,
                "silence_beats_ms": [],
                "polish_skipped": True,
            }
        ]
    }


def apply_dialogue_passthrough(bible: dict[str, Any]) -> dict[str, Any]:
    out = extract_raw_dialogue(bible)
    bible["dialogue"] = out["dialogue"]
    bible.setdefault("meta", {})["dialogue_polish"] = "skipped"
    return bible
