"""Fresh run directories, actual subprocess records and rechecked artifact hashes."""
from __future__ import annotations

import json
import csv
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid

from .contracts import validate, unique
from .execution import ExecutionBackend, LocalSubprocessBackend
from .io import file_hash, now, read_json, safe_path, write_json, canonical_root, object_hash
from .state import workspace_lock


def validate_output(path: Path, output: dict):
    """Check declared flat JSON/CSV fields; domain correctness belongs to validators."""
    if output["format"] == "json":
        data = read_json(path)
        rows = data if isinstance(data, list) else [data]
        coercion = False
    elif output["format"] == "csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("CSV header is empty or contains duplicate fields")
            rows = list(reader)
        coercion = True
    else:
        raise ValueError("This runner requires JSON/CSV outputs; XLSX/TXT need a task-specific structural adapter")
    if not rows:
        raise ValueError("Empty structured output rows")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Structured output requires objects with declared fields")
        for field in output["fields"]:
            if field["name"] not in row:
                raise ValueError(f"Missing output field: {field['name']}")
            value = row[field["name"]]
            kind = field["type"]
            if kind in {"number", "integer"}:
                if coercion:
                    try:
                        value = float(value)
                    except (ValueError, TypeError) as exc:
                        raise ValueError("Nonnumeric CSV output field") from exc
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Nonfinite or nonnumeric output field")
                if kind == "integer" and value != int(value):
                    raise ValueError("Nonintegral integer output field")
            elif kind == "boolean":
                if not isinstance(value, bool) and not (coercion and value in {"true", "false"}):
                    raise ValueError("Invalid boolean output field")
            elif not isinstance(value, str):
                raise ValueError("Invalid string output field")


def execution_environment(seed: int) -> dict[str, str]:
    # Do not forward provider credentials, arbitrary PYTHONPATH or user site packages.
    environment = {key: value for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "TEMP", "TMP", "LANG", "LC_ALL"}}
    environment.update(PYTHONHASHSEED=str(seed), PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
        PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    return environment


def interpreter_info(interpreter: str, environment: dict) -> dict:
    path = Path(interpreter).expanduser()
    if not path.is_absolute():
        found = shutil.which(interpreter)
        if not found:
            raise ValueError(f"Interpreter unavailable: {interpreter}")
        path = Path(found)
    path = path.resolve(strict=True)
    command = "import sys,json,platform,importlib.metadata as m;print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform.platform(),'packages':{d.metadata['Name']:d.version for d in m.distributions() if d.metadata['Name']}}))"
    result = subprocess.run([str(path), "-s", "-c", command], env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        text=True, encoding="utf-8", timeout=30, shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise ValueError(f"Interpreter preflight failed: exit {result.returncode}")
    info = json.loads(result.stdout)
    if Path(info["executable"]).resolve() != path:
        raise ValueError("Interpreter resolved to a different executable")
    return {"requested": interpreter, "sha256": file_hash(path), **info}


def snapshot(root: Path, run: Path, source_relative: str, destination: str) -> dict:
    source = safe_path(root, source_relative)
    if not source.stat().st_size:
        raise ValueError(f"Empty source artifact: {source_relative}")
    before = file_hash(source)
    output = safe_path(run, destination, exists=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as original, output.open("xb") as copy:
        shutil.copyfileobj(original, copy)
    if file_hash(output) != before or file_hash(source) != before:
        raise ValueError("Source changed during snapshot")
    output.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return {"source_path": source_relative, "snapshot_path": output.relative_to(root).as_posix(),
            "sha256": before, "size_bytes": output.stat().st_size}


def _history(root: Path, question: str, method: str, role: str) -> list[dict]:
    histories = []
    runs = safe_path(root, "runs", exists=False)
    if runs.exists():
        for pending in runs.glob("*/planned.json"):
            planned = read_json(pending)
            if not pending.with_name("run_manifest.json").is_file() and (
                planned["question_id"], planned["method_id"], planned["role"]) == (question, method, role):
                if not pending.with_name("recovery.json").is_file():
                    raise ValueError(f"Interrupted run requires recovery before retry: {planned['run_id']}")
                from .recovery import verify_recovery
                recovered = verify_recovery(root, pending.parent.relative_to(root).as_posix())
                histories.append({**planned, "status": recovered["status"], "started_at": planned["created_at"]})
        for path in runs.glob("*/run_manifest.json"):
            record = validate("run_manifest", read_json(path), root=root)
            if (record["question_id"], record["method_id"], record["role"]) == (question, method, role):
                histories.append(record)
    return sorted(histories, key=lambda record: (record["started_at"], record["run_id"]))


def execute_model(root: Path, spec_relative: str, *, role="main", interpreter=None,
                  backend: ExecutionBackend | None = None, retry_of: str | None = None) -> dict:
    root = canonical_root(root)
    backend = backend or LocalSubprocessBackend()
    spec_path = safe_path(root, spec_relative)
    spec_hash = file_hash(spec_path)
    spec = validate("model_spec", read_json(spec_path), root=root)
    if file_hash(spec_path) != spec_hash:
        raise ValueError("Spec changed during preflight")
    if role not in {"main", "baseline", "probe", "validator", "fallback"}:
        raise ValueError("Unknown execution role")
    if role == "fallback":
        from .probes import verify_fallback_authorization
        verify_fallback_authorization(root, spec)
    elif "fallback_authorization" in spec:
        raise ValueError("Fallback authorization may only be consumed by a fallback execution")
    if spec["limits"]["memory_mb"] is not None:
        raise ValueError("This runner cannot enforce requested memory limits; use a capable backend")
    inputs_path = safe_path(root, "input_manifest.json")
    inputs = validate("input_manifest", read_json(inputs_path), root=root)
    inputs_hash = file_hash(inputs_path)
    input_records = {record["input_id"]: record for record in inputs["files"]}
    if set(spec["inputs"]) - input_records.keys():
        raise ValueError("Spec references an unregistered original input")
    sidecars = []
    for field, contract_name in (("criteria", "validation_criteria"), ("probe", "risk_probe_plan"), ("screening_card", "method_card"), ("assumptions", "assumption_plan")):
        reference = spec["validation_plan"].get(field)
        if reference:
            path = safe_path(root, reference["path"])
            if file_hash(path) != reference["sha256"]:
                raise ValueError("Predeclared validation/probe contract hash mismatch")
            validate(contract_name, read_json(path), root=root)
            sidecars.append((contract_name, reference))
    if role == "fallback":
        sidecars.extend((name, spec["fallback_authorization"][field]) for field, name in
                        (("card", "method_card"), ("probe_report", "risk_probe"), ("probe_run", "run_manifest")))
    if len({name for name, _ in sidecars}) != len(sidecars):
        raise ValueError("Duplicate execution sidecar contract")
    upstream = unique(spec.get("upstream_freezes", []), "question_id")
    upstream_sources = []
    for question_id, reference in upstream.items():
        from .freeze import verify_freeze
        if question_id == spec["question_id"]:
            raise ValueError("A model cannot depend on its own frozen result")
        frozen = verify_freeze(root, question_id, refresh=False)
        if frozen["freeze_id"] != reference["freeze_id"]:
            raise ValueError("Upstream freeze is no longer the active version")
        upstream_sources.append((reference, f"freezes/{frozen['freeze_id']}/frozen_numbers.json"))
    for relative in spec["implementation"]["code_files"]:
        path = safe_path(root, relative)
        if not path.stat().st_size:
            raise ValueError("Empty implementation file")
        if path.suffix == ".py":
            compile(path.read_bytes(), str(path), "exec")
    environment = execution_environment(spec["seed"])
    info = interpreter_info(str(interpreter or sys.executable), environment)
    fingerprint = object_hash({"spec": spec_hash, "inputs": inputs_hash, "interpreter": info,
                               "code": {path: file_hash(safe_path(root, path)) for path in spec["implementation"]["code_files"]}})
    with workspace_lock(root):
        history = _history(root, spec["question_id"], spec["method_id"], role)
        previous = history[-1] if history else None
        if previous and previous["status"] in {"FAIL", "ABANDONED"}:
            if retry_of != previous["run_id"]:
                raise ValueError("Previous failed run requires an explicit retry_of reference")
            attempt = previous["attempt"] + 1
            if attempt > 3:
                raise ValueError("Root-cause retry budget exhausted; return to the upstream owner")
            changed = fingerprint != previous["request_fingerprint"] if previous["status"] == "ABANDONED" else (file_hash(spec_path) != previous["spec"]["source_sha256"]
                       or info != previous["interpreter"]
                       or any(file_hash(safe_path(root, c["source_path"])) != c["sha256"] for c in previous["code"])
                       or file_hash(inputs_path) != previous["input_manifest_sha256"])
            if not changed:
                raise ValueError("Retry requires a recorded change to spec/code/inputs/environment")
        else:
            if retry_of:
                raise ValueError("retry_of must reference the latest failed run")
            attempt = 1
        run_id = "run-" + uuid.uuid4().hex
        run = safe_path(root, f"runs/{run_id}", exists=False)
        run.mkdir(parents=True)
        write_json(run / "planned.json", {"run_id": run_id, "question_id": spec["question_id"],
            "method_id": spec["method_id"], "role": role, "attempt": attempt, "retry_of": retry_of,
            "created_at": now(), "request_fingerprint": fingerprint}, exclusive=True)
        from .processes import identity
        write_json(run / "owner.json", {"owner": identity()}, exclusive=True)
        spec_snapshot = snapshot(root, run, spec_relative, "snapshot/model_spec.json")
        if spec_snapshot["sha256"] != spec_hash:
            raise ValueError("Spec changed after preflight")
        code = [snapshot(root, run, path, f"snapshot/code/{path}") for path in spec["implementation"]["code_files"]]
        contract_snapshots = []
        for name, reference in sidecars:
            copied = snapshot(root, run, reference["path"], f"snapshot/{name}.json")
            if copied["sha256"] != reference["sha256"]:
                raise ValueError("Validation/probe contract changed after preflight")
            contract_snapshots.append({"contract": name, **copied})
        upstream_snapshots = [{**reference, **snapshot(root, run, path, f"snapshot/upstream/{reference['question_id']}.json")}
                              for reference, path in upstream_sources]
        originals = []
        for input_id in spec["inputs"]:
            record = input_records[input_id]
            copied = snapshot(root, run, record["path"], f"snapshot/inputs/{record['path']}")
            if copied["sha256"] != record["sha256"]:
                raise ValueError("Input no longer matches frozen input manifest")
            originals.append({"input_id": input_id, **copied})
        work = run / "work"
        work.mkdir()
        outputs = run / "outputs"
        outputs.mkdir()
        for output in spec["outputs"]:
            safe_path(outputs, output["path"], exists=False).parent.mkdir(parents=True, exist_ok=True)
        launcher = run / "bootstrap.py"
        launcher.write_bytes(Path(__file__).with_name("runner_bootstrap.py").read_bytes())
        context_path = run / "context.json"
        context = {"seed": spec["seed"], "spec": str(root / spec_snapshot["snapshot_path"]),
            "inputs": {item["input_id"]: str(root / item["snapshot_path"]) for item in originals},
            "output_dir": str(outputs), "code_root": str(run / "snapshot/code"),
            "entrypoint": str(run / "snapshot/code" / spec["implementation"]["entrypoint"])}
        context["contracts"] = {item["contract"]: str(root / item["snapshot_path"]) for item in contract_snapshots}
        context["upstream"] = {item["question_id"]: str(root / item["snapshot_path"]) for item in upstream_snapshots}
        write_json(context_path, context, exclusive=True)
        controls = [{"path": p.relative_to(root).as_posix(), "sha256": file_hash(p)} for p in [launcher, context_path]]
        for p in (launcher, context_path):
            p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        argv = [info["executable"], "-s", str(launcher), str(context_path)]
        started = now()
        write_json(run / "started.json", {"run_id": run_id, "started_at": started, "argv": argv,
                   "attempt": attempt, "retry_of": retry_of, "status": "RUNNING"}, exclusive=True)
        controls.extend({"path": p.relative_to(root).as_posix(), "sha256": file_hash(p)}
                        for p in [run / "started.json", run / "planned.json", run / "owner.json"])
        result = backend.execute(argv, cwd=work, environment=environment, timeout=spec["limits"]["timeout_seconds"],
                                 stdout=run / "stdout.txt", stderr=run / "stderr.txt")
        if (run / "process.json").exists():
            controls.append({"path": (run / "process.json").relative_to(root).as_posix(), "sha256": file_hash(run / "process.json")})
        failure_class = cause = message = None
        if result.startup_error:
            failure_class, cause, message = "ENV_FAILURE", "process-start", result.startup_error
        elif result.timed_out:
            failure_class, cause, message = "CODE_FAILURE", "execution-timeout", "Execution exceeded declared timeout"
        elif result.returncode != 0:
            failure_class, cause, message = "CODE_FAILURE", "nonzero-exit", f"Process exited {result.returncode}"
        collected = []
        try:
            if file_hash(inputs_path) != inputs_hash or file_hash(spec_path) != spec_snapshot["sha256"]:
                raise ValueError("Canonical input manifest/spec changed during execution")
            for record in [spec_snapshot, *originals, *code, *contract_snapshots, *upstream_snapshots]:
                if file_hash(safe_path(root, record["snapshot_path"])) != record["sha256"] or file_hash(safe_path(root, record["source_path"])) != record["sha256"]:
                    raise ValueError("Input/code/spec changed during execution")
            for item in upstream_snapshots:
                from .freeze import verify_freeze
                if verify_freeze(root, item["question_id"], refresh=False)["freeze_id"] != item["freeze_id"]:
                    raise ValueError("Upstream freeze changed during execution")
            for item in controls:
                if file_hash(safe_path(root, item["path"])) != item["sha256"]:
                    raise ValueError("Run controls changed during execution")
            declared = {item["path"].replace("\\", "/") for item in spec["outputs"]}
            actual = {path.relative_to(outputs).as_posix() for path in outputs.rglob("*") if path.is_file()}
            if actual != declared:
                raise ValueError("Missing or undeclared final output files")
            for output in spec["outputs"]:
                path = safe_path(outputs, output["path"])
                if not path.stat().st_size:
                    raise ValueError("Empty final output")
                validate_output(path, output)
                collected.append({"name": output["name"], "path": path.relative_to(root).as_posix(),
                    "sha256": file_hash(path), "size_bytes": path.stat().st_size})
        except (ValueError, OSError) as exc:
            if failure_class is None:
                failure_class, cause, message = "VALIDATION_FAILURE", "artifact-contract", str(exc)
        logs = {}
        for label in ("stdout", "stderr"):
            path = run / f"{label}.txt"
            logs[label] = {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path), "size_bytes": path.stat().st_size}
        manifest = {"schema_version": "2.0", "run_id": run_id, "question_id": spec["question_id"],
            "method_id": spec["method_id"], "role": role, "producer": "runner", "actor_id": spec["actor_id"],
            "backend": backend.name, "capabilities": backend.capabilities, "interpreter": info,
            "argv": argv, "cwd": str(work), "environment": environment, "seed": spec["seed"],
            "started_at": started, "ended_at": now(), "duration_seconds": result.duration_seconds,
            "timeout_seconds": spec["limits"]["timeout_seconds"], "returncode": result.returncode, "timed_out": result.timed_out,
            "status": "FAIL" if failure_class else "PASS", "failure_class": failure_class, "cause_id": cause,
            "failure_message": message, "attempt": attempt, "retry_of": retry_of,
            "spec": {"source_path": spec_relative, "source_sha256": spec_snapshot["sha256"],
                     "snapshot_path": spec_snapshot["snapshot_path"], "sha256": spec_snapshot["sha256"]},
            "input_manifest_sha256": inputs_hash, "inputs": originals, "code": code, "outputs": collected,
            "logs": logs, "control_files": controls, "scientific_acceptance": "NOT_RUN"}
        manifest["contract_snapshots"] = contract_snapshots
        manifest["upstream_freezes"] = upstream_snapshots
        validate("run_manifest", manifest, root=root)
        write_json(run / "run_manifest.json", manifest, exclusive=True)
        return manifest


def verify_run(root: Path, manifest_relative: str, *, require_success=True, current_sources=True) -> dict:
    """Recheck recorded bytes and execution structure; never certify mathematics."""
    root = canonical_root(root)
    manifest_path = safe_path(root, manifest_relative)
    record = validate("run_manifest", read_json(manifest_path), root=root)
    run_relative = f"runs/{record['run_id']}"
    if manifest_path != safe_path(root, f"{run_relative}/run_manifest.json"):
        raise ValueError("Run manifest location does not match its identity")
    if require_success and record["status"] != "PASS":
        raise ValueError("A failed execution cannot serve as passing evidence")
    spec = record["spec"]
    for item in [spec, *record["inputs"], *record["code"], *record.get("contract_snapshots", []), *record.get("upstream_freezes", [])]:
        path = safe_path(root, item["snapshot_path"])
        path.relative_to(root / run_relative / "snapshot")
        if file_hash(path) != item["sha256"]:
            raise ValueError("Run snapshot hash mismatch")
        if "size_bytes" in item and path.stat().st_size != item["size_bytes"]:
            raise ValueError("Run snapshot size mismatch")
        if current_sources and file_hash(safe_path(root, item["source_path"])) != item["sha256"]:
            raise ValueError("Run is stale: canonical source changed")
    if spec["source_sha256"] != spec["sha256"]:
        raise ValueError("Spec snapshot differs from source hash")
    frozen_spec = validate("model_spec", read_json(root / spec["snapshot_path"]), root=root)
    if record["role"] == "fallback":
        from .probes import verify_fallback_authorization
        verify_fallback_authorization(root, frozen_spec)
    elif "fallback_authorization" in frozen_spec:
        raise ValueError("Fallback authorization used by a different execution role")
    upstream = unique(record.get("upstream_freezes", []), "question_id")
    declared_upstream = unique(frozen_spec.get("upstream_freezes", []), "question_id")
    if upstream.keys() != declared_upstream.keys():
        raise ValueError("Run omitted a declared upstream question freeze")
    for question_id, item in upstream.items():
        if item["freeze_id"] != declared_upstream[question_id]["freeze_id"]:
            raise ValueError("Run used a different upstream freeze")
        if current_sources:
            from .freeze import verify_freeze
            current = verify_freeze(root, question_id, refresh=False)
            if current["freeze_id"] != item["freeze_id"]:
                raise ValueError("Upstream question has been refrozen")
    sidecars = unique(record.get("contract_snapshots", []), "contract")
    expected_sidecars = {}
    for field, contract_name in (("criteria", "validation_criteria"), ("probe", "risk_probe_plan"), ("screening_card", "method_card"), ("assumptions", "assumption_plan")):
        reference = frozen_spec["validation_plan"].get(field)
        if reference:
            expected_sidecars[contract_name] = reference
    if record["role"] == "fallback":
        expected_sidecars.update({name: frozen_spec["fallback_authorization"][field] for field, name in
                                 (("card", "method_card"), ("probe_report", "risk_probe"), ("probe_run", "run_manifest"))})
    if sidecars or "contract_snapshots" in record:
        if sidecars.keys() != expected_sidecars.keys():
            raise ValueError("Run did not snapshot its declared validation/probe contracts")
        for name, reference in expected_sidecars.items():
            if sidecars[name]["source_path"] != reference["path"] or sidecars[name]["sha256"] != reference["sha256"]:
                raise ValueError("Run changed a predeclared validation/probe contract")
    for key in ("question_id", "method_id", "actor_id", "seed"):
        if record[key] != frozen_spec[key]:
            raise ValueError(f"Run changed model spec {key}")
    if record["timeout_seconds"] != frozen_spec["limits"]["timeout_seconds"]:
        raise ValueError("Run changed the declared timeout")
    if {item["source_path"] for item in record["code"]} != set(frozen_spec["implementation"]["code_files"]):
        raise ValueError("Run code bundle differs from model spec")
    if {item["input_id"] for item in record["inputs"]} != set(frozen_spec["inputs"]):
        raise ValueError("Run input coverage differs from model spec")
    for item in [*record["outputs"], *record["logs"].values(), *record["control_files"]]:
        path = safe_path(root, item["path"])
        path.relative_to(root / run_relative)
        if file_hash(path) != item["sha256"]:
            raise ValueError("Run artifact hash mismatch")
        if "size_bytes" in item and path.stat().st_size != item["size_bytes"]:
            raise ValueError("Run artifact size mismatch")
    expected_controls = {f"{run_relative}/{name}" for name in ("bootstrap.py", "context.json", "started.json", "planned.json")}
    planned = read_json(root / run_relative / "planned.json")
    if "request_fingerprint" in planned:
        expected_controls.add(f"{run_relative}/owner.json")
        if record["backend"] == "local_subprocess" and record["returncode"] is not None:
            expected_controls.add(f"{run_relative}/process.json")
    if {item["path"] for item in record["control_files"]} != expected_controls:
        raise ValueError("Missing execution control evidence")
    started = read_json(root / run_relative / "started.json")
    for key in ("run_id", "started_at", "argv", "attempt", "retry_of"):
        if record[key] != started[key]:
            raise ValueError("Run record contradicts the recorded execution request")
    context = read_json(root / run_relative / "context.json")
    expected_argv = [record["interpreter"]["executable"], "-s", str(root / run_relative / "bootstrap.py"),
                     str(root / run_relative / "context.json")]
    if record["argv"] != expected_argv or Path(record["cwd"]) != root / run_relative / "work":
        raise ValueError("Run command or working directory mismatch")
    if context["seed"] != record["seed"] or record["environment"].get("PYTHONHASHSEED") != str(record["seed"]):
        raise ValueError("Run seed disagrees with bootstrap/environment")
    if context["spec"] != str(root / spec["snapshot_path"]) or context["inputs"] != {
            item["input_id"]: str(root / item["snapshot_path"]) for item in record["inputs"]}:
        raise ValueError("Run context did not consume declared input/spec snapshots")
    if context["entrypoint"] != str(root / run_relative / "snapshot/code" / frozen_spec["implementation"]["entrypoint"]):
        raise ValueError("Run context changed solver entrypoint")
    if context["output_dir"] != str(root / run_relative / "outputs"):
        raise ValueError("Run context changed output directory")
    if "contract_snapshots" in record and context.get("contracts") != {item["contract"]: str(root / item["snapshot_path"]) for item in record["contract_snapshots"]}:
        raise ValueError("Run context changed validation/probe snapshots")
    if "upstream_freezes" in record and context.get("upstream") != {item["question_id"]: str(root / item["snapshot_path"]) for item in record["upstream_freezes"]}:
        raise ValueError("Run context changed upstream frozen inputs")
    if require_success:
        expected = {(item["name"], f"{run_relative}/outputs/{item['path']}") for item in frozen_spec["outputs"]}
        if {(item["name"], item["path"]) for item in record["outputs"]} != expected:
            raise ValueError("Run output coverage differs from spec")
        actual = {p.relative_to(root).as_posix() for p in (root / run_relative / "outputs").rglob("*") if p.is_file()}
        if actual != {path for _, path in expected}:
            raise ValueError("Run has missing or unregistered output artifacts")
        for output in frozen_spec["outputs"]:
            validate_output(safe_path(root, f"{run_relative}/outputs/{output['path']}"), output)
    if current_sources:
        manifest = safe_path(root, "input_manifest.json")
        if file_hash(manifest) != record["input_manifest_sha256"]:
            raise ValueError("Run is stale: input manifest changed")
        validate("input_manifest", read_json(manifest), root=root)
    return record
