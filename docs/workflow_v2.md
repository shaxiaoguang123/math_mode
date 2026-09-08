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

Gate observations: `NOT_RUN`, `PASS`, `WARN`, `FAIL`, `BLOCKED`. PASS requires all
applicable checks completed without blocker or unresolved warning. Nonapplicable
checks carry a concrete reason; they are not silently marked passed. Human review
required by actual policy remains pending until the reviewer event arrives.

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

Each attempt records class, normalized root cause, changed artifacts, observation
and repair owner. At most three retries for the same unresolved cause; the budget
persists across resume. A new traceback spelling or run ID does not reset it.
After exhaustion, return upstream or report an actionable blocker. Every actual
retry uses a fresh output directory and preserves failed evidence.

## Profiles, reference blindness and disclosure

`autopilot` lets a real reasoning agent decide with `decided_by=agent`.
`human_gate` requires the user's actual response. Both obey the same evidence
gates. `lean` stores core contracts and compact success logs; `submission` adds
full validation, freeze, paper package and final audit. Profiles change reporting
density, not scientific correctness.

`blind_reference_mode` is explicit for independent evaluation: frame/model/code/
results/paper baseline first, freeze all baseline hashes, then record and permit
same-problem reference access. Never infer past blindness from a hardcoded boolean.
General algorithm references remain permitted and logged. AI use events record
actual provider/model/activity/artifact scope and any real human postprocessing;
disclosure is derived from events and the verified policy.

## Engineering completion

T02 **PASS** establishes this state machine, ownership boundaries, contract
catalog, stale graph and implementation sequence before runtime code. Later stage
reports must link actual tests and artifacts. The release must complete T03–T12;
these design documents alone cannot establish MathMode V2 READY.
