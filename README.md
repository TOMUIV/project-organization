# project-organization

> 大项目组织方法论 + 可执行脚手架。把"会长大的项目"用一套固定层级组织起来：
> `projects/` 按主题分层、`.trash/` 软删除、`.tools/journal.jsonl` 操作日志、结构自检，
> 外加一个 **`buffer/` 缓冲区**：人把文件丢进去，agent 一句"读取 buffer"即按语义归位。

跨 Windows / Linux / macOS，纯 Python 标准库，无第三方依赖。

## 它解决什么

任务开始时很小，但会长成庞然大物：文件散落到根目录、按文件类型平铺、无法归档。
本 skill 提供**从第一天就用**的层级结构、归属判断规则，以及一组可被 agent 直接调用的脚本。

## 能力

| 能力 | 脚本 |
|------|------|
| 新建「大项目根」骨架 | `scripts/new_big_project.py` |
| 新建「子项目/阶段」骨架 | `scripts/new_subproject.py` |
| 结构自检（散落物 / 缺 README / 必备目录） | `scripts/audit_project.py` |
| 软删除 `.trash`（可恢复；硬删需 `--confirm`） | `scripts/trash.py` |
| 操作日志（append-only JSONL + 派生 Markdown） | `scripts/journal.py` |
| **缓冲区 / buffer**（人类 ⇄ AI 交换：`init`/`list`/`take`/`deliver`/`add`/`discard`） | `scripts/buffer.py` |
| 公共库（定位/JSON/模板/日志） | `scripts/common.py` |

## 大项目目录结构

```
<大项目根>/                     # 含 .bigproject.json 标记
├── README.md                  # 顶层唯一允许的 .md
├── .bigproject.json           # 根标记（供脚本自动定位）
├── projects/                  # ★ 所有子项目/阶段
│   ├── _index.md              # 子项目索引（脚本维护）
│   └── <项目名>/{README.md, scripts/, data/, results/, output/, [task/]}
├── shared/                    # 跨项目只读共享
│   └── references/ models/ config/ templates/ pipeline/
├── archive/                   # 已结束项目归档（含 README.md 索引）
├── buffer/                    # 人类 ⇄ AI 交换区：inbox/（人投递）+ outbox/（AI 交付）
├── .tools/                    # 工具 + 操作日志（journal.jsonl / _log.md）
└── .trash/                    # 软删除暂存（可恢复）
```

## 用法

```bash
PO="<skill>/scripts"

# 建大项目根（在父目录下建 <name>/）
python "$PO/new_big_project.py" --name my-research --root ~/projects

# 建子项目（自动向上查找 .bigproject.json 定位根）
python "$PO/new_subproject.py" --name analysis --description "数据分析"

# 结构自检
python "$PO/audit_project.py" --root ~/projects/my-research

# 软删除（默认只预演，加 --apply 执行）
python "$PO/trash.py" put old-dir --reason "迁移" --apply

# 操作日志
python "$PO/journal.py" --tail 20

# 缓冲区：人把文件丢进 <大项目根>/buffer/inbox/ 后，agent 读 buffer 归位
python "$PO/buffer.py" init --root ~/projects/my-research     # 建（幂等）
python "$PO/buffer.py" list --root ~/projects/my-research     # 列 inbox/outbox
python "$PO/buffer.py" take --item data.csv --subproject analysis --subdir data --apply
python "$PO/buffer.py" deliver --file out/report.pdf --apply  # AI 把产物放进 outbox
```

所有脚本默认**先预演后执行**（`--dry-run` / `--apply`），stdout 输出 JSON。

## 设计原则

- **大项目制 + 按语义分层**：子文件夹代表主题，不是文件类型。
- **删除 = 软删除**：一律先进 `.trash/`，硬删必须 `--confirm`。
- **每步可预演**：变更类默认 dry-run；输出 stdout JSON，日志走 stderr。
- **跨机可移植**：位置由 `--root` / `--path` 显式指定，零本机绝对路径。
- **缓冲区归位**：人只负责把文件丢进 `buffer/inbox/`，agent 负责语义归位与记账（移动前先出方案）。

## License

MIT
