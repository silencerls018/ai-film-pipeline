from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from film_pipeline.paths import KNOWLEDGE_DIR


class KnowledgeStore:
    """Load rule tables and short docs from the knowledge/ tree."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or KNOWLEDGE_DIR

    def load_json(self, relative: str) -> Any:
        path = self.root / relative
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

    def emotion_camera(self, emotion: str) -> dict[str, Any]:
        table = self.load_json("camera/emotion_to_camera.json")
        key = self._normalize_emotion(emotion, table)
        return table.get(key, table.get("suspicion", {}))

    def emotion_look(self, emotion: str) -> dict[str, Any]:
        table = self.load_json("look/emotion_to_look.json")
        key = self._normalize_emotion(emotion, table)
        return table.get(key, table.get("suspicion", {}))

    def retrieve_for_stage(self, stage: str, bible: dict[str, Any]) -> dict[str, Any]:
        """Return a compact KB bundle for a pipeline stage."""
        style_id = (bible.get("meta") or {}).get("style_pack", "neo_noir")
        pack = self.style_pack(style_id)
        bundle: dict[str, Any] = {"style_pack": pack}

        if stage in {"look", "cinematography", "critic"}:
            bundle["emotion_to_look"] = self.load_json("look/emotion_to_look.json")
        if stage in {"cinematography", "director", "critic"}:
            bundle["emotion_to_camera"] = self.load_json("camera/emotion_to_camera.json")
            bundle["moves"] = self.load_json("camera/moves.json")
            bundle["lens_language"] = self.load_json("camera/lens_language.json")
        if stage == "dramaturg":
            bundle["principles"] = self.load_text("storycraft/principles.md")
        if stage == "dialogue":
            bundle["rules"] = self.load_text("dialogue/rules.md")
        if stage == "director":
            bundle["shot_syntax"] = self.load_text("directing/shot_syntax.md")
        if stage == "cinematography":
            bundle["axis"] = self.load_text("continuity/axis.md")
            try:
                bundle["exemplar"] = self.load_json(
                    "exemplars/betrayal_reveal_push_in.json"
                )
            except FileNotFoundError:
                pass
        if stage in {"timing", "generator", "critic"}:
            bundle["model_limits"] = self.load_json("timing/model_limits.json")
            bundle["speaking_rates"] = self.load_json("timing/speaking_rates.json")
            bundle["move_durations"] = self.load_json("timing/move_durations.json")
            bundle["holds"] = self.load_json("timing/holds.json")
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
