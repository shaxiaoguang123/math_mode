"""Synthetic runnable fixture: compute an input sum and seeded random draws."""
import argparse
import json
import os
from pathlib import Path
import random
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--context", type=Path, required=True)
context = json.loads(parser.parse_args().context.read_text(encoding="utf-8"))
inputs = json.loads(Path(context["inputs"]["data"]).read_text(encoding="utf-8"))
result = {"sum": sum(inputs["values"]), "draw": random.random(), "interpreter": sys.executable,
          "hash_seed": os.environ["PYTHONHASHSEED"], "secret_forwarded": "MATHMODE_TEST_SECRET" in os.environ}
path = Path(context["output_dir"]) / "results/result.json"
path.write_text(json.dumps(result), encoding="utf-8")
print("Computed sum from original fixture input")
