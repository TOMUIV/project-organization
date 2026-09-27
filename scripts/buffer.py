#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""buffer.py — 人类 ⇄ AI 交换缓冲区（skill: project-organization）。

在大项目根下维护一个 `buffer/`：
  buffer/inbox/   人 → AI：用户投递文件
  buffer/outbox/  AI → 人：AI 放回执/产物

子命令：
  init      建缓冲区骨架（幂等；纯新增，直接落盘）
  list      列出 inbox/outbox 内容（只读）
  take      把 inbox 项移动到目标目录（默认预演，--apply 落盘）
  deliver   AI 把产物放进 outbox（默认预演，--apply 落盘）
  add       把外部文件放进 inbox（默认预演，--apply 落盘）
  discard   把 inbox 项弃入暂存区（默认预演，--apply 落盘）

根定位：--root 显式指定；否则从 cwd 向上找 `.bigproject.json`，
找不到再回退到含 `projects/` + `README.md` 的目录。

用法:
  python scripts/buffer.py init
  python scripts/buffer.py list
  python scripts/buffer.py take --item 报名表.pdf --subproject registration --subdir data --apply
  python scripts/buffer.py deliver --file output/报告.pdf --apply

stdout: {"status":"ok", ...}
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the (synced) skill dir free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


# ----------------------------------------------------------------- helpers ---
def resolve_root(explicit):
    if explicit:
        root = Path(explicit).expanduser().resolve()
        return root, C.is_big_project(root)
    root, is_big = C.find_project_root(Path.cwd())
    return root, is_big


def require_root(explicit):
    root, is_big = resolve_root(explicit)
    if root is None:
        C.emit({"status": "error",
                "message": "未找到项目根（无 .bigproject.json，也非 projects/+README.md 结构）；"
                           "请用 --root 指定大项目根"}, 1)
    return root, is_big


def entry_info(path, root):
    p = Path(path)
    if p.is_dir():
        n = sum(1 for _ in p.rglob("*"))
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        kind = "dir"
    else:
        n = 1
        size = p.stat().st_size
        kind = "file"
    return {"name": p.name, "rel": str(p.relative_to(root)).replace("\\", "/"),
            "type": kind, "size": size, "files": n,
            "mtime": C.datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(
                timespec="seconds")}


def list_dir(d, root):
    if not d.is_dir():
        return []
    return [entry_info(c, root) for c in sorted(d.iterdir())]


def resolve_dest(args, root):
    if args.dest:
        return Path(args.dest).expanduser()
    if args.subproject:
        base = Path(root) / C.PROJECTS_DIR / C.slugify(args.subproject)
        return base / args.subdir if args.subdir else base
    C.emit({"status": "error",
            "message": "需要 --dest DIR 或 --subproject NAME [--subdir SUB]"}, 2)


# -------------------------------------------------------------------- init ---
def cmd_init(args):
    root, is_big = require_root(args.root)
    bdir, inbox, outbox = C.buffer_dir(root), C.buffer_inbox(root), C.buffer_outbox(root)
    readme = bdir / "README.md"
    ctx = {"NAME": root.name, "DATE": C.today()}
    content = C.render_template(C.load_template("buffer_README.md"), ctx)
    planned = []
    for d in (bdir, inbox, outbox):
        if not d.is_dir():
            planned.append({"action": "mkdir", "path": str(d)})
    if not readme.is_file() or args.force:
        planned.append({"action": "write", "path": str(readme)})

    created = []
    for d in (bdir, inbox, outbox):
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    if not readme.is_file() or args.force:
        C.write_text(readme, content)
        created.append(str(readme))
    if created:
        C.project_log(root, is_big, "buffer.init", target=root,
                      created=len(created))
    C.log("缓冲区就绪: %s" % bdir)
    C.emit({"status": "ok", "root": str(root), "buffer": str(bdir),
            "is_big_project": is_big, "planned": planned, "created": created})


# -------------------------------------------------------------------- list ---
def cmd_list(args):
    root, is_big = require_root(args.root)
    inbox = list_dir(C.buffer_inbox(root), root)
    outbox = list_dir(C.buffer_outbox(root), root)
    C.emit({"status": "ok", "root": str(root), "is_big_project": is_big,
            "buffer": str(C.buffer_dir(root)),
            "inbox": inbox, "outbox": outbox,
            "inbox_count": len(inbox), "outbox_count": len(outbox)})


# ------------------------------------------------------- move primitive -----
def do_move(src, dst, root, is_big, overwrite, reason, dry_run):
    dst = Path(dst)
    existed = dst.exists()
    if existed:
        if not overwrite:
            raise RuntimeError("目标已存在: %s（如需覆盖加 --overwrite）" % dst)
        if not dry_run:
            C.soft_remove(root, is_big, dst, reason="buffer 覆盖: %s" % reason)
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    return {"from": str(src), "to": str(dst), "overwrote": existed}


# -------------------------------------------------------------------- take ---
def cmd_take(args):
    root, is_big = require_root(args.root)
    inbox = C.buffer_inbox(root)
    if not inbox.is_dir():
        C.emit({"status": "error", "message": "无 buffer/inbox，先跑 buffer.py init"}, 1)
    items = args.item or [c.name for c in sorted(inbox.iterdir())]
    if not items:
        C.emit({"status": "ok", "root": str(root), "moves": [],
                "message": "inbox 为空，无需处理"})
    dest = Path(resolve_dest(args, root))
    dry_run = not args.apply
    if not dest.exists() and not args.mkdir and not dry_run:
        C.emit({"status": "error",
                "message": "目标目录不存在: %s（确认后加 --mkdir 或先新建子项目）" % dest}, 1)

    moves = []
    for name in items:
        src = inbox / name
        if not src.exists():
            C.emit({"status": "error", "message": "inbox 中不存在: %s" % name}, 1)
        moves.append(do_move(src, dest / name, root, is_big,
                             args.overwrite, args.reason, dry_run))
    if not dry_run:
        C.project_log(root, is_big, "buffer.take", target=dest,
                      items=[Path(m["from"]).name for m in moves],
                      dest=str(dest), reason=args.reason)
    C.emit({"status": "ok", "root": str(root), "dry_run": dry_run,
            "dest": str(dest), "moves": moves})


# ----------------------------------------------------------------- deliver ---
def cmd_deliver(args):
    root, is_big = require_root(args.root)
    src = Path(args.file).expanduser()
    if not src.exists():
        C.emit({"status": "error", "message": "文件不存在: %s" % src}, 1)
    outbox = C.buffer_outbox(root)
    if not outbox.is_dir():
        outbox.mkdir(parents=True, exist_ok=True)
    name = args.name or src.name
    dst = outbox / name
    dry_run = not args.apply
    if dst.exists():
        if not args.overwrite:
            C.emit({"status": "error",
                    "message": "outbox 已存在同名: %s（加 --overwrite 覆盖）" % dst}, 1)
        if not dry_run:
            C.soft_remove(root, is_big, dst, reason="outbox 覆盖")
    if not dry_run:
        if args.move:
            shutil.move(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        C.project_log(root, is_big, "buffer.deliver", target=dst,
                      src=str(src), mode="move" if args.move else "copy")
    C.emit({"status": "ok", "root": str(root), "dry_run": dry_run,
            "to": str(dst), "mode": "move" if args.move else "copy"})


# --------------------------------------------------------------------- add ---
def cmd_add(args):
    root, is_big = require_root(args.root)
    inbox = C.buffer_inbox(root)
    if not inbox.is_dir():
        C.emit({"status": "error", "message": "无 buffer/inbox，先跑 buffer.py init"}, 1)
    dry_run = not args.apply
    moves = []
    for f in args.file:
        src = Path(f).expanduser()
        if not src.exists():
            C.emit({"status": "error", "message": "文件不存在: %s" % src}, 1)
        dst = inbox / (src.name)
        if dst.exists():
            if not args.overwrite:
                C.emit({"status": "error",
                        "message": "inbox 已存在同名: %s（加 --overwrite）" % dst}, 1)
            if not dry_run:
                C.soft_remove(root, is_big, dst, reason="inbox 覆盖")
        if not dry_run:
            if args.move:
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
        moves.append({"from": str(src), "to": str(dst)})
    if not dry_run:
        C.project_log(root, is_big, "buffer.add", target=inbox,
                      files=[Path(m["from"]).name for m in moves],
                      mode="move" if args.move else "copy")
    C.emit({"status": "ok", "root": str(root), "dry_run": dry_run, "moves": moves})


# ----------------------------------------------------------------- discard ---
def cmd_discard(args):
    root, is_big = require_root(args.root)
    inbox = C.buffer_inbox(root)
    dry_run = not args.apply
    discarded = []
    for name in args.item:
        src = inbox / name
        if not src.exists():
            C.emit({"status": "error", "message": "inbox 中不存在: %s" % name}, 1)
        dest = None
        if not dry_run:
            dest = C.soft_remove(root, is_big, src, reason=args.reason or "buffer discard")
            C.project_log(root, is_big, "buffer.discard", target=src, trashed=str(dest))
        discarded.append({"item": name, "trashed": str(dest) if dest else None})
    C.emit({"status": "ok", "root": str(root), "dry_run": dry_run, "discarded": discarded})


# -------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser(description="人类 ⇄ AI 交换缓冲区")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="建缓冲区骨架（幂等，直接落盘）")
    p.add_argument("--root"); p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("list", help="列出 inbox/outbox（只读）")
    p.add_argument("--root")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("take", help="把 inbox 项移动到目标目录")
    p.add_argument("--root")
    p.add_argument("--item", action="append", help="inbox 中的名字（可重复；默认全部）")
    p.add_argument("--dest", help="目标目录（绝对或相对）")
    p.add_argument("--subproject", help="目标子项目名（→ projects/<名>/）")
    p.add_argument("--subdir", help="子项目内子目录（如 data/scripts/output/results）")
    p.add_argument("--mkdir", action="store_true", help="目标目录不存在时创建")
    p.add_argument("--overwrite", action="store_true", help="覆盖同名（旧物入暂存）")
    p.add_argument("--reason", default="buffer take")
    p.add_argument("--apply", action="store_true", help="真正执行（默认只预演）")
    p.set_defaults(func=cmd_take)

    p = sub.add_parser("deliver", help="AI 把产物放进 outbox")
    p.add_argument("--root"); p.add_argument("--file", required=True)
    p.add_argument("--name"); p.add_argument("--move", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_deliver)

    p = sub.add_parser("add", help="把外部文件放进 inbox")
    p.add_argument("--root"); p.add_argument("--file", nargs="+", required=True)
    p.add_argument("--move", action="store_true"); p.add_argument("--overwrite", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("discard", help="把 inbox 项弃入暂存区")
    p.add_argument("--root"); p.add_argument("--item", nargs="+", required=True)
    p.add_argument("--reason"); p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_discard)

    args = ap.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        C.emit({"status": "error", "message": str(e)}, 1)


if __name__ == "__main__":
    main()
