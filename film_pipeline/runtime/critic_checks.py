"""Deterministic critic checks — dialogue coverage, speaker clarity, job presence."""

from __future__ import annotations

import re
from typing import Any

from film_pipeline.runtime.dialogue_passthrough import extract_raw_dialogue, list_spoken_lines

# Speech-act verbs OK in cinematic prose (not only "X says")
_SPEECH_VERBS = (
    "说",
    "问",
    "喊",
    "叫",
    "道",
    "答",
    "回",
    "吼",
    "嘀咕",
    "低声",
    "压声",
    "冷冷",
    "怒",
    "诧异",
    "says",
    "asks",
    "shouts",
    "replies",
    "mutters",
    "snaps",
)


def _norm(s: str) -> str:
    t = (s or "").strip()
    t = re.sub(r"\s+", "", t)
    t = t.replace("……", "…").replace("...", "…")
    return t


def _prompt_fields(job: dict[str, Any]) -> str:
    parts = []
    for k in (
        "director_guided_prompt",
        "director_guided_prompt_zh",
        "actor_free_prompt",
        "actor_free_prompt_zh",
        "zh_director_summary",
    ):
        parts.append(str(job.get(k) or ""))
    return "\n".join(parts)


def _all_prompt_text(bible: dict[str, Any]) -> str:
    return "\n".join(_prompt_fields(j) for j in (bible.get("generation_jobs") or []))


def _parse_linked_entry(raw: str) -> tuple[str, str]:
    t = (raw or "").strip()
    m = re.match(
        r"^(技术员A|技术员B|Ananke|Anake|高岩|[A-Za-z\u4e00-\u9fff]{1,12})\s*[：:]\s*(.+)$",
        t,
        re.S,
    )
    if m:
        sp = m.group(1).strip()
        if sp == "Anake":
            sp = "Ananke"
        return sp, (m.group(2) or "").strip()
    return "", t


def _expected_rows(bible: dict[str, Any]) -> list[dict[str, str]]:
    """
    Lines that must appear in prompts.

    Prefer director-linked dialogue on shots (industrial contract).
    Fall back to dialogue[] / script extract when no links exist.
    """
    expected_rows: list[dict[str, str]] = []
    # 1) Shot-linked lines (authoritative for what must be on screen)
    for shot in bible.get("shots") or []:
        for raw in shot.get("linked_dialogue") or []:
            sp, body = _parse_linked_entry(str(raw))
            if not body:
                continue
            # resolve to full catalog line when possible
            full = body
            char = sp
            for block in bible.get("dialogue") or []:
                for ln in block.get("lines") or []:
                    lt = (ln.get("text") or "").strip()
                    lc = (ln.get("character") or "").strip()
                    if not lt:
                        continue
                    if body in lt or lt in body or body[:14] in lt or lt[:14] in body:
                        full = lt
                        char = lc or char
                        break
            if not char or char in {"NARRATION", "Speaker"}:
                continue
            expected_rows.append(
                {
                    "character": char,
                    "text": full,
                    "scene_id": str(shot.get("scene_id") or ""),
                    "delivery": "",
                    "shot_id": str(shot.get("shot_id") or ""),
                }
            )

    if expected_rows:
        # dedupe
        seen: set[tuple[str, str]] = set()
        uniq: list[dict[str, str]] = []
        for r in expected_rows:
            k = (r["character"], r["text"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        return uniq

    # 2) Fall back: dialogue[] then script extract
    expected_rows = list_spoken_lines(bible)
    if not expected_rows and bible.get("source_script"):
        extracted = extract_raw_dialogue(bible)
        for blk in extracted.get("dialogue") or []:
            for ln in blk.get("lines") or []:
                text = (ln.get("text") or "").strip()
                char = (ln.get("character") or "").strip()
                if text and char and char != "NARRATION":
                    expected_rows.append(
                        {
                            "character": char,
                            "text": text,
                            "scene_id": str(blk.get("scene_id") or ""),
                            "delivery": str(ln.get("delivery") or ""),
                        }
                    )
    return expected_rows


def _subject_names_in_job(job: dict[str, Any], shot: dict[str, Any] | None) -> str:
    """Who is established on-screen for this clip (SUBJECT + shot subject)."""
    parts = [
        job.get("director_guided_prompt") or "",
        job.get("director_guided_prompt_zh") or "",
        job.get("actor_free_prompt") or "",
        job.get("actor_free_prompt_zh") or "",
    ]
    if shot:
        parts.append(str(shot.get("subject") or ""))
        parts.append(str(shot.get("subject_en") or ""))
        parts.append(str(shot.get("dramatic_beat") or ""))
    # only first section-ish + subject fields matter most
    text = "\n".join(parts)
    # pull SUBJECT block if present
    m = re.search(
        r"1\.\s*SUBJECT[:：].*?(?=2\.\s*CAMERA|2\.\s*摄影|\Z)",
        text,
        flags=re.I | re.S,
    )
    subj_block = m.group(0) if m else text[:400]
    return subj_block + "\n" + str((shot or {}).get("subject") or "")


def speaker_clear_for_line(
    character: str,
    text: str,
    job: dict[str, Any],
    shot: dict[str, Any] | None = None,
) -> bool:
    """
    A line is OK if a viewer/model can tell who speaks.

    Accepted patterns (all fine):
      A) 导演说：「…」 / 导演（诧异）说：「…」 / 导演 says: "…"
      B) 诧异问："…" / 低声说："…"  when SUBJECT/shot clearly is 导演
         (图1是导演 / subject 含导演 / 画面主体就是说话人)

    Not OK:
      Bare quote with no speech verb context and subject is not that character
      (or multi-person shot with no name attached to the quote)
    """
    if not character or not text:
        return False
    hay = _prompt_fields(job)
    if not hay:
        return False

    frag = text.strip()
    cores = [frag]
    if len(frag) >= 8:
        cores.append(frag[:8])
    cores.append(re.sub(r"[…。！？!?，,\s]", "", frag)[:10])

    found_at: list[int] = []
    for core in cores:
        if not core:
            continue
        start = 0
        while True:
            i = hay.find(core, start)
            if i < 0:
                break
            found_at.append(i)
            start = i + 1
        if found_at:
            break
    if not found_at:
        # normalized fallback
        if _norm(frag)[:10] not in _norm(hay):
            return False
        found_at = [max(0, _norm(hay).find(_norm(frag)[:10]))]

    subj = _subject_names_in_job(job, shot)
    subject_is_speaker = character in subj

    for i in found_at:
        window = hay[max(0, i - 56) : i + min(len(frag), 24) + 8]
        pre = window[: max(8, window.find(frag[:6]) if frag[:6] in window else 40)]

        # A) explicit name + speech near quote
        if character in pre or character in window:
            if any(v in window for v in _SPEECH_VERBS) or "说" in window or "says" in window.lower() or "ask" in window.lower():
                # name shouldn't only be inside the quote itself
                quote_part = window[window.find(frag[:4]) :] if frag[:4] in window else ""
                name_only_in_quote = character in quote_part and character not in pre
                if not name_only_in_quote:
                    return True
            # 导演说 / 导演（x）说
            if re.search(
                rf"{re.escape(character)}\s*[（(][^）)]{{0,20}}[）)]?\s*(说|问|道|says|asks)",
                window,
                re.I,
            ):
                return True

        # B) cinematic prose: 低声说 / 诧异问 + quote, subject is this character
        if subject_is_speaker:
            if any(v in pre or v in window for v in ("说", "问", "道", "says", "asks", "低声", "诧异", "怒", "冷")):
                # and quote is not attributed to someone else
                other = re.search(
                    r"([\u4e00-\u9fff]{1,6})\s*(说|问|道)|([A-Za-z]{2,12})\s+says",
                    pre,
                )
                if other:
                    who = other.group(1) or other.group(3) or ""
                    if who and who != character and character not in who:
                        # another named speaker claimed it
                        continue
                return True

        # C) fully labeled form anywhere in job
        if f"{character}说：「{text}" in hay or f'{character} says: "{text}"' in hay:
            return True
        if re.search(
            rf"{re.escape(character)}\s*[（(][^）)]+[）)]\s*说：\s*「?{re.escape(text[:8])}",
            hay,
        ):
            return True

    return False


# Back-compat name used by patch script / tests
def speaker_attributed_in_text(character: str, text: str, haystack: str) -> bool:
    """
    Legacy API: only text blob, no shot context.
    Still accepts 低声说/诧异问 if character name appears near the quote,
    OR labeled 角色说 forms.
    """
    job = {
        "director_guided_prompt": haystack,
        "director_guided_prompt_zh": haystack,
        "actor_free_prompt": "",
        "actor_free_prompt_zh": "",
    }
    # Fake subject if name is in haystack SUBJECT-like
    shot = {"subject": character if character in haystack else ""}
    return speaker_clear_for_line(character, text, job, shot)


def check_dialogue_coverage(bible: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Fail if spoken lines missing from prompts, or who-speaks is unclear.
    """
    failures: list[dict[str, Any]] = []
    expected_rows = _expected_rows(bible)

    if not expected_rows:
        failures.append(
            {
                "type": "dialogue_empty",
                "reason": "无法从剧本解析出任何对白行",
                "reroute_to": "dialogue",
                "severity": "error",
            }
        )
        return failures

    # When expected comes from shot.linked_dialogue, do not fail bible membership
    # (director may shorten; prompts must still carry full speakable Chinese).
    from_shot_links = any(r.get("shot_id") for r in expected_rows)
    if not from_shot_links:
        have_dialogue = _norm(
            "".join(f"{r['character']}{r['text']}" for r in list_spoken_lines(bible))
        )
        missing_in_dialogue: list[str] = []
        for r in expected_rows:
            key = _norm(r["text"])
            if len(key) < 2:
                continue
            if key not in have_dialogue and _norm(r["text"][:12]) not in have_dialogue:
                missing_in_dialogue.append(f"{r['character']}：{r['text']}")

        if missing_in_dialogue:
            sample = "；".join(missing_in_dialogue[:5])
            failures.append(
                {
                    "type": "dialogue_not_in_bible",
                    "reason": f"剧本台词未进入 dialogue[]（{len(missing_in_dialogue)} 条），例：{sample}",
                    "reroute_to": "dialogue",
                    "severity": "error",
                }
            )

    jobs = bible.get("generation_jobs") or []
    if not jobs:
        return failures

    polish = (bible.get("meta") or {}).get("dialogue_polish")
    strict = polish == "skipped" or (bible.get("meta") or {}).get("scheme") == "B"
    shots_by_id = {s.get("shot_id"): s for s in (bible.get("shots") or [])}
    prompt_blob = _all_prompt_text(bible)

    missing_text: list[str] = []
    unclear_speaker: list[str] = []

    for r in expected_rows:
        char = r["character"]
        text = r["text"]
        key = _norm(text)
        core = key[:10] if len(key) >= 10 else key
        in_prompts = (core and core in _norm(prompt_blob)) or (
            text[:8] in prompt_blob if len(text) >= 8 else text in prompt_blob
        )
        if not in_prompts:
            missing_text.append(f"{char}：{text}")
            continue

        # Find best job containing this line
        candidates = []
        for j in jobs:
            fields = _prompt_fields(j)
            if text[:8] in fields or _norm(text)[:10] in _norm(fields):
                candidates.append(j)
        if not candidates:
            # line only in linked_dialogue path — still unclear for film
            unclear_speaker.append(f"{char}：{text}")
            continue

        ok_any = False
        for j in candidates:
            shot = shots_by_id.get(j.get("shot_id"))
            if speaker_clear_for_line(char, text, j, shot):
                ok_any = True
                break
        if not ok_any:
            unclear_speaker.append(f"{char}：{text}")

    if missing_text:
        sample = "；".join(missing_text[:5])
        failures.append(
            {
                "type": "dialogue_not_in_prompts",
                "reason": f"台词未出现在镜头提示词（{len(missing_text)} 条），例：{sample}",
                "reroute_to": "generator",
                "severity": "error" if strict else "warn",
            }
        )

    if unclear_speaker:
        sample = "；".join(unclear_speaker[:5])
        failures.append(
            {
                "type": "dialogue_speaker_unclear",
                "reason": (
                    f"台词在提示词里，但看不出是谁说的（{len(unclear_speaker)} 条）。"
                    f"可用「导演说」或「图1是导演 + 诧异问/低声说」。例：{sample}"
                ),
                "reroute_to": "generator",
                "severity": "error" if strict else "warn",
            }
        )

    # Opening three speakers must each be clear (order preserved in dialogue[])
    first3 = expected_rows[:3]
    if len(first3) >= 3 and strict:
        bad = [
            f"{r['character']}"
            for r in first3
            if f"{r['character']}：{r['text']}" in unclear_speaker
            or f"{r['character']}：{r['text']}" in missing_text
            or any(
                r["text"][:8] in m and r["character"] in m
                for m in unclear_speaker + missing_text
            )
        ]
        # re-evaluate first3 clarity
        unclear_first = []
        for r in first3:
            cands = [
                j
                for j in jobs
                if r["text"][:8] in _prompt_fields(j)
                or _norm(r["text"])[:10] in _norm(_prompt_fields(j))
            ]
            ok = any(
                speaker_clear_for_line(r["character"], r["text"], j, shots_by_id.get(j.get("shot_id")))
                for j in cands
            )
            if not ok:
                unclear_first.append(r["character"])
        if unclear_first:
            failures.append(
                {
                    "type": "dialogue_open_speakers",
                    "reason": (
                        "开场前三句须能看懂谁在说。"
                        f"顺序应为：1={first3[0]['character']} 2={first3[1]['character']} "
                        f"3={first3[2]['character']}；未看清：{','.join(unclear_first)}"
                    ),
                    "reroute_to": "generator",
                    "severity": "error",
                }
            )

    return failures


MAX_LINES_PER_SHOT_PROMPT = 4


def check_line_shot_binding(bible: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Each spoken line should live primarily on few shots (not whole-scene dump).
    Count labeled occurrences per shot prompt; flag overload / unbound lines.
    """
    failures: list[dict[str, Any]] = []
    jobs = bible.get("generation_jobs") or []
    if not jobs:
        return failures

    polish = (bible.get("meta") or {}).get("dialogue_polish")
    strict = polish == "skipped" or (bible.get("meta") or {}).get("scheme") == "B"
    expected = _expected_rows(bible)
    shots_by_id = {s.get("shot_id"): s for s in (bible.get("shots") or [])}

    # per-generation-package dialogue load
    # packages may contain several beats — allow more lines than single-shot jobs
    per_unit_counts: dict[str, int] = {}
    for j in jobs:
        unit = str(j.get("package_id") or j.get("clip_id") or j.get("shot_id") or "")
        is_pkg = bool(j.get("package_id") or j.get("internal_cut") or j.get("beats"))
        cap = max(MAX_LINES_PER_SHOT_PROMPT, 3 * len(j.get("beats") or [1])) if is_pkg else MAX_LINES_PER_SHOT_PROMPT
        fields = _prompt_fields(j)
        n = 0
        for r in expected:
            if r["text"][:8] in fields or _norm(r["text"])[:10] in _norm(fields):
                shot = shots_by_id.get(j.get("shot_id"))
                if speaker_clear_for_line(r["character"], r["text"], j, shot):
                    n += 1
        per_unit_counts[unit] = n
        if n > cap:
            per_unit_counts[unit] = n  # keep for report
            # mark overload with cap
            j.setdefault("_dialogue_cap", cap)

    overloaded = []
    for j in jobs:
        unit = str(j.get("package_id") or j.get("clip_id") or j.get("shot_id") or "")
        is_pkg = bool(j.get("package_id") or j.get("internal_cut") or j.get("beats"))
        cap = max(MAX_LINES_PER_SHOT_PROMPT, 3 * len(j.get("beats") or [1])) if is_pkg else MAX_LINES_PER_SHOT_PROMPT
        c = per_unit_counts.get(unit, 0)
        if c > cap:
            overloaded.append(f"{unit}×{c}/{cap}")

    if overloaded:
        failures.append(
            {
                "type": "dialogue_shot_overload",
                "reason": (
                    "单段生成提示词对白过多："
                    + "；".join(overloaded[:6])
                    + "。时间轴段内可多镜，但总句数应受控。"
                ),
                "reroute_to": "director",
                "severity": "error" if strict else "warn",
            }
        )

    # line appears on too many shots (spray)
    sprayed: list[str] = []
    for r in expected:
        hosts = []
        for j in jobs:
            fields = _prompt_fields(j)
            if r["text"][:8] in fields or _norm(r["text"])[:10] in _norm(fields):
                hosts.append(j.get("shot_id"))
        if len(set(hosts)) > 3:
            sprayed.append(f"{r['character']}：{r['text'][:16]}…→{len(set(hosts))}镜")
    if sprayed:
        failures.append(
            {
                "type": "dialogue_line_sprayed",
                "reason": (
                    "同一句台词出现在过多镜头提示词中："
                    + "；".join(sprayed[:5])
                    + "。应绑定主镜。"
                ),
                "reroute_to": "generator",
                "severity": "error" if strict else "warn",
            }
        )

    return failures


def run_critic_checks(bible: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    failures.extend(check_dialogue_coverage(bible))
    failures.extend(check_line_shot_binding(bible))

    # Product honesty: live path that used stub without declaring
    meta = bible.get("meta") or {}
    if meta.get("run_mode") == "live" and meta.get("used_stub"):
        failures.append(
            {
                "type": "silent_stub_used",
                "reason": "live 模式使用了 stub 降级，交付不可冒充真剧组输出",
                "reroute_to": "generator",
                "severity": "error",
            }
        )

    shots = bible.get("shots") or []
    if not shots:
        failures.append(
            {
                "type": "no_shots",
                "reason": "无 shots",
                "reroute_to": "director",
                "severity": "error",
            }
        )

    jobs = bible.get("generation_jobs") or []
    if shots and not jobs:
        failures.append(
            {
                "type": "no_generation_jobs",
                "reason": "有分镜但无 generation_jobs（终点提示词未完成）",
                "reroute_to": "generator",
                "severity": "error",
            }
        )

    errors = [f for f in failures if f.get("severity") != "warn"]
    score = 1.0 if not errors else max(0.0, 1.0 - 0.15 * len(errors))
    reroute = errors[0].get("reroute_to") if errors else None
    return {
        "pass": len(errors) == 0,
        "score": round(score, 2),
        "summary": (
            "交付可用：结构/对白/说话人/镜句绑定通过"
            if not errors
            else f"发现 {len(errors)} 项必须修复（提示词未达完成标准）"
        ),
        "failures": failures,
        "reroute_to": reroute,
        "agent": "critic",
        "checks": [
            "dialogue_coverage",
            "dialogue_speaker_clarity",
            "line_shot_binding",
            "shots_present",
            "jobs_present",
            "stub_honesty",
        ],
    }
