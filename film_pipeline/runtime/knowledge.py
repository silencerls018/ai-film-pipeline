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

    def infer_subject_class(
        self,
        shot_size: str | None = None,
        subject: str | None = None,
        *,
        env_or_object: bool = False,
    ) -> str:
        """Map shot fields → strategy_matrix subject_class."""
        size = (shot_size or "").upper()
        blob = f"{subject or ''}".lower()
        if size in {"INSERT", "ECU"} or env_or_object and size == "INSERT":
            return "object_insert"
        if env_or_object or size in {"EWS", "WS"} and any(
            k in blob for k in ("room", "street", "city", "landscape", "exterior", "环境", "街道", "房间")
        ):
            if size in {"EWS", "WS"} or any(
                k in blob for k in ("room", "street", "city", "landscape", "环境", "街道")
            ):
                if not any(k in blob for k in ("face", "man", "woman", "person", "人", "脸")):
                    return "environment"
        if any(
            k in blob
            for k in (
                "two",
                "both",
                "ots",
                "over-the-shoulder",
                "over the shoulder",
                "双人",
                "两人",
                "过肩",
            )
        ):
            return "two_shot"
        if env_or_object and size in {"EWS", "WS"}:
            return "environment"
        if env_or_object:
            return "object_insert"
        return "person"

    def strategy_move_keywords(
        self,
        emotion: str,
        shot_size: str | None = None,
        subject_class: str | None = None,
    ) -> list[str]:
        """Expand strategy_matrix families → catalog keyword list."""
        matrix = self.try_load_ai_json("camera/strategy_matrix.json") or {}
        emo = self.normalize_emotion(emotion)
        size = (shot_size or "MS").upper()
        # Normalize size families used in matrix
        size_aliases = {
            "EWS": "WS",
            "VWS": "WS",
            "FS": "MS",
            "MWS": "MS",
            "MCU": "MCU",
            "CU": "CU",
            "ECU": "INSERT",
            "INSERT": "INSERT",
            "WS": "WS",
            "MS": "MS",
        }
        size_key = size_aliases.get(size, size if size in {"WS", "MS", "MCU", "CU", "INSERT"} else "MS")
        subj = subject_class or "person"
        emo_block = (matrix.get("matrix") or {}).get(emo) or {}
        size_block = emo_block.get(size_key) or {}
        families = list(size_block.get(subj) or [])
        if not families:
            # Fallback: any subject under this size, then any size under emotion
            for _s, block in size_block.items():
                if isinstance(block, list) and block:
                    families = list(block)
                    break
        if not families:
            for _sz, block in emo_block.items():
                if isinstance(block, dict):
                    cand = block.get(subj) or block.get("person")
                    if cand:
                        families = list(cand)
                        break
        kw_map = matrix.get("family_to_catalog_keywords") or {}
        keywords: list[str] = []
        for fam in families:
            for k in kw_map.get(fam) or [fam.replace("_", " ")]:
                if k not in keywords:
                    keywords.append(k)
        return keywords

    def pick_move_for_emotion(
        self,
        emotion: str,
        shot_size: str | None = None,
        subject_class: str | None = None,
        *,
        env_or_object: bool = False,
    ) -> dict[str, Any] | None:
        """
        Prefer strategy_matrix keywords + emotion catalog samples;
        fall back to emotion preferred_moves.
        """
        emo = self.normalize_emotion(emotion)
        rules = self.emotion_camera(emo)
        samples = list(rules.get("catalog_samples") or [])
        subj = subject_class or self.infer_subject_class(
            shot_size, None, env_or_object=env_or_object
        )
        strategy_keys = self.strategy_move_keywords(emo, shot_size, subj)
        # Legacy emotion bias (still useful when matrix sparse)
        # Motion-first house style (static only as last resort)
        prefer_substrings = {
            "revelation": ("reveal", "push", "dolly", "rack", "creep", "focus", "pan", "tilt"),
            "oppression": ("push", "creep", "low", "dolly", "track"),
            "intimacy": ("drift", "float", "push", "slow"),
            "grief": ("push", "drift", "dolly out", "slow", "lateral"),
            "dread": ("creep", "push", "dutch", "drift"),
            "suspicion": ("push", "creep", "pan", "drift", "rack"),
            "calm": ("pan", "establish", "lateral", "drift", "track", "drone"),
        }
        legacy_keys = prefer_substrings.get(emo, ())
        # Object/env: ban human-performance catalog phrases
        ban_if_object = (
            "sleeping",
            "villain",
            "face",
            "eyes",
            "smile",
            "tears",
            "portrait",
            "actor",
            "character",
            "person",
            "figure",
            "woman",
            "man ",
            "girl",
            "boy",
            "alone in",
            "her face",
            "his face",
        )
        static_tokens = ("static", "locked-off", "locked off", "tripod hold", "hold still")

        def score_move(s: dict[str, Any]) -> int:
            blob = f"{s.get('id','')} {s.get('en','')} {s.get('prompt_en','')}".lower()
            if subj in {"object_insert", "environment"} and any(b in blob for b in ban_if_object):
                return -100
            # Horror-only catalog lines should not win for non-dread drama
            if emo not in {"dread"} and any(
                b in blob
                for b in ("sleeping figure", "creepy", "horror", "jump scare", "ghost")
            ):
                return -50
            score = 0
            for k in strategy_keys:
                kl = k.lower()
                if kl in blob:
                    score += 3
            for k in legacy_keys:
                if k in blob:
                    score += 1
            # House style: penalize pure static unless matrix explicitly wants it
            if any(t in blob for t in static_tokens) and "static" not in " ".join(
                strategy_keys
            ):
                score -= 4
            # Prefer gentle motion language for inserts
            if subj == "object_insert" and any(
                t in blob for t in ("push", "drift", "rack", "pan", "tilt", "macro")
            ):
                score += 2
            return score

        def pick_best(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
            if not candidates:
                return None
            ranked = sorted(((score_move(s), s) for s in candidates), key=lambda x: -x[0])
            for sc, s in ranked:
                if sc < 0:
                    continue
                if sc == 0 and strategy_keys:
                    continue  # require strategy hit when matrix available
                sid = s.get("id")
                full = self.catalog_move_by_id(sid) if sid else None
                return full or s
            # Fallback: non-banned only
            for sc, s in ranked:
                if sc >= 0:
                    sid = s.get("id")
                    full = self.catalog_move_by_id(sid) if sid else None
                    return full or s
            return None

        picked = pick_best(samples)
        if picked:
            return picked

        # Search full catalog by strategy keywords when samples empty/weak
        if strategy_keys:
            cat = self.moves_catalog()
            if cat:
                picked = pick_best(list(cat.get("moves") or []))
                if picked:
                    return picked

        # Safe motion defaults (house style: avoid pure static)
        if subj == "object_insert":
            return {
                "en": "Slow Push In",
                "zh": "缓推",
                "prompt_en": "very slow push-in on the object detail",
            }
        if subj == "environment":
            return {
                "en": "Slow Pan",
                "zh": "慢摇",
                "prompt_en": "slow pan across the environment, cinematic",
            }

        moves = rules.get("preferred_moves") or []
        # Skip static-named first preference when possible
        ordered = list(moves)
        non_static = [
            m
            for m in ordered
            if not any(t in str(m).lower() for t in ("static", "locked", "hold"))
        ]
        if non_static:
            ordered = non_static + [m for m in ordered if m not in non_static]
        if not ordered:
            return {
                "en": "Micro Drift",
                "zh": "微漂",
                "prompt_en": "subtle floating micro drift, living camera",
            }
        name = ordered[0]
        cat = self.moves_catalog()
        if cat:
            for m in cat.get("moves") or []:
                if m.get("en", "").lower() == str(name).lower() or m.get("id") == name:
                    return m
        return {"en": name, "prompt_en": str(name)}

    def pick_angle_for_emotion(
        self,
        emotion: str,
        shot_size: str | None = None,
        subject_class: str | None = None,
        *,
        env_or_object: bool = False,
    ) -> tuple[str, str]:
        """
        House style: prefer angled camera; avoid pure eye_level.
        Returns (angle, height_hint).
        """
        emo = self.normalize_emotion(emotion)
        subj = subject_class or self.infer_subject_class(
            shot_size, None, env_or_object=env_or_object
        )
        basics = self.try_load_ai_json("camera/angles_lenses_lighting_basics.json") or {}
        by_emo = (basics.get("angle_by_emotion") or {}).get(emo) or []
        by_subj = basics.get("angle_by_subject") or {}
        subj_list = by_subj.get(subj)
        candidates: list[str] = []
        if isinstance(subj_list, list):
            candidates.extend(subj_list)
        candidates.extend(list(by_emo))
        # emotion_to_camera preferred_angles (already angled in KB)
        cam_rules = self.emotion_camera(emo)
        for a in cam_rules.get("preferred_angles") or []:
            if a not in candidates:
                candidates.append(str(a))
        # Filter pure eye_level
        angled = [
            a
            for a in candidates
            if str(a).lower() not in {"eye_level", "eye-level", "eye level"}
        ]
        if not angled:
            # Emotion-safe fallbacks
            fallback = {
                "oppression": "low_angle",
                "dread": "dutch_mild",
                "grief": "slight_high",
                "suspicion": "slight_high",
                "intimacy": "slight_low",
                "revelation": "slight_low",
                "calm": "slight_high",
            }
            angled = [fallback.get(emo, "slight_low")]
        angle = angled[0]
        heights = basics.get("height_hints") or {}
        height = str(heights.get(angle) or "chest")
        if env_or_object or (shot_size or "").upper() in {"EWS", "WS", "INSERT"}:
            # Still angled; prefer high/slight_high for plates & inserts
            if angle in {"eye_level"} or not angle:
                angle = "slight_high"
                height = str(heights.get(angle) or "above_eye")
        return angle, height

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
                "look/character_lighting.json",
            ],
            "cinematography": [
                "camera/decision_rules.json",
                "camera/motivation_types.json",
                "camera/strategy_matrix.json",
                "camera/coverage_moves.json",
                "camera/angles_lenses_lighting_basics.json",
                "camera/composition_framing.json",
                "camera/three_point_and_motivated_light.json",
                "look/emotion_to_look.json",
                "look/lighting_for_emotion.json",
                "look/character_lighting.json",
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

        # Daily web digests (orchestrator knowledge upgrade)
        web = self.try_load_ai_json(f"{stage}/web_digest/latest.json")
        if web is None and stage == "generator":
            # prompt_writer digests alias for generator stage
            web = self.try_load_ai_json("prompt_writer/web_digest/latest.json")
        if web:
            bundle["web_digest"] = {
                "updated_at": web.get("updated_at"),
                "local_date": web.get("local_date"),
                "ok_count": web.get("ok_count"),
                # compact for prompts: only ok items' bullets
                "notes": [
                    {
                        "title": it.get("title") or it.get("query"),
                        "why": it.get("why"),
                        "bullets": it.get("bullets") or [],
                        "url": it.get("url"),
                    }
                    for it in (web.get("items") or [])
                    if it.get("ok")
                ],
            }

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
