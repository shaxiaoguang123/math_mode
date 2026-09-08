"""Copied into each run; only the selected interpreter executes this file."""
import json
import random
import runpy
import sys
from pathlib import Path

context_path = Path(sys.argv[1]).resolve()
context = json.loads(context_path.read_text(encoding="utf-8"))
random.seed(context["seed"])
try:
    import numpy as np
except ImportError:
    pass
else:
    np.random.seed(context["seed"])

entrypoint = Path(context["entrypoint"])
sys.path.insert(0, str(entrypoint.parent))
sys.path.insert(1, context["code_root"])
sys.argv = [str(entrypoint), "--context", str(context_path)]
runpy.run_path(str(entrypoint), run_name="__main__")
