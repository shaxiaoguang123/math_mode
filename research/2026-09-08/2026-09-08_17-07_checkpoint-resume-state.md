# MathModel Agent Research

## 1. 本轮研究主题

**赛时长时程 Agent 的 Memory / Checkpoint / Resume：从“聊天记忆”升级为可恢复、可验证、可分支的 workflow state。**

本轮集中回答一个前两轮尚未解决的工程问题：

> 华为杯连续数十小时运行时，如果发生上下文压缩、模型切换、进程崩溃、工具会话丢失、多 Agent 并行、求解路线回退，`math_mode` 如何恢复到“最后一个可信状态”，同时避免把过期结论、未验证实验和旧文件重新带回主线？

本轮深入研究 3 个高价值对象：

1. `langchain-ai/langgraph`：thread-scoped checkpoint、checkpoint lineage、pending writes、state history 与 durable execution；
2. `microsoft/agent-framework`：完整 workflow checkpoint、`graph_signature_hash` 兼容性校验、executor/edge/pending request 恢复、原子文件写入；
3. `OpenHands/software-agent-sdk`：持久化 ConversationState + append-only EventLog + active branch，以及 live session 丢失后的 transcript bootstrap resume。

本轮结论不是“给 Agent 加向量记忆”，而是：

> `math_mode` 应把 **事实、实验、工作流状态、对话上下文** 分开管理；恢复时以机器可读 checkpoint 和真实 artifact 为事实源，LLM 上下文只从可信状态重新构造。

建议的最小结构是：

```text
题面/数据/规范（不可变事实）
        ↓
Workflow State（当前阶段与任务）
        ↓
Last Known Good Checkpoint（可恢复快照）
        ↓
Append-only Event / Decision Log（完整过程）
        ↓
Result Index + Validation + Artifact Hash（结果事实）
        ↓
Resume Context（为新模型/新会话重建的短上下文）
```

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

已有三轮研究分别覆盖：

- 14:00：Evidence-first 科研工作流；
- 15:06：候选模型树搜索、实验账本、MCTS/UCT、执行环境；
- 16:04：Reviewer/Judge 的可执行验证、校准和 false-negative 防护。

因此本轮严格不重复以下结论：

- “结果必须真实运行”；
- “需要实验账本”；
- “需要 Reviewer”；
- “需要多模型比较”；
- “需要 SHA-256”。

本轮新增问题是：

1. 这些已有证据和实验状态在 48–72 小时长时程运行中如何保存和恢复？
2. checkpoint 到底应该保存什么，什么绝不能保存成“已确认事实”？
3. workflow 或代码结构变化后，旧 checkpoint 是否仍可恢复？
4. 多 Agent 并行时如何防止旧状态覆盖新状态？
5. 远程 sandbox / provider session 丢失后，如何在不依赖原聊天上下文的情况下继续？
6. 如何支持回退到旧模型路线，但不污染当前主线？
7. “长期 memory”与“比赛当前状态”应如何分离？

### 2.2 当前 math_mode 已有能力与明确缺口

本轮重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、当前 research 索引和最近两轮报告后确认：

当前 `math_mode` 已有较强的静态事实链：

```text
原始题目/数据
→ 求解代码
→ 结构化结果
→ 独立验证
→ 求解/结果索引.md
→ 论文
→ 支撑材料 + SHA-256
```

同时已经规划：

- `求解/题面约束清单.md`
- `求解/求解计划.md`
- `求解/AI使用记录.md`
- `求解/结果索引.md`
- 可选 `求解/决策记录.jsonl`

但代码搜索和目录检查没有发现统一的：

- machine-readable workflow state；
- last-good checkpoint；
- checkpoint parent lineage；
- pending task / pending message 恢复；
- resume compatibility guard；
- crash recovery protocol；
- branch / active head；
- stale checkpoint invalidation。

因此当前架构已经很擅长回答“最终证据在哪里”，但还不够擅长回答：

> **Agent 中断以后，下一次应该从哪里继续，而且怎样证明继续的位置仍然有效？**

## 3. 搜索范围与关键词

本轮轮换到 P2，但只研究对华为杯赛时直接有价值的状态基础设施：

- durable agent execution
- workflow checkpoint resume
- checkpoint lineage
- workflow state persistence
- crash recovery agent
- pending writes resume
- graph signature checkpoint compatibility
- event sourcing agent
- append-only event log
- conversation restore
- session lost resume
- state branching time travel
- checkpoint atomic write
- stale state prevention
- long-running multi-agent state

优先阅读：

- 官方 GitHub README；
- checkpoint/state 核心源码；
- restore 逻辑；
- event log；
- checkpoint compatibility；
- branch/head；
- crash/session-loss 恢复相关代码与测试线索。

未把普通聊天 memory、通用向量数据库、个人助理记忆项目纳入主研究对象。

## 4. 新发现项目

### 项目 1：LangGraph

- 名称：LangGraph
- Repository：https://github.com/langchain-ai/langgraph
- Stars：41,240（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T08:59:57Z`；`pushed_at=2026-09-06T00:55:48Z`
- 目标：面向 long-running、stateful Agent 的低层编排框架。
- 核心能力：durable execution、checkpoint persistence、interrupt/resume、state history、time travel、短期/长期 memory、subgraph state。
- 本轮实际阅读：README；`libs/checkpoint/langgraph/checkpoint/base/__init__.py`；checkpoint / pending-writes / migration / state-history 测试搜索结果。

对 `math_mode` 最重要的不是直接采用 LangGraph，而是它把 **thread state checkpoint** 与更广义长期 memory 分开，并将 `thread_id`、checkpoint history、pending writes 当作一等概念。

### 项目 2：Microsoft Agent Framework

- 名称：Microsoft Agent Framework
- Repository：https://github.com/microsoft/agent-framework
- Stars：13,385（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T09:03:22Z`；`pushed_at=2026-09-08T08:17:35Z`
- 目标：生产级 AI Agent 与 multi-agent workflow 的 Python/.NET 框架。
- 核心能力：graph workflow、checkpointing、restartability、time travel、HITL、并发/顺序/交接编排、observability。
- 本轮实际阅读：README；`_workflows/_checkpoint.py`；`_workflows/_runner.py`；checkpoint/resume sample 和 checkpoint compatibility 代码搜索结果。

它对 `math_mode` 最有价值的机制是：

> checkpoint 不只保存数据，还保存 **workflow identity**，恢复前必须确认 workflow topology 与 checkpoint 兼容。

### 项目 3：OpenHands Software Agent SDK

- 名称：OpenHands Software Agent SDK
- Repository：https://github.com/OpenHands/software-agent-sdk
- Stars：1,066（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T06:28:21Z`；`pushed_at=2026-09-08T04:23:47Z`
- 目标：构建真正操作代码、文件和工作空间的软件 Agent。
- 核心能力：ConversationState、persistent EventLog、workspace、execution status、skills state、agent state、branchable event history、remote/ephemeral workspace。
- 本轮实际阅读：README；`conversation/state.py`；`conversation/event_store.py`；`event/resume_transcript.py`。

它提供了一个非常适合数模赛时状态管理的组合：

```text
Base State / Current State
        +
Append-only Event History
        +
Active Branch HEAD
```

## 5. 深入架构分析

### 5.1 LangGraph：Checkpoint 与 Memory 不是同一个概念

LangGraph `BaseCheckpointSaver` 的源码说明：启用 checkpointer 后，workflow 通过 `thread_id` 保存和读取 state；没有 `thread_id`，就不能正确保存状态、从 interrupt 恢复或做 time-travel debugging。

`CheckpointTuple` 不只保存一个状态对象，还包含：

```text
config
checkpoint
metadata
parent_config
pending_writes
```

并提供：

```text
get_tuple()
list()
put()
put_writes()
delete_thread()
copy_thread()
```

这说明可恢复 workflow 至少需要三个不同层次：

1. **当前 committed state**；
2. **checkpoint lineage / history**；
3. **尚未进入下一稳定状态的 pending writes**。

对数学建模而言，这可以映射为：

```text
Committed:
  已经真实运行 + 已通过最低验证的模型结果

Pending:
  当前正在跑的候选 / 尚未验证的新参数 / 待复算结果

History:
  上一条可回退的可信状态
```

这比“每隔一段时间把聊天记录保存起来”可靠得多。

### 5.2 Microsoft Agent Framework：恢复前必须验证 workflow identity

`WorkflowCheckpoint` 源码保存：

```text
workflow_name
graph_signature_hash
checkpoint_id
previous_checkpoint_id
timestamp
messages
state
pending_request_info_events
iteration_count
metadata
version
```

其中最值得迁移的是 `graph_signature_hash`。

`Runner.restore_from_checkpoint()` 会先验证：

```text
当前 graph_signature_hash
== checkpoint.graph_signature_hash
```

不一致就拒绝恢复，并明确提示 workflow graph 已变化。

这是 `math_mode` 目前非常需要但尚未标准化的保护。赛时可能发生：

- 修改求解流程；
- 更换主模型；
- 修改数据切分；
- 更新 Skill/Prompt；
- 修改验证标准；
- 改写脚本入口。

如果仍无条件恢复旧 state，就会形成非常隐蔽的“新流程 + 旧状态”混合污染。

对 `math_mode`，建议不要只做一个 workflow hash，而是建立：

```text
resume_signature = hash(
  题面/附件关键输入,
  workflow schema version,
  当前求解计划,
  active agent/skill version,
  environment lock,
  validation contract version
)
```

变化后，不一定所有旧结果都报废，但必须进入 **partial rehydrate / selective invalidation**，而不是静默继续。

### 5.3 Microsoft Agent Framework：Checkpoint 应在稳定边界创建

其 runner 在创建 checkpoint 前会：

1. 保存 executor state；
2. 保存 edge runner state；
3. commit shared state；
4. 再生成 checkpoint。

并且 checkpoint 失败不会让整个 workflow 失败；下一次成功 checkpoint 仍以“最后一个成功 checkpoint”为 parent。

这对应一个重要原则：

> **Checkpoint 不是“当前内存 dump”，而是一个可恢复的一致性边界。**

对 `math_mode`，checkpoint 的合理时点不是每次 LLM 输出后，而应是：

- 题面与数据审计完成；
- 每问求解计划通过 plan gate；
- 某候选模型真实执行完成；
- 关键 validation hard gate 通过；
- 结果索引完成一次原子更新；
- 某问题章节证据链闭合；
- 论文全局门禁通过。

### 5.4 Microsoft Agent Framework：恢复时先清旧状态，防 stale key 泄漏

`restore_from_checkpoint()` 在 import checkpoint 前先 clear 当前 shared state，再恢复 executor/edge state 和 pending events。

这个细节非常重要：

> 恢复不是把旧状态 merge 到当前内存，而是让 checkpoint 成为该恢复分支的权威基线。

对数学建模最危险的错误之一正是：

```text
旧模型结果
+ 新模型参数
+ 新数据版本
+ 未清理的旧指标
= 看似完整、实际不一致的论文证据
```

因此未来 `math_mode` Resume Guard 应默认 **fail closed**：发现无法证明一致性的旧字段时，不把它自动合并成当前有效事实。

### 5.5 OpenHands：Snapshot + Append-only EventLog 比单一 state.json 更稳

OpenHands `ConversationState` 明确区分当前状态与持久化事件：

- 当前 execution status：`IDLE / RUNNING / PAUSED / WAITING_FOR_CONFIRMATION / FINISHED / ERROR / STUCK / DELETING`；
- agent、workspace、activated skills、agent-specific state；
- `leaf_event_id` / active HEAD；
- 独立 `EventLog` 保存每个事件。

`EventLog` 采用 append-only 设计：

- 每个 event 有独立 ID；
- 可以有 parent event；
- duplicate ID 被拒绝；
- parent 不存在时拒绝写入；
- 支持 `path_to_root(leaf)`；
- 写入带锁；
- 对事件长度使用 sidecar marker；
- marker 更新失败时宁可“没有 marker”，也不留下一个假装最新的 stale marker。

这对 `math_mode` 的直接启发是：

```text
current_state.json
  = 当前权威状态的快照

events.jsonl / 决策记录.jsonl
  = 只追加的过程事实
```

二者用途不同：

- snapshot 负责快速恢复；
- event log 负责解释“怎么走到这里”、并发防冲突、branch lineage、审计和必要时重建。

### 5.6 OpenHands：active branch 能避免失败路线继续污染主线

OpenHands 当前 state 使用 `leaf_event_id` 表示 conversation tree 的 HEAD，`active_branch()` 只返回从 HEAD 回到 root 的有效路径；被放弃的分支不会继续进入当前 view。

这与 15:06 的候选模型树研究形成了新的连接：

```text
模型路线 A ── A1 ── A2（失败）
       \
        B1 ── B2（验证通过） ← active HEAD
```

当前 `math_mode` 可以保留失败路线用于复盘，但论文和结果索引只应沿 **active validated branch** 读取证据。

这比简单覆盖文件更安全，因为覆盖会让“旧结果为什么消失”无法追溯。

### 5.7 OpenHands：live session 丢失时，Resume Context 只是恢复接口，不是真相源

`resume_transcript.py` 处理了一个很现实的问题：远程 sandbox 被回收后，provider 自己的 session 存储可能消失，此时无法按原 session ID 恢复。

其 fallback 是：

```text
durable SDK event history
→ 渲染为 resume transcript
→ 建立新 session
→ 把旧历史作为 background context
```

实现还会：

- 设置明确 resume marker；
- 避免重复包裹；
- 对过长历史截断；
- 总体截断优先保留尾部新事件；
- 保留工具输入/输出摘要。

关键方法学结论是：

> **新 LLM 会话可以丢，但结构化 state 和 event history 不能丢。**

`math_mode` 不应依赖“同一个聊天窗口一直活着”。当模型切换或上下文压缩时，应从 checkpoint + 结果索引 + 最近 event tail 重新生成 Resume Context。

## 6. Agent / Skill 设计

本轮不建议新增一个泛化的 `memory-agent`。更合理的是拆成三个窄职责组件。

### 6.1 `workflow-checkpoint-manager`

职责：

- 创建一致性 checkpoint；
- 保存 parent checkpoint；
- 标记 last known good；
- 原子写入；
- 记录 workflow/resume signature；
- 管理 checkpoint retention；
- 不参与模型选择和论文写作。

### 6.2 `resume-guard`

职责：恢复前硬检查：

```text
题面/附件 hash 是否一致？
数据版本是否一致？
workflow signature 是否一致？
当前代码/环境是否允许恢复？
Validation Contract 是否变化？
checkpoint 引用的 artifact 是否还存在且 hash 一致？
是否有更新 checkpoint 已经 supersede 当前 checkpoint？
```

输出必须是机器状态：

```text
RESUME_SAFE
PARTIAL_REHYDRATE
INVALIDATED
CONFLICT
```

而不是 LLM 的“看起来应该没问题”。

### 6.3 `context-rehydrator`

职责：

- 不保存事实；
- 只从可信 checkpoint、结果索引、题面硬约束、最近 event tail 重建 LLM 上下文；
- 可针对 Solver / Reviewer / Writer 生成不同最小上下文；
- 禁止从过期聊天摘要反向覆盖机器状态。

## 7. Workflow

建议的赛时恢复流程：

```text
Phase / Question 开始
      ↓
读取 current checkpoint
      ↓
Resume Guard
 ┌───────────────┬──────────────────┬──────────────┐
 SAFE            PARTIAL            INVALID/CONFLICT
 ↓               ↓                  ↓
恢复 committed   保留仍新鲜 artifact  回到最近可信 checkpoint
state            失效受影响字段       或重建阶段
      ↓
Context Rehydrator
      ↓
Agent 继续工作
      ↓
产生 pending state
      ↓
真实执行 / Validation
      ↓
commit state
      ↓
atomic checkpoint
      ↓
更新 current HEAD / result index
```

### 推荐 checkpoint 层级

```text
C0  题面/数据审计完成
C1  全局路线与每问计划完成
C2  问题一主要结果 + validation pass
C3  问题二主要结果 + validation pass
...
Cn  全部问题证据闭合
Cn+1 论文 evidence gate pass
Cn+2 最终 PDF / 支撑材料 gate pass
```

模型搜索内部可有更细粒度 candidate checkpoint，但不应全部升级成 global last-known-good。

## 8. Code Execution / Tools

### LangGraph

本轮确认的是 checkpoint/state 基础设施源码，不是其数学建模能力。

- 可保存 thread state；
- 支持 pending writes；
- 有 state history / migration / resume 测试路径；
- README 明确面向 durable execution 和 long-running stateful agents。

没有证据表明 LangGraph 本身会验证数学模型，因此不能把“可恢复”误认为“结果可靠”。

### Microsoft Agent Framework

本轮代码级确认：

- workflow runner 创建 checkpoint；
- checkpoint 保存 executor 和 edge state；
- pending request-info event 可被恢复；
- checkpoint graph signature 不兼容时拒绝恢复；
- FileCheckpointStorage 使用临时文件 + `os.replace()` 原子替换；
- checkpoint 可形成 parent chain。

没有在本轮运行其样例，因此这里只声称源码级确认，不声称本环境完成实测。

### OpenHands SDK

本轮代码级确认：

- persistent event log；
- workspace + conversation execution state；
- agent state；
- active event branch；
- resume transcript fallback；
- 可在 local 或 ephemeral workspace 中工作。

本轮没有启动 OpenHands Agent Server，不将源码存在等同于运行验证。

## 9. QA / Reviewer / Verification

本轮状态研究带来的一个关键约束是：

> **只有通过最低验证的结果才能进入 committed checkpoint。**

因此 checkpoint 本身需要 QA：

### Checkpoint Integrity Gate

至少检查：

```text
checkpoint schema valid
parent exists
artifact paths exist
artifact hashes match
input/data hashes match
workflow signature match
validation status not stale
result index hash match
no unresolved hard conflict
```

### Resume QA

恢复后不能立即继续写论文，应执行最小 smoke validation：

- 加载关键结果 JSON/CSV；
- 对 1–2 个关键数值重新计算；
- 确认执行环境可用；
- 确认 active model route 与结果索引一致；
- 确认当前论文引用的 figure/table 仍指向 valid artifact。

### Checkpoint 自身不能替代 Reviewer

一个 checkpoint 可以“完整恢复一个错误状态”。所以本轮结论与 16:04 Reviewer 研究必须串联：

```text
Execution
→ Validation Contract
→ Commit
→ Checkpoint
```

而不是：

```text
Execution
→ Checkpoint
→ 默认认为正确
```

## 10. 值得借鉴的设计

### A. 可以直接借鉴

1. **Graph / Workflow Signature Guard**：恢复前校验 workflow identity。
2. **Parent Checkpoint Lineage**：不要只保留一个 mutable state 文件。
3. **Last Known Good**：checkpoint 创建失败时不污染上一个有效 checkpoint。
4. **Atomic Snapshot Write**：临时文件写完后原子替换。
5. **Snapshot + Append-only Log**：当前状态和过程历史分开。
6. **Explicit Execution Status**：RUNNING / PAUSED / ERROR / STUCK / FINISHED 等。
7. **Active HEAD**：失败探索路线可以保留，但不再作为当前证据分支。

### B. 可以改造后采用

1. LangGraph 的 `thread_id`：改造为 `competition_run_id + question_id + branch_id`。
2. LangGraph 的 long-term store：只用于跨问题共享的**已验证全局事实**，不能成为未经审核的“经验真相库”。
3. OpenHands event tree：只在候选模型/路线明显需要分支时启用，不把所有普通步骤都树化。
4. Microsoft workflow checkpoint：保留思想，但不需要为了 checkpoint 整体迁移到 MAF。

### C. 可以作为对照实验

1. `snapshot-only` vs `snapshot + append-only event log`。
2. `完整聊天恢复` vs `结构化 checkpoint + recent event tail`。
3. 每步 checkpoint vs 仅稳定 barrier checkpoint。
4. 无 signature guard vs 有 signature guard。
5. crash 后重新执行全部 vs 从 last-known-good 恢复。

### D. 不建议采用

1. 把向量 memory 当作赛题事实源。
2. 每个 LLM token / 每条自然语言都做全量 checkpoint。
3. 未验证候选自动写进 canonical state。
4. workflow 已变仍静默恢复旧 checkpoint。
5. 初期就引入复杂分布式数据库和跨机器一致性协议。
6. 将不透明 pickle blob 作为唯一可审计状态格式。

## 11. 存在的问题

### LangGraph

- 通用框架能力很强，但对数学建模的 artifact hash、验证门禁、题面约束没有内建语义；
- 如果直接引入，可能增加依赖和调试复杂度；
- checkpoint 数量长期增长需要 retention 策略。

### Microsoft Agent Framework

- 生产级抽象较重；
- 完整迁移会让 `math_mode` 从“竞赛工程”变成“框架工程”，收益不一定抵消复杂度；
- 文件 checkpoint 内部允许复杂对象编码，`math_mode` 更适合优先保留可读 JSON/JSONL + artifact path/hash。

### OpenHands SDK

- event tree / workspace / agent server 设计主要服务软件开发 Agent；
- 分支事件模型很强，但如果所有数模动作都用事件树会过度工程化；
- transcript resume 是 provider session 丢失的 fallback，不应替代正式结构化 state restore。

### 对所有方案的共同限制

状态恢复只保证“继续运行”，并不保证：

- 数学模型正确；
- 数值结果正确；
- 数据切分合理；
- 论文结论没有过度解释。

因此 Checkpoint 必须位于现有 Evidence / Validation 体系之后或与之绑定。

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 题面/数据事实源 | 很强，原始文件只读、题面约束优先 | 三项目均为通用 Agent 状态 | **保持 math-mode** |
| 结果证据 | 已有结果索引、独立验证、支撑材料、SHA | 通用框架通常不懂数模证据 | **保持 math-mode** |
| Workflow state | 主要是文档型 Phase/计划 | LangGraph/MAF 有 machine state | **新增** |
| Checkpoint | 当前无统一协议 | LangGraph/MAF 为一等能力 | **新增** |
| Checkpoint lineage | 无标准 parent chain | MAF `previous_checkpoint_id`；LangGraph history | **新增** |
| Restore compatibility | 无统一 hash/signature guard | MAF `graph_signature_hash` | **P0 新增** |
| Pending work | 无统一 machine-readable pending state | LangGraph pending writes；MAF pending requests/messages | **新增** |
| Event history | 可有 `决策记录.jsonl`，但非统一 runtime event schema | OpenHands 持久化 EventLog | **改进** |
| 分支/回退 | 模型候选研究已提出树，但正式 state 未连接 | OpenHands active HEAD；LangGraph time travel | **P1 实验** |
| Crash recovery | 规范强调失败处理，但无通用 resume protocol | 三项目均有恢复思想 | **新增** |
| 对话上下文恢复 | 当前依赖 Agent/平台上下文较多 | OpenHands 可从 durable history bootstrap 新 session | **改进** |
| Memory 分层 | AI 使用记录/决策/结果有不同文件，但未形成状态模型 | LangGraph 明确 thread state vs long-term memory | **新增契约，不必换框架** |
| QA/验证 | 当前很强 | checkpoint 框架本身通常不验证数学正确性 | **保持并绑定 checkpoint** |

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：定义 `Workflow Checkpoint Contract`

建议先只形成设计，不立即改正式代码；未来机器可读字段至少包括：

```json
{
  "schema_version": "1.0",
  "checkpoint_id": "...",
  "parent_checkpoint_id": "...",
  "created_at": "...",
  "competition_run_id": "...",
  "phase": "solve_q2",
  "question_id": "Q2",
  "status": "last_known_good",
  "resume_signature": "...",
  "input_hashes": {},
  "environment_hash": "...",
  "workflow_hash": "...",
  "validation_contract_hash": "...",
  "active_route": "...",
  "committed_artifacts": [],
  "pending_tasks": [],
  "result_index_hash": "...",
  "event_log_offset": 0,
  "resume_note": "..."
}
```

重点不在字段名字，而在三条不变量：

1. canonical checkpoint 只能引用已提交/已验证 artifact；
2. checkpoint 必须可证明自己对应哪个输入和哪个 workflow；
3. checkpoint 必须知道自己的 parent 和是否已被新状态 supersede。

#### P0-2：增加 Resume Guard

恢复前强制比较：

```text
input/data hash
workflow signature
validation contract version
active code/environment identity
artifact hash
latest checkpoint lineage
```

任何关键 mismatch 默认禁止“无提示继续”。

#### P0-3：把 `决策记录.jsonl` 升级为 append-only event schema

当前 `CLAUDE.md` 已允许重要决策写 `求解/决策记录.jsonl`。建议未来不要另造多份聊天日志，而是统一事件类型，例如：

```text
PLAN_CREATED
MODEL_CANDIDATE_CREATED
CODE_EXECUTED
VALIDATION_PASSED
VALIDATION_FAILED
ROUTE_SWITCHED
ARTIFACT_COMMITTED
CHECKPOINT_CREATED
CHECKPOINT_INVALIDATED
RESUME_STARTED
RESUME_COMPLETED
```

每条带：timestamp、actor、question、branch、artifact refs、hash、parent event。

### P1：值得实验

#### P1-1：故障注入测试

在往届赛题复现中主动：

- kill Python 进程；
- 清空 LLM conversation context；
- 切换模型；
- 修改一份数据文件；
- 修改 workflow 版本；
- 删除一个结果 artifact；
- 让两个 Agent 同时尝试更新同一 question state。

检查系统是否能正确表现为：

```text
正常 crash → 从 last good 恢复
输入变化 → checkpoint invalid
workflow 变化 → partial rehydrate / rebuild
artifact 丢失 → hard fail
并发旧写 → stale write 被拒绝
```

#### P1-2：结构化 Resume Context

做对照：

```text
A: 把历史聊天全文/摘要继续喂给模型
B: 题面硬约束 + checkpoint + 结果索引 + 最近 event tail
```

评价：恢复后约束遗漏率、重复实验率、旧结论污染率、token 成本和继续求解正确率。

#### P1-3：Candidate Branch HEAD

把 15:06 候选树与本轮 active HEAD 连接：

- 每个模型分支有自己的 parent；
- failed branch 保留；
- active branch 才能更新主结果索引；
- Reviewer/Validation 通过后才能 promote branch。

### P2：长期考虑

当未来真的出现多进程/多机器 Agent 同时求解时，再评估：

- SQLite / Postgres checkpoint backend；
- compare-and-swap / optimistic concurrency；
- branch merge；
- checkpoint retention/compaction；
- workflow migration schema。

当前赛时单机环境优先使用：

> **可读 JSON snapshot + JSONL event log + 原子写 + hash guard。**

### 不建议采用

- 不建议为了 checkpoint 全面迁移到 LangGraph / MAF / OpenHands；
- 不建议把“长期 memory”作为自动注入的真相库；
- 不建议让 LLM 自己决定旧 checkpoint 是否兼容；
- 不建议每次恢复都全文 replay 历史聊天；
- 不建议 checkpoint 未验证中间结果后直接让 Writer 使用。

## 14. 可形成的新 Skill / Agent

只提出设计建议，不在本轮创建：

### `workflow-checkpoint-manager`

输入：当前 workflow state、artifact manifest、validation status。
输出：一致性 checkpoint、parent lineage、last-good pointer。

### `resume-guard`

输入：checkpoint + 当前输入/代码/环境/workflow signature。
输出：`SAFE / PARTIAL / INVALIDATED / CONFLICT` 与具体失效范围。

### `context-rehydrator`

输入：可信 checkpoint + 题面约束 + 结果索引 + recent events。
输出：面向 Solver/Reviewer/Writer 的最小 resume context。

### `stale-state-auditor`

检查：旧模型指标、过期图表、旧 data hash、被 supersede 的结论是否仍被结果索引或论文引用。

## 15. 与历史调研的去重检查

本轮去重结果：

- **没有重复** 14:00 的“需要 evidence-first”结论；本轮关注 evidence 如何跨中断保持状态连续性。
- **没有重复** 15:06 的“候选树 / 实验账本 / MCTS”结论；本轮新增的是 candidate branch 如何成为可恢复 state、如何选择 active HEAD、如何防 stale branch 污染。
- **没有重复** 16:04 的 Reviewer/Judge 结构；本轮只规定 validation pass 与 checkpoint commit 的接口关系。

本轮新增认知可归纳为：

1. checkpoint ≠ chat memory；
2. restore 必须验证 workflow/input compatibility；
3. snapshot 与 append-only event history 应分离；
4. canonical state 与 pending state 应分离；
5. active branch / last-known-good 是防旧结果污染的核心结构；
6. LLM session 丢失时，应从结构化事实重建上下文，而不是依赖原会话继续存在。

此前 research 索引中没有针对这六点的独立调研记录，因此本轮具有明确新增性。

## 16. 下一轮推荐方向

建议下一轮轮换到：

**多 Agent 并行 artifact ownership / stale-write prevention / conflict-free merge。**

重点问题：

- 两个 Solver 同时更新同一问题时谁拥有写权限？
- Reviewer 读取时如何锁定对应 artifact 版本？
- Writer 如何避免引用刚刚被新实验 supersede 的结果？
- optimistic concurrency / compare-and-swap 是否适合赛时？
- 多 Agent 共享 `结果索引` 时如何防止最后写入者覆盖更可信版本？
- candidate branch 应在什么条件下 merge/promote 到 canonical branch？

这会自然承接本轮 checkpoint/state，但研究对象将从“单 workflow 恢复”转向“多 Agent 并发一致性”，避免重复。

## 17. Sources

### 已阅读官方 README / 源码

1. LangGraph Repository  
   https://github.com/langchain-ai/langgraph

2. LangGraph README  
   https://github.com/langchain-ai/langgraph/blob/main/README.md

3. LangGraph Checkpoint Base：`CheckpointTuple` / `BaseCheckpointSaver`  
   https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py

4. Microsoft Agent Framework Repository  
   https://github.com/microsoft/agent-framework

5. Microsoft Agent Framework README  
   https://github.com/microsoft/agent-framework/blob/main/README.md

6. Microsoft Agent Framework `WorkflowCheckpoint` / storage implementation  
   https://github.com/microsoft/agent-framework/blob/main/python/packages/core/agent_framework/_workflows/_checkpoint.py

7. Microsoft Agent Framework Runner checkpoint / restore  
   https://github.com/microsoft/agent-framework/blob/main/python/packages/core/agent_framework/_workflows/_runner.py

8. Microsoft Agent Framework checkpoint/resume samples  
   https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/checkpoint

9. OpenHands Software Agent SDK Repository  
   https://github.com/OpenHands/software-agent-sdk

10. OpenHands SDK README  
    https://github.com/OpenHands/software-agent-sdk/blob/main/README.md

11. OpenHands `ConversationState`  
    https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/state.py

12. OpenHands persistent `EventLog`  
    https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/event_store.py

13. OpenHands resume transcript fallback  
    https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/event/resume_transcript.py

### 当前 math_mode 基线

14. `math_mode/README.md`  
    https://github.com/shaxiaoguang123/math_mode/blob/main/README.md

15. `math_mode/AGENTS.md`  
    https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md

16. `math_mode/CLAUDE.md`  
    https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md

17. `research/INDEX.md`  
    https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md

18. 上一轮 Reviewer/Judge 调研  
    https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_16-04_reviewer-judge-calibration.md

19. 上两轮 Model Selection 调研  
    https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_15-06_model-selection-tree-search.md

### 阅读边界声明

- 本轮对三个外部项目均读取了官方 README 和关键源码，不是只依赖搜索摘要。
- 本轮没有在本地安装并运行 LangGraph、Microsoft Agent Framework 或 OpenHands；因此所有“确认”均限定为源码/官方文档层面的实现确认，不声称完成运行时 benchmark。
- 没有把 stars、README 宣传语或通用 memory 能力当作数学建模效果证据。
