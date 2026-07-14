"""
Final prompt writer — natural language from FilmBible contract.

Fixed four-part format (product contract):
  1. Subject
  2. Camera gear & parameters
  3. Storyline (performance, dialogue, emotion, size, move, light, continuous vs cut)
  4. SFX only — no music, no subtitles

- English and Chinese: both feedable finished products (same four-part structure)

When LLM is available (FILM_PIPELINE_DRY_RUN=0 + API key), AI writes the prose.
When offline, a plain-language rule writer is used.
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any

from film_pipeline.runtime.llm import LLMClient
from film_pipeline.runtime.shot_locale import (
    ensure_shot_english_slots,
    has_cjk,
    is_environment_or_object_shot,
    resolve_dramatic_beat_en,
    resolve_dramatic_beat_zh,
    resolve_subject_en,
    resolve_subject_zh,
)

# Soft wrap width for delivery txt/md (auto line break — no horizontal drag)
PROMPT_WRAP_WIDTH = 88


def format_prompt_for_delivery(text: str, width: int = PROMPT_WRAP_WIDTH) -> str:
    """
    Normalize final prompts for copy-paste into video models:
    - force section headers on their own lines
    - soft-wrap long paragraphs (auto 换行)
    - strip reading-aid-only banners
    """
    if not text:
        return ""
    t = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    t = re.sub(r"^【看懂用[·・]?非主投喂】\s*", "", t)
    t = re.sub(r"^【仅供阅读】\s*", "", t)

    # Ensure numbered sections start new lines
    for pat, rep in (
        (r"(?<!\n)\s*(1\.\s*SUBJECT\s*:)", r"\n\1"),
        (r"(?<!\n)\s*(2\.\s*CAMERA[^\n:]*:)", r"\n\1"),
        (r"(?<!\n)\s*(3\.\s*STORYLINE\s*:)", r"\n\1"),
        (r"(?<!\n)\s*(4\.\s*AUDIO\s*:)", r"\n\1"),
        (r"(?<!\n)\s*(1\.\s*指定主体[^\n:：]*[:：])", r"\n\1"),
        (r"(?<!\n)\s*(2\.\s*摄影[^\n:：]*[:：])", r"\n\1"),
        (r"(?<!\n)\s*(3\.\s*故事线[^\n:：]*[:：]?)", r"\n\1"),
        (r"(?<!\n)\s*(4\.\s*音效[^\n:：]*[:：]?)", r"\n\1"),
    ):
        t = re.sub(pat, rep, t, flags=re.I)
    t = t.lstrip("\n")

    # Expand "1. SUBJECT: foo" so body can wrap under the header
    def _split_header_body(line: str) -> tuple[str, str] | None:
        m = re.match(
            r"^(1\.\s*SUBJECT\s*:|2\.\s*CAMERA[^:]*:|3\.\s*STORYLINE\s*:|4\.\s*AUDIO\s*:|"
            r"1\.\s*指定主体[^:：]*[:：]|2\.\s*摄影[^:：]*[:：]|3\.\s*故事线[^:：]*[:：]?|4\.\s*音效[^:：]*[:：]?)\s*(.*)$",
            line,
            flags=re.I,
        )
        if not m:
            return None
        return m.group(1).rstrip(), (m.group(2) or "").strip()

    out_lines: list[str] = []
    for raw_line in t.split("\n"):
        line = raw_line.rstrip()
        if not line:
            out_lines.append("")
            continue
        hb = _split_header_body(line)
        if hb:
            header, body = hb
            out_lines.append(header)
            if body:
                wrapped = textwrap.fill(
                    body,
                    width=width,
                    # never split mid-token (e.g. "3.4秒" / "12.45s")
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                out_lines.extend(wrapped.split("\n"))
            continue
        # normal paragraph wrap — keep timeline tokens intact
        if len(line) > width:
            wrapped = textwrap.fill(
                line,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            out_lines.extend(wrapped.split("\n"))
        else:
            out_lines.append(line)

    # collapse 3+ blank lines
    text_out = "\n".join(out_lines)
    text_out = re.sub(r"\n{3,}", "\n\n", text_out).strip() + "\n"
    return text_out

_SIZE_EN = {
    "EWS": "extreme wide establishing shot",
    "WS": "wide shot",
    "FS": "full shot",
    "MS": "medium shot",
    "MCU": "medium close-up",
    "CU": "close-up",
    "ECU": "extreme close-up",
    "INSERT": "insert detail shot",
}
_SIZE_ZH = {
    "EWS": "大远景/建立镜头",
    "WS": "全景",
    "FS": "全身景",
    "MS": "中景",
    "MCU": "中近景",
    "CU": "特写",
    "ECU": "大特写",
    "INSERT": "插入细节镜头",
}

_BAD_MOVE = re.compile(
    r"villain|horror|sleeping figure|creepy slow push in on sleeping",
    re.I,
)

# Map Look / cinematography CJK (or token) phrases → English for main prompts
_LOOK_EN = {
    "冷青或病态绿可选": "cold cyan or optional sickly green practicals",
    "冷阴影主导": "cold shadow-dominant key",
    "暖白": "warm white practicals",
    "冰蓝": "ice-blue console glow",
    "琥珀": "amber gauge backlight",
    "可选底光或硬侧光，深阴影": "optional under-light or hard side key, deep shadows",
    "偏硬侧光或顶侧光，面部部分被暗吞没": (
        "hard side or top-side key; part of the face swallowed by shadow"
    ),
    "亲密空间被知情权撕裂：暖实用光 vs 冷阴影": (
        "intimate space torn by the right-to-know: warm practical vs cold shadow"
    ),
    "中灰日常 → 低调高反差对质": "mid-gray everyday → low-key high-contrast confrontation",
    "cold_cyan_shadow": "cold cyan shadows",
    "warm_practical_key": "warm practical key light",
    "low_key_neo_noir": "low-key neo-noir",
    "controlled_low": "controlled low saturation",
    "cold_cyan, sick_green_optional": "cold cyan with optional sick green",
    "bright_sitcom": "bright sitcom lighting",
}


def _en_phrase(val: Any, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    if s in _LOOK_EN:
        return _LOOK_EN[s]
    # token_case → readable
    if re.fullmatch(r"[a-z0-9_]+", s):
        return s.replace("_", " ")
    if has_cjk(s):
        # keep meaning via partial map hits; else drop (avoid CJK in EN main)
        for zh, en in _LOOK_EN.items():
            if zh in s:
                return en
        return default
    return s


def _palette_en(palette: list[Any] | None) -> list[str]:
    out = []
    for p in palette or []:
        e = _en_phrase(p, "")
        if e:
            out.append(e)
    return out


def _scene_look(bible: dict[str, Any], scene_id: str | None) -> dict[str, Any]:
    for s in (bible.get("look_bible") or {}).get("scene_looks") or []:
        if s.get("scene_id") == scene_id:
            return s
    return {}


def _film_look(bible: dict[str, Any]) -> dict[str, Any]:
    return (bible.get("look_bible") or {}).get("film_look") or {}


_ATMOSPHERE_EN = {
    "dread": "oppressive cold dread in the air",
    "suspicion": "tight suspicious tension",
    "oppression": "heavy psychological pressure",
    "revelation": "quiet shock of a hard truth landing",
    "calm": "uneasy stillness",
    "intimacy": "close fragile intimacy",
    "grief": "muted grief",
}
_ATMOSPHERE_ZH = {
    "dread": "空气里发冷的压迫与不安",
    "suspicion": "紧绷的怀疑",
    "oppression": "沉重的心理压力",
    "revelation": "真相落下时的静默震惊",
    "calm": "不安的平静",
    "intimacy": "脆弱的亲密",
    "grief": "压抑的悲伤",
}


def _emotion_lighting_recipe(emotion: str) -> dict[str, Any]:
    """Load character lighting recipe for emotion from knowledge (cached lightly)."""
    try:
        from film_pipeline.runtime.knowledge import KnowledgeStore

        store = KnowledgeStore()
        table = store.try_load_ai_json("look/lighting_for_emotion.json") or {}
        by = table.get("by_emotion") or {}
        emo = (emotion or "suspicion").strip().lower()
        return dict(by.get(emo) or by.get("suspicion") or {})
    except Exception:
        return {}


def _compose_look_blocks(
    bible: dict[str, Any],
    shot: dict[str, Any],
    light_plan: dict[str, Any],
    *,
    object_shot: bool = False,
) -> dict[str, str]:
    """
    Visible light/color language only — never cite pipeline sources.
    Lead with emotion atmosphere + face modeling for people plates.
    """
    look = shot.get("look") or {}
    film = _film_look(bible)
    scene = _scene_look(bible, shot.get("scene_id"))
    emo = str((shot.get("emotion") or {}).get("primary") or "")
    recipe = _emotion_lighting_recipe(emo) if not object_shot else {}

    tone = _en_phrase(
        look.get("tone") or scene.get("base_tone") or film.get("key"),
        "low-key",
    ).replace("_", " ")
    contrast = _en_phrase(
        look.get("contrast") or scene.get("contrast") or film.get("contrast") or recipe.get("contrast"),
        "high",
    )
    color = _en_phrase(
        look.get("color_temp") or scene.get("color") or recipe.get("color_temp"),
        "motivated practical light",
    )
    key = _en_phrase(look.get("key_light"), "")
    if not key and recipe.get("prompt_en"):
        key = str(recipe.get("prompt_en") or "")
    fill_ratio = look.get("fill_ratio") or ""
    grade = _en_phrase(
        look.get("grade_intent"),
        "controlled deep blacks, readable material detail"
        if object_shot
        else "controlled deep blacks, readable facial detail",
    )
    if object_shot and grade and "facial" in grade.lower():
        grade = "controlled deep blacks, readable material detail"
    palette = _palette_en(film.get("palette"))
    sat = _en_phrase(film.get("saturation"), "")
    portrait = ""
    rim = ""
    if not object_shot:
        portrait = _en_phrase(
            light_plan.get("key")
            or light_plan.get("key_en")
            or recipe.get("face")
            or recipe.get("prompt_en"),
            "",
        )
        rim = _en_phrase(light_plan.get("rim") or light_plan.get("fill"), "")

    atmos_en = str(recipe.get("atmosphere_en") or "").strip()
    atmos_zh = str(recipe.get("atmosphere_zh") or "").strip()
    prompt_zh = str(recipe.get("prompt_zh") or "").strip()
    face_zh = str(recipe.get("face") or "").strip()

    # English: mood first, then face light, then technical grade
    en_bits: list[str] = []
    if not object_shot and atmos_en:
        en_bits.append(f"mood atmosphere: {atmos_en}")
    en_bits.append(f"{tone} lighting")
    en_bits.append(f"{contrast} contrast")
    if not object_shot and portrait:
        en_bits.append(f"face modeling: {portrait}")
    elif not object_shot and recipe.get("prompt_en"):
        en_bits.append(f"face lighting: {recipe.get('prompt_en')}")
    if key and key != portrait:
        en_bits.append(f"motivated key: {key}")
    if rim:
        en_bits.append(f"edge/rim: {rim}")
    if fill_ratio:
        en_bits.append(f"fill about {fill_ratio}")
    if palette:
        en_bits.append("colors: " + ", ".join(palette))
    if sat:
        en_bits.append(sat + " saturation" if "saturation" not in sat else sat)
    en_bits.append(f"color temperature feel: {color}")
    if grade:
        en_bits.append(grade)
    if object_shot:
        en_bits.insert(
            0,
            "object plate: material-readable key, texture micro-shadows, no portrait face recipe",
        )
    en = "LIGHTING & MOOD — " + "; ".join(en_bits) + "."

    # Chinese: 情绪氛围优先，再脸光
    zh_bits: list[str] = []
    if not object_shot and atmos_zh:
        zh_bits.append(f"情绪氛围：{atmos_zh}")
    zh_bits.append(f"{'低调' if 'low' in tone.lower() else '影调'}{tone}")
    zh_bits.append(f"反差{contrast}")
    if not object_shot and (prompt_zh or face_zh):
        zh_bits.append(f"人物打光：{prompt_zh or face_zh}")
    if key:
        zh_bits.append(f"动机主光：{key}")
    if look.get("key_light") and has_cjk(str(look.get("key_light"))):
        kl = str(look.get("key_light"))
        if kl not in "；".join(zh_bits):
            zh_bits.append(f"光源：{kl}")
    if fill_ratio:
        zh_bits.append(f"补光约 {fill_ratio}")
    if palette:
        zh_bits.append("色彩：" + "、".join(palette))
    zh_bits.append(f"色温：{color}")
    if grade:
        zh_bits.append(f"暗部/质感：{grade}")
    if object_shot:
        zh_bits.insert(0, "物镜：材质可读主光，纹理微阴影，不用人像脸谱")
    zh = "【光影与氛围】" + "；".join(zh_bits) + "。"

    return {
        "look_tone": tone,
        "color_temp": color,
        "key_light": key,
        "contrast": contrast,
        "look_block_en": en,
        "look_block_zh": zh,
        "portrait_light_en": portrait,
        "fill_or_rim": rim,
        "portrait_light_motivation": atmos_en or atmos_zh,
        "atmosphere_en": atmos_en,
        "atmosphere_zh": atmos_zh,
    }


def _world_context(bible: dict[str, Any], shot: dict[str, Any]) -> dict[str, str]:
    """Self-contained scene anchors so each clip can be used alone."""
    story = bible.get("story") or {}
    logline = str(story.get("logline") or "").strip()
    scene_id = shot.get("scene_id")
    scene_obj: dict[str, Any] = {}
    for s in bible.get("scenes") or []:
        if s.get("scene_id") == scene_id or s.get("id") == scene_id:
            scene_obj = s
            break
    loc = str(
        scene_obj.get("location")
        or scene_obj.get("setting")
        or scene_obj.get("heading")
        or scene_obj.get("title")
        or ""
    ).strip()
    time_of = str(scene_obj.get("time") or scene_obj.get("time_of_day") or "").strip()
    synopsis = str(scene_obj.get("summary") or scene_obj.get("action") or "").strip()

    names = []
    for c in bible.get("characters") or []:
        n = c.get("name") or c.get("id")
        if n:
            names.append(str(n))
    names_s = ", ".join(names[:4])

    en_parts = []
    if loc and not has_cjk(loc):
        en_parts.append(f"Setting: {loc}")
    elif loc:
        en_parts.append("Setting: deep-dive vessel / contracted world")
    if time_of and not has_cjk(time_of):
        en_parts.append(time_of)
    if logline and not has_cjk(logline):
        en_parts.append(f"Story world: {logline[:160]}")
    elif logline:
        sub = resolve_subject_en(shot)
        beat = resolve_dramatic_beat_en(shot)
        en_parts.append(
            f"Story world: {beat[:100]}. Focus: {sub}"
            if beat
            else "Story world: confined deep-dive mission under corporate pressure"
        )
    if names_s and not has_cjk(names_s):
        en_parts.append(f"People in story: {names_s}")

    zh_parts = []
    if loc:
        zh_parts.append(f"场景：{loc}")
    if time_of:
        zh_parts.append(f"时间：{time_of}")
    if logline:
        zh_parts.append(f"故事背景：{logline[:120]}")
    if synopsis and has_cjk(synopsis):
        zh_parts.append(f"本场：{synopsis[:80]}")
    if names_s:
        zh_parts.append(f"人物：{names_s}")

    return {
        "context_en": ". ".join(en_parts).strip() + ("." if en_parts else ""),
        "context_zh": "。".join(zh_parts).strip() + ("。" if zh_parts else ""),
    }


def _asset_anchors(item: dict[str, Any], limit: int = 2) -> str:
    anchors = item.get("consistency_anchors") or []
    bits = []
    for a in anchors:
        s = str(a).strip()
        if not s:
            continue
        if s.startswith("identity:") or s.startswith("voice"):
            continue
        bits.append(s)
        if len(bits) >= limit:
            break
    return "; ".join(bits)


def _build_subject_image_refs(
    bible: dict[str, Any],
    shot: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Multi-reference image roles for SUBJECT section:
      图1 是谁/是什么 · 图2 是场景 · 图3 是道具/武器 …
    Each clip must restate fully (no 'same as previous').
    """
    sub_en = resolve_subject_en(shot)
    sub_zh = resolve_subject_zh(shot)
    beat_en = resolve_dramatic_beat_en(shot)
    beat_zh = resolve_dramatic_beat_zh(shot)
    blob = f"{sub_en} {sub_zh} {beat_en} {beat_zh}".lower()
    blob_raw = f"{sub_en} {sub_zh} {beat_en} {beat_zh}"

    ab = bible.get("asset_bible") or {}
    chars_assets = list(ab.get("characters") or [])
    props_assets = list(ab.get("props") or [])
    sets_assets = list(ab.get("sets") or [])
    if not chars_assets:
        for c in bible.get("characters") or []:
            chars_assets.append(
                {
                    "name": c.get("name") or c.get("id"),
                    "type": "character",
                    "consistency_anchors": [],
                }
            )

    refs: list[dict[str, str]] = []
    used_names: set[str] = set()

    def _add(role_en: str, role_zh: str, name_en: str, name_zh: str, detail_en: str = "", detail_zh: str = "") -> None:
        key = (name_zh or name_en).strip().lower()
        if not key or key in used_names:
            return
        used_names.add(key)
        refs.append(
            {
                "role_en": role_en,
                "role_zh": role_zh,
                "name_en": name_en.strip(),
                "name_zh": (name_zh or name_en).strip(),
                "detail_en": detail_en.strip(),
                "detail_zh": (detail_zh or detail_en).strip(),
            }
        )

    # 1) Who / what — characters mentioned, else primary object
    people_hit = False
    for c in chars_assets:
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        if name in blob_raw or name.lower() in blob:
            people_hit = True
            det = _asset_anchors(c)
            det_en = det if det and not has_cjk(det) else ""
            # light EN name: keep roman if any anchor has english
            name_en = name if not has_cjk(name) else name
            # try common names
            name_map = {
                "高岩": "Gao Yan",
                "Ananke": "Ananke",
                "技术员A": "Technician A",
                "技术员B": "Technician B",
                "林安": "Lin An",
                "周宁": "Zhou Ning",
            }
            name_en = name_map.get(name, name_en if not has_cjk(name) else f"character {name}")
            _add(
                "who/what (character)",
                "是谁/是什么（人物）",
                name_en,
                name,
                det_en or "keep face and wardrobe identity locked to this reference",
                det or "外貌与服装与此参考图一致",
            )

    if not people_hit:
        # Primary on-screen object / phenomenon as 图1
        # Prefer prop match
        prop_hit = False
        for p in props_assets:
            pname = str(p.get("name") or "").strip()
            if not pname:
                continue
            if pname in blob_raw or any(
                tok in blob for tok in re.findall(r"[\w\u4e00-\u9fff]{2,}", pname.lower())
            ):
                prop_hit = True
                det = _asset_anchors(p)
                _add(
                    "who/what (object)",
                    "是谁/是什么（物件）",
                    pname if not has_cjk(pname) else sub_en or pname,
                    pname,
                    det if det and not has_cjk(det) else "material and shape locked to this reference",
                    det or "材质外形与此参考图一致",
                )
                break
        if not prop_hit:
            # Heuristic prop kinds from subject text
            obj_en, obj_zh = sub_en, sub_zh
            if any(k in blob for k in ("speaker", "oscilloscope", "音箱", "示波器")):
                obj_en = "oscilloscope speaker unit with display"
                obj_zh = "带示波器显示屏的音箱"
            elif any(k in blob for k in ("submarine", "sub ", "潜艇")):
                obj_en = "small exploration submarine exterior"
                obj_zh = "小型勘探潜艇"
            elif any(k in blob for k in ("book", "书", "kant", "康德")):
                obj_en = "worn paperback book (Critique of Practical Reason)"
                obj_zh = "翻毛边的实体书《实践理性批判》"
            elif any(k in blob for k in ("photo", "照片", "工作照")):
                obj_en = "1986 yellowed black-and-white work photo"
                obj_zh = "1986 年泛黄黑白工作照"
            elif any(k in blob for k in ("geometry", "几何", "waveform", "display", "屏")):
                obj_en = "speaker display showing morphing irregular geometry"
                obj_zh = "音箱显示屏上的变形不规则几何"
            _add(
                "who/what (on-screen subject)",
                "是谁/是什么（画面主体）",
                obj_en,
                obj_zh,
                "this is the primary on-screen subject for this clip",
                "本镜画面主主体，身份/外形锁定此参考",
            )

    # 2) Scene — always
    scene_id = shot.get("scene_id")
    scene_obj: dict[str, Any] = {}
    for s in bible.get("scenes") or []:
        if s.get("scene_id") == scene_id or s.get("id") == scene_id:
            scene_obj = s
            break
    set_name_zh = str(
        (sets_assets[0].get("name") if sets_assets else None)
        or scene_obj.get("setting")
        or scene_obj.get("location")
        or "故事场景"
    ).strip()
    set_detail = ""
    if sets_assets:
        set_detail = _asset_anchors(sets_assets[0])
    set_name_en = set_name_zh
    if has_cjk(set_name_zh):
        if any(k in set_name_zh for k in ("潜艇", "深水", "深潜", "舱")):
            set_name_en = "deep-dive exploration submarine interior / turbid deep water world"
        else:
            set_name_en = "story location environment"
    _add(
        "scene (environment)",
        "场景（环境）",
        set_name_en,
        set_name_zh,
        set_detail if set_detail and not has_cjk(set_detail) else "architecture, layout, practical lights locked",
        set_detail or "空间结构、陈设与实用光位置锁定此参考",
    )

    # 3) Extra props / "weapon" / tools if mentioned and not already 图1
    prop_keywords = [
        ("envelope", "信封", "kraft paper envelope", "牛皮纸信封"),
        ("book", "书", "worn hardcover/paperback book", "实体书"),
        ("speaker", "音箱", "speaker with oscilloscope display", "示波器音箱"),
        ("clamp", "断线钳", "long-handle cable cutter", "长柄断线钳"),
        ("multimeter", "万用表", "multimeter", "万用表"),
        ("cup", "马克杯", "stainless mug with coffee", "不锈钢马克杯"),
        ("e-ink", "电子墨水", "personal e-ink tablet", "个人电子墨水屏"),
        ("jar", "密封罐", "sealed sample jar", "物理密封罐"),
        ("photo", "照片", "1986 work photograph", "1986 工作照"),
        ("hand", "手", "pale human hand", "苍白的手"),
    ]
    for en_k, zh_k, en_label, zh_label in prop_keywords:
        if en_k in blob or zh_k in blob_raw:
            # skip if already primary object with same label family
            already = any(
                en_k in (r["name_en"] + r["name_zh"]).lower() or zh_k in (r["name_en"] + r["name_zh"])
                for r in refs
            )
            if already and refs and refs[0]["role_en"].startswith("who/what"):
                # if primary is already this prop, skip duplicate; still may add as tool of character
                if not people_hit:
                    continue
            owner = ""
            owner_zh = ""
            for c in chars_assets:
                n = str(c.get("name") or "")
                if n and n in blob_raw:
                    owner = n if not has_cjk(n) else {
                        "高岩": "Gao Yan",
                        "技术员A": "Technician A",
                        "技术员B": "Technician B",
                    }.get(n, n)
                    owner_zh = n
                    break
            if owner:
                _add(
                    "prop / tool (whose item)",
                    "道具/武器（谁的）",
                    f"{en_label} belonging to {owner}",
                    f"{owner_zh}的{zh_label}",
                    "prop identity locked to this reference image",
                    "道具外形锁定此参考图",
                )
            else:
                _add(
                    "prop / object",
                    "道具/物件",
                    en_label,
                    zh_label,
                    "prop identity locked to this reference image",
                    "道具外形锁定此参考图",
                )
            if len(refs) >= 4:
                break

    # Cap at 4 refs for model clarity
    return refs[:4]


def _short_name_en(r: dict[str, str]) -> str:
    """Bare label only — short noun phrase."""
    name = (r.get("name_en") or r.get("name_zh") or "subject").strip()
    if name.startswith("character "):
        name = name.replace("character ", "", 1)
    role = (r.get("role_en") or "").lower()
    # shorten scene / prop boilerplate
    if "scene" in role or "environment" in role:
        if "sub" in name.lower() or "cabin" in name.lower() or "deep" in name.lower():
            return "sub cabin"
        if len(name) > 36:
            return "the scene"
    if "belonging to" in name:
        # "worn book belonging to Gao Yan" → "Gao Yan's book"
        left, _, right = name.partition(" belonging to ")
        short = left.replace("worn hardcover/paperback ", "").replace("unit with display", "").strip()
        if right:
            return f"{right}'s {short}".replace("  ", " ")
    # speaker
    if "oscilloscope speaker" in name.lower() or "speaker" in name.lower():
        return "the speaker"
    if "small exploration submarine" in name.lower():
        return "the submarine"
    if len(name) > 48:
        return name[:45].rstrip() + "…"
    return name


def _short_name_zh(r: dict[str, str]) -> str:
    name = (r.get("name_zh") or r.get("name_en") or "主体").strip()
    role = r.get("role_zh") or ""
    if "场景" in role:
        if "→" in name:
            name = name.split("→")[-1].strip()
        if "舱" in name or "潜艇" in name:
            return "潜艇舱内"
        if len(name) > 16:
            return "场景"
    # 物件简称
    if "音箱" in name or "示波" in name:
        return "音响"
    if "勘探潜艇" in name or name == "小型勘探潜艇":
        return "潜艇"
    if "实体书" in name or "的书" in name:
        name = name.replace("实体书", "书")
        return name
    name = name.replace("的实体书", "的书")
    if len(name) > 20:
        name = name[:18] + "…"
    return name


def format_subject_refs_en(refs: list[dict[str, str]], focus_en: str = "") -> str:
    """Minimal: Image 1 is Gao Yan. Image 2 is the speaker. Image 3 is the cabin."""
    if not refs:
        return focus_en or "subject"
    parts = [f"Image {i} is {_short_name_en(r)}." for i, r in enumerate(refs, 1)]
    return " ".join(parts)


def format_subject_refs_zh(refs: list[dict[str, str]], focus_zh: str = "") -> str:
    """极简：图1是高岩。图2是音响。图3是场景。图号用户可后改。"""
    if not refs:
        return focus_zh or "主体"
    parts = [f"图{i}是{_short_name_zh(r)}。" for i, r in enumerate(refs, 1)]
    return "".join(parts)


def _clean_move_en(cam: dict[str, Any]) -> str:
    mov = (cam or {}).get("movement") or {}
    prompt = str(mov.get("prompt_en") or "").strip()
    mtype = str(mov.get("type") or "").strip()
    zh = str(mov.get("zh") or "").strip()
    if prompt and not _BAD_MOVE.search(prompt) and not has_cjk(prompt):
        return prompt
    if mtype and not _BAD_MOVE.search(mtype):
        return mtype.replace("_", " ")
    if zh and not has_cjk(zh):
        return f"camera move: {zh}"
    return "locked-off or very slow motivated move"


def _clean_move_zh(cam: dict[str, Any]) -> str:
    mov = (cam or {}).get("movement") or {}
    zh = str(mov.get("zh") or "").strip()
    mtype = str(mov.get("type") or "").strip()
    prompt = str(mov.get("prompt_en") or "").strip()
    if zh and "知识库" not in zh and "服务 beat" not in zh:
        return zh
    if mtype and not _BAD_MOVE.search(mtype):
        table = {
            "Creep In": "缓慢推进",
            "Dolly Out": "拉镜",
            "Dolly In": "推镜",
            "Static Locked-Off": "固定机位",
            "Tilt Down": "下摇",
            "Tilt Up": "上摇",
            "Dutch Angle": "荷兰角（慎用）",
        }
        return table.get(mtype, mtype.replace("_", " "))
    if prompt and not _BAD_MOVE.search(prompt) and not has_cjk(prompt):
        return prompt
    return "缓慢或固定运镜"


# Max spoken lines written into ONE shot prompt (crew rule: one plate ≠ whole scene)
MAX_DIALOGUE_LINES_PER_SHOT = 3


def _dialogue_lines(bible: dict[str, Any], shot: dict[str, Any]) -> list[dict[str, str]]:
    """
    ONLY lines bound to this shot via linked_dialogue.

    Product rule: prompt writer must not dump the whole scene's dialogue into one clip.
    If linked_dialogue is empty → no spoken lines in this prompt (OK for env/insert).
    """
    linked = [str(t).strip() for t in (shot.get("linked_dialogue") or []) if str(t).strip()]
    if not linked:
        return []

    scene_id = shot.get("scene_id")
    catalog: list[dict[str, str]] = []
    for block in bible.get("dialogue") or []:
        if scene_id and block.get("scene_id") != scene_id:
            continue
        for line in block.get("lines") or []:
            text = (line.get("text") or "").strip()
            if not text:
                continue
            char = str(line.get("character") or "Speaker").strip()
            if char in {"画外", "NARRATION"}:
                continue
            if len(text) > 180:
                cut = re.split(r"[。！？]", text, maxsplit=1)[0]
                text = (cut + "。") if cut else text[:120]
            catalog.append(
                {
                    "character": char,
                    "text": text,
                    "delivery": str(line.get("delivery") or "")[:80],
                }
            )

    preferred: list[dict[str, str]] = []
    for t in linked:
        for ln in catalog:
            if t in ln["text"] or ln["text"] in t or t == ln["text"]:
                preferred.append(ln)
                break
        else:
            # linked string not found in catalog — still emit as unknown speaker line
            preferred.append({"character": "Speaker", "text": t[:180], "delivery": ""})

    # dedupe preserve order
    seen: set[tuple[str, str]] = set()
    uniq: list[dict[str, str]] = []
    for ln in preferred:
        k = (ln["character"], ln["text"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(ln)
    return uniq[:MAX_DIALOGUE_LINES_PER_SHOT]


def _is_object_shot(shot: dict[str, Any]) -> bool:
    """Delegate to shared classifier (blocks facial templates on env plates)."""
    return is_environment_or_object_shot(shot)


def _continuity_en(
    stitch: str | None,
    duration_sec: float,
    *,
    subject_en: str = "",
    look_en: str = "",
) -> str:
    """
    Self-contained continuity language. Never say 'same as previous prompt'.
    Re-state identity anchors so the clip stands alone.
    """
    s = (stitch or "single").lower()
    anchors = []
    if subject_en:
        # Keep phrase compact so soft-wrap rarely splits the keyword sequence
        anchors.append(f"same subject identity: {subject_en}")
    if look_en:
        anchors.append("stable lighting palette for the whole take")
    anchor_s = "; ".join(anchors) + ". " if anchors else ""
    if s in {"single", "", "full"}:
        return (
            f"{anchor_s}One continuous take, about {int(round(float(duration_sec or 0)))} seconds, "
            f"smooth motion, no jump cut mid-action."
        )
    # multi-clip: still fully restate — no "previous clip"
    return (
        f"{anchor_s}Continuous take energy for about {int(round(float(duration_sec or 0)))} seconds; "
        f"stable framing, wardrobe, light; photoreal continuity."
    )


def _continuity_zh(
    stitch: str | None,
    duration_sec: float,
    *,
    subject_zh: str = "",
) -> str:
    s = (stitch or "single").lower()
    who = f"主体保持为：{subject_zh}。" if subject_zh else ""
    d = int(round(float(duration_sec or 0)))
    if s in {"single", "", "full"}:
        return f"{who}连续拍摄约 {d} 秒，动作中途不跳切，光影稳定。"
    return (
        f"{who}本段约 {d} 秒，连续镜头感；"
        f"服装、身份、舱体材质、灯光与色调在本段内写全，不依赖其他提示词。"
    )


def _sfx_en(brief: dict[str, Any]) -> str:
    beat = (brief.get("dramatic_beat_en") or "").lower()
    sub = (brief.get("subject_en") or "").lower()
    bits = []
    if any(k in beat or k in sub for k in ("water", "deep", "sub", "ocean", "turbid")):
        bits.append("muffled deep-water pressure, slow metal hull creak")
    if any(k in beat or k in sub for k in ("console", "holo", "gauge", "screen", "oscilloscope")):
        bits.append("soft instrument hum, occasional UI click (no readable UI text)")
    if any(k in beat or k in sub for k in ("book", "hand", "finger", "knock")):
        bits.append("quiet fingertip taps on paper, cloth rustle")
    if brief.get("dialogue") and not brief.get("object_shot"):
        bits.append("clear spoken dialogue only, dry room tone")
    if not bits:
        bits.append("subtle room tone and motivated diegetic action sounds")
    return (
        "SFX only: "
        + "; ".join(bits)
        + ". No music, no score, no BGM, no saxophone theme, no jazz underscore. "
        "No subtitles, no captions, no on-screen text, no watermark, no UI overlays."
    )


def _sfx_zh(brief: dict[str, Any]) -> str:
    return (
        "只保留音效：环境与动作声（水压、金属微动、呼吸、仪器轻响等，按画面合理取用）。"
        "不要音乐、不要配乐、不要主题曲。"
        "不要字幕、不要水印、不要界面文字。"
    )


def build_contract_brief(
    bible: dict[str, Any],
    shot: dict[str, Any],
    clip: dict[str, Any] | None = None,
    style_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact, clean contract for AI / offline writer (no pipeline meta)."""
    ensure_shot_english_slots(shot)
    cam = shot.get("camera") or {}
    emo = shot.get("emotion") or {}
    perf = shot.get("performance") or {}
    light_plan = (perf.get("lighting_plan") or {}) if isinstance(perf, dict) else {}
    dur = (clip or {}).get("duration_sec") or shot.get("duration_sec") or 4
    style = (style_pack or {}).get("label") or (bible.get("meta") or {}).get("style_pack")
    object_shot = _is_object_shot(shot)
    stitch = (clip or {}).get("stitch") or "single"
    look_blocks = _compose_look_blocks(
        bible,
        shot,
        light_plan if isinstance(light_plan, dict) else {},
        object_shot=object_shot,
    )
    ctx = _world_context(bible, shot)
    move_en = _clean_move_en(cam)
    move_zh = _clean_move_zh(cam)
    # Env plates: never keep Dutch / horror catalog moves in the final prose
    if object_shot:
        blob = f"{move_en} {move_zh}".lower()
        if any(k in blob for k in ("dutch", "荷兰", "villain", "horror", "sleeping")):
            beat = f"{shot.get('dramatic_beat_en') or ''} {shot.get('dramatic_beat') or ''}"
            if "push" in beat.lower() or "推" in beat:
                move_en, move_zh = "very slow motivated push-in", "缓推"
            else:
                move_en, move_zh = "static locked-off hold", "锁定固定"
    sub_en = resolve_subject_en(shot)
    sub_zh = resolve_subject_zh(shot)
    cont_en = _continuity_en(
        stitch,
        float(dur),
        subject_en=sub_en,
        look_en=look_blocks["look_block_en"],
    )
    cont_zh = _continuity_zh(stitch, float(dur), subject_zh=sub_zh)
    emo_key = str(emo.get("primary") or "tense")
    brief: dict[str, Any] = {
        "shot_id": shot.get("shot_id"),
        "duration_sec": float(dur),
        "dramatic_beat_en": resolve_dramatic_beat_en(shot),
        "dramatic_beat_zh": resolve_dramatic_beat_zh(shot),
        "subject_en": sub_en,
        "subject_zh": sub_zh,
        "shot_size": shot.get("shot_size"),
        "shot_size_en": _SIZE_EN.get(str(shot.get("shot_size")), str(shot.get("shot_size"))),
        "shot_size_zh": _SIZE_ZH.get(str(shot.get("shot_size")), str(shot.get("shot_size"))),
        "emotion": emo_key,
        "atmosphere_en": _ATMOSPHERE_EN.get(emo_key, f"{emo_key} atmosphere"),
        "atmosphere_zh": _ATMOSPHERE_ZH.get(emo_key, f"{emo_key} 氛围"),
        "emotion_intensity": emo.get("intensity"),
        "camera_body": cam.get("body") or "ARRI Alexa 35 (virtual cinematic look)",
        "camera_move_en": move_en,
        "camera_move_zh": move_zh,
        "lens_mm": cam.get("lens_mm"),
        "aperture": cam.get("aperture") or cam.get("t_stop") or "T2.0",
        "angle": cam.get("angle") or "eye_level",
        "height": cam.get("height") or "eye",
        "look_tone": look_blocks["look_tone"],
        "key_light": look_blocks["key_light"],
        "color_temp": look_blocks["color_temp"],
        "contrast": look_blocks["contrast"],
        "look_block_en": look_blocks["look_block_en"],
        "look_block_zh": look_blocks["look_block_zh"],
        "portrait_light_en": look_blocks["portrait_light_en"],
        "fill_or_rim": look_blocks["fill_or_rim"],
        "context_en": ctx["context_en"],
        "context_zh": ctx["context_zh"],
        "image_refs": _build_subject_image_refs(bible, shot),
        "style": style,
        "object_shot": object_shot,
        "dialogue": [] if object_shot else _dialogue_lines(bible, shot),
        "stitch": stitch,
        "continuity_en": cont_en,
        "continuity_zh": cont_zh,
        "format_required": [
            "1_subject",
            "2_camera_gear",
            "3_storyline",
            "4_sfx_no_music_no_subs",
        ],
        "rules_for_writer": [
            "each prompt fully self-contained",
            "no same-as-previous",
            "no pipeline jargon",
            "visible light only",
            "subject as Image1 who/what Image2 scene Image3 prop",
        ],
    }
    brief["subject_block_en"] = format_subject_refs_en(
        brief["image_refs"], focus_en=sub_en
    )
    brief["subject_block_zh"] = format_subject_refs_zh(
        brief["image_refs"], focus_zh=sub_zh
    )
    if not object_shot:
        brief["performance_en"] = {
            "physiology": perf.get("physiology_en") or "",
            "micro_actions": perf.get("micro_actions_en") or [],
            "gaze": perf.get("gaze_en") or "",
            "voice": perf.get("voice_hint_en") or "",
            "intensity": perf.get("intensity_label_en") or "",
        }
        brief["performance_zh"] = {
            "physiology": perf.get("physiology_zh") or "",
            "micro_actions": perf.get("micro_actions") or [],
            "gaze": perf.get("gaze") or "",
            "voice": perf.get("voice_hint") or "",
            "intensity": perf.get("intensity_label_zh") or "",
        }
    return brief


def _dialogue_en_block(brief: dict[str, Any]) -> str:
    parts = []
    for d in brief.get("dialogue") or []:
        delivery = d.get("delivery") or ""
        if any(x in delivery for x in ("跳过", "原剧本")):
            delivery = ""
        bit = f'{d.get("character")} says: "{d.get("text")}"'
        if delivery and not has_cjk(delivery):
            bit += f" ({delivery})"
        elif delivery:
            bit += f" (delivery: measured)"
        parts.append(bit + ".")
    return " ".join(parts)


def _dialogue_zh_block(brief: dict[str, Any]) -> str:
    parts = []
    for d in brief.get("dialogue") or []:
        parts.append(f"{d.get('character')}说：「{d.get('text')}」。")
    return "".join(parts)


def write_prompts_offline(brief: dict[str, Any]) -> dict[str, str]:
    """Four-part prompts: self-contained, video-model language only."""
    dur = float(brief.get("duration_sec") or 4)
    beat_en = brief.get("dramatic_beat_en") or "Scene action"
    beat_zh = brief.get("dramatic_beat_zh") or beat_en
    sub_en = brief.get("subject_en") or "subject"
    sub_zh = brief.get("subject_zh") or sub_en
    size_en = brief.get("shot_size_en") or "shot"
    size_zh = brief.get("shot_size_zh") or ""
    move_en = brief.get("camera_move_en") or "slow camera move"
    move_zh = brief.get("camera_move_zh") or "缓慢运镜"
    style = brief.get("style") or "cinematic"
    style_en = str(style).replace("_", " ")
    object_shot = bool(brief.get("object_shot"))
    body = brief.get("camera_body") or "ARRI Alexa 35 (virtual cinematic look)"
    lens = brief.get("lens_mm")
    aperture = brief.get("aperture") or "T2.0"
    angle = brief.get("angle") or "eye_level"
    height = brief.get("height") or "eye"
    cont_en = brief.get("continuity_en") or _continuity_en(
        brief.get("stitch"), dur, subject_en=sub_en
    )
    cont_zh = brief.get("continuity_zh") or _continuity_zh(
        brief.get("stitch"), dur, subject_zh=sub_zh
    )
    sfx_en = _sfx_en(brief)
    sfx_zh = _sfx_zh(brief)
    ctx_en = brief.get("context_en") or ""
    ctx_zh = brief.get("context_zh") or ""
    atmos_en = brief.get("atmosphere_en") or "tense atmosphere"
    atmos_zh = brief.get("atmosphere_zh") or "紧张氛围"
    light_en = brief.get("look_block_en") or (
        f"Light and grade: {brief.get('look_tone') or 'low-key'}, "
        f"{brief.get('color_temp') or 'motivated practical light'}."
    )
    light_zh = brief.get("look_block_zh") or (
        f"光影：{brief.get('look_tone') or 'low-key'}。"
    )

    lens_bit = f"{lens}mm" if lens else "prime lens"
    gear_en = (
        f"{body}; {lens_bit} lens, {aperture}; "
        f"{angle} angle, camera height {height}; {size_en}."
    )
    gear_zh = (
        f"{body}；{lens_bit}，{aperture}；"
        f"{angle} 角度，高度 {height}；{size_zh or size_en}。"
    )

    # Subject = multi-ref image cards (图1 是谁/什么, 图2 场景, 图3 道具…)
    subject_line_en = brief.get("subject_block_en") or sub_en
    subject_line_zh = brief.get("subject_block_zh") or sub_zh
    if not brief.get("subject_block_en") and ctx_en:
        subject_line_en = f"{sub_en}. {ctx_en}"
    if not brief.get("subject_block_zh") and ctx_zh:
        subject_line_zh = f"{sub_zh}。{ctx_zh}"

    # --- English free ---
    free_story = (
        f"What happens: {beat_en}. "
        f"Atmosphere: {atmos_en}. "
        f"Camera move: {move_en}. "
        f"{light_en} "
        f"{cont_en} "
        f"Photoreal {style_en} cinema, natural motion."
    )
    free_en = format_prompt_for_delivery(
        f"1. SUBJECT: {subject_line_en}\n"
        f"2. CAMERA GEAR & PARAMETERS: {gear_en}\n"
        f"3. STORYLINE: {free_story}\n"
        f"4. AUDIO: {sfx_en}"
    )

    # --- English guided ---
    if object_shot:
        guided_story = (
            f"What happens: {beat_en}. "
            f"Show materials, surfaces, and environment in frame only. "
            f"Atmosphere: {atmos_en}. "
            f"Camera: {move_en} as {size_en}. "
            f"{light_en} "
            f"{cont_en} "
            f"Photoreal {style_en} cinema."
        )
    else:
        perf = brief.get("performance_en") or {}
        phys = perf.get("physiology") or f"natural body language under {atmos_en}"
        micros = perf.get("micro_actions") or []
        micro_s = "; ".join(micros[:3]) if micros else "small natural gestures"
        dlg = _dialogue_en_block(brief)
        guided_story = (
            f"What happens: {beat_en}. "
            f"Atmosphere: {atmos_en}. "
            f"Performance: {phys}. Micro-actions: {micro_s}. "
            f"Eyes/gaze: {perf.get('gaze') or 'clear motivated eye-line'}. "
            f"Camera: {move_en} as {size_en}. "
            f"{light_en} "
            f"{cont_en} "
            f"Photoreal {style_en} cinema, coherent anatomy and identity."
        )
        # Only this shot's linked lines (max 3). Cinematic verbs OK if subject is speaker.
        if dlg:
            guided_story += (
                f" Spoken lines for THIS shot only (exact wording, labeled speaker): {dlg}"
            )

    guided_en = format_prompt_for_delivery(
        f"1. SUBJECT: {subject_line_en}\n"
        f"2. CAMERA GEAR & PARAMETERS: {gear_en}\n"
        f"3. STORYLINE: {guided_story}\n"
        f"4. AUDIO: {sfx_en}"
    )

    # --- Chinese free (also for generation — full product, not reading aid) ---
    free_zh = format_prompt_for_delivery(
        f"1. 指定主体：{subject_line_zh}\n"
        f"2. 摄影设备与参数：{gear_zh}\n"
        f"3. 故事线：画面发生——{beat_zh}。"
        f"氛围：{atmos_zh}。运镜：{move_zh}。"
        f"{light_zh}{cont_zh}"
        f"写实电影感，风格 {style_en}。\n"
        f"4. 音效：{sfx_zh}"
    )

    # --- Chinese guided (direct feed for CN video models) ---
    if object_shot:
        guided_zh_story = (
            f"画面发生——{beat_zh}。"
            f"只拍环境与物件的材质、轮廓、反光。"
            f"氛围：{atmos_zh}。运镜：{move_zh}（{size_zh}）。"
            f"{light_zh}{cont_zh}"
            f"写实电影，风格 {style_en}。"
        )
    else:
        perf_zh = brief.get("performance_zh") or {}
        phys_zh = perf_zh.get("physiology") or f"符合氛围的自然身体状态"
        micros_zh = perf_zh.get("micro_actions") or []
        micro_zh_s = "；".join(micros_zh[:3]) if micros_zh else "自然的小动作"
        dlg_zh = _dialogue_zh_block(brief)
        guided_zh_story = (
            f"画面发生——{beat_zh}。氛围：{atmos_zh}。"
            f"表演：{phys_zh}。微动作：{micro_zh_s}。"
            f"视线：{perf_zh.get('gaze') or '有明确落点的视线'}。"
            f"运镜：{move_zh}（{size_zh}）。"
            f"{light_zh}{cont_zh}"
            f"写实电影，身份与光影稳定，风格 {style_en}。"
        )
        if dlg_zh:
            guided_zh_story += f" 本镜台词：{dlg_zh}"

    guided_zh = format_prompt_for_delivery(
        f"1. 指定主体：{subject_line_zh}\n"
        f"2. 摄影设备与参数：{gear_zh}\n"
        f"3. 故事线：{guided_zh_story}\n"
        f"4. 音效：{sfx_zh}"
    )

    return {
        "actor_free_prompt": free_en.strip() + "\n",
        "director_guided_prompt": guided_en.strip() + "\n",
        "actor_free_prompt_zh": free_zh.strip() + "\n",
        "director_guided_prompt_zh": guided_zh.strip() + "\n",
        "writer": "offline_plain",
    }


_SYSTEM = """You write FINAL prompts for VIDEO generation models (Chinese and English both usable).

The model only understands visible/audio scene description.
It does NOT understand pipeline jargon or references to other prompts.

MANDATORY four-part structure for BOTH languages (each section on its own line; use real newlines):
1. SUBJECT — minimal, e.g. Image 1 is Gao Yan. / 图1是高岩。图2是音响。
2. CAMERA GEAR & PARAMETERS — body, lens, T-stop, angle, height, shot size
3. STORYLINE — what happens THIS clip; performance; dialogue with clear speaker
   (导演说 / 图1是导演+诧异问/低声说 OK); light as visible effects; duration
4. AUDIO — SFX only; No music; No subtitles

Output JSON keys:
  actor_free_prompt, director_guided_prompt  (English — generation-ready)
  actor_free_prompt_zh, director_guided_prompt_zh  (Chinese — ALSO generation-ready, NOT "reading aid only")

Use newline characters between the 4 sections. Soft-wrap long sentences.

ABSOLUTELY FORBIDDEN:
- 同上 / same as previous
- pipeline jargon, music/BGM, subtitles
- 【看懂用】【非主投喂】 banners
- dumping whole-scene dialogue into one shot (only this shot's lines)

Rules:
- EN and ZH are equal products for video models.
- Prefer subject_block / look_block / continuity / atmosphere from contract.

- object_shot true → materials/environment only, no facial physiology.
- Dialogue text EXACT. English product; Chinese = same meaning, clean language.
- Photoreal cinematic; honor duration_sec.
"""


def write_prompts_with_llm(brief: dict[str, Any], llm: LLMClient | None = None) -> dict[str, str]:
    llm = llm or LLMClient()
    user = (
        "Write final prompts for this shot contract (must use 4-part format):\n"
        + json.dumps(brief, ensure_ascii=False, indent=2)
    )
    raw = llm.complete_json(_SYSTEM, user)
    out = {
        "actor_free_prompt": str(raw.get("actor_free_prompt") or "").strip(),
        "director_guided_prompt": str(raw.get("director_guided_prompt") or "").strip(),
        "actor_free_prompt_zh": str(raw.get("actor_free_prompt_zh") or "").strip(),
        "director_guided_prompt_zh": str(raw.get("director_guided_prompt_zh") or "").strip(),
        "writer": "llm",
    }
    if not out["actor_free_prompt"] or not out["director_guided_prompt"]:
        raise ValueError("LLM returned empty main prompts")
    if not out["actor_free_prompt_zh"] or not out["director_guided_prompt_zh"]:
        off = write_prompts_offline(brief)
        out["actor_free_prompt_zh"] = out["actor_free_prompt_zh"] or off["actor_free_prompt_zh"]
        out["director_guided_prompt_zh"] = (
            out["director_guided_prompt_zh"] or off["director_guided_prompt_zh"]
        )
    # Always normalize line breaks for delivery
    for k in (
        "actor_free_prompt",
        "director_guided_prompt",
        "actor_free_prompt_zh",
        "director_guided_prompt_zh",
    ):
        out[k] = format_prompt_for_delivery(out[k])
    return out


def write_final_prompts_for_clip(
    bible: dict[str, Any],
    shot: dict[str, Any],
    clip: dict[str, Any] | None = None,
    style_pack: dict[str, Any] | None = None,
    llm: LLMClient | None = None,
    prefer_llm: bool = True,
) -> dict[str, str]:
    """
    Public entry: try AI writer when live; else plain offline writer.
    """
    brief = build_contract_brief(bible, shot, clip=clip, style_pack=style_pack)
    llm = llm or LLMClient()
    if prefer_llm and not llm.dry_run and llm.api_key:
        try:
            return write_prompts_with_llm(brief, llm=llm)
        except Exception:
            offline = write_prompts_offline(brief)
            offline["writer"] = "offline_fallback"
            return offline
    return write_prompts_offline(brief)
