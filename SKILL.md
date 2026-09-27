---
name: project-organization
description: >
  大项目组织方法论 + 可执行脚手架（跨机跨系统）。当用户开始一个会长期演进、多阶段/多子任务的项目，
  需要按研究/业务主题分层组织文件、或项目文件已散落在根目录需归整时使用。
  核心是"大项目制 + 按语义分层 + agent 自动判断归属 + .trash 软删除"。
  提供新建大项目/子项目骨架、结构自检、结构安全删除（.trash）脚本与模板。
  含项目根下的「缓冲区 / buffer」——人类把文件丢进 `buffer/`，AI 说"读取 buffer"即按语义归位到 projects/。
  触发词：组织项目、项目结构、大项目、项目管理、目录整理、项目化、分层结构、新建项目、归档项目、
  读取 buffer、处理 buffer、缓冲区、把文件丢进 buffer、buffer 归位。
  Use ONLY for long-lived / multi-phase projects；一次性临时任务走 `temp-workspace`，不要用本 skill。
version: 2.1.0
---

# Project Organization — 大项目组织方法论

把"组织大项目"固化为**方法论 + 可执行脚手架**。很多任务开始时很小，但会长成庞然大物。
本 skill 提供一套**从第一天就用**的层级结构、归属判断规则，以及一组跨机跨系统的落地脚本。

> 适用：任何会长期演进、有多阶段/多子任务的工程、研究、写作、开发项目。

---

## 一、边界：和 temp-workspace 的分工

| 场景 | 用哪个 skill | 建在哪 |
|------|--------------|--------|
| **会长期成长**、有多个阶段/子项目、需归档 | **本 skill** | 大项目根（`projects/` 分层） |
| **一次性**分析报告 / 临时小实验，用完即弃 | `temp-workspace` | `$OPENCODE_SCRATCH_DIR/<日期>_<主题>/` |

一句话：**"要不要为它建 `projects/` 分层"是分水岭**。只是临时跑一下 → `temp-workspace`；
预期会攒东西、要给人交付、要归档 → 本 skill。

### 与 temp-workspace 的交接协议（晋升 / 降级）

两个 skill 是同一根生命周期的两端，**不是二选一就结束**——项目可随体量在两者间迁移：

| 方向 | 触发 | 工具 |
|------|------|------|
| scratch → 大项目（**晋升 promote**） | 临时项目长大：出现多阶段/子任务、要交付、要归档 | `temp-workspace/scripts/promote.py`（内部调用本 skill 的 `new_subproject.py` + `trash.py`）|
| 大项目 → scratch（**降级 demote**） | 大项目里冒出一段纯一次性实验，不值得建子项目 | `temp-workspace/scripts/new_project.py` |

- `promote.py` 会：建子项目骨架 → 把 scratch 的 `data/src/output/results` 按语义映射进来（`src→scripts`）
  → 用本 skill 的 `trash.py` 把空壳**软删除**进 `.trash/`（不硬删）→ 重建 scratch 索引。
- 因此**接收晋升项目无需额外操作**：子项目天然落在 `projects/<名>/`，且已登记索引。
- 判据仍是一句话：**"要不要为它建 `projects/` 分层"**——不确定时先在 scratch 起，长大后 `promote.py` 过来即可。

---

## 二、大项目根放在哪（接 AGENTS 项目目录规范）

大项目根的**父目录**按 AGENTS.md「本地项目目录规范」四类归属，全部走环境变量：

| 项目类别 | base 根 | 脚本 `--kind` |
|----------|---------|---------------|
| 清华 / 学习 / 校园 | `$OPENCODE_THU_DIR/` | `thu` |
| 腾讯云 / VPS 相关 | `$OPENCODE_TEMP_DIR/tencentcloud-ops/` | `tencent` |
| 跨机共享数据 / 项目 | `$OPENCODE_TEMP_DIR/` | `shared` |
| opencode 临时小项目 | `$OPENCODE_SCRATCH_DIR/` | `scratch` |
| 其它（用户已有目录等） | 显式 `--root` / `--path` | `custom` |

> 例：`--kind thu --name "ALS Program"` → `$OPENCODE_THU_DIR/ALS-Program/`。
> **不写死盘符**：脚本读环境变量，三端（Windows/Linux/macOS）通用。

---

## 三、推荐的层级结构（hierarchical layout）

```
<大项目根>/                     # 含 .bigproject.json 标记
├── README.md                  # 顶层唯一允许的 .md（目的/结构/子项目清单索引）
├── .bigproject.json           # 由脚手架写入的根标记（供脚本自动定位）
├── projects/                  # ★ 所有子项目/阶段，每个一个子文件夹
│   ├── _index.md              # 子项目索引（脚本自动维护）
│   └── <项目名>/
│       ├── README.md          # 强制：目的/进展/结果/脚本讲解（无 README 视为未完成）
│       ├── scripts/           # 该项目脚本
│       ├── data/              # 输入数据
│       ├── results/           # 中间结果
│       ├── output/            # 最终产出（报告/图/PPT）
│       └── task/ 或 workplan/ # 任务表/任务书（可选，--with-task 生成）
├── shared/                    # 跨项目共享（只读引用，不在此写新文件）
│   └── references/ models/ config/ templates/ pipeline/
├── buffer/                    # ★ 人类 ⇄ AI 交换区（见 §四 缓冲区）
│   ├── inbox/                 # 人 → AI：你投递文件
│   ├── outbox/                # AI → 人：AI 放回执/产物
│   └── README.md
├── archive/                   # 已结束项目归档（含 README.md 索引）
├── .tools/                    # 工具/脚本 + 操作日志（journal.jsonl / _log.md）
└── .trash/                    # 软删除暂存（见 §六，可恢复）
```

**关键点**
- 子项目名用英文短横线（`ag-analysis`、`literature-download`），阶段用 `--type stage` 或子文件夹区分。
- 子项目根目录**只有 README.md**，其余内容进子目录。
- 任务表/任务书归入所属项目的 `task/`，**不留在根目录**。
- 顶层只允许 `README.md` / `AGENTS.md` / `MEMORY.md` / `.bigproject.json` 与上述目录（含 `buffer/`），其余一律视为散落物（`audit_project.py` 会报）。

---

## 四、agent 判断归属规则

每次来新任务，先判断（**语义判断，不是关键词匹配**）：

| 情形 | 动作 |
|------|------|
| 新任务与现有项目无重叠、有独立目标/产出 | **新建** `projects/<项目名>/`（`new_subproject.py`） |
| 任务属于某项目内已有阶段/子任务 | **复用**，直接在该项目子文件夹内工作，不新建 |
| 项目目标达成、不再推进 | **归档** 到 `archive/<YYYY-MM-DD>_<项目名>/` |
| 多个项目共享的资源 | 放 `shared/`（不属任何单一项目） |
| 一次性、用完即弃 | 不属于本 skill → 走 `temp-workspace` |

- 看任务的**目标/产出**是否与某项目一致，而非看关键词。
- 不确定时**倾向复用**（避免项目碎片化）；目标确实独立时果断新建。

### 4.1 缓冲区（buffer）——人类 ⇄ AI 交换区

> 让"人随手丢文件、AI 自动归位"变成一句口令：**用户把文件丢进 `<大项目根>/buffer/inbox/`，
> 对 AI 说「读取 buffer」即可。** 目录 `buffer/` 由 `new_big_project.py` 自动建，也可 `buffer.py init` 补建。

```
<大项目根>/buffer/
├── inbox/     # 人 → AI：用户投递（随便命名，文件/目录/压缩包都行）
├── outbox/    # AI → 人：AI 放回执/产物
└── README.md  # 面向人的用法说明（skill 的 templates/buffer_README.md）
```

**「读取 buffer」= 固定协议（4 步）**

1. `python scripts/buffer.py list` —— 列 `inbox/`（+ `outbox/`）清单。
2. 对 `inbox/` 每一项做**语义归属判断**（用上面 §四 的规则）：已有子项目 / 新建子项目 / `shared/` / `archive/` / 丢弃。
3. **先出「归属方案」清单**（源 → 目标，含"需要新建 XX 子项目"），**等用户确认**（符合移动铁律）。
4. 确认后执行并记账：
   - 新建的：`new_subproject.py --name X ...`
   - 移动的：`buffer.py take --item F --subproject X --subdir data --apply`
   - 记日志：`take/deliver/discard` 自动写 journal（无标记的根写 `buffer/_buffer_log.jsonl`）。
   - 最后提醒 `outbox/` 里有没有要给用户的东西。

**规则**
- `buffer/` 只做**中转**，处理完 `inbox/` 应清空；`audit_project.py` 会对非空 inbox 报 `buffer_pending`（提醒归位）。
- **一切移动/覆盖都先预演后执行**（`--apply`），覆盖同名旧物进暂存（大项目 `.trash/`，否则 `buffer/.replaced/`），不硬删。
- 根定位：`--root` 显式 → 否则从 cwd 向上找 `.bigproject.json`；找不到再回退到含 `projects/`+`README.md` 的目录（兼容手工搭建、无标记的项目根）。
- 支持双向：`buffer.py deliver --file <产物>` 让 AI 把东西放进 `outbox/` 交给人。

---

## 五、快速开始

```powershell
$PO = "$env:USERPROFILE\.config\opencode\skills\project-organization\scripts"

# 1) 建大项目根（按类别自动落到对应环境变量根下）
python "$PO\new_big_project.py" --name "ALS Program" --kind thu

# 2) 进大项目后建子项目（自动向上查找 .bigproject.json 定位根）
python "$PO\new_subproject.py" --name ag-analysis --description "AG 结果分析"

# 2.5) 缓冲区：用户把文件丢进 buffer/inbox/ 后，AI 读 buffer 并归位
python "$PO\buffer.py" init --root .                 # 建缓冲区（幂等；new_big_project 已自带）
python "$PO\buffer.py" list                          # 列 inbox/outbox → 出归属方案 → 用户确认
python "$PO\buffer.py" take --item 数据.csv --subproject ag-analysis --subdir data --apply
python "$PO\buffer.py" deliver --file output/报告.pdf --apply   # AI 把产物放进 outbox

# 3) 结构自检
python "$PO\audit_project.py" --root "<大项目根>"

# 4) 归整时"删除"旧目录 → 软删除进 .trash（默认只预演）
python "$PO\trash.py" put "<旧目录>" --reason "迁移到 projects/xxx" 
python "$PO\trash.py" put "<旧目录>" --reason "迁移到 projects/xxx" --apply

# 5) 看操作日志（谁在何时创建/删除/归档了什么）
python "$PO\journal.py" --tail 20
```

> 所有脚本均**先预演、后执行**（默认 dry-run，需 `--apply` 才落盘/移动）；输出 stdout 为 JSON。

---

## 六、删除 = 软删除（.trash 机制）

**任何"删除"都先移入 `<大项目根>/.trash/`，不得直接硬删**（AGENTS.md「文件删除铁律」的工具化）。

- 条目结构：`.trash/<时间戳>__<原名>/`，内含被移入的文件/目录 + `_manifest.json`（记录原路径、原因、时间）。
- `put` 移入、`list` 查看、`restore` 恢复、`purge` 彻底删除。
- `purge` 是**唯一**的硬删路径，必须 `--confirm`，且执行前仍须**按 AGENTS 铁律列清单并经用户确认**。
- `.trash/` 是可恢复区，长期留存；确认无用的条目由用户决定何时 `purge`。

---

## 七、操作日志（journal）

每个大项目根自带一份**追加式操作日志**，记录"谁在何时做了什么"，与 `.trash` 互为印证。

- **存储**：`<大项目根>/.tools/journal.jsonl`（append-only，每行一个事件 JSON）。
- **事件字段**：`{ts, actor, event, target, ...extra}`；`actor` 取 `OPENCODE_ACTOR` → 系统用户名。
- **覆盖事件**：`root.created` / `subproject.created` / `trash.put` / `trash.restore` / `trash.purge` / `audit.run`。
- **查看**：`journal.py`（`--tail` / `--since` / `--event` / `--actor` 过滤，默认输出 JSON）。
- **派生可读版**：`journal.py --render` 生成 `.tools/_log.md`（Markdown 表格）。
- 日志写入**不阻断主流程**（失败仅静默返回 None）；`.tools/` 不被 `audit_project.py` 视为散落物。

---

## 八、本地 ↔ 远程/集群对应

- 本地 = 主项目（脚本/文档/报告），远程 = 工作区（数据/计算/产物）。
- 在本地子项目的 README 里写明远程工作区路径与对应关系。
- **禁止在远程根目录散落脚本/数据/log**——同样按项目归入远程子文件夹。
- 本地与远程目录名尽量一致，便于对照。
- 访问远程机器一律走 `ssh-mesh` 别名（见 `skill-spec` §5.1），不在本 skill 内拼 ssh。

---

## 九、迁移落地流程（把已混乱的项目归整）

1. **全面探查**：列出根目录所有目录/文件，理解每个的语义归属。
2. **设计映射**：把每个平级目录/散落文件映射到目标子项目的子目录。
3. **先建结构**：`new_big_project.py` / `new_subproject.py` 建骨架。
4. **归任务文件**：把根目录任务表/任务书归入所属项目的 `task/`。
5. **归报告/产物**：把平铺的 `output/` 报告按项目归入各子项目 `output/`。
6. **迁移共享**：把跨项目的 `pipeline/` `references/` `models/` 等移入 `shared/`。
7. **写 README**：为每个项目补 README（无 README 视为未完成）。
8. **旧物入 .trash**：旧的空壳/废弃目录用 `trash.py put --apply` 移入 `.trash/`（不硬删）。
9. **更新规范**：更新根 README/AGENTS 反映新结构；历史文档顶部加迁移说明。
10. **验证**：`audit_project.py` 确认无散落物、每个子项目有 README。

> **安全铁律**：任何删除/移动前，先列完整清单 + 等用户确认；**删除一律走 `.trash/`**。

---

## 十、脚本

> 全部为 Python 标准库实现，跨 Windows/Linux/macOS；stdout 输出 JSON，日志走 stderr。
> `<PO>` = 本 skill 的 `scripts/` 目录。

### `scripts/common.py`
公共库（JSON 输出、根目录标记定位、环境变量解析、模板渲染）。被其余脚本 import，不单独调用。

### `scripts/new_big_project.py`
用途：建立大项目根骨架（含 `projects/ shared/ archive/ .tools/ .trash/` 与索引、根标记）。
| 参数 | 说明 | 必填 |
|------|------|------|
| `--name` | 大项目名（用于目录名与 README） | ✅ |
| `--kind` | `thu\|tencent\|shared\|scratch\|custom`，按 AGENTS 规范解析 base 根 | 否（默认 custom） |
| `--root` | base 根目录（在其下建 `<name>/`） | custom 时 ✅ |
| `--path` | 直接指定大项目根完整路径（优先） | 否 |
| `--force` | 目录已存在且非空时复用 | 否 |
| `--dry-run` | 只预演，不落盘 | 否 |

示例：`python scripts/new_big_project.py --name "ALS Program" --kind thu`
输出：`{"status":"ok","root":...,"marker":...,"created":[...]}`

### `scripts/new_subproject.py`
用途：在大项目根下新建子项目/阶段骨架，并登记到 `projects/_index.md`。
| 参数 | 说明 | 必填 |
|------|------|------|
| `--name` | 子项目名（英文短横线） | ✅ |
| `--root` | 大项目根（默认从 cwd 向上查找 `.bigproject.json`） | 否 |
| `--type` | `project\|stage` | 否（默认 project） |
| `--with-task` | 额外建 `task/`（任务表/任务书） | 否 |
| `--description` | 项目目的（写入 README 与索引） | 否 |
| `--force` / `--dry-run` | 复用已存在目录 / 只预演 | 否 |

示例：`python scripts/new_subproject.py --name ag-analysis --description "AG 结果分析"`
输出：`{"status":"ok","root":...,"project":...,"created":[...]}`

### `scripts/buffer.py`
用途：人类 ⇄ AI 交换缓冲区（`<大项目根>/buffer/{inbox,outbox}`）——`init` / `list` / `take` / `deliver` / `add` / `discard`。
| 子命令 | 关键参数 | 说明 |
|--------|----------|------|
| `init` | `--root` `--force` | 建缓冲区骨架 + README；**幂等、直接落盘**（纯新增） |
| `list` | `--root` | 列 `inbox/`、`outbox/`（只读；`--root` 缺省时从 cwd 向上找根） |
| `take` | `--item NAME...` `--dest DIR` \| `--subproject NAME [--subdir SUB]` `--mkdir` `--overwrite` `--reason` `--apply` | 把 inbox 项移动到目标目录；**默认预演** |
| `deliver` | `--file FILE` `--name` `--move` `--overwrite` `--apply` | AI 把产物放进 `outbox/`（默认复制） |
| `add` | `--file FILE...` `--move` `--overwrite` `--apply` | 把外部文件放进 `inbox/` |
| `discard` | `--item NAME...` `--reason` `--apply` | 把 inbox 项弃入暂存区（`.trash/` 或 `buffer/.replaced/`） |

根定位：`--root` → cwd 向上找 `.bigproject.json` → 回退到含 `projects/`+`README.md` 的目录。
覆盖同名旧物**不硬删**：大项目根进 `.trash/`，否则进 `buffer/.replaced/`。
日志：大项目根写标准 journal；否则写 `buffer/_buffer_log.jsonl`。

示例：`python scripts/buffer.py take --item 数据.csv --subproject ag-analysis --subdir data --apply`
输出：`{"status":"ok","dry_run":false,"dest":...,"moves":[{"from":...,"to":...,"overwrote":false}]}`

### `scripts/trash.py`
用途：`.trash` 软删除暂存（可恢复）——`put` / `list` / `restore` / `purge` / `status`。
| 子命令 | 关键参数 | 说明 |
|--------|----------|------|
| `put` | `paths...` `--reason` `--root` `--apply` | 移入暂存；**默认预演**，`--apply` 才移动 |
| `list` | `--root` | 列出暂存条目 |
| `restore` | `--id` `--root` `--apply` `--force` | 还原到原路径；默认预演 |
| `purge` | `--id` \| `--all` \| `--older-than DAYS` `--confirm` `--root` | 彻底删除；**必须 `--confirm`** |
| `status` | `--root` | 条目数与占用字节 |

示例：`python scripts/trash.py put "old/" --reason "迁移" --apply`
输出：`{"status":"ok","entry":...,"items":[...]}`

### `scripts/audit_project.py`
用途：大项目「层级结构」自检（顶层散落物、子项目 README、必备目录、.trash）。
| 参数 | 说明 | 必填 |
|------|------|------|
| `--root` | 大项目根（默认从 cwd 向上查找标记） | 否 |
| `--strict` | 存在 high 问题时退出码 1 | 否 |

示例：`python scripts/audit_project.py --root "<大项目根>"`
输出：`{"status":"ok","root":...,"summary":{"by_severity":...},"issues":[...]}`

### `scripts/journal.py`
用途：查看/渲染操作日志（源 `.tools/journal.jsonl`）。
| 参数 | 说明 | 必填 |
|------|------|------|
| `--root` | 大项目根（默认从 cwd 向上查找标记） | 否 |
| `--tail N` | 只显示最近 N 条 | 否 |
| `--since` | 起始时间（`YYYY-MM-DD` 或 ISO） | 否 |
| `--event` / `--actor` | 事件 / 操作者过滤（子串） | 否 |
| `--render` | 生成 `.tools/_log.md`（Markdown） | 否 |
| `--out` | `--render` 的输出路径 | 否 |

示例：`python scripts/journal.py --tail 20` ／ `python scripts/journal.py --render`
输出：`{"status":"ok","root":...,"count":N,"records":[...]}`

---

## 十一、与现有系统的关系

- 本 skill 定义**组织方法论 + 通用脚手架**，不含领域逻辑；领域结构以项目自身 AGENTS.md/README 为准。
- 进行中的在 `projects/`，结束移入 `archive/`；共享资源进 `shared/`。
- 访问远程/集群走 `ssh-mesh`；临时小项目走 `temp-workspace`。
- 不新建/下载额外 skill 来"管项目"——本 skill 已是该能力。

---

## 十二、真实案例（ALS 项目，2026-09-02）

大项目根从散落状态归整为：

```
projects/
├── carbon/           # Carbon 致病性打分
├── ag-analysis/      # AG 结果分析
├── intronic/         # Intronic 5 模态分析
├── literature-download/  # 文献下载（task/ 放任务表 csv）
├── knowledge-graph/  # 知识图谱（workplan/ 放任务书）
├── podmon/           # 集群 AI 审计 Agent
└── gnomad/           # gnomAD 注释验证
shared/
├── pipeline/  cluster/  meetings/  references/  models/  knowledge/
```

每个项目一个 README；集群同步项目化（根目录散落文件归入 `literature-download/`）；
归整过程中废弃的旧目录一律经 `.trash/` 暂存，未硬删。
