"""
Orchestrator — scheduling commander.

Assigns TaskTickets, runs main track and optional asset track.
Does not invent art direction; reads ProductionBrief only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from film_pipeline.orchestrator.brief import ProductionBrief
from film_pipeline.orchestrator.task_ticket import (
    ASSET_STAGES,
    MAIN_STAGES,
    TaskTicket,
    make_ticket,
)
from film_pipeline.paths import ensure_project_dir
from film_pipeline.runtime.agent_runner import AgentRunner
from film_pipeline.runtime.prompt_compiler import export_prompts_markdown
from film_pipeline.runtime.timing import format_timing_report

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(msg)


class Orchestrator:
    """Central work dispatcher."""

    def __init__(
        self,
        runner: AgentRunner | None = None,
        log: LogFn | None = None,
    ) -> None:
        self.runner = runner or AgentRunner()
        self.log = log or _default_log
        self._ticket_seq = 0

    # ── bible I/O ─────────────────────────────────────────────

    def project_path(self, project_id: str) -> Path:
        return ensure_project_dir(project_id) / "film_bible.json"

    def save(self, bible: dict[str, Any]) -> Path:
        project_id = bible["meta"]["project_id"]
        path = self.project_path(project_id)
        path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
        if bible.get("generation_jobs"):
            md = ensure_project_dir(project_id) / "prompt_board.md"
            md.write_text(export_prompts_markdown(bible), encoding="utf-8")
        if bible.get("timing_plan"):
            tp = ensure_project_dir(project_id) / "timing_plan.md"
            tp.write_text(format_timing_report(bible), encoding="utf-8")
        if bible.get("asset_bible"):
            ap = ensure_project_dir(project_id) / "asset_board.md"
            ap.write_text(self._export_asset_board(bible), encoding="utf-8")
        if bible.get("production_brief"):
            bp = ensure_project_dir(project_id) / "production_brief.json"
            bp.write_text(
                json.dumps(bible["production_brief"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return path

    def load(self, project_id: str) -> dict[str, Any]:
        with self.project_path(project_id).open(encoding="utf-8") as f:
            return json.load(f)

    def new_bible(self, brief: ProductionBrief, script: str) -> dict[str, Any]:
        b = brief.to_dict()
        return {
            "meta": {
                "project_id": brief.project_id,
                "title": brief.title,
                "style_pack": brief.style_pack,
                "max_clip_sec": brief.max_clip_sec,
                "model_profile": brief.model_profile,
                "video_clip_label": b["video_clip_label"],
                "end_product": brief.end_product,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_version": "0.2.0",
                "commander": "orchestrator",
            },
            "production_brief": b,
            "source_script": script,
            "story": None,
            "characters": [],
            "scenes": [],
            "dialogue": [],
            "shots": [],
            "look_bible": None,
            "timing_plan": None,
            "generation_jobs": [],
            "asset_bible": None,
            "assets": [],  # legacy alias; prefer asset_bible
            "reviews": [],
            "task_log": [],
            "stage_history": [],
        }

    # ── tickets ───────────────────────────────────────────────

    def _next_ticket(self, stage: str, constraints: dict[str, Any] | None = None) -> TaskTicket:
        self._ticket_seq += 1
        brief_constraints = constraints or {}
        return make_ticket(stage, self._ticket_seq, constraints=brief_constraints)

    def _log_ticket(self, bible: dict[str, Any], ticket: TaskTicket) -> None:
        bible.setdefault("task_log", []).append(ticket.to_dict())

    def assign_and_run(
        self,
        bible: dict[str, Any],
        stage: str,
        extra_constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a ticket, run expert, mark done/failed, persist history."""
        brief = bible.get("production_brief") or {}
        constraints = {
            "max_clip_sec": (bible.get("meta") or {}).get("max_clip_sec"),
            "style_pack": (bible.get("meta") or {}).get("style_pack"),
            "end_product": brief.get("end_product", "prompts_only"),
            **(extra_constraints or {}),
        }
        ticket = self._next_ticket(stage, constraints=constraints)
        ticket.mark_running()
        self.log(
            f"[Orchestrator] 派工 {ticket.ticket_id} → {stage} "
            f"(track={ticket.track}, writes={ticket.writes})"
        )
        try:
            # Attach active ticket for runner/debug
            bible["_active_ticket"] = ticket.to_dict()
            bible = self.runner.run_stage(stage, bible)
            bible.pop("_active_ticket", None)
            ticket.mark_done()
            self.log(f"[Orchestrator] 完成 {ticket.ticket_id}")
        except Exception as e:
            bible.pop("_active_ticket", None)
            ticket.mark_failed(str(e))
            self._log_ticket(bible, ticket)
            bible.setdefault("stage_history", []).append(
                {
                    "stage": stage,
                    "ticket_id": ticket.ticket_id,
                    "status": "failed",
                    "at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                }
            )
            self.save(bible)
            raise

        self._log_ticket(bible, ticket)
        bible.setdefault("stage_history", []).append(
            {
                "stage": stage,
                "ticket_id": ticket.ticket_id,
                "status": "done",
                "track": ticket.track,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save(bible)
        return bible

    # ── tracks ────────────────────────────────────────────────

    def _should_skip_dialogue_polish(self, bible: dict[str, Any]) -> bool:
        brief = bible.get("production_brief") or {}
        tracks = brief.get("tracks") or {}
        if "dialogue_polish" in tracks:
            return not bool(tracks["dialogue_polish"])
        if "run_dialogue_polish" in brief:
            return not bool(brief["run_dialogue_polish"])
        return False

    def _run_or_skip_stage(self, bible: dict[str, Any], stage: str) -> dict[str, Any]:
        """Run stage, or passthrough dialogue when user skipped polish."""
        if stage == "dialogue" and self._should_skip_dialogue_polish(bible):
            from film_pipeline.orchestrator.task_ticket import make_ticket
            from film_pipeline.runtime.dialogue_passthrough import apply_dialogue_passthrough

            self._ticket_seq += 1
            ticket = make_ticket(
                "dialogue",
                self._ticket_seq,
                constraints={"mode": "passthrough"},
                note="user skipped dialogue polish — keep original lines",
            )
            ticket.mark_running()
            self.log(
                f"[Orchestrator] 跳过对白精修 {ticket.ticket_id} "
                "→ 保留原剧本台词（passthrough）"
            )
            bible = apply_dialogue_passthrough(bible)
            ticket.mark_done()
            ticket.note = "polish_skipped"
            self._log_ticket(bible, ticket)
            from datetime import datetime, timezone

            bible.setdefault("stage_history", []).append(
                {
                    "stage": "dialogue",
                    "ticket_id": ticket.ticket_id,
                    "status": "skipped_polish",
                    "track": "main",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self.save(bible)
            return bible
        return self.assign_and_run(bible, stage)

    def run_main_track(self, bible: dict[str, Any], until: str | None = None) -> dict[str, Any]:
        self.log("[Orchestrator] ▶ 主链 main 开始")
        for stage in MAIN_STAGES:
            bible = self._run_or_skip_stage(bible, stage)
            if until and stage == until:
                self.log(f"[Orchestrator] 主链停在 until={until}")
                break
        self.log("[Orchestrator] ■ 主链 main 结束（终点=最终提示词）")
        return bible

    def run_asset_track(self, bible: dict[str, Any]) -> dict[str, Any]:
        self.log("[Orchestrator] ▶ 资产旁路 assets 开始（不阻塞换图）")
        for stage in ASSET_STAGES:
            bible = self.assign_and_run(bible, stage)
        self.log("[Orchestrator] ■ 资产旁路结束（三视图提示词 / asset_bible）")
        return bible

    def run_production(
        self,
        brief: ProductionBrief,
        script: str,
        until: str | None = None,
        asset_after_dramaturg: bool = True,
    ) -> dict[str, Any]:
        """
        Full production under orchestrator command.

        Order (reasonable default):
          1. Init bible from brief
          2. Main: dramaturg
          3. If assets enabled: run asset track (has names from dramaturg)
          4. Rest of main chain
        Asset track can also be run alone later via run_asset_track.
        """
        self.log(
            f"[Orchestrator] 接受 ProductionBrief: "
            f"max_clip={brief.max_clip_sec}s style={brief.style_pack} "
            f"main={brief.run_main_track} assets={brief.run_asset_track} "
            f"dialogue_polish={brief.run_dialogue_polish}"
        )
        bible = self.new_bible(brief, script)
        self.save(bible)

        if not brief.run_main_track and brief.run_asset_track:
            # assets-only needs at least crude cast list — run dramaturg first lightly
            bible = self.assign_and_run(bible, "dramaturg")
            bible = self.run_asset_track(bible)
            return bible

        if not brief.run_main_track:
            self.log("[Orchestrator] 主链关闭，无工作")
            return bible

        if asset_after_dramaturg and brief.run_asset_track:
            # dramaturg → assets fork → continue main
            for stage in MAIN_STAGES:
                bible = self._run_or_skip_stage(bible, stage)
                if stage == "dramaturg" and brief.run_asset_track:
                    bible = self.run_asset_track(bible)
                if until and stage == until:
                    break
            return bible

        # Simple serial main, assets after whole main (or never)
        bible = self.run_main_track(bible, until=until)
        if brief.run_asset_track and (until is None or until in MAIN_STAGES):
            # only if main fully done or user didn't stop early before useful cast data
            if until is None:
                bible = self.run_asset_track(bible)
        return bible

    def reroute(self, bible: dict[str, Any], stage: str) -> dict[str, Any]:
        """Critic-driven precise re-run of one stage."""
        self.log(f"[Orchestrator] 精确重跑 stage={stage}")
        return self.assign_and_run(bible, stage)

    @staticmethod
    def _export_asset_board(bible: dict[str, Any]) -> str:
        ab = bible.get("asset_bible") or {}
        lines = [
            f"# Asset Board — {(bible.get('meta') or {}).get('title', '')}",
            "",
            "三视图/设定提示词（可随时换 image_refs，不影响主链镜头合同）",
            "",
        ]
        for section, key in [
            ("Characters", "characters"),
            ("Props", "props"),
            ("Sets", "sets"),
        ]:
            items = ab.get(key) or []
            if not items:
                continue
            lines.append(f"## {section}")
            lines.append("")
            for it in items:
                lines.append(f"### {it.get('asset_id')} — {it.get('name', '')}")
                lines.append(f"- type: {it.get('type')}")
                lines.append(f"- anchors: {it.get('consistency_anchors')}")
                if it.get("image_size_hint"):
                    lines.append(f"- size hint: {it.get('image_size_hint')}")
                lines.append("")
                if it.get("sheet_prompt_zh_summary"):
                    lines.append("**中文说明（辅助）**")
                    lines.append("")
                    lines.append(it.get("sheet_prompt_zh_summary") or "")
                    lines.append("")
                lines.append("**sheet_prompt（英文主稿 · 生图用）**")
                lines.append("```")
                lines.append(it.get("sheet_prompt") or "")
                lines.append("```")
                lines.append("")
                refs = it.get("image_refs") or []
                lines.append(f"- image_refs: {refs if refs else '（空，可稍后替换）'}")
                lines.append("")
        return "\n".join(lines)


# Back-compat alias used by older imports
Pipeline = Orchestrator
