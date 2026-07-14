"""Clean rebuild: timing floors + package writer v2. No cross-shot dialogue inject."""
from __future__ import annotations

from pathlib import Path

from film_pipeline.orchestrator.orchestrator import Orchestrator
from film_pipeline.runtime.agent_runner import _merge_timing
from film_pipeline.runtime.critic_checks import run_critic_checks
from film_pipeline.runtime.dialogue_passthrough import apply_dialogue_passthrough
from film_pipeline.runtime.knowledge import KnowledgeStore
from film_pipeline.runtime.prompt_compiler import (
    export_final_prompts_package,
    export_prompts_markdown,
)
from film_pipeline.runtime.prompt_writer_agent import run_prompt_writer_agent


def main() -> None:
    orch = Orchestrator()
    b = orch.load("ananke_a")
    # re-passthrough dialogue with cleaner glue strip
    if b.get("source_script"):
        b = apply_dialogue_passthrough(b)
    b = _merge_timing(b, {})
    r = run_prompt_writer_agent(b, knowledge=KnowledgeStore())
    jobs = r.get("generation_jobs") or []
    b["generation_jobs"] = jobs
    b.setdefault("meta", {})
    b["meta"]["prompt_agent"] = "prompt_writer_v3_clean"
    b["meta"]["used_stub"] = False
    rev = run_critic_checks(b)
    b["last_review"] = rev
    orch.save(b)
    export_final_prompts_package(b)
    Path("film_pipeline/bible/projects/ananke_a/prompt_board.md").write_text(
        export_prompts_markdown(b), encoding="utf-8"
    )

    print("packages", len(b.get("generation_packages") or []))
    print("jobs", len(jobs))
    print("critic", rev.get("pass"), rev.get("score"), [f.get("type") for f in rev.get("failures") or []])

    # G08 checks
    for j in jobs:
        if j.get("package_id") != "G08" and j.get("shot_id") != "S09":
            # find ballast
            zh = j.get("director_guided_prompt_zh") or ""
            en_af = j.get("actor_free_prompt") or ""
            en_dg = j.get("director_guided_prompt") or ""
            if "压载舱" in zh or "压载舱" in en_af or "压载舱" in en_dg:
                print("HIT", j.get("package_id"), j.get("shot_id"))
                print(" ZH has full:", "万分之一秒内把我们捏扁" in zh)
                print(" EN free has 中文台词:", "压载舱" in en_af)
                print(" EN guided has 中文台词:", "压载舱" in en_dg)
                print(" EN free spoken-line junk:", "delivers a spoken line" in en_af)
                # no tech dump
                print(" no techA junk:", "核心主板" not in en_af and "核心主板" not in en_dg)
                # show dialogue snippets
                import re

                for m in re.finditer(r"高岩(?:说道| says)[:：]?[「\"][^」\"]+[」\"]", zh + "\n" + en_af):
                    print(" ", m.group(0)[:100])


if __name__ == "__main__":
    main()
