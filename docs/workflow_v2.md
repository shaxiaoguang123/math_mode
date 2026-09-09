# V2 workflow and state machine (T02 design)

The outer workflow has six phases. Every entry guard reads current canonical
files; prior chat, existing filenames or a previous PASS cannot authorize a stale
stage. See [contracts](contracts.md) and [architecture](architecture_v2.md).

| Phase / gate | Evidence required | Next producer if missing |
| --- | --- | --- |
| 0 / G0 POLICY_READY | Verified official policy and template hash; official/heuristic split | Policy curator; retain POLICY_FAILURE if unverified |
| 1 / G1 INPUTS_FROZEN | Complete original-input roles/hashes and read-only originals | Input/data auditor |
| 1 / G2 PROBLEM_FRAMED | Full question frame, valid DAG, symbols, reviewed ambiguity/assumptions, data audit | Framer/ambiguity/data roles |
| 2 / G3 METHOD_SCREENED | Main + usable baseline, executed probes, optional concrete fallback | Council, critic, probe runner |
| 2 / G3.5 METHOD_DECIDED | Attributed decision citing fresh probe evidence | Decision agent in autopilot; actual user in human_gate |
| 3 / G4 CODE_AND_RUN_VALID | Reviewed implementation, actual successful main/baseline runs, output contracts/hashes | Code agent or runner |
| 4 / G5 EVIDENCE_PASSED | Independent computation, constraints/metrics, applicable robustness, fresh artifact lineage | Independent validator and evidence auditor |
| 4 / G6 RESULTS_FROZEN | Immutable values/units/locators and current validated source hashes | Freeze service |
| 5 / G7 PAPER_READY | Frozen numerical claims, validated figures/tables/references, complete paper, source/render/format QA | Visual agent and paper writer |
| 5 / G8 FINAL_AUDIT | Every question answered; cross-media consistency; official outputs and package; AI disclosure; current official policy | Independent final auditor |

G0/G8 official-compliance requirements cannot be bypassed by lean mode or fixture
mode. Synthetic engineering fixtures explicitly label synthetic policy and cannot
claim official compliance. Read-only input research and runtime development can
proceed while official sources are being verified; final submission remains gated.

## Runtime transition rules

Artifacts: `DRAFT → VALID → FROZEN`; failure gives `FAILED`; missing or changed
dependencies produce `STALE`. Only successful rerun and revalidation produce new
VALID/FROZEN artifacts. Old versions remain historical, not current acceptance.

Gate observations: `NOT_RUN`, `PASS`, `LIMITED`, `WARN`, `FAIL`, `BLOCKED`. PASS requires all
applicable checks completed without blocker or unresolved warning. Nonapplicable
checks carry a concrete reason; they are not silently marked passed. Human review
required by actual policy remains pending until the reviewer event arrives.
LIMITED preserves independently reviewed restrictions and permits only the bounded
numerical continuation described below; it never establishes final acceptance.

Agent work: `PENDING → RUNNING → PRODUCED → REVIEWED`; failures route to the
responsible upstream stage. A task result is a proposal until its independent
checks pass. Actor output cannot set a gate directly. Role access is enforced at
the harness input/tool boundary, with local OS trust limits stated explicitly.

| Role | Reads | Writes / handoff | Prohibited |
| --- | --- | --- | --- |
| Orchestrator | Current contracts, DAG, gate results | Tasks/state; next responsible role | Choosing models, fabricating results, self-approval |
| Framer | Original problem/policy/input manifest | Frame/DAG → ambiguity and data auditors | Quietly changing official question requirements |
| Ambiguity/assumption auditor | Original sources, frame, units | Registers/ledger/symbol issues → framer/modeler | Treating unresolved ambiguity as fact |
| Data auditor | Original data and schema | Coverage/quality/split audit → council | Rewriting originals or training on holdout |
| Method retriever | Frame/data audit, permitted literature | Source-backed method cards → council | Same-problem references before blind freeze |
| Modeling council | Canonical frame/data/assumptions | Applicable five-view proposals → critic | Voting unsupported claims into truth |
| Critic | Proposals, requirements, probe results | Named blockers and repairs → council | Editing measurements to improve a score |
| Risk probe role | Candidate/spec/raw inputs | Small executable probes + measured summary → decision | Declaring unexecuted probe PASS |
| Model decision | Fresh critic/probe evidence | Attributed choice → code role | Fabricating a human decision |
| Code role | Approved spec/input contract | Main/baseline source → code reviewer/runner | Untriggered fallback or result approval |
| Runner | Reviewed code bundle, declared inputs | Immutable run record → validator | Choosing a model or claiming mathematical correctness |
| Independent validator | Original inputs, spec, final outputs, criteria | Independent code/run/validation → evidence auditor | Solver imports/intermediates or actor self-review |
| Evidence auditor | Fresh run/validation/claim chain | Gate findings → freeze or repair owner | Repairing facts inside the audit |
| Visual role | Frozen results, approved figure plan | Figure/QA → visual auditor and writer | Reading arbitrary exploratory CSV for final figures |
| Writer | Verified freeze/package/spec/assumptions/references/figures | TeX and claim manifest → final audit | Invented numbers, citations or unvalidated claims |
| Final auditor | All current evidence and official policy | Cross-media/package verdict | External contest submission or Git merge |

## Failure recovery and budgets

| Failure class | Return to |
| --- | --- |
| ENV_FAILURE | Interpreter/dependency/backend setup |
| DATA_FAILURE | Input audit, units, schema, splits |
| CODE_FAILURE | Approved implementation and code review |
| MODEL_FAILURE | Assumptions, constraints, method decision/probes |
| VALIDATION_FAILURE | Validator diagnosis; then responsible data/code/model stage |
| POLICY_FAILURE | Official source/scope/template verification |

The target repair lifecycle records class, normalized root cause, changed artifacts,
observation and repair owner. At most three total attempts for the same unresolved cause; the budget
persists across resume. A new traceback spelling or run ID does not reset it.
After exhaustion, return upstream or report an actionable blocker. Every actual
retry uses a fresh output directory and preserves failed evidence.

The runner verifies completed history against its snapshots, logs and execution
controls before using it to select the predecessor or attempt budget. Canonical
source changes are allowed for this historical check; altered historical evidence
blocks execution before a new run directory is created. Failed runs remain FAIL.
Damaged snapshots require explicit diagnosis rather than automatic retries, and
historical fallback runs still require valid fallback authorization. This is a
trusted local evidence check, not protection against coordinated rewriting of all
files. Automatic repair application and cross-method root-cause budgets remain pending.

On resume, a terminal failed main/baseline/fallback or probe run now dispatches an
independent reviewer through the actual agent scheduler. The task receives the
verified failed manifest, complete historical code/input/spec/sidecar snapshots,
recorded outputs, logs and controls, plus the framed question DAG. It produces a pinned
`failure_diagnosis` with a stable cause identifier, rationale, evidence citations
and ordered repair steps. Its classification selects the responsible owner from
the table above; a process `CODE_FAILURE` symptom may have a data/model cause.
The diagnosis remains a scientific judgment, not deterministic root-cause proof.

The fixed task/output identity derives from the failed run. Resuming reuses a
verified diagnosis rather than soliciting another verdict. Failed, interrupted or
unverified diagnostic tasks stay blocked and require explicit repair. Altered
historical evidence blocks dispatch. Canonical code changes do not erase its
historical diagnosis. No backend means WAITING_AGENT, never an invented review.
`verify-diagnosis --workspace <root> --diagnosis reviews/<file>.json` checks actual
role provenance, source pins and historical execution integrity. Its PASS scope
is the diagnostic handoff only; the source remains FAIL. The workflow reports
the next owner, repair steps and remaining run attempts. CODE_FAILURE with a
remaining run budget now advances into staged repair generation and review as
described below. Exhausted attempts return to the upstream modeling owner without
another code task. Validation-summary failures, preflight errors without terminal
manifests, automatic activation/retry and actual upstream modeling escalation
remain subsequent integrations. Existing evidence gates remain blocked.
Unregistered partial/invalid output files are not added as though the old manifest
had hashed them; insufficient recorded evidence must yield a diagnostic blocker.

`code_repair_request` pins the diagnosis, failed run and unchanged original model
specification, and derives fixed candidate spec/code/review paths. The code role
(or probe role for a failed probe) produces a separate complete implementation.
It must preserve the actual author and every model field except the relocated
implementation paths. Parameters, formulae, split, seed, criteria, output and
resource changes are rejected as model changes requiring upstream work. The
candidate spec and every code file must come from one verified producer handoff;
a spec pointing to manually supplied code is insufficient. Byte-identical code
does not constitute a repair. Relocated multi-file imports remain the author's
responsibility and are explicitly reviewed before a future execution.

Another reviewer, different from both code author and diagnostician, reviews the
candidate, failed evidence, current original requirements and selected model pair
when present. Its review must cite the request, diagnosis, failure, original and
candidate specs and complete candidate code. Unresolved findings, LIMITED/BLOCKED
verdicts and missing evidence prevent approval. Fixed task/output identities
preserve failed or interrupted proposals and avoid repeatedly soliciting a more
favorable review. `verify-code-repair --workspace <root> --request
repairs/<repair-id>/request.json` checks this chain; its PASS scope is only the
independently reviewed code repair, with execution and scientific acceptance
NOT_RUN. It does not activate the candidate or call the runner. A subsequent
adapter must bind the reviewed candidate to the effective workflow job, enforce
the latest predecessor and remaining budget, execute, revalidate, reassess stale
assumptions and refreeze. Original sources and failures remain unchanged.

The T08 recovery service now records owner PID/creation time, local child identity
and observed descendants. `mathmode recover` rejects live recorded processes and
preserves a separate ABANDONED event, with no invented returncode or completed run
manifest. An explicit subsequent retry retains the original attempt count. Locks
can be archived/released by `recover-lock` only after their recorded owner stops.
Pre-launch interruption differs from a launch whose process identity was never
recorded; the latter and legacy timestamp-only locks remain diagnostic blockers.
Local process-tree observation remains best effort and cannot prove universal
descendant quiescence. Automatic orchestration of recovery routes remains pending.

## Profiles, reference blindness and disclosure

`autopilot` lets a real reasoning agent decide with `decided_by=agent`.
`human_gate` requires the user's actual response. Both obey the same evidence
gates. `lean` stores core contracts and compact success logs; `submission` adds
full validation, freeze, paper package and final audit. Profiles change reporting
density, not scientific correctness.

For a scheduled `human_gate` decision, `workflow --advance` (also with `--no-agent`)
or `advance-agents` reports a `human_requests` entry after the framed question,
method card and probes are ready. In an interactive terminal, run:

```powershell
python -m mathmode human-decision --workspace ../competitions/case-id --request-id <reported-id> --actor-id local-user
python -m mathmode verify-human-decision --workspace ../competitions/case-id --decision decisions/choice.jsonl
```

The first command displays the actual question, methods and measured probes, then
reads an eligible role (`main` or triggered `fallback`) or `defer`, a reason and
explicit `SUBMIT`. Use the decision path declared in your schedule for verification.
Cancellation/deferral leaves modeling blocked. Changed evidence while waiting
requires a new scoped task/request; the old response cannot approve new evidence.
Resume reuses a completed event without asking again. This interface admits local
terminal input, not a supplied JSON flag or authenticated human identity. Its
engineering tests simulate the terminal and do not claim an actual user's review.

`blind_reference_mode` is explicit for independent evaluation: frame/model/code/
results/paper baseline first, freeze all baseline hashes, then record and permit
same-problem reference access. Never infer past blindness from a hardcoded boolean.
For multi-question problems seal each question with `seal-baseline`, then use
`seal-case-baseline --workspace <root> --baseline-id <Q1-checkpoint> --baseline-id <Q2-checkpoint>`
(repeat for every framed question). Pass the resulting case baseline ID to
`admit-reference` or `retrieve-reference`. The complete frame and original inputs
must agree across checkpoints; each question needs actual model/code/results and
writer-produced TeX. A single-question checkpoint remains directly usable for a
single-question frame. `verify-baseline` inspects either kind of immutable history.
Any same-problem admission prevents claiming a new blind checkpoint for any question.

Use `init --no-blind-reference-mode` when the host explicitly intends non-blind
work; same-problem retrieval then needs no baseline and records that mode. The
default remains blind for compatibility. The choice is immutable during a run,
so changing it requires a new explicitly non-blind workspace, preserving the old
history. Blind mode is for independent evaluation, not an official contest rule.
General algorithm references remain permitted and logged. AI use events record
actual provider/model/activity/artifact scope and any real human postprocessing;
disclosure is derived from events and the verified policy.

For an explicit host-classified HTTP reference, use the retrieval service to create
the actual source snapshot before supplying it to a role:

```powershell
python -m mathmode retrieve-reference --workspace ../competitions/case-id --question-id Q1 --source https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html --classification general --retrieval-id scipy-method
python -m mathmode verify-reference --workspace ../competitions/case-id --receipt references/scipy-method/retrieval.json
```

The method retriever receives both the receipt and `references/scipy-method/body.bin`.
Its source summary binds those exact paths/hashes and the observed completion time.
No PDF/HTML scripts are executed and no literature value becomes an empirical result.
Optional host-declared `reference_requests` in the workflow plan perform one eligible
download per advance before scheduling roles; resume reuses verified receipts.
Same-problem requests without their required sealed baseline remain unread while
the blind computation continues. Retrieval failure is preserved, with no implicit
retry or usable partial snapshot. Redirects are recorded and admitted before GET.

## Engineering completion

T08 implementation is in progress. The `agent_schedule` contract and
`mathmode advance-agents --workspace <root> --schedule <file> --max-tasks <n>`
execute a bounded number of ready role tasks with fresh prerequisite checks.
Task blueprints list paths; the dispatcher resolves actual registered input
hashes after dependencies are produced. Every resume rechecks prior handoffs.
Completed task inputs/instructions cannot be changed through the schedule.

`mathmode data-audit` registers original inputs and authoritative deterministic
statistics. `agent` is the lower-level scoped transport API; `verify-agent` checks
an actual session and its bundle. `probe-report` computes the six-category risk
report from actual run outputs. `mathmode workflow` now coordinates the separate
run/validation/freeze services and observes G0–G8, with G7/G8 explicitly BLOCKED
pending T09 integration. A schedule PASS explicitly does not award scientific
acceptance or official compliance.

For a private workspace with actual role-produced framing/spec/review artifacts,
create a `workflow_plan` covering every framed question. The structural example
`fixtures/agents/workflow_plan.json` is exercised by actual numerical fixture tests;
its paths and synthetic case identity must be adapted to the workspace. It does
not create missing evidence or provide authored PASS records.

```powershell
python -m mathmode workflow --workspace ../competitions/case-id --plan workflow_plan.json
python -m mathmode workflow --workspace ../competitions/case-id --plan workflow_plan.json --advance --no-agent --interpreter <python-path>
python -m mathmode workflow --workspace ../competitions/case-id --plan workflow_plan.json --advance
```

`--plan` is resolved from the CLI working directory; artifact paths inside it are
relative to the private workspace. `--advance` performs one transition. With a
configured backend it can dispatch one ready scheduled role or generate an
independent semantic validation task. `--no-agent` pauses at missing role handoffs.
An overall BLOCKED result can accompany a successful intermediate transition;
inspect `performed`, per-question `next_action` and the gate blockers. CLI exit 0
requires all gates PASS, including final official and paper checks.

Missing progress pointers adopt reverified existing runs/validation without new
computation. Changed/repaired runs replace obsolete pointers and clear previous
validation/evidence pointers. A recorded failed run still needs an explicit repair
and retry; new IDs do not reset budgets. After thaw, both model runs must be new.
Only an independent current semantic review permits workflow numerical freezing.
Warnings and LIMITED verdicts require the independently reviewed dispositions
described below; without them they remain blocked.

When the main probe activates a predeclared fallback trigger, the fallback's own
probe must also pass. An attributed `execution_role=fallback` decision selects it
and the normal usable baseline. Point the plan's `main_spec` at the reviewed
fallback spec; it must pin that exact trigger authorization. The coordinator then
performs `run-fallback` → `run-baseline` → `independent-validate` → semantic review
→ freeze. The code and validation reviews must cite the card, decision and both
probe reports. Existing field names `main_run` and `main_mse` denote the selected
production solution; its actual manifest role remains fallback. A lost progress
pointer reports `adopt-fallback` when adopting its verified completed execution.

Each advance holds a distinct workflow owner lock through dispatch and progress
publication. Concurrent coordinators are refused. After an observed coordinator
exit, use `recover-lock --scope workflow --reason <diagnosis>`; separately recover
interrupted runner/agent executions. Releasing a coordinator lock does not certify
that unobserved child processes have stopped.

The first actual scheduled framer call timed out and remained FAILED. Its explicit
second attempt succeeded after instructions excluded runtime transcript reads and
batched input/schema reads. A subsequent resume executed zero new tasks and verified
the successful handoff. This is synthetic backend integration evidence, not a
completed historical contest run. Details are in `audit/t08_agent_runtime_progress.md`.

T02 **PASS** establishes this state machine, ownership boundaries, contract
catalog, stale graph and implementation sequence before runtime code. Later stage
reports must link actual tests and artifacts. The release must complete T03–T12;
these design documents alone cannot establish MathMode V2 READY.

## Reviewed warning and LIMITED dispositions

Inspection roles can consume a current deterministic WARN/FAIL report to understand
the problem. A FAIL still blocks modeling. A WARN requires an `issue_disposition`
proposal and a different actor's `disposition_review` before modeling dispatch.
The proposal pins the exact data audit or LIMITED semantic review and the complete
problem frame by path/SHA-256. Each warning finding and limitation has its own JSON
Pointer (for example `/issues/0`, `/findings/1`, `/limitations/0`), affected question
IDs, actual evidence references, rationale and explicit boundary of retained use.
All source issues must be covered exactly, with no omitted/invented locators.
Data issues cover every question consuming that input; other problem/rule input
issues conservatively apply case-wide. A semantic issue covers its source question.

The independent review pins the proposal, cites source/frame/proposal evidence,
and returns LIMITED or BLOCKED. Its actor differs from the proposal author, source
reviewer and producers of the original reviewed work. Both proposal and review
require actual successful role handoffs. Authored JSON and fixture transports do
not authorize continuation. Errors, BLOCKED sources, `repair_required` actions,
uncovered questions, stale hashes and missing evidence remain blocking. The source
report is never rewritten to PASS. Review judgment is a trusted role observation,
not person authentication, provider attestation or a mathematical correctness proof.

Add the corresponding paths to the host-owned workflow plan:

```json
{
  "dispositions": [{
    "source": "framing/deterministic_data_audit.json",
    "proposal": "framing/data-disposition.json",
    "review": "reviews/data-disposition.json"
  }]
}
```

This is an optional fragment, not a complete plan or preapproved fixture. Use the
existing agent schedule to produce the actual artifacts: `data_auditor` may propose
`issue_disposition` under `framing/`, `code` under `models/`, and `reviewer` may
produce `disposition_review` under `reviews/`. Data disposition tasks use null
question scope; semantic disposition tasks use the source question ID. Supply the
original input manifest, actual source, frame and relevant evidence to the proposal
author; supply these and the proposal to the independent reviewer. Question-scoped
review tasks also require the current framed DAG. Later modeling tasks must receive
the data source, proposal, approval and all cited evidence in their input bundle.
The generated independent validator task receives data restrictions while its
existing solver-source/intermediate exclusion remains enforced. A schedule and
explicit bindings are required; automatic proposal generation and repair scheduling
remain additional T08 work. Existing unfavorable reviews are not repeatedly queried
for a more favorable verdict.

```powershell
python -m mathmode verify-disposition --workspace ../competitions/case-id --source framing/deterministic_data_audit.json --proposal framing/data-disposition.json --review reviews/data-disposition.json
```

Approved limits produce `LIMITED` phase gates, including downstream model/validation
and freeze gates, and preserve their exact source/proposal/review pins in the report.
LIMITED allows the next bounded numerical transition; it never establishes final
official/paper acceptance. G7/G8 still await T09. CLI exit zero remains reserved for
PASS: an approved `verify-disposition` returns LIMITED with exit one. Likewise,
`freeze` and `verify-freeze` expose LIMITED and the restrictions when present; inspect
the structured status/scope instead of treating every nonzero result as corruption.

Workflow freezing supplies optional `qualification_sources`. The freeze service
independently rechecks those pins, source coverage and actual provenance, derives
the retained restrictions and rechecks under the publication lock. It also inherits
restrictions from the actual upstream freezes of both main and baseline runs.
`frozen_numbers.qualifications` records confidence `limited`, direct sources,
inherited freeze pins and the original issue/boundary text. Registry dependencies
bind all supporting evidence. Review/evidence changes invalidate the snapshot and
its downstream consumers. A bare numerical freeze cannot satisfy a workflow that
requires these qualifications; explicit thaw, fresh executions/validation and
refreeze are required. The lower-level numerical freeze API still establishes
numerical integrity only, not complete semantic or scientific acceptance.

This mechanism accounts for retained limitations; it does not implement data
cleaning or turn missing essential values into valid numerical inputs. Actual
repair/preprocessing and additional input-perturbation adapters remain required work.

## Assumption sensitivity execution

G5 additionally checks every assumption used by the selected production method
(main or fallback) and usable baseline. A ledger's accepted/tested fields alone
cannot meet this gate. An independent `reviewer` produces an `assumption_plan`
under `reviews/`, consuming the actual accepted ledger and both production specs
in its hashed input bundle. The planner must differ from both solver authors.
Set the question's `assumption_plan` path in the host workflow plan. Its assumption
IDs must exactly cover the selected methods; rejected assumptions belonging only
to an unselected candidate do not become evidence obligations for the fallback.

The plan either assigns named sensitivity scenarios or gives a specific rationale
for NOT_APPLICABLE. Each scenario changes one existing numeric parameter or the
random seed of the main production model and declares a maximum absolute change
for independently checked metrics and units. Original inputs, split, constraints,
criteria, implementation and the baseline remain unchanged. Up to twenty distinct
perturbations are permitted per plan. This supports numerical parameter/seed
sensitivity; it does not claim input-noise, missingness or arbitrary structural
alternative-model coverage. Those require additional reviewed experiment adapters.

```powershell
python -m mathmode assess-assumptions --workspace ../competitions/case-id --plan reviews/assumptions.json --interpreter <python-path>
python -m mathmode verify-assumptions --workspace ../competitions/case-id --assessment assessments/<plan-id>/assumption_report.json
```

The service creates derived study specs under `assessments/<plan-id>/`, adding the
plan hash as a pre-execution sidecar. It executes a control, a fixed usable baseline
and the actual perturbed production models with the normal runner. Each production
output is independently validated without the solver source/intermediates. Reported
changes come from those verified numerical summaries. A failing independent check
or an excessive change yields FAIL and cannot enter a frozen assumption claim.
NOT_APPLICABLE reports contain no fake trials and remain a separately identified
independent judgment, subject to the later semantic validation of applicability.

Resume reuses verified runs, validation summaries and completed reports. It does
not silently rerun failed/stale work or relax thresholds. Model/ledger/plan changes
invalidate the current assessment. `Workflow.advance` calls the same service while
holding its workflow lock, and pauses for a missing/invalid independent plan. The
generated semantic-validator task receives the plan and report; its final review
must cite both. Frozen snapshots bind `assumption_reports`, and subsequent report
or upstream evidence changes make the snapshot and its dependent artifacts stale.
All scenarios reuse the actual control baseline run. A report can bind a freeze
only when its production-model pins match both of that freeze's actual source
specs, not merely the question ID.
These checks establish the declared experiment's evidence, not the scientific truth
of the assumption or final official compliance.

The service records each validation request before dispatch. A completed numerical
summary can be adopted after interruption; a previous request without a completed
summary requires diagnosis/explicit repair, instead of launching another validator
under a fresh ID. A report written before registry publication is independently
recomputed before its interrupted registration can resume. Neither case invents
an execution result for an unobserved process.


### Reviewed repair execution checkpoint

`run-code-repair --workspace <root> --request repairs/<id>/request.json
--interpreter <python>` now executes an independently reviewed candidate with its
actual request/review/candidate hashes, execution role and failed predecessor.
A workflow lock serializes service calls. A matching terminal retry is verified
and returned on resume, including FAIL; it is never silently rerun. An intervening
unrelated execution or interrupted reservation blocks implicit retry. The runner
retains the three-attempt budget and requires actual changed code/spec.

Run verification compares authorization with the hashed pre-execution planned
record and, when checking current sources, revalidates the actual repair review.
Candidate path, role and predecessor must match the repair itself. Older manifests
without authorization remain readable; absence does not establish repair review.
An ordinary run cannot gain authorization by changing only its manifest.

This command executes a candidate; it does not switch the effective workflow
model, reuse old numerical validation, reassess assumptions or freeze results.
Those workflow activation and evidence transitions remain pending. Its PASS only
reports process/output-contract success, with scientific_acceptance=NOT_RUN.
Adoption is an explicit subsequent checkpoint:
`activate-repair --workspace <root> --request repairs/<id>/request.json --run runs/<run-id>/run_manifest.json`.
It writes a `repair_activation` event binding the request, independent review,
candidate spec, successful run and failed predecessor by SHA-256. The event is
idempotent and never overwrites the original model. Consumers must treat it as
a new lineage, invalidate prior evidence, rerun main and baseline as a pair,
and independently validate before freezing again.
