#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""trash.py — 大项目根内的软删除暂存（可恢复），替代直接硬删（skill: project-organization）。

"删除"一律先移入 <大项目根>/.trash/<时间戳>__<原名>/，附 _manifest.json 记录原路径、
原因与时间，可随时恢复；唯有 purge 才真正删除，且必须显式 --confirm。

子命令:
  put     移入暂存（默认只预演，加 --apply 执行）
  list    列出暂存条目
  restore 恢复条目到原路径（默认只预演，加 --apply 执行）
  purge   彻底删除（需 --confirm；AGENTS「文件删除铁律」要求先经用户确认）
  status  暂存区统计

用法:
  python scripts/trash.py put <路径...> --reason "..."
  python scripts/trash.py put <路径...> --reason "..." --apply
  python scripts/trash.py list
  python scripts/trash.py restore --id 20260926-101500__old-dir --apply
  python scripts/trash.py purge --id 20260926-101500__old-dir --confirm
  python scripts/trash.py purge --older-than 30 --confirm

stdout: {"status":"ok",...}（每条命令一份 JSON）
"""
import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

MANIFEST = "_manifest.json"


def resolve_root(explicit, target=None):
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not C.is_big_project(root):
            C.emit({"status": "error",
                    "message": "指定目录不是大项目根（缺 %s）" % C.MARKER,
                    "root": str(root)}, 1)
        return root
    start = target or Path.cwd()
    root = C.find_root(start)
    if root is None:
        C.emit({"status": "error",
                "message": "未找到大项目根（缺 %s）；请用 --root 指定" % C.MARKER}, 1)
    return root


def trash_dir(root):
    return Path(root) / C.TRASH_DIR


def unique_entry(trash, name):
    base = "%s__%s" % (C.timestamp(), C.slugify(name))
    cand = trash / base
    n = 1
    while cand.exists():
        n += 1
        cand = trash / ("%s-%d" % (base, n))
    return cand


def entry_dirs(trash):
    if not trash.is_dir():
        return []
    out = []
    for p in sorted(trash.iterdir()):
        if p.is_dir() and p.name != C.TRASH_DIR:
            out.append(p)
    return out


def load_manifest(entry):
    return C.read_json(entry / MANIFEST, default={}) or {}


def cmd_put(args):
    targets = [Path(t).expanduser() for t in args.paths]
    for t in targets:
        if not t.exists():
            C.emit({"status": "error", "message": "路径不存在: %s" % t}, 1)
    root = resolve_root(args.root, target=targets[0])
    trash = trash_dir(root)
    plan = []
    for t in targets:
        src = t.resolve()
        if src == root or root in src.parents and src == root:
            C.emit({"status": "error", "message": "拒绝移动大项目根本身", "path": str(src)}, 1)
        if trash == src or trash in src.parents:
            C.emit({"status": "error", "message": "路径已在 .trash 内", "path": str(src)}, 1)
        plan.append({"from": str(src), "name": src.name})
    entry = unique_entry(trash, targets[0].name)

    if not args.apply:
        C.emit({"status": "ok", "dry_run": True, "root": str(root),
                "entry": str(entry), "reason": args.reason, "items": plan}, 0)

    trash.mkdir(parents=True, exist_ok=True)
    entry.mkdir(parents=True, exist_ok=False)
    items = []
    for p in plan:
        src = Path(p["from"])
        dest = entry / src.name
        k = 1
        while dest.exists():
            k += 1
            dest = entry / ("%s-%d" % (src.name, k))
        shutil.move(str(src), str(dest))
        items.append({"name": dest.name, "from": str(src), "to": str(dest)})
    C.write_json(entry / MANIFEST,
                 {"id": entry.name, "time": C.now_iso(), "root": str(root),
                  "reason": args.reason or "", "items": items})
    C.journal(root, "trash.put", target=entry.name, reason=args.reason or "",
              items=[i["name"] for i in items])
    C.log("已移入暂存: %s" % entry)
    C.emit({"status": "ok", "dry_run": False, "root": str(root),
            "entry": str(entry), "reason": args.reason or "", "items": items}, 0)


def cmd_list(args):
    start = Path(args.root).expanduser() if args.root else Path.cwd()
    root = C.find_root(start)
    if root is None:
        C.emit({"status": "error",
                "message": "未找到大项目根（缺 %s）；请用 --root 指定" % C.MARKER}, 1)
    trash = trash_dir(root)
    entries = []
    for e in entry_dirs(trash):
        m = load_manifest(e)
        entries.append({"id": e.name,
                        "time": m.get("time", ""),
                        "reason": m.get("reason", ""),
                        "items": [i.get("from", "") for i in m.get("items", [])]})
    C.emit({"status": "ok", "root": str(root), "count": len(entries), "entries": entries}, 0)


def cmd_restore(args):
    root = resolve_root(args.root)
    trash = trash_dir(root)
    entry = trash / args.id
    if not entry.is_dir():
        C.emit({"status": "error", "message": "条目不存在: %s" % args.id}, 1)
    m = load_manifest(entry)
    items = m.get("items", [])
    if not items:
        C.emit({"status": "error", "message": "条目缺少清单，无法恢复: %s" % args.id}, 1)

    plan = []
    for it in items:
        target = Path(it["from"])
        plan.append({"name": it["name"], "to": str(target), "exists": target.exists()})

    if not args.apply:
        C.emit({"status": "ok", "dry_run": True, "entry": args.id, "restore": plan}, 0)

    restored = []
    for it in items:
        src = Path(it["to"])
        target = Path(it["from"])
        if not src.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if not args.force:
                C.emit({"status": "error",
                        "message": "目标已存在，拒绝覆盖（加 --force 覆盖）: %s" % target}, 1)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(src), str(target))
        restored.append(str(target))
    # 若条目内已无待恢复内容，整个条目（含 _manifest.json）一并移除，避免幽灵条目
    remaining = [p for p in entry.iterdir() if p.name != MANIFEST]
    if not remaining:
        shutil.rmtree(entry, ignore_errors=True)
    else:
        C.write_json(entry / MANIFEST, {**m, "restored_at": C.now_iso(), "restored": restored})
    C.journal(root, "trash.restore", target=args.id, restored=restored)
    C.log("已恢复: %s" % args.id)
    C.emit({"status": "ok", "dry_run": False, "entry": args.id, "restored": restored}, 0)


def cmd_purge(args):
    root = resolve_root(args.root)
    trash = trash_dir(root)
    entries = []
    if args.id:
        e = trash / args.id
        if not e.is_dir():
            C.emit({"status": "error", "message": "条目不存在: %s" % args.id}, 1)
        entries = [e]
    elif args.all or args.older_than is not None:
        cutoff = None
        if args.older_than is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=args.older_than)
        for e in entry_dirs(trash):
            if args.all:
                entries.append(e)
                continue
            m = load_manifest(e)
            t = m.get("time", "")
            try:
                if datetime.datetime.fromisoformat(t) < cutoff:
                    entries.append(e)
            except Exception:
                continue
    else:
        C.emit({"status": "error", "message": "须指定 --id、--all 或 --older-than DAYS"}, 1)

    listing = [str(e) for e in entries]
    if not entries:
        C.emit({"status": "ok", "purged": [], "message": "无匹配条目"}, 0)
    if not args.confirm:
        C.emit({"status": "error",
                "message": "彻底删除不可恢复；确认后加 --confirm（并确保已获用户同意）",
                "would_purge": listing}, 1)

    names = [e.name for e in entries]
    for e in entries:
        shutil.rmtree(e)
    C.journal(root, "trash.purge", target=root, entries=names)
    C.log("已彻底删除 %d 个条目" % len(entries))
    C.emit({"status": "ok", "purged": listing}, 0)


def cmd_status(args):
    start = Path(args.root).expanduser() if args.root else Path.cwd()
    root = C.find_root(start)
    if root is None:
        C.emit({"status": "error",
                "message": "未找到大项目根（缺 %s）；请用 --root 指定" % C.MARKER}, 1)
    trash = trash_dir(root)
    entries = entry_dirs(trash)
    total = 0
    for e in entries:
        for p in e.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    C.emit({"status": "ok", "root": str(root), "trash": str(trash),
            "count": len(entries), "bytes": total}, 0)


def main():
    ap = argparse.ArgumentParser(description="大项目根 .trash 软删除暂存")
    sub = ap.add_subparsers(dest="action", required=True)

    p = sub.add_parser("put", help="移入暂存（默认预演，--apply 执行）")
    p.add_argument("paths", nargs="+", help="要移入的路径")
    p.add_argument("--reason", default="", help="删除原因")
    p.add_argument("--root", help="大项目根（默认从路径向上查找标记）")
    p.add_argument("--apply", action="store_true", help="真正执行（默认仅预演）")
    p.set_defaults(func=cmd_put)

    p = sub.add_parser("list", help="列出暂存条目")
    p.add_argument("--root", help="大项目根")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("restore", help="恢复到原路径（默认预演，--apply 执行）")
    p.add_argument("--id", required=True, help="条目 id")
    p.add_argument("--root", help="大项目根")
    p.add_argument("--apply", action="store_true", help="真正执行（默认仅预演）")
    p.add_argument("--force", action="store_true", help="目标已存在时覆盖")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("purge", help="彻底删除（需 --confirm）")
    p.add_argument("--id", help="条目 id")
    p.add_argument("--all", action="store_true", help="全部条目")
    p.add_argument("--older-than", type=float, default=None, help="早于 N 天的条目")
    p.add_argument("--root", help="大项目根")
    p.add_argument("--confirm", action="store_true", help="确认彻底删除（不可恢复）")
    p.set_defaults(func=cmd_purge)

    p = sub.add_parser("status", help="暂存区统计")
    p.add_argument("--root", help="大项目根")
    p.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
