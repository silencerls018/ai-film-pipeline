"""Video model clip length: only two choices — 15s or 30s."""

from __future__ import annotations

from typing import Any

from film_pipeline.runtime.knowledge import KnowledgeStore

# Canonical user-facing options
CLIP_MAX_CHOICES = (15, 30)

PROFILE_BY_MAX = {
    15: "max_15s",
    30: "max_30s",
}

MAX_BY_PROFILE = {
    "max_15s": 15,
    "max_30s": 30,
    # legacy aliases
    "generic_30s": 30,
    "extendable_30s": 30,
    "short_10s": 15,  # map old short profiles toward 15 if seen
    "short_5s": 15,
}


def normalize_max_clip(value: int | str | None) -> int:
    """Return 15 or 30. Raises ValueError otherwise."""
    if value is None:
        raise ValueError("max_clip is required: 15 or 30")
    if isinstance(value, str):
        v = value.strip().lower().replace("s", "")
        if v in {"15", "30"}:
            return int(v)
        if v in MAX_BY_PROFILE:
            return MAX_BY_PROFILE[v]
        raise ValueError(f"Invalid max clip '{value}'. Use 15 or 30.")
    n = int(value)
    if n not in CLIP_MAX_CHOICES:
        raise ValueError(f"Invalid max clip {n}. Use 15 or 30.")
    return n


def profile_for_max_clip(max_clip_sec: int) -> str:
    max_clip_sec = normalize_max_clip(max_clip_sec)
    return PROFILE_BY_MAX[max_clip_sec]


def max_clip_from_profile(profile: str | None) -> int | None:
    if not profile:
        return None
    if profile in MAX_BY_PROFILE:
        return MAX_BY_PROFILE[profile]
    return None


def resolve_clip_settings(
    max_clip_sec: int | str | None = None,
    model_profile: str | None = None,
) -> dict[str, Any]:
    """
    Prefer explicit max_clip_sec (15|30). Fallback to model_profile name.
    """
    if max_clip_sec is not None:
        m = normalize_max_clip(max_clip_sec)
    elif model_profile:
        m = max_clip_from_profile(model_profile)
        if m is None:
            raise ValueError(
                f"Unknown model_profile '{model_profile}'. Use max_15s / max_30s or max_clip 15|30."
            )
        m = normalize_max_clip(m)
    else:
        raise ValueError("Must choose video max length: 15 or 30 seconds")

    profile = profile_for_max_clip(m)
    store = KnowledgeStore()
    limits = store.load_json("timing/model_limits.json")
    prof = (limits.get("profiles") or {}).get(profile) or {
        "max_clip_sec": m,
        "min_clip_sec": 2,
        "preferred_clip_sec": 6 if m == 15 else 8,
        "label": f"max {m}s",
    }
    return {
        "max_clip_sec": m,
        "model_profile": profile,
        "profile": prof,
        "label": prof.get("label") or f"最长 {m} 秒",
    }
