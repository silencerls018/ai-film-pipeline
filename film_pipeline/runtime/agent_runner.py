from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from film_pipeline.paths import SKILLS_DIR
from film_pipeline.runtime.knowledge import KnowledgeStore
from film_pipeline.runtime.llm import LLMClient
from film_pipeline.runtime.offline_stubs import STUBS
from film_pipeline.runtime.validate import load_schema, validate_against_schema

# Fields each stage is allowed to contribute into FilmBible
WRITE_PLAN: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {}


def _merge_dramaturg(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["story"] = out["story"]
    bible["characters"] = out["characters"]
    bible["scenes"] = out["scenes"]
    return bible


def _merge_dialogue(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["dialogue"] = out["dialogue"]
    return bible


def _merge_director(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["shots"] = out["shots"]
    # Director owns performance intent package on each shot
    from film_pipeline.runtime.performance import enrich_shots_with_performance

    return enrich_shots_with_performance(bible)


def _merge_look(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["look_bible"] = out["look_bible"]
    intents = {i["shot_id"]: i for i in out.get("shot_look_intents") or []}
    for shot in bible.get("shots") or []:
        if shot["shot_id"] in intents:
            shot["look_intent"] = intents[shot["shot_id"]].get("look_intent")
            shot["look_intent_motivation"] = intents[shot["shot_id"]].get("motivation")
    return bible


def _merge_cinematography(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    patches = {p["shot_id"]: p for p in out.get("shot_patches") or []}
    for shot in bible.get("shots") or []:
        p = patches.get(shot["shot_id"])
        if not p:
            continue
        shot["camera"] = p["camera"]
        shot["look"] = p["look"]
        if "duration_sec" in p:
            shot["duration_sec"] = p["duration_sec"]
        # Align light execution with director performance.lighting_plan when present
        perf = shot.get("performance") or {}
        plan = (perf.get("lighting_plan") or {}) if isinstance(perf, dict) else {}
        if plan and isinstance(shot.get("look"), dict):
            if plan.get("key") and not shot["look"].get("key_light"):
                shot["look"]["key_light"] = plan["key"]
            if plan.get("color") and not shot["look"].get("color_temp"):
                shot["look"]["color_temp"] = plan["color"]
            if plan.get("motivation"):
                base_m = shot["look"].get("motivation") or ""
                if plan["motivation"] not in base_m:
                    shot["look"]["motivation"] = (
                        f"{base_m} | light: {plan['motivation']}"
                    ).strip(" |")
    # Refresh performance after camera locked (move may inform director note)
    from film_pipeline.runtime.performance import enrich_shots_with_performance

    return enrich_shots_with_performance(bible)


def _merge_timing(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    """Always re-run deterministic planner so dialogue/move budgets stay consistent."""
    from film_pipeline.runtime.timing import apply_timing_plan

    profile = (bible.get("meta") or {}).get("model_profile")
    if out.get("timing_plan") and out.get("shot_timings"):
        # still prefer code path
        pass
    return apply_timing_plan(bible, model_profile=profile)


def _merge_generator(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    """
    Prompt Writer Agent owns generation_jobs.
    Prefer agent output; only fall back to full compile if agent returned nothing.
    """
    jobs = out.get("generation_jobs") or []
    if jobs:
        bible["generation_jobs"] = jobs
        bible["meta"] = dict(bible.get("meta") or {})
        bible["meta"]["prompt_agent"] = out.get("agent") or "prompt_writer"
        return bible

    from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent

    agent_out = run_prompt_writer_agent(bible)
    bible["generation_jobs"] = agent_out.get("generation_jobs") or []
    bible["meta"] = dict(bible.get("meta") or {})
    bible["meta"]["prompt_agent"] = agent_out.get("agent") or "prompt_writer"
    return bible


def _merge_critic(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    reviews = bible.setdefault("reviews", [])
    reviews.append(out["review"])
    bible["last_review"] = out["review"]
    return bible


def _merge_asset(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["asset_bible"] = out["asset_bible"]
    # flat list for convenience / legacy
    flat = []
    ab = out["asset_bible"]
    for key in ("characters", "props", "sets"):
        flat.extend(ab.get(key) or [])
    bible["assets"] = flat
    return bible


MERGERS = {
    "dramaturg": _merge_dramaturg,
    "dialogue": _merge_dialogue,
    "director": _merge_director,
    "look": _merge_look,
    "cinematography": _merge_cinematography,
    "timing": _merge_timing,
    "generator": _merge_generator,
    "critic": _merge_critic,
    "asset": _merge_asset,
}

# All stages the runner knows (main + assets)
ALL_STAGES = list(MERGERS.keys())


class AgentRunner:
    def __init__(
        self,
        skills_dir: Path | None = None,
        knowledge: KnowledgeStore | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.skills_dir = skills_dir or SKILLS_DIR
        self.knowledge = knowledge or KnowledgeStore()
        self.llm = llm or LLMClient()

    @staticmethod
    def _style_pack_for_merge(style_id: str) -> dict[str, Any]:
        return KnowledgeStore().style_pack(style_id)

    def load_skill(self, stage: str) -> tuple[str, dict[str, Any]]:
        skill_path = self.skills_dir / stage / "SKILL.md"
        schema_path = self.skills_dir / stage / "schema.json"
        skill_text = skill_path.read_text(encoding="utf-8")
        schema = load_schema(schema_path)
        return skill_text, schema

    def run_stage(self, stage: str, bible: dict[str, Any]) -> dict[str, Any]:
        skill_text, schema = self.load_skill(stage)
        kb = self.knowledge.retrieve_for_stage(stage, bible)
        payload = self._slice_bible(stage, bible)

        # Timing is deterministic code (speech/move budgets + clip split).
        if stage == "timing":
            from film_pipeline.runtime.timing import apply_timing_plan

            profile = (bible.get("meta") or {}).get("model_profile")
            bible = apply_timing_plan(bible, model_profile=profile)
            # Build a schema-valid envelope for history/debug
            raw = {
                "timing_plan": bible.get("timing_plan") or {},
                "shot_timings": [
                    {
                        "shot_id": s.get("shot_id"),
                        "duration_sec": s.get("duration_sec"),
                        "timing": s.get("timing"),
                        "generation_clips": s.get("generation_clips") or [],
                    }
                    for s in bible.get("shots") or []
                ],
            }
            errors = validate_against_schema(raw, schema)
            if errors:
                raise ValueError(
                    f"Schema validation failed for stage={stage}:\n" + "\n".join(errors)
                )
            return bible

        # Dedicated Prompt Writer Agent (dispatch stage name: generator)
        if stage == "generator":
            from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent

            engines = bible.setdefault("meta", {}).setdefault("stage_engines", {})
            dry = bool(self.llm.dry_run or not self.llm.api_key)
            raw = run_prompt_writer_agent(
                bible,
                llm=self.llm,
                knowledge=self.knowledge,
                skills_dir=self.skills_dir,
            )
            engines["generator"] = "prompt_writer_offline" if dry else "prompt_writer_llm"
            if dry:
                bible["meta"]["used_stub"] = True
                bible["meta"]["run_mode"] = bible["meta"].get("run_mode") or "dry-run"
            # Prefer prompt_writer schema if present
            pw_schema_path = self.skills_dir / "prompt_writer" / "schema.json"
            if pw_schema_path.exists():
                schema = load_schema(pw_schema_path)
            errors = validate_against_schema(raw, schema)
            if errors:
                raise ValueError(
                    f"Schema validation failed for stage=generator/prompt_writer:\n"
                    + "\n".join(errors)
                )
            merger = MERGERS[stage]
            return merger(bible, raw)

        import os

        engines = bible.setdefault("meta", {}).setdefault("stage_engines", {})
        dry = bool(self.llm.dry_run or not self.llm.api_key)
        allow_stub_fallback = os.getenv("FILM_PIPELINE_STUB_FALLBACK", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if dry:
            # Intentional offline path — never pretend it was live LLM
            raw = STUBS[stage](bible, kb)
            engines[stage] = "stub_offline"
            bible["meta"]["used_stub"] = True
            bible["meta"]["run_mode"] = bible["meta"].get("run_mode") or "dry-run"
        else:
            try:
                schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
                system = (
                    skill_text
                    + "\n\n你必须只输出合法 JSON 对象，不要 markdown 代码块，不要包裹```json```。"
                    + "\n严格符合以下 JSON Schema：\n\n"
                    + schema_str
                    + "\n\n特别注意："
                    + "\n- 所有 ID 字段（scene_id, shot_id, character id 等）必须用字符串，不要用数字"
                    + "\n- enum 类型字段的值必须严格取枚举列表中之一，不能自创"
                    + "\n- numeric 类型字段（如 emotion.peak）必须用数字，不是文字"
                    + "\n- character.id 字段（如 dramaturg output 中的）是必需的"
                )
                user = json.dumps(
                    {"film_bible_slice": payload, "knowledge": kb},
                    ensure_ascii=False,
                    indent=2,
                )
                raw = self.llm.complete_json(system, user)
                engines[stage] = "llm"
            except Exception as e:
                # Product rule: live mode must NOT silently become stub
                if allow_stub_fallback:
                    raw = STUBS[stage](bible, kb)
                    engines[stage] = f"stub_fallback:{type(e).__name__}"
                    bible["meta"]["used_stub"] = True
                    bible.setdefault("meta", {}).setdefault("stub_fallback_errors", {})[
                        stage
                    ] = str(e)
                else:
                    raise RuntimeError(
                        f"岗位 {stage} 在线 LLM 失败，已禁止静默降级 stub。"
                        f" 设 FILM_PIPELINE_STUB_FALLBACK=1 可显式允许降级。"
                        f" 原因: {e}"
                    ) from e

        errors = validate_against_schema(raw, schema)
        if errors:
            # Offline stubs should pass; for LLM, surface errors clearly
            raise ValueError(
                f"Schema validation failed for stage={stage}:\n" + "\n".join(errors)
            )

        merger = MERGERS[stage]
        return merger(bible, raw)

    def _slice_bible(self, stage: str, bible: dict[str, Any]) -> dict[str, Any]:
        meta = bible.get("meta") or {}
        brief = bible.get("production_brief") or {}
        if stage == "dramaturg":
            return {
                "production_brief": brief,
                "meta": meta,
                "source_script": bible.get("source_script", ""),
            }
        if stage == "dialogue":
            return {
                "production_brief": brief,
                "meta": meta,
                "story": bible.get("story"),
                "characters": bible.get("characters"),
                "scenes": bible.get("scenes"),
                "source_script": bible.get("source_script", ""),
            }
        if stage == "director":
            return {
                "production_brief": brief,
                "meta": meta,
                "story": bible.get("story"),
                "characters": bible.get("characters"),
                "scenes": bible.get("scenes"),
                "dialogue": bible.get("dialogue"),
            }
        if stage == "asset":
            return {
                "production_brief": brief,
                "meta": meta,
                "story": bible.get("story"),
                "characters": bible.get("characters"),
                "scenes": bible.get("scenes"),
                "look_bible": bible.get("look_bible"),
                "source_script": bible.get("source_script", ""),
            }
        if stage == "look":
            return {
                "meta": meta,
                "story": bible.get("story"),
                "scenes": bible.get("scenes"),
                "shots": [
                    {
                        "shot_id": s.get("shot_id"),
                        "scene_id": s.get("scene_id"),
                        "dramatic_beat": s.get("dramatic_beat"),
                        "emotion": s.get("emotion"),
                        "shot_size": s.get("shot_size"),
                    }
                    for s in bible.get("shots") or []
                ],
            }
        if stage == "cinematography":
            return {
                "meta": meta,
                "look_bible": bible.get("look_bible"),
                "shots": bible.get("shots"),
                "scenes": bible.get("scenes"),
            }
        if stage == "timing":
            return {
                "meta": meta,
                "shots": bible.get("shots"),
                "dialogue": bible.get("dialogue"),
            }
        if stage == "generator":
            return {
                "production_brief": brief,
                "meta": meta,
                "story": bible.get("story"),
                "shots": bible.get("shots"),
                "look_bible": bible.get("look_bible"),
                "dialogue": bible.get("dialogue"),
                "characters": bible.get("characters"),
                "timing_plan": bible.get("timing_plan"),
                "asset_bible": bible.get("asset_bible"),
            }
        if stage == "critic":
            return {
                "story": bible.get("story"),
                "scenes": bible.get("scenes"),
                "dialogue": bible.get("dialogue"),
                "look_bible": bible.get("look_bible"),
                "shots": bible.get("shots"),
                "timing_plan": bible.get("timing_plan"),
                "generation_jobs": bible.get("generation_jobs"),
            }
        return bible
