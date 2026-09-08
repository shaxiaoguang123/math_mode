# MathModel Agent Research

## 1 本轮研究主题

**Numerical Reliability / Solver Certificate Agent：把“solver 返回 optimal/success”拆成可审计的数值证书、最优性语义与独立复算门禁。**

本轮聚焦一个对数学建模竞赛结果真实性非常关键、但经常被工作流忽略的问题：

> 优化器、非线性求解器或 MIP 求解器显示 `optimal`、`success`、`solved` 时，`math_mode` 到底允许在论文中写什么？这个状态是否真的意味着约束满足、目标正确、数值稳定、整数可行、达到全局最优，还是只表示“在该求解器自己的停止准则和容差下停止”？

本轮不再研究新的优化建模范式，而是研究**求解器输出本身的可信度**，形成从原始 solver status 到可进入论文的 claim 之间的证据链。

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的高价值对象：

1. `ERGO-Code/HiGHS`：LP/QP/MIP 求解中的 primal/dual feasibility、KKT residual、integrality violation、MIP gap，以及对 solver 自报 optimal 的再次数值判定；
2. `coin-or/Ipopt`：非线性优化中的 desired convergence、acceptable convergence、primal/dual/complementarity residual 和终止状态语义；
3. `scipopt/scip`：MIP/MINLP 中 solution feasibility checking、浮点容差与 exact/rational solution API，作为关键结果的更高强度核验路线。

本轮核心结论是：

> `math_mode` 应新增一层 **Solver Certificate Layer**。Solver 的原始状态只能是证据输入，不能直接成为论文事实。每次高价值优化求解都应保存 solver/version/options/tolerances、原始 termination、primal/dual/integrality/KKT 残差、bound/gap、原单位独立约束复算、模型/结果/log hash；再由一个确定性的 Status Normalizer 把它映射成 `PROVEN_GLOBAL / OPTIMAL_WITHIN_TOL / LOCAL_STATIONARY / ACCEPTABLE_ONLY / FEASIBLE_ONLY / LIMIT_REACHED / NUMERICALLY_SUSPECT / UNKNOWN` 等统一语义。只有通过 Numerical Reliability Gate 的证书，才允许 Candidate Promotion 和 Writer 使用相应强度的结论。

建议目标链路：

```text
Problem Contract + Candidate Model
              ↓
          Solver Run
              ↓
       Raw Solver Output
 status / objective / bound / gap / iterations / log
              ↓
        Solver Certificate
 solver version + options + tolerances + residuals
              ↓
 Independent Original-unit Recheck
 objective / constraints / integrality / domain / units
              ↓
    Numerical Reliability Gate
              ↓
 Ambiguous/high-stakes?
      ↓ yes              ↓ no
 cross-solver /          normalized
 multistart / exact       certificate
 verification                ↓
      └──────────────→ Candidate Promotion
                          ↓
                    Result Index / Writer
```

---

## 2 为什么选择这个主题（说明与历史调研差异）

### 2.1 基线读取与去重

本轮开始前重新读取了：

- 根目录 `README.md`；
- `AGENTS.md`；
- `CLAUDE.md`；
- `华为杯_求解规范/华为杯_求解规范.md`；
- `.agents/skills/` 目录及当前唯一项目级 `academic-figure-skill/SKILL.md`；
- `research/INDEX.md`；
- 最近一轮 `2026-09-09_00-05_robust-decision-under-uncertainty.md`；
- 当前远程 `main` HEAD 与 base tree。

截至本轮，历史调研已经覆盖：

- evidence-first 科研 Agent；
- 模型搜索树 / MCTS / 并行实验；
- Reviewer / Judge 校准；
- Checkpoint / Resume；
- Artifact Ownership / canonical promotion；
- Resource Scheduler / pruning；
- Citation / External Evidence Provenance；
- Problem Contract / Proof Obligations；
- Counterexample / Falsification；
- UQ / Calibration；
- Robust / Chance / CVaR / DRO 决策。

本轮没有重访这些已有机制。本轮回答的是一个更底层的问题：**同一个数学模型已经构造完、已经真实调用 solver 之后，solver 结果本身是否足够可信。**

### 2.2 与上一轮 Robust Decision 的区别

上一轮研究：

- uncertainty set / probability / ambiguity set；
- robust / chance / CVaR / DRO；
- out-of-sample risk backtest；
- robust feasible vs robust optimal。

本轮不改变风险语义，而研究：

- solver 的 `optimal` 是什么含义；
- tolerance 到底是多少；
- primal/dual/KKT/integrality violation 是否真的满足；
- MIP gap 和 bound 是否支持“全局最优”的强表述；
- NLP 的局部收敛是否被误写成全局最优；
- scaling / conditioning 是否让相对残差掩盖大绝对误差；
- time limit / acceptable level / feasible point 是否被错误当成 optimal；
- 是否需要第二求解器、多初值或 exact verification。

因此本轮是**结果真实性层**，不是优化策略层。

### 2.3 当前 math_mode 已经有什么

当前仓库已经有很好的基础：

- 题面硬约束优先；
- Baseline → 主模型 → 改进模型 → 独立验证；
- `求解/结果索引.md` 作为论文事实索引；
- 虚拟环境与 `requirements.txt`；
- 支撑材料清单、实际运行记录和 SHA-256；
- Evidence Matrix 要覆盖误差、约束、独立验证、鲁棒性和反证；
- 当前规范明确要求真实计算落盘后才能绘图和写论文；
- 前几轮 research 已经设计 Validation Contract、Candidate Artifact Contract、canonical promotion、Problem Contract、Counterexample Archive 和 Robust Decision Evidence Pack。

但基线搜索与文件读取没有发现当前正式规范中已经存在以下统一机器层：

- `solver_certificate.schema.json`；
- solver status 的跨求解器统一语义；
- solver tolerance 快照；
- primal/dual/KKT/integrality residual 的统一落盘；
- local/global optimum claim capability；
- 原单位独立约束复算报告；
- conditioning / scaling 风险状态；
- cross-solver disagreement 状态；
- solver log hash 与 certificate hash；
- “什么证书允许 Writer 写什么话”的确定性映射。

因此本轮不是重复已有“要验证结果”的原则，而是把它推进到**求解器证书协议和 claim gate**。

---

## 3 搜索范围与关键词

本轮属于 P1 `optimization / simulation / verification / reproducible research`，直接服务 P0 数学建模结果真实性。

重点关键词包括：

- solver certificate optimality numerical reliability
- LP MIP primal dual feasibility tolerance
- KKT residual complementarity optimality tolerance
- MIP gap primal bound dual bound integrality violation
- solver optimal status numerical accuracy
- absolute vs relative residual scaling conditioning
- nonlinear optimizer acceptable convergence local optimum
- Ipopt acceptable_tol constr_viol_tol dual_inf_tol
- HiGHS KKT tolerance residual infeasibility
- SCIP feasibility tolerance exact solution rational
- independent solution checker optimization
- cross solver validation optimization result
- ill-conditioned LP MIP solver verification

筛选标准：

1. 必须是真实数值优化器或求解器框架；
2. 必须有源码级 termination / tolerance / residual / solution verification 信息；
3. 优先能暴露“solver 自报成功但证据强度不同”的语义；
4. 优先有 machine-readable information，而不只打印日志；
5. 不研究普通 Agent orchestration；
6. 不把求解器功能宣传页当作已验证代码行为。

本轮没有实际在本地安装并运行这 3 个 solver；结论来自其官方 GitHub 仓库、源码、文档和 release 信息。凡涉及“实际运行效果”的内容均只作为待 `math_mode` 后续实验验证的建议，不声称本轮已经跑过 benchmark。

---

## 4 新发现项目（名称、Repository、Stars 如可得、最近更新时间、目标、核心能力）

### 4.1 HiGHS

- 名称：HiGHS
- Repository：https://github.com/ERGO-Code/HiGHS
- 本轮固定读取 commit：`73cac48c5340d775a477087198611862559be250`
- Stars：约 1,825（本轮 GitHub metadata）
- Repository `updated_at`：2026-09-07
- Repository `pushed_at`：2026-09-08
- 最新正式 Release：`v1.15.1`，2026-07-02
- 目标：高性能 LP、MIP、QP 求解。
- 本轮核心价值：其代码和官方 KKT 文档把 solver 的“optimal”拆成 primal feasibility、dual feasibility、primal/dual equation residual、complementarity / objective error、integrality violation、MIP bound/gap 等具体数值证据。

本轮实际阅读源码/文档：

- `docs/src/guide/kkt.md`
- `highs/lp_data/HighsInfo.h`
- GitHub release / repository metadata

### 4.2 Ipopt

- 名称：Ipopt — Interior Point Optimizer
- Repository：https://github.com/coin-or/Ipopt
- 本轮固定读取 commit：`1e71ba4eeef0514549587448123ea6fdcb2b0ccd`
- Stars：约 1,781
- Repository `updated_at`：2026-09-08
- Repository `pushed_at`：2026-08-29
- 当前默认维护分支：`stable/3.14`
- 最新 Release：`3.14.20`，2026-08-27
- 目标：大规模连续非线性优化。
- 本轮核心价值：源码明确区分“desired convergence”和“acceptable convergence”，并把 dual infeasibility、constraint violation、complementarity、总体 optimality error、时间/迭代限制映射成不同退出状态。

本轮实际阅读源码/文档：

- `src/Algorithm/IpOptErrorConvCheck.cpp`
- `src/Interfaces/IpReturnCodes_inc.h`
- release 3.14.20 元数据

### 4.3 SCIP

- 名称：SCIP — Solving Constraint Integer Programs
- Repository：https://github.com/scipopt/scip
- 本轮固定读取 commit：`92c7a7639d63d7cbe95db334142984926c176c40`
- Stars：约 649
- Repository `updated_at`：2026-09-08
- Repository `pushed_at`：2026-09-07
- 最新 Release：`v10.0.3`，2026-07-06
- 目标：MIP / MINLP / constraint integer programming。
- 本轮核心价值：除了普通浮点 solution API，源码还存在 exact/rational solution 路线，如 `SCIPsetSolValExact`、`SCIPgetSolValExact`、`SCIPgetSolOrigObjExact`、`SCIPmakeSolExact`、`SCIPretransformSolExact`；同时存在 solution checking / feasibility tolerance 体系。

本轮实际阅读源码/文档：

- `src/scip/scip_sol.h`
- `src/scip/set.c` 与 numerical tolerance 相关搜索
- GitHub repository/release metadata

---

## 5 深入架构分析

### 5.1 HiGHS：把“最优”拆成可查询的数值诊断

`HighsInfoStruct` 的设计对 `math_mode` 最有直接参考价值。它不是只返回：

```text
status = OPTIMAL
objective = 123.45
```

而是同时暴露：

- `primal_solution_status`
- `dual_solution_status`
- `objective_function_value`
- `mip_dual_bound`
- `mip_gap`
- `max_integrality_violation`
- `num_primal_infeasibilities`
- `max_primal_infeasibility`
- `sum_primal_infeasibilities`
- `num_dual_infeasibilities`
- `max_dual_infeasibility`
- primal/dual residual error
- relative primal/dual residual error
- complementarity violation
- primal-dual objective error
- iteration/node counts

这说明高质量 Solver Adapter 的产物应当是一个**证书对象**，不是单一状态字符串。

### 5.2 HiGHS：absolute 与 relative tolerance 不能混为一谈

HiGHS 官方 KKT 文档给出了非常重要的工程警告：

- 连续优化的精确可行性/最优性条件在浮点计算中只能在 tolerance 内满足；
- 不同算法可能使用 absolute 或 relative stopping criterion；
- relative measure 可能因为 RHS 或 cost vector 中非常大的、但实际对解不敏感的分量而被“放宽”；
- 因此某底层算法认为“optimal”的点，按更统一的绝对/相对数值标准重新检查后，HiGHS 甚至可能把状态降级为 `unknown`。

这对数学建模竞赛尤其重要。大量题目存在：

- 千、万、亿不同数量级同时出现；
- Big-M；
- 距离 m 与 mm、时间 s 与 h 混用；
- 目标值很大而约束误差的工程容忍度很小；
- 归一化后求解、反归一化后写论文。

因此 `math_mode` 不能只保存“solver tolerance=1e-7”，还要知道这个 tolerance 是针对什么量、absolute 还是 relative，并在**原始物理单位**重新检查题面硬约束。

### 5.3 Ipopt：`Solve_Succeeded` 与 `Solved_To_Acceptable_Level` 是不同证据等级

Ipopt 源码的 `OptimalityErrorConvergenceCheck` 显式存在两层终止：

**Desired level** 需要同时满足：

- overall optimality error；
- unscaled dual infeasibility；
- unscaled constraint violation；
- unscaled complementarity。

**Acceptable level** 则允许在无法达到 desired tolerance 时，连续若干迭代达到较宽松的 acceptable 条件后提前结束。

对应 return code 又明确区分：

- `Solve_Succeeded`
- `Solved_To_Acceptable_Level`
- `Infeasible_Problem_Detected`
- `Search_Direction_Becomes_Too_Small`
- `Diverging_Iterates`
- `Feasible_Point_Found`
- `Maximum_Iterations_Exceeded`
- `Maximum_CpuTime_Exceeded`
- `Maximum_WallTime_Exceeded`
- 以及 restoration / computation / invalid-number 等失败状态。

因此适配器如果写成：

```python
success = status in {0, 1}
```

然后 Writer 看到 `success=True` 就写“模型求得最优解”，会丢失最重要的语义。

### 5.4 Ipopt：NLP 的“求解成功”不能自动提升为全局最优

Ipopt 是连续非线性局部优化器。即便达到其 desired convergence，也主要说明当前点满足相应的一阶/KKT 收敛准则到设定容差，并不自动构成一般非凸问题的全局最优证明。

因此 `math_mode` 至少要区分：

```text
LP/QP convex + valid certificate
MIP + global bound/gap
convex NLP
nonconvex NLP local solver
MINLP global/local solver
heuristic/metaheuristic
```

“solver 返回 optimal”必须结合**模型类别 + solver 能力 + certificate**解释。

### 5.5 SCIP：高风险结果可以有更强的 exact verification 路径

SCIP 源码暴露了 float solution 与 exact/rational solution API 的并行设计。这带来一个很重要的工程启发：

> 常规赛时不需要把所有模型都 exact solve；但对小规模、关键、边界敏感、求解器之间发生分歧的 MILP/LP，可增加一个“更强验证层”，而不是无限把浮点 tolerance 调小。

这比全局强制 `1e-12` tolerance 更合理，因为：

- 极端 tolerance 会显著增加运行时间；
- ill-conditioned 模型并不会因为 tolerance 数字更小就自动变好；
- exact verification 应是一种升级策略，而不是默认路径。

### 5.6 对 math_mode 的建议分层

建议 Solver Certificate Layer 至少分 4 层：

```text
L0 Raw Status
solver 原始退出码、日志、版本、options

L1 Numeric Certificate
objective / bound / gap / primal / dual / KKT / integrality / tolerance

L2 Independent Recheck
用独立代码在原单位重新计算目标和题面约束

L3 Claim Capability
允许 Writer 使用的最强结论语义
```

其中 L2 不能由 solver 自己的状态替代。

---

## 6 Agent / Skill 设计

本轮不创建 Agent/Skill，只提出设计。

### 6.1 `solver-certificate-agent`

职责：

- 读取 candidate model、Problem Contract 和 solver raw output；
- 解析 solver name/version/options；
- 保存 tolerance 与 termination reason；
- 从 solver API 提取 residual、bound、gap、integrality 等证据；
- 调用独立 checker 在原单位复算；
- 生成机器可读 `solver_certificate.json`；
- 输出统一 status semantics；
- 不负责选择模型，不负责写论文。

推荐字段：

```json
{
  "certificate_id": "...",
  "candidate_id": "...",
  "contract_hash": "...",
  "model_hash": "...",
  "solution_hash": "...",
  "solver": {
    "name": "...",
    "version": "...",
    "build_or_commit": "...",
    "backend": "...",
    "threads": 1,
    "seed": null
  },
  "model_class": "LP|QP|MIP|NLP|MINLP|HEURISTIC",
  "termination": {
    "raw_code": "...",
    "raw_message": "...",
    "normalized": "..."
  },
  "tolerances": {},
  "objective": {
    "solver_value": null,
    "independent_value": null,
    "abs_diff": null,
    "rel_diff": null
  },
  "bounds": {
    "primal_bound": null,
    "dual_bound": null,
    "absolute_gap": null,
    "relative_gap": null
  },
  "residuals": {
    "max_primal_violation": null,
    "max_dual_violation": null,
    "max_integrality_violation": null,
    "stationarity": null,
    "complementarity": null,
    "kkt": null
  },
  "scaling": {},
  "independent_recheck": {},
  "cross_solver": {},
  "claim_capability": "...",
  "promotion_status": "PASS|WARN|BLOCK"
}
```

### 6.2 `status-normalizer`

这是确定性 Skill/Library，比 LLM Agent 更合适。

示例统一状态：

- `PROVEN_GLOBAL`
- `OPTIMAL_WITHIN_TOL`
- `LOCAL_STATIONARY`
- `ACCEPTABLE_ONLY`
- `FEASIBLE_ONLY`
- `LIMIT_REACHED_WITH_INCUMBENT`
- `INFEASIBLE_CERTIFIED`
- `INFEASIBLE_SUSPECT`
- `NUMERICALLY_SUSPECT`
- `UNKNOWN`
- `FAILED`

它需要 solver-specific adapter，而不是让 LLM 根据日志自由总结。

### 6.3 `independent-solution-checker`

职责：

- 不调用原 solver 的“check”结果作为唯一依据；
- 读取最终变量值；
- 在原始物理单位重新计算：
  - 目标函数；
  - equality residual；
  - inequality margin；
  - 整数性；
  - domain；
  - 守恒；
  - 题面特殊约束；
- 对照 Problem Contract tolerance。

这可以直接接入 21:04 的 Proof Obligation 体系。

### 6.4 `solver-claim-compiler`

目的不是生成文风，而是限制事实强度。

例如：

| certificate | Writer 最强允许表述 |
|---|---|
| MIP + valid global bound + gap within contract | “在设定最优性容差内得到全局最优解” |
| MIP time limit + feasible incumbent | “在给定时间预算内得到当前最好可行解” |
| Ipopt desired convergence on nonconvex NLP | “获得满足设定一阶收敛条件的局部解” |
| Ipopt acceptable level | “获得可接受精度候选解，经独立约束复算后用于比较” |
| feasible only | “得到可行方案” |
| unknown / numerical suspect | 禁止写“最优/稳定/收敛可靠” |

---

## 7 Workflow

### 7.1 推荐工作流

```text
Candidate ready
    ↓
Detect model class
    ↓
Select solver adapter
    ↓
Run solver with explicit options
    ↓
Persist raw log + solution
    ↓
Extract solver-native certificate
    ↓
Independent objective/constraint recompute
    ↓
Check physical-unit tolerances
    ↓
Check status semantics
    ↓
Numeric warning?
 ┌──┴─────────────┐
 yes              no
 ↓                 ↓
scaling check      certificate PASS
multi-start             ↓
cross-solver       promotion gate
exact verify            ↓
 ↓                 result index
re-evaluate             ↓
 └──────────────→ Writer claim compiler
```

### 7.2 与 Candidate Promotion 的关系

18:04 已提出 candidate 不直接写 canonical result。本轮增加：

```text
Validation PASS
并不等于
Numerical Certificate PASS
```

一个 candidate 必须同时满足：

1. Problem Contract hard gate；
2. 独立算法/模型验证；
3. Solver Certificate Gate；
4. 若适用，UQ / Risk Gate；
5. 没有 unresolved hard counterexample；

才允许 promote。

### 7.3 Checkpoint / Resume

Solver Certificate 本身必须是 immutable artifact，并绑定：

- `model_hash`
- `input_hashes`
- `solver_version`
- `solver_options_hash`
- `environment_hash`
- `solution_hash`
- `checker_version`
- `contract_hash`

任一关键上游变化后，certificate 自动 `STALE`，不能在 resume 时沿用旧“optimal”判断。

### 7.4 Task state

建议 solver task 至少区分：

```text
QUEUED
RUNNING
SOLVED_RAW
CERTIFICATE_EXTRACTED
INDEPENDENT_CHECKED
NUMERIC_WARNING
CERTIFIED
BLOCKED
STALE
```

不能把 `solver process exit code = 0` 直接映射为 `CERTIFIED`。

---

## 8 Code Execution / Tools

### 8.1 本轮对象是否真实执行代码

三个对象都是实际数值求解器，不是只生成文本的 Agent：

- HiGHS：原生 C++ LP/MIP/QP solver，提供 Python/Julia 等接口生态；
- Ipopt：C++ 连续 NLP solver；
- SCIP：C 求解器框架，处理 MIP/MINLP/constraint integer programming。

本轮**没有**在 `math_mode` 中安装或运行它们，因此未验证本机环境的 solver 可用性、速度或与现有 `cvxpy/Pyomo` wrapper 的兼容性。

### 8.2 Python / MATLAB / Julia / Jupyter / Docker / sandbox

本轮重点不是沙箱架构。对 `math_mode` 而言更适合：

- Python 统一 orchestration；
- solver 可以经 `scipy.optimize`、`cvxpy`、`pyomo`、原生 Python binding 等接入；
- MATLAB/Julia 只有赛题本身或现有代码需要时才接；
- 不应为了“Solver Certificate Agent”强制 Docker；
- 可复现性依赖版本、options、日志、模型和结果 hash，比容器本身更关键。

### 8.3 真实运行时必须捕获的工具数据

建议每次优化运行至少持久化：

- command / API call configuration；
- solver version；
- solver options；
- wall time / CPU time；
- thread count；
- seed（如适用）；
- node / iteration count；
- presolve/scaling 状态（若 API 可得）；
- raw solver log；
- raw solution；
- solver-native info object；
- independent checker report。

---

## 9 QA / Reviewer / Verification

### 9.1 HiGHS 给出的启发：重新判断 solver 的“optimal”

HiGHS 的 KKT 文档明确说明，在某些无 basis 的算法中，内部 relative termination 可能给出表面上的 optimal，而统一重新计算后的绝对/相对误差可能暴露问题，最终状态甚至可能被降级为 unknown。

这意味着 `math_mode` 的 Reviewer 不应问：

> “solver 是否显示 optimal？”

而应问：

> “在题目原始单位和我们的 Problem Contract tolerance 下，这个 solution 是否真的满足约束、整数性、目标复算和相应最优性证据？”

### 9.2 Ipopt 给出的启发：终止状态必须保真

必须保留 `Solve_Succeeded` 与 `Solved_To_Acceptable_Level` 的差异。

`acceptable` 不是失败，但也不应被无损归并为 `optimal`。

建议：

- `Solve_Succeeded`：进入正常 residual gate；
- `Solved_To_Acceptable_Level`：默认 WARN，必须独立复算，并优先做重缩放/多初值/替代 solver；
- `Feasible_Point_Found`：仅允许“可行”；
- time/iteration limit：若存在 incumbent，允许保存但不能写最优；
- diverging / invalid number：BLOCK。

### 9.3 MIP Gap 的正确定位

MIP 的“最优”证据与连续 NLP 不同：

- incumbent 是当前可行上界/下界一侧；
- global bound 是另一侧；
- gap 表示二者距离；
- gap within contract 才能支持“在指定容差下全局最优”的表述；
- time limit 下即使 incumbent 很好，也不能把“当前最好可行解”提升成“最优解”。

对于赛题，如果题面不要求精确最优，但时间有限，可以接受非零 gap；关键是**论文必须按证书如实表述**。

### 9.4 Scaling / Conditioning Gate

建议出现以下信号时触发 WARN：

- coefficient magnitude 跨度极大；
- Big-M 远大于实际可行量级；
- 原单位 residual 与 scaled residual 结论不一致；
- 同一模型稍微缩放后 objective/feasibility 大幅变化；
- solver 报 numerical issue / unknown；
- 两个成熟 solver 对相同 LP/MIP 给出不同可行性或 objective。

此时优先：

1. 检查单位与建模；
2. 重新缩放；
3. 检查 Big-M；
4. 独立复算；
5. 必要时 cross-solver；
6. 小型关键模型再考虑 exact verification。

不推荐第一反应就是把所有 tolerance 改为 `1e-12`。

### 9.5 Cross-solver 验证

Cross-solver 不应成为所有实验的默认成本，而应是高风险升级策略。

优先触发条件：

- final canonical candidate；
- solver 状态 ambiguous；
- 数值尺度差；
- MIP gap 接近论文关键结论阈值；
- 不同初值产生显著不同 NLP 解；
- 结果处在题面硬约束边界；
- Reviewer 或 Counterexample Agent 指出 numerical inconsistency。

### 9.6 Hallucination 防护

Writer/LLM 最容易产生的错误是把求解器术语“升级翻译”：

- `feasible` → “最优”；
- `acceptable` → “成功收敛到最优”；
- `local optimum` → “全局最优”；
- `gap=1%` → “精确最优”；
- `time limit` → “算法收敛”；
- `no counterexample found` → “证明正确”。

Solver Claim Compiler 应禁止这些升级。

---

## 10 值得借鉴的设计

### A 可直接借鉴

**A1. HiGHS 式 machine-readable 数值诊断。**

直接借鉴其“status 之外还暴露 primal/dual/integrality/residual/complementarity/gap”的思想。

判断：**新增**。

**A2. Ipopt 原始 termination taxonomy 保真。**

不把 acceptable、feasible、time limit、max iterations、diverging 合成 success/fail 二值。

判断：**改进** solver wrapper。

**A3. 原单位 independent recheck。**

与现有独立验证原则高度一致，可直接落入 Validation Contract / Proof Obligation。

判断：**改进**。

### B 改造后采用

**B1. Cross-solver verification。**

仅针对 final/high-risk/ambiguous candidate，避免赛时过度耗时。

判断：**新增但按条件触发**。

**B2. Exact/rational verification。**

仅用于小型关键 LP/MILP 或 solver disagreement，不作为所有模型默认路线。

判断：**长期按需新增**。

**B3. Solver-specific adapter。**

需要把 HiGHS / Ipopt / SCIP / CVXPY / Pyomo 各自状态统一成 math_mode contract，但必须保留 raw code。

判断：**新增**。

### C 可作为对照实验

**C1. tolerance sweep。**

比较默认、较松、较严 tolerance 对 objective、residual、runtime 的影响。

**C2. scaling mutation。**

对同一个等价模型做单位/尺度变化，观察 solver status 和独立 residual 是否保持一致。

**C3. cross-solver。**

LP/MIP 可做 HiGHS vs SCIP；NLP 可做多初值 Ipopt，并在可用时与其他成熟 NLP solver 对照。

### D 不建议采用

**D1. “solver 显示 optimal 就直接入论文”。**

不建议。

**D2. 所有模型统一强制极端 tolerance。**

不建议。

**D3. 所有模型都 exact solve。**

赛时成本过高，不建议。

**D4. 用 LLM 自由解释 solver log 来决定 optimality。**

不建议。核心状态映射必须 deterministic。

---

## 11 存在的问题

### 11.1 不同 solver 的 certificate 字段并不统一

LP/MIP、NLP、MINLP 的证据结构不同：

- LP/QP：primal/dual/KKT；
- MIP：incumbent/bound/gap/integrality；
- NLP：KKT/constraint/complementarity/locality；
- heuristic：通常没有数学最优性 certificate。

因此不能做一个只包含 `status/objective/gap` 的过度简化 schema。

### 11.2 “全局最优”不仅依赖 solver，还依赖模型类别

同一个状态文本在不同上下文意义不同。必须结合：

- convexity；
- discrete/continuous；
- solver global/local capability；
- termination；
- bound；
- certificate。

### 11.3 独立 checker 也可能写错

上一轮 Reviewer/Judge research 已经说明 verifier 本身也需要回归测试。因此 Solver Certificate Gate 也要有 regression suite，不能把独立 checker 当绝对真理。

### 11.4 Cross-solver 不是数学证明

两个 solver 一致只能增强可信度，不能自动替代理论证明。特别是两个 wrapper 可能共享相同预处理、相同建模错误或相同数据错误。

### 11.5 Exact solving 的适用范围有限

SCIP 的 exact/rational API 很有价值，但不能据此声称任意 MINLP 都能在比赛时间内获得 exact global proof。本轮没有进行性能验证。

### 11.6 本轮未实际 benchmark

本轮实际完成的是源码/文档研究与工程设计；没有对同一 benchmark 真实运行 HiGHS、Ipopt、SCIP，因此没有声称任何速度、稳定性或“谁更准”的经验排名。

---

## 12 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 独立验证原则 | 已有，规范要求结构化结果与独立验证 | HiGHS/Ipopt/SCIP 主要提供 solver-native 数值状态 | math_mode 原则正确，但缺少统一 solver certificate schema |
| solver status 保真 | 尚未发现统一跨 solver 状态合同 | Ipopt 明确区分 success / acceptable / feasible / limit / diverging | 应新增 Status Normalizer，且保留 raw code |
| primal feasibility | 题面约束要求验证，但未见统一数值字段 | HiGHS 暴露 max/count/sum primal infeasibility | 可直接结构化落盘 |
| dual feasibility | 当前规范未统一要求所有优化结果落盘 | HiGHS/Ipopt 均暴露 dual infeasibility | 优化类结果应按模型类型纳入证书 |
| KKT / complementarity | 无统一机器合同 | HiGHS 有 complementarity/objective error；Ipopt 有 complementarity criterion | NLP/QP 需要正式 certificate 字段 |
| MIP integrality | 有约束意识，但未见统一证书字段 | HiGHS 有 max integrality violation | 应加入 hard gate |
| MIP bound / gap | 当前研究中有概念，但正式规范未见统一 certificate | HiGHS 暴露 dual bound / mip gap | 应决定论文“最优”表述强度 |
| acceptable convergence | 未统一建模 | Ipopt 源码有独立 acceptable convergence | 必须映射为 WARN/低强度 claim，而不是 success |
| local/global 语义 | 当前规范鼓励多初值/收敛检查，但无统一机器 claim capability | Ipopt 属局部 NLP 路线；MIP solver 有 bound-based global certificate | 应新增模型类别 + solver capability 联合判断 |
| absolute vs relative residual | 有单位意识，但未见 solver-level统一检查 | HiGHS 官方文档专门讨论 relative criterion 可误导 optimal | 应在原物理单位独立复算 |
| scaling/conditioning | 现有规范有数据和建模审计，但无统一数值可靠性状态 | HiGHS 文档暴露尺度相关风险 | 应新增 NUMERICALLY_SUSPECT / scaling gate |
| exact verification | 无 | SCIP 有 exact/rational solution API 路线 | 适合作为高风险小模型升级验证，不宜默认使用 |
| solver log provenance | 支撑材料有运行记录/SHA 思想 | 三项目均有丰富原生日志/信息 | 应把 raw solver log hash 纳入 candidate provenance |
| Writer claim gate | 论文只允许基于真实结果，但未见 solver-specific wording gate | 项目本身不负责论文 | math_mode 可新增 Solver Claim Compiler |
| checkpoint / stale | research 已提出 hash/signature 与 STALE | solver 项目不负责 math_mode workflow | certificate 应绑定 solver/options/model/input/checker hash |

总判断：

- **保持**：现有“真实运行 + 独立验证 + 结果索引 + 支撑材料”的事实链；
- **改进**：把“独立验证”从原则升级为原单位 deterministic solution recheck；
- **新增**：Solver Certificate Contract、Status Normalizer、Numerical Reliability Gate、Solver Claim Compiler；
- **替换**：若未来任何 wrapper 只输出 `success=True/False`，应替换为保留 raw status + normalized semantics 的接口；
- **暂不采用**：全模型 exact solve、全模型双 solver、全局极端 tolerance。

---

## 13 对 math-mode 的具体启发（P0 建议近期加入、P1 值得实验、P2 长期考虑、不建议采用）

### P0 建议近期加入

#### P0-1 Solver Certificate Contract

新增设计文件（本轮只提出，不创建正式代码）：

```text
华为杯_求解规范/solver_certificate.schema.json
```

每个优化 candidate 生成：

```text
求解/问题X/结果/solver_certificate.json
```

至少绑定：

- candidate / contract / model / input hash；
- solver name/version/build；
- options/tolerance snapshot；
- raw termination code/message；
- model class；
- objective；
- primal/dual bound；
- gap；
- primal/dual/integrality residual；
- KKT/complementarity（适用时）；
- runtime/iterations/nodes；
- independent recheck；
- claim capability；
- raw log hash。

#### P0-2 Independent Original-unit Recheck

所有 canonical optimization result 都必须使用独立代码重新计算：

- objective；
- equality residual；
- inequality slack；
- domain；
- integrality；
- 题面 hard constraints。

并明确使用**题目原单位**和 Problem Contract tolerance。

#### P0-3 Status Semantics Normalizer

把不同 solver 状态映射到统一的 math_mode 状态，但必须保存 raw status。

建议最少：

```text
PROVEN_GLOBAL
OPTIMAL_WITHIN_TOL
LOCAL_STATIONARY
ACCEPTABLE_ONLY
FEASIBLE_ONLY
LIMIT_REACHED_WITH_INCUMBENT
INFEASIBLE_CERTIFIED
INFEASIBLE_SUSPECT
NUMERICALLY_SUSPECT
UNKNOWN
FAILED
```

#### P0-4 Numerical Reliability Promotion Gate

Candidate Promotion 前增加：

```text
raw solve
+ numeric certificate
+ independent recheck
+ status semantics
= promotion decision
```

`UNKNOWN / NUMERICALLY_SUSPECT / unresolved hard violation` 一律不能 canonical promote。

#### P0-5 Solver Claim Compiler

Writer 只能读取 `claim_capability`，不能直接读取 solver log 后自行“升级”表述。

### P1 值得实验

#### P1-1 Numerical Mutation Regression Suite

对历史优化题或人工小模型注入：

- 系数尺度 `1e-9 ~ 1e9`；
- redundant huge RHS；
- Big-M 过大/过小；
- nearly parallel constraints；
- near-integer boundary；
- equality cancellation；
- 非凸 NLP 多局部极值；
- time limit；
- acceptable convergence；
- tolerance 松紧变化。

评价：

- false-optimal acceptance rate；
- false-infeasible rate；
- max independent violation；
- objective recompute mismatch；
- cross-solver disagreement；
- runtime overhead；
- certificate completeness。

#### P1-2 Final-candidate Cross-solver

只对 final/high-risk candidate 做第二 solver 或多初值复核。

#### P1-3 Tolerance Sweep

不是追求越小越好，而是检查结论是否对合理 tolerance 稳定。

#### P1-4 Scaling Audit

记录变量/约束/目标数量级，检查 scaled 与 original-unit residual 是否一致。

### P2 长期考虑

- 小规模 LP/MILP exact/rational verification；
- condition estimation；
- iterative refinement；
- 自动生成 solver capability matrix；
- 对特定 solver version 的 regression corpus；
- certificate 与机器验证/形式化 proof 的更深集成。

### 不建议采用

- 任何 solver `optimal` 都自动写“全局最优”；
- `success=True` 二值接口作为唯一事实；
- 无条件把 tolerance 调到极端小；
- 为了“可靠”而所有 candidate 双 solver；
- 所有模型 exact solve；
- LLM 根据自然语言日志自行决定最优性等级；
- 只比较 objective，不检查 constraint residual / gap / integrality。

---

## 14 可形成的新 Skill / Agent（只提设计，不创建）

### 14.1 `solver-certificate-agent`

输入：

- Problem Contract；
- Candidate manifest；
- solver raw result/log；
- solution artifact。

输出：

- `solver_certificate.json`；
- normalized status；
- warning list；
- claim capability。

### 14.2 `independent-solution-checker` Skill

确定性工具优先，不使用 LLM 判断数值是否满足。

包含：

- objective recompute；
- constraints recompute；
- integrality check；
- unit-aware tolerance；
- proof obligation mapping。

### 14.3 `numerical-reliability-reviewer`

只在 certificate WARN/BLOCK 时启动，检查：

- scaling；
- Big-M；
- tolerance；
- solver warning；
- local/global semantics；
- multistart/cross-solver/exact-verification 是否必要。

### 14.4 `solver-claim-compiler` Skill

将 certificate 映射为论文可使用的最强事实表述，不负责润色。

### 14.5 不建议的 Agent 划分

不建议建立一个“万能 Solver Expert Agent”同时负责：

- 模型选择；
- 写 solver code；
- 判断自己算得对不对；
- 写论文最优性结论。

这会破坏职责隔离。Solver、Checker、Reviewer、Writer 应保持证据边界。

---

## 15 与历史调研的去重检查

### 15.1 项目级去重

`research/INDEX.md` 中此前未出现：

- `ERGO-Code/HiGHS`
- `coin-or/Ipopt`
- `scipopt/scip`

因此本轮不是旧项目换措辞重访。

### 15.2 机制级去重

与历史主题的关系：

- 与 16:04 Reviewer：此前研究 Reviewer 是否可靠；本轮研究 solver 数值 certificate 的事实输入；
- 与 18:04 Artifact Promotion：此前研究谁能写 canonical；本轮定义一个 candidate 在数值层必须满足什么才能 promote；
- 与 21:04 Problem Contract：此前定义 hard constraints；本轮用这些 hard constraints 独立复算 solver solution；
- 与 22:06 Falsification：此前主动找反例；本轮检查 solver 自身的数值误差和最优性语义；
- 与 23:04 UQ：此前处理数据/模型不确定性；本轮处理数值求解可信度；
- 与 00:05 Robust Decision：此前选择 robust/chance/CVaR/DRO；本轮检查这些模型被 solver 解出来后是否真的有足够证据。

### 15.3 新增结论去重

本轮真正新增、此前索引没有明确提出的结论：

1. solver `optimal/success` 必须经过 Status Semantics Normalizer，不能直接进入论文；
2. Solver Certificate 必须保存 tolerance + residual + gap/bound + local/global capability，而不仅是 objective；
3. 原单位 independent recheck 是 solver certificate 的必要组成；
4. Ipopt `acceptable` 与 desired success 必须区分；
5. relative criterion 可能掩盖绝对 residual，需 scaling/conditioning gate；
6. exact/rational verification 适合作为小型高风险模型的升级验证，而非默认流程；
7. Writer 的最优性措辞应由 certificate 决定，而不是由 LLM 自由解释。

本轮写入前再次对 INDEX 与近期 research 做了主题检查，没有发现明显重复。

---

## 16 下一轮推荐方向

下一轮建议主动轮换到：

**Surrogate / Multi-fidelity Simulation Agent：昂贵仿真、代理模型、主动采样与真实性门禁。**

理由：

当前研究链已经逐渐覆盖：

```text
Problem Contract
→ Model Search
→ Scheduler
→ Solver Certificate
→ Falsification
→ UQ
→ Robust Decision
→ Reviewer
→ Provenance
```

但华为杯常出现高成本仿真、ODE/PDE、Monte Carlo、有限元/CFD 外部结果或大量参数扫描。赛时 Agent 很容易为了节约时间：

- 用代理模型替代真仿真但未标明；
- 在训练点上报告精度；
- extrapolation；
- 用低保真结果冒充高保真；
- 主动采样停止过早；
- surrogate uncertainty 没有进入 decision gate。

下一轮可重点研究：

- BoTorch / Ax 的 multi-fidelity / Bayesian optimization；
- SMT / Emukit / DeepHyper 等 surrogate workflow；
- fidelity ledger；
- high-fidelity anchor points；
- active learning stopping criterion；
- surrogate error gate；
- low/high fidelity disagreement；
- 在 candidate promotion 前强制真实高保真复核关键最优点。

这与本轮的数值 solver reliability 不重复，并且直接服务“建模质量 > 结果真实性 > 验证能力”。

---

## 17 Sources

### 17.1 已阅读 `math_mode` 源码/文档

1. `shaxiaoguang123/math_mode` README  
   https://github.com/shaxiaoguang123/math_mode/blob/main/README.md
2. `AGENTS.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md
3. `CLAUDE.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md
4. `华为杯_求解规范/华为杯_求解规范.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/main/%E5%8D%8E%E4%B8%BA%E6%9D%AF_%E6%B1%82%E8%A7%A3%E8%A7%84%E8%8C%83/%E5%8D%8E%E4%B8%BA%E6%9D%AF_%E6%B1%82%E8%A7%A3%E8%A7%84%E8%8C%83.md
5. `.agents/skills/academic-figure-skill/SKILL.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/main/.agents/skills/academic-figure-skill/SKILL.md
6. `research/INDEX.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md
7. 上一轮 Robust Decision 报告  
   https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-09/2026-09-09_00-05_robust-decision-under-uncertainty.md

### 17.2 已阅读 HiGHS 官方仓库源码/文档

1. Repository：  
   https://github.com/ERGO-Code/HiGHS
2. 本轮固定 commit：`73cac48c5340d775a477087198611862559be250`
3. KKT / feasibility / optimality guide：  
   https://github.com/ERGO-Code/HiGHS/blob/73cac48c5340d775a477087198611862559be250/docs/src/guide/kkt.md
4. `HighsInfo.h`：  
   https://github.com/ERGO-Code/HiGHS/blob/73cac48c5340d775a477087198611862559be250/highs/lp_data/HighsInfo.h
5. Release `v1.15.1`：  
   https://github.com/ERGO-Code/HiGHS/releases/tag/v1.15.1

### 17.3 已阅读 Ipopt 官方仓库源码/文档

1. Repository：  
   https://github.com/coin-or/Ipopt
2. 本轮固定 commit：`1e71ba4eeef0514549587448123ea6fdcb2b0ccd`
3. Convergence checker：  
   https://github.com/coin-or/Ipopt/blob/1e71ba4eeef0514549587448123ea6fdcb2b0ccd/src/Algorithm/IpOptErrorConvCheck.cpp
4. Return codes：  
   https://github.com/coin-or/Ipopt/blob/1e71ba4eeef0514549587448123ea6fdcb2b0ccd/src/Interfaces/IpReturnCodes_inc.h
5. Release `3.14.20`：  
   https://github.com/coin-or/Ipopt/releases/tag/releases/3.14.20

### 17.4 已阅读 SCIP 官方仓库源码/文档

1. Repository：  
   https://github.com/scipopt/scip
2. 本轮固定 commit：`92c7a7639d63d7cbe95db334142984926c176c40`
3. Solution API / exact solution API：  
   https://github.com/scipopt/scip/blob/92c7a7639d63d7cbe95db334142984926c176c40/src/scip/scip_sol.h
4. Numerical settings implementation/search context：  
   https://github.com/scipopt/scip/blob/92c7a7639d63d7cbe95db334142984926c176c40/src/scip/set.c
5. Release `v10.0.3`：  
   https://github.com/scipopt/scip/releases/tag/v10.0.3

### 17.5 仅外部说明 / 未执行验证

- 本轮未在本地安装或运行 HiGHS、Ipopt、SCIP；因此没有报告实际 benchmark、速度排名或本机兼容性结论。
- 本轮没有把 GitHub 搜索摘要当作核心功能证据；关键机制均回到官方源码或官方文档确认。
- “Cross-solver 能否降低竞赛错误率”“exact verification 的赛时成本”“不同 tolerance 下 false-optimal rate”均属于下一步应运行的实验，不是本轮已经验证的事实。
