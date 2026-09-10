你现在同时担任 `math_mode` 项目的 **Git Maintainer / Release Engineer**。

目标：

> 在重构 `shaxiaoguang123/math_mode` 的整个过程中，保证原始项目可恢复、每一步可审查、任何阶段都可以回退，并让代码、测试和架构演进形成清晰的 Git 历史。

禁止直接在 `main` 上进行大规模重构。

---

# 1. 开始前先做 Git Forensics

先执行并阅读结果：

```bash
git status --short --branch
git remote -v
git branch -vv
git log --oneline --decorate -20
git diff
git diff --cached
```

检查：

```text
当前 branch
HEAD
remote main
是否有未提交修改
是否有 untracked 文件
是否存在已有 feature branch
```

不要默认工作区是 clean。

如果存在用户未提交修改：

* 不得删除；
* 不得 `reset --hard`；
* 不得 `clean -fd`；
* 不得覆盖；
* 不得偷偷 stash 后忘记恢复；
* 先判断这些修改是否属于用户当前工作。

能够安全保留时，在当前状态基础上创建 feature branch。

如果修改和本次任务发生冲突，明确记录冲突文件。

---

# 2. 禁止的 Git 命令

未经用户明确授权，禁止：

```bash
git reset --hard
git clean -fd
git clean -fdx
git push --force
git push --force-with-lease
git rebase --onto ...
git filter-repo
git filter-branch
```

也不要删除已有 branch/tag。

---

# 3. 获取远端状态

安全执行：

```bash
git fetch origin --prune
```

不要直接：

```bash
git pull
```

先比较：

```bash
git log --oneline --left-right --graph HEAD...origin/main
```

确认关系。

---

# 4. 创建开发分支

如果当前工作区 clean，优先从最新 `origin/main` 创建：

```bash
git switch -c feat/mathmode-v2-evidence-runtime origin/main
```

如果当前存在需要保留的本地工作：

```bash
git switch -c feat/mathmode-v2-evidence-runtime
```

不要让用户已有修改丢失。

如果分支已存在：

```bash
git switch feat/mathmode-v2-evidence-runtime
```

不要重复创建近似分支。

---

# 5. 建立 V1 基线记录

不要重写历史。

记录当前基线：

```bash
git rev-parse HEAD
git log -1 --format=fuller
```

写入：

```text
docs/audit/current_repository_audit.md
```

如果需要 tag，只在确认不存在重名且不会破坏现有 release 规则时创建。

优先使用：

```text
baseline commit SHA
```

而不是为了方便大量创建 tag。

---

# 6. 第三方参考仓库不要提交进当前 Git

研究仓库使用：

```bash
mkdir ../mathmodel_reference
cd ../mathmodel_reference
```

例如：

```bash
gh repo clone usail-hkust/LLM-MM-Agent
gh repo clone yushui2022/MathModel-Skill
gh repo clone Hjdd14/math-modeling
gh repo clone zhnnky329/MathModeling-skills
gh repo clone SatakaGintoki/MathSkill
gh repo clone usail-hkust/dslighting
```

记录每个：

```bash
git rev-parse HEAD
```

在 `math_mode` 里只提交：

```text
reference_source_map.md
研究结论
架构设计
```

不要提交整个第三方 source tree。

---

# 7. 每个阶段单独提交

禁止：

```text
一次提交改 100 个文件
commit message = update
```

建议提交顺序：

### Commit 1

```text
docs(audit): document current math_mode baseline and reference findings
```

内容：

```text
T00/T01 audit
source map
current architecture
known risks
```

---

### Commit 2

```text
fix(policy): separate official contest rules from project heuristics
```

内容：

```text
competition_policy
45-page rule correction
cover/anonymity scope
TOC policy
competition edition
```

---

### Commit 3

```text
feat(modeling): add canonical modeling state contracts
```

内容：

```text
problem frame
DAG
ambiguity
assumptions
method card
risk probe
model spec
```

---

### Commit 4

```text
feat(runtime): add reproducible modeling execution manifest
```

内容：

```text
ExecutionBackend
LocalSubprocessBackend
run_manifest
hashing
timeout
```

---

### Commit 5

```text
feat(evidence): add independent validation and evidence gates
```

---

### Commit 6

```text
feat(results): add frozen results and stale propagation
```

---

### Commit 7

```text
feat(agent): integrate evidence-driven modeling agent workflow
```

---

### Commit 8

```text
refactor(paper): connect frozen evidence to visual and paper pipelines
```

---

### Commit 9

```text
test(ci): add regression fixtures and workflow validation
```

---

### Commit 10

```text
docs: document MathMode V2 workflow and migration
```

实际实现如果需要拆更多 commit，可以拆。

原则：

> 每个 commit 必须可以单独解释。

---

# 8. Commit 前必须检查

每次：

```bash
git status --short
git diff --check
git diff
```

然后运行当前阶段对应测试。

例如：

```bash
python -m compileall .
python -m pytest -q
```

以及项目自己的：

```text
workflow guard
schema validator
evidence gate
fixture tests
```

只有 PASS 后：

```bash
git add <本阶段相关文件>
git commit -m "..."
```

不要无脑：

```bash
git add .
```

优先精确 add，避免把：

```text
临时数据
虚拟环境
PDF 构建缓存
身份信息
API key
研究 clone
```

提交进去。

---

# 9. 每次 commit 后验证工作区

```bash
git status --short
git show --stat --oneline HEAD
```

确认提交内容符合预期。

---

# 10. `.gitignore` 专门审计

检查并补充至少：

```text
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/

.env
.env.*
*.key
*.secret

临时 reference repositories
本地 benchmark cache
正式比赛 workspace
运行缓存
大型临时输出
Word 临时文件
TeX 临时文件
```

但是：

> 不要因为 `.gitignore` 修改就把当前已经 tracked 的重要模板删除。

---

# 11. Public Repository Privacy Gate

当前如果仓库是 public：

提交前扫描：

```text
队伍姓名
学号
手机号
邮箱
学校内部账号
API key
token
私有比赛结果
正式比赛答案文件
未发布比赛数据
```

正式比赛 workspace 默认：

```text
不进入 public template repository
```

建议独立：

```text
../competitions/<case-id>/
```

---

# 12. 大文件策略

检查：

```bash
git ls-files
```

并分析大型：

```text
PDF
DOCX
PNG
ZIP
数据集
```

不要为了优化仓库历史贸然运行：

```text
Git LFS migration
history rewrite
```

如有必要，只提出迁移计划。

没有用户明确授权，不改写旧 Git 历史。

---

# 13. Schema 修改的 Git 规则

如果：

```text
schema v1 → v2
```

必须同时提交：

```text
schema
migration
tests
fixture
docs
```

不要：

```text
只改 schema
让旧工作区全部坏掉
```

优先：

```text
backward-compatible reader
```

或者显式 migration tool。

---

# 14. AGENTS / CLAUDE 同步规则

如果修改公共行为：

```text
AGENTS.md
CLAUDE.md
```

必须在同一个 commit 内同步。

如果：

```text
.agents/skills
.claude/skills
```

是镜像：

必须运行：

```text
sync/check
```

CI 必须阻止两边漂移。

---

# 15. 测试失败不能 commit 成 PASS

允许提交测试失败的情况只有：

> 明确的 red-test commit，用于 TDD，而且 commit message 必须明确。

例如：

```text
test(runtime): add failing stale-propagation regression
```

下一 commit：

```text
feat(runtime): implement stale propagation
```

如果没有采用 TDD，就保持每个 feature commit green。

---

# 16. 不要把自动生成垃圾提交进去

默认检查：

```text
*.aux
*.log
*.out
*.toc
*.xdv
*.synctex.gz
*.fdb_latexmk
*.fls
__pycache__
pytest cache
temporary render
temporary reports
```

正式：

```text
schema
fixture
golden file
audit report
```

是否提交，根据是否属于长期 regression evidence 判断。

---

# 17. Feature Branch push

本地验证通过后：

```bash
git push -u origin feat/mathmode-v2-evidence-runtime
```

不要 push 到：

```text
main
```

---

# 18. PR 创建前执行最终检查

```bash
git fetch origin --prune

git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
```

运行完整：

```text
unit tests
negative fixtures
integration fixtures
workflow guard
evidence gate
stale test
schema validation
agent parity check
CI-equivalent test
```

---

# 19. PR 标题

推荐：

```text
feat: upgrade MathMode to evidence-driven modeling runtime
```

---

# 20. PR 描述必须包含

```markdown
## Goal

## Current baseline

## Architecture changes

## Modeling quality changes

## Evidence lineage

## Competition policy changes

## Git/privacy changes

## Backward compatibility

## Tests

## Historical dry-run

## Known limitations

## Not implemented

## Migration notes

## Rollback
```

---

# 21. PR 中明确列出参考项目

只写：

```text
Inspired by architectural ideas from:
- MM-Agent
- MathModel-Skill
- Hjdd14/math-modeling
- zhnnky329/MathModeling-skills
- SatakaGintoki/MathSkill
- DSLighting
```

同时链接：

```text
docs/research/reference_source_map.md
```

不要暗示这些项目“认可”本项目。

---

# 22. 不自动 merge

PR 创建并 CI PASS 后：

停止在：

```text
READY FOR REVIEW
```

除非用户明确要求：

```text
合并
merge
```

否则不要自动 merge 到 main。

---

# 23. 如果用户明确要求 merge

合并前再次：

```text
fetch
CI
PR head SHA
review threads
```

优先：

```text
squash
```

还是：

```text
merge commit
```

根据仓库既有历史风格选择。

不要擅自重写 main。

---

# 24. Merge 后

如果已经明确授权并成功合并：

```bash
git switch main
git fetch origin
git pull --ff-only origin main
```

只允许：

```text
--ff-only
```

避免自动 merge commit。

然后：

```bash
git status
git log --oneline -10
```

确认 clean。

---

# 25. Release 状态

最终 Git 报告必须包括：

```text
base commit
feature branch
commit list
PR
CI status
merge status
final main SHA
working tree status
```

---

# 26. Git 最高原则

任何时候优先保证：

```text
用户工作不丢失
历史可追溯
修改可审查
测试可证明
结果可复现
main 可恢复
```

而不是追求：

> “Git 看起来很干净”。

开始执行前，先做：

```text
Git Forensics
```

再进入 MathMode 的：

```text
T00 Repository Forensics
```

此后每个 T 阶段：

```text
实现
→ 验证
→ commit
→ 下一阶段
```

直到：

```text
PR READY FOR REVIEW
```
