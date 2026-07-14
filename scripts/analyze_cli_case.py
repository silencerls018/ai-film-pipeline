"""Analyze deep_dive_cli pipeline output for QA notes."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bible_path = ROOT / "film_pipeline" / "bible" / "projects" / "deep_dive_cli" / "film_bible.json"
b = json.loads(bible_path.read_text(encoding="utf-8"))

print("=== META ===")
print("logline:", (b.get("story") or {}).get("logline", "")[:100])
print("chars:", [c.get("name") for c in b.get("characters") or []])
dlg = (b.get("dialogue") or [{}])[0].get("lines") or []
print("dialogue_lines:", len(dlg))
for i, ln in enumerate(dlg[:10]):
    t = (ln.get("text") or "").replace("\n", " ")[:60]
    print(f"  D{i} {ln.get('character')}: {t}")

print("\n=== SHOTS ===")
for s in b.get("shots") or []:
    mov = ((s.get("camera") or {}).get("movement") or {}).get("type")
    print(
        s.get("shot_id"),
        s.get("shot_size"),
        s.get("duration_sec"),
        "clips=",
        len(s.get("generation_clips") or []),
        "move=",
        mov,
        "|",
        (s.get("dramatic_beat_en") or s.get("dramatic_beat") or "")[:48],
    )

print("\n=== SAMPLE PROMPTS ===")
for want in ("S01_T01", "S01_T04", "S01_T14"):
    for j in b.get("generation_jobs") or []:
        if j.get("shot_id") == want and str(j.get("clip_id", "")).endswith("c01"):
            print("=" * 64)
            print(j.get("clip_id"), "dur=", j.get("duration_sec"))
            print("[EN actor_free]")
            print(j.get("actor_free_prompt"))
            print("[EN director_guided]")
            print(j.get("director_guided_prompt"))
            print(
                "CJK_in_actor_free=",
                bool(re.search(r"[\u4e00-\u9fff]", j.get("actor_free_prompt") or "")),
            )
            break

print("\n=== PROBLEMS ===")
issues: list[str] = []
for s in b.get("shots") or []:
    sid = s.get("shot_id")
    mov = str(((s.get("camera") or {}).get("movement") or {}).get("type") or "")
    size = s.get("shot_size")
    if sid in {"S01_T01", "S01_T02"} and "Dutch" in mov:
        issues.append(f"{sid}: 深水建立镜却用 Dutch Angle（情绪表乱配运镜）")
    if size in {"EWS", "INSERT", "WS"} and sid in {"S01_T01", "S01_T02", "S01_T07", "S01_T08", "S01_T15"}:
        perf = s.get("performance") or {}
        if perf.get("physiology_en") and "pupil" in str(perf.get("physiology_en")).lower():
            issues.append(f"{sid}: 物体/空镜仍挂了人脸表演生理")
    dur = float(s.get("duration_sec") or 0)
    if dur > 30:
        issues.append(f"{sid}: 镜时长 {dur}s > 30s（虽会拆 clip，但对白整段挂一镜过重）")
    clips = s.get("generation_clips") or []
    if len(clips) >= 4:
        issues.append(f"{sid}: 拆成 {len(clips)} 段 clip（对白/时长膨胀）")

for j in b.get("generation_jobs") or []:
    en = j.get("director_guided_prompt") or ""
    if "envelope" in en.lower() or "信封" in en:
        issues.append(f"{j.get('clip_id')}: 提示词串入信封样本内容")
    if "sleeping figure" in en.lower() or "horror" in en.lower():
        issues.append(f"{j.get('clip_id')}: 运镜英文串 horror 词库例句")
    free = j.get("actor_free_prompt") or ""
    if re.search(r"[\u4e00-\u9fff]", free):
        issues.append(f"{j.get('clip_id')}: actor_free 英文主稿仍含中文")

ab = b.get("asset_bible") or {}
props = [p.get("name") for p in ab.get("props") or []]
if any("信封" in str(p) or "envelope" in str(p).lower() for p in props):
    issues.append(f"资产轨 props 仍是信封模板: {props}")

# dialogue passthrough meta
for ln in dlg:
    if "跳过对白" in str(ln.get("subtext") or ""):
        # ok if filtered from final prompt
        pass

# check final prompts still have pipeline meta
for j in b.get("generation_jobs") or []:
    blob = (j.get("director_guided_prompt") or "") + (j.get("actor_free_prompt") or "")
    if "跳过对白" in blob or "知识库运镜" in blob:
        issues.append(f"{j.get('clip_id')}: 终稿含流程脏数据")

# dedupe
seen = set()
uniq = []
for x in issues:
    if x not in seen:
        seen.add(x)
        uniq.append(x)
for x in uniq:
    print("-", x)
print(f"\nTotal issue tags: {len(uniq)}")
print("jobs:", len(b.get("generation_jobs") or []))
print("tasks:", [(t.get("stage"), t.get("status")) for t in b.get("task_log") or []])

desk = Path.home() / "Desktop" / "深眸号_CLI全流程_prompt_board.md"
board = ROOT / "film_pipeline" / "bible" / "projects" / "deep_dive_cli" / "prompt_board.md"
if board.exists():
    shutil.copy2(board, desk)
    print("copied board ->", desk)
