# MathModel Agent Research

## 1. 本轮研究主题

科研型 Agent 的证据闭环（Evidence-first Scientific Workflow）与数学建模 Agent 架构设计。

## 2. 为什么选择这个主题

本轮为首次 research 基线建立。当前 math_mode 已具备华为杯论文生产、绘图规范、支撑材料审计和部分 Skill 化流程，但需要进一步研究如何把“生成论文工具”提升为“可靠建模 Agent 系统”。因此选择比普通论文生成更接近竞赛核心的问题：结果真实性、实验可追溯性和自动验证。

## 3. 搜索范围与关键词

关键词：
- AI Scientist workflow
- scientific agent verification
- evidence driven agent
- reproducible research agent
- mathematical modeling agent workflow
- experiment tracking agent

重点参考：
- Sakana AI AI Scientist 项目公开论文与仓库资料（机制层分析）
- math_mode 当前 README 与工程结构

## 4. 新发现项目

### 项目 1：The AI Scientist

- Repository：SakanaAI/AI-Scientist
- 类型：科研自动化 Agent 工作流
- 目标：自动完成研究假设生成、实验、论文草稿生成。
- 核心价值：不是单纯文本生成，而是将 idea、code、experiment、paper 串联。

## 5. 深入架构分析

该类系统核心思想：

```text
Research Idea
↓
Literature / Hypothesis
↓
Code Generation
↓
Experiment Execution
↓
Result Evaluation
↓
Paper Generation
```

对数学建模竞赛而言，关键迁移点不是自动写论文，而是：

```text
赛题理解
↓
模型候选生成
↓
代码实现
↓
真实运行
↓
结果验证
↓
论文表达
```

## 6. Agent / Skill 设计

可拆分角色：

- Problem Analyst：题目解析
- Model Designer：模型候选设计
- Coding Agent：代码生成
- Experiment Agent：运行实验
- Reviewer Agent：检查合理性
- Writer Agent：论文组织

当前 math_mode 已有论文生产和绘图 Skill，但实验验证角色仍需强化。

## 7. Workflow

推荐状态机：

```text
DRAFT
↓
MODEL_PLAN
↓
CODE_READY
↓
EXPERIMENT_RUN
↓
EVIDENCE_CHECK
↓
PAPER_READY
```

每个阶段保存 artifact，而不是只保存最终文本。

## 8. Code Execution / Tools

核心启发：数学建模 Agent 必须有真实执行环境。

需要记录：

- 输入数据 hash
- 代码版本
- 参数
- 随机种子
- 输出结果
- 图表文件
- 运行日志

## 9. QA / Reviewer / Verification

建议增加：

- 数值一致性检查
- 单位检查
- 模型假设检查
- 代码运行检查
- 图表来源检查

## 10. 值得借鉴的设计

A 可直接借鉴：

- artifact-first 工作流
- 实验记录作为一等公民
- reviewer 阶段独立存在

B 改造后采用：

- 科研 Agent workflow 改造成数学建模赛题 workflow。

C 对照实验：

- 有 Reviewer 与无 Reviewer 的论文质量差异。

D 不建议：

- 完全自动生成研究结论，不经过数学验证。

## 11. 存在的问题

AI Scientist 偏科研探索，不针对数学建模竞赛时间限制；自动化程度高但验证责任仍需要人工设计。

## 12. 与 math-mode 对比

|能力|math-mode|科研 Agent|差异|
|-|-|-|-|
|论文生成|已有 LaTeX/Word 链路|通常具备|math_mode 更偏竞赛规范|
|实验状态|部分存在|强调 experiment loop|需要加强|
|证据链|已有支撑材料审计|artifact 思路|可融合|
|Reviewer|已有审计工具|独立 Agent|建议增强|

## 13. 对 math-mode 的具体启发

### P0：建议近期加入

建立 Modeling Evidence Agent：负责检查模型结果是否来自真实运行。

### P1：值得实验

增加 Model Debate Agent：多个模型路线竞争，并由 Reviewer 评分。

### P2：长期考虑

建立长期实验 Memory 和 benchmark。

### 不建议采用

完全无人监督论文生成。

## 14. 可形成的新 Skill / Agent

- experiment-manager-agent
- modeling-reviewer-agent
- evidence-verification-agent
- model-debate-agent

仅作为设计建议。

## 15. 与历史调研的去重检查

research 初始为空，本轮建立基线。未发现历史重复。

## 16. 下一轮推荐方向

研究数学建模中的 Model Selection Agent 和多模型竞争机制。

## 17. Sources

- SakanaAI/AI-Scientist GitHub repository（机制参考，需进一步源码级阅读）
- math_mode README.md（已阅读）

区分：math_mode 为已读取仓库资料；AI Scientist 为公开项目机制研究对象，后续需继续源码深读。
