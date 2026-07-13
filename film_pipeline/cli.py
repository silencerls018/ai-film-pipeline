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

    list_p = sub.add_parser("stages", help="List pipeline stages")

    args = parser.parse_args(argv)
    pipe = Pipeline()

    if args.command == "stages":
        for i, s in enumerate(STAGES, 1):
            console.print(f"{i}. {s}")
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

    review = bible.get("last_review")
    if review:
        status = "PASS" if review.get("pass") else "FAIL"
        color = "green" if review.get("pass") else "yellow"
        console.print(
            f"\nCritic: [{color}]{status}[/{color}] score={review.get('score')} — {review.get('summary')}"
        )
        for f in review.get("failures") or []:
            console.print(f"  - [{f.get('reroute_to')}] {f.get('type')}: {f.get('reason')}")

    # compact JSON tip
    console.print(
        f"\nFull bible JSON keys: {', '.join(k for k, v in bible.items() if v not in (None, [], {{}}))}"
    )


if __name__ == "__main__":
    sys.exit(main())
