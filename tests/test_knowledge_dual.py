from __future__ import annotations

from film_pipeline.runtime.knowledge import KnowledgeStore


def test_validate_script_ok():
    from scripts.validate_knowledge_dual import main

    assert main() == 0


def test_knowledge_store_loads_ai_shared():
    k = KnowledgeStore()
    ek = k.emotion_keys()
    assert {x["id"] for x in ek["keys"]} >= {
        "calm",
        "suspicion",
        "oppression",
        "revelation",
        "intimacy",
        "grief",
        "dread",
    }
    assert k.normalize_emotion("压抑") == "oppression"
    assert k.normalize_emotion("betrayal") == "revelation"


def test_retrieve_includes_shared_for_cinematography():
    k = KnowledgeStore()
    b = k.retrieve_for_stage("cinematography", {"meta": {"style_pack": "neo_noir"}})
    assert b.get("shared", {}).get("emotion_keys")
    assert b.get("decision_rules") or b.get("shared")
    assert "emotion_to_camera" in b
