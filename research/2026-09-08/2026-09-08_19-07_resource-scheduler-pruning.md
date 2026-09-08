# MathModel Agent Research

## 1. 本轮研究主题

**赛时 Multi-Agent Resource Scheduler：把“候选模型搜索”进一步拆成可审计的时间/CPU/GPU 调度、低价值候选自动剪枝、资源动态再分配与故障回收。**

本轮重点回答一个此前只提出过、但尚未代码级展开的问题：

> 当 `math_mode` 已经能够产生多个候选模型、并行执行、保存 candidate artifact、进行 Reviewer 验证和 canonical promotion 后，48–72 小时赛时究竟应该由谁决定“哪个任务先跑、给多少 CPU/GPU、什么时候暂停/终止、失败资源何时回收、剩余时间不足时哪些探索必须停止”？

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的对象：

1. `ray-project/ray`：Ray Tune 的 ASHA early stopping、`ResourceChangingScheduler`、TopJob 动态资源分配、并发/总时间预算；
2. `optuna/optuna`：Hyperband/SHA pruning、trial state、heartbeat 与 stale trial 回收；
3. `dask/distributed`：task priority、resource restrictions、scheduler queue、基于计算/通信成本的 transactional work stealing。

本轮核心结论是：

> `math_mode` 不应把“搜索策略”“实验执行”“资源调度”混成一个 Agent。更稳妥的结构是 **两级调度器**：上层 Candidate Scheduler 按赛时预算、模型价值和中间证据决定 CONTINUE / PAUSE / PRUNE / REALLOCATE；下层 Task Scheduler 按依赖 DAG、优先级和 CPU/GPU/内存资源执行具体代码、复算、绘图和验证任务。科学结论仍由 Validation / Promotion Gate 决定，Resource Scheduler 只决定“算什么、何时算、算多久、占多少资源”。

建议目标结构：

```text
赛题依赖 DAG + 剩余赛时 + 资源清单 + Candidate Registry
                     ↓
        Candidate / Experiment Scheduler
  ┌────────────────────────────────────────────┐
  │ route value / evidence gap / cost estimate │
  │ grace period / prune / pause / reallocate  │
  └────────────────────────────────────────────┘
          ↓ task contract              ↑ intermediate evidence
        Task Scheduler ────────────────┘
  priority / deps / CPU / GPU / memory / timeout
          ↓
  CPU workers / GPU workers / sandbox
          ↓
 candidate artifact → Validation Gate → Promotion Gate
          ↓
 canonical snapshot → 结果索引 → 图表 → 论文
```

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

当前 `research/INDEX.md` 已覆盖：

- 14:00：evidence-first 科研工作流；
- 15:06：模型候选树、MCTS/UCT、并行实验、预算感知；
- 16:04：Reviewer / Judge 可执行与可校准验证；
- 17:07：Memory / Checkpoint / Resume；
- 18:04：candidate artifact ownership、stale-write prevention、canonical promotion。

15:06 已经提出 `search-budget-controller`，并指出要记录“剩余赛时、token、CPU/GPU、最大实验数、explore→exploit 切换”；18:04 又提出下一轮研究 resource scheduler。但此前仍缺少以下代码级答案：

1. 中间结果到什么程度才能安全 early stop，而不是因为“前几步暂时差”误杀最终优秀路线；
2. 低价值候选被终止后，释放出的 CPU/GPU 怎样动态分配给更有价值候选；
3. 搜索层的“好候选”与执行层的“当前可运行任务”如何分离；
4. 多个任务同时 ready 时，应该按 FIFO、关键路径、用户优先级还是资源匹配调度；
5. worker/进程崩溃后，怎样识别 stale RUNNING 状态并回收资源；
6. work stealing / task migration 哪些任务可以做，哪些有副作用的 promotion/canonical write 绝对不能迁移或重复执行；
7. 如何对 Scheduler 自身做回归测试，避免“为了省算力”反而把真正最优路线提前剪掉。

因此，本轮不重复“需要预算控制”这一旧结论，而是研究 **Budget Controller 的执行语义、状态机和安全边界**。

### 2.2 当前 math_mode 已有什么，缺什么

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、`.agents/skills/` 和近期 research 后确认：

当前已有：

- 题面阶段要求识别时间、CPU/GPU 等硬约束；
- 明确的 `Baseline → 主模型 → 必要改进 → 独立验证 → 敏感性/稳健性` 事实链；
- `求解/结果索引.md`、视觉计划、支撑材料和 SHA-256 审计；
- 研究层已经提出 Candidate Registry、Experiment Journal、Checkpoint、Reviewer、Promotion Gate；
- `.agents/skills/` 当前正式项目级 skill 仍主要是 `academic-figure-skill`，尚无正式 resource scheduler skill/agent。

当前尚未形成机器可读的：

- task dependency DAG / criticality；
- CPU/GPU/内存/许可证等 resource request；
- global deadline / per-task timeout / reserve time；
- `READY / RUNNING / PAUSED / PRUNED / TIMEOUT / STALE / CANCELLED` 等统一执行状态；
- intermediate progress signal；
- pruning policy / grace period；
- runtime estimator；
- resource reallocation policy；
- heartbeat / stale-running recovery；
- scheduler decision log；
- false-prune regression benchmark。

这意味着当前 `math_mode` 能规定“正确结果必须怎样产生和验收”，但还不能在算力有限、任务很多且时间固定时可靠地决定 **先算什么、停止什么、把资源转给谁**。

## 3. 搜索范围与关键词

本轮轮换到 P2“底层 orchestration / task scheduling”，但只研究直接服务数学建模赛时效率与结果真实性的机制。

主要关键词：

- competition agent resource scheduler
- deadline aware experiment scheduling
- trial early stopping ASHA
- dynamic resource allocation top trial
- hyperband pruning intermediate metric
- heartbeat stale trial recovery
- task priority dependency DAG
- CPU GPU resource restrictions
- work stealing compute communication ratio
- transactional task migration
- scheduler queue saturation
- time budget concurrent trials
- low value candidate termination

优先阅读：

- GitHub 官方仓库元数据；
- Ray Tune `async_hyperband.py`、`resource_changing_scheduler.py`；
- Optuna `pruners/_hyperband.py`、`storages/_heartbeat.py`、`trial/_state.py`；
- Dask `distributed/stealing.py`、scheduler priority/resource restriction 代码；
- Ray / Optuna / Dask 官方文档；
- ASHA / Hyperband 原论文作为算法背景。

本轮没有把 Kubernetes、Slurm、Airflow 等通用基础设施作为主要对象，因为当前 `math_mode` 更需要的是赛时“候选实验 + Python 任务”层的轻量调度语义，而不是先建设集群平台。

## 4. 新发现项目

### 项目 1：Ray / Ray Tune

- 名称：Ray / Ray Tune
- Repository：https://github.com/ray-project/ray
- Stars：43,739（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T10:52:57Z`；`pushed_at=2026-09-08T01:32:42Z`
- 目标：分布式 AI 计算运行时以及训练、调参、服务等上层库。
- 核心能力：Trial Scheduler、ASHA early stopping、固定/动态 trial resources、Placement Group、并发限制、总时间预算、checkpoint-aware pause/resume。
- 本轮实际阅读：
  - `python/ray/tune/schedulers/async_hyperband.py`
  - `python/ray/tune/schedulers/resource_changing_scheduler.py`
  - `python/ray/tune/tune_config.py` 相关搜索结果
  - Ray Tune Trial Scheduler / stopping / resource 官方文档

对 `math_mode` 最有价值的是：**trial 的搜索价值判断和 CPU/GPU 分配是两个独立但可组合的调度维度。**

### 项目 2：Optuna

- 名称：Optuna
- Repository：https://github.com/optuna/optuna
- Stars：14,759（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T10:03:02Z`；`pushed_at=2026-09-07T06:56:15Z`
- 目标：超参数优化与并行 trial 管理。
- 核心能力：sampler、pruner、Hyperband/SHA、trial state、RDB storage、heartbeat、stale trial failure/retry hooks。
- 本轮实际阅读：
  - `optuna/pruners/_hyperband.py`
  - `optuna/storages/_heartbeat.py`
  - `optuna/trial/_state.py`
  - 官方 pruning / Hyperband 文档

对 `math_mode` 最有价值的是：**PRUNED 与 FAIL 必须是不同状态；运行中的 trial 还需要 heartbeat 证明它仍然真实存活。**

### 项目 3：Dask Distributed

- 名称：Dask Distributed
- Repository：https://github.com/dask/distributed
- Stars：1,690（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-07T07:33:44Z`；`pushed_at=2026-09-08T08:23:57Z`
- 目标：Dask 的分布式动态任务调度器。
- 核心能力：task state machine、priority、worker/resource restrictions、scheduler queue、work stealing、数据 locality、worker occupancy。
- 本轮实际阅读：
  - `distributed/stealing.py`
  - `distributed/scheduler.py` 中 priority / resource restriction 相关源码检索
  - Work Stealing / Prioritizing Work / Worker Resources / Scheduler State Machine 官方文档

对 `math_mode` 最有价值的是：**调度不能只看“谁空闲”，还必须考虑依赖数据搬运成本、task priority、资源约束和任务是否已经开始执行。**

## 5. 深入架构分析

### 5.1 Ray ASHA：不要让每个候选都跑满预算

Ray `AsyncHyperBandScheduler` 在每次 `on_trial_result()` 收到中间结果时决定 `CONTINUE` 或 `STOP`。核心参数不是某个特定 ML 模型，而是通用的：

```text
time_attr           进度单位，可是 iteration，也可以是 wall-clock 或自定义单调进度
metric              中间目标指标
max_t               单 trial 最大资源/进度
min/grace_period    至少运行到这个阶段再允许停止
reduction_factor    每个 rung 保留比例
```

源码 `_Bracket.on_result()` 会在 milestone 到达后，用同 rung 已记录 trial 的分位 cutoff 判断当前候选是否停止。默认 `reduction_factor=4` 时，每轮大致只保留较好的约 1/4 候选。

对 `math_mode` 的直接启发不是“照搬准确率做 ASHA”，而是建立 **Intermediate Evidence Contract**：只有某个模型确实存在可比较的阶段性证据时才允许被 prune。

例如：

```text
可安全作为阶段证据的候选：
- 迭代优化：迭代次数 → 当前目标值/约束违反量
- 神经网络：epoch → 固定 validation split 指标
- Monte Carlo：样本数 → 估计均值 + CI 宽度
- 参数扫描：已完成场景比例 → 当前稳健性统计

不应直接用来 prune：
- 只跑了训练集 loss，但最终评价依赖独立测试集
- 不同候选使用了不同数据切分
- 早期阶段尚未满足约束，后期算法本来会修复
- 多目标问题只看其中一个 metric
```

也就是说，赛时节省算力必须服从“可比较性”和“结果真实性”，不能反过来。

### 5.2 Grace period 是防止“慢启动好模型”被误杀的安全阀

Ray ASHA 的 `grace_period` 和 Optuna Hyperband 的 `min_resource` 都表达同一个原则：

> 在证据还不足时，不允许因为中间指标暂时落后就杀死候选。

对数学建模尤其重要，因为很多方法具有不同的启动成本：

- MILP / MINLP 前期可能先做 presolve；
- 贝叶斯/群智能算法早期指标波动大；
- 有复杂特征构造的模型前期耗时但后期更强；
- 数值 PDE / 仿真要先完成网格或初始化；
- bootstrap / sensitivity analysis 只有达到一定重复数后统计才稳定。

因此 `math_mode` 不应设置一个全局统一的“运行 10% 就剪枝”，而应让每种 route family 声明：

```text
progress_unit
grace_period
comparison_metric
comparison_direction
minimum_evidence_count
hard_constraints_to_check_before_prune
```

### 5.3 Ray ResourceChangingScheduler：停止差候选之外，还可以把释放的资源转给好候选

Ray `ResourceChangingScheduler` 不是另一个搜索器，而是**包装一个 base scheduler**：先由 ASHA/FIFO 等决定 trial 是否继续，再调用 `resources_allocation_function` 决定是否改变 live trial 的 CPU/GPU 请求。

源码中有两个很值得区分的策略：

1. `DistributeResources`：把可用资源较均匀地分配给 live trials；
2. `DistributeResourcesToTopJob`：把空闲资源集中到当前表现最好的 trial。

资源变更不是直接在正在执行的 trial 上“硬改”：如果新资源不同，scheduler 会让 trial `PAUSE`，待其不再 `RUNNING` 后更新资源，再重新运行。这也解释了官方文档为什么强调 trainable 应支持 checkpoint。

对 `math_mode` 的映射：

```text
候选 A/B/C 都有最低保底资源
      ↓ 中间 evidence
A 明显无希望 → PRUNE → 释放 4 CPU
B 仍有创新价值 → 保持 2 CPU
C 已证明高价值且可并行 → 增加到 6 CPU / 1 GPU
```

但 **TopJob 不能直接照搬**：华为杯不是 Kaggle 单指标。资源增配应该基于 `MathModel Score Card + route diversity + hard-gate status`，而不是只看一个 validation score，否则会过早形成“赢家通吃”，把结构完全不同但潜在更好的路线饿死。

### 5.4 Ray 的 time budget / concurrency 是全局边界，不等于每个 trial timeout

Ray Tune 的配置同时提供：

- `max_concurrent_trials`：并发 trial 上限；
- `time_budget_s`：整个 tuning run 的时间预算；
- per-trial scheduler/stopper：单候选的早停规则。

这给 `math_mode` 一个必须明确的三层时间语义：

```text
Competition Deadline   整场比赛硬截止
Phase Reserve          留给验证/图表/论文/最终审计的保留时间
Task / Trial Budget    单个实验/复算/绘图任务 timeout 或 max progress
```

如果只给每个 Python 脚本设置 timeout，没有全局 reserve，Agent 仍可能在比赛最后阶段同时启动 10 个“有趣但来不及验收”的模型。

### 5.5 Optuna Hyperband：固定预算下要同时探索“多而浅”和“少而深”

Optuna `HyperbandPruner` 将多个 `SuccessiveHalvingPruner` 作为不同 bracket。它解决的是有限预算 `B` 下一个基本矛盾：

- 多跑候选 → 每个候选得到的资源少；
- 每个候选跑得深 → 能探索的候选数量少。

源码还暴露两个对赛时很重要的工程事实：

1. `max_resource="auto"` 时，在最初完整 trial 还没告诉系统最大进度前，无法真正 prune；
2. bracket 分配与 `study_name + trial.number` 绑定，官方明确建议固定 `study_name` 以提高 reproducibility。

对 `math_mode` 的启发：模型搜索必须先知道“这个 route 的预算单位是什么”。如果连最大迭代/场景数/样本数都不知道，就无法设计可靠的 early stopping。

### 5.6 Optuna：PRUNED、FAIL、WAITING、RUNNING 不能混成“没成功”

Optuna `TrialState` 明确区分：

```text
WAITING
RUNNING
COMPLETE
PRUNED
FAIL
```

这比常见的 `success=false` 更适合 `math_mode`：

- `PRUNED`：算法正常、证据不足以继续投入资源；
- `FAIL`：代码/环境/数值错误；
- `TIMEOUT`：到达本 task 时间预算；
- `STALE`：worker 已死但状态仍显示 RUNNING；
- `CANCELLED`：因为全局赛时策略主动取消；
- `PAUSED`：准备换资源或等待高优先级任务。

这些状态的后续处理完全不同。`PRUNED` 不应该进入 debug queue；`FAIL` 可能值得 debug；`CANCELLED` 可能在时间充足时重新排队。

### 5.7 Optuna Heartbeat：失败资源必须能自动回收

`optuna/storages/_heartbeat.py` 中，运行 trial 会周期写 heartbeat；`fail_stale_trials()` 会找到长时间没有心跳的 trial，并尝试将其状态改成 `FAIL`。若其他进程已经完成了状态变更，代码捕获 finished-trial update conflict，而不是再次覆盖。

这对赛时非常实际：

```text
Agent 认为：candidate-17 仍 RUNNING，占 1 GPU
现实：Python 进程已崩溃 40 分钟
结果：GPU/调度配额被“幽灵任务”占住
```

因此 Candidate Scheduler 必须有 liveness，不应只相信“我之前启动过这个 subprocess”。

### 5.8 Dask：task-level scheduler 与 candidate-level scheduler解决的是不同问题

Ray/Optuna 更像“一个候选实验是否值得继续”；Dask 更像“一个 DAG 中现在有几十个 ready task，应派哪个 worker”。

Dask 的 scheduler state 中存在 `waiting / no-worker / queued / processing / memory / erred / forgotten` 等状态；其 priority 逻辑综合用户优先级、提交 generation 和图结构排序；同时 task 可以声明 worker/resource restrictions，例如某任务必须需要 GPU 或只能去特定 worker。

对 `math_mode` 的映射：

```text
Candidate C 仍值得继续       ← Candidate Scheduler
          ↓
C 当前需要：
  1. 训练模型（GPU）
  2. 读取缓存数据（CPU+大内存）
  3. 独立复算（CPU）
  4. 结果图（CPU）
          ↓
这些 task 的具体派发          ← Task Scheduler
```

因此不应让 `model-search-agent` 自己负责进程池、GPU 锁、task priority 和 worker crash recovery。

### 5.9 Dask Work Stealing：空闲 worker 不代表所有任务都应该迁移

Dask 的 Work Stealing 不是简单的“谁空闲就把任务搬过去”。源码 `steal_time_ratio()` 显式估计：

```text
compute_time
vs
依赖数据传输时间 = nbytes / bandwidth + latency
```

只有计算相对通信成本足够大时，任务才值得被 steal；任务还按 cost ratio 分桶。

这对数模 Agent 很重要：如果一个任务依赖几十 GB 中间矩阵或大型模型 checkpoint，把它迁到空闲 worker 可能比原地等更慢。

更关键的是 Dask 的迁移是**事务式**的：scheduler 先向原 worker 发 `steal-request`，并用唯一 `stimulus_id` 对应确认；如果原 worker 已经开始执行，迁移被拒绝；如果回复已过期，scheduler 记录 stale response 而不盲目执行。

这说明 `math_mode` 的 speculative execution / task migration 必须先区分副作用：

- 可以迁移/重试：纯计算、只读输入、输出写独立 candidate path 的任务；
- 不应自动重复：canonical promotion、结果索引写入、支撑材料发布、最终论文写入等有外部状态变化的动作。

## 6. Agent / Skill 设计

本轮三套系统共同表明：resource scheduling 更适合作为**基础设施 Agent/Service**，而不是人格化“资源经理聊天 Agent”。

建议抽象：

```text
Search Policy
  只回答：下一条候选路线是什么？
        ↓
Candidate Scheduler
  只回答：CONTINUE / PAUSE / PRUNE / REALLOCATE / CANCEL？
        ↓
Task Scheduler
  只回答：哪个 READY task 先运行、放到哪个资源槽？
        ↓
Executor
  真正运行 Python / R / MATLAB / solver / figure job
        ↓
Validation + Artifact Registry
  决定结果能否被信任和晋级
```

### A. 可以直接借鉴

- 明确 task/trial 状态机；
- 任务声明 resource request，而不是由 Agent 临时猜；
- global time budget 与单任务 timeout 分离；
- `grace_period` / `min_resource` 防止 premature pruning；
- 中间结果通过统一 report channel 进入 scheduler；
- heartbeat / liveness 自动回收幽灵任务；
- scheduler decision 写 append-only log；
- task migration 采用 request/confirm，并拒绝 stale response；
- 副作用任务禁止自动重复。

### B. 可以改造后采用

Ray/Optuna 的单 metric pruning 需要改造成 **MathModel Progress Signal**：

```text
progress
primary_metric
constraint_violation
validation_protocol_id
numerical_status
runtime_s
peak_memory
uncertainty_or_ci
```

只有 `validation_protocol_id` 一致、hard constraint 口径一致的候选才可以同 rung 比较。

`DistributeResourcesToTopJob` 应改成：

```text
eligible = hard_gate_pass && evidence_comparable
priority = expected_value / estimated_remaining_cost
           + downstream_blocking_bonus
           + route_diversity_bonus
           + deadline_urgency
```

具体公式可以后续实验，不建议现在硬编码一个权重。

### C. 可以作为对照实验

- FIFO vs dependency/criticality priority；
- 不剪枝 vs ASHA-like pruning；
- fixed resource vs dynamic reallocation；
- single-metric pruning vs hard-gate + score-card pruning；
- work stealing on/off；
- heartbeat off/on；
- aggressive early stop vs route-specific grace period。

### D. 不建议采用

- 在当前单机/有限硬件场景一开始就强依赖 Ray+Dask 集群部署；
- 把 Kaggle accuracy/loss 直接当华为杯统一 pruning metric；
- 赢家通吃式 TopJob，导致不同模型家族过早失去最低探索预算；
- 对没有 checkpoint 的任务动态缩放资源；
- 自动重跑具有 canonical write / 外部副作用的任务；
- 把“任务被剪掉”解释成“模型被证明错误”。PRUNED 只代表在当前预算与当前证据下不再继续投入。

## 7. Workflow

建议的赛时两级 workflow：

```text
[0] 建立比赛总 deadline 与不可占用 reserve
        ↓
[1] 从题面生成 Question DAG
        ↓
[2] Candidate Search 产生候选
        ↓
[3] Candidate Manifest 声明
    - deps
    - progress unit
    - grace period
    - resource profile
    - checkpointable?
    - prunable?
        ↓
[4] Task Scheduler 派发 READY task
        ↓
[5] Executor 周期报告 intermediate evidence + heartbeat
        ↓
[6] Candidate Scheduler 决策
    CONTINUE / PAUSE / PRUNE / REALLOCATE / CANCEL
        ↓
[7] 释放/重新分配 CPU/GPU
        ↓
[8] COMPLETE candidate → Validation Gate
        ↓
[9] PASS → Promotion Gate → canonical
        ↓
[10] deadline 接近 reserve 边界
     禁止新增长周期探索，只允许验证、补证据、图表、论文和审计
```

这里最重要的是第 10 步：是否还能启动新候选，不应由 LLM 主观“感觉还有时间”，而应由：

```text
remaining_time
estimated_candidate_cost
estimated_validation_cost
estimated_paper_and_final_qa_reserve
```

共同决定。

## 8. Code Execution / Tools

### Ray

- 真正启动/管理 trial；
- 支持 CPU/GPU/custom resource；
- ASHA 可根据 `tune.report()` 中间结果早停；
- ResourceChangingScheduler 可以 pause 后修改资源；
- PlacementGroup 可以表达多 bundle 资源需求；
- 有 global time budget / max concurrency；
- 需要 trainable 对 checkpoint/resource change 有适配能力。

### Optuna

- 本身负责 study/trial/pruning 状态和存储，不是完整 sandbox；
- objective 内真实运行用户代码；
- `report()` / `should_prune()` 提供中间结果早停接口；
- RDB/heartbeat 支持多进程优化存活检测；
- 不负责像 Dask 那样做 task-level data-locality scheduling。

### Dask Distributed

- 真正运行 Python task graph；
- scheduler 管依赖、worker、task state；
- 支持 user priority / resource restrictions；
- work stealing 动态平衡 worker；
- 对任务迁移考虑 data transfer 与 compute cost；
- 对有副作用任务仍需要上层系统约束幂等性。

### 对 math_mode 的实现边界

近期更合理的是先实现一个**轻量 local scheduler contract**，后端初期可以是：

```text
subprocess + ProcessPoolExecutor + GPU semaphore
```

而不是先引入完整 Ray/Dask。只要 contract 设计成可替换 backend，未来任务规模需要时再接 Ray/Dask。

## 9. QA / Reviewer / Verification

本轮最重要的新 QA 结论是：**Scheduler 自己也需要 benchmark。**

如果一个 pruning policy 节省了 70% 计算，但经常把最终最优模型在早期剪掉，它对竞赛是负收益。

建议建立 `Scheduler Regression Suite`，至少测：

### 9.1 False-prune audit

在历史题/小规模 benchmark 中：

1. 一部分 trial 完整跑到底，得到 final ranking；
2. 用 scheduler 模拟当时中间 evidence；
3. 统计本应进入最终 Top-K 的 trial 有多少被提前 PRUNE。

核心指标：

```text
false_prune_rate
compute_saved_ratio
best_final_candidate_survival
wall_clock_saved
```

### 9.2 Deadline success

不是只测“平均快了多少”，还要测：

```text
在固定 deadline 前：
- 是否至少得到 1 个 complete + validated + promotable 主路线？
- 是否保留足够时间做独立验证？
- 是否留出论文/图表/最终审计 reserve？
```

### 9.3 Resource leak / ghost task

故意 kill worker/subprocess，验证：

- heartbeat 过期后是否标记 STALE/FAIL；
- CPU/GPU token 是否释放；
- candidate artifact 是否保持非 canonical；
- checkpointable task 是否可重排；
- 非幂等任务是否禁止自动重试。

### 9.4 Pruning evidence correctness

Reviewer 应检查：

- 同 rung 候选是否使用同一个 validation protocol；
- metric 是否同方向/同单位；
- 是否有 data leakage；
- hard constraint 是否先检查；
- intermediate metric 是否真的对 final outcome 有预测意义。

因此 Reviewer 不是 Scheduler 的下属：Scheduler 只能基于 Reviewer/Checker 已批准的可比较 evidence 做 prune。

## 10. 值得借鉴的设计

### 10.1 搜索与调度必须解耦

15:06 的 `search-budget-controller` 可以保留，但应进一步拆成：

```text
Search Budget Policy
- 还要不要探索新路线？

Resource Scheduler
- 已有任务谁先跑、给多少资源、何时停？
```

这避免搜索 Agent 因为“喜欢某个模型”直接抢占 GPU。

### 10.2 资源是 vector，不是一个数字

任务至少可能需要：

```text
CPU cores
GPU count / GPU class
RAM
local disk / temp disk
license / external solver slot
network/data-locality
```

即使近期实现只支持 CPU/GPU，也应该让 schema 预留 generic resource map。

### 10.3 Intermediate evidence 必须是一等产物

早停的依据不能只存在 stdout。每次 report 应进入实验账本，例如：

```json
{
  "candidate_id": "q2-c17",
  "step": 12,
  "progress_unit": "epoch",
  "metric": 0.843,
  "validation_protocol_id": "vp-03",
  "constraint_violation": 0,
  "runtime_s": 418.2,
  "resource_snapshot": {"CPU": 4, "GPU": 1}
}
```

这样 PRUNE 决策才能追溯。

### 10.4 动态资源分配必须和 checkpoint 绑定

Ray 的资源变化通过 PAUSE / checkpoint / resume 才可靠。对 `math_mode`：

- 可 checkpoint 的迭代模型：允许缩放/暂停；
- 不能 checkpoint 的黑盒求解：宁可固定资源跑完或取消，不要假装可以无损 PAUSE。

### 10.5 Work stealing 只用于纯任务

18:04 已建立 candidate ownership 思路，本轮补上更明确的 scheduler 规则：

```text
side_effect_class = PURE / CANDIDATE_WRITE / CANONICAL_WRITE
```

- PURE：可 retry / steal；
- CANDIDATE_WRITE：仅在独立 candidate namespace 内幂等时可 retry；
- CANONICAL_WRITE：禁止 speculative duplicate / work stealing 式重复执行，只能走 Promotion Gate。

## 11. 存在的问题

### Ray

- 完整依赖和运行时相对重；
- `ResourceChangingScheduler` 仍是 beta/实验性质接口；
- TopJob 假定可以用单 metric 判断“最好”，不适合直接迁移到多目标数学建模；
- 动态资源变更要求任务支持 checkpoint/resume；
- ASHA 可能误杀慢启动候选，尤其当中间 metric 与最终得分弱相关时。

### Optuna

- pruner 主要针对可迭代、可 report 中间值的 objective；
- `should_prune()` 文档明确不支持 multi-objective trial 的直接 pruning；
- Hyperband 的 bracket / TPE startup 会消耗一定 trial 数，超小预算下未必划算；
- heartbeat 解决“进程是否活着”，不验证它是否逻辑卡死或数值失真。

### Dask

- work stealing 是性能优化，不保证对所有 workload 更快；
- resource annotation 是调度约束，不等价于实时 GPU 显存/RAM 精确监控；
- 分布式调度本身增加部署与调试复杂度；
- task migration 在 worker death/network failure 情况下仍可能出现重复执行风险，因此不能依赖 Dask 替代上层幂等/ownership 设计。

### 对 math_mode 的共同风险

- 过度自动剪枝会降低创新性；
- 若 runtime estimate 错误，deadline scheduling 可能比 FIFO 更差；
- 如果 scheduler 直接读取未经验证的 metric，会放大数据泄漏或错误评测；
- 太复杂的调度层可能在比赛现场成为新的故障源。

因此近期设计原则应是：**先可审计，再智能；先单机可靠，再分布式。**

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 比赛总 deadline | 有人工/规范层时间意识，但无统一机器预算对象 | Ray 有 `time_budget_s` 等全局边界 | math-mode 应新增全局 Deadline/Budget Contract |
| 并发上限 | 研究中提出并行候选，正式 workflow 未统一实现 | Ray 有 `max_concurrent_trials`；Dask 有 worker capacity | 需要显式 concurrency policy |
| Early stopping | 研究中有“失败分支停止”，无通用中间证据协议 | Ray ASHA、Optuna Hyperband/SHA | 新增 Progress Signal + grace period |
| 动态资源再分配 | 无 | Ray `ResourceChangingScheduler` | 值得改造实验，不宜直接上 TopJob |
| Trial 状态 | Candidate/Checkpoint 概念已有，但正式状态未统一 | Optuna WAITING/RUNNING/COMPLETE/PRUNED/FAIL | 建议扩展为竞赛执行状态机 |
| Heartbeat | 无统一机制 | Optuna stale heartbeat → FAIL | P0 应加入 worker/task liveness |
| Task DAG 优先级 | 题目有问题依赖，但未编译为调度 priority | Dask user priority + graph ordering | 可把 question dependency / evidence gap 编译为 priority |
| Resource restriction | Phase 1 会记录 CPU/GPU 限制 | Ray/Dask 都支持 per-task/trial resources | 应变成机器可读 Task Contract |
| Work stealing | 无 | Dask 按 compute/communication cost迁移任务 | 只适用于纯/幂等 candidate task |
| Stale response 防护 | 18:04 有 stale promotion guard | Dask steal 使用 unique stimulus_id 拒绝 stale reply | 两者可统一采用 expected-state/version 思想 |
| Scheduler QA | 无 | 三项目本身有测试，但不面向数模 false-prune | math-mode 应自建 Scheduler Regression Suite |
| Canonical 事实写入 | 已研究 Promotion Gate | 三项目主要关注执行/调优 | **保持**：Scheduler 不得绕过 Promotion Gate |

总体判断：

- **保持**：现有 evidence-first、Validation Gate、Candidate Registry、Promotion Gate；
- **改进**：15:06 的 Budget Controller，拆成 Search Policy + Resource Scheduler；
- **新增**：Task Contract、Progress Signal、Heartbeat、Scheduler Decision Log、false-prune regression；
- **替换**：不替换现有求解/验证主链，只在 Executor 前增加调度层；
- **暂不采用**：强依赖 Ray/Dask 集群作为默认运行时。

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：`Resource / Task Contract`

建议概念 schema：

```text
task_id
candidate_id
question_id
stage
dependencies
priority_class
resource_request {CPU, GPU, RAM, custom...}
expected_runtime_s
timeout_s
checkpointable
prunable
progress_contract_id
side_effect_class
retry_policy
```

它应放在 **Executor 上一层、Candidate Registry 下一层**。

#### P0-2：统一执行状态机

建议至少：

```text
WAITING
READY
RUNNING
PAUSED
PRUNED
COMPLETED
FAILED
TIMEOUT
STALE
CANCELLED
```

状态变化必须写 append-only scheduler event log。

#### P0-3：`Progress Signal Contract`

不是所有模型都能 early stop。每个 prunable route 显式声明：

```text
progress_unit
grace_period
max_resource
comparison_metric
validation_protocol_id
minimum_comparable_trials
hard_constraint_fields
```

没有 contract 的任务只能 timeout/cancel，不能凭 LLM 主观提前停止。

#### P0-4：Heartbeat + Resource Reclaim

Executor 定期写：

```text
last_heartbeat
pid / worker_id
resource_lease
current_step
last_checkpoint
```

超过 grace window 后进入 `STALE`，释放调度配额；是否自动 retry 再根据 `side_effect_class` 和 checkpoint 决定。

#### P0-5：比赛全局 `Deadline Guard`

维护：

```text
remaining_time
reserved_validation_time
reserved_paper_time
reserved_final_qa_time
estimated_ready_work
```

当 `remaining_time` 无法覆盖“新候选预计耗时 + 必要验证 + 后续 reserve”时，禁止启动新的长周期探索。

### P1：值得实验

#### P1-1：ASHA-like MathModel Pruner

在往届题/合成 benchmark 上，只针对存在可靠 intermediate evidence 的模型族实验：

- no pruning；
- median stopping；
- ASHA-like；
- route-specific grace period。

必须同时报告 compute saved 与 false-prune rate。

#### P1-2：动态 CPU/GPU Reallocation

比较：

```text
fixed equal resources
vs
uniform free-resource redistribution
vs
score-card weighted redistribution
```

不能只比较“最快”；还要比较 deadline 前最终 validated solution 的质量。

#### P1-3：Criticality-aware Task Priority

将当前题目问题依赖、结果依赖编译成 task DAG，优先跑会阻塞多个下游的问题：

```text
Q1 baseline → Q2 参数 → Q3 优化 → 全文主结论
```

即使 Q4 的一个探索任务很新颖，只要它不阻塞主线，也不应长期抢占 Q1/Q2 的唯一 GPU/solver slot。

#### P1-4：Work-stealing fault injection

只对 PURE task 测试：

- worker saturation；
- 一个 worker 空闲；
- 大/小 dependency data；
- worker 在 steal request 后已经开始执行；
- stale confirm。

验证不会产生重复 candidate artifact。

### P2：长期考虑

- 真正需要跨机器/多 GPU 时将 backend 换为 Ray/Dask；
- 用历史实验训练 runtime / memory estimator；
- 根据 deadline slack 做更复杂的 expected-value scheduling；
- speculative duplicate execution 只针对高价值、纯计算、长尾任务；
- 将 token/API quota 也作为 generic resource 纳入 scheduler。

### 不建议采用

- 默认把所有任务交给 Ray/Dask；
- 单一 metric 的赢家通吃资源策略；
- 任何模型都启用 aggressive pruning；
- 为了节省 wall-clock 跳过独立验证；
- deadline 前仍不断开新模型分支；
- 允许 Scheduler 自己把一个候选标记为“科学上正确”。

## 14. 可形成的新 Skill / Agent

只提出设计，不创建：

### `competition-resource-scheduler`

职责：

- 读取 task DAG / resource inventory / global deadline；
- 维护 READY queue；
- 选择下一 task；
- 记录 scheduler event；
- 不解释数学结论。

### `trial-pruner`

职责：

- 读取经过 Checker 批准的 intermediate evidence；
- 应用 route-specific grace period / pruning policy；
- 输出 CONTINUE / PRUNE / PAUSE；
- 每个 decision 给出 machine-readable reason。

### `deadline-guard`

职责：

- 估计剩余主线工作量；
- 保留 validation / paper / final QA reserve；
- 阻止来不及完成证据闭环的新长周期实验。

### `runtime-estimator`

职责：

- 从历史 task event log 学习 wall-clock / memory 分布；
- 给 Scheduler 提供估计和不确定性；
- 不直接做调度决策。

### `scheduler-auditor`

职责：

- 计算 compute saved、false-prune、deadline success、resource utilization；
- 检查 scheduler 是否改变了 validation protocol；
- 回归测试升级后的 pruning policy。

## 15. 与历史调研的去重检查

本轮逐项对照 `research/INDEX.md`：

- **没有重复** 14:00 的 evidence-first / Scientific Agent 主题；
- **没有重复** 15:06 的候选模型搜索树、MCTS/UCT、Experiment Journal。本轮承接其 `Budget Controller`，但新增的是 Ray/Optuna/Dask 的代码级调度语义：ASHA rung、grace period、dynamic resource reallocation、heartbeat、task priority、resource restriction、transactional work stealing；
- **没有重复** 16:04 Reviewer/Judge。本轮只规定 Scheduler 必须消费可验证 intermediate evidence，并提出 scheduler 自身 false-prune QA；
- **没有重复** 17:07 checkpoint/resume。Checkpoint 在本轮只是动态资源 PAUSE 和 crash recovery 的依赖；核心不是恢复协议；
- **没有重复** 18:04 artifact ownership/promotion。本轮进一步明确只有 PURE/CANDIDATE_WRITE task 可安全重试/steal，CANONICAL_WRITE 仍由 Promotion Gate 独占。

本轮三个主项目 `ray-project/ray`、`optuna/optuna`、`dask/distributed` 均未出现在此前 INDEX 主项目集合中，因此属于新增研究对象。

本轮新增认知可以浓缩为：

> 之前解决的是“有哪些候选、结果是否可信、谁能晋级”；本轮解决的是“在 deadline 和有限算力下，哪些候选/任务值得继续消耗资源，以及调度失败时如何安全回收”。

## 16. 下一轮推荐方向

建议下一轮轮换到：

**赛时 Citation / External Evidence Provenance Agent：外部文献、官方规则、网络数据怎样进入模型假设与论文，同时避免引用幻觉、过期来源和数据来源断链。**

重点问题：

1. Citation Agent 如何区分“发现来源”“阅读全文”“提取可用事实”“论文正式引用”；
2. 外部数据如何记录获取时间、URL、license、hash、处理脚本并进入支撑材料；
3. 对模型参数来自论文/手册时，如何保存 exact evidence span；
4. Writer 如何只消费 verified citation，不自行补 DOI/作者/年份；
5. 网页变化/文献版本变化后如何标记 stale evidence；
6. citation verifier 如何检查正文 claim 是否真正被来源支持。

该方向与当前结果 provenance 有联系，但研究对象将从“内部计算 artifact”切换为“外部事实 / 文献 / 数据 evidence”。

## 17. Sources

### 17.1 已阅读源码 / 官方仓库

#### Ray / Ray Tune

- Repository: https://github.com/ray-project/ray
- ASHA source: https://github.com/ray-project/ray/blob/master/python/ray/tune/schedulers/async_hyperband.py
- Dynamic resource source: https://github.com/ray-project/ray/blob/master/python/ray/tune/schedulers/resource_changing_scheduler.py
- Tune scheduler docs: https://docs.ray.io/en/latest/tune-schedulers.html
- Tune getting started / ASHA: https://docs.ray.io/en/latest/tune/getting-started.html
- Tune resource FAQ: https://docs.ray.io/en/latest/tune/faq.html
- Tune stoppers: https://docs.ray.io/en/latest/tune/api/stoppers.html

本轮源码确认：ASHA 在中间 result 上做 STOP/CONTINUE；`ResourceChangingScheduler` 包装 base scheduler，资源变化时先 PAUSE，再更新 trial resources；`DistributeResourcesToTopJob` 会将可用资源倾向当前最优 trial。

#### Optuna

- Repository: https://github.com/optuna/optuna
- Hyperband source: https://github.com/optuna/optuna/blob/master/optuna/pruners/_hyperband.py
- Heartbeat source: https://github.com/optuna/optuna/blob/master/optuna/storages/_heartbeat.py
- Trial state source: https://github.com/optuna/optuna/blob/master/optuna/trial/_state.py
- Hyperband docs: https://optuna.readthedocs.io/en/stable/reference/generated/optuna.pruners.HyperbandPruner.html
- Efficient optimization / pruning: https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/003_efficient_optimization_algorithms.html

本轮源码确认：Hyperband 由多个 SHA bracket 组成；trial state 区分 WAITING/RUNNING/COMPLETE/PRUNED/FAIL；heartbeat 会周期记录 liveness，stale running trial 可转为 FAIL，并处理并发状态已被其他进程更新的情况。

#### Dask Distributed

- Repository: https://github.com/dask/distributed
- Work stealing source: https://github.com/dask/distributed/blob/main/distributed/stealing.py
- Scheduler source: https://github.com/dask/distributed/blob/main/distributed/scheduler.py
- Work stealing docs: https://distributed.dask.org/en/latest/work-stealing.html
- Priority docs: https://distributed.dask.org/en/latest/priority.html
- Worker resources docs: https://distributed.dask.org/en/latest/resources.html
- Scheduler state machine: https://distributed.dask.org/en/latest/scheduling-state.html

本轮源码确认：work stealing 使用 compute-vs-transfer cost 估计；task migration 通过 request/confirm 与唯一 stimulus ID 防止 stale response；scheduler 可保存 resource restrictions 和 user priority。

### 17.2 官方论文 / 算法背景

- Li et al., **Massively Parallel Hyperparameter Tuning / ASHA**: https://arxiv.org/abs/1810.05934
- Li et al., **Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization**: https://jmlr.org/papers/v18/16-558.html

这些论文用于理解 early stopping / budget allocation 的理论来源；本轮工程结论优先以当前仓库源码和官方文档为依据。

### 17.3 当前 math_mode 基线

- Repository: https://github.com/shaxiaoguang123/math_mode
- README: https://github.com/shaxiaoguang123/math_mode/blob/main/README.md
- AGENTS: https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md
- CLAUDE: https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md
- Research Index: https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md
- Previous model-search research: https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_15-06_model-selection-tree-search.md
- Previous artifact research: https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_18-04_artifact-ownership-promotion.md

### 17.4 证据边界

- 本轮**没有**实际安装或运行 Ray/Optuna/Dask benchmark；对其行为的判断来自当前源码与官方文档阅读，不声称完成 runtime benchmark。
- 本轮**没有**修改 `math_mode` 的 Agent、Skill、workflow 或正式求解代码。
- 提出的 `competition-resource-scheduler`、`trial-pruner`、`deadline-guard` 等均为设计建议，不代表已经创建或验证。
