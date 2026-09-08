"""Predeclared parameter/seed experiments and independent assumption evidence."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .contracts import read_ledger, unique, validate
from .dispositions import pin
from .io import canonical_root, file_hash, now, read_json, safe_path, write_json
from .lineage import ArtifactRegistry, artifact_id
from .runner import execute_model, verify_run
from .state import workspace_lock
from .validation import independently_validate, audit_evidence, validate_criteria


def _contract(root, path, name):
    from .orchestrator import Orchestrator
    kind, value = Orchestrator(root, None)._kind(path)
    if kind != name:
        raise ValueError(f"Assumption assessment requires a current {name} handoff: {path}")
    return value


def _plan(root, reference):
    if pin(root, reference["path"]) != reference:
        raise ValueError("Assumption plan hash changed")
    plan = _contract(root, reference["path"], "assumption_plan")
    for source in [plan["ledger"], *plan["models"].values()]:
        if pin(root, source["path"]) != source:
            raise ValueError("Assumption ledger or production model changed")
    _contract(root, plan["ledger"]["path"], "assumption_ledger")
    latest = {entry["assumption_id"]: entry for entry in read_ledger(root / plan["ledger"]["path"])}
    for item in plan["assumptions"]:
        entry = latest.get(item["assumption_id"])
        if not entry or entry["status"] != "accepted" or plan["question_id"] not in entry["question_ids"]:
            raise ValueError("Assumption plan requires accepted assumptions for the current question")
    models = {role: _contract(root, ref["path"], "model_spec") for role, ref in plan["models"].items()}
    if any(spec["question_id"] != plan["question_id"] or spec["actor_id"] == plan["actor_id"] for spec in models.values()):
        raise ValueError("Assumption plan needs an independent reviewer of the same question's models")
    if models["main"]["method_id"] == models["baseline"]["method_id"]:
        raise ValueError("Assumption assessment needs a distinct baseline")
    if any("assumptions" in spec["validation_plan"] for spec in models.values()):
        raise ValueError("Production models cannot depend cyclically on their assessment plan")
    for field in ("question_id", "decision_id", "task_type", "data_split", "inputs", "outputs", "constraints", "objective", "upstream_freezes"):
        if models["main"].get(field) != models["baseline"].get(field):
            raise ValueError("Assumption assessment models are not comparable: " + field)
    reference = models["main"]["validation_plan"].get("criteria")
    if not reference or models["baseline"]["validation_plan"].get("criteria") != reference or pin(root, reference["path"]) != reference:
        raise ValueError("Assumption assessment needs identical current predeclared validation criteria")
    criteria = validate_criteria(read_json(safe_path(root, reference["path"])))
    units = {item["metric"]: item["unit"] for item in criteria["checks"]}
    for scenario in plan["scenarios"]:
        source = models["main"]["parameters"] if scenario["field"] == "parameter" else models["main"]
        key = scenario["parameter"] if scenario["field"] == "parameter" else "seed"
        if key not in source or source[key] == scenario["value"]:
            raise ValueError("Sensitivity must change an existing parameter or seed")
        for metric in scenario["metrics"]:
            if units.get(metric["metric"]) != metric["unit"]:
                raise ValueError("Sensitivity metric/unit must be independently checked by the pinned criteria")
    return plan, models


def report_path(plan):
    return f"assessments/{plan['plan_id']}/assumption_report.json"


def _specs(plan, models, reference):
    result = {"baseline": deepcopy(models["baseline"]), "control": deepcopy(models["main"])}
    for scenario in plan["scenarios"]:
        spec = deepcopy(models["main"])
        if scenario["field"] == "parameter":
            spec["parameters"][scenario["parameter"]] = scenario["value"]
        else:
            spec["seed"] = int(scenario["value"])
        result[scenario["scenario_id"]] = spec
    for spec in result.values():
        spec["validation_plan"]["assumptions"] = reference
    return result


def _compute(root, reference, experiments, timestamp):
    plan, models = _plan(root, reference)
    expected = _specs(plan, models, reference)
    indexed = unique(experiments, "scenario_id")
    required = {"control", *(s["scenario_id"] for s in plan["scenarios"])} if plan["scenarios"] else set()
    if indexed.keys() != required:
        raise ValueError("Assumption report must cover every planned experiment and control exactly")
    if indexed and any(item["baseline_run"] != indexed["control"]["baseline_run"] for item in indexed.values()):
        raise ValueError("Sensitivity experiments must reuse the fixed control baseline execution")
    measurements, blockers, checks = {}, [], []
    for name, experiment in indexed.items():
        for ref in (experiment["main_run"], experiment["baseline_run"], experiment["validation"]):
            if pin(root, ref["path"]) != ref:
                raise ValueError("Assumption experiment evidence hash changed")
        for role, expected_name in (("main", name), ("baseline", "baseline")):
            run = verify_run(root, experiment[role + "_run"]["path"])
            spec = read_json(root / run["spec"]["snapshot_path"])
            execution_role = "fallback" if "fallback_authorization" in spec else role
            if spec != expected[expected_name] or run["role"] != execution_role:
                raise ValueError("Sensitivity run differs from its predeclared production-model perturbation")
            if not any(item["contract"] == "assumption_plan" and item["source_path"] == reference["path"]
                       and item["sha256"] == reference["sha256"] for item in run.get("contract_snapshots", [])):
                raise ValueError("Sensitivity plan was not pinned before execution")
        summary = read_json(root / experiment["validation"]["path"])
        if summary["main_run"] != experiment["main_run"] or summary["baseline_run"] != experiment["baseline_run"]:
            raise ValueError("Sensitivity validation covers different executions")
        evidence = audit_evidence(root, experiment["validation"]["path"])
        if evidence["status"] != "PASS":
            blockers.extend(name + ": " + reason for reason in evidence["blockers"])
        else:
            measurements[name] = summary["measurements"]
    for scenario in plan["scenarios"]:
        name = scenario["scenario_id"]
        if name not in measurements or "control" not in measurements:
            continue
        for metric in scenario["metrics"]:
            control, perturbed = (measurements[key][metric["metric"]] for key in ("control", name))
            change = abs(perturbed - control)
            passed = change <= metric["max_absolute_change"]
            checks.append({"scenario_id": name, **metric, "control": control, "perturbed": perturbed,
                           "absolute_change": change, "status": "PASS" if passed else "FAIL"})
            if not passed:
                blockers.append(f"{name}: {metric['metric']} exceeds the predeclared sensitivity limit")
    assessments = []
    for item in plan["assumptions"]:
        failed = any(name not in measurements or any(c["status"] != "PASS" for c in checks if c["scenario_id"] == name)
                     for name in item["scenario_ids"]) or bool(item["scenario_ids"] and "control" not in measurements)
        assessments.append({"assumption_id": item["assumption_id"], "scenario_ids": item["scenario_ids"],
            "rationale": item["rationale"], "status": "NOT_APPLICABLE" if item["mode"] == "not_applicable" else "FAILED" if failed else "TESTED"})
    return validate("assumption_report", {"schema_version": "2.0", "question_id": plan["question_id"], "plan": reference,
        "created_at": timestamp, "producer": "assumption-assessment-service", "scope": "declared_assumption_checks",
        "experiments": experiments, "checks": checks, "assessments": assessments,
        "status": "FAIL" if blockers else "PASS", "blockers": blockers}, root=root)


def verify_assessment(root: Path, relative: str):
    root = canonical_root(root)
    actual = validate("assumption_report", read_json(safe_path(root, relative)), root=root)
    expected = _compute(root, actual["plan"], actual["experiments"], actual["created_at"])
    if actual != expected:
        raise ValueError("Assumption report differs from independently recomputed evidence")
    registry = ArtifactRegistry(root)
    records = {a["artifact_id"]: a for a in registry.store.load()["artifacts"]}
    key = artifact_id(relative)
    if key not in records or records[key]["status"] != "VALID" or records[key]["producer"] != "assumption-assessment-service" or key in registry.store.inspect_freshness()["stale"]:
        raise ValueError("Assumption report is missing or stale in the evidence graph")
    return actual


def assess_assumptions(root: Path, plan_relative: str, *, interpreter=None):
    root = canonical_root(root)
    with workspace_lock(root, scope="workflow"):
        return _assess_assumptions(root, plan_relative, interpreter=interpreter)


def _assess_assumptions(root, plan_relative, *, interpreter=None):
    """Called under the workflow lock; interrupted successful steps are adopted."""
    reference = pin(root, plan_relative)
    plan, models = _plan(root, reference)
    relative = report_path(plan)
    existing_report = None
    if safe_path(root, relative, exists=False).exists():
        records = {item["artifact_id"] for item in ArtifactRegistry(root).store.load()["artifacts"]}
        if artifact_id(relative) in records:
            return verify_assessment(root, relative)
        existing_report = validate("assumption_report", read_json(root / relative), root=root)
        if existing_report != _compute(root, reference, existing_report["experiments"], existing_report["created_at"]):
            raise ValueError("Unregistered assumption report differs from actual completed work")
    registry = ArtifactRegistry(root)
    dependencies = [registry.register(plan["ledger"]["path"], producer=read_ledger(root / plan["ledger"]["path"])[-1]["producer"])]
    dependencies.extend(registry.register(ref["path"], producer=models[role]["actor_id"]) for role, ref in plan["models"].items())
    dependencies.append(registry.register(plan_relative, producer=plan["actor_id"], dependencies=dependencies))
    experiments = []
    if plan["scenarios"]:
        runs = {}
        for name, spec in _specs(plan, models, reference).items():
            spec_path = f"assessments/{plan['plan_id']}/{name}_spec.json"
            destination = safe_path(root, spec_path, exists=False)
            if destination.exists():
                if read_json(destination) != spec:
                    raise ValueError("Assessment ID already has different immutable experiment specs")
            else:
                write_json(destination, spec, exclusive=True)
            dependencies.append(registry.register(spec_path, producer="assumption-assessment-service", dependencies=[artifact_id(plan_relative)]))
            matches = []
            for path in (root / "runs").glob("*/run_manifest.json"):
                raw = read_json(path)
                if raw["spec"]["source_path"] == spec_path:
                    # Preserve and stop on failed/stale work; no implicit retry.
                    matches.append((raw["started_at"], path.relative_to(root).as_posix()))
            role = "baseline" if name == "baseline" else "fallback" if "fallback_authorization" in spec else "main"
            run = verify_run(root, max(matches)[1]) if matches else execute_model(root, spec_path, role=role, interpreter=interpreter)
            if run["status"] != "PASS":
                raise ValueError("Assumption experiment failed; inspect its actual run before explicit repair/retry")
            runs[name] = pin(root, f"runs/{run['run_id']}/run_manifest.json")
        from .freeze import _bind_evidence, _register_run
        for name in sorted(runs.keys() - {"baseline"}):
            matches = []
            for path in (root / "validations").glob("*/validation_summary.json"):
                summary = read_json(path)
                if summary["main_run"] == runs[name] and summary["baseline_run"] == runs["baseline"]:
                    matches.append(path.relative_to(root).as_posix())
            if len(matches) > 1:
                raise ValueError("Multiple assessment validations require explicit reconciliation")
            if matches:
                summary_path = matches[0]
            else:
                request_path = f"assessments/{plan['plan_id']}/{name}_validation_request.json"
                if safe_path(root, request_path, exists=False).exists():
                    raise ValueError("Prior assessment validation has no completed summary; inspect the interrupted/failed attempt before explicit repair")
                write_json(root / request_path, {"plan": reference, "scenario_id": name, "main_run": runs[name],
                    "baseline_run": runs["baseline"], "requested_at": now()}, exclusive=True)
                registry.register(request_path, producer="assumption-assessment-service", dependencies=[artifact_id(plan_relative)])
                summary = independently_validate(root, runs[name]["path"], runs["baseline"]["path"], interpreter=interpreter)
                summary_path = f"validations/{summary['validation_id']}/validation_summary.json"
            request_path = f"assessments/{plan['plan_id']}/{name}_validation_request.json"
            if safe_path(root, request_path, exists=False).exists():
                request = read_json(root / request_path)
                if any(request[key] != value for key, value in {"plan": reference, "scenario_id": name,
                        "main_run": runs[name], "baseline_run": runs["baseline"]}.items()):
                    raise ValueError("Assessment validation request changed its declared scope")
                dependencies.append(registry.register(request_path, producer="assumption-assessment-service", dependencies=[artifact_id(plan_relative)]))
            experiments.append({"scenario_id": name, "main_run": runs[name], "baseline_run": runs["baseline"],
                                "validation": pin(root, summary_path)})
            evidence = audit_evidence(root, summary_path)
            evidence_path = summary_path.replace("validation_summary.json", "evidence.json")
            if not safe_path(root, evidence_path, exists=False).exists():
                write_json(root / evidence_path, evidence, exclusive=True)
            if evidence["status"] == "PASS":
                _, _, evidence_id, _ = _bind_evidence(registry, root, summary_path, evidence_path)
                dependencies.append(evidence_id)
            else:
                with registry.batch():
                    for ref in (runs[name], runs["baseline"]):
                        run_id, _ = _register_run(registry, root, root, verify_run(root, ref["path"]))
                        dependencies.append(run_id)
                    dependencies.append(registry.register(summary_path, producer="independent-validator", dependencies=dependencies))
    report = _compute(root, reference, sorted(experiments, key=lambda item: item["scenario_id"]),
                      existing_report["created_at"] if existing_report else now())
    if existing_report:
        if existing_report != report:
            raise ValueError("Interrupted assumption report no longer matches its evidence")
    else:
        write_json(root / relative, report, exclusive=True)
    registry.register(relative, producer="assumption-assessment-service", dependencies=dependencies)
    return report


def bind_assessment_reports(root, references, question_id, *, model_pins=None):
    """Recheck direct evidence before freezing; failed assessments never qualify."""
    unique(references, "path")
    dependencies = []
    for reference in references:
        if pin(root, reference["path"]) != reference:
            raise ValueError("Assumption report hash changed")
        report = verify_assessment(root, reference["path"])
        if report["question_id"] != question_id or report["status"] != "PASS":
            raise ValueError("Freeze requires passing assumption evidence for the same question")
        plan, _ = _plan(canonical_root(root), report["plan"])
        if model_pins is not None and plan["models"] != model_pins:
            raise ValueError("Assumption report evaluates different production models than this freeze")
        dependencies.append(artifact_id(reference["path"]))
    return dependencies
