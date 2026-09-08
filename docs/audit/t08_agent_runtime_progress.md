# T08 agent runtime — IN PROGRESS

T00–T07 are committed and pushed. T07 head is `b0117c5`; this document describes
the first T08 implementation checkpoint, not a completed stage or a release
acceptance claim. T08 is split into reviewable implementation checkpoints as
permitted by `git_rule.md`; its remaining work below precedes T09.

Implemented so far: role output scopes, structured agent task/response/result
contracts, independent reviewer identity checks, canonical output validation,
input/control tamper rejection, real Codex CLI backend, AI usage events,
deterministic input statistics, actual measured risk-probe reports and a numerical
lifecycle coordinator. Thirteen new schemas bring the generated catalog to 33.
Complete live role-chain examples and several integrations remain outstanding.

Official backend documentation was searched through the official documentation
index and fetched from
<https://developers.openai.com/codex/noninteractive/>, which redirected to
<https://learn.chatgpt.com/docs/non-interactive-mode>. Installed CLI: 0.153.4.
The actual local `codex exec --help` confirms `--json`, `--output-schema`,
`--output-last-message`, `--ephemeral`, `--sandbox read-only` and
`--skip-git-repo-check`. The backend uses explicit argv and native/node launchers,
preserves configured CLI authentication/model choice, and records an unreported
model as null rather than guessing its name. No credential values are published.

A real synthetic council call succeeded after two recorded transport-schema
failures. The service first required explicit types for const/enums, then rejected
regex lookaround. The transport schema now uses typed enums and omits provider-
unsupported pattern/uniqueItems keywords; canonical parent validation retains all
restrictions. Third attempt exited 0 and produced an actual statistical proposal
in 50.39 seconds: affine least squares main, training-mean baseline, and explicit
small-sample/extrapolation limitations without invented empirical scores.

Private evidence location (outside this public template):
`../mathmode_agent_smoke/smoke-b4a8d753e569/agent_runs/` with task IDs
`council-smoke`, `council-smoke-retry`, `council-smoke-final`.
Successful response SHA-256:
`86f2e56d0ed06af5419f45da33b9754e77fc9fd3f60efcc76e82004e39bc63fd`.
Published synthetic proposal SHA-256:
`04bb92940626935aa77119fc5dee952b823509d51bd0cf22d2f10a55511e2128`.
These are backend integration observations, not full contest-solver evidence.

Integration refinement: model-generated validation/probe plans can now be pinned
as separately snapshotted contracts before execution without rewriting the original
input manifest. `validation_plan.criteria` and optional `validation_plan.probe`
are hashed before/after execution; `run_manifest.contract_snapshots` binds them.
Legacy criteria imported as original rule inputs remain readable. Runner/validator/
freeze bindings have been adapted and their targeted real-run tests pass.

Additional completed work:

- `verify_agent_result` rechecks registered request/response/result/transcript
  provenance, the full hashed input/control bundle and current canonical artifacts.
  Fixture transports cannot pass a reasoning handoff. Backend exceptions become
  truthful failed records without copying potentially credential-bearing messages.
- Role/question/view/evidence identities and review verdict semantics are checked.
  Fresh task IDs or actor names cannot reset an unresolved three-attempt chain.
  Both direct transport and scheduler reject an agent impersonating human_gate.
- Generated criteria and probe plans are separately snapshotted without rewriting
  original inputs. Fallback runs now require a measured trigger pinned in the
  method card before the probe, with reverified card/report/run hashes.
- A real two-question test executes Q2 using Q1's frozen values, independently
  validates and freezes Q2, then thaws Q1 and observes Q2 invalidation. This exposed
  and fixed an order-only dependency comparison defect; ID/hash mappings are now
  compared without treating list reordering as changed scientific evidence.
- `Orchestrator` resolves real input hashes, schedules a role DAG, rechecks completed
  handoffs on resume, checks framing/source/role prerequisites and upstream question
  freezes. CLI entries: agent, verify-agent, advance-agents, data-audit, probe-report.
  `Workflow` now connects numerical transitions through G6; paper remains T09 work.
- AGENTS/CLAUDE are thin generated routers from `docs/agent_router.md`, sharing
  `docs/runtime_rules.md`. `sync_agent_assets.py --check` passes; both complete figure
  skill mirrors retain 263 identical files. Original DOCX/class/sty/figure assets
  show no diff against the baseline. A changed-file credential-pattern scan found
  no matches (pattern scanning is not an exhaustive confidentiality proof).
- Reference baseline sealing now requires actual framer/writer handoffs and a
  current numerical freeze, and preserves independent immutable copies of frame,
  models, code, results and paper. Same-problem access requires this checkpoint;
  method source proposals require actual supplied snapshot hashes and admission
  before retrieval/dispatch. CLI: seal-baseline and admit-reference. Outside-host
  reference exposure remains explicitly unverifiable. Reference tests use real
  computed freezes and explicitly mocked role authorship, not a claim of a live
  complete paper baseline; real historical use remains T11 work.
- Interrupted execution recovery now records real owner PID/creation time, child
  and observed descendant identities. It refuses active/unknown owners, active
  recorded children/descendants, timestamp-only legacy locks and ambiguous launches
  lacking process identity. Pre-launch interruption is distinguished explicitly.
  `recover` and `recover-lock` retain evidence, record ABANDONED with null returncode,
  and continue actual retry histories without manufacturing completed manifests.
  New successful local run controls hash owner/process metadata. psutil 7.2.2 was
  already installed in Conda test and is now declared as a runtime dependency.
  Observation remains best effort; unobserved/detached descendants are not claimed
  impossible and descendant_quiescence remains NOT_PROVEN.

Real updated handoff smoke outside the public repository:
`../mathmode_agent_smoke/handoff-cb203914abac`, task `council-handoff-smoke`.
The actual backend call produced a proposal in 68.91 seconds and passed the new
handoff verifier, including its CLI entry. Session:
`01a08078-167b-7b30-862f-79aa659bdd75`; response SHA-256:
`cbdf74c6f6687bbc993c3fb6a3b0753fc8744c151110640d2369b61e1a398e2b`.
Provider remains `codex-configured-provider`, model unreported/null.

Real scheduler smoke: `../mathmode_agent_smoke/schedule-2ccbd0aec788`.
`frame-smoke` timed out after 181.47 seconds while making unnecessary transcript
reads. The failure is preserved. Instructions now batch independent input/schema
reads and exclude runtime transcripts. Explicit attempt 2, `frame-smoke-retry`,
produced actual frame/DAG contracts in 105.58 seconds. Session:
`01a08082-941e-7e00-8cdf-e84c21cd3866`; response SHA-256:
`7ea874d5d7c8ac780da170b36af9b63e2d19202730f83283c1515e31016517d7`.
Resume reverified the successful task and executed zero new tasks. Schedule PASS
retained scientific_acceptance=NOT_RUN and official_compliance=NOT_RUN.

Latest full regression, including scheduler, reference baseline/source admission
and real interrupted process recovery: **157 passed, 1 skipped** in 208.07s.
The five recovery cases exercise live owner/child/descendant refusal, preserved
run and agent attempts, actual pre-launch interruption, ambiguous launch refusal,
legacy lock refusal and PID reuse. The Windows symlink privilege skip is unchanged.
That earlier regression preceded the workflow coordinator additions below.
The deliberately blocked schedule fixture passes structural validation only.
Standard `git diff --check` passes under the repository's configured line-ending
policy. The previous 45-path scan found no credential-pattern matches; no credentials
are included in the newly added process/recovery metadata or tests.
The complete stage requirements below remain; this checkpoint does not mark T08 PASS.

Lifecycle additions at this checkpoint:

- `workflow_plan` covers every framed question and names actual role handoffs,
  measured probes, reviewed main/baseline specs, independent semantic reviews and
  frozen-number locators. `workflow_progress` stores only resume pointers.
- `Workflow.observe` recomputes G0–G6 and keeps G7/G8 explicitly BLOCKED pending
  paper/visual/final evidence. G0 remains blocked with the default unverified policy.
  `Workflow.advance` performs one admissible numerical/role transition per call.
- Missing progress adopts current verified runs/validation. Explicit repaired
  successful runs replace stale pointers and clear obsolete validation pointers.
  Thaw requires new main and baseline executions even without source changes.
- Generated validation-review tasks exclude solver source/intermediates and cite
  actual run-specific numerical evidence. Stale historical outputs cannot enter
  the bundle and do not prevent using valid repaired outputs. Existing reviews of
  old evidence cannot suppress review of a new numerical pair. A current unfavorable
  review is not repeatedly queried for a better verdict.
- A separate workflow owner lock serializes complete coordinator transitions.
  Real process tests refuse live-owner recovery, preserve crash ownership and
  require explicit scoped recovery. Individual interrupted execution recovery
  remains necessary; the lock does not establish universal child quiescence.
- Root runtime directories, state/progress/freeze indexes, AI logs and both lock
  files are ignored in the public template. Nested schemas and regression fixtures
  remain trackable; the workspace initializer still defaults outside the repository.
- Successful critic revisions are limited to three per question/view and unchanged
  original/framing hashes, even with new task/actor/proposal IDs. Explicitly
  recovered validator tasks preserve their original retry chain on dispatch.
- `fixtures/agents/workflow_plan.json` is consumed by actual numerical lifecycle
  tests. Main MSE 0 and baseline MSE 26 are independently computed for the synthetic
  affine fixture. Role provenance alone is mocked, and the unpatched coordinator
  rejects these authored files as reasoning evidence. This is not a historical run.

Fetch during this checkpoint found five new `origin/main` research-only commits,
ending at `707ba40`. They add survey documents and update `research/INDEX.md`, with
no overlap with these runtime edits. The feature branch history is preserved;
base integration must be rechecked before the eventual PR. No merge to main is
authorized by this optimization goal.

Checkpoint verification in Conda test (Python 3.12.13): full regression **165
passed, 1 skipped** in 281.85s. The skip requires unavailable Windows symlink
privilege. After the final fix ensuring old evidence reviews do not suppress new
reviews, the entire workflow test file passed again: **5 passed** in 76.64s.
Compileall, all **33** distributed schemas, the structural example plan and
router/mirror checks pass. Both figure skill mirrors retain **263** identical files.
Protected DOCX/class/sty/figure assets have no diff from `d3b3f48`. A changed-file
credential/email/phone pattern scan found no matches and no changed file exceeds
5 MB; pattern scanning is not an exhaustive privacy proof. Root runtime ignore
patterns were checked directly with `git check-ignore`. No CI or historical E2E
completion is inferred from these local checks.

Still required before T08 can be committed as complete:

- Extend the numerical coordinator to complete live multi-question role chains and
  reviewed stage examples; G7/G8 visual/paper observations require T09 adapters.
- Complete the honest host human-event boundary and all-question reference-blind
  checkpoint enforcement for references covering the entire contest problem.
- Automatic repair/recovery routing beyond explicit recovered-task resume.
- Complete role semantic checks/examples, deterministic data/probe disposition,
  validator criteria admission, method source access controls and framing assumption
  review. Visual/paper dispatch intentionally requires the pending T09 handoff adapter.
- Keep contracts/migration/backend documentation and exact Git/privacy/asset checks
  synchronized as the remaining T08 integrations are added, then record stage PASS.

T09 legacy visual/paper/support integration, T10 CI/computed five-case benchmark,
T11 complete public historical dry run, and T12 release/PR/CI acceptance all remain
required. Do not merge. The overall goal remains active.

## Follow-up: measured fallback lifecycle

The next T08 checkpoint connects fallback selection through code review, actual
execution, independent validation and freeze. The additive optional decision field
`execution_role` preserves old main decisions while recording fallback explicitly.
The main probe must activate a trigger pinned before execution and the fallback's
own six-category probe must pass. All reports bind the same current card/question;
the attributed decision cites both reports. There is no automatic choice merely
because a fallback is eligible.

Fallback code/semantic reviews must include the decision, card and both reports.
The source-free validator bundle admits those selection artifacts and retains the
actual fallback role. Independent recomputation uses the same original task,
constraints, split, units, criteria and usable baseline. A validator's own spec
does not inherit the solver's execution authorization. Resume can adopt actual
fallback runs, and altered screening evidence breaks their freeze lineage.

The unselected main's rejected assumptions and historical formula references stay
in the ledger without forcing abandoned formulae into the selected fallback model.
An active method still cannot rely on rejected assumptions or unknown formulae.
Decision proposals now reject evidence references outside their actual input scope.

The new synthetic lifecycle fixture uses a median pairwise training-slope solver,
a training-mean baseline and actual independent holdout metrics (0 and 26 MSE).
Its main probe uses a deliberately strict variance threshold to exercise the
trigger; it does not claim least squares is scientifically invalid for those
data. The independent review provenance is explicitly doubled for engineering
tests, while numerical execution, checks, frozen values and tamper detection are
real. A static fallback-decision example provides structure only, not admission.

This implements fallback from completed measured probes. A production crash or
timeout without such evidence still requires explicit repair/re-probing and a new
attributed decision; automatic failure routing is not yet implemented. T08 human
event admission, retrieval integration, LIMITED/data-warning disposition and full
live role-chain examples still remain before T08 PASS. G7/G8 and all T09–T12
deliverables remain pending.

Verification: full regression **168 passed, 1 skipped** in 379.62s in Conda test.
The Windows symlink-privilege skip is unchanged. With implementation unchanged,
two additional decision-artifact scope tests passed in 1.85s, and an additional
fallback-validator guard test passed in 8.19s. The latter independently exercises
missing decision/probe refusal and solver-source exclusion with the role authorship
fixture double. Compileall, all 33 distributed schemas, the structural decision
example and router/mirror checks pass. Protected assets remain unchanged and the
changed-file credential/email/phone pattern scan reports no matches. These local
checks do not establish live historical completion or GitHub CI acceptance.

## Follow-up: actual reference retrieval and source handoff

`reference_retrieval` expands the generated catalog to 34. The HTTP service now
records host admission before each initial/redirect GET, preserves the actual
response bytes and metadata, and binds the receipt/controls/snapshot into lineage.
Same-problem access requires the existing sealed question baseline before any
network read. Failed/empty/truncated/oversized responses, redirect failures and
timeouts preserve FAILED receipts and cannot supply reference snapshots. Existing
IDs are never overwritten and verification never downloads a newer version.

HTTP method-source summaries require the actual receipt plus body snapshot in
their role input bundle. URI, question/classification, observed access time and
byte hashes are checked before publication. Host-declared `reference_requests`
can be advanced one at a time by the workflow. Requests awaiting same-problem
baseline admission remain unread while the blind numerical pipeline progresses.
Root reference snapshots and baseline directories are ignored in the public repo.

Actual public HTTP integration retrieved the general SciPy `theilslopes` method
documentation from
<https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html>.
Observed page title: `theilslopes — SciPy v1.18.0 Manual`. The response contained
44,758 bytes; SHA-256:
`f7c7e27202daf9cd85c1f06b8620253ae69260ea57499dea094b48465c9e20f5`.
Receipt SHA-256:
`0b73ae2c0a8def789b2f10c05bd7f59bdd7a4c57fedfc922139acd2d9e4315a3`.
Private raw evidence stays in
`../mathmode_reference_smoke/http-3338b575bb43/`; no third-party HTML is committed.

A real configured Codex method-retriever call consumed that exact snapshot and
receipt, produced an attributed definition/limitations record and passed the real
handoff verifier in 64.77s. Task: `retrieved-source-smoke`; session:
`01a080ee-9196-7000-8a07-4be47964d636`. Response SHA-256:
`b0d37cb44a82242561e761fef5cd02cd459a45a25e71eb8a8c4e05d15123710d`.
Provider is `codex-configured-provider`; model was not reported and remains null.
The output describes the median pairwise-slope estimator and documentation caveats;
it does not invent experiments or claim a contest result. This verifies real
download → source summary → provenance handoff, not an entire modeling workflow.

The timeout scope is socket operations and checks between chunks; OS DNS lookup
is not a hard wall-clock process limit. URL/redirect classification remains a
trusted host assertion; outside-host exposure is UNVERIFIABLE. Search/discovery,
whole-problem blind checkpoint enforcement, human events, warning/LIMITED
disposition, automatic repair routing and complete live role chains remain T08
work. G7/G8 and the T09–T12 deliverables are still outstanding.

Verification: full regression **195 passed, 1 skipped** in 480.54s (Conda test).
The Windows symlink-privilege skip is unchanged. After making the workflow test
consume the static host-request fixture, that test passed again in 10.38s without
an implementation change. Current CLI `verify-reference` and `verify-agent` both
pass for the real SciPy/source-summary smoke evidence. Compileall, all 34 schemas
and both complete 263-file skill mirrors pass. Protected template assets remain
unchanged. The privacy-pattern scan flags only the deliberately fake URL-userinfo
rejection fixture; its literal placeholder was inspected and no actual credential,
email identity or private contest content was found. Root reference ignore rules
were checked directly. Fetch found only a new research survey/index change on
`origin/main` (`5d7abb4`), with no runtime overlap. No merge to main is performed.

## Follow-up: complete-case blindness and explicit non-blind work

The catalog now contains 35 contracts. `reference_case_baseline` binds all framed
questions' existing immutable checkpoints. Each question still needs a real
framer/writer handoff and its actual independently validated numerical freeze;
the aggregate additionally requires exact question coverage, identical full-frame
and original-input-manifest hashes, and the current question freezes. It cannot
be assembled after any same-problem access. Question sealing now also treats
exposure to another question as exposure to the whole problem.

`seal-case-baseline` and `verify-baseline` expose creation and historical checking.
Single-question baseline records remain readable and directly admissible for
single-question frames. Multi-question source admission requires the aggregate.
Before first exposure, current frame/input identity must match the sealed history.
HTTP receipts depend transitively on all question snapshots, and both HTTP and
local source handoffs recheck admission semantics. Old partial-case admissions
remain diagnostic records, not a migration path to restored blindness. Later
reference-informed canonical revisions preserve the independent historical copies.

`goal.md` explicitly limits mandatory blindness to independent evaluation, not
every official competition. `init --no-blind-reference-mode` now selects non-blind
work explicitly; the compatible default remains true. Ordinary `StateStore`
mutations cannot change it in either direction. New events/HTTP receipts record
the mode; legacy records default to true. Non-blind same-problem retrieval has no
baseline ID and cannot claim one. The trusted host can still read outside the
system or directly rewrite files; no OS-level blindness enforcement is claimed.

The engineering regression computes Q1 and dependent Q2 with real subprocesses,
independent validation and MSE freezes. Its framer/writer authorship and paper
draft are explicit synthetic test doubles. It checks refusal before any network
request when Q2 is missing, actual aggregate-admitted redirect/download, immutable
history after canonical revisions, Q2 snapshot tampering propagating to receipts,
mixed frames/forged original fingerprints/incomplete aggregates, legacy single
question reads and old partial-case exposure, immutable mode and non-blind CLI
initialization/download. The static aggregate fixture contains illustrative hashes
for schema tests only. These tests do not complete a historical scientific run.

T08 still requires host human-event admission, warning/LIMITED dispositions,
automatic repair routing, source discovery and complete live role-chain examples.
T09 visual/paper/support integration, T10 CI/benchmark, T11 full historical contest
and T12 release/PR acceptance remain required. No T08 PASS or overall completion
is claimed by this checkpoint.

Verification: full regression **203 passed, 1 skipped** in 676.90s in Conda test.
The skip is the existing Windows symlink-privilege test. Earlier focused reference
tests passed 25/25; case/upstream/contract tests passed 61 with the same one skip.
The full run also covers the subsequently added forged-original-fingerprint
negative. Compileall, all 35 distributed schemas and both complete 263-file skill
mirrors pass. The existing real SciPy download and actual method-retriever handoff
still pass current CLI verification without refetching. Protected assets and
large files are unchanged; changed-file credential/email/phone pattern scans found
no matches. These are local checks, not GitHub CI or historical-contest acceptance.

## Follow-up: human decision terminal boundary

The catalog now contains 37 contracts. `human_decision_request` binds the actual
framed question, screened methods/probes, exact task input hashes and immutable
task/display snapshots. The scheduler prepares it in `human_gate` without calling
a model, returns WAITING_HUMAN and exposes the request ID. The existing workflow
can also prepare/resume requests with `--no-agent`; other ready reasoning roles
remain WAITING_AGENT when no backend is present.

`human-decision` displays the question, methods, critic findings and measured
probes, then reads an eligible role or deferral, a rationale and explicit SUBMIT
from interactive input/output streams. A `human_decision_event` retains that host
observation and request hash. Piped input, missing/invalid choice, cancellation,
deferral and model-supplied human JSON cannot publish a method choice. Human tasks
produce no invented agent session or AI-usage entry. Raw code transport in human
mode also checks the actual host event before invoking its backend.

The request is reverified after the wait and under the writer lock. A current
event publishes an append-only decision; empty ledgers and valid legacy final lines
without a newline preserve their original byte hashes. `verify-human-decision`
checks exact event-derived fields, actor, prior ledger bytes, screening and lineage.
Resume uses a completed choice without another prompt; a registered response
interrupted before publication is recoverable through the same command. Old task
IDs cannot silently change scope. A new explicit task can request reconsideration
after input changes while retaining old event history. Active frozen consumers
must be thawed before the current decision ledger can change. Multiple unresolved
terminal responses require explicit reconciliation; an already published choice
remains authoritative on resume.

Engineering tests use explicitly named in-memory terminal doubles and mocked
framer/critic/semantic-review provenance. The actual host code consumes those
streams, while probe, main/baseline, independent validation and numerical freezing
run as real subprocesses. They exercise main and eligible fallback choices,
cancel/defer/piped input, stale evidence during the wait, changed task scope,
interrupted publication, append-only history, new responses after changed framing,
frozen-consumer refusal and event tampering invalidating downstream numerical
freeze. These are not real user interactions or scientific acceptance. A live
human terminal session remains NOT_RUN; the host boundary explicitly does not
authenticate the person at the keyboard or protect against direct host tampering.

The first full regression exposed an intermittent Windows DOCX package-replacement
denial in the existing policy derivative test. The independent repair, bounded
retry behavior and 26 passing focused tests are documented in
`docs/audit/docx_windows_replacement.md` and committed separately as `c6130be`.
The latest six focused human-decision tests passed before the final full run.

T08 warning/LIMITED disposition, automatic repair routing, source discovery and
complete live role-chain examples remain required. T09 visual/paper/support,
T10 CI/benchmark, T11 full historical contest and T12 release/PR acceptance remain
outstanding. This checkpoint does not claim T08 PASS or overall completion.

Final verification for this checkpoint: **218 passed, 1 skipped** in 826.95s in
Conda test. The skip remains the Windows symlink-privilege case. This final run
includes the current terminal/reconsideration/history implementation and the DOCX
replacement repair. Compileall, all 37 schema distributions and both complete
263-file skill mirrors pass. The existing real SciPy retrieval and actual method
retriever handoff still pass their current CLI verifiers without refetching.
Changed-file privacy patterns found no matches; no protected assets or large files
changed. Human request/event ignore rules were directly checked. Fetch found only
the research report/index addition `b599be7` on main, with no runtime overlap;
there is no merge, PR or GitHub CI acceptance claim at this stage.

## Reviewed warning/LIMITED continuation checkpoint

The subsequent implementation admits exact current data reports to inspection,
requires hash-bound proposals and independent role reviews before bounded use,
retains LIMITED throughout affected workflow gates and immutable numerical
freezes, and inherits restrictions through actual upstream freezes. The catalog
now contains 39 contracts. Its evidence, compatibility boundaries and remaining
work are in `t08_reviewed_dispositions.md`. This adds a warning-handling path;
T08 remains IN PROGRESS and the full T09–T12 deliverables remain outstanding.

Final verification for this checkpoint: **223 passed, 1 skipped** in 859.19s in
Conda test; full compileall, all 39 schemas and both 263-file mirrors pass. The skip
remains Windows symlink privilege. No protected assets changed, no changed-file
privacy-pattern matches or new large files were found, and diff whitespace checks
pass. This remains feature-branch progress, not final release/CI acceptance.
