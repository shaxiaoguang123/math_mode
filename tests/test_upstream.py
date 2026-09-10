import sys

import pytest

from test_freeze import frozen, prepared, runs
from mathmode.freeze import freeze_results, thaw, verify_freeze
from mathmode.io import read_json, write_json, file_hash
from mathmode.runner import execute_model, verify_run
from mathmode.validation import independently_validate, audit_evidence, upstream_input_id


def compute_child(frozen):
    """Actually execute, independently validate and freeze Q2 from Q1's MSE."""
    root, parent, _, _ = frozen
    code = (root / "code/regression.py").read_text(encoding="utf-8")
    code = code.replace('predictions = [', 'prior = json.loads(Path(context["upstream"]["Q1"]).read_text(encoding="utf-8"))\noffset = prior["numbers"][0]["value"]\npredictions = [')
    code = code.replace('slope * rows[key]["x"] + intercept}', 'slope * rows[key]["x"] + intercept + offset}')
    (root / "code/child.py").write_text(code, encoding="utf-8")
    original_manifest = file_hash(root / "input_manifest.json")
    old_spec = read_json(root / "main_spec.json")
    criteria = read_json(root / old_spec["validation_plan"]["criteria"]["path"])
    criteria["question_id"] = "Q2"
    write_json(root / "child_criteria.json", criteria)
    executions = []
    for role, method in (("main", "affine-main"), ("baseline", "mean-baseline")):
        spec = read_json(root / "main_spec.json")
        spec.update(question_id="Q2", actor_id="child-modeler", method_id=method, inputs=["data"],
            upstream_freezes=[{"question_id": "Q1", "freeze_id": parent["freeze_id"]}],
            implementation={"entrypoint": "code/child.py", "code_files": ["code/child.py"], "language": "python"})
        spec["validation_plan"]["criteria"] = {"path": "child_criteria.json", "sha256": file_hash(root / "child_criteria.json")}
        spec_path = f"child_{role}_spec.json"
        write_json(root / spec_path, spec)
        run = execute_model(root, spec_path, role=role, interpreter=sys.executable)
        assert run["status"] == "PASS", run
        assert run["upstream_freezes"][0]["freeze_id"] == parent["freeze_id"]
        executions.append(f"runs/{run['run_id']}/run_manifest.json")
    assert file_hash(root / "input_manifest.json") == original_manifest
    summary = independently_validate(root, *executions, interpreter=sys.executable)
    assert summary["status"] == "PASS"
    child_validator = root / summary["validator_workspace"]
    validator_manifest = read_json(child_validator / "input_manifest.json")
    assert upstream_input_id("Q1") in {item["input_id"] for item in validator_manifest["files"]}
    summary_relative = f"validations/{summary['validation_id']}/validation_summary.json"
    evidence = audit_evidence(root, summary_relative)
    assert evidence["status"] == "PASS", evidence
    write_json(root / "child_evidence.json", evidence)
    request = {"schema_version": "2.0", "actor_id": "freeze-service", "question_id": "Q2", "decision_id": "decision1",
        "numbers": [{"frozen_number_id": "Q2-MSE", "claim_id": "Q2-fit", "source_path": summary_relative,
            "locator": "/measurements/main_mse", "unit": "fixture-dimensionless", "precision": 6}]}
    child_freeze = freeze_results(root, request, "child_evidence.json")
    assert verify_freeze(root, "Q2")["freeze_id"] == child_freeze["freeze_id"]
    return root, child_freeze, executions


def test_two_question_freeze_dependency_is_consumed_and_invalidated(frozen):
    root, child_freeze, executions = compute_child(frozen)
    outcome = thaw(root, "Q1", actor_id="orchestrator", reason="Revise upstream model")
    assert child_freeze["registry_artifact_id"] in outcome["affected"]
    with pytest.raises(ValueError, match="active"):
        verify_run(root, executions[0])
    with pytest.raises(ValueError, match="stale"):
        verify_freeze(root, "Q2")
