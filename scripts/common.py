#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""project-organization 公共工具：JSON 输出、根目录标记定位、命名与时间戳。

跨机/跨系统（Windows / Linux / macOS）纯标准库实现，零本机绝对路径。
大项目根位置一律由调用方通过 --root / --path 显式指定。
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

# 大项目根标记文件：某目录含此文件即认定其为 project-organization 管理的大项目根
MARKER = ".bigproject.json"
TRASH_DIR = ".trash"
PROJECTS_DIR = "projects"
SHARED_DIR = "shared"
ARCHIVE_DIR = "archive"
TOOLS_DIR = ".tools"

# 操作日志（append-only JSONL + 派生 Markdown）
JOURNAL_NAME = "journal.jsonl"
JOURNAL_MD = "_log.md"

# 大项目根允许出现的顶层文件/目录（其余视为散落物）
ROOT_ALLOWED_FILES = {MARKER, "README.md", "AGENTS.md", "MEMORY.md"}
ROOT_ALLOWED_DIRS = {PROJECTS_DIR, SHARED_DIR, ARCHIVE_DIR, TOOLS_DIR, TRASH_DIR}

SHARED_SUBDIRS = ["references", "models", "config", "templates", "pipeline"]
SUBPROJECT_SUBDIRS = ["scripts", "data", "results", "output"]


def reconfigure_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def emit(data, code=0):
    """stdout 只输出 JSON；成功/失败用退出码区分。"""
    reconfigure_stdio()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    raise SystemExit(code)


def log(msg):
    """进度/日志写 stderr，不污染 stdout JSON。"""
    reconfigure_stdio()
    print(msg, file=sys.stderr, flush=True)


def slugify(name):
    s = (name or "").strip()
    s = re.sub(r"[\\/:*?\"<>|\s]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s or "project"


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def actor():
    """操作者标识：优先 PROJECT_ORG_ACTOR，其次系统用户名。"""
    return (os.environ.get("PROJECT_ORG_ACTOR")
            or os.environ.get("USERNAME")
            or os.environ.get("USER")
            or "unknown")


def journal_path(root, markdown=False):
    return Path(root) / TOOLS_DIR / (JOURNAL_MD if markdown else JOURNAL_NAME)


def journal(root, event, target=None, **extra):
    """向 <大项目根>/.tools/journal.jsonl 追加一条操作日志（append-only）。

    事件字段：ts / actor / event / target / <extra>。日志失败不阻断主流程（返回 None）。
    """
    try:
        root = Path(root)
        rec = {"ts": now_iso(), "actor": actor(), "event": event}
        if target is not None:
            rec["target"] = str(target)
        rec.update({k: v for k, v in extra.items() if v is not None})
        p = journal_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec
    except Exception:
        return None


def read_journal(root):
    """读取全部日志记录（坏行跳过）。"""
    p = journal_path(root)
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def render_journal(records):
    """把日志记录渲染成 Markdown 表格（用于派生 _log.md）。"""
    lines = ["# 操作日志（_log.md）", "",
             "> 由 `scripts/journal.py --render` 生成；数据源 `.tools/journal.jsonl`（append-only）。", "",
             "| 时间 | 操作者 | 事件 | 对象 | 详情 |",
             "|------|--------|------|------|------|"]
    keys_exclude = {"ts", "actor", "event", "target"}
    for r in records:
        extra = {k: v for k, v in r.items() if k not in keys_exclude}
        detail = json.dumps(extra, ensure_ascii=False) if extra else ""
        detail = detail.replace("|", "\\|")
        lines.append("| %s | %s | %s | %s | %s |" % (
            r.get("ts", ""), r.get("actor", ""), r.get("event", ""),
            str(r.get("target", "")).replace("|", "\\|"), detail))
    return "\n".join(lines) + "\n"


def find_root(start):
    """从 start（文件或目录）向上逐级查找含 MARKER 的大项目根；找不到返回 None。"""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for cand in [p, *p.parents]:
        if (cand / MARKER).is_file():
            return cand
    return None


def is_big_project(path):
    return (Path(path) / MARKER).is_file()


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_template(template_text, mapping):
    out = template_text
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def load_template(name):
    """读取 skill 内 templates/<name>（相对 __file__ 定位，跨机可用）。"""
    tpl = Path(__file__).resolve().parent.parent / "templates" / name
    if tpl.is_file():
        return tpl.read_text(encoding="utf-8")
    return ""
