from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from film_pipeline.paths import KNOWLEDGE_DIR


class KnowledgeStore:
    """
    Load dual knowledge base:
      - knowledge/ai/**     machine rules (preferred for agents)
      - knowledge/camera/** excel catalog & legacy tables
      - knowledge/timing/** timing params
      - knowledge/human/**  not loaded at runtime (humans only)
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or KNOWLEDGE_DIR
        self.ai = self.root / "ai"

    def load_json(self, relative: str) -> Any:
        """Load from knowledge root (legacy paths like camera/..., timing/...)."""
        path = self.root / relative
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def load_ai_json(self, relative: str) -> Any:
        path = self.ai / relative
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def try_load_ai_json(self, relative: str) -> Any | None:
        path = self.ai / relative
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def load_text(self, relative: str) -> str:
        path = self.root / relative
        return path.read_text(encoding="utf-8")

    def style_pack(self, pack_id: str) -> dict[str, Any]:
        path = self.root / "style_packs" / f"{pack_id}.json"
        if not path.exists():
            path = self.root / "style_packs" / "neo_noir.json"
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def emotion_keys(self) -> dict[str, Any]:
        data = self.try_load_ai_json("shared/emotion_keys.json")
        if data:
            return data
        return {"keys": [], "aliases": {}}

    def normalize_emotion(self, emotion: str) -> str:
        table = self.emotion_camera_table()
        ek = self.emotion_keys()
        aliases = ek.get("aliases") or {}
        e = (emotion or "").strip()
        if e in aliases:
            return aliases[e]
        el = e.lower().replace(" ", "_")
        if el in aliases:
            return aliases[el]
        return self._normalize_emotion(el, table)

    def emotion_camera_table(self) -> dict[str, Any]:
        return self.load_json("camera/emotion_to_camera.json")

    def emotion_camera(self, emotion: str) -> dict[str, Any]:
        table = self.emotion_camera_table()
        key = self.normalize_emotion(emotion)
        if key not in table:
            key = self._normalize_emotion(key, table)
        return table.get(key, table.get("suspicion", {}))

    def emotion_look(self, emotion: str) -> dict[str, Any]:
        # Prefer ai/look copy
        table = self.try_load_ai_json("look/emotion_to_look.json")
        if table is None:
            table = self.load_json("look/emotion_to_look.json")
        key = self.normalize_emotion(emotion)
        if key not in table:
            key = self._normalize_emotion(key, table)
        return table.get(key, table.get("suspicion", {}))

    def moves_catalog(self) -> dict[str, Any] | None:
        path = self.root / "camera" / "moves_catalog.json"
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def catalog_move_by_id(self, move_id: str) -> dict[str, Any] | None:
        cat = self.moves_catalog()
        if not cat:
            return None
        for m in cat.get("moves") or []:
            if m.get("id") == move_id or m.get("en") == move_id:
                return m
        return None

    def pick_move_for_emotion(self, emotion: str) -> dict[str, Any] | None:
        rules = self.emotion_camera(emotion)
        samples = list(rules.get("catalog_samples") or [])
        # Prefer story-meaningful moves over generic pan/tilt for certain emotions
        prefer_substrings = {
            "revelation": ("reveal", "push", "dolly", "rack", "creep", "focus"),
            "oppression": ("push", "creep", "low", "dolly", "track"),
            "intimacy": ("static", "locked", "drift", "hold"),
            "grief": ("static", "hold", "slow", "push"),
            "dread": ("creep", "hold", "static", "dutch"),
            "suspicion": ("static", "push", "creep", "hold"),
            "calm": ("static", "pan", "establish", "locked", "lateral"),
        }
        keys = prefer_substrings.get(emotion, ())
        if samples and keys:
            ranked = []
            for s in samples:
                blob = f"{s.get('id','')} {s.get('en','')} {s.get('prompt_en','')}".lower()
                score = sum(1 for k in keys if k in blob)
                ranked.append((score, s))
            ranked.sort(key=lambda x: -x[0])
            if ranked[0][0] > 0:
                samples = [ranked[0][1]] + [s for _, s in ranked[1:]]
        if samples:
            sid = samples[0].get("id")
            full = self.catalog_move_by_id(sid) if sid else None
            return full or samples[0]
        moves = rules.get("preferred_moves") or []
        if not moves:
            return None
        name = moves[0]
        cat = self.moves_catalog()
        if cat:
            for m in cat.get("moves") or []:
                if m.get("en", "").lower() == str(name).lower() or m.get("id") == name:
                    return m
        return {"en": name, "prompt_en": str(name)}

    def retrieve_for_stage(self, stage: str, bible: dict[str, Any]) -> dict[str, Any]:
        """Compact KB bundle for a pipeline stage (AI JSON + big catalogs)."""
        style_id = (bible.get("meta") or {}).get("style_pack", "neo_noir")
        pack = self.style_pack(style_id)
        bundle: dict[str, Any] = {
            "style_pack": pack,
            "shared": {
                "emotion_keys": self.try_load_ai_json("shared/emotion_keys.json"),
                "handoff": self.try_load_ai_json("shared/handoff_contracts.json"),
                "vocabulary": self.try_load_ai_json("shared/vocabulary.json"),
            },
        }

        # Stage-specific AI rules
        stage_files = {
            "dramaturg": ["dramaturg/principles.json", "dramaturg/scene_functions.json"],
            "dialogue": ["dialogue/rules.json", "dialogue/line_functions.json"],
            "director": [
                "director/shot_syntax.json",
                "director/coverage_patterns.json",
                "director/performance_physics.json",
                "director/shot_performance_lighting.json",
                "director/dual_prompt_policy.json",
            ],
            "look": [
                "look/tone_types.json",
                "look/emotion_to_look.json",
                "look/lighting_for_emotion.json",
            ],
            "cinematography": [
                "camera/decision_rules.json",
                "look/emotion_to_look.json",
                "look/lighting_for_emotion.json",
                "director/shot_performance_lighting.json",
            ],
            "timing": ["timing/rules.json"],
            "asset": [
                "asset/sheet_rules.json",
                "asset/three_view_template.json",
            ],
            "generator": [
                "generator/compile_rules.json",
                "director/dual_prompt_policy.json",
            ],
            "critic": ["critic/rubric.json"],
        }
        for rel in stage_files.get(stage, []):
            data = self.try_load_ai_json(rel)
            if data is not None:
                key = rel.split("/")[-1].replace(".json", "")
                bundle[key] = data

        if stage in {"look", "cinematography", "critic", "generator"}:
            try:
                bundle["emotion_to_look"] = self.try_load_ai_json(
                    "look/emotion_to_look.json"
                ) or self.load_json("look/emotion_to_look.json")
            except FileNotFoundError:
                pass

        if stage in {"cinematography", "director", "critic", "generator"}:
            try:
                bundle["emotion_to_camera"] = self.load_json("camera/emotion_to_camera.json")
            except FileNotFoundError:
                pass
            cat = self.moves_catalog()
            if cat:
                bundle["moves_catalog_meta"] = cat.get("meta")
                bundle["moves_catalog_count"] = len(cat.get("moves") or [])
            try:
                bundle["moves"] = self.load_json("camera/moves.json")
            except FileNotFoundError:
                bundle["moves"] = {}
            try:
                bundle["lens_language"] = self.load_json("camera/lens_language.json")
            except FileNotFoundError:
                pass
            try:
                bundle["shot_sizes"] = self.load_json("camera/shot_sizes.json")
            except FileNotFoundError:
                pass

        if stage == "dramaturg":
            # optional legacy prose
            try:
                bundle["legacy_principles_md"] = self.load_text("storycraft/principles.md")
            except FileNotFoundError:
                pass

        if stage == "dialogue":
            try:
                bundle["legacy_rules_md"] = self.load_text("dialogue/rules.md")
            except FileNotFoundError:
                pass

        if stage == "director":
            try:
                bundle["legacy_shot_syntax_md"] = self.load_text("directing/shot_syntax.md")
            except FileNotFoundError:
                pass

        if stage == "cinematography":
            try:
                bundle["axis"] = self.load_text("continuity/axis.md")
            except FileNotFoundError:
                pass
            etc = bundle.get("emotion_to_camera") or {}
            bundle["catalog_by_emotion"] = {
                emo: (etc.get(emo) or {}).get("catalog_samples") or []
                for emo in (
                    "oppression",
                    "suspicion",
                    "intimacy",
                    "grief",
                    "revelation",
                    "calm",
                    "dread",
                )
            }
            try:
                bundle["exemplar"] = self.load_json("exemplars/betrayal_reveal_push_in.json")
            except FileNotFoundError:
                pass

        if stage in {"timing", "generator", "critic"}:
            for name in ("model_limits", "speaking_rates", "move_durations", "holds"):
                try:
                    bundle[name] = self.load_json(f"timing/{name}.json")
                except FileNotFoundError:
                    pass

        if stage == "asset":
            try:
                bundle["emotion_to_look"] = self.try_load_ai_json("look/emotion_to_look.json") or self.load_json(
                    "look/emotion_to_look.json"
                )
            except FileNotFoundError:
                pass

        if stage == "generator":
            try:
                bundle["compile_rules_md"] = self.load_text("prompting/compile_rules.md")
            except FileNotFoundError:
                pass

        if stage == "critic":
            bundle["orchestrator_policy"] = self.try_load_ai_json("orchestrator/policy.json")

        return bundle

    @staticmethod
    def _normalize_emotion(emotion: str, table: dict[str, Any]) -> str:
        e = (emotion or "").strip().lower().replace(" ", "_")
        if e in table:
            return e
        aliases = {
            "pressure": "oppression",
            "betrayal": "revelation",
            "shock": "revelation",
            "fear": "dread",
            "sad": "grief",
            "sadness": "grief",
            "love": "intimacy",
            "tense": "suspicion",
            "anxiety": "suspicion",
            "quiet": "calm",
            "peaceful": "calm",
        }
        if e in aliases and aliases[e] in table:
            return aliases[e]
        for key in table:
            if key in e or e in key:
                return key
        return e
