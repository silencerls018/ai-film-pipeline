"""
Orchestrator daily knowledge upgrade.

Collects professional reference digests from the public web (Wikipedia summary API)
and stores them under knowledge/ai/<role>/web_digest/ for agent KnowledgeStore.

Triggers:
  1) First pipeline run of each calendar day (local)
  2) Explicit CLI / scheduled job at 23:00
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from film_pipeline.paths import KNOWLEDGE_DIR, ROOT

LogFn = Callable[[str], None]

# Each role: English wiki search terms (public encyclopedic craft notes)
ROLE_TOPICS: dict[str, list[dict[str, str]]] = {
    "dramaturg": [
        {"q": "Three-act structure", "why": "story structure"},
        {"q": "Dramatic structure", "why": "scene function"},
        {"q": "Character arc", "why": "want/need/arc"},
    ],
    "dialogue": [
        {"q": "Dialogue (fiction)", "why": "spoken line craft"},
        {"q": "Subtext", "why": "subtext in dialogue"},
        {"q": "Screenplay", "why": "screen dialogue form"},
    ],
    "director": [
        {"q": "Film director", "why": "directing craft"},
        {"q": "Coverage (filmmaking)", "why": "coverage patterns"},
        {"q": "Blocking (stage)", "why": "blocking & performance"},
    ],
    "look": [
        {"q": "Color grading", "why": "look & grade"},
        {"q": "Cinematic color", "why": "palette language"},
        {"q": "High-key lighting", "why": "tonal keys"},
    ],
    "cinematography": [
        {"q": "Cinematography", "why": "camera craft"},
        {"q": "Camera movement", "why": "motivated moves"},
        {"q": "180-degree rule", "why": "axis continuity"},
    ],
    "timing": [
        {"q": "Film editing", "why": "pacing & rhythm"},
        {"q": "Continuity editing", "why": "duration continuity"},
    ],
    "asset": [
        {"q": "Character design", "why": "character sheets"},
        {"q": "Model sheet", "why": "turnaround reference"},
        {"q": "Production design", "why": "sets & props"},
    ],
    "generator": [
        {"q": "Prompt engineering", "why": "prompt writing"},
        {"q": "Text-to-video", "why": "video generation prompts"},
    ],
    "prompt_writer": [
        {"q": "Prompt engineering", "why": "final prompt craft"},
        {"q": "Text-to-image", "why": "visual prompt structure"},
    ],
    "critic": [
        {"q": "Continuity (fiction)", "why": "continuity QC"},
        {"q": "Film editing", "why": "edit/logic QC"},
    ],
    "orchestrator": [
        {"q": "Film production", "why": "production pipeline"},
        {"q": "Multi-agent system", "why": "agent coordination"},
    ],
}

STATE_PATH = KNOWLEDGE_DIR / ".daily_update_state.json"
INDEX_PATH = KNOWLEDGE_DIR / "ai" / "_web_updates" / "latest_index.json"
UA = "AI-Film-Pipeline-KnowledgeUpdater/0.2 (+local research digest; educational)"


def _log(log: LogFn | None, msg: str) -> None:
    if log:
        log(msg)
    else:
        print(msg)


def _http_get_json(url: str, timeout: float = 12.0) -> Any | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _wiki_summary(title: str, lang: str = "en") -> dict[str, Any] | None:
    """MediaWiki REST summary (no API key)."""
    enc = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{enc}"
    data = _http_get_json(url)
    if not data or data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None
    extract = (data.get("extract") or "").strip()
    if not extract:
        return None
    return {
        "title": data.get("title") or title,
        "extract": extract[:1200],
        "url": (data.get("content_urls") or {}).get("desktop", {}).get("page")
        or data.get("content_urls", {}).get("desktop", {}).get("page")
        or f"https://{lang}.wikipedia.org/wiki/{enc}",
        "lang": lang,
        "description": data.get("description") or "",
    }


def _wiki_search_title(query: str, lang: str = "en") -> str | None:
    q = urllib.parse.quote(query)
    url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=opensearch&search={q}&limit=1&namespace=0&format=json"
    )
    data = _http_get_json(url)
    if not data or len(data) < 2 or not data[1]:
        return None
    return str(data[1][0])


def fetch_topic_digest(query: str, why: str) -> dict[str, Any]:
    """Fetch one topic: try EN wiki, then ZH wiki search."""
    title = _wiki_search_title(query, "en") or query
    summary = _wiki_summary(title, "en")
    if not summary:
        # Chinese fallback for film craft terms
        title_zh = _wiki_search_title(query, "zh")
        if title_zh:
            summary = _wiki_summary(title_zh, "zh")
    if not summary:
        return {
            "query": query,
            "why": why,
            "ok": False,
            "note": "network unavailable or page not found",
        }
    return {
        "query": query,
        "why": why,
        "ok": True,
        "source": "wikipedia_rest_summary",
        "title": summary["title"],
        "description": summary.get("description") or "",
        "extract": summary["extract"],
        "url": summary["url"],
        "lang": summary.get("lang") or "en",
        # compact bullets for agents (first 3 sentences-ish)
        "bullets": _to_bullets(summary["extract"]),
    }


def _to_bullets(extract: str, n: int = 4) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", extract.strip())
    out = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        out.append(p[:280])
        if len(out) >= n:
            break
    if not out and extract:
        out = [extract[:280]]
    return out


def today_local() -> str:
    return date.today().isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def already_updated_today(state: dict[str, Any] | None = None) -> bool:
    st = state if state is not None else load_state()
    return st.get("last_success_date") == today_local()


def should_skip_network() -> bool:
    return os.getenv("FILM_PIPELINE_SKIP_KNOWLEDGE_UPDATE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def update_role_knowledge(
    role: str,
    topics: list[dict[str, str]] | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    topics = topics or ROLE_TOPICS.get(role) or []
    day = today_local()
    items: list[dict[str, Any]] = []
    for t in topics:
        dig = fetch_topic_digest(t["q"], t.get("why") or "")
        items.append(dig)
        status = "ok" if dig.get("ok") else "miss"
        _log(log, f"  · [{role}] {t['q']}: {status}")

    payload = {
        "role": role,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "local_date": day,
        "commander": "orchestrator",
        "purpose": "daily professional craft digest for multi-agent knowledge base",
        "items": items,
        "ok_count": sum(1 for i in items if i.get("ok")),
        "item_count": len(items),
    }

    out_dir = KNOWLEDGE_DIR / "ai" / role / "web_digest"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # rolling latest pointer for KnowledgeStore
    latest = out_dir / "latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"role": role, "path": str(path), "ok_count": payload["ok_count"]}


def run_daily_knowledge_update(
    *,
    force: bool = False,
    roles: list[str] | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """
    Orchestrator knowledge upgrade entry.
    Returns summary dict; no-op if already done today (unless force).
    """
    if should_skip_network() and not force:
        _log(log, "[Orchestrator] 知识库日更跳过（FILM_PIPELINE_SKIP_KNOWLEDGE_UPDATE）")
        return {"skipped": True, "reason": "env_skip"}

    state = load_state()
    if already_updated_today(state) and not force:
        _log(
            log,
            f"[Orchestrator] 知识库今日已更新（{today_local()}），跳过网络收集",
        )
        return {
            "skipped": True,
            "reason": "already_today",
            "last_success_date": state.get("last_success_date"),
            "last_report": state.get("last_report"),
        }

    _log(log, "[Orchestrator] ▶ 日更：为各岗位从网络收集专业技能摘要…")
    role_list = roles or list(ROLE_TOPICS.keys())
    results: list[dict[str, Any]] = []
    for role in role_list:
        try:
            results.append(update_role_knowledge(role, log=log))
        except Exception as e:  # noqa: BLE001 — isolate per-role failures
            _log(log, f"  · [{role}] ERROR {e}")
            results.append({"role": role, "ok_count": 0, "error": str(e)})

    report = {
        "local_date": today_local(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "roles": results,
        "total_ok": sum(int(r.get("ok_count") or 0) for r in results),
        "force": force,
        "root": str(KNOWLEDGE_DIR / "ai"),
    }

    # global index
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_any = report["total_ok"] > 0
    state = {
        "last_attempt_date": today_local(),
        "last_success_date": today_local() if ok_any else state.get("last_success_date"),
        "last_report": report,
        "last_error": None if ok_any else "zero topics fetched (offline?)",
    }
    save_state(state)

    _log(
        log,
        f"[Orchestrator] ■ 知识库日更结束：抓取成功条目 {report['total_ok']} · "
        f"索引 {INDEX_PATH.relative_to(ROOT) if INDEX_PATH.is_relative_to(ROOT) else INDEX_PATH}",
    )
    return report


def maybe_daily_knowledge_update_on_run(log: LogFn | None = None) -> dict[str, Any]:
    """
    Call at first production run of the day.
    Controlled by FILM_PIPELINE_DAILY_KNOWLEDGE (default on).
    """
    flag = os.getenv("FILM_PIPELINE_DAILY_KNOWLEDGE", "1").lower()
    if flag in {"0", "false", "no", "off"}:
        return {"skipped": True, "reason": "disabled"}
    return run_daily_knowledge_update(force=False, log=log)
