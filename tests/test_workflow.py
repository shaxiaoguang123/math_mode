from copy import deepcopy
from pathlib import Path
import sys

import pytest

from test_validation import prepared
from mathmode.contracts import validate, read_ledger
from mathmode.io import read_json, write_json, file_hash, now
from mathmode.lineage import artifact_id
from mathmode.probes import measured_probe
from mathmode.runner import execute_model
from mathmode.workflow import Workflow
from mathmode.freeze import thaw
from mathmode.state import workspace_lock

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/contracts"


def review(root, path, producer, required):
    write_json(root / path, {"schema_version": "2.0", "review_id": "fixture-review", "actor_id": "fixture-independent-reviewer",
        "reviewed_actor_id": producer, "question_id": "Q1", "artifact_refs": [artifact_id(p) for p in sorted(set(required))],
        "findings": [], "verdict": "SUPPORTED", "limitations": [], "created_at": now()})


@pytest.fixture
def case(prepared, monkeypatch):
    """Actual numerical lifecycle; authored semantic reviews are explicit test doubles."""
    root = prepared
    service = Workflow(root)
    service.agents.prepare_inputs()
    spec = read_json(root / "main_spec.json")
    framing = {name: f"framing/{name}.json" for name in ("problem_frame", "problem_dag", "symbol_table", "ambiguity_register")}
    framing.update(assumption_ledger="framing/assumptions.jsonl", review="reviews/framing.json")
    question = {"question_id": "Q1", "title": "Synthetic affine holdout prediction", "task_type": spec["task_type"],
        "inputs": spec["inputs"], "outputs": spec["outputs"], "constraints": spec["constraints"], "source_refs": ["problem:1"],
        "resources": spec["limits"], "objective": {"description": "Evaluate a synthetic affine model", **{key: spec["objective"][key] for key in ("metric", "sense")}}}
    write_json(root / framing["problem_frame"], {"schema_version": "2.0", "case_id": "validation-fixture", "producer": "fixture-framer",
        "source_refs": ["problem"], "data_audit_ref": artifact_id("framing/deterministic_data_audit.json"), "questions": [question]})
    for name in ("problem_dag", "symbol_table", "ambiguity_register"):
        write_json(root / framing[name], read_json(FIXTURES / f"{name}.json"))
    assumption = read_json(FIXTURES / "assumption_ledger.json")
    assumption["status"] = "accepted"
    write_json(root / framing["assumption_ledger"], assumption)
    review(root, framing["review"], "fixture-framer", [framing[name] for name in framing if name != "review"] + ["framing/deterministic_data_audit.json"])
    card = read_json(FIXTURES / "method_card.json")
    for method in card["methods"]:
        method["outputs"] = ["predictions"]
    write_json(root / "methods/card.json", card)
    # A real six-category probe executes before the decision and production runs.
    code = '''import json,sys,statistics
from pathlib import Path
c=json.loads(Path(sys.argv[sys.argv.index('--context')+1]).read_text())
rows=json.loads(Path(c['inputs']['data']).read_text())['rows']
x=[row['x'] for row in rows]
out={'count':len(x),'minimum':min(x),'variance':statistics.pvariance(x),
     'perturbation':max(abs((2*(v+0.01)+1)-(2*v+1)) for v in x)}
(Path(c['output_dir'])/'probe.json').write_text(json.dumps(out))
'''
    (root / "probes").mkdir()
    (root / "probes/measure.py").write_text(code, encoding="utf-8")
    measurements = [("executability", "runtime", "/returncode", "eq", 0), ("coverage", "diagnostics", "/count", "eq", 5),
        ("assumptions", "diagnostics", "/minimum", "ge", 1), ("degeneracy", "diagnostics", "/variance", "ge", 1),
        ("perturbation", "diagnostics", "/perturbation", "le", 0.021), ("scale", "runtime", "/duration_seconds", "le", 30)]
    probe_plan = {"schema_version": "2.0", "question_id": "Q1", "method_id": "affine-main", "actor_id": "fixture-probe",
        "checks": [{"category": category, "not_applicable_reason": None, "reason": "Synthetic exact-case measured diagnostic",
            "measurements": [{"metric": category, "output_name": output, "locator": locator, "operator": operator, "threshold": threshold}]}
            for category, output, locator, operator, threshold in measurements]}
    write_json(root / "probes/plan.json", probe_plan)
    probe_spec = deepcopy(spec)
    probe_spec.update(implementation={"entrypoint": "probes/measure.py", "code_files": ["probes/measure.py"], "language": "python"},
        outputs=[{"name": "diagnostics", "path": "probe.json", "format": "json", "precision": 12,
                  "fields": [{"name": "count", "type": "integer", "unit": "1"}]}])
    probe_spec["validation_plan"].update(probe={"path": "probes/plan.json", "sha256": file_hash(root / "probes/plan.json")},
        screening_card={"path": "methods/card.json", "sha256": file_hash(root / "methods/card.json")})
    write_json(root / "probes/spec.json", probe_spec)
    run = execute_model(root, "probes/spec.json", role="probe", interpreter=sys.executable)
    write_json(root / "probes/report.json", measured_probe(root, f"runs/{run['run_id']}/run_manifest.json"))
    decision = read_json(FIXTURES / "method_decision.json")
    decision.update(evidence_refs=[artifact_id("probes/report.json")], decided_at=now())
    write_json(root / "decisions/decision.jsonl", decision)
    review(root, "reviews/code.json", spec["actor_id"], ["main_spec.json", "baseline_spec.json", "code/regression.py", spec["validation_plan"]["criteria"]["path"]])
    plan = read_json(FIXTURES.parent / "agents/workflow_plan.json")
    assert plan["framing"] == framing
    # Only role provenance is doubled. All schemas, cross-file guards, executions,
    # independent metrics, stale checks and freeze operations are real.
    def fixture_contract(path, name):
        if name in {"method_decision", "assumption_ledger"}:
            return read_ledger(root / path, name)[-1]
        return validate(name, read_json(root / path), root=root)
    monkeypatch.setattr(service, "_contract", fixture_contract)
    return root, service, plan


def test_real_lifecycle_stops_for_semantic_review_then_freezes(case, monkeypatch):
    root, service, plan = case
    assert Workflow(root).observe(plan)["gates"]["G2"]["status"] == "BLOCKED", "Authored fixture files cannot replace a real reasoning handoff"
    first = service.observe(plan)
    assert first["gates"]["G2"]["status"] == "PASS", first
    assert first["gates"]["G0"]["status"] == "BLOCKED"
    assert first["questions"]["Q1"]["next_action"] == "run-main", first
    for expected in ("run-main", "run-baseline", "independent-validate"):
        result = service.advance(plan, interpreter=sys.executable)
        assert result["performed"] == {"question_id": "Q1", "action": expected}, result
    assert result["questions"]["Q1"]["next_action"] == "review-validation"
    assert result["gates"]["G5"]["status"] == "BLOCKED"
    assert service.advance(plan)["performed"] is None
    progress = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    summary = read_json(root / progress["validation"])
    assert summary["measurements"]["main_mse"] == 0
    assert summary["measurements"]["baseline_mse"] == 26
    captured = []
    original_advance = service.agents.advance
    service.agents.backend = object()
    def capture_schedule(schedule):
        captured.append(schedule)
        return {"status": "BLOCKED", "executed": [], "blocked": {"fixture": ["No actual reasoning performed by this capture"]}}
    monkeypatch.setattr(service.agents, "advance", capture_schedule)
    assert service.advance(plan)["performed"] is None
    inputs = captured[0]["tasks"][0]["inputs"]
    assert "code/regression.py" not in inputs
    assert {"main_spec.json", "baseline_spec.json", progress["validation"], progress["evidence"]} <= set(inputs)
    assert captured[0]["tasks"][0]["reviewed_actor_id"] == "modeler"
    service.agents.backend = None
    monkeypatch.setattr(service.agents, "advance", original_advance)
    # Losing only the workflow pointer must not repeat completed numerical work.
    run_count = len(list((root / "runs").glob("*/run_manifest.json")))
    validation_count = len(list((root / "validations").glob("*/validation_summary.json")))
    (root / "workflow_progress.json").unlink()
    for action in ("adopt-main", "adopt-baseline", "adopt-validation"):
        assert service.advance(plan)["performed"]["action"] == action
    assert len(list((root / "runs").glob("*/run_manifest.json"))) == run_count
    assert len(list((root / "validations").glob("*/validation_summary.json"))) == validation_count
    spec = read_json(root / "main_spec.json")
    review(root, "reviews/validation.json", spec["actor_id"], [progress["validation"], progress["evidence"],
        "main_spec.json", "baseline_spec.json", spec["validation_plan"]["criteria"]["path"]])
    result = service.advance(plan, interpreter=sys.executable)
    assert result["performed"]["action"] == "freeze", result
    assert result["gates"]["G6"]["status"] == "PASS"
    assert result["gates"]["G7"]["status"] == "BLOCKED"
    assert result["official_compliance"] == "BLOCKED"
    before = len(list((root / "runs").glob("*/run_manifest.json")))
    assert service.advance(plan)["performed"] is None
    assert len(list((root / "runs").glob("*/run_manifest.json"))) == before
    changed_plan = deepcopy(plan)
    changed_plan["questions"][0]["frozen_numbers"][0]["claim_id"] = "different-claim"
    assert service.observe(changed_plan)["gates"]["G6"]["status"] == "BLOCKED"
    # Unchanged bytes still require actual new executions after an explicit thaw.
    thaw(root, "Q1", actor_id="fixture-host", reason="Exercise a fresh independent verification cycle")
    assert service.observe(plan)["questions"]["Q1"]["next_action"] == "run-main"
    assert service.advance(plan)["performed"] is None
    repaired = execute_model(root, "main_spec.json", role="main", interpreter=sys.executable)
    result = service.advance(plan)
    assert result["performed"]["action"] == "adopt-main"
    changed_progress = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    assert repaired["run_id"] in changed_progress["main_run"]
    assert changed_progress["validation"] is changed_progress["evidence"] is None
    assert result["questions"]["Q1"]["next_action"] == "run-baseline"
    execute_model(root, "baseline_spec.json", role="baseline", interpreter=sys.executable)
    assert service.advance(plan)["performed"]["action"] == "adopt-baseline"
    assert service.advance(plan, interpreter=sys.executable)["performed"]["action"] == "independent-validate"
    assert service.observe(plan)["questions"]["Q1"]["next_action"] == "review-validation"
    # A structurally valid review of old run-specific evidence cannot prevent a
    # new review after repair/refreeze, even if the model-spec bytes are unchanged.
    captured.clear()
    service.agents.backend = object()
    monkeypatch.setattr(service.agents, "advance", capture_schedule)
    assert service.advance(plan)["performed"] is None
    updated = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    assert updated["validation"] in captured[0]["tasks"][0]["inputs"]
    service.agents.backend = None
    monkeypatch.setattr(service.agents, "advance", original_advance)
    (root / "code/regression.py").write_text("print('canonical source changed')", encoding="utf-8")
    assert service.observe(plan)["gates"]["G4"]["status"] == "BLOCKED"


def test_model_spec_cannot_change_the_framed_question(case):
    root, service, plan = case
    spec = read_json(root / "main_spec.json")
    spec["objective"]["metric"] = "unapproved-metric"
    write_json(root / "main_spec.json", spec)
    result = service.advance(plan)
    assert result["performed"] is None
    assert "objective differs" in result["questions"]["Q1"]["gates"]["G4"]["blockers"][0]


def test_different_baseline_author_requires_separate_review(case):
    root, service, plan = case
    baseline = read_json(root / "baseline_spec.json")
    baseline["actor_id"] = "baseline-producer"
    write_json(root / "baseline_spec.json", baseline)
    result = service.observe(plan)
    assert "own independent code review" in result["questions"]["Q1"]["gates"]["G4"]["blockers"][0]
    path = "reviews/baseline-code.json"
    plan["questions"][0]["baseline_code_review"] = path
    review(root, path, baseline["actor_id"], ["baseline_spec.json", "code/regression.py", baseline["validation_plan"]["criteria"]["path"]])
    assert service.observe(plan)["questions"]["Q1"]["next_action"] == "run-main"


def test_missing_probe_report_is_recomputed_from_existing_execution(case):
    root, service, plan = case
    plan["questions"][0]["probe_specs"] = ["probes/spec.json"]
    (root / "probes/report.json").unlink()
    before = len(list((root / "runs").glob("*/run_manifest.json")))
    result = service.advance(plan, interpreter=sys.executable)
    assert result["performed"]["action"] == "adopt-probe"
    assert len(list((root / "runs").glob("*/run_manifest.json"))) == before
    assert read_json(root / "probes/report.json")["verdict"] == "PASS"


def test_workflow_advancement_serializes_the_entire_transition(tmp_path, monkeypatch):
    service = Workflow(tmp_path)
    calls = []
    def transition(plan, *, interpreter):
        # Nested state mutations remain available, but another coordinator cannot enter.
        with workspace_lock(tmp_path):
            calls.append("state-written")
        with pytest.raises(ValueError, match="Workspace is locked"):
            Workflow(tmp_path).advance(plan)
        raise RuntimeError("Simulated transition failure")
    monkeypatch.setattr(service, "_advance", transition)
    with pytest.raises(RuntimeError, match="Simulated transition failure"):
        service.advance({})
    assert calls == ["state-written"]
    assert not (tmp_path / ".workflow.advance.lock").exists()
    with workspace_lock(tmp_path, scope="workflow"):
        with pytest.raises(ValueError, match="Workspace is locked"):
            service.advance({})
