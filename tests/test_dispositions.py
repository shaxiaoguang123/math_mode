"""Real numerical work; independent reasoning provenance is explicitly doubled."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from test_validation import prepared
from test_workflow import case, review as semantic_review
from test_upstream import compute_child
from mathmode import dispositions
from mathmode.agents import _check_response
from mathmode.contracts import validate
from mathmode.freeze import verify_freeze
from mathmode.io import read_json, write_json, now, file_hash
from mathmode.lineage import artifact_id
from mathmode.orchestrator import Orchestrator


def authored_disposition(root, service, plan, source, source_kind):
    """Author test doubles, never a real reasoning or scientific approval claim."""
    frame_path = plan["framing"]["problem_frame"]
    value = read_json(root / source)
    frame = read_json(root / frame_path)
    pending = dispositions.issues(source_kind, value, frame)
    stem = "data" if source_kind == "data_audit" else "validation"
    proposal_path, review_path = f"framing/{stem}-disposition.json", f"reviews/{stem}-disposition.json"
    raw = next(item["path"] for item in read_json(root / "input_manifest.json")["files"] if item["input_id"] == "data")
    proposal = {"schema_version": "2.0", "disposition_id": stem + "-fixture", "actor_id": "fixture-disposition-author",
        "question_id": None if source_kind == "data_audit" else "Q1", "source_kind": source_kind,
        "source": dispositions.pin(root, source), "frame": dispositions.pin(root, frame_path), "created_at": now(),
        "items": [{"locator": locator, "question_ids": sorted(questions), "action": "retain_with_limit",
            "boundary": "Synthetic exact-case fixture only; absent notes supply no numerical feature or scientific conclusion.",
            "rationale": "Only supplied x and observed_y enter the actual fixture calculation.",
            "evidence_refs": [artifact_id(raw)]} for locator, (_, questions) in pending.items()]}
    write_json(root / proposal_path, proposal)
    review = {"schema_version": "2.0", "review_id": stem + "-review-fixture", "actor_id": "fixture-disposition-reviewer",
        "reviewed_actor_id": proposal["actor_id"], "question_id": proposal["question_id"],
        "proposal": dispositions.pin(root, proposal_path), "verdict": "LIMITED", "rationale": "Explicit semantic provenance double.",
        "evidence_refs": [artifact_id(path) for path in (source, frame_path, proposal_path, raw)], "created_at": now()}
    write_json(root / review_path, review)
    registry = service.registry
    registry.register(frame_path, producer=frame["producer"])
    registry.register(source, producer=value["actor_id"])
    with registry.batch():
        registry.register(proposal_path, producer=proposal["actor_id"],
            dependencies=[artifact_id(source), artifact_id(frame_path), artifact_id(raw)])
        registry.register(review_path, producer=review["actor_id"],
            dependencies=[artifact_id(proposal_path), artifact_id(source), artifact_id(frame_path), artifact_id(raw)])
    binding = {"source": source, "proposal": proposal_path, "review": review_path}
    plan.setdefault("dispositions", []).append(binding)
    return binding


def double_role_provenance(monkeypatch):
    monkeypatch.setattr(dispositions, "_contract", lambda root, path, name: validate(name, read_json(root / path), root=root))


@pytest.mark.parametrize("prepared", ["missing_unused_note"], indirect=True)
def test_reviewed_warnings_and_limited_validation_freeze_and_propagate(case, monkeypatch, capsys):
    root, service, plan = case
    audit_path = "framing/deterministic_data_audit.json"
    audit_hash = file_hash(root / audit_path)
    assert Orchestrator(root, None)._kind(audit_path)[1]["status"] == "WARN"
    # Actual scheduling guard admits inspection and blocks modeling without the
    # full reviewed warning bundle. Only frame authorship is doubled here.
    orchestrator = Orchestrator(root, None)
    real_kind = orchestrator._kind
    frame_path = plan["framing"]["problem_frame"]
    monkeypatch.setattr(orchestrator, "_kind", lambda path: ("problem_frame", read_json(root / path))
                        if path == frame_path else real_kind(path))
    inputs = [{"path": path, "artifact_id": artifact_id(path)} for path in ("input_manifest.json", audit_path, frame_path)]
    task = {"role": "framer", "interaction_mode": "autopilot", "question_id": None, "inputs": inputs}
    orchestrator._guard({}, task, {})
    with pytest.raises(ValueError, match="reviewed disposition"):
        orchestrator._guard({}, {**task, "role": "method_retriever", "question_id": "Q1"}, {})
    blocked = service.observe(plan)
    assert blocked["gates"]["G2"]["status"] == "BLOCKED"
    binding = authored_disposition(root, service, plan, audit_path, "data_audit")
    with pytest.raises(ValueError, match="handoff"):
        dispositions.verify_disposition(root, binding)
    double_role_provenance(monkeypatch)
    assert dispositions.verify_disposition(root, binding)["restrictions"]
    assert service.observe(plan)["gates"]["G2"]["status"] == "LIMITED"
    for action in ("run-main", "run-baseline", "independent-validate"):
        result = service.advance(plan, interpreter=sys.executable)
        assert result["performed"]["action"] == action, result
    record = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    spec = read_json(root / "main_spec.json")
    review_path = plan["questions"][0]["validation_review"]
    semantic_review(root, review_path, spec["actor_id"], [record["validation"], record["evidence"],
        "main_spec.json", "baseline_spec.json", spec["validation_plan"]["criteria"]["path"]])
    limited = read_json(root / review_path)
    limited.update(verdict="LIMITED", limitations=["A synthetic affine case does not establish real-world performance."],
        findings=[{"severity": "warning", "issue": "No real-world external test population.", "evidence_refs": [artifact_id(record["validation"])]}])
    write_json(root / review_path, limited)
    assert service.observe(plan)["gates"]["G5"]["status"] == "BLOCKED"
    authored_disposition(root, service, plan, review_path, "semantic_review")
    result = service.advance(plan)
    assert result["performed"]["action"] == "freeze", result
    assert all(result["gates"][gate]["status"] == "LIMITED" for gate in ("G2", "G3", "G4", "G5", "G6"))
    assert result["gates"]["G7"]["status"] == result["official_compliance"] == "BLOCKED"
    assert read_json(root / audit_path)["status"] == "WARN" and file_hash(root / audit_path) == audit_hash
    parent = verify_freeze(root, "Q1")
    assert parent["numbers"][0]["value"] == 0
    assert len(parent["qualifications"]["restrictions"]) == 3
    assert len(parent["qualifications"]["sources"]) == 2
    from mathmode.__main__ import main
    assert main(["verify-disposition", "--workspace", str(root), "--source", binding["source"],
                 "--proposal", binding["proposal"], "--review", binding["review"]]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "LIMITED"
    assert main(["verify-freeze", "--workspace", str(root), "--question-id", "Q1"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "LIMITED"
    _, child, _ = compute_child((root, parent, None, None))
    assert child["qualifications"]["restrictions"] == parent["qualifications"]["restrictions"]
    assert child["qualifications"]["inherited_from"][0]["freeze_id"] == parent["freeze_id"]
    assert child["qualifications"]["sources"] == []
    original_numbers = deepcopy(parent["numbers"])
    changed = read_json(root / binding["review"])
    changed["rationale"] = "Altered after the numerical snapshot"
    write_json(root / binding["review"], changed)
    for qid in ("Q1", "Q2"):
        with pytest.raises(ValueError, match="stale"):
            verify_freeze(root, qid)
    assert read_json(root / f"freezes/{parent['freeze_id']}/frozen_numbers.json")["numbers"] == original_numbers


@pytest.mark.parametrize("prepared", ["missing_unused_note"], indirect=True)
def test_dispositions_reject_omissions_self_review_errors_and_stale_context(case, monkeypatch):
    root, service, plan = case
    binding = authored_disposition(root, service, plan, "framing/deterministic_data_audit.json", "data_audit")
    double_role_provenance(monkeypatch)
    proposal, review = (read_json(root / binding[key]) for key in ("proposal", "review"))
    for mutate, reason in (
        (lambda p, r: r.update(actor_id=p["actor_id"]), "independent"),
        (lambda p, r: r.update(actor_id="data-auditor-tool"), "independent"),
        (lambda p, r: r.update(verdict="BLOCKED"), "blocks"),
        (lambda p, r: p["items"][0].update(locator="/issues/99"), "every warning"),
        (lambda p, r: p["items"][0].update(question_ids=["Q9"]), "affected questions"),
        (lambda p, r: p["items"][0].update(action="repair_required"), "requires repair"),
        (lambda p, r: r.update(evidence_refs=[artifact_id(binding["proposal"])]), "omits"),
    ):
        altered, approval = deepcopy(proposal), deepcopy(review)
        mutate(altered, approval)
        write_json(root / binding["proposal"], altered)
        approval["proposal"] = dispositions.pin(root, binding["proposal"])
        write_json(root / binding["review"], approval)
        with pytest.raises(ValueError, match=reason):
            dispositions.verify_disposition(root, binding)
    write_json(root / binding["proposal"], proposal)
    write_json(root / binding["review"], review)
    result = dispositions.verify_disposition(root, binding)
    with pytest.raises(ValueError, match="exactly one"):
        dispositions.qualify_source(root, binding["source"], [binding, binding])
    with pytest.raises(ValueError, match="different problem frame"):
        dispositions.verify_disposition(root, binding, frame_path="framing/another.json")
    audit = read_json(root / binding["source"])
    audit["status"] = "FAIL"
    audit["issues"][0]["severity"] = "error"
    write_json(root / binding["source"], audit)
    with pytest.raises(ValueError, match="hash changed"):
        dispositions.verify_disposition(root, result["sources"])
    proposal["source"] = dispositions.pin(root, binding["source"])
    write_json(root / binding["proposal"], proposal)
    review["proposal"] = dispositions.pin(root, binding["proposal"])
    write_json(root / binding["review"], review)
    with pytest.raises(ValueError, match="errors require repair"):
        dispositions.verify_disposition(root, binding)


def test_proposed_disposition_cannot_pin_or_cite_unsupplied_evidence():
    proposal = read_json(Path(__file__).parents[1] / "fixtures/contracts/issue_disposition.json")
    path = "framing/disposition.json"
    task = {"task_id": "fixture", "actor_id": proposal["actor_id"], "question_id": None,
        "inputs": [{"artifact_id": "fixture-evidence", **proposal["source"]}, {"artifact_id": "fixture-frame", **proposal["frame"]}],
        "outputs": [{"path": path, "format": "json", "contract": "issue_disposition"}], "reviewed_actor_id": None}
    response = {"schema_version": "2.0", "task_id": "fixture", "actor_id": task["actor_id"], "status": "PRODUCED",
        "rationale": "Structural test only", "blockers": [], "evidence_refs": [],
        "artifacts": [{"path": path, "content": json.dumps(proposal)}]}
    assert _check_response(task, response)
    valid = deepcopy(proposal)
    proposal["items"][0]["evidence_refs"] = ["outside-inputs"]
    response["artifacts"][0]["content"] = json.dumps(proposal)
    with pytest.raises(ValueError, match="outside its input"):
        _check_response(task, response)
    proposal = valid
    proposal["source"]["sha256"] = "1" * 64
    response["artifacts"][0]["content"] = json.dumps(proposal)
    with pytest.raises(ValueError, match="actual supplied"):
        _check_response(task, response)
