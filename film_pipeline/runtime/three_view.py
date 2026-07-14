"""Build character three-view (reference sheet) prompts — 原版布局强化版.

- Left 50%: ultra-large facial close-up
- Right 50%: front/back/side full body with black face boxes
- Must state ethnicity
"""

from __future__ import annotations

from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore

_POSTURE_HINTS = [
    (("冷静", "克制", "短句", "cold", "restrain", "control"), "intellectual"),
    (("职业", "权力", "领导", "power", "boss"), "confident_professional"),
    (("温", "柔", "亲", "gentle", "soft", "tender"), "elegant"),
    (("酷", "街头", "cool", "street"), "cool_street"),
    (("可爱", "活泼", "cute", "playful"), "cute_playful"),
]

# loose keyword → English ethnicity label for image models
_ETHNICITY_HINTS = [
    (("东亚", "中国", "华人", "日本", "韩国", "east asian", "chinese", "japanese", "korean"), "East Asian"),
    (("东南亚", "越南", "泰国", "southeast asian", "thai", "vietnamese"), "Southeast Asian"),
    (("南亚", "印度", "south asian", "indian"), "South Asian"),
    (("白人", "欧裔", "caucasian", "white", "european"), "White / Caucasian"),
    (("黑人", "非裔", "african", "black"), "Black / African"),
    (("拉丁", "hispanic", "latino", "latina"), "Hispanic / Latino"),
    (("中东", "middle eastern", "arab"), "Middle Eastern"),
    (("混血", "mixed"), "Mixed race"),
]


def load_template(store: KnowledgeStore | None = None) -> dict[str, Any]:
    store = store or KnowledgeStore()
    return store.try_load_ai_json("asset/three_view_template.json") or {}


def pick_posture(voice: str = "", role: str = "", name: str = "") -> tuple[str, str]:
    blob = f"{voice} {role} {name}".lower()
    opts = load_template().get("posture_options") or {}
    for keys, opt in _POSTURE_HINTS:
        if any(k.lower() in blob for k in keys):
            return opt, opts.get(opt, opts.get("intellectual", "Thoughtful elegance"))
    return "intellectual", opts.get(
        "intellectual",
        "Thoughtful elegance, one hand near chin, contemplative gaze",
    )


def resolve_ethnicity(char: dict[str, Any], style_pack: dict[str, Any] | None = None) -> str:
    """Prefer explicit fields; else keyword; else style default."""
    for key in ("ethnicity", "race", "人种", "种族"):
        val = char.get(key)
        if val and str(val).strip():
            return str(val).strip()
    blob = " ".join(
        str(char.get(k) or "")
        for k in ("name", "voice", "want", "need", "arc", "description", "notes")
    ).lower()
    for keys, label in _ETHNICITY_HINTS:
        if any(k.lower() in blob for k in keys):
            return label
    tpl = load_template()
    defaults = tpl.get("ethnicity_defaults") or {}
    style_id = (style_pack or {}).get("id") or ""
    return defaults.get(style_id) or defaults.get("default") or "East Asian"


def infer_character_fields(char: dict[str, Any], style_pack: dict[str, Any] | None = None) -> dict[str, str]:
    name = char.get("name") or char.get("id") or "Character"
    voice = char.get("voice") or ""
    want = char.get("want") or ""
    pack = style_pack or {}
    film_look = pack.get("film_look") or {}
    palette = ", ".join(film_look.get("palette") or ["cinematic neutral"])
    style_id = pack.get("id") or ""
    ethnicity = resolve_ethnicity(char, pack)

    if "noir" in style_id or "cold" in palette.lower() or "cyan" in palette.lower():
        clothing = (
            "dark tailored coat over muted knit sweater, charcoal trousers, "
            "understated urban night wardrobe matching neo-noir mood"
        )
        shoes = "matte black leather shoes, practical low profile"
        hair = "neat dark hair, slightly damp night texture, natural parting"
        face = (
            "restrained expression, natural uneven skin, "
            "subtle under-eye fatigue, realistic pores, natural bone structure matching stated ethnicity"
        )
    else:
        clothing = (
            "simple contemporary layered clothes in muted tones, "
            "story-appropriate everyday outfit"
        )
        shoes = "simple everyday shoes matching the outfit"
        hair = "natural medium-dark hair, clean everyday style"
        face = (
            "natural facial features, realistic skin texture with pores, "
            "minimal sheer makeup, expressive eyes, natural bone structure matching stated ethnicity"
        )

    # if user already provided detailed face/hair in char card, prefer them
    if char.get("hair") or char.get("发型"):
        hair = str(char.get("hair") or char.get("发型"))
    if char.get("face") or char.get("面部") or char.get("facial_features"):
        face = str(char.get("face") or char.get("面部") or char.get("facial_features"))
    if char.get("clothing") or char.get("服装"):
        clothing = str(char.get("clothing") or char.get("服装"))
    if char.get("shoes") or char.get("鞋"):
        shoes = str(char.get("shoes") or char.get("鞋"))

    posture_key, posture = pick_posture(voice=voice, role=want, name=name)

    return {
        "name": str(name),
        "ETHNICITY": ethnicity,
        "HAIR_STYLE_AND_COLOR": hair,
        "FACIAL_FEATURES": face,
        "EARRINGS_AND_NECKLACE": str(
            char.get("jewelry") or char.get("配饰") or "minimal or no jewelry"
        ),
        "HEAD_ACCESSORIES": str(char.get("headwear") or char.get("头饰") or "no headwear"),
        "POSTURE_DESCRIPTION": posture,
        "CLOTHING_DESCRIPTION": clothing,
        "SHOES_DESCRIPTION": shoes,
        "PROPS_OR_EMPTY": str(char.get("prop") or char.get("道具") or "nothing"),
        "posture_key": posture_key,
        "inferred_note_zh": (
            f"人种：{ethnicity}。"
            f"剧本未细写外貌时按风格包与声口「{voice or '未标注'}」推断（可改）；"
            f"姿态 {posture_key}。"
            f"布局：左50%超大面部特写，右50%全身三视图+脸部黑块。"
        ),
    }


def build_character_sheet_prompt(
    char: dict[str, Any],
    style_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """English sheet_prompt (primary) + Chinese summary."""
    tpl = load_template()
    fields = infer_character_fields(char, style_pack)
    template = tpl.get("template_en") or ""
    prompt = template
    for key in (
        "ETHNICITY",
        "HAIR_STYLE_AND_COLOR",
        "FACIAL_FEATURES",
        "EARRINGS_AND_NECKLACE",
        "HEAD_ACCESSORIES",
        "POSTURE_DESCRIPTION",
        "CLOTHING_DESCRIPTION",
        "SHOES_DESCRIPTION",
        "PROPS_OR_EMPTY",
    ):
        prompt = prompt.replace("{" + key + "}", fields.get(key, ""))

    name = fields["name"]
    ethnicity = fields["ETHNICITY"]
    zh_sum = (tpl.get("zh_summary_template") or "【三视图】{name}（人种：{ethnicity}）").format(
        name=name, ethnicity=ethnicity
    )
    zh_sum += " " + fields["inferred_note_zh"]

    return {
        "sheet_prompt": prompt.strip(),
        "negative_prompt": "",
        "sheet_prompt_zh_summary": zh_sum,
        "template_vars": fields,
        "ethnicity": ethnicity,
        "views": ["face_closeup_left_50pct", "full_front", "full_back", "full_side"],
        "image_size_hint": tpl.get("image_size_hint") or "1792x1024",
    }


def build_prop_sheet_prompt(name: str, anchors: list[str] | None = None) -> dict[str, str]:
    anchors = anchors or []
    detail = ", ".join(anchors) if anchors else "consistent scale and wear marks"
    prompt = (
        f"Professional product reference sheet of {name} on neutral gray background, "
        f"multi-view layout: top view, side view, three-quarter view, "
        f"photoreal commercial photography, 8K, consistent material, {detail}, "
        f"no people, no text overlay"
    )
    zh = f"【道具三视图】{name}：灰底，俯视/侧视/3/4 视图，写实电商产品图。"
    return {"sheet_prompt": prompt, "negative_prompt": "", "sheet_prompt_zh_summary": zh}


def build_set_sheet_prompt(name: str, anchors: list[str] | None = None) -> dict[str, str]:
    anchors = anchors or []
    detail = ", ".join(anchors) if anchors else "consistent architecture and props"
    prompt = (
        f"Location design reference sheet for {name}, multi-view environment: "
        f"wide master, left wall, right wall, corner detail, "
        f"photoreal cinematic set stills, consistent layout, {detail}, "
        f"neutral presentation lighting, 8K, no crowds"
    )
    zh = f"【场景多视图】{name}：总览/左墙/右墙/角落细节。"
    return {"sheet_prompt": prompt, "negative_prompt": "", "sheet_prompt_zh_summary": zh}
