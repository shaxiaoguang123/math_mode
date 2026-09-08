"""Evidence-derived phase gates and resumable numerical lifecycle coordination."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import uuid
from jsonschema import ValidationError

from .contracts import validate, unique, validate_modeling_bundle, read_ledger, topological_order
from .freeze import verify_freeze, freeze_results, freeze_events, _register_run, _bind_evidence
from .io import canonical_root, read_json, write_json, safe_path, file_hash, now, object_hash
from .lineage import ArtifactRegistry, artifact_id
from .orchestrator import Orchestrator
from .policy import load_policy, audit_policy
from .probes import measured_probe, screening_options, verify_screened_decision, verify_fallback_authorization
from .runner import execute_model, verify_run
from .state import workspace_lock
from .validation import independently_validate, audit_evidence, validate_criteria, verify_evidence_report

GATES = ("G0", "G1", "G2", "G3", "G3.5", "G4", "G5", "G6", "G7", "G8")


class Workflow:
    def __init__(self, root: Path, backend=None):
        self.root = canonical_root(root)
        self.registry = ArtifactRegistry(self.root)
        self.agents = Orchestrator(self.root, backend)

    def _contract(self, path, name):
        kind, value = self.agents._kind(path)
        if kind != name:
            raise ValueError(f"Missing current {name} handoff: {path}")
        return value

    def _review(self, path, required, question_id=None, reviewed_actor=None):
        review = self._contract(path, "semantic_review")
        if review["verdict"] != "SUPPORTED" or any(item["severity"] in {"warning", "error"} for item in review["findings"]):
            raise ValueError("Required semantic review has unresolved limitations/findings")
        if question_id is not None and review["question_id"] != question_id:
            raise ValueError("Semantic review belongs to another question")
        if reviewed_actor is not None and review["reviewed_actor_id"] != reviewed_actor:
            raise ValueError("Semantic review does not review the actual producer")
        if {artifact_id(item) for item in required} - set(review["artifact_refs"]):
            raise ValueError("Semantic review omits required artifacts")
        return review

    def _framing(self, plan):
        fields = plan["framing"]
        bundle = {name: self._contract(fields[name], name) for name in
                  ("problem_frame", "problem_dag", "symbol_table", "ambiguity_register")}
        bundle["input_manifest"] = validate("input_manifest", read_json(self.root / "input_manifest.json"), root=self.root)
        audit = self._contract("framing/deterministic_data_audit.json", "data_audit")
        if bundle["problem_frame"]["data_audit_ref"] != artifact_id("framing/deterministic_data_audit.json"):
            raise ValueError("Frame does not bind the current deterministic data audit")
        validate_modeling_bundle(bundle, root=self.root)
        self._contract(fields["assumption_ledger"], "assumption_ledger")
        assumptions = read_ledger(self.root / fields["assumption_ledger"])
        latest = {entry["assumption_id"]: entry for entry in assumptions}
        question_ids = {q["question_id"] for q in bundle["problem_frame"]["questions"]}
        for entry in latest.values():
            if set(entry["question_ids"]) - question_ids or entry["status"] == "pending":
                raise ValueError("Assumptions contain unknown questions or pending dispositions")
        self._review(fields["review"], [fields[name] for name in fields if name != "review"] +
                     ["framing/deterministic_data_audit.json"], reviewed_actor=bundle["problem_frame"]["producer"])
        if question_ids != {job["question_id"] for job in plan["questions"]}:
            raise ValueError("Workflow plan must cover every framed question exactly")
        return bundle, assumptions

    def _screened(self, job):
        card = self._contract(job["method_card"], "method_card")
        if card["question_id"] != job["question_id"]:
            raise ValueError("Method card belongs to another question")
        screening_options(self.root, job["method_card"], job["probe_reports"])
        return card

    def _decided(self, job, card):
        decision = self._contract(job["decision"], "method_decision")
        state = self.registry.store.load()
        if state["interaction_mode"] == "human_gate":
            raise ValueError("WAITING_HUMAN: host event admission is required before execution")
        if decision["decided_by"] != "agent" or decision["question_id"] != job["question_id"]:
            raise ValueError("Decision owner or question identity is invalid")
        screening = screening_options(self.root, job["method_card"], job["probe_reports"])
        verify_screened_decision(decision, screening, job["probe_reports"])
        return decision

    def _code(self, job, bundle, assumptions, card, decision):
        specs = [self._contract(job[name], "model_spec") for name in ("main_spec", "baseline_spec")]
        used = {key for method in card["methods"] for key in method["assumption_ids"]}
        latest = {entry["assumption_id"]: entry for entry in assumptions}
        if any(key not in latest or job["question_id"] not in latest[key]["question_ids"] for key in used):
            raise ValueError("Selected methods use assumptions outside this question's scope")
        selected_events = [entry for entry in assumptions if entry["assumption_id"] in used]
        validate_modeling_bundle({**bundle, "assumption_events": selected_events,
            "method_cards": [card], "method_decisions": [decision], "model_specs": specs}, root=self.root)
        if decision.get("execution_role", "main") == "fallback":
            verify_fallback_authorization(self.root, specs[0])
            screening = screening_options(self.root, job["method_card"], job["probe_reports"])
            if specs[0]["fallback_authorization"] != screening["options"]["fallback"]["authorization"]:
                raise ValueError("Fallback spec does not bind the selected decision's screening evidence")
        for spec, field in zip(specs, ("main_method_id", "baseline_method_id")):
            if spec["method_id"] != decision[field]:
                raise ValueError("Model spec is assigned to the wrong execution role")
            reference = spec["validation_plan"].get("criteria")
            if not reference or file_hash(safe_path(self.root, reference["path"])) != reference["sha256"]:
                raise ValueError("Model criteria are missing or changed before execution")
            validate_criteria(read_json(self.root / reference["path"]))
        if specs[0]["validation_plan"]["criteria"] != specs[1]["validation_plan"]["criteria"]:
            raise ValueError("Main/baseline must pin identical independent criteria")
        selection = [job["method_card"], job["decision"], *job["probe_reports"]] if decision.get("execution_role", "main") == "fallback" else []
        if specs[0]["actor_id"] == specs[1]["actor_id"]:
            required = [job["main_spec"], job["baseline_spec"], specs[0]["validation_plan"]["criteria"]["path"], *selection]
            required.extend(path for spec in specs for path in spec["implementation"]["code_files"])
            self._review(job["code_review"], required, job["question_id"], specs[0]["actor_id"])
        else:
            if not job.get("baseline_code_review"):
                raise ValueError("A different baseline producer needs its own independent code review")
            for spec, field, review_path in zip(specs, ("main_spec", "baseline_spec"), (job["code_review"], job["baseline_code_review"])):
                self._review(review_path, [job[field], spec["validation_plan"]["criteria"]["path"], *spec["implementation"]["code_files"], *selection],
                             job["question_id"], spec["actor_id"])
        return specs

    def _progress(self, plan):
        path = safe_path(self.root, "workflow_progress.json", exists=False)
        progress = read_json(path) if path.exists() else {"schema_version": "2.0", "case_id": plan["case_id"], "questions": {}}
        validate("workflow_progress", progress, root=self.root)
        if progress["case_id"] != plan["case_id"]:
            raise ValueError("Workflow progress belongs to another case")
        return progress

    def _evidence(self, summary_path, evidence_path):
        actual = verify_evidence_report(self.root, evidence_path)
        if actual["validation"]["path"] != summary_path:
            raise ValueError("Workflow evidence points to a different validation")
        return actual

    def _schedule(self, plan):
        if not self.agents.backend or not plan.get("agent_schedule"):
            return None
        schedule = read_json(safe_path(self.root, plan["agent_schedule"]))
        return self.agents.advance(schedule, max_tasks=1)

    def _reference_requests(self, plan):
        """Process one ready host-declared URL; failed/interrupted requests are preserved."""
        from .reference_retrieval import retrieve_reference, verify_retrieval
        blockers = []
        for request in plan.get("reference_requests", []):
            try:
                relative = f"references/{request['retrieval_id']}/retrieval.json"
                if safe_path(self.root, relative, exists=False).exists():
                    receipt = verify_retrieval(self.root, relative)
                    if any(receipt[key] != value for key, value in request.items()):
                        raise ValueError("Reference request changed after retrieval; declare a new explicit request")
                    continue
                receipt = retrieve_reference(self.root, **request)
                return {"performed": {"action": "retrieve-reference", "retrieval_id": receipt["retrieval_id"],
                    "status": receipt["status"]}, "blockers": blockers}
            except (ValueError, OSError, ValidationError) as error:
                blockers.append({"retrieval_id": request["retrieval_id"], "reason": str(error)})
        return {"performed": None, "blockers": blockers}

    def _review_validation(self, plan, job, record):
        if self.agents.backend is None:
            return None
        spec = self._contract(job["main_spec"], "model_spec")
        selection = [job["method_card"], job["decision"], *job["probe_reports"]] if "fallback_authorization" in spec else []
        review_path = safe_path(self.root, job["validation_review"], exists=False)
        if review_path.exists():
            try:
                existing = self._contract(job["validation_review"], "semantic_review")
            except (ValueError, OSError, ValidationError):
                pass  # Re-review changed inputs, never repeatedly solicit a better verdict.
            else:
                required = {artifact_id(path) for path in (record["validation"], record["evidence"], job["main_spec"], job["baseline_spec"], *selection)}
                if required <= set(existing["artifact_refs"]):
                    return None
        inputs = ["input_manifest.json", job["main_spec"], job["baseline_spec"], spec["validation_plan"]["criteria"]["path"],
                  record["validation"], record["evidence"], *selection]
        inputs.extend(path for name, path in plan["framing"].items() if name != "review")
        inputs.extend(item["path"] for item in read_json(self.root / "input_manifest.json")["files"])
        for role in ("main", "baseline"):
            run = verify_run(self.root, record[role + "_run"])
            inputs.extend(item["path"] for item in run["outputs"])
        qid = job["question_id"]
        attempt, previous = 1, None
        histories = []
        for path in (self.root / "agent_runs").glob("*/task.json"):
            task = read_json(safe_path(self.root, path.relative_to(self.root).as_posix()))
            if task["role"] == "validator" and task["question_id"] == qid:
                histories.append(task)
        if histories:
            latest = max(histories, key=lambda value: value["created_at"])
            result_path = self.root / "agent_runs" / latest["task_id"] / "agent_result.json"
            if not result_path.exists():
                from .recovery import verify_recovery
                recovered = verify_recovery(self.root, "agent_runs/" + latest["task_id"])
                if recovered["kind"] != "agent" or recovered["execution_id"] != latest["task_id"]:
                    raise ValueError("Interrupted validator requires its own verified recovery")
                attempt, previous = latest["attempt"] + 1, latest["task_id"]
            elif read_json(safe_path(self.root, result_path.relative_to(self.root).as_posix()))["status"] in {"FAILED", "BLOCKED"}:
                attempt, previous = latest["attempt"] + 1, latest["task_id"]
        task_id = "validation-review-" + uuid.uuid4().hex
        blueprint = {"task_id": task_id, "actor_id": "semantic-validator-" + object_hash(qid)[:16], "role": "validator",
            "question_id": qid, "instructions": "Independently review this question's original requirements, assumptions, specs, criteria and actual final outputs plus independent numerical evidence. Verify scope/units/coverage, leakage, constraints, baseline comparability, applicable sensitivity/robustness and supported claim boundaries. Cite all supplied specs, criteria, numerical summary and evidence in artifact_refs. Do not read solver source/intermediates. Do not infer final official compliance. Return an honest SUPPORTED/LIMITED/BLOCKED review; never hide limitations or seek a target verdict.",
            "inputs": sorted(set(inputs)), "outputs": [{"path": job["validation_review"], "contract": "semantic_review", "format": "json"}],
            "reviewed_actor_id": spec["actor_id"], "view": None, "depends_on": [], "attempt": attempt, "supersedes_task_id": previous}
        schedule = {"schema_version": "2.0", "case_id": plan["case_id"], "question_dag": self._contract(plan["framing"]["problem_dag"], "problem_dag"),
                    "tasks": [blueprint]}
        return self.agents.advance(schedule)

    def _run_after(self, question_id):
        after = None
        index = safe_path(self.root, "frozen_numbers.json", exists=False)
        if index.exists():
            pointer = validate("freeze_index", read_json(index), root=self.root)["questions"].get(question_id)
            if pointer and pointer["status"] == "THAWED":
                event = next(event for event in reversed(freeze_events(self.root)) if event["freeze_id"] == pointer["freeze_id"] and event["kind"] == "THAW")
                after = datetime.fromisoformat(event["timestamp"])
        return after

    def _matching_run(self, job, role):
        after = self._run_after(job["question_id"])
        execution_role = self._contract(job["decision"], "method_decision").get("execution_role", "main") if role == "main" else role
        candidates = []
        for path in (self.root / "runs").glob("*/run_manifest.json"):
            try:
                record = verify_run(self.root, path.relative_to(self.root).as_posix())
                if (record["question_id"], record["role"], record["spec"]["source_path"]) != (job["question_id"], execution_role, job[role + "_spec"]):
                    continue
                if after and datetime.fromisoformat(record["started_at"]) <= after:
                    continue
                candidates.append(record)
            except (ValueError, OSError, ValidationError):
                continue
        return max(candidates, key=lambda value: value["started_at"]) if candidates else None

    def _matching_validation(self, record):
        matches = []
        for path in (self.root / "validations").glob("*/validation_summary.json"):
            try:
                value = validate("validation_summary", read_json(safe_path(self.root, path.relative_to(self.root).as_posix())), root=self.root)
                if value["main_run"]["path"] == record["main_run"] and value["baseline_run"]["path"] == record["baseline_run"]:
                    if audit_evidence(self.root, path.relative_to(self.root).as_posix())["status"] == "PASS":
                        matches.append(value)
            except (ValueError, OSError, ValidationError):
                continue
        return max(matches, key=lambda value: value["created_at"]) if matches else None

    def _freeze_request(self, job, record):
        numbers = []
        run = verify_run(self.root, record["main_run"])
        outputs = unique(run["outputs"], "name")
        for requested in job["frozen_numbers"]:
            if requested["source"] == "validation":
                source = record["validation"]
            elif requested["output_name"] in outputs:
                source = outputs[requested["output_name"]]["path"]
            else:
                raise ValueError("Requested freeze output is absent")
            numbers.append({key: requested[key] for key in ("frozen_number_id", "claim_id", "locator", "unit", "precision")} | {"source_path": source})
        spec = read_json(self.root / job["main_spec"])
        return {"schema_version": "2.0", "actor_id": "workflow-freeze-service", "question_id": job["question_id"],
                "decision_id": spec["decision_id"], "numbers": numbers}

    def observe(self, plan: dict, *, persist=True) -> dict:
        validate("workflow_plan", plan, root=self.root)
        jobs = unique(plan["questions"], "question_id")
        if plan["case_id"] != self.registry.store.load()["case_id"]:
            raise ValueError("Workflow plan belongs to another case")
        progress = self._progress(plan)
        gate_reports = {}
        def check(gate, operation, dependencies=()):
            if any(gate_reports[dep]["status"] != "PASS" for dep in dependencies):
                gate_reports[gate] = {"status": "BLOCKED", "blockers": ["A prerequisite gate is not current"]}
                return None
            try:
                value = operation()
                gate_reports[gate] = {"status": "PASS", "blockers": []}
                return value
            except (ValueError, OSError, ValidationError) as exc:
                gate_reports[gate] = {"status": "BLOCKED", "blockers": [str(exc)]}
                return None
        def policy():
            path = safe_path(self.root, plan["policy_path"]) if plan["policy_path"] else None
            report = audit_policy(load_policy(path), self.root)
            if report["status"] != "PASS":
                raise ValueError("; ".join(report["issues"]))
        check("G0", policy)
        check("G1", lambda: validate("input_manifest", read_json(self.root / "input_manifest.json"), root=self.root))
        framed = check("G2", lambda: self._framing(plan), ("G1",))
        per_question = {}
        if framed:
            bundle, assumptions = framed
            nodes = unique(bundle["problem_dag"]["nodes"], "question_id")
            for qid in topological_order({qid: node["depends_on"] for qid, node in nodes.items()}):
                job = jobs[qid]
                status = {}
                phase = "G3"
                next_action = "screen-method"
                try:
                    card = self._screened(job)
                    status["G3"] = {"status": "PASS", "blockers": []}
                    phase, next_action = "G3.5", "decide-method"
                    decision = self._decided(job, card)
                    status["G3.5"] = {"status": "PASS", "blockers": []}
                    phase, next_action = "G4", "review-code"
                    specs = self._code(job, bundle, assumptions, card, decision)
                    for dependency in nodes[qid]["depends_on"]:
                        parent = verify_freeze(self.root, dependency)
                        for spec in specs:
                            if {item["question_id"]: item["freeze_id"] for item in spec.get("upstream_freezes", [])}.get(dependency) != parent["freeze_id"]:
                                raise ValueError("Dependent model does not consume the current parent freeze")
                    record = progress["questions"].get(qid, {})
                    for role, spec in zip(("main", "baseline"), specs):
                        execution_role = decision.get("execution_role", "main") if role == "main" else role
                        next_action = "run-" + execution_role
                        path = record.get(role + "_run")
                        if not path:
                            raise ValueError("Missing actual " + role + " execution")
                        run = verify_run(self.root, path)
                        after = self._run_after(qid)
                        if after and datetime.fromisoformat(run["started_at"]) <= after:
                            raise ValueError("Explicit thaw requires new main/baseline executions")
                        if run["question_id"] != qid or run["role"] != execution_role or run["spec"]["source_path"] != job[role + "_spec"]:
                            raise ValueError("Workflow run does not implement the selected spec/role")
                    status["G4"] = {"status": "PASS", "blockers": []}
                    phase, next_action = "G5", "independent-validate"
                    if not record.get("validation") or not record.get("evidence"):
                        raise ValueError("Independent numerical validation is missing")
                    self._evidence(record["validation"], record["evidence"])
                    summary = read_json(self.root / record["validation"])
                    if summary["main_run"]["path"] != record["main_run"] or summary["baseline_run"]["path"] != record["baseline_run"]:
                        raise ValueError("Validation belongs to different workflow runs")
                    next_action = "review-validation"
                    selection = [job["method_card"], job["decision"], *job["probe_reports"]] if decision.get("execution_role", "main") == "fallback" else []
                    review = self._review(job["validation_review"], [record["validation"], record["evidence"], job["main_spec"], job["baseline_spec"],
                                 specs[0]["validation_plan"]["criteria"]["path"], *selection], qid, specs[0]["actor_id"])
                    if review["actor_id"] in {spec["actor_id"] for spec in specs}:
                        raise ValueError("Independent semantic reviewer cannot be either solver producer")
                    status["G5"] = {"status": "PASS", "blockers": []}
                    phase, next_action = "G6", "freeze"
                    snapshot = verify_freeze(self.root, qid)
                    if snapshot["validation"]["path"] != record["validation"]:
                        raise ValueError("Active freeze belongs to a different validation")
                    requested = self._freeze_request(job, record)["numbers"]
                    actual = [{key: number[key] for key in ("frozen_number_id", "claim_id", "locator", "unit", "precision", "source_path")}
                              for number in snapshot["numbers"]]
                    if sorted(actual, key=lambda item: item["frozen_number_id"]) != sorted(requested, key=lambda item: item["frozen_number_id"]):
                        raise ValueError("Active freeze does not cover the requested claims/locators; explicit thaw is required")
                    status["G6"] = {"status": "PASS", "blockers": []}
                    next_action = "visual-and-paper"
                except (ValueError, OSError, ValidationError) as exc:
                    status[phase] = {"status": "BLOCKED", "blockers": [str(exc)]}
                for gate in ("G3", "G3.5", "G4", "G5", "G6"):
                    status.setdefault(gate, {"status": "BLOCKED", "blockers": ["Prior question phase is not current"]})
                per_question[qid] = {"gates": status, "next_action": next_action}
        for gate in ("G3", "G3.5", "G4", "G5", "G6"):
            blockers = [f"{qid}: {message}" for qid, item in per_question.items() for message in item["gates"][gate]["blockers"]]
            if not per_question:
                blockers = ["Framing is not ready"]
            gate_reports[gate] = {"status": "BLOCKED" if blockers else "PASS", "blockers": blockers}
        gate_reports["G7"] = {"status": "BLOCKED", "blockers": ["Verified visual, paper and render/format evidence is required"]}
        gate_reports["G8"] = {"status": "BLOCKED", "blockers": ["Final policy, paper and submission audits are required"]}
        if persist:
            state = self.registry.store.load()
            refs = [item["artifact_id"] for item in state["artifacts"] if item["status"] in {"VALID", "FROZEN"}]
            self.registry.store.update(lambda current: current.update(gates=[{"gate_id": gate, **gate_reports[gate],
                "artifact_refs": refs, "checked_at": now()} for gate in GATES]), expected_revision=state["revision"])
        return {"status": "PASS" if all(item["status"] == "PASS" for item in gate_reports.values()) else "BLOCKED",
                "scope": "workflow_gates", "gates": gate_reports, "questions": per_question,
                "official_compliance": gate_reports["G0"]["status"]}

    def advance(self, plan, *, interpreter=None):
        """Execute one admissible numerical transition; never silently invent a review."""
        with workspace_lock(self.root, scope="workflow"):
            return self._advance(plan, interpreter=interpreter)

    def _advance(self, plan, *, interpreter=None):
        report = self.observe(plan)
        if report["gates"]["G2"]["status"] != "PASS":
            if report["gates"]["G1"]["status"] == "PASS":
                self.agents.prepare_inputs()
            scheduled = self._schedule(plan)
            return {**self.observe(plan), "performed": {"action": "agent-schedule", "result": scheduled} if scheduled and scheduled["executed"] else None,
                    "agent_schedule": scheduled,
                    "next_owner": "framing-and-review"}
        progress = self._progress(plan)
        jobs = unique(plan["questions"], "question_id")
        reference_requests = self._reference_requests(plan)
        if reference_requests["performed"]:
            return {**self.observe(plan), **reference_requests}
        for qid, item in report["questions"].items():
            action = item["next_action"]
            job = jobs[qid]
            record = progress["questions"].setdefault(qid, {"main_run": None, "baseline_run": None, "validation": None, "evidence": None})
            if action == "screen-method" and job.get("probe_specs"):
                try:
                    self._contract(job["method_card"], "method_card")
                except (ValueError, OSError, ValidationError):
                    continue
                for spec_path, report_path in zip(job["probe_specs"], job["probe_reports"]):
                    if not safe_path(self.root, report_path, exists=False).exists():
                        try:
                            self._contract(spec_path, "model_spec")
                        except (ValueError, OSError, ValidationError):
                            continue
                        run = self._matching_run({**job, "probe_spec": spec_path}, "probe")
                        adopted = run is not None
                        if run is None:
                            run = execute_model(self.root, spec_path, role="probe", interpreter=interpreter)
                        if run["status"] != "PASS":
                            return {**report, "performed": {"question_id": qid, "action": "probe-failed", "run_id": run["run_id"]}}
                        measured = measured_probe(self.root, f"runs/{run['run_id']}/run_manifest.json")
                        write_json(self.root / report_path, measured)
                        with self.registry.batch():
                            run_id, _ = _register_run(self.registry, self.root, self.root, run)
                            self.registry.register(report_path, producer="probe-service", dependencies=[run_id])
                        return {**self.observe(plan), "performed": {"question_id": qid, "action": "adopt-probe" if adopted else "probe"}}
                continue
            if action in {"run-main", "run-fallback", "run-baseline"}:
                execution_role = action.removeprefix("run-")
                role = "main" if execution_role == "fallback" else execution_role
                # Existing/stale executions require an explicit repair/retry decision.
                run = self._matching_run(job, role)
                if record[role + "_run"] and run is None:
                    continue
                if run:
                    action = "adopt-" + execution_role
                else:
                    run = execute_model(self.root, job[role + "_spec"], role=execution_role, interpreter=interpreter)
                record[role + "_run"] = f"runs/{run['run_id']}/run_manifest.json"
                # A repaired run invalidates the old pair's numerical/semantic evidence.
                record["validation"] = record["evidence"] = None
                if run["status"] == "PASS":
                    with self.registry.batch():
                        _register_run(self.registry, self.root, self.root, run)
            elif action == "independent-validate" and record["validation"] is None:
                summary = self._matching_validation(record)
                if summary:
                    action = "adopt-validation"
                else:
                    summary = independently_validate(self.root, record["main_run"], record["baseline_run"], interpreter=interpreter)
                record["validation"] = f"validations/{summary['validation_id']}/validation_summary.json"
                evidence = audit_evidence(self.root, record["validation"])
                record["evidence"] = f"validations/{summary['validation_id']}/evidence.json"
                if (self.root / record["evidence"]).exists():
                    self._evidence(record["validation"], record["evidence"])
                else:
                    write_json(self.root / record["evidence"], evidence)
                if evidence["status"] == "PASS":
                    _bind_evidence(self.registry, self.root, record["validation"], record["evidence"])
            elif action == "freeze":
                freeze_results(self.root, self._freeze_request(job, record), record["evidence"])
            elif action == "review-validation":
                scheduled = self._review_validation(plan, job, record)
                if scheduled:
                    return {**self.observe(plan), "performed": {"question_id": qid, "action": action, "result": scheduled} if scheduled["executed"] else None,
                            "agent_schedule": scheduled}
                continue
            else:
                continue
            validate("workflow_progress", progress, root=self.root)
            write_json(self.root / "workflow_progress.json", progress)
            return {**self.observe(plan), "performed": {"question_id": qid, "action": action}}
        scheduled = self._schedule(plan)
        return {**self.observe(plan), "performed": {"action": "agent-schedule", "result": scheduled} if scheduled and scheduled["executed"] else None,
                "agent_schedule": scheduled,
                "reference_blockers": reference_requests["blockers"],
                "next_owner": "required-role-or-explicit-repair"}
