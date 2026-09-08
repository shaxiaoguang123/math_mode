"""Compute risk verdicts from predeclared plans and actually executed probes."""
from pathlib import Path

from .contracts import validate, unique
from .freeze import json_pointer
from .io import canonical_root, read_json, file_hash, safe_path
from .runner import verify_run
from .lineage import artifact_id


def measured_probe(root: Path, run_relative: str) -> dict:
    root = canonical_root(root)
    record = verify_run(root, run_relative)
    if record["role"] != "probe":
        raise ValueError("Risk evidence requires an actual probe-role execution")
    plans = [item for item in record.get("contract_snapshots", []) if item["contract"] == "risk_probe_plan"]
    if len(plans) != 1:
        raise ValueError("Probe measurements need a plan pinned before execution")
    plan = validate("risk_probe_plan", read_json(root / plans[0]["snapshot_path"]), root=root)
    if (plan["question_id"], plan["method_id"]) != (record["question_id"], record["method_id"]):
        raise ValueError("Probe plan and execution identities differ")
    categories = unique(plan["checks"], "category")
    required = {"executability", "coverage", "assumptions", "degeneracy", "perturbation", "scale"}
    if categories.keys() != required:
        raise ValueError("Probe plan must cover exactly all six risk categories")
    outputs = unique(record["outputs"], "name")
    checks = []
    for category, check in categories.items():
        measurements = unique(check["measurements"], "metric")
        if check["not_applicable_reason"]:
            if category in {"executability", "coverage"} or measurements:
                raise ValueError("Executability/coverage cannot be waived and N/A cannot claim measurements")
            checks.append({"category": category, "status": "NOT_APPLICABLE", "evidence_refs": [plans[0]["snapshot_path"]],
                "metrics": {}, "thresholds": {}, "reason": check["not_applicable_reason"]})
            continue
        if not measurements:
            raise ValueError("Applicable probe category needs actual measurements")
        metrics, thresholds, evidence = {}, {}, []
        passed = True
        for name, measurement in measurements.items():
            if measurement["output_name"] == "runtime":
                if measurement["locator"] not in {"/returncode", "/duration_seconds"}:
                    raise ValueError("Only observed returncode/duration are runtime probe metrics")
                source, value = run_relative, json_pointer(record, measurement["locator"])
            else:
                if measurement["output_name"] not in outputs:
                    raise ValueError("Probe measurement refers to an absent output")
                source = outputs[measurement["output_name"]]["path"]
                value = json_pointer(read_json(safe_path(root, source)), measurement["locator"])
            metrics[name] = value
            thresholds[name] = measurement["threshold"]
            evidence.append(source + "#" + measurement["locator"])
            threshold = measurement["threshold"]
            passed &= {"le": value <= threshold, "ge": value >= threshold, "eq": value == threshold}[measurement["operator"]]
        if category == "executability" and not any(m["output_name"] == "runtime" and m["locator"] == "/returncode"
                and m["operator"] == "eq" and m["threshold"] == 0 for m in measurements.values()):
            raise ValueError("Executability must verify the actual zero returncode")
        checks.append({"category": category, "status": "PASS" if passed else "FAIL", "evidence_refs": evidence,
            "metrics": metrics, "thresholds": thresholds, "reason": check["reason"]})
    return validate("risk_probe", {"schema_version": "2.0", "question_id": record["question_id"],
        "method_id": record["method_id"], "run_id": record["run_id"], "checks": checks,
        "verdict": "FAIL" if any(check["status"] == "FAIL" for check in checks) else "PASS"}, root=root)


def verify_probe(root: Path, report_relative: str, run_relative: str) -> dict:
    expected = measured_probe(root, run_relative)
    actual = validate("risk_probe", read_json(safe_path(root, report_relative)), root=root)
    if expected != actual:
        raise ValueError("Risk report differs from executed measurements and pinned thresholds")
    return actual


def screening_options(root: Path, card_relative: str, report_relatives: list[str]) -> dict:
    """Recompute admissible production choices from pre-execution screening evidence."""
    root = canonical_root(root)
    card = validate("method_card", read_json(safe_path(root, card_relative)), root=root)
    methods = unique(card["methods"], "method_id")
    reports = {}
    for relative in report_relatives:
        raw = read_json(safe_path(root, relative))
        run_relative = f"runs/{raw['run_id']}/run_manifest.json"
        report = verify_probe(root, relative, run_relative)
        run = verify_run(root, run_relative)
        if not any(item["contract"] == "method_card" and item["source_path"] == card_relative
                   and item["sha256"] == file_hash(root / card_relative) for item in run.get("contract_snapshots", [])):
            raise ValueError("Risk probe did not pin the current screened method card before execution")
        method_id = report["method_id"]
        if report["question_id"] != card["question_id"] or method_id not in methods:
            raise ValueError("Risk probe belongs to another question or an unknown method")
        if method_id in reports:
            raise ValueError("Screening requires one declared current probe report per method")
        reports[method_id] = {"report": report, "path": relative, "run_path": run_relative}
    main = next(method for method in methods.values() if method["role"] == "main_candidate")
    main_probe = reports.get(main["method_id"])
    options = {}
    if main_probe and main_probe["report"]["verdict"] == "PASS":
        options["main"] = {"method_id": main["method_id"], "authorization": None}
    fallback = next((method for method in methods.values() if method["role"] == "conditional_fallback"), None)
    if main_probe and fallback:
        trigger = fallback_triggered(card, main_probe["report"])
        own_probe = reports.get(fallback["method_id"])
        if trigger["triggered"] and own_probe and own_probe["report"]["verdict"] == "PASS":
            options["fallback"] = {"method_id": fallback["method_id"], "authorization": {
                field: {"path": path, "sha256": file_hash(root / path)} for field, path in
                (("card", card_relative), ("probe_report", main_probe["path"]), ("probe_run", main_probe["run_path"]))}}
    if not options:
        raise ValueError("No screened production method: need passing main, or triggered fallback with its own passing probe")
    return {"card": card, "options": options}


def verify_screened_decision(decision: dict, screening: dict, report_relatives: list[str]) -> str:
    validate("method_decision", decision)
    card = screening["card"]
    role = decision.get("execution_role", "main")
    option = screening["options"].get(role)
    baseline = next(method for method in card["methods"] if method["role"] == "usable_baseline")
    if (decision["question_id"] != card["question_id"] or option is None
            or decision["main_method_id"] != option["method_id"] or decision["baseline_method_id"] != baseline["method_id"]):
        raise ValueError("Decision does not select an eligible screened production method and baseline")
    if {artifact_id(path) for path in report_relatives} - set(decision["evidence_refs"]):
        raise ValueError("Decision omits its actual measured probes")
    return role


def fallback_triggered(card: dict, probe: dict) -> dict:
    validate("method_card", card)
    validate("risk_probe", probe)
    candidates = [method for method in card["methods"] if method["role"] == "conditional_fallback"]
    if len(candidates) != 1 or card["question_id"] != probe["question_id"]:
        raise ValueError("A question-specific conditional fallback is required")
    fallback = candidates[0]
    trigger = fallback["fallback_trigger"]
    metrics = {check["category"] + "." + name: value for check in probe["checks"] for name, value in check["metrics"].items()}
    if trigger["metric"] not in metrics:
        raise ValueError("Fallback trigger must reference an actual qualified probe metric")
    value, threshold = metrics[trigger["metric"]], trigger["threshold"]
    triggered = {"gt": value > threshold, "ge": value >= threshold, "lt": value < threshold,
                 "le": value <= threshold, "eq": value == threshold}[trigger["operator"]]
    return {"method_id": fallback["method_id"], "metric": trigger["metric"], "value": value,
            "operator": trigger["operator"], "threshold": threshold, "triggered": triggered}


def verify_fallback_authorization(root: Path, spec: dict) -> dict:
    """Only a trigger pinned before its actual probe can admit fallback execution."""
    root = canonical_root(root)
    authorization = spec.get("fallback_authorization")
    if not authorization:
        raise ValueError("Fallback requires a recorded measured trigger via the workflow harness")
    for reference in authorization.values():
        if file_hash(safe_path(root, reference["path"])) != reference["sha256"]:
            raise ValueError("Fallback authorization hash changed")
    raw_run = validate("run_manifest", read_json(root / authorization["probe_run"]["path"]), root=root)
    # Check the role before recursively auditing so forged fallback cycles fail closed.
    if raw_run["role"] != "probe":
        raise ValueError("Fallback authorization requires a probe-role run")
    record = verify_run(root, authorization["probe_run"]["path"])
    cards = [item for item in record.get("contract_snapshots", []) if item["contract"] == "method_card"]
    if len(cards) != 1 or cards[0]["sha256"] != authorization["card"]["sha256"] or cards[0]["source_path"] != authorization["card"]["path"]:
        raise ValueError("Fallback trigger must be pinned in the method card before probing")
    card = validate("method_card", read_json(root / authorization["card"]["path"]), root=root)
    main = next(method for method in card["methods"] if method["role"] == "main_candidate")
    if record["method_id"] != main["method_id"] or record["question_id"] != spec["question_id"]:
        raise ValueError("Fallback must evaluate the screened main method for the same question")
    probe = verify_probe(root, authorization["probe_report"]["path"], authorization["probe_run"]["path"])
    result = fallback_triggered(card, probe)
    if result["method_id"] != spec["method_id"] or not result["triggered"]:
        raise ValueError("Fallback trigger is inactive or selects a different method")
    return result
