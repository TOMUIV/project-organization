#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new_big_project.py — 建立「大项目根」骨架（skill: project-organization）。

由 --path（完整路径）或 --root（父目录）显式指定大项目根位置。
生成 projects/ shared/ archive/ .tools/ .trash/ 与顶层 README、各索引，
并写下 .bigproject.json 标记。

用法:
  python scripts/new_big_project.py --name my-research --root ~/projects
  python scripts/new_big_project.py --name myproj --path /exact/big/root
  python scripts/new_big_project.py --name myproj --path /exact/big/root --dry-run

stdout: {"status":"ok","root":...,"created":[...],"dry_run":bool}
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def build_plan(root, name):
    root = Path(root)
    dirs = [root, root / C.PROJECTS_DIR, root / C.SHARED_DIR]
    dirs += [root / C.SHARED_DIR / d for d in C.SHARED_SUBDIRS]
    dirs += [root / C.ARCHIVE_DIR, root / C.TOOLS_DIR, root / C.TRASH_DIR]

    ctx = {"NAME": name, "DATE": C.today()}
    files = {
        root / "README.md": C.render_template(C.load_template("root_README.md"), ctx),
        root / C.PROJECTS_DIR / "_index.md": C.load_template("projects_index.md"),
        root / C.ARCHIVE_DIR / "README.md": C.load_template("archive_index.md"),
        root / C.TRASH_DIR / "README.md": C.load_template("trash_README.md"),
    }
    return dirs, files


def main():
    ap = argparse.ArgumentParser(description="建立 project-organization 大项目根骨架")
    ap.add_argument("--name", required=True, help="大项目名（用于目录名与 README）")
    ap.add_argument("--root", help="父目录（在其下建 <name>/）")
    ap.add_argument("--path", help="直接指定大项目根的完整路径（优先于 --root）")
    ap.add_argument("--force", action="store_true", help="目录已存在且非空时复用")
    ap.add_argument("--dry-run", action="store_true", help="只预演，不落盘")
    args = ap.parse_args()

    if args.path:
        root = Path(args.path).expanduser()
    elif args.root:
        root = Path(args.root).expanduser() / C.slugify(args.name)
    else:
        C.emit({"status": "error",
                "message": "请提供 --path（完整路径）或 --root（父目录）"}, 2)
    root = root.resolve()

    if C.is_big_project(root):
        C.emit({"status": "error", "message": "该目录已是大项目根（含 %s）" % C.MARKER,
                "root": str(root)}, 1)
    if root.exists() and any(root.iterdir()) and not args.force:
        C.emit({"status": "error",
                "message": "目录已存在且非空，确认可复用请加 --force",
                "root": str(root)}, 1)

    dirs, files = build_plan(root, args.name)
    if args.dry_run:
        C.emit({"status": "ok", "dry_run": True, "root": str(root),
                "plan": {"dirs": [str(d) for d in dirs],
                         "files": [str(f) for f in files]},
                "created": []}, 0)

    created = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    for f, content in files.items():
        if (not f.exists()) or args.force:
            C.write_text(f, content)
            created.append(str(f))
    C.write_json(root / C.MARKER,
                 {"name": args.name, "created": C.now_iso(), "version": 1})
    created.append(str(root / C.MARKER))
    C.journal(root, "root.created", target=root, name=args.name)

    C.log("大项目根已建立: %s" % root)
    C.emit({"status": "ok", "dry_run": False, "root": str(root),
            "marker": str(root / C.MARKER), "created": created}, 0)


if __name__ == "__main__":
    main()
