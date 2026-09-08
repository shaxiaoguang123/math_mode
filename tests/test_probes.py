from copy import deepcopy
import sys

import pytest

from test_runner import workspace
from mathmode.io import read_json, write_json, file_hash
from mathmode.runner import execute_model
from mathmode.probes import measured_probe, verify_probe, fallback_triggered


def setup_probe(root):
    code = root / "code/compute.py"
    code.write_text(code.read_text(encoding="utf-8") + '''
import statistics
result.update(input_count=len(inputs["values"]), negative_count=sum(v < 0 for v in inputs["values"]),
    variance=statistics.pvariance(inputs["values"]),
    perturbation_change=abs(sum(v+0.01 for v in inputs["values"])-sum(inputs["values"])))
path.write_text(json.dumps(result), encoding="utf-8")
''', encoding="utf-8")
    checks = []
    for category, metric, output, locator, operator, threshold in [
        ("executability", "returncode", "runtime", "/returncode", "eq", 0),
        ("coverage", "input_count", "result", "/input_count", "eq", 3),
        ("assumptions", "negative_count", "result", "/negative_count", "eq", 0),
        ("degeneracy", "variance", "result", "/variance", "ge", 1),
        ("perturbation", "aggregate_change", "result", "/perturbation_change", "le", 0.1),
        ("scale", "duration", "runtime", "/duration_seconds", "le", 30),
    ]:
        checks.append({"category": category, "not_applicable_reason": None,
            "measurements": [{"metric": metric, "output_name": output, "locator": locator, "operator": operator, "threshold": threshold}],
            "reason": "Predeclared aggregate-computation fixture check, not a contest modeling claim."})
    plan = {"schema_version": "2.0", "question_id": "Q1", "method_id": "affine-main", "actor_id": "probe-fixture", "checks": checks}
    write_json(root / "probe_plan.json", plan)
    spec = read_json(root / "model_spec.json")
    spec["validation_plan"]["probe"] = {"path": "probe_plan.json", "sha256": file_hash(root / "probe_plan.json")}
    write_json(root / "model_spec.json", spec)
    return plan


def test_probe_verdict_comes_from_actual_measurements_and_pinned_plan(workspace):
    setup_probe(workspace)
    manifest_before = file_hash(workspace / "input_manifest.json")
    run = execute_model(workspace, "model_spec.json", role="probe", interpreter=sys.executable)
    relative = f"runs/{run['run_id']}/run_manifest.json"
    report = measured_probe(workspace, relative)
    assert report["verdict"] == "PASS"
    assert file_hash(workspace / "input_manifest.json") == manifest_before
    assert next(check for check in report["checks"] if check["category"] == "coverage")["metrics"]["input_count"] == 3
    write_json(workspace / "risk_probe.json", report)
    verify_probe(workspace, "risk_probe.json", relative)
    report["checks"][0]["metrics"]["returncode"] = 999
    write_json(workspace / "risk_probe.json", report)
    with pytest.raises(ValueError, match="differs"):
        verify_probe(workspace, "risk_probe.json", relative)


def test_probe_cannot_change_threshold_after_execution(workspace):
    plan = setup_probe(workspace)
    run = execute_model(workspace, "model_spec.json", role="probe", interpreter=sys.executable)
    plan["checks"][1]["measurements"][0]["threshold"] = 999
    write_json(workspace / "probe_plan.json", plan)
    with pytest.raises(ValueError, match="stale"):
        measured_probe(workspace, f"runs/{run['run_id']}/run_manifest.json")


def test_fallback_trigger_uses_an_executed_qualified_metric(workspace):
    from pathlib import Path
    setup_probe(workspace)
    run = execute_model(workspace, "model_spec.json", role="probe", interpreter=sys.executable)
    report = measured_probe(workspace, f"runs/{run['run_id']}/run_manifest.json")
    card = read_json(Path(__file__).resolve().parents[1] / "fixtures/contracts/method_card.json")
    fallback = deepcopy(card["methods"][0])
    fallback.update(method_id="fallback", role="conditional_fallback", fallback_trigger={"metric": "degeneracy.variance", "operator": "lt", "threshold": 0.1})
    card["methods"].append(fallback)
    assert not fallback_triggered(card, report)["triggered"]
    fallback["fallback_trigger"]["threshold"] = 100
    assert fallback_triggered(card, report)["triggered"]


@pytest.mark.parametrize("threshold,allowed", [(100, True), (0.1, False)])
def test_fallback_executes_only_after_predeclared_measured_trigger(workspace, threshold, allowed):
    from pathlib import Path
    from mathmode.runner import verify_run
    setup_probe(workspace)
    card = read_json(Path(__file__).resolve().parents[1] / "fixtures/contracts/method_card.json")
    fallback = deepcopy(card["methods"][0])
    fallback.update(method_id="fallback", role="conditional_fallback",
                    fallback_trigger={"metric": "degeneracy.variance", "operator": "lt", "threshold": threshold})
    card["methods"].append(fallback)
    write_json(workspace / "screening.json", card)
    spec = read_json(workspace / "model_spec.json")
    spec["validation_plan"]["screening_card"] = {"path": "screening.json", "sha256": file_hash(workspace / "screening.json")}
    write_json(workspace / "model_spec.json", spec)
    run = execute_model(workspace, "model_spec.json", role="probe", interpreter=sys.executable)
    relative = f"runs/{run['run_id']}/run_manifest.json"
    write_json(workspace / "probe_report.json", measured_probe(workspace, relative))
    spec["method_id"] = "fallback"
    spec["validation_plan"].pop("probe")
    spec["validation_plan"].pop("screening_card")
    spec["fallback_authorization"] = {field: {"path": path, "sha256": file_hash(workspace / path)}
        for field, path in (("card", "screening.json"), ("probe_report", "probe_report.json"), ("probe_run", relative))}
    write_json(workspace / "fallback_spec.json", spec)
    if not allowed:
        with pytest.raises(ValueError, match="inactive"):
            execute_model(workspace, "fallback_spec.json", role="fallback", interpreter=sys.executable)
        return
    outcome = execute_model(workspace, "fallback_spec.json", role="fallback", interpreter=sys.executable)
    assert outcome["status"] == "PASS", outcome
    manifest = f"runs/{outcome['run_id']}/run_manifest.json"
    assert verify_run(workspace, manifest)["role"] == "fallback"
    report = read_json(workspace / "probe_report.json")
    report["checks"][0]["metrics"]["returncode"] = 10
    write_json(workspace / "probe_report.json", report)
    with pytest.raises(ValueError, match="stale|hash changed"):
        verify_run(workspace, manifest)
