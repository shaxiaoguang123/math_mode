# MathModel Agent Research

## 1. 本轮研究主题

**Counterexample / Falsification Agent：从 Problem Contract / Proof Obligations 自动生成反例、边界工况与最小失败用例。**

本轮继续沿上一轮 `Problem Specification / Constraint Compiler` 向下推进，但研究目标发生了明确变化：上一轮解决“题面硬约束如何被编译成机器可读、可执行的 Proof Obligations”；本轮研究的是：

> 当我们已经知道“模型应该满足什么”之后，系统怎样主动寻找“它在哪里不满足”，并把失败案例压缩成可复现、可回归、可阻断错误模型晋级的证据？

当前 `math_mode` 已经要求 Evidence Matrix 覆盖敏感性/鲁棒性、场景、理论边界与反证，并要求标准/复杂问题审查失效边界；求解规范也要求小样本机理问题做参考值对比、参数扰动和极限情况，优化问题做可行性验证、baseline 与多初值稳定性。这些规则方向正确，但目前主要以“计划项/验证项”存在，尚未形成统一的：

- `proof_obligation -> test domain -> generator -> oracle/monitor -> counterexample` 机器链路；
- 最小反例（shrinking/minimization）；
- 反例独立重放；
- 失败案例生命周期；
- 反例进入 regression suite 的机制；
- 未解决 hard counterexample 阻断 canonical promotion 的门禁。

本轮深入研究三个此前没有进入 `research/INDEX.md` 的对象：

1. `HypothesisWorks/hypothesis`：property-based testing、stateful invariants、shrinking、failure replay；
2. `pschanely/CrossHair`：symbolic execution / SMT 驱动的 Python contract counterexample search；
3. `BerkeleyLearnVerify/VerifAI`：simulation-guided falsification、robustness margin、active sampling 与 counterexample analysis。

本轮核心结论：

> `math_mode` 不应把“反证”继续停留在论文中的一段敏感性分析，而应在 `Problem Contract / Proof Obligations` 与 `Reviewer / Promotion Gate` 之间增加一个独立的 Falsification Layer：先生成合法且有攻击性的边界/极端输入，再真实执行模型，发现失败后做缩减、独立重放和分类，最后把确认的失败场景提升为长期 regression case。

建议的目标结构：

```text
Problem Contract + Proof Obligations
                ↓
       Falsification Planner
 test domain / oracle / margin / budget
                ↓
    ┌───────────┼────────────┐
    ↓           ↓            ↓
Property      Symbolic    Simulation-guided
Testing       Search      Active Falsification
(Hypothesis)  (CrossHair) (VerifAI pattern)
    └───────────┼────────────┘
                ↓
        Counterexample Found
                ↓
       Minimize / Shrink / Cluster
                ↓
        Independent Replay
                ↓
 Counterexample Archive / Regression Suite
                ↓
      Counterexample Promotion Gate
 unresolved hard violation → candidate cannot become canonical
```

---

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

`research/INDEX.md` 已覆盖：

- 14:00：evidence-first 科研 Agent；
- 15:06：模型搜索树、MCTS/UCT、并行实验；
- 16:04：Reviewer / Judge 与 JudgeEval；
- 17:07：Checkpoint / Resume；
- 18:04：Artifact Ownership / canonical promotion；
- 19:07：Resource Scheduler / pruning；
- 20:08：Citation / External Evidence Provenance；
- 21:04：Problem Contract / Proof Obligations。

本轮不重复上述主题：

- 与 16:04 的 Reviewer 不同：Reviewer 是**评价已经存在的证据**；Falsifier 是**主动制造高价值验证证据**。
- 与 15:06 的模型搜索不同：Model Search 的目标是“找到更好的 candidate”；Falsification 的目标是“尽快找到 candidate 的失效点”。
- 与 21:04 的 Proof Obligation 不同：Proof Obligation 定义“应该满足什么”；Falsification 负责“主动尝试打破它”。
- 与普通敏感性分析不同：敏感性分析常问“输入变化时输出怎么变”；falsification 明确优化“让约束余量最小、让错误发生、找到最小可重现失效案例”。

上一轮报告已经把本主题列为下一轮推荐，因此本轮属于计划中的研究方向轮换，而不是通过改写措辞重复旧结论。

### 2.2 当前 math_mode 已经有的基础

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、当前 Skill 和求解规范后，当前项目已有：

- 固定事实链：题目/数据 → 求解代码 → 结构化结果 → 独立验证 → 结果索引 → 论文；
- `题面约束清单.md`，以及上一轮建议的 machine-readable Problem Contract / Proof Obligations；
- Evidence Matrix 强制考虑理论边界、反证和失效边界；
- 小样本机理题要求参考值、参数扰动、极限情况；
- 优化题要求可行性、baseline、多初值稳定性；
- 结果与图表进入论文前有 QA / 审计；
- 18:04 已提出 candidate workspace 与 canonical promotion；
- 16:04 已提出独立 Reviewer / hard gate。

因此，`math_mode` 已经拥有“发现反例后应该阻断什么”的基础，但缺少“怎样系统地发现反例、压缩反例、复现反例”的执行层。

### 2.3 为什么这对数学建模竞赛是高价值能力

数学建模常见的高风险失败并不是代码直接崩溃，而是：

- 单位范围内大部分点正常，但某个边界处符号反转；
- 优化模型大多数随机初值可行，但某些组合违反业务硬约束；
- 预测模型平均指标良好，但某类极端样本误差灾难性增大；
- 仿真模型在常规参数下稳定，但临界工况违反守恒或出现非物理解；
- 数据处理函数在常规 index 下正确，但特殊长度、重复值、空组或时间边界时泄漏；
- Q2/Q3 依赖 Q1 的输出，只有某种候选组合才产生逻辑矛盾；
- Writer 只展示成功区间，未暴露模型在哪些条件下失效。

这些错误靠“再看一遍代码”通常不够。更有效的策略是：

> 把题面规则和模型假设转成可以被攻击的 property / monitor，然后系统寻找 violation。

---

## 3. 搜索范围与关键词

本轮属于 P1（verification / experiment agent）与 P2（formal methods / tooling）交叉方向，但目标明确服务于 P0 的华为杯可靠建模。

重点关键词：

- property-based testing counterexample shrinking
- stateful model-based testing invariant
- symbolic execution Python contracts counterexample
- SMT counterexample generation
- simulation guided falsification robustness margin
- temporal logic falsification active sampling
- adversarial scenario generation scientific model
- counterexample minimization regression promotion
- metamorphic testing numerical scientific software
- differential testing model implementation
- failure boundary discovery optimization simulation

筛选标准：

1. 必须真实执行代码/仿真或进行符号执行；
2. 必须有明确 property/specification/monitor，而不是纯文本 critic；
3. 优先存在 counterexample、shrinking、replay、error table、robustness score 等可迁移机制；
4. 不把普通 fuzzing 或安全漏洞扫描泛化为数模能力；
5. 不把“随机扰动很多次”直接等同于系统 falsification。

---

## 4. 新发现项目

### 项目 1：Hypothesis

- 名称：Hypothesis
- Repository：https://github.com/HypothesisWorks/hypothesis
- 本轮固定读取 commit：`a8dcd7422a325926693b5464f73349e361562b7c`
- Stars：8948（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T11:43:45Z`；`pushed_at=2026-09-08T05:01:33Z`
- 目标：Python property-based testing；用户声明应对一类输入成立的性质，由框架生成覆盖边界情况的输入并寻找失败案例。
- 核心能力：structured strategies、edge-case generation、shrinking、ExampleDatabase/replay、stateful testing、invariant checking、seed/reproduce failure。
- 本轮实际阅读：
  - `README.md`
  - `hypothesis/src/hypothesis/stateful.py`
  - 官方 stateful / replay / shrinking 文档

最重要价值：**发现失败只是第一步；把失败自动缩减成“最简单的反例”，并让它稳定重放，才真正适合调试和长期回归。**

README 的示例非常直观：错误排序函数把重复元素去掉，Hypothesis 不只发现“某个很长列表失败”，而是最终报告 `[0, 0]` 这样的最小失败输入。对于数学建模，这意味着复杂的极端场景也应尝试被压缩到最小冲突参数集。

### 项目 2：CrossHair

- 名称：CrossHair
- Repository：https://github.com/pschanely/CrossHair
- 本轮固定读取 commit：`ad4a8d06591e55eef7197790c0778f481cd1bf0d`
- Stars：1323（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-07T21:35:48Z`；`pushed_at=2026-09-01T12:22:41Z`
- 最新 release：`v0.0.110`，发布于 2026-08-16
- 目标：对带 type annotations / contracts 的 Python 函数执行 symbolic/concolic analysis，利用 SMT solver 探索执行路径并寻找 counterexample。
- 核心能力：symbolic inputs、Z3/SMT、path exploration、contract checking、unit-test generation、behavioral difference discovery。
- 本轮实际阅读：
  - `README.md`
  - `crosshair/core.py`
  - 官方 contracts / how-it-works / diffbehavior 文档

最重要价值：**对于范围有限、纯 Python、可表达成 contract 的小型 checker，反例不必靠随机采样，可以让 SMT 主动寻找使 predicate 不成立的输入。**

但它也提供了一个重要边界：CrossHair 更适合小函数和相对纯的 Python 逻辑；对 NumPy/Pandas、大型 solver、C 扩展和有副作用的完整赛题 pipeline，不能把“符号执行未找到错误”当成模型正确证明。

### 项目 3：VerifAI

- 名称：VerifAI
- Repository：https://github.com/BerkeleyLearnVerify/VerifAI
- 本轮固定读取 commit：`7ef383f191cac0cb2d0174829ac2ec75ab7a0f3c`
- Stars：219（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-08-24T14:40:43Z`；`pushed_at=2026-07-05T23:03:46Z`
- 目标：对包含 AI/ML 与环境不确定性的系统进行 formal design/analysis，通过智能仿真执行 falsification、systematic fuzzing、parameter synthesis 和 counterexample analysis。
- 核心能力：sample space、sampler、monitor、robustness/rho、falsification threshold、simulation server、parallel falsifier、error/safe tables、counterexample analysis。
- 本轮实际阅读：
  - `README.md`
  - `src/verifai/falsifier.py`
  - `src/verifai/error_table.py`
  - 包目录中的 monitor / sampler / server 结构
  - 官方 sampler/server 文档

最重要价值：**面对不能符号执行的黑盒仿真/优化模型，可以把“是否违反规则”变成连续的 violation margin / robustness score，再用主动 sampler 搜索最危险区域，而不是均匀随机扫全空间。**

---

## 5. 深入架构分析

### 5.1 Hypothesis：Generator 与 Oracle 分离，失败后自动 Shrink

Hypothesis 的基本契约可以抽象为：

```text
Input Strategy / Domain
          ↓
 Generated Example
          ↓
Property / Invariant
          ↓
PASS / FAIL
          ↓ FAIL
Shrink toward simpler failing example
          ↓
Minimal reproducible counterexample
```

这比传统“手工列 5 个边界值”多两个关键能力：

1. **输入空间是结构化的。**不仅是某个参数的 min/max，而可以是列表、集合、嵌套结构、条件相关参数和操作序列。
2. **失败会被最小化。**复杂失败案例经过 shrink，减少不相关维度，便于定位到底是哪条假设或哪几个参数组合造成问题。

对 `math_mode`，应当把上一轮 Problem Contract 中每个可测试 constraint 转成至少四件事：

```text
proof_obligation_id
↓
test_domain / generator
↓
oracle / invariant
↓
shrink policy
```

例如“分配总量必须等于总需求”不应该只运行一组固定数据；可以生成合法规模、边界需求、0 值、重复类别、最大容量和刚好饱和的组合，寻找最小违反守恒的输入。

### 5.2 Hypothesis Stateful：反例可能是一串操作，而不是单点输入

`RuleBasedStateMachine` 的源码非常适合迁移到多阶段数学建模 workflow：它寻找的是**一串操作导致系统破坏的最小程序**。运行时：

- 从当前可用规则中选择操作；
- 执行后立即检查 invariants；
- 可根据执行历史改变下一步允许的 rule；
- 最终失败时输出 minimal breaking program。

对 `math_mode`，这适用于：

- 数据清洗 → 特征构造 → split → 训练 → 预测的顺序错误；
- candidate promote / rollback / rerun 的状态错误；
- Q1 canonical 变化后 Q2 仍消费旧依赖；
- 多 Agent artifact promotion 顺序；
- checkpoint/resume 后 stale artifact 混入。

因此反例不仅应该是：

```text
parameter = 0.0001
```

还可能是：

```text
load Q1-v3
→ build Q2 candidate
→ promote Q1-v4
→ resume old Q2
→ publish figure
```

并证明这串操作导致 lineage mismatch。

### 5.3 CrossHair：对小型 Proof Obligation 使用 Symbolic Search

CrossHair 的 README 和 `core.py` 共同确认：它使用 symbolic values、Z3 和 state-space/path exploration，反复调用目标函数，在路径约束下寻找违反 contract 的模型。

对 `math_mode`，适合的对象不是整个论文项目，而是类似：

```python
def convert_units(x_mm: float) -> float:
    ...

def is_feasible(x, constraints) -> bool:
    ...

def split_time_series(timestamps, cutoff):
    ...

def aggregate_mass(flows):
    ...
```

如果 Proof Obligation 能写成：

```text
precondition -> postcondition
```

就可以尝试 symbolic counterexample search。

尤其值得借鉴 `diffbehavior` 思路：当 Candidate B 声称只是“性能优化，没有改变数值语义”时，可以比较 baseline function 与 candidate function，主动寻找行为不一致输入。

### 5.4 VerifAI：黑盒模型需要 Robustness Score，而不是只有 PASS/FAIL

VerifAI 的 `falsifier.py` 中，server 每次返回：

```text
sample
rho (robustness)
timings
```

是否为 counterexample 由：

```text
rho <= falsification_threshold
```

判定；并保存 error table 与 safe table。这个设计非常重要：

如果只返回 PASS/FAIL，搜索算法无法知道“哪个成功案例离失败更近”；如果定义连续 margin，就可以把 falsification 变成优化问题。

对应数模场景：

- 约束 `g(x) <= 0`：可定义 margin = `-g(x)`；越小越危险，负值即违反；
- 守恒误差：margin = `tolerance - abs(balance_error)`；
- 预测误差上限：margin = `allowed_error - actual_error`；
- 稳定性条件：margin = `stability_limit - spectral_radius`；
- 最小安全间距：margin = `actual_distance - required_distance`。

然后 sampler 不再“均匀取 100 个点”，而是寻找最小 margin。

### 5.5 VerifAI Error Table：反例需要分类，而不是只保存最坏一个

`error_table.py` 不只是把失败输入写 CSV，还提供：

- normalized / standardized representation；
- PCA；
- KMeans / KModes cluster；
- k-closest representative samples；
- random representative cases。

这启发 `math_mode`：多个反例可能实际上属于不同 failure regime。例如：

```text
Failure Family A：低流量 + 高黏度
Failure Family B：临界边界 + 极端温度
Failure Family C：数据缺失 + 某类别稀疏
```

论文里更有价值的不是堆 100 个失败点，而是识别 2–4 类失效机制，并为每类保存一个 minimal / representative counterexample。

---

## 6. Agent / Skill 设计

### 6.1 建议新增：`falsification-agent`

只提出设计，不创建正式 Agent。

输入：

```text
Problem Contract
Proof Obligation Contract
candidate manifest
canonical baseline
search budget
validated input domain
```

输出：

```text
Falsification Plan
Counterexample Records
minimal / representative cases
replay results
regression candidates
promotion blocking status
```

职责不要与 Reviewer 混合：

- Falsifier：主动找失败证据；
- Reviewer：判断证据是否足以支持/反驳 claim；
- Solver：修模型；
- Experiment Manager：真实执行；
- Promotion Gate：决定是否可晋级 canonical。

### 6.2 建议新增：`counterexample-minimizer`

并非所有数模输入都能直接使用 Hypothesis shrink，因此需要 contest-specific minimization：

- 数值变量向边界/0/简单有理数收缩；
- 删除无关特征/约束/样本；
- 缩短时间序列长度；
- 减少场景数量；
- 缩短 operation sequence；
- 固定一部分参数，仅保留导致 violation 的最小集合。

目标不是“得到最坏分数”，而是“得到最容易解释和重放的失败原因”。

### 6.3 建议新增：`metamorphic-oracle-builder`

现实数模中经常没有精确 ground truth，此时可以从 Problem Contract / 模型性质生成 metamorphic relations：

- 合法单位换算前后物理量应等价；
- 如果问题具有 permutation invariance，改变输入顺序不应改变结果；
- 对守恒系统，总量变化必须满足指定关系；
- 对明确单调关系，输入增加不应导致方向错误；
- 对对称几何，对称变换应产生对应对称结果；
- 对尺度齐次模型，合法缩放应满足已知比例关系。

这些 relation 本身也是 Proof Obligation，可由 Falsifier 主动寻找违例。

---

## 7. Workflow

建议形成以下比赛期工作流：

```text
[1] Problem Contract
        ↓
[2] Proof Obligations
        ↓
[3] Candidate Model / Code
        ↓
[4] Falsification Planner
        ├─ obligation 是简单纯 Python predicate
        │      → symbolic search optional
        ├─ domain 是结构化离散/数值输入
        │      → property-based generation
        ├─ model 是昂贵仿真/black-box
        │      → active simulation falsification
        └─ 无绝对 oracle
               → metamorphic / differential relations
        ↓
[5] Execute in isolated candidate workspace
        ↓
[6] Found violation?
        ├─ No → 记录 coverage / budget / 未证明状态
        └─ Yes
             ↓
[7] Shrink / minimize / cluster
             ↓
[8] Independent replay（建议不同进程/clean environment）
             ↓
[9] classify
  CONFIRMED / FLAKY / INVALID_INPUT / CHECKER_BUG
             ↓
[10] confirmed hard violation
      → BLOCK canonical promotion
      → Solver repair
      → replay old counterexample
      → promote important case to regression
```

这里必须强调：

> `NO_COUNTEREXAMPLE_FOUND` 不是 `PROVED_CORRECT`。

报告状态应明确区分：

```text
PASS_ON_TESTED_DOMAIN
COUNTEREXAMPLE_FOUND
COUNTEREXAMPLE_CONFIRMED
FLAKY
UNSUPPORTED_ENGINE
BUDGET_EXHAUSTED
UNPROVEN
```

---

## 8. Code Execution / Tools

### 8.1 Hypothesis：真实运行 Python 测试

Hypothesis 是实际执行测试函数的框架。它的 stateful testing 真实执行 rule 并在每步后检查 invariants；失败后利用 shrink 机制减少案例复杂度，并支持 failure replay / seed / reproduce failure。

对 `math_mode` 的适配方式建议是：

- 不要求所有赛题直接依赖 Hypothesis；
- 先把“property-based testing”抽象成接口；
- Python 题目可以用 Hypothesis 作为一个 backend；
- MATLAB/Julia 等可以实现各自 generator + shrinker；
- 统一输出 Counterexample Record。

### 8.2 CrossHair：symbolic execution / Z3

CrossHair 真实运行目标 Python 函数，但输入是 symbolic proxy；利用 SMT 约束探索可行路径。

适合：

- 单位转换；
- 边界判断；
- index/time-split helper；
- 小型 feasibility predicate；
- baseline 与 candidate 的行为差异。

不适合直接作为：

- NumPy-heavy 主模型 verifier；
- pandas pipeline verifier；
- 外部求解器全流程 verifier；
- 有文件/网络/数据库副作用的任意代码执行器。

CrossHair 官方文档也明确存在 side-effect 与支持范围边界，所以如果未来接入，应在 sandbox/isolated process 中运行。

### 8.3 VerifAI：Simulation Server + Monitor + Sampler

其结构可以抽象为：

```text
Sampler proposes scenario
        ↓
Server calls simulator
        ↓
Simulator returns trajectory/result
        ↓
Monitor computes rho
        ↓
Sampler learns/searches next scenario
```

这非常适合 `math_mode` 的黑盒模型：

- COMSOL/有限元代理模型；
- ODE/PDE 数值仿真；
- 复杂优化；
- 交通/调度仿真；
- Monte Carlo 风险模型；
- 动态控制模型。

不一定要安装 VerifAI；更现实的是借鉴这一接口，写轻量 contest adapter。

---

## 9. QA / Reviewer / Verification

Falsifier 本身也会产生假阳性，因此必须与 16:04 的 Reviewer/Judge 研究联动。

### 9.1 Counterexample 不能发现即定罪

每个发现的 counterexample 至少经过：

1. input-domain validation：输入是否满足题面允许范围；
2. independent replay：干净进程/环境再次执行；
3. oracle validation：monitor/checker 自己是否正确；
4. artifact/hash check：是否使用正确 candidate、数据和 contract；
5. repeated replay：随机模型至少多次验证；
6. classification：confirmed / flaky / invalid / checker-bug。

### 9.2 Counterexample 需要绑定原始 Proof Obligation

不能只记录：

```text
模型在 x=0.7 失败
```

而应记录：

```text
proof_obligation_id = Q2-CONSERVATION-004
contract_hash = ...
candidate_id = q2-cand-17
input = {...}
monitor = conservation_margin_v2
margin = -0.038
threshold = 0
observed_output = ...
replay_count = 5
replay_failures = 5
status = CONFIRMED
```

### 9.3 推荐状态生命周期

```text
FOUND
  ↓ minimize
SHRUNK
  ↓ independent replay
CONFIRMED ─────────────→ OPEN (unresolved)
  ↓ fixed candidate             ↓
FIX_CANDIDATE            BLOCK_PROMOTION
  ↓ replay old case
REGRESSION_PASS
```

若重复运行表现不一致：

```text
FLAKY
```

而不是强行判 PASS/FAIL。

---

## 10. 值得借鉴的设计

### A. 可以直接借鉴

1. **Hypothesis 的 shrink 思想**：失败用例自动向更简单案例收缩。
2. **Stateful invariant after every step**：多阶段 workflow 每次操作后立即检查关键不变量。
3. **Failure replay**：失败必须能以固定 seed / explicit example / replay record 重现。
4. **VerifAI 的 robustness margin**：把 hard constraint 转成连续安全余量，用于主动搜索。
5. **Error table 分析**：对失败场景做聚类/代表性选择，而不是只保存单一 worst case。

### B. 可以改造后采用

1. CrossHair symbolic checking：只在小型纯 Python checker 中采用。
2. VerifAI sampler：抽象其 `sample → simulate → monitor → score`，不必引入完整 autonomous-system stack。
3. Hypothesis ExampleDatabase：可用于赛时快速 replay，但重要反例必须固化为 repository regression record，不能只依赖临时数据库。

### C. 可以作为对照实验

1. random perturbation vs property-based generation；
2. random search vs active falsification；
3. 不 shrink vs shrink 后调试效率；
4. 仅 Reviewer vs Falsifier + Reviewer；
5. 单点边界测试 vs stateful operation-sequence testing；
6. baseline/candidate differential testing vs 只比较最终 metric。

### D. 不建议采用

1. 把“全 pipeline 符号执行”设为默认；
2. 把没有找到反例解释为数学证明；
3. 无题面 domain constraint 的随机 fuzzing；
4. LLM 只在文本中想象 adversarial example，却不真实运行；
5. 为了“看起来 rigorous”引入复杂 temporal-logic 工具，但没有真实需要；
6. 将所有失败都自动写入论文，导致噪声堆积。

---

## 11. 存在的问题

### 11.1 Property-based testing 不等于数学证明

即使生成很多输入，也只说明被测试区域没有发现违例；连续高维空间仍然可能存在未发现失效点。

### 11.2 Shrinking 可能破坏物理合法性

通用 shrinker 往 0、短列表、简单值收缩时，可能得到不满足真实工程约束的场景。因此数模必须使用 domain-aware shrink：

- 保持几何约束；
- 保持时间顺序；
- 保持概率和为 1；
- 保持容量/需求基本关系；
- 保持题面指定上下界。

### 11.3 Oracle 可能错

如果 monitor/checker 自身写错，Falsifier 会高效地产生大量“假反例”。因此 checker 仍需 JudgeEval/回归测试。

### 11.4 Symbolic execution 的适用范围有限

真实科学计算大量依赖 NumPy、SciPy、Pandas、求解器和 native code；不能把 CrossHair 的局部能力泛化为完整形式验证。

### 11.5 Active falsification 会消耗赛时预算

复杂仿真一次可能需要分钟甚至小时，因此必须接入 19:07 的 Resource Scheduler：

- 按 hard obligation 优先级分配 budget；
- early stop 无价值 search；
- 在 deadline 前停止开放式 falsification；
- 为最终论文/QA 保留资源。

### 11.6 找到反例后可能出现“过拟合反例”

Solver 修复一个 minimal counterexample，不代表整个 failure family 已解决。因此修复后要：

1. replay minimal case；
2. replay cluster neighbors；
3. 重新运行同一 generator；
4. 检查是否产生新 failure regime。

---

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 题面硬约束 | 已有 `题面约束清单.md`；21:04 建议 Problem Contract | 三个项目都依赖显式 property/spec/monitor | math-mode 上游基础更贴合竞赛，但缺少统一 falsification mapping |
| 极端/边界验证 | 规范已要求极限情况、反证、失效边界 | Hypothesis 自动生成 edge cases | 当前更多依赖 Agent 计划；可升级为 generator |
| 最小反例 | 未发现统一机制 | Hypothesis 自动 shrinking | 建议新增 domain-aware counterexample minimizer |
| 状态序列反例 | 未发现专门机制 | Hypothesis RuleBasedStateMachine | 可用于多阶段数据/模型/promotion workflow |
| 符号反例 | 未发现 | CrossHair + Z3 | 仅适合小型纯 Python proof obligations |
| 黑盒主动反证 | 当前主要是参数扰动/敏感性 | VerifAI active sampling + robustness | 可将“随机扫参数”升级为 margin-driven search |
| 失败场景分类 | 结果索引/图表可以人工总结 | VerifAI error table + PCA/cluster | 建议自动形成 failure families |
| 反例重放 | 结果可复现要求已存在 | Hypothesis seed/example DB/reproduce failure | 建议建立统一 replay command + hashes |
| 反例回归 | 未发现独立 Counterexample Registry | Hypothesis 会重放历史失败 | 重要失败应固化为长期 regression case |
| Promotion Gate | 18:04 已提出 canonical promotion | 三项目本身不负责赛题 promotion | math-mode 可进一步规定 unresolved hard CE 必须 block |
| Reviewer | 16:04 已有设计建议 | Falsification 框架不是 Reviewer | 两者互补：Falsifier 造证据，Reviewer 验证证据 |
| Resource control | 19:07 已有 scheduler 研究 | VerifAI 有 n_iters/max_time/parallel falsifier | 应接入统一 budget/deadline guard |
| 论文失效边界 | 规范要求写适用边界 | Counterexample 能给真实证据 | 可用反例 cluster 支撑论文适用范围，而不是空泛描述 |

总体判断：

- **保持**：现有独立验证、敏感性/鲁棒性、理论边界、反证与失效边界要求；
- **改进**：把自然语言“做反证”编译成 `proof obligation → generator/monitor`；
- **新增**：Falsification Plan、Counterexample Archive、Minimizer、Replay、Regression Promotion Gate；
- **替换**：不建议替换 Reviewer、Solver 或现有验证体系；Falsifier 是新增证据生产层；
- **暂不采用**：全量 CrossHair / VerifAI 重依赖，先做轻量接口与可选 backend。

---

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：定义 Counterexample Contract / Archive

建议设计机器可读 `counterexamples.jsonl`（路径仅为设计建议，不直接创建正式文件），每条至少包含：

```text
counterexample_id
question_id
contract_hash
proof_obligation_id
candidate_id
engine                 # property / symbolic / simulation / metamorphic / manual
input_or_scenario
input_hash
seed
generation_trace
monitor_id
monitor_version
violation_metric
threshold
margin
observed_output
expected_predicate
failure_class
minimality_status
shrunk_from
replay_command
code_hash
environment_hash
artifact_hashes
replay_count
replay_failures
status                 # FOUND / SHRUNK / CONFIRMED / FLAKY / FIXED / REGRESSION_PASS
discovered_at
```

#### P0-2：Proof Obligation 增加 falsification 字段

上一轮的每个 hard proof obligation 再增加：

```text
test_domain
generator_type
oracle_or_monitor
failure_threshold
shrink_policy
search_budget
replay_policy
hard_blocking
```

如此 Problem Contract 才真正连接到可执行反证。

#### P0-3：建立 Counterexample Gate

晋级规则建议：

```text
confirmed unresolved HARD counterexample > 0
→ candidate.status = BLOCKED
→ 禁止 canonical promotion
→ 禁止 Writer 把对应 claim 写成已验证事实
```

SOFT counterexample 可以进入 limitation / sensitivity discussion，但不能与 hard violation 混淆。

#### P0-4：建立 found → shrink → replay → regression 生命周期

找到失败后不要直接修代码然后遗忘。重要反例必须：

1. 最小化；
2. 独立重放；
3. 修复；
4. 修复后重放；
5. 固化成 regression case；
6. 后续 candidate 自动复测。

这是本轮最值得直接借鉴 Hypothesis 的机制。

### P1：值得实验

#### P1-1：建立历史赛题 Mutation Benchmark

人工向历史题实现中注入已知 bug：

- `<=` ↔ `>=`；
- 最大化 ↔ 最小化；
- m ↔ mm；
- off-by-one index；
- 时间 split 泄漏；
- 漏掉某条守恒；
- 极端参数下除 0；
- 空类别/重复值处理错误；
- Q1 旧 artifact 被 Q2 消费。

比较不同 falsification engine 的：

```text
counterexample_discovery_rate
time_to_first_counterexample
median_shrunk_size
false_alarm_rate
coverage_by_obligation
replay_success_rate
compute_cost
```

#### P1-2：Random Sensitivity vs Active Falsification

对同样预算，比较：

- 均匀随机参数扰动；
- Latin Hypercube / random；
- property-based boundary-biased generation；
- margin-guided active search。

核心不是谁找到“更差的平均指标”，而是谁更快找到**真实 hard violation**。

#### P1-3：Metamorphic Testing

对无绝对答案的问题建立关系型 oracle，尤其适合：

- 物理单位换算；
- 排序/重命名不变性；
- 守恒；
- 单调性；
- 对称性；
- 尺度关系。

#### P1-4：Differential Testing

当改进模型声称保持某个子模块语义不变时，主动搜索 baseline 与 candidate 输出分歧的输入。可以借鉴 CrossHair `diffbehavior`，但实际 backend 可按任务替换。

### P2：长期考虑

建立跨赛题 Counterexample Curriculum：按题型积累最常见 failure patterns，例如：

- 优化：不可行/边界/整数性/多初值；
- 时序：泄漏/时间边界/漂移；
- 机理：守恒/量纲/极限；
- 分类预测：极端类别不平衡/稀有类；
- 网络图：空图/断连/孤点；
- 空间：坐标系/边界/奇异几何。

未来 Problem Contract 编译后，可自动选择对应 falsification recipe，但必须建立在真实回归数据上，而不是纯 LLM 经验库。

### 不建议采用

- 不建议把 CrossHair/SMT 强制作用于所有建模代码；
- 不建议直接引入完整 VerifAI 依赖栈作为赛时默认基础设施；
- 不建议把“没有找到反例”写成“模型已证明正确”；
- 不建议只让 LLM 生成十几个“极端场景”然后不执行；
- 不建议只优化最坏 metric，而不验证生成场景是否属于合法题面 domain；
- 不建议修复一个反例后立即认为 failure family 已消失。

---

## 14. 可形成的新 Skill / Agent

以下只提出设计建议，不创建：

### 1. `falsification-agent`

从 Proof Obligations 选择 property / symbolic / simulation / metamorphic engine，主动搜索 violation。

### 2. `counterexample-minimizer`

把复杂失败场景压缩成可解释、可重放、仍满足 domain constraint 的最小反例。

### 3. `metamorphic-oracle-builder`

从物理/数学不变量生成无 ground-truth 条件下的关系型验证规则。

### 4. `counterexample-regression-manager`

管理反例状态、replay、修复确认、回归提升和 stale contract invalidation。

### 5. `failure-boundary-analyzer`

对多个 counterexamples 做聚类、边界拟合、代表性场景选择，并输出论文可使用的真实“适用范围/失效机制”证据。

---

## 15. 与历史调研的去重检查

### 新项目去重

本轮三个主要对象此前均未出现在 `research/INDEX.md`：

- `HypothesisWorks/hypothesis`：新；
- `pschanely/CrossHair`：新；
- `BerkeleyLearnVerify/VerifAI`：新。

### 新机制去重

此前：

- 16:04 研究“怎样判断结果是否可信”；
- 21:04 研究“怎样定义机器可执行题面约束”；
- 本轮首次研究“怎样主动搜索让这些约束失效的输入/场景，并最小化与长期保存失败案例”。

本轮新增认知明确包括：

1. shrinking/minimal counterexample；
2. stateful breaking sequence；
3. symbolic contract counterexample search；
4. continuous robustness margin；
5. active simulation falsification；
6. failure-cluster analysis；
7. counterexample → regression promotion lifecycle。

因此不存在通过修改措辞重复前几轮结论的问题。

---

## 16. 下一轮推荐方向

建议下一轮轮换到：

**Model Calibration / Uncertainty Quantification Agent：模型不确定性、置信区间、预测区间、bootstrap/conformal prediction、参数不确定性传播与“结论可信区间”。**

理由：当前 research 已经逐步覆盖“题面合同 → 搜索候选 → 真实执行 → 反例攻击 → Reviewer → provenance”，但数学建模论文中另一个常见薄弱点是把单次点估计写得过于确定。下一轮可以研究如何自动区分：

- aleatoric vs epistemic uncertainty；
- 参数不确定性 vs 模型结构不确定性；
- point estimate vs interval；
- bootstrap / conformal / Bayesian / ensemble 何时适用；
- 如何让 Writer 只能引用经过校准的区间与风险结论。

该方向与本轮 falsification 不同：本轮寻找“哪里会坏”；下一轮回答“在未坏的区域，我们到底有多确定”。

---

## 17. Sources

### A. 已阅读源码 / 官方仓库文档

1. Hypothesis 官方仓库：
   - https://github.com/HypothesisWorks/hypothesis
   - 固定 commit：`a8dcd7422a325926693b5464f73349e361562b7c`
   - README：https://github.com/HypothesisWorks/hypothesis/blob/a8dcd7422a325926693b5464f73349e361562b7c/README.md
   - Stateful source：https://github.com/HypothesisWorks/hypothesis/blob/a8dcd7422a325926693b5464f73349e361562b7c/hypothesis/src/hypothesis/stateful.py
   - Stateful testing docs：https://hypothesis.readthedocs.io/en/latest/stateful.html
   - Reproducing failures：https://hypothesis.readthedocs.io/en/latest/reproducing.html

2. CrossHair 官方仓库：
   - https://github.com/pschanely/CrossHair
   - 固定 commit：`ad4a8d06591e55eef7197790c0778f481cd1bf0d`
   - README：https://github.com/pschanely/CrossHair/blob/ad4a8d06591e55eef7197790c0778f481cd1bf0d/README.md
   - core source：https://github.com/pschanely/CrossHair/blob/ad4a8d06591e55eef7197790c0778f481cd1bf0d/crosshair/core.py
   - How it works：https://crosshair.readthedocs.io/en/latest/how_does_it_work.html
   - diffbehavior：https://crosshair.readthedocs.io/en/latest/diff_behavior.html
   - latest release v0.0.110：https://github.com/pschanely/CrossHair/releases/tag/v0.0.110

3. VerifAI 官方仓库：
   - https://github.com/BerkeleyLearnVerify/VerifAI
   - 固定 commit：`7ef383f191cac0cb2d0174829ac2ec75ab7a0f3c`
   - README：https://github.com/BerkeleyLearnVerify/VerifAI/blob/7ef383f191cac0cb2d0174829ac2ec75ab7a0f3c/README.md
   - falsifier source：https://github.com/BerkeleyLearnVerify/VerifAI/blob/7ef383f191cac0cb2d0174829ac2ec75ab7a0f3c/src/verifai/falsifier.py
   - error table source：https://github.com/BerkeleyLearnVerify/VerifAI/blob/7ef383f191cac0cb2d0174829ac2ec75ab7a0f3c/src/verifai/error_table.py
   - docs：https://verifai.readthedocs.io/

4. 当前 `math_mode`：
   - README：https://github.com/shaxiaoguang123/math_mode/blob/b599be7e17eef273af69dbe3da1e5b7701e80252/README.md
   - AGENTS：https://github.com/shaxiaoguang123/math_mode/blob/b599be7e17eef273af69dbe3da1e5b7701e80252/AGENTS.md
   - CLAUDE：https://github.com/shaxiaoguang123/math_mode/blob/b599be7e17eef273af69dbe3da1e5b7701e80252/CLAUDE.md
   - 求解规范：https://github.com/shaxiaoguang123/math_mode/blob/b599be7e17eef273af69dbe3da1e5b7701e80252/%E5%8D%8E%E4%B8%BA%E6%9D%AF_%E6%B1%82%E8%A7%A3%E8%A7%84%E8%8C%83/%E5%8D%8E%E4%B8%BA%E6%9D%AF_%E6%B1%82%E8%A7%A3%E8%A7%84%E8%8C%83.md
   - 上一轮 Problem Specification 研究：https://github.com/shaxiaoguang123/math_mode/blob/b599be7e17eef273af69dbe3da1e5b7701e80252/research/2026-09-08/2026-09-08_21-04_problem-specification-compiler.md

### B. 官方说明 / 论文层资料

1. VerifAI CAV 2019 project/paper information：
   - https://people.eecs.berkeley.edu/~sseshia/pubs/b2hd-verifai-cav19.html
2. Hypothesis 官方文档中的 shrinking / replay / ExampleDatabase 说明：
   - https://hypothesis.readthedocs.io/en/latest/
3. CrossHair 官方文档中的 contracts、symbolic execution 和 limitations：
   - https://crosshair.readthedocs.io/en/latest/

### C. 本轮未做的验证声明

- 本轮没有在 `math_mode` 中安装或运行 Hypothesis、CrossHair、VerifAI；因此没有声称这些工具已经在当前华为杯工程中兼容或验证通过。
- 本轮没有修改正式 Agent / Skill / workflow。
- 对 CrossHair 和 VerifAI 的迁移建议属于源码/官方文档支持下的架构建议，不等于已完成赛题 benchmark。
- “Falsification 找不到反例”在本报告中从未被解释为形式证明。
