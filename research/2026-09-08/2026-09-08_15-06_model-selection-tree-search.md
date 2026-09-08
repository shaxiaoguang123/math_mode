# MathModel Agent Research

## 1. 本轮研究主题

**赛时模型选择：代码搜索树、并行实验与可执行评测环境。**

本轮不再泛化讨论“科研 Agent 要有 evidence / reviewer”，而是进一步回答一个更具体的工程问题：

> 华为杯赛时，当一个子问题存在多条合理模型路线时，`math_mode` 应如何让 Agent 生成候选、真实运行、比较、淘汰、局部改进，并在固定时间/算力预算下选出值得进入论文主线的方案？

本轮深入研究 3 个高价值对象：

1. `WecoAI/aideml`：AIDE 的代码空间树搜索；
2. `sjtu-sai-agents/ML-Master`：MCTS/UCT、并行候选搜索、分支记忆与预算感知；
3. `MLE-Dojo/MLE-Dojo`：把代码验证、受限执行、评测反馈、历史记录封装成 Gym 风格可执行环境。

同时使用 `openai/mle-bench` 作为外部评测基准，重点检查 Agent 结果的方差、可比性和预算报告方式。

## 2. 为什么选择这个主题

上一轮（2026-09-08 14:00）研究的是 **Evidence-first Scientific Workflow**，核心新增认知是：真实代码执行、结果证据、Reviewer 与 artifact-first 工作流；并提出了 `Model Debate Agent` 作为后续方向。

本轮刻意不重复“需要 Reviewer / Evidence”的结论，而是把上一轮尚未落地的问题推进到代码级：

- “多模型竞争”到底应是几个 Agent 互相说服，还是多个可执行候选之间的搜索？
- 如何避免每次都从零生成一个新模型？
- 如何让一次改动的收益可归因？
- 如何在 12–24 小时甚至更短的赛时预算内分配探索和利用？
- 如何保存候选之间的父子关系、失败原因和评测结果？
- 如何把执行环境与模型搜索逻辑解耦？

当前 `math_mode` 已明确要求每问建立 `Baseline → 主模型 → 必要改进 → 独立验证 → 敏感性/稳健性`，并有强证据链、结果索引、支撑材料与 SHA-256 审计；但当前规则仍主要描述“最终路线应做什么”，尚未形成**机器可执行的候选模型搜索/实验账本协议**。因此，本轮与现有架构存在直接补位关系，而不是重复建设。

## 3. 搜索范围与关键词

本轮轮换到 P1“Model Selection / Coding Agent / Experiment Agent”，并覆盖与其直接相关的 P2 执行环境与实验状态。

主要关键词：

- model selection agent
- machine learning engineering agent
- code tree search agent
- agentic tree search
- MCTS coding agent
- UCT model search
- parallel experiment agent
- experiment journal
- benchmark machine learning agent
- sandbox feedback agent
- MLE-Bench agent
- reproducible model search

优先阅读：

- GitHub 官方 README；
- 搜索策略源码；
- Node / Journal / Memory 数据结构；
- Interpreter / Sandbox；
- metric / feedback / best-solution 选择逻辑；
- 并行调度代码；
- 当前 benchmark 官方 README。

## 4. 新发现项目

### 项目 1：AIDE ML

- 名称：AIDE — AI-Driven Exploration in the Space of Code
- Repository：https://github.com/WecoAI/aideml
- Stars：1509（本轮读取 GitHub 元数据时）
- 最近更新时间：GitHub `updated_at=2026-09-07T23:44:25Z`；`pushed_at=2026-09-03T15:58:13Z`
- 目标：把机器学习工程任务视为“代码空间中的搜索”，自动生成、运行、评测、调试和改进候选程序。
- 核心能力：代码树、多个初始 draft、真实执行、metric feedback、debug/improve 分支、Journal memory、最佳节点选择。

AIDE 对 `math_mode` 最有价值的不是“Kaggle 自动化”，而是其**候选节点作为一等数据结构**以及“每次 improvement 只做一个原子变化”的工程约束。

### 项目 2：ML-Master

- 名称：ML-Master / ML-Master 2.0
- Repository：https://github.com/sjtu-sai-agents/ML-Master
- Stars：449（本轮读取 GitHub 元数据时）
- 最近更新时间：GitHub `updated_at=2026-09-07T09:20:16Z`；`pushed_at=2026-03-29T18:00:43Z`
- 目标：面向长时程机器学习工程，将探索、推理、执行反馈和记忆结合起来。
- 核心能力（本轮源码确认部分）：MCTS 节点、UCT 选择、并行搜索、draft/debug/improve 分支、局部最优记忆、改进阈值、动态探索常数、best solution 持久化。

README 在 2026-03-24 进一步说明 ML-Master 2.0 已扩展为 EvoMaster，并将 2.0 描述为带 Hierarchical Cognitive Caching（HCC）的长时程科学 Agent。**本轮源码阅读确认的是当前 `main` 中的 MCTS/并行搜索/分支记忆实现；未在已检查文件中独立定位并验证完整 HCC 代码路径，因此不把 README 的 HCC 描述当作已完成的代码级验证。**

### 项目 3：MLE-Dojo

- 名称：MLE-Dojo: Interactive Environments for Empowering LLM Agents in Machine Learning Engineering
- Repository：https://github.com/MLE-Dojo/MLE-Dojo
- Stars：107（本轮读取 GitHub 元数据时）
- 最近更新时间：GitHub `updated_at=2026-09-06T06:42:24Z`；`pushed_at=2025-10-30T00:30:27Z`
- 目标：把 200+ Kaggle 任务封装成 Gym 风格、可执行、可评测的 Agent 环境。
- 核心能力：`request_info / validate_code / execute_code / reset / get_history` 动作空间、资源受限执行、结构化 feedback、raw/position score、环境历史、Agent/环境轨迹。

MLE-Dojo 对 `math_mode` 的价值不是直接提供“华为杯模型”，而是展示一种更清晰的边界：**Agent 负责决策，Environment 负责真实执行与客观反馈。**

### 评测参考：OpenAI MLE-bench

- Repository：https://github.com/openai/mle-bench
- Stars：1739（本轮读取 GitHub 元数据时）
- README 当前状态：2026-04-24 起暂停接受新的 leaderboard submission，以改进公平性和可比性流程。
- 重要方法学信息：官方建议至少 3 个 seeds，报告均值 ± SEM，并明确运行时长和计算资源，因为 Agent/LLM 具有高方差。

这一点直接影响 `math_mode`：赛时自动模型选择不能只保留“某一次跑出来最好的分数”。

## 5. 深入架构分析

### 5.1 AIDE：把模型选择转为“候选代码树”

AIDE 的核心数据流可以概括为：

```text
Task + 固定评测指标
        ↓
多个初始 Draft
        ↓
执行 Python 代码
        ↓
解析执行日志 + Validation Metric
        ↓
Journal / Solution Tree
   ↙          ↓          ↘
Debug      Improve     New Draft
   \          |          /
        再次真实执行
              ↓
         Best Node
```

源码中 `search_policy()` 的行为不是“一条链无限改”：

- draft 数不足时先建立多个起始方案；
- 以一定概率优先调试 buggy leaf；
- 没有 good node 时重新 draft；
- 有可用结果后选当前 best node 继续改进。

`_improve()` 特别要求一次只提出 **single actionable improvement**，并明确该改进应当是 atomic，便于通过实验判断变化是否有效。这一点非常适合数学建模：如果一次同时换特征、换模型、换损失、换验证切分，最终即使指标提升，也无法知道真正原因。

### 5.2 AIDE Journal：实验树不是聊天历史

`Journal`/`Node` 源码把下列信息放在节点上：

```text
plan
code
parent / children
step / id / create time
terminal output
execution time
exception type / stack
analysis
metric
is_buggy
```

`Journal.generate_summary()` 将已有 good nodes 的 Design、Results、Validation Metric 压缩成 Memory，再喂给后续候选生成。

这与普通“把聊天上下文塞回 Prompt”不同：Memory 是由**实际运行过的候选**构成，而不是未经验证的想法列表。

### 5.3 ML-Master：从贪心树升级到 MCTS/UCT + 并行探索

ML-Master 当前源码中 `MCTSNode` 增加：

```text
visits
total_reward
UCT
is_terminal
local_best_node
continue_improve
improve_failure_depth
expected_child_count
lock
```

其 UCT 形式是典型的：

```text
exploitation + C * sqrt(log(parent_visits) / visits)
```

这使 Agent 不必永远追逐当前最高分节点，而能在“利用当前好方案”和“探索尚未充分尝试的方案”之间平衡。

源码还对不同节点采用不同展开规则：

- Root：建立多个 draft；
- Bug 节点：优先 debug，但有最大 debug 深度；
- Good 节点：建立多个 improvement；
- 改进低于阈值连续若干次后，将分支停止；
- 新结果明显提升时更新 local best；
- 搜索结果通过 backpropagation 更新祖先节点。

### 5.4 ML-Master：真正把赛时预算放进 Agent Prompt 和搜索策略

`mcts_agent.py` 会把以下信息写进实现指导：

```text
TOTAL_TIME_REMAINING
TOTAL_STEPS_REMAINING
单次代码执行 timeout
```

并支持随搜索阶段变化的 exploration constant：

- linear decay
- exponential decay
- piecewise decay
- dynamic piecewise decay

这提供了一个非常实用的赛时启发：

> 早期应该广搜模型家族，后期应该把剩余算力集中到已经证明有效的路线，而不是 48 小时内始终保持同样的“创新欲”。

### 5.5 ML-Master：并行搜索不是多个 Agent 聊天，而是多个实验并发

`main_mcts.py` 使用 `ThreadPoolExecutor`，并根据 `parallel_search_num` 同时执行多个候选节点；节点完成后立即：

1. 写入 Journal；
2. 更新搜索树；
3. 保存 run；
4. 从新的树状态继续派生后续任务。

这比“Planner → Coder → Reviewer”串行角色链更适合赛时模型探索，因为计算资源可以在多个候选之间并行利用。

### 5.6 MLE-Dojo：把执行与 Agent 解耦

MLE-Dojo 的架构更像：

```text
Agent
  ↓ action
KaggleEnvironment
  ├── InfoInterface
  ├── CodeValidationInterface
  ├── CodeExecutionInterface
  ├── Sandbox
  └── FeedbackManager
          ↓
 observation / reward / history
          ↓
        Agent
```

`KaggleEnvironment` 保存：

- step count；
- 当前分数；
- best score；
- best code；
- 每次 action；
- result；
- feedback；
- timestamp。

这一架构说明，`math_mode` 不应让某个“大 Agent”同时负责：写代码、执行代码、判定是否成功、决定分数、修改论文。更稳妥的方式是把执行与评测做成受约束的环境层。

## 6. Agent / Skill 设计

三个项目给出的共同信号是：高质量自动建模不一定需要大量人格化 Agent，而需要职责清晰的**搜索—执行—反馈**组件。

可以抽象为：

```text
Model Search Policy
        ↓
Candidate Generator
        ↓
Experiment Executor
        ↓
Validity Gate
        ↓
Metric / Evidence Evaluator
        ↓
Experiment Journal
        ↓
Budget Controller
        ↺
```

对 `math_mode` 的映射：

### A. 可以直接借鉴

- 候选方案必须有稳定 `candidate_id`；
- 必须保存 `parent_id`，形成可追踪模型谱系；
- improvement 默认只允许一个核心原子变化；
- Bug、无指标、结果文件缺失的候选不得进入模型比较；
- 已运行候选摘要进入 Memory，避免重复路线；
- 最佳方案不是“最新方案”，而是从可比较候选中选择。

### B. 可以改造后采用

将 AIDE/ML-Master 的单一 Kaggle metric 改造成 **MathModel Score Card**：先通过硬门禁，再做多维评分。

建议候选记录至少包含：

```text
正确性 / 约束满足
验证误差或目标函数
敏感性 / 稳健性
可解释性
计算时间
数据泄漏风险
模型复杂度
创新增益
```

### C. 可以作为对照实验

- 当前线性单路线 vs 候选树搜索；
- greedy best-node vs UCT；
- 串行实验 vs 受控并行实验；
- 一次运行选 best vs 多 seed / 多切分确认；
- 文本 Model Debate vs execution-backed model competition。

### D. 不建议采用

- 为每个模型家族建立一个长期常驻人格 Agent；
- 只靠 LLM 读 stdout 判断数值正确；
- 直接把 Kaggle leaderboard score 当华为杯模型优劣标准；
- 在所有题型上强制 MCTS。

## 7. Workflow

建议未来 `math_mode` 的模型选择层演化为：

```text
赛题 / 子问题
    ↓
Problem Analysis + Hard Constraints
    ↓
Model Route Pool
    ├── Baseline A
    ├── Baseline B
    └── Mechanism/Optimization Route C
           ↓
Candidate Node
    ↓
生成/修改代码
    ↓
Experiment Environment
    ├── 语法/依赖检查
    ├── 资源/超时限制
    └── 真正执行
           ↓
Hard Validity Gate
    ├── 是否运行成功
    ├── 输出是否齐全
    ├── 单位/约束是否满足
    ├── 是否存在数据泄漏
    └── metric schema 是否一致
           ↓
MathModel Score Card
           ↓
Experiment Journal / Tree
           ↓
Search Policy + Budget Controller
    ↙             ↓              ↘
new route       improve          debug
           ↓
候选收敛 / 时间预算触发
           ↓
Promote Best Route
           ↓
现有 math_mode 链路：
结果索引 → 独立验证 → Figure Plan → 支撑材料 → 论文
```

这里的关键不是“增加更多流程”，而是把当前 `Baseline → 主模型 → 改进` 之间尚未机器化的选择过程显式化。

## 8. Code Execution / Tools

### AIDE

本轮源码确认：

- 真实执行 Python；
- 单独子进程；
- 捕获 stdout/stderr；
- 捕获异常与 stack；
- 记录执行时间；
- 支持 timeout；
- 每个候选执行后才进入 Journal。

但 `aide/interpreter.py` 本身主要是 multiprocessing + timeout，并不是完整的文件系统/网络隔离 sandbox；README 另提供 Docker 运行方式。因此不能把其 Interpreter 直接等价成安全容器。

### ML-Master

本轮源码确认：

- 有独立 Interpreter；
- 多候选并行执行；
- 强制验证 metric 和 submission；
- 可通过 grading server 检查输出格式；
- 保存 best `solution.py`、`submission.csv`、node id；
- README 提供 Docker 运行方式。

### MLE-Dojo

本轮源码确认 `Sandbox` 支持：

- CPU time limit；
- memory limit；
- GPU device / GPU memory 参数；
- execution timeout；
- subprocess / process-group cleanup；
- execution log。

从已检查源码看，其“sandbox”重点是资源受限与进程管理；README 推荐 Docker 作为外层执行环境。本轮未完成针对网络隔离、文件系统只读挂载等安全属性的全面审计，因此不声称它具备完整容器安全边界。

### 对 math_mode 的差距

当前 `math_mode` 已要求：

- 项目 `.venv`；
- 显式 Python 路径；
- 真实求解代码；
- 运行时间记录；
- 随机种子固定；
- 结果索引；
- 支撑材料运行记录和 SHA-256。

这些复现基础**已经优于很多纯 Agent Demo**。真正缺少的是：

> 将“运行一次最终代码”扩展成“统一运行多个候选，并把每个候选的输入、代码、变更、指标、失败原因、运行时间和父子关系作为机器可读实验记录”。

## 9. QA / Reviewer / Verification

### 9.1 AIDE 的验证方式

已确认：

- 对任务先确定统一 validation metric 及最大化/最小化方向；
- 生成代码必须打印 hold-out metric；
- 执行失败、无 metric、NaN 会被判为坏节点；
- evaluator 读取实现和 execution output 后给出 bug/metric 判断。

不足：metric 仍可能由生成代码本身定义错误；LLM 从日志提取 metric 也不是独立真值验证。

### 9.2 ML-Master 的额外门禁

当前源码增加：

- `submission.csv` 实际存在性检查；
- 可选 submission format server；
- metric direction 一致性检查；
- 对与历史 best 相差异常数量级的 metric 做启发式拒绝；
- 连续改进低于阈值后终止分支。

这些机制适合迁移为“华为杯候选晋级门禁”，但不能原样采用。例如“metric 相差 50 倍就可疑”只是一种 Kaggle 式启发式，不适用于跨数学模型的多指标比较。

### 9.3 MLE-Dojo 的环境级反馈

MLE-Dojo 将：

```text
validate_code
execute_code
score
feedback
history
```

放在 Agent 外部，并将每次 action 的 result/feedback 持久化。这一点对于防止“Agent 自己写答案、自己宣布正确”非常重要。

### 9.4 MLE-bench 给出的重要警告：Agent 结果有高方差

当前 MLE-bench README 明确建议至少进行 3 个 seeds，并报告 mean ± SEM；同时要求说明运行时长和算力配置。其 README 还在 2026-04-24 暂停新 leaderboard submission，原因是继续改进公平性和可比性流程。

对 `math_mode` 的含义：

1. 候选模型不能只比较一次运行的 best score；
2. 随机模型至少应做重复 seed、重复 split 或 bootstrap/扰动验证；
3. 每个候选必须记录 compute/time budget；
4. “不同验证协议下的数字”禁止直接排序；
5. 最终选择应优先选择**在独立验证与敏感性分析下仍稳定的方案**，而不是一次峰值最高的方案。

## 10. 值得借鉴的设计

### 10.1 原子改进（Atomic Improvement）

这是本轮最值得直接引入的机制之一。

推荐把一次 candidate 变更定义为：

```text
父节点模型 + 1 个主要变化 → 子节点
```

例如：

- 只换损失函数；
- 只增加一个物理约束；
- 只增加一个特征族；
- 只替换优化器；
- 只改变验证方案；
- 只加入一个稳健化机制。

这样才能生成真正有价值的消融记录。

### 10.2 搜索树 Memory，而不是对话 Memory

真正值得记住的是：

```text
尝试了什么
怎么运行的
为什么失败
指标是多少
改动是什么
哪个候选是它的父节点
```

而不是保存大量聊天文本。

### 10.3 Explore → Exploit 的赛时动态预算

建议按剩余比赛时间改变策略：

```text
早期：3–5 条明显不同路线
中期：集中改进 2–3 条已验证路线
后期：只允许低风险原子优化 + 验证 + 论文证据补齐
```

不建议在最后数小时继续大规模搜索全新模型家族。

### 10.4 Environment / Agent 分离

把执行、资源限制、结果读取、硬门禁独立于模型搜索 Agent，可以明显减少“自评自证”。

## 11. 存在的问题

### AIDE

- 强依赖统一数值 metric，适合 Kaggle，但华为杯很多问题是机理、优化、仿真、评价或多目标问题；
- Interpreter 本身不等于强安全 sandbox；
- evaluator 仍依赖 LLM 解析执行日志；
- 贪心 best-node 改进可能较早陷入局部最优。

### ML-Master

- MCTS 和并行搜索计算成本明显高于单路线；
- 当前实现高度适配 MLE-Bench/Kaggle 的 `submission.csv + metric`；
- metric validity 的数量级启发式不能直接迁移；
- 长时间自治容易在错误验证协议上持续优化；
- README 的 HCC/2.0 架构描述与本轮实际检查的 MCTS 源码层级需要严格区分，本轮未完成 HCC 全代码链确认。

### MLE-Dojo

- 主要面向标准化 ML competition；
- `score/reward` 结构比华为杯问题简单；
- 200+ Kaggle 任务并不代表覆盖 ODE/PDE、机理建模、运筹优化、数值仿真等典型数学建模路线；
- sandbox 本轮确认的是资源约束和进程隔离机制，不应未经审计宣称为完全安全隔离。

### 共同风险

最重要的共同风险是 **validation overfitting**：如果 Agent 能反复看到同一个验证分数，它会逐渐优化到验证集，而不一定提高真实泛化能力。

对数学建模竞赛尤其要防止：

- 测试集泄漏；
- 用最终评估集反复调参；
- 只追指标而破坏机理合理性；
- 复杂模型用微小分数优势掩盖巨大解释成本；
- 用不同 metric / split 的结果直接排序。

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 赛题硬约束 | 已很强：题面 > 附件 > 求解规范 | AIDE/ML-Master 主要遵循 task metric | **保持 math-mode**，不能被 AutoML 逻辑替换 |
| Baseline / 主模型 | 已要求每问明确 Baseline、主模型、必要改进 | AIDE/ML-Master 会同时维护多个候选 | `math_mode` 缺机器可读候选池/搜索树 |
| 候选谱系 | 重要决策可写 `决策记录.jsonl`，但非强制搜索结构 | Node 有 parent/children | 建议新增标准 candidate lineage |
| 原子消融 | 当前要求比较/消融，但未规定每次改动粒度 | AIDE 明确 single actionable atomic improvement | 可直接借鉴 |
| 真实代码执行 | 已要求真实求解、固定环境、运行记录 | 三项目均强调执行 | **保持**；进一步统一候选执行接口 |
| 并行实验 | 当前无统一搜索级并行协议 | ML-Master `ThreadPoolExecutor` 并行节点 | 可改造后采用 |
| 搜索策略 | 当前更接近人工/Agent 选择 Baseline→主模型 | AIDE greedy/tree；ML-Master MCTS/UCT | 值得加入轻量 search policy |
| 时间预算 | 已检查题面运行限制，但无统一“剩余赛时搜索预算” | ML-Master 显式剩余时间/steps + C decay | 高价值新增 |
| 模型 Memory | 结果索引、AI 使用记录、决策记录偏事实留档 | AIDE Journal / ML-Master branch memory | 应新增实验记忆，而非扩大聊天 memory |
| 数值 QA | 有独立验证、敏感性/稳健性、Evidence Matrix | 外部 Agent 更偏 metric/format | **math-mode 更强，必须保持** |
| 结果可追溯 | 支撑材料、运行验证、SHA-256 已较强 | AIDE/ML-Master 保存代码/日志/最佳节点 | 保持并接入 candidate_id |
| 随机性 | 规范已要求固定随机种子 | MLE-bench 推荐多 seed 汇总 | 固定 seed 之外还应加入重复运行稳定性验证 |
| 执行环境边界 | `.venv` + 本机真实运行 | MLE-Dojo 资源限制 + Docker 推荐 | 可新增统一 timeout/resource profile |
| 论文/图表 | 已有强 LaTeX/视觉/支撑材料链 | 三项目不是重点 | **不替换** |

结论：

- **保持**：题面约束、独立验证、Evidence Matrix、结果索引、支撑材料、LaTeX/绘图 QA；
- **改进**：`Baseline → 主模型` 之间增加可执行候选选择层；
- **新增**：实验账本、candidate lineage、search budget、model-search/experiment-manager；
- **替换**：暂不建议替换任何现有正式链路；
- **暂不采用**：全局强制 MCTS、RL 训练 Agent、Kaggle 单指标式终局评分。

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：建立“实验账本”机器协议

建议未来设计一个 `求解/实验账本.jsonl`（仅建议，本轮不创建正式代码/协议），每个候选至少记录：

```text
candidate_id
parent_id
question_id
route_family
change_type
atomic_change
code_path
input_hashes
seed
validation_protocol
metric_schema
metrics
constraint_checks
exec_time
status
failure_reason
artifact_paths
artifact_hashes
created_at
```

它与现有 `求解/结果索引.md` 不冲突：

- 实验账本记录“所有值得追踪的尝试”；
- 结果索引记录“最终进入事实链的正式结果”；
- 支撑材料审计仍负责最终可提交证据。

#### P0-2：设计 `experiment-manager-agent`

职责应严格受限：

- 接收 candidate；
- 按环境/timeout/seed 运行；
- 捕获 stdout/stderr/异常；
- 验证要求的输出文件；
- 记录资源和运行时间；
- 返回机器结构化结果。

**它不负责写论文，也不负责自行宣布模型合理。**

#### P0-3：设计 `model-search-agent`

建议默认采用轻量搜索，而不是一上来 MCTS：

```text
阶段 A：生成 3–5 条模型家族明显不同的候选
阶段 B：硬门禁淘汰无效路线
阶段 C：对前 2–3 名做原子改进
阶段 D：必要时再启用 UCT/预算分配
阶段 E：独立验证后 Promote
```

#### P0-4：建立 MathModel Score Card，先 Gate 后 Score

华为杯不能只有一个 RMSE。

建议顺序：

```text
Hard Gate
- 题面约束满足？
- 输出完整？
- 单位正确？
- 无泄漏？
- 数值稳定？
        ↓
Score Card
- 目标指标
- 独立验证
- 稳健性
- 复杂度
- 可解释性
- 计算时间
- 创新增益
```

硬门禁失败的方案不允许因为某个指标高而晋级。

### P1：值得实验

#### P1-1：并行 2–4 个候选分支

在 CPU/GPU 允许时，让互不依赖的 baseline/route 同时跑，而不是让一个 Agent 串行等待全部实验。

#### P1-2：Greedy vs UCT 对照

在历史华为杯赛题上测试：

- greedy：只改当前最好路线；
- UCT：保留一定探索；
- fixed diversity：固定 3 条模型家族并行。

比较：最终质量、耗时、token、运行次数、失败率。

#### P1-3：从“固定 seed”升级到“重复验证”

固定 seed 保证可复现，但无法证明稳定。

对存在随机性的模型，建议 winner promotion 前做 3 次低成本重复，或使用多 split / bootstrap / 扰动试验，并保存均值、方差/区间，而不是只保存最幸运的一次。

#### P1-4：文本 Debate 与执行型 Competition 做 A/B

上一轮提出 `Model Debate Agent`。本轮代码级研究后，应将其降级为可选机制：

> 先让候选真实执行，再让 Reviewer 对**已有证据**进行 debate；不要让纯文本 debate 替代实验。

### P2：长期考虑

#### P2-1：历史赛题 Benchmark Harness

借鉴 MLE-Dojo，把往届华为杯题目逐步整理为可重放环境：

```text
problem package
input manifest
hard constraints
expected artifacts
validation hooks
budget profile
scoring rubric
```

用于评估 `math_mode` 新 Agent/Skill 是否真的变好。

#### P2-2：分层认知缓存 / 长期经验库

ML-Master 2.0 的 HCC 思想值得后续单独深挖，但在 `math_mode` 还没有足够实验轨迹之前，不应优先建设复杂长期记忆系统。

### 不建议采用

- 所有题型默认 MCTS；
- 为追求“自治”把评测逻辑交给同一个 LLM；
- 直接训练 RL Agent 作为近期目标；
- 复制 12/24 小时 Kaggle 搜索预算；
- 对机理/优化问题强制使用单一 scalar reward；
- 最后数小时仍大规模开新模型路线。

## 14. 可形成的新 Skill / Agent

只提出设计，不在本轮创建：

### `model-search-agent`

负责：候选路线生成、候选树、搜索策略、diversity、晋级/停止策略。

### `experiment-manager-agent`

负责：真实运行、资源限制、seed、timeout、stdout/stderr、artifact 收集。

### `candidate-evaluator`

负责：Hard Gate + MathModel Score Card；禁止只按单一 metric 评分。

### `search-budget-controller`

负责：剩余赛时、token、CPU/GPU、最大实验数，以及 explore→exploit 切换。

### `experiment-journal`

它更适合定义为机器数据契约/Skill，而不是人格 Agent；负责候选 lineage、失败经验和结果摘要。

## 15. 与历史调研的去重检查

已读取：

- `research/INDEX.md`；
- `research/2026-09-08/2026-09-08_14-00_scientific-agent-evidence-workflow.md`。

上一轮已有：

- evidence-first；
- Reviewer；
- Modeling Evidence Agent；
- 泛化的 Model Debate Agent；
- 长期实验 Memory 概念。

**本轮新增且此前未记录的内容：**

1. AIDE 源码级 `Node / Journal / search_policy / draft-debug-improve` 数据结构；
2. “单次改进必须 atomic”的可实验归因机制；
3. ML-Master 源码级 MCTS/UCT、不同节点展开策略、改进阈值、backpropagation；
4. ML-Master 并行候选执行与剩余时间/steps 感知；
5. 动态 exploration constant 的赛时 explore→exploit 思路；
6. MLE-Dojo 的 Agent/Environment 分离、`validate_code/execute_code/get_history` 协议；
7. MLE-bench 对多 seed、mean±SEM、算力预算和公平可比性的明确要求；
8. 基于以上机制，提出 `实验账本.jsonl + model-search-agent + experiment-manager-agent + search-budget-controller` 的具体落点。

本轮未重访 AI Scientist，因此没有通过改写上一轮措辞制造“新研究”。

## 16. 下一轮推荐方向

建议下一轮轮换到：

**“数学模型合理性 Reviewer / Judge：如何验证不是纯预测指标的问题。”**

重点研究：

- dimensional/unit consistency agent；
- constraint verification；
- symbolic/numerical cross-check；
- optimization feasibility checker；
- simulation sanity check；
- sensitivity / perturbation / counterexample generation；
- reviewer rubric；
- 多 Judge 一致性与争议处理。

原因：本轮已经解决“怎么搜索候选”，下一步应解决“如何判断一个数值看起来不错的数学模型在机理上也成立”。

## 17. Sources

### 已阅读源码 / 一手文档

#### 当前 math_mode

- https://github.com/shaxiaoguang123/math_mode/blob/main/README.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/华为杯_求解规范/华为杯_求解规范.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_14-00_scientific-agent-evidence-workflow.md

#### AIDE

- https://github.com/WecoAI/aideml
- https://github.com/WecoAI/aideml/blob/main/README.md
- https://github.com/WecoAI/aideml/blob/main/aide/agent.py
- https://github.com/WecoAI/aideml/blob/main/aide/journal.py
- https://github.com/WecoAI/aideml/blob/main/aide/interpreter.py

#### ML-Master

- https://github.com/sjtu-sai-agents/ML-Master
- https://github.com/sjtu-sai-agents/ML-Master/blob/main/README.md
- https://github.com/sjtu-sai-agents/ML-Master/blob/main/main_mcts.py
- https://github.com/sjtu-sai-agents/ML-Master/blob/main/agent/mcts_agent.py
- https://github.com/sjtu-sai-agents/ML-Master/blob/main/search/mcts_node.py

#### MLE-Dojo

- https://github.com/MLE-Dojo/MLE-Dojo
- https://github.com/MLE-Dojo/MLE-Dojo/blob/main/README.md
- https://github.com/MLE-Dojo/MLE-Dojo/blob/main/mledojo/gym/env.py
- https://github.com/MLE-Dojo/MLE-Dojo/blob/main/mledojo/gym/sandbox.py

#### MLE-bench

- https://github.com/openai/mle-bench
- https://github.com/openai/mle-bench/blob/main/README.md

### 官方论文 / 项目说明

- AIDE: https://arxiv.org/abs/2502.13138
- MLE-Bench: https://arxiv.org/abs/2410.07095
- MLE-Dojo: https://arxiv.org/abs/2505.07782
- ML-Master 1.0: https://arxiv.org/abs/2506.16499
- ML-Master 2.0: https://arxiv.org/abs/2601.10402

### 证据边界声明

本轮进行了仓库文档和关键源码阅读，但**没有在本地下载完整数据集并实际运行 AIDE、ML-Master、MLE-Dojo 或 MLE-bench benchmark**。因此：

- “源码中存在某机制”与“本轮实际运行验证该机制”严格区分；
- 性能数字仅作为官方 README/benchmark 的外部证据，不视为本地复现；
- ML-Master 2.0 的 HCC 本轮仅确认 README/论文层描述，未把其声明为已完成代码级验证。
