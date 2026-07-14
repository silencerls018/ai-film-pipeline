from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
KNOWLEDGE_DIR = ROOT / "knowledge"
SCHEMAS_DIR = ROOT / "schemas"
BIBLE_DIR = Path(__file__).resolve().parent / "bible"
PROJECTS_DIR = BIBLE_DIR / "projects"
EXAMPLES_DIR = BIBLE_DIR / "examples"
# Final prompts only — each project gets its own folder named after project_id
FINAL_PROMPTS_ROOT = ROOT / "outputs"


def sanitize_project_id(project_id: str) -> str:
    """Safe single-folder name (no path segments / reserved chars)."""
    s = (project_id or "untitled").strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)
    s = s.strip(". ") or "untitled"
    if s in {".", ".."}:
        s = "untitled"
    return s


def ensure_project_dir(project_id: str) -> Path:
    path = PROJECTS_DIR / sanitize_project_id(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def final_prompts_dir(project_id: str) -> Path:
    """
    Dedicated delivery folder for final prompts.
    Path: outputs/<项目名>/
    Folder name == project name (project_id).
    """
    return FINAL_PROMPTS_ROOT / sanitize_project_id(project_id)


def ensure_final_prompts_dir(project_id: str) -> Path:
    path = final_prompts_dir(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path
