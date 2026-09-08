# MathModel Agent Research

## 1. 本轮研究主题

**Citation / External Evidence Provenance：把“找到一篇论文”升级为“可验证来源实体 → 可定位全文证据 → claim-evidence 映射 → 可引用状态 → stale 检查”。**

本轮聚焦华为杯数学建模 Agent 的外部知识可信链。核心问题不是“怎样让 Writer 多引用文献”，而是：

> 当模型公式、参数范围、算法依据、工程背景、官方统计数据和赛题外数据来自论文、标准、手册、网页或数据库时，如何证明“来源真实存在、元数据没有编造、真正读到了可支撑该论断的内容、引用的是正确版本，而且后续 Writer 没有自行补 DOI/作者/年份或把一个真实但不支持 claim 的来源塞进论文”？

本轮深入研究 3 个此前未进入 `research/INDEX.md` 的高价值对象：

1. `Future-House/paper-qa`（PaperQA2）：科学文献 agentic retrieval、文档/元数据/content hash、Context 与引用链；
2. `KathCYM/CiteGuard`：retrieval-aware citation attribution，主动搜索、全文读取、`find_in_text`、额外上下文与可追踪运行历史；
3. `boheling/deltasci`（DeltaScience）：确定性 citation verification，将“来源存在”“元数据一致”“claim 被支持”“无法验证”拆成不同审计状态。

本轮核心结论：

> `math_mode` 已经有较强的**结果证据链**和**自主数据文件级溯源**，但还缺少一个位于“搜索/阅读”和“论文 Writer”之间的 **External Evidence Ledger + Citation Gate**。Writer 不应直接消费搜索结果、URL、LLM 摘要或自由手写 BibTeX，而应只消费已经完成来源解析、内容快照、证据定位和 claim-support 审计的 `evidence_id`。

建议目标结构：

```text
外部搜索 / 官方站点 / 论文库 / 手册 / 数据门户
                      ↓
             Source Resolver
 DOI / arXiv / PMID / URL / title / version / metadata providers
                      ↓
          Source Snapshot / Manifest
 content_hash + retrieved_at + local_snapshot + license + version
                      ↓
              Evidence Extractor
 raw page/section/span + span_hash + context summary (derived only)
                      ↓
               Claim Ledger
 claim_id → evidence_id → SUPPORTS / PARTIAL / CONTRADICTS / UNVERIFIABLE
                      ↓
              Citation Gate
 existence + metadata + content freshness + claim support
                      ↓ only VERIFIED/CITABLE
 BibTeX builder → 结果索引/求解说明 → Writer → TeX → 最终论文
```

## 2. 为什么选择这个主题

### 2.1 与历史调研的差异

当前 `research/INDEX.md` 已覆盖：

- 14:00：evidence-first 科研 Agent；
- 15:06：模型候选树、并行实验与可执行评测；
- 16:04：Reviewer / Judge 可执行与校准；
- 17:07：Memory / Checkpoint / Resume；
- 18:04：candidate artifact ownership、stale-write prevention、canonical promotion；
- 19:07：Resource Scheduler、early pruning 与动态资源回收。

18:04 的 provenance 重点是**内部计算 artifact**：代码、输入和结果发生变化后，旧结果应标记 STALE。本轮不重复内部 artifact lineage，而研究完全不同的一条链：

```text
外部论文/网页/官方数据
→ 是否真实存在？
→ 是否是正确版本？
→ 元数据是否一致？
→ 是否真正读取？
→ 哪一页/哪一段支持哪个 claim？
→ Writer 是否只能引用已验证证据？
```

19:07 报告也明确把 Citation / External Evidence Provenance 列为下一轮建议方向，因此本轮属于主动轮换而非改写旧内容。

### 2.2 当前 math_mode 已有什么

重新读取 `README.md`、`AGENTS.md`、`CLAUDE.md`、`华为杯_求解规范/华为杯_求解规范.md`、论文模板与近期 research 后确认：

当前已经具备的重要基础：

- 数学模型、公式和学术论断要求引用正式文献或官方资料，明确“不把 AI 当参考文献来源”；
- 赛题外、真正进入模型或结论的自主数据必须保存到 `数据/自主/`，并登记来源/URL、获取日期、许可/条款、获取与整理方式、脚本；
- `求解/结果索引.md` 是论文数字、参数、图表的主索引；
- 支撑材料通过清单和 SHA-256 审计；
- LaTeX 主链已经有 `reference.bib`、`natbib`、`gmcm.bst` 和真实参考文献章节；
- 正式论文不允许凭“看起来合理”补数。

这些规则已经很好地解决了“来源应该被记录”和“最终结果应该可复核”的原则问题。

### 2.3 当前缺口

仓库当前尚未形成统一机器可读的：

- `source_id` / canonical identifier；
- bibliographic metadata 的**来源本身**（Crossref、DataCite、官方页、作者 PDF 等）；
- source content hash / snapshot version；
- `evidence_id` 与精确 page/section/span；
- `claim_id → evidence_id` 关系；
- source existence / metadata match / claim support 三类独立状态；
- `UNVERIFIABLE` / `STALE` 的一等状态；
- Writer 的“只允许使用 VERIFIED evidence”硬门禁；
- 由 verified metadata 自动构建 `reference.bib` 的流程；
- citation verifier 自身的版本与回归测试。

因此，现在即使遵守“必须有真实参考文献”，仍可能发生：

```text
真实论文 + 错 DOI
真实 DOI + 错题名/作者/年份
真实论文 + 与正文 claim 无关
只读摘要，却在论文中写成全文结论
来源网页后来更新，旧参数仍被使用
LLM 自动补全一个不存在的 BibTeX 字段
一个 citation 实际只支持句子的一半
```

这些问题需要独立的 citation/evidence lifecycle，而不是继续扩充 Writer prompt。

## 3. 搜索范围与关键词

本轮属于 P1“scientific research / paper writing / verification agent”与 P2“provenance / citation verification”的交叉，但只研究对数模竞赛直接有价值的外部证据可信链。

主要关键词：

- scientific citation verification agent
- citation attribution alignment
- full text citation validation
- claim evidence traceability
- citation provenance content hash
- DOI metadata verification Crossref
- real paper wrong citation detection
- evidence span page citation
- scientific RAG citation context
- verifier calibration unsupported citation
- external data provenance snapshot hash
- stale web evidence

优先阅读：

- 三个项目 GitHub 官方仓库、README、源码；
- PaperQA2 的 `types.py`、agent tools 与 metadata 处理；
- CiteGuard 的 agent loop、全文读取、结果持久化；
- DeltaScience 的 audit type system、citation verifier 目录、claim-support auditor；
- 项目对应 arXiv/官方论文页面；
- 2026 年 citation verifier calibration 论文作为机制补充。

没有把普通 Zotero 插件、通用 RAG、论文格式化工具当作重点对象。

## 4. 新发现项目

### 项目 1：PaperQA2

- 名称：PaperQA2
- Repository：https://github.com/Future-House/paper-qa
- 本轮固定读取 commit：`57e89f7223b0960d5ee5ea048c69e3c47e088572`
- Stars：9,173（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-09-08T08:55:34Z`；`pushed_at=2026-09-07T22:05:10Z`
- 目标：面向科学文献的高准确率 agentic RAG，强调 grounded answer 与 in-text citation。
- 核心能力：文献搜索、全文索引、metadata hydration、evidence gathering、contextual summary、re-ranking、引用、retraction/journal-quality metadata。
- 本轮实际阅读：
  - `README.md`
  - `src/paperqa/types.py`
  - `src/paperqa/agents/tools.py`
  - metadata/provider 相关源码检索

对 `math_mode` 最有价值的不是“再加一个 RAG”，而是它把**来源文档、原始 chunk、派生 Context、bibliographic metadata、content hash 和会话/工具历史分开保存**。

### 项目 2：CiteGuard

- 名称：CiteGuard
- Repository：https://github.com/KathCYM/CiteGuard
- 本轮固定读取 commit：`391aee8bd3204c130c6fd0db2e515a8719db682f`
- Stars：7（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-08-05T10:54:37Z`；`pushed_at=2026-04-13T02:55:04Z`
- 目标：把 citation evaluation 重构为 citation attribution alignment，并通过 retrieval-aware agent 找到真正适合某个科学 claim 的引用。
- 核心能力：`search_relevance`、`search_citation_count`、`read`、`find_in_text`、`search_text_snippet`、`ask_for_more_context`、`select`，以及运行 history/result JSON。
- 本轮实际阅读：
  - `README.md`
  - `src/retriever/agent.py`
  - `src/run_main.py`
  - arXiv:2510.17853 的正文与实验说明

对 `math_mode` 最有价值的是：**引用选择不能停在标题/摘要层；证据不足时 Agent 应主动进入全文、搜索原文、补上下文，再决定 citation。**

### 项目 3：DeltaScience

- 名称：DeltaScience / `deltasci`
- Repository：https://github.com/boheling/deltasci
- 本轮固定读取 commit：`5b36015ead6934a67622b1777f11ce59dfe36a68`
- Stars：143（本轮 GitHub 元数据）
- 最近更新时间：`updated_at=2026-06-14T17:58:01Z`；`pushed_at=2026-05-30T08:20:34Z`
- 目标：scientific work verification layer；对 PMID、DOI、arXiv、GitHub、dataset 等来源做实际解析和审计。
- 核心能力：citation existence/metadata verification、claim support、PDF bibliography linking、machine-readable findings、MCP/CLI verifier。
- 本轮实际阅读：
  - GitHub README / changelog
  - `src/deltasci/audit/base.py`
  - `src/deltasci/audit/support.py`
  - `src/deltasci/audit/citations/` 目录结构

对 `math_mode` 最有价值的是它明确把：

```text
“这个来源存在”
“元数据正确”
“这个来源真的支持该 claim”
“当前无法可靠判断”
```

拆成不同判定，而不是一个模糊的 `citation_ok=true`。

## 5. 深入架构分析

### 5.1 PaperQA2：文献对象、原始文本和 Context 不应混为一个对象

PaperQA2 的 `Doc` 保存：

```text
docname
dockey
citation
content_hash
```

其中 `content_hash` 明确针对**文档内容本身**，而不是文件路径。

`DocDetails` 进一步保存：

```text
authors / title / publication_date / year
journal / publisher / volume / pages
DOI / DOI URL / pdf_url
citation_count
is_retracted
license
file_location
doc_id
bibtex
other metadata
```

尤其值得注意的是：`doc_id` 可以由 DOI 与 content hash 共同构造；BibTeX metadata 还记录其来源，例如：

```text
self_generated
crossref
semantic_scholar
```

这对 `math_mode` 很重要，因为：

> DOI 是“文献实体身份”的一部分，而 content hash 是“本次实际读到的内容版本”的一部分；两者不能相互替代。

一篇论文可能：

- DOI 不变，但作者接受稿/最终出版版内容不同；
- arXiv 同一 ID 出现新版；
- 网页 URL 不变，但正文更新；
- metadata provider 返回的字段发生修正。

因此，External Evidence Ledger 不能只有 URL。

### 5.2 PaperQA2：Context 是派生证据，不是原始事实源

`Text` 对象把一个原始 chunk 与其 `Doc` 绑定；`Context` 再保存：

- 针对某个 question 的 contextual summary；
- 链回原始 `Text`；
- relevance score；
- context ID。

`PQASession` 又保存 raw answer、contexts、references、config hash、tool history，并能识别哪些 Context ID 真正被 answer 使用。

这是一个很好的 lineage：

```text
Doc → Text chunk → Context summary → Answer
```

但对于 `math_mode`，必须再加一个限制：

> LLM 生成的 Context summary 只能用于检索、排序和写作辅助，不能成为 canonical evidence。正式 claim 应回链到原始 page/section/span，并保存 span hash。

否则会出现“summary 自己已经轻微改写原文含义，后续 Writer 又把 summary 当一手证据”的二次漂移。

### 5.3 CiteGuard：citation attribution 是一个主动检索过程

CiteGuard 的 agent loop 不是一次 search → select，而支持：

```text
search_relevance
search_citation_count
read
find_in_text
search_text_snippet
ask_for_more_context
select
```

源码 `_read()` 会真实下载 open-access PDF，使用 PDF reader 提取全文；`_read_and_find_in_text()` 会在实际全文中寻找指定内容。如果全文读取失败，则显式返回失败，而不是假装已经阅读全文。

这给 `math_mode` 一个很重要的 Citation Agent 行为边界：

```text
发现候选文献 ≠ 已读取
已读取摘要 ≠ 已读取全文
全文可访问 ≠ 找到支持 claim 的 span
找到相关 span ≠ 元数据/版本已验证
```

这些状态应该机器化记录，而不是在最终报告中用一句“已查阅文献”概括。

### 5.4 CiteGuard：一个 claim 可能有多个合法 citation

CiteGuard 的研究将 citation attribution 从“唯一标准答案”扩展为可能存在多个合理引用。其 iterative retrieval 会把已经选中的文献加入 exclusion set，再继续寻找其他候选；人工评价也允许 alternative valid citations。

这对数学建模尤其重要：

- 一个经典算法可以有原始论文、标准教材和权威软件文档；
- 一个工程参数可能有标准、厂家手册和论文多个来源；
- 同一模型公式可以有原始来源和更适合解释/复现的现代资料。

因此 `math_mode` 的 Claim Ledger 不应强制：

```text
1 claim = 1 citation
```

而应允许：

```text
claim_id
  ├─ primary_evidence
  ├─ corroborating_evidence[]
  └─ conflicting_evidence[]
```

### 5.5 一个非常实际的 version-drift 示例

本轮读取 CiteGuard 的 arXiv 页面时发现一个很有价值的 provenance 现象：

- 页面顶部 abstract 仍写“最高 65.4%、human 69.7%”；
- 同一页面当前论文正文/实验表中已经写“DeepSeek-R1 68.1%、human 69.2%”，并给出 5-run 结果。

也就是说，**同一个 arXiv 标识符下，不同信息层可能对应不同修订状态**。

本轮不把这当作谁“写错了”，而把它作为架构证据：

> 不能仅保存 `arXiv:2510.17853` 就认为未来一定能重现今天读到的数字；应保存访问时间、版本/内容 hash，并让具体 claim 指向实际读取的证据 span。

这正是 External Evidence Ledger 需要 `source identity + source snapshot + evidence span` 三层的原因。

### 5.6 DeltaScience：来源真实性与 claim-support 必须分开

`AuditFinding` 的状态系统包括：

```text
verified
mismatch
unverifiable
skipped
```

并保存：

```text
target_summary
auditor_name
fetched_metadata
mismatch_reasons
confidence
audited_at
```

更关键的是其基类明确要求：

> 不实际 fetch 并比较真实 record，就不能标记为 verified。

这比“让 LLM 再检查一次刚才自己生成的 DOI”可靠得多。

DeltaScience 还把不同 auditor 分开：Crossref、PubMed、OpenAlex、arXiv、DataCite、Semantic Scholar 等分别解析来源。这个设计很适合 `math_mode`：identifier resolver 应该是 provider-specific tool，而不是让 Writer 直接根据记忆补 metadata。

### 5.7 DeltaScience：真实论文也可能是错误引用

它的 `ClaimSupportAuditor` 专门处理一个常见失败模式：

```text
citation 真实存在
metadata 也正确
但是这篇论文并不支持当前句子
```

当前实现以 fresh-fetched PubMed abstract 的 salient-term overlap 做保守检查，并定义：

- 支持阈值；
- 明显不支持阈值；
- 中间区间返回 `unverifiable`；
- claim 太短或没有可用 abstract 也 abstain；
- 不会因为“无法判断”就自动 PASS。

虽然这个算法不能直接覆盖数学、运筹、工程手册和中文官方网页，但**分层语义非常值得照搬**：

```text
Existence Gate
Metadata Gate
Evidence Access Gate
Claim Support Gate
```

### 5.8 Verifier 本身也存在测量误差

2026 年论文《Evaluating and Guarding Citation Faithfulness in Agentic Scientific Synthesis》指出，在完全相同的 agent 输出上，仅改变 verifier 严格度，测得的 unsupported-citation rate 可以从约 3% 变化到约 18%。

这与 16:04 的 Judge calibration 研究形成新的连接：

> Citation Gate 也必须记录 verifier 名称、版本、阈值和 calibration set；不能输出一个无上下文的“citation accuracy=98%”。

本轮新增的是 citation-specific calibration，而不是重复通用 Reviewer 结论。

## 6. Agent / Skill 设计

建议未来不是创建一个“万能文献 Agent”，而是按职责拆成四个轻量组件。

### 6.1 Source Resolver

负责：

```text
输入：URL / DOI / arXiv ID / PMID / title / dataset ID
输出：canonical source record
```

职责：

- 标识符规范化；
- 实际查询官方/权威 metadata provider；
- 多 provider 冲突记录；
- 不允许 LLM 凭记忆生成缺失 DOI。

### 6.2 Evidence Extractor

负责：

```text
source snapshot
→ relevant raw span
→ page / section / line-or-offset
→ evidence_id
```

LLM 可以辅助定位，但必须保留 raw span 与 snapshot hash。

### 6.3 Citation Verifier

负责四层检查：

```text
SOURCE_EXISTS
METADATA_MATCH
CONTENT_FRESH
CLAIM_SUPPORTED
```

输出不能只有 PASS/FAIL，至少需要：

```text
VERIFIED
PARTIAL
CONTRADICTED
UNVERIFIABLE
STALE
REJECTED
```

### 6.4 Writer Citation Interface

Writer 不直接访问任意搜索结果，接口只提供：

```text
claim_id
verified evidence IDs
approved BibTeX keys
short evidence summaries
exact source locations
```

如果没有 `VERIFIED/CITABLE` evidence，则 Writer 必须：

- 降低 claim 强度；
- 标记待证；
- 或不写该学术论断。

而不是自动找一个“看起来相关”的文献补上。

## 7. Workflow

建议未来的外部证据生命周期：

```text
DISCOVERED
   ↓
RESOLVED
   ↓  identifier/metadata resolved
SNAPSHOTTED
   ↓  content hash + local/immutable snapshot
EVIDENCE_EXTRACTED
   ↓  raw span/page/section
VERIFIED
   ↓  claim-support + metadata gate
CITABLE
   ↓
Writer / reference.bib
```

旁路状态：

```text
UNVERIFIABLE  无法取得足够证据
CONTRADICTED  来源与 claim 冲突
REJECTED      假来源/错 metadata/低质量来源
STALE         source/version/content 变化后旧审计失效
```

### 与现有 math_mode 的接点

```text
Phase 1 题目与数据审计
  └─ 外部数据进入 Source Resolver + 数据/自主/

Phase 2 求解计划
  └─ 公式/参数/背景 claim 创建 claim_id

Phase 3 求解
  └─ 用到外部参数时引用 evidence_id

独立验证
  └─ Citation Gate + external evidence audit

结果索引
  └─ 记录关键 claim/evidence IDs

论文阶段
  └─ 只从 CITABLE source record 生成 reference.bib
```

这不改变现有事实链，而是在“外部知识进入事实链”的入口增加一道可审计接口。

## 8. Code Execution / Tools

### PaperQA2

本轮源码确认：

- 真实构建文献索引；
- metadata provider 查询；
- 文档 chunk / embedding / evidence retrieval；
- LLM contextual summarization；
- agent tool history；
- content hash；
- BibTeX 生成/合并。

它不是数学模型执行 sandbox，也没有替代 `math_mode` 的 Python/MATLAB 求解器；价值在 external evidence layer。

### CiteGuard

本轮源码确认：

- Semantic Scholar 检索；
- open-access PDF 下载与解析；
- 全文查找；
- 多步 Agent action loop；
- run metadata、history、papers、duration、token 使用持久化；
- 已处理 ID 可跳过，具有基础 resume 行为。

它主要验证“该 claim 应该引用哪篇论文”，不是数值计算环境。

### DeltaScience

本轮源码/文档确认：

- 对多个 identifier/provider 做真实外部 lookup；
- deterministic verifier 被刻意放在 trust path；
- claim-support checker 使用 fresh-fetched evidence；
- 可输出机器可读 audit findings；
- README 描述 PDF bibliography → in-text citation context 的 paper mode，以及 MCP/CLI verifier。

它同样不是数学求解器，而是可嵌入的 scientific verification layer。

## 9. QA / Reviewer / Verification

本轮最重要的 QA 结论是：citation QA 至少要拆成五问。

### Q1：Source existence

“这个 DOI/arXiv/URL/数据集 ID 真的存在吗？”

不能由 LLM 自评。

### Q2：Metadata integrity

“title / authors / year / venue / version 与真实 record 一致吗？”

一个真实 DOI 也可能被配上错误标题。

### Q3：Evidence accessibility

“本轮是否实际拿到了支持 claim 所需的全文/页面/表格/官方页面内容？”

只拿到 search snippet 时不能宣称“阅读全文”。

### Q4：Claim support

“当前 citation 是否真正支持这句 claim？”

这与 Q1/Q2 完全不同。

### Q5：Freshness

“当前 claim 引用的 evidence span 是否仍来自当前 source snapshot？”

如果网页、arXiv 版本、官方数据或本地快照变化，旧 `VERIFIED` 应自动变为 `STALE`。

### Citation verifier 自身 QA

建议建立专门 regression cases：

- fabricated DOI；
- 真实 DOI + 错 title；
- 真实论文 + 错 claim；
- claim 只被部分支持；
- abstract 支持但全文限定条件不同；
- source 无法访问；
- 多个同样合理的 citation；
- arXiv 新旧版本；
- 官方网页改版但 URL 不变；
- metadata providers 互相冲突；
- 中文标准/手册无 DOI；
- 数据门户提供新版本数据。

至少报告：

```text
fabrication_detection_recall
metadata_mismatch_precision
unsupported_claim_recall
false_reject_rate
unverifiable_rate
citation_coverage
verification_latency
```

## 10. 值得借鉴的设计

### A. 可以直接借鉴

1. **PaperQA2：原始 Doc / Text 与派生 Context 分离。**
   - 原始 span 是证据；Context 是检索/摘要产物。
2. **PaperQA2：content hash 与 metadata source provenance。**
   - DOI/URL 之外还绑定实际读取内容。
3. **CiteGuard：search → read/full-text → find_in_text → select。**
   - citation attribution 是主动 evidence gathering，而非标题匹配。
4. **CiteGuard：保存 paper buffer + agent history + run metadata。**
   - 可以解释“为什么最后选这篇文献”。
5. **DeltaScience：existence、metadata、support、unverifiable 分层。**
6. **DeltaScience：保存 fetched metadata、mismatch reasons、audited_at。**
7. **DeltaScience：无法可靠判断时 abstain，而不是自动 PASS。**

### B. 可以改造后采用

1. DeltaScience 当前 claim-support 核心对 PubMed abstract 更友好；`math_mode` 需要扩展到：
   - 数学/统计论文；
   - 标准；
   - 工程手册；
   - 官方竞赛规则；
   - 政府/行业数据；
   - 中文网页/PDF。
2. PaperQA2 自动生成/补 BibTeX 很方便，但 `math_mode` 不应让 `self_generated` metadata 直接进入最终 bibliography；需要 Citation Gate 后才可发布。
3. CiteGuard 的目标是 attribution accuracy；数模项目还需要“参数数值/公式/假设是否由该 span 精确支持”的 finer-grained claim check。
4. 外部 evidence freshness 应与 18:04 的 internal artifact freshness 复用同一理念，但两套 fingerprint 分开维护。

### C. 可以作为对照实验

- Writer 自由联网引用 vs Writer 只读 verified evidence ledger；
- abstract-only citation selection vs full-text/span-aware；
- 只校验 DOI existence vs existence + metadata + claim-support；
- 单 verifier vs calibrated multi-stage verifier；
- 不保存 source snapshot vs content-hash snapshot；
- 单一“PASS/FAIL” vs `UNVERIFIABLE/STALE/PARTIAL` 多状态。

### D. 不建议采用

- 让 Writer 直接从模型记忆生成 DOI/BibTeX；
- “有 DOI 就算引用真实”；
- “检索结果摘要看起来相关就算读过论文”；
- 用 LLM summary 代替原始证据 span；
- source fetch 失败时默认通过；
- Citation Judge 不记录版本、阈值与审计时间；
- 为追求引用数量而引用与 claim 关系弱的论文。

## 11. 存在的问题

### 11.1 PaperQA2

- 重点是高质量 scientific RAG，不是严格的 formal citation gate；
- Context 是 LLM summary，仍需回到 raw text；
- metadata hydration/自动 BibTeX 提升便利性，但对正式论文仍需要额外 verified-state；
- 大规模索引和多 provider 可能增加赛时网络/API 成本。

### 11.2 CiteGuard

- 重点是找到合适 citation，不等价于逐句逻辑 entailment；
- 全文可访问性仍是现实约束；
- benchmark 的 fuzzy title correctness 不适合作为 `math_mode` 最终 bibliography 校验规则；
- Agent retrieval 本身有随机性，因此正式引用仍需要 deterministic post-check。

### 11.3 DeltaScience

- claim-support 当前实现具有领域限制，不能直接用于所有数学建模来源；
- 基于 abstract salient-term overlap 是保守启发式，不是数学意义上的蕴含证明；
- 对无标准 identifier 的中文手册/网页需要新增 resolver；
- 来源质量、版本、引用适用范围仍需 `math_mode` 自己定义。

### 11.4 通用问题

External Evidence Ledger 会增加工作量；如果每一个常识句都做完整 source snapshot，会拖慢赛时。因此建议分级：

```text
Tier 0 题面/官方附件：直接纳入只读事实源
Tier 1 进入模型的公式/参数/外部数据：强制 ledger + snapshot + exact span
Tier 2 关键学术/工程论断：强制 citation verification
Tier 3 普通背景叙述：至少 verified bibliographic source，可降低 span 审计强度
```

这样把验证预算集中在真正影响建模质量和结果真实性的地方。

## 12. 与 math-mode 对比

| 能力 | math-mode | 本轮项目 | 差异 |
|---|---|---|---|
| 外部数据来源记录 | 已要求来源、日期、许可、脚本 | PaperQA2/DeltaScience 有结构化 metadata | 保持现有规则，升级为机器 ledger |
| 文献实体身份 | 有 `reference.bib`，但无统一 resolver contract | PaperQA2 DOI/doc_id；DeltaScience provider verifier | **新增** canonical source record |
| 实际内容版本 | 内部支撑材料有 SHA；外部文献未统一绑定 snapshot | PaperQA2 `content_hash` | **新增** external source content hash |
| 原始证据定位 | 当前主要靠人工/Agent 写作过程 | PaperQA2 Text→Context；CiteGuard full-text search | **新增** page/section/span + span hash |
| citation attribution | 无独立 Agent | CiteGuard 主动 retrieval/read/select | **新增** citation attribution workflow |
| DOI/metadata 校验 | BibTeX 格式链存在，真实性门禁不完整 | DeltaScience/Crossref 等真实 lookup | **新增** deterministic metadata gate |
| claim-support | 要求引用真实资料，但未形成 claim→source checker | DeltaScience ClaimSupportAuditor | **改进**为独立 support gate |
| 无法验证状态 | 原则上可阻塞，但 citation 无统一状态 | DeltaScience `unverifiable/skipped` | **新增**一等状态 |
| stale external evidence | 18:04 已研究内部 artifact stale | PaperQA2 content identity + 本轮版本分析 | **新增** external source stale semantics |
| Writer 引用权限 | Writer 需要真实参考文献，但仍可自由写 BibTeX | 本轮分层方案 | **改进**为 only-CITABLE interface |
| citation verifier QA | 16:04 有通用 JudgeEval 思路 | 2026 citation guard 研究显示 verifier 严格度显著影响结果 | **新增** citation-specific regression/calibration |

整体结论：

```text
保持：现有事实链、数据/自主/、结果索引、BibTeX/TeX 主路线、SHA 支撑材料审计
改进：外部来源从“URL/参考文献条目”升级为 source snapshot + evidence span
新增：External Evidence Ledger、Citation Gate、source resolver、claim-evidence map、STALE/UNVERIFIABLE
替换：不建议替换现有论文/求解链；在其入口处增加验证层即可
暂不采用：完整 PaperQA2/DeltaScience 平台级依赖；优先移植 contract 与 gate 机制
```

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

#### P0-1：External Evidence Ledger Contract

建议先定义而不是立刻实现复杂 Agent。概念字段至少包括：

```json
{
  "source_id": "src-...",
  "source_type": "paper|official_rule|dataset|manual|web",
  "canonical_identifier": "doi/arxiv/url/...",
  "title": "...",
  "authors": [],
  "publication_or_version_date": "...",
  "metadata_sources": [],
  "retrieved_at": "...",
  "license_or_terms": "...",
  "snapshot_path": "...",
  "content_hash": "...",
  "resolver_version": "...",
  "status": "RESOLVED|SNAPSHOTTED|STALE|REJECTED"
}
```

#### P0-2：EvidenceSpan + Claim Mapping

每个关键公式、参数和学术论断不要只写 citation key，而应形成：

```json
{
  "evidence_id": "ev-...",
  "source_id": "src-...",
  "page_or_section": "...",
  "span_locator": "...",
  "span_hash": "...",
  "claim_ids": ["claim-..."],
  "relation": "SUPPORTS|PARTIAL|CONTRADICTS|UNVERIFIABLE",
  "verified_at": "...",
  "verifier_version": "..."
}
```

正式论文不必暴露这些内部字段，但系统必须能从一句关键 claim 回溯到真实证据位置。

#### P0-3：Citation Gate 放在 Writer 之前

建议硬规则：

```text
Writer 可使用 citation
⇔ source exists
∧ metadata verified
∧ snapshot fresh
∧ claim has usable evidence span
∧ support status ∈ {VERIFIED, APPROVED_PARTIAL}
```

未通过时 Writer 不得自行补参考文献。

#### P0-4：由 verified source records 构建 `reference.bib`

当前 `reference.bib` 与 `gmcm.bst` 可以保留，但未来 BibTeX 应成为**派生产物**：

```text
verified source registry
          ↓
     build_reference_bib
          ↓
     reference.bib
```

不要让 bibliography 反过来成为 source of truth。

### P1：值得实验

#### P1-1：Citation Regression Suite

构造 50–100 条小规模赛前用例，覆盖 fabricated、miscited、partial、stale、unverifiable、alternative citation 等情况。

比较：

```text
A: LLM-only Reviewer
B: identifier/metadata deterministic gate
C: B + exact-span/full-text evidence
D: C + calibrated semantic support verifier
```

#### P1-2：Full-text value ablation

CiteGuard 的论文显示 full-text/search-in-content 能显著改善 citation attribution。可在数学/运筹/工程文献上做自己的小 benchmark：

```text
abstract only
vs
abstract + full text span
```

重点测参数/公式类 claim，而不是普通背景句。

#### P1-3：Verifier calibration

给 citation verifier 保存：

```text
verifier_name
version
thresholds
calibration_dataset_hash
precision/recall/F1
last_calibrated_at
```

避免不同时间、不同 Judge 得到的“citation error rate”不可比较。

### P2：长期考虑

- 多 provider metadata corroboration；
- 网页 WARC/PDF immutable snapshot；
- source version diff；
- contradiction-aware evidence graph；
- 引用关系图：claim → formula → parameter → source → evidence span；
- 与 checkpoint/canonical manifest 联动，使 checkpoint 只引用当前 fresh evidence IDs。

### 不建议采用

- 一开始就引入完整文献 RAG 平台和数据库集群；
- 让 Citation Agent 同时负责求解、写作和最终审核；
- 只用 citation count 判断来源质量；
- 仅凭 LLM-as-a-Judge 判定“引用正确”；
- 对所有背景句执行昂贵 full-text verifier，影响赛时主任务。

## 14. 可形成的新 Skill / Agent

只提出设计，不创建正式代码。

### 1. `source-resolver`

输入 DOI/URL/title，输出 canonical source record + metadata conflicts。

### 2. `evidence-span-extractor`

从已 snapshot 的 PDF/网页中定位公式、参数、方法和结论的 exact span。

### 3. `citation-verifier`

执行 existence / metadata / freshness / claim-support 四层门禁。

### 4. `external-evidence-ledger`

维护 source/evidence/claim 状态、hash、version、审计时间。

### 5. `reference-bib-builder`

只根据 CITABLE source records 生成 BibTeX，禁止自由补 metadata。

其中真正值得近期落地的不是五个独立大 Agent，而是先做 **ledger contract + citation gate + BibTeX builder**，其他可以作为同一 Agent 的工具。

## 15. 与历史调研的去重检查

### 本轮新内容

此前没有研究：

- PaperQA2；
- CiteGuard；
- DeltaScience；
- source entity 与 source snapshot 的分离；
- bibliography metadata provider provenance；
- raw evidence span 与 LLM contextual summary 分离；
- citation attribution 的全文主动检索；
- source existence / metadata / claim-support 三层拆分；
- citation-specific `UNVERIFIABLE`；
- external source version drift；
- verified evidence → derived BibTeX 的单向接口；
- citation verifier calibration。

### 与 16:04 Reviewer 研究的差异

16:04 回答“如何校准数学模型 Reviewer”；本轮回答“Reviewer 的外部证据到底来自哪里、是否真实、是否支持 claim、是否仍然 fresh”。

### 与 18:04 provenance 研究的差异

18:04 是：

```text
本地 code/input/result artifact freshness
```

本轮是：

```text
external source identity/snapshot/span/claim freshness
```

两者后续可以统一接到 canonical manifest，但不能混成一套 ID。

### 与 19:07 Scheduler 的差异

19:07 解决算力与时间分配；本轮不讨论调度，而是解决外部知识进入事实链的可信边界。

本轮不存在通过改措辞重复旧结论的情况。

## 16. 下一轮推荐方向

建议下一轮从底层 P2 轮换回更直接的 P0/P1：

**Problem Specification / Constraint Compiler：把华为杯题面、附件说明、单位、输出格式、目标函数、硬约束和评分要求自动编译为机器可执行的 `Problem Contract + Proof Obligations`。**

重点可研究：

1. 题面 PDF → structured problem specification；
2. 每问 input/output/dependency/objective/constraint/unit schema；
3. 自然语言约束怎样变成 deterministic assertions；
4. Solver 如何声明“我满足了哪些 proof obligations”；
5. Reviewer 如何逐条检查题面约束，而不是只读论文；
6. 题面/附件版本变化如何自动 invalidate 下游求解；
7. 多 Agent 如何共享同一份 immutable Problem Contract。

这会直接连接当前已有 `求解/题面约束清单.md`，但需要寻找已有 scientific/coding agent 的 specification-driven 实现，而不是重复当前自然语言清单。

## 17. Sources

### A. 本轮已直接阅读源码 / 官方仓库文档

1. math_mode 当前仓库
   - https://github.com/shaxiaoguang123/math_mode
   - `README.md`
   - `AGENTS.md`
   - `CLAUDE.md`
   - `华为杯_求解规范/华为杯_求解规范.md`
   - `research/INDEX.md`
   - `research/2026-09-08/2026-09-08_18-04_artifact-ownership-promotion.md`
   - `research/2026-09-08/2026-09-08_19-07_resource-scheduler-pruning.md`

2. PaperQA2
   - Repository: https://github.com/Future-House/paper-qa
   - 固定阅读 commit: https://github.com/Future-House/paper-qa/tree/57e89f7223b0960d5ee5ea048c69e3c47e088572
   - README: https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/README.md
   - types: https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/types.py
   - agent tools: https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/agents/tools.py

3. CiteGuard
   - Repository: https://github.com/KathCYM/CiteGuard
   - 固定阅读 commit: https://github.com/KathCYM/CiteGuard/tree/391aee8bd3204c130c6fd0db2e515a8719db682f
   - README: https://github.com/KathCYM/CiteGuard/blob/391aee8bd3204c130c6fd0db2e515a8719db682f/README.md
   - agent: https://github.com/KathCYM/CiteGuard/blob/391aee8bd3204c130c6fd0db2e515a8719db682f/src/retriever/agent.py
   - run state/output: https://github.com/KathCYM/CiteGuard/blob/391aee8bd3204c130c6fd0db2e515a8719db682f/src/run_main.py

4. DeltaScience
   - Repository: https://github.com/boheling/deltasci
   - 固定阅读 commit: https://github.com/boheling/deltasci/tree/5b36015ead6934a67622b1777f11ce59dfe36a68
   - audit type system: https://github.com/boheling/deltasci/blob/5b36015ead6934a67622b1777f11ce59dfe36a68/src/deltasci/audit/base.py
   - claim support: https://github.com/boheling/deltasci/blob/5b36015ead6934a67622b1777f11ce59dfe36a68/src/deltasci/audit/support.py
   - citation auditors: https://github.com/boheling/deltasci/tree/5b36015ead6934a67622b1777f11ce59dfe36a68/src/deltasci/audit/citations

### B. 本轮阅读的官方论文 / 一手论文页面

5. PaperQA2 / WikiCrow
   - Skarlinski et al., *Language agents achieve superhuman synthesis of scientific knowledge*
   - arXiv:2409.13740
   - https://arxiv.org/abs/2409.13740

6. CiteGuard
   - Choi et al., *CiteGuard: Faithful Citation Attribution for LLMs via Retrieval-Augmented Validation*
   - arXiv:2510.17853
   - https://arxiv.org/abs/2510.17853
   - 本轮特别核对了 abstract 与当前正文中指标版本的差异；因此报告不把单一 abstract 字段当作唯一版本事实源。

7. Citation verifier calibration
   - Goo et al., *Evaluating and Guarding Citation Faithfulness in Agentic Scientific Synthesis*
   - arXiv:2607.20527
   - https://arxiv.org/abs/2607.20527

### C. 仅作为补充背景、未作为核心项目展开

8. BibAgent
   - Li et al., *BibAgent: An Agentic Framework for Traceable Miscitation Detection in Scientific Literature*
   - arXiv:2601.16993
   - https://arxiv.org/abs/2601.16993

### 证据边界声明

- 本轮对 PaperQA2、CiteGuard、DeltaScience 均实际读取了源码/官方仓库文档，不是只看搜索摘要。
- 本轮没有运行三个外部项目的完整 benchmark，因此没有把其 README/论文报告指标写成“本轮自行复现实验结果”。
- Stars 与更新时间来自本轮 GitHub API 查询，只代表本轮读取时状态。
- 对 claim-support 的建议是架构迁移，不声称 DeltaScience 当前 PubMed-oriented heuristic 已经适用于华为杯所有数学/工程来源。
- 对 CiteGuard 指标版本差异只记录本轮实际观察到的页面状态，不据此推断作者发布流程中的原因。