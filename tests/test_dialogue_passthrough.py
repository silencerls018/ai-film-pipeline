"""Screenplay dialogue passthrough + critic coverage."""

from __future__ import annotations

from film_pipeline.runtime.critic_checks import check_dialogue_coverage, run_critic_checks
from film_pipeline.runtime.dialogue_passthrough import (
    apply_dialogue_passthrough,
    extract_raw_dialogue,
)


SCRIPT = """
1-1 黄金岛户外 日 外
人物：苏檀、导演
△ （空镜）晨雾。
导演：（愠怒）那个赵凛到底来不来？耍大牌也要有个限度吧？
△ 副导演冲过来。
副导演：导演，苏制片说她能搞定赵凛。
导演：（诧异）她？怎么搞定？
副导演：听说他们……（压低声音）是高中时期的青梅竹马。
1-2 休息室 日 内
苏檀：（灿烂假笑）赵凛，好久不见啊。
赵凛：我们的关系，没熟到需要叙旧吧？
"""


def test_extract_director_line_how_to_handle():
    out = extract_raw_dialogue({"source_script": SCRIPT, "scenes": [
        {"scene_id": "S01"}, {"scene_id": "S02"}
    ]})
    lines = [ln for blk in out["dialogue"] for ln in blk["lines"]]
    texts = [ln["text"] for ln in lines]
    chars = [ln["character"] for ln in lines]
    assert "导演" in chars
    assert any("怎么搞定" in t for t in texts)
    # must not glue stage directions into dialogue
    assert not any("△" in t for t in texts)
    assert "第一集" not in chars
    # delivery peeled
    target = next(ln for ln in lines if "怎么搞定" in ln["text"])
    assert target["character"] == "导演"
    assert "她？怎么搞定" in target["text"]
    assert target.get("delivery") == "诧异" or "诧异" in (target.get("delivery") or "")


def test_critic_fails_when_line_missing_from_jobs():
    bible = {
        "source_script": SCRIPT,
        "scenes": [{"scene_id": "S01"}, {"scene_id": "S02"}],
        "shots": [{"shot_id": "S01_T01", "dramatic_beat": "开场"}],
        "generation_jobs": [
            {
                "shot_id": "S01_T01",
                "clip_id": "S01_T01_c01",
                "director_guided_prompt": "Image 1 is director. No full dialogue here.",
                "actor_free_prompt": "x",
            }
        ],
        "meta": {"dialogue_polish": "skipped", "scheme": "B"},
    }
    apply_dialogue_passthrough(bible)
    fails = check_dialogue_coverage(bible)
    types = {f.get("type") for f in fails}
    assert "dialogue_not_in_prompts" in types
    review = run_critic_checks(bible)
    assert review["pass"] is False


def test_cinematic_speech_verbs_ok_when_subject_is_speaker():
    """图1是导演 + 诧异问/低声说 = 合格；悬空引号且主体不是他 = 不合格。"""
    from film_pipeline.runtime.critic_checks import speaker_clear_for_line

    job_ok = {
        "shot_id": "S01_T05",
        "director_guided_prompt": '1. SUBJECT: Image 1 is the director.\n3. STORYLINE: He asks in surprise: "她？怎么搞定？"',
        "director_guided_prompt_zh": '1. SUBJECT: 图1是导演。\n3. STORYLINE: 诧异问："她？怎么搞定？"',
        "actor_free_prompt": "",
        "actor_free_prompt_zh": "",
    }
    shot = {"shot_id": "S01_T05", "subject": "导演半身与监视器"}
    assert speaker_clear_for_line("导演", "她？怎么搞定？", job_ok, shot)

    job_bare = {
        "shot_id": "S01_T05",
        "director_guided_prompt": '1. SUBJECT: Image 1 is the boardwalk.\n3. asks: "她？怎么搞定？"',
        "director_guided_prompt_zh": '1. SUBJECT: 图1是栈道。\n3. 问："她？怎么搞定？"',
        "actor_free_prompt": "",
        "actor_free_prompt_zh": "",
    }
    shot_env = {"shot_id": "S01_T05", "subject": "木质栈道空镜"}
    assert not speaker_clear_for_line("导演", "她？怎么搞定？", job_bare, shot_env)

    # labeled form still ok
    job_label = {
        "director_guided_prompt_zh": '导演（诧异）说：「她？怎么搞定？」',
        "director_guided_prompt": '导演 (诧异) says: "她？怎么搞定？"',
        "actor_free_prompt": "",
        "actor_free_prompt_zh": "",
    }
    assert speaker_clear_for_line("导演", "她？怎么搞定？", job_label, None)
