# V2 contract catalog (T02 design)

All new contracts use `schema_version: "2.0"`, JSON Schema Draft 2020-12 and strict
object fields. This catalog defines responsibilities before implementation.
Later schemas/tests are executable definitions; changed contracts must update
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
