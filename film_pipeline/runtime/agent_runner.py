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
    return bible


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
    return bible


def _merge_generator(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    bible["generation_jobs"] = out["generation_jobs"]
    return bible


def _merge_critic(bible: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    reviews = bible.setdefault("reviews", [])
    reviews.append(out["review"])
    bible["last_review"] = out["review"]
    return bible


MERGERS = {
    "dramaturg": _merge_dramaturg,
    "dialogue": _merge_dialogue,
    "director": _merge_director,
    "look": _merge_look,
    "cinematography": _merge_cinematography,
    "generator": _merge_generator,
    "critic": _merge_critic,
}


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

        try:
            if self.llm.dry_run or not self.llm.api_key:
                raise RuntimeError("dry-run")
            system = (
                skill_text
                + "\n\n你必须只输出合法 JSON 对象，不要 markdown。"
                + "\n严格符合该岗位 schema 字段。"
            )
            user = json.dumps(
                {"film_bible_slice": payload, "knowledge": kb},
                ensure_ascii=False,
                indent=2,
            )
            raw = self.llm.complete_json(system, user)
        except Exception:
            raw = STUBS[stage](bible, kb)

        errors = validate_against_schema(raw, schema)
        if errors:
            # Offline stubs should pass; for LLM, surface errors clearly
            raise ValueError(f"Schema validation failed for stage={stage}:\n" + "\n".join(errors))

        merger = MERGERS[stage]
        return merger(bible, raw)

    def _slice_bible(self, stage: str, bible: dict[str, Any]) -> dict[str, Any]:
        meta = bible.get("meta") or {}
        if stage == "dramaturg":
            return {"meta": meta, "source_script": bible.get("source_script", "")}
        if stage == "dialogue":
            return {
                "meta": meta,
                "story": bible.get("story"),
                "characters": bible.get("characters"),
                "scenes": bible.get("scenes"),
                "source_script": bible.get("source_script", ""),
            }
        if stage == "director":
            return {
                "meta": meta,
                "story": bible.get("story"),
                "characters": bible.get("characters"),
                "scenes": bible.get("scenes"),
                "dialogue": bible.get("dialogue"),
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
        if stage == "generator":
            return {
                "shots": bible.get("shots"),
                "look_bible": bible.get("look_bible"),
                "characters": bible.get("characters"),
            }
        if stage == "critic":
            return {
                "story": bible.get("story"),
                "scenes": bible.get("scenes"),
                "dialogue": bible.get("dialogue"),
                "look_bible": bible.get("look_bible"),
                "shots": bible.get("shots"),
                "generation_jobs": bible.get("generation_jobs"),
            }
        return bible
