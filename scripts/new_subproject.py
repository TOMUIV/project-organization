#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new_subproject.py — 在大项目根下新建子项目/阶段骨架（skill: project-organization）。

自动从 --root 或当前目录向上查找 .bigproject.json 定位大项目根。
生成 projects/<name>/{README.md,scripts,data,results,output}（可选 task/），
并在 projects/_index.md 追加一行索引。

用法:
  python scripts/new_subproject.py --name data-prep
  python scripts/new_subproject.py --name knowledge-graph --with-task --type stage
  python scripts/new_subproject.py --name modeling --root /path/to/big/root --dry-run

stdout: {"status":"ok","root":...,"project":...,"created":[...],"dry_run":bool}
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def resolve_root(explicit):
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not C.is_big_project(root):
            C.emit({"status": "error",
                    "message": "指定目录不是大项目根（缺 %s）" % C.MARKER,
                    "root": str(root)}, 1)
        return root
    root = C.find_root(Path.cwd())
    if root is None:
        C.emit({"status": "error",
                "message": "未找到大项目根（缺 %s）；请用 --root 指定或先运行 new_big_project.py"
                           % C.MARKER}, 1)
    return root


def main():
    ap = argparse.ArgumentParser(description="在大项目根下新建子项目骨架")
    ap.add_argument("--name", required=True, help="子项目名（英文短横线）")
    ap.add_argument("--root", help="大项目根（默认从当前目录向上查找标记）")
    ap.add_argument("--type", default="project", choices=["project", "stage"],
                    help="project=独立子项目；stage=某项目的阶段")
    ap.add_argument("--with-task", action="store_true", help="额外创建 task/（任务表/任务书）")
    ap.add_argument("--description", default="", help="项目目的（写入 README）")
    ap.add_argument("--force", action="store_true", help="目录已存在且非空时复用")
    ap.add_argument("--dry-run", action="store_true", help="只预演，不落盘")
    args = ap.parse_args()

    root = resolve_root(args.root)
    slug = C.slugify(args.name)
    proj = root / C.PROJECTS_DIR / slug

    if proj.exists() and any(proj.iterdir()) and not args.force:
        C.emit({"status": "error",
                "message": "子项目目录已存在且非空，确认可复用请加 --force",
                "project": str(proj)}, 1)

    dirs = [proj] + [proj / d for d in C.SUBPROJECT_SUBDIRS]
    if args.with_task:
        dirs.append(proj / "task")

    readme = C.render_template(C.load_template("subproject_README.md"), {"NAME": args.name})
    if args.description:
        readme = readme.replace("<一两句话说明这个项目要做什么>", args.description)

    index = root / C.PROJECTS_DIR / "_index.md"
    index_row = "| %s | %s | %s | active | %s |" % (slug, args.type, C.today(),
                                                     args.description or "")

    if args.dry_run:
        C.emit({"status": "ok", "dry_run": True, "root": str(root),
                "project": str(proj),
                "plan": {"dirs": [str(d) for d in dirs],
                         "readme": str(proj / "README.md"),
                         "index": str(index), "index_row": index_row},
                "created": []}, 0)

    created = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    C.write_text(proj / "README.md", readme)
    created.append(str(proj / "README.md"))

    if not index.exists():
        C.write_text(index, C.load_template("projects_index.md"))
        created.append(str(index))
    with open(index, "a", encoding="utf-8", newline="\n") as f:
        f.write(index_row + "\n")

    C.journal(root, "subproject.created", target=proj, type=args.type,
              description=args.description or "")
    C.log("子项目已建立: %s" % proj)
    C.emit({"status": "ok", "dry_run": False, "root": str(root),
            "project": str(proj), "created": created}, 0)


if __name__ == "__main__":
    main()
