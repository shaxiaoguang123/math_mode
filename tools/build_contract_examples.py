"""Generate explicitly synthetic examples, never scientific acceptance records."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathmode.io import write_json, file_hash
from mathmode.state import initial_state


def build():
    root = Path(__file__).resolve().parents[1] / "fixtures/contracts"
    root.mkdir(parents=True, exist_ok=True)
    (root / "problem.txt").write_bytes(b"SYNTHETIC CONTRACT FIXTURE: estimate y = a*x + b from training data.\n")
    stamp = "2026-09-08T00:00:00Z"
    source = {"uri": "fixture://synthetic-contract-example", "accessed_at": stamp,
              "license": "Repository-authored synthetic fixture"}
    limit = {"timeout_seconds": 30, "memory_mb": None}
    out = {"name": "prediction", "path": "results/predictions.json", "format": "json",
           "fields": [{"name": "value", "type": "number", "unit": "1"}], "precision": 6}
    files = [{"input_id": "problem", "path": "problem.txt", "role": "problem",
              "sha256": file_hash(root / "problem.txt"), "size_bytes": (root / "problem.txt").stat().st_size,
              "source": source, "readonly": True}]
    samples = {
        "input_manifest": {"case_id": "contract-fixture", "created_at": stamp, "producer": "preflight", "frozen": True, "files": files},
        "problem_frame": {"case_id": "contract-fixture", "producer": "framer", "source_refs": ["problem"],
            "data_audit_ref": "data-audit", "questions": [{"question_id": "Q1", "title": "Synthetic prediction task",
                "task_type": "regression", "inputs": ["problem"], "outputs": [out],
                "objective": {"description": "Estimate holdout responses", "metric": "mse", "sense": "min"},
                "constraints": [], "source_refs": ["problem:line1"], "resources": limit}]},
        "problem_dag": {"nodes": [{"question_id": "Q1", "depends_on": []}]},
        "ambiguity_register": {"reviewed_by": "ambiguity-auditor", "reviewed_at": stamp, "items": []},
        "assumption_ledger": {"entry_id": "assumption-event1", "assumption_id": "linearity", "supersedes": None,
            "content": "An affine response is a candidate approximation.", "kind": "simplifying",
            "source_refs": ["problem:line1"], "question_ids": ["Q1"], "formula_ids": ["affine"],
            "validation_method": "Compare residual structure on held-out observations.",
            "sensitivity_status": "pending", "status": "pending", "created_at": stamp, "producer": "modeler"},
        "symbol_table": {"symbols": [{"symbol_id": name, "symbol": name, "meaning": meaning,
            "unit": "1", "dimensions": {}, "code_name": name,
            "domain": {"kind": "real", "lower": None, "upper": None}, "question_ids": ["Q1"]}
            for name, meaning in [("x", "input"), ("y", "prediction"), ("a", "slope"), ("b", "intercept")]]},
        "method_card": {"question_id": "Q1", "methods": [{"method_id": mid, "role": role, "idea": idea,
            "completes_task": True, "outputs": ["prediction"],
            "assumption_ids": ["linearity"] if mid == "affine-main" else [], "source_refs": ["problem:line1"],
            "cost": limit, "fallback_trigger": None, "validation_plan": ["Independently recompute holdout MSE."],
            "rejection_reason": None} for mid, role, idea in [
                ("affine-main", "main_candidate", "Least squares affine fit"),
                ("mean-baseline", "usable_baseline", "Training mean prediction")]],
            "critic": {"actor_id": "critic", "findings": [], "evidence_refs": ["fixture-design:synthetic-only"]}},
        "risk_probe": {"question_id": "Q1", "method_id": "affine-main", "run_id": "not-executed-example",
            "checks": [{"category": c, "status": "FAIL", "evidence_refs": ["fixture-design:unexecuted"],
                "metrics": {}, "thresholds": {}, "reason": "Contract illustration has no executed risk probe."}
                for c in ["executability", "coverage", "assumptions", "degeneracy", "perturbation", "scale"]], "verdict": "FAIL"},
        "method_decision": {"decision_id": "decision1", "question_id": "Q1", "main_method_id": "affine-main",
            "baseline_method_id": "mean-baseline", "rationale": "Illustrative contract selection; runtime approval NOT_RUN.",
            "evidence_refs": ["illustrative-probe"], "decided_by": "agent", "actor_id": "decision-agent",
            "decided_at": stamp, "human_event_id": None},
        "model_spec": {"question_id": "Q1", "method_id": "affine-main", "decision_id": "decision1", "actor_id": "modeler",
            "task_type": "regression", "variables": ["x", "y", "a", "b"], "formulae": [{"formula_id": "affine",
                "expression": "y=a*x+b", "input_symbols": ["x", "a", "b"], "output_symbol": "y",
                "unit_check": "All variables and terms dimensionless."}],
            "objective": {"metric": "mse", "sense": "min", "expression": "mean((y-y_hat)^2)"},
            "constraints": [], "parameters": {}, "inputs": ["problem"], "outputs": [out], "seed": 42,
            "validation_plan": {"checks": ["holdout-mse"], "independent_entrypoint": "validators/prediction.py"},
            "implementation": {"entrypoint": "code/prediction.py", "code_files": ["code/prediction.py"], "language": "python"},
            "data_split": {"strategy": "holdout", "train_ids": ["row1", "row2"], "test_ids": ["row3"],
                "fit_ids": ["row1", "row2"], "target": "observed_y", "features": ["x"],
                "sample_times": {}, "sample_groups": {}}, "limits": limit},
        "workflow_state": initial_state("contract-fixture", "fixture"),
        "ai_usage": {"event_id": "example-event", "timestamp": stamp, "provider": "synthetic-example",
            "model": "not-an-actual-provider-call", "version_date": None, "question_id": "Q1", "activity": "modeling",
            "input_scope": ["synthetic fixture only"], "output_used": False, "human_postprocess": None,
            "artifact_refs": [], "actor_id": "example-actor"},
    }
    samples["workflow_state"].update(created_at=stamp, updated_at=stamp)
    for name, value in samples.items():
        value["schema_version"] = "2.0"
        write_json(root / (name + ".json"), value)
    bundle = {k: samples[k] for k in ["input_manifest", "problem_frame", "problem_dag", "ambiguity_register", "symbol_table"]}
    bundle.update(method_cards=[samples["method_card"]], method_decisions=[samples["method_decision"]],
                  model_specs=[samples["model_spec"]], assumption_events=[samples["assumption_ledger"]])
    write_json(root / "modeling_bundle.json", bundle)


if __name__ == "__main__":
    build()
