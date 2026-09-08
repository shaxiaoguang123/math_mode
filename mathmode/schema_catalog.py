"""Source definitions for generated V2 modeling schemas.

Edit this catalog, then run tools/build_contract_schemas.py. Generated standalone
schemas are distribution artifacts; CI --check must detect drift.
"""
from __future__ import annotations

TEXT = {"type": "string", "minLength": 1, "pattern": r"\S"}
ID = {"type": "string", "pattern": r"^[A-Za-z][A-Za-z0-9_.-]{0,95}$"}
PATH = {"type": "string", "minLength": 1, "pattern": r"^(?![/\\])(?!.*(?:^|[/\\])\.\.(?:[/\\]|$))(?!.*:).+$"}
HASH = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
TIME = {"type": "string", "format": "date-time"}
NUMBER = {"type": "number"}
BOOL = {"type": "boolean"}


def obj(fields, optional=()):
    return {"type": "object", "additionalProperties": False,
            "required": [k for k in fields if k not in optional], "properties": fields}


def arr(item, minimum=0, unique=False):
    return {"type": "array", "items": item, "minItems": minimum, "uniqueItems": unique}


def enum(*values):
    return {"enum": list(values)}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def mapping(item):
    return {"type": "object", "additionalProperties": item}


def contract(fields):
    return obj({"schema_version": {"const": "2.0"}, **fields})


LIMITS = obj({"timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
              "memory_mb": nullable({"type": "integer", "minimum": 1})})
SOURCE = obj({"uri": TEXT, "accessed_at": TIME, "license": TEXT})
DEPENDENCY = obj({"artifact_id": ID, "sha256": HASH})
ARTIFACT = obj({"artifact_id": ID, "path": PATH, "sha256": HASH,
    "size_bytes": {"type": "integer", "minimum": 1}, "created_at": TIME,
    "producer": ID, "depends_on": arr(DEPENDENCY),
    "status": enum("DRAFT", "VALID", "FROZEN", "STALE", "FAILED")})
TASK_TYPE = enum("regression", "optimization", "time_series", "mechanism", "simulation",
                 "graph", "classification", "decision")
OUTPUT = obj({"name": ID, "path": PATH, "format": enum("json", "csv", "xlsx", "txt"),
              "fields": arr(obj({"name": TEXT, "type": enum("number", "integer", "string", "boolean"),
                                  "unit": TEXT}), 1), "precision": {"type": "integer", "minimum": 0, "maximum": 16}})
TRIGGER = obj({"metric": TEXT, "operator": enum("gt", "ge", "lt", "le", "eq"), "threshold": NUMBER})
CONSTRAINT = obj({"constraint_id": ID, "expression": TEXT, "unit": TEXT,
                  "source_ref": TEXT, "validator": ID, "tolerance": {"type": "number", "minimum": 0}})


def catalog():
    return {
        "input_manifest": contract({"case_id": ID, "created_at": TIME, "producer": ID,
            "frozen": {"const": True}, "files": arr(obj({
                "input_id": ID, "path": PATH, "role": enum("problem", "data", "template", "rule", "description"),
                "sha256": HASH, "size_bytes": {"type": "integer", "minimum": 1},
                "source": SOURCE, "readonly": {"const": True}}), 1)}),
        "problem_frame": contract({"case_id": ID, "producer": ID, "source_refs": arr(ID, 1, True),
            "data_audit_ref": ID, "questions": arr(obj({"question_id": ID, "title": TEXT,
                "task_type": TASK_TYPE, "inputs": arr(ID, 1, True), "outputs": arr(OUTPUT, 1),
                "objective": obj({"description": TEXT, "metric": TEXT, "sense": enum("min", "max", "match", "explain")}),
                "constraints": arr(CONSTRAINT), "source_refs": arr(TEXT, 1, True),
                "resources": LIMITS}), 1)}),
        "problem_dag": contract({"nodes": arr(obj({"question_id": ID, "depends_on": arr(ID, 0, True)}), 1)}),
        "ambiguity_register": contract({"reviewed_by": ID, "reviewed_at": TIME,
            "items": arr(obj({"ambiguity_id": ID, "severity": enum("low", "medium", "high"),
                "source": TEXT, "issue": TEXT, "interpretations": arr(TEXT, 2),
                "question_ids": arr(ID, 1, True), "status": enum("unresolved", "resolved", "mitigated"),
                "resolution": nullable(TEXT), "evidence_refs": arr(TEXT)}))}),
        "assumption_ledger": contract({"entry_id": ID, "assumption_id": ID, "supersedes": nullable(ID),
            "content": TEXT, "kind": enum("necessary", "simplifying"), "source_refs": arr(TEXT, 1, True),
            "question_ids": arr(ID, 1, True), "formula_ids": arr(ID, 0, True), "validation_method": TEXT,
            "sensitivity_status": enum("pending", "tested", "not_applicable"),
            "status": enum("pending", "accepted", "rejected"), "created_at": TIME, "producer": ID}),
        "symbol_table": contract({"symbols": arr(obj({"symbol_id": ID, "symbol": TEXT,
            "meaning": TEXT, "unit": TEXT, "dimensions": mapping({"type": "integer"}), "code_name": ID,
            "domain": obj({"kind": enum("real", "integer", "boolean"), "lower": nullable(NUMBER), "upper": nullable(NUMBER)}),
            "question_ids": arr(ID, 1, True)}), 1)}),
        "method_card": contract({"question_id": ID, "methods": arr(obj({"method_id": ID,
            "role": enum("main_candidate", "usable_baseline", "conditional_fallback", "diagnostic_reference"),
            "idea": TEXT, "completes_task": BOOL, "outputs": arr(TEXT, 1, True),
            "assumption_ids": arr(ID, 0, True), "source_refs": arr(TEXT, 1, True),
            "cost": LIMITS, "fallback_trigger": nullable(TRIGGER), "validation_plan": arr(TEXT, 1),
            "rejection_reason": nullable(TEXT)}), 2),
            "critic": obj({"actor_id": ID, "findings": arr(TEXT), "evidence_refs": arr(TEXT, 1)})}),
        "risk_probe": contract({"question_id": ID, "method_id": ID, "run_id": ID,
            "checks": arr(obj({"category": enum("executability", "coverage", "assumptions", "degeneracy", "perturbation", "scale"),
                "status": enum("PASS", "CONDITIONAL", "FAIL", "NOT_APPLICABLE"),
                "evidence_refs": arr(TEXT, 1), "metrics": mapping(NUMBER), "thresholds": mapping(NUMBER), "reason": TEXT}), 6),
            "verdict": enum("PASS", "CONDITIONAL", "FAIL")}),
        "method_decision": contract({"decision_id": ID, "question_id": ID, "main_method_id": ID,
            "baseline_method_id": ID, "rationale": TEXT, "evidence_refs": arr(ID, 1, True),
            "decided_by": enum("agent", "human"), "actor_id": ID, "decided_at": TIME,
            "human_event_id": nullable(ID)}),
        "model_spec": contract({"question_id": ID, "method_id": ID, "decision_id": ID,
            "actor_id": ID, "task_type": TASK_TYPE, "variables": arr(ID, 1, True),
            "formulae": arr(obj({"formula_id": ID, "expression": TEXT,
                "input_symbols": arr(ID, 0, True), "output_symbol": ID, "unit_check": TEXT}), 1),
            "objective": obj({"metric": TEXT, "sense": enum("min", "max", "match", "explain"), "expression": TEXT}),
            "constraints": arr(CONSTRAINT), "parameters": mapping(NUMBER), "inputs": arr(ID, 1, True),
            "outputs": arr(OUTPUT, 1), "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
            "validation_plan": obj({"checks": arr(ID, 1, True), "independent_entrypoint": PATH,
                "criteria": obj({"path": PATH, "sha256": HASH})}, optional=("criteria",)),
            "implementation": obj({"entrypoint": PATH, "code_files": arr(PATH, 1, True), "language": {"const": "python"}}),
            "data_split": obj({"strategy": enum("none", "holdout", "time", "group", "rolling"),
                "train_ids": arr(TEXT, 0, True), "test_ids": arr(TEXT, 0, True), "fit_ids": arr(TEXT, 0, True),
                "target": nullable(TEXT), "features": arr(TEXT, 0, True),
                "sample_times": mapping(TIME), "sample_groups": mapping(TEXT)}), "limits": LIMITS}),
        "workflow_state": contract({"case_id": ID, "revision": {"type": "integer", "minimum": 0},
            "created_at": TIME, "updated_at": TIME, "workspace_kind": enum("competition", "fixture"),
            "interaction_mode": enum("autopilot", "human_gate"), "rigor_profile": enum("lean", "submission"),
            "blind_reference_mode": BOOL, "artifacts": arr(ARTIFACT),
            "gates": arr(obj({"gate_id": enum("G0", "G1", "G2", "G3", "G3.5", "G4", "G5", "G6", "G7", "G8"),
                "status": enum("NOT_RUN", "PASS", "WARN", "FAIL", "BLOCKED"), "artifact_refs": arr(ID),
                "checked_at": TIME, "blockers": arr(TEXT)})),
            "retry_history": arr(obj({"cause_id": ID, "category": enum("ENV_FAILURE", "DATA_FAILURE", "CODE_FAILURE", "MODEL_FAILURE", "VALIDATION_FAILURE", "POLICY_FAILURE"),
                "attempt": {"type": "integer", "minimum": 1, "maximum": 3}, "question_id": ID,
                "message": TEXT, "changed_artifacts": arr(ID), "at": TIME})),
            "reference_access": arr(obj({"source": TEXT, "question_id": ID, "same_problem": BOOL,
                                         "at": TIME, "baseline_freeze_id": nullable(ID)}))}),
        "ai_usage": contract({"event_id": ID, "timestamp": TIME, "provider": TEXT, "model": TEXT,
            "version_date": nullable(TEXT), "question_id": nullable(ID),
            "activity": enum("literature", "problem_analysis", "modeling", "coding", "visualization", "writing", "review"),
            "input_scope": arr(TEXT, 1), "output_used": BOOL, "human_postprocess": nullable(TEXT),
            "artifact_refs": arr(ID), "actor_id": ID}),
        "run_manifest": contract({"run_id": ID, "question_id": ID, "method_id": ID,
            "role": enum("main", "baseline", "probe", "validator", "fallback"), "producer": {"const": "runner"},
            "actor_id": ID, "backend": TEXT,
            "capabilities": obj({"os_sandbox": BOOL, "network_isolation": BOOL,
                "filesystem_isolation": BOOL, "memory_limit": BOOL, "cpu_limit": BOOL,
                "timeout": BOOL, "process_tree_termination": enum("best_effort", "enforced", "unsupported")}),
            "interpreter": obj({"requested": TEXT, "executable": TEXT, "sha256": HASH,
                "version": TEXT, "platform": TEXT, "packages": mapping(TEXT)}),
            "argv": arr(TEXT, 1), "cwd": TEXT, "environment": mapping(TEXT),
            "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
            "started_at": TIME, "ended_at": TIME, "duration_seconds": {"type": "number", "minimum": 0},
            "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
            "returncode": nullable({"type": "integer"}), "timed_out": BOOL,
            "status": enum("PASS", "FAIL"), "failure_class": nullable(enum("ENV_FAILURE", "DATA_FAILURE",
                "CODE_FAILURE", "MODEL_FAILURE", "VALIDATION_FAILURE", "POLICY_FAILURE")),
            "cause_id": nullable(ID), "failure_message": nullable(TEXT),
            "attempt": {"type": "integer", "minimum": 1, "maximum": 3}, "retry_of": nullable(ID),
            "spec": obj({"source_path": PATH, "source_sha256": HASH, "snapshot_path": PATH, "sha256": HASH}),
            "input_manifest_sha256": HASH,
            "inputs": arr(obj({"input_id": ID, "source_path": PATH, "snapshot_path": PATH,
                "sha256": HASH, "size_bytes": {"type": "integer", "minimum": 1}}), 1),
            "code": arr(obj({"source_path": PATH, "snapshot_path": PATH,
                "sha256": HASH, "size_bytes": {"type": "integer", "minimum": 1}}), 1),
            "outputs": arr(obj({"name": ID, "path": PATH, "sha256": HASH,
                "size_bytes": {"type": "integer", "minimum": 1}})),
            "logs": obj({"stdout": obj({"path": PATH, "sha256": HASH, "size_bytes": {"type": "integer", "minimum": 0}}),
                "stderr": obj({"path": PATH, "sha256": HASH, "size_bytes": {"type": "integer", "minimum": 0}})}),
            "control_files": arr(obj({"path": PATH, "sha256": HASH}), 1),
            "scientific_acceptance": {"const": "NOT_RUN"}}),
        "validation_criteria": contract({"criteria_id": ID, "question_id": ID,
            "task_type": enum("regression", "time_series", "optimization", "mechanism", "graph"),
            "data_input_id": ID, "main_output_name": ID, "baseline_output_name": ID,
            "source_refs": arr(TEXT, 1), "checks": arr(obj({"check_id": ID, "metric": ID,
                "operator": enum("le", "ge", "eq"), "threshold": NUMBER, "unit": TEXT,
                "source_ref": TEXT}), 1),
            "symbol_dimensions": mapping(mapping({"type": "integer"})),
            "robustness": obj({"status": enum("required", "not_applicable"), "reason": TEXT,
                "required_metrics": arr(ID, 0, True)}),
            "evaluation": obj({"sense": enum("min", "max"), "target": nullable(TEXT),
                "bootstrap_repetitions": {"type": "integer", "minimum": 0, "maximum": 10000},
                "confidence": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}})}),
        "validation_summary": contract({"validation_id": ID, "question_id": ID, "actor_id": ID,
            "created_at": TIME, "main_run": obj({"path": PATH, "sha256": HASH}),
            "baseline_run": obj({"path": PATH, "sha256": HASH}),
            "criteria": obj({"path": PATH, "sha256": HASH}),
            "validator_workspace": PATH, "validator_run": obj({"path": PATH, "sha256": HASH}),
            "validator_code": arr(obj({"path": PATH, "sha256": HASH}), 1),
            "measurements": mapping(NUMBER),
            "checks": arr(obj({"check_id": ID, "metric": ID, "value": NUMBER, "operator": enum("le", "ge", "eq"),
                "threshold": NUMBER, "unit": TEXT, "status": enum("PASS", "FAIL")}), 1),
            "status": enum("PASS", "FAIL"), "limitations": arr(TEXT)}),
        "evidence_gate": contract({"evidence_id": ID, "question_id": ID, "created_at": TIME,
            "producer": {"const": "evidence-auditor"}, "validation": obj({"path": PATH, "sha256": HASH}),
            "dependencies": arr(obj({"path": PATH, "sha256": HASH}), 1),
            "status": enum("PASS", "FAIL", "BLOCKED"), "blockers": arr(TEXT),
            "scope": {"const": "computed_model_evidence"}, "official_compliance": {"const": "NOT_RUN"}}),
    }
