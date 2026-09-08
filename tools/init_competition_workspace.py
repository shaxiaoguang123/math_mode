"""Compatibility entry point for the shared MathMode workspace initializer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathmode.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(["init", *sys.argv[1:]]))
