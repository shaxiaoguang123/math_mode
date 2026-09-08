你现在作为 **高级 AI Agent 架构师、数学建模竞赛研究员、科研软件工程师、Python 工程师、质量保障负责人和 Git 工程负责人**，对我的数学建模项目进行一次**源码级研究、架构审计和分阶段重构**。

项目仓库：

`shaxiaoguang123/math_mode`

本任务的目标不是简单修改 README、增加几个 Prompt、堆更多 Skill，也不是重新创建一个与当前项目平行的新项目，而是：

> **在充分保留当前 `math_mode` 已经做得好的部分的基础上，把它升级成一套真正可执行、可恢复、可追溯、可验证、可审计、适用于“华为杯”中国研究生数学建模竞赛的 Evidence-Driven Mathematical Modeling Agent System。**

最终目标不是“一键生成看起来完整的论文”，而是建立下面这条可信链：

```text
官方题目 / 原始附件
        ↓
题意解析与约束冻结
        ↓
歧义与假设管理
        ↓
子问题依赖 DAG
        ↓
候选模型与风险探针
        ↓
Baseline + Main + Conditional Fallback
        ↓
赛题专用真实代码
        ↓
受控执行
        ↓
Run Manifest
        ↓
独立验证
        ↓
Evidence Gate
        ↓
Frozen Results
        ↓
Figure / Table Evidence
        ↓
论文
        ↓
官方格式与提交材料
        ↓
Final Audit
```

---

# 一、最重要的执行原则

你必须**先真实阅读，再设计，再实现**。

禁止以下做法：

1. 只看 README 就判断项目能力；
2. 只根据文件名猜实现；
3. 把其他项目整个复制进 `math_mode`；
4. 大量增加 Markdown 规则但没有机器执行器；
5. 为了“多 Agent”而机械增加 Agent 数量；
6. 为了“高级”而增加模型动物园；
7. 用“代码没有报错”作为模型正确的证明；
8. 用 LLM 自己生成的结论验证自己；
9. 论文中出现无法追溯到真实代码结果的数值；
10. 一个 Agent 同时负责“生产结果”和“最终批准结果”；
11. 把参考论文结果、优秀论文数字或 benchmark 数字当成当前赛题结果；
12. 把 Warning 当 PASS；
13. 用 placeholder、示例结果、scaffold result 通过正式门禁；
14. 修改上游结果后继续使用旧图、旧论文数字、旧审计报告；
15. 直接覆盖原始题目、原始数据、官方 Word 模板或官方答案文件；
16. 因为篇幅不足而虚构实验、重复图片、复制结论或放大版面；
17. 未核对当届官方文件就把经验性规则当成官方硬要求；
18. 未检查许可证就复制外部项目源码。

本次任务是**仓库工程优化**，不是正式求解某一道赛题。除非仓库中存在专门用于 regression 的历史赛题，否则不要生成虚假的正式赛题结果。

---

# 二、首先对当前 `math_mode` 做源码级 Forensics

任何修改之前，完整递归检查当前仓库。

至少阅读：

```text
AGENTS.md
CLAUDE.md

华为杯_求解规范/
  华为杯_求解规范.md
  华为杯_绘图规范.md
  视觉计划.schema.json
  支撑材料清单.schema.json
  tools/*.py

华为杯_论文规范模板/
  README.md
  华为杯_论文章节规范.md
  agent_manifest.schema.json
  page_targets.json
  gmcm-title.sty
  gmcmthesis.cls
  tools/*.py

.agents/
.claude/

题目/
数据/
求解/
论文/
提交附件/

.gitignore
.git/
```

还要检查：

```text
Git 当前 branch
HEAD commit
commit history
remote
tracked / untracked files
大文件
二进制模板
现有测试
现有 CI
Python 入口
schema
所有 audit/build/init 脚本
所有硬编码路径
所有比赛届次硬编码
所有 page / cover / anonymity / TOC 规则
```

不要依赖 AGENTS.md 中对仓库自身状态的旧描述。

**代码和真实文件状态优先于文档中的历史描述。**

生成：

```text
docs/audit/current_repository_audit.md
docs/audit/current_repository_inventory.json
```

至少说明：

* 当前项目真正实现了什么；
* 哪些只是规范；
* 哪些已经有机器执行器；
* 哪些有 schema；
* 哪些有 PASS/FAIL；
* 哪些没有真实验证；
* 哪些规则重复；
* 哪些规则已经漂移；
* 哪些属于项目经验规则；
* 哪些是真正官方规则；
* 哪些模块不应改动。

---

# 三、深入阅读以下参考项目的真实代码

把参考项目放在**仓库之外的临时研究目录**，不要把完整第三方仓库提交进 `math_mode`。

推荐使用：

```text
../mathmodel_reference/
```

使用 Git/GitHub 获取以下项目，并记录研究时的 commit SHA。

必须研究：

```text
usail-hkust/LLM-MM-Agent
yushui2022/MathModel-Skill
Hjdd14/math-modeling
zhnnky329/MathModeling-skills
SatakaGintoki/MathSkill
usail-hkust/dslighting
```

可补充：

```text
ModelingAgent / ModelingBench
其他真正包含执行器、状态机、benchmark 或 audit 的数学建模 Agent
```

不要因为一个仓库名字里有 30、50 个 Skills 就认为它更好。

评价重点是：

```text
有没有真实状态机
有没有真实执行
有没有真实验证
有没有可恢复工作流
有没有输入/代码/输出 hash
有没有 stale propagation
有没有独立 evaluator
有没有 benchmark
有没有 CI
有没有 failure handling
有没有 evidence contract
```

---

# 四、对每个参考项目必须读哪些内容

## A. MM-Agent

至少检查：

```text
MMAgent/main.py
MMAgent/agent/coordinator.py
MMAgent/agent/problem_analysis.py
MMAgent/agent/problem_decompse.py
MMAgent/agent/retrieve_method.py
MMAgent/agent/task_solving.py
MMAgent/utils/computational_solving.py
MMAgent/HMML/HMML.*
MMAgent/prompt/*
```

重点学习：

### 1. 子问题 DAG

学习其：

```text
Task dependency analysis
→ DAG construction
→ Topological sorting
→ fallback dependency chain
```

但是不要直接照抄实现。

我们需要更加严格：

```text
DAG JSON schema
cycle detection
unknown dependency detection
upstream result hash
downstream stale propagation
```

### 2. Actor → Critic → Improvement

借鉴：

```text
生成方案
→ 独立批评
→ 修正
```

但不能允许同一个模型无限自我循环。

最多：

```text
2~3 轮
```

随后必须进入 deterministic validation。

### 3. HMML / 方法检索

借鉴：

```text
题型
→ 建模方法 family
→ candidate methods
```

但不要建立一个“万能模型推荐器”。

方法检索只能生成候选。

最终模型必须经过：

```text
data compatibility
assumption checks
output degeneracy
sensitivity
scale
baseline comparison
```

### 4. 自动代码生成与 debug

学习：

```text
生成代码
→ 执行
→ stderr
→ 修复
→ 再执行
```

但明确禁止复制 MM-Agent 中以下弱点：

```text
shell=True
仅检查 Traceback 判断成功
没有完整 provenance
没有独立结果验证
无限或过多 retry
把执行成功等同模型成功
```

---

# 五、MathModel-Skill 重点学习内容

深入阅读其：

```text
paper-workflow-orchestrator
workflow_guard.py
preflight_check.py
model-code-and-result-generator
run_modeling.py
quality-assurance-auditor/evidence_gate.py
context-memory-keeper
paper-formal-writer
```

重点借鉴：

## 1. Preflight

输入第一次进入系统时：

```text
文件角色
文件大小
SHA-256
题面 / 数据 / 模板 / 说明
```

必须冻结。

下游禁止重新凭文件名猜角色。

## 2. Workflow Guard

每阶段进入前真正执行：

```text
guard(stage)
```

不能只写：

> “请确保上一阶段完成”。

## 3. Run Manifest

真正记录：

```text
script
command
return code
input files
input hashes
code hash
output files
output hashes
question IDs
```

## 4. Evidence Gate

论文之前必须证明：

```text
结果是真实运行得到
代码没有运行后被偷偷修改
输入没有发生漂移
输出文件真实存在
指标非空
指标 finite
图表不是 placeholder
结论能映射回 question
```

## 5. Workflow Memory

支持：

```text
中断
恢复
长上下文
重新打开项目
```

但不要依赖聊天记忆作为唯一状态。

磁盘上的机器状态必须是事实源。

---

# 六、Hjdd14/math-modeling 重点学习内容

重点阅读：

```text
SKILL.md
references/workflow.md
tools/workflow_runner.py
tools/state_manager.py
tools/pipeline_check.py
所有 checker
tests/
evals/
.github/workflows/ci.yml
```

重点吸收以下设计。

## 1. problem_brief

建立一份真正的结构化问题事实源。

## 2. Ambiguity Register

当前 `math_mode` 已经有“题面约束清单”，但还应增加：

```text
题目没有说明清楚什么？
```

例如：

```text
单位歧义
边界定义
评价指标口径
变量含义
题目内部矛盾
附件与正文冲突
“最优”的实际含义
```

## 3. Assumption Ledger

所有假设必须记录：

```text
assumption_id
内容
来源
必要假设 / 简化假设
影响问题
影响公式
验证方法
敏感性状态
当前状态
```

## 4. 五视角建模

可以借鉴：

```text
Optimization Agent
Statistics Agent
Mechanism Agent
Engineering Agent
Innovation Agent
```

但是：

> 多 Agent 是候选方案生成器，不是投票决定真理的系统。

## 5. 独立复现 Agent

必须只读：

```text
原始输入
最终 model spec
最终输出
```

不要读取主代码的内部中间状态。

核心结果必须尽量独立复算。

## 6. Judge Panel

可以建立多个不同职责评委：

```text
数学正确性
统计有效性
工程解释
代码复现
图表证据
竞赛评分
```

最后由 deterministic gate 判断是否存在 blocker。

不要让 LLM 评分本身成为 PASS 的唯一标准。

## 7. CI + benchmark

必须学习其：

```text
fixture workspace
negative fixture
pipeline checker
mini benchmark
CI
```

---

# 七、zhnnky329/MathModeling-skills 重点学习内容

重点阅读：

```text
AGENTS.md
method-selector
risk-probe-contract
workflow-orchestrator
solution-package-builder
consistency-auditor
quality-assurance-auditor
```

核心吸收：

## 1. 不再用“模型动物园”

每个问题原则上只保留：

```text
1 个 main_candidate
1 个 genuinely usable baseline
最多 1 个 conditional_fallback
```

如果一个简单模型不能完成题目的真实任务：

```text
diagnostic_reference
```

不能叫 Baseline。

## 2. Risk Probe

正式实现复杂模型之前先检查：

```text
executability
data coverage
load-bearing assumptions
output degeneracy
perturbation sensitivity
scale/runtime
```

Verdict：

```text
PASS
CONDITIONAL
FAIL
```

## 3. Fallback 必须有触发条件

不能写：

> “如果主模型不好，就用模型 B。”

必须是机器可检查条件，例如：

```text
constraint_violation_rate > 0
CV_RMSE deterioration > 10%
runtime > official_limit
parameter instability > threshold
```

## 4. Frozen Numbers

采用：

```text
code
↓
canonical results
↓
freeze
↓
paper
```

禁止论文直接从随机 CSV 或控制台复制数字。

## 5. Stale Propagation

如果发生：

```text
数据变了
代码变了
参数变了
公式变了
```

任何依赖结果自动：

```text
STALE
```

然后：

```text
重跑
→ 重验证
→ 重冻结
```

## 6. Lean / Submission

避免过程中过度 bureaucratic。

设计两个 rigor profile：

```text
lean
submission
```

探索阶段只保存核心 machine contracts。

最终阶段才生成完整审计材料。

---

# 八、SatakaGintoki/MathSkill 重点学习

重点研究：

```text
freeze_baseline.py
validate_workspace.py
agents/*
quality-gates
paper-evidence-contract
```

吸收：

## Blind Baseline Freeze

在 benchmark、训练或研究 Agent 自主建模能力时：

```text
先独立解题
→ 代码
→ 结果
→ 论文基线
→ SHA256 freeze
→ 之后才允许看同题优秀论文
```

这应该作为：

```text
blind_reference_mode
```

而不是所有正式赛题的强制模式。

目的：

> 防止“检索能力”冒充“建模能力”。

---

# 九、DSLighting 重点学习

重点学习架构思想：

```text
Agent
Workflow
Operator
Service
Workspace
State
Sandbox
AgentResult
Benchmark
```

借鉴：

```text
显式 Agent Harness
执行后端抽象
统一 Result object
DAG runtime
benchmark framework
```

但是注意：

> DSLighting 使用 AGPL 等许可证约束时，不要直接复制代码到本项目。

只借鉴架构思想。

如果确实要复制源码：

1. 先检查 LICENSE；
2. 明确 compatibility；
3. 记录文件来源；
4. 记录许可证；
5. 未确认兼容则不要复制。

---

# 十、为所有参考项目建立 Source Map

创建：

```text
docs/research/reference_source_map.md
```

格式：

| 来源项目 | 实际读取文件 | 值得借鉴 | 不应照搬 | MathMode 对应设计 | License |
| ---- | ------ | ---- | ---- | ------------- | ------- |

不能只写 README 总结。

必须指向真实实现文件。

---

# 十一、MathMode V2 的架构原则

不要推翻现有优秀能力。

目前应该尽量保留：

```text
华为杯_求解规范
华为杯_绘图规范
academic-figure-skill
视觉计划
audit_visual_plan.py
支撑材料清单
build_supporting_materials.py
audit_supporting_materials.py
LaTeX-first 论文链
audit_tex.py
audit_paper.py
DOCX 派生工具
```

新的重点是：

> **补齐“题意 → 模型 → 代码 → 结果 → 验证”这一段的机器执行层。**

---

# 十二、统一 Source of Truth

必须建立清晰的唯一事实源。

推荐：

```text
官方规则事实源
competition_policy.json

输入事实源
input_manifest.json

题意事实源
problem_frame.json

问题依赖事实源
problem_dag.json

歧义事实源
ambiguity_register.json

假设事实源
assumption_ledger.jsonl

符号事实源
symbol_table.json

模型事实源
model_spec.json

运行事实源
run_manifest.json

验证事实源
validation_summary.json

论文数字事实源
frozen_numbers.json

视觉事实源
视觉计划.json

提交事实源
支撑材料清单.json
```

不要在：

```text
AGENTS.md
CLAUDE.md
README
论文
多个 JSON
```

重复维护同一个事实。

---

# 十三、建议增加的机器协议

在现有架构上增加以下 schema。

具体目录可以根据当前仓库实际结构微调，但不要无意义大搬家。

建议：

```text
华为杯_求解规范/schemas/

competition_policy.schema.json
input_manifest.schema.json
problem_frame.schema.json
problem_dag.schema.json
ambiguity_register.schema.json
assumption_ledger.schema.json
symbol_table.schema.json

method_card.schema.json
risk_probe.schema.json
model_spec.schema.json

run_manifest.schema.json
validation_summary.schema.json
evidence_gate.schema.json

frozen_numbers.schema.json
workflow_state.schema.json
ai_usage.schema.json
```

---

# 十四、正式赛题工作区建议

正式赛题不要把状态散落。

推荐：

```text
求解/
├── 状态/
│   ├── competition_policy.json
│   ├── workflow_state.json
│   ├── input_manifest.json
│   ├── problem_frame.json
│   ├── problem_dag.json
│   ├── ambiguity_register.json
│   ├── assumption_ledger.jsonl
│   ├── symbol_table.json
│   └── ai_usage.jsonl
│
├── 问题一/
│   ├── 方法/
│   │   ├── method_card.json
│   │   ├── risk_probe_summary.json
│   │   └── model_spec.json
│   │
│   ├── 代码/
│   ├── 结果/
│   │   ├── experiments/
│   │   ├── run_manifest.json
│   │   ├── metrics.json
│   │   ├── validation_summary.json
│   │   └── frozen_numbers.json
│   │
│   ├── 验证/
│   └── 图片/
│
└── ...
```

尽量兼容当前：

```text
求解/问题X/
```

不要为了新架构破坏原路径。

---

# 十五、Agent 职责必须清楚

建立 Agent 不等于建立很多 Persona。

每个 Agent 必须有：

```text
允许读取什么
允许写什么
禁止做什么
输入 contract
输出 contract
PASS 条件
handoff
```

---

## Agent 1：Orchestrator

职责：

```text
阶段判断
状态读取
DAG 调度
并行/串行判断
失败回退
stale propagation
```

禁止：

```text
亲自选择模型
亲自伪造结果
亲自写正式论文结果
亲自批准自己的阶段
```

---

## Agent 2：Problem Framing Agent

负责：

```text
任务拆解
目标
输入
输出
约束
评价指标
时间/空间/CPU要求
官方附件要求
问题依赖
```

输出：

```text
problem_frame.json
```

---

## Agent 3：Ambiguity & Assumption Agent

负责：

```text
歧义
冲突
隐含定义
假设
单位
边界
```

输出：

```text
ambiguity_register.json
assumption_ledger.jsonl
symbol_table.json
```

未解决 High Severity ambiguity：

```text
不得静默进入建模
```

如果能根据官方题面或附件解决，则自动解决。

只有无法通过证据解决的歧义才阻塞。

---

## Agent 4：Data Auditor

只负责：

```text
文件角色
shape
dtype
missing
duplicate
range
unit
time
space
group
label
leakage risk
```

禁止：

> 在数据审计阶段擅自决定最终模型。

---

## Agent 5：Literature / Method Retrieval Agent

负责：

```text
寻找方法
官方定义
权威文献
相似题型
已知 failure modes
```

禁止：

```text
直接把优秀论文模型当答案
复制往届数字
复制往届实验结果
```

所有引用必须可验证。

---

## Agent 6：Modeling Council

候选角色：

```text
Mechanism Agent
Statistics Agent
Optimization Agent
Engineering Agent
Innovation Agent
```

根据题型动态启用。

不需要每题全部启用。

每个 Agent 独立输出候选方案。

---

## Agent 7：Method Screening / Critic Agent

负责：

```text
候选模型评估
baseline validity
assumption burden
data suitability
interpretability
compute cost
failure modes
```

生成：

```text
Main Candidate
Usable Baseline
Conditional Fallback
```

不能直接生成正式代码。

---

## Agent 8：Risk Probe Agent

正式实现之前进行小成本探针。

必须检查：

```text
executability
data coverage
assumptions
output degeneracy
perturbation sensitivity
runtime / memory
```

输出：

```text
PASS
CONDITIONAL
FAIL
```

---

## Agent 9：Model Decision Agent

根据：

```text
题面
risk probe
baseline
资源
竞赛限制
```

作选择。

系统需要支持：

```text
interaction_mode = autopilot
interaction_mode = human_gate
```

### autopilot

AI 可以作决定，但是必须写：

```json
"decided_by": "agent"
```

绝不能伪造成：

```json
"decided_by": "human"
```

### human_gate

等待用户决定。

不要把 zhnnky 的“Human Gate”硬编码到所有场景。

---

## Agent 10：Code Generation Agent

只能实现：

```text
approved main
approved baseline
```

Fallback 只有 trigger 被触发才能实现。

代码必须符合：

```text
唯一入口
显式 input path
显式 output path
固定 seed
计算与绘图分离
无隐藏全局状态
无绝对本机路径
```

---

## Agent 11：Execution Runner

它不是 LLM Agent，而应该是 deterministic tool。

必须：

```text
使用 sys.executable 或指定 interpreter
不用 shell=True
限制 cwd
timeout
捕获 stdout
捕获 stderr
记录 returncode
记录 duration
记录 environment
记录 seed
记录 input hashes
记录 code hash
记录 output hashes
```

设计：

```text
ExecutionBackend
```

第一版：

```text
LocalSubprocessBackend
```

未来可以：

```text
DockerBackend
E2BBackend
RemoteBackend
```

不要声称普通 subprocess 是真正 OS Sandbox。

接口上为未来 sandbox 留出扩展点即可。

---

## Agent 12：Independent Validator

这是整个系统最关键的 Agent 之一。

输入尽量只包括：

```text
原始数据
model_spec
最终输出
官方评价规则
```

不要读取主算法内部“自认为正确”的状态。

负责：

```text
硬约束重新计算
目标函数重新计算
评分公式重新计算
单位检查
范围检查
守恒检查
极限情况
小例 oracle
secondary solver
统计验证
```

---

## Agent 13：Evidence Auditor

这是 deterministic gate + LLM semantic review 的组合。

Deterministic gate 优先。

检查：

```text
code actually ran
return code = 0
input hashes current
code hash current
outputs exist
outputs non-empty
metrics finite
baseline exists
validation exists
hard constraints pass
run manifest current
no placeholder
no stale
```

然后才允许 semantic review。

---

## Agent 14：Visual Agent

继续使用现有：

```text
视觉计划
academic-figure-skill
audit_visual_plan.py
```

但 Figure 必须绑定：

```text
claim_id
evidence_id
run_id
result_file
frozen_number_id
```

论文图不能读取未冻结的临时输出。

---

## Agent 15：Paper Writer

只能读取：

```text
frozen_numbers
solution package
validated figures
validated tables
model spec
assumption ledger
verified references
```

禁止凭聊天记忆写数字。

---

## Agent 16：Compliance / Final Audit

独立检查：

```text
题面全部回答？
硬约束全部满足？
官方格式？
AI 使用披露？
匿名规则？
封面？
官方附件？
引用？
数字？
图表？
SHA？
提交材料？
```

任何 blocker：

```text
不能称 FINAL PASS
```

---

# 十六、建立明确的 Phase + Gate

建议外部流程保持简洁：

```text
Phase 0  Policy / Preflight
Phase 1  Problem + Data
Phase 2  Modeling Decision
Phase 3  Code + Experiment
Phase 4  Evidence + Freeze + Visual
Phase 5  Paper + Submission
```

对应机器 Gate：

---

## G0 — POLICY_READY

必须：

```text
当前比赛 policy 已加载
官方规则来源存在
模板 hash 已记录
heuristic 与 official 分开
```

---

## G1 — INPUTS_FROZEN

必须：

```text
input_manifest
SHA256
附件角色
原始文件只读
```

---

## G2 — PROBLEM_FRAMED

必须：

```text
problem_frame
problem_dag
symbol_table
ambiguity reviewed
assumptions reviewed
data audit
```

---

## G3 — METHOD_SCREENED

必须：

```text
Main
Baseline
optional Fallback
risk probe
```

---

## G3.5 — METHOD_DECIDED

必须：

```text
method decision exists
evidence refs exist
decision owner honest
```

---

## G4 — CODE_AND_RUN_VALID

必须：

```text
main ran
baseline ran
run manifest
code review
output contract
```

---

## G5 — EVIDENCE_PASSED

必须：

```text
independent validation
robustness / sensitivity where applicable
constraints
metric verification
no stale artifact
```

---

## G6 — RESULTS_FROZEN

生成：

```text
frozen_numbers.json
```

冻结以后：

```text
paper numbers only from freeze
```

---

## G7 — PAPER_READY

必须：

```text
visual QA
paper source
reference QA
format QA
```

---

## G8 — FINAL_AUDIT

必须：

```text
cross-media consistency
semantic completeness
submission package
AI disclosure
official policy
```

---

# 十七、建模质量必须如何保证

不要设计一个抽象“quality score”就结束。

至少建立以下真实机制。

---

## 1. Baseline

每个核心问题必须回答：

> 如果不用复杂模型，最简单可用方案是什么？

Baseline 必须：

```text
能完成真实任务
能输出同口径指标
```

否则只是：

```text
diagnostic reference
```

---

## 2. Risk Probe

复杂模型正式编码前先低成本验证。

---

## 3. Formula / Unit Check

建立：

```text
equation checker
unit checker
parameter provenance
```

核心变量必须：

```text
symbol
definition
unit
code variable
source
```

---

## 4. Independent Validator

主算法和验证器尽量不同实现。

---

## 5. Optimization Certificate

优化问题至少记录：

```text
feasibility
equality residual
inequality violation
objective recomputation
multi-start
solver status
best bound / gap（可获得时）
small-instance oracle（可行时）
```

---

## 6. Statistical Validation

预测/统计问题根据题型选择：

```text
KFold
GroupKFold
time split
rolling
spatial block
bootstrap
confidence interval
```

禁止：

```text
时间序列 random split
空间邻近样本 random leak
同设备窗口跨 train/test
目标域无标签却报告 Accuracy
```

---

## 7. Robustness

适用时必须：

```text
seed robustness
noise
missingness
parameter perturbation
constraint perturbation
scenario variation
```

不是所有问题都机械 Monte Carlo。

---

## 8. Ablation

只有模型确实包含可移除组件时做。

不要为了“有消融”制造假模块。

---

## 9. Sanity Check

必须按问题类型检查：

```text
range
monotonicity
sign
unit
physical upper/lower bound
conservation
symmetry
known special case
```

---

## 10. Negative Evidence

不能只问：

> 为什么结果是对的？

还要问：

> 什么证据可以证明它可能错？

---

# 十八、Frozen Results 与 Stale Propagation

必须设计统一 lineage。

例如：

```text
input
 └── code
      └── run
           ├── metrics
           ├── tables
           └── figures
                 ↓
              freeze
                 ↓
               paper
```

每个 canonical artifact 保存：

```text
artifact_id
created_at
sha256
depends_on
producer
status
```

状态：

```text
DRAFT
VALID
FROZEN
STALE
FAILED
```

如果父节点 hash 变化：

```text
所有 downstream 自动 STALE
```

禁止：

> 代码变了，但论文仍 PASS。

---

# 十九、Frozen Numbers 规则

`frozen_numbers.json`：

禁止手工修改。

只能：

```text
thaw
→ change canonical source
→ rerun
→ revalidate
→ refreeze
```

记录：

```text
freeze_change_log
```

论文数字引用：

```text
frozen_id
```

而不是：

```text
复制粘贴 0.9231
```

---

# 二十、模型运行稳定性

Runner 必须有：

```text
timeout
max retries
root-cause retry
```

Retry 规则：

同一根因最多：

```text
3 次
```

如果重复失败：

```text
回退上游
```

而不是：

```text
继续让 LLM 改 20 次
```

区分：

```text
ENV_FAILURE
DATA_FAILURE
CODE_FAILURE
MODEL_FAILURE
VALIDATION_FAILURE
POLICY_FAILURE
```

每种失败回退到不同阶段。

---

# 二十一、不要把日志堆满仓库

借鉴 lean/submission。

## lean

保存：

```text
manifest
method card
risk probe
run summary
validation summary
```

完整 stdout/stderr 只在：

```text
failure
warning
reproduction
```

时保留。

## submission

增加：

```text
freeze
full validation
paper package
final audit
```

---

# 二十二、Competition Policy 必须从代码和 Prompt 中分离

新增：

```text
competition_policy.json
```

至少：

```text
competition
year
edition

official_sources
official_template_path
official_template_sha256

cover_policy
anonymity_policy
abstract_policy
toc_policy
page_policy
reference_policy
ai_policy
attachment_policy
submission_policy
```

官方规则和项目 heuristic 必须分开：

```json
{
  "official": {},
  "project_recommendations": {}
}
```

---

# 二十三、重点修复当前 45 页逻辑

当前仓库如果仍存在：

```text
required_body_pages = 45
```

必须重新审查来源。

如果当前届官方标准没有最低 45 页要求：

不能：

```text
<45 = FAIL
```

应降级成：

```text
historical heuristic / warning
```

不能用优秀论文的页数：

> 推导出官方最低页数。

真正硬门禁应该是：

```text
Evidence completeness
```

而不是：

```text
page count
```

---

# 二十四、重新审计官方封面

不要假定当前：

```text
gmcm-title.sty
```

就是官方封面。

必须根据**当届官方标准文档**验证。

设计原则：

```text
Official Cover
≠
Anonymous Body
```

例如：

```text
Page 1:
official cover policy

Page 2+:
anonymity policy
```

如果当届要求封面填写团队信息：

匿名审计不能扫描第一页并因此失败。

---

# 二十五、TOC 不能硬编码为官方要求

如果当前：

```text
\maketoc
```

被强制生成，

必须确认：

> 当届官方标准文档是否要求目录。

如果不是官方要求：

把它做成：

```text
policy-controlled
```

---

# 二十六、比赛届次不能硬编码

不要把：

```text
第二十三届
二十三
2026
```

散落在 TeX/Python/Markdown。

统一读取：

```text
competition_policy
```

---

# 二十七、AI 使用记录机器化

新增：

```text
求解/状态/ai_usage.jsonl
```

记录：

```text
timestamp
provider
model
version/date
question_id
activity

literature
problem_analysis
modeling
coding
visualization
writing
review

input_scope
output_used
human_postprocess
artifact_refs
```

最终根据当届规定自动生成必要披露。

绝不能伪造“人工完成”。

---

# 二十八、保护 public template repo

当前 `math_mode` 是模板/工具仓库时，不应把正式比赛中的：

```text
队伍身份
未提交论文
大数据
官方答案
私有结果
```

意外推送到 public GitHub。

优化 `.gitignore`。

更推荐：

```text
math_mode
    ↓ init
独立 competition workspace
```

例如：

```text
../competitions/2026_problem_A/
```

提供：

```text
init_competition_workspace.py
```

默认不把正式工作区提交到公开模板库。

---

# 二十九、Agent/Claude/Codex 规则去重复

当前存在：

```text
AGENTS.md
CLAUDE.md
.agents/*
.claude/*
```

不要手工复制大量公共规则。

设计：

```text
canonical policy
       ↓
runtime-specific thin router
```

对于必须存在两份的 Skill：

增加：

```text
sync_agent_assets.py
sync_agent_assets.py --check
```

CI 检查两份行为一致。

---

# 三十、测试体系

当前 V2 必须有：

```text
tests/
fixtures/
.github/workflows/
```

不能只测试“happy path”。

---

## Unit Tests

覆盖：

```text
schema
hash
DAG
cycle
stale
freeze
manifest
path safety
policy
validator
```

---

## Negative Fixtures

至少：

```text
missing input
changed input hash
changed code after run
empty output
NaN metric
constraint violation
data leakage
stale freeze
missing baseline
placeholder result
cycle DAG
wrong official output
paper using unfrozen number
```

每个都应该确保：

```text
FAIL
```

---

## PASS Fixtures

建立小型可快速复现任务：

```text
regression
optimization
time series
mechanism / simulation
graph / scheduling
```

不必很复杂。

测试 workflow，不测试“是否得一等奖”。

---

# 三十一、End-to-End Historical Dry Run

V2 完成后，选择：

```text
一个已经结束的公开历史赛题
```

进行完整 dry-run。

如果用于评价 Agent 独立建模能力：

先：

```text
blind_reference_mode=true
```

完整运行：

```text
problem
→ model
→ code
→ validation
→ freeze
```

然后才读优秀论文。

需要比较：

```text
问题理解
方法合理性
结果正确性
证据覆盖
代码复现
论文链稳定性
```

不要比较：

> 谁的模型名字更高级。

---

# 三十二、CI 设计

至少增加 Fast CI。

建议：

```text
Windows latest
Python 3.11
Python 3.12
```

可补：

```text
Ubuntu
```

执行：

```text
compileall
pytest
schema tests
fixture tests
workflow guard
model evidence gate
stale tests
sync checks
```

不要让 GitHub CI 依赖：

```text
Microsoft Word COM
本地专有字体
人工安装软件
```

这些作为：

```text
local integration test
```

TeX 视觉测试也应分层：

```text
CI structural test
local official-render test
```

---

# 三十三、Reference / License Boundary

创建：

```text
docs/research/reference_source_map.md
```

如果借鉴的是思想：

写：

```text
inspired_by
```

如果复制源码：

必须记录：

```text
source repository
source file
commit
license
changes
```

尤其对：

```text
DSLighting
```

不要在许可证不兼容时复制。

---

# 三十四、不要继续把所有东西写进 AGENTS.md

最终目标：

`AGENTS.md` / `CLAUDE.md` 只负责：

```text
入口
核心禁令
阶段路由
如何调用机器 guard
```

详细规则：

```text
schemas
policy
tools
docs
```

不要让 20k–70k 字 Markdown 成为唯一执行机制。

---

# 三十五、建议实现阶段

严格分阶段开发。

不要一次大提交。

---

## T00 — Repository Forensics

只审计，不大改。

输出：

```text
current_repository_audit.md
inventory.json
current architecture diagram
known risks
test baseline
```

Gate：

```text
T00 PASS
```

---

## T01 — Reference Project Audit

真实阅读上述项目代码。

输出：

```text
reference_source_map.md
reference_architecture_comparison.md
borrow / reject matrix
```

Gate：

```text
每个关键设计必须指出真实源码依据
```

---

## T02 — V2 Architecture & Contracts

先设计：

```text
architecture_v2.md
workflow_v2.md
contract list
state machine
stale graph
```

不要先写大量实现。

---

## T03 — Competition Policy Layer

实现：

```text
competition_policy
official / heuristic split
cover policy
anonymous scope
page policy
TOC policy
edition config
```

修复当前硬编码。

---

## T04 — Modeling State Contracts

实现：

```text
problem_frame
DAG
ambiguity
assumption
symbol table
method card
risk probe
model spec
workflow state
```

---

## T05 — Modeling Runner

实现：

```text
ExecutionBackend
LocalSubprocessBackend
run_manifest
hashes
timeout
safe path
seed
environment
```

禁止：

```text
shell=True
```

---

## T06 — Independent Validation + Evidence Gate

实现：

```text
validation_summary
constraint validator
metric evaluator
model evidence gate
```

---

## T07 — Freeze + Stale Propagation

实现：

```text
frozen_numbers
freeze
thaw
dependency graph
stale detector
```

---

## T08 — Agent Layer

再增加：

```text
Orchestrator
Problem
Data
Model Council
Risk Probe
Code
Validator
Reviewer
```

不要反过来先做 Persona。

---

## T09 — Existing Visual / Paper Integration

接通：

```text
Evidence ID
→ Visual Plan
→ Figure
→ Frozen Results
→ Paper
```

不要破坏现有绘图系统。

---

## T10 — Tests + CI + Mini Benchmark

完成：

```text
pytest
fixtures
negative tests
GitHub Actions
mini benchmark
```

---

## T11 — Historical End-to-End Run

完整跑一题。

发现问题：

```text
修代码
→ 回归测试
→ 再跑
```

---

## T12 — Release Audit

同步：

```text
AGENTS.md
CLAUDE.md
README
schemas
docs
CHANGELOG
```

运行全部 Gate。

---

# 三十六、每个阶段必须做到

每阶段：

```text
1. 说明目标
2. 检查前置 Gate
3. 实现
4. 测试
5. 运行真实 checker
6. 输出结果
7. Git commit
8. 再进入下一阶段
```

失败时不能提交“看起来完成”。

---

# 三十七、修改影响等级

实现类似：

```text
NONE
LOCAL
CANONICAL
FROZEN
```

### NONE

文档错别字、注释。

### LOCAL

未冻结的实验代码。

### CANONICAL

```text
数据 schema
单位
公式
模型参数
模型定义
正式结果文件
```

需要 affected-question audit。

### FROZEN

任何影响论文数字的修改。

必须：

```text
THAW
→ RUN
→ VALIDATE
→ FREEZE
→ CONSISTENCY CHECK
```

---

# 三十八、模型结论的 Evidence Lineage

每个重要 conclusion：

```json
{
  "claim_id": "Q2-C03",
  "text": "...",
  "evidence_refs": [
    "Q2-METRIC-01",
    "Q2-FIG-03"
  ],
  "validation_refs": [
    "Q2-VAL-02"
  ],
  "confidence": "supported"
}
```

允许：

```text
supported
limited
exploratory
```

禁止：

```text
proven
```

除非数学上真正证明。

---

# 三十九、写作边界

Writer Agent 禁止：

```text
改模型
重新计算
擅自改数字
创造实验
虚构文献
```

发现证据不足：

```text
return evidence_gap
```

回到 Modeling，而不是补文字。

---

# 四十、创新边界

“创新”必须回答：

```text
解决哪个具体痛点？
baseline 有什么缺点？
你的改进是什么？
有什么真实 evidence？
付出了什么代价？
在哪些情况下失效？
```

不能：

```text
模型A + 模型B
```

就自动叫创新。

---

# 四十一、Git 必须贯穿整个过程

本次重构必须使用 Git 作为工程状态管理。

完整规则按照后面的 Git 专用提示词执行。

核心原则：

```text
不直接改 main
不 force push
不 reset --hard
不 clean -fd
不重写历史
不混入第三方仓库
不提交正式比赛私有数据
每阶段一个或多个可审查 commit
测试通过后再 commit
最终通过 PR 合并
```

---

# 四十二、过程汇报要求

执行长任务时，阶段性汇报即可。

不要每改一个文件汇报。

格式：

```text
T04 Modeling Contracts — PASS

完成：
- ...

新增：
- ...

验证：
- ...

发现问题：
- ...

下一步：
T05 Modeling Runner
```

如果已经发现重要 Bug，及时指出。

---

# 四十三、阻塞条件

只有以下情况可以真正阻塞：

```text
官方关键文件缺失且无法获取
仓库损坏
必须软件不存在且没有替代
用户本地未提交改动与目标修改发生不可安全合并冲突
许可证明确阻止实现方案
关键赛题事实无法确认
继续会制造虚假结果
```

普通设计选择不要反复问用户。

选择合理默认并记录。

---

# 四十四、最终必须交付

至少：

```text
docs/audit/current_repository_audit.md
docs/research/reference_source_map.md
docs/architecture_v2.md
docs/workflow_v2.md
docs/contracts.md
docs/migration_v1_to_v2.md

competition policy schema

modeling contracts
workflow guard
runner
run manifest
independent validator
model evidence gate
freeze/stale system

tests/
fixtures/
.github/workflows/

更新后的 AGENTS.md
更新后的 CLAUDE.md
更新后的 README
CHANGELOG
```

以及：

```text
历史赛题 E2E 验证报告
CI PASS
```

---

# 四十五、最终验收标准

只有全部满足才可以称：

```text
MathMode V2 READY
```

至少：

1. 当前仓库功能已真实阅读；
2. 参考项目真实代码已审计；
3. 引用思想有 source map；
4. 许可证边界明确；
5. 官方规则与经验规则分离；
6. 题目/附件有 hash manifest；
7. problem DAG 可机器验证；
8. ambiguity / assumption 可机器追踪；
9. Baseline/Main/Fallback 有明确 contract；
10. Risk Probe 可以真正运行；
11. Runner 不使用 `shell=True`；
12. Run Manifest 真实记录输入/代码/输出；
13. Independent Validator 与主算法解耦；
14. Evidence Gate 可以真正阻止错误结果；
15. Frozen Numbers 不可手改；
16. upstream change 可以让 downstream STALE；
17. Visual Plan 接入 Evidence lineage；
18. Writer 不能使用未冻结数字；
19. 当前比赛封面/匿名规则由 policy 驱动；
20. 45 页不再无依据作为官方硬限制；
21. AI 使用有结构化记录；
22. `.agents` / `.claude` 无行为漂移；
23. 有 unit tests；
24. 有 negative fixtures；
25. 有 E2E fixture；
26. 有 GitHub Actions；
27. 有历史赛题完整 dry-run；
28. 所有核心测试 PASS；
29. Git 工作区 clean；
30. PR 中能完整说明架构、迁移、验证和已知限制。

---

# 四十六、最高优先级原则

始终记住：

```text
聪明的模型选择
<
正确的问题定义
<
可靠的数据
<
真实运行
<
独立验证
<
可追溯证据
<
稳定的全流程
```

这个项目的目标不是：

> “让 AI 看起来像一个数学建模高手。”

而是：

> **让 AI 的每一个建模结论都尽可能能被代码、数据、数学、实验和独立验证重新证明。**

从现在开始按：

```text
T00 → T01 → T02 → ...
```

逐阶段执行。

**不要只给我一份方案然后停止。**

真实读取仓库、真实修改代码、真实运行测试、真实提交 Git。

每一步都必须在上一步验证通过后继续。
