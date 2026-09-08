"""Strict data IO and confined paths shared by all runtime producers."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def finite_tree(value) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite number is not a valid contract value")
    if isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(text: str):
    result = json.loads(text, object_pairs_hook=_pairs)
    finite_tree(result)
    return result


def read_json(path: Path):
    return loads(path.read_text(encoding="utf-8-sig"))


def canonical_bytes(value) -> bytes:
    finite_tree(value)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def object_hash(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_root(path: Path) -> Path:
    """Use extended Windows paths so nested evidence bundles do not hit MAX_PATH."""
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        resolved = "\\\\?\\UNC\\" + resolved[2:] if resolved.startswith("\\\\") else "\\\\?\\" + resolved
    return Path(resolved)


def safe_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    if (not isinstance(relative, str) or not relative.strip()
            or relative.startswith(("/", "\\")) or ":" in relative or "\x00" in relative):
        raise ValueError("Expected a nonempty workspace-relative path")
    parts = relative.replace("\\", "/").split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Noncanonical or traversing workspace path")
    # Windows aliases/reserved names must not bypass checks on either platform.
    reserved = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    if any(part.endswith((" ", ".")) or reserved.match(part)
           or re.search(r'[<>"|?*\x00-\x1f]', part) for part in parts):
        raise ValueError("Ambiguous or reserved Windows path")
    anchor = canonical_root(root)
    target = anchor.joinpath(*PurePosixPath("/".join(parts)).parts)
    current = anchor
    for part in parts:
        current = current / part
        try:
            reparse = bool(getattr(current.lstat(), "st_file_attributes", 0)
                           & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        except FileNotFoundError:
            reparse = False
        if current.is_symlink() or reparse:
            raise ValueError("Symlink/junction artifacts are not permitted")
    target.resolve().relative_to(anchor)
    if exists and not target.is_file():
        raise ValueError(f"Missing artifact: {relative}")
    return target


def write_json(path: Path, value, *, exclusive: bool = False) -> None:
    content = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
