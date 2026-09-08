"""Actual perturbation runs and validators; role judgments remain explicit doubles."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

from test_validation import prepared
from test_workflow import case, review
from mathmode import assessments
from mathmode.contracts import read_ledger, validate
from mathmode.dispositions import pin
from mathmode.freeze import verify_freeze
from mathmode.io import file_hash, now, read_json, write_json


def double_handoffs(monkeypatch):
    def load(root, path, name):
        if name == "assumption_ledger":
            return read_ledger(root / path)[-1]
        return validate(name, read_json(root / path), root=root)
    monkeypatch.setattr(assessments, "_contract", load)


def measured_plan(root, *, limit=1e-8):
    ledger = read_json(Path(__file__).parents[1] / "fixtures/contracts/assumption_ledger.json")
    ledger.update(status="accepted", sensitivity_status="tested")
    write_json(root / "framing/assumptions.jsonl", ledger)
    code = root / "code/regression.py"
    content = code.read_text(encoding="utf-8").replace("import argparse", "import argparse\nimport random")
    content = content.replace('slope * rows[key]["x"] + intercept}',
        'slope * rows[key]["x"] + intercept + spec["parameters"].get("offset", 0) + spec["parameters"].get("jitter", 0)*random.random()}')
    code.write_text(content, encoding="utf-8")
    spec = read_json(root / "main_spec.json")
    spec["parameters"].update(offset=0, jitter=1e-6)
    write_json(root / "main_spec.json", spec)
    return {"schema_version": "2.0", "plan_id": "measured-assumptions", "question_id": "Q1", "actor_id": "fixture-independent-planner",
        "created_at": now(), "ledger": pin(root, "framing/assumptions.jsonl"),
        "models": {role: pin(root, role + "_spec.json") for role in ("main", "baseline")},
        "assumptions": [{"assumption_id": "linearity", "mode": "sensitivity", "rationale": "Measure this synthetic model's small offset and random-seed perturbations.",
            "scenario_ids": ["offset", "seed"]}], "scenarios": [
            {"scenario_id": name, "field": field, "parameter": parameter, "value": value,
             "rationale": "Predeclared engineering perturbation with an independent held-out metric.",
             "metrics": [{"metric": "main_mse", "unit": "fixture-dimensionless", "max_absolute_change": limit}]}
            for name, field, parameter, value in [("offset", "parameter", "offset", 1e-5), ("seed", "seed", None, 7)]]}


@pytest.mark.parametrize("limit,expected", [(1e-8, "PASS"), (1e-12, "FAIL")])
def test_actual_parameter_and_seed_perturbations_are_independently_measured(prepared, monkeypatch, capsys, limit, expected):
    root = prepared
    plan = measured_plan(root, limit=limit)
    path = "reviews/assumptions.json"
    write_json(root / path, plan)
    with pytest.raises(ValueError, match="handoff"):
        assessments.assess_assumptions(root, path)
    double_handoffs(monkeypatch)
    report = assessments.assess_assumptions(root, path, interpreter=sys.executable)
    assert report["status"] == expected, report
    assert len(report["experiments"]) == 3 and len(report["checks"]) == 2
    checks = {check["scenario_id"]: check for check in report["checks"]}
    assert checks["offset"]["absolute_change"] > 1e-11
    assert 0 < checks["seed"]["absolute_change"] < 1e-11
    assert report["assessments"][0]["status"] == ("TESTED" if expected == "PASS" else "FAILED")
    report_path = assessments.report_path(plan)
    assert assessments.verify_assessment(root, report_path) == report
    from mathmode.__main__ import main
    assert main(["verify-assumptions", "--workspace", str(root), "--assessment", report_path]) == (0 if expected == "PASS" else 1)
    assert '"scope": "declared_assumption_checks"' in capsys.readouterr().out
    for experiment in report["experiments"]:
        run = read_json(root / experiment["main_run"]["path"])
        assert any(item["contract"] == "assumption_plan" and item["sha256"] == file_hash(root / path) for item in run["contract_snapshots"])
        validation = read_json(root / experiment["validation"]["path"])
        assert not list((root / validation["validator_workspace"]).rglob("regression.py"))
    if expected == "FAIL":
        with pytest.raises(ValueError, match="passing assumption"):
            assessments.bind_assessment_reports(root, [pin(root, report_path)], "Q1")
    else:
        other_models = deepcopy(plan["models"])
        other_models["main"] = other_models["baseline"]
        with pytest.raises(ValueError, match="different production models"):
            assessments.bind_assessment_reports(root, [pin(root, report_path)], "Q1", model_pins=other_models)
    monkeypatch.setattr(assessments, "execute_model", lambda *a, **k: pytest.fail("Resume must reuse existing executions"))
    assert assessments.assess_assumptions(root, path) == report
    tampered = deepcopy(report)
    tampered["checks"][0]["absolute_change"] = 999
    write_json(root / report_path, tampered)
    with pytest.raises(ValueError, match="recomputed"):
        assessments.verify_assessment(root, report_path)
    write_json(root / report_path, report)
    mismatched = deepcopy(report)
    mismatched["experiments"][1]["baseline_run"] = mismatched["experiments"][1]["main_run"]
    write_json(root / report_path, mismatched)
    with pytest.raises(ValueError, match="fixed control baseline"):
        assessments.verify_assessment(root, report_path)
    write_json(root / report_path, report)
    altered = deepcopy(plan)
    altered["scenarios"][0]["metrics"][0]["max_absolute_change"] = 100
    write_json(root / path, altered)
    with pytest.raises(ValueError, match="hash changed"):
        assessments.verify_assessment(root, report_path)


def test_workflow_requires_actual_assumption_report_and_freeze_binds_it(case):
    root, service, plan = case
    job = plan["questions"][0]
    actual = read_json(root / job["assumption_plan"])
    actual.update(plan_id="workflow-measured-assumptions", scenarios=[{"scenario_id": "alternate-seed", "field": "seed", "parameter": None,
        "value": 8, "rationale": "Check deterministic synthetic predictions with another seed.",
        "metrics": [{"metric": "main_mse", "unit": "fixture-dimensionless", "max_absolute_change": 0}]}])
    actual["assumptions"][0].update(mode="sensitivity", scenario_ids=["alternate-seed"])
    job["assumption_plan"] = "reviews/workflow-measured-assumptions.json"
    write_json(root / job["assumption_plan"], actual)
    for action in ("run-main", "run-baseline", "independent-validate"):
        assert service.advance(plan, interpreter=sys.executable)["performed"]["action"] == action
    result = service.observe(plan)
    assert result["questions"]["Q1"]["next_action"] == "assess-assumptions"
    assert result["gates"]["G5"]["status"] == "BLOCKED"
    result = service.advance(plan, interpreter=sys.executable)
    assert result["performed"]["action"] == "assess-assumptions"
    assert result["questions"]["Q1"]["next_action"] == "review-validation"
    progress = read_json(root / "workflow_progress.json")["questions"]["Q1"]
    spec = read_json(root / job["main_spec"])
    required = [job["main_spec"], job["baseline_spec"], progress["validation"], progress["evidence"], spec["validation_plan"]["criteria"]["path"],
                job["assumption_plan"], assessments.report_path(actual)]
    review(root, job["validation_review"], spec["actor_id"], required)
    assert service.advance(plan)["performed"]["action"] == "freeze"
    frozen = verify_freeze(root, "Q1")
    assert frozen["assumption_reports"] == [pin(root, assessments.report_path(actual))]
    report = read_json(root / assessments.report_path(actual))
    report["assessments"][0]["rationale"] = "Changed after freeze"
    write_json(root / assessments.report_path(actual), report)
    with pytest.raises(ValueError, match="stale"):
        verify_freeze(root, "Q1")


def test_tested_flag_cannot_replace_evidence_and_plan_rejects_invalid_waivers(case):
    root, service, plan = case
    job = plan["questions"][0]
    plan_without_evidence = deepcopy(plan)
    plan_without_evidence["questions"][0].pop("assumption_plan")
    ledger = read_ledger(root / plan["framing"]["assumption_ledger"])[-1]
    ledger["sensitivity_status"] = "tested"
    write_json(root / plan["framing"]["assumption_ledger"], ledger)
    with pytest.raises(ValueError, match="actual evidence"):
        service._assumptions(plan_without_evidence, plan_without_evidence["questions"][0],
                            read_json(root / job["method_card"]), read_ledger(root / job["decision"], "method_decision")[-1])
    study = read_json(root / job["assumption_plan"])
    study["assumptions"][0]["mode"] = "sensitivity"
    with pytest.raises(ValueError, match="needs scenarios"):
        validate("assumption_plan", study)


def test_interrupted_validation_and_report_publication_adopt_actual_completed_work(prepared, monkeypatch):
    root = prepared
    plan = measured_plan(root)
    path = "reviews/assumptions.json"
    write_json(root / path, plan)
    double_handoffs(monkeypatch)
    real_validate = assessments.independently_validate
    def interrupted_after_real_validation(*args, **kwargs):
        real_validate(*args, **kwargs)
        raise OSError("Synthetic interruption after actual summary publication")
    with monkeypatch.context() as interrupted:
        interrupted.setattr(assessments, "independently_validate", interrupted_after_real_validation)
        with pytest.raises(OSError, match="actual summary"):
            assessments.assess_assumptions(root, path, interpreter=sys.executable)
    run_count = len(list((root / "runs").glob("*/run_manifest.json")))
    from mathmode.lineage import ArtifactRegistry
    register = ArtifactRegistry.register
    def interrupted_register(self, relative, **kwargs):
        if relative.endswith("/assumption_report.json"):
            raise OSError("Synthetic interruption before report registration")
        return register(self, relative, **kwargs)
    with monkeypatch.context() as interrupted:
        interrupted.setattr(ArtifactRegistry, "register", interrupted_register)
        with pytest.raises(OSError, match="report registration"):
            assessments.assess_assumptions(root, path, interpreter=sys.executable)
    saved = (root / assessments.report_path(plan)).read_bytes()
    validations = len(list((root / "validations").glob("*/validation_summary.json")))
    monkeypatch.setattr(assessments, "execute_model", lambda *a, **k: pytest.fail("Already completed model run repeated"))
    monkeypatch.setattr(assessments, "independently_validate", lambda *a, **k: pytest.fail("Already completed validation repeated"))
    assert assessments.assess_assumptions(root, path)["status"] == "PASS"
    assert (root / assessments.report_path(plan)).read_bytes() == saved
    assert len(list((root / "runs").glob("*/run_manifest.json"))) == run_count
    assert len(list((root / "validations").glob("*/validation_summary.json"))) == validations


def test_unfinished_validation_request_is_not_silently_retried(prepared, monkeypatch):
    root = prepared
    plan = measured_plan(root)
    plan["scenarios"] = plan["scenarios"][:1]
    plan["assumptions"][0]["scenario_ids"] = ["offset"]
    write_json(root / "reviews/assumptions.json", plan)
    double_handoffs(monkeypatch)
    calls = []
    def interrupted(*args, **kwargs):
        calls.append("requested")
        raise OSError("Synthetic uncompleted validator request")
    monkeypatch.setattr(assessments, "independently_validate", interrupted)
    with pytest.raises(OSError, match="uncompleted"):
        assessments.assess_assumptions(root, "reviews/assumptions.json", interpreter=sys.executable)
    with pytest.raises(ValueError, match="no completed summary"):
        assessments.assess_assumptions(root, "reviews/assumptions.json", interpreter=sys.executable)
    assert calls == ["requested"]
    assert not (root / assessments.report_path(plan)).exists()


def test_invalid_independent_plan_fails_before_experiment_dispatch(prepared, monkeypatch):
    root = prepared
    original = measured_plan(root)
    double_handoffs(monkeypatch)
    for mutate, reason in (
        (lambda p: p.update(actor_id="modeler"), "independent reviewer"),
        (lambda p: p["scenarios"][0].update(parameter="unknown"), "existing parameter"),
        (lambda p: p["scenarios"][1].update(value=42), "must change"),
        (lambda p: p["scenarios"][0]["metrics"][0].update(unit="wrong-unit"), "metric/unit"),
        (lambda p: p["scenarios"][1].update(field="parameter", parameter="offset", value=1e-5), "Duplicate perturbations"),
    ):
        plan = deepcopy(original)
        mutate(plan)
        write_json(root / "reviews/assumptions.json", plan)
        with pytest.raises(ValueError, match=reason):
            assessments.assess_assumptions(root, "reviews/assumptions.json")
    assert not (root / "runs").exists()
