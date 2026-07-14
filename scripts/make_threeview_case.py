"""Generate a readable three-view case from sample script."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("FILM_PIPELINE_DRY_RUN", "1")

from film_pipeline.orchestrator import Orchestrator, ProductionBrief
from film_pipeline.paths import EXAMPLES_DIR, PROJECTS_DIR


def main() -> None:
    script = (EXAMPLES_DIR / "sample_script.txt").read_text(encoding="utf-8")
    brief = ProductionBrief(
        project_id="case_threeview",
        title="信封",
        max_clip_sec=30,
        style_pack="neo_noir",
        run_asset_track=True,
        run_dialogue_polish=False,
    )
    bible = Orchestrator(log=lambda m: None).run_production(brief, script)
    ab = bible.get("asset_bible") or {}

    lines: list[str] = [
        "# 案例：剧本《信封》— 三视图提示词",
        "",
        "来源剧本：`film_pipeline/bible/examples/sample_script.txt`",
        "规范：`E:/AI/skill/三视图.skill` → `knowledge/ai/asset/three_view_template.json`",
        "",
        "约定：**英文 sheet_prompt = 生图主稿**；**中文 summary = 只帮你看懂**。",
        "",
    ]

    for c in ab.get("characters") or []:
        lines += [
            f"## 人物：{c.get('name')}（`{c.get('asset_id')}`）",
            "",
            "### 中文说明（辅助）",
            "",
            c.get("sheet_prompt_zh_summary") or "（无）",
            "",
            "### 英文主稿 sheet_prompt（复制去生图）",
            "",
            "```",
            c.get("sheet_prompt") or "",
            "```",
            "",
            f"建议尺寸：`{c.get('image_size_hint') or '1792x1024'}`",
            "",
            "一致性锚点：",
            "",
        ]
        for a in c.get("consistency_anchors") or []:
            lines.append(f"- {a}")
        lines.append("")

    for p in (ab.get("props") or [])[:1]:
        lines += [
            f"## 道具：{p.get('name')}（`{p.get('asset_id')}`）",
            "",
            p.get("sheet_prompt_zh_summary") or "",
            "",
            "```",
            p.get("sheet_prompt") or "",
            "```",
            "",
        ]

    for s in (ab.get("sets") or [])[:1]:
        lines += [
            f"## 场景：{s.get('name')}（`{s.get('asset_id')}`）",
            "",
            s.get("sheet_prompt_zh_summary") or "",
            "",
            "```",
            s.get("sheet_prompt") or "",
            "```",
            "",
        ]

    out = PROJECTS_DIR / "case_threeview" / "CASE_三视图示例.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)

    # also print first character for terminal
    if ab.get("characters"):
        c0 = ab["characters"][0]
        print("\n==== 人物案例预览 ====\n")
        print(c0.get("sheet_prompt_zh_summary"))
        print("\n---- EN ----\n")
        print(c0.get("sheet_prompt"))


if __name__ == "__main__":
    main()
