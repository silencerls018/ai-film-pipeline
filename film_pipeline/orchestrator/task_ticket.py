"""Task tickets — how the Orchestrator assigns work to experts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Track = Literal["main", "assets"]
TicketStatus = Literal["pending", "running", "done", "failed", "skipped"]

# Canonical read/write contracts per stage (orchestrator enforces conceptually)
STAGE_CONTRACTS: dict[str, dict[str, Any]] = {
    "dramaturg": {
        "track": "main",
        "reads": ["production_brief", "meta", "source_script"],
        "writes": ["story", "characters", "scenes"],
        "forbidden": ["dialogue", "shots", "look_bible", "camera", "generation_jobs", "asset_bible"],
    },
    "dialogue": {
        "track": "main",
        "reads": ["production_brief", "story", "characters", "scenes", "source_script"],
        "writes": ["dialogue"],
        "forbidden": ["shots", "look_bible", "generation_jobs", "asset_bible"],
    },
    "director": {
        "track": "main",
        "reads": ["production_brief", "story", "characters", "scenes", "dialogue"],
        "writes": ["shots"],  # dramatic layer only
        "forbidden": ["dialogue", "look_bible", "generation_jobs"],
    },
    "look": {
        "track": "main",
        "reads": ["production_brief", "story", "scenes", "shots"],
        "writes": ["look_bible", "shots.look_intent"],
        "forbidden": ["dialogue", "shots.camera", "generation_jobs"],
    },
    "cinematography": {
        "track": "main",
        "reads": ["production_brief", "shots", "look_bible", "scenes", "dialogue"],
        "writes": ["shots.camera", "shots.look", "shots.duration_sec"],
        "forbidden": ["dialogue", "story", "generation_jobs"],
    },
    "timing": {
        "track": "main",
        "reads": ["production_brief", "meta", "shots", "dialogue"],
        "writes": ["shots.duration_sec", "shots.timing", "shots.generation_clips", "timing_plan"],
        "forbidden": ["dialogue", "story", "look_bible"],
    },
    "generator": {
        "track": "main",
        "reads": [
            "production_brief",
            "meta",
            "story",
            "shots",
            "look_bible",
            "dialogue",
            "characters",
            "timing_plan",
            "asset_bible",
        ],
        "writes": ["generation_jobs"],
        "forbidden": ["dialogue", "story", "shots.camera"],
    },
    "critic": {
        "track": "main",
        "reads": ["production_brief", "film_bible_summary"],
        "writes": ["reviews", "last_review"],
        "forbidden": ["dialogue", "shots", "story"],  # may not rewrite art fields
    },
    "asset": {
        "track": "assets",
        "reads": [
            "production_brief",
            "meta",
            "story",
            "characters",
            "scenes",
            "look_bible",
            "source_script",
        ],
        "writes": ["asset_bible"],
        "forbidden": ["dialogue", "shots", "generation_jobs", "timing_plan"],
    },
}

MAIN_STAGES = [
    "dramaturg",
    "dialogue",
    "director",
    "look",
    "cinematography",
    "timing",
    "generator",
    "critic",
]

ASSET_STAGES = ["asset"]


@dataclass
class TaskTicket:
    ticket_id: str
    stage: str
    track: Track
    assigned_by: str = "orchestrator"
    reads: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    status: TicketStatus = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str | None = None
    error: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def mark_running(self) -> None:
        self.status = "running"

    def mark_done(self) -> None:
        self.status = "done"
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def mark_skipped(self, note: str = "") -> None:
        self.status = "skipped"
        self.note = note
        self.finished_at = datetime.now(timezone.utc).isoformat()


def make_ticket(
    stage: str,
    seq: int,
    constraints: dict[str, Any] | None = None,
    note: str = "",
) -> TaskTicket:
    if stage not in STAGE_CONTRACTS:
        raise ValueError(f"Unknown stage for ticket: {stage}")
    c = STAGE_CONTRACTS[stage]
    return TaskTicket(
        ticket_id=f"T-{stage}-{seq:03d}",
        stage=stage,
        track=c["track"],
        reads=list(c["reads"]),
        writes=list(c["writes"]),
        forbidden=list(c["forbidden"]),
        constraints=constraints or {},
        note=note,
    )


def describe_org_chart() -> str:
    return """
调度总指挥 Orchestrator（代码）
  ├─ 主链 main: dramaturg → dialogue → director → look → cinematography → timing → generator → critic
  └─ 资产旁路 assets: asset（可并行、可晚做、可换图，不堵主链）

创作意图 Producer / 用户 → ProductionBrief（15|30、风格、是否资产轨）
专家 Agent → 只接 TaskTicket，只写合同字段
终点 → 最终提示词（generation_jobs / prompt_board），不调用视频 API
""".strip()
