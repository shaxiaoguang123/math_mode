# MathModel Agent Research

## 1. 本轮研究主题

**多 Agent 并行求解中的 Artifact Ownership、Stale-write Prevention 与 Canonical Promotion：从“共享目录直接写”升级为“隔离候选 → 版本化证据 → 验证后安全晋级”。**

本轮集中回答上一轮 checkpoint/resume 之后仍未解决的并发一致性问题：

> 当多个 Solver、Reviewer、Visualizer、Writer 同时推进同一道赛题时，如何保证每个 Agent 只修改自己拥有的候选产物，Reviewer 始终检查正确版本，旧 Agent 不会用过期结果覆盖新证据，并且只有通过验证的候选能够进入 `求解/结果索引.md`、论文和官方提交文件？

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的高价值对象：

1. `treeverse/dvc`：实验临时工作区、baseline-bound experiment refs、读写锁、diverged ref 拒绝覆盖；
2. `mlflow/mlflow`：不可变模型版本、source run lineage、`candidate` / `champion` alias、validation tags、显式 promotion；
3. `dagster-io/dagster`：DataVersion / DataProvenance、staleness、blocking asset checks、下游消费门禁。

本轮核心结论是：

> `math_mode` 不应让多个 Agent 直接争写同一份“最新结果”。更安全的最小架构是 **immutable candidate artifacts + versioned provenance + blocking validation gate + compare-before-promote canonical pointer**。计算可以高度并行，但“晋级为正式事实”必须是一个很小、可验证、拒绝 stale writer 的临界区。

建议的目标结构：

```text
题面 / 原始数据 / 规范（只读事实）
                ↓ baseline_signature
┌───────────────────────────────────────┐
│ Candidate Workspace Layer             │
│ q1/candidate-A/  q1/candidate-B/ ...  │
│ code / result / figure / validation   │
└───────────────────────────────────────┘
        ↓               ↓
  Hard Validation    Reviewer
        └───────┬───────┘
                ↓
        Promotion Gate
 expected_canonical_version == current ?
 artifact fresh ? hard gate PASS ?
                ↓
       Canonical Manifest / Pointer
                ↓
结果索引 → 视觉计划 → 支撑材料 → 论文 → 官方输出
```

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

当前索引中已有四轮：

- 14:00：Evidence-first 科研工作流；
- 15:06：候选模型树、并行实验和可执行评测环境；
- 16:04：Reviewer / Judge 的可执行、可校准验证；
- 17:07：长时程 Memory / Checkpoint / Resume 与 workflow state。

上一轮已经提出 checkpoint、active HEAD、last-known-good 和 stale checkpoint invalidation，但重点是**中断后如何恢复**。本轮不再重复 durable state，而专门研究：

1. 多个候选同时运行时，文件所有权如何隔离；
2. 多个 Reviewer / Solver 完成顺序不同，如何防止 last-writer-wins；
3. 某候选基于旧输入、旧代码、旧 canonical 结果运行完成后，如何识别为 stale；
4. “候选产物”与“正式可被论文消费的 canonical 产物”如何分层；
5. promotion 怎样做到显式、可审计，并在基线已变化时拒绝旧 Agent 晋级；
6. 哪些锁需要持有，哪些计算绝不能放在全局锁内。

### 2.2 当前 math_mode 已有什么，缺什么

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md` 和 `华为杯_求解规范/华为杯_求解规范.md` 后确认，当前项目已经有非常明确的事实链：

```text
原始题目/数据
→ 求解代码
→ 结构化结果
→ 独立验证
→ 求解/结果索引.md
→ 论文
→ 支撑材料 + SHA-256
```

已有重要规则包括：

- 原始题目和原始数据只读；
- 每问有唯一主入口脚本；
- `求解/`、`数据/` 是事实源；
- `求解/结果索引.md` 是论文数字、参数、图、表的主索引；
- `提交附件/支撑材料/` 必须从清单重建，不允许在快照里单独手改；
- 支撑材料与正式图表已经有审计和 SHA-256；
- 当前项目级完整 Skill 主要是 `academic-figure-skill`，尚未形成正式的并行 Solver/Reviewer artifact 协调层。

但是，本轮仓库搜索没有发现统一的：

- candidate artifact namespace；
- artifact owner / writer identity；
- immutable candidate manifest；
- canonical machine-readable pointer；
- candidate → canonical promotion protocol；
- expected-parent / compare-and-swap guard；
- stale artifact status；
- writer lease / critical-section policy。

因此当前系统已经擅长回答“最终结果应该如何审计”，但如果未来真正加入多 Agent 并行，就仍然可能遇到：

```text
Solver-A 基于 v3 数据开始运行
      ↓
Solver-B 基于 v4 数据更快完成并通过验证
      ↓
B 写入结果索引
      ↓
A 晚到完成
      ↓
A 再次覆盖同一路径
      ↓
论文读取了旧 v3 结果
```

这类问题不是 Reviewer 能单独解决的，而是 artifact lifecycle / ownership 问题。

## 3. 搜索范围与关键词

本轮轮换到 P2 底层能力，但只研究与数模赛时并行求解直接相关的机制：

- multi-agent artifact ownership
- isolated experiment workspace
- experiment refs baseline
- stale write prevention
- optimistic concurrency
- compare before promote
- canonical artifact pointer
- candidate champion alias
- immutable model version
- model registry promotion
- data version provenance
- stale asset detection
- blocking asset checks
- read write lock experiments
- diverged ref protection
- artifact lineage

优先阅读：

- GitHub 官方仓库与 README；
- 实验 executor / ref / lock 源码；
- registry version / alias / tag 官方文档；
- data version / provenance / stale status 源码；
- blocking check 源码。

没有把普通 Git 教程、团队协作 SaaS、通用文件锁库作为主要研究对象。

## 4. 新发现项目

### 项目 1：DVC

- 名称：DVC（Data Version Control）
- Repository：https://github.com/treeverse/dvc
- Stars：15,865（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T04:36:05Z`；`pushed_at=2026-09-07T18:54:56Z`
- 目标：数据/模型版本管理、可复现实验、pipeline 和本地实验追踪。
- 核心能力：experiment refs、临时独立 workspace、实验队列、参数/指标比较、apply、数据缓存与可复现 pipeline。
- 本轮实际阅读：`README.rst`、`dvc/repo/experiments/executor/local.py`、`refs.py`、`utils.py`、`apply.py`。

与 `math_mode` 最相关的不是 DVC 的存储后端，而是其**候选实验与主 workspace 分离**的设计。

### 项目 2：MLflow

- 名称：MLflow
- Repository：https://github.com/mlflow/mlflow
- Stars：27,856（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T09:49:44Z`；`pushed_at=2026-09-08T06:31:40Z`
- 目标：Agent / LLM / ML 模型的实验、评估、注册、管理和生命周期平台。
- 核心能力：Run lineage、model version、registry、alias、tag、跨环境 promotion。
- 本轮实际阅读：Model Registry 官方仓库文档 `docs/docs/classic-ml/model-registry/workflow.mdx`，并检索 alias/store 实现。

对 `math_mode` 最有价值的是把**版本实体**和**可移动的人类可读别名**分开：候选版本不被覆盖，`champion` 只是指向某个已存在版本的可移动 pointer。

### 项目 3：Dagster

- 名称：Dagster
- Repository：https://github.com/dagster-io/dagster
- Stars：16,125（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T09:15:39Z`；`pushed_at=2026-09-08T07:03:18Z`
- 目标：以 data assets 为中心的 pipeline orchestration、lineage、observability 与测试。
- 核心能力：DataVersion、DataProvenance、asset graph、asset checks、blocking gate、staleness、automation conditions、concurrency pools。
- 本轮实际阅读：README、`_core/definitions/data_version.py`、`_core/definitions/decorators/asset_check_decorator.py` 以及相关执行代码搜索结果。

它对 `math_mode` 最有价值的是回答：

> “某个结果虽然文件还在，但它是否仍然是当前代码与当前输入产生的 fresh result？”

## 5. 深入架构分析

### 5.1 DVC：并行实验不应该直接运行在 canonical workspace

DVC `TempDirExecutor` 会为实验建立临时目录，在该目录中初始化独立 Git 环境，再注入：

```text
EXEC_HEAD      当前实验基线
EXEC_MERGE     待复现实验改动
EXEC_BASELINE  baseline
```

随后在独立目录 checkout / apply，而不是让所有实验同时修改主 workspace。

这给 `math_mode` 一个很直接的映射：

```text
错误：
Solver-A ─┐
Solver-B ─┼→ 求解/问题一/结果/latest.csv
Solver-C ─┘

建议：
Solver-A → 求解/.candidates/q1/A/...
Solver-B → 求解/.candidates/q1/B/...
Solver-C → 求解/.candidates/q1/C/...
                         ↓
                    Promotion Gate
                         ↓
                    canonical pointer
```

候选可以并行、失败、被淘汰，但正式结果目录不应该是它们的直接写入目标。

### 5.2 DVC：候选身份绑定 baseline，而不是只靠文件名

`ExpRefInfo` 将 experiment ref 放到：

```text
refs/exps/<baseline_sha>/<experiment_name>
```

也就是说，实验身份天然包含 baseline。

对数模 Agent，应避免只有：

```text
q1_xgboost_v2
```

而应至少绑定：

```text
candidate_id
question_id
baseline_id
input_hashes
code_hash
validation_contract_hash
```

这样 Reviewer 才能判断：这个“看起来指标很好”的候选究竟是基于哪一版数据、哪一版代码和哪套验证标准运行的。

### 5.3 DVC：锁用于 ref 更新，而不是把整个实验串行化

DVC experiments 使用 `get_exp_rwlock()` 对实验 ref 的 reads / writes 做读写锁。`push_refspec()` 默认 `force=False`，如果远端 ref 已发生 divergence，会显式抛错，而不是静默覆盖。

这里最值得借鉴的原则是：

> **长时间计算不应持有全局 canonical 锁；锁只包住真正需要一致性的短写操作。**

如果 `math_mode` 为了避免冲突而让所有 Solver 从开始训练到生成图表一直持有一个全局锁，多 Agent 就失去了并行意义。更合理的是：

1. 各 Agent 在独立 candidate workspace 自由计算；
2. Reviewer 在 candidate 上只读；
3. 只有 promotion 时读取当前 canonical version、执行 freshness/hard gate、写新 pointer；
4. promotion 临界区结束后立即释放。

### 5.4 MLflow：候选版本和 `champion` pointer 是两个概念

MLflow Model Registry 每次注册可以生成新的 Model Version；version 记录 source run 等 lineage。官方 workflow 同时提供：

```python
client.set_registered_model_alias("example-model", "champion", 1)
client.set_registered_model_alias("example-model", "Champion", 2)
client.get_model_version_by_alias(...)
```

并允许版本 tag：

```text
validation_status = approved
```

这形成一个重要的生命周期分离：

```text
immutable-ish versions:
 v1, v2, v3, v4 ...

mutable pointer:
 champion → v3
```

对 `math_mode`，可映射为：

```text
Candidate Artifact Version
    candidate-A
    candidate-B
    candidate-C

Canonical Pointer
    q1.current → candidate-B
```

Writer、Visualizer、支撑材料构建器不应该寻找“最新修改时间最大的文件”，而应解析 canonical pointer，再读取它明确绑定的 immutable artifact hashes。

### 5.5 MLflow：promotion 应是显式动作，而不是复制文件即生效

MLflow 文档把 `candidate` alias 的版本 copy/promote 到 production model 作为显式生命周期动作。

这一点非常适合华为杯：

```text
生成候选 ≠ 正式结果
Reviewer 给高分 ≠ 正式结果
文件存在 ≠ 正式结果

只有：
Candidate
  + hard gate PASS
  + evidence complete
  + freshness PASS
  + promotion transaction success
= Canonical Result
```

但本轮没有在 MLflow alias API 中找到“基于 expected old alias 的 compare-and-swap”保证，因此不能直接声称 MLflow 已解决两个 Reviewer 同时移动 alias 的 race condition。

对 `math_mode` 的改造应更严格：

```text
promote(candidate_id,
        expected_canonical_version=17)

若当前 canonical_version 已经变成 18：
    REJECT_STALE_PROMOTION
```

也就是说，本轮借鉴 MLflow 的“version + alias”，但要额外加入 optimistic concurrency guard。

### 5.6 Dagster：文件未改变路径，不代表结果仍然 fresh

Dagster `DataProvenance` 源码明确记录：

```text
code_version
input_data_versions
input_storage_ids
is_user_provided
```

其 `compute_logical_data_version()` 会把 `code_version` 与排序后的 input data versions 一起计算 SHA-256，且定义：

```text
MISSING
STALE
FRESH
```

这对数学建模尤其重要，因为最危险的并不是“结果文件丢了”，而是：

```text
results.csv 还在
但数据已经更新
或代码已经修改
或验证协议已经改变
```

因此建议 `math_mode` 的 artifact fingerprint 不只做文件 SHA，而至少是：

```text
artifact_fingerprint = H(
  code_hash,
  input_hashes,
  params_hash,
  environment_hash,
  validation_contract_hash
)
```

如果任一依赖变化，则原 canonical artifact 即使物理文件还存在，也必须进入 `STALE`。

### 5.7 Dagster：验证应该是 downstream 的 blocking dependency

Dagster 的 `@asset_check(..., blocking=True)` 定义说明：下游会等待 check 完成；如果 check 以 `ERROR` severity 失败，下游不会执行。

这比“Reviewer 写一段建议，但 Writer 仍继续写论文”更适合 `math_mode`。

可以映射为：

```text
Candidate Result
     ↓
[unit/dimension check]
[constraint check]
[independent recompute]
[data leakage check]
[official schema check]
[freshness check]
     ↓ all hard checks PASS
Canonical Promotion
     ↓
Figure / Paper / Submission
```

Reviewer 可以补充软判断，但正式论文消费必须依赖 hard blocking gate。

## 6. Agent / Skill 设计

本轮不建议创建大量 Agent，而建议把“所有权”和“晋级权”拆开。

### 6.1 Solver / Model Search Agent

权限：

- 可以创建自己的 candidate workspace；
- 可以写自己的 code/result/figure/log；
- 不允许直接写 canonical manifest；
- 不允许直接修改 `求解/结果索引.md` 中已晋级事实。

最小输出：`candidate_manifest.json`。

建议字段：

```json
{
  "candidate_id": "q1-20260908-1804-a7f3",
  "question_id": "q1",
  "agent_id": "solver-2",
  "baseline_id": "...",
  "base_canonical_version": 17,
  "input_hashes": {},
  "code_hash": "...",
  "params_hash": "...",
  "environment_hash": "...",
  "validation_contract_hash": "...",
  "artifact_hashes": {},
  "metrics": {},
  "hard_gate_status": "PENDING",
  "reviewer_status": "PENDING",
  "immutable": true
}
```

### 6.2 Validation / Reviewer Agent

权限：

- candidate artifact 只读；
- 输出 validation report；
- 可以建议 `PROMOTE / REJECT / NEEDS_EVIDENCE`；
- 不直接覆盖 candidate 计算结果；
- 不独立移动 canonical pointer。

这样可避免 Reviewer 一边检查一边“顺手修结果”导致证据失真。

### 6.3 Artifact Promotion Manager

这不是“更聪明的 LLM”，而应尽可能是确定性小模块。

职责：

1. 读取 candidate manifest；
2. 重新计算关键 hash；
3. 验证 hard gate；
4. 检查 `expected_canonical_version`；
5. 若 canonical 已变化，拒绝 stale promotion；
6. 原子更新 canonical pointer；
7. 追加 promotion event；
8. 再生成人类可读结果索引投影。

### 6.4 Writer / Visualization Agent

只允许消费 canonical snapshot：

```text
canonical_version + candidate_id + artifact hashes
```

不要允许 Writer 直接扫描 `.candidates/` 寻找“最好的”或“最新的”文件。

## 7. Workflow

建议赛时 workflow：

```text
Phase A：冻结本轮 baseline
input_hash + code/workflow version + validation contract
                 ↓
Phase B：并行候选
Solver-A → candidate-A
Solver-B → candidate-B
Solver-C → candidate-C
                 ↓
Phase C：独立验证
Hard Check + Reviewer + repeat/recompute
                 ↓
Phase D：Promotion proposal
candidate-B requests promotion
expected canonical version = N
                 ↓
Phase E：Promotion critical section
read current canonical version
        ├─ != N → reject stale proposal
        └─ == N → recheck hashes/gates → write N+1
                 ↓
Phase F：Canonical consumers
结果索引 / Figure Plan / 支撑材料 / 论文
```

### 7.1 candidate 失败时

失败候选保留：

- code；
- logs；
- failure reason；
- metrics（如果有效）；
- provenance。

但不进入 canonical。

这与上一轮 append-only event/history 兼容：失败分支对审计有价值，但不应该污染当前事实头。

### 7.2 canonical 已前进时

旧 candidate 不一定要删除，而应标记：

```text
STALE_BY_CANONICAL_ADVANCE
```

根据变更类型决定：

- 如果 canonical 前进只改变论文措辞，候选可能仍可复核；
- 如果输入、代码、约束或验证 contract 变化，则必须重跑或至少重新验证；
- 不允许直接“强制晋级”。

## 8. Code Execution / Tools

### 8.1 DVC

DVC 是真实代码执行/实验工具，不只是 metadata registry。

本轮源码确认：

- `TempDirExecutor` 使用独立临时目录；
- 实验有 `EXEC_HEAD / EXEC_BASELINE / EXEC_MERGE`；
- 使用 read/write lock；
- experiment ref 与 baseline SHA 绑定；
- divergence 可被显式拒绝。

因此其 candidate isolation 设计可直接作为参考。

### 8.2 MLflow

MLflow 重点不是 sandbox，而是：

- tracking run；
- model artifact；
- immutable version identity；
- registry alias/tag；
- lineage / promotion。

对于 `math_mode`，它更适合参考“产物生命周期协议”，而不是拿来执行数学建模代码。

### 8.3 Dagster

Dagster 真正运行 Python asset / check，并维护：

- asset dependency；
- data version；
- provenance；
- asset check；
- blocking downstream；
- concurrency pool。

对 `math_mode`，更值得借用其 asset-version/check 思想，不建议整套引入。

## 9. QA / Reviewer / Verification

本轮把 QA 进一步分成两类：

### 9.1 Candidate correctness

回答：

- 数值是否正确？
- 约束是否满足？
- 单位/量纲是否正确？
- 是否泄漏？
- 独立复算是否一致？
- 结果是否稳定？

这延续 16:04 Reviewer/Judge 研究。

### 9.2 Candidate identity / freshness

回答：

- Reviewer 检查的是哪个 candidate？
- candidate 的 input/code/params/env 是哪一版？
- figure 是否来自同一 candidate？
- Writer 引用的结果是否仍是 canonical？
- canonical 是否在 Reviewer 检查后被别人更新？
- promotion 时 base canonical 是否仍然一致？

第二类正是本轮新增。

建议所有 hard validation report 都绑定：

```text
candidate_id
artifact_fingerprint
validation_contract_hash
reviewer_version
validated_at
```

这样即使报告内容是 PASS，只要 candidate hash 变化，旧 PASS 自动失效。

## 10. 值得借鉴的设计

### A. 可以直接借鉴

1. **DVC：candidate workspace 隔离**——不同 Solver 不直接争写主目录。
2. **DVC：baseline-bound candidate identity**——候选必须知道自己基于哪个基线。
3. **Dagster：DataVersion / DataProvenance**——结果版本由代码版本和输入版本共同决定。
4. **Dagster：blocking check**——验证失败时阻止论文/提交等 downstream 消费。
5. **MLflow：version 与 alias 分离**——immutable candidate version 与可移动 canonical pointer 分开。

### B. 可以改造后采用

1. **MLflow champion alias → `math_mode` canonical pointer**：需要额外加入 `expected_canonical_version`，不能只有无条件 alias reassignment。
2. **Dagster DataVersion → MathModel Artifact Fingerprint**：除 code/input 外增加 parameters、environment、validation contract。
3. **DVC experiment refs → 轻量 candidate manifest/目录**：不必引入完整 DVC cache/remote，只采用 namespace、baseline、lock 和 promotion 思想。
4. **concurrency pool → canonical writer lease**：只控制临界写，不把整个模型训练放进全局串行池。

### C. 可以作为对照实验

1. shared workspace vs isolated candidate workspace；
2. last-writer-wins vs expected-version promotion；
3. 只做文件 SHA vs provenance fingerprint；
4. Reviewer PASS 后直接写论文 vs blocking promotion gate；
5. 全局大锁 vs 只锁 canonical pointer 更新。

### D. 不建议采用

1. 比赛中直接部署完整 DVC + MLflow + Dagster 三套基础设施；
2. 用 `latest.csv`、`final_v7.csv` 之类文件名代替正式 version identity；
3. Solver / Reviewer / Writer 都拥有 `求解/结果索引.md` 的写权限；
4. 为避免 race，把全部并行计算都置于一个全局锁；
5. Reviewer 通过后无条件覆盖 canonical，不检查 canonical 是否已被其他 Agent 前进。

## 11. 存在的问题

### 11.1 DVC 的问题

- 对竞赛项目来说完整 DVC 引入成本偏高；
- Git refs、cache、queue、remote 增加运维面；
- 临时 workspace 与 apply 机制本身复杂，历史 issues 中也存在 queue/temp/apply 边界问题；
- 它解决的是通用实验版本问题，不理解华为杯题面硬约束。

结论：**借机制，不建议直接把 DVC 变成 math_mode 核心运行时。**

### 11.2 MLflow 的问题

- Model Registry 面向模型生命周期，不直接理解多问数学建模、表格、仿真、优化方案和证明；
- alias 本质上是 mutable pointer；本轮一手资料未证明其 alias 更新提供 expected-old-version CAS；
- 若直接照搬，两个 Reviewer 仍可能发生“后写覆盖先写”的晋级 race。

结论：`math_mode` 应采用 version + alias 思想，但 promotion 必须更严格。

### 11.3 Dagster 的问题

- 完整 orchestrator 对赛时环境过重；
- DataVersion 是通用资产版本，不自动等于科学有效性；
- `blocking=True` 只是一种执行门控，本身不能判断数学结论是否合理；
- concurrency pool 也不能替代 artifact immutability / optimistic concurrency。

结论：借用 provenance/staleness/check 模式，而不是引入整套服务。

## 12. 与 math-mode 对比

| 能力 | math-mode | 项目 | 差异 |
|---|---|---|---|
| 原始输入只读 | 已有明确规则 | DVC/Dagster 均强调版本化依赖 | 保持 |
| 候选实验隔离 | 尚无统一 candidate namespace | DVC TempDirExecutor | **新增** |
| 候选绑定 baseline | 尚无机器协议 | DVC `refs/exps/<baseline>/<name>` | **新增** |
| 结果 provenance | 已有文件 SHA、结果索引、支撑材料链 | Dagster code + input DataVersion | **改进：从文件 hash 升级到依赖 fingerprint** |
| stale 状态 | 规则层有“旧证据不可用”思想，但无统一状态 | Dagster `MISSING/STALE/FRESH` | **新增** |
| 确定性验证门禁 | 已较强 | Dagster blocking asset check | 保持并结构化 |
| Reviewer | 已规划 evidence judge / regression | 三项目都不是数学 Reviewer | 保持 |
| candidate / canonical 分离 | 尚无统一机器 pointer | MLflow version + alias | **新增** |
| promotion | 目前主要靠流程约定 | MLflow candidate/champion/promote | **新增正式生命周期动作** |
| stale-write 防护 | 尚无 expected-version protocol | DVC ref divergence + rwlock 提供参考 | **新增 CAS/expected-parent guard** |
| canonical writer | `结果索引.md` 是主索引，但未定义唯一写入器 | DVC lock / Dagster concurrency pool 可参考 | **改进为小临界区单写** |
| 论文消费版本 | 依赖结果索引和审计 | MLflow alias 解耦消费者与版本 | **改进：Writer 固定解析 canonical manifest** |
| checkpoint/resume | 上轮建议新增 | 本轮不重复 | checkpoint 应额外保存 canonical_version 与 pending candidate IDs |

总体判断：

- **保持**：只读输入、真实执行、独立验证、结果索引、支撑材料 hash、LaTeX source of truth；
- **改进**：结果索引由“人工/Agent 共享可写事实表”逐步变成 canonical manifest 的人类可读投影；
- **新增**：candidate namespace、artifact provenance fingerprint、STALE 状态、promotion manager、expected-version guard；
- **替换**：用“versioned candidate + pointer”替换 `latest/final_vN` 文件命名式事实管理；
- **暂不采用**：完整 DVC / MLflow / Dagster runtime。

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：设计 Candidate Artifact Contract

不要先做复杂多 Agent，先定义候选产物契约。

建议候选目录概念：

```text
求解/.candidates/
  q1/
    <candidate_id>/
      candidate_manifest.json
      code/
      results/
      figures/
      validation/
      logs/
```

这是未来 model-search-agent、Reviewer、checkpoint、支撑材料的共同边界。

#### P0-2：建立 machine-readable Canonical Manifest

建议不要让 `求解/结果索引.md` 独自承担并发事实源。

概念上增加：

```text
求解/canonical.json
```

例如：

```json
{
  "canonical_version": 18,
  "questions": {
    "q1": {
      "candidate_id": "q1-...-b2",
      "artifact_fingerprint": "...",
      "validation_status": "PASS"
    }
  }
}
```

`求解/结果索引.md` 可以由它和真实产物生成/核对，继续作为人类可读索引。

#### P0-3：Promotion 必须使用 expected-version guard

最关键的 stale-write 防护：

```text
读取 canonical_version = 18
↓
Reviewer 对 candidate-B 完成检查
↓
请求 promote(expected=18)
↓
如果当前还是 18 → 可晋级到 19
如果已经是 19 → 拒绝，重新检查
```

这比“谁最后写文件谁赢”安全得多。

#### P0-4：把 freshness 变成硬门禁

至少检查：

```text
input_hashes
code_hash
params_hash
environment_hash
validation_contract_hash
artifact_hashes
```

任何关键依赖变化，candidate / figure / validation report 都进入 `STALE`，不得进入论文。

### P1：值得实验

#### P1-1：并行故障注入实验

模拟：

1. Solver-A/B 同时基于 canonical v10 开始；
2. B 先完成并晋级 v11；
3. A 后完成并尝试晋级；
4. 系统应拒绝 A 的 stale promotion，而不是覆盖 v11。

#### P1-2：artifact source consistency test

故意制造：

- 表格来自 candidate-A；
- 图来自 candidate-B；
- 论文引用 candidate-C 的 metric。

检查 provenance gate 能否发现“跨版本拼接”。

#### P1-3：锁粒度实验

比较：

- 全流程 global lock；
- per-question lock；
- candidate 无锁计算 + promotion 短锁/CAS。

评估吞吐量、冲突率、恢复复杂度和赛时总耗时。

### P2：长期考虑

- 将 canonical manifest 与上一轮 checkpoint contract 统一版本号；
- artifact lineage DAG；
- 跨问题依赖的 selective invalidation，例如 Q1 canonical 改变后只标记依赖它的 Q2/Q3 artifact stale；
- 更细粒度的 resource lease / writer lease；
- candidate retention / garbage collection 策略。

### 不建议采用

- 现在立即把正式项目改成 DVC/MLflow/Dagster 集成项目；
- 让 LLM 自己判断“这份文件应该是最新的”；
- 依赖文件 mtime 选择结果；
- 通过人工命名 `final_final_v8` 表示 canonical；
- 为追求并行而放弃 promotion gate。

## 14. 可形成的新 Skill / Agent

以下只提出设计，不在本轮创建：

### `artifact-registry-manager`

维护 candidate manifest、fingerprint、STALE/FRESH 和 canonical pointer。

### `promotion-gate-agent`

名称可叫 Agent，但核心应是确定性规则：验证 candidate 的 hard gate、hash 和 expected canonical version，再执行 promotion。

### `artifact-lineage-auditor`

检查论文、图表、表格、官方输出是否全部来自同一 canonical lineage；发现跨 candidate 混用立即阻塞。

### `stale-result-detector`

在数据、代码、参数、验证协议改变后计算受影响产物集合，只使依赖它们的 artifact 失效。

### `writer-snapshot-resolver`

为 Writer 固定一个 canonical snapshot，使长篇写作过程中 canonical 后续变化不会造成同一论文前后引用不同版本；若需升级，显式开启新 snapshot。

## 15. 与历史调研的去重检查

### 15.1 本轮未重复的内容

- 不再论证“结果必须真实运行”（14:00 已有）；
- 不再研究模型搜索算法/MCTS（15:06 已有）；
- 不再研究 Reviewer 校准/JudgeEval（16:04 已有）；
- 不再研究 checkpoint 如何保存和恢复（17:07 已有）。

### 15.2 本轮真正新增认知

1. **candidate workspace isolation**：并行计算与正式事实写入必须隔离；
2. **baseline-bound candidate identity**：候选必须绑定它开始时的事实基线；
3. **version + alias/pointer 分离**：候选版本不覆盖，canonical 只是指针；
4. **artifact staleness**：文件存在不代表仍可用，依赖版本变化必须使其失效；
5. **blocking promotion gate**：验证必须成为下游论文/提交的执行依赖；
6. **expected-version promotion**：旧 Agent 晚到时必须拒绝 stale write；
7. **锁只保护短 promotion 临界区**：不牺牲并行求解吞吐。

### 15.3 项目去重

`DVC`、`MLflow`、`Dagster` 均未出现在此前 `research/INDEX.md` 的四轮项目集合中，因此是本轮新研究对象。

## 16. 下一轮推荐方向

建议下一轮轮换到：

**赛时 Multi-Agent Resource Scheduler：时间预算、CPU/GPU 预算、关键路径、speculative execution 与自动取消。**

重点问题：

- 48–72 小时比赛如何按 deadline 动态分配 Solver/Reviewer/Writer 预算；
- 哪些候选应继续算，哪些应提前停止；
- 多问存在依赖时如何识别 critical path；
- GPU/CPU/内存有限时如何避免多个 Agent 互相拖死；
- 是否需要 speculative execution，以及如何在已有可信结果足够时自动取消低价值分支；
- 如何把资源预算与 15:06 的 model-search budget、17:07 checkpoint 和本轮 candidate registry 联动。

## 17. Sources

### 已阅读源码 / 官方仓库文档

#### math_mode 当前基线

- https://github.com/shaxiaoguang123/math_mode/blob/main/README.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/AGENTS.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/CLAUDE.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/华为杯_求解规范/华为杯_求解规范.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/INDEX.md
- https://github.com/shaxiaoguang123/math_mode/blob/main/research/2026-09-08/2026-09-08_17-07_checkpoint-resume-state.md

#### DVC

- https://github.com/treeverse/dvc
- https://github.com/treeverse/dvc/blob/main/README.rst
- https://github.com/treeverse/dvc/blob/main/dvc/repo/experiments/executor/local.py
- https://github.com/treeverse/dvc/blob/main/dvc/repo/experiments/refs.py
- https://github.com/treeverse/dvc/blob/main/dvc/repo/experiments/utils.py
- https://github.com/treeverse/dvc/blob/main/dvc/repo/experiments/apply.py

#### MLflow

- https://github.com/mlflow/mlflow
- https://github.com/mlflow/mlflow/blob/master/docs/docs/classic-ml/model-registry/workflow.mdx
- https://github.com/mlflow/mlflow/blob/master/mlflow/store/model_registry/abstract_store.py
- https://github.com/mlflow/mlflow/blob/master/mlflow/store/model_registry/sqlalchemy_store.py

#### Dagster

- https://github.com/dagster-io/dagster
- https://github.com/dagster-io/dagster/blob/master/README.md
- https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/data_version.py
- https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_check_decorator.py

### 官方说明（作为源码阅读补充）

- DVC Experiments / versioning：https://dvc.org/doc/start/experiments
- DVC experiment refs：https://dvc.org/blog/experiment-refs/
- MLflow Model Registry：https://mlflow.org/docs/latest/ml/model-registry
- MLflow Registry Workflow：https://www.mlflow.org/docs/latest/ml/model-registry/workflow/
- Dagster Asset Checks：https://docs.dagster.io/guides/test/asset-checks

### 证据边界

- 本轮没有实际在 `math_mode` 中安装或运行 DVC、MLflow、Dagster，因此不声称这些框架已在本项目环境验证通过。
- DVC 的 workspace isolation / refs / rwlock / divergence 结论来自实际源码阅读。
- MLflow 的 version / alias / tag / promotion 结论来自官方仓库文档和 API 实现搜索；**没有证据证明 alias 更新具备 expected-old-version CAS，因此 `math_mode` 的 expected-version guard 是本轮提出的增强设计，不是 MLflow 已有能力。**
- Dagster 的 DataVersion / DataProvenance / STALE/FRESH / blocking check 来自实际源码阅读；它们只保证资产版本与执行门控，不等价于数学模型正确性。
