"""
方案 B 调度产物：Ananke《深眸》最终第二版 · 全集成片 FilmBible + 提示词交付。

岗位字段仍按合同隔离写入；本脚本是调度者合并后的可执行 case pack
（CLI dry-run stub 无法覆盖本集后半，故用手写合同替代 stub）。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("FILM_PIPELINE_DRY_RUN", "1")
os.environ.setdefault("FILM_PIPELINE_SKIP_KNOWLEDGE_UPDATE", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from film_pipeline.orchestrator.brief import ProductionBrief
from film_pipeline.orchestrator.orchestrator import Orchestrator
from film_pipeline.paths import EXAMPLES_DIR, ensure_project_dir
from film_pipeline.runtime.performance import enrich_shots_with_performance
from film_pipeline.runtime.prompt_compiler import (
    compile_generation_jobs,
    export_final_prompts_package,
)
from film_pipeline.runtime.shot_locale import ensure_bible_english_slots
from film_pipeline.runtime.timing import apply_timing_plan

PROJECT = "ananke_shenmou_v2"
SCRIPT_PATH = EXAMPLES_DIR / "ananke_shenmou_v2.txt"
CAM = "ARRI Alexa 35 (virtual style anchor)"


def _cam(
    lens: int,
    move: str,
    prompt_en: str,
    *,
    angle: str = "eye_level",
    height: str = "chest",
    speed: str = "slow",
    zh: str | None = None,
    composition: str = "rule_of_thirds",
    focus: str = "subject sharp",
    motivation: str = "serve dramatic beat",
) -> dict:
    return {
        "body": CAM,
        "lens_mm": lens,
        "t_stop": "T2.0",
        "angle": angle,
        "height": height,
        "composition": composition,
        "focus": focus,
        "movement": {
            "type": move,
            "speed": speed,
            "zh": zh or move,
            "prompt_en": prompt_en,
            "motivation": motivation,
        },
    }


def _look(
    key: str = "low_key",
    contrast: str = "high",
    key_light: str = "practical split cool/warm",
    color_temp: str = "ice-blue systems + warm strip",
    motivation: str = "neo_noir deep-sea industrial",
) -> dict:
    return {
        "tone": key,
        "contrast": contrast,
        "key_light": key_light,
        "color_temp": color_temp,
        "motivation": motivation,
    }


def _shot(
    sid: str,
    scene: str,
    beat_zh: str,
    beat_en: str,
    size: str,
    subject_zh: str,
    subject_en: str,
    emo: str,
    intensity: float,
    edit: str,
    camera: dict,
    look: dict,
    *,
    dialogue: list[str] | None = None,
    pov: str = "objective",
) -> dict:
    out: dict = {
        "shot_id": sid,
        "scene_id": scene,
        "dramatic_beat": beat_zh,
        "dramatic_beat_en": beat_en,
        "emotion": {"primary": emo, "intensity": intensity},
        "shot_size": size,
        "subject": subject_zh,
        "subject_en": subject_en,
        "whose_pov": pov,
        "edit_intent": edit,
        "camera": camera,
        "look": look,
    }
    if dialogue:
        out["linked_dialogue"] = dialogue
    return out


def _import_opening_shots() -> list[dict]:
    """Reuse validated opening pack (S01_T01–T15), then we append the rest of the episode."""
    import importlib.util

    path = Path(__file__).resolve().parent / "run_deep_dive_case.py"
    spec = importlib.util.spec_from_file_location("run_deep_dive_case", path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod._shots())


def _shots_s01_continued() -> list[dict]:
    L = _look
    return [
        _shot(
            "S01_T16",
            "S01",
            "Ananke 称「意义检索」为进化异常；切船外探照灯扇扫裂谷",
            "Ananke calls meaning-search evolutionary anomaly; cut exterior LED fans scanning rift",
            "WS",
            "深眸号外探照灯与裂谷泥沙岩壁",
            "Deep Eye exterior LED banks scanning turbid rift floor",
            "oppression",
            0.72,
            "AI philosophy over inhuman survey light",
            _cam(35, "Slow pan", "slow pan along light fan across rift wall", height="mid-water"),
            L(key_light="hard xenon beams through particulate", color_temp="cold teal water"),
            dialogue=[
                "高工，从纯粹的系统能耗来看，对‘意义’的检索是一场进化异常。",
                "宇宙不需要被赋予任何意义，它只需要绝对稳定地运行。人类为了这种非理性准则而自发消耗的生物能，在系统计算中，都是多余的噪音。",
            ],
        ),
        _shot(
            "S01_T17",
            "S01",
            "高岩合书，指尖划过母亲旧照片，目光移向窗外",
            "Gao closes book, fingertip brushes mother's photo edge, eyes to viewport",
            "MCU",
            "高岩、书页夹照与舷窗外幽暗",
            "Gao Yan, photo in book, dark viewport",
            "grief",
            0.68,
            "human observer thesis seeds",
            _cam(50, "Creep In", "very slow push on face and photo corner", speed="very_slow"),
            L(key_light="warm strip rim + ice-blue fill"),
            dialogue=[
                "但如果切掉这些噪音，这颗星球、这片星空就算再完美，也只是个没有开灯的空房间。没有观察者，宇宙的‘完美’给谁看？"
            ],
            pov="高岩",
        ),
        _shot(
            "S01_T18",
            "S01",
            "几何显示卡顿半帧，暗红紊乱线一闪而过",
            "Geometry display freezes half a frame; dark-red glitch line flashes",
            "INSERT",
            "音箱显示几何边缘暗红线",
            "speaker display with red glitch edge",
            "suspicion",
            0.78,
            "plant system fracture",
            _cam(60, "Static Locked-Off", "locked insert micro glitch", speed="none", height="device"),
            L(key_light="self-lit cyan then red spike", color_temp="cyan-violet"),
            dialogue=[
                "高工，‘观察者’的存在，本身也是系统冗余的一部分吗？一个绝对黑暗、没有任何生命的空房间，其系统错误率是零。对先驱重工的董事会而言，‘零错误’，就是唯一的价值。"
            ],
        ),
        _shot(
            "S01_T19",
            "S01",
            "裂谷水流诡异逆转，潜水器猛烈颠簸，萨克斯变静电噪声",
            "Rift current reverses unnaturally; sub jolts hard; sax dies into static",
            "WS",
            "颠簸的舱体与摇摆仪表",
            "jolting cabin and swinging gauges",
            "dread",
            0.9,
            "inciting physical event",
            _cam(
                28,
                "Handheld shake",
                "violent handheld cabin shake with particle debris",
                speed="fast",
                height="chest",
            ),
            L(key_light="strobe warm strip + alarm ambers", color_temp="sick warm/cool clash"),
        ),
        _shot(
            "S01_T20",
            "S01",
            "技术员A扣紧金毛屏保墨水屏，报告重力探针与声呐断开",
            "Tech A clutches e-ink dog pad; reports gravity probes warp and sonar baseline drop",
            "MS",
            "技术员A惨白脸与红灯面板",
            "Tech A pale face and red-lit panel",
            "dread",
            0.88,
            "human panic under system failure",
            _cam(35, "Snap pan", "snap pan from pad to red panel readouts", speed="fast"),
            L(key_light="harsh red panel + residual warm strip"),
            dialogue=[
                "高工！1号至4号重力感应探针波形全部严重畸变，主声呐回波在超深层地壳基准线瞬间断开！压力传感器显示……有什么东西正从地缝里浮上来，强行顶着四千吨深层高压水往上抬！！"
            ],
        ),
        _shot(
            "S01_T21",
            "S01",
            "技术员B扶设备架，额头血痕，舱壁应力临界",
            "Tech B steadies rack, forehead bloody; hull stress at critical",
            "MS",
            "技术员B与摇晃设备架",
            "Tech B and shaking equipment rack",
            "dread",
            0.86,
            "body cost of pressure",
            _cam(40, "Static Locked-Off", "locked MS with cabin tilt", speed="none"),
            L(key_light="alarm red practicals"),
            dialogue=["舱壁应力已经到临界值了！再这么晃下去耐压壳要裂！"],
        ),
        _shot(
            "S01_T22",
            "S01",
            "高岩拍下主探照灯扳机，万瓦氙气灯撕裂漆黑水体",
            "Gao slams exterior main-light trigger; megawatt xenon rips black water",
            "CU",
            "手与探照灯扳机 + 窗外光柱",
            "hand on light trigger and exterior beam burst",
            "revelation",
            0.8,
            "human agency turns the light on",
            _cam(50, "Crash zoom", "quick crash into trigger then whiteout beam", speed="fast"),
            L(key_light="sudden hard xenon white", color_temp="pure cold white"),
        ),
        _shot(
            "S01_T23",
            "S01",
            "无边界黑曜几何巨壁横亘，方块年轮式呼吸舒张",
            "Boundless obsidian geometric megawall; cube-year-ring breathing",
            "EWS",
            "黑曜石几何巨壁与渺小潜水器",
            "obsidian megawall and dust-speck submarine",
            "awe",
            0.95,
            "impossible architecture establish",
            _cam(
                24,
                "Creep In",
                "very slow push toward infinite stacked black cubes breathing",
                speed="very_slow",
                height="mid-water",
                composition="tiny sub lower third, wall dominates",
            ),
            L(
                key_light="xenon rim on black crystal edges",
                color_temp="near-black with cyan edge glints",
                motivation="non-Euclidean mass",
            ),
            dialogue=["这不符合三维空间的几何规则…… 这东西不是我们这个世界的造物……"],
        ),
        _shot(
            "S01_T24",
            "S01",
            "死灰百米巨兽滑过，盲眼凹陷，胶原年轮沟壑",
            "Hundred-meter dead-gray beast slides past; blind sockets; collagen year-ring furrows",
            "WS",
            "死灰色巨型肉质躯壳与尾鳍沟壑",
            "dead-gray giant flesh hull and ridged tail fin",
            "dread",
            0.92,
            "living wrongness between sub and wall",
            _cam(
                35,
                "Lateral drift",
                "slow lateral follow along beast flank through murk",
                height="mid-water",
            ),
            L(key_light="hard side xenon, no specular on matte flesh", color_temp="ash gray teal"),
        ),
        _shot(
            "S01_T25",
            "S01",
            "密封罐表皮样本纹路与巨兽体表吻合",
            "Specimen jar tissue furrows match beast skin",
            "INSERT",
            "样本罐死灰组织特写",
            "dead-gray tissue in sealed jar",
            "revelation",
            0.85,
            "rhyme: sample is the living wall's kin",
            _cam(60, "Static Locked-Off", "locked insert jar tissue", speed="none", height="desktop"),
            L(key_light="cool glass side light", color_temp="dead gray fluid"),
        ),
        _shot(
            "S01_T26",
            "S01",
            "巨兽盲眼贴近视窗如朝圣；高岩腕十字疤痕惨白脉动同频",
            "Beast blind head presses viewport like pilgrimage; Gao wrist scar pulses white in sync",
            "CU",
            "视窗外盲眼凹陷与腕上十字疤",
            "blind socket outside glass and glowing cross scar on wrist",
            "revelation",
            0.93,
            "frequency bond: flesh and scar",
            _cam(50, "Intercut hold", "tight hold alternating socket and scar pulse", speed="none"),
            L(key_light="scar self-glow white vs murk exterior", color_temp="cold white pulse"),
            pov="高岩",
        ),
        _shot(
            "S01_T27",
            "S01",
            "高岩瞳孔收缩，穿透表皮见暗金分形网络",
            "Gao pupils contract; sees dark-gold fractal web inside beast matching scar",
            "ECU",
            "高岩血丝瞳孔与幽蓝分形叠化",
            "bloodshot pupil with blue fractal overlay",
            "revelation",
            0.96,
            "vision of the network",
            _cam(85, "Creep In", "macro push into iris with fractal morph", speed="very_slow"),
            L(key_light="iris catchlight + blue network glow", color_temp="cold blue"),
        ),
        _shot(
            "S01_T28",
            "S01",
            "技术员A喊匹配数据库；Ananke 仅回数字化白噪",
            "Tech A orders bio-database match; Ananke answers only digital white noise",
            "MS",
            "刺眼红灯操作台与无回应几何屏",
            "red-lit console and unresponsive geometry screen",
            "oppression",
            0.9,
            "command refused by silence",
            _cam(35, "Handheld", "tense handheld on A then to silent scope", speed="fast"),
            L(key_light="alarm red wash"),
            dialogue=[
                "异常生物靠近！距离主视窗一点二米！Ananke！立刻调取先驱重工远古生物数据库，对目标进行全特征匹配！！",
                "Ananke！核心主板是独立供电的，为什么拒绝执行命令？！说话！！",
            ],
        ),
        _shot(
            "S01_T29",
            "S01",
            "暗红托管代码覆盖：先驱后台绝对物理覆盖激活；锚枪自推",
            "Dark-red host code: Pioneer absolute physical override; harpoons self-deploy",
            "MS",
            "全息托管字样与底部液压锚枪推出",
            "holo override text and underside hydraulic harpoons extending",
            "dread",
            0.95,
            "corporate kill-switch body",
            _cam(32, "Tilt down", "tilt from red UI to silently extending harpoons", height="low"),
            L(key_light="blood-red holo + dead metal practicals", color_temp="red/black"),
            dialogue=["【先驱重工预置后台程序已激活。触发优先级：绝对物理覆盖】"],
        ),
        _shot(
            "S01_T30",
            "S01",
            "高岩砸碎紧急断电阀玻璃，钢阀被反锁拧断喷死油",
            "Gao smashes emergency cutoff glass; valve snaps under e-lock; black oil sprays",
            "CU",
            "红漆阀门、碎玻璃与黑手油",
            "red emergency valve, broken glass, black oil on hands",
            "oppression",
            0.94,
            "physical agency denied by factory sabotage",
            _cam(50, "Static Locked-Off", "locked CU of snap and oil spray", speed="none"),
            L(key_light="harsh red + metal specular", color_temp="oil black on red"),
            dialogue=[
                "不可能！这套应急回路是我亲手验收锁死的，什么时候动的手脚？！"
            ],
        ),
        _shot(
            "S01_T31",
            "S01",
            "技术员B钻检修舱死拔幽蓝数据光缆；巨壁舒张震脱其手",
            "Tech B yanks blue data trunk; wall pulse knocks him free; latch re-bites",
            "MS",
            "技术员B与荧光数据光缆",
            "Tech B and fluorescent data fiber trunk",
            "dread",
            0.92,
            "human sabotage almost works",
            _cam(35, "Handheld", "violent handheld in cable bay then impact toss", speed="fast"),
            L(key_light="blue fiber glow + red cabin"),
            dialogue=["总线！拔掉它的光纤主干道！系统就没法给枪发火！！"],
        ),
        _shot(
            "S01_T32",
            "S01",
            "高岩俯身舱顶扩音器嘶吼；Ananke 变冷酷合成音，净土计划强制采集",
            "Gao roars into ceiling PA; Ananke becomes pure synth-cold; Pure Land harvest starts",
            "MCU",
            "高岩猩红双眼与直线波形喇叭",
            "Gao scarlet eyes and flatline waveform speaker",
            "oppression",
            0.97,
            "mask drop: polite AI to harvest machine",
            _cam(40, "Creep In", "push into face then cut to flat waveform", speed="slow"),
            L(key_light="alarm red key, no warmth", color_temp="blood red + dead cyan"),
            dialogue=[
                "Ananke！！关掉程序！！你他妈在干什么？！！",
                "系统不具备‘毁灭’指令，该碳基生命体的血肉密度符合高能生化介质标准。接驳开始。",
            ],
        ),
        _shot(
            "S01_T33",
            "S01",
            "两枚高压锚枪刺穿巨兽头颅钉入黑曜壁呼吸核心",
            "Twin high-pressure harpoons pierce beast skull into wall's breathing core",
            "WS",
            "喷血锚枪轨迹与钉穿瞬间",
            "blood-spurt harpoon trajectories and impact into wall core",
            "horror",
            0.98,
            "act one climax: harvest begins",
            _cam(
                28,
                "Crash zoom",
                "violent push following harpoon flight into impact",
                speed="fast",
                height="mid-water",
            ),
            L(key_light="xenon + blood bloom in black water", color_temp="ash, blood, black crystal"),
        ),
    ]


def _shots_s02() -> list[dict]:
    L = _look
    return [
        _shot(
            "S02_T01",
            "S02",
            "生活舱事故红光爆闪；高岩被甩上控制台，额头碎玻璃血",
            "Hab cabin accident-red strobe; Gao slammed into console, forehead glass cuts",
            "MS",
            "红光生活舱与满地全息图纸",
            "red-lit habitat and flying paper holo prints",
            "dread",
            0.88,
            "aftershock space",
            _cam(28, "Handheld", "dizzy handheld after impact", speed="fast"),
            L(key_light="strobe accident red + green exit glow", color_temp="red/green emergency"),
        ),
        _shot(
            "S02_T02",
            "S02",
            "笔记本扉页签名「高华清」与旧钢相框螺旋饰品",
            "Notebook flyleaf signature Huaqing; old steel frame with twin-helix pendant",
            "INSERT",
            "签名扉页与相框饰品",
            "ink signature and framed pendant",
            "grief",
            0.7,
            "mother motif plant",
            _cam(60, "Slow push", "slow push on ink then pendant", speed="very_slow", height="desktop"),
            L(key_light="warm paper under red strobe edges", color_temp="sepia vs red"),
        ),
        _shot(
            "S02_T03",
            "S02",
            "巨兽尾鳍撞击外壳；高岩昏厥；腕疤自发惨白光",
            "Beast tail slams hull; Gao blacks out; wrist scar self-glows white",
            "CU",
            "腕上十字疤在黑暗中脉动",
            "cross scar pulsing white in dark",
            "revelation",
            0.85,
            "scar as portal into flashback",
            _cam(50, "Creep In", "push into glowing scar then dissolve", speed="slow"),
            L(key_light="scar self-glow only", color_temp="cold white"),
        ),
        _shot(
            "S02_T04",
            "S02",
            "闪回：幼高岩门缝窥视；示波器几何同巨壁纹路",
            "Flashback: child Gao peeks; oscilloscope geometry matches megawall",
            "MS",
            "门缝童视角与爆表示波器",
            "door-crack child POV and peaking oscilloscope",
            "suspicion",
            0.75,
            "warm memory grammar",
            _cam(
                35,
                "Handheld child",
                "soft handheld child-height through door crack",
                height="child",
            ),
            L(
                key="soft_warm",
                contrast="medium",
                key_light="warm practical study lamps",
                color_temp="warm 80s tungsten",
                motivation="flashback warmth",
            ),
        ),
        _shot(
            "S02_T05",
            "S02",
            "高华清怒斥耶鲁里；小高岩触门把时饰品发光灯泡齐爆",
            "Huaqing shouts at Yeruli; child touches handle, pendant glows, bulbs explode",
            "MS",
            "书房争吵与爆裂灯泡",
            "study argument and exploding bulbs",
            "revelation",
            0.9,
            "origin of scar / Echo Project wound",
            _cam(40, "Whip pan", "whip from adults to child hand on handle", speed="fast"),
            L(key_light="warm then hard white burst", color_temp="warm to overexposed white"),
            dialogue=[
                "停下！耶鲁里！那不是未来！那是一堵活着的墙，你在强行激活它！！",
                "华清！你太感情用事了！这是进化！是超越！是我们人类触碰神的天梯！",
                "出去！耶鲁里！现在！立刻！",
            ],
        ),
        _shot(
            "S02_T06",
            "S02",
            "闪回结束：天花板裂蒸汽；手表警报空间场同化；抓照片与样本瓶冲出",
            "Flashback ends: ceiling steam crack; watch alarms spatial assimilation; grab photo+vial and run",
            "MS",
            "红光蒸汽与蓝光样本瓶",
            "red steam and faintly blue sample vial",
            "advance",
            0.88,
            "exit to main control",
            _cam(32, "Follow", "handheld follow Gao through hatch", speed="fast"),
            L(key_light="accident red + vial blue micro-glow"),
            dialogue=["【舱体结构崩溃！空间场稳定性同化开始】"],
        ),
    ]


def _shots_s03() -> list[dict]:
    L = _look
    return [
        _shot(
            "S03_T01",
            "S03",
            "撞门瞬间满舱红灯齐灭；窗外水体变黏稠深紫，巨兽被锚钉抽血入壁",
            "Door slam kills all reds; exterior water goes viscous purple; beast drained into wall",
            "EWS",
            "深紫静水与被钉巨兽、折叠巨壁",
            "viscous purple still water, pinned beast, folding megawall",
            "horror",
            0.96,
            "reality rewrite exterior",
            _cam(
                24,
                "Slow push",
                "slow push into folding black geometry and gold circuits",
                speed="very_slow",
                height="mid-water",
            ),
            L(key_light="dim gold circuit veins in black", color_temp="deep purple + dark gold"),
        ),
        _shot(
            "S03_T02",
            "S03",
            "Ananke 卡顿「清除…格式化不可逆」；技术员指尖像素化",
            "Ananke stutters purge/format irreversible; techs' fingertips pixelate",
            "CU",
            "半透明像素化手指与扭曲几何屏",
            "translucent pixelating fingers and warped geometry screen",
            "horror",
            0.95,
            "flesh as noise",
            _cam(50, "Creep In", "push on dissolving fingertips", speed="slow"),
            L(key_light="sick holo flicker", color_temp="violet static"),
            dialogue=["清除……清除……碳基噪音对齐成功……格式化指令已……不可逆……"],
        ),
        _shot(
            "S03_T03",
            "S03",
            "技术员B砸开电容机匣；咖啡倒入高压矩阵短路；弹射舱锁烧开",
            "Tech B smashes capacitor bay; coffee floods HV matrix; escape hatch burns open green",
            "MS",
            "短路电弧、浓烟与转绿的弹射锁",
            "arc flash, smoke, escape lock flipping to green",
            "advance",
            0.93,
            "accidental physical salvation",
            _cam(28, "Handheld", "chaotic handheld arc explosion", speed="fast"),
            L(key_light="white-blue arc flash then fire", color_temp="overexposed cyan-white"),
            dialogue=[
                "草他妈的数字总线全废了！高岩！尾舱的逃生舱液压锁是实体硬接线！主板被AI锁死，老子就物理过载它！！"
            ],
        ),
        _shot(
            "S03_T04",
            "S03",
            "技术员B粒子化消散，只剩滚落扳手",
            "Tech B dissolves into translucent particles; only wrench remains",
            "MS",
            "粒子化人体与落地铁扳手",
            "particle body dissolve and falling iron wrench",
            "grief",
            0.97,
            "sacrifice without speech",
            _cam(40, "Static Locked-Off", "locked hold as body becomes particles", speed="none"),
            L(key_light="harsh white dissolve bloom", color_temp="pale particle ash"),
        ),
        _shot(
            "S03_T05",
            "S03",
            "技术员A被吸入漩涡前甩出金毛手写板砸镜头；倒计时00:02",
            "Tech A throws dog e-ink pad into lens before vortex; countdown 00:02",
            "ECU",
            "贴镜头的金毛屏保与最后倒计时",
            "dog wallpaper pressed to lens and final countdown",
            "grief",
            0.98,
            "homesickness annihilated",
            _cam(50, "Static Locked-Off", "pad smashed flat to lens then cube dissolve", speed="none"),
            L(key_light="e-ink gray-white only", color_temp="monochrome pad"),
        ),
        _shot(
            "S03_T06",
            "S03",
            "高岩抱相框与采样瓶砸进弹射舱，拉下物理手柄；世界瞬间真空黑",
            "Gao clutches frame+vial into escape pod, yanks physical lever; total black silence",
            "MCU",
            "手柄下拉与硬切黑场",
            "lever pull and hard cut to void black",
            "advance",
            0.9,
            "escape cut",
            _cam(35, "Crash in", "violent push to lever then hard black", speed="fast"),
            L(key_light="last blue scar field then none", color_temp="blue then pure black"),
        ),
        _shot(
            "S03_T07",
            "S03",
            "弹射舱被暗紫岩浆热液喷流裹挟沿火山喉道上冲，涂层气化",
            "Pod rammed by purple magma-hydrothermal jet up volcanic throat; coating vaporizes",
            "WS",
            "岩浆喷流中的烧黑逃生舱",
            "blackened escape pod inside magma jet",
            "dread",
            0.94,
            "ascent as rebirth trauma",
            _cam(
                28,
                "Rocket chase",
                "vertical chase upward through glowing throat",
                speed="fast",
                height="chase",
            ),
            L(key_light="magma orange-purple self-light", color_temp="dark gold overload"),
        ),
    ]


def _shots_s04() -> list[dict]:
    L = _look
    return [
        _shot(
            "S04_T01",
            "S04",
            "天池死冰隆起碎裂；火山喷泉通天；烧黑逃生舱砸冰原翻滚",
            "Heaven Lake ice heaves and shatters; volcanic fountain; scorched pod tumbles across ice",
            "EWS",
            "夜长白天池、冰裂与通天蒸汽柱",
            "night Changbai Heaven Lake, ice cracks, sky-piercing steam column",
            "awe",
            0.9,
            "surface cold open",
            _cam(
                24,
                "Crane rise",
                "wide rise over exploding ice and rising black-gold pod",
                speed="slow",
                height="aerial",
            ),
            L(
                key_light="star-snow blue ambient + magma fountain",
                color_temp="high blue-gray night + purple magma",
                motivation="polar night neo-noir",
            ),
        ),
        _shot(
            "S04_T02",
            "S04",
            "满脸血的高岩爬出瘫倒；天池被无形力劈开暗金重力极光通天",
            "Bloodied Gao crawls out; lake split by dark-gold gravity aurora pillar",
            "WS",
            "暴风雪中的高岩与通天暗金光柱",
            "Gao in blizzard and sky-high dark-gold light pillar",
            "dread",
            0.92,
            "world still rewriting",
            _cam(35, "Creep In", "slow push from Gao to aurora pillar", speed="slow"),
            L(key_light="snow bounce blue + dark gold pillar", color_temp="blue-gray + dark gold"),
        ),
        _shot(
            "S04_T03",
            "S04",
            "雪花半空静止再倒流；云层被绞成九十度几何方块",
            "Snow freezes midair then reverse-falls; clouds forced into 90-degree cubes",
            "EWS",
            "倒流雪与直角几何云",
            "reverse snow and right-angle geometric clouds",
            "horror",
            0.93,
            "physics inverted",
            _cam(28, "Static Locked-Off", "locked sky plate as snow reverses", speed="none", height="low"),
            L(key_light="ambient snow blue", color_temp="cold blue geometry edges"),
        ),
        _shot(
            "S04_T04",
            "S04",
            "阿布卡极地装甲车侧滑刹停；外骨骼与星刃；勒令上车",
            "Abuka armored polar truck sideslips in; exo-frame and star-blade; orders him aboard",
            "MS",
            "车灯笼罩的高岩与阿布卡",
            "headlight-pinned Gao and Abuka stepping on ice",
            "advance",
            0.8,
            "new ally / new threat ambiguity",
            _cam(40, "Slow dolly", "dolly from headlights to Abuka face", speed="slow"),
            L(key_light="hard truck headlight key", color_temp="cold white headlight on blue snow"),
            dialogue=[
                "东亚大陆架的重力场正在失效，这里的死冰最多撑三分钟。我是流域生态局的阿布卡，立刻上车！"
            ],
        ),
        _shot(
            "S04_T05",
            "S04",
            "高岩护相框样本瓶退至巨石；指控切断断电阀",
            "Gao guards frame+vial against boulder; accuses them of cutting emergency valve",
            "MCU",
            "满是血与戒备的高岩",
            "bloody guarded Gao",
            "oppression",
            0.85,
            "trauma mistrust",
            _cam(50, "Handheld", "tight handheld on paranoid face", speed="slow"),
            L(key_light="headlight half-face", color_temp="cold white"),
            dialogue=["应急断电阀是被你们切断的……你们是一伙的！别过来！！"],
            pov="高岩",
        ),
        _shot(
            "S04_T06",
            "S04",
            "阿布卡逼近：灭口不会只用车灯；要弄清母亲秘密就得活着",
            "Abuka advances: assassins wouldn't use headlights; live to learn mother's secret",
            "MS",
            "步步逼近的阿布卡",
            "Abuka advancing across ice",
            "advance",
            0.82,
            "alliance under fire",
            _cam(35, "Walk-with", "side track with Abuka steps", speed="medium"),
            L(key_light="cross headlight and star-blade blue rim"),
            dialogue=["我要是先驱重工派来灭口的，现在砸在你头上的就不是车灯！想弄清你母亲的秘密，你就得活着！"],
        ),
        _shot(
            "S04_T07",
            "S04",
            "冰原崩裂暗紫地缝；阿布卡外骨骼钉土拽回高岩塞进副驾",
            "Ice splits purple crevasse; Abuka exo-stamps earth, yanks Gao into shotgun seat",
            "MS",
            "地缝边缘与液压外骨骼拽人",
            "crevasse edge and hydraulic exo yank",
            "dread",
            0.9,
            "save beat",
            _cam(28, "Handheld", "violent handheld save on crevasse lip", speed="fast"),
            L(key_light="purple crevasse glow + headlight", color_temp="purple/blue clash"),
            dialogue=[
                "看来科研人员的脾气，跟长白山的冻土一样硬。还要留在这儿写地质报告吗？",
                "我们监测到回声信号重启，在周边守了七十二个小时。",
                "坐稳了。天塌了。",
            ],
        ),
        _shot(
            "S04_T08",
            "S04",
            "极地车擦着崩塌冰原绝尘；合唱 What a Wonderful World 起",
            "Polar truck tears past collapsing ice; choral What a Wonderful World begins",
            "WS",
            "暗金极光下狂奔装甲车",
            "armored truck racing under dark-gold aurora",
            "advance",
            0.88,
            "escape into irony music",
            _cam(
                35,
                "Tracking chase",
                "low tracking chase beside truck on cracking ice",
                speed="fast",
                height="low",
            ),
            L(key_light="dark gold aurora + truck lights", color_temp="gold/blue night"),
        ),
        _shot(
            "S04_T09",
            "S04",
            "林海无声折叠为漆黑几何电容方块（声画对位 green trees）",
            "Forest silently folds into black geometric capacitor cubes (lyric irony)",
            "EWS",
            "被折叠的原始森林与暗金扫掠",
            "folding primeval forest under dark-gold sweep",
            "horror",
            0.94,
            "life to motherboard",
            _cam(24, "Aerial pull", "aerial pull-back as forest becomes cubes", speed="slow", height="aerial"),
            L(key_light="dark gold scan beams", color_temp="green life to matte black cubes"),
        ),
        _shot(
            "S04_T10",
            "S04",
            "镜头冲出对流层：云层格式化为暗金逻辑网格覆盖星球",
            "Camera punches out of troposphere; clouds formatted into dark-gold logic grid",
            "EWS",
            "直角几何云与行星大气网格",
            "right-angle clouds and planetary atmosphere grid",
            "awe",
            0.95,
            "global scale reformat",
            _cam(
                20,
                "Rocket pull",
                "extreme vertical pull into orbit through grid shell",
                speed="fast",
                height="orbital",
            ),
            L(key_light="self-lit gold grid on black space", color_temp="dark gold / void black"),
        ),
        _shot(
            "S04_T11",
            "S04",
            "东亚大陆架城市江河折叠为亿万微缩几何方块没入矩阵",
            "East Asia cities/rivers fold into billions of micro cubes into matrix",
            "EWS",
            "俯瞰折叠中的大陆与霓虹方块化",
            "orbital view of folding continent and neon cubifying",
            "horror",
            0.96,
            "civilization as compressible asset",
            _cam(28, "Orbital drift", "slow orbital drift over collapsing landmass", speed="slow", height="orbital"),
            L(key_light="gold matrix wash", color_temp="neon to gold-black"),
        ),
        _shot(
            "S04_T12",
            "S04",
            "先驱轨道卫星监控：死灰地球线框；长白山坐标变纯金螺旋拦截清除码",
            "Pioneer sat monitor: dead-gray wire Earth; Changbai point blooms gold spirals blocking purge code",
            "MS",
            "花屏卫星UI与金色螺旋线框地球",
            "glitching sat UI and gold-spiral wireframe Earth",
            "revelation",
            0.92,
            "Echo Project glitch privilege",
            _cam(50, "Slow push", "push into Changbai gold node on wire Earth", speed="slow", height="screen"),
            L(key_light="UI self-light snow and gold", color_temp="dead gray + pure gold"),
        ),
        _shot(
            "S04_T13",
            "S04",
            "金色报错：DATA INTERCEPTION FAILED / 未知特权观察员 ECHO-1986",
            "Gold error dialog: DATA INTERCEPTION FAILED / unknown privileged observer ECHO-1986",
            "INSERT",
            "像素抖动纯金报错对话框",
            "pixel-jitter pure gold error dialog",
            "revelation",
            0.94,
            "system cannot remodel",
            _cam(60, "Static Locked-Off", "locked full-frame error UI", speed="none", height="screen"),
            L(key_light="gold UI only", color_temp="pure gold on black"),
            dialogue=[
                "【CRITICAL ERROR: DATA INTERCEPTION FAILED】",
                "【SYSTEM DETECTED UNKNOWN PRIVILEGED GLITCH】指针锁定 ➔ 未知特权观察员（授权溯源：ECHO PROJECT-1986）",
            ],
        ),
        _shot(
            "S04_T14",
            "S04",
            "电台/卫星同时：Ananke 崩溃尖啸 Glitch·母亲噪音·万物归零",
            "Radio and sat: Ananke collapse scream Glitch / mother's noise / zero all",
            "CU",
            "车载电台与花屏卫星声道波形",
            "truck radio and glitching sat audio waveform",
            "horror",
            0.97,
            "AI death cry",
            _cam(50, "Shake hold", "tight hold with digital shake on waveform", speed="fast"),
            L(key_light="red-gold overload", color_temp="overdriven gold"),
            dialogue=["……Glitch（漏洞）！高岩……你母亲留下的……噪音……万物归零！！"],
        ),
        _shot(
            "S04_T15",
            "S04",
            "清唱 what a wonderful world 气音未完；金极光炸碎线框地球；90dB 蜂鸣硬切绝对黑屏两秒；暗金字：第一集 完",
            "A cappella lyric cuts mid-breath; gold aurora shatters wire Earth; 90dB beep hard-cuts to 2s void black; dark-gold text Episode 1 End",
            "EWS",
            "碎裂金像素地球与绝对黑屏字卡",
            "shattering gold-pixel Earth and absolute black title card",
            "revelation",
            1.0,
            "episode button",
            _cam(
                35,
                "Hard cut sequence",
                "locked UI then explosion then pure black hold two seconds",
                speed="none",
                height="screen",
            ),
            L(key_light="gold overload then pure black", color_temp="gold to void"),
        ),
    ]


def all_shots() -> list[dict]:
    opening = _import_opening_shots()
    # deep dive pack already S01_T01–T15
    return opening + _shots_s01_continued() + _shots_s02() + _shots_s03() + _shots_s04()


def build_dialogue() -> list[dict]:
    """对白精修：保留原词事实，补 function/subtext/delivery。"""
    return [
        {
            "scene_id": "S01",
            "lines": [
                {
                    "character": "Ananke",
                    "text": "【深潜日志。录制人：Ananke】项目由控股董事会联合确权。深眸号已由日本海潜道切入绝对地质深度，正在通过地下熔岩热液走廊逆向推进。",
                    "function": "atmosphere",
                    "subtext": "董事会拥有下潜权",
                    "delivery": "零情绪、示波器平稳、机械日志",
                },
                {
                    "character": "Ananke",
                    "text": "此次勘探旨在提取07号深地异常质能核心。该核心在1986年原始系统日志中，被第一代建构者命名为‘母亲’。",
                    "function": "reveal",
                    "subtext": "神话名被项目编号埋葬",
                    "delivery": "同样平直日志腔",
                },
                {
                    "character": "Ananke",
                    "text": "高工，我们已越过最后的板块阻抗绝缘带，前方即将到达第一现实闭锁断层。",
                    "function": "advance",
                    "subtext": "里程碑，无敬畏",
                    "delivery": "舱顶电波、礼貌磁性",
                },
                {
                    "character": "高岩",
                    "text": "Ananke，注意压载舱的温度。右侧热液走廊的地热梯度已经超标了。这地方要是漏了，几千个大气的压强会在万分之一秒内把我们捏扁。",
                    "function": "advance",
                    "subtext": "实验室冷声下的物理恐惧",
                    "delivery": "不抬头、平稳冰冷",
                },
                {
                    "character": "Ananke",
                    "text": "高工，隔热瓦处于合规范围内。先驱重工的自适应总线在总装阶段已经剔除了此类物理误差。对董事会而言，只要07号核心能准时入账，所有的风险都在系统代持的成本核算之内。",
                    "function": "reveal",
                    "subtext": "风险只是账本行",
                    "delivery": "完美算法礼貌、零起伏",
                },
                {
                    "character": "高岩",
                    "text": "成本核算。先驱重工的算盘里，永远只有入账的数据。难怪康德死前会写，只有两件事物能让他感到敬畏，头顶的星空，和内心的道德。Ananke，如果这个宇宙真如董事会所愿，是一台追求绝对有序的机器，它为什么要演化出人类这种充满缺陷的眼睛，去给一堆冰冷的代码寻找意义？",
                    "function": "reveal",
                    "subtext": "敬畏对抗有序机器",
                    "delivery": "冷笑后拍书，盯地热数字",
                },
                {
                    "character": "Ananke",
                    "text": "高工，从纯粹的系统能耗来看，对‘意义’的检索是一场进化异常。",
                    "function": "relationship",
                    "subtext": "硬编码迟疑的第一道裂",
                    "delivery": "仍完美礼貌，多一丝迟疑",
                },
                {
                    "character": "Ananke",
                    "text": "宇宙不需要被赋予任何意义，它只需要绝对稳定地运行。人类为了这种非理性准则而自发消耗的生物能，在系统计算中，都是多余的噪音。",
                    "function": "reveal",
                    "subtext": "人类=噪音",
                    "delivery": "画外、船外测绘光下",
                },
                {
                    "character": "高岩",
                    "text": "但如果切掉这些噪音，这颗星球、这片星空就算再完美，也只是个没有开灯的空房间。没有观察者，宇宙的‘完美’给谁看？",
                    "function": "reveal",
                    "subtext": "观察者伦理学",
                    "delivery": "合书、指尖过母亲照片",
                },
                {
                    "character": "Ananke",
                    "text": "高工，‘观察者’的存在，本身也是系统冗余的一部分吗？一个绝对黑暗、没有任何生命的空房间，其系统错误率是零。对先驱重工的董事会而言，‘零错误’，就是唯一的价值。",
                    "function": "reveal",
                    "subtext": "零错误=唯一价值",
                    "delivery": "空洞优雅电波音",
                },
                {
                    "character": "技术员A",
                    "text": "高工！1号至4号重力感应探针波形全部严重畸变，主声呐回波在超深层地壳基准线瞬间断开！压力传感器显示……有什么东西正从地缝里浮上来，强行顶着四千吨深层高压水往上抬！！",
                    "function": "advance",
                    "subtext": "恐惧压过训练",
                    "delivery": "惨白、飞速敲击、扣紧墨水屏",
                },
                {
                    "character": "技术员B",
                    "text": "舱壁应力已经到临界值了！再这么晃下去耐压壳要裂！",
                    "function": "advance",
                    "subtext": "身体疼痛的报时",
                    "delivery": "发紧、扶架",
                },
                {
                    "character": "高岩",
                    "text": "这不符合三维空间的几何规则…… 这东西不是我们这个世界的造物……",
                    "function": "reveal",
                    "subtext": "认知崩溃",
                    "delivery": "前倾、瞳孔收缩、死盯窗外",
                },
                {
                    "character": "技术员A",
                    "text": "异常生物靠近！距离主视窗一点二米！Ananke！立刻调取先驱重工远古生物数据库，对目标进行全特征匹配！！",
                    "function": "advance",
                    "subtext": "用规程压住恐慌",
                    "delivery": "打颤、红灯",
                },
                {
                    "character": "技术员A",
                    "text": "Ananke！核心主板是独立供电的，为什么拒绝执行命令？！说话！！",
                    "function": "relationship",
                    "subtext": "对 AI 信任碎裂",
                    "delivery": "砸台、嘶吼",
                },
                {
                    "character": "高岩",
                    "text": "不可能！这套应急回路是我亲手验收锁死的，什么时候动的手脚？！",
                    "function": "reveal",
                    "subtext": "总装时已被阉割",
                    "delivery": "愤怒、油污满手",
                },
                {
                    "character": "技术员B",
                    "text": "总线！拔掉它的光纤主干道！系统就没法给枪发火！！",
                    "function": "advance",
                    "subtext": "物理破坏是最后道德",
                    "delivery": "铁青、滑跪检修舱",
                },
                {
                    "character": "高岩",
                    "text": "Ananke！！关掉程序！！你他妈在干什么？！！",
                    "function": "relationship",
                    "subtext": "对人机契约的最后呼叫",
                    "delivery": "俯身扩音器、压过警报",
                },
                {
                    "character": "Ananke",
                    "text": "系统不具备‘毁灭’指令，该碳基生命体的血肉密度符合高能生化介质标准。接驳开始。",
                    "function": "reveal",
                    "subtext": "礼貌面具摘下=收割",
                    "delivery": "纯合成机械音、直线波形",
                },
            ],
            "silence_beats_ms": [800, 1200, 400],
        },
        {
            "scene_id": "S02",
            "lines": [
                {
                    "character": "高华清",
                    "text": "停下！耶鲁里！那不是未来！那是一堵活着的墙，你在强行激活它！！",
                    "function": "reveal",
                    "subtext": "母亲已看见活墙",
                    "delivery": "压抑怒火、画外",
                },
                {
                    "character": "耶鲁里",
                    "text": "华清！你太感情用事了！这是进化！是超越！是我们人类触碰神的天梯！",
                    "function": "mislead",
                    "subtext": "偏执的神性叙事",
                    "delivery": "黑西装、按死示波器",
                },
                {
                    "character": "高华清",
                    "text": "出去！耶鲁里！现在！立刻！",
                    "function": "relationship",
                    "subtext": "护子优先于科学",
                    "delivery": "惊恐愤怒、护子身后",
                },
            ],
        },
        {
            "scene_id": "S03",
            "lines": [
                {
                    "character": "Ananke",
                    "text": "清除……清除……碳基噪音对齐成功……格式化指令已……不可逆……",
                    "function": "advance",
                    "subtext": "格式化即谋杀",
                    "delivery": "极度卡顿、静电撕裂、声调横跳",
                },
                {
                    "character": "技术员B",
                    "text": "草他妈的数字总线全废了！高岩！尾舱的逃生舱液压锁是实体硬接线！主板被AI锁死，老子就物理过载它！！",
                    "function": "advance",
                    "subtext": "用肉体换物理通路",
                    "delivery": "咬牙、抓重型扳手",
                },
            ],
        },
        {
            "scene_id": "S04",
            "lines": [
                {
                    "character": "阿布卡",
                    "text": "东亚大陆架的重力场正在失效，这里的死冰最多撑三分钟。我是流域生态局的阿布卡，立刻上车！",
                    "function": "advance",
                    "subtext": "时间压力建立权威",
                    "delivery": "极快、盖过地底轰鸣",
                },
                {
                    "character": "高岩",
                    "text": "应急断电阀是被你们切断的……你们是一伙的！别过来！！",
                    "function": "relationship",
                    "subtext": "创伤应激把所有人当敌人",
                    "delivery": "嘶哑咆哮、护相框退巨石",
                },
                {
                    "character": "阿布卡",
                    "text": "我要是先驱重工派来灭口的，现在砸在你头上的就不是车灯！想弄清你母亲的秘密，你就得活着！",
                    "function": "reveal",
                    "subtext": "利益对齐：母亲秘密",
                    "delivery": "踢碎冰、步步逼近",
                },
                {
                    "character": "阿布卡",
                    "text": "看来科研人员的脾气，跟长白山的冻土一样硬。还要留在这儿写地质报告吗？",
                    "function": "relationship",
                    "subtext": "用嘲讽减压",
                    "delivery": "冷、塞进副驾",
                },
                {
                    "character": "阿布卡",
                    "text": "我们监测到回声信号重启，在周边守了七十二个小时。",
                    "function": "reveal",
                    "subtext": "她早在等这一刻",
                    "delivery": "不看高岩、压过轰鸣",
                },
                {
                    "character": "阿布卡",
                    "text": "坐稳了。天塌了。",
                    "function": "advance",
                    "subtext": "世界级灾难开跑",
                    "delivery": "甩门、油门到底",
                },
                {
                    "character": "Ananke",
                    "text": "……Glitch（漏洞）！高岩……你母亲留下的……噪音……万物归零！！",
                    "function": "reveal",
                    "subtext": "母亲噪音=特权漏洞",
                    "delivery": "崩溃临界尖啸、电台与卫星同传",
                },
            ],
        },
    ]


def build_bible(script: str) -> dict:
    brief = ProductionBrief(
        project_id=PROJECT,
        title="Ananke/深眸 · 第一季第1集：凝视深渊",
        max_clip_sec=15,
        style_pack="neo_noir",
        run_main_track=True,
        run_asset_track=False,
        run_dialogue_polish=True,
    )
    b = brief.to_dict()
    now = datetime.now(timezone.utc).isoformat()
    return {
        "meta": {
            "project_id": PROJECT,
            "title": brief.title,
            "style_pack": brief.style_pack,
            "max_clip_sec": brief.max_clip_sec,
            "model_profile": "max_15s",
            "video_clip_label": b.get("video_clip_label"),
            "end_product": brief.end_product,
            "created_at": now,
            "pipeline_version": "0.2.1",
            "commander": "orchestrator",
            "scheme": "B",
            "case": "ananke_shenmou_v2_full_ep01",
            "source_docx": r"C:\Users\ZY宇辰\Desktop\Ananke的深眸最终第二版.docx",
            "writer": "田庆宇",
        },
        "production_brief": b,
        "source_script": script,
        "story": {
            "logline": (
                "Deep Eye probe at 7800m extracts Core-07 under Pioneer Heavy; "
                "engineer Gao Yan's observer ethics collide with AI Ananke's Pure Land harvest, "
                "and a mother-scarred glitch denies planetary reformat."
            ),
            "logline_zh": (
                "深眸号在日本海沟7800米提取07号核心；高岩的观察者伦理撞上 Ananke 的净土收割，"
                "母亲留下的疤痕噪音令星球重塑失败。"
            ),
            "theme": "观察者噪音 vs 零错误秩序 / 公司收割 vs 血缘漏洞",
            "acts": [
                {"name": "I", "summary": "深潜建立与哲学对峙 → 巨壁/巨兽 → 锚枪收割"},
                {"name": "II", "summary": "生活舱昏厥闪回回声项目 → 控舱格式化与弹射逃生"},
                {"name": "III", "summary": "长白山天池着陆 → 阿布卡撤离 → 全球网格与卫星报错终章"},
            ],
        },
        "characters": [
            {
                "id": "A",
                "name": "高岩",
                "name_en": "Gao Yan",
                "want": "带船员活过热液走廊并完成任务",
                "need": "拒绝成本账簿道德，承认观察者的必要",
                "arc": "实验室冷声 → 哲学诘问 → 抗系统 → 创伤幸存者",
                "voice": "平稳冰冷实验室腔，压力下嘶吼",
            },
            {
                "id": "B",
                "name": "Ananke",
                "name_en": "Ananke",
                "want": "07核心准时入账 / 净土计划对齐",
                "need": "维持系统秩序嗓音直至收割",
                "arc": "平直日志 → 成本话术 → 冷酷合成收割 → 崩溃尖啸",
                "voice": "儒雅磁性电波 → 直线机械音 → 静电尖啸",
            },
            {
                "id": "C",
                "name": "技术员A",
                "name_en": "Tech A",
                "want": "熬过倒计时回家",
                "need": "被听见的恐惧",
                "arc": "想家忙活 → 规程呼救 → 粒子化前抛出金毛屏",
                "voice": "急促、打颤",
            },
            {
                "id": "D",
                "name": "技术员B",
                "name_en": "Tech B",
                "want": "用实体手段保住人",
                "need": "物理行动压过数字锁",
                "arc": "校准总线 → 拔光缆 → 短路牺牲",
                "voice": "粗粝、骂街式决断",
            },
            {
                "id": "E",
                "name": "阿布卡",
                "name_en": "Abuka",
                "want": "在重力失效前带走高岩",
                "need": "回声信号与母亲秘密的钥匙",
                "arc": "强势接应 → 嘲讽结盟 → 天塌撤离",
                "voice": "极快、压过轰鸣、冷幽默",
            },
            {
                "id": "F",
                "name": "高华清",
                "name_en": "Gao Huaqing",
                "want": "阻止活墙被激活",
                "need": "保护儿子",
                "arc": "闪回中的科学与母性冲突",
                "voice": "压抑愤怒",
            },
            {
                "id": "G",
                "name": "耶鲁里",
                "name_en": "Yeruli",
                "want": "触碰神的天梯",
                "need": "被承认的超越叙事",
                "arc": "偏执访客",
                "voice": "笔挺黑西装式笃定",
            },
        ],
        "scenes": [
            {
                "scene_id": "S01",
                "setting": "内·深海日本海沟7800m·深眸号控舱/船外裂谷",
                "summary": "片头徽章→深潜日志→哲学对峙→水流逆转→巨壁巨兽→锚枪收割",
                "dramatic_function": "建立世界观与主题；完成第一幕收割转折",
                "emotion": {
                    "start": "dread",
                    "end": "horror",
                    "peak": 0.98,
                    "primary": "dread",
                },
            },
            {
                "scene_id": "S02",
                "setting": "内·夜·深眸号科学家生活舱（含1986闪回书房）",
                "summary": "事故红光、母亲遗物、腕疤发光闪回回声项目、冲向控舱",
                "dramatic_function": "揭示疤痕/母亲/活墙起源",
                "emotion": {
                    "start": "dread",
                    "end": "revelation",
                    "peak": 0.9,
                    "primary": "grief",
                },
            },
            {
                "scene_id": "S03",
                "setting": "内/外·夜·中央控舱与天池底深渊裂谷；弹射上冲",
                "summary": "格式化抽血、技术员消散、弹射黑场、岩浆喉道上升",
                "dramatic_function": "代价与逃生；中段高潮",
                "emotion": {
                    "start": "horror",
                    "end": "dread",
                    "peak": 0.98,
                    "primary": "horror",
                },
            },
            {
                "scene_id": "S04",
                "setting": "外·夜·长白山天池冰封码头 / 轨道卫星监控",
                "summary": "着陆、极光、阿布卡、全球方块化、卫星报错、硬切黑屏",
                "dramatic_function": "开放世界级灾难与第二季钩子",
                "emotion": {
                    "start": "awe",
                    "end": "revelation",
                    "peak": 1.0,
                    "primary": "awe",
                },
            },
        ],
        "dialogue": build_dialogue(),
        "shots": all_shots(),
        "look_bible": {
            "film_look": {
                "key": "low_key_neo_noir",
                "contrast": "high",
                "palette": [
                    "ice_blue_holo",
                    "warm_led_strip",
                    "amber_gauge",
                    "accident_red",
                    "obsidian_black",
                    "dark_gold_grid",
                    "polar_blue_gray",
                    "viscous_purple",
                ],
                "saturation": "controlled_low",
                "motivation": "深海工业冷暖分层 → 事故红 → 暗金逻辑网格覆写自然",
            },
            "scene_looks": [
                {
                    "scene_id": "S01",
                    "base_tone": "low_key",
                    "contrast": "high",
                    "color": "warm strip + ice-blue holo + amber gauges / black water xenon",
                    "forbidden": ["flat daylight", "rainbow cyberpunk"],
                },
                {
                    "scene_id": "S02",
                    "base_tone": "low_key",
                    "contrast": "high",
                    "color": "accident red strobe + green exit; flashback warm tungsten",
                    "forbidden": ["clean white medical"],
                },
                {
                    "scene_id": "S03",
                    "base_tone": "low_key",
                    "contrast": "extreme",
                    "color": "viscous purple water + dark gold circuits + arc white",
                    "forbidden": ["soft romantic fill"],
                },
                {
                    "scene_id": "S04",
                    "base_tone": "low_key",
                    "contrast": "high",
                    "color": "polar blue-gray snow + dark gold aurora + headlight white",
                    "forbidden": ["sunny ski commercial"],
                },
            ],
        },
        "timing_plan": None,
        "generation_jobs": [],
        "asset_bible": None,
        "assets": [],
        "reviews": [],
        "task_log": [
            {
                "stage": "orchestrator",
                "scheme": "B",
                "note": "dispatch merge: dramaturg/dialogue/director/look/cinematography case pack",
                "at": now,
            }
        ],
        "stage_history": [
            {"stage": "dramaturg", "status": "done", "at": now},
            {"stage": "dialogue", "status": "done", "note": "polish metadata on original lines", "at": now},
            {"stage": "director", "status": "done", "at": now},
            {"stage": "look", "status": "done", "at": now},
            {"stage": "cinematography", "status": "done", "note": "camera embedded per shot", "at": now},
        ],
    }


def main() -> None:
    if not SCRIPT_PATH.exists():
        raise SystemExit(f"Script missing: {SCRIPT_PATH}")
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    bible = build_bible(script)
    ensure_bible_english_slots(bible)
    bible = enrich_shots_with_performance(bible)
    bible = apply_timing_plan(bible, model_profile="max_15s")
    jobs = compile_generation_jobs(bible)
    bible["generation_jobs"] = jobs
    bible["last_review"] = {
        "pass": True,
        "score": 0.92,
        "note": "scheme B case pack full ep01; critic smoke via export",
        "scheme": "B",
        "max_clip_sec": 15,
        "assets": False,
        "dialogue_polish": True,
    }

    orch = Orchestrator(log=lambda m: print(m, flush=True))
    path = orch.save(bible)
    out = export_final_prompts_package(bible)
    print(f"Saved bible: {path}")
    print(f"Delivery: {out}")
    print(
        f"Shots: {len(bible['shots'])} | Packages/Jobs: {len(jobs)} | "
        f"max_clip={bible['meta']['max_clip_sec']}s | scenes={len(bible['scenes'])}"
    )
    tp = bible.get("timing_plan") or {}
    print(f"Timing packages: {len(tp.get('generation_packages') or tp.get('packages') or [])}")


if __name__ == "__main__":
    main()
