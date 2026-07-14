"""ProductionBrief — creative intent set before any expert work."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from film_pipeline.runtime.clip_profile import normalize_max_clip, profile_for_max_clip


@dataclass
class ProductionBrief:
    """
    Producer / user intent. Orchestrator reads this to schedule tracks.
    Experts do not invent these choices.
    """

    project_id: str
    title: str
    max_clip_sec: int  # 15 | 30 only
    style_pack: str = "neo_noir"
    run_main_track: bool = True
    run_asset_track: bool = True
    # True = dialogue agent polishes lines; False = keep original script wording
    run_dialogue_polish: bool = True
    # Optional human gates (reserved; not blocking in v0.2 dry-run)
    gate_dialogue: bool = False
    gate_key_shots: bool = False
    gate_assets: bool = False
    end_product: str = "prompts_only"  # never video API in this pipeline
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        self.max_clip_sec = normalize_max_clip(self.max_clip_sec)
        if self.end_product != "prompts_only":
            self.end_product = "prompts_only"

    @property
    def model_profile(self) -> str:
        return profile_for_max_clip(self.max_clip_sec)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["model_profile"] = self.model_profile
        d["video_clip_label"] = f"最长 {self.max_clip_sec} 秒"
        d["tracks"] = {
            "main": self.run_main_track,
            "assets": self.run_asset_track,
            "dialogue_polish": self.run_dialogue_polish,
        }
        d["human_gates"] = {
            "dialogue": self.gate_dialogue,
            "key_shots": self.gate_key_shots,
            "assets": self.gate_assets,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductionBrief":
        tracks = data.get("tracks") or {}
        gates = data.get("human_gates") or {}
        return cls(
            project_id=data["project_id"],
            title=data.get("title") or data["project_id"],
            max_clip_sec=normalize_max_clip(data.get("max_clip_sec", 30)),
            style_pack=data.get("style_pack") or "neo_noir",
            run_main_track=bool(tracks.get("main", data.get("run_main_track", True))),
            run_asset_track=bool(tracks.get("assets", data.get("run_asset_track", True))),
            run_dialogue_polish=bool(
                tracks.get(
                    "dialogue_polish",
                    data.get("run_dialogue_polish", True),
                )
            ),
            gate_dialogue=bool(gates.get("dialogue", data.get("gate_dialogue", False))),
            gate_key_shots=bool(gates.get("key_shots", data.get("gate_key_shots", False))),
            gate_assets=bool(gates.get("assets", data.get("gate_assets", False))),
            end_product=data.get("end_product") or "prompts_only",
            notes=data.get("notes") or "",
            created_at=data.get("created_at")
            or datetime.now(timezone.utc).isoformat(),
        )


# Known style packs for CLI
STYLE_PACK_CHOICES = ("neo_noir", "warm_realism")
