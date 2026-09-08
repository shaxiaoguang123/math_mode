# V2 contract catalog

All new contracts use `schema_version: "2.0"`, JSON Schema Draft 2020-12 and strict
object fields. This catalog defines responsibilities before implementation.
T04 implements modeling contracts, T05 the run manifest, and T06 independent
validation/evidence. Agent contracts remain scheduled for T08.
Schemas/tests are executable definitions; changed contracts must update
this catalog, examples and migration together.

Common artifact reference: `artifact_id`, workspace-relative `path`, `sha256`,
`size_bytes`, `created_at`, `producer`, `depends_on` (IDs and recorded hashes),
`status` (`DRAFT`, `VALID`, `FROZEN`, `STALE`, `FAILED`). IDs are nonempty and unique
in scope; cross-contract references must resolve. JSON rejects NaN/Infinity and
duplicate keys; JSONL validates each line independently. Schema validity is not
scientific acceptance. All final gates also validate cross-file semantics.

| Contract | Producer / consumer | Required information and semantic constraints |
| --- | --- | --- |
| competition_policy | Policy curator / all gates and paper tools | Competition, year, edition; verified official sources with URL/date/snapshot/hash/scope; official template path/hash; distinct official and project recommendations; cover, anonymity, abstract, TOC, pages, references, AI, attachments and submission policies. Unknown verification cannot pass G0/G8. |
| input_manifest | Preflight / every producer | Explicit roles, source, bytes/hash for each original file; extraction/data coverage; no role guessing downstream; no duplicate/path escapes. |
| problem_frame | Framer / council, code, validator | Every question's input IDs, required outputs/schema/units/precision, goals, hard constraints, evaluation metrics, resources, source citations. |
| problem_dag | Framer / orchestrator | All question IDs and `depends_on`; reject duplicates, missing nodes, self edges and cycles; deterministic topological order. |
| ambiguity_register | Ambiguity agent / G2 | IDs, severity, source, issue, conflicting interpretations, affected questions, resolution and evidence; unresolved load-bearing ambiguity blocks. |
| assumption_ledger (JSONL) | Assumption agent / model and paper | ID, content, source, necessary/simplifying kind, questions/formulas affected, validation method, sensitivity status, current status; append-only events with explicit supersession. |
| symbol_table | Framer/modeler / code, validator, paper | Symbol ID, meaning, units/dimensions, code name, domain, source and scope; uniqueness and formula-variable coverage. |
| method_card | Council/critic / decision | Main, usable baseline, optional fallback; mathematical idea, inputs/outputs, assumptions, complexity/resources, selection/rejection evidence and machine-checkable fallback trigger. |
| risk_probe | Probe runner / critic and decision | Method/run IDs; coverage selection, executability, assumptions, degeneracy, perturbation and scale measurements, thresholds, artifacts and verdict; actual executed run links, conditional mitigation. |
| model_spec | Approved modeler / code and validator | Question/method/decision IDs, variables, formulae, objective, constraints, parameters, units, input/output mapping, seeds, validation plan and limits; baseline comparison shares target/split/metric. |
| method_decision (JSONL) | Decision agent or actual human / G3.5 | Choice, rationale, probe evidence refs, time, `decided_by`, actor ID; autopilot is agent; human_gate requires actual received human event. |
| run_manifest | Runner only / validator, evidence, freeze | Run ID, question/method/role, code bundle, explicit argv/interpreter/cwd, seed, approved env summary, backend capabilities, start/end/duration, return code/timeout/failure class, input/code/output snapshots/hashes, stdout/stderr evidence and attempt/root cause. |
| validation_summary | Independent validator / evidence gate | Validator identity/code/run, original input/spec/output hashes, independently recomputed metrics and constraints, baseline comparison, oracle/cross-check and applicable sensitivity/robustness; no unresolved failures or nonfinite values. |
| evidence_gate | Deterministic auditor / freeze | Exact audited hashes, checks and blockers, claim/question coverage, fresh main+baseline+validator records; semantic reviewer separately attributed; warnings do not become PASS. |
| frozen_numbers | Freeze service / visual and paper | Immutable freeze/version ID, claim and frozen IDs, values/units/precision, source artifact and locator, run/validation/gate hashes, freeze timestamp, producer and decision; no manual mutation. |
| workflow_state | Orchestrator / all tools | Workspace/profile/mode, DAG, registry, gate observations, next owner/action, retry history and failure classes; atomic revisioned write; resume rechecks hashes. |
| ai_usage (JSONL) | Harness/host recorder / disclosure tool | Timestamp, provider/model/version/date, question, activity, input scope, output used, actual human postprocess and artifact refs. Unknown provider versions stay unknown; no fabricated human work. |
| agent_task / agent_result | Harness / role backend and orchestrator | Task/actor/role IDs, input refs and hashes, read/write scope, expected schema, output refs, errors, attempts, provenance; actor cannot approve own output. |

Existing `视觉计划.schema.json`, `支撑材料清单.schema.json` and paper
`agent_manifest.schema.json` gain explicit V2 lineage adapters during T09. V1
payloads remain structural plans; migration does not synthesize run, validation or
freeze records. Final V2 figure entries link `claim_id`, `evidence_id`, `run_id`,
`result_file` and `frozen_number_id`; paper manifests bind numerical claims to
freeze IDs. Official outputs specify exact filenames/sheets/columns/precision and
are reopened and validated after export.

## Cross-contract invariants

1. Input role/hash authority is unique. Spec, run and validation must reference the
   same data/split/parameters; expected and actual code hashes match.
2. Method choice references completed probes and the chosen main/baseline. A
   fallback cannot be implemented or run until its concrete trigger is recorded.
3. Original inputs and main outputs are read-only to the validator. Independent
   recomputation does not import the primary implementation.
4. A PASS report cannot override missing, stale, malformed, empty or NaN artifacts.
5. Dependencies form a validated graph. Any canonical change invalidates all
   descendants and all affected questions, including paper/package observations.
6. Freeze source locators resolve to the recorded finite value and units. Changed
   snapshot bytes fail hash verification; thaw/refreeze preserves prior versions.
7. Actor/decision identity is attributed honestly. Scientific review and result
   generation use separate roles; deterministic gate remains final authority.

## Executable modeling contracts (T04)

`mathmode/schema_catalog.py` defines 12 standalone generated schemas. Rebuild with
`python tools/build_contract_schemas.py`; use `--check` to reject distribution drift.
`fixtures/contracts/` contains one explicitly synthetic example per schema and a
cross-contract bundle. Examples demonstrate consistency, never scientific approval.

`python -m mathmode validate <contract> <file> [--workspace <root>]` checks strict
JSON, schema, timestamps, finite numbers, portable paths and contract semantics.
Use `modeling_bundle` to check question/DAG coverage, source and assumption
references, selected methods, symbol scope, unchanged question requirements and
comparable main/baseline splits. Input hashes and read-only permissions are checked
when a workspace is supplied. Schema validation without a workspace cannot verify
that declared inputs exist. Textual citations and unit explanations still require
source/semantic review; structural consistency never proves their truth.

Chronological splits include `sample_times` for all train/holdout IDs; group splits
include `sample_groups`. Training must precede holdout and groups cannot overlap.
Each rolling fold is a separate evaluated spec/run; this contract does not infer
chronology from lexicographic sample IDs. Actual data rows must later be compared
to declared membership by the independent validator.

`StateStore` uses an exclusive writer lock, atomic JSON replacement and expected
revision checks. Retry/reference histories cannot be shortened or rewritten by
its update API. A crashed writer lock is preserved for diagnosis. Assumption JSONL
uses append-only events and explicit supersession; torn/invalid lines fail closed.
These are trusted local APIs, not OS security boundaries: editing files outside
the API is not prohibited by the operating system.

`python -m mathmode status --workspace <root>` rehashes registered artifacts and
finds transitive stale dependencies. The reported scope is artifact freshness;
an empty registry passing this check does not pass any workflow gate. Gate writes,
provenance-authenticated run evidence, immutable freezes, source authenticity,
actual human events and scientific checks are later-stage responsibilities.

## Executed run contract (T05)

The catalog now additionally generates `run_manifest.schema.json`. Its example is
the actually executed fixture in `fixtures/runner/` and `tests/test_runner.py`, not
a static fabricated PASS record. Each run snapshots the spec, explicit original
inputs, complete declared code bundle and bootstrap/context controls. It records
the actual interpreter/hash/version/package inventory, argv, cwd, allowlisted
environment, Python/NumPy seed, timestamps, process duration, return code, timeout,
output/log hashes and bounded retry chain. Full stdout/stderr are retained locally.

The `LocalSubprocessBackend` uses argv with `shell=False`, a fresh working/output
directory, timeout and best-effort process-tree termination. Capability fields
explicitly deny OS/network/filesystem/CPU/memory isolation. Non-null memory limits
are rejected, never ignored. Only trusted local generated code is appropriate.
Python and NumPy seeding does not promise cross-platform/GPU-library determinism.

Run PASS establishes process and declared JSON/CSV structure integrity only.
No outputs, extra final files, malformed/nonfinite values, changed sources or
nonzero exit cannot pass. XLSX/TXT specs currently need a structural adapter and
are rejected by this runner. `scientific_acceptance` always remains NOT_RUN.
`verify-run` rehashes snapshots/current sources, controls, logs and outputs and
cross-checks their identities, command, seed, input/code/output coverage and spec.
Local file owners can rewrite the disk; hashes do not authenticate such an attacker.

Retries require the latest failed run ID and changed code/spec/inputs/environment.
The current conservative bound is three total attempts per unresolved failure
chain, even if error wording changes. A successful run starts a new chain.
Interrupted runs remain visible and block a silent retry; inspect the recorded
process before explicit recovery (workflow recovery integration is T08).

## Independent validation and computed evidence (T06)

Three new schemas describe `validation_criteria`, `validation_summary` and
`evidence_gate`. A V2 spec may omit `validation_plan.criteria` for draft/execution
compatibility, but evidence cannot pass without it. Both main and baseline must
pin identical criteria path/hash and select that frozen original input before
execution. Changing tolerances after seeing results requires new specs and runs.
Check IDs cover mandatory task residuals, exact coverage/leakage checks and every
declared hard-constraint validator. Required robustness needs measured checks.

`independent-validate` copies only the original problem/data, frozen criteria/spec
and final main/baseline outputs to a separate workspace. Built-in validator code
is copied independently; solver source and intermediate state are excluded. The
validator receives no expected final answer and emits measured numbers, never
approval booleans. Its run passes through the actual runner. A parent comparator
applies the predeclared thresholds; the evidence gate recomputes those comparisons
and rechecks run hashes, actor separation, reviewed validator code and exact input
bindings. An unresolved stderr diagnostic blocks evidence PASS.

Adapters currently cover the explicit JSON protocols documented in
`fixtures/validation/README.md`: regression/time series, continuous linear programs,
first-order A→B reaction and nonnegative directed shortest paths. The evaluator
checks actual row/timestamp/group membership, optional bootstrap uncertainty,
independent objective/feasibility/oracle gaps, conservation and graph validity.
Scalar AST dimensional algebra verifies the pinned symbol registry against formula
equalities without `eval`. It does not claim general symbolic/TeX theorem proving.

Evidence PASS has scope `computed_model_evidence`; official compliance remains
NOT_RUN. Source authenticity, appropriateness of assumptions/thresholds, actual
agent role attribution and question-wide semantic acceptance still require the
T08 workflow and T09/T12 final audits. Custom problems need reviewed independent
adapters rather than changing a `task_type` label. Windows extended paths support
nested evidence bundles beyond the traditional MAX_PATH limit.
