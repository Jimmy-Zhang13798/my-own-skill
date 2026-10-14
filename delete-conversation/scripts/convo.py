#!/usr/bin/env python3
"""List and permanently delete local Claude Code conversations.

  convo.py list [--grep TEXT]        list sessions (newest first), optionally filtered
  convo.py show SESSION_ID           print every user message of one session
  convo.py delete SESSION_ID [...]   delete all local traces of the given sessions
"""
import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.expanduser("~/.claude")
PROJECTS = os.path.join(ROOT, "projects")
HISTORY = os.path.join(ROOT, "history.jsonl")
CONFIG = os.path.expanduser("~/.claude.json")
CONFIG_BACKUPS = os.path.join(ROOT, "backups", ".claude.json.backup.*")


def user_texts(path):
    """Yield the text of each real (typed) user message in a transcript."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user" or d.get("isMeta"):
                continue
            c = (d.get("message") or {}).get("content")
            if isinstance(c, list):
                c = " ".join(p.get("text", "") for p in c
                             if isinstance(p, dict) and p.get("type") == "text")
            if isinstance(c, str) and c.strip() and not c.lstrip().startswith("<"):
                yield c.strip()


def title_of(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"customTitle"' in line or '"summary"' in line:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                t = d.get("customTitle") or d.get("summary")
                if t:
                    return t
    return ""


def sessions():
    for path in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        sid = os.path.basename(path)[:-6]
        yield sid, os.path.basename(os.path.dirname(path)), path


def find_paths(sid):
    """Every file or directory named after the session."""
    pats = [
        os.path.join(PROJECTS, "*", sid + ".jsonl"),
        os.path.join(PROJECTS, "*", sid),
        os.path.join(ROOT, "session-env", sid),
        os.path.join(ROOT, "file-history", sid),
        os.path.join(ROOT, "todos", sid + "*"),
        os.path.join(ROOT, "debug", sid + "*"),
        os.path.join(ROOT, "tasks", sid + "*"),
    ]
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return sorted(set(out))


def scrub(obj, sid):
    """Drop dict entries and list items that mention sid; return how many."""
    n = 0
    if isinstance(obj, dict):
        for k in list(obj):
            v = obj[k]
            if sid in k or (isinstance(v, str) and sid in v):
                del obj[k]
                n += 1
            else:
                n += scrub(v, sid)
    elif isinstance(obj, list):
        for i in reversed(range(len(obj))):
            v = obj[i]
            if isinstance(v, str) and sid in v:
                del obj[i]
                n += 1
            else:
                n += scrub(v, sid)
    return n


def scrub_config_files(sid):
    """Remove the session from ~/.claude.json and its backups (e.g. lastSessionId)."""
    for fp in [CONFIG] + sorted(glob.glob(CONFIG_BACKUPS)):
        try:
            with open(fp, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if sid not in text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            print("skipped %s: not valid JSON" % fp)
            continue
        n = scrub(data, sid)
        if not n:
            continue
        tmp = fp + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.chmod(tmp, os.stat(fp).st_mode & 0o777)
        os.replace(tmp, fp)
        print("removed %d entr%s from %s" % (n, "y" if n == 1 else "ies", fp))


def cmd_list(args):
    rows = []
    for sid, proj, path in sessions():
        msgs = list(user_texts(path))
        hay = (title_of(path) + "\n" + "\n".join(msgs)).lower()
        if args.grep and args.grep.lower() not in hay:
            continue
        rows.append((os.path.getmtime(path), sid, proj, title_of(path),
                     msgs[0] if msgs else "", len(msgs)))
    rows.sort(reverse=True)
    for mtime, sid, proj, title, first, n in rows:
        when = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print("%s  %s  [%s]  %d msgs" % (sid, when, proj, n))
        if title:
            print("    title: %s" % title[:100])
        print("    first: %s" % first.replace("\n", " ")[:120])
    if not rows:
        print("no matching sessions")


def cmd_show(args):
    hits = [p for sid, _, p in sessions() if sid == args.sid]
    if not hits:
        sys.exit("session not found: " + args.sid)
    for i, t in enumerate(user_texts(hits[0]), 1):
        print("%d. %s" % (i, t.replace("\n", " ")[:300]))


def cmd_delete(args):
    for sid in args.sids:
        if len(sid) < 8:
            sys.exit("refusing short id %r: pass the full session id" % sid)
        paths = find_paths(sid)
        if not paths:
            print("%s: no files found" % sid)
        for p in paths:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            print("deleted %s" % p)

        if os.path.exists(HISTORY):
            with open(HISTORY, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            keep = []
            for line in lines:
                try:
                    if json.loads(line).get("sessionId") == sid:
                        continue
                except ValueError:
                    pass
                keep.append(line)
            if len(keep) != len(lines):
                tmp = HISTORY + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.writelines(keep)
                os.chmod(tmp, 0o600)
                os.replace(tmp, HISTORY)
                print("removed %d line(s) from history.jsonl" % (len(lines) - len(keep)))

        scrub_config_files(sid)

        # Report anything that still mentions the session (e.g. other transcripts).
        candidates = [CONFIG]
        for dirpath, _, files in os.walk(ROOT):
            candidates.extend(os.path.join(dirpath, name) for name in files)
        left = []
        for fp in candidates:
            try:
                with open(fp, "rb") as f:
                    if sid.encode() in f.read():
                        left.append(fp)
            except OSError:
                pass
        if left:
            print("%s is still mentioned in:" % sid)
            for fp in left:
                print("    " + fp)
        else:
            print("%s: no remaining references under ~/.claude or ~/.claude.json" % sid)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--grep")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("show")
    p.add_argument("sid")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("delete")
    p.add_argument("sids", nargs="+")
    p.set_defaults(func=cmd_delete)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
