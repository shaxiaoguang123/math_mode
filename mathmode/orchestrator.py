"""Deterministic role scheduling, fresh handoffs and question dependency guards.

The scheduler transports tasks; it does not choose methods or award scientific
gates. Numerical execution/validation/freeze services retain their own checks.
"""
from __future__ import annotations

from pathlib import Path
from jsonschema import ValidationError

from .agents import run_agent_task, validate_task, verify_agent_result
from .contracts import validate, unique, topological_order, read_ledger, validate_modeling_bundle
from .data_audit import audit_inputs
from .freeze import verify_freeze
from .io import canonical_root, read_json, safe_path, now, write_json
from .lineage import ArtifactRegistry
from .probes import verify_probe, screening_options, verify_screened_decision


REQUIRED_CONTRACTS = {
    "framer": {"input_manifest", "data_audit"},
    "ambiguity": {"problem_frame"},
    "data_auditor": {"input_manifest"},
    "method_retriever": {"problem_frame", "data_audit"},
    "council": {"input_manifest", "problem_frame", "problem_dag", "symbol_table", "ambiguity_register", "data_audit"},
    "critic": {"method_proposal", "problem_frame"},
    "probe": {"method_card", "problem_frame"},
    "decision": {"method_card", "risk_probe"},
    "code": {"method_decision", "method_card", "risk_probe", "problem_frame"},
    "validator": {"model_spec", "validation_criteria"},
    "reviewer": set(),
}


def validate_schedule(schedule: dict) -> list[str]:
    validate("agent_schedule", schedule)
    if set(schedule) != {"schema_version", "case_id", "tasks", "question_dag"} or schedule["schema_version"] != "2.0":
        raise ValueError("Schedule requires schema_version, case_id, tasks and question_dag")
    tasks = unique(schedule["tasks"], "task_id")
    if not tasks:
        raise ValueError("An agent schedule cannot be empty")
    for task in tasks.values():
        if set(task) != {"task_id", "actor_id", "role", "question_id", "instructions", "inputs", "outputs",
                         "reviewed_actor_id", "view", "depends_on", "attempt", "supersedes_task_id"}:
            raise ValueError("Unknown or missing schedule task fields")
        # Reuse the canonical task validator with stand-ins only for unresolved hashes.
        # These are not persisted or accepted as evidence; dispatch resolves real hashes.
        validate_task({**{key: value for key, value in task.items() if key not in {"depends_on", "inputs"}},
                       "schema_version": "2.0", "created_at": now(), "interaction_mode": "autopilot",
                       "inputs": [{"artifact_id": f"input-{i}", "path": path, "sha256": "0" * 64}
                                  for i, path in enumerate(task["inputs"])]})
        if task["task_id"] in task["depends_on"]:
            raise ValueError("Task cannot depend on itself")
    if schedule["question_dag"] is not None:
        validate("problem_dag", schedule["question_dag"])
        questions = {node["question_id"] for node in schedule["question_dag"]["nodes"]}
        if any(task["question_id"] is not None and task["question_id"] not in questions for task in tasks.values()):
            raise ValueError("Scheduled task has an unknown question")
    return topological_order({key: value["depends_on"] for key, value in tasks.items()})


class Orchestrator:
    def __init__(self, root: Path, backend):
        self.root = canonical_root(root)
        self.backend = backend
        self.registry = ArtifactRegistry(self.root)

    def prepare_inputs(self) -> dict:
        """Register originals and recomputed statistics without changing their manifest."""
        manifest = validate("input_manifest", read_json(self.root / "input_manifest.json"), root=self.root)
        report = audit_inputs(self.root)
        relative = "framing/deterministic_data_audit.json"
        existing = safe_path(self.root, relative, exists=False)
        if existing.exists():
            prior = read_json(existing)
            report["created_at"] = prior["created_at"]
        write_json(existing, report)
        with self.registry.batch():
            originals = [self.registry.register(item["path"], producer="preflight") for item in manifest["files"]]
            manifest_id = self.registry.register("input_manifest.json", producer="preflight", dependencies=originals)
            self.registry.register(relative, producer="data-auditor-tool", dependencies=[manifest_id])
        return report

    def _kind(self, relative: str) -> tuple[str | None, object]:
        path = safe_path(self.root, relative)
        if relative == "input_manifest.json":
            return "input_manifest", validate("input_manifest", read_json(path), root=self.root)
        if relative == "framing/deterministic_data_audit.json":
            report = validate("data_audit", read_json(path), root=self.root)
            current = audit_inputs(self.root)
            current["created_at"] = report["created_at"]
            if report != current or report["status"] != "PASS":
                raise ValueError("Data audit is stale or has unresolved input issues")
            return "data_audit", report
        # Canonical role contracts require the original successful reasoning call.
        runs = safe_path(self.root, "agent_runs", exists=False)
        if runs.exists():
            for task_path in sorted(runs.glob("*/task.json"), reverse=True):
                task = read_json(safe_path(self.root, task_path.relative_to(self.root).as_posix()))
                for output in task["outputs"]:
                    if output["path"] == relative and output["contract"] and output["contract"] != "data_audit":
                        result_path = task_path.with_name("agent_result.json")
                        if not result_path.exists() or read_json(result_path)["status"] != "PRODUCED":
                            continue
                        try:
                            verify_agent_result(self.root, task["task_id"])
                        except ValueError:
                            continue
                        if output["format"] == "jsonl":
                            return output["contract"], read_ledger(path, output["contract"])[-1]
                        return output["contract"], validate(output["contract"], read_json(path), root=self.root)
        # Probe reports have independently recomputable process provenance.
        if path.suffix == ".json":
            value = read_json(path)
            if isinstance(value, dict) and {"retrieval_id", "requests", "snapshot"} <= value.keys():
                from .reference_retrieval import verify_retrieval
                return "reference_retrieval", verify_retrieval(self.root, relative)
            if isinstance(value, dict) and {"run_id", "checks", "verdict"} <= value.keys():
                return "risk_probe", verify_probe(self.root, relative, f"runs/{value['run_id']}/run_manifest.json")
            if isinstance(value, dict) and {"criteria_id", "checks", "symbol_dimensions"} <= value.keys():
                from .validation import validate_criteria
                manifest = validate("input_manifest", read_json(self.root / "input_manifest.json"), root=self.root)
                if any(item["path"] == relative and item["role"] == "rule" for item in manifest["files"]):
                    return "validation_criteria", validate_criteria(value)
            if isinstance(value, dict) and {"validation_id", "validator_run", "measurements"} <= value.keys():
                from .validation import audit_evidence
                if audit_evidence(self.root, relative)["status"] == "PASS":
                    return "validation_summary", validate("validation_summary", value, root=self.root)
            if isinstance(value, dict) and {"evidence_id", "validation", "dependencies"} <= value.keys():
                from .validation import verify_evidence_report
                return "evidence_gate", verify_evidence_report(self.root, relative)
        return None, None

    def _guard(self, blueprint, task, schedule):
        role = task["role"]
        if role in {"visual", "writer"}:
            raise ValueError("Visual/paper dispatch requires the T09 audited handoff adapter")
        if role in {"decision", "code"} and task["interaction_mode"] == "human_gate":
            raise ValueError("WAITING_HUMAN: an actual host user event must supply the decision")
        if role in {"critic", "validator", "reviewer"}:
            registered = {entry["artifact_id"]: entry for entry in self.registry.store.load()["artifacts"]}
            if not any(registered[item["artifact_id"]]["producer"] == task["reviewed_actor_id"] for item in task["inputs"]):
                raise ValueError("Review must include work from the declared different producer")
        kinds = {}
        for item in task["inputs"]:
            kind, value = self._kind(item["path"])
            if kind:
                kinds.setdefault(kind, []).append(value)
        missing = REQUIRED_CONTRACTS[role] - kinds.keys()
        if missing:
            raise ValueError("Missing fresh phase prerequisites: " + ", ".join(sorted(missing)))
        if role == "method_retriever":
            supplied = {item["path"]: item["sha256"] for item in task["inputs"]}
            for receipt in kinds.get("reference_retrieval", []):
                if receipt["question_id"] != task["question_id"] or supplied.get(receipt["snapshot"]["path"]) != receipt["snapshot"]["sha256"]:
                    raise ValueError("Method retrieval requires the same question's actual downloaded snapshot")
            verified_paths = {receipt["snapshot"]["path"] for receipt in kinds.get("reference_retrieval", [])}
            if any(path.startswith("references/") and path.endswith("/body.bin") and path not in verified_paths for path in supplied):
                raise ValueError("Downloaded method inputs require their actual retrieval receipt")
        if role == "council":
            validate_modeling_bundle({name: kinds[name][0] for name in
                ("input_manifest", "problem_frame", "problem_dag", "symbol_table", "ambiguity_register")}, root=self.root)
        qid = task["question_id"]
        for kind in ("method_card", "risk_probe", "method_decision", "model_spec", "validation_criteria"):
            if any(value["question_id"] != qid for value in kinds.get(kind, [])):
                raise ValueError("Phase prerequisite belongs to another question")
        for register in kinds.get("ambiguity_register", []):
            if any(item["severity"] == "high" and item["status"] != "resolved" for item in register["items"]):
                raise ValueError("Unresolved high-severity ambiguity blocks modeling")
        fallback_validation = role == "validator" and any("fallback_authorization" in spec for spec in kinds.get("model_spec", []))
        if fallback_validation and {"method_card", "risk_probe", "method_decision"} - kinds.keys():
            raise ValueError("Fallback validation requires its actual decision, trigger card and both screening reports")
        if role in {"decision", "code"} or fallback_validation:
            if len(kinds["method_card"]) != 1:
                raise ValueError("Decision/code requires exactly one current method card")
            card_path = next(item["path"] for item in task["inputs"] if self._kind(item["path"])[0] == "method_card")
            report_paths = [item["path"] for item in task["inputs"] if self._kind(item["path"])[0] == "risk_probe"]
            screening = screening_options(self.root, card_path, report_paths)
            if role == "code" or fallback_validation:
                if len(kinds["method_decision"]) != 1:
                    raise ValueError("Code requires exactly one current decision")
                decision = kinds["method_decision"][0]
                if decision["decided_by"] != "agent":
                    raise ValueError("Code task does not consume the current screened agent decision")
                selected_role = verify_screened_decision(decision, screening, report_paths)
                if fallback_validation and (selected_role != "fallback" or any(
                        spec["method_id"] != decision["main_method_id"] for spec in kinds["model_spec"] if "fallback_authorization" in spec)):
                    raise ValueError("Fallback validation does not consume the selected production spec")
        if role in {"code", "validator", "reviewer"} and qid:
            if schedule["question_dag"] is None:
                raise ValueError("Question execution requires an explicit framed DAG")
            nodes = unique(schedule["question_dag"]["nodes"], "question_id")
            if not any(value == schedule["question_dag"] for value in kinds.get("problem_dag", [])):
                raise ValueError("Question DAG requires a fresh framed handoff in the input bundle")
            for dependency in nodes[qid]["depends_on"]:
                verify_freeze(self.root, dependency)
        if role == "validator":
            # Only original inputs, specs/criteria and actual final outputs are admitted.
            manifest = read_json(self.root / "input_manifest.json")
            allowed = {item["path"] for item in manifest["files"]}
            for item in task["inputs"]:
                kind, _ = self._kind(item["path"])
                if kind in {"input_manifest", "problem_frame", "problem_dag", "symbol_table", "ambiguity_register", "assumption_ledger",
                            "method_card", "method_decision", "risk_probe",
                            "model_spec", "validation_criteria", "validation_summary", "evidence_gate"}:
                    allowed.add(item["path"])
            from .runner import verify_run
            for run_path in (self.root / "runs").glob("*/run_manifest.json"):
                relative = run_path.relative_to(self.root).as_posix()
                record = read_json(safe_path(self.root, relative))
                if record["question_id"] == qid and record["role"] in {"main", "fallback", "baseline"}:
                    try:
                        verified = verify_run(self.root, relative)
                    except (ValueError, OSError, ValidationError):
                        continue  # Historical failed/stale outputs cannot enter the bundle.
                    allowed.update(item["path"] for item in verified["outputs"])
            if {item["path"] for item in task["inputs"]} - allowed:
                raise ValueError("Validator bundle includes solver source/intermediates or unapproved inputs")

    def advance(self, schedule: dict, *, max_tasks=1, timeout=300) -> dict:
        """Run up to max_tasks ready roles, rechecking prior handoffs on every resume."""
        if not isinstance(max_tasks, int) or max_tasks < 1:
            raise ValueError("max_tasks must be a positive integer")
        order = validate_schedule(schedule)
        state = self.registry.store.load()
        if schedule["case_id"] != state["case_id"]:
            raise ValueError("Agent schedule belongs to another workspace")
        tasks = unique(schedule["tasks"], "task_id")
        completed, blocked, executed = [], {}, []
        for key in order:
            blueprint = tasks[key]
            result_path = safe_path(self.root, f"agent_runs/{key}/agent_result.json", exists=False)
            try:
                if set(blueprint["depends_on"]) - set(completed):
                    raise ValueError("Upstream role handoff is missing, failed or stale")
                if result_path.exists():
                    verify_agent_result(self.root, key)
                    actual_task = read_json(result_path.with_name("task.json"))
                    for field, value in blueprint.items():
                        if field not in {"depends_on", "inputs"} and actual_task[field] != value:
                            raise ValueError("Schedule changed an already executed task")
                    if [item["path"] for item in actual_task["inputs"]] != blueprint["inputs"]:
                        raise ValueError("Schedule changed an already executed input scope")
                    self._guard(blueprint, actual_task, schedule)
                    completed.append(key)
                    continue
                if len(executed) >= max_tasks:
                    continue
                fresh = self.registry.store.inspect_freshness()
                registered = {item["path"]: item for item in self.registry.store.load()["artifacts"]}
                inputs = []
                for relative in blueprint["inputs"]:
                    entry = registered.get(relative)
                    if not entry or entry["artifact_id"] in fresh["stale"]:
                        raise ValueError("Missing/stale scheduled input: " + relative)
                    inputs.append({field: entry[field] for field in ("artifact_id", "path", "sha256")})
                task = {**{field: value for field, value in blueprint.items() if field not in {"depends_on", "inputs"}},
                        "schema_version": "2.0", "inputs": inputs, "created_at": now(),
                        "interaction_mode": state["interaction_mode"]}
                self._guard(blueprint, task, schedule)
                result = run_agent_task(self.root, task, self.backend, timeout=timeout)
                executed.append(key)
                if result["status"] == "PRODUCED":
                    verify_agent_result(self.root, key)
                    completed.append(key)
                else:
                    blocked[key] = result["blockers"]
            except (ValueError, OSError) as exc:
                blocked[key] = [str(exc)]
        return {"status": "BLOCKED" if blocked else "PASS" if len(completed) == len(tasks) else "PENDING",
                "scope": "agent_schedule", "completed": completed, "executed": executed, "blocked": blocked,
                "pending": [key for key in order if key not in completed and key not in blocked],
                "scientific_acceptance": "NOT_RUN", "official_compliance": "NOT_RUN"}
