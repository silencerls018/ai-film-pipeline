from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from film_pipeline.paths import ensure_project_dir
from film_pipeline.runtime.agent_runner import AgentRunner
from film_pipeline.runtime.prompt_compiler import export_prompts_markdown
from film_pipeline.runtime.timing import format_timing_report

STAGES = [
    "dramaturg",
    "dialogue",
    "director",
    "look",
    "cinematography",
    "timing",  # duration budget + clip split under model max (e.g. 30s)
    "generator",
    "critic",
]


class Pipeline:
    def __init__(self, runner: AgentRunner | None = None) -> None:
        self.runner = runner or AgentRunner()

    def new_bible(
        self,
        project_id: str,
        script: str,
        style_pack: str = "neo_noir",
        title: str | None = None,
        max_clip_sec: int = 30,
        model_profile: str | None = None,
    ) -> dict[str, Any]:
        from film_pipeline.runtime.clip_profile import profile_for_max_clip, resolve_clip_settings

        clip = resolve_clip_settings(max_clip_sec=max_clip_sec, model_profile=model_profile)
        return {
            "meta": {
                "project_id": project_id,
                "title": title or project_id,
                "style_pack": style_pack,
                "max_clip_sec": clip["max_clip_sec"],
                "model_profile": clip["model_profile"],
                "video_clip_label": clip["label"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_version": "0.1.0",
            },
            "source_script": script,
            "story": None,
            "characters": [],
            "scenes": [],
            "dialogue": [],
            "shots": [],
            "look_bible": None,
            "generation_jobs": [],
            "timing_plan": None,
            "assets": [],
            "reviews": [],
            "stage_history": [],
        }

    def project_path(self, project_id: str) -> Path:
        return ensure_project_dir(project_id) / "film_bible.json"

    def save(self, bible: dict[str, Any]) -> Path:
        project_id = bible["meta"]["project_id"]
        path = self.project_path(project_id)
        path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
        # Side-export human-readable prompt board when jobs exist
        if bible.get("generation_jobs"):
            md_path = ensure_project_dir(project_id) / "prompt_board.md"
            md_path.write_text(export_prompts_markdown(bible), encoding="utf-8")
        if bible.get("timing_plan"):
            t_path = ensure_project_dir(project_id) / "timing_plan.md"
            t_path.write_text(format_timing_report(bible), encoding="utf-8")
        return path

    def load(self, project_id: str) -> dict[str, Any]:
        path = self.project_path(project_id)
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def run_stage(self, bible: dict[str, Any], stage: str) -> dict[str, Any]:
        if stage not in STAGES:
            raise ValueError(f"Unknown stage: {stage}. Choose from {STAGES}")
        bible = self.runner.run_stage(stage, bible)
        bible.setdefault("stage_history", []).append(
            {
                "stage": stage,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save(bible)
        return bible

    def run_all(
        self,
        project_id: str,
        script: str,
        style_pack: str = "neo_noir",
        title: str | None = None,
        until: str | None = None,
        max_clip_sec: int = 30,
        model_profile: str | None = None,
    ) -> dict[str, Any]:
        """
        max_clip_sec must be 15 or 30 — chosen by the user *before* pipeline work.
        Final stage is prompt compilation only (no video API).
        """
        bible = self.new_bible(
            project_id,
            script,
            style_pack=style_pack,
            title=title,
            max_clip_sec=max_clip_sec,
            model_profile=model_profile,
        )
        self.save(bible)
        for stage in STAGES:
            bible = self.run_stage(bible, stage)
            if until and stage == until:
                break
        return bible
