# MathModel Agent Research

## 1. 本轮研究主题

**数学模型 Reviewer / Judge：从“文本评审”升级为可校准、可执行、按证据拆解的验证系统。**

本轮围绕一个比“是否需要 Reviewer”更具体的问题展开：

> `math_mode` 已经要求独立验证、敏感性/稳健性、守恒/约束、结果索引与支撑材料审计；下一步怎样把这些规则从自然语言规范变成一个机器可执行、可解释、可校准，而且不会把 LLM 自己的判断当成数学真值的 Reviewer / Judge 层？

本轮深入研究 3 个高价值对象：

1. `openai/frontier-evals` 中的 **PaperBench**：层级 Rubric、独立复现实验、按 criterion 定位证据、LLM Judge，以及专门验证 Judge 本身的 JudgeEval；
2. `SakanaAI/AI-Scientist` 的 **代码级 reviewer 实现**：多 Reviewer ensemble、meta-review、reflection、结构化评分和 confidence；
3. `OSU-NLP-Group/ScienceAgentBench`：科研 Agent 的可执行评测、Docker harness、多维指标，以及 2026 年专门为降低 false negative 发布的 verified benchmark。

这三者构成了很互补的三角：

```text
PaperBench
  → criterion-level evidence + reproduce + judge calibration

AI Scientist reviewer
  → soft critique diversity + meta-review + confidence

ScienceAgentBench
  → executable evaluator + evaluator false-negative correction
```

本轮结论不是“再加一个 Reviewer Agent”，而是：

> `math_mode` 需要把 Reviewer 拆成 **确定性硬门禁 → 独立执行/复算 → 证据型 Judge → 软性 Meta-Reviewer → Judge 自身回归测试** 五层，而不是让一个 LLM 同时判断代码、数值、模型合理性和论文质量。

## 2. 为什么选择这个主题

### 2.1 与前两轮调研的差异

2026-09-08 14:00 的研究建立了 Evidence-first Scientific Workflow 基线，提出“需要 Reviewer / Evidence Agent”。

2026-09-08 15:06 的研究进一步解决了候选模型如何真实运行、搜索、比较的问题，重点是 AIDE、ML-Master、MLE-Dojo 的候选树、MCTS/UCT、实验账本与执行环境。

因此本轮不能再重复：

- “结果必须真实运行”；
- “要有 Reviewer”；
- “要保存日志”；
- “多模型需要比较”。

本轮新增问题是：

1. Reviewer 到底检查什么？
2. 哪些判断必须用确定性程序完成，而不是让 LLM 猜？
3. 如何证明“代码存在”“代码实际执行”“执行结果真的支持结论”是三件不同的事？
4. 如何让 Reviewer 给出的失败结论能定位到具体证据文件和具体 criterion？
5. 如何评价 Reviewer 自己是否可靠，避免“Judge 幻觉”？
6. 如果 evaluator 本身存在 false negative，应如何版本化和回归测试？
7. 文本型多 Reviewer / debate 在什么位置有价值，在什么位置反而危险？

### 2.2 当前 math_mode 已经做得比较强的部分

基线读取确认，当前 `math_mode` 已经不是“只会写论文”的项目：

- `README.md` 和两个总控文件明确要求真实代码运行、结构化结果、独立验证、敏感性/稳健性和结果索引；
- `华为杯_求解规范/华为杯_求解规范.md` 已将机理模型的量纲/数量级、守恒、边界/极限、参考值、参数扰动、错误假设反证列为验证内容；
- 优化问题要求可行性与官方指标独立复算、收敛、多初值和最优性 Gap（可获得时）；
- 视觉计划审计器已经对标准/复杂问题设置“必须有独立验证证据/图”的门禁；
- 支撑材料链已经保存源码、真实运行记录、自主数据来源、补充图表和 SHA-256；
- 论文规范要求验证尽量就地写入每个问题，正文不足应补充可复算证据，而不是扩写空话。

因此真正缺的不是“验证意识”，而是一个统一的、机器可审计的 **Validation Rubric / Judge Contract**：目前规则分散在求解规范、视觉计划、结果索引、支撑材料和论文门禁中，但没有一个统一数据结构去回答：

```text
这个结论需要满足哪些 criterion？
每个 criterion 的证据在哪？
由什么 checker 判定？
它是 hard gate 还是 soft score？
判定是否有效？
Judge 版本是什么？
Judge 自己是否经过回归校准？
```

## 3. 搜索范围与关键词

本轮轮换到 P1：Reviewer / Judge / Verification Agent，并覆盖直接相关的 P2：evaluation harness、provenance、judge calibration、artifact isolation。

主要关键词：

- scientific agent judge
- reviewer agent verification
- code execution judge
- hierarchical rubric judge
- criterion-level grading
- reproduction benchmark judge
- judge evaluation benchmark
- LLM judge calibration
- false negative evaluator
- scientific agent executable evaluation
- model soundness reviewer
- constraint verification agent
- dimensional analysis verification
- reproducibility judge
- meta reviewer ensemble

重点阅读对象：

- PaperBench README、rubric task schema、`GradedTaskNode`、`SimpleJudge.grade_leaf()`、JudgeEval；
- AI Scientist `perform_review.py`；
- ScienceAgentBench README、`compute_scores.py`、`calculate_metrics.py`、visual judge；
- 当前 `math_mode` 的 README、AGENTS、CLAUDE、求解规范、视觉审计规则以及既有 research。

## 4. 新发现项目

### 项目 1：OpenAI PaperBench（现位于 frontier-evals）

- 名称：PaperBench — Evaluating AI's Ability to Replicate AI Research
- Repository：https://github.com/openai/frontier-evals/tree/main/project/paperbench
- 宿主仓库：`openai/frontier-evals`
- Stars：1292（本轮读取 `openai/frontier-evals` GitHub 元数据时；PaperBench 当前是 monorepo 子项目，不单独计 star）
- GitHub 元数据：`updated_at=2026-09-08T05:53:56Z`，`pushed_at=2026-04-21T20:53:31Z`
- 目标：评价 Agent 是否能够从论文开始，真正构建代码并复现实验结果，而不是只生成一份看似合理的研究文本。
- 核心能力：层级 Rubric、独立 reproduction container、独立 grading container、criterion-level grading、证据文件定位、执行日志、JudgeEval。

PaperBench 对 `math_mode` 最有价值的一点是：它明确把“写出了代码”“代码真的运行”“运行结果支持结论”拆成不同类型的 Rubric criterion，而不是用一个总分模糊处理。

### 项目 2：The AI Scientist Reviewer（旧项目代码级重访）

- 名称：The AI Scientist Reviewer
- Repository：https://github.com/SakanaAI/AI-Scientist
- Stars：14508（本轮 GitHub 元数据）
- GitHub 元数据：`updated_at=2026-09-08T02:19:27Z`，`pushed_at=2025-12-19T07:46:21Z`
- 本轮读取文件：`ai_scientist/perform_review.py`
- 目标：模拟 ML 会议评审，从论文文本层面对 Originality、Quality、Clarity、Significance、Soundness、Contribution、Overall、Confidence 等维度给出结构化评审。
- 核心能力：多次 review ensemble、meta-review、数值评分聚合、review reflection、结构化 JSON、confidence。

**为什么允许重访：**

14:00 首轮只把 AI Scientist 当作 `idea → experiment → paper` 的科研工作流机制参考，并明确标注“后续需源码深读”。本轮新增的是此前完全没有研究的 reviewer 代码级实现：ensemble、meta-review、reflection、confidence 和结构化评审协议。因此符合“以前只做表面调查，本轮补充代码级实现细节”的重访条件。

### 项目 3：ScienceAgentBench

- 名称：ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery
- Repository：https://github.com/OSU-NLP-Group/ScienceAgentBench
- Stars：169（本轮 GitHub 元数据）
- GitHub 元数据：`updated_at=2026-09-07T23:53:34Z`，`pushed_at=2026-07-18T05:25:41Z`
- 目标：先严格评价 Agent 在科研 workflow 的单项真实任务能力，再讨论端到端自动科研。
- 数据：102 个任务，来自 44 篇同行评议论文、4 个学科，并由 9 位领域专家参与验证。
- 核心能力：每个任务输出统一为可运行 Python 程序；Dockerized evaluation；执行结果、代码相似度、有效程序率、成本等指标；JSONL trajectory/eval log；visual judge。
- 关键更新：2026-04-30 发布 verified version，官方明确说明其目的之一是降低评价中的 false negatives。

这个 2026 verified 更新对 `math_mode` 有很强的方法学价值：

> Reviewer / evaluator 不是天然正确的。一个“看起来严格”的自动门禁也可能把正确结果判错，因此 evaluator 自身也必须版本化、回归测试和维护 false-negative case corpus。

## 5. 深入架构分析

### 5.1 PaperBench：三阶段隔离比“一个 Agent 自己检查自己”可靠

PaperBench 当前工作流明确拆成三个阶段：

```text
Stage 1: Agent Rollout
Agent 在容器 A 中完成代码/提交物
        ↓
Stage 2: Reproduction
把提交物放到全新的容器 B 中执行
        ↓
Executed Submission
        ↓
Stage 3: Grading
在容器 C 中用 Rubric + Judge 评分
```

三个环境的意义不是 Docker 本身，而是**职责隔离**：

- Agent 的工作环境不是最终验证环境；
- “在我的上下文里跑过”不能代替 clean reproduction；
- Judge 也不和执行器共享全部隐式状态；
- 最终判定基于已执行后的 artifact，而不是 Agent 自己的解释。

对 `math_mode` 的直接映射应该是：

```text
Solver Workspace
  写代码 / 搜模型 / 生成候选
        ↓
Fresh Validation Run
  从约定入口重新执行
        ↓
Validation Artifacts
  JSON/CSV/log/figures/official outputs
        ↓
Reviewer Layer
  只读证据并判定
```

不一定需要三个 Docker，但至少需要**逻辑上的三个身份与输入边界**。

### 5.2 PaperBench：Rubric Tree 把“好不好”拆成可判定叶节点

源码 `rubric/tasks.py` 将 Rubric 建模成 `TaskNode` 树：

```text
TaskNode
├── id
├── requirements
├── weight
├── sub_tasks
├── task_category
└── finegrained_task_category
```

叶节点才具有可直接评分的 task category。当前代码将主要 criterion 分成：

- `Code Development`
- `Code Execution`
- `Result Analysis`
- `Subtree`

并为前三类明确设置不同问题：

```text
Code Development
→ 是否真的存在正确实现该要求的代码？
  只有说明文字不算。

Code Execution
→ reproduce.sh 实际运行时是否成功执行了该要求？

Result Analysis
→ reproduce.sh 产生的证据是否与所声称结果一致？
```

这是本轮最重要的新机制之一。

对数学建模而言，一个模型“正确”至少也应该拆成：

```text
模型实现正确？
       ≠
求解程序成功运行？
       ≠
约束/守恒/边界满足？
       ≠
独立复算一致？
       ≠
数值结果真的支持论文结论？
       ≠
论文表达是否准确、不过度外推？
```

如果把这些混成一个 LLM 的“综合评价 8/10”，任何一层失败都可能被其他优点掩盖。

### 5.3 PaperBench：`GradedTaskNode` 让判定具有状态，而不是只有分数

`graded_task_node.py` 在 criterion 上保存：

```text
score
valid_score
explanation
judge_metadata
sub_tasks
```

叶节点通常用 0/1；父节点按 child weight 加权聚合。

这里 `valid_score` 非常重要：

> “评分为 0”与“Judge 本次评分无效”不是一回事。

对 `math_mode` 可以对应：

```json
{
  "criterion_id": "q2.constraint.capacity",
  "status": "pass | fail | unknown | judge_error",
  "score_valid": true,
  "evidence": ["求解/问题二/结果/constraint_check.json"],
  "checker": "deterministic",
  "explanation": "..."
}
```

如果数据文件损坏、单位来源缺失或 evaluator 崩溃，应进入 `unknown/judge_error`，而不是静默记成 fail，也不能让论文继续当作已验证。

### 5.4 PaperBench：先定位相关文件，再评 criterion

`SimpleJudge` 并非把整个提交无差别塞进一个 prompt。

源码流程是：

```text
criterion
  ↓
读取 submission 文件树
  ↓
LLM 先选择最相关文件
  ↓
读取这些文件 + paper + reproduce.sh + reproduce.log
  ↓
结合前置 rubric context
  ↓
对单个 criterion 评分
```

这是一种 **evidence localization**。

迁移到 `math_mode` 后，Reviewer 不应只是：

```text
“请检查整个项目有没有问题”
```

而应变成：

```text
criterion: Q3-OPT-04
要求: 所有方案必须满足容量与时间窗约束
证据:
  - constraint_summary.json
  - solution.csv
  - independent_recheck.py
  - independent_recheck.log
检查器:
  deterministic + independent_recompute
```

每个判定都知道“看哪里”。这可以大幅降低 Reviewer 在长上下文中凭印象评价的问题。

### 5.5 PaperBench：结果分析存在硬门禁

`SimpleJudge.grade_leaf()` 中有一个非常明确的 hard gate：

如果 `Result Analysis` criterion 需要评价，但 reproduction 没有修改/产生任何结果文件，则该类任务直接记 0，并解释：没有 reproduced results 可分析。

这体现了一个对 `math_mode` 很有价值的原则：

> 某些事实不应该交给 LLM“综合考虑”，而应先由确定性门禁阻断。

可直接迁移的 hard gate 示例：

```text
代码未成功退出                    → 结果相关 criterion 禁止 PASS
结果文件不存在                    → 论文引用相关 criterion 禁止 PASS
输入 hash 与当前题目/数据不一致    → 运行记录 stale
约束独立复算失败                  → 优化可行性 FAIL
单位无法闭合                      → 机理推导不得进入“已验证”
测试标签泄漏                      → ML 结果直接 disqualify
官方输出结构不匹配                → 提交物 gate FAIL
```

### 5.6 PaperBench：Judge 也必须被 JudgeEval

PaperBench 没有把 LLM Judge 当作可信神谕，而是建立独立 `JudgeEval`。

JudgeEval 的做法：

1. 人工给一组 reproduction submission 做 criterion-level ground truth；
2. 每个叶节点有人工 binary score + explanation；
3. 用待测 Judge 对同样的 submission 评分；
4. 比较 Accuracy、Precision、Recall、F1；
5. 因类别不平衡，特别关注 macro F1。

这对 `math_mode` 的意义比“用更强模型当 Reviewer”更重要：

> Reviewer 能力本身必须被基准测试。

如果 `competition-reviewer` 没有回归集，就无法知道某次改 prompt、换模型、改 checker 后，是变得更严格，还是只是增加了 false positive / false negative。

### 5.7 AI Scientist：多 Reviewer ensemble 的真正作用边界

`AI-Scientist/ai_scientist/perform_review.py` 的 reviewer 输出是结构化 JSON，覆盖：

- Summary
- Strengths / Weaknesses
- Originality
- Quality
- Clarity
- Significance
- Questions
- Limitations
- Soundness
- Presentation
- Contribution
- Overall
- Confidence
- Decision

代码还支持：

```text
num_reviews_ensemble > 1
       ↓
并行产生多个 review
       ↓
解析有效 review
       ↓
meta-review
       ↓
数值项取 ensemble 平均并回写
```

同时支持多轮 reflection，让 Reviewer 检查自己刚才评审的准确性与 soundness，再进行修订。

这说明文本型 Reviewer 的优势在：

- 找论证缺口；
- 发现假设未解释；
- 评价表达是否过度；
- 从不同视角提出反例问题；
- 对创新性、意义、局限性作软性判断。

但它并不能自动证明数值是真的。

因此对 `math_mode` 最合理的迁移不是“3 个 Reviewer 投票决定模型对不对”，而是：

```text
Hard Evidence Gate 已通过
        ↓
2~3 个 Soft Reviewer
  - 数学合理性
  - 工程合理性
  - 竞赛评审视角
        ↓
Meta Reviewer
        ↓
输出需要补证据的争议项
```

### 5.8 AI Scientist：Confidence 应和“是否验证过”区分

AI Scientist reviewer 有 1–5 的 Confidence，并在定义中明确区分“是否仔细检查 math/other details”。

这给 `math_mode` 一个实用设计：

Reviewer 输出不要只有：

```text
PASS / FAIL
```

还应区分：

```text
verification_level:
  exact_check
  independent_numeric_check
  invariant_check
  literature_crosscheck
  llm_reasoned
  visual_only
  not_checked
```

以及：

```text
confidence
```

因为“LLM 很自信”和“程序精确复算通过”不是同一种证据等级。

### 5.9 ScienceAgentBench：科研评测先统一为可运行程序

ScienceAgentBench 的设计很直接：每个科研任务最终统一要求一个 self-contained Python program，然后从生成程序、真实执行结果和成本多个维度评价。

它公开的指标计算中包含：

```text
success_rate
valid_program_rate
codebert_score
cost
```

`compute_scores.py` 的执行链还做了以下检查：

```text
预测程序
  ↓
subprocess 真执行（900 s timeout）
  ↓
return code 检查
  ↓
指定 output 文件存在检查
  ↓
调用任务专用 eval()
  ↓
success / log_info
```

这再次说明：科研 Agent 评价不能从文本输出直接跳到“正确”。

### 5.10 ScienceAgentBench：验证器会出错，false negative 是一等工程问题

ScienceAgentBench README 在 2026-04-30 明确发布 verified version，目的就是 **mitigate false negatives in evaluation**。

这是本轮对 `math_mode` 最有长期价值的第二个新发现。

门禁越多，并不天然越可靠。可能出现：

```text
正确结果
  ↓
错误 evaluator 假设
  ↓
被错误判 FAIL
```

例如数学建模中很常见：

- evaluator 假定唯一答案，但问题允许多个等价最优解；
- 绝对误差阈值不适合大数量级结果；
- 不同单位制数值不同但物理等价；
- 路径/节点编号不同但目标值与约束均正确；
- 随机算法正常波动被当作复现失败；
- 画图像素不完全一致却表达同一科学结论；
- 浮点排序/solver tolerance 导致边界项差异。

所以 Reviewer 系统必须支持：

```text
judge_version
checker_version
tolerance_policy
known_false_negative_cases
regression_suite
manual_override_reason
```

否则随着规则堆叠，系统可能越来越“严格”，但不是越来越正确。

### 5.11 ScienceAgentBench：视觉 Judge 适合视觉语义，不适合替代数据验证

其 `gpt4_visual_judge.py` 对生成图与 gold 图进行多次视觉评分并取平均。

可借鉴的是：

- 图像 QA 可以有模型辅助；
- 多样本评分可降低单次随机性。

但对 `math_mode` 不应把“图看起来像正确图”当作结果验证。

正确顺序仍应是：

```text
结构化数据正确
→ 图脚本只读结构化结果
→ 图像语义/布局 QA
```

这与当前 `math_mode` “先算后画、图不能成为事实源”的规则完全一致，应保持。

## 6. Agent / Skill 设计

本轮不建议建立一个全能 `ReviewerAgent`。更适合 `math_mode` 的分层结构是：

```text
                    Competition Reviewer Layer
                              │
             ┌────────────────┴────────────────┐
             │                                 │
      Deterministic Gates                 Soft Review
             │                                 │
   ┌─────────┼──────────┐              ┌───────┼────────┐
   │         │          │              │       │        │
Unit/Dim  Constraint  Execution      Math    Domain   Judge
Checker   Checker     Reproducer    Critic   Critic   Critic
   │         │          │              └───────┼────────┘
   └─────────┼──────────┘                      │
             │                             Meta Reviewer
      Evidence Bundle                         │
             └──────────────┬──────────────────┘
                            ↓
                     Validation Report
                            ↓
                    Judge Regression Set
```

### A. 可以直接借鉴

#### 1. Hierarchical Rubric Tree

每问建立 criterion tree，而不是一个总分。

建议叶节点最少覆盖：

- 输入/单位/坐标系；
- 模型实现；
- 执行成功；
- 约束/守恒/边界；
- 独立复算；
- 误差/验证；
- 稳健性/敏感性；
- 论文 claim 与证据一致；
- 官方输出格式。

#### 2. Evidence Stage 分类

每个 criterion 明确属于：

```text
implementation
execution
result
claim
presentation
```

不能因为 implementation PASS 就推断 result PASS。

#### 3. `valid_score` / `unknown`

区分“明确失败”和“验证过程自身无效”。

#### 4. JudgeEval 思路

在赛前建立 Reviewer regression corpus，专门测试 Judge 是否会误判。

### B. 可以改造后采用

#### 1. AI Scientist ensemble + meta-review

只用于软性判断：模型假设、合理性、创新性、局限性、论文 claim 强度。

改造点：

- 先输入经过 hard gate 的 evidence bundle；
- 每条 criticism 必须引用 criterion/evidence id；
- 不允许 reviewer 自己创造数值；
- disagreement 不自动平均掉，应生成争议项。

#### 2. PaperBench 的 binary leaves

数学建模中部分 criterion 可以 binary：

- 程序是否成功运行；
- 官方文件是否存在；
- 所有约束是否满足；
- 单位是否闭合。

但模型合理性、稳健性质量、创新性不能硬塞成 0/1，应保留等级或结构化说明。

### C. 可以作为对照实验

1. **当前规范 Reviewer vs Rubric-tree Reviewer**
   - 是否更容易定位失败原因；
   - 是否减少遗漏。

2. **LLM-only Reviewer vs Hard-gate + LLM Reviewer**
   - 重点测数值错误、单位错误、约束违约的漏检率。

3. **Single Reviewer vs Ensemble + Meta Reviewer**
   - 只测试软性评价，不测试确定性数值事实。

4. **无 Judge regression vs 有 regression**
   - 人工构造 20–50 个典型错误/正确样例，观察 prompt/checker 更新后的 false positive / false negative。

### D. 不建议采用

- 让一个 LLM 阅读论文后直接给“模型正确 9/10”；
- 多个 LLM 一致就视为数学正确；
- 用视觉 Judge 代替结构化数值检查；
- 把所有 criterion 加权后允许 hard failure 被高软分抵消；
- evaluator 改规则后不保留版本与 regression 结果；
- 只检查最终 PDF，不读取实际结果与执行日志。

## 7. Workflow

建议未来形成如下赛时验证流程（只作为设计建议，本轮不修改正式 workflow）：

```text
[1] Problem Contract
题面约束 + 单位 + 输出 + 目标 + 方法限制
        ↓
[2] Validation Rubric Build
每问生成 hierarchical criteria
        ↓
[3] Solver Run
求解代码真实运行
        ↓
[4] Fresh Reproduction
从唯一入口在干净状态重新执行核心结果
        ↓
[5] Deterministic Hard Gates
单位 / shape / output / constraints / leakage / hash / residual
        ↓
[6] Independent Numerical Checks
第二公式 / 第二实现 / 解析极限 / benchmark / solver crosscheck
        ↓
[7] Evidence Localization
每个 criterion 绑定结果、日志、脚本、图表、来源
        ↓
[8] Soft Reviewer Panel
数学合理性 / 工程合理性 / 竞赛评审
        ↓
[9] Meta Review
合并争议，但不得覆盖 hard failure
        ↓
[10] Validation Report
PASS / FAIL / UNKNOWN + evidence + explanation
        ↓
[11] 结果索引 / 支撑材料 / 论文
```

### 推荐状态

```text
UNVERIFIED
→ EXECUTED
→ HARD_GATE_PASS
→ INDEPENDENT_CHECK_PASS
→ SOFT_REVIEW_PASS
→ CLAIM_READY
```

失败状态至少区分：

```text
EXECUTION_FAIL
EVIDENCE_MISSING
HARD_CONSTRAINT_FAIL
NUMERICAL_MISMATCH
JUDGE_ERROR
VALIDATION_UNKNOWN
STALE_EVIDENCE
```

## 8. Code Execution / Tools

### PaperBench

确认存在真实代码执行，而且有非常强的隔离：

- Agent 在第一容器工作；
- submission 在 fresh reproduction container 执行；
- executed submission 再交给第三个 grading container；
- 运行目录保存 agent log、grade、metadata、run log、status、submission snapshot 和 executed submission artifact。

这比单纯“agent 说自己跑过”可靠得多。

### AI Scientist Reviewer

本轮读取的 `perform_review.py` 主要是文档级 Reviewer；该 reviewer 函数本身不承担数学程序的独立执行。

因此它适合 Reviewer 的软性层，不适合成为数值真实性门禁。

### ScienceAgentBench

确认真实执行：

- 独立 `sci-agent-eval` 环境；
- 推荐 Dockerized evaluation；
- 支持 parallel workers；
- evaluator 会实际运行预测程序；
- 有 timeout、return code、output file existence、task-specific eval；
- 运行轨迹与评价日志使用 JSONL；
- visual output 另有视觉 Judge。

## 9. QA / Reviewer / Verification

### 9.1 最关键的新认识：Reviewer 不是 QA 的终点

应是：

```text
Solver 需要验证
Reviewer 也需要验证
Evaluator 也需要验证
```

即：

```text
Solution QA
↓
Judge QA
↓
Judge Regression
```

### 9.2 建议的 Judge Regression 数据集

赛前可从历史题或合成最小例子建立：

#### 正确样例

- 等价单位转换；
- 多个等价最优解；
- solver tolerance 范围内的数值差；
- 不同随机 seed 但统计结论一致；
- 同一关系的不同图型表达。

#### 错误样例

- 把 mm 当 m；
- 训练测试泄漏；
- 目标函数写反；
- 某个约束漏写；
- 论文数字与 JSON 不一致；
- 只生成图而没有底层结果；
- 结果文件来自旧 input hash；
- 运行失败但引用旧 artifact；
- 随机选一次最优 seed；
- 敏感性区间超出物理范围。

### 9.3 Judge 指标

PaperBench JudgeEval 提供了一个直接可借鉴的方法：

```text
Accuracy
Precision
Recall
Macro F1
```

对 `math_mode` 更应重点看：

```text
False Negative Rate
  正确结果被错误阻断

False Positive Rate
  错误结果被放进论文
```

由于本项目优先级是“结果真实性 > 自动化便利”，关键 hard gate 应偏向低 false positive；但同时必须防止 evaluator 设计错误造成大量 false negative。

### 9.4 Deterministic Checker 优先级

能程序检查的不要交给 LLM：

| 检查 | 首选方式 |
|---|---|
| 文件是否存在 | deterministic |
| 程序退出码 | deterministic |
| 单位/shape/schema | deterministic |
| 优化约束 | independent recompute |
| 守恒残差 | numeric invariant |
| 指标公式 | independent recompute |
| input/output hash | deterministic |
| 泄漏 | programmatic + data audit |
| 模型假设合理性 | LLM/domain reviewer |
| 创新性 | LLM + literature evidence |
| 论文解释是否过度 | LLM reviewer |

## 10. 值得借鉴的设计

### 10.1 “Evidence Bundle” 应成为 Reviewer 的唯一主要输入

不是把整个项目随意塞给 Reviewer，而是每个 criterion 绑定：

```text
criterion_id
requirement
checker_type
evidence_paths
source_hashes
execution_id
expected_invariant
tolerance
status
explanation
```

### 10.2 Hard Gate 不可被软分覆盖

建议未来总判定结构：

```text
if any critical_hard_gate == FAIL:
    result = BLOCKED
else:
    result = soft_scorecard(...)
```

而不是：

```text
0.4 * 准确性 + 0.2 * 创新 + 0.2 * 清晰 + 0.2 * 约束
```

后者可能出现“约束根本不满足，但因为图好看、模型新颖，总分仍高”的错误。

### 10.3 Judge disagreement 是信息，不是噪声

多个软 Reviewer 不一致时，应该输出：

```text
DISPUTED_CRITERION
```

以及各自理由和需要补的证据，而不是直接平均后消失。

### 10.4 Reviewer 自身要有版本

最低建议记录：

```text
reviewer_schema_version
checker_version
llm_model
prompt_hash
tolerance_policy_version
regression_suite_version
```

这与当前 `math_mode` 已经使用 SHA-256 和支撑材料 manifest 的理念一致，可以自然接上。

## 11. 存在的问题

### PaperBench 的限制

1. 主要针对 AI 论文复现，不是数学建模竞赛；
2. 多数叶 criterion 的 binary grading 不能原样覆盖连续数值/物理合理性；
3. LLM Judge 仍有误判风险，所以才需要 JudgeEval；
4. 三容器重执行成本高，华为杯赛时必须选择性使用。

### AI Scientist Reviewer 的限制

1. 主要从论文文本评审；
2. ensemble 一致不代表事实正确；
3. numerical score 平均容易制造“看似稳定”的假确定性；
4. reflection 只能修正推理文本，不能替代程序复算。

### ScienceAgentBench 的限制

1. 任务统一成 Python 程序，不能覆盖全部数学建模任务，如纯解析推导、复杂 MATLAB/COMSOL/Julia workflow；
2. CodeBERTScore 对 `math_mode` 不应成为核心指标；
3. visual judge 适合图形相似性，不适合证明科学结论；
4. verified version 本身说明 evaluator 也存在维护成本。

## 12. 与 math-mode 对比

| 能力 | math-mode | 本轮项目 | 差异 |
|---|---|---|---|
| 真实代码运行 | 已明确要求 | PaperBench/SAB 强制执行 | 保持；建议增加 fresh reproduction 语义 |
| 独立验证 | 规范层已很强 | PaperBench criterion 化 | math_mode 缺统一机器 Rubric |
| 量纲/守恒/边界 | 求解规范已有 | PaperBench 不专门面向物理 | math_mode 已有领域优势，应该编译成 checker |
| Criterion 分层 | 分散在 Evidence Matrix/规范 | PaperBench TaskNode tree | 建议新增统一 Validation Rubric |
| Implementation/Execution/Result 区分 | 当前未形成统一状态模型 | PaperBench 明确拆分 | **新增价值高** |
| Hard gate | 视觉/支撑材料已有局部门禁 | PaperBench 有 result hard gate | 应推广到求解真实性 |
| 证据定位 | 结果索引/支撑材料已有 | PaperBench criterion→relevant files | 可以直接融合 |
| Reviewer 多视角 | 尚未正式结构化 | AI Scientist ensemble/meta-review | 只用于 soft review |
| Reviewer confidence | 无统一协议 | AI Scientist 有 Confidence | 可改造加入 verification level |
| Judge 自身评测 | 未发现统一 Judge regression | PaperBench JudgeEval | **P0 缺口** |
| Evaluator false-negative 管理 | 未发现专门机制 | SAB 2026 verified version | **P0/P1 缺口** |
| evaluator version | SHA/manifest 可承载但未专门定义 | SAB/PaperBench 显示必要性 | 建议接入 provenance |
| 图像 QA | 已有 academic-figure-skill + visual audit | SAB 有 LLM visual judge | math_mode 当前“数据先于图”更合理，保持 |
| 可复现 artifact | 支撑材料 + SHA-256 已强 | PaperBench/SAB 也保存运行 artifact | 保持并向 validation report 延伸 |

### 当前 math-mode 已经有什么？

- 强规则层：题面约束、量纲、守恒、验证、稳健性、独立复算；
- 强证据层：结果索引、视觉计划、支撑材料、SHA；
- 强论文门禁：LaTeX/PDF/图表审计；
- 已经比很多通用 Agent 更强调“不能伪造、先算后写”。

### 新项目有什么我们没有？

- 层级 criterion tree；
- implementation / execution / result 的明确三分；
- 每个 criterion 的 `valid_score` 和 explanation；
- evidence localization；
- hard gate 优先于 LLM judge；
- JudgeEval；
- evaluator false-negative 回归维护；
- soft reviewer ensemble/meta-review 的边界化设计。

### 是否值得增加？

值得，但不是新增“大一统 Reviewer”，而是新增 **Validation Contract + Checker 层**。

### 应放在哪一层？

建议未来位于：

```text
求解代码/结构化结果
        ↓
Validation Layer   ← 新增
        ↓
结果索引/支撑材料
        ↓
论文写作
```

### 会影响哪些已有模块？

若未来实现，会与以下模块对接：

- `求解/题面约束清单.md`
- `求解/求解计划.md`
- `求解/视觉计划.json`
- `求解/结果索引.md`
- `求解/支撑材料清单.json`
- `audit_visual_plan.py`
- `audit_supporting_materials.py`
- 论文 Evidence Matrix

但本轮仅研究，不修改上述正式文件。

### 五类判断

- **保持**：当前题面优先、真实执行、独立验证、先算后画、SHA 支撑材料机制。
- **改进**：把自然语言验证规则转换为 criterion + checker + evidence 的机器契约。
- **新增**：JudgeEval / Reviewer regression、evaluator version、false-negative case set。
- **替换**：未来若存在“单一 LLM 综合评价模型是否正确”的做法，应替换为分层验证。
- **暂不采用**：PaperBench 的全量三容器复现、CodeBERT 相似度作为核心评分、视觉相似度当科学正确性。

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：设计 `Validation Rubric` 机器契约

建议未来新增概念（只设计，不创建）：

```text
求解/验证清单.json
```

可能字段：

```json
{
  "criterion_id": "q1.physics.mass_balance",
  "requirement": "质量守恒残差在给定容差内",
  "criticality": "hard",
  "evidence_stage": "result",
  "checker_type": "numeric_invariant",
  "checker_entry": "...",
  "evidence_paths": ["..."],
  "tolerance_policy": "...",
  "status": "pass",
  "score_valid": true,
  "explanation": "...",
  "judge_version": "..."
}
```

#### P0-2：实现“硬门禁优先”的 Reviewer 设计

至少覆盖：

- 程序退出码；
- 输入 hash 新鲜度；
- 结果文件存在；
- 官方 schema；
- 约束可行性；
- 关键单位；
- 训练测试泄漏；
- 独立复算；
- 关键残差。

这些通过后，才允许 Soft Reviewer 讨论“合理性/创新性/叙事”。

#### P0-3：建立 Reviewer Regression / JudgeEval

这是本轮优先级最高的新建议之一。

赛前为 `competition-reviewer` 准备一批人工已知结果：

```text
正确案例
错误案例
边界案例
等价答案案例
随机波动案例
单位转换案例
solver tolerance 案例
```

每次修改 Reviewer prompt/checker 后计算：

```text
precision / recall / F1
false positive / false negative
```

### P1：值得实验

#### P1-1：三层 Reviewer

```text
Invariant Checker
      ↓
Evidence Judge
      ↓
Meta Reviewer
```

其中：

- Invariant Checker 不用 LLM；
- Evidence Judge 混合程序规则和 LLM；
- Meta Reviewer 只处理开放问题和 Reviewer disagreement。

#### P1-2：独立 reproduction 模式

对关键最终模型，在论文接入前，从统一入口重新执行一次；不要直接使用开发过程中内存状态或手工拼接结果。

赛时可只对进入论文主线的 finalist model 执行，避免 PaperBench 式全量高成本。

#### P1-3：Reviewer disagreement queue

多个 reviewer 分歧较大时，不自动平均，生成：

```text
求解/待补证据.md
```

概念上记录：

- criterion；
- reviewer A/B 分歧；
- 缺的证据；
- 是否阻塞。

#### P1-4：Evaluator False-Negative Regression

借鉴 ScienceAgentBench verified release 思路：一旦发现 evaluator 错误判 FAIL，把该 case 加入 regression suite，防止后续版本复发。

### P2：长期考虑

- 为不同赛题类型维护 checker registry：预测 / 优化 / 机理 / 仿真 / 时空 / 网络；
- 建立历史华为杯 Reviewer benchmark；
- 对关键公式做 symbolic dimensional checking；
- 用 property-based testing 自动生成边界/反例；
- 建立 cross-solver 验证接口，如 scipy ↔ cvxpy、解析 ↔ 数值、Python ↔ MATLAB/Julia；
- Reviewer 模型升级时自动跑历史 JudgeEval。

### 不建议采用

- 直接把 AI Scientist 的论文评审分数当数学正确性；
- 用 3 个 LLM 投票替代约束/单位/数值复算；
- 为“严格”而把所有验证都设 hard gate；
- evaluator 没有 `UNKNOWN/JUDGE_ERROR` 状态；
- 没有回归集就频繁改 Reviewer prompt；
- 用模型相似度或图像相似度替代结果真实性。

## 14. 可形成的新 Skill / Agent

仅提出设计建议，不创建：

### `competition-validation-orchestrator`

职责：从题面约束 + 求解计划生成验证 criterion tree，并路由到不同 checker。

### `deterministic-invariant-checker`

职责：单位、shape、约束、残差、hash、schema、leakage、output existence 等硬验证。

### `independent-result-verifier`

职责：用第二实现/第二公式/第二 solver 复算关键指标。

### `competition-reviewer`

职责：只对已经通过 hard evidence gate 的模型做数学合理性、工程解释、竞赛价值和 claim strength 评审。

### `reviewer-regression-evaluator`

职责：使用人工标注的历史 fault cases 评价 Reviewer 本身的 precision/recall/F1 和 false positive/negative。

### `review-meta-agent`

职责：合并 soft reviewers 的争议，要求补证据，而不是覆盖 hard gate。

## 15. 与历史调研的去重检查

### 已有主题集合

1. 14:00：Evidence-first Scientific Workflow、实验状态、Reviewer 概念；
2. 15:06：AIDE/ML-Master/MLE-Dojo 的候选模型搜索、实验树、并行执行、MCTS/UCT、预算和实验账本。

### 本轮明确未重复的内容

- 不再论证“为什么需要 Reviewer”；
- 不再研究模型候选搜索策略；
- 不重复 AIDE / ML-Master / MLE-Dojo；
- 不把“保存 evidence”本身当新发现。

### 本轮新增认知

1. **PaperBench 的 implementation / execution / result criterion 分层**；
2. **criterion-level evidence localization + hard gate**；
3. **`valid_score`：失败与 Judge 无效必须区分**；
4. **JudgeEval：Reviewer 本身要由人工 ground truth 校准**；
5. **AI Scientist reviewer 的 ensemble / meta-review / reflection 代码级机制，以及它只适合 soft review 的边界**；
6. **ScienceAgentBench 2026 verified release 显示 evaluator false negative 必须被当作真实工程风险**；
7. **Validation Contract 应位于 Solver 与论文证据层之间**。

### AI Scientist 重访说明

该项目在 14:00 只做了高层机制阅读。本轮明确新增了 `perform_review.py` 的代码级分析，因此不是措辞变化式重复。

## 16. 下一轮推荐方向

建议下一轮主动轮换到：

**赛时 Memory / Checkpoint / Resume 与长时程工作流状态。**

重点问题：

- 48–72 小时赛时如何让 Agent 在压缩上下文后不丢失题面硬约束；
- 如何区分聊天 memory、事实 memory、实验 memory 和 workflow state；
- checkpoint 如何绑定 input/code/result hash；
- Agent 崩溃或模型切换后如何从可信 checkpoint 恢复；
- 多 Agent 并行时如何防止旧结论覆盖新证据；
- 哪些长期记忆应该进入比赛项目，哪些应保持 session-local。

优先研究具备代码级 state/checkpoint/resume 的 scientific/coding workflow，而不是泛泛聊天记忆项目。

## 17. Sources

### 已阅读源码 / 官方仓库文档

#### 当前 math_mode

- https://github.com/shaxiaoguang123/math_mode/blob/main/README.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/华为杯_求解规范/华为杯_求解规范.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_14-00_scientific-agent-evidence-workflow.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_15-06_model-selection-tree-search.md

#### PaperBench / OpenAI Frontier Evals

- https://github.com/openai/frontier-evals/tree/main/project/paperbench
- https://github.com/openai/frontier-evals/blob/main/project/paperbench/README.md
- https://github.com/openai/frontier-evals/blob/main/project/paperbench/paperbench/rubric/tasks.py
- https://github.com/openai/frontier-evals/blob/main/project/paperbench/paperbench/judge/graded_task_node.py
- https://github.com/openai/frontier-evals/blob/main/project/paperbench/paperbench/judge/simple.py
- https://github.com/openai/frontier-evals/blob/main/project/paperbench/paperbench/judge/judge_eval/README.md

#### AI Scientist Reviewer

- https://github.com/SakanaAI/AI-Scientist
- https://github.com/SakanaAI/AI-Scientist/blob/main/ai_scientist/perform_review.py

#### ScienceAgentBench

- https://github.com/OSU-NLP-Group/ScienceAgentBench
- https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/main/README.md
- https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/main/compute_scores.py
- https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/main/calculate_metrics.py
- https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/main/gpt4_visual_judge.py

### 官方项目页 / 论文说明

- OpenAI PaperBench：https://openai.com/index/paperbench/
- ScienceAgentBench 项目主页：https://osu-nlp-group.github.io/ScienceAgentBench/
- ScienceAgentBench arXiv：https://arxiv.org/abs/2410.05080

### 证据边界说明

- PaperBench：本轮已读取当前 `frontier-evals` 中 README、Rubric 数据结构、Judge 主要源码和 JudgeEval 文档；报告中的 criterion 分层、fresh reproduction、hard gate、JudgeEval 均来自实际源码/官方文档。
- AI Scientist：本轮已读取 `perform_review.py`，确认 ensemble、meta-review、reflection、结构化评分；未把其文本 Reviewer 描述成独立数值验证器。
- ScienceAgentBench：本轮已读取 README、执行评分脚本、指标脚本与视觉 Judge；2026-04-30 verified version 的“mitigate false negatives”来自当前官方 README。未声称本轮实际运行了这三个外部项目的 benchmark。
- `math_mode`：本轮只读对比，不修改正式 Agent / Skill / workflow / 求解规范。