from copy import deepcopy
from pathlib import Path
import stat
import sys

import pytest
from jsonschema import Draft202012Validator

from mathmode.evaluators import evaluate
from mathmode.io import read_json, write_json
from mathmode.runner import execute_model
from mathmode.schema_catalog import catalog
from mathmode.validation import independently_validate, audit_evidence, REQUIRED_METRICS
from mathmode.workspace import initialize

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def criteria_for(kind):
    metrics = sorted(REQUIRED_METRICS[kind])
    return {"schema_version": "2.0", "criteria_id": "fixture-criteria", "question_id": "Q1", "task_type": kind,
        "data_input_id": "data", "main_output_name": "predictions", "baseline_output_name": "predictions",
        "source_refs": ["fixture:analytic-construction"], "checks": [{"check_id": name, "metric": name,
            "operator": "le", "threshold": 0.0 if name in {"coverage_error", "split_leakage", "main_feasibility_error", "baseline_feasibility_error"} else 1e-8,
            "unit": "fixture-dimensionless", "source_ref": "fixture:analytic-construction"} for name in metrics],
        "symbol_dimensions": {key: {} for key in ("x", "y", "a", "b")},
        "robustness": {"status": "not_applicable", "reason": "Deterministic synthetic exact-case regression; robustness is tested in separate perturbed fixtures.", "required_metrics": []},
        "evaluation": {"sense": "min", "target": "observed_y" if kind in {"regression", "time_series"} else None,
                       "bootstrap_repetitions": 0, "confidence": 0.95}}


@pytest.fixture
def prepared(tmp_path, request):
    problem = tmp_path / "problem.txt"
    problem.write_text("Synthetic exact affine regression fixture", encoding="utf-8")
    data = tmp_path / "data.json"
    rows = [{"id": f"row{i}", "x": i, "observed_y": 2 * i + 1} for i in range(1, 6)]
    if getattr(request, "param", None) == "missing_unused_note":
        for row in rows:
            row["note"] = None
    write_json(data, {"rows": rows})
    criteria = tmp_path / "criteria.json"
    write_json(criteria, criteria_for("regression"))
    source = {"uri": "fixture://independent-validation", "accessed_at": "2026-09-08T00:00:00Z", "license": "Repository-authored synthetic fixture"}
    root = initialize("validation-fixture", [{"input_id": key, "path": str(path), "role": role, "source": source}
        for key, path, role in [("problem", problem, "problem"), ("data", data, "data"), ("criteria", criteria, "rule")]],
        destination=tmp_path / "workspace", kind="fixture")
    inputs = {item["input_id"]: item for item in read_json(root / "input_manifest.json")["files"]}
    (root / "code").mkdir()
    (root / "code/regression.py").write_bytes((FIXTURES / "validation/regression_solver.py").read_bytes())
    for method, file in [("affine-main", "main_spec.json"), ("mean-baseline", "baseline_spec.json")]:
        spec = read_json(FIXTURES / "contracts/model_spec.json")
        spec.update(method_id=method, inputs=["data", "criteria"],
            implementation={"entrypoint": "code/regression.py", "code_files": ["code/regression.py"], "language": "python"})
        spec["data_split"].update(train_ids=["row1", "row2", "row3"], fit_ids=["row1", "row2", "row3"], test_ids=["row4", "row5"])
        spec["outputs"] = [{"name": "predictions", "path": "predictions.json", "format": "json", "precision": 12,
            "fields": [{"name": "id", "type": "string", "unit": "identifier"}, {"name": "prediction", "type": "number", "unit": "1"}]}]
        spec["validation_plan"].update(checks=sorted(REQUIRED_METRICS["regression"]),
            criteria={"path": inputs["criteria"]["path"], "sha256": inputs["criteria"]["sha256"]})
        write_json(root / file, spec)
    yield root
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)


@pytest.fixture
def runs(prepared):
    main = execute_model(prepared, "main_spec.json", role="main", interpreter=sys.executable)
    baseline = execute_model(prepared, "baseline_spec.json", role="baseline", interpreter=sys.executable)
    return prepared, f"runs/{main['run_id']}/run_manifest.json", f"runs/{baseline['run_id']}/run_manifest.json"


def test_real_independent_computation_and_evidence(runs):
    root, main, baseline = runs
    summary = independently_validate(root, main, baseline, interpreter=sys.executable)
    assert summary["status"] == "PASS"
    assert summary["measurements"]["main_mse"] == 0
    assert summary["measurements"]["baseline_mse"] == 26
    child = root / summary["validator_workspace"]
    assert not any(path.name == "regression.py" for path in child.rglob("*.py"))
    relative = f"validations/{summary['validation_id']}/validation_summary.json"
    report = audit_evidence(root, relative)
    assert report["status"] == "PASS", report
    assert report["official_compliance"] == "NOT_RUN"
    for name in ("validation_criteria", "validation_summary", "evidence_gate"):
        Draft202012Validator.check_schema(catalog()[name])


def test_self_validation_is_rejected(runs):
    root, main, baseline = runs
    with pytest.raises(ValueError, match="producer"):
        independently_validate(root, main, baseline, actor_id="modeler")


def test_evidence_rejects_tampered_measurements(runs):
    root, main, baseline = runs
    summary = independently_validate(root, main, baseline, interpreter=sys.executable)
    relative = f"validations/{summary['validation_id']}/validation_summary.json"
    summary["measurements"]["baseline_mse"] = 999
    write_json(root / relative, summary)
    assert audit_evidence(root, relative)["status"] == "FAIL"


def test_evidence_detects_changed_upstream_after_validation(runs):
    root, main, baseline = runs
    summary = independently_validate(root, main, baseline, interpreter=sys.executable)
    (root / "code/regression.py").write_text("print('changed')", encoding="utf-8")
    report = audit_evidence(root, f"validations/{summary['validation_id']}/validation_summary.json")
    assert report["status"] == "FAIL"
    assert "stale" in report["blockers"][0]


def test_wrong_predictions_fail_independent_numbers(prepared):
    code = prepared / "code/regression.py"
    content = code.read_text(encoding="utf-8")
    code.write_text(content.replace("slope * rows[key]['x'] + intercept", "0") if "slope * rows[key]['x'] + intercept" in content else
                    content.replace('slope * rows[key]["x"] + intercept', '0.0'), encoding="utf-8")
    main = execute_model(prepared, "main_spec.json", role="main", interpreter=sys.executable)
    baseline = execute_model(prepared, "baseline_spec.json", role="baseline", interpreter=sys.executable)
    assert main["status"] == baseline["status"] == "PASS"  # valid files, wrong mathematics
    summary = independently_validate(prepared, f"runs/{main['run_id']}/run_manifest.json", f"runs/{baseline['run_id']}/run_manifest.json", interpreter=sys.executable)
    assert summary["status"] == "FAIL"
    assert summary["measurements"]["main_mse"] > 0
    assert audit_evidence(prepared, f"validations/{summary['validation_id']}/validation_summary.json")["status"] == "FAIL"


def test_small_linear_oracle_recomputes_feasibility_and_optimality():
    data = {"c": [-1, -1], "bounds": [[0, None], [0, None]], "A_ub": [[1, 1]], "b_ub": [3], "A_eq": [], "b_eq": []}
    criteria = criteria_for("optimization")
    metrics = evaluate(data, {"x": [1, 2], "objective": -3}, {"x": [0, 0], "objective": 0}, {}, criteria)
    assert metrics["optimality_gap"] == 0
    assert metrics["main_inequality_violation"] == 0
    invalid = evaluate(data, {"x": [2, 2], "objective": -3}, {"x": [0, 0], "objective": 0}, {}, criteria)
    assert invalid["main_inequality_violation"] == 1
    assert invalid["main_reported_objective_error"] == 1


def test_q5_frontier_adapter_recomputes_engineering_candidates():
    import hashlib
    import numpy as np
    rows = []
    labels = ["\u6b63\u5f26\u6ce2", "\u4e09\u89d2\u6ce2", "\u68af\u5f62\u6ce2"]
    for index, label in enumerate(labels):
        rows.append({"id": f"q5-{index}", "source_input": "C-INPUT-2", "row_number": index + 2,
                     "temperature": 25.0, "frequency": 50_000.0 + index,
                     "loss": 10.0 + index, "waveform_class": label, "material_class": 1,
                     "waveform": [0.1 * index, 0.2 + 0.1 * index, -0.1]})
    criteria = {"task_type": "optimization", "source_refs": ["engineering:q5-frontier"],
                "evaluation": {"sense": "max"}}
    spec = {"seed": 20240921, "parameters": {"n_estimators": 4,
            "min_samples_leaf": 1, "max_features": 1.0}}
    metrics = evaluate({"rows": rows}, [], [], spec, criteria)
    assert metrics["expected_frontier_count"] >= 1
    assert metrics["all_unique_design_count"] == 3
    assert metrics["coverage_error"] == 1
    def output_row(row):
        peak = max(abs(min(row["waveform"])), abs(max(row["waveform"])))
        return {"candidate_id": row["id"], "source_input": row["source_input"],
                "row_number": row["row_number"], "temperature": row["temperature"],
                "frequency": row["frequency"], "waveform_class": row["waveform_class"],
                "material_class": row["material_class"],
                "waveform_sha256": hashlib.sha256(np.asarray(row["waveform"], dtype=float).tobytes()).hexdigest(),
                "predicted_loss": 1.0, "peak_flux": peak,
                "energy_proxy": row["frequency"] * peak}
    main = [output_row(row) for row in rows]
    baseline = list(main)
    metrics = evaluate({"rows": rows}, main, baseline, spec, criteria)
    assert metrics["energy_proxy_max_abs_error"] == 0
    tampered = list(main)
    tampered[0] = {**tampered[0], "energy_proxy": tampered[0]["energy_proxy"] + 1}
    assert evaluate({"rows": rows}, tampered, baseline, spec, criteria)["energy_proxy_max_abs_error"] == 1
    rows[0]["waveform_class"] = "unknown"
    with pytest.raises(ValueError, match="Unknown waveform class"):
        evaluate({"rows": rows}, [], [], spec, criteria)


def test_q5_frontier_adapter_rejects_duplicate_candidate_ids():
    row = {"id": "duplicate", "source_input": "C-INPUT-2", "row_number": 2,
           "temperature": 25.0, "frequency": 50_000.0, "loss": 10.0,
           "waveform_class": "正弦波", "material_class": 1,
           "waveform": [0.0, 0.1, -0.1]}
    spec = {"seed": 20240921, "parameters": {"n_estimators": 4,
            "min_samples_leaf": 1, "max_features": 1.0}}
    criteria = {"task_type": "optimization", "source_refs": ["engineering:q5-frontier"],
                "evaluation": {"sense": "max"}}
    with pytest.raises(ValueError, match="duplicate candidate IDs"):
        evaluate({"rows": [row, dict(row)]}, [], [], spec, criteria)


def test_mechanism_conservation_is_independently_computed():
    import math
    data = {"initial_A": 10, "rate": 0.2, "times": [0, 1, 2]}
    rows = [{"time": t, "A": 10 * math.exp(-0.2 * t), "B": 10 - 10 * math.exp(-0.2 * t)} for t in data["times"]]
    metrics = evaluate(data, rows, rows, {}, criteria_for("mechanism"))
    assert metrics["main_mass_residual"] == 0
    changed = deepcopy(rows)
    changed[-1]["B"] += 1
    assert evaluate(data, changed, rows, {}, criteria_for("mechanism"))["main_mass_residual"] == 1


def test_graph_oracle_rejects_invented_edge_and_wrong_cost():
    data = {"nodes": ["A", "B", "C"], "edges": [{"from": "A", "to": "B", "weight": 1}, {"from": "B", "to": "C", "weight": 2}, {"from": "A", "to": "C", "weight": 5}], "start": "A", "end": "C"}
    main, baseline = {"path": ["A", "B", "C"], "cost": 3}, {"path": ["A", "C"], "cost": 5}
    assert evaluate(data, main, baseline, {}, criteria_for("graph"))["optimality_gap"] == 0
    main["cost"] = 1
    assert evaluate(data, main, baseline, {}, criteria_for("graph"))["main_reported_cost_error"] == 2
    data["edges"].pop(0)
    with pytest.raises(ValueError, match="nonexistent edge"):
        evaluate(data, main, baseline, {}, criteria_for("graph"))


def test_time_split_is_checked_against_actual_raw_rows():
    spec = read_json(FIXTURES / "contracts/model_spec.json")
    spec["data_split"].update(strategy="time", sample_times={"row1": "2026-01-01T00:00:00Z", "row2": "2026-01-02T00:00:00Z", "row3": "2026-01-03T00:00:00Z"})
    data = {"rows": [{"id": f"row{i}", "x": i, "observed_y": i, "time": f"2026-01-0{i}T00:00:00Z"} for i in (1, 2, 3)]}
    predictions = [{"id": "row3", "prediction": 3}]
    assert evaluate(data, predictions, predictions, spec, criteria_for("time_series"))["main_mse"] == 0
    data["rows"][0]["time"] = "2026-01-04T00:00:00Z"
    with pytest.raises(ValueError, match="chronological leakage"):
        evaluate(data, predictions, predictions, spec, criteria_for("time_series"))


def test_dimension_checker_catches_mismatches_and_does_not_execute_code():
    from mathmode.units import expression_dimensions, verify_formula_units
    symbols = {"distance": {"length": 1}, "time": {"time": 1}, "speed": {"length": 1, "time": -1}}
    assert expression_dimensions("distance/time", symbols) == symbols["speed"]
    with pytest.raises(ValueError, match="mismatch"):
        expression_dimensions("distance+time", symbols)
    with pytest.raises(ValueError, match="dimensionless"):
        expression_dimensions("exp(distance)", symbols)
    with pytest.raises(ValueError, match="Unsupported"):
        expression_dimensions("__import__('os').system('echo unsafe')", symbols)
    spec = {"variables": list(symbols), "formulae": [{"formula_id": "speed-law", "expression": "speed=distance/time", "output_symbol": "speed"}]}
    verify_formula_units(spec, symbols)
    spec["formulae"][0]["expression"] = "speed=distance*time"
    with pytest.raises(ValueError, match="unit mismatch"):
        verify_formula_units(spec, symbols)


def test_uncertainty_is_computed_from_holdout_samples():
    spec = read_json(FIXTURES / "contracts/model_spec.json")
    spec["data_split"]["test_ids"] = ["row3", "row4"]
    data = {"rows": [{"id": f"row{i}", "x": i, "observed_y": i} for i in range(1, 5)]}
    criteria = criteria_for("regression")
    criteria["evaluation"]["bootstrap_repetitions"] = 200
    predictions = [{"id": "row3", "prediction": 2}, {"id": "row4", "prediction": 2}]
    metrics = evaluate(data, predictions, predictions, spec, criteria)
    assert metrics["main_mse"] == 2.5
    assert metrics["mse_bootstrap_low"] <= 2.5 <= metrics["mse_bootstrap_high"]


def test_criteria_cannot_waive_coverage_or_required_robustness():
    from mathmode.validation import validate_criteria
    criteria = criteria_for("regression")
    criteria["checks"] = [check for check in criteria["checks"] if check["metric"] != "coverage_error"]
    with pytest.raises(ValueError, match="mandatory"):
        validate_criteria(criteria)
    criteria = criteria_for("regression")
    next(check for check in criteria["checks"] if check["metric"] == "coverage_error")["threshold"] = 1
    with pytest.raises(ValueError, match="nonzero"):
        validate_criteria(criteria)
    criteria = criteria_for("regression")
    criteria["robustness"]["status"] = "required"
    with pytest.raises(ValueError, match="explicit measured"):
        validate_criteria(criteria)


def test_unresolved_warning_blocks_evidence(prepared):
    code = prepared / "code/regression.py"
    code.write_text(code.read_text(encoding="utf-8") + "\nimport sys\nsys.stderr.write('Warning: unresolved fixture diagnostic\\n')\n", encoding="utf-8")
    main = execute_model(prepared, "main_spec.json", role="main", interpreter=sys.executable)
    baseline = execute_model(prepared, "baseline_spec.json", role="baseline", interpreter=sys.executable)
    summary = independently_validate(prepared, f"runs/{main['run_id']}/run_manifest.json", f"runs/{baseline['run_id']}/run_manifest.json", interpreter=sys.executable)
    assert summary["status"] == "PASS"
    report = audit_evidence(prepared, f"validations/{summary['validation_id']}/validation_summary.json")
    assert report["status"] == "FAIL"
    assert "Unresolved stderr" in report["blockers"][0]
