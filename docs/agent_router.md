# MathMode 项目入口（{{runtime}}）

<!-- Generated from docs/agent_router.md by tools/sync_agent_assets.py. -->

先读取 `docs/runtime_rules.md`。开发目标为 `goal.md`，Git 操作遵循
`git_rule.md`；仓库状态以当前 Git 命令为准。真实比赛在仓库外创建私有工作区，
原始题目、数据、官方模板和既有绘图资产保持完整。历史论文、示例和 fixture
不能作为当前赛题计算结果或最终验收证据。

阶段与证据入口：

| 工作 | 规则与执行入口 |
| --- | --- |
| 官方规则和输入 | `mathmode policy`、`mathmode init`；默认 policy 未核验，不能声称最终合规 |
| 题意、DAG、假设、模型 | `docs/contracts.md`、`docs/workflow_v2.md`；`mathmode validate` |
| 人工模型选择 | `human_gate` 等待已展示证据的终端响应；`human-decision`、`verify-human-decision`，详见工作流文档 |
| 真实执行和独立验证 | `mathmode run`、`verify-run`、`independent-validate`、`evidence` |
| 分阶段推进与恢复 | `mathmode workflow` 按真实证据观察/推进；`recover`、`recover-lock` 保留中断记录，详见工作流文档 |
| 冻结和过期检查 | `mathmode freeze`、`verify-freeze`、`thaw`、`refresh` |
| 参考资料与盲测 | `seal-baseline`、`seal-case-baseline`、`verify-baseline`、`admit-reference`、`retrieve-reference`、`verify-reference`；整题盲测与显式非盲测模式见工作流文档 |
| 普通科学结果图 | 完整读取绘图规范，调用 `{{skill_path}}/SKILL.md`，按需读取其 references/scripts/assets |
| 机理图和流程图 | 项目 Schematic/Flowchart Plan、真实结构审查、TikZ/XeLaTeX 门禁 |
| 论文与提交材料 | 论文规范、LaTeX 工具、视觉审计、支撑材料构建审计，见共享规则 |

上述命令均使用 `python -m mathmode <命令>`。实际接口以 `--help` 为准。
数值或结构审计通过不能替代科学语义、视觉和官方合规门禁；未实现的集成
不能由角色描述或 JSON 中手写的 PASS 代替。当前阶段见 `docs/audit/`。

禁止编造运行记录、实验数字、文献、人工决定和审查结论。独立验证者不能读取
求解源码或中间状态；作者不能自审通过。冻结数字只能从实测证据取得；变更上游
须显式解冻、重新执行、验证、冻结，并使旧图表、论文和附件过期。

按已授权范围持续推进；不得擅自推断额外审批要求。外部比赛提交和 Git 合并
需要用户明确授权；当前优化目标在 PR 与 CI 通过后停于 READY FOR REVIEW，不合并。

本入口由同一源生成；修改公共行为后运行
`python tools/sync_agent_assets.py`，提交前运行其 `--check`。
