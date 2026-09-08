# MathModel Agent Research

## 1. 本轮研究主题

**Robust Optimization / Chance-Constrained Decision Agent：把上一轮 UQ 证据真正编译成“会因不确定性而改变”的稳健决策，而不是只在论文里增加误差带。**

本轮研究的问题是：

> 当 `math_mode` 已经知道输入、参数、场景或预测存在不确定性之后，怎样决定应该使用 nominal optimization、robust optimization、chance constraint、CVaR 还是 distributionally robust optimization（DRO）；怎样把这些不确定性假设编译进可执行优化模型；以及怎样证明最终方案是真的“更稳健”，而不是因为人为扩大参数范围或改变目标函数而得到一个看似保守的答案？

上一轮已经建立了 UQ 的基本研究结论：不确定性必须有来源、数据角色和适用假设，prediction interval 要检查 coverage/sharpness，敏感性分析要保存采样设计与 CI。当前缺口是：

- UQ 仍主要回答“结果有多不确定”；
- 还没有统一回答“决策应如何响应这种不确定性”；
- 还没有 machine-readable 的 `risk semantics`：某个区间到底表示集合不确定性、概率分布、经验场景，还是分布本身也不确定；
- 还没有把 `robust feasible`、`robust optimal`、`chance-feasible`、`CVaR-improved` 等状态与 solver certificate、out-of-sample 回测和 canonical promotion 绑定；
- 还没有系统检查 chance constraint 中的 scenario probability、binary indicator、Big-M、样本外违约率；
- 还没有明确区分“控制违约概率”和“控制尾部损失严重程度”；
- 还没有把“名义方案 vs 稳健方案”的代价—风险权衡固定为必须报告的证据。

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的高价值对象：

1. `Pyomo/pyomo` 中的 **PyROS**：两阶段非线性 robust optimization、uncertainty set、master/separation、`robust_feasible` / `robust_optimal` 终止语义；
2. `XiongPengNUS/rsome`：robust / distributionally robust optimization、event-wise ambiguity set、support / expectation / probability set 与 adaptive recourse；
3. `Pyomo/mpi-sppy`：scenario-based stochastic programming、CVaR、当前开发分支中的 SAA chance constraint、真实 solver tests，以及“CVaR 可分解而 chance constraint 跨场景耦合”的架构差异。

本轮核心结论：

> `math_mode` 不应设置一个固定的“鲁棒优化模型”作为所有题目的高级选项，而应新增 **Decision Under Uncertainty Layer**：先由 UQ Contract 判断不确定性语义和证据强度，再选择风险模型，生成 nominal / robust / chance / CVaR / DRO 候选，真实求解并独立做样本外/最坏情形验证，最后只有具备可追溯风险假设与 solver/validation certificate 的方案才能被称为“稳健方案”并进入 canonical result。

建议的目标结构为：

```text
Problem Contract + Candidate Model + UQ Contract
                    ↓
          Decision Risk Compiler
 uncertainty semantics / authority / stage / recourse
                    ↓
    ┌───────────────┼────────────────────┐
    ↓               ↓                    ↓
 Nominal        Robust Set           Probabilistic
 baseline       Optimization         decision
                PyROS-like           chance / CVaR
                                         ↓
                               Distribution uncertain?
                                     ↓ yes
                                    DRO
                    ↓
              Real Solver Runs
                    ↓
          Decision Evidence Pack
 objective / feasibility / worst case / violation rate
 CVaR / scenario failures / optimality gap / solver status
                    ↓
       Independent Out-of-Sample Review
                    ↓
        Robust Decision Promotion Gate
                    ↓
 canonical result → Result Index → Figure Plan → Paper
```

---

## 2. 为什么选择这个主题（说明与历史调研差异）

### 2.1 历史去重基线

本轮开始前重新读取了 `README.md`、`AGENTS.md`、`CLAUDE.md`、项目树、`.agents/skills/academic-figure-skill/SKILL.md`、`research/INDEX.md` 以及最近两轮 research。

截至本轮，历史研究已经覆盖：

- 14:00：evidence-first 科研 Agent；
- 15:06：模型搜索树、MCTS/UCT、并行实验；
- 16:04：Reviewer / Judge 与 JudgeEval；
- 17:07：Checkpoint / Resume；
- 18:04：Artifact Ownership / canonical promotion；
- 19:07：Resource Scheduler / pruning；
- 20:08：Citation / External Evidence Provenance；
- 21:04：Problem Contract / Proof Obligations；
- 22:06：Counterexample / Falsification；
- 23:04：Model Calibration / Uncertainty Quantification。

本轮与这些主题的边界是：

- 与 **UQ** 不同：UQ 量化不确定性，本轮研究“决策怎样根据不确定性改变”；
- 与 **Falsification** 不同：Falsifier 主动找失败，本轮需要设计能在不确定条件下仍满足风险标准的 decision policy；
- 与 **Reviewer** 不同：Reviewer 验证已有方案，本轮产生 nominal / robust / risk-averse / DRO 等新的决策候选；
- 与 **Model Search** 不同：Model Search 主要比较模型路线，本轮比较的是同一问题在不同 risk semantics 下的决策策略；
- 与 **Problem Contract** 不同：Problem Contract 固定题面硬约束，本轮增加的是“允许多大违约概率、控制什么尾部风险、是否需要 recourse”等决策语义；
- 与当前已有“鲁棒性/场景分析”不同：现有规范要求真实运行场景和鲁棒性分析，但尚未形成 risk model contract、solver certificate 和 out-of-sample decision gate。

上一轮 23:04 报告已经把 **Robust Optimization / Chance-Constrained Decision Agent** 明确列为下一轮推荐，因此本轮属于主动轮换，不是措辞变化式重访。

### 2.2 当前 math_mode 已经有什么

基线读取确认当前项目已经有很强的优化与验证基础：

- `AGENTS.md` / `CLAUDE.md` 要求每问先写 Baseline、主模型、验证、敏感性/稳健性、关键结果与问题依赖；
- Evidence Matrix 必须覆盖误差/约束、对比、敏感性/鲁棒性、场景、理论边界与反证；
- 求解规范对优化/调度问题要求：
  - 无优化或简单启发式 baseline；
  - 可行性与官方指标独立复算；
  - 优化前后对比；
  - 权重或约束扫描；
  - Pareto；
  - 收敛与多初值；
  - 规模—时间；
  - 可获得时报告 optimality gap；
- 多目标优化要求单目标极值、加权和 baseline、Pareto 前沿、代表折中点、目标冲突、权重/epsilon 扫描以及场景下前沿移动；
- 新增的 sensitivity / robustness / scenario / Monte Carlo 分析必须真实运行并保存到 `求解/问题X/结果/`；
- 绘图脚本只能读取已落盘结果，不允许为了图重新优化、抽样或补数；
- `求解/结果索引.md` 是论文数字和结论的事实主索引；
- 支撑材料链已经有源码、运行记录和 SHA-256；
- 前几轮 research 已经提出 UQ Contract、Candidate workspace、canonical promotion、Reviewer Gate、Counterexample Archive 等机制。

因此当前缺口并不是“没有鲁棒性意识”，而是：

> 现有项目能要求做“鲁棒性分析”，但还没有统一定义何时应该真的改变优化目标/约束，怎样区分 set-based robustness、probabilistic reliability 和 tail-risk aversion，以及什么证据足以支持“稳健最优/风险受控”这种更强的论文表述。

### 2.3 为什么这对华为杯有直接价值

数学建模竞赛里非常常见的一类问题是：

- 需求、价格、载荷、到达时间、故障率等未来参数不确定；
- 预测模型输出要继续进入优化模型；
- 题目要求在风险、成本、收益、可靠性之间权衡；
- 方案不能只在一个“平均场景”好看；
- 最优解对小扰动非常脆弱；
- 题目没有直接给出完整概率分布，只给区间、历史样本或几个场景。

常见错误包括：

- 把所有参数统一 ±10% 后直接称为“鲁棒优化”；
- 没有概率证据，却写 `P(constraint) >= 0.95`；
- 把 chance constraint 的“违约频率”当成“违约损失不会很大”；
- 用 CVaR 后只报告目标值变差，不报告尾部风险到底下降多少；
- 把样本内场景全部满足称为“95% 可靠”；
- 在训练/调参用过的同一场景上评估稳健方案；
- Big-M 取得过小导致真实可行决策被错误排除，或过大造成数值病态；
- solver 只返回 robust feasible，却在论文写“全局稳健最优”；
- 并行分解算法本身并不支持某种跨场景风险约束，但工作流静默忽略该约束；
- risk-aversion 参数 `alpha/beta/radius` 只是为了让图更漂亮而人工调节。

本轮目标就是把这些高风险点变成可执行的工程门禁。

---

## 3. 搜索范围与关键词

本轮属于 P1（optimization / simulation / reproducible decision）为主，直接服务 P0 数学建模决策质量。

核心关键词：

- robust optimization agent mathematical modeling
- robust counterpart uncertainty set Pyomo PyROS
- generalized robust cutting set separation problem
- robust feasible robust optimal certificate
- distributionally robust optimization ambiguity set Python
- RSOME support set expectation set probability set
- adaptive robust decision recourse policy
- stochastic programming CVaR scenario optimization
- chance constraint sample average approximation
- chance constraint binary indicator big-M validation
- CVaR risk neutral comparison tail loss
- out-of-sample feasibility robust decision
- uncertainty set calibration data-driven robust optimization
- stochastic programming confidence interval candidate solution
- decision under uncertainty regression tests

筛选标准：

1. 必须能真实构建并求解优化模型，而不是只做自然语言风险分析；
2. 必须清楚表达 uncertainty/risk semantics；
3. 优先有 solver termination、scenario/separation、validation test 或结果对象；
4. 优先能够暴露错误建模边界，例如 robust vs chance、chance vs CVaR、uncertainty set vs ambiguity set；
5. 不泛化到普通调度库、通用 Agent 框架或 RAG；
6. 本轮限制 3 个高价值对象，避免项目堆砌。

---

## 4. 新发现项目（名称、Repository、Stars 如可得、最近更新时间、目标、核心能力）

### 4.1 Pyomo / PyROS

- 名称：PyROS — Pyomo Robust Optimization Solver
- Repository：https://github.com/Pyomo/pyomo
- 本轮固定读取 commit：`e099f6463abd3b17b3231abf108b0a46e9640d1a`
- Stars：2522（本轮 GitHub metadata）
- Repository `updated_at`：2026-09-07；`pushed_at`：2026-09-02
- Pyomo 最新 GitHub Release：`6.10.1`，2026-06-04 发布
- PyROS 最新官方论文/技术报告页面：2026-06-18，Optimization Online，`PyROS: The Pyomo Robust Optimization Solver`
- 目标：在用户已有 deterministic Pyomo model + uncertainty set 基础上，自动构造并求解两阶段非线性 robust counterpart。
- 核心能力：continuous/nonconvex NLP、first/second-stage decision、uncertain equality/inequality/objective、continuous/discrete uncertainty set、static/affine/quadratic decision rule、Generalized Robust Cutting-Set（GRCS）、local/global NLP subordinate solver、separation priority、robust termination semantics。

本轮实际阅读：

- `doc/OnlineDocs/explanation/solvers/pyros/overview.rst`
- `doc/OnlineDocs/explanation/solvers/pyros/solver_interface.rst`
- `pyomo/contrib/pyros/uncertainty_sets.py`
- `pyomo/contrib/pyros/util.py` / termination condition 搜索
- `pyomo/contrib/pyros/pyros_algorithm_methods.py` 相关终止状态搜索
- PyROS 2026 官方论文页面

### 4.2 RSOME

- 名称：RSOME — Robust Stochastic Optimization Made Easy
- Repository：https://github.com/XiongPengNUS/rsome
- 本轮固定读取 commit：`1a0cf887efaa122e941651f8a40cc20d46f0dbf5`
- Stars：347
- Repository `updated_at`：2026-08-13；最近代码 `pushed_at`：2024-11-15
- README 当前 PyPI 版本：`1.3.1`
- 目标：用 NumPy 风格数组 API 建模 robust optimization 和 distributionally robust optimization，并编译为线性/二阶锥/指数锥等确定性问题交给外部 solver。
- 核心能力：RO、DRO、scenario representation、event-wise ambiguity set、support set、expectation set、probability set、event-wise static/affine adaptation、worst-case expectation、多个开源/商业 solver 接口。

本轮实际阅读：

- `README.md`
- `docs/dro_rsome.md`
- `rsome/dro.py`
- 2023 INFORMS Journal on Computing 官方论文页面

### 4.3 mpi-sppy

- 名称：mpi-sppy — MPI-based Stochastic Programming in Python
- Repository：https://github.com/Pyomo/mpi-sppy
- 本轮固定读取 commit：`fd920757af27d6494c92be6e2cf618f5f4ef08e5`
- Stars：91
- Repository `updated_at`：2026-09-06；`pushed_at`：2026-09-08 15:35 UTC
- 最新正式 GitHub Release：`0.14.0`，2026-07-10
- 当前 `main` 已进入 `0.14.1.dev0` 文档流；本轮关注的 chance-constraint 设计文档仍标记 `draft for review`，因此本报告只说“当前 main 源码级存在实现与测试”，不声称它已经成为稳定 release API。
- 目标：对场景型随机规划使用 MPI 和 hub-and-spoke / PH 等方法进行大规模并行优化。
- 核心能力：Extensive Form、Progressive Hedging/APH、多个 bound/xhat spokes、CVaR risk management、scenario-based evaluation、并行执行、当前 main 中的 SAA chance constraint EF transform。

本轮实际阅读：

- `README.md`
- `mpisppy/utils/chance_constraint.py`
- `doc/designs/chance_constraint_design.md`
- `mpisppy/tests/test_chance_constraint.py`
- `doc/src/risk_management.rst`
- `0.14.0` release metadata
- 当前 readthedocs 的 chance constraint / CVaR 页面作为文档补充

---

## 5. 深入架构分析

### 5.1 PyROS：Master 决策 + Separation 反例搜索

PyROS 的一个非常关键的结构是：

```text
Deterministic Pyomo Model
  + first-stage vars
  + second-stage vars
  + uncertain params
  + uncertainty set Q
            ↓
   Robust Counterpart Semantics
            ↓
       Master Problem
   当前已知不确定场景集合
            ↓
       Candidate Decision
            ↓
    Separation Subproblems
 在 Q 内寻找最大违反/最坏场景
       ┌────┴────┐
 no violation   violation
       ↓           ↓
 robust state   add scenario/cut
       ↓           └──→ next master iteration
   termination
```

这与前两轮 `Falsification Agent` 和 `UQ Contract` 可以天然连接：

- UQ Contract 给出合法 uncertainty set；
- robust solver 产生 candidate；
- separation 本质上是在不确定集合内部做 adversarial search；
- 找到 worst-case realization 后，它不是只写进论文，而是重新进入优化；
- 直到没有可接受的违反场景，才形成 robust feasibility 证据。

这说明 `math_mode` 未来的“鲁棒优化”不应采用一次性：

```text
取几个极端点 → 求解一次 → 声称鲁棒
```

更可靠的是：

```text
设计 → 主动寻找最坏场景 → 加回优化 → 再验证
```

### 5.2 PyROS 对“robust feasible”和“robust optimal”的严格区分

`solver_interface.rst` 给了一个非常值得直接借鉴的状态语义：

- 求解可以返回 `robust_feasible`；
- 只有在：
  1. master problem 采用全局求解；
  2. objective focus 是 worst-case；
  才将终止状态标成 `robust_optimal`；
- 否则即使找到符合不确定集合的方案，也不应升级成“robust optimal”。

这正是数学建模论文中经常被写错的地方。

建议 `math_mode` 将优化结论拆成：

```text
FEASIBLE
NOMINAL_OPTIMAL
ROBUST_FEASIBLE
ROBUST_OPTIMAL_CERTIFIED
RISK_CONSTRAINED_FEASIBLE
SAA_FEASIBLE
OUT_OF_SAMPLE_VALIDATED
UNVERIFIED
```

而不是所有 solver 返回结果都写“最优方案”。

### 5.3 PyROS 的 uncertainty set 是 executable object，不是描述性文字

`uncertainty_sets.py` 把 uncertainty set 变成真正可以生成约束的对象，包含：

- BoxSet；
- BudgetSet；
- CardinalitySet；
- EllipsoidalSet；
- FactorModelSet；
- DiscreteScenarioSet；
- CartesianProductSet；
- 自定义 NLP-representable uncertainty set。

同时代码检查维度、类型、finite values 等。

对 `math_mode` 的直接启发：

> `UQ Contract` 中的区间/协方差/场景不能只写在 Markdown，应能够被编译成 executable uncertainty object，并保存其 hash；求解、separation、图表和论文全部引用同一版本。

### 5.4 一个非常重要的细节：不是每个约束都必须“robust”

PyROS 的 separation priority 允许某些约束优先检查，也允许将 priority 设为 `None`，使约束只在 nominal realization 下执行，而不进入 robust separation。

这提示 `math_mode` 需要显式区分：

- `hard_for_all_uncertainty`：所有允许不确定 realization 都必须满足；
- `chance_limited`：允许一定概率违约；
- `nominal_only`：仅名义工况约束；
- `soft_penalty`：违反进入目标函数惩罚；
- `diagnostic_only`：只报告，不阻断。

如果 Agent 不做这一步，最容易出现的错误是把所有约束都“鲁棒化”，导致过度保守，或者相反把安全硬约束只做平均意义优化。

### 5.5 RSOME：从“值的不确定”升级为“分布的不确定”

RSOME 的 DRO 结构比普通 robust optimization 更进一步。

它把不确定性分成：

```text
Scenario/Event Structure
        ↓
Random Variables z
        ↓
Ambiguity Set F
  ├─ support set Z_s
  ├─ expectation/moment set Q_k
  └─ scenario probability set P
        ↓
Worst-case expectation / constraints
        ↓
Adaptive decision rule
        ↓
Deterministic conic reformulation
        ↓
External solver
```

这给出一个非常关键的概念分界：

- **uncertainty set**：参数可能取哪些值；
- **probability distribution**：这些值出现的概率是什么；
- **ambiguity set**：我们连概率分布本身也不确定，只知道其 support/moment/probability constraints。

数学建模 Agent 必须知道这三者不是同一件事。

### 5.6 RSOME 的 ambiguity set 要“完整可审计”

RSOME 文档说明：如果某个 scenario 的 support 未指定，模型求解时会报错；`showevents()` 用于显示已声明的 supports 和 expectations，帮助检查 ambiguity set。

这个设计很适合迁移为 `math_mode` 的 **Risk Contract Preview**：

```text
uncertain quantity | semantics | support | probability/moment | source | stage | used by
```

在真正求解前先生成机器/人均可读的审计表。缺项时不应自动假设正态分布或均匀分布。

### 5.7 RSOME：recourse / adaptation 是决策语义，不只是算法细节

RSOME 支持 event-wise static adaptation 和 event-wise affine adaptation。

这意味着稳健决策还有一个竞赛中经常被忽略的问题：

> 哪些变量必须“现在决定”，哪些变量可以等不确定性部分揭示之后再调整？

例如：

- 赛前资源配置可能是 first-stage；
- 实际需求到达后的补货量可以是 recourse；
- 已知未来信息之前不允许决策依赖未来随机变量，否则就是信息泄漏。

因此 UQ/风险优化的 machine contract 还应包含：

```text
decision_stage
information_available_at_decision
adaptive_to
nonanticipativity_group
recourse_policy_type
```

这与前面数据泄漏检查是不同层级的“决策信息泄漏”。

### 5.8 mpi-sppy：同样是风险控制，CVaR 和 chance constraint 的计算结构完全不同

当前 mpi-sppy 文档/源码给出了一个非常高价值的架构对比。

#### CVaR

CVaR 使用 Rockafellar–Uryasev 线性化：

```text
shared VaR variable eta
+ per-scenario excess delta_s
+ E[Cost] / tail loss objective
```

因为风险目标可以分布到各场景，shared `eta` 作为 nonanticipative first-stage variable，EF、PH/APH、Lagrangian、xhat 等算法可以复用它。

#### Chance Constraint

当前 main 的 chance constraint 使用：

```text
z_s = 1 iff risky constraint satisfied in scenario s

sum_s p_s * z_s >= 1 - alpha
```

这个单一约束把**所有场景的 indicator**耦合到一起，因此它不能被简单拆到每个 scenario subproblem；当前实现明确只支持 extensive form。

这说明：

> 风险模型选择会直接影响可用的求解架构。Agent 不能先选并行算法，再不管数学结构地往上挂一个风险约束。

### 5.9 mpi-sppy：chance constraint 不帮你发明风险语义

`chance_constraint.py` 明确把责任留给用户：

- 用户定义 indicator `z_s`；
- 用户定义 `z_s` 与风险约束是否满足之间的 Big-M linking constraints；
- mpi-sppy 只负责聚合 `sum p_s z_s >= 1-alpha`。

这对 Agent 极其重要：

> 工具可以编译风险约束，但不能替代“哪个约束是 risky constraint”“怎样构造正确 indicator”“Big-M 为什么是这个值”的建模推理。

因此 `math_mode` 若未来自动生成 chance constraint，必须把这三项放进 Reviewer Gate，而不能只检查 solver 成功。

### 5.10 Fresh finding：mpi-sppy 当前 main 已有真实 chance-constraint solver tests，但仍需版本边界声明

本轮发现是一个真正“新近”的机制：

- 当前 main `fd920757...` 已有 `mpisppy/utils/chance_constraint.py`；
- 有 `mpisppy/tests/test_chance_constraint.py`；
- 测试真实构造 EF，并在 solver 可用时执行求解；
- 测试包含：
  - `alpha=0.5`；
  - `alpha=0.75`；
  - `alpha=0` 等价 robust；
  - 不加 chance constraint 等价 risk-neutral；
  - indexed indicator；
  - missing indicator / bad alpha validation；
- 但 design 文档仍写 `Status: draft for review`；
- 最新正式 GitHub release 仍是 2026-07-10 的 `0.14.0`。

因此报告只能得出：

> **当前开发 main 源码级已实现并测试此能力。**

不能把它写成：

> **稳定 release 已正式支持并经过生产验证。**

这种版本边界正是 `math_mode` 外部工具 Agent 应保持的证据标准。

---

## 6. Agent / Skill 设计

本轮三个项目本身主要是 optimization software，不是 LLM Agent 系统。因此这里不伪造“它们已经有某种 AI Agent”；真正值得迁移的是把其数学/solver 责任边界转成 `math_mode` 的 Agent/Skill 划分。

### 6.1 Decision-Risk Planner

职责：在调用任何 solver 前先决定风险语义。

输入：

- Problem Contract；
- UQ Contract；
- 数据审计；
- candidate model；
- 决策时点/信息结构；
- 题面硬约束。

输出：

```text
risk_semantics:
  nominal | robust_set | chance | cvar | stochastic | dro

uncertainty_authority:
  problem | measurement | historical_data | external_evidence | scenario_only

constraint_roles:
  hard_for_all | chance_limited | nominal_only | soft_penalty

recourse:
  stages / information_sets / adaptive variables
```

为什么必须独立：

- 风险语义属于数学建模，不应该由某个具体 solver adapter 暗自决定；
- 同一个数据范围可能用于 worst-case set，也可能用于 scenario distribution，两者论文含义完全不同。

### 6.2 Robust-Optimization Adapter

职责：

- 把 executable uncertainty set + deterministic model 编译成 robust formulation；
- 调用 PyROS-like solver 或项目自写 robust model；
- 保存 master/separation/worst-case scenario/termination 状态；
- 不自行创造 uncertainty bounds。

### 6.3 Chance/CVaR Adapter

职责：

- chance：构建 scenario indicator、概率聚合、`alpha`、Big-M linking；
- CVaR：构建 `eta` / excess variables / tail risk objective；
- 检查求解后 risk-neutral vs risk-averse 对照。

为什么两者不要合并成“Risk Agent”：

- chance 约束的是违约频率；
- CVaR 约束/惩罚的是尾部损失的严重程度；
- 两者计算结构不同、可分解性不同、验证指标也不同。

### 6.4 DRO / Ambiguity Adapter

职责：

- 明确 support / moments / scenario probability ambiguity；
- 记录每个 ambiguity component 的数据/文献来源；
- 生成 `showevents`-like preview；
- 缺少必要 distribution evidence 时拒绝把 scenario set 升级成概率分布。

### 6.5 Big-M Auditor

这是本轮建议新增的一个非常具体且高价值的 verifier。

职责：

- 找出所有 chance/disjunctive indicator 使用的 M；
- 记录 M 的推导来源；
- 尝试基于变量 bounds / Problem Contract 推导 tighter valid M；
- 检查 `too-small M` 是否切掉合法解；
- 检查 `too-large M` 是否造成尺度异常/solver 数值问题；
- 输出 `M_validity_status` 与证据。

### 6.6 Risk Backtest Reviewer

职责：

- 对 canonical candidate 使用独立 holdout scenarios / resamples / adversarial cases；
- 不允许用生成方案时已经使用过的同一组场景直接宣称样本外可靠；
- 重新计算：
  - violation rate；
  - worst-case constraint margin；
  - tail loss；
  - CVaR；
  - objective regret；
  - recovery/recourse feasibility；
- 输出可进入 Reviewer Gate 的独立证据。

---

## 7. Workflow

### 7.1 推荐主流程

```text
Phase A  Problem Contract
         ↓
Phase B  Candidate Model + deterministic baseline
         ↓
Phase C  UQ Contract
         uncertainty source / range / distribution / dependence
         ↓
Phase D  Decision Risk Planning
         robust? chance? CVaR? DRO? recourse?
         ↓
Phase E  Risk Contract Audit
         semantics / authority / alpha / radius / Big-M / stages
         ↓
Phase F  Candidate Fork
         ├─ nominal
         ├─ robust
         ├─ chance
         ├─ CVaR
         └─ DRO (only when evidence supports)
         ↓
Phase G  Real Solver Execution
         status / log / gap / runtime / scenario / separation
         ↓
Phase H  Independent Risk Backtest
         held-out / resampled / adversarial uncertainty
         ↓
Phase I  Trade-off Analysis
         performance vs risk vs compute vs interpretability
         ↓
Phase J  Robust Decision Promotion Gate
         ↓
canonical result
         ↓
Result Index → Figure Plan → Paper
```

### 7.2 Workflow state

建议新增状态：

```text
DRAFT_RISK_CONTRACT
AUDITED_RISK_CONTRACT
COMPILED
SOLVING
SOLVED
SOLVER_INCONCLUSIVE
ROBUST_FEASIBLE
ROBUST_OPTIMAL_CERTIFIED
SAA_FEASIBLE
BACKTEST_FAILED
BACKTEST_PASSED
PROMOTABLE
STALE
```

关键规则：

- `SOLVED` 不能直接等于 `PROMOTABLE`；
- `SAA_FEASIBLE` 不能直接等于“真实概率保证”；
- `ROBUST_FEASIBLE` 不能写成 `ROBUST_OPTIMAL_CERTIFIED`；
- risk contract / UQ contract / Problem Contract 任一 hash 改变，下游 decision evidence 自动 `STALE`。

### 7.3 Checkpoint / resume

本轮项目没有提供 LLM 对话 memory，但其 solver state 提醒 `math_mode`：

- robust master iteration；
- active uncertainty scenarios；
- incumbent decision；
- separation results；
- scenario solution；
- solver status / bound / gap；

都应该成为结构化 checkpoint，而不是塞进聊天摘要。

与 17:07 的 checkpoint 研究结合：恢复时至少验证：

```text
problem_contract_hash
uq_contract_hash
risk_contract_hash
model_code_hash
scenario_set_hash
solver_config_hash
```

任何一项变化都不应静默续跑旧 optimization state。

### 7.4 多阶段决策 / nonanticipativity

对于存在阶段信息的题目，workflow 必须先生成：

```text
Decision Information Table

variable | decision time | observed information | can adapt to | nonanticipativity group
```

然后才能生成 stochastic/robust recourse model。

否则极易出现：

- 决策变量非法使用未来信息；
- 测试集信息进入优化；
- scenario-specific decision 被错误当作赛前可执行统一方案。

---

## 8. Code Execution / Tools

### 8.1 PyROS

真实执行路径：

```text
Python / Pyomo
  ↓
PyROS meta-solver
  ↓
local NLP solver + global NLP solver
  ↓
master + separation subproblems
  ↓
ROSolveResults
```

已确认：

- 实际调用 external solver；
- 支持 local/global NLP subordinate solvers；
- uncertainty set 是 executable object；
- 返回明确 termination condition；
- 支持连续变量，当前并非通用 mixed-integer robust solver。

本轮没有在本地实际运行 PyROS，因此不能声称已对某个比赛模型做过求解验证。

### 8.2 RSOME

真实执行路径：

```text
Python RSOME model
  ↓
RO / DRO algebraic transformation
  ↓
LP / SOC / EC / SDP-like deterministic representation
  ↓
external solver interface
```

README 明确列出 SciPy、CyLP、OR-Tools、ECOS、Gurobi、Mosek、CPLEX、COPT 等接口能力。

本轮确认了代码/文档机制，没有实际安装并运行这些 solver。

### 8.3 mpi-sppy

真实执行路径：

```text
Python / Pyomo scenario creator
  ↓
MPI + mpi4py
  ↓
EF or decomposition / hub-spoke
  ↓
external mathematical solver
  ↓
scenario solutions / bounds / logs
```

README 明确要求 MPI + mpi4py；多 rank 运行推荐 `python -m mpi4py` 以便异常时能正确 abort。

`test_chance_constraint.py` 源码明确：

- 构造真实 Pyomo EF；
- 如果 solver 可用则调用 solver；
- `assert_optimal_termination`；
- 再检查 scenario indicator 与 objective 是否符合 closed-form expectation。

这比仅检查“生成了 chance constraint expression”更强。

### 8.4 Python / MATLAB / Julia / Jupyter / Docker / Sandbox 覆盖情况

本轮三个对象：

- Python：是，核心实现；
- 数学优化 solver：是，真实执行；
- MPI：mpi-sppy 是；
- MATLAB：未发现本轮对象依赖；
- Julia：未发现本轮对象依赖；
- Jupyter：可能有示例生态，但不是本轮核心执行契约；
- Docker/sandbox：不是三者的核心可信边界；
- LLM code sandbox：没有。

对 `math_mode` 的结论：

> 不需要因为研究了这些项目就引入新的 Agent sandbox；应继续复用当前“项目虚拟环境 + 真实 solver + 运行日志 + 支撑材料 hash”机制，但扩展 solver/version/license/config 记录。

### 8.5 建议新的 Solver Run Manifest

每次风险优化至少落盘：

```text
run_id
candidate_id
problem_contract_hash
uq_contract_hash
risk_contract_hash
model_code_hash
scenario_set_hash
solver_name
solver_version
solver_options
seed
start/end/runtime
termination_condition
primal_status
dual/bound status
optimality_gap
risk_metric
risk_parameters
worst_case_scenario
artifact_hashes
stdout/stderr/log path
```

---

## 9. QA / Reviewer / Verification

### 9.1 Robust Optimization QA

必须独立检查：

1. nominal point 是否位于 uncertainty set；
2. uncertainty set 的 range/correlation/budget/radius 是否来自 UQ evidence；
3. 约束哪些是 robust、哪些不是；
4. separation 是否真的执行；
5. worst-case realization 是什么；
6. 最小 constraint margin；
7. termination 是 robust feasible 还是 robust optimal；
8. local/global solver 状态；
9. 方案相对 nominal 的 performance cost；
10. 独立随机/holdout 情景下是否仍有稳定收益。

### 9.2 Chance Constraint QA

chance constraint 至少验证：

```text
alpha range
scenario probability normalization
indicator exists
indicator is binary
indicator semantics correct
Big-M linking valid
sample scenario provenance
in-sample violation rate
out-of-sample violation rate
confidence interval / uncertainty of violation estimate
```

特别需要防止：

- continuous indicator 被当作真实概率约束；
- `alpha=0.05` 被写成“未来一定 95% 满足”，但场景根本不是 IID/代表性抽样；
- 用同一场景优化并评估后直接报告 95%。

### 9.3 Big-M QA

Reviewer 应问：

- M 从哪里来？
- 是否可通过变量 bounds/物理边界推导？
- M 缩小 10%、扩大 10 倍会发生什么？
- 缩小是否改变理论可行域？
- 扩大是否造成 solver warning、gap 恶化或数值不稳定？

Big-M 应成为 evidence，而不是魔法常数。

### 9.4 CVaR QA

CVaR 不能只报告一个新 objective。

至少同时报告：

- risk-neutral expected value；
- risk-averse expected value；
- VaR / CVaR；
- tail samples/scenarios；
- `alpha`；
- CVaR weight；
- worst / selected quantiles；
- 方案变化；
- out-of-sample tail loss；
- solver convergence/gap。

mpi-sppy 文档还给出一个重要数值风险：shared VaR 变量 `eta` 的尺度可能和普通一阶段变量完全不同，导致 PH 的统一 rho 不合适。因此 Reviewer 还需检查 scaling / solver parameter 是否让算法假收敛或极慢。

### 9.5 DRO QA

DRO 要比 robust/chance 多检查一层：

- support set；
- moments / expectation set；
- scenario probability set；
- ambiguity radius/parameter；
- 每一项来自什么数据或理论；
- ambiguity set 是否过大导致极端保守；
- 是否进行 out-of-sample comparison；
- 与 plain stochastic / robust model 的增益是否真实。

不能因为“DRO 更高级”而默认选择它。

### 9.6 Regression / equivalence tests

mpi-sppy 当前 chance tests 给 `math_mode` 一个很好的 QA 模式：

- `alpha = 0` → 应退化为所有场景满足的 robust constraint；
- 不添加 chance constraint → 应回到 risk-neutral baseline；
- alpha 足够大 → risk constraint 应趋向 inactive；
- 小型实例 → 与 closed-form / brute force 结果一致；
- indexed constraints → 数量/索引必须一致。

建议把这类 **degenerate-case equivalence** 变成 optimization verifier 的固定项目。

### 9.7 多模型/竞争/critic/debate/scoring

本轮三个优化项目并不使用 LLM debate。

对 `math_mode` 更可靠的竞争机制应是：

```text
same deterministic model
same UQ evidence
same decision outputs

Nominal
vs Robust(Set)
vs Chance
vs CVaR
vs DRO (when justified)
```

Score Card 不应只按 objective 排序，而应包含：

```text
hard feasibility
out-of-sample violation
worst-case margin
tail loss
expected performance
robustness price
optimality gap
runtime
interpretability
evidence strength
```

文本 Reviewer 只负责解释这些真实结果和选择理由，不替代数值比较。

### 9.8 Hallucination 防护

风险优化领域最危险的 hallucination 不是虚构一篇论文，而是虚构数学保证。

必须禁止：

- solver `optimal` → 自动写成“robust optimal”；
- SAA scenario pass → 自动写成“95% 概率保证”；
- arbitrary uncertainty interval → 自动写成“置信区间”；
- CVaR 下降 → 自动写成“违约概率下降”；
- no observed violation → 自动写成“绝对安全”；
- DRO → 自动写成“最优且最鲁棒”。

这些都必须由 structured evidence gate 控制论文措辞。

---

## 10. 值得借鉴的设计

| 设计 | 来源 | 评级 | 对 math_mode 的迁移 |
|---|---|---|---|
| `robust_feasible` 与 `robust_optimal` 分开 | PyROS | **A 可直接借鉴** | 直接进入 Solver/Reviewer 状态机，限制论文强结论 |
| uncertainty set 是 executable object | PyROS | **A** | UQ Contract 编译出带 hash 的 set，而非 Markdown 描述 |
| master → separation → violation 回灌 | PyROS | **B 改造后采用** | 与 Falsification Layer 合并，形成决策—反证闭环 |
| robust constraint scope 可显式控制 | PyROS | **A** | `hard_for_all / nominal_only / chance / soft` 角色表 |
| support / expectation / probability 分层的 ambiguity set | RSOME | **A** | 建立 `Decision Risk Contract` 的 distribution semantics |
| ambiguity preview / 完整性检查 | RSOME | **A** | 求解前生成 risk contract preview，缺 evidence 不求解 |
| event-wise adaptive recourse | RSOME | **B** | 有多阶段题时引入 information-set / nonanticipativity contract |
| CVaR 与 chance 的数学结构分开 | mpi-sppy | **A** | Risk Planner 必须先选语义，再选 solver/并行策略 |
| chance constraint EF-only guard | mpi-sppy | **A** | tool capability 与 formulation compatibility 不匹配时 hard fail |
| 不替用户猜 indicator / Big-M | mpi-sppy | **A** | Big-M 和 risky constraint 必须成为建模证据 |
| `alpha=0` / no-CC 等价测试 | mpi-sppy | **A** | 建立风险模型 regression suite |
| MPI hub/spoke 大规模随机规划 | mpi-sppy | **C 可作对照实验** | 只有真实大场景题且单机瓶颈明显时再考虑 |
| 所有题统一上 DRO | 无 | **D 不建议采用** | 证据和赛时成本都不支持 |
| 所有不确定参数统一 ±10% 作为 robust set | 无 | **D** | 违反上一轮 UQ authority 规则 |
| 当前开发 main 的 chance API 作为生产强依赖 | mpi-sppy 当前开发版 | **D/暂不采用** | 设计文档仍 draft，先借鉴机制而不是锁死依赖 |

---

## 11. 存在的问题

### 11.1 Robust Optimization 可能过度保守

如果 uncertainty set 取值没有数据依据、边界过宽，robust solution 可能为了极不现实的 worst case 牺牲大量正常性能。

因此必须报告：

```text
Price of Robustness
= nominal objective loss / risk reduction
```

而不是把“目标更差”解释成稳健模型能力强。

### 11.2 uncertainty set 设计本身就是建模假设

Box / ellipsoid / budget / discrete scenario 并不是可互换的技术细节。

不同 set 会直接改变：

- 哪些方向允许同时极端；
- 是否表达相关性；
- worst-case realization；
- 保守程度；
- solver 难度。

因此它必须被 UQ evidence 约束。

### 11.3 SAA chance constraint 不是自动的真实世界概率保证

当前 mpi-sppy 实现是 sample-average approximation。

如果 scenario sample：

- 太少；
- 不独立；
- 不代表未来；
- 来自同一训练窗口；
- 手工挑选；

则 `sum p_s z_s >= 1-alpha` 只是在该场景集上成立。

必须独立 out-of-sample backtest。

### 11.4 Chance Constraint 只控制频率，不控制严重程度

两个策略都可能有 5% violation：

- A 的最坏损失是 1%；
- B 的最坏损失是灾难性 1000%。

chance constraint 自身不能区分。

这就是为什么 Risk Planner 必须根据题意在 chance / CVaR / hard robust constraint 间选择。

### 11.5 CVaR 并不等价于所有场景可行

CVaR 主要控制尾部损失，不自动保证每个 hard constraint 都满足。

安全/物理硬约束不能因为采用 CVaR 就软化。

### 11.6 Multistage CVaR 的 time consistency 边界

mpi-sppy 当前文档明确其 CVaR 是 root-stage、total cost 上的风险度量，并不是 nested/time-consistent multistage risk measure。

因此多阶段题中不能仅因为使用了 CVaR，就声称得到了严格的动态风险一致策略。

### 11.7 Big-M 是 chance constraint 的实际高风险点

Big-M 太小：

- 错误切掉合法可行解；
- 结果可能“看起来很稳”，实则模型被改坏。

Big-M 太大：

- 数值病态；
- relaxation 弱；
- MIP 变慢；
- gap/termination 质量下降。

它必须进入 audit。

### 11.8 PyROS 并非通用 MIP robust solver

当前 PyROS solver interface 明确面向 continuous variables。

如果赛题核心是整数调度/组合优化，不应强行把 PyROS 当统一 backend。

### 11.9 Solver license / availability

真实竞赛环境可能没有 BARON/Gurobi/CPLEX/Mosek 等商业 solver。

Risk Planner 必须先看：

- 开源 solver 是否够用；
- 全局 solver 是否存在；
- 时间预算；
- 许可证；

不能在 plan 里默认使用无法执行的 solver。

### 11.10 没有 LLM memory/checkpoint

本轮三个项目并不提供 Agent memory / conversation resume。

不能从“solver 有 internal iteration state”推断出“项目有 AI Agent checkpoint”。

应该继续使用 17:07 研究的 workflow checkpoint 体系，仅把 risk solver state 作为新的 payload。

---

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| deterministic baseline | 已强制 baseline / 可行性 / 指标复算 | 三者均从 deterministic/scenario model 出发 | **保持** |
| uncertainty source | 上轮建议 UQ Contract，当前正式代码尚未形成统一 schema | PyROS 要 uncertainty set；RSOME 要 support/ambiguity；mpi-sppy 要 scenarios | **改进**：把 UQ source 编译到 decision risk contract |
| robust counterpart | 当前规范要求鲁棒性，但无统一 robust solver contract | PyROS 直接支持 | **新增** adapter/gate，不强制全项目依赖 |
| worst-case separation | 当前 Falsification 是研究建议，未与优化闭环 | PyROS master/separation 回灌 | **新增** 决策—反例闭环 |
| robust certificate | 当前通常记录 solver/验证，但没有 `robust_feasible vs robust_optimal` 标准状态 | PyROS 明确区分 | **新增** |
| uncertainty set 类型 | 当前可在求解计划中描述 | PyROS 有 Box/Budget/Ellipsoid/Discrete 等 executable sets | **改进** 为 hashable executable contract |
| distribution ambiguity | 当前无统一结构 | RSOME support + expectation + probability ambiguity | **新增**，只在证据允许时启用 |
| recourse / information structure | 当前题目依赖和阶段可描述，但无统一 nonanticipativity schema | PyROS/RSOME/mpi-sppy 都有阶段/适应语义 | **新增** Decision Information Table |
| chance constraint | 当前可由用户/solver 手写，无统一 gate | mpi-sppy 当前 main 有 SAA transform | **新增** semantics + verifier；具体依赖暂不固定 |
| CVaR | 当前无统一风险层 | mpi-sppy 有 risk transform | **新增** risk adapter / experiment |
| Big-M audit | 当前可在代码审查中发现，但没有专门资产 | mpi-sppy 明确把 link/M 留给用户 | **新增** Big-M Auditor |
| out-of-sample decision backtest | 当前要求独立验证，但没有风险决策专门协议 | 本轮项目提供建模/部分 CI 能力但非完整 contest gate | **改进** 为独立 Risk Backtest Reviewer |
| solver compatibility | 当前 Phase 0 检查环境，但未针对风险结构选求解架构 | chance EF-only，CVaR 可 scenario decomposition | **新增** formulation-capability gate |
| regression equivalence | 当前已有独立验证思想 | mpi-sppy 真实测试 `alpha=0` / no-CC 等 | **新增** risk regression suite |
| result provenance | 当前强：结果索引、支撑材料、SHA | 三者不覆盖竞赛论文全链路 | **保持** math-mode 优势 |
| Figure QA | 当前 academic-figure-skill 很强 | 三项目不是绘图系统 | **保持**；只让它消费通过 risk gate 的 evidence |
| paper claim gate | 当前论文数字必须来自真实结果 | 三项目只提供 solver semantics | **改进**：将 solver/risk status 映射到允许的论文措辞 |
| LLM multi-agent | 当前 Codex/Claude workflow router | 三项目不是 LLM Agent | 不照搬；把数学机制作为 tool/skill 层 |

---

## 13. 对 math-mode 的具体启发

### P0 建议近期加入

#### P0-1：新增 `Decision Risk Contract`

建议未来设计：

```json
{
  "decision_id": "q2-plan-v3",
  "problem_contract_hash": "...",
  "uq_contract_hash": "...",
  "risk_semantics": "chance",
  "uncertain_quantities": ["demand", "travel_time"],
  "uncertainty_authority": "historical_holdout",
  "constraint_roles": {
    "capacity": "hard_for_all",
    "service_level": "chance_limited"
  },
  "risk_parameters": {
    "alpha": 0.05
  },
  "decision_stages": ["pre", "post-demand"],
  "nonanticipativity": "...",
  "solver_capability_required": ["MILP", "EF"],
  "validation_protocol_id": "risk-backtest-v1"
}
```

它应该放在：

```text
Problem Contract / UQ Contract
          ↓
Decision Risk Contract
          ↓
optimization candidate
```

影响模块：

- `求解计划.md`：增加 risk semantics；
- 未来实验账本：记录 risk candidate；
- checkpoint：绑定 risk contract hash；
- candidate manifest：保存 risk parameters；
- Reviewer：按 risk 类型选择 checker；
- Result Index：明确证书状态；
- Figure Plan：只画通过 gate 的 risk trade-off；
- Writer：限制“稳健/概率保证/尾部风险”措辞。

判断：**新增**。

#### P0-2：强制保留 Risk-Neutral Baseline

任何 robust/chance/CVaR/DRO 模型都必须与同一个 deterministic/scenario baseline 比较。

最低表：

```text
model
objective
hard feasibility
worst-case margin
in-sample violation
out-of-sample violation
CVaR / tail metric
runtime
optimality gap
```

原因：没有 baseline 就无法说明“为稳健性付出了什么代价、换来了什么”。

判断：**保持现有 baseline 规则并增强**。

#### P0-3：新增 `Robust Decision Evidence Pack`

建议机器产物至少包含：

```text
risk_contract.json
solver_run.json
scenario_manifest.json
uncertainty_set.json
worst_case_scenarios.csv
constraint_margin.csv
risk_metrics.json
out_of_sample_backtest.json
solver.log
artifact_hashes.json
```

判断：**新增**。

#### P0-4：新增 Robust Decision Promotion Gate

示意规则：

```text
if hard_constraint_violation:
    BLOCK
elif solver_status not acceptable:
    BLOCK
elif risk_contract_missing_authority:
    BLOCK
elif chance and big_m_unverified:
    BLOCK
elif backtest_failed:
    BLOCK
else:
    PROMOTABLE_WITH_STATUS
```

注意：promotion status 应保留语义，例如：

- `ROBUST_FEASIBLE`；
- `ROBUST_OPTIMAL_CERTIFIED`；
- `SAA_CHANCE_FEASIBLE_BACKTESTED`；
- `CVAR_RISK_AVERSE_VALIDATED`。

不能全部压成 `PASS`。

判断：**新增**。

#### P0-5：Big-M Auditor

对所有 chance/disjunctive model：

- 找出 M；
- 推导或引用 M 来源；
- 验证 tightness；
- 数值缩放检查；
- 保存测试。

判断：**新增**。

#### P0-6：样本外 Risk Backtest

优化场景与验证场景必须分离，尤其是 chance / CVaR / DRO。

建议：

```text
construction scenarios
validation scenarios
stress scenarios
```

三者有独立 manifest/hash。

如果数据量太少，应明确写“经验场景稳健性”，而不是伪造统计保证。

判断：**改进**现有独立验证。

### P1 值得实验

#### P1-1：Nominal vs Robust vs Chance vs CVaR 对照

对历史优化题选择 1–2 个适合不确定决策的问题，固定同一输入与同一 UQ evidence，只改变 decision risk semantics。

比较：

- objective loss；
- violation rate；
- tail loss；
- worst-case margin；
- runtime；
- feasibility；
- solution stability。

这能形成真正有论文价值的对照，而不是模型堆叠。

#### P1-2：Risk Parameter Sweep

例如：

- robust set radius；
- budget Γ；
- chance `alpha`；
- CVaR `alpha` / beta；
- DRO ambiguity radius。

输出 `performance-risk frontier`。

但参数扫描范围必须来自 UQ evidence 或明确作为 scenario study，不能反过来调出“最好看的曲线”。

#### P1-3：Degenerate Equivalence Regression Suite

至少实现：

```text
uncertainty radius = 0 → nominal
chance alpha = 0 → all sampled scenarios hard-satisfied
chance disabled → risk-neutral
CVaR weight = 0 → expected objective baseline
single scenario → deterministic equivalent
identical scenarios → expected / scenario solution consistency
```

这些测试非常适合赛前做 framework regression。

#### P1-4：Robustness Price / Tail-risk Price 自动报告

让 Writer 不再只拿最优值，而是自动读取：

```text
nominal performance
robust performance
absolute/relative performance sacrifice
violation reduction
tail-loss reduction
```

作为论文“模型改进是否值得”的核心证据。

### P2 长期考虑

#### P2-1：PyROS adapter

适合：

- 连续非线性模型；
- 有明确 uncertainty set；
- 本地有合适 NLP/global solver。

不是默认 backend。

#### P2-2：RSOME adapter

适合：

- 线性/锥可表示的 robust/DRO；
- distribution ambiguity 证据明确；
- 需要清晰 event/scenario adaptation。

#### P2-3：mpi-sppy backend

只有在：

- scenario 数量大；
- 单机 EF 明显成为瓶颈；
- MPI 环境已验证；
- 风险模型与 decomposition 兼容；

时才值得加入。

当前 chance constraint 开发实现不应立刻成为项目生产依赖。

### 不建议采用

1. **不建议**所有优化题默认 robust/DRO；
2. **不建议**没有证据时统一 ±5%/±10% 造 uncertainty set；
3. **不建议**把 SAA chance result 写成无条件真实概率保证；
4. **不建议**只看 in-sample scenarios；
5. **不建议**忽略 Big-M 来源；
6. **不建议**把 `robust_feasible` 写成“全局稳健最优”；
7. **不建议**为了并行而使用与风险结构不兼容的 decomposition；
8. **不建议**将“没有发生 violation”写成“无风险”；
9. **不建议**为了创新点机械加入 DRO；
10. **不建议**用 LLM debate 代替 solver certificate 和样本外回测。

总体判断：

- 当前求解规范的 baseline / feasibility / Pareto / scenario / robustness：**保持**；
- UQ 到决策之间的接口：**新增**；
- 独立验证：**改进**为 risk-specific backtest；
- Solver 状态：**改进**为 certificate-aware；
- academic-figure-skill：**保持**，不改图层职责；
- 强制引入某一个 robust software stack：**暂不采用**；
- “全问题统一鲁棒化”：**不采用**。

---

## 14. 可形成的新 Skill / Agent（只提设计，不创建）

### 14.1 `decision-risk-planner`

输入：Problem Contract + UQ Contract + deterministic model summary。

输出：

- risk semantics；
- constraint roles；
- decision stages；
- candidate risk formulations；
- solver capability requirements；
- required validation protocol。

### 14.2 `robust-optimization-verifier`

职责：

- 读 solver logs；
- 检查 uncertainty set；
- 重新计算 worst-case margins；
- 检查 termination semantics；
- 将 `robust feasible` / `robust optimal` 分开；
- 输出 machine-readable certificate。

### 14.3 `big-m-auditor`

职责：

- 找 M；
- 推导/校验 bounds；
- mutation test；
- numerical scaling；
- 输出 M evidence report。

### 14.4 `risk-backtest-reviewer`

职责：

- 独立 scenario/resample；
- 违约概率；
- tail loss；
- worst-case；
- strategy regret；
- 与 nominal / alternate risk policy 比较。

### 14.5 `decision-evidence-writer-guard`

不是新 Writer，而是 Writer 前的 guard：

```text
ROBUST_FEASIBLE
→ 允许："在所声明不确定集合内通过稳健可行性检查"

SAA_FEASIBLE only
→ 禁止："未来以 95% 概率保证"

ROBUST_OPTIMAL_CERTIFIED
→ 才允许更强最优性措辞，并注明求解/假设范围
```

以上均为设计建议，本轮不创建 Agent/Skill、不修改正式 workflow。

---

## 15. 与历史调研的去重检查

### 15.1 对象级去重

本轮三个对象此前均未作为独立研究对象进入 `research/INDEX.md`：

- `Pyomo/pyomo::PyROS`：新；
- `XiongPengNUS/rsome`：新；
- `Pyomo/mpi-sppy`：新。

虽然 21:04 的 ORPilot 研究可能在实现层使用优化建模工具，但当时主题是“自然语言 → typed optimization IR”，没有研究 PyROS 的 uncertainty set / separation / robust certificate，因此不属于重复。

### 15.2 机制级去重

| 历史轮次 | 已研究 | 本轮新增差异 |
|---|---|---|
| 15:06 Model Search | 如何寻找更好的模型候选 | 本轮固定模型后研究不确定条件下的决策策略 |
| 16:04 Reviewer | 如何验证结果 | 本轮产生 risk-aware decision evidence 与 certificate |
| 18:04 Canonical Promotion | 怎样防旧结果覆盖 | 本轮定义什么样的 risk result 才有资格 promotion |
| 19:07 Scheduler | 如何分配算力 | 本轮说明 risk formulation 会反过来限制可用并行架构 |
| 21:04 Problem Contract | 题面硬规则 | 本轮增加 risk semantics / recourse / probability constraint |
| 22:06 Falsification | 主动寻找失效场景 | PyROS-like separation 将最坏场景回灌到优化，形成闭环 |
| 23:04 UQ | 不确定性从哪里来、有多大 | 本轮决定“因此应该怎样做决策” |

### 15.3 本轮真正新增的机制集合

新增关键词：

```text
robust counterpart
uncertainty set compiler
master-separation loop
robust feasible vs robust optimal
constraint robustness scope
ambiguity set
support / expectation / probability set
recourse / nonanticipativity
chance constraint SAA
binary satisfaction indicator
Big-M audit
CVaR tail-risk objective
risk formulation compatibility
out-of-sample decision backtest
price of robustness
risk regression equivalence
```

这些关键词/机制没有在历史 INDEX 中被完整研究。

### 15.4 写入前重复检查结论

本轮不是把 23:04 的“UQ Contract”换个名字再写一遍。

真正新增链路是：

```text
UQ Evidence
    ↓
Decision Risk Semantics
    ↓
Executable Risk Formulation
    ↓
Solver Certificate
    ↓
Out-of-Sample Risk Backtest
    ↓
Canonical Decision
```

因此值得形成独立 research 记录。

---

## 16. 下一轮推荐方向

推荐下一轮研究：

**Numerical Reliability / Solver Certificate Agent：数值尺度、容差、KKT/duality、optimality gap、solver status、可行性残差与跨 solver 复算。**

原因：

前几轮已经逐渐建立：

```text
Problem Contract
→ Model Search
→ Real Execution
→ Falsification
→ UQ
→ Risk-aware Decision
→ Reviewer
→ Canonical Result
```

但还有一个贯穿所有优化/仿真的薄弱点：

> solver 说“success/optimal”，是否真的意味着数学上和数值上可信？

下一轮可以重点研究：

- primal/dual feasibility tolerance；
- KKT residual；
- MIP optimality gap；
- infeasible/unbounded diagnosis；
- scaling / conditioning；
- numerical warnings；
- local optimum vs global optimum；
- independent solver / formulation cross-check；
- deterministic small-case oracle；
- solver version / options / tolerance provenance；
- 如何把 `OPTIMAL / LOCALLY_OPTIMAL / FEASIBLE / TIME_LIMIT / NUMERICAL_ERROR` 编译成论文允许的结论等级。

优先级仍是：

```text
建模质量
> 结果真实性
> 验证能力
> 创新性
> 赛时效率
> 论文质量
> 自动化程度
```

---

## 17. Sources

### A. 已实际阅读源码 / 官方仓库文档

#### math_mode 基线

1. `shaxiaoguang123/math_mode` README
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/README.md
2. `AGENTS.md`
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/AGENTS.md
3. `CLAUDE.md`
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/CLAUDE.md
4. academic-figure-skill
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/.agents/skills/academic-figure-skill/SKILL.md
5. 当前研究索引
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/research/INDEX.md
6. 上一轮 UQ 报告
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/research/2026-09-08/2026-09-08_23-04_uncertainty-calibration-agent.md
7. Counterexample / Falsification 报告
   - https://github.com/shaxiaoguang123/math_mode/blob/a179b491e1267846762f76a7bb66bca3b4b6d566/research/2026-09-08/2026-09-08_22-06_counterexample-falsification.md

#### Pyomo / PyROS

8. PyROS methodology overview（本轮固定 commit）
   - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/doc/OnlineDocs/explanation/solvers/pyros/overview.rst
9. PyROS solver interface
   - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/doc/OnlineDocs/explanation/solvers/pyros/solver_interface.rst
10. PyROS uncertainty sets
    - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/pyomo/contrib/pyros/uncertainty_sets.py
11. PyROS solver core
    - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/pyomo/contrib/pyros/pyros.py
12. PyROS algorithm methods
    - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/pyomo/contrib/pyros/pyros_algorithm_methods.py
13. PyROS utilities / termination semantics
    - https://github.com/Pyomo/pyomo/blob/e099f6463abd3b17b3231abf108b0a46e9640d1a/pyomo/contrib/pyros/util.py
14. Pyomo 6.10.1 Release
    - https://github.com/Pyomo/pyomo/releases/tag/6.10.1

#### RSOME

15. RSOME README
    - https://github.com/XiongPengNUS/rsome/blob/1a0cf887efaa122e941651f8a40cc20d46f0dbf5/README.md
16. RSOME DRO user guide
    - https://github.com/XiongPengNUS/rsome/blob/1a0cf887efaa122e941651f8a40cc20d46f0dbf5/docs/dro_rsome.md
17. RSOME DRO implementation
    - https://github.com/XiongPengNUS/rsome/blob/1a0cf887efaa122e941651f8a40cc20d46f0dbf5/rsome/dro.py

#### mpi-sppy

18. mpi-sppy README
    - https://github.com/Pyomo/mpi-sppy/blob/fd920757af27d6494c92be6e2cf618f5f4ef08e5/README.md
19. 当前 main chance constraint 实现
    - https://github.com/Pyomo/mpi-sppy/blob/fd920757af27d6494c92be6e2cf618f5f4ef08e5/mpisppy/utils/chance_constraint.py
20. chance constraint design（注意：文档自身仍标记 draft）
    - https://github.com/Pyomo/mpi-sppy/blob/fd920757af27d6494c92be6e2cf618f5f4ef08e5/doc/designs/chance_constraint_design.md
21. chance constraint solver tests
    - https://github.com/Pyomo/mpi-sppy/blob/fd920757af27d6494c92be6e2cf618f5f4ef08e5/mpisppy/tests/test_chance_constraint.py
22. CVaR risk management 文档源码
    - https://github.com/Pyomo/mpi-sppy/blob/fd920757af27d6494c92be6e2cf618f5f4ef08e5/doc/src/risk_management.rst
23. mpi-sppy 0.14.0 Release
    - https://github.com/Pyomo/mpi-sppy/releases/tag/0.14.0

### B. 已阅读官方论文 / 官方项目页面

24. Sherman, Isenberg, Siirola, Gounaris, **PyROS: The Pyomo Robust Optimization Solver**, Optimization Online，2026-06-18
    - https://optimization-online.org/2026/06/pyros-the-pyomo-robust-optimization-solver/
25. PyROS current docs
    - https://pyomo.readthedocs.io/en/stable/explanation/solvers/pyros/index.html
26. Chen & Xiong, **RSOME in Python: An Open-Source Package for Robust Stochastic Optimization Made Easy**, INFORMS Journal on Computing 35(4), 2023, DOI `10.1287/ijoc.2023.1291`
    - https://pubsonline.informs.org/doi/10.1287/ijoc.2023.1291
27. Chen, Sim, Xiong, **Robust Stochastic Optimization Made Easy with RSOME**, Management Science 66(8), 2020, DOI `10.1287/mnsc.2020.3603`
    - https://pubsonline.informs.org/doi/10.1287/mnsc.2020.3603
28. mpi-sppy documentation — Chance Constraints
    - https://mpi-sppy.readthedocs.io/en/latest/chance_constraints.html
29. mpi-sppy documentation — Risk Management (CVaR)
    - https://mpi-sppy.readthedocs.io/en/latest/risk_management.html
30. Knueven et al., **A Parallel Hub-and-Spoke System for Large-Scale Scenario-Based Optimization Under Uncertainty**, Mathematical Programming Computation 15, 2023
    - https://link.springer.com/article/10.1007/s12532-023-00247-3

### C. 仅作为背景、没有被当作已验证实现的说明

本轮没有用博客、知乎、Reddit 或搜索摘要替代核心结论。所有关键工程判断均基于上面的 GitHub 源码/仓库文档或官方论文页面。

### 本轮验证边界声明

- 已确认：相关源码、文档、测试和 repository metadata 在上述固定 commit/页面中真实存在；
- 已确认：mpi-sppy 当前 main 的 chance constraint 有实现文件和真实 solver test 代码；
- 未执行：本轮没有在本地安装 PyROS/RSOME/mpi-sppy，也没有对具体华为杯题目跑一次 robust/chance/CVaR/DRO 求解；
- 因此本报告不声称这些库在当前机器/某个比赛模型上已经实际跑通；
- mpi-sppy chance constraint 的 design 文档仍标记 draft，且最新稳定 Release 为 0.14.0，本报告不将当前 main 开发功能描述为稳定 release guarantee。
