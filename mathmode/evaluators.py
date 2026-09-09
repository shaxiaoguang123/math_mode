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
    evaluator = {"regression": regression, "time_series": regression, "optimization": optimization,
                 "mechanism": mechanism, "graph": graph, "classification": classification}[criteria["task_type"]]
    result = evaluator(data, main, baseline, spec, criteria)
    return {key: number(value) for key, value in result.items()}
