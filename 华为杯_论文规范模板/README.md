# 华为杯论文生成与验收工具

本目录提供 LaTeX-first 论文生产链和可选 Word 派生链：

1. `tools/build_latex.py`：根据 TeX-only manifest 生成唯一主入口 `论文/论文.tex`，章节通过 `\input{}` 组合；
2. `tools/audit_tex.py`：检查 `.tex` 输入链、三级目录命令/顺序及编译后的 `.toc`、Markdown 残留、环境/花括号、图片、匿名、标签/引用、Unicode 数学字符和显式斜体；
3. `论文.tex`：匿名 LaTeX 生产骨架，保留 `gmcmthesis.cls + gmcm.bst + figures/`，使用 A4、四边 25 mm、摘要页起始页码 1、摘要可自然延续至第 2 页、正文小四宋体、无页眉和页脚居中页码；
4. `tools/audit_paper.py`：检查最终 PDF 页数、摘要/正文边界、参考文献/附录边界和各章页数；
5. `tools/build_docx.py`：从同一批 `.tex` 章节生成可选 DOCX 派生物，明确拒绝 Markdown 和旧 inline content 字段；
6. `tools/audit_docx.py`、`tools/render_word.vbs`：审计动态 TOC 字段、标题大纲级别、格式和可选 Word 派生输出的渲染；
7. `agent_manifest.schema.json`：TeX-only 智能体输入协议。

求解阶段另使用 `华为杯_求解规范/视觉计划.schema.json`、`tools/init_visual_plan.py` 和 `tools/audit_visual_plan.py` 管理视觉证据。它们不并入论文 manifest，避免把求解/绘图状态混入 TeX 章节协议。

支撑材料使用独立的 `华为杯_求解规范/支撑材料清单.schema.json` 和 `华为杯_求解规范/tools/init_supporting_materials.py`、`华为杯_求解规范/tools/build_supporting_materials.py`、`华为杯_求解规范/tools/audit_supporting_materials.py`。论文 manifest 仍只管理 TeX；论文定稿后由支撑材料清单接收正文未完整展示的长表/批量图，并与每问完整源码、自主数据溯源、官方输出共同生成 `提交附件/readme.md`。

## 推荐工作流

```text
求解结果/图片/文献
  → 按 agent_manifest.schema.json 写入论文/章节内容/*.tex
  → tools/build_latex.py 生成论文/论文.tex
  → 华为杯_求解规范/tools/audit_visual_plan.py --stage paper
  → tools/audit_tex.py
  → XeLaTeX 双遍编译
  → tools/audit_paper.py
  → PDF 字体、日志和页面视觉抽检
  → 重审补充图表 → build_supporting_materials.py → audit_supporting_materials.py --stage final
  → 只修改真实内容、图表布局和章节拆分，不修改字号/页边距/行距来凑页数
```

最终论文正文禁止以 Markdown `.md` 作为章节源文件。`.md` 只用于求解计划、结果索引、AI 记录、内部审计和 `legacy_markdown/` 归档。`论文/论文.tex` 是唯一主入口，`论文/章节内容/*.tex` 是唯一正式论文 source of truth。

## LaTeX 主路线

封面赛事标题由 `gmcm-title.sty` 统一生成，调用 `\GMCMContestTitle{届次中文数字}`。该组件使用 XeLaTeX 和系统字体 `STXinwei`；正常情况下不要修改此文件，字体缺失时应报告错误。

```powershell
python 华为杯_论文规范模板\tools\build_latex.py --manifest 论文\论文输入.json --output 论文\论文.tex --template-dir 华为杯_论文规范模板 --manifest-out 论文\论文.inputs.json
python 华为杯_求解规范\tools\audit_visual_plan.py --plan 求解\视觉计划.json --stage paper --project-root . --main-tex 论文\论文.tex --report 论文\验收输出\视觉计划.paper.audit.json
python 华为杯_论文规范模板\tools\audit_tex.py --manifest 论文\论文输入.json --main 论文\论文.tex --report 论文\验收输出\论文.tex.audit.json
cd 论文
xelatex -interaction=nonstopmode -halt-on-error -file-line-error 论文.tex
xelatex -interaction=nonstopmode -halt-on-error -file-line-error 论文.tex
cd ..
python 华为杯_论文规范模板\tools\audit_paper.py --pdf 论文\论文.pdf --source 论文\论文.tex --targets 华为杯_论文规范模板\page_targets.json --report 论文\验收输出\论文.audit.json
```

编译日志不得包含致命错误、字体缺字、未定义引用或不可接受的 `Overfull \hbox`。摘要一般不超过 2 页，可自然延续至第 2 页；关键词后由工具链自动生成三级动态目录，正文从目录结束后的下一页开始。总页数不等于正文页数；正文到参考文献标题前结束，附录不计入。

## 可选 Word 派生路线

```powershell
python 华为杯_论文规范模板\tools\build_docx.py --template 第二十三届研赛论文Word标准模板.docx --input 论文\论文输入.json --output 论文\验收输出\论文.docx --manifest-out 论文\验收输出\论文.chapters.json
python 华为杯_论文规范模板\tools\audit_docx.py --docx 论文\验收输出\论文.docx --report 论文\验收输出\论文.docx.audit.json
cscript //nologo 华为杯_论文规范模板\tools\render_word.vbs 论文\验收输出\论文.docx 论文\验收输出\论文.word.pdf 论文\验收输出\论文.word.json
```

Word 输出只能从 TeX-only manifest 和 `.tex` 章节派生，不能手工修改后反向覆盖 `.tex`。不要以 `docProps/app.xml` 中保存的页数作为验收结果。

## 章节页数策略

`tools/calibrate_page_targets.py` 根据两份优秀论文建立**角色区间**，而不是把样例页数硬复制到每篇文章：

```powershell
python tools\calibrate_page_targets.py --baseline 章节页数基线.json --output page_targets.json
```

默认硬门槛：正文（不含摘要、参考文献、附录）至少 45 页。问题章节区间是异常检测窗口；问题之间允许明显不均衡。正文不足时，智能体必须补充真实的模型推导、数据处理、结果分析和验证，不能通过缩小字体、页边距、行距或堆砌虚假内容达标。

补页按“问题章内证据恢复”执行：先补真实的阻断互验、误差结构、参数可辨识性、敏感性/鲁棒性、场景/边界，再补与主入口一致的伪代码和复杂度，随后把逐折分布、设备/场景差异、模型胜负和特征响应转为已审计多面板 Figure。全量逐折表、特征字典、文件行数、哈希、序列化和交付完整性进入附录、结果索引或支撑材料，不得单独撑起正文后置章节。流程图只有在每问确有独立数据流、循环或验证闭环时增加，不执行机械的“每问一图”。

每轮 PDF 除页数外还要生成逐页联系表，检查图表是否全部集中在前半段、正文后 1/3 是否出现连续稀疏页以及短表是否造成异常大空白。总页数达标但后段证据稀薄仍需重排；不能用装饰性/无意义图、同一结果换图型、放大图表或强制分页消除稀疏告警。

## 当前演练结果

历史 Word 示例 PDF 为 4 页、正文 1 页，是页数门槛的故意负例。任何示例产物都不是赛题答案或通过证据。真实论文必须以 XeLaTeX 最终 PDF 通过正文 45 页硬门槛后才交付。

## 证据链与科研图工作流

求解计划中的每个问题应同时维护 `Evidence Matrix`、`Figure Plan` 和 `求解/视觉计划.json`。Evidence Matrix 每行填写适用性、原因、数据形态、`figure / schematic / table / text / N/A`、结果路径和关联 ID；Figure Plan 在代码前反向声明结果字段、扫描/重复实验、Panel、archetype、hero/layout、输出、统计/QA 路径。机理/几何示意图另建 Schematic Plan，算法/数据流结构另建 Flowchart Plan。论文阶段只引用 `qa_pass` 且通过视觉计划 render/paper 审计的正式图。

默认采用出版级科研多面板表达：简单问题通常至少 2 个 Figure，标准/复杂问题通常 3--6 个，并要求主结果图与独立验证图；四问型标准/复杂赛题组合级通常审查 15--25 个非冗余 Figure。低于阈值允许真实例外，但必须登记原因和替代证据。布局按信息结构选择对称网格或带 hero panel 的非规则组合，不能让全篇机械重复同一种 `1×2`。
