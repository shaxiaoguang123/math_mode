# 华为杯论文生成与验收工具

T03 已增加比赛策略层：`competition_policy.json` 区分 official 与 project_recommendations；随仓库提供的配置为 **unverified**，不能通过官方合规门禁。TeX/DOCX 构建与审计可传 `--policy`，身份封面另传 `--cover-tex`。配置与迁移说明见 `docs/migration_v1_to_v2.md`（项目根目录）。

本目录提供 LaTeX-first 论文生产链和可选 Word 派生链。绘图视觉、图型选择、Figure/Schematic/Flowchart Plan、三维/柱状/饼图限制和质量检查统一由 `华为杯_求解规范/华为杯_绘图规范.md` 管理；它是项目内绘图规则的唯一详细来源。`求解/求解计划.md` 保存解释性计划，`求解/视觉计划.json` 按 `视觉计划.schema.json` 保存机器可审计合同。

`视觉计划.schema.json` 供编辑器或外部 JSON Schema 工具执行完整结构校验；项目自带 `audit_visual_plan.py` 仅使用 Python 标准库，强制检查证据覆盖、图量例外、引用关系、渲染产物和论文接入等语义门禁，不要求额外安装 `jsonschema`。正式流程必须运行审计器，外部 schema 校验不能替代它。

提交附件另由 `华为杯_求解规范/支撑材料清单.schema.json`、`华为杯_求解规范/tools/init_supporting_materials.py`、`华为杯_求解规范/tools/build_supporting_materials.py` 和 `华为杯_求解规范/tools/audit_supporting_materials.py` 管理。它们把每问完整源码与实际运行记录、自主搜集数据及溯源、正文未完整展示的补充图表、题面指定官方输出统一接入 `提交附件/readme.md` 和 SHA-256 清单；schema 校验同样不能替代语义审计。

## academic-figure-skill 集成

项目内完整 skill 位于 `.agents/skills/academic-figure-skill/`（Codex）和 `.claude/skills/academic-figure-skill/`（Claude Code），两份目录必须保持文件列表和内容一致。普通科学结果图请求触发对应 skill，入口为大小写敏感的 `SKILL.md`；运行时按需读取 `references/`、`scripts/` 和 `assets/figures/`，优先使用匹配资产并输出矢量图、PNG 预览、统计报告和 QA 报告。普通结果图的标题、坐标轴、图例、注释和统计解释默认使用中文；`scripts/chinese_fonts.py` 负责实际字体检测和烟雾渲染，缺字、乱码或 `fig.canvas.draw()`/Cairo 渲染失败时状态保持未完成。项目 Figure Plan 负责把科学问题、真实结果文件、字段、archetype、Panel/布局、资产目录、运行模式、脚本、输出和论文引用接起来。

机理/几何示意图由 `Schematic Plan` + TikZ/XeLaTeX 负责；流程图、总体技术路线图和模型结构图由 `Flowchart Plan` + TikZ/XeLaTeX 负责。skill 的 schematic-led 只管理组合层级，不能替代元素/节点/箭头真实性门禁。调用顺序固定为：证据审查 → Figure/Schematic/Flowchart Plan → `audit_visual_plan.py --stage plan` → 真实计算落盘 → 普通结果图调用 academic-figure-skill，示意/流程图调用 TikZ → 实际渲染与 QA → `--stage render` → 正式图片目录和结果索引 → 通过后接入论文。

不强制触发 skill 的任务包括交互式 dashboard、探索性可视化、数学函数图、PowerPoint/Illustrator/Figma 设计、纯代码调试、统计检验本身和数据清洗本身。

1. `tools/build_latex.py`：根据 TeX-only manifest 生成唯一主入口 `论文/论文.tex`，章节通过 `\input{}` 组合；
2. `tools/audit_tex.py`：检查 `.tex` 输入链、Markdown 残留、环境/花括号、图片、匿名、标签/引用、Unicode 数学字符和显式斜体；
3. `论文.tex`：匿名 LaTeX 生产骨架，保留 `gmcmthesis.cls + gmcm.bst + figures/`，使用 A4、四边 25 mm、摘要页起始页码 1、摘要可自然延续至第 2 页、正文小四宋体、无页眉和页脚居中页码；
4. `tools/audit_paper.py`：检查最终 PDF 页数、摘要/正文边界、参考文献/附录边界和各章页数；
5. `tools/build_docx.py`：从同一批 `.tex` 章节生成可选 DOCX 派生物，明确拒绝 Markdown 和旧 inline content 字段；
6. `tools/audit_docx.py`、`tools/render_word.vbs`：仅用于可选 Word 派生输出的审计与渲染；
7. `agent_manifest.schema.json`：TeX-only 智能体输入协议。
8. `华为杯_求解规范/tools/build_supporting_materials.py`：从 `求解/支撑材料清单.json` 重建 `提交附件/支撑材料/`，刷新 `readme.md`、构建清单和 SHA-256；不改写官方输出目录。
9. `华为杯_求解规范/tools/audit_supporting_materials.py`：执行逐问和最终支撑材料门禁，检查源码完整性声明、运行记录、外部数据溯源、补充图表、官方输出、README 覆盖和哈希漂移。

## 推荐工作流

```text
原始数据 → 求解代码 → 结构化结果
  → 读取华为杯_求解规范/华为杯_绘图规范.md
  → Figure/Schematic/Flowchart Plan/视觉编码表 → audit_visual_plan.py --stage plan
  → 绘图脚本只读结果并完成渲染检查 → audit_visual_plan.py --stage render
  → 每问更新支撑材料清单 → build_supporting_materials.py → --stage question 审计
  → 求解/问题X/图片/ → 按 agent_manifest.schema.json 写入论文/章节内容/*.tex
  → tools/build_latex.py 生成论文/论文.tex
  → audit_visual_plan.py --stage paper
  → tools/audit_tex.py
  → XeLaTeX 双遍编译
  → tools/audit_paper.py
  → 重审正文未完整展示的长表/批量图 → 重建提交附件 → --stage final 审计
  → PDF 字体、日志和页面视觉抽检
  → 只修改真实内容、图表布局和章节拆分，不修改字号/页边距/行距来凑页数
```

最终论文正文禁止以 Markdown `.md` 作为章节源文件。`.md` 只用于求解计划、结果索引、AI 记录、内部审计和 `legacy_markdown/` 归档。`论文/论文.tex` 是唯一主入口，`论文/章节内容/*.tex` 是唯一正式论文 source of truth。论文规范只处理图像路径、尺寸、图题、标签、正文引用、PDF 缩放和裁切；不得在论文规范中另建颜色或图型规则。

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

编译日志不得包含致命错误、字体缺字、未定义引用或不可接受的 `Overfull \hbox`。摘要页数、目录是否生成及深度从 policy 读取；启用目录时置于摘要后、正文前。正文页数从首个正文标题计至参考文献或附录之前，目录不计入。

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

`page_targets.json` 保存历史章节窗口与正文 45 页经验提醒，均不构成官方硬要求。实际页数限制从已核验的 `competition_policy.json` 读取；页数不能替代证据完整性，也不得用空白、重复内容、虚构实验或缩放版式凑页数。

## 当前演练结果

历史示例只用于工具链演练；其页数既不是赛题结果，也不能证明当前流程通过。当前交付以真实运行、独立验证、冻结证据、当届策略和最终渲染审计为准。

## 证据链与科研图工作流

求解计划中的每个问题应同时维护 `Evidence Matrix`、`Figure Plan` 和 `视觉计划.json`；机理/几何图按需建立 `Schematic Plan`，多阶段/迭代/数据流结构按需建立 `Flowchart Plan`。Evidence Matrix 每行必须填写适用性、原因、数据形态、`figure / schematic / table / text / N/A`、结果路径和关联 ID。Figure Plan 在代码前反向定义结果字段、扫描/重复实验、Panel、archetype、hero/layout、图型、视觉 token、输出、统计和 QA 路径。论文阶段只引用 `qa_pass` 且通过 render/paper 两阶段视觉审计的正式图。

任何创建、修改、审查或解释 Figure 前，Codex 和 Claude Code 都必须读取绘图规范；绘图失败时先修复字体、布局、编码或数据源，不得把未通过检查的图写入论文，也不得为了 经验页数机械增加图数。

生成、修改或审查流程图前，还必须读取绘图规范和论文章节规范，完成“题面/附件 → 真实模型结构 → 节点/箭头真实性审核 → 结构类型 → Flowchart Plan → TikZ/XeLaTeX → 视觉与版心审计”的顺序。流程图不是固定模板或页数填充；A/B/C 代码仅为历史示例，不能复制为生产图。

### 绘图规则迁移与冲突处理

- 原 `华为杯_求解规范.md` 的大段颜色、图型、透明度和布局细节已收敛为接口摘要；详细规则统一迁移到 `华为杯_求解规范/华为杯_绘图规范.md`。
- 旧的“低饱和度/克制配色”与“禁止所有多色渐变”类表述不再作为项目规则；当前规则允许有数据语义的高亮度离散色和连续渐变，但禁止无语义彩虹色，并要求灰度可辨。
- 柱状图不再是默认图型；饼图不能单独承担核心证据；三维图只有在真实三变量关系或空间/轨迹含义存在时才使用，不得伪造，缺少真实三维关系时使用二维替代并记录原因。
- 论文规范中的 A/B/C 流程图代码仅保留为历史示例，不能作为固定视觉模板；论文规范只负责 LaTeX 接入和 PDF 可读性。
- `gmcmthesis.cls`、`gmcm-title.sty`、`gmcm.bst`、官方 `figures/` 和 Word 模板保持只读，绘图迁移不改变 LaTeX-first、XeLaTeX 或证据门禁。

默认采用出版级科研多面板表达：简单问题通常至少 2 个 Figure，标准/复杂问题通常 3--6 个，并要求主结果图与独立验证图；四问型标准/复杂赛题组合级通常审查 15--25 个非冗余 Figure。低于阈值允许真实例外，但必须登记理由和替代证据。布局按信息结构使用对称网格或带 hero panel 的非规则组合，不能让全篇机械重复 `1×2`；图数和花哨程度都不能替代真实证据。

---

## 项目使用说明（华为杯自动化论文 skill）

### 1. 项目是什么

本项目是一个面向华为杯数学建模竞赛的自动化论文辅助项目，提供“题目/数据审计 → 建模求解 → 结果验证 → 科研绘图 → LaTeX 论文 → PDF 审计”的可追溯工作流。日常使用时把它称作“华为杯自动化论文 skill”即可，但它本质上是一个项目文件夹，不能脱离其中的规范、工具和结果文件单独使用。

项目支持的自动化 harness 包括：

- **Codex**：读取根目录 `AGENTS.md`，适合在项目目录内执行命令、编写代码、运行审计和维护结果链；
- **Claude Code（CC）**：读取根目录 `CLAUDE.md`，可执行同一项目流程。两套规则应保持一致，具体运行时以当前 harness 能实际读取到的规则文件为准。

使用任一 harness 时，都应把工作目录设为本项目根目录（本机示例为 `D:\jsw_DeskTop\huawei_skillsv2`，换电脑后以实际路径为准），不要只打开某个子目录。模板源文件和规范文件默认只读，赛题数据和生成结果应保持事实链可追溯。

### 2. 赛题和数据放置位置

收到新赛题后，建议为该赛题新建独立工作目录（或先确认现有目录中没有其他赛题产物），再按以下约定放置文件：

```text
题目/
  题目正文.pdf、题目正文.docx、附件说明.txt 等（题面和官方规则，只读）
数据/
  原始/          原始 Excel、CSV、TXT、图片、压缩包等（只读）
  中间/          解压副本、清洗数据、转换后的中间文件
  自主/          非官方、自主查阅/整理/爬取并实际用于建模的数据、来源记录和采集脚本
求解/
  问题一/问题一.py、结果/、图片/
  问题二/问题二.py、结果/、图片/
  支撑材料清单.json
  ...
提交附件/
  最终提交文件/   题面要求的 Excel、TXT、CSV 等官方输出
  支撑材料/       工具生成的逐问源码、运行验证、补充图表和自主数据快照
  readme.md       所有文件及作用的目录
  _支撑材料构建清单.json、SHA256SUMS.txt
论文/             论文.tex、章节内容/*.tex、验收输出/
```

> **使用者应将赛题正文放至项目文件 `题目/` 中，官方附件数据放在 `数据/原始/` 中；如用 Codex，请授予项目所需的文件与命令权限，并在 goal 模式下输入一键启动提示词。**
## 3. 本机必备软件

基础环境建议使用 Windows + PowerShell，并准备：

1. **Python 3.10 或更高版本**，建议为本项目建立 `.venv`；至少用于运行求解代码、`build_latex.py`、`audit_tex.py`、`audit_paper.py` 和 `audit_visual_plan.py`；
2. **TeX Live（含 XeLaTeX、TikZ、BibTeX）**，论文主链路必须使用 `xelatex`；
3. **系统字体 `STXinwei`**，用于华为杯封面标题组件 `gmcm-title.sty`。缺字体时应报告并安装，不要静默替换；
4. 一个可用的 **Codex 或 Claude Code** harness，并允许其在项目目录执行 Python、XeLaTeX 和审计命令；
5. 题目所需的 Python 科学计算/绘图库（常见为 `numpy`、`pandas`、`scipy`、`matplotlib`、`scikit-learn` 等）按实际赛题安装，不要无必要安装大型依赖。

可选组件：Microsoft Word（用于 DOCX 派生和 `render_word.vbs`）、R/Rscript（题目明确需要 R 时）、PDF 查看/渲染工具（如 `pdfinfo`、PyMuPDF 或 `pdftoppm`）。项目当前未提供统一的 `requirements.txt`，依赖应记录在 `求解/环境与依赖.md`。

环境检查示例：

```powershell
python --version
xelatex --version
where.exe python
where.exe xelatex
```

### 4. 一键启动提示词

在项目根目录启动 Codex 或 Claude Code 后，可直接粘贴以下提示词。它会要求 agent 遵守现有门禁，并在缺少关键材料时停止，而不是猜测结果：

```text
请在当前项目根目录执行“华为杯自动化论文”全流程。先读取并遵守 AGENTS.md（Claude Code 同时遵守 CLAUDE.md），再完整读取华为杯_求解规范/华为杯_求解规范.md、华为杯_求解规范/华为杯_绘图规范.md，以及论文阶段需要的论文规范、README、schema 和 page_targets.json。

请按 FULL AUTO / ONE-SHOT MODE 工作：
1. 审计题目/和数据/，生成求解/环境与依赖.md、题面约束清单.md、数据审计.md；
2. 为每个问题建立求解计划、Evidence Matrix、Figure/Schematic/Flowchart Plan 和求解/视觉计划.json，并先运行 audit_visual_plan.py --stage plan；
3. 初始化求解/支撑材料清单.json；逐题真实运行代码，保存结构化结果、独立验证、敏感性/稳健性分析、图片和结果索引，不得伪造或凭感觉补数；
4. 普通科研结果图必须调用 .agents/skills/academic-figure-skill/SKILL.md（Claude Code 使用对应 .claude/skills/academic-figure-skill/），流程图和示意图按规范使用 TikZ/XeLaTeX；
5. 每问完成时将完整可运行源码、实际运行验证、自主查阅/整理/爬取数据及溯源、正文未完整展示的补充图表写入支撑材料清单，运行 build_supporting_materials.py 和 audit_supporting_materials.py --stage question；
6. 通过 render 审计后，以论文/章节内容/*.tex 为唯一正文源，生成论文/论文.tex，执行 paper 视觉审计、audit_tex.py、XeLaTeX 双遍和 audit_paper.py；
7. 论文定稿后重审补充图表，重建提交附件，运行 audit_supporting_materials.py --stage final；核对摘要、正文、图表、结果索引、官方输出和支撑材料数字完全一致，并报告每个门禁的证据路径。

不要等待我在阶段之间确认普通技术选择。只有关键材料缺失/损坏、题意或单位无法判定、必需软件不可用、硬约束无法满足，或继续计算会制造虚假结果时才停止，并说明精确错误、已尝试修复、现有产物和最小解决条件。
```

### 5. 图表瑕疵修复提示词

生成图表后如出现乱码、字体缺失、标签重叠、图例遮挡、裁切、空白、坐标单位错误、颜色不可辨或图与结论不一致，可把图片路径、脚本路径和审计报告一起交给 Codex/CC，并粘贴：

```text
请修复这张科研图，不要只做表面美化。先读取华为杯_求解规范/华为杯_绘图规范.md 和对应 academic-figure-skill/SKILL.md，再检查原始结构化结果、Figure Plan、绘图脚本及 QA 报告。

图片：<图片路径>
脚本：<脚本路径>
问题描述：<乱码/重叠/裁切/单位/图例/颜色/数据不一致等>

请定位根因并修改绘图代码或数据接口；不要手工篡改图片，不要编造数据，不要用未验证的占位值。重新运行脚本和字体检测，输出 PDF/SVG/PNG、统计报告和 QA 报告，更新求解/视觉计划.json 与求解/结果索引.md，并运行 audit_visual_plan.py --stage render。只有审计通过后才允许重新接入论文，同时说明修改前后差异。
```

若问题发生在 PDF 排版，可追加：

```text
请继续检查论文 PDF 中的图表越界、浮动位置、图题/label、正文引用和字体。保持字号、页边距和行距规范不变，只调整真实内容或合法布局；修复后重新执行 audit_tex.py、XeLaTeX 双遍和 audit_paper.py。
```

### 6. 结果、验收与安全边界

最终交付至少应能从原始题目/数据追溯到代码、结构化结果、独立验证、结果索引、正式图片、论文 PDF、官方输出和支撑材料。`提交附件/readme.md` 必须列出包内全部文件及作用；每问源码、运行记录、自主数据溯源、补充图表和 SHA-256 必须通过 final 审计。示例 PDF、模板示例和历史演练产物仅用于测试工具链，不能当作赛题答案或验收证据。未经用户明确授权，agent 不进行竞赛系统登录、外部提交或代替参赛者作出诚信声明。

### 7. 免责声明

本项目及其生成的代码、模型、图表、文字、LaTeX、PDF 和 DOCX **仅供学习、研究、流程演示和写作辅助参考**，不保证正确性、完整性、适用性或符合当届竞赛的全部要求。生成的竞赛论文不得未经人工复核直接提交，也不得将其视为官方答案、专家意见或获奖保证。使用者必须自行核验题意、数据、单位、公式、程序、引用、图表、格式和学术诚信要求，并对最终提交材料及其后果承担全部责任。不得使用本项目伪造数据、抄袭他人成果、规避查重/反作弊或违反竞赛和学校规定。

### 8. 版权与署名

“华为杯自动化论文 skill”项目归属：**小红书 ID：小红薯65F5F4DC；小红书号：49469317685**。未经权利人许可，不得移除本版权声明、冒用项目作者身份或将项目整体包装为他人原创。项目中引用的华为杯模板、字体、第三方库、示例论文和其他素材仍归其原权利人所有，使用时应遵守相应许可证、竞赛规则和版权要求。

本节是面向使用者的补充说明，不替换或降低本 README 前文、`AGENTS.md`、`CLAUDE.md`、`华为杯_求解规范/` 和 `华为杯_论文规范模板/` 中的任何技术门禁；发生冲突时，以项目总控文件规定的权威顺序为准。
