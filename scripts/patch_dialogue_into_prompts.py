"""Inject missing spoken lines into generation_jobs so critic dialogue coverage passes."""

from __future__ import annotations

import json
import re
from pathlib import Path

from film_pipeline.orchestrator import Orchestrator
from film_pipeline.runtime.critic_checks import (
    check_dialogue_coverage,
    speaker_attributed_in_text,
)
from film_pipeline.runtime.dialogue_passthrough import (
    apply_dialogue_passthrough,
    list_spoken_lines,
)
from film_pipeline.runtime.offline_stubs import stub_critic
from film_pipeline.runtime.prompt_compiler import export_final_prompts_package


def _norm(s: str) -> str:
    t = re.sub(r"\s+", "", (s or "").strip())
    return t.replace("……", "…").replace("...", "…")


def _jobs_blob(jobs: list[dict]) -> str:
    parts = []
    for j in jobs:
        for k in (
            "director_guided_prompt",
            "director_guided_prompt_zh",
            "actor_free_prompt",
            "actor_free_prompt_zh",
            "zh_director_summary",
        ):
            parts.append(str(j.get(k) or ""))
    return _norm("".join(parts))


def _line_missing(text: str, blob: str) -> bool:
    key = _norm(text)
    if len(key) < 2:
        return False
    core = key[:10] if len(key) >= 10 else key
    if core in blob:
        return False
    core2 = re.sub(r"[…。！？!?，,]", "", key)[:10]
    return not (core2 and core2 in blob)


def _score_job(job: dict, char: str, scene_id: str, shots_by_id: dict) -> int:
    sid = job.get("shot_id") or ""
    shot = shots_by_id.get(sid) or {}
    score = 0
    if shot.get("scene_id") == scene_id:
        score += 10
    blob = " ".join(
        [
            str(shot.get("subject") or ""),
            str(shot.get("dramatic_beat") or ""),
            str(job.get("director_guided_prompt_zh") or ""),
            str(job.get("zh_director_summary") or ""),
        ]
    )
    if char and char in blob:
        score += 5
    # prefer MCU/CU for dialogue
    size = str(shot.get("shot_size") or "").upper()
    if size in {"MCU", "CU", "MS"}:
        score += 2
    return score


def _labeled_bits(char: str, text: str, delivery: str = "") -> tuple[str, str]:
    """Always label speaker — film is unreadable without who speaks."""
    deliv = (
        f"（{delivery}）"
        if delivery and delivery not in {"按原剧本自然表演", ""}
        else ""
    )
    zh_bit = f"{char}{deliv}说：「{text}」"
    if delivery and delivery not in {"按原剧本自然表演", ""}:
        en_bit = f'{char} ({delivery}) says: "{text}"'
    else:
        en_bit = f'{char} says: "{text}"'
    return en_bit, zh_bit


def _inject_line(job: dict, char: str, text: str, delivery: str = "") -> None:
    """Ensure spoken line appears WITH speaker name in EN/ZH prompts."""
    from film_pipeline.runtime.critic_checks import speaker_attributed_in_text

    en_bit, zh_bit = _labeled_bits(char, text, delivery)
    for key, bit in (
        ("director_guided_prompt", en_bit),
        ("director_guided_prompt_zh", zh_bit),
        ("actor_free_prompt", en_bit),
        ("actor_free_prompt_zh", zh_bit),
    ):
        cur = job.get(key) or ""
        if speaker_attributed_in_text(char, text, cur):
            continue
        # Always append a fully labeled line before AUDIO section
        if "4. AUDIO" in cur:
            cur = cur.replace("4. AUDIO", f"SPEAKER LINE: {bit}\n4. AUDIO", 1)
        elif "4. 音效" in cur:
            cur = cur.replace("4. 音效", f"台词（必带说话人）：{bit}\n4. 音效", 1)
        else:
            cur = cur.rstrip() + f"\nSPEAKER LINE: {bit}"
        job[key] = cur

    # linked on sources if any
    src = job.get("sources") or {}
    linked = list(src.get("linked_dialogue") or [])
    if text not in linked:
        linked.append(text)
        src["linked_dialogue"] = linked
        job["sources"] = src


def patch_project(project_id: str) -> dict:
    root = Path("film_pipeline/bible/projects") / project_id
    bible = json.loads((root / "film_bible.json").read_text(encoding="utf-8"))
    bible.setdefault("meta", {})["scheme"] = "B"
    bible["meta"]["dialogue_polish"] = "skipped"
    apply_dialogue_passthrough(bible)

    # delivery map character+text -> delivery
    delivery_map: dict[str, str] = {}
    for blk in bible.get("dialogue") or []:
        for ln in blk.get("lines") or []:
            delivery_map[f"{ln.get('character')}|{ln.get('text')}"] = str(
                ln.get("delivery") or ""
            )

    jobs = list(bible.get("generation_jobs") or [])
    shots = bible.get("shots") or []
    shots_by_id = {s.get("shot_id"): s for s in shots}

    # also patch shot linked_dialogue
    for s in shots:
        s.setdefault("linked_dialogue", [])

    spoken = list_spoken_lines(bible)
    blob = _jobs_blob(jobs)
    # also include existing shot links in scoring blob for missing detect
    for s in shots:
        for ld in s.get("linked_dialogue") or []:
            blob += _norm(str(ld))
        blob += _norm(str(s.get("dramatic_beat") or ""))

    missing = [r for r in spoken if _line_missing(r["text"], blob)]
    print(f"missing before patch: {len(missing)}")
    for r in missing:
        print(" ", r["character"], r["text"][:40])

    for r in spoken:
        text = r["text"]
        char = r["character"]
        scene_id = r.get("scene_id") or ""
        # always ensure linked_dialogue on best shot
        best_shot = None
        best_sc = -1
        for s in shots:
            sc = 0
            if s.get("scene_id") == scene_id:
                sc += 10
            subj = str(s.get("subject") or "") + str(s.get("dramatic_beat") or "")
            if char in subj:
                sc += 5
            if sc > best_sc:
                best_sc = sc
                best_shot = s
        if best_shot is not None:
            ld = list(best_shot.get("linked_dialogue") or [])
            if text not in ld:
                ld.append(text)
                best_shot["linked_dialogue"] = ld

        # inject if missing text OR missing speaker attribution
        prompt_all = "\n".join(
            (j.get("director_guided_prompt") or "")
            + "\n"
            + (j.get("director_guided_prompt_zh") or "")
            for j in jobs
        )
        need = _line_missing(text, _jobs_blob(jobs)) or not speaker_attributed_in_text(
            char, text, prompt_all
        )
        if not need:
            continue

        ranked = sorted(
            jobs,
            key=lambda j: _score_job(j, char, scene_id, shots_by_id),
            reverse=True,
        )
        if not ranked:
            continue
        job = ranked[0]
        delivery = delivery_map.get(f"{char}|{text}", "")
        _inject_line(job, char, text, delivery=delivery)
        print(f"labeled inject -> {job.get('shot_id')}: {char} / {text[:30]}")

    bible["generation_jobs"] = jobs
    bible["shots"] = shots

    # re-check
    fails = check_dialogue_coverage(bible)
    print("coverage after", fails)
    review = stub_critic(bible, {})["review"]
    bible["last_review"] = review
    bible.setdefault("reviews", []).append(review)
    print("critic pass", review.get("pass"), review.get("summary"))
    if not review.get("pass"):
        for f in review.get("failures") or []:
            print(" FAIL", f)

    orch = Orchestrator(log=lambda m: print(m))
    orch.save(bible)
    out = export_final_prompts_package(bible)
    print("delivery", out)
    return review


if __name__ == "__main__":
    import sys

    pid = sys.argv[1] if len(sys.argv) > 1 else "golden_island_ep01"
    patch_project(pid)
