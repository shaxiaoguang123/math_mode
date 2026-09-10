"""Synthetic main/baseline solver; independent validator uses separate code."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--context", type=Path, required=True)
context = json.loads(parser.parse_args().context.read_text(encoding="utf-8"))
spec = json.loads(Path(context["spec"]).read_text(encoding="utf-8"))
rows = json.loads(Path(context["inputs"]["data"]).read_text(encoding="utf-8"))["rows"]
rows = {row["id"]: row for row in rows}
train = [rows[key] for key in spec["data_split"]["train_ids"]]
x_mean = sum(row["x"] for row in train) / len(train)
y_mean = sum(row["observed_y"] for row in train) / len(train)
if spec["method_id"] == "mean-baseline":
    slope = 0.0
else:
    slope = sum((row["x"] - x_mean) * (row["observed_y"] - y_mean) for row in train) / sum((row["x"] - x_mean) ** 2 for row in train)
intercept = y_mean - slope * x_mean
predictions = [{"id": key, "prediction": slope * rows[key]["x"] + intercept} for key in spec["data_split"]["test_ids"]]
(Path(context["output_dir"]) / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
