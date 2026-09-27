# buffer — 人类 ⇄ AI 交换区

> 本项目（**{{NAME}}**）根下的**缓冲区**。你把文件丢进来，跟 AI 说一句「**读取 buffer**」，
> AI 就会把 `inbox/` 里的东西归位到 `projects/`（已有子项目或新建子项目）、`shared/` 或 `archive/`。

## 目录

```
buffer/
├── inbox/     # 人 → AI：你投递的文件/文件夹放这里
├── outbox/    # AI → 人：AI 交给你的回执/产物放这里
└── README.md  # 本说明
```

## 怎么用

1. 把要处理的东西**丢进 `inbox/`**（文件、文件夹、压缩包都行，随便命名）。
2. 对 AI 说：**「读取 buffer」**（或「处理 buffer」）。
3. AI 会先列出 `inbox/` 清单 + 给出**归属方案**（每个 → 去哪个子项目的哪个目录，是否需要新建子项目），
   **你确认后**它才移动（符合「删除/移动前先列清单并确认」的规则）。
4. AI 也会看看 `outbox/`，提醒你取走它给你的东西。

## 规则

- 本目录**只做中转**，不要长期堆放；处理完 `inbox/` 应清空。
- AI 的移动一律**可追溯**：记进 `.tools/journal.jsonl`（本目录无大项目标记时记在 `buffer/_buffer_log.jsonl`）。
- 覆盖同名文件时，旧文件会先进暂存区（大项目用 `.trash/`，否则 `buffer/.replaced/`），不硬删。

## AI 侧的对应命令

```powershell
$PO = "$env:USERPROFILE\.config\opencode\skills\project-organization\scripts"
python "$PO\buffer.py" init   --root .                 # 建缓冲区（幂等）
python "$PO\buffer.py" list   --root .                 # 列 inbox/outbox
python "$PO\buffer.py" take   --item 某文件 --subproject analysis --subdir data --apply
python "$PO\buffer.py" deliver --file 报告.pdf                      # AI 把产物放进 outbox
```
