# MathModel Agent Research

## 1. 本轮研究主题

**Model Calibration / Uncertainty Quantification Agent：把“敏感性/鲁棒性”升级为可审计的不确定性建模、预测区间、校准诊断与全局敏感性证据链。**

本轮研究的问题不是“再多画几张误差带或敏感性图”，而是：

> 当一个候选模型已经通过真实运行、基础验证和反例搜索后，`math_mode` 如何回答“这个数到底有多确定、这种确定性从哪里来、在什么假设下成立、哪些参数主导不确定性、哪些场景下区间失效”，并把这些回答变成可机器审计、可复现、可阻断错误论文结论的证据？

当前 `math_mode` 已经要求敏感性、鲁棒性、Monte Carlo、bootstrap、理论边界等分析必须真实运行并保存结果，也明确要求绘图脚本只读取已落盘结果；但这些要求目前仍主要以求解规范、Evidence Matrix 和 Figure Plan 的自然语言规则存在。尚未形成统一的：

- 不确定性来源分类与来源依据；
- 训练 / 校准（conformalization）/ 最终测试的数据角色锁定；
- 预测区间或预测集合的 coverage / width / sharpness / proper score 质量门禁；
- subgroup / conditional calibration 检查；
- conformal 方法适用前的 exchangeability / distribution-shift 风险检查；
- 参数采样设计与 sensitivity analyzer 的兼容性契约；
- 灵敏度指数自身的 bootstrap 置信区间与收敛性检查；
- 不确定性实验的 `input/sample/result/analysis` 状态失效规则；
- 与 candidate、checkpoint、canonical promotion 和论文 claim 的统一 lineage。

本轮深入研究三个此前未进入 `research/INDEX.md` 的对象：

1. `scikit-learn-contrib/MAPIE`：conformal prediction、prediction interval/set、risk control、exchangeability testing；
2. `uncertainty-toolbox/uncertainty-toolbox`：预测不确定性的 calibration、sharpness、proper scoring rules、adversarial group calibration 与 recalibration；
3. `SALib/SALib`：Sobol/Morris/PAWN 等全局敏感性分析、sampling → evaluate → analyze 的状态协议，以及 Sobol 指数 bootstrap 置信区间。

本轮核心结论：

> `math_mode` 应把 UQ 从“论文后段的敏感性分析”提升为 Solver 与 Reviewer 之间的一等证据层：先声明不确定性是什么、来自哪里、采用什么数据角色和假设，再执行可复现的校准/传播/敏感性实验，最后由 UQ Gate 判断“coverage 是否成立、区间是否有信息量、关键子群是否失校准、敏感性排序是否稳定”。只有通过门禁的 UQ 结论才能晋级 canonical 并进入论文。

建议目标结构：

```text
Problem Contract + Data Audit + Candidate Model
                    ↓
       Uncertainty Specification Compiler
  source / kind / range-distribution / dependence / authority
  train / calibration / test / scenario role
                    ↓
              UQ Planner
       ┌────────────┼─────────────┐
       ↓            ↓             ↓
 Predictive UQ   Input/Param UQ  Global Sensitivity
 conformal /     MC / bootstrap  Sobol / Morris /
 interval / set  propagation     PAWN ...
       └────────────┼─────────────┘
                    ↓
            Real Code Execution
                    ↓
             UQ Evidence Pack
 coverage / width / sharpness / proper score
 subgroup coverage / exchangeability / shift diagnostics
 output distribution / tail risk / S1-ST-S2 + CI
                    ↓
                 UQ Gate
                    ↓
       canonical result → Figure Skill → Paper
```

---

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

截至本轮开始，`research/INDEX.md` 已覆盖：

- 14:00：evidence-first 科研 Agent；
- 15:06：模型搜索树、MCTS/UCT、并行实验；
- 16:04：Reviewer / Judge 与 JudgeEval；
- 17:07：Checkpoint / Resume；
- 18:04：Artifact Ownership / canonical promotion；
- 19:07：Resource Scheduler / pruning；
- 20:08：Citation / External Evidence Provenance；
- 21:04：Problem Contract / Proof Obligations；
- 22:06：Counterexample / Falsification。

本轮与上述主题的边界明确：

- 与 22:06 Falsification 不同：Falsifier 追求“找到一个能把模型打坏的场景”；UQ 追求“量化结果分布、区间质量、参数贡献与剩余不确定性”。
- 与 16:04 Reviewer 不同：Reviewer 评价已有证据；UQ layer 主动生产新的统计/概率证据。
- 与 15:06 Model Search 不同：Model Search 决定哪个候选更好；UQ 决定这个候选的结果有多稳定、区间是否校准、风险是否可接受。
- 与 21:04 Problem Contract 不同：Problem Contract 固化题面硬约束；UQ Contract 固化“哪些输入/参数/模型成分是不确定的，以及如何量化”。
- 与当前已有“敏感性/鲁棒性”要求不同：本轮重点不是要求做，而是研究**怎样把 UQ 做成正确的数据角色、正确的统计对象、正确的实验状态与门禁**。

上一轮报告已经把 Model Calibration / UQ 列为推荐下一方向，因此本轮属于正常轮换，不是改写旧结论。

### 2.2 当前 math_mode 已经有什么

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、`.agents/skills/academic-figure-skill/SKILL.md`、求解规范相关搜索结果与近期 research 后，可以确认当前项目已有很好的底座：

- 固定事实链：题目/数据 → 求解代码 → 结构化结果 → 独立验证 → 结果索引 → 论文；
- 题面约束、数据审计、求解计划、Evidence Matrix；
- 要求敏感性、鲁棒性、场景、Monte Carlo、bootstrap 等必须真实运行并落盘；
- 要求固定随机种子、记录运行时间和解释器；
- Figure Skill 只消费真实结果，不允许为了画图重新训练、抽样或手工补数；
- 支撑材料、SHA-256、结果索引与论文 QA；
- 前几轮研究已经提出 candidate workspace、artifact fingerprint、checkpoint、promotion gate、proof obligation、counterexample archive。

因此本轮不是从零增加“可靠性意识”，而是补齐一个明显缺口：

> 当前项目知道“敏感性/鲁棒性要真实做”，但还没有统一回答“UQ 的对象、假设、数据角色、指标、统计保证和失效条件分别是什么”。

### 2.3 为什么对华为杯有直接价值

数学建模竞赛中常见的误区是只报告一个最优点估计：

- 预测 RMSE 很低，但 95% 区间实际只覆盖 70%；
- 区间覆盖率够高，但宽到没有决策价值；
- 全体样本平均覆盖正常，但某个关键时间段/设备/地区严重失校准；
- 参数做了 ±10% 扰动，但 ±10% 没有数据、文献或题面依据；
- Sobol 排名只跑一次，没有 CI，不知道第一名和第二名是否真的可区分；
- Monte Carlo 抽样方案改了，旧灵敏度图仍被论文引用；
- 模型在训练分布内区间有效，却在时间漂移或场景迁移后仍声称“95% 保证”；
- 调参、校准和最终评估使用同一测试集，产生隐性乐观偏差。

这些问题不一定导致代码报错，却会直接降低建模可信度、结果真实性和论文说服力。

---

## 3. 搜索范围与关键词

本轮属于 P1（data science / model validation / reproducible research）为主，并直接服务 P0 的华为杯赛时建模。

重点关键词：

- uncertainty quantification mathematical modeling workflow
- conformal prediction calibration prediction interval
- conformal exchangeability testing distribution shift
- conditional coverage subgroup calibration
- uncertainty calibration sharpness proper scoring rule
- adversarial group calibration predictive uncertainty
- bootstrap uncertainty interval reproducibility
- global sensitivity Sobol Morris PAWN confidence interval
- sensitivity index bootstrap confidence interval convergence
- uncertainty propagation Monte Carlo parameter distributions
- calibration set train test leakage
- aleatoric epistemic parameter model uncertainty
- uncertainty-aware model selection

筛选原则：

1. 必须真实计算预测区间、校准指标、采样结果或灵敏度指数；
2. 优先有明确数据角色、状态机、sample/evaluate/analyze 协议或 validity check；
3. 优先有 coverage、sharpness、proper score、subgroup calibration、CI 等可审计量；
4. 不把“LLM 自评置信度”当作数值模型 UQ；
5. 不把普通误差条或单次 ±10% 扰动直接当作完整 UQ；
6. 本轮控制在 3 个高价值项目，避免泛化收集。

---

## 4. 新发现项目

### 项目 1：MAPIE

- 名称：MAPIE — Model Agnostic Prediction Interval Estimator
- Repository：https://github.com/scikit-learn-contrib/MAPIE
- 本轮固定读取 commit：`4105fc5ce81359b6ea276c8bb09a8cabdfae7b30`
- Stars：1587（本轮读取 GitHub metadata）
- Repository `updated_at`：2026-09-06；最近代码 `pushed_at`：2026-08-14
- 最新正式 release：`v1.5.0`，2026-08-05 发布
- 目标：以 conformal prediction / distribution-free inference 为核心，为回归、分类、时序等预测器产生 prediction interval / prediction set，并提供 risk control 与适用性检查。
- 核心能力：Split/Cross conformal、Jackknife-after-Bootstrap、quantile regression conformalization、conditional conformal、risk control、coverage metrics、exchangeability tests。

本轮实际阅读：

- `README.md`
- `mapie/regression/regression.py`
- exchangeability testing 相关源码/测试与示例索引
- v1.5.0 Release notes

最值得借鉴的机制不是某一种 conformal 公式，而是**把训练、conformalization、最终预测的生命周期显式拆开，并对调用顺序做状态保护**。

`SplitConformalRegressor` 的公开接口明确是：

```text
fit(training set)
      ↓
conformalize(held-out conformalization set)
      ↓
predict_interval(test / future X)
```

这比“训练完直接画 95% 区间”更适合 `math_mode`，因为它迫使 Agent 对数据角色负责。

2026 年 README 与 v1.5.0 还新增/强化了 exchangeability testing、conditional conformal 与 conditional coverage，这提供了另一个重要工程原则：

> 理论保证不是模型名字自带的属性；必须检查适用假设或把保证降级为经验性结果。

### 项目 2：Uncertainty Toolbox

- 名称：Uncertainty Toolbox
- Repository：https://github.com/uncertainty-toolbox/uncertainty-toolbox
- 本轮固定读取 commit：`6ea1fed6591923a95d49d8049a197e33d4d8092d`
- Stars：2013
- Repository `updated_at`：2026-09-02；最近代码 `pushed_at`：2025-03-05
- 目标：评价、可视化和改进 predictive uncertainty，当前主要聚焦 regression。
- 核心能力：accuracy、average calibration、adversarial group calibration、sharpness、NLL/CRPS/check score/interval score、isotonic/std recalibration。

本轮实际阅读：

- `README.md`
- `uncertainty_toolbox/metrics.py`
- `uncertainty_toolbox/metrics_calibration.py`
- `uncertainty_toolbox/recalibration.py`

最值得借鉴的是：**UQ 质量不能被一个 coverage 数字概括。**其 `get_all_metrics` 同时返回：

```text
accuracy
+ average calibration
+ adversarial group calibration
+ sharpness
+ proper scoring rules
```

这对数模 Agent 很重要。一个区间可以通过把宽度无限放大获得很高覆盖率，因此 coverage 必须与 width/sharpness、proper score 和点预测质量共同评价。

另一个高价值机制是 `adversarial_group_calibration`：它针对不同 group size 重复抽取子群，并关注每次 trial 中遇到的**最差 calibration error**，而不是只看全局平均值。它可以迁移为华为杯里的：

- 不同设备；
- 不同时间区间；
- 不同地区；
- 不同工况；
- 不同类别；
- 高风险/尾部区域。

注意：该仓库最近代码 push 为 2025-03-05，因此本轮将其视为“成熟机制参考”，而不是“2026 最新算法项目”。

### 项目 3：SALib

- 名称：Sensitivity Analysis Library (SALib)
- Repository：https://github.com/SALib/SALib
- 本轮固定读取 commit：`aa2c5545b3bfd0a982e9fad7625070a8ea340d38`
- Stars：1008
- Repository `updated_at`：2026-09-08；最近代码 `pushed_at`：2026-07-17
- 目标：为系统建模提供 Sobol、Morris、FAST、RBD-FAST、Delta、DGSM、HDMR、PAWN、Regional Sensitivity Analysis 等方法。
- 核心能力：参数问题定义、采样、真实模型 evaluate、全局敏感性分析、并行执行、bootstrap CI、结果对象。

本轮实际阅读：

- `README.rst`
- `src/SALib/util/problem.py`
- `src/SALib/analyze/sobol.py`

最值得借鉴的不是“支持很多灵敏度方法”，而是其 `ProblemSpec` 把状态明确拆成：

```text
samples → results → analysis
```

而且当 `samples` 被替换时，会主动清除旧 `results`；重新 sampling 时同时清除旧 `results` 与 `_analysis`。也就是说：

> 上游不确定性实验设计变了，下游结果必须自动失效，不能因为文件还在就继续使用。

这与 `math_mode` 前几轮研究出的 STALE / artifact provenance / checkpoint 思路高度兼容。

Sobol analyzer 还要求输出长度必须与 sample design 匹配，并显式支持 `num_resamples`、`conf_level`、`seed`，返回 `S1_conf / ST_conf / S2_conf`。这说明**灵敏度指数本身也是估计量，也需要不确定性和收敛性证据**。

---

## 5. 深入架构分析

### 5.1 MAPIE：把 UQ 变成独立生命周期，而不是模型的附加字段

MAPIE 的核心数据流可抽象为：

```text
Training Data
   ↓
Base Estimator.fit
   ↓
Conformalization Data
   ↓
Conformity Scores
   ↓
Prediction Interval / Set
   ↓
Coverage / Conditional Coverage / Risk Diagnostics
```

这对 `math_mode` 的关键启发有三层。

第一，**calibration/conformalization data 是独立角色**。当前 `math_mode` 已经要求训练/测试隔离，但未来 UQ 不能只继续用 `train/test` 二分法。对于 split conformal，应显式有：

```text
TRAIN
CALIBRATION / CONFORMALIZATION
TEST / FINAL EVALUATION
```

数据角色必须进入机器契约，Writer 不得把 calibration set 上的 coverage 当最终泛化证据。

第二，**conformity score 是中间产物，不应该只保存最后区间图**。它应进入 UQ Evidence Pack，绑定数据 hash、candidate、方法版本和 confidence level。

第三，**假设验证要成为结果状态的一部分**。当 exchangeability 或相关适用假设明显不成立时，不应继续输出“95% 保证”式语言，而应标记为：

```text
GUARANTEE_VALID
EMPIRICAL_ONLY
ASSUMPTION_WARNING
GUARANTEE_INVALID
```

具体状态名称可后续设计，但原则应先进入架构。

### 5.2 Uncertainty Toolbox：Calibration 与 Sharpness 必须一起看

其架构更接近评价层：

```text
point prediction + predicted uncertainty + ground truth
                    ↓
             UQ Metric Suite
    ┌───────────────┼────────────────┐
    ↓               ↓                ↓
calibration      sharpness      proper score
    ↓               ↓                ↓
 average + worst-subgroup diagnostics
                    ↓
             optional recalibration
```

这里最重要的工程思想是**多目标 UQ scorecard**。

例如：

- Coverage 高、区间极宽：不应判优；
- 区间很窄、coverage 严重不足：过度自信；
- 全局 calibration 好、关键场景差：不能只报告平均；
- recalibration 后平均 calibration 变好：仍需在独立 test 上重新评估，不能在同一校准数据上自证成功。

因此 `math_mode` 的未来 `UQ Gate` 至少应该同时消费：

- point accuracy；
- empirical coverage / calibration error；
- interval width / sharpness；
- proper scoring rule；
- subgroup/conditional metrics；
- calibration-test split lineage。

### 5.3 SALib：Sensitivity 本质上是一个受实验设计约束的工作流

SALib 明确采用：

```text
ProblemSpec(names, bounds, outputs)
          ↓
Sampler
          ↓
Samples
          ↓
Real Model Evaluation
          ↓
Results
          ↓
Analyzer compatible with sampler
          ↓
Sensitivity indices + confidence intervals
```

这与很多竞赛论文中的“改一个参数看曲线”完全不同。

代码级值得借鉴的状态规则：

1. sample 变化 → results 清空；
2. sample 变化 → analysis 清空；
3. 没有 model results → analyze 直接拒绝；
4. samples/results shape 不匹配 → 拒绝；
5. Sobol analyzer 检查输出长度与采样协议是否兼容；
6. `seed`、`num_resamples`、`conf_level` 明确进入计算；
7. S1/ST/S2 同时返回 bootstrap confidence interval。

可以把这个模式直接迁移为 `math_mode` 的 UQ state machine：

```text
PLANNED
→ SAMPLED
→ EXECUTED
→ ANALYZED
→ VALIDATED
→ CANONICAL

上游 spec/sample hash 变化：
ANALYZED/VALIDATED → STALE
```

### 5.4 三个项目合并后的统一认识

三个项目关注不同层，但正好构成一条完整 UQ 链：

```text
SALib
  解决：输入不确定性怎样设计采样、传播并归因

MAPIE
  解决：预测结果怎样产生具有统计意义的 interval/set

Uncertainty Toolbox
  解决：interval/distribution 到底校准得好不好、是否过宽、子群是否失效
```

`math_mode` 不需要照搬任何一个项目，而应把三者抽象为统一 contract + evidence + gate。

---

## 6. Agent / Skill 设计

### 6.1 建议的职责分层

不建议做一个无边界的 `uncertainty-agent`。更合理的是四个职责层，其中前两个可以先合并实现：

```text
Uncertainty Specification Agent
        ↓
UQ Experiment Manager
        ↓
Calibration / Sensitivity Auditor
        ↓
现有 Reviewer / Promotion Gate / Figure Skill
```

#### Uncertainty Specification Agent

输入：

- Problem Contract；
- 数据审计；
- candidate 模型说明；
- 外部 evidence ledger；
- 题面/文献给出的误差、参数范围、测量精度。

职责：

- 识别不确定性来源；
- 区分 `aleatoric / epistemic / input / parameter / scenario / model_structure`；
- 给每个范围/分布标记依据；
- 指定变量之间的 dependence/correlation；
- 决定是否是 probability distribution 还是仅 scenario range；
- 指定 TRAIN/CALIBRATION/TEST 数据角色；
- 生成 UQ Contract。

关键原则：

> “不知道真实分布”时不能自动伪造 Normal(μ,σ)；可以标记为 bounded scenario uncertainty，并把结论写成 scenario robustness，而不是概率保证。

#### UQ Experiment Manager

职责：

- 生成 bootstrap / Monte Carlo / conformalization / sensitivity samples；
- 真实运行 candidate；
- 保存 sample matrix、seed、环境、运行日志；
- 维护 `samples → results → analysis` 状态；
- 并行时接入此前的 Resource Scheduler；
- 上游 UQ spec 变化后自动使旧结果 STALE。

#### Calibration / Sensitivity Auditor

职责：

- coverage；
- width / sharpness；
- proper score；
- subgroup/conditional coverage；
- exchangeability / shift warning；
- Sobol/Morris 等 sensitivity 的稳定性和 CI；
- 判断 UQ 结论能否进入 canonical。

#### Figure Skill

保持现有设计：

- **不负责重新做 UQ 计算**；
- 只消费 `qa_pass` 的 UQ structured result；
- 渲染 calibration curve、prediction interval、Sobol index + CI、uncertainty propagation distribution、parameter-response surface 等。

### 6.2 Agent 不应拥有的权限

UQ Agent 不应：

- 自己修改题面硬约束；
- 自己发明参数范围；
- 使用 final test 数据拟合 recalibration；
- 为了获得漂亮区间调大 confidence/scale 后不重新验证；
- 把 nominal confidence 直接写成实际 coverage；
- 覆盖原始数据；
- 直接写正式论文结论。

---

## 7. Workflow

建议未来的赛时 UQ 工作流为：

```text
[1] Problem Contract / Data Audit
    ↓
[2] Uncertainty Source Register
    每个不确定量记录来源、单位、范围/分布、依赖、authority
    ↓
[3] UQ Route Selection
    ├─ prediction → conformal / bootstrap / ensemble
    ├─ physical/parametric → sampling + propagation
    ├─ ranking of drivers → global sensitivity
    └─ only bounded assumptions → scenario robustness, not probability claim
    ↓
[4] Data Role Lock
    train / calibration / test / scenario
    ↓
[5] Experiment Design
    sampler / N / seed / resamples / confidence / subgroup slices
    ↓
[6] Candidate-specific Real Execution
    raw samples + outputs + logs + hashes
    ↓
[7] Analysis
    interval / distribution / sensitivity indices + CI
    ↓
[8] UQ Validation
    calibration + sharpness + subgroup + assumptions + convergence
    ↓
[9] UQ Gate
    FAIL / WARNING / EMPIRICAL_ONLY / PASS
    ↓
[10] Canonical Promotion
    ↓
[11] Figure Skill & Writer only consume promoted UQ evidence
```

### 7.1 对预测题的最小闭环

```text
Train
↓
Conformalize / Calibrate on dedicated split
↓
Predict interval on untouched test
↓
Coverage + Width + Conditional Coverage
↓
Assumption / shift diagnostic
↓
Pass → report interval
Fail → model/recalibration route returns to Solver
```

### 7.2 对机理/仿真/优化题的最小闭环

```text
Uncertain parameter specification
↓
Sample design
↓
Model execution
↓
Output distribution / feasibility probability
↓
Global sensitivity + CI
↓
Convergence / repeated-seed stability
↓
Pass → report uncertainty-aware conclusion
```

---

## 8. Code Execution / Tools

### 8.1 MAPIE

- Python 实际执行；
- 兼容 scikit-learn 模型，也可包装其他模型；
- `fit → conformalize → predict_interval` 有显式状态；
- Cross conformal / Jackknife-after-Bootstrap 等方法会真实重复拟合或利用交叉验证/重采样；
- 2026 代码包含 exchangeability testing 与 conditional conformal 相关实现/测试；
- 本轮未在 `math_mode` 内实际安装/运行 MAPIE，因此不能声称它已通过本项目环境验证。

### 8.2 Uncertainty Toolbox

- Python；
- 输入是已生成的 point prediction / uncertainty / ground truth；
- `get_all_metrics` 真实计算 calibration、sharpness、proper scores 等；
- adversarial group calibration 会重复抽取子群并统计最差 calibration；
- recalibration 用 isotonic regression 或标度优化；
- 本轮只阅读源码，没有执行其测试套件。

### 8.3 SALib

- Python；
- sampler 产生真实 sample matrix；
- `ProblemSpec.evaluate` 调用实际 model function；
- 支持本地并行，源码对并行/分布式实验功能有 warning，应按其实际成熟度看待；
- Sobol analyzer 对结果执行真实 resampling 并生成置信区间；
- 本轮没有在 `math_mode` 的赛题环境中安装/执行 SALib。

### 8.4 对 math_mode 的工具策略

近期不建议让正式 workflow 强依赖这三个外部库。

优先顺序应是：

1. 先定义 `UQ Contract / UQ Result Contract / UQ Gate`；
2. backend 可以是项目自写轻量实现或调用 MAPIE/SALib；
3. 结果结构对 backend 保持稳定；
4. 外部库不可用时可以切换 backend，但不能降低证据字段要求；
5. provenance 必须记录 backend 名称、版本/commit 与关键参数。

---

## 9. QA / Reviewer / Verification

### 9.1 UQ 的第一道 QA：不确定性来源是否真实

每个 uncertainty item 至少应回答：

```text
这个量为什么是不确定的？
范围/分布来自题面、数据估计、文献还是人为 scenario？
单位是什么？
是否与其他变量相关？
```

禁止：

```text
“通常做 ±10%，所以所有参数都 ±10%”
```

如果没有 probabilistic evidence，只能标记为 scenario range。

### 9.2 预测区间 QA

至少检查：

- calibration set 是否与 train/test 独立；
- nominal coverage 与 empirical coverage；
- interval width / sharpness；
- proper score；
- subgroup / conditional coverage；
- 时间/空间/类别 shift；
- 是否满足方法需要的 exchangeability 或相关假设；
- 多个 confidence level 是否一致；
- test set 是否被用来选择 recalibration 参数。

### 9.3 Sensitivity QA

至少检查：

- sampler 与 analyzer 是否兼容；
- bounds / distributions 是否有依据；
- 参数相关性是否被错误忽略；
- sample budget 是否足够；
- 多 seed / 多 N 下排名是否稳定；
- S1/ST 等是否带 CI；
- CI 重叠严重时是否仍武断声明“参数 A 最重要”；
- 失败/不可行样本如何处理；
- sample hash 变化是否使旧 analysis STALE。

### 9.4 Reviewer 应区分的三类结论

```text
Point claim
  “模型预测值为 123.4”

Uncertainty claim
  “90% prediction interval 为 [...]”

Guarantee claim
  “在某假设下具有至少某种覆盖/风险保证”
```

第三类 claim 的证据门槛必须最高。不能因为代码调用了 conformal library 就自动获得“保证”。

### 9.5 UQ Reviewer 自身的 regression cases

可以建立已知错误样例：

- calibration 与 test 数据重合；
- nominal 95%，empirical coverage 72%；
- coverage 99%，但 interval width 极端大；
- overall coverage 95%，关键 subgroup 60%；
- 时间序列随机打乱后做 split conformal；
- 参数 bounds 无来源；
- Sobol sample 与 analyzer 配置不匹配；
- sample matrix 更新但沿用旧 sensitivity JSON；
- 只报告 S1 不报告 CI；
- recalibration 在 final test 上拟合并在同一 test 上报告改进。

---

## 10. 值得借鉴的设计

### A. 可以直接借鉴

1. **MAPIE 的 train → conformalize → predict 生命周期分离**
   - 直接借鉴为数据角色契约；
   - 强制 calibration/conformalization set 成为一等数据角色。

2. **SALib 的 samples → results → analysis 状态依赖**
   - samples 一旦变化，旧 result/analysis 失效；
   - 与当前 `math_mode` 的 hash、STALE、checkpoint、promotion 思路完全兼容。

3. **Uncertainty Toolbox 的多维 UQ scorecard**
   - accuracy + calibration + sharpness + proper score；
   - 避免“高 coverage = 好 UQ”的单指标陷阱。

### B. 可以改造后采用

1. **MAPIE exchangeability tests**
   - 原方案面向 conformal validity；
   - `math_mode` 应扩展为 `UQ Assumption Check`，包含时间漂移、covariate shift、分层差异等题目相关诊断；
   - 失败时降级 guarantee，不一定直接否决全部点预测。

2. **Adversarial group calibration**
   - 原实现主要随机抽取不同规模子群；
   - `math_mode` 更应该优先用有语义的 slices：设备、阶段、地区、负载等级、类别、时间窗口、风险分位。

3. **SALib ProblemSpec**
   - 不建议直接复制整个 API；
   - 应借鉴状态失效和协议兼容性，映射到项目自己的 UQ JSON contracts。

### C. 可以作为对照实验

- point-only vs point + conformal interval；
- naive bootstrap interval vs conformal interval；
- average coverage-only vs average + subgroup coverage gate；
- 固定 ±10% one-at-a-time sensitivity vs global Sobol/Morris；
- 单次 Sobol 排名 vs 多 sample budget / 多 seed 稳定性；
- 无 recalibration vs calibration-set recalibration + untouched test；
- 只有 best metric 的 model selection vs uncertainty-aware scorecard。

### D. 不建议采用

- 把 LLM 的“我有 90% 把握”当作模型 uncertainty；
- 用 training loss 直接构造置信区间；
- 统一对所有参数做无来源的 ±5%/±10%；
- 在 final test 上 recalibrate 后仍用同一 test 报告 calibration；
- 只看 average coverage；
- 只看区间宽度；
- 无视 exchangeability/shift 就宣称 conformal 的 nominal guarantee；
- 为了“显得高级”给所有题目强制加 Bayesian/MCMC；
- 在赛时一开始就引入大型 UQ 平台，增加依赖与调试成本。

---

## 11. 存在的问题

### 11.1 MAPIE 的边界

- 主要价值集中在 prediction / risk control，不覆盖所有机理建模与优化问题；
- conformal 的统计保证依赖方法对应的假设，不能泛化成“任何数据分布都保证 95%”；
- calibration/conformalization 会消耗样本，小样本竞赛题必须权衡数据利用率；
- 时序、空间相关、distribution shift 需要方法特定处理；
- v1.5.0 已要求 Python 3.10+，赛时环境兼容性需要单独验证。

### 11.2 Uncertainty Toolbox 的边界

- 当前主要聚焦 regression predictive uncertainty；
- 最近代码 push 在 2025-03-05，本轮不是把它当最新活跃框架；
- 部分 metric 默认依赖 Gaussian mean/std 表达，不适合所有非参数分布；
- adversarial group calibration 的随机 subgroup 机制不能替代业务语义 slice；
- recalibration 改善 calibration 并不等于模型机理更正确。

### 11.3 SALib 的边界

- 参数 bounds / distribution 错了，再精细的 Sobol 也只是精确分析错误输入；
- Sobol 对模型调用次数要求高，昂贵仿真需要预算控制或 surrogate；
- 参数独立性/采样设计假设需要仔细处理；
- 它是分析库，不会自动理解题面里哪个参数应视为随机变量；
- parallel/distributed 相关代码本身有 experimental warning，不应直接当作生产级 scheduler。

### 11.4 对竞赛 Agent 的共同风险

- UQ 很容易变成 token/算力黑洞；
- 如果没有先做 Uncertainty Specification，Agent 会“为了有图而制造不确定性”；
- 如果不给 UQ 结论分级，Writer 很容易把 empirical observation 写成 theoretical guarantee；
- 如果图形层和计算层不分离，Figure Agent 可能在绘图时偷偷重采样，破坏 provenance。

---

## 12. 与 math-mode 对比

| 能力 | math-mode | 本轮项目 | 差异 |
|---|---|---|---|
| 真实执行 | 已强制真实建模、真实敏感性/Monte Carlo 结果落盘 | 三个项目均真实计算 | **保持** math-mode 的强门禁 |
| 不确定性来源登记 | 题面约束/数据审计中可描述，但无统一 UQ schema | SALib 需 problem bounds；UQ 工具需 uncertainty input | **新增** Uncertainty Source Register |
| 数据角色 | 已强调 train/test 隔离 | MAPIE 明确 train/conformalization/test 生命周期 | **改进**：加入 CALIBRATION/CONFORMALIZATION 角色 |
| 预测区间 | 无统一标准流程 | MAPIE 是核心能力 | **新增** predictive-UQ route |
| Calibration 评价 | 无统一 UQ scorecard | UQ Toolbox 有 MACE/RMSCE/miscalibration | **新增** calibration gate |
| Sharpness / 区间信息量 | 无统一门禁 | UQ Toolbox 明确 sharpness / interval score | **新增**，避免靠加宽区间刷 coverage |
| Subgroup/conditional calibration | 当前未形成标准门禁 | MAPIE conditional coverage；UQ Toolbox adversarial group calibration | **新增/改造**为语义场景 slices |
| 方法适用性检查 | Reviewer 有模型合理性要求 | MAPIE 2026 增加 exchangeability tests | **改进**为 UQ assumption status |
| 全局敏感性 | 已要求敏感性/鲁棒性，但方法自由 | SALib 提供 Sobol/Morris/PAWN 等协议 | **改进**为 method-aware experiment contract |
| 灵敏度 CI | 无统一机器要求 | SALib Sobol 返回 bootstrap CI | **新增** sensitivity uncertainty |
| UQ 状态失效 | 有 artifact hash/STALENESS 的研究方案，但 UQ 未落地 | SALib sample 改变即清结果/analysis | **直接借鉴**到 UQ lineage |
| 随机种子 | 当前规范已要求固定并记录 | SALib resampling 支持 seed | **保持并扩展**到所有 UQ run |
| UQ 可视化 | Figure Skill 已有敏感性/区间类绘图能力 | 项目均有/可配可视化 | **保持** Figure Skill，只消费 UQ evidence |
| 论文 claim 门禁 | 已有 QA/结果索引 | 本轮项目不负责竞赛论文 | **改进** Writer 只可引用 `UQ_PASS` evidence |

总体判断：

- **保持**：当前真实运行、结果索引、随机种子、Figure Skill、支撑材料与 SHA 门禁；
- **改进**：train/test → train/calibration/test；普通 sensitivity → experiment-design-aware sensitivity；
- **新增**：UQ Contract、UQ Evidence Pack、Calibration/Assumption Gate、Sensitivity CI/Convergence Gate；
- **替换**：不替换现有 Solver/Reviewer/Figure Skill，只在它们之间补一个 UQ evidence layer；
- **暂不采用**：大型全功能 UQ 平台或所有题目强制 Bayesian workflow。

---

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：设计 `UQ Contract / 不确定性计划` 机器协议

建议未来增加类似：

```text
求解/不确定性计划.json
求解/不确定性结果.json
```

只提出设计，本轮不创建正式文件。

建议 UQ Contract 至少包含：

```json
{
  "uq_id": "uq-q1-001",
  "contract_hash": "...",
  "candidate_id": "...",
  "target": "...",
  "uncertainty_items": [
    {
      "name": "parameter_x",
      "kind": "input|parameter|aleatoric|epistemic|scenario|model_structure",
      "unit": "...",
      "representation": "distribution|bounds|empirical_samples|scenario_set",
      "distribution_or_bounds": "...",
      "dependence": "...",
      "source_evidence_id": "...",
      "authority": "official|measured|literature|estimated|assumed_scenario"
    }
  ],
  "data_roles": {
    "train": "...",
    "calibration": "...",
    "test": "..."
  },
  "method": "...",
  "assumptions": [],
  "sampler": "...",
  "sample_budget": 0,
  "seed": 0,
  "resamples": 0,
  "confidence_levels": [],
  "metrics": [],
  "subgroup_slices": [],
  "validity_checks": []
}
```

最重要的不是字段名，而是**让每个不确定性范围/分布都能追溯来源**。

#### P0-2：建立 Prediction Calibration Gate

预测类问题至少要求：

```text
point accuracy
+ empirical coverage
+ interval width / sharpness
+ proper score
+ subgroup/conditional coverage
+ data-role leak check
+ assumption/shift status
```

若 exchangeability/适用假设无法确认，允许保留经验区间，但必须把论文语言降级成“在当前测试/场景中的经验覆盖”，不得写成无条件保证。

#### P0-3：把 Sensitivity Analysis 变成有状态的 Experiment Contract

至少保存：

```text
parameter spec hash
sample design
sample matrix hash
model/candidate hash
raw results hash
analyzer
N
seed
resamples
confidence level
S1/ST/S2 or other indices
CI
convergence / rank stability
```

如果 bounds、distribution、sample matrix 或 candidate 变化：

```text
old UQ analysis → STALE
```

不能只因为旧 PNG 仍存在就继续用于论文。

#### P0-4：UQ 结果必须先进入结果索引，再进入 Figure Skill

保持当前项目已经正确建立的边界：

```text
UQ code
↓
structured UQ results
↓
UQ QA/Gate
↓
结果索引
↓
academic-figure-skill
↓
论文
```

禁止 Figure Skill 在渲染阶段重新 bootstrap / Monte Carlo / fit conformalizer。

### P1：值得实验

#### P1-1：历史赛题 Prediction-UQ Benchmark

选择有监督预测类往届题，比较：

```text
Point-only
vs
Naive bootstrap interval
vs
Split/Cross conformal interval
```

评价：

- RMSE/MAE；
- coverage；
- mean/median interval width；
- interval score；
- subgroup worst coverage；
- runtime；
- calibration sample cost。

重点不是证明 conformal 总是最好，而是确定它在什么数据量/时序条件下值得赛时使用。

#### P1-2：Sensitivity Convergence Benchmark

对同一模型运行不同 sample budget：

```text
N = 128 / 256 / 512 / 1024 / ...
```

记录：

- S1/ST 排名变化；
- CI width；
- top-k rank stability；
- compute cost；
- 多 seed 变异。

只有 ranking 稳定后，论文才宣称“关键参数”。

#### P1-3：Average Coverage vs Scenario Coverage 对照

按题意定义真实语义 slices，而不是随机 slice：

- 高/低负载；
- 时间早/中/晚；
- 不同设备；
- 不同区域；
- 极端值/普通值。

比较全局 90/95% coverage 与各 slice coverage，验证“总体不错但关键场景失效”是否常见。

### P2：长期考虑

1. 模型结构不确定性：把 15:06 多 candidate/search tree 的多个模型族作为 epistemic/model-structure uncertainty，而不是只选一个 winner 后忘掉其他合理路线；
2. surrogate-assisted UQ：昂贵仿真先建 surrogate，再做大规模 propagation，但必须验证 surrogate error；
3. adaptive sampling：把 19:07 Resource Scheduler 与 UQ 结合，把更多计算预算分给高影响/高不确定区域；
4. uncertainty-aware decision：下一阶段研究 chance constraints / robust optimization，把“不确定性”真正传入决策，而不是只画误差带。

### 不建议采用

- 所有问题默认 MCMC/Bayesian；
- 把任何 ±x% 都叫“置信区间”；
- 只做 one-at-a-time 曲线就声称“全局敏感性”；
- 同一 test set 既用于 recalibration 又用于最终 UQ 报告；
- nominal coverage = empirical coverage；
- 区间越宽越安全的单指标优化；
- 不检查数据漂移就引用理论保证；
- UQ 结果没有 sample/result hash 就进入论文。

---

## 14. 可形成的新 Skill / Agent

只提出设计，不直接创建。

### 14.1 `uncertainty-specification-agent`

职责：

- 从 Problem Contract、数据审计和外部 evidence 中抽取不确定性；
- 区分 probability uncertainty 与 scenario assumption；
- 生成 UQ Contract；
- 检查范围/分布是否有来源。

### 14.2 `uq-experiment-manager`

职责：

- bootstrap / Monte Carlo / conformalization / sensitivity sample orchestration；
- 保存 samples/results/log/hash；
- 维护 UQ state；
- 接入 resource scheduler 和 checkpoint。

### 14.3 `calibration-auditor`

职责：

- coverage；
- sharpness/width；
- proper scoring；
- subgroup/conditional calibration；
- exchangeability/shift diagnostics；
- recalibration leakage 检查。

### 14.4 `sensitivity-auditor`

职责：

- sample/analyzer compatibility；
- sensitivity index CI；
- sample-budget convergence；
- rank stability；
- bounds/distribution provenance。

建议初期不要四个都独立成 LLM Agent。更合理的是：

```text
一个 UQ Planner（LLM/规则混合）
+ 一个 deterministic UQ executor/auditor
```

等实际赛题验证价值后再拆分。

---

## 15. 与历史调研的去重检查

本轮建立的去重集合包含：AI Scientist evidence workflow、AIDE/ML-Master/MLE-Dojo 模型搜索、PaperBench Judge、LangGraph/MS Agent Framework/OpenHands checkpoint、DVC/MLflow/Dagster artifact promotion、Ray/Optuna/Dask scheduler、PaperQA/CiteGuard/DeltaScience citation provenance、ORPilot/CCA/OptiMUS Problem Contract、Hypothesis/CrossHair/VerifAI falsification。

本轮新增且此前没有形成独立结论的内容：

1. **数据角色从 train/test 扩展为 train/calibration/test，并把 conformalization 变成机器状态；**
2. **UQ quality 采用 calibration + sharpness + proper score + subgroup calibration，而不是只看 coverage；**
3. **理论 guarantee 与 empirical interval 分级，并加入 exchangeability/shift validity status；**
4. **Sensitivity sample design 与 analyzer 必须协议兼容；**
5. **Sensitivity index 自身必须带 bootstrap CI 与 sample-budget convergence；**
6. **samples/spec 变化必须自动使 downstream UQ analysis STALE；**
7. **不确定性范围/分布必须有 evidence authority，无法概率化时标记 scenario，而不是伪造 distribution。**

与 22:06 的关系：

- Falsification 负责寻找“存在一个失败案例”；
- UQ 负责量化“结果在分布/参数空间里如何变化、区间是否校准、哪些因素贡献最大”。

两者互补但不可替代，因此本轮不存在通过改写措辞重复上轮的问题。

本轮三个重点仓库均未出现在此前 `research/INDEX.md`，不存在旧项目重访问题。

---

## 16. 下一轮推荐方向

优先推荐：

**Robust Optimization / Chance-Constrained Decision Agent：如何把 UQ Evidence 真正编译成决策约束。**

研究问题：

- chance-constrained optimization；
- robust optimization；
- distributionally robust optimization；
- scenario optimization；
- feasibility probability；
- CVaR / tail-risk；
- uncertain Pareto front；
- nominal optimum vs robust optimum；
- 如何把 UQ Contract 中的 parameter/source/coverage 直接映射为优化约束；
- 如何验证“鲁棒方案”不是靠极端保守性换来的。

原因：到本轮为止，`math_mode` 的研究链已经逐步覆盖：

```text
题面合同
→ 多路线模型搜索
→ 真实执行
→ artifact/candidate provenance
→ checkpoint/resource scheduling
→ counterexample falsification
→ reviewer calibration
→ external citation evidence
→ uncertainty quantification
```

下一步最自然的问题是：

> 已经知道结果有多不确定之后，Agent 应如何据此改变最终决策，而不是只在论文里增加一段“敏感性分析”？

---

## 17. Sources

### A. math_mode 当前基线：已读取源码/文档

1. `README.md`（当前 `main`）  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/README.md
2. `AGENTS.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/AGENTS.md
3. `CLAUDE.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/CLAUDE.md
4. `.agents/skills/academic-figure-skill/SKILL.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/.agents/skills/academic-figure-skill/SKILL.md
5. `华为杯_求解规范/华为杯_求解规范.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/华为杯_求解规范/华为杯_求解规范.md
6. `华为杯_求解规范/华为杯_绘图规范.md`  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/华为杯_求解规范/华为杯_绘图规范.md
7. `research/INDEX.md` 与 22:06 Counterexample/Falsification 报告，用于去重。  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/research/INDEX.md  
   https://github.com/shaxiaoguang123/math_mode/blob/cc1846612d7adec743caf1de7cde3632cb2722f2/research/2026-09-08/2026-09-08_22-06_counterexample-falsification.md

### B. MAPIE：已读取官方仓库、源码与 Release

8. Repository / README（固定 commit `4105fc5...`）  
   https://github.com/scikit-learn-contrib/MAPIE  
   https://github.com/scikit-learn-contrib/MAPIE/blob/4105fc5ce81359b6ea276c8bb09a8cabdfae7b30/README.md
9. `mapie/regression/regression.py` — Split/Cross conformal 与 Jackknife-after-Bootstrap  
   https://github.com/scikit-learn-contrib/MAPIE/blob/4105fc5ce81359b6ea276c8bb09a8cabdfae7b30/mapie/regression/regression.py
10. Exchangeability testing implementation  
    https://github.com/scikit-learn-contrib/MAPIE/tree/4105fc5ce81359b6ea276c8bb09a8cabdfae7b30/mapie/exchangeability_testing
11. MAPIE v1.5.0 Release（2026-08-05）  
    https://github.com/scikit-learn-contrib/MAPIE/releases/tag/v1.5.0

### C. Uncertainty Toolbox：已读取官方仓库与源码

12. Repository / README（固定 commit `6ea1fed...`）  
    https://github.com/uncertainty-toolbox/uncertainty-toolbox  
    https://github.com/uncertainty-toolbox/uncertainty-toolbox/blob/6ea1fed6591923a95d49d8049a197e33d4d8092d/README.md
13. `uncertainty_toolbox/metrics.py`  
    https://github.com/uncertainty-toolbox/uncertainty-toolbox/blob/6ea1fed6591923a95d49d8049a197e33d4d8092d/uncertainty_toolbox/metrics.py
14. `uncertainty_toolbox/metrics_calibration.py`  
    https://github.com/uncertainty-toolbox/uncertainty-toolbox/blob/6ea1fed6591923a95d49d8049a197e33d4d8092d/uncertainty_toolbox/metrics_calibration.py
15. `uncertainty_toolbox/recalibration.py`  
    https://github.com/uncertainty-toolbox/uncertainty-toolbox/blob/6ea1fed6591923a95d49d8049a197e33d4d8092d/uncertainty_toolbox/recalibration.py

### D. SALib：已读取官方仓库与源码

16. Repository / README（固定 commit `aa2c554...`）  
    https://github.com/SALib/SALib  
    https://github.com/SALib/SALib/blob/aa2c5545b3bfd0a982e9fad7625070a8ea340d38/README.rst
17. `src/SALib/util/problem.py` — ProblemSpec / sample-result-analysis state  
    https://github.com/SALib/SALib/blob/aa2c5545b3bfd0a982e9fad7625070a8ea340d38/src/SALib/util/problem.py
18. `src/SALib/analyze/sobol.py` — Sobol indices、resampling、confidence interval、seed  
    https://github.com/SALib/SALib/blob/aa2c5545b3bfd0a982e9fad7625070a8ea340d38/src/SALib/analyze/sobol.py

### E. 仅外部说明 / 未作为核心证据

本轮核心结论没有依赖博客、知乎、Reddit 或搜索摘要。`SURGroup/UQpy` 仅做了补充仓库结构检查（确认其覆盖 distribution / inference / reliability / sampling / sensitivity / stochastic process / surrogate 等模块），没有把未深入到具体算法源码的内容写成核心结论，因此不列入本轮 3 个重点项目。
