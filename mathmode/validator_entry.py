"""Executed in a separate input bundle without solver source/intermediate state."""
import argparse
from pathlib import Path
from strict_io import read_json, write_json
from evaluators import evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--context", type=Path, required=True)
context = read_json(parser.parse_args().context)
inputs = {key: Path(value) for key, value in context["inputs"].items()}
metrics = evaluate(read_json(inputs["raw-data"]), read_json(inputs["main-result"]),
    read_json(inputs["baseline-result"]), read_json(inputs["solver-spec"]), read_json(inputs["validation-criteria"]))
write_json(Path(context["output_dir"]) / "measurements.json", [{"metric": key, "value": value} for key, value in sorted(metrics.items())])
