"""Structural and cross-contract checks; passing these is not scientific proof."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from jsonschema import Draft202012Validator, FormatChecker

from .io import finite_tree, safe_path, file_hash, loads
from .schema_catalog import catalog


def unique(items, key, label=None):
    result = {}
    for item in items:
        value = item[key]
        if value in result:
            raise ValueError(f"Duplicate {label or key}: {value}")
        result[value] = item
    return result


def references(values, available, label):
    missing = set(values) - set(available)
    if missing:
        raise ValueError(f"Unknown {label}: {sorted(missing)}")


def topological_order(nodes: dict[str, list[str]]) -> list[str]:
    for node, dependencies in nodes.items():
        if node in dependencies:
            raise ValueError(f"Self dependency: {node}")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"Duplicate dependency: {node}")
        references(dependencies, nodes, "dependency")
    pending = {key: set(value) for key, value in nodes.items()}
    result = []
    while pending:
        ready = sorted(key for key, deps in pending.items() if not deps)
        if not ready:
            raise ValueError(f"Dependency cycle: {sorted(pending)}")
        result.extend(ready)
        for key in ready:
            del pending[key]
        for deps in pending.values():
            deps.difference_update(ready)
    return result


def _outputs(outputs):
    unique(outputs, "name")
    paths = [item["path"].replace("\\", "/").casefold() for item in outputs]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate output path")
    for output in outputs:
        unique(output["fields"], "name", "output field")


def validate(name: str, value: dict, *, root: Path | None = None) -> dict:
    definitions = catalog()
    if name not in definitions:
        raise ValueError(f"Unknown contract: {name}")
    finite_tree(value)
    Draft202012Validator(definitions[name], format_checker=FormatChecker()).validate(value)
    # Semantic path checks also run without a workspace (no filesystem writes).
    anchor = root or Path.cwd()
    def paths(item):
        if isinstance(item, dict):
            for key, val in item.items():
                if key in {"path", "source_path", "snapshot_path", "entrypoint", "independent_entrypoint"}:
                    if "\\" in val:
                        raise ValueError("Contract paths must use portable forward slashes")
                    safe_path(anchor, val, exists=False)
                elif key == "code_files":
                    for relative in val:
                        if "\\" in relative:
                            raise ValueError("Contract paths must use portable forward slashes")
                        safe_path(anchor, relative, exists=False)
                else:
                    paths(val)
        elif isinstance(item, list):
            for child in item:
                paths(child)
    paths(value)
    if name == "input_manifest":
        unique(value["files"], "input_id")
        folded = [item["path"].replace("\\", "/").casefold() for item in value["files"]]
        if len(folded) != len(set(folded)):
            raise ValueError("Duplicate input path")
        if not any(item["role"] == "problem" for item in value["files"]):
            raise ValueError("An explicit original problem input is required")
        if root:
            for item in value["files"]:
                path = safe_path(root, item["path"])
                if path.stat().st_size != item["size_bytes"] or file_hash(path) != item["sha256"]:
                    raise ValueError(f"Original input changed: {item['input_id']}")
                if path.stat().st_mode & 0o222:
                    raise ValueError(f"Original input is writable: {item['input_id']}")
    elif name == "semantic_review":
        if value["actor_id"] == value["reviewed_actor_id"]:
            raise ValueError("Review requires an independent actor")
        if any(f["severity"] == "error" for f in value["findings"]) and value["verdict"] != "BLOCKED":
            raise ValueError("Error findings must block semantic acceptance")
        if value["verdict"] == "SUPPORTED" and (value["limitations"] or any(f["severity"] == "warning" for f in value["findings"])):
            raise ValueError("Warnings/limitations require a limited or blocked verdict")
        if value["verdict"] == "LIMITED" and not value["limitations"]:
            raise ValueError("Limited review must state its limitations")
        if value["verdict"] == "BLOCKED" and not value["findings"]:
            raise ValueError("Blocked review must state its findings")
    elif name == "method_proposal":
        if value["applicable"] and (not value["main_idea"] or not value["baseline_idea"] or not value["validation_plan"]):
            raise ValueError("Applicable proposal requires main, baseline and validation plan")
    elif name == "problem_frame":
        unique(value["questions"], "question_id")
        for question in value["questions"]:
            _outputs(question["outputs"])
            unique(question["constraints"], "constraint_id")
    elif name == "problem_dag":
        nodes = unique(value["nodes"], "question_id")
        topological_order({key: node["depends_on"] for key, node in nodes.items()})
    elif name == "ambiguity_register":
        unique(value["items"], "ambiguity_id")
        for item in value["items"]:
            if item["status"] != "unresolved" and (not item["resolution"] or not item["evidence_refs"]):
                raise ValueError("Resolved/mitigated ambiguity requires resolution and evidence")
    elif name == "symbol_table":
        unique(value["symbols"], "symbol_id")
        unique(value["symbols"], "code_name")
        for symbol in value["symbols"]:
            domain = symbol["domain"]
            low, high = domain["lower"], domain["upper"]
            if low is not None and high is not None and low > high:
                raise ValueError("Reversed symbol domain")
            if domain["kind"] == "integer" and any(x is not None and x != int(x) for x in (low, high)):
                raise ValueError("Nonintegral integer domain")
            if domain["kind"] == "boolean" and any(x is not None and x not in (0, 1) for x in (low, high)):
                raise ValueError("Boolean domain must lie in [0, 1]")
    elif name == "method_card":
        unique(value["methods"], "method_id")
        chosen = []
        for role in ("main_candidate", "usable_baseline"):
            methods = [m for m in value["methods"] if m["role"] == role]
            if len(methods) != 1 or not methods[0]["completes_task"] or methods[0]["rejection_reason"]:
                raise ValueError(f"Exactly one usable {role} is required")
            chosen.append(methods[0])
        if set(chosen[0]["outputs"]) != set(chosen[1]["outputs"]):
            raise ValueError("Main and baseline must complete the same outputs")
        fallbacks = [m for m in value["methods"] if m["role"] == "conditional_fallback"]
        if len(fallbacks) > 1:
            raise ValueError("At most one conditional fallback is allowed")
        for method in value["methods"]:
            if (method["role"] == "conditional_fallback") != (method["fallback_trigger"] is not None):
                raise ValueError("Only a fallback must have an explicit measured trigger")
            if method["role"] == "conditional_fallback" and (not method["completes_task"] or method["rejection_reason"] or set(method["outputs"]) != set(chosen[0]["outputs"])):
                raise ValueError("Fallback must complete all required outputs")
    elif name == "risk_probe":
        checks = unique(value["checks"], "category")
        required = {"executability", "coverage", "assumptions", "degeneracy", "perturbation", "scale"}
        if set(checks) != required:
            raise ValueError("All six risk categories are required exactly once")
        statuses = {check["status"] for check in checks.values()}
        expected = "FAIL" if "FAIL" in statuses else "CONDITIONAL" if "CONDITIONAL" in statuses else "PASS"
        if checks["executability"]["status"] == "NOT_APPLICABLE" or checks["coverage"]["status"] == "NOT_APPLICABLE":
            raise ValueError("Executability and task coverage cannot be waived")
        if value["verdict"] != expected:
            raise ValueError("Risk verdict contradicts checks")
    elif name == "method_decision":
        if value["main_method_id"] == value["baseline_method_id"]:
            raise ValueError("Main and usable baseline must be distinct")
        if (value["decided_by"] == "human") != (value["human_event_id"] is not None):
            raise ValueError("Human attribution requires an actual human event reference")
    elif name == "model_spec":
        unique(value["formulae"], "formula_id")
        unique(value["constraints"], "constraint_id")
        _outputs(value["outputs"])
        for formula in value["formulae"]:
            references([*formula["input_symbols"], formula["output_symbol"]], value["variables"], "formula variable")
        implementation = value["implementation"]
        if implementation["entrypoint"] not in implementation["code_files"]:
            raise ValueError("Entrypoint missing from explicit code bundle")
        if value["validation_plan"]["independent_entrypoint"] in implementation["code_files"]:
            raise ValueError("Independent validator cannot belong to solver bundle")
        split = value["data_split"]
        train, test, fit = (set(split[key]) for key in ("train_ids", "test_ids", "fit_ids"))
        if train & test or not fit <= train:
            raise ValueError("Split leakage: train/test overlap or fit outside training")
        if split["target"] in split["features"]:
            raise ValueError("Target leakage in features")
        if split["strategy"] == "none" and (train or test or fit):
            raise ValueError("Unsplit strategy cannot declare split membership")
        if split["strategy"] != "none" and (not train or not test):
            raise ValueError("Split strategy requires nonempty train and holdout")
        if value["task_type"] == "time_series" and split["strategy"] not in {"time", "rolling"}:
            raise ValueError("Time-series evaluation requires chronological splitting")
        if split["strategy"] in {"time", "rolling"}:
            times = split["sample_times"]
            references(train | test, times, "sample timestamp")
            parsed = {key: datetime.fromisoformat(times[key].replace("Z", "+00:00")) for key in train | test}
            if max(parsed[key] for key in train) >= min(parsed[key] for key in test):
                raise ValueError("Chronological leakage: training must precede holdout")
        if split["strategy"] == "group":
            groups = split["sample_groups"]
            references(train | test, groups, "sample group")
            if {groups[key] for key in train} & {groups[key] for key in test}:
                raise ValueError("Group leakage across train and holdout")
    elif name == "workflow_plan":
        unique(value["questions"], "question_id")
        unique([number for job in value["questions"] for number in job["frozen_numbers"]], "frozen_number_id")
        for job in value["questions"]:
            if "probe_specs" in job and len(job["probe_specs"]) != len(job["probe_reports"]):
                raise ValueError("Workflow probe specs must map one-to-one to report paths")
            for number in job["frozen_numbers"]:
                if (number["source"] == "main_output") != (number["output_name"] is not None):
                    raise ValueError("Frozen output locators require exactly one declared output name")
    elif name == "workflow_state":
        artifacts = unique(value["artifacts"], "artifact_id")
        if len({a["path"].casefold() for a in artifacts.values()}) != len(artifacts):
            raise ValueError("Artifact paths must be unique")
        topological_order({key: [d["artifact_id"] for d in a["depends_on"]] for key, a in artifacts.items()})
        unique(value["gates"], "gate_id")
        for gate in value["gates"]:
            references(gate["artifact_refs"], artifacts, "gate artifact")
            if gate["status"] == "PASS" and (gate["blockers"] or not gate["artifact_refs"]):
                raise ValueError("PASS gate must have evidence and no blockers")
        causes = {}
        for event in value["retry_history"]:
            key = (event["question_id"], event["cause_id"])
            causes[key] = causes.get(key, 0) + 1
            if event["attempt"] != causes[key] or causes[key] > 3:
                raise ValueError("Retry sequence skipped/reset or budget exhausted")
    elif name == "run_manifest":
        if value["status"] == "PASS" and (value["returncode"] != 0 or value["timed_out"]
                or value["failure_class"] is not None or value["cause_id"] is not None
                or value["failure_message"] is not None or not value["outputs"]):
            raise ValueError("Run PASS contradicts process/artifact observations")
        if value["status"] == "FAIL" and any(value[key] is None for key in ("failure_class", "cause_id", "failure_message")):
            raise ValueError("Failed run requires failure class, root cause and message")
        if (value["attempt"] == 1) != (value["retry_of"] is None):
            raise ValueError("Retry attempt requires predecessor")
        if datetime.fromisoformat(value["ended_at"]) < datetime.fromisoformat(value["started_at"]):
            raise ValueError("Run timestamps are reversed")
        unique(value["inputs"], "input_id")
        unique(value["code"], "source_path")
        unique(value["outputs"], "name")
        if value["backend"] == "local_subprocess" and any(value["capabilities"][key] for key in
                ("os_sandbox", "network_isolation", "filesystem_isolation", "memory_limit", "cpu_limit")):
            raise ValueError("Local subprocess cannot claim isolation capabilities")
    elif name == "validation_summary":
        unique(value["checks"], "check_id")
        expected = "PASS" if all(check["status"] == "PASS" for check in value["checks"]) else "FAIL"
        if value["status"] != expected:
            raise ValueError("Validation status contradicts numerical checks")
        for check in value["checks"]:
            if value["measurements"].get(check["metric"]) != check["value"]:
                raise ValueError("Validation check disagrees with its measurement")
            measured, threshold = check["value"], check["threshold"]
            passed = {"le": measured <= threshold, "ge": measured >= threshold, "eq": measured == threshold}[check["operator"]]
            if (check["status"] == "PASS") != passed:
                raise ValueError("Validation status disagrees with numerical comparison")
    elif name == "evidence_gate":
        if (value["status"] == "PASS") == bool(value["blockers"]):
            raise ValueError("Evidence gate status contradicts blockers")
    return value


def read_ledger(path: Path, contract="assumption_ledger") -> list[dict]:
    entries = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            raise ValueError("Blank JSONL event")
        entries.append(validate(contract, loads(line)))
    validate_events(entries, contract)
    return entries


def validate_events(entries: list[dict], contract="assumption_ledger"):
    for entry in entries:
        validate(contract, entry)
    if contract == "assumption_ledger":
        unique(entries, "entry_id")
        current = {}
        for entry in entries:
            previous = current.get(entry["assumption_id"])
            if entry["supersedes"] != (previous["entry_id"] if previous else None):
                raise ValueError("Assumption events must supersede the current revision")
            current[entry["assumption_id"]] = entry
    else:
        unique(entries, "event_id" if contract == "ai_usage" else "decision_id")


def validate_modeling_bundle(bundle: dict, *, root: Path | None = None) -> dict:
    """Require cross-file consistency before modeling; not a run/evidence gate."""
    required = {"input_manifest", "problem_frame", "problem_dag", "ambiguity_register", "symbol_table"}
    if required - bundle.keys():
        raise ValueError(f"Missing modeling contracts: {sorted(required - bundle.keys())}")
    for name in required:
        validate(name, bundle[name], root=root)
    inputs = unique(bundle["input_manifest"]["files"], "input_id")
    frame = bundle["problem_frame"]
    if frame["case_id"] != bundle["input_manifest"]["case_id"]:
        raise ValueError("Mismatched case identity")
    references(frame["source_refs"], inputs, "source input")
    questions = unique(frame["questions"], "question_id")
    nodes = unique(bundle["problem_dag"]["nodes"], "question_id")
    if questions.keys() != nodes.keys():
        raise ValueError("DAG must cover exactly every question")
    for question in questions.values():
        references(question["inputs"], inputs, "question input")
    sources = set(inputs) | set(bundle.get("source_ids", []))
    def citations(values):
        references([value.split(":", 1)[0] for value in values], sources, "source citation")
    for question in questions.values():
        citations(question["source_refs"])
        citations([item["source_ref"] for item in question["constraints"]])
    for ambiguity in bundle["ambiguity_register"]["items"]:
        references(ambiguity["question_ids"], questions, "ambiguity question")
        if ambiguity["severity"] == "high" and ambiguity["status"] != "resolved":
            raise ValueError("Unresolved high-severity ambiguity blocks modeling")
    symbols = unique(bundle["symbol_table"]["symbols"], "symbol_id")
    for symbol in symbols.values():
        references(symbol["question_ids"], questions, "symbol question")
    cards = unique(bundle.get("method_cards", []), "question_id")
    decisions = unique(bundle.get("method_decisions", []), "question_id")
    events = bundle.get("assumption_events", [])
    validate_events(events)
    assumptions = {event["assumption_id"]: event for event in events}
    formula_ids = {f["formula_id"] for spec in bundle.get("model_specs", []) for f in spec["formulae"]}
    active_assumptions = set()
    for qid, card in cards.items():
        decision = decisions.get(qid)
        selected = {decision["main_method_id"], decision["baseline_method_id"]} if decision else None
        active_assumptions.update(key for method in card["methods"] if selected is None or method["method_id"] in selected
                                  for key in method["assumption_ids"])
    for assumption in assumptions.values():
        references(assumption["question_ids"], questions, "assumption question")
        # Unselected/rejected-method history remains in the ledger, while active
        # assumptions must still name formulae in the implemented model bundle.
        if assumption["assumption_id"] in active_assumptions or not cards:
            references(assumption["formula_ids"], formula_ids, "assumption formula")
        citations(assumption["source_refs"])
    for question_id, card in cards.items():
        validate("method_card", card, root=root)
        references([question_id], questions, "method question")
        expected = {out["name"] for out in questions[question_id]["outputs"]}
        for method in card["methods"]:
            references(method["assumption_ids"], assumptions, "method assumption")
            citations(method["source_refs"])
            selected = decisions.get(question_id)
            is_active = selected is None or method["method_id"] in {selected["main_method_id"], selected["baseline_method_id"]}
            if is_active and any(assumptions[key]["status"] == "rejected" for key in method["assumption_ids"]):
                raise ValueError("Selected candidate uses a rejected assumption")
            if method["role"] != "diagnostic_reference" and set(method["outputs"]) != expected:
                raise ValueError("Method output coverage differs from question")
    for question_id, decision in decisions.items():
        validate("method_decision", decision, root=root)
        references([question_id], cards, "decision question card")
        methods = unique(cards[question_id]["methods"], "method_id")
        selected_role = "conditional_fallback" if decision.get("execution_role", "main") == "fallback" else "main_candidate"
        for field, role in (("main_method_id", selected_role), ("baseline_method_id", "usable_baseline")):
            references([decision[field]], methods, "selected method")
            if methods[decision[field]]["role"] != role:
                raise ValueError("Method selection role mismatch")
    spec_keys = set()
    for spec in bundle.get("model_specs", []):
        validate("model_spec", spec, root=root)
        qid = spec["question_id"]
        references([qid], decisions, "spec decision question")
        key = (qid, spec["method_id"])
        if key in spec_keys:
            raise ValueError("Duplicate model specification")
        spec_keys.add(key)
        decision = decisions[qid]
        if spec["decision_id"] != decision["decision_id"] or spec["method_id"] not in {decision["main_method_id"], decision["baseline_method_id"]}:
            raise ValueError("Spec does not implement the approved main/baseline decision")
        selected_fallback = decision.get("execution_role", "main") == "fallback" and spec["method_id"] == decision["main_method_id"]
        if selected_fallback != ("fallback_authorization" in spec):
            raise ValueError("Only the selected fallback spec must carry measured authorization")
        references(spec["variables"], symbols, "model variable")
        for variable in spec["variables"]:
            if qid not in symbols[variable]["question_ids"]:
                raise ValueError("Variable outside question scope")
        question = questions[qid]
        for field in ("metric", "sense"):
            if spec["objective"][field] != question["objective"][field]:
                raise ValueError("Model objective differs from question")
        for field in ("inputs", "outputs", "task_type", "constraints"):
            if spec[field] != question[field]:
                raise ValueError(f"Model spec changed official question {field}")
    for qid in questions:
        specs = [spec for spec in bundle.get("model_specs", []) if spec["question_id"] == qid]
        if len(specs) > 1 and any(spec["data_split"] != specs[0]["data_split"] for spec in specs[1:]):
            raise ValueError("Main and baseline must share identical evaluation splits")
    return {"status": "PASS", "scope": "modeling_contract_consistency",
            "scientific_acceptance": "NOT_RUN", "order": topological_order({k: v["depends_on"] for k, v in nodes.items()})}
