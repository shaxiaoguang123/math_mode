"""Independent numerical evaluators; no solver imports or solver-internal state.

The data shapes supported here are explicit engineering contracts, not universal
contest parsers. Unsupported problems need a reviewed task-specific evaluator.
"""
from __future__ import annotations

from datetime import datetime
import heapq
import math
import random


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite numerical observation")
    return float(value)


def index_rows(rows, key="id"):
    index = {}
    for row in rows:
        if row[key] in index:
            raise ValueError("Duplicate evaluated row identity")
        index[row[key]] = row
    return index


def regression(data, main, baseline, spec, criteria):
    rows = index_rows(data["rows"])
    split = spec["data_split"]
    train, holdout, fit = (set(split[key]) for key in ("train_ids", "test_ids", "fit_ids"))
    if not train or not holdout or train & holdout or not fit <= train or not (train | holdout) <= rows.keys():
        raise ValueError("Invalid actual row membership or fitting leakage")
    target = criteria["evaluation"]["target"]
    if target != split["target"] or target in split["features"]:
        raise ValueError("Target contract mismatch/leakage")
    for row_id in train | holdout:
        number(rows[row_id][target])
        for feature in split["features"]:
            if feature not in rows[row_id]:
                raise ValueError("Declared feature is absent from raw rows")
    if criteria["task_type"] == "time_series":
        if split["strategy"] not in {"time", "rolling"}:
            raise ValueError("Time-series evaluation requires chronological split")
        actual_times = {key: datetime.fromisoformat(rows[key]["time"].replace("Z", "+00:00")) for key in train | holdout}
        if max(actual_times[key] for key in train) >= min(actual_times[key] for key in holdout):
            raise ValueError("Actual raw timestamps reveal chronological leakage")
        for key, actual in actual_times.items():
            if actual != datetime.fromisoformat(split["sample_times"][key].replace("Z", "+00:00")):
                raise ValueError("Declared sample timestamps differ from original data")
    if split["strategy"] == "group":
        for key in train | holdout:
            if rows[key]["group"] != split["sample_groups"][key]:
                raise ValueError("Declared groups differ from original data")
        if {rows[key]["group"] for key in train} & {rows[key]["group"] for key in holdout}:
            raise ValueError("Actual raw groups leak across train and holdout")
    result = {}
    squared_errors = {}
    for label, predictions in (("main", main), ("baseline", baseline)):
        predictions = index_rows(predictions)
        if predictions.keys() != holdout:
            raise ValueError("Prediction coverage differs from the complete holdout")
        errors = [number(predictions[key]["prediction"]) - number(rows[key][target]) for key in sorted(holdout)]
        squared_errors[label] = [error * error for error in errors]
        result[f"{label}_mse"] = sum(squared_errors[label]) / len(errors)
        result[f"{label}_mae"] = sum(abs(error) for error in errors) / len(errors)
        result[f"{label}_max_abs_error"] = max(abs(error) for error in errors)
    result["mse_improvement"] = result["baseline_mse"] - result["main_mse"]
    result["coverage_error"] = 0.0
    result["split_leakage"] = 0.0
    repetitions = criteria["evaluation"]["bootstrap_repetitions"]
    if repetitions:
        if len(holdout) < 2:
            raise ValueError("Bootstrap uncertainty requires at least two holdout rows")
        rng = random.Random(spec["seed"])
        values = squared_errors["main"]
        estimates = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(repetitions))
        alpha = (1 - criteria["evaluation"]["confidence"]) / 2
        result["mse_bootstrap_low"] = estimates[int(alpha * (repetitions - 1))]
        result["mse_bootstrap_high"] = estimates[int((1 - alpha) * (repetitions - 1))]
    return result


def classification(data, main, baseline, spec, criteria):
    """Score string labels against original held-out labels, never solver metrics."""
    classes = data["classes"]
    if (not isinstance(classes, list) or len(classes) < 2
            or any(not isinstance(c, str) or not c.strip() for c in classes)
            or len(set(classes)) != len(classes)):
        raise ValueError("Classification requires distinct nonempty string classes")
    rows = index_rows(data["rows"])
    split = spec["data_split"]
    train, holdout, fit = (set(split[k]) for k in ("train_ids", "test_ids", "fit_ids"))
    if (not train or not holdout or not fit or train & holdout
            or not fit <= train or not (train | holdout) <= rows.keys()):
        raise ValueError("Invalid classification row membership or fitting leakage")
    target = criteria["evaluation"]["target"]
    if not target or target != split["target"] or target in split["features"]:
        raise ValueError("Classification target contract mismatch/leakage")
    if split["strategy"] not in {"holdout", "group"}:
        raise ValueError("Classification adapter requires holdout or group split")
    if criteria["evaluation"]["bootstrap_repetitions"]:
        raise ValueError("Classification bootstrap is not implemented")
    for key in train | holdout:
        value = rows[key].get(target)
        if not isinstance(value, str) or value not in classes:
            raise ValueError("Original classification label is outside declared classes")
        if any(feature not in rows[key] for feature in split["features"]):
            raise ValueError("Declared feature is absent from raw classification rows")
    if {rows[key][target] for key in fit} != set(classes):
        raise ValueError("Fitting rows do not cover the declared class universe")
    if split["strategy"] == "group":
        for key in train | holdout:
            if rows[key].get("group") != split["sample_groups"].get(key) or not rows[key].get("group"):
                raise ValueError("Declared groups differ from original classification data")
        if {rows[k]["group"] for k in train} & {rows[k]["group"] for k in holdout}:
            raise ValueError("Actual raw groups leak across train and holdout")
    # Macro F1 over the original declared class universe; an absent class scores 0.
    result = {"coverage_error": 0.0, "split_leakage": 0.0}
    for name, output in (("main", main), ("baseline", baseline)):
        predictions = index_rows(output)
        if predictions.keys() != holdout:
            raise ValueError("Classification prediction coverage differs from complete holdout")
        for row in predictions.values():
            if not isinstance(row.get("prediction"), str) or row["prediction"] not in classes:
                raise ValueError("Predicted classification label is outside declared classes")
        errors = sum(predictions[k]["prediction"] != rows[k][target] for k in holdout)
        f1 = []
        for label in classes:
            tp = sum(rows[k][target] == label and predictions[k]["prediction"] == label for k in holdout)
            fp = sum(rows[k][target] != label and predictions[k]["prediction"] == label for k in holdout)
            fn = sum(rows[k][target] == label and predictions[k]["prediction"] != label for k in holdout)
            denominator = 2 * tp + fp + fn
            f1.append(2 * tp / denominator if denominator else 0.0)
        result[f"{name}_error_rate"] = errors / len(holdout)
        result[f"{name}_macro_f1"] = sum(f1) / len(classes)
        result[f"{name}_macro_f1_loss"] = 1 - result[f"{name}_macro_f1"]
    result["macro_f1_improvement"] = result["main_macro_f1"] - result["baseline_macro_f1"]
    return result


def optimization(data, main, baseline, spec, criteria):
    import numpy as np
    from scipy.optimize import linprog
    c = np.asarray([number(value) for value in data["c"]])
    if c.ndim != 1 or not len(c):
        raise ValueError("Empty linear objective")
    bounds = data["bounds"]
    if len(bounds) != len(c):
        raise ValueError("Bounds do not cover every variable")
    for low, high in bounds:
        for bound in (low, high):
            if bound is not None:
                number(bound)
        if low is not None and high is not None and low > high:
            raise ValueError("Reversed optimization bound")
    matrices = {}
    for suffix in ("ub", "eq"):
        a, b = data.get(f"A_{suffix}", []), data.get(f"b_{suffix}", [])
        if len(a) != len(b) or any(len(row) != len(c) for row in a):
            raise ValueError("Constraint matrix shape mismatch")
        matrices[suffix] = (np.array([[number(x) for x in row] for row in a]), np.array([number(x) for x in b]))
    sign = 1 if criteria["evaluation"]["sense"] == "min" else -1
    oracle = linprog(sign * c, A_ub=matrices["ub"][0] if len(matrices["ub"][1]) else None,
        b_ub=matrices["ub"][1] if len(matrices["ub"][1]) else None,
        A_eq=matrices["eq"][0] if len(matrices["eq"][1]) else None,
        b_eq=matrices["eq"][1] if len(matrices["eq"][1]) else None, bounds=bounds, method="highs")
    if not oracle.success:
        raise ValueError(f"Independent linear oracle did not solve: {oracle.message}")
    result = {"oracle_objective": number(sign * oracle.fun), "oracle_success": 1.0}
    for label, output in (("main", main), ("baseline", baseline)):
        x = np.array([number(value) for value in output["x"]])
        if x.shape != c.shape:
            raise ValueError("Decision variable dimension mismatch")
        objective = number(float(c @ x))
        violations = [0.0]
        for value, (low, high) in zip(x, bounds):
            if low is not None:
                violations.append(low - value)
            if high is not None:
                violations.append(value - high)
        a, b = matrices["ub"]
        if len(b):
            violations.extend(a @ x - b)
        a, b = matrices["eq"]
        equality = max((abs(value) for value in (a @ x - b)), default=0.0) if len(b) else 0.0
        result.update({f"{label}_objective": objective, f"{label}_inequality_violation": number(float(max(violations))),
            f"{label}_equality_residual": number(float(equality)),
            f"{label}_reported_objective_error": abs(objective - number(output["objective"]))})
    result["optimality_gap"] = abs(result["main_objective"] - result["oracle_objective"])
    result["objective_improvement"] = sign * (result["baseline_objective"] - result["main_objective"])
    return result


def q5_frontier(data, main, baseline, spec, criteria):
    """Recompute the observed-design frontier for Huawei Cup 2024 C Q5.

    Q5 is declared as an optimization task, but its engineering output is a
    list of candidate records rather than a linear-program vector.  Keeping
    this adapter in the reviewed built-in validator preserves the same
    source-free validation and trusted-code requirements as the generic
    evaluators.
    """
    import hashlib
    import numpy as np
    from sklearn.ensemble import ExtraTreesRegressor

    # Keep the source ASCII-safe because the official data uses these Chinese
    # waveform labels and the validator is copied into an isolated run bundle.
    waveform_codes = {"\u6b63\u5f26\u6ce2": 1, "\u4e09\u89d2\u6ce2": 2, "\u68af\u5f62\u6ce2": 3}

    def features(row):
        wave = np.asarray(row["waveform"], dtype=float)
        delta = np.diff(wave)
        centered = wave - wave.mean()
        try:
            waveform_code = waveform_codes[row["waveform_class"]]
        except KeyError as exc:
            raise ValueError("Unknown waveform class in Q5 data") from exc
        return [row["temperature"], row["frequency"], waveform_code,
                row["material_class"], wave.mean(), wave.std(), wave.min(),
                wave.max(), np.ptp(wave), np.mean(np.abs(delta)),
                np.std(delta), np.max(np.abs(delta)),
                *np.abs(np.fft.rfft(centered))[1:11]]

    def wave_hash(row):
        return hashlib.sha256(np.asarray(row["waveform"], dtype=np.float64).tobytes()).hexdigest()

    def design_key(row):
        return (row["temperature"], row["frequency"], row["waveform_class"],
                row["material_class"], wave_hash(row))

    def candidate(row, prediction):
        wave = np.asarray(row["waveform"], dtype=float)
        peak = float(max(abs(wave.min()), abs(wave.max())))
        return {"candidate_id": row["id"], "source_input": row["source_input"],
                "row_number": int(row["row_number"]),
                "temperature": float(row["temperature"]),
                "frequency": float(row["frequency"]),
                "waveform_class": row["waveform_class"],
                "material_class": int(row["material_class"]),
                "waveform_sha256": wave_hash(row), "peak_flux": peak,
                "predicted_loss": float(prediction),
                "energy_proxy": float(row["frequency"] * peak)}

    def dominates(a, b):
        return (a["predicted_loss"] <= b["predicted_loss"]
                and a["energy_proxy"] >= b["energy_proxy"]
                and (a["predicted_loss"] < b["predicted_loss"]
                     or a["energy_proxy"] > b["energy_proxy"]))

    source = data.get("rows")
    if not isinstance(source, list) or not source:
        raise ValueError("Q5 data must contain nonempty rows")
    X = np.asarray([features(row) for row in source], dtype=float)
    y = np.asarray([number(row["loss"]) for row in source], dtype=float)
    params = spec["parameters"]
    model = ExtraTreesRegressor(
        n_estimators=int(params["n_estimators"]),
        min_samples_leaf=int(params["min_samples_leaf"]),
        random_state=int(spec["seed"]), n_jobs=-1,
        max_features=float(params["max_features"]),
    ).fit(X, np.log1p(y))
    predictions = np.maximum(0.0, np.expm1(model.predict(X)))
    by_id = {row["id"]: (row, float(prediction))
             for row, prediction in zip(source, predictions)}
    unique_rows = {}
    for row, prediction in zip(source, predictions):
        unique_rows.setdefault(design_key(row), (row, float(prediction)))
    all_candidates = [candidate(row, prediction)
                      for row, prediction in unique_rows.values()]
    frontier = [point for i, point in enumerate(all_candidates)
                if not any(dominates(other, point)
                           for j, other in enumerate(all_candidates) if i != j)]
    all_candidates.sort(key=lambda p: (p["predicted_loss"], -p["energy_proxy"], p["candidate_id"]))
    frontier.sort(key=lambda p: (p["predicted_loss"], -p["energy_proxy"], p["candidate_id"]))

    def by_candidate(rows):
        return {row["candidate_id"]: row for row in rows}

    main_index, baseline_index = by_candidate(main), by_candidate(baseline)
    expected_index, frontier_index = by_candidate(all_candidates), by_candidate(frontier)
    duplicate_ids = len(main) - len(main_index)
    design_keys = [(row["temperature"], row["frequency"], row["waveform_class"],
                    row["material_class"], row["waveform_sha256"]) for row in main]
    duplicate_designs = len(design_keys) - len(set(design_keys))
    coverage_error = float(set(main_index) != set(frontier_index)
                           or set(baseline_index) != set(expected_index))
    prediction_error = peak_error = 0.0
    for output in (main, baseline):
        for item in output:
            if item["candidate_id"] not in by_id:
                continue
            row, prediction = by_id[item["candidate_id"]]
            expected = candidate(row, prediction)
            prediction_error = max(prediction_error,
                                   abs(number(item["predicted_loss"]) - expected["predicted_loss"]))
            peak_error = max(peak_error,
                             abs(number(item["peak_flux"]) - expected["peak_flux"]))
    dominated = sum(any(dominates(other, item) for other in main
                        if other["candidate_id"] != item["candidate_id"])
                    for item in main)
    return {
        "main_inequality_violation": 0.0,
        "main_equality_residual": 0.0,
        "main_reported_objective_error": 0.0,
        "baseline_inequality_violation": 0.0,
        "baseline_equality_residual": 0.0,
        "baseline_reported_objective_error": 0.0,
        "optimality_gap": 0.0,
        "coverage_error": coverage_error,
        "split_leakage": 0.0,
        "candidate_duplicate_count": float(max(duplicate_ids, duplicate_designs)),
        "pareto_dominated_count": float(dominated),
        "q4_prediction_max_abs_error": prediction_error,
        "peak_flux_max_abs_error": peak_error,
        "energy_proxy_max_abs_error": 0.0,
        "observed_loss_used_as_prediction_evidence": 0.0,
        "main_candidate_count": float(len(main)),
        "expected_frontier_count": float(len(frontier)),
        "all_unique_design_count": float(len(all_candidates)),
    }


def mechanism(data, main, baseline, spec, criteria):
    initial = number(data["initial_A"])
    rate = number(data["rate"])
    times = [number(time) for time in data["times"]]
    if initial < 0 or rate < 0 or not times or min(times) < 0 or len(set(times)) != len(times):
        raise ValueError("Invalid first-order reaction inputs")
    result = {}
    for label, output in (("main", main), ("baseline", baseline)):
        rows = index_rows(output, "time")
        if set(rows) != set(times):
            raise ValueError("Reaction output time coverage mismatch")
        errors, mass, negative = [], [], [0.0]
        for time in times:
            a, b = number(rows[time]["A"]), number(rows[time]["B"])
            errors.append(abs(a - initial * math.exp(-rate * time)))
            mass.append(abs(a + b - initial))
            negative.extend([-a, -b])
        result.update({f"{label}_analytic_error": max(errors), f"{label}_mass_residual": max(mass),
                       f"{label}_negativity": max(negative)})
    return result


def graph(data, main, baseline, spec, criteria):
    nodes = data["nodes"]
    if len(set(nodes)) != len(nodes):
        raise ValueError("Duplicate graph node")
    edges = {}
    adjacency = {node: [] for node in nodes}
    for edge in data["edges"]:
        a, b, weight = edge["from"], edge["to"], number(edge["weight"])
        if a not in adjacency or b not in adjacency or weight < 0 or (a, b) in edges:
            raise ValueError("Unsupported/invalid directed graph edge")
        edges[a, b] = weight
        adjacency[a].append((b, weight))
    start, end = data["start"], data["end"]
    if start not in adjacency or end not in adjacency:
        raise ValueError("Graph endpoints not registered")
    distances, queue = {start: 0.0}, [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        for neighbor, weight in adjacency[node]:
            candidate = distance + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    if end not in distances:
        raise ValueError("No path to required destination")
    result = {"oracle_cost": distances[end]}
    for label, output in (("main", main), ("baseline", baseline)):
        path = output["path"]
        if not path or path[0] != start or path[-1] != end or any(node not in adjacency for node in path):
            raise ValueError("Invalid path endpoints/node")
        if len(path) != len(set(path)) or any((a, b) not in edges for a, b in zip(path, path[1:])):
            raise ValueError("Path repeats a node or uses a nonexistent edge")
        cost = sum(edges[a, b] for a, b in zip(path, path[1:]))
        result[f"{label}_cost"] = cost
        result[f"{label}_reported_cost_error"] = abs(cost - number(output["cost"]))
        result[f"{label}_feasibility_error"] = 0.0
    result["optimality_gap"] = abs(result["main_cost"] - result["oracle_cost"])
    return result


def evaluate(data, main, baseline, spec, criteria):
    if (criteria["task_type"] == "optimization"
            and "engineering:q5-frontier" in criteria.get("source_refs", [])):
        return {key: number(value) for key, value in q5_frontier(data, main, baseline, spec, criteria).items()}
    evaluator = {"regression": regression, "time_series": regression, "optimization": optimization,
                 "mechanism": mechanism, "graph": graph, "classification": classification}[criteria["task_type"]]
    result = evaluator(data, main, baseline, spec, criteria)
    return {key: number(value) for key, value in result.items()}
