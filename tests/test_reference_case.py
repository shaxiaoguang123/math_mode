from datetime import datetime, timedelta
import json

import pytest

from test_reference_access import frozen, prepared, runs, role_sources, sealed_baseline
from test_reference_retrieval import server, reference_root
from test_upstream import compute_child
from mathmode.__main__ import main
from mathmode.io import now, read_json, write_json
from mathmode.lineage import ArtifactRegistry, artifact_id
from mathmode.reference_access import admit_reference, seal_baseline
from mathmode.reference_baselines import seal_case_baseline, verify_baseline, verify_blind_admission
from mathmode.reference_retrieval import retrieve_reference, verify_retrieval
from mathmode.state import StateStore, initial_state


def seal(root, question):
    return seal_baseline(root, question, framer_task="framer-fixture", frame_path="framing/frame.json",
                         writer_task="writer-fixture", paper_paths=["paper/draft.tex"])


@pytest.fixture
def complete_case(frozen, monkeypatch):
    root, child, _ = compute_child(frozen)
    assert frozen[1]["numbers"][0]["value"] == child["numbers"][0]["value"] == 0
    role_sources(root, monkeypatch, two_questions=True)
    return root, [seal(root, question) for question in ("Q1", "Q2")]


def test_partial_case_cannot_read_any_same_problem_source(frozen, monkeypatch):
    root = frozen[0]
    role_sources(root, monkeypatch, two_questions=True)
    q1 = seal(root, "Q1")
    assert verify_baseline(root, q1["baseline_id"]) == q1, "Partial history remains inspectable"
    with pytest.raises(ValueError, match="all framed questions"):
        seal_case_baseline(root, [q1["baseline_id"]])
    with server(root) as (base, requests):
        with pytest.raises(ValueError, match="all-question"):
            retrieve_reference(root, source=base + "/method", question_id="Q1", same_problem=True,
                               baseline_id=q1["baseline_id"])
        assert requests == []
    assert StateStore(root).load()["reference_access"] == []
    # Older hosts could record a Q1-only admission. It cannot restore Q2 blindness.
    store = StateStore(root)
    legacy = {"source": "fixture:historical-partial-exposure", "question_id": "Q1", "same_problem": True,
              "baseline_freeze_id": q1["baseline_id"], "at": now()}
    store.update(lambda state: state["reference_access"].append(legacy), expected_revision=store.load()["revision"])
    with pytest.raises(ValueError, match="all-question"):
        verify_blind_admission(root, legacy)
    with pytest.raises(ValueError, match="cannot be reconstructed"):
        seal(root, "Q2")
    with pytest.raises(ValueError, match="cannot be reconstructed"):
        seal_case_baseline(root, [q1["baseline_id"]])


def test_complete_case_http_lineage_and_immutable_history(complete_case, capsys):
    root, checkpoints = complete_case
    ids = [item["baseline_id"] for item in checkpoints]
    assert main(["seal-case-baseline", "--workspace", str(root),
                 "--baseline-id", ids[0], "--baseline-id", ids[1]]) == 0
    envelope = json.loads(capsys.readouterr().out)
    case = verify_baseline(root, envelope["baseline_id"])
    assert case["question_ids"] == ["Q1", "Q2"] and case["paper_acceptance"] == "NOT_RUN"
    with server(root) as (base, requests):
        receipt = retrieve_reference(root, source=base + "/redirect", question_id="Q2", same_problem=True,
            baseline_id=case["baseline_id"], retrieval_id="whole-case")
        assert receipt["status"] == "RETRIEVED"
        assert len(requests) == 2 and all(item["admitted_before_request"] for item in requests)
    relative = "references/whole-case/retrieval.json"
    assert verify_retrieval(root, relative) == receipt
    assert main(["verify-baseline", "--workspace", str(root), "--baseline-id", case["baseline_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["paper_acceptance"] == "NOT_RUN"
    (root / "paper/draft.tex").write_text("Reference-informed revision", encoding="utf-8")
    (root / "code/child.py").write_text("# Reference-informed code revision\n", encoding="utf-8")
    assert verify_baseline(root, case["baseline_id"]) == case
    assert verify_retrieval(root, relative) == receipt
    with pytest.raises(ValueError, match="cannot be reconstructed"):
        seal(root, "Q1")
    # Q2's historical paper is a transitive dependency of the aggregate and HTTP receipt.
    snapshot = root / checkpoints[1]["artifacts"]["paper"][0]["path"]
    snapshot.chmod(0o600)
    snapshot.write_text("Changed blind history", encoding="utf-8")
    stale = StateStore(root).inspect_freshness()["stale"]
    assert artifact_id(f"reference_baselines/{case['baseline_id']}.json") in stale
    assert artifact_id(relative) in stale
    with pytest.raises(ValueError, match="stale"):
        verify_retrieval(root, relative)


def test_case_rejects_mixed_frames_missing_questions_and_originals(complete_case):
    root, checkpoints = complete_case
    ids = [item["baseline_id"] for item in checkpoints]
    with pytest.raises(ValueError, match="unique"):
        seal_case_baseline(root, [ids[0], ids[0]])
    frame = read_json(root / "framing/frame.json")
    frame["questions"][0]["question_id"] = "Q3"
    write_json(root / "framing/frame.json", frame)
    q2_other_frame = seal(root, "Q2")
    with pytest.raises(ValueError, match="different frames"):
        seal_case_baseline(root, [ids[0], q2_other_frame["baseline_id"]])
    with pytest.raises(ValueError, match="changed before sealing"):
        seal_case_baseline(root, ids)
    # Restore the actual old frame bytes, not an invented record.
    old_frame = checkpoints[0]["artifacts"]["frame"][0]
    (root / "framing/frame.json").write_bytes((root / old_frame["path"]).read_bytes())
    case = seal_case_baseline(root, ids)
    path = f"reference_baselines/{case['baseline_id']}.json"
    tampered = dict(case, input_manifest_sha256="0" * 64)
    (root / path).chmod(0o600)
    write_json(root / path, tampered)
    ArtifactRegistry(root).register(path, producer="blind-baseline-service")
    with pytest.raises(ValueError, match="original inputs"):
        verify_baseline(root, case["baseline_id"])
    # Structural tampering cannot drop a question even with a rewritten registry entry.
    tampered = dict(case, question_ids=["Q1"], baselines=[case["baselines"][0]])
    (root / path).chmod(0o600)
    write_json(root / path, tampered)
    ArtifactRegistry(root).register(path, producer="blind-baseline-service",
                                    dependencies=[artifact_id(case["baselines"][0]["path"])])
    with pytest.raises(ValueError, match="different frames"):
        verify_baseline(root, case["baseline_id"])


def test_legacy_single_question_history_and_scope_change(sealed_baseline):
    root, checkpoint = sealed_baseline
    legacy = {"source": "fixture:legacy-single-question", "question_id": "Q1", "same_problem": True,
              "baseline_freeze_id": checkpoint["baseline_id"], "at": now()}
    assert verify_blind_admission(root, legacy) == checkpoint
    earlier = datetime.fromisoformat(checkpoint["created_at"]) - timedelta(seconds=1)
    with pytest.raises(ValueError, match="after case reference exposure"):
        verify_blind_admission(root, dict(legacy, at=earlier.isoformat()))
    frame = read_json(root / "framing/frame.json")
    frame["questions"][0]["question_id"] = "Q2"
    write_json(root / "framing/frame.json", frame)
    with pytest.raises(ValueError, match="changed since checkpoint"):
        admit_reference(root, source="fixture:changed-frame", question_id="Q1", same_problem=True,
                        baseline_id=checkpoint["baseline_id"])


def test_mode_off_is_explicit_immutable_and_does_not_claim_blindness(tmp_path):
    root = tmp_path
    store = StateStore(root)
    store.create(initial_state("nonblind-fixture", "fixture", blind_reference_mode=False))
    with server(root) as (base, requests):
        receipt = retrieve_reference(root, source=base + "/redirect", question_id="Q1", same_problem=True,
                                     retrieval_id="nonblind")
        assert receipt["status"] == "RETRIEVED" and len(requests) == 2
    assert receipt["blind_reference_mode"] is False and receipt["baseline_id"] is None
    assert verify_retrieval(root, "references/nonblind/retrieval.json") == receipt
    with pytest.raises(ValueError, match="cannot claim"):
        admit_reference(root, source="fixture:false-claim", question_id="Q1", same_problem=True, baseline_id="alleged")
    with pytest.raises(ValueError, match="cannot be reconstructed"):
        seal(root, "Q1")
    with pytest.raises(ValueError, match="Immutable state identity"):
        store.update(lambda state: state.update(blind_reference_mode=True), expected_revision=store.load()["revision"])
    assert store.load()["blind_reference_mode"] is False
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(0o600)


def test_mode_cannot_be_disabled_mid_run(reference_root):
    store = StateStore(reference_root)
    with pytest.raises(ValueError, match="Immutable state identity"):
        store.update(lambda state: state.update(blind_reference_mode=False), expected_revision=store.load()["revision"])
    with pytest.raises(ValueError, match="sealed blind baseline"):
        admit_reference(reference_root, source="fixture:mode-bypass", question_id="Q1", same_problem=True)


def test_cli_initialization_can_explicitly_disable_blind_mode(tmp_path, capsys):
    problem = tmp_path / "original.txt"
    problem.write_text("Synthetic original problem", encoding="utf-8")
    declarations = tmp_path / "inputs.json"
    write_json(declarations, [{"input_id": "problem", "path": str(problem), "role": "problem",
        "source": {"uri": "fixture:mode-test", "accessed_at": now(), "license": "synthetic fixture"}}])
    root = tmp_path / "case"
    assert main(["init", "--case-id", "nonblind-cli", "--inputs", str(declarations), "--destination", str(root),
                 "--kind", "fixture", "--no-blind-reference-mode"]) == 0
    assert json.loads(capsys.readouterr().out)["scientific_acceptance"] == "NOT_RUN"
    assert StateStore(root).load()["blind_reference_mode"] is False
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(0o600)
