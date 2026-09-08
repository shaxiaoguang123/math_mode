# V2 contract catalog

All new contracts use `schema_version: "2.0"`, JSON Schema Draft 2020-12 and strict
object fields. This catalog defines responsibilities before implementation.
T04 implements modeling contracts, T05 the run manifest, T06 independent
validation/evidence and T07 freeze/lineage. T08 agent contracts are implemented,
while workflow-wide integration remains in progress.
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
Interrupted runs remain visible and block a silent retry. `recover` observes the
recorded owner/child/descendant identities and preserves an ABANDONED event before
admitting an explicit changed retry. It never synthesizes a completed run manifest.

## Independent validation and computed evidence (T06)

Three new schemas describe `validation_criteria`, `validation_summary` and
`evidence_gate`. A V2 spec may omit `validation_plan.criteria` for draft/execution
compatibility, but evidence cannot pass without it. Both main and baseline must
pin identical criteria path/hash before execution. Criteria can be generated after
framing and snapshotted separately in `contract_snapshots`; they need not alter
the original input manifest. Imported original-rule criteria remain readable.
Changing tolerances after seeing results requires new specs and runs.
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

## Immutable freezes and dependency graph (T07)

`freeze_request` contains IDs, source JSON Pointers, declared units and precision,
never manually supplied values. The service only accepts verified main-output
fields or checked independent measurements. It re-audits evidence and hashes,
then creates a read-only exclusive snapshot at
`freezes/<freeze-id>/frozen_numbers.json`. Root `frozen_numbers.json` is a
`freeze_index`: each question points to its active version/hash and FROZEN/THAWED
state. This mutable index contains no numerical values. Snapshot versions and
numerical IDs are distinct, and active numerical IDs are globally unique.

`freeze_change_log.jsonl` appends FREEZE/THAW events with actor, time, reason,
snapshot hash and previous-event hash. The index and registry must agree with the
log before a snapshot can be consumed. Filesystem-owner attacks remain outside
local hash-chain authentication guarantees. A crash between file/state writes
fails closed on verification; archived bytes are never silently replaced.

`thaw` preserves the archive and invalidates all descendant artifacts and affected
gates. Refreeze requires new main/baseline runs after the thaw and new independent
validation; it cannot recycle the old passing records. `verify-freeze` checks the
active pointer, event chain, registry, exact numeric locators and current evidence.

The registry binds original/code/spec/snapshots to runs, run outputs to independent
inputs, validator measurements to the summary/evidence, and evidence to freeze.
Existing model/assumption/parameter dependencies are retained when binding runs.
Visual/paper/package producers add their own downstream edges during T08–T09.

## Agent transport and measured preflight (T08 in progress)

Twenty-three additional contracts bring the catalog to 43: `code_repair_request`, `failure_diagnosis`, `assumption_plan`,
`assumption_report`, `issue_disposition`,
`disposition_review`, `human_decision_request`,
`human_decision_event`, `reference_retrieval`, `workflow_plan`,
`workflow_progress`, `recovery_event`, `reference_baseline`, `reference_case_baseline`, `agent_schedule`, `agent_task`, `agent_response`,
`agent_result`, `semantic_review`, `method_proposal`, `data_audit`, `method_sources`
and `risk_probe_plan`. Task actors, question/view identities, role directories,
exact output sets and input evidence scope are checked before publication. Error
findings block semantic acceptance; warnings/limitations cannot claim SUPPORTED.

`issue_disposition` binds source kind, source/frame paths and hashes, question
scope, per-locator affected questions, retained boundaries/repair requests and
evidence references. `disposition_review` binds the proposal hash, independent
actor and LIMITED/BLOCKED judgment. The runtime checks exact warning/limitation
coverage, current role provenance and evidence freshness. Source errors or repair
requests cannot be approved away. `workflow_plan.dispositions` supplies the three
paths; `workflow_state.gates[].status` additionally admits LIMITED. Optional
`freeze_request.qualification_sources` pins those three artifacts and optional
`frozen_numbers.qualifications` contains derived direct/inherited restrictions.
The service, not an agent, constructs the latter. See the reviewed-disposition
section in `workflow_v2.md` for role scheduling, CLI status and numerical boundaries.

`run_agent_task` materializes hashed read-only inputs and role instructions, calls
the backend, and validates its proposal before canonical publication. Successful
transport does not imply mathematical acceptance. `verify_agent_result` rechecks
the registered request/result/response/logs, complete input/control bundle and
current canonical input/output hashes. Reasoning handoffs require an actual
backend session; fixture transports cannot satisfy them. These hashes operate
within the trusted local filesystem boundary, not as provider-signed attestations.

Fresh task IDs or actor names cannot restart a failed logical role/question/view
chain. Three total attempts are permitted. Interrupted tasks block resume pending
explicit recovery. Backend exceptions produce a failed result; exception details
are not copied because they may contain credentials. Provider/model/session fields
record observed information, preserving unknown values. The Codex CLI transport
has been actually exercised; unsupported transport-schema restrictions remain
enforced by the canonical parent validator.

`audit_inputs` deterministically inspects original files. `measured_probe` computes
the six risk categories from actual outputs or recorded process returncode/duration
using a pre-execution `risk_probe_plan`. Its report can be recomputed; manually
edited measurements or thresholds cannot pass verification.

Fallback execution requires `model_spec.fallback_authorization` with hashed card,
probe report and probe-run references. The card and trigger must already have been
pinned as `validation_plan.screening_card` in that main-method probe. The runner
recomputes the trigger before admission and rechecks its evidence on verification.
The run snapshots all authorization contracts. Changing the card after seeing
probe results, inactive conditions or a different method cannot authorize fallback.
The numerical workflow now consumes this authorization through an explicitly
attributed fallback decision, independent code/semantic review and the same
validation/freeze services used by the primary candidate; details follow below.

Dependent questions declare `model_spec.upstream_freezes` with exact question and
freeze IDs. The runner snapshots each current parent and supplies `context.upstream`;
the independent validator receives an attributed parent snapshot without solver
source. Freeze lineage binds these copies to the parent. Thawing Q1 invalidates Q2
runs, evidence and freeze transitively. Dependency order alone is not a content
change; registry comparisons use ID/hash associations rather than list ordering.

`agent_schedule` supplies a task DAG with explicit role, inputs, outputs and retry
predecessors. `Orchestrator.advance` resolves current registered hashes at dispatch,
verifies prior real reasoning handoffs on resume, and checks role prerequisites.
Council inputs receive cross-contract frame/DAG/source checks. Code/validation
work must use the actual framed question DAG and current upstream freezes. Human
decision tasks prepare a host request and stay WAITING_HUMAN until the terminal
adapter records an actual response. They never dispatch a reasoning backend or
invent `agent_result`/AI-usage records. Code consumes the verified host decision.
The deterministic data report is authoritative; model-proposed counts cannot
replace it. Actual scheduling and no-repeat resume have been exercised through
the configured Codex backend, after a preserved initial timeout.

CLI entry points include `agent`, `verify-agent`, `advance-agents`, `human-decision`,
`verify-human-decision`, `data-audit` and `probe-report`. A scheduler PASS has scope `agent_schedule` and leaves scientific
acceptance and official compliance NOT_RUN. `Workflow` now coordinates the separate
services through G6 as described below. Successful critic rounds are also bounded:
at most three per question/view for unchanged original/framing input hashes. New
proposal/task/actor IDs do not reset this count. Source/admission review, honest host
human-event admission, complete live role-chain integration and automatic repair routing
remain required before T08 is declared complete.

## Evidence-derived lifecycle (T08)

`workflow_plan` names real framing/review contracts, every question's method card,
measured probe reports, decision, main/baseline specs, independent code/validation
reviews and frozen claim locators. It contains no supplied numerical values.
Optional `agent_schedule` dispatches ready roles; optional paired `probe_specs`
let the coordinator execute or reuse actual probes before screening. Different
baseline authors require their own `baseline_code_review`. Each spec pins the same
independent criteria and preserves the original question requirements.

`workflow_progress` contains per-question main/baseline run, validation and evidence
paths. These are resume hints, never evidence by themselves. `Workflow.observe`
revalidates actual provenance, cross-contract identity, current inputs/code/results,
numerical evidence, semantic reviews and frozen claim coverage. Each dependent
question must consume the exact current upstream freeze. G0 audits official policy;
G1–G6 are computed from their corresponding artifacts. G7/G8 remain BLOCKED until
T09 supplies actual paper/visual/final audit adapters. Development can continue with
unverified official policy; no final compliance is inferred from numerical PASS.

`Workflow.advance` performs one admissible transition. Missing progress pointers
adopt only verified matching executions; manually repaired stale/failed pointers
can likewise adopt new successful runs and discard the old validation pointers.
It does not silently relaunch a recorded failed run. Explicit thaw requires new
main and baseline executions even when canonical bytes are unchanged. Generated
semantic validation tasks receive originals, framing/assumptions, both specs,
criteria, final outputs and independent numerical evidence, without solver source
or intermediates. Historical stale outputs remain excluded without blocking current
repaired runs. An unfavorable current review is not repeatedly queried for PASS.
Verified explicit agent recovery preserves the validator retry predecessor/budget.

A separate `.workflow.advance.lock` serializes the complete coordinator transition,
including model dispatch and progress publication, while short revisioned state
transactions retain `.mathmode.lock`. It prevents competing `Workflow.advance`
calls, not arbitrary filesystem editing or unrelated direct service invocations.
Owner identity is preserved after a crash; `recover-lock --scope workflow` releases
only an observed stopped owner. Interrupted child executions retain their separate
recovery checks. Progress writes are atomic; a crash between service completion and
pointer publication is recovered by verified adoption.

Current lifecycle tests use actual probe/main/baseline/independent numerical runs
and freezes, with explicitly mocked role provenance. The unpatched coordinator
rejects those authored semantic files. These tests do not claim a live full-agent
historical run. Warning/LIMITED cases now require independently reviewed explicit
dispositions and retain LIMITED through affected gates and freezes. Missing
dispositions still block; automatic repair and additional input/structural
sensitivity adapters remain incomplete.

### Predeclared assumption assessments

An independently role-produced `assumption_plan` pins the accepted assumption
ledger and the actual main/baseline production specs. Each selected assumption
has sensitivity scenarios or an explicit not-applicable rationale. Scenarios
change one existing numeric parameter or the seed of the main production model,
and name independently checked metrics, units and maximum absolute changes.
The baseline stays fixed. The actual experiment specs additionally pin that plan
through `model_spec.validation_plan.assumptions`; `run_manifest.contract_snapshots`
now admits `assumption_plan`, preventing post-execution threshold declarations.

`assumption_report` is generated by a deterministic service from real control and
perturbed runs plus independent validation summaries. It retains every scenario,
measured values, deltas, limits and failures. NOT_APPLICABLE is distinct from TESTED
and has no invented experiment. Current successful reports are required for G5
and cited by the semantic validator; their pins enter optional
`freeze_request.assumption_reports` and `frozen_numbers.assumption_reports`.
This reports declared numerical stability checks, not proof that an assumption
is universally true. Data noise/missingness, structural alternative-model assays
and automatic repair routing remain further integration work.

### Human decision host boundary

In `human_gate` mode, the scheduler prepares a `human_decision_request` from a
fresh framed question, one verified method card, current measured probes and the
exact registered task inputs. Its immutable task/display snapshots and input
hashes are registered under `human_requests/`. The display includes the question,
methods, critic findings and measured probe checks; the host cannot offer an
untriggered fallback or a method without a passing admissible probe.

`human-decision --workspace <root> --request-id <id> --actor-id <local-pseudonym>`
requires interactive stdin/stdout. It displays the prepared evidence, reads an
eligible role or `defer`, requires a reason and records only an explicit `SUBMIT`.
Piped input and model-generated decision JSON have no admission path. Cancellation
publishes nothing; deferral records the event but publishes no method choice.
The model transport continues rejecting human-attributed outputs even when they
include a `human_event_id`. Raw code transport in human mode also requires the
actual verified host event before calling its backend.

`human_decision_event` records the observed terminal response, time, local actor,
confirmation and request hash in `human_events/`. Evidence is rechecked after the
wait and under the writer lock before publication. A changed input leaves the
observed response diagnostic and prevents decision publication. A completed choice
appends a canonical `method_decision`, preserving the exact previous ledger bytes;
the existing `human_event_id` identifies the immutable host event. The decision's
dependencies include the request and event, which bind the original scoped inputs.
Model specs produced from it carry those dependencies through numerical freeze.

`verify-human-decision` rechecks the current decision's exact event-derived fields,
ledger prefix, producer and dependencies, plus the current screening. Scheduler
resume matches the original task/input signature and does not prompt or call a
model again. A captured registered choice interrupted before ledger publication
can be resumed by the same terminal command without another response. Unregistered
interrupted observations remain diagnostic. A new explicit task ID can request
reconsideration after changed evidence; old task identities cannot silently change
scope. Active frozen consumers require explicit thaw before any new decision can
overwrite the current ledger hash. Request/response files remain private by default.

This is a trusted local terminal boundary, **not person authentication or an OS
sandbox**. A host with direct filesystem/process control could falsify observations;
the system does not claim to authenticate the person at the keyboard. Engineering
tests use explicitly labelled in-memory terminal streams and framed-role doubles,
while probe/solver/validator subprocesses and freeze propagation are real. No live
human interaction or historical scientific acceptance is inferred from those tests.
`workflow --advance --no-agent` can prepare/resume human requests; missing reasoning
roles remain WAITING_AGENT instead of being synthesized by the host.

### Fallback production decisions

`method_decision.execution_role` is an optional `main`/`fallback` discriminator;
absent means `main` for existing workspaces. `main_method_id` continues to name the
selected production solution, while `execution_role=fallback` explicitly selects
the card's conditional fallback. `baseline_method_id` still selects the usable
baseline. The run manifest always retains its actual `fallback` role.

`screening_options` reaudits one declared current report per method. Every probe
must bind the same question and method card before execution. Main selection needs
its passing probe. Fallback selection additionally needs an active predeclared
trigger measured by the main probe and a passing six-category probe of the fallback
itself. Both reports must be cited by the decision. A duplicated/unknown-method
report, missing fallback probe, changed card, inactive trigger or role mismatch
cannot authorize fallback. Runner authorization must match that selected main
probe/card exactly. An eligible fallback is not silently selected by the coordinator;
an actual attributed decision remains necessary.

This route uses completed measured probes. A production crash or timeout without
that evidence still needs explicit repair/re-probing and a new decision; an
arbitrary failed production run is not silently converted into fallback admission.

The fallback code review and subsequent independent semantic review must cover
the decision, card and both probe reports in addition to code/spec or numerical
evidence respectively. Source-free validator tasks receive these selection
artifacts; the scheduler rejects missing selection evidence. Decision-agent
proposals cannot cite artifacts outside their input bundle. Rejected assumptions
of an unselected method remain in history; only selected methods may rely on
non-rejected assumptions and formula references in the implemented model bundle.
Unselected historical formula references do not force the abandoned algorithm's
formulae into the fallback spec.

`main_spec`, `main_run` and measurement names such as `main_mse` are existing
production-solution slots. They can point to an explicitly marked fallback; no run
is relabeled as main and no measured values are copied from the failed candidate.
Independent validation compares that actual fallback to the usable baseline using
the same original question, outputs, split, constraints, units and pinned criteria.
The validator's own spec does not inherit fallback execution authorization, since
it performs independent measurement. Freeze and resume retain the actual fallback
run/decision/hash lineage, and altered screening evidence invalidates its consumers.

`tests/test_workflow_fallback.py` computes a median pairwise-slope fallback against
a training-mean baseline on synthetic affine holdout data. The main screening
threshold is deliberately strict to exercise rejection/trigger routing; it is not
a scientific assertion that least squares fails on these data. Role provenance is
explicitly mocked, while probes, solver/validator subprocesses, freeze and tamper
checks are real. `fixtures/agents/fallback_decision.json` is only a structural
example and does not supply valid screening evidence.

`reference_baseline` now seals independent immutable copies of the actual frame,
executed main/baseline specs and code, results/validation/freeze and writer-produced
TeX. `seal-baseline` requires real framer/writer handoffs and a current numerical
freeze before any same-problem access is recorded. Subsequent canonical edits do
not erase this historical baseline; altered snapshot bytes block further admission.

`admit-reference` requires explicit general/same-problem classification. In blind
mode, the latter requires checkpoints covering all five groups for **every framed
question**. `seal-case-baseline` binds the per-question checkpoints, verifies exact
question coverage, one complete frame hash, one original-input manifest hash and
the current independently validated numerical freezes. Its registered dependencies
are the immutable question checkpoints, so a changed Q2 paper invalidates a receipt
requested for Q1 as well. `verify-baseline` inspects historical integrity without
requiring later reference-informed canonical sources to stay unchanged.

A single-question frame can still use its original `reference_baseline` directly.
A multi-question frame requires `reference_case_baseline`; relabeling one question
as an aggregate or mixing different frames/originals fails verification. Before the
first same-case admission the current frame and input manifest must still match.
Any earlier same-problem exposure blocks sealing *any* new question/case checkpoint.
Both HTTP receipts and local method-source handoffs recheck admission semantics;
an old partial-case access event does not authorize a new valid source handoff.

Admission appends a host event before retrieval; it does not itself fetch a URL.
Method-source proposals must
bind an actual supplied snapshot/hash and an admission preceding both retrieval and
task dispatch. Access outside this trusted host cannot be reconstructed and remains
explicitly UNVERIFIABLE. Baseline sealing is not final paper/scientific acceptance.

`init --no-blind-reference-mode` explicitly creates a non-blind workspace. The
backward-compatible default remains true. `StateStore.update` treats the mode as
immutable workspace identity: neither agents nor ordinary state mutations can
toggle it during a run. Non-blind same-problem sources are admitted and logged
without a baseline; supplying one is rejected to avoid a false blindness claim.
New admission events and HTTP receipts record the mode explicitly. Missing mode
fields on legacy events/receipts mean true. This is an application boundary, not
protection against a host directly rewriting files or reading outside the system.

### Actual HTTP reference retrieval

`retrieve-reference` connects host classification/admission to actual HTTP GETs.
It records every requested URL and its prior admission, observed response status,
redirect target, content metadata, request/response times, owner identity and byte
limits. Redirects inherit the host's explicit classification and are separately
admitted before being requested. HTTP(S) URLs cannot contain embedded credentials
or fragments; HTTPS cannot downgrade to HTTP. The client does not execute page
scripts or use ambient cookies, authentication or proxies. Classification is still
a trusted host assertion about the source/redirect chain, not automated proof of
semantic relevance or absence of same-problem material.

`reference_retrieval` binds immutable `planned.json`, `owner.json`, `trace.json`
and `body.bin` records under `references/<retrieval-id>/`. Response bytes are stored
without content decoding; HTTP content type/encoding remain metadata. Successful
receipts and their snapshots are registered with evidence dependencies, including
the required whole-case blind baseline for same-problem access in blind mode.
`verify-reference` checks these records, admission order, redirect continuity and actual bytes without
downloading a newer version. This is evidence from the trusted local HTTP client,
not a server-signed attestation or a claim of scientific acceptance.

Empty/truncated responses, unsuccessful HTTP status, unsupported redirects, size
limits and timeouts preserve FAILED receipts and any partial bytes. Partial files
cannot serve as reference snapshots. Interrupted requests lacking a completed
receipt likewise cannot be adopted. Existing request IDs are never overwritten;
there are no automatic retry loops. Default limits are 20 MB, five redirects and
30 seconds. Timeout bounds socket operations and is checked between chunks; OS
DNS resolution is not a hard preemptible wall-clock limit.

HTTP `method_sources` entries require a `retrieval` path/hash in the actual role
input bundle. The URI, observed access time, question/classification and snapshot
bytes must match the verified receipt. Downloaded paths under `references/` cannot
bypass this by claiming a different URI scheme. The method retriever scheduler
requires the matching receipt and downloaded bytes together; the raw role transport
also checks source binding before publication. Existing explicitly supplied
non-HTTP/local fixture sources retain their distinct admission checks.

The optional `workflow_plan.reference_requests` array supplies stable retrieval
IDs, source URLs, question IDs, explicit classifications and nullable baseline IDs.
After framing, each advance can retrieve one eligible source before role scheduling.
Task inputs can name `references/<id>/body.bin` and `references/<id>/retrieval.json`.
Resume verifies existing receipts without refetching; changed declarations require
a new explicit request. A same-problem request awaiting its baseline performs no
network access and does not prevent computing that blind baseline. Failed/missing
reference evidence remains a blocker for roles that require those inputs.

Local HTTP tests verify admissions before the server receives each request, actual
redirect/download failure handling, receipt/source tampering, same-problem baseline
lineage and workflow resume. `tests/test_reference_case.py` additionally computes
and independently freezes synthetic Q1→Q2 results, then checks partial-case refusal,
complete-case download admission and transitive snapshot tampering. Framer/writer
authorship is explicitly doubled in these engineering tests; this is not a live
historical contest or completed scientific paper. The static case-baseline fixture
contains illustrative hashes for schema validation only and cannot grant access.

## Interrupted execution recovery (T08)

New workspace locks record owner PID, process creation time and a unique token.
Each reserved run/task records `owner.json`. The local backend records actual
child PID/creation time and observed descendants in `process.json`. The `psutil`
dependency supports Windows and POSIX observation. A reused PID is distinguished
from its original owner; missing permission or malformed metadata fails closed.

`recover-lock --workspace <root> --reason <diagnosis>` preserves an archive and
releases a lock only after its recorded owner has stopped. Legacy timestamp-only
locks lack ownership evidence and are not silently removed. `recover --kind run`
or `--kind agent` additionally checks the recorded child and all observed descendants.
The service does not kill processes or infer that a timed-out tool observation means
an execution stopped. Recovery before backend launch is distinct from the ambiguous
window after launch starts but before a child identity is persisted; the latter
cannot be automatically recovered from insufficient evidence.

`recovery_event` records status ABANDONED, reason, request/process-evidence hashes,
attempt and actual observation. Returncode remains null and scientific acceptance
NOT_RUN. Old logs, outputs and request files remain untouched. Recovery never
creates a fabricated run_manifest or agent_result. The next run must explicitly
reference the abandoned predecessor, change its code/spec/input/environment and
continue the three-attempt budget. Agent retries likewise preserve predecessor
and attempt identity; new task IDs cannot restart the failed chain.

Process-tree observation and termination remain best effort. The local backend is
not an OS sandbox and cannot prove that unobserved/detached descendants never existed;
recovery records descendant_quiescence=NOT_PROVEN. This boundary is explicit rather
than claiming universal process isolation. Known live descendants block recovery.
`refresh` rehashes and persists transitive STALE states, including cross-question
consumers, and changes affected gate observations to BLOCKED. Merely refreshing a
broken frozen chain does not authorize canonical changes: an explicit thaw is
still required. Batch graph registration validates all references and commits one
revision, so a failed batch publishes no partial state.


## Terminal failure diagnosis (T08)

`failure_diagnosis` is an independent reviewer contract with `diagnosis_id`,
`actor_id`, `question_id`, a hashed `failure_source`, `created_at`, `failure_class`,
`cause_id`, `rationale`, `evidence_refs` and ordered `repair_steps`. The class is
one of ENV/DATA/CODE/MODEL/VALIDATION/POLICY_FAILURE. It describes a supported
underlying diagnosis, which may differ from the runner's process symptom.

Publication requires the complete verified historical execution bundle and the
actual different failed producer in the task. The source must be a terminal FAIL
manifest with matching question and hash, and the diagnosis must cite it. The
role cannot produce a diagnosis using an authored success claim, a partial log
bundle or a source owned by itself. The usual scoped evidence citations and real
backend-session provenance remain required. Canonical model/code repairs do not
rewrite this historical bundle; corrupted snapshots still block verification.
The deterministic owner map and remaining attempt count are workflow outputs,
not agent-controlled budget changes. This contract neither approves the proposed
steps nor establishes that they fix the model. See workflow_v2.md for current
automatic dispatch and remaining repair application limitations.


## Staged code repair request (T08)

`code_repair_request` is host-generated, not an agent's permission to change the
model. It binds repair/question/time, diagnosis and failed-run pins, original
specification, actual execution role, candidate spec and review paths, and each
original code file's immutable snapshot/hash and deterministic candidate path.
The verifier rederives the complete request from current verified failure evidence.
It rejects other failure classes, exhausted attempts, altered originals and path
redirection. Original model/code files are never overwritten by this adapter.

The code/probe role may propose the exact corresponding candidate spec and Python
bundle. Verification preserves all model semantics and requires one actual
producer handoff covering the entire bundle. Independent semantic review must
bind the original failure and complete repair evidence, and cannot be authored by
the code author or diagnostician. A reviewed candidate is not a successful run,
accepted mathematical result or activated workflow model. See workflow_v2.md for
the remaining activation/retry/validation boundaries.
