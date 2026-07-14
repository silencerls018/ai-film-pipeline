"""
Backward-compatible Pipeline facade over Orchestrator.

Prefer: from film_pipeline.orchestrator import Orchestrator, ProductionBrief
"""

from __future__ import annotations

from typing import Any

from film_pipeline.orchestrator.brief import ProductionBrief
from film_pipeline.orchestrator.orchestrator import Orchestrator
from film_pipeline.orchestrator.task_ticket import ASSET_STAGES, MAIN_STAGES

# Main-chain stage names (for CLI --until etc.)
STAGES = list(MAIN_STAGES)
ALL_STAGES = list(MAIN_STAGES) + list(ASSET_STAGES)


class Pipeline(Orchestrator):
    """Compat wrapper: old Pipeline.run_all → Orchestrator + Brief."""

    def run_all(
        self,
        project_id: str,
        script: str,
        style_pack: str = "neo_noir",
        title: str | None = None,
        until: str | None = None,
        max_clip_sec: int = 30,
        model_profile: str | None = None,
        run_asset_track: bool = True,
        run_main_track: bool = True,
        run_dialogue_polish: bool = True,
    ) -> dict[str, Any]:
        brief = ProductionBrief(
            project_id=project_id,
            title=title or project_id,
            max_clip_sec=max_clip_sec,
            style_pack=style_pack,
            run_main_track=run_main_track,
            run_asset_track=run_asset_track,
            run_dialogue_polish=run_dialogue_polish,
        )
        return self.run_production(brief, script, until=until)

    def run_stage(self, bible: dict[str, Any], stage: str) -> dict[str, Any]:
        if stage not in ALL_STAGES:
            raise ValueError(f"Unknown stage: {stage}. Choose from {ALL_STAGES}")
        return self.assign_and_run(bible, stage)
