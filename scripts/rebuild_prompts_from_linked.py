"""Rebuild generation_jobs using only linked_dialogue (max 3/shot) + clean delivery."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from film_pipeline.orchestrator import Orchestrator
from film_pipeline.runtime.critic_checks import run_critic_checks, speaker_clear_for_line
from film_pipeline.runtime.dialogue_passthrough import (
    apply_dialogue_passthrough,
    list_spoken_lines,
)
from film_pipeline.runtime.offline_stubs import stub_critic
from film_pipeline.runtime.prompt_compiler import export_final_prompts_package
from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent
from film_pipeline.runtime.timing import apply_timing_plan

MAX_LINKED = 3


def _score_shot(shot: dict, char: str, text: str, scene_id: str) -> int:
    sc = 0
    if shot.get("scene_id") == scene_id:
        sc += 20
    blob = f"{shot.get('subject') or ''}{shot.get('dramatic_beat') or ''}{shot.get('subject_en') or ''}"
    if char and char in blob:
        sc += 15
    # prefer people sizes for dialogue
    size = str(shot.get("shot_size") or "").upper()
    if size in {"MCU", "CU", "MS"}:
        sc += 5
    if size in {"INSERT", "EWS"}:
        sc -= 10
    # keyword overlap
    for tok in re.findall(r"[\u4e00-\u9fff]{2,}", text[:20]):
        if tok in blob:
            sc += 2
    return sc


def assign_linked_dialogue(bible: dict) -> None:
    """Each spoken line → exactly one primary shot; max MAX_LINKED per shot."""
    shots = bible.get("shots") or []
    for s in shots:
        s["linked_dialogue"] = []

    loads: dict[str, int] = {s.get("shot_id"): 0 for s in shots}
    spoken = list_spoken_lines(bible)

    for row in spoken:
        char, text, scene_id = row["character"], row["text"], row.get("scene_id") or ""
        ranked = sorted(
            shots,
            key=lambda s: (
                _score_shot(s, char, text, scene_id),
                -loads.get(s.get("shot_id"), 0),
            ),
            reverse=True,
        )
        placed = False
        for s in ranked:
            sid = s.get("shot_id")
            if loads.get(sid, 0) >= MAX_LINKED:
                continue
            if _score_shot(s, char, text, scene_id) < 10 and scene_id:
                # prefer same scene at least
                if s.get("scene_id") != scene_id:
                    continue
            ld = s.setdefault("linked_dialogue", [])
            if text not in ld:
                ld.append(text)
                loads[sid] = loads.get(sid, 0) + 1
                placed = True
                break
        if not placed:
            # force onto best same-scene shot even if full (replace last)
            same = [s for s in shots if s.get("scene_id") == scene_id] or shots
            if same:
                s = max(same, key=lambda x: _score_shot(x, char, text, scene_id))
                ld = s.setdefault("linked_dialogue", [])
                if text not in ld:
                    if len(ld) >= MAX_LINKED:
                        ld.pop()
                    ld.append(text)


def main(project_id: str) -> None:
    o = Orchestrator(log=print)
    b = o.load(project_id)
    b.setdefault("meta", {})
    b["meta"]["scheme"] = b["meta"].get("scheme") or "B"
    b["meta"]["dialogue_polish"] = "skipped"
    apply_dialogue_passthrough(b)
    assign_linked_dialogue(b)
    # re-time + pack packages (15/30 cap, internal cut timeline)
    apply_timing_plan(b, model_profile=(b.get("meta") or {}).get("model_profile"))

    out = run_prompt_writer_agent(b)
    b["generation_jobs"] = out.get("generation_jobs") or []
    b["meta"]["prompt_agent"] = "prompt_writer"
    b["meta"]["stage_engines"] = {
        **(b["meta"].get("stage_engines") or {}),
        "generator": "prompt_writer_offline_rebuild",
    }

    # ensure speaker clarity: inject labeled form only for this shot's linked lines if unclear
    shots_by = {s.get("shot_id"): s for s in b.get("shots") or []}
    for j in b["generation_jobs"]:
        shot = shots_by.get(j.get("shot_id")) or {}
        for t in shot.get("linked_dialogue") or []:
            # find line meta
            char, delivery = "Speaker", ""
            for row in list_spoken_lines(b):
                if t in row["text"] or row["text"] in t:
                    char, delivery = row["character"], ""
                    break
            for blk in b.get("dialogue") or []:
                for ln in blk.get("lines") or []:
                    if ln.get("text") == t or t in (ln.get("text") or ""):
                        char = ln.get("character") or char
                        delivery = ln.get("delivery") or ""
            if not speaker_clear_for_line(char, t if len(t) > 8 else (t + "。"), j, shot):
                # light label append before AUDIO
                deliv = (
                    f"（{delivery}）"
                    if delivery and delivery not in {"按原剧本自然表演", ""}
                    else ""
                )
                zh = f"{char}{deliv}说：「{t}」"
                en = (
                    f'{char} ({delivery}) says: "{t}"'
                    if delivery and delivery not in {"按原剧本自然表演", ""}
                    else f'{char} says: "{t}"'
                )
                for key, bit in (
                    ("director_guided_prompt", en),
                    ("director_guided_prompt_zh", zh),
                ):
                    cur = j.get(key) or ""
                    if char in cur and (t[:8] in cur):
                        # already has pieces
                        if f"{char}说" in cur or f"{char} says" in cur or "说" in cur:
                            continue
                    if "4. AUDIO" in cur:
                        j[key] = cur.replace("4. AUDIO", f"{bit}\n4. AUDIO", 1)
                    elif "4. 音效" in cur:
                        j[key] = cur.replace("4. 音效", f"{bit}\n4. 音效", 1)
                    else:
                        j[key] = cur + f"\n{bit}"

    full = run_critic_checks(b)
    rev = {
        "pass": full.get("pass"),
        "score": full.get("score"),
        "summary": full.get("summary"),
        "failures": [
            {
                "type": f.get("type") or "check",
                "reason": f.get("reason") or "",
                "reroute_to": f.get("reroute_to") or "generator",
            }
            for f in (full.get("failures") or [])
            if f.get("severity") != "warn"
        ],
    }
    b["last_review"] = rev
    b.setdefault("reviews", []).append(rev)
    o.save(b)
    path = export_final_prompts_package(b)
    print("critic", rev.get("pass"), rev.get("summary"))
    for f in rev.get("failures") or []:
        print(" FAIL", f)
    print("delivery", path)
    print("jobs", len(b["generation_jobs"]))
    # load stats
    loads = {
        s.get("shot_id"): len(s.get("linked_dialogue") or []) for s in b.get("shots") or []
    }
    print("linked loads", {k: v for k, v in loads.items() if v})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "golden_island_ep01")
