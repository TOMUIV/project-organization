#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_project.py — 大项目「层级结构」自检（skill: project-organization）。

检查大项目根是否符合 project-organization 约定：顶层只允许规定文件/目录、
每个子项目有 README.md、必备目录齐全、.trash 存在等。

用法:
  python scripts/audit_project.py
  python scripts/audit_project.py --root /path/to/big/root
  python scripts/audit_project.py --strict        # 有 high 问题则退出码 1

stdout: {"status":"ok","root":...,"summary":{...},"issues":[...]}
"""
import argparse
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the (synced) skill dir free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def audit(root):
    root = Path(root)
    issues = []

    def add(sev, kind, path, detail):
        issues.append({"severity": sev, "kind": kind,
                       "path": str(path), "detail": detail})

    if not C.is_big_project(root):
        add("high", "missing_marker", root / C.MARKER,
            "缺少大项目标记 %s（可能不是 project-organization 根）" % C.MARKER)
    if not (root / "README.md").is_file():
        add("high", "missing_readme", root / "README.md", "大项目根缺 README.md")

    for d in (C.PROJECTS_DIR, C.SHARED_DIR, C.ARCHIVE_DIR, C.TRASH_DIR):
        if not (root / d).is_dir():
            add("medium", "missing_dir", root / d, "缺少目录 %s/" % d)
    if (root / C.ARCHIVE_DIR).is_dir() and not (root / C.ARCHIVE_DIR / "README.md").is_file():
        add("low", "missing_index", root / C.ARCHIVE_DIR / "README.md", "归档缺索引 README.md")
    if (root / C.TRASH_DIR).is_dir() and not (root / C.TRASH_DIR / "README.md").is_file():
        add("low", "missing_readme", root / C.TRASH_DIR / "README.md", ".trash 缺说明 README.md")

    # 缓冲区（人类 ⇄ AI 交换区）
    bdir = root / C.BUFFER_DIR
    if bdir.is_dir():
        for sub in (C.BUFFER_INBOX, C.BUFFER_OUTBOX):
            if not (bdir / sub).is_dir():
                add("low", "missing_dir", bdir / sub, "缓冲区缺 %s/（跑 buffer.py init）" % sub)
        inbox = bdir / C.BUFFER_INBOX
        if inbox.is_dir():
            pending = [c for c in sorted(inbox.iterdir()) if not c.name.startswith(".")]
            if pending:
                add("low", "buffer_pending", inbox,
                    "缓冲区 buffer/inbox 有 %d 个待处理项（说“读取 buffer”让 AI 归位）"
                    % len(pending))

    # 顶层散落物
    if root.is_dir():
        for child in sorted(root.iterdir()):
            name = child.name
            if child.is_dir():
                if name not in C.ROOT_ALLOWED_DIRS:
                    add("medium", "stray_dir", child, "顶层出现非约定目录（应归入 projects/shared/archive）")
            else:
                if name not in C.ROOT_ALLOWED_FILES:
                    add("medium", "stray_file", child, "顶层出现散落文件（应归入某个子项目）")

    # 每个子项目必须有 README.md
    projects = root / C.PROJECTS_DIR
    if projects.is_dir():
        for child in sorted(projects.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if not (child / "README.md").is_file():
                add("high", "missing_readme", child / "README.md",
                    "子项目 %s 缺 README.md（无 README 视为未完成）" % child.name)

    summary = {"total": len(issues)}
    by_sev, by_kind = {}, {}
    for it in issues:
        by_sev[it["severity"]] = by_sev.get(it["severity"], 0) + 1
        by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
    summary["by_severity"] = by_sev
    summary["by_kind"] = by_kind
    return summary, issues


def main():
    ap = argparse.ArgumentParser(description="大项目层级结构自检")
    ap.add_argument("--root", help="大项目根（默认从当前目录向上查找标记）")
    ap.add_argument("--strict", action="store_true", help="存在 high 问题时以非 0 退出")
    args = ap.parse_args()

    if args.root:
        root = Path(args.root).expanduser().resolve()
    else:
        root = C.find_root(Path.cwd())
        if root is None:
            C.emit({"status": "error",
                    "message": "未找到大项目根（缺 %s）；请用 --root 指定" % C.MARKER}, 1)

    summary, issues = audit(root)
    if C.is_big_project(root):
        C.journal(root, "audit.run", target=root, total=summary.get("total", 0),
                  by_severity=summary.get("by_severity", {}))
    code = 1 if (args.strict and summary.get("by_severity", {}).get("high")) else 0
    C.emit({"status": "ok", "root": str(root), "summary": summary, "issues": issues}, code)


if __name__ == "__main__":
    main()
