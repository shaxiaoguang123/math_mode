# Reference architecture comparison

See [pinned source map](reference_source_map.md) for code links and licenses.
`Present` below refers to inspected implementation, not independently verified
modeling performance. Prompt contracts and runtime code are distinguished.

| Project | Reasoning / coordination | Execution / evaluation | Freeze / recovery | Best use here |
| --- | --- | --- | --- | --- |
| LLM-MM-Agent | Actual LLM actor/critic and DAG coordination | Actual code generation/execution; weak success detection | In-memory dependencies and saved solution; no inspected frozen-number gate | Bounded reasoning/critique stages and dependency modeling |
| MathModel-Skill | Skill routing with actual workflow guard | Hash-aware provenance/evidence checkers; generated runner | Workflow memory from disk | Input roles, fresh guard, result contracts |
| Hjdd14/math-modeling | Five-view reasoning prompts plus explicit deterministic CLI | Many actual checkers and code runner; some supplied-status checks | Atomic state writes and resume | Negative fixtures, validation taxonomy and Windows CI |
| MathModeling-skills | Compact method-selection and human-decision prompt policy | Probe schemas/instructions; execution delegated to agents | Prompt-defined freeze/change-impact/lean workflow | Main/baseline roles and machine-checkable fallback design |
| MathSkill | Agent definitions plus structural validator | Syntax, artifact and paper evidence checks; manual science gates | Actual blind freeze hashes; refusal to overwrite | Reference blindness and immutable snapshots |
| DSLighting | Full agent/workflow/operator/service platform and DAG types | Swappable local/remote backends and evaluator interfaces | State abstractions and per-run workspaces | Minimal backend/harness boundary, independently implemented |

## Decisions before implementation

1. Keep the current figure assets, Chinese font QA, TikZ conventions, LaTeX source
   and optional DOCX derivative. No upstream paper route replaces these assets.
2. Build one small Python package for shared schema/path/hash/state/gate services.
   Standalone V1 command paths remain adapters. Do not reproduce a whole platform.
3. Separate mathematical reasoning from deterministic checks. A configured host
   agent produces structured proposals; validators recompute metrics from original
   inputs and final outputs. The CLI must not pretend fixed templates are reasoning.
4. Hashes prove artifact consistency under the local trust model. They do not
   authenticate a malicious user with full disk access or prove model correctness.
   Runner-issued records, independent recomputation and fresh gate checks are all
   needed. Local subprocess does not enforce filesystem/network isolation.
5. Only one usable baseline and one main method are required; one fallback can
   activate on a recorded threshold. Extra diagnostic references remain optional.
6. Freeze stores values, units, locators, model/run/validator hashes and claim IDs.
   Changes invalidate every dependent result, figure, paper and package. A new
   snapshot follows thaw, rerun and revalidation; the old record remains auditable.
7. Autopilot records agent decisions honestly. Human mode waits for actual user
   input. Neither mode permits an actor to approve its own scientific evidence.
8. Structural fixture tests, computed numerical benchmarks and historical contest
   dry runs have different evidentiary scopes. In particular, oracle replay into
   generated output cannot demonstrate independent modeling performance.

## Scope limits

No upstream LLM API was invoked, no benchmark leaderboard was reproduced, and
no same-problem excellent paper has been used for the forthcoming historical
modeling run. Reading generic engineering code is not reading that problem's
solution. Root/template license provenance and current official contest rules
remain separate checks. GPL/AGPL and unlicensed reference code must not be copied
into the runtime; do not infer a license from repository visibility.
