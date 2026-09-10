# T01 — Pinned reference source map

Read on 2026-09-08 from shallow clones outside this repository. Links below pin
the inspected revision, not a moving default branch. This is source inspection;
upstream benchmarks and LLM workflows were not run. No third-party implementation
or HMML corpus is copied into MathMode. Recommendations are independent designs.

| Project | Revision | Root LICENSE inspected | Boundary |
| --- | --- | --- | --- |
| usail-hkust/LLM-MM-Agent | `c593c794131a7343c6d9ed379220969322b91e64` | GPL-3.0 text | Architecture study only |
| yushui2022/MathModel-Skill | `0cc261d90d21e4ed540b02b0c71018cdcd47af58` | MIT | Study; no copied code |
| Hjdd14/math-modeling | `9f5239414a7a93b5f71dee0a0d626f7d0c828e11` | MIT | Study; no copied code |
| zhnnky329/MathModeling-skills | `046a6e74814c2e5fef72b5ee56305509a8635e1d` | MIT, also plugin LICENSE | Contracts are largely prompt-level |
| SatakaGintoki/MathSkill | `d274047383147b8a6a22a9ab9a99dd38c4e4af3e` | No LICENSE found in tracked tree | No grant inferred; study only |
| usail-hkust/dslighting | `d38eb7d90d98841d1f15aca1d40ac01c22eca9c1` | AGPL-3.0 text | Architecture study only; no dependency |

## Mechanism-to-source map / borrow–reject matrix

Paths grouped in a row were inspected for the stated mechanism. Large files were
reviewed through relevant functions and call sites; this does not claim exhaustive
review of every upstream file or correctness of all upstream implementations.

| Source and actual implementation | Borrow | Reject / observed limit | MathMode design |
| --- | --- | --- | --- |
| [MM-Agent coordinator](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/agent/coordinator.py), `compute_dag_order`, `analyze_dependencies` | Subquestion dependency order and cycle rejection | Parse failure silently substitutes a fully sequential graph; unknown dependency is reported as cycle | Explicit DAG schema; reject unknown IDs separately; never invent dependencies |
| [problem analysis](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/agent/problem_analysis.py), [decomposition](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/agent/problem_decompse.py) | Actor → critic → revised formulation before code | Repeated LLM prose is not evidence or independent approval; decomposition falls back to type C/four tasks | Structured frame, ambiguity ledger and bounded critic handoff |
| [method retrieval](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/agent/retrieve_method.py), `HMML/HMML.md`, `HMML.json`, `prompt/template.py`, `prompt/decompose_prompt.json` | Hierarchical method search, applicability discussion | Weighted retrieval/LLM scores do not prove model suitability; retriever rewrites HMML JSON | Small independent method cards with source, assumptions, rejected alternatives and executed probes |
| [task solver](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/agent/task_solving.py), `execute_script`, `coding` | Execute generated code and repair from observations | `shell=True`, ambient `python`, no execution timeout, success inferred from absence of three error strings, nested retry budgets | Explicit interpreter/argv, return code, timeout, hashes, at most three repairs for one cause |
| [computational solving](https://github.com/usail-hkust/LLM-MM-Agent/blob/c593c794131a7343c6d9ed379220969322b91e64/MMAgent/utils/computational_solving.py), `MMAgent/main.py` | Persist task result and dependencies | `is_pass` is stored but does not stop result interpretation; positional execution result lands in `user_prompt` parameter of `TaskSolver.result` | Failed runs cannot reach validation/freeze/writer |
| [MathModel-Skill workflow guard](https://github.com/yushui2022/MathModel-Skill/blob/0cc261d90d21e4ed540b02b0c71018cdcd47af58/packages/codex/.agents/skills/paper-workflow-orchestrator/scripts/workflow_guard.py), `check_s0`–`check_s6`, `evaluate`; adjacent `preflight_check.py` | Frozen file roles/sizes/hashes and executable entry guards | Some early stages check existence/JSON readability only; PDF preflight samples pages | Complete input extraction plus schema and cross-contract checks |
| [evidence gate](https://github.com/yushui2022/MathModel-Skill/blob/0cc261d90d21e4ed540b02b0c71018cdcd47af58/packages/codex/.agents/skills/quality-assurance-auditor/scripts/evidence_gate.py), `run_manifest_failures`, `metric_value_failures`, `indexed_artifact_failures` | Rehash code/input/output, reject empty/nonfinite metrics and declared placeholders | Metadata alone is not independent recomputation; numeric strings/types need stricter validation | Deterministic scientific evaluator followed by provenance gate |
| [result contracts](https://github.com/yushui2022/MathModel-Skill/blob/0cc261d90d21e4ed540b02b0c71018cdcd47af58/packages/codex/.agents/skills/model-code-and-result-generator/scripts/build_result_contracts.py); [example runner](https://github.com/yushui2022/MathModel-Skill/blob/0cc261d90d21e4ed540b02b0c71018cdcd47af58/examples/cumcm2024-b-demo/paper_output/code/modeling/run_modeling.py) | Draft contracts explicitly distinguish missing real modeling | `run_modeling.py` is generated workspace/example output, not a reusable script at the requested skill path; this example runner emits no full hashed manifest | MathMode owns one reusable execution backend and manifest producer |
| [workflow memory](https://github.com/yushui2022/MathModel-Skill/blob/0cc261d90d21e4ed540b02b0c71018cdcd47af58/packages/codex/.agents/skills/context-memory-keeper/scripts/update_workflow_memory.py), `build_snapshot`; `paper-formal-writer/SKILL.md` | Resume from disk and guard writer entry; bounded repair queue | Memory summaries cannot override fresh files; Markdown/Word-first route and character/page floors differ from MathMode | Disk state plus fresh gate recalculation; preserve TeX-first route |
| [Hjdd workflow runner](https://github.com/Hjdd14/math-modeling/blob/9f5239414a7a93b5f71dee0a0d626f7d0c828e11/tools/workflow_runner.py), `state_manager.py`, `pipeline_check.py`, `SKILL.md`, `references/workflow.md` | Explicit distinction between CLI orchestration and reasoning agents; state locking/atomic writes; checker aggregation | File presence may advance resumed phase; age-only lock expiry can remove an active writer's lock | Persist observed gates with dependency hashes, safe locking, no inferred PASS |
| [evidence checker](https://github.com/Hjdd14/math-modeling/blob/9f5239414a7a93b5f71dee0a0d626f7d0c828e11/tools/evidence_checker.py), `data_leakage_checker.py`, `optimization_certificate_checker.py`, `model_spec_checker.py`, `unit_checker.py`, `manifest_checker.py` | Question-specific validation profiles, units, leakage, feasibility and hashes | Many checks inspect supplied declarations; standard mode allows missing evidence with `passed=true`; unit presence is not dimensional algebra | Independent recomputation and explicit PASS/WARN/FAIL/NOT_RUN states |
| [mini benchmark runner](https://github.com/Hjdd14/math-modeling/blob/9f5239414a7a93b5f71dee0a0d626f7d0c828e11/tools/mini_benchmark_runner.py), `_case_payload`, `_solution_code`; `evals/mini_contest_benchmark.json`, `tests/test_evidence_checker.py`, `tests/test_workflow_runner.py`, `.github/workflows/ci.yml` | Disposable fixtures, negative cases, Windows 3.11/3.12 matrix | Runner embeds expected oracle values and prefilled validation booleans into generated scripts: useful contract tests, not evidence of autonomous solving | Real computed positive fixtures; independent expected values hidden from solvers; historical run separately labeled |
| [zhnn method selector](https://github.com/zhnnky329/MathModeling-skills/blob/046a6e74814c2e5fef72b5ee56305509a8635e1d/.codex/skills/method-selector/SKILL.md), `references/risk-probe-contract.md`, root `AGENTS.md` | Main + usable baseline + optional triggered fallback; representative coverage, degeneracy, perturbation and scale probes | Instructions/JSON examples are not an executed probe engine; human-only choice conflicts with requested autopilot | Actual probe runs and recorded thresholds; truthful `decided_by=agent` in autopilot |
| [zhnn orchestrator](https://github.com/zhnnky329/MathModeling-skills/blob/046a6e74814c2e5fef72b5ee56305509a8635e1d/.codex/skills/workflow-orchestrator/SKILL.md), `solution-package-builder/SKILL.md`, `consistency-auditor/SKILL.md`, `quality-assurance-auditor/SKILL.md` | Lean/submission profiles, freeze locators, change impact, downstream stale and scoped review | Prompt policy, no Python stale/freeze runtime found in inspected skill distribution; frozen-number example lacks full run/validator hash chain | Implement immutable snapshot service and transitive dependency invalidation |
| [MathSkill baseline freeze](https://github.com/SatakaGintoki/MathSkill/blob/d274047383147b8a6a22a9ab9a99dd38c4e4af3e/.claude/skills/math-modeling/scripts/freeze_baseline.py), `validate_workspace.py`, `references/quality-gates.md`, `references/paper-evidence-contract.md`, `.claude/agents/reviewer.md`, `model-builder.md` | Refuse overwriting freeze; exclude dependency trees; blind modeling before same-problem references; distinguish automated/manual evidence | `same_problem_reference_content_opened=False` is written, not independently observed; file existence does not prove results; blanket booleans not sufficient | Log actual reference-access events and freeze state; blind mode opt-in for evaluation; block unfrozen evidence |
| [DSLighting backend contract](https://github.com/usail-hkust/dslighting/blob/d38eb7d90d98841d1f15aca1d40ac01c22eca9c1/dslighting/services/sandbox_backends/backends/base.py), `local.py`, `services/sandbox.py` | Backend substitution and explicit execution result/timeout | Local subprocess is not an OS security sandbox; `resource` service is POSIX-dependent | Portable LocalSubprocessBackend with honest capability metadata; no copied AGPL code |
| [DSLighting workflow](https://github.com/usail-hkust/dslighting/blob/d38eb7d90d98841d1f15aca1d40ac01c22eca9c1/dslighting/workflows/base.py), `ops/base.py`, `state/base.py`, `services/workspace.py`, `core/interfaces/__init__.py`, `runner.py`, `runtime/dag/types.py`, `runtime/dag/reducer.py`, `benchmark/evaluators/base.py`, `tests/services/test_sandbox_timeout_override.py` | Separate agent, workflow, operator, service, state, workspace, result and evaluator; node input bindings and attempts | Full dynamic multiworkflow platform is excessive for this repo; managed path joining alone is not confinement | Small typed harness, dependency injection, deterministic gates and isolated validator input bundles |

## Checker coverage supplement

All `tools/*checker.py` in Hjdd14/math-modeling were inventoried and their core
validation predicates inspected. In addition to the deep reads above, this covers
`award_readiness`, `brief_completeness`, `case_retrieval`, `compliance`,
`consistency`, `figure`, `innovation`, `judge_panel`, `mini_benchmark`,
`model_selection`, `robustness`, `schema`, `source_freshness`, `source_registry`,
`statistical_validation`, `uncertainty_budget`, `validation_profile` and
`writer_prompt` checkers. Their patterns are informative but not all transferable:
source-count quotas, blanket confidence/multistart thresholds, keyword matching,
supplied reviewer scores and required artifact counts are not mathematical proofs.
Actual dataframe checks in `schema_checker` and byte-hash checks in
`manifest_checker` are stronger than declarative metadata and should remain
separate from semantic reasoning. This is a targeted source audit, not an upstream
security certification or an assertion that those checks were executed here.

T01 **PASS**: all six sources are pinned, actual mechanisms and limits are mapped,
license boundaries are recorded, and each proposed core runtime mechanism has a
source-level rationale. MathMode must still implement and test its own contracts.
