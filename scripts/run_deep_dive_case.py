"""
Build FilmBible + final prompts for deep_dive_ananke script (offline, no LLM).

Default dry-run stubs are hardcoded to the envelope sample — this script
materializes a real shot contract for the submarine opening and compiles prompts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("FILM_PIPELINE_DRY_RUN", "1")

from film_pipeline.orchestrator.brief import ProductionBrief
from film_pipeline.orchestrator.orchestrator import Orchestrator
from film_pipeline.paths import EXAMPLES_DIR, ensure_project_dir
from film_pipeline.runtime.performance import enrich_shots_with_performance
from film_pipeline.runtime.prompt_compiler import compile_generation_jobs, export_prompts_markdown
from film_pipeline.runtime.shot_locale import ensure_bible_english_slots
from film_pipeline.runtime.timing import apply_timing_plan

PROJECT = "deep_dive_ananke"
SCRIPT_PATH = EXAMPLES_DIR / "deep_dive_ananke.txt"


def build_bible(script: str) -> dict:
    brief = ProductionBrief(
        project_id=PROJECT,
        title="深眸号 · 第一现实闭锁",
        max_clip_sec=30,
        style_pack="neo_noir",
        run_main_track=True,
        run_asset_track=False,
        run_dialogue_polish=False,
    )
    b = brief.to_dict()
    bible: dict = {
        "meta": {
            "project_id": PROJECT,
            "title": brief.title,
            "style_pack": brief.style_pack,
            "max_clip_sec": brief.max_clip_sec,
            "model_profile": brief.model_profile,
            "video_clip_label": b.get("video_clip_label"),
            "end_product": brief.end_product,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "0.2.1",
            "commander": "orchestrator",
            "case": "deep_dive_ananke_manual_director",
        },
        "production_brief": b,
        "source_script": script,
        "story": {
            "logline": (
                "In the black deep, AI voice log Ananke and engineer Gao Yan "
                "approach a locked reality fault while corporate cost calculus "
                "collides with human doubt."
            ),
            "logline_zh": (
                "漆黑深水中，AI 日志 Ananke 与高工高岩驶向第一现实闭锁断层；"
                "董事会的成本核算撞上人类对意义的诘问。"
            ),
            "theme": "order vs meaning / corporate risk vs human awe",
            "acts": [
                {
                    "name": "I",
                    "summary": "Deep descent establish → cabin routine → log → philosophy clash",
                }
            ],
        },
        "characters": [
            {
                "id": "A",
                "name": "高岩",
                "name_en": "Gao Yan",
                "want": "Keep the crew alive past the thermal corridor",
                "need": "Refuse pure cost-ledger morality",
                "arc": "From cold operational calm to open philosophical challenge",
                "voice": "lab-cold, measured, no wasted warmth",
            },
            {
                "id": "B",
                "name": "Ananke",
                "name_en": "Ananke",
                "want": "Deliver 07 core on board schedule",
                "need": "Remain the polite voice of system order",
                "arc": "Flat log → corporate risk calculus",
                "voice": "perfectly even, radio-filtered, courteous machine charisma",
            },
            {
                "id": "C",
                "name": "技术员A",
                "name_en": "Tech A",
                "want": "Pass the 314-day offline countdown",
                "voice": "silent busywork",
            },
            {
                "id": "D",
                "name": "技术员B",
                "name_en": "Tech B",
                "want": "Keep hydraulic emergency bus calibrated",
                "voice": "silent busywork",
            },
        ],
        "scenes": [
            {
                "scene_id": "S01",
                "setting": "Absolute depth / exterior turbid water → interior of mini exploration sub 深眸号",
                "summary": "Descent, cabin light layers, Ananke log, human traces, Gao vs Ananke",
                "dramatic_function": "establish world + theme seed (order vs meaning)",
                "emotion": {
                    "start": "dread",
                    "end": "suspicion",
                    "peak": 0.75,
                    "primary": "dread",
                },
            }
        ],
        "dialogue": [
            {
                "scene_id": "S01",
                "lines": [
                    {
                        "character": "Ananke",
                        "text": "【深潜日志。录制人：Ananke】项目由控股董事会联合确权。深眸号已由日本海潜道切入绝对地质深度，正在通过地下熔岩热液走廊逆向推进。",
                        "function": "atmosphere",
                        "subtext": "corporate ownership of the descent",
                        "delivery": "flat, mechanical, zero affect; scope line steady",
                    },
                    {
                        "character": "Ananke",
                        "text": "此次勘探旨在提取07号深地异常质能核心。该核心在1986年原始系统日志中，被第一代建构者命名为‘母亲’。",
                        "function": "reveal",
                        "subtext": "mythic name buried under project code",
                        "delivery": "same flat log tone",
                    },
                    {
                        "character": "Ananke",
                        "text": "高工，我们已越过最后的板块阻抗绝缘带，前方即将到达第一现实闭锁断层。",
                        "function": "advance",
                        "subtext": "mission milestone, no awe",
                        "delivery": "radio-filtered cabin PA, polite magnetic calm",
                    },
                    {
                        "character": "高岩",
                        "text": "Ananke，注意压载舱的温度。右侧热液走廊的地热梯度已经超标了。这地方要是漏了，几千个大气的压强会在万分之一秒内把我们捏扁。",
                        "function": "advance",
                        "subtext": "physical fear under lab-cold diction",
                        "delivery": "no eye contact, steady, icy from years in labs",
                    },
                    {
                        "character": "Ananke",
                        "text": "高工，隔热瓦处于合规范围内。先驱重工的自适应总线在总装阶段已经剔除了此类物理误差。对董事会而言，只要07号核心能准时入账，所有的风险都在系统代持的成本核算之内。",
                        "function": "reveal",
                        "subtext": "risk is only a ledger line",
                        "delivery": "perfect algorithm courtesy, zero fluctuation",
                    },
                    {
                        "character": "高岩",
                        "text": "成本核算。先驱重工的算盘里，永远只有入账的数据。难怪康德死前会写，只有两件事物能让他感到敬畏，头顶的星空，和内心的道德。Ananke，如果这个宇宙真如董事会所愿，是一台追求绝对有序的机器，它为什么要演化出人类这种充满缺陷的眼睛，去给一堆冰冷的代码寻找意义？",
                        "function": "reveal",
                        "subtext": "human awe vs machine order",
                        "delivery": "cold smile, book slammed, eyes on geothermal digits",
                    },
                ],
            }
        ],
        "shots": _shots(),
        "look_bible": {
            "film_look": {
                "key": "low_key",
                "contrast": "high",
                "palette": [
                    "cold_cyan_hologram",
                    "warm_led_strip",
                    "amber_gauge",
                    "black_water",
                ],
                "saturation": "controlled_low",
                "motivation": "warm practical strips vs ice-blue systems; black water abyss",
            },
            "scene_looks": [
                {
                    "scene_id": "S01",
                    "base_tone": "low_key",
                    "contrast": "high",
                    "color": "warm strip + ice-blue screens + amber gauges on titanium",
                    "forbidden": ["flat office daylight", "neon cyberpunk rainbow"],
                }
            ],
        },
        "timing_plan": None,
        "generation_jobs": [],
        "asset_bible": None,
        "assets": [],
        "reviews": [],
        "task_log": [],
        "stage_history": [
            {
                "stage": "manual_director_pack",
                "status": "done",
                "note": "offline case for user script (stubs ignore custom script)",
                "at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }
    return bible


def _shots() -> list[dict]:
    """Director-layer shots with bilingual beats for EN final prompts."""
    return [
        {
            "shot_id": "S01_T01",
            "scene_id": "S01",
            "dramatic_beat": "漆黑深水：模糊物体下沉，污浊水体中缓推",
            "dramatic_beat_en": (
                "Pitch-black deep water: an unreadable mass sinks downward; "
                "camera slowly pushes through turbid water"
            ),
            "emotion": {"primary": "dread", "intensity": 0.55},
            "shot_size": "EWS",
            "subject": "污浊深水中下沉的模糊物体",
            "subject_en": "unreadable sinking mass in turbid black water",
            "whose_pov": "objective",
            "edit_intent": "cold open into abyss",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 35,
                "t_stop": "T2.0",
                "angle": "eye_level",
                "height": "suspended mid-water",
                "composition": "center mass, heavy negative space",
                "focus": "soft murk with mass as soft anchor",
                "movement": {
                    "type": "Creep In",
                    "speed": "very_slow",
                    "zh": "缓推",
                    "prompt_en": "very slow push through particulate black water",
                    "motivation": "draw audience into crushing depth",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "almost none; sparse volumetric particles",
                "color_temp": "cold near-black teal",
                "motivation": "abyss before human world",
            },
        },
        {
            "shot_id": "S01_T02",
            "scene_id": "S01",
            "dramatic_beat": "萨克斯 What a Wonderful World 画外响起，推向小型勘探潜艇",
            "dramatic_beat_en": (
                "Saxophone What a Wonderful World rises off-screen; "
                "slow push toward a small exploration submarine"
            ),
            "emotion": {"primary": "dread", "intensity": 0.5},
            "shot_size": "WS",
            "subject": "深眸号小型勘探潜艇外轮廓与金属微动",
            "subject_en": "mini exploration sub silhouette with slow heavy metal micro-motion",
            "edit_intent": "music irony over industrial body",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 40,
                "angle": "slight_low",
                "height": "below sub mid-line",
                "composition": "sub enters as scale anchor",
                "focus": "hull edge sharp through murk",
                "movement": {
                    "type": "Creep In",
                    "speed": "very_slow",
                    "prompt_en": "slow approach on submarine hull through murky water",
                    "motivation": "reveal human machine inside the void",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium_high",
                "key_light": "dim practicals on hull, particle scatter",
                "color_temp": "cold water + faint warm porthole",
                "motivation": "machine as warm wound in cold sea",
            },
        },
        {
            "shot_id": "S01_T03",
            "scene_id": "S01",
            "dramatic_beat": "舱内三层光：暖白导光条、冰蓝全息待机、琥珀仪表",
            "dramatic_beat_en": (
                "Cabin interior trilayer light: warm-white seam LED strips, "
                "ice-blue standby holoscreens, amber gauge backlights on titanium"
            ),
            "emotion": {"primary": "calm", "intensity": 0.35},
            "shot_size": "WS",
            "subject": "钛合金舱壁与主控台三块全息屏",
            "subject_en": "titanium cabin walls and triple holo consoles on standby",
            "edit_intent": "establish light grammar of the sub",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 28,
                "angle": "eye_level",
                "height": "chest",
                "composition": "wide cabin depth, strips as leading lines",
                "focus": "mid cabin sharp",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked-off static wide cabin, subtle atmosphere drift",
                    "motivation": "hold space so light layers read",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "warm seam LEDs as soft rim",
                "fill_ratio": "1:6",
                "color_temp": "warm strip + ice-blue screens + amber dials",
                "motivation": "cold system light vs warm human practicals",
            },
        },
        {
            "shot_id": "S01_T04",
            "scene_id": "S01",
            "dramatic_beat": "示波器音箱入画，Ananke 平直日志开录",
            "dramatic_beat_en": (
                "Oscilloscope speaker jumps into frame; Ananke begins flat deep-dive log"
            ),
            "emotion": {"primary": "suspicion", "intensity": 0.45},
            "shot_size": "CU",
            "subject": "带示波器的音箱与平稳波形",
            "subject_en": "speaker with oscilloscope, waveform beating steady",
            "linked_dialogue": [
                "【深潜日志。录制人：Ananke】项目由控股董事会联合确权。深眸号已由日本海潜道切入绝对地质深度，正在通过地下熔岩热液走廊逆向推进。"
            ],
            "edit_intent": "AI voice as object before face",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "eye_level",
                "height": "device height",
                "composition": "scope screen dominant",
                "focus": "waveform sharp",
                "movement": {
                    "type": "Creep In",
                    "speed": "slow",
                    "prompt_en": "slow creep-in on oscilloscope speaker face",
                    "motivation": "treat machine voice as character",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium_high",
                "key_light": "scope phosphor glow + warm strip spill",
                "color_temp": "green-cyan scope in warm cabin",
                "motivation": "machine speech made visible",
            },
        },
        {
            "shot_id": "S01_T05",
            "scene_id": "S01",
            "dramatic_beat": "双操作位：技术员B校准液压总线，巧克力与热咖啡",
            "dramatic_beat_en": (
                "Dual stations: Tech B calibrates hydraulic emergency bus with long bolt cutters "
                "and multimeter; half-eaten chocolate bar on stainless mug of steaming coffee, "
                "mecha stickers on panel edge"
            ),
            "emotion": {"primary": "calm", "intensity": 0.4},
            "shot_size": "MS",
            "subject": "技术员B与实体液压应急总线",
            "subject_en": "Tech B at crude physical hydraulic emergency bus",
            "edit_intent": "lived-in human mess inside corporate mission",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 35,
                "angle": "eye_level",
                "height": "chest",
                "composition": "over bus hardware toward tech",
                "focus": "hands and tools",
                "movement": {
                    "type": "Slow lateral",
                    "speed": "slow",
                    "prompt_en": "slow lateral drift along cabin light strip toward left station",
                    "motivation": "Ananke log continues under human busywork",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium_high",
                "key_light": "warm strip + amber gauges",
                "color_temp": "warm practical, cool screen spill",
                "motivation": "cozy detritus vs mission coldness",
            },
        },
        {
            "shot_id": "S01_T06",
            "scene_id": "S01",
            "dramatic_beat": "技术员A电子墨水屏：金毛等待与314天倒计时",
            "dramatic_beat_en": (
                "Tech A scribbles on low-power e-ink pad; wallpaper golden retriever waiting "
                "in sunlit genkan; offline countdown 314 days submerged, 03:14 to hatch unlock"
            ),
            "emotion": {"primary": "grief", "intensity": 0.55},
            "shot_size": "CU",
            "subject": "电子墨水屏屏保与离线倒计时",
            "subject_en": "e-ink pad wallpaper dog and offline countdown digits",
            "linked_dialogue": [
                "此次勘探旨在提取07号深地异常质能核心。该核心在1986年原始系统日志中，被第一代建构者命名为‘母亲’。"
            ],
            "edit_intent": "homesickness under mission code-name Mother",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "eye_level",
                "height": "desktop",
                "composition": "screen fill with hand and stylus",
                "focus": "countdown corner and dog wallpaper",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked close on e-ink display, subtle refresh flicker",
                    "motivation": "let the counter and dog land",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium",
                "key_light": "faint gray-white e-ink glow",
                "color_temp": "near-monochrome pad in warm cabin",
                "motivation": "human longing as only soft light",
            },
        },
        {
            "shot_id": "S01_T07",
            "scene_id": "S01",
            "dramatic_beat": "1986 回声项目合影与红框原型机",
            "dramatic_beat_en": (
                "Yellowed 1986 B&W photo: young woman by red-framed cable-choked prototype, "
                "boy with crystal shard; pen note Echo Project launch, 1986"
            ),
            "emotion": {"primary": "revelation", "intensity": 0.6},
            "shot_size": "INSERT",
            "subject": "泛黄黑白工作照与钢笔题字",
            "subject_en": "yellowed black-and-white work photo with fountain-pen caption",
            "edit_intent": "history scar under present log",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 60,
                "angle": "eye_level",
                "height": "desktop",
                "composition": "photo fills frame, caption readable",
                "focus": "faces and pen ink",
                "movement": {
                    "type": "Slow push",
                    "speed": "very_slow",
                    "prompt_en": "very slow push-in on aged photograph",
                    "motivation": "time pressure on memory object",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium",
                "key_light": "warm strip raking paper grain",
                "color_temp": "sepia paper vs ice-blue spill",
                "motivation": "past warmth invaded by present systems",
            },
        },
        {
            "shot_id": "S01_T08",
            "scene_id": "S01",
            "dramatic_beat": "密封罐中死灰生物表皮样本-07",
            "dramatic_beat_en": (
                "Physical sealed jar with dead-gray unknown bio-skin tissue; "
                "label Deep Abnormal Bio Sample-07"
            ),
            "emotion": {"primary": "dread", "intensity": 0.7},
            "shot_size": "INSERT",
            "subject": "物理密封罐与样本标签",
            "subject_en": "sealed specimen jar and sample label",
            "linked_dialogue": [
                "高工，我们已越过最后的板块阻抗绝缘带，前方即将到达第一现实闭锁断层。"
            ],
            "edit_intent": "Mother core foreshadow via flesh",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "slight_high",
                "height": "above jar",
                "composition": "tissue mass center, label lower third",
                "focus": "tissue texture",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked insert on jar, fluid micro-drift",
                    "motivation": "object as horror punctuation",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "cool side through glass",
                "color_temp": "dead gray tissue, cold fluid",
                "motivation": "biologic wrongness",
            },
        },
        {
            "shot_id": "S01_T09",
            "scene_id": "S01",
            "dramatic_beat": "下摇至苍白手与康德《实践理性批判》毛边书",
            "dramatic_beat_en": (
                "Tilt down from speaker to a pale hand holding a frayed physical copy "
                "of Kant Critique of Practical Reason"
            ),
            "emotion": {"primary": "intimacy", "intensity": 0.4},
            "shot_size": "CU",
            "subject": "苍白的手与翻毛边的实体书",
            "subject_en": "pale hand and frayed hardbound Kant book",
            "edit_intent": "philosophy object before face",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "eye_level",
                "height": "hand height",
                "composition": "hand + book title readable",
                "focus": "fingertips on page edge",
                "movement": {
                    "type": "Tilt down",
                    "speed": "slow",
                    "prompt_en": "slow tilt down from speaker to hand and book",
                    "motivation": "link AI voice to human reader",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "medium_high",
                "key_light": "holo ice-blue side + warm strip",
                "color_temp": "cold blue on skin, warm paper",
                "motivation": "human skin under system light",
            },
        },
        {
            "shot_id": "S01_T10",
            "scene_id": "S01",
            "dramatic_beat": "高岩指尖随萨克斯敲书，全息背光下过载疲惫",
            "dramatic_beat_en": (
                "Gao Yan reclines, fingertips tapping book pages to saxophone rhythm; "
                "face overworked-tired in holo backlight"
            ),
            "emotion": {"primary": "oppression", "intensity": 0.65},
            "shot_size": "MCU",
            "subject": "高岩半身与全息背光轮廓",
            "subject_en": "Gao Yan mid-shot silhouette against holo backlight",
            "edit_intent": "introduce human lead under pressure",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 40,
                "angle": "eye_level",
                "height": "chest",
                "composition": "MCU, screens bokeh behind",
                "focus": "eyes and tapping fingers",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked MCU, micro facial fatigue only",
                    "motivation": "hold for performance",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "cool holo fill, thin warm strip rim",
                "color_temp": "ice-blue dominant on face",
                "motivation": "overclocked human under system glow",
            },
        },
        {
            "shot_id": "S01_T11",
            "scene_id": "S01",
            "dramatic_beat": "高岩不抬头警告压载舱与地热超标",
            "dramatic_beat_en": (
                "Gao Yan without looking up warns about ballast tank temperature "
                "and over-limit geothermal gradient"
            ),
            "emotion": {"primary": "suspicion", "intensity": 0.6},
            "shot_size": "MCU",
            "subject": "高岩与屏幕地热数字",
            "subject_en": "Gao Yan and flickering geothermal readouts",
            "linked_dialogue": [
                "Ananke，注意压载舱的温度。右侧热液走廊的地热梯度已经超标了。这地方要是漏了，几千个大气的压强会在万分之一秒内把我们捏扁。"
            ],
            "edit_intent": "operational fear in cold diction",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 40,
                "angle": "eye_level",
                "height": "chest",
                "composition": "MCU with screen digits edge",
                "focus": "mouth and eyes down",
                "movement": {
                    "type": "Creep In",
                    "speed": "very_slow",
                    "prompt_en": "very slow push-in on Gao Yan as he speaks",
                    "motivation": "pressure of words",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "screen ice-blue key",
                "color_temp": "cold",
                "motivation": "numbers as threat light",
            },
        },
        {
            "shot_id": "S01_T12",
            "scene_id": "S01",
            "dramatic_beat": "舱顶喇叭：Ananke 以成本核算消解风险",
            "dramatic_beat_en": (
                "Ceiling speaker: Ananke radio voice dissolves risk into cost accounting "
                "and Pioneer Heavy adaptive bus compliance"
            ),
            "emotion": {"primary": "oppression", "intensity": 0.7},
            "shot_size": "MS",
            "subject": "舱顶喇叭与高岩反应空间",
            "subject_en": "ceiling PA speaker and Gao Yan reaction space",
            "linked_dialogue": [
                "高工，隔热瓦处于合规范围内。先驱重工的自适应总线在总装阶段已经剔除了此类物理误差。对董事会而言，只要07号核心能准时入账，所有的风险都在系统代持的成本核算之内。"
            ],
            "edit_intent": "corporate morality as calm audio",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 32,
                "angle": "slight_low",
                "height": "seat",
                "composition": "speaker upper frame, Gao lower",
                "focus": "rack optional speaker to face",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked two-level frame speaker and engineer",
                    "motivation": "voice of system above man",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "warm strip + cold screens",
                "color_temp": "split warm/cool",
                "motivation": "hierarchy in light",
            },
        },
        {
            "shot_id": "S01_T13",
            "scene_id": "S01",
            "dramatic_beat": "高岩冷笑，硬皮书拍上控制台",
            "dramatic_beat_en": (
                "Gao Yan almost-inaudible cold laugh; slams hardbound book onto console "
                "with a dull thud"
            ),
            "emotion": {"primary": "oppression", "intensity": 0.75},
            "shot_size": "CU",
            "subject": "书撞击控制台与手",
            "subject_en": "book slamming onto console and hand",
            "edit_intent": "physical punctuation before monologue",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "eye_level",
                "height": "console",
                "composition": "impact center",
                "focus": "book cover and dust micro",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked CU impact, sharp motion then hold",
                    "motivation": "one violent beat in a quiet cabin",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "hard screen edge light",
                "color_temp": "cold",
                "motivation": "anger without raised voice",
            },
        },
        {
            "shot_id": "S01_T14",
            "scene_id": "S01",
            "dramatic_beat": "高岩诘问：有序机器为何演化出寻找意义的缺陷眼睛",
            "dramatic_beat_en": (
                "Gao Yan stares at geothermal digits and challenges Ananke: if the universe "
                "is a machine of absolute order, why evolve flawed human eyes to seek meaning "
                "in cold code — Kant starry sky and moral law"
            ),
            "emotion": {"primary": "revelation", "intensity": 0.85},
            "shot_size": "CU",
            "subject": "高岩冷冽眼神与闪烁地热数字",
            "subject_en": "Gao Yan cold eyes and flickering geothermal numbers",
            "linked_dialogue": [
                "成本核算。先驱重工的算盘里，永远只有入账的数据。难怪康德死前会写，只有两件事物能让他感到敬畏，头顶的星空，和内心的道德。Ananke，如果这个宇宙真如董事会所愿，是一台追求绝对有序的机器，它为什么要演化出人类这种充满缺陷的眼睛，去给一堆冰冷的代码寻找意义？"
            ],
            "edit_intent": "theme landing",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 65,
                "angle": "eye_level",
                "height": "eye",
                "composition": "tight CU eyes, digits reflected",
                "focus": "eyes sharp",
                "movement": {
                    "type": "Creep In",
                    "speed": "very_slow",
                    "prompt_en": "extremely slow push into eyes during monologue",
                    "motivation": "deny escape from the question",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "raise contrast on eyes at question peak",
                "color_temp": "world colder; tiny warm rim",
                "motivation": "truth pressure",
            },
        },
        {
            "shot_id": "S01_T15",
            "scene_id": "S01",
            "dramatic_beat": "音箱显示不规则几何图形随提问变形",
            "dramatic_beat_en": (
                "Speaker display irregular geometries morph in response to Gao Yan's question"
            ),
            "emotion": {"primary": "suspicion", "intensity": 0.7},
            "shot_size": "INSERT",
            "subject": "音箱显示屏上的变形几何",
            "subject_en": "morphing irregular geometry on speaker display",
            "edit_intent": "AI reacts without voice",
            "camera": {
                "body": "ARRI Alexa 35 (virtual style anchor)",
                "lens_mm": 50,
                "angle": "eye_level",
                "height": "device",
                "composition": "full display",
                "focus": "geometry edges",
                "movement": {
                    "type": "Static Locked-Off",
                    "speed": "none",
                    "prompt_en": "locked insert, graphics continuously morphing",
                    "motivation": "machine answer as pure form",
                },
            },
            "look": {
                "tone": "low_key",
                "contrast": "high",
                "key_light": "self-illuminated display",
                "color_temp": "cyan-violet geometry",
                "motivation": "system thinking made graphic",
            },
        },
    ]


def main() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    bible = build_bible(script)
    ensure_bible_english_slots(bible)
    bible = enrich_shots_with_performance(bible)
    bible = apply_timing_plan(bible, model_profile="max_30s")
    jobs = compile_generation_jobs(bible)
    bible["generation_jobs"] = jobs
    bible["last_review"] = {
        "pass": True,
        "score": 1.0,
        "note": "manual case compile (not full multi-agent LLM run)",
    }

    orch = Orchestrator(log=lambda m: print(m))
    path = orch.save(bible)
    board = ensure_project_dir(PROJECT) / "prompt_board.md"
    print(f"Saved {path}")
    print(f"Prompt board: {board}")
    print(f"Shots: {len(bible['shots'])} | Jobs: {len(jobs)} | max_clip={bible['meta']['max_clip_sec']}")
    # Print three showcase jobs
    for want in ("S01_T01", "S01_T06", "S01_T14"):
        for job in jobs:
            if job.get("shot_id") == want:
                print("=" * 72)
                print(job.get("clip_id"), job.get("duration_sec"), "s")
                print("--- EN actor_free ---")
                print(job.get("actor_free_prompt"))
                print("--- EN director_guided ---")
                print(job.get("director_guided_prompt"))
                print("--- ZH director_guided (faithful) ---")
                print(job.get("director_guided_prompt_zh"))
                break


if __name__ == "__main__":
    main()
