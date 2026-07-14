from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from film_pipeline.orchestrator import (
    ALL_STAGES,
    MAIN_STAGES,
    Orchestrator,
    ProductionBrief,
    describe_org_chart,
)
from film_pipeline.orchestrator.brief import STYLE_PACK_CHOICES
from film_pipeline.runtime.clip_profile import CLIP_MAX_CHOICES, normalize_max_clip

console = Console()


def _ask(prompt: str) -> str:
    try:
        return console.input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[red]已取消。[/red]")
        raise SystemExit(1)


def collect_production_brief_interactive(
    project_id: str,
    title: str | None,
    style_default: str | None,
    max_clip_flag: int | None,
    assets_flag: bool | None,
    dialogue_flag: bool | None = None,
) -> ProductionBrief:
    """
    Producer intake — must finish before Orchestrator assigns any expert work.
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold]Production Brief · 创作意图（总指挥开工单）[/bold]\n\n"
            "调度总指挥 Orchestrator 将按此单派工。\n"
            "终点是 [cyan]最终提示词[/cyan]，不调用视频 API。\n"
            "资产轨（三视图）与主链解耦，可换图。",
            border_style="cyan",
            title="开机",
        )
    )

    # 1) max clip
    if max_clip_flag is not None:
        max_clip = normalize_max_clip(max_clip_flag)
        console.print(f"[green]视频单段上限：{max_clip}s[/green]（来自 --max-clip）")
    else:
        console.print(
            "\n[bold]① 视频模型单段最长[/bold]\n"
            "  [cyan]1[/cyan] — 15 秒\n"
            "  [cyan]2[/cyan] — 30 秒"
        )
        while True:
            raw = _ask("请选择 1/2 或 15/30: ")
            if raw in {"1", "15", "15s"}:
                max_clip = 15
                break
            if raw in {"2", "30", "30s"}:
                max_clip = 30
                break
            console.print("[yellow]请输入 1、2、15 或 30[/yellow]")
        console.print(f"[green]已选：{max_clip}s[/green]")

    # 2) style
    if style_default and style_default in STYLE_PACK_CHOICES:
        style = style_default
        console.print(f"[green]风格包：{style}[/green]（来自 --style）")
    else:
        console.print("\n[bold]② 风格包 style_pack[/bold]")
        for i, s in enumerate(STYLE_PACK_CHOICES, 1):
            console.print(f"  [cyan]{i}[/cyan] — {s}")
        while True:
            raw = _ask("请选择编号或名称: ")
            if raw.isdigit() and 1 <= int(raw) <= len(STYLE_PACK_CHOICES):
                style = STYLE_PACK_CHOICES[int(raw) - 1]
                break
            if raw in STYLE_PACK_CHOICES:
                style = raw
                break
            console.print(f"[yellow]可选：{', '.join(STYLE_PACK_CHOICES)}[/yellow]")
        console.print(f"[green]已选：{style}[/green]")

    # 3) asset track
    if assets_flag is not None:
        run_assets = assets_flag
        console.print(
            f"[green]资产轨：{'开' if run_assets else '关'}[/green]（来自 CLI）"
        )
    else:
        console.print(
            "\n[bold]③ 是否开启资产旁路（人物/道具/场景三视图提示词）[/bold]\n"
            "  与主链独立，不阻塞分镜；图可随时换\n"
            "  [cyan]Y[/cyan] 开启（推荐）  [cyan]N[/cyan] 仅主链"
        )
        while True:
            raw = _ask("Y/N: ").lower()
            if raw in {"y", "yes", "是", "1"}:
                run_assets = True
                break
            if raw in {"n", "no", "否", "0"}:
                run_assets = False
                break
            console.print("[yellow]请输入 Y 或 N[/yellow]")
        console.print(f"[green]资产轨：{'开' if run_assets else '关'}[/green]")

    # 4) dialogue polish
    if dialogue_flag is not None:
        run_dialogue = dialogue_flag
        console.print(
            f"[green]对白精修：{'开' if run_dialogue else '关（保留原台词）'}[/green]（来自 CLI）"
        )
    else:
        console.print(
            "\n[bold]④ 是否对白精修[/bold]\n"
            "  有的剧本台词已定稿，不需要改\n"
            "  [cyan]Y[/cyan] 开启精修（改潜台词/节奏）\n"
            "  [cyan]N[/cyan] 跳过，保留原剧本措辞"
        )
        while True:
            raw = _ask("Y/N: ").lower()
            if raw in {"y", "yes", "是", "1"}:
                run_dialogue = True
                break
            if raw in {"n", "no", "否", "0"}:
                run_dialogue = False
                break
            console.print("[yellow]请输入 Y 或 N[/yellow]")
        console.print(
            f"[green]对白精修：{'开' if run_dialogue else '关（保留原台词）'}[/green]"
        )

    t = title or project_id
    brief = ProductionBrief(
        project_id=project_id,
        title=t,
        max_clip_sec=max_clip,
        style_pack=style,
        run_main_track=True,
        run_asset_track=run_assets,
        run_dialogue_polish=run_dialogue,
        end_product="prompts_only",
    )
    console.print()
    console.print(
        Panel.fit(
            f"project: [bold]{brief.project_id}[/bold]\n"
            f"max_clip: [cyan]{brief.max_clip_sec}s[/cyan]\n"
            f"style: {brief.style_pack}\n"
            f"tracks: main=ON assets={'ON' if brief.run_asset_track else 'OFF'} "
            f"dialogue_polish={'ON' if brief.run_dialogue_polish else 'OFF'}\n"
            f"end: 最终提示词（无 API）",
            title="Brief 确认",
            border_style="green",
        )
    )
    return brief


def resolve_brief_from_args(args: argparse.Namespace) -> ProductionBrief:
    """Non-interactive: all critical fields via flags."""
    if args.max_clip is None:
        if not sys.stdin.isatty():
            console.print("[red]非交互环境必须 --max-clip 15|30[/red]")
            raise SystemExit(2)
        # interactive path handled by caller
        raise RuntimeError("use collect_production_brief_interactive")

    run_assets = True if args.assets is None else args.assets
    run_dialogue = True if getattr(args, "dialogue", None) is None else args.dialogue
    return ProductionBrief(
        project_id=args.project,
        title=args.title or args.project,
        max_clip_sec=args.max_clip,
        style_pack=args.style or "neo_noir",
        run_main_track=True,
        run_asset_track=run_assets,
        run_dialogue_polish=run_dialogue,
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="film-pipeline",
        description=(
            "AI Film Pipeline — Orchestrator assigns TaskTickets. "
            "ProductionBrief first (15|30, style, assets). End product: prompts only."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Brief → Orchestrator 派工全流程")
    run_p.add_argument("--script", required=True)
    run_p.add_argument("--project", required=True)
    run_p.add_argument("--style", default=None, help="neo_noir | warm_realism")
    run_p.add_argument("--max-clip", type=int, choices=list(CLIP_MAX_CHOICES), default=None)
    run_p.add_argument("--title", default=None)
    run_p.add_argument("--until", default=None, choices=list(MAIN_STAGES))
    run_p.add_argument(
        "--assets",
        dest="assets",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="--assets / --no-assets（默认交互询问）",
    )
    run_p.add_argument(
        "--dialogue",
        dest="dialogue",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="--dialogue 对白精修 / --no-dialogue 跳过精修保留原台词",
    )

    step_p = sub.add_parser("step", help="Orchestrator 精确派一岗")
    step_p.add_argument("--project", required=True)
    step_p.add_argument("--stage", required=True, choices=list(ALL_STAGES))

    assets_p = sub.add_parser("assets", help="只跑资产旁路（三视图提示词）")
    assets_p.add_argument("--project", required=True)

    show_p = sub.add_parser("show", help="项目总览")
    show_p.add_argument("--project", required=True)

    brief_p = sub.add_parser("brief", help="查看 ProductionBrief")
    brief_p.add_argument("--project", required=True)

    tasks_p = sub.add_parser("tasks", help="查看 Orchestrator 派工日志")
    tasks_p.add_argument("--project", required=True)

    prompts_p = sub.add_parser("prompts", help="最终镜头提示词（主链终点）")
    prompts_p.add_argument("--project", required=True)
    prompts_p.add_argument("--shot", default=None)
    prompts_p.add_argument("--out", default=None)

    timing_p = sub.add_parser("timing", help="时长账本")
    timing_p.add_argument("--project", required=True)
    timing_p.add_argument("--max-clip", type=int, choices=list(CLIP_MAX_CHOICES), default=None)

    org_p = sub.add_parser("org", help="组织架构 / 谁指挥谁")

    list_p = sub.add_parser("stages", help="主链与资产岗列表")

    args = parser.parse_args(argv)
    orch = Orchestrator(log=lambda m: console.print(f"[dim]{m}[/dim]"))

    if args.command == "org":
        console.print(describe_org_chart())
        return 0

    if args.command == "stages":
        console.print("[bold]主链 main[/bold]")
        for i, s in enumerate(MAIN_STAGES, 1):
            console.print(f"  {i}. {s}")
        console.print("\n[bold]资产旁路 assets[/bold]")
        console.print("  · asset  （三视图提示词，可独立）")
        console.print(
            "\n[dim]指挥：Orchestrator 派 TaskTicket；意图：ProductionBrief[/dim]"
        )
        return 0

    if args.command == "run":
        script_path = Path(args.script)
        if not script_path.exists():
            console.print(f"[red]Script not found:[/red] {script_path}")
            return 1
        script = script_path.read_text(encoding="utf-8")

        fully_flagged = (
            args.max_clip is not None
            and args.style is not None
            and args.assets is not None
            and args.dialogue is not None
        )
        if fully_flagged:
            brief = resolve_brief_from_args(args)
        elif not sys.stdin.isatty() and args.max_clip is None:
            console.print("[red]非交互环境必须 --max-clip 15|30[/red]")
            return 2
        elif args.max_clip is not None and (
            args.style is not None or args.assets is not None or args.dialogue is not None
        ):
            if sys.stdin.isatty() and (
                args.style is None or args.assets is None or args.dialogue is None
            ):
                brief = collect_production_brief_interactive(
                    args.project,
                    args.title,
                    args.style,
                    args.max_clip,
                    args.assets,
                    args.dialogue,
                )
            else:
                brief = ProductionBrief(
                    project_id=args.project,
                    title=args.title or args.project,
                    max_clip_sec=args.max_clip,
                    style_pack=args.style or "neo_noir",
                    run_asset_track=True if args.assets is None else args.assets,
                    run_dialogue_polish=True if args.dialogue is None else args.dialogue,
                )
        elif sys.stdin.isatty():
            brief = collect_production_brief_interactive(
                args.project,
                args.title,
                args.style,
                args.max_clip,
                args.assets,
                args.dialogue,
            )
        else:
            console.print(
                "[red]非交互环境需要 --max-clip；建议同时 "
                "--style --assets/--no-assets --dialogue/--no-dialogue[/red]"
            )
            return 2

        console.print(
            f"[bold]Orchestrator 开机[/bold] project={brief.project_id} "
            f"max_clip={brief.max_clip_sec}s"
        )
        bible = orch.run_production(brief, script, until=args.until)
        console.print(f"[green]Saved[/green] {orch.project_path(brief.project_id)}")
        _print_summary(bible)
        return 0

    if args.command == "step":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        bible = orch.assign_and_run(bible, args.stage)
        console.print(f"[green]OK[/green] ticket logged → {args.stage}")
        return 0

    if args.command == "assets":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        if not bible.get("characters"):
            console.print("[yellow]尚无人物表，先派 dramaturg…[/yellow]")
            bible = orch.assign_and_run(bible, "dramaturg")
        bible = orch.run_asset_track(bible)
        console.print(f"[green]asset_bible 已更新[/green]")
        ab = bible.get("asset_bible") or {}
        console.print(
            f"  characters={len(ab.get('characters') or [])} "
            f"props={len(ab.get('props') or [])} "
            f"sets={len(ab.get('sets') or [])}"
        )
        board = orch.project_path(args.project).parent / "asset_board.md"
        if board.exists():
            console.print(f"  board: {board}")
        return 0

    if args.command == "show":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        _print_summary(bible)
        return 0

    if args.command == "brief":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        console.print_json(json.dumps(bible.get("production_brief") or {}, ensure_ascii=False))
        return 0

    if args.command == "tasks":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        table = Table(title="Task log (Orchestrator)")
        table.add_column("ticket_id")
        table.add_column("stage")
        table.add_column("track")
        table.add_column("status")
        for t in bible.get("task_log") or []:
            table.add_row(
                str(t.get("ticket_id")),
                str(t.get("stage")),
                str(t.get("track")),
                str(t.get("status")),
            )
        console.print(table)
        return 0

    if args.command == "timing":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        from film_pipeline.runtime.clip_profile import profile_for_max_clip
        from film_pipeline.runtime.timing import apply_timing_plan, format_timing_report

        if args.max_clip is not None:
            m = normalize_max_clip(args.max_clip)
            bible.setdefault("meta", {})["max_clip_sec"] = m
            bible["meta"]["model_profile"] = profile_for_max_clip(m)
            if bible.get("production_brief"):
                bible["production_brief"]["max_clip_sec"] = m
            apply_timing_plan(bible)
            orch.save(bible)
        if not bible.get("timing_plan"):
            apply_timing_plan(bible)
            orch.save(bible)
        console.print(format_timing_report(bible))
        return 0

    if args.command == "prompts":
        try:
            bible = orch.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        from film_pipeline.runtime.prompt_compiler import (
            compile_generation_jobs,
            export_prompts_markdown,
        )

        jobs = bible.get("generation_jobs") or compile_generation_jobs(bible)
        if args.shot:
            jobs = [
                j
                for j in jobs
                if j.get("shot_id") == args.shot or j.get("clip_id") == args.shot
            ]
            if not jobs:
                console.print(f"[red]Shot not found:[/red] {args.shot}")
                return 1
        if args.out:
            tmp = dict(bible)
            tmp["generation_jobs"] = jobs
            Path(args.out).write_text(export_prompts_markdown(tmp), encoding="utf-8")
            console.print(f"[green]Wrote[/green] {args.out}")
        for job in jobs:
            title = job.get("clip_id") or job.get("shot_id")
            console.rule(str(title))
            console.print(job.get("zh_director_summary") or "")
            console.print(f"[dim]时长={job.get('duration_sec')}s[/dim]")
            console.print("\n[bold]① 演员自由发挥 · 英文主稿[/bold]\n")
            console.print(job.get("actor_free_prompt") or "")
            console.print("\n[dim]中文对照：[/dim]")
            console.print(job.get("actor_free_prompt_zh") or "")
            console.print("\n[bold]② 导演指导 · 英文主稿[/bold]\n")
            console.print(job.get("director_guided_prompt") or "")
            console.print("\n[dim]中文对照：[/dim]")
            console.print(job.get("director_guided_prompt_zh") or "")
            console.print()
        return 0

    return 1


def _print_summary(bible: dict) -> None:
    meta = bible.get("meta") or {}
    brief = bible.get("production_brief") or {}
    console.print(f"\n[bold]{meta.get('title')}[/bold]")
    tracks = brief.get("tracks") or {}
    polish = tracks.get(
        "dialogue_polish",
        brief.get("run_dialogue_polish", True),
    )
    console.print(
        f"Brief: max_clip=[cyan]{meta.get('max_clip_sec')}s[/cyan] "
        f"style={meta.get('style_pack')} "
        f"assets={'ON' if tracks.get('assets', brief.get('run_asset_track')) else 'OFF'} "
        f"dialogue_polish={'ON' if polish else 'OFF'} "
        f"commander={meta.get('commander', 'orchestrator')}"
    )
    story = bible.get("story") or {}
    if story:
        console.print(f"Logline: {story.get('logline')}")

    table = Table(title="Shots")
    table.add_column("shot_id")
    table.add_column("size")
    table.add_column("sec")
    table.add_column("clips")
    table.add_column("move")
    for shot in bible.get("shots") or []:
        cam = shot.get("camera") or {}
        mov = (cam.get("movement") or {}).get("type", "-")
        table.add_row(
            str(shot.get("shot_id")),
            str(shot.get("shot_size")),
            str(shot.get("duration_sec", "-")),
            str(len(shot.get("generation_clips") or []) or 1),
            str(mov),
        )
    if bible.get("shots"):
        console.print(table)

    ab = bible.get("asset_bible") or {}
    if ab:
        console.print(
            f"\n[bold]Assets[/bold]: "
            f"chars={len(ab.get('characters') or [])} "
            f"props={len(ab.get('props') or [])} "
            f"sets={len(ab.get('sets') or [])} "
            f"[dim](image_refs 可空可换)[/dim]"
        )

    jobs = bible.get("generation_jobs") or []
    if jobs:
        console.print(f"\n[bold]Final prompts[/bold]: {len(jobs)} jobs（终点，无 API）")

    log = bible.get("task_log") or []
    if log:
        console.print(f"Task tickets: {len(log)} 条  → film-pipeline tasks --project {meta.get('project_id')}")

    review = bible.get("last_review")
    if review:
        st = "PASS" if review.get("pass") else "FAIL"
        console.print(f"Critic: {st} score={review.get('score')}")


if __name__ == "__main__":
    sys.exit(main())
