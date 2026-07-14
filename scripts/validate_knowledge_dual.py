#!/usr/bin/env python3
"""Validate dual knowledge base: human docs exist + AI JSON loadable + emotion consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "knowledge"
HUMAN = K / "human"
AI = K / "ai"

REQUIRED_HUMAN = [
    "00_shared_emotions_and_handoffs.md",
    "01_dramaturg.md",
    "02_dialogue.md",
    "03_director.md",
    "04_look.md",
    "05_cinematography.md",
    "06_timing.md",
    "07_asset.md",
    "08_generator.md",
    "09_critic.md",
    "10_orchestrator.md",
]

REQUIRED_AI = [
    "shared/emotion_keys.json",
    "shared/handoff_contracts.json",
    "shared/vocabulary.json",
    "dramaturg/principles.json",
    "dramaturg/scene_functions.json",
    "dialogue/rules.json",
    "dialogue/line_functions.json",
    "director/shot_syntax.json",
    "director/coverage_patterns.json",
    "director/performance_physics.json",
    "director/shot_performance_lighting.json",
    "director/dual_prompt_policy.json",
    "look/tone_types.json",
    "look/emotion_to_look.json",
    "look/lighting_for_emotion.json",
    "camera/decision_rules.json",
    "timing/rules.json",
    "asset/sheet_rules.json",
    "asset/three_view_template.json",
    "generator/compile_rules.json",
    "critic/rubric.json",
    "orchestrator/policy.json",
]


def load(p: Path):
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED_HUMAN:
        if not (HUMAN / name).exists():
            errors.append(f"missing human doc: {name}")
    for rel in REQUIRED_AI:
        path = AI / rel
        if not path.exists():
            errors.append(f"missing ai json: {rel}")
            continue
        try:
            load(path)
        except Exception as e:
            errors.append(f"invalid json {rel}: {e}")

    # emotion key consistency
    try:
        keys = {k["id"] for k in load(AI / "shared/emotion_keys.json")["keys"]}
        look = load(AI / "look/emotion_to_look.json")
        cam_path = K / "camera" / "emotion_to_camera.json"
        if cam_path.exists():
            cam = load(cam_path)
            for ek in keys:
                if ek not in look:
                    errors.append(f"emotion_to_look missing key: {ek}")
                if ek not in cam:
                    errors.append(f"emotion_to_camera missing key: {ek}")
        # handoff stages
        handoff = load(AI / "shared/handoff_contracts.json")["stages"]
        policy = load(AI / "orchestrator/policy.json")
        for s in policy["main_order"]:
            if s not in handoff:
                errors.append(f"handoff missing stage from policy: {s}")
        # dialogue functions match vocabulary
        vocab = load(AI / "shared/vocabulary.json")
        dfun = {f["id"] for f in load(AI / "dialogue/line_functions.json")["functions"]}
        if set(vocab["dialogue_functions"]) != dfun:
            errors.append("dialogue_functions mismatch vocabulary vs line_functions")
    except Exception as e:
        errors.append(f"consistency check failed: {e}")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("OK dual knowledge base")
    print(f"  human docs: {len(REQUIRED_HUMAN)}")
    print(f"  ai json: {len(REQUIRED_AI)}")
    print(f"  emotion keys: {sorted(keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
