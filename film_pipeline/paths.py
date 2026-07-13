from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
KNOWLEDGE_DIR = ROOT / "knowledge"
SCHEMAS_DIR = ROOT / "schemas"
BIBLE_DIR = Path(__file__).resolve().parent / "bible"
PROJECTS_DIR = BIBLE_DIR / "projects"
EXAMPLES_DIR = BIBLE_DIR / "examples"


def ensure_project_dir(project_id: str) -> Path:
    path = PROJECTS_DIR / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path
