"""
English generation slots for shots.

Policy:
  - English final prompts MUST prefer dramatic_beat_en / subject_en.
  - Chinese dramatic_beat / subject stay for human boards & ZH对照 context.
  - If only Chinese exists, use known map or a neutral English fallback
    (never dump raw Chinese into the English generation main draft when avoidable).
"""

from __future__ import annotations

import re
from typing import Any

_CJK = re.compile(r"[\u4e00-\u9fff]")

# Known sample / stub beats → stable English (extend as needed)
_BEAT_ZH_TO_EN: dict[str, str] = {
    "雨夜客厅建立：信封在茶几中央": (
        "Rainy-night living room establish: sealed envelope centered on the coffee table"
    ),
    "信封封口胶已翘起（信息）": (
        "Insert detail: envelope seal adhesive already lifted (information plant)"
    ),
    "林安不抬头说出信封被动过": (
        "Lin An, without looking up, states the envelope has been tampered with"
    ),
    "周宁心虚地反问": "Zhou Ning asks back, defensive and uneasy",
    "林安抬眼确认：你早就看过了": (
        "Lin An looks up and confirms: you already read it"
    ),
    "周宁笑容塌陷": "Zhou Ning's smile collapses",
    "关灯前的最后通牒感": "Final ultimatum beat before the lamp goes dark",
}

_SUBJECT_ZH_TO_EN: dict[str, str] = {
    "客厅、台灯、茶几上的信封": (
        "living room, table lamp, envelope on the coffee table"
    ),
    "信封封口细节": "close detail of the envelope seal",
    "林安上半身与茶几": "Lin An upper body and the coffee table",
    "周宁从厨房方向进入画框": "Zhou Ning entering frame from the kitchen direction",
    "林安眼睛与微表情": "Lin An's eyes and micro-expressions",
    "周宁半边脸落在台灯里": "half of Zhou Ning's face caught in the lamp light",
    "两人与即将熄灭的台灯": "both characters and the lamp about to go out",
}


def has_cjk(text: str | None) -> bool:
    return bool(text and _CJK.search(str(text)))


def _clean(text: str | None) -> str:
    return (text or "").strip()


# Music / score mentions must not enter final generation prompts
_MUSIC_RE = re.compile(
    r"What a Wonderful World|Wonderful World|"
    r"saxophone|sax\b|jazz\s*(score|underscore|music)?|"
    r"萨克斯|爵士|配乐|主题曲|BGM|underscore|musical theme",
    re.I,
)

_ENV_SUBJECT_RE = re.compile(
    r"submarine|sub\b|hull|water|ocean|deep.?water|turbid|"
    r"console|holo|gauge|screen|speaker|oscilloscope|e-?ink|display|"
    r"envelope|jar|photo|photograph|geometry|cabin|titanium|"
    r"潜艇|深水|水体|舱壁|全息|仪表|音箱|示波器|电子墨水|信封|密封罐|"
    r"工作照|照片|喇叭|控制台|液压|总线",
    re.I,
)

_HUMAN_SUBJECT_RE = re.compile(
    r"高岩|技术员|林安|周宁|Ananke|人|脸|眼|手(?!机)|指尖|半身|上半身|"
    r"gao\s*yan|technician|face|eyes?|pupil|hand|finger|silhouette of (a |the )?(man|woman|person)",
    re.I,
)


def strip_music_mentions(text: str | None, *, lang: str = "en") -> str:
    """Remove score/music phrases from beat text used in generation prompts."""
    s = _clean(text)
    if not s:
        return s
    s = _MUSIC_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s*[,，、；;:：]\s*[,，、；;:：]+", ", ", s)
    s = s.strip(" ,，、；;:：")
    if not s:
        return "Scene continues in silence aside from diegetic SFX" if lang == "en" else "无配乐，仅环境与动作"
    # Clean leftover “画外响起” after music title removed
    s = re.sub(r"(画外)?(响起|传来)[，,]?", "", s)
    s = re.sub(r"(rises|plays|sounds)\s+off-?screen[.,]?", "", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,，.;；")
    s = re.sub(r"^[,，.;；\s]+", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s or ("atmospheric establish" if lang == "en" else "建立镜头")


def is_environment_or_object_shot(shot: dict[str, Any]) -> bool:
    """
    True when the frame is primarily environment / prop / vehicle — not a person
    performance plate. Used to block facial dread templates on submarines, etc.
    """
    size = str(shot.get("shot_size") or "").upper()
    if size in {"INSERT", "EWS"}:
        return True

    sub_en = _clean(shot.get("subject_en"))
    sub_zh = _clean(shot.get("subject") or shot.get("subject_zh"))
    blob = f"{sub_en} {sub_zh}"

    has_human = bool(_HUMAN_SUBJECT_RE.search(blob))
    has_env = bool(_ENV_SUBJECT_RE.search(blob))

    # Wide/env: prefer environment if no clear human subject
    if size in {"WS", "FS"} and has_env and not has_human:
        return True
    if has_env and not has_human:
        return True
    # Detail CU of props/screens without people
    if size in {"CU", "ECU", "MS"} and has_env and not has_human:
        return True
    return False


def resolve_dramatic_beat_en(shot: dict[str, Any]) -> str:
    """English dramatic beat for generation prompts."""
    for key in ("dramatic_beat_en", "beat_en"):
        v = _clean(shot.get(key))
        if v:
            return strip_music_mentions(v, lang="en")
    zh = _clean(shot.get("dramatic_beat"))
    if not zh:
        return "Scene beat"
    if not has_cjk(zh):
        return strip_music_mentions(zh, lang="en")
    if zh in _BEAT_ZH_TO_EN:
        return strip_music_mentions(_BEAT_ZH_TO_EN[zh], lang="en")
    # Unknown Chinese: do not pollute EN main draft with raw ZH
    return "Dramatic beat (see Chinese field dramatic_beat)"


def resolve_subject_en(shot: dict[str, Any]) -> str:
    """English subject for generation prompts."""
    for key in ("subject_en",):
        v = _clean(shot.get(key))
        if v:
            return v
    zh = _clean(shot.get("subject"))
    if not zh:
        return "scene subject"
    if not has_cjk(zh):
        return zh
    if zh in _SUBJECT_ZH_TO_EN:
        return _SUBJECT_ZH_TO_EN[zh]
    return "scene subject (see Chinese field subject)"


def resolve_dramatic_beat_zh(shot: dict[str, Any]) -> str:
    """Chinese beat for human summaries (prefer original ZH, music stripped for prompt use)."""
    zh = _clean(shot.get("dramatic_beat"))
    if zh and has_cjk(zh):
        return strip_music_mentions(zh, lang="zh")
    en = resolve_dramatic_beat_en(shot)
    # reverse map if possible
    for k, v in _BEAT_ZH_TO_EN.items():
        if v == en or strip_music_mentions(v, lang="en") == en:
            return strip_music_mentions(k, lang="zh")
    return strip_music_mentions(zh or en, lang="zh")


def resolve_subject_zh(shot: dict[str, Any]) -> str:
    zh = _clean(shot.get("subject"))
    if zh and has_cjk(zh):
        return zh
    en = resolve_subject_en(shot)
    for k, v in _SUBJECT_ZH_TO_EN.items():
        if v == en:
            return k
    return zh or en


def ensure_shot_english_slots(shot: dict[str, Any]) -> dict[str, Any]:
    """
    Fill dramatic_beat_en / subject_en on the shot if missing.
    Keeps Chinese dramatic_beat / subject untouched.
    """
    if not _clean(shot.get("dramatic_beat_en")):
        shot["dramatic_beat_en"] = resolve_dramatic_beat_en(shot)
    if not _clean(shot.get("subject_en")):
        shot["subject_en"] = resolve_subject_en(shot)
    return shot


def ensure_bible_english_slots(bible: dict[str, Any]) -> dict[str, Any]:
    for shot in bible.get("shots") or []:
        ensure_shot_english_slots(shot)
    return bible
