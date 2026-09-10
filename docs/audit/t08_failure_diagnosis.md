# T08 terminal failure diagnosis checkpoint

Date: 2026-09-09. Parent: `ac3d6b0378f2eb6c20b03a888ecc9bf3990e4fe1`.
Branch: `feat/mathmode-v2-evidence-runtime`. T08 remains **IN PROGRESS**.

## Observed gap and actual transition

After a terminal main/baseline/fallback run failed, the workflow recorded the
failed pointer and then stopped without dispatching diagnosis. A failed probe
without a measured report could instead reach the runner's explicit-retry guard
on resume. Both cases now inspect verified history and dispatch a fixed independent
reviewer task through the existing real agent transport. This is an actual
scheduled diagnostic call, not a static role description or an automatic PASS.

The task binds a complete bundle of the manifest's historical input/code/spec and
sidecar snapshots, recorded outputs, logs and controls, and the current framed
question DAG. Historical files are opaque evidence, so a snapshot resembling a
model contract cannot substitute for a current approved model handoff. Runner
ownership of those bytes is separate from the failed model's actual author; the
reviewer must differ from that author. Canonical repairs do not silently rewrite
the failed bundle or invalidate its historical meaning.

`failure_diagnosis` is an additive 2.0 contract (catalog: 42). It pins the actual
terminal failed manifest and records question, reviewer, underlying failure class,
stable cause identifier, rationale, scoped evidence citations and ordered repair
steps. A process-level CODE_FAILURE can have an underlying data/model cause;
this classification is an independent judgment, not mechanically proven truth.
Publication checks the source hash, complete task input bundle, source citation,
same question and actual different failed producer. Existing real backend-session
checks still apply. The deterministic owner map exposes the responsible next
stage and the runner's remaining attempts, without allowing a diagnosis to alter
the budget or authorize a numerical retry.

One failed run has one deterministic diagnostic task and output path. Repeated
resume adopts the verified diagnosis. A failed or interrupted diagnostic call is
preserved; the workflow does not solicit a fresh verdict under a new identifier.
Missing backend stays WAITING_AGENT. Hand-authored files, stale transport,
modified source/logs or omitted bundle files do not become accepted handoffs.
`verify-diagnosis` confines its PASS to diagnostic integrity/provenance and emits
scientific_acceptance=NOT_RUN. The actual run remains FAIL.

## Verification scope

Broad regression: `pytest -q` completed with **251 passed, 1 skipped in
975.13s**. It began before the final historical-log instruction correction and
failure_source path restriction discovered by the real smoke. It is not claimed
to have tested those later changes. The final source then passed
`tests/test_repairs.py tests/test_contracts.py tests/test_agents.py
 tests/test_orchestrator.py`: **104 passed, 1 skipped in 41.62s**, including the
source-path negative and explicit diagnostic retry. The Windows symlink privilege
is the sole skip. Actual provider verification of the corrected instructions and
source pin is recorded below.

Earlier checkpoints: 92 passed/1 skipped for the initial diagnosis, contract and
agent checks; 26 passed for workflow/fallback/orchestrator integration; and 102
passed/1 skipped before the final source-pin refinement. These are scoped
intermediate results, not additional historical or scientific acceptance.

Final compileall for the repository, all 42 distributed contracts, router parity,
both complete 263-file skill mirrors and default git diff whitespace checks PASS.
The 20 intended changed files have no scanned credential/email/phone patterns,
no files over 5 MB and no protected template or figure changes. External smoke
workspaces and full provider transcripts remain outside the repository.

The tests execute actual failing Python subprocesses. Diagnostic proposals and
framed DAG provenance are explicitly doubled in positive unit tests; the tests
also confirm those transport doubles fail real backend-session verification.
Negatives cover altered source pins/logs, missing manifest citation, self-review,
wrong question, incomplete bundle, authored diagnosis, failed-proposal reuse and
missing backend. The workflow test observes a real production failure and its
subsequent diagnostic schedule without changing the failed progress pointer.

## Real provider smoke and fixes

Actual Codex CLI calls used repository-external synthetic workspaces under
`../mathmode_repair_smoke/`. No provider token, original private material or
workspace output is added to this template repository. Provider is
`codex-configured-provider`; model is null/unreported.

The first workspace (`smoke-e9b2f4fc60e1`) completed actual framing, an actual
Python NameError, and a real diagnostic response. It exposed an instruction
conflict: the generic instruction to avoid execution transcripts caused the
reviewer to exclude even explicitly supplied historical logs. Its diagnosis
honestly retained that limitation and used static code evidence. Both the shared
role instruction and Codex CLI task message now distinguish supplied historical
log snapshots from the worker's own live execution transcripts.

The next workspace (`smoke-64b058076999`) performed new actual framing and a new
actual failing run, `run-85d9a8ef31e94637b45247bcc6f358fa`. The first diagnostic
proposal read the historical traceback but incorrectly pinned the code snapshot
as failure_source. Publication rejected it and preserved FAILED. The contract
now restricts failure_source to a runs/<id>/run_manifest.json path, and generated
diagnostic instructions explicitly supply that manifest's path/hash.

An explicit second diagnostic attempt superseded that same failed task; it did
not create another numerical run or reset the diagnostic budget. It returned a
valid diagnosis, passed real backend-session verification and was reused on
workflow diagnostic resume with no new execution. The old failed agent_result
hash remained unchanged. The actual provider transcript contains a successful
PowerShell command iterating all input_map bundle paths; its output includes
the actual NameError traceback. This confirms historical logs were read rather
than merely included in a request or claimed by the final text.

Final diagnostic task:
`failure-diagnosis-run-85d9a8ef31e94637b45247bcc6f358fa-retry`.
Session: `01a081c9-1151-73c3-bcdd-8c829e3db5aa`; duration: 74.766 seconds.
Failed manifest SHA-256:
`b4112da70b2145334116603027895ee2bb31b93fd21d9cd2972990d35235c940`.
Diagnosis SHA-256:
`c813b33193f9965cb520ee4fa9186c4cdd17ae3610120d2c8e34cda93ba16dbf`.
Preserved first failed diagnostic result SHA-256:
`fef454eabdbf360e94229d2af4e95299ce4c616f13eb220f5678bf3ec98faf77`.
The external report is `smoke-64b058076999/retry_report.json`.

This is real transport/reasoning over a synthetic engineering failure. It is
neither a historical contest nor an implemented scientific repair. The reviewer
retained missing full requirements/validator and runtime capability boundaries;
no solver correction, rerun, numerical validation or final approval was inferred.

## Remaining work

This checkpoint automatically dispatches diagnosis and identifies the repair
owner. It does not yet apply the steps, independently review a code repair,
authorize/run it, escalate exhausted budgets, handle validation-summary failures
or diagnose preflight exceptions without terminal manifests. Unregistered
partial/invalid output bytes are not retrospectively claimed to be hashed by an
old manifest. Insufficient evidence must remain a diagnostic blocker.

Cross-method root-cause budgets, automatic repair application and full live
multi-question role chains remain T08 work. The local evidence store is not an
authenticated append-only log or an OS sandbox. Historical fallback verification
still checks its authorization; corrupted historical evidence is not silently
weakened for convenience. T09 visual/paper/support lineage, T10 final CI/benchmark,
T11 the full public historical contest and T12 release/PR/CI remain outstanding.
No final scientific, official-policy, human, historical or release acceptance is
inferred from a diagnosis or this engineering checkpoint.
