"""Independent recomputation service and deterministic evidence gate."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import uuid

from .contracts import validate, unique
from .io import file_hash, now, read_json, safe_path, write_json, canonical_root, object_hash
from .runner import execute_model, verify_run
from .workspace import initialize
from .units import verify_formula_units

REQUIRED_METRICS = {
    "regression": {"main_mse", "coverage_error", "split_leakage"},
    "time_series": {"main_mse", "coverage_error", "split_leakage"},
    "optimization": {"main_inequality_violation", "main_equality_residual", "main_reported_objective_error",
        "baseline_inequality_violation", "baseline_equality_residual", "baseline_reported_objective_error", "optimality_gap"},
    "mechanism": {"main_analytic_error", "main_mass_residual", "main_negativity", "baseline_mass_residual", "baseline_negativity"},
    "graph": {"main_feasibility_error", "baseline_feasibility_error", "main_reported_cost_error", "baseline_reported_cost_error", "optimality_gap"},
}


def upstream_input_id(question_id):
    return "upstream-" + object_hash(question_id)[:16]


def verify_evidence_report(root: Path, report_relative: str) -> dict:
    root = canonical_root(root)
    actual = validate("evidence_gate", read_json(safe_path(root, report_relative)), root=root)
    fresh = audit_evidence(root, actual["validation"]["path"])
    if fresh["status"] != "PASS":
        raise ValueError("Independent evidence failed: " + "; ".join(fresh["blockers"]))
    if any(actual[key] != value for key, value in fresh.items() if key not in {"evidence_id", "created_at"}):
        raise ValueError("Stored evidence disagrees with the current independent audit")
    return actual


def validate_criteria(criteria):
    validate("validation_criteria", criteria)
    checks = unique(criteria["checks"], "check_id")
    metrics = {item["metric"] for item in checks.values()}
    if REQUIRED_METRICS[criteria["task_type"]] - metrics:
        raise ValueError("Validation criteria omit mandatory task checks")
    for check in checks.values():
        if check["metric"] in REQUIRED_METRICS[criteria["task_type"]]:
            if check["operator"] != "le" or check["threshold"] < 0:
                raise ValueError("Required residual checks need a nonnegative upper tolerance")
        if check["metric"] in {"coverage_error", "split_leakage", "main_feasibility_error", "baseline_feasibility_error"} and check["threshold"] != 0:
            raise ValueError("Coverage/leakage/feasibility cannot use a nonzero acceptance tolerance")
    robustness = criteria["robustness"]
    if robustness["status"] == "required" and (not robustness["required_metrics"] or not set(robustness["required_metrics"]) <= metrics):
        raise ValueError("Required robustness must have explicit measured criteria")
    if robustness["status"] == "not_applicable" and robustness["required_metrics"]:
        raise ValueError("Nonapplicable robustness cannot claim measured checks")
    return criteria


def compare_metrics(criteria, measurements):
    checks = []
    for check in criteria["checks"]:
        if check["metric"] not in measurements:
            raise ValueError(f"Independent validator did not compute {check['metric']}")
        value, threshold = measurements[check["metric"]], check["threshold"]
        passed = {"le": value <= threshold, "ge": value >= threshold, "eq": value == threshold}[check["operator"]]
        checks.append({key: check[key] for key in ("check_id", "metric", "operator", "threshold", "unit")} |
                      {"value": value, "status": "PASS" if passed else "FAIL"})
    return checks


def _compatible(root, main, baseline):
    if main["role"] not in {"main", "fallback"} or baseline["role"] != "baseline" or main["method_id"] == baseline["method_id"]:
        raise ValueError("Evidence requires distinct main and usable baseline executions")
    main_spec = read_json(root / main["spec"]["snapshot_path"])
    baseline_spec = read_json(root / baseline["spec"]["snapshot_path"])
    for field in ("question_id", "decision_id", "task_type", "data_split", "inputs", "outputs", "constraints", "objective"):
        if main_spec[field] != baseline_spec[field]:
            raise ValueError(f"Main and baseline are not comparable: {field}")
    if main["input_manifest_sha256"] != baseline["input_manifest_sha256"]:
        raise ValueError("Main/baseline original input manifests differ")
    if main_spec.get("upstream_freezes", []) != baseline_spec.get("upstream_freezes", []):
        raise ValueError("Main/baseline upstream frozen inputs differ")
    criteria_ref = main_spec["validation_plan"].get("criteria")
    if not criteria_ref or baseline_spec["validation_plan"].get("criteria") != criteria_ref:
        raise ValueError("Both models must pin identical criteria before execution")
    criteria_path = safe_path(root, criteria_ref["path"])
    if file_hash(criteria_path) != criteria_ref["sha256"]:
        raise ValueError("Predeclared validation criteria changed")
    for run in (main, baseline):
        if not any(item["source_path"] == criteria_ref["path"] and item["sha256"] == criteria_ref["sha256"]
                   for item in [*run["inputs"], *run.get("contract_snapshots", [])]):
            raise ValueError("Validation criteria were not frozen before each execution")
    criteria = validate_criteria(read_json(criteria_path))
    verify_formula_units(main_spec, criteria["symbol_dimensions"])
    verify_formula_units(baseline_spec, criteria["symbol_dimensions"])
    if criteria["task_type"] != main_spec["task_type"] or criteria["question_id"] != main["question_id"]:
        raise ValueError("Validation task/question mismatch")
    if criteria["evaluation"]["sense"] != main_spec["objective"]["sense"]:
        raise ValueError("Independent evaluator objective direction differs from model")
    if set(main_spec["validation_plan"]["checks"]) != {item["check_id"] for item in criteria["checks"]}:
        raise ValueError("Model validation plan does not cover the pinned check IDs")
    if {item["validator"] for item in main_spec["constraints"]} - {item["check_id"] for item in criteria["checks"]}:
        raise ValueError("Hard constraint lacks a declared independent check")
    return main_spec, criteria_ref, criteria


def independently_validate(root: Path, main_relative: str, baseline_relative: str, *, actor_id="builtin-independent-validator",
                         interpreter=None) -> dict:
    root = canonical_root(root)
    main, baseline = verify_run(root, main_relative), verify_run(root, baseline_relative)
    if actor_id in {main["actor_id"], baseline["actor_id"]}:
        raise ValueError("A producer cannot independently validate its own output")
    spec, criteria_ref, criteria = _compatible(root, main, baseline)
    validation_id = "validation-" + uuid.uuid4().hex
    directory = safe_path(root, f"validations/{validation_id}", exists=False)
    main_outputs = unique(main["outputs"], "name")
    baseline_outputs = unique(baseline["outputs"], "name")
    if criteria["main_output_name"] not in main_outputs or criteria["baseline_output_name"] not in baseline_outputs:
        raise ValueError("Required validation output does not exist")
    originals = unique(read_json(root / "input_manifest.json")["files"], "input_id")
    if criteria["data_input_id"] not in {item["input_id"] for item in main["inputs"]}:
        raise ValueError("Validator data was not consumed by the solver")
    problem = next(item for item in originals.values() if item["role"] == "problem")
    selected = [("problem", problem["path"], "problem"),
        ("raw-data", originals[criteria["data_input_id"]]["path"], "data"),
        ("main-result", main_outputs[criteria["main_output_name"]]["path"], "data"),
        ("baseline-result", baseline_outputs[criteria["baseline_output_name"]]["path"], "data"),
        ("solver-spec", main["spec"]["snapshot_path"], "description"),
        ("validation-criteria", criteria_ref["path"], "rule")]
    selected.extend((upstream_input_id(item["question_id"]), item["snapshot_path"], "description")
                    for item in main.get("upstream_freezes", []))
    declarations = [{"input_id": key, "path": str(safe_path(root, relative)), "role": role,
        "source": {"uri": f"workspace-artifact:{relative}", "accessed_at": now(),
                   "license": "Private workspace evidence; original rights unchanged"}} for key, relative, role in selected]
    child = initialize(validation_id, declarations, destination=directory / "workspace", kind="fixture", producer="validation-bundler")
    # This is an engineering execution bundle even inside a real competition workspace;
    # it never claims official compliance. Only allowlisted source-free evidence is copied.
    code_dir = child / "validator"
    code_dir.mkdir()
    code_files = []
    for source, target in [("validator_entry.py", "entry.py"), ("evaluators.py", "evaluators.py"), ("io.py", "strict_io.py")]:
        output = code_dir / target
        output.write_bytes(Path(__file__).with_name(source).read_bytes())
        code_files.append(output.relative_to(child).as_posix())
    copied_inputs = read_json(child / "input_manifest.json")
    validator_spec = deepcopy(spec)
    # Upstream frozen evidence is passed as explicit input snapshots below; the
    # validator's independent workspace does not contain the parent's registry.
    validator_spec.pop("upstream_freezes", None)
    validator_spec.pop("fallback_authorization", None)
    validator_spec.update(method_id="independent-validator", actor_id=actor_id,
        inputs=[item["input_id"] for item in copied_inputs["files"]],
        implementation={"entrypoint": "validator/entry.py", "code_files": code_files, "language": "python"},
        outputs=[{"name": "measurements", "path": "measurements.json", "format": "json", "precision": 12,
            "fields": [{"name": "metric", "type": "string", "unit": "identifier"}, {"name": "value", "type": "number", "unit": "per-criteria"}]}],
        validation_plan={"checks": [item["check_id"] for item in criteria["checks"]], "independent_entrypoint": "review/unused.py"})
    write_json(child / "model_spec.json", validator_spec, exclusive=True)
    validator_run = execute_model(child, "model_spec.json", role="validator", interpreter=interpreter)
    child_manifest = f"runs/{validator_run['run_id']}/run_manifest.json"
    if validator_run["status"] != "PASS":
        write_json(directory / "failure.json", {"status": "FAIL", "validation_id": validation_id,
            "validator_manifest": (child / child_manifest).relative_to(root).as_posix(),
            "reason": validator_run["failure_message"]}, exclusive=True)
        raise ValueError(f"Independent computation failed; inspect {directory.relative_to(root)}/failure.json")
    verify_run(child, child_manifest)
    raw_measurements = read_json(child / validator_run["outputs"][0]["path"])
    measurements = {key: row["value"] for key, row in unique(raw_measurements, "metric").items()}
    checks = compare_metrics(criteria, measurements)
    summary = {"schema_version": "2.0", "validation_id": validation_id, "question_id": main["question_id"],
        "actor_id": actor_id, "created_at": now(),
        "main_run": {"path": main_relative, "sha256": file_hash(root / main_relative)},
        "baseline_run": {"path": baseline_relative, "sha256": file_hash(root / baseline_relative)},
        "criteria": criteria_ref, "validator_workspace": child.relative_to(root).as_posix(),
        "validator_run": {"path": (child / child_manifest).relative_to(root).as_posix(), "sha256": file_hash(child / child_manifest)},
        "validator_code": [{"path": (child / item).relative_to(root).as_posix(), "sha256": file_hash(child / item)} for item in code_files],
        "measurements": measurements, "checks": checks,
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "limitations": ["Local input separation is not OS isolation.",
                        "Only declared adapter checks are computed; source/model semantic review is a separate workflow gate."]}
    validate("validation_summary", summary, root=root)
    write_json(directory / "validation_summary.json", summary, exclusive=True)
    return summary


def audit_evidence(root: Path, summary_relative: str) -> dict:
    root = canonical_root(root)
    summary_path = safe_path(root, summary_relative)
    summary = validate("validation_summary", read_json(summary_path), root=root)
    blockers, dependencies = [], []
    try:
        for reference in [summary["main_run"], summary["baseline_run"], summary["criteria"], summary["validator_run"], *summary["validator_code"]]:
            if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
                raise ValueError("Validation dependency hash changed")
            dependencies.append(reference)
        main = verify_run(root, summary["main_run"]["path"])
        baseline = verify_run(root, summary["baseline_run"]["path"])
        spec, criteria_ref, criteria = _compatible(root, main, baseline)
        if summary["criteria"] != criteria_ref or summary["question_id"] != main["question_id"]:
            raise ValueError("Validation summary changed its task or pinned criteria")
        child = safe_path(root, summary["validator_workspace"], exists=False)
        child_run = safe_path(root, summary["validator_run"]["path"]).relative_to(child).as_posix()
        validator_run = verify_run(child, child_run)
        if validator_run["role"] != "validator" or summary["actor_id"] != validator_run["actor_id"] or summary["actor_id"] in {main["actor_id"], baseline["actor_id"]}:
            raise ValueError("Validator identity/role is not independent")
        trusted_sources = {"validator/entry.py": "validator_entry.py", "validator/evaluators.py": "evaluators.py", "validator/strict_io.py": "io.py"}
        if {record["source_path"] for record in validator_run["code"]} != set(trusted_sources):
            raise ValueError("Unexpected validator code bundle")
        for record in validator_run["code"]:
            if record["sha256"] != file_hash(Path(__file__).with_name(trusted_sources[record["source_path"]])):
                raise ValueError("Validator code differs from reviewed built-in implementation")
        solver_hashes = {item["sha256"] for run in (main, baseline) for item in run["code"]}
        if solver_hashes & {item["sha256"] for item in validator_run["code"]}:
            raise ValueError("Validator reuses solver implementation")
        supplied = unique(validator_run["inputs"], "input_id")
        originals = unique(main["inputs"], "input_id")
        expected = {"raw-data": originals[criteria["data_input_id"]]["sha256"],
            "main-result": unique(main["outputs"], "name")[criteria["main_output_name"]]["sha256"],
            "baseline-result": unique(baseline["outputs"], "name")[criteria["baseline_output_name"]]["sha256"],
            "solver-spec": main["spec"]["sha256"], "validation-criteria": criteria_ref["sha256"]}
        expected.update({upstream_input_id(item["question_id"]): item["sha256"] for item in main.get("upstream_freezes", [])})
        if set(supplied) != {*expected, "problem"} or any(supplied[key]["sha256"] != value for key, value in expected.items()):
            raise ValueError("Validator did not consume the original inputs/spec/final outputs")
        if solver_hashes & {item["sha256"] for item in supplied.values()}:
            raise ValueError("Solver source leaked into validator inputs")
        rows = read_json(child / validator_run["outputs"][0]["path"])
        measurements = {key: row["value"] for key, row in unique(rows, "metric").items()}
        checks = compare_metrics(criteria, measurements)
        if measurements != summary["measurements"] or checks != summary["checks"]:
            raise ValueError("Validation summary does not match executed measurements/thresholds")
        if summary["status"] != "PASS" or any(check["status"] != "PASS" for check in checks):
            raise ValueError("Independent numerical checks failed")
        for run, base in ((main, root), (baseline, root), (validator_run, child)):
            if run["logs"]["stderr"]["size_bytes"]:
                raise ValueError("Unresolved stderr diagnostics require review before evidence PASS")
    except (ValueError, OSError, KeyError) as exc:
        blockers.append(str(exc))
    report = {"schema_version": "2.0", "evidence_id": "evidence-" + uuid.uuid4().hex,
        "question_id": summary["question_id"], "created_at": now(), "producer": "evidence-auditor",
        "validation": {"path": summary_relative, "sha256": file_hash(summary_path)},
        "dependencies": dependencies or [{"path": summary_relative, "sha256": file_hash(summary_path)}],
        "status": "FAIL" if blockers else "PASS", "blockers": blockers,
        "scope": "computed_model_evidence", "official_compliance": "NOT_RUN"}
    validate("evidence_gate", report, root=root)
    return report
