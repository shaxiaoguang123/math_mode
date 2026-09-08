# MathModel Agent Research Index

| 时间 | 主题 | 项目/机制 | 核心发现 | 对 math_mode 的价值 |
|---|---|---|---|---|
| 2026-09-08 14:00 | 科研型 Agent 工作流与证据闭环 | AI Scientist 类工作流机制分析 | 首轮建立 evidence-first、实验状态和验证闭环研究基线 | 为后续 Agent 架构调研提供去重索引 |
| 2026-09-08 15:06 | 赛时模型选择：搜索树、并行实验与可执行评测环境 | WecoAI/aideml；sjtu-sai-agents/ML-Master；MLE-Dojo/MLE-Dojo；openai/mle-bench（评测参考） | 代码级确认候选树与原子改进、MCTS/UCT 并行搜索、预算感知、受限执行与环境历史；单次最佳分数不足，应加入重复验证与可比性门禁 | 建议新增实验账本、model-search-agent、experiment-manager-agent、search-budget-controller 和多目标 Score Card，并接入现有结果索引/支撑材料审计 |
| 2026-09-08 16:04 | 数学模型 Reviewer / Judge：可执行、可校准、按证据拆解的验证系统 | OpenAI PaperBench；SakanaAI/AI-Scientist reviewer（代码级重访）；OSU-NLP-Group/ScienceAgentBench | PaperBench 将实现/执行/结果拆成不同 criterion，并以 fresh reproduction、evidence localization、hard gate 和 JudgeEval 校准 Reviewer；AI Scientist 提供 ensemble/meta-review/reflection 的软评审机制；ScienceAgentBench 2026 verified release 证明 evaluator false negative 必须版本化和回归测试 | 建议在 Solver 与论文证据层之间新增 Validation Contract：hierarchical rubric + deterministic hard gates + independent recompute + soft meta-review + reviewer regression/JudgeEval；保持现有量纲/守恒/独立验证规则，但把它们编译成机器 checker |
