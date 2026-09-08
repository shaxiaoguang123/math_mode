# MathModel Agent Research

## 1. 本轮研究主题

**Problem Specification / Constraint Compiler：把华为杯题面、附件说明和提交规则从自然语言清单编译成机器可执行的 `Problem Contract + Proof Obligations`。**

本轮关注一个比“选什么模型”更靠前、也更容易造成全链路错误的问题：

> Solver、Reviewer、Visualizer、Writer 如何确保理解的是**同一份题面事实**，并且每一个硬约束、单位、目标方向、边界、输出格式、数据切分和资源限制都能被机器追踪、验证和版本化，而不是依赖多个 Agent 各自重新阅读题面并形成略有差异的自然语言理解？

当前 `math_mode` 已经要求生成 `求解/题面约束清单.md`，并明确记录每问输入、输出、依赖、方法限制、指标、单位、边界、精度、时间/CPU/GPU、训练测试隔离、官方答案结构和 AI 要求；这是一套很强的人类可读规则。但仓库中尚未发现与之对应的统一机器可读 `Problem Contract`、schema、constraint ID、source span、proof obligation 或 contract hash。

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的对象：

1. `GuangruiXieVT/ORPilot`：自然语言业务问题 → ProblemDefinition → solver-agnostic IR → deterministic compiler；
2. `TonyQJH/cca-emnlp2026`：rule-dense context → typed IR → executable verifier → violation-gated correction；
3. `teshnizi/OptiMUS`：参数 → 目标 → 约束 → 数学形式 → 代码 → 执行/调试的分阶段优化建模工作流。

本轮核心结论：

> `math_mode` 应保留现有 `题面约束清单.md` 作为人类可读视图，但新增一个更上游的、不可变、带来源定位和版本哈希的 `题面契约.json`。所有 Solver / Model Search / Reviewer / Writer 都只消费同一个 `contract_id + contract_hash`；再由 `Proof Obligation Compiler` 把硬约束编译成可执行检查，避免“读题正确性”只存在于 Prompt 中。

建议目标结构：

```text
题目 PDF / Word / 附件说明 / 官方输出模板 / 用户明确补充
                         ↓
                 Source Parser
 source_path + page/section/span + quote_hash + authority
                         ↓
              Specification Compiler
                  求解/题面契约.json
 inputs / outputs / objectives / constraints / units / tolerance
 method restrictions / data split / resource limits / output schema
                         ↓
                Contract Auditor
 schema + conflict + completeness + dependency + source-fidelity
                         ↓
             Proof Obligation Compiler
 unit/range/schema/conservation/split/objective/output/dependency checks
                         ↓
 Solver / Model Search / Reviewer / Figure / Writer
        全部绑定同一个 contract_hash
```

---

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

`research/INDEX.md` 目前已覆盖：

- 14:00：科研型 Agent 与 evidence-first；
- 15:06：模型候选树、并行实验、可执行评测；
- 16:04：Reviewer / Judge 与校准；
- 17:07：Checkpoint / Resume；
- 18:04：Artifact Ownership / stale-write / promotion；
- 19:07：Resource Scheduler / pruning；
- 20:08：Citation / External Evidence Provenance。

这些研究都默认存在一个前提：**系统已经正确理解题面。**

本轮不重复 Reviewer、provenance 或 checkpoint，而研究它们共同依赖的上游事实层：

```text
题面原文到底说了什么？
↓
哪些是硬约束，哪些是允许假设？
↓
约束适用于哪一问、哪一种数据、哪个输出？
↓
单位、精度、上下界和目标方向是什么？
↓
哪个原文 span 是该约束的权威来源？
↓
如何把它变成可执行 proof obligation？
```

20:08 报告已经把“Problem Specification / Constraint Compiler”列为下一轮推荐方向，因此本轮属于有计划的主题轮换。

### 2.2 当前 math_mode 已有能力

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、当前求解规范和历史 research 后，当前项目已有：

- 清晰的规则优先级：用户当前要求 > 赛题正文 > 官方附件/模板/公式/提交要求 > 项目规范 > 工具/schema > Agent router；
- Phase 1 强制完整读题，并生成 `求解/题面约束清单.md`；
- 每问显式记录输入、输出、依赖、单位、边界、方法限制、指标、精度、CPU/GPU/时间、训练测试隔离、官方输出格式和 AI 要求；
- 原始题目、原始数据与官方模板只读；
- 固定事实链：题目/数据 → 代码 → 结构化结果 → 独立验证 → 结果索引 → 论文；
- 视觉计划、支撑材料、结果索引已经存在机器审计和哈希机制。

因此，本轮不是建议推倒重来，而是补一层当前最明显的结构缺口：**题面清单有 Markdown，但没有可共享、可执行、可版本化的 contract。**

### 2.3 为什么这是 P0 而不是“以后再优化”

如果题面解释错一条硬约束，下游再强的模型搜索、Reviewer、图表 QA 和论文审计都可能围绕错误目标工作。例如：

- 最大化被误读成最小化；
- “不超过”被实现成“至少”；
- mm 被当成 m；
- 测试集被用于模型选择；
- 官方要求保留 4 位小数，代码输出了整数；
- 官方 Excel 指定列名/顺序被 Writer 或代码擅自修改；
- Q2 依赖 Q1 的输出版本，但多个 Agent 使用不同 Q1 candidate；
- 一个附件规则覆盖题面一般描述，但 Solver 只重新读了正文。

这些属于**specification failure**，不是普通代码 bug。

---

## 3. 搜索范围与关键词

本轮属于 P0/P1 交叉方向：数学优化 Agent、formalized problem specification、constraint extraction、context compiler、executable verifier。

重点关键词：

- natural language to optimization IR
- operations research LLM intermediate representation
- constraint extraction optimization agent
- typed context IR executable verifier
- problem specification compiler LLM
- source-grounded constraint extraction
- proof obligation generation
- deterministic semantic validation optimization IR
- constraint completeness verification
- mathematical model formulation agent
- solver-agnostic optimization IR

筛选原则：

- 不研究普通 prompt-to-code demo；
- 必须存在结构化中间层、约束/目标拆解、代码执行或验证机制；
- 优先阅读真实源码，而不是只引用 README 的架构图。

本轮实际读取了三个仓库的 README、核心 schema、workflow / compiler / validation / execution 源码，并固定当前主分支 commit 用于可追溯性。

---

## 4. 新发现项目

### 项目 1：ORPilot

- 名称：ORPilot — AI Operations Research Modeling Agent
- Repository：https://github.com/GuangruiXieVT/ORPilot
- 本轮固定读取 commit：`d153a680aaecd3f90e8466f77259bd8275bd6216`
- Stars：16（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-08-26T21:17:42Z`；`pushed_at=2026-06-10T20:09:29Z`
- 目标：把不完整、真实业务描述转化为可运行的数学优化模型。
- 核心能力：interview agent、数据需求定义、参数计算、ProblemDefinition、solver-agnostic IR、IR semantic validation、deterministic compiler、多 solver backend、运行错误回修、session resume。
- 本轮实际阅读：
  - `README.md`
  - `orpilot/models/problem.py`
  - `orpilot/models/ir.py`
  - `orpilot/workflow/nodes/ir_builder.py`
  - `orpilot/codegen/ir_validator.py`
  - `orpilot/workflow/nodes/ir_compiler_node.py`

最重要价值：**LLM 负责把自然语言变成 typed IR，但“IR 是否结构合法、部分语义是否合理、怎样转成 solver code”尽量交给确定性代码。**

### 项目 2：CCA — Context Compilation Architecture

- 名称：Compile, Don't Memorize: A Context Compilation Architecture
- Repository：https://github.com/TonyQJH/cca-emnlp2026
- 本轮固定读取 commit：`a8230f94c957c60fb8be808742398612a2da6699`
- Stars：0（仓库 2026-09-01 新建，本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-03T14:58:56Z`；`pushed_at=2026-09-03T14:58:17Z`
- 论文：arXiv:2609.00759；EMNLP 2026 Findings
- 目标：把长、规则密集的上下文先“编译”为 typed IR，而不是要求模型每次从原始长上下文重新记住所有规则。
- 核心能力：`must_do / must_not / conditional`、`source` quote、`codeable`、`code_hint`、`output_spec`、`available_tools`、`data_profile`、Python verifier、violation-gated correction、resume、可复现实验记录。
- 本轮实际阅读：
  - `README.md`
  - `code/cca_core.py`
  - 仓库实验/执行结构

最重要价值：**规则不应只存在于 prompt；应编译成有 ID、有来源、有可执行性标记的固定槽位。**

### 项目 3：OptiMUS

- 名称：OptiMUS — Optimization Modeling Using MIP Solvers and Large Language Models
- Repository：https://github.com/teshnizi/OptiMUS
- 本轮固定读取 commit：`59e8d99653459b40361f618eafdc91eee3a85ebb`
- Stars：293（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-07T13:05:02Z`；`pushed_at=2025-11-04T17:10:14Z`
- 目标：从自然语言优化问题中分阶段抽取并形式化参数、目标、约束和变量，再生成/执行 MIP solver code。
- 核心能力：参数抽取、目标抽取、约束抽取、约束/目标数学化、代码生成、分阶段 state 保存、执行与 LLM debug、RAG 变体。
- 本轮实际阅读：
  - `main.py`
  - `parameters.py`
  - `constraint.py`
  - `execute_code.py`

最重要价值：**先做语义拆解，再形式化，再写代码；不要把“读题 + 建模 + 编码”塞进一次大模型调用。**

---

## 5. 深入架构分析

### 5.1 ORPilot：两级结构化比直接 Prompt-to-Code 更可靠

ORPilot 先构造相对粗粒度 `ProblemDefinition`：

```text
title
description
problem_type
objective + objective_description
constraints[]
decision_variables[]
additional_notes
csv_file_paths
```

之后再生成严格的 `IRModel`：

```text
problem_class
model_type
sense
sets{}
parameters{}
variables{}
constraints{}
objective
```

IR 不是自然语言摘要，而是可以被 deterministic compiler 消费的模型结构。例如 `IRVariable` 明确记录 domain/type/bounds；`IRConstraint` 记录 domain/expression tree/sense/rhs；时间集合还能声明 `ordered` 以支持 lag。

这个两级模式很适合 `math_mode`：

```text
题面原文
↓
Problem Contract（赛事/题面语义层）
↓
Model IR（某一路线的数学模型层）
↓
Code
```

关键是不要把“题面合同”和“模型实现 IR”混为一个对象。一个题面可能允许多个模型路线，但**所有路线必须服从同一个 Problem Contract**。

### 5.2 ORPilot：schema valid 不等于 model valid

`ir_builder.py` 不接受 LLM 直接输出任意 JSON 后就继续，而是通过 `submit_ir` 工具进入：

1. Pydantic schema validation；
2. `validate_ir_semantics()`；
3. CSV member / hardcoded index 检查；
4. 若失败，把精确错误反馈给 LLM，仅修复失败部分；
5. 最多多轮重试。

其 semantic validator 进一步检查：

- inventory balance 流入/流出符号错误；
- lag 约束缺少初始化约束；
- ordered time set 使用错误硬编码 size；
- RHS 顶层裸 variable；
- variable × variable 导致非线性；
- objective 中错误 lag；
- domain alias 误用；
- 共享 CSV source 未正确区分 set 等。

对 `math_mode` 的启发不是照搬这些 supply-chain heuristics，而是：

> **每一种 contract predicate 都应该对应可执行的 semantic checker；机器检查应证明“约束真的被满足”，而不是只证明 JSON 能解析。**

### 5.3 ORPilot：IR → solver code 的边界应尽量 deterministic

`ir_compiler_node.py` 调用 `IRCompiler().compile(ir_model, solver)`。IR 一旦通过，编译器负责生成目标 solver 代码；失败时才把 traceback 放入 `error_context` 并路由回 IR builder。

这形成一个清楚的 trust boundary：

```text
LLM：理解/提出结构
Deterministic code：校验/编译/运行
```

`math_mode` 可迁移成：

```text
LLM：从题面提出 contract candidate
Deterministic code：schema + source + units + output schema + contradiction audit
LLM/Agent：解决无法代码化的歧义
Deterministic code：把 hard constraints 编译为 proof obligations
```

### 5.4 CCA：规则密集上下文最怕“每个 Agent 各读一遍”

CCA 的 Compiler 不是普通摘要器，而是固定输出：

```json
{
  "rules": {
    "must_do": [],
    "must_not": [],
    "conditional": []
  },
  "knowledge": {},
  "data_profile": {},
  "workflow": {},
  "output_spec": {},
  "available_tools": []
}
```

每条 rule 还包含：

```text
id
rule
source（原文 quote）
codeable
code_hint
```

这与华为杯高度相关。一个赛题的硬规则并不只有数学公式，还可能包括：

- “结果保留四位小数”；
- “不得使用某类外部数据”；
- “必须给出某附件”；
- “输出文件名固定为 result.xlsx”；
- “第 3 问使用第 2 问给定情形”；
- “预测期不能使用未来数据”；
- “总运行时间不得超过某阈值”。

如果这些仍只存在于 Markdown，Solver、Reviewer 和 Writer 都可能漏掉不同的部分。

### 5.5 CCA：从规则自动生成 verifier

CCA 的 CodeGen 只对 `codeable=true` 的 rule 生成 Python checker，并特别强调减少 false positive；无法可靠代码化的规则要跳过而不是硬判。

这一点应直接迁移为 `math_mode` 的两类 proof obligation：

```text
Deterministic obligation
- 单位
- 数值范围
- 文件名
- Sheet/列顺序
- 行数/shape
- 小数位
- 时间范围
- train/test split
- 守恒/恒等式

Semantic obligation
- 模型假设是否合理
- 机理是否解释充分
- 创新性是否成立
- 某段论证是否真正回答题意
```

前者必须机器执行；后者交给 Reviewer，但 Reviewer 也必须引用 contract criterion ID。

### 5.6 OptiMUS：语义分解是一种实用防错手段

OptiMUS 的 `main.py` 顺序保存：

```text
state_1_params.json
state_2_objective.json
state_3_constraints.json
state_4_constraints_modeled.json
state_5_objective_modeled.json
state_6_code.json
```

这说明优化建模不应“一步生成完整程序”。参数、目标、约束、数学形式和代码属于不同错误类型，分开处理更易审计、debug 和回退。

`parameters.py` 会单独判断某个 quantity 是否真的是“已知参数”；`constraint.py` 单独抽取约束，并设计 keep/remove/modify 的复核流程。

但它主要依赖 LLM confidence，因此更适合作为设计参考，而不是直接作为华为杯 hard gate。

---

## 6. Agent / Skill 设计

### 6.1 推荐新增的职责层，而不是再加一个“大 Prompt”

建议未来形成四个职责概念：

```text
problem-contract-compiler
    ↓
problem-contract-auditor
    ↓
proof-obligation-compiler
    ↓
contract-aware solver / reviewer / writer
```

这里“建议”仅是设计，不在本轮创建正式 Agent/Skill。

### 6.2 `problem-contract-compiler`

输入：

- 题面正文；
- 附件说明；
- 官方模板；
- 用户明确补充；
- 当前赛事规范。

输出：`求解/题面契约.json` candidate。

每条 constraint 建议至少包含：

```json
{
  "constraint_id": "Q1-C-007",
  "source_ref": {
    "file": "题目/A题.pdf",
    "page": 3,
    "section": "问题1",
    "span": "...",
    "quote_hash": "sha256:..."
  },
  "authority": "problem_body",
  "scope": ["Q1"],
  "kind": "hard",
  "target": "solution",
  "predicate_type": "inequality",
  "normalized_predicate": "x <= 100",
  "units": {"x": "MPa"},
  "tolerance": null,
  "codeable": true,
  "checker_type": "numeric_predicate",
  "proof_obligation_ids": ["PO-Q1-007"],
  "status": "parsed"
}
```

### 6.3 `problem-contract-auditor`

职责不是“再读一遍总结”，而是执行：

- schema completeness；
- source span/hash 存在性；
- authority precedence；
- 重复/冲突约束；
- objective direction 一致性；
- unit compatibility；
- output schema 完整性；
- question dependency DAG；
- ambiguous/unresolved hard rules；
- contract hash 计算。

任何 hard conflict 不应被 LLM 静默猜测。

### 6.4 `proof-obligation-compiler`

把 contract 中可以代码化的 hard constraints 编译为：

```text
PO-Q1-001 unit_check
PO-Q1-002 range_check
PO-Q1-003 objective_direction_check
PO-Q1-004 official_output_schema_check
PO-Q1-005 train_test_leakage_check
PO-Q1-006 conservation_check
PO-Q1-007 precision_check
```

每个结果 artifact 必须携带：

```text
contract_hash
proof_obligation_report_hash
```

否则不得进入 18:04 报告提出的 canonical promotion。

---

## 7. Workflow

推荐未来的比赛主链调整为：

```text
Phase 1A 题面/附件原文冻结
↓
Phase 1B Source Span Index
↓
Phase 1C Problem Contract candidate
↓
Contract audit
├─ CONFLICT / AMBIGUOUS → 证据回读 / 明确记录阻塞
└─ PASS
↓
Proof Obligations
↓
现有 求解/题面约束清单.md（由 contract 生成/同步的人类视图）
↓
Phase 2 求解计划 / Model Search
↓
Candidate execution
↓
Reviewer + deterministic obligations
↓
Canonical promotion
↓
Figure / Writer
```

与历史调研衔接：

- 15:06 Model Search：所有 candidate 必须引用同一个 `contract_hash`；
- 16:04 Reviewer：rubric criterion 可直接引用 `constraint_id / proof_obligation_id`；
- 17:07 Checkpoint：checkpoint 保存 `contract_hash`；
- 18:04 Candidate Promotion：contract 变更后旧 candidate → STALE；
- 19:07 Scheduler：resource limit 直接来自 contract；
- 20:08 External Evidence：如果题面外引入参数，来源证据进入 External Evidence Ledger，但不能反向篡改题面 hard constraints。

---

## 8. Code Execution / Tools

### ORPilot

是真实 code execution 系统，不只是文本生成：

- 生成 IR；
- Pydantic 验证；
- semantic validator；
- deterministic IR compiler；
- 输出 PuLP / Pyomo / OR-Tools / Gurobi / CPLEX；
- 运行 solver；
- 用 traceback / infeasibility feedback 做定向修复；
- 可从已有 working code 反向生成 solver-agnostic IR。

这说明 typed contract/IR 不是文档格式，而应当成为实际执行接口。

### CCA

真实生成并执行 Python verifier，包括：

- `rule_checker`
- `format_validator`
- `data_analyzer`

并把 verifier violations 反馈给第二阶段 Reasoner。它证明“从自然语言规则生成可执行检查器”在工程上是可行方向，但华为杯需要更严格地限制自动生成 checker 的权限，并对 checker 自身做 16:04 报告提出的 regression/JudgeEval。

### OptiMUS

实际生成 Python solver code，通过 subprocess 执行；执行失败后把 error + code + problem description 反馈给 LLM，最多多轮 debug。

需要强调：

> `process exit == 0` 只能证明程序执行成功，不能证明数学模型正确。

因此 `math_mode` 的 proof obligation 必须覆盖“能运行”之上的题意正确性。

---

## 9. QA / Reviewer / Verification

### 9.1 三项目的验证层次不同

| 项目 | 结构验证 | 语义验证 | 真实执行 | 约束来源定位 | verifier 校准 |
|---|---|---|---|---|---|
| ORPilot | 强：Pydantic IR | 中-强：若干 deterministic semantic checks | 是 | ProblemDefinition/IR 不强调 page/span | 有 benchmark，但本轮未见通用 JudgeEval |
| CCA | 强：typed IR | 针对规则 adherence | verifier Python execution | `source` quote | 有 CL-bench 全量实验，但 checker 仍需特定任务适配 |
| OptiMUS | 分阶段 JSON/state | 主要 LLM confidence/reflection | 是 | 不强 | 较弱 |

### 9.2 对 math_mode 的关键要求

`Problem Contract` 本身也必须 QA：

1. **Source fidelity**：每个 hard constraint 是否有可回读的 source span；
2. **Completeness**：是否覆盖官方输出、单位、精度、资源和依赖，不只覆盖数学公式；
3. **Conflict resolution**：冲突时是否按现有权威顺序处理；
4. **No silent assumption**：题面没有给出的条件不能伪装成 hard constraint；
5. **Executable coverage**：能代码化的 hard rule 是否都有 proof obligation；
6. **Semantic backlog**：不能代码化的 rule 是否进入 Reviewer checklist，而不是消失；
7. **Contract mutation invalidation**：contract 变化是否令旧结果 STALE。

### 9.3 Proof Obligation 不能完全由 LLM 自己判

例如：

- 单位是否匹配 → Pint/SymPy/自建 unit table；
- CSV/Excel schema → deterministic parser；
- 数值范围/等式 → Python/SymPy；
- 线性约束结构 → expression AST；
- 数据泄漏 → split manifest + row/time IDs；
- 文件命名/目录 → filesystem checker；
- 精度/小数位 → exact formatter check；
- 模型合理性 → Reviewer，带 `criterion_id`。

这与 16:04 的结论一致：hard fact check 与 soft meta-review 应分离。

---

## 10. 值得借鉴的设计

### A. 可以直接借鉴

**A1 — CCA 的固定 typed slot + rule ID + source quote + codeable/code_hint。**

直接迁移到题面 contract，能解决“规则只藏在 prose 中”的问题。

**A2 — ORPilot 的 LLM extraction + deterministic schema/semantic validation。**

LLM 可以提出结构，但不能自行宣布结构有效。

**A3 — ORPilot 的 deterministic IR compiler 思想。**

对于已经明确的 hard constraints，尽量编译成 checker，而不是每次重新让 LLM解释。

**A4 — OptiMUS 的阶段拆解。**

参数/目标/约束/数学形式/代码分开保存，错误定位比单次生成整段求解代码清楚得多。

### B. 可以改造后采用

**B1 — ORPilot IR 从 LP/MIP 扩展成比赛 Problem Contract。**

不能只包含 sets/variables/linear constraints；还要包含统计任务、预测任务、仿真任务、ODE/PDE、图算法、评价指标、输出 artifact、数据 split 等。

**B2 — CCA verifier 从“检查最终文本”扩展到“检查全过程 artifact”。**

华为杯 checker 的 target 至少包括：data、model code、result、figure、official output、paper claim。

**B3 — OptiMUS 的 confidence check 改为 evidence-based status。**

不使用“LLM 4/5 置信度 = 正确”，而使用 `PARSED / VERIFIED / AMBIGUOUS / CONFLICT / UNRESOLVED`，每个状态附 source evidence。

### C. 可以作为对照实验

**C1 — Markdown checklist vs typed Problem Contract。**

评价：遗漏约束率、错误单位率、错误输出格式率、返工次数、最终 validation failure、token/time。

**C2 — 每个 Agent 直接读全文 vs compile-once contract。**

评价多个 Agent 对同一题面产生的 constraint set Jaccard、一致率和 downstream contradiction。

**C3 — LLM-only Reviewer vs deterministic proof obligations + Reviewer。**

评价 false positive/false negative、正确 candidate survival、错误 candidate promotion。

**C4 — contract mutation tests。**

故意改变一个单位、一个不等号、目标方向、官方列名、测试切分、时间约束，看系统是否能准确 invalidate 下游结果。

### D. 不建议采用

**D1 — CCA compiler 失败时静默退化到 direct prompting。**

比赛 hard constraint 不允许“contract 编译失败但继续猜”。应明确 INVALID/AMBIGUOUS 并阻塞受影响环节。

**D2 — OptiMUS 用 LLM 自报 confidence 作为 constraint truth。**

可用于排序人工/Agent 复查优先级，但不能作为 hard gate。

**D3 — 把 ORPilot 的 MIP 专用语义 heuristic 直接当通用数模 validator。**

变量名启发式可能误报，必须基于 contract type/plugin 做 checker。

**D4 — 把“代码运行成功”当作建模正确。**

运行通过只是最低门槛。

---

## 11. 存在的问题

### ORPilot

- 主要覆盖 LP/MIP，不能直接代表数学建模全题型；
- `ProblemDefinition` 太粗，没有 page/span/source hash、authority、unit、tolerance、official output schema；
- semantic validator 中部分规则依赖领域/命名 heuristic；
- IR 很适合“模型实现”，但不等价于“赛事题面合同”。

### CCA

- 原任务是通用 rule-dense ICL，不是数学建模；
- verifier 主要检查输出 adherence，不覆盖 solver/data/result lineage；
- 自动生成 checker 仍可能产生 checker bug；
- compiler parse 失败时允许 fallback，对华为杯 hard requirements 太宽松。

### OptiMUS

- 主要依赖 LLM confidence 和自然语言反思；
- constraint/source 的原文定位与哈希不足；
- execute/debug 更重“程序是否能跑”，不足以证明“模型是否正确”；
- 较老架构，适合借鉴 decomposition，不适合直接作为当前底层框架。

---

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 题面完整读取 | 已强制 Phase 1 完整读取题面/附件 | ORPilot interview 强调补齐缺失信息 | **保持**现有完整读取；增加结构化编译 |
| 人类可读约束 | `求解/题面约束清单.md` 很完整 | OptiMUS 约束/参数分阶段保存 | **保持** Markdown，不替换 |
| Machine-readable Problem Contract | 未发现统一 schema/JSON | CCA typed IR、ORPilot ProblemDefinition/IR | **新增** |
| 规则 source span | 原则上可从题面回读，但无统一 ID/hash | CCA 有 `source` quote | **改进**为 file/page/span/hash |
| 权威优先级 | AGENTS/CLAUDE 已明确 | 三项目不针对华为杯 | **保持**并编译成 contract conflict resolver |
| 单位/精度/输出格式 | 清单要求记录 | CCA numeric/output_spec 可结构化 | **新增** machine fields + checker |
| 数学模型 IR | 当前主要由求解代码/结果体现 | ORPilot 有 solver-agnostic IR | **值得实验**，先从优化题型开始 |
| Semantic validation | 求解规范要求独立验证 | ORPilot 有 deterministic IR semantic checks | **新增** proof obligation 层 |
| 规则执行 checker | 视觉/支撑材料已有专用 auditor | CCA 自动生成 Python verifier | **改进**：扩展到题面 hard rules |
| 多路线模型搜索 | 历史 research 已建议 | ORPilot 非重点 | contract 应成为所有路线共享基线 |
| Checkpoint stale | 已提出 contract/hash 思路 | CCA/ORPilot 支持 resume/session | **新增** contract_hash 到 checkpoint/candidate |
| Reviewer 对齐 | 已研究 hierarchical rubric | CCA violation feedback | Reviewer criterion 应引用 constraint_id |
| 正式论文约束 | TeX/视觉/支撑材料审计很强 | 三项目不覆盖华为杯论文 | **保持**现有优势 |

五类总体判断：

- **保持**：现有 `题面约束清单.md`、权威顺序、不可变原始输入、证据链；
- **改进**：让 Markdown 从 machine contract 派生/同步，减少双重事实源；
- **新增**：Problem Contract、source span、contract hash、Proof Obligation；
- **替换**：不建议替换现有求解工作流，只在 Phase 1→Phase 2 间增加 contract gate；
- **暂不采用**：完整引入 ORPilot/OptiMUS 作为主框架、通用自动 checker 生成、MIP-only IR 作为全题型标准。

---

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：定义 `题面契约.schema.json` 与 `求解/题面契约.json`

第一版不需要过度形式化，但至少覆盖：

```text
contract_id / contract_version / contract_hash
source_manifest
questions[]
inputs[]
outputs[]
objectives[]
constraints[]
units[]
precision_and_tolerance[]
method_restrictions[]
data_split_rules[]
resource_limits[]
official_output_schema[]
question_dependencies[]
ai_submission_rules[]
conflicts[]
unresolved_items[]
```

#### P0-2：每条 hard rule 强制 source-grounded

每条规则保存：

```text
constraint_id
source_ref.file/page/section/span/quote_hash
authority
scope
kind
target
predicate_type
normalized_predicate
units
tolerance
codeable
checker_type
status
```

没有 source 的条目只能标记为 `ASSUMPTION` 或 `DERIVED`，不能伪装成题面 hard rule。

#### P0-3：新增 Proof Obligation Contract

建议概念文件：

```text
求解/验证义务.json
```

每条 obligation 绑定：

```text
obligation_id
constraint_id
checker_type
input_artifacts
expected_predicate
tolerance
status
evidence_path
checker_version
```

只有 hard obligation 全部 PASS 或被明确豁免，candidate 才能进入 canonical promotion。

#### P0-4：所有下游 artifact 绑定 `contract_hash`

将历史几轮研究真正串起来：

- checkpoint；
- candidate manifest；
- result index；
- validation report；
- figure plan；
- paper input manifest。

contract 改变后，由 18:04 的 stale 机制使受影响产物自动失效。

#### P0-5：冲突和歧义成为一等状态

不要猜：

```text
VERIFIED
AMBIGUOUS
CONFLICT
MISSING
ASSUMPTION
DERIVED
```

权威冲突按现有 AGENTS/CLAUDE 顺序处理；无法解决的硬冲突停止受影响 question，而不是静默继续。

### P1：值得实验

#### P1-1：历史赛题 Contract Regression Corpus

选 5–10 个往届题，人工建立 gold contract，再测试 compiler 的：

- hard constraint recall；
- source span precision；
- unit extraction accuracy；
- objective direction accuracy；
- official output schema accuracy；
- ambiguity detection accuracy。

#### P1-2：Mutation Suite

对题面 contract 人为注入：

- `<=` → `>=`；
- 最大化 → 最小化；
- m → mm；
- 4 位小数 → 2 位；
- result.xlsx → result.csv；
- train/test 时间边界移动；
- Q2 dependency 指向错误 Q1 version。

系统必须能在 solver/promotion/paper 前发现。

#### P1-3：Compile-once vs Re-read-every-time 对照

让多个 Agent 独立读题 vs 全部共享 contract，比较：

- constraint disagreement；
- downstream rework；
- token；
- 最终违反题面 hard rules 的次数。

### P2：长期考虑

- 对数学表达式建立 typed AST；
- 引入 SymPy/Z3 做部分可满足性和符号约束检查；
- 用 unit algebra 做维度分析；
- 自动解析官方 Excel/CSV 模板为 output schema；
- 自动生成 question dependency DAG；
- 对 PDE/ODE/统计/仿真定义专用 contract plugin，而不是一个超大通用 schema。

### 不建议采用

- 不建议让题面 compiler 失败后退回“Agent 自己读着办”；
- 不建议用 LLM confidence 分数代替来源证据；
- 不建议第一版就做一个覆盖所有数学学科的复杂 formal language；
- 不建议让机器 contract 与 `题面约束清单.md` 变成两个独立维护、可能漂移的事实源。

---

## 14. 可形成的新 Skill / Agent

仅提出设计建议，本轮不创建：

### `problem-contract-compiler`

把题面/附件/官方模板编译为 source-grounded typed contract。

### `problem-contract-auditor`

检查 contract 的完整性、冲突、source fidelity、单位、依赖和版本。

### `proof-obligation-compiler`

把 codeable hard constraints 转成 deterministic checks，并输出 obligation manifest。

### `contract-diff-agent`

在题面/用户补充/附件变化时，解释 contract diff，并列出需要 invalidate 的 solver/result/figure/paper artifacts。

这四者应属于**题面事实层**，位于 model-search / solver / reviewer 之前。

---

## 15. 与历史调研的去重检查

本轮逐项对 `research/INDEX.md` 检查：

- **不是 15:06 Model Selection**：本轮不研究 candidate 怎么搜索，而研究所有 candidate 必须共享什么题面合同；
- **不是 16:04 Reviewer**：本轮不设计 Judge scoring，而定义 Reviewer 要验证的 upstream criterion / proof obligation；
- **不是 17:07 Checkpoint**：本轮只提出 `contract_hash` 作为 checkpoint 依赖；不重复 resume 架构；
- **不是 18:04 Artifact Provenance**：那一轮关注计算结果 stale；本轮关注题面 constraint 的 source/span/authority 和 contract compilation；
- **不是 20:08 External Evidence**：20:08 解决外部论文 claim-evidence；本轮解决官方题面/附件/模板的 specification truth。

三个项目 `ORPilot`、`CCA`、`OptiMUS` 均未出现在当前 INDEX 的历史项目集合中。

本轮新增认知是：

1. **题面应先“编译”再分发给 Agent，而不是只生成一份 Markdown 清单；**
2. **Problem Contract 与 Model IR 必须分层：一个题面合同可支持多个模型路线；**
3. **hard constraints 应进一步编译为 Proof Obligations，使题意正确性进入机器门禁；**
4. **contract_hash 应成为此前 checkpoint / candidate / validation / promotion / paper provenance 的共同上游版本锚点。**

因此不存在通过改写旧结论凑数的问题。

---

## 16. 下一轮推荐方向

建议下一轮轮换到：

**Counterexample / Falsification Agent：自动生成边界条件、极端工况、反例和 adversarial scenarios，对数学模型做“主动证伪”而不是只做常规敏感性分析。**

可重点研究：

- property-based testing；
- metamorphic testing；
- adversarial scenario generation；
- optimization infeasibility / constraint stress tests；
- scientific model falsification；
- 如何从本轮 `Proof Obligations` 自动生成测试场景；
- 如何区分“代码 bug”“模型失效边界”“题面本来就不可满足”。

这会直接提高优先级中的“建模质量、结果真实性、验证能力”，且目前 INDEX 尚未覆盖。

---

## 17. Sources

### 已阅读源码 / 官方仓库

1. `math_mode` 当前仓库：
   - https://github.com/shaxiaoguang123/math_mode
   - `README.md`
   - `AGENTS.md`
   - `CLAUDE.md`
   - `research/INDEX.md`
   - `research/2026-09-08/2026-09-08_20-08_citation-evidence-provenance.md`

2. ORPilot：
   - Repository: https://github.com/GuangruiXieVT/ORPilot
   - 本轮固定 commit: `d153a680aaecd3f90e8466f77259bd8275bd6216`
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/README.md
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/orpilot/models/problem.py
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/orpilot/models/ir.py
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/orpilot/workflow/nodes/ir_builder.py
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/orpilot/codegen/ir_validator.py
   - https://github.com/GuangruiXieVT/ORPilot/blob/main/orpilot/workflow/nodes/ir_compiler_node.py
   - Paper: https://arxiv.org/abs/2605.02728

3. CCA：
   - Repository: https://github.com/TonyQJH/cca-emnlp2026
   - 本轮固定 commit: `a8230f94c957c60fb8be808742398612a2da6699`
   - https://github.com/TonyQJH/cca-emnlp2026/blob/main/README.md
   - https://github.com/TonyQJH/cca-emnlp2026/blob/main/code/cca_core.py
   - Paper: https://arxiv.org/abs/2609.00759
   - OpenReview: https://openreview.net/forum?id=fkHzqnhdIY

4. OptiMUS：
   - Repository: https://github.com/teshnizi/OptiMUS
   - 本轮固定 commit: `59e8d99653459b40361f618eafdc91eee3a85ebb`
   - https://github.com/teshnizi/OptiMUS/blob/main/main.py
   - https://github.com/teshnizi/OptiMUS/blob/main/parameters.py
   - https://github.com/teshnizi/OptiMUS/blob/main/constraint.py
   - https://github.com/teshnizi/OptiMUS/blob/main/execute_code.py
   - Paper: https://arxiv.org/abs/2407.19633

### 证据级别说明

- 本轮关于 ORPilot 的 ProblemDefinition、IR schema、semantic validator、deterministic compiler 与 retry loop：**已阅读源码**。
- 本轮关于 CCA 的 typed IR、source/codeable/code_hint、Python verifier 和 correction flow：**已阅读 README 与核心源码**。
- 本轮关于 OptiMUS 的分阶段 state、参数/约束抽取和 subprocess 执行/debug：**已阅读源码**。
- 本轮未在本机实际安装/运行三个项目，因此没有声称其 runtime performance 已由本轮独立复现实验验证；论文/README 中的 benchmark 数字仅作为项目官方报告信息，不作为 `math_mode` 已验证结论。
