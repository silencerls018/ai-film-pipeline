"""
Faithful EN → ZH translation for final generation prompts.

English final prompt is the single source of truth.
Chinese is a reading aid that must mirror the English content (no parallel rewrite).
"""

from __future__ import annotations

import re
from functools import lru_cache

# Longer phrases first — applied as whole-phrase replacements (case-insensitive for ASCII).
# Values must not invent new creative content; only render the same slots in Chinese.
_GLOSSARY_PAIRS: list[tuple[str, str]] = [
    # Fixed compiler footers / headers
    (
        "Photoreal cinematic film, coherent anatomy, continuous identity, "
        "no subtitles, no watermark, no UI.",
        "写实电影感；解剖结构正确；人物身份连续；无字幕、无水印、无界面。",
    ),
    (
        "Photoreal cinematic film, no subtitles, no watermark.",
        "写实电影，无字幕、无水印。",
    ),
    (
        "Do not prescribe exact facial muscle choreography.",
        "不规定具体面部肌肉走位。",
    ),
    ("Emotion (free performance):", "情绪（自由发挥）："),
    ("Micro-actions:", "微动作："),
    ("Performance:", "表演："),
    ("Subject:", "主体："),
    ("Camera move:", "运镜："),
    ("Camera:", "摄影机："),
    ("Lighting:", "灯光："),
    ("Gaze:", "视线："),
    ("Voice:", "声音："),
    ("delivery:", "说法："),
    ("subtext:", "潜台词："),
    (" says: ", " 说："),
    ("cinematic look.", "电影风格。"),
    ("tonal key", "影调"),
    ("height.", "高度。"),
    (" height", " 高度"),
    # Intensity / emotion scale (EN labels from knowledge)
    ("relaxed", "松弛"),
    ("clear wariness", "明显戒备"),
    ("almost breathless", "几乎窒息感"),
    ("physiological freeze shock", "生理休克式僵直"),
    ("soft warmth", "柔和温暖"),
    ("heavy quiet sorrow", "沉重静默的悲伤"),
    ("cold dread", "冰冷恐惧"),
    # Emotions
    ("suspicion", "怀疑/紧绷"),
    ("oppression", "压迫"),
    ("revelation", "揭示/震惊"),
    ("intimacy", "亲密"),
    ("grief", "悲伤"),
    ("dread", "恐惧/惊悚"),
    ("calm", "平静"),
    # Actor-free tags
    ("neutral breath", "呼吸平稳"),
    ("soft presence", "柔和存在感"),
    ("heavy pressure", "沉重压迫"),
    ("no exit", "无路可退"),
    ("truth lands", "真相落地"),
    ("vulnerable soft", "柔软脆弱"),
    ("heavy loss", "沉重失落"),
    ("composed", "克制沉着"),
    ("suspicious", "怀疑"),
    ("tense", "紧绷"),
    ("wary", "戒备"),
    ("alert", "警觉"),
    ("oppressed", "受压"),
    ("cornered", "被逼到绝境"),
    ("shock", "震惊"),
    ("realization", "恍然大悟"),
    ("stunned", "呆住"),
    ("intimate", "亲密"),
    ("tender", "温柔"),
    ("close", "靠近"),
    ("sorrow", "哀伤"),
    ("heartbroken", "心碎"),
    ("fear", "害怕"),
    ("terror", "惊恐"),
    ("freeze", "僵住"),
    # Shot sizes (word-boundary friendly forms)
    ("EWS shot", "大远景（EWS）"),
    ("WS shot", "全景/远景（WS）"),
    ("FS shot", "全身景（FS）"),
    ("MS shot", "中景（MS）"),
    ("MCU shot", "中近景（MCU）"),
    ("CU shot", "特写（CU）"),
    ("ECU shot", "大特写（ECU）"),
    ("INSERT shot", "插入镜头（INSERT）"),
    # Angles / camera
    ("eye_level_tight", "平视偏紧"),
    ("eye_level", "平视"),
    ("slight_low", "略仰"),
    ("slight_high", "略俯"),
    ("dutch_rare", "荷兰角（慎用）"),
    ("dutch", "荷兰角"),
    ("very_slow", "极慢"),
    ("locked-off static wide shot, characters move in frame", "锁定固定全景，人物在画内活动"),
    ("dolly out revealing the character alone in the empty room", "拉镜揭示人物独自在空房间中"),
    ("creepy slow push in on sleeping figure, horror", "缓慢潜行推进（词库英文参考）"),
    ("slow push in", "缓慢推进"),
    ("static hold", "固定维持"),
    ("Static Locked-Off", "锁定固定"),
    ("Creep In", "缓推/潜行推"),
    ("Dolly Out", "拉镜"),
    # Look / grade
    ("low_key", "低调光"),
    ("high_key", "高调光"),
    ("medium_high", "中高反差"),
    ("medium_low", "中低反差"),
    ("cold_cyan_shadow", "冷青阴影"),
    ("warm_practical_key", "暖实用主光"),
    ("Neo Noir", "新黑色电影"),
    ("neo_noir", "新黑色电影"),
    ("warm realism", "温暖写实"),
    ("warm_realism", "温暖写实"),
    # Generic
    ("Scene.", "场景。"),
    ("scene", "场景"),
    ("character", "人物"),
    ("about ", "约 "),
    (" seconds.", " 秒。"),
    (" seconds", " 秒"),
    ("second.", "秒。"),
    ("palette ", "色板 "),
    ("shot,", "镜头，"),
    ("shot.", "镜头。"),
    # Mid intensity fallback labels
    (" mid)", " 中)"),
    ("(mid)", "（中）"),
    (" low)", " 低)"),
    (" high)", " 高)"),
]

# Standalone shot-size tokens (e.g. "MCU, about 3s")
_SHOT_SIZE_TOKEN = {
    "EWS": "大远景（EWS）",
    "WS": "全景/远景（WS）",
    "FS": "全身景（FS）",
    "MS": "中景（MS）",
    "MCU": "中近景（MCU）",
    "CU": "特写（CU）",
    "ECU": "大特写（ECU）",
    "INSERT": "插入镜头（INSERT）",
}


def _sorted_glossary() -> list[tuple[str, str]]:
    # Longest English source first to avoid partial clobbering
    return sorted(_GLOSSARY_PAIRS, key=lambda p: len(p[0]), reverse=True)


def _en_pattern(en: str) -> re.Pattern[str]:
    """Compile EN phrase: word-boundary for bare words; plain escape for multi-token."""
    flags = re.IGNORECASE if all(ord(c) < 128 for c in en) else 0
    escaped = re.escape(en)
    # Bare ASCII word/token → avoid partial matches (character ≠ characters)
    if re.fullmatch(r"[A-Za-z][A-Za-z_]*", en):
        return re.compile(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])", flags)
    return re.compile(escaped, flags)


@lru_cache(maxsize=1)
def _compiled_patterns() -> list[tuple[re.Pattern[str], str]]:
    return [(_en_pattern(en), zh) for en, zh in _sorted_glossary()]


def _protect_segments(text: str) -> tuple[str, list[str]]:
    """
    Protect quoted strings and CJK runs so glossary replace won't mangle dialogue / already-Chinese beats.
    """
    vault: list[str] = []

    def stash(m: re.Match[str]) -> str:
        vault.append(m.group(0))
        return f"\x00P{len(vault) - 1}\x00"

    # Double-quoted dialogue first
    text = re.sub(r'"[^"\n]*"', stash, text)
    # Single-quoted short tokens
    text = re.sub(r"'[^'\n]{1,80}'", stash, text)
    # Existing Chinese / fullwidth runs (leave as-is in final output)
    text = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+", stash, text)
    return text, vault


def _restore_segments(text: str, vault: list[str]) -> str:
    def unstash(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return vault[idx] if 0 <= idx < len(vault) else m.group(0)

    return re.sub(r"\x00P(\d+)\x00", unstash, text)


def _replace_shot_size_tokens(text: str) -> str:
    """Translate bare shot-size codes; skip ones already inside （CODE）/ (CODE)."""

    def repl(m: re.Match[str]) -> str:
        code = m.group(1)
        start = m.start()
        # Already annotated e.g. 特写（CU） or 全景/远景（WS）
        if start > 0 and text[start - 1] in "（(":
            return code
        return _SHOT_SIZE_TOKEN.get(code, code)

    return re.sub(
        r"(?<![A-Za-z])(" + "|".join(_SHOT_SIZE_TOKEN.keys()) + r")(?![A-Za-z])",
        repl,
        text,
    )


def _normalize_spacing(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([，。；：、）】》])", r"\1", text)
    text = re.sub(r"([（【《])\s+", r"\1", text)
    # "约 3.4s" / "约 3.4 s" → "约 3.4 秒"
    text = re.sub(r"约\s*(\d+(?:\.\d+)?)\s*s\b", r"约 \1 秒", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*s\b", r"\1 秒", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d+)\s*mm\b", r"\1 毫米", text, flags=re.IGNORECASE)
    return text.strip()


def translate_prompt_en_to_zh(english: str) -> str:
    """
    Faithfully render an English final prompt into Chinese for human reading.

    Does not invent new beats/moves/lights. Untranslated English fragments may
    remain when no glossary entry exists (better than hallucinating).
    """
    if not english or not str(english).strip():
        return ""

    src = str(english).strip()
    protected, vault = _protect_segments(src)
    out = protected
    for pat, zh in _compiled_patterns():
        out = pat.sub(zh, out)
    out = _replace_shot_size_tokens(out)
    out = _restore_segments(out, vault)
    out = _normalize_spacing(out)
    # Prefix so board readers know this is a mirror, not a second creative draft
    if not out.startswith("【中文对照·忠实翻译英文终稿】"):
        out = "【中文对照·忠实翻译英文终稿】" + out
    return out


def extract_alignment_markers(english: str) -> list[str]:
    """
    Stable markers that must survive into Chinese (coverage checks).
    """
    if not english:
        return []
    markers: list[str] = []
    # Durations
    markers.extend(re.findall(r"\d+(?:\.\d+)?", english))
    # Shot sizes
    for code in _SHOT_SIZE_TOKEN:
        if re.search(rf"(?<![A-Za-z]){re.escape(code)}(?![A-Za-z])", english):
            markers.append(code)
    # Quoted dialogue (must appear verbatim in ZH)
    markers.extend(re.findall(r'"([^"\n]+)"', english))
    # mm values
    markers.extend(re.findall(r"(\d+)\s*mm", english, flags=re.IGNORECASE))
    # Dedup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for m in markers:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def zh_covers_en_markers(english: str, chinese: str) -> list[str]:
    """Return markers present in EN but missing from ZH."""
    missing: list[str] = []
    for m in extract_alignment_markers(english):
        if m not in (chinese or ""):
            missing.append(m)
    return missing
