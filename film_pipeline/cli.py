from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from film_pipeline.orchestrator.pipeline import STAGES, Pipeline
from film_pipeline.runtime.clip_profile import CLIP_MAX_CHOICES, normalize_max_clip

console = Console()


def ask_max_clip_interactive() -> int:
    """
    Before any pipeline work: user must choose video model max length.
    Only two options: 15s or 30s.
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold]开始前请选择视频模型单段最长时长[/bold]\n\n"
            "提示词是本流水线的最后一步（不调用生成 API）。\n"
            "时长规划与拆镜将严格按你选的上限计算。\n\n"
            "  [cyan]1[/cyan]  —  最长 [bold]15[/bold] 秒\n"
            "  [cyan]2[/cyan]  —  最长 [bold]30[/bold] 秒\n",
            title="视频模型时长",
            border_style="cyan",
        )
    )
    while True:
        try:
            raw = console.input("[bold]请选择 1 或 2（也可直接输入 15 / 30）: [/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[red]已取消。必须先选择 15 或 30 秒才能开始。[/red]")
            raise SystemExit(1)

        if raw in {"1", "15", "15s", "15S"}:
            console.print("[green]已选择：最长 15 秒[/green]\n")
            return 15
        if raw in {"2", "30", "30s", "30S"}:
            console.print("[green]已选择：最长 30 秒[/green]\n")
            return 30
        console.print("[yellow]无效输入。请输入 1 / 2，或 15 / 30。[/yellow]")


def resolve_max_clip_for_run(args: argparse.Namespace) -> int:
    """CLI flag wins; otherwise interactive ask. Never silent default on run."""
    if getattr(args, "max_clip", None) is not None:
        return normalize_max_clip(args.max_clip)
    # Non-interactive environments: require explicit flag
    if not sys.stdin.isatty():
        console.print(
            "[red]非交互环境必须指定 --max-clip 15 或 --max-clip 30[/red]"
        )
        raise SystemExit(2)
    return ask_max_clip_interactive()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="film-pipeline",
        description=(
            "AI Film Pipeline — script → shot contracts → final prompts. "
            "Before run: choose video max clip 15s or 30s."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run full pipeline on a script (asks 15s/30s first)")
    run_p.add_argument("--script", required=True, help="Path to screenplay text")
    run_p.add_argument("--project", required=True, help="Project id")
    run_p.add_argument("--style", default="neo_noir", help="style pack id")
    run_p.add_argument(
        "--max-clip",
        type=int,
        choices=list(CLIP_MAX_CHOICES),
        default=None,
        help="Video model max seconds per clip: 15 or 30. If omitted, ask interactively.",
    )
    run_p.add_argument("--title", default=None)
    run_p.add_argument("--until", default=None, choices=STAGES, help="Stop after stage")

    step_p = sub.add_parser("step", help="Run one stage on existing project")
    step_p.add_argument("--project", required=True)
    step_p.add_argument("--stage", required=True, choices=STAGES)

    show_p = sub.add_parser("show", help="Print summary of a project bible")
    show_p.add_argument("--project", required=True)

    prompts_p = sub.add_parser(
        "prompts",
        help="Export / print final compiled prompts (pipeline end product)",
    )
    prompts_p.add_argument("--project", required=True)
    prompts_p.add_argument(
        "--shot",
        default=None,
        help="Only print one shot_id (e.g. S01_T05)",
    )
    prompts_p.add_argument(
        "--out",
        default=None,
        help="Optional path to write prompt_board.md",
    )

    timing_p = sub.add_parser(
        "timing",
        help="Show duration budget (dialogue / move / clip splits under max cap)",
    )
    timing_p.add_argument("--project", required=True)
    timing_p.add_argument(
        "--max-clip",
        type=int,
        choices=list(CLIP_MAX_CHOICES),
        default=None,
        help="Re-plan with 15 or 30",
    )

    list_p = sub.add_parser("stages", help="List pipeline stages")

    args = parser.parse_args(argv)
    pipe = Pipeline()

    if args.command == "stages":
        for i, s in enumerate(STAGES, 1):
            console.print(f"{i}. {s}")
        console.print(
            "\n[dim]开始前须选择视频单段上限 15s 或 30s。"
            "最后一步是 generator 编译提示词（不调用 API）。[/dim]"
        )
        return 0

    if args.command == "run":
        script_path = Path(args.script)
        if not script_path.exists():
            console.print(f"[red]Script not found:[/red] {script_path}")
            return 1

        max_clip = resolve_max_clip_for_run(args)
        script = script_path.read_text(encoding="utf-8")
        console.print(
            f"[bold]Running pipeline[/bold] project={args.project} "
            f"style={args.style} [cyan]max_clip={max_clip}s[/cyan]"
        )
        console.print("[dim]终点：最终提示词（prompt_board.md），不调用视频 API。[/dim]")
        bible = pipe.run_all(
            project_id=args.project,
            script=script,
            style_pack=args.style,
            title=args.title,
            until=args.until,
            max_clip_sec=max_clip,
        )
        path = pipe.project_path(args.project)
        console.print(f"[green]Saved[/green] {path}")
        _print_summary(bible)
        return 0

    if args.command == "step":
        try:
            bible = pipe.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        if not (bible.get("meta") or {}).get("max_clip_sec"):
            console.print(
                "[yellow]该项目未记录 max_clip_sec。请重新 run 并选择 15 或 30。[/yellow]"
            )
        console.print(f"[bold]Stage[/bold] {args.stage}")
        bible = pipe.run_stage(bible, args.stage)
        console.print(f"[green]OK[/green] → {pipe.project_path(args.project)}")
        return 0

    if args.command == "show":
        try:
            bible = pipe.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        _print_summary(bible)
        return 0

    if args.command == "timing":
        try:
            bible = pipe.load(args.project)
        except FileNotFoundError:
            console.print(f"[red]Project not found:[/red] {args.project}")
            return 1
        from film_pipeline.runtime.timing import apply_timing_plan, format_timing_report

        if args.max_clip is not None:
            m = normalize_max_clip(args.max_clip)
            bible.setdefault("meta", {})["max_clip_sec"] = m
            from film_pipeline.runtime.clip_profile import profile_for_max_clip

            bible["meta"]["model_profile"] = profile_for_max_clip(m)
            apply_timing_plan(bible, model_profile=bible["meta"]["model_profile"])
            pipe.save(bible)
        plan = bible.get("timing_plan")
        if not plan:
            if not (bible.get("meta") or {}).get("max_clip_sec"):
                console.print(
                    "[red]项目尚未选择 15/30 秒上限。请 film-pipeline run 时选择，"
                    "或 film-pipeline timing --project X --max-clip 15|30[/red]"
                )
                return 1
            apply_timing_plan(bible)
            pipe.save(bible)
            plan = bible.get("timing_plan")
        console.print(format_timing_report(bible))
        console.print(
            f"\n[dim]max_clip={plan.get('max_clip_sec')}s · "
            f"film_total={plan.get('film_total_sec')}s · "
            f"warnings={len(plan.get('warnings') or [])}[/dim]"
        )
        return 0

    if args.command == "prompts":
        try:
            bible = pipe.load(args.project)
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
            out_path = Path(args.out)
            tmp = dict(bible)
            tmp["generation_jobs"] = jobs
            out_path.write_text(export_prompts_markdown(tmp), encoding="utf-8")
            console.print(f"[green]Wrote[/green] {out_path}")
        for job in jobs:
            title = job.get("clip_id") or job.get("shot_id")
            console.rule(str(title))
            console.print(f"[cyan]中文摘要[/cyan] {job.get('zh_director_summary', '')}")
            console.print(f"[dim]duration={job.get('duration_sec')}s stitch={job.get('stitch')}[/dim]")
            console.print("\n[bold]visual_prompt[/bold]")
            console.print(job.get("visual_prompt") or "")
            console.print("\n[bold]motion_prompt[/bold]")
            console.print(job.get("motion_prompt") or "")
            console.print("\n[bold]master_prompt[/bold]")
            console.print(job.get("master_prompt") or "")
            console.print("\n[bold]negative_prompt[/bold]")
            console.print(job.get("negative_prompt") or "")
            console.print()
        board = pipe.project_path(args.project).parent / "prompt_board.md"
        if board.exists() and not args.out:
            console.print(f"[dim]Also on disk:[/dim] {board}")
        return 0

    return 1


def _print_summary(bible: dict) -> None:
    meta = bible.get("meta") or {}
    console.print(f"\n[bold]{meta.get('title')}[/bold]  style={meta.get('style_pack')}")
    if meta.get("max_clip_sec"):
        console.print(
            f"Video clip cap: [cyan]{meta.get('max_clip_sec')}s[/cyan] "
            f"({meta.get('video_clip_label') or meta.get('model_profile')})"
        )
    story = bible.get("story") or {}
    if story:
        console.print(f"Logline: {story.get('logline')}")
        console.print(f"Theme:   {story.get('theme')}")

    table = Table(title="Shots")
    table.add_column("shot_id")
    table.add_column("size")
    table.add_column("emotion")
    table.add_column("lens")
    table.add_column("move")
    table.add_column("tone")
    table.add_column("sec")
    table.add_column("clips")
    for shot in bible.get("shots") or []:
        cam = shot.get("camera") or {}
        look = shot.get("look") or {}
        mov = (cam.get("movement") or {}).get("type", "-")
        nclips = len(shot.get("generation_clips") or []) or 1
        table.add_row(
            str(shot.get("shot_id")),
            str(shot.get("shot_size")),
            str((shot.get("emotion") or {}).get("primary", "-")),
            str(cam.get("lens_mm", "-")),
            str(mov),
            str(look.get("tone", "-")),
            str(shot.get("duration_sec", "-")),
            str(nclips),
        )
    if bible.get("shots"):
        console.print(table)

    plan = bible.get("timing_plan") or {}
    if plan:
        console.print(
            f"\n[bold]Timing:[/bold] max_clip={plan.get('max_clip_sec')}s · "
            f"film_total={plan.get('film_total_sec')}s "
            f"({plan.get('film_total_min')} min) · "
            f"profile={plan.get('model_profile')}"
        )
        if plan.get("warnings"):
            console.print(
                f"[yellow]warnings:[/yellow] {len(plan['warnings'])} "
                f"(see film-pipeline timing --project {meta.get('project_id')})"
            )

    jobs = bible.get("generation_jobs") or []
    if jobs:
        console.print(f"\n[bold]Final prompts:[/bold] {len(jobs)} jobs (end product, no API)")
        sample = jobs[0]
        preview = (sample.get("visual_prompt") or "")[:180]
        console.print(f"  example {sample.get('clip_id') or sample.get('shot_id')}: {preview}...")
        console.print(
            "  export: [cyan]film-pipeline prompts --project "
            f"{meta.get('project_id')}[/cyan]"
        )

    review = bible.get("last_review")
    if review:
        status = "PASS" if review.get("pass") else "FAIL"
        color = "green" if review.get("pass") else "yellow"
        console.print(
            f"\nCritic: [{color}]{status}[/{color}] score={review.get('score')} — {review.get('summary')}"
        )
        for f in review.get("failures") or []:
            console.print(f"  - [{f.get('reroute_to')}] {f.get('type')}: {f.get('reason')}")

    nonempty = [k for k, v in bible.items() if v not in (None, [], {})]
    console.print(f"\nFull bible JSON keys: {', '.join(nonempty)}")


if __name__ == "__main__":
    sys.exit(main())
