from pathlib import Path

import pytest

from test_freeze import frozen, prepared, runs
from mathmode.io import read_json, write_json
from mathmode.reference_access import seal_baseline, admit_reference
from mathmode.state import StateStore, initial_state


def test_same_problem_reference_cannot_be_admitted_by_a_boolean_flag(tmp_path):
    StateStore(tmp_path).create(initial_state("blind-fixture", "fixture"))
    with pytest.raises(ValueError, match="sealed blind baseline"):
        admit_reference(tmp_path, source="https://example.org/same-problem", question_id="Q1", same_problem=True)
    assert StateStore(tmp_path).load()["reference_access"] == []
    result = admit_reference(tmp_path, source="https://example.org/general-method", question_id="Q1", same_problem=False)
    assert result["external_read_performed"] is False
    assert result["outside_host_blindness"] == "UNVERIFIABLE"
    assert len(StateStore(tmp_path).load()["reference_access"]) == 1


def role_sources(root, monkeypatch, *, two_questions=False):
    """Explicit test-double authorship; never claims real reasoning/paper acceptance."""
    frame = read_json(Path(__file__).resolve().parents[1] / "fixtures/contracts/problem_frame.json")
    frame["case_id"] = StateStore(root).load()["case_id"]
    if two_questions:
        from copy import deepcopy
        child = deepcopy(frame["questions"][0])
        child["question_id"] = "Q2"
        frame["questions"].append(child)
    write_json(root / "framing/frame.json", frame)
    (root / "paper").mkdir()
    (root / "paper/draft.tex").write_text("Synthetic checkpoint draft. No official or scientific acceptance claimed.", encoding="utf-8")
    write_json(root / "agent_runs/framer-fixture/agent_result.json", {"not_actual_reasoning": True})
    write_json(root / "agent_runs/writer-fixture/agent_result.json", {"not_actual_reasoning": True})
    write_json(root / "agent_runs/writer-fixture/task.json", {"question_id": None})
    monkeypatch.setattr("mathmode.reference_access._role_artifacts", lambda root, task, role:
                        {"framing/frame.json": {}} if role == "framer" else {"paper/draft.tex": {}})


@pytest.fixture
def sealed_baseline(frozen, monkeypatch):
    """Real numerical freeze; role authorship is an explicit test double here."""
    root, _, _, _ = frozen
    role_sources(root, monkeypatch)
    baseline = seal_baseline(root, "Q1", framer_task="framer-fixture", frame_path="framing/frame.json",
                             writer_task="writer-fixture", paper_paths=["paper/draft.tex"])
    return root, baseline


def test_checkpoint_preserves_blind_sources_and_refuses_snapshot_tampering(sealed_baseline):
    root, baseline = sealed_baseline
    assert set(baseline["artifacts"]) == {"frame", "models", "code", "results", "paper"}
    assert all(baseline["artifacts"].values())
    assert baseline["paper_acceptance"] == "NOT_RUN"
    result = admit_reference(root, source="https://example.org/explicitly-classified-reference",
                             question_id="Q1", same_problem=True, baseline_id=baseline["baseline_id"])
    assert result["status"] == "PASS"
    with pytest.raises(ValueError, match="cannot be reconstructed"):
        seal_baseline(root, "Q1", framer_task="framer-fixture", frame_path="framing/frame.json",
                      writer_task="writer-fixture", paper_paths=["paper/draft.tex"])
    (root / "paper/draft.tex").write_text("Changed after checkpoint", encoding="utf-8")
    assert admit_reference(root, source="https://example.org/later-reference", question_id="Q1",
                           same_problem=True, baseline_id=baseline["baseline_id"])["status"] == "PASS"
    paper = root / baseline["artifacts"]["paper"][0]["path"]
    assert paper.read_text(encoding="utf-8").startswith("Synthetic checkpoint")
    paper.chmod(0o600)
    paper.write_text("Tampered historical baseline", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        admit_reference(root, source="https://example.org/later-reference", question_id="Q1",
                         same_problem=True, baseline_id=baseline["baseline_id"])
