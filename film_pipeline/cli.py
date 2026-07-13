from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from film_pipeline.orchestrator.pipeline import STAGES, Pipeline

console = Console()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="film-pipeline",
        description="AI Film Pipeline — script to shot contracts (skills + knowledge)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run full pipeline on a script")
    run_p.add_argument("--script", required=True, help="Path to screenplay text")
    run_p.add_argument("--project", required=True, help="Project id")
    run_p.add_argument("--style", default="neo_noir", help="style pack id")
    run_p.add_argument("--title", default=None)
    run_p.add_argument("--until", default=None, choices=STAGES, help="Stop after stage")

    step_p = sub.add_parser("step", help="Run one stage on existing project")
    step_p.add_argument("--project", required=True)
    step_p.add_argument("--stage", required=True, choices=STAGES)

    show_p = sub.add_parser("show", help="Print summary of a project bible")
    show_p.add_argument("--project", required=True)

    prompts_p = sub.add_parser(
        "prompts",
        help="Export / print final compiled prompts (all stages merged)",
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

    list_p = sub.add_parser("stages", help="List pipeline stages")

    args = parser.parse_args(argv)
    pipe = Pipeline()

    if args.command == "stages":
        for i, s in enumerate(STAGES, 1):
            console.print(f"{i}. {s}")
        console.print(
            "\n[dim]Final merge stage: generator (Prompt Compiler) "
            "→ generation_jobs + prompt_board.md[/dim]"
        )
        return 0

    if args.command == "run":
        script_path = Path(args.script)
        if not script_path.exists():
            console.print(f"[red]Script not found:[/red] {script_path}")
            return 1
        script = script_path.read_text(encoding="utf-8")
        console.print(f"[bold]Running pipeline[/bold] project={args.project} style={args.style}")
        bible = pipe.run_all(
            project_id=args.project,
            script=script,
            style_pack=args.style,
            title=args.title,
            until=args.until,
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
            jobs = [j for j in jobs if j.get("shot_id") == args.shot]
            if not jobs:
                console.print(f"[red]Shot not found:[/red] {args.shot}")
                return 1
        if args.out:
            out_path = Path(args.out)
            # if filtering one shot, still export that subset as md
            tmp = dict(bible)
            tmp["generation_jobs"] = jobs
            out_path.write_text(export_prompts_markdown(tmp), encoding="utf-8")
            console.print(f"[green]Wrote[/green] {out_path}")
        for job in jobs:
            console.rule(str(job.get("shot_id")))
            console.print(f"[cyan]中文摘要[/cyan] {job.get('zh_director_summary', '')}")
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
    for shot in bible.get("shots") or []:
        cam = shot.get("camera") or {}
        look = shot.get("look") or {}
        mov = (cam.get("movement") or {}).get("type", "-")
        table.add_row(
            str(shot.get("shot_id")),
            str(shot.get("shot_size")),
            str((shot.get("emotion") or {}).get("primary", "-")),
            str(cam.get("lens_mm", "-")),
            str(mov),
            str(look.get("tone", "-")),
        )
    if bible.get("shots"):
        console.print(table)

    jobs = bible.get("generation_jobs") or []
    if jobs:
        console.print(f"\n[bold]Compiled prompts:[/bold] {len(jobs)} jobs")
        sample = jobs[0]
        preview = (sample.get("visual_prompt") or "")[:180]
        console.print(f"  example {sample.get('shot_id')}: {preview}...")
        board = Path(__file__).resolve().parent / "bible" / "projects" / meta.get(
            "project_id", ""
        ) / "prompt_board.md"
        # show relative hint
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
