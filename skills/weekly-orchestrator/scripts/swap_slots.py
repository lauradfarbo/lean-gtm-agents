#!/usr/bin/env python3
"""Evergreen swaps and fallback drafts for blocked rows (weekly orchestrator).

Usage:
  python3 swap_slots.py calendar.json select.json match.json [--config workspace.json]
                        [--drafter-blocked W03-01,...] [--as-of YYYY-MM-DD] [--days 5] [--max-fallbacks 4]

calendar.json: the calendar table (before.json).
select.json:   output of select_rows.py for the same snapshot.
match.json:    output of proof intake's match_proof.py for the same snapshot.

Config (workspace.json, all optional): swaps.types, swaps.source_label, swaps.chapters,
swaps.excluded_chapters, run.swap_days, run.max_fallbacks, visuals.no_repeat_weeks,
calendar.teaser_regex, calendar.blog_id_regex, calendar.statuses, company.approver.name.
--days and --max-fallbacks override the config.

A row is a swap candidate when its date is swap_days (default 5) or fewer away and it cannot be
drafted this run:
  blocked     Planned row the selection marked blocked (not a dependency hold), or a draft row whose
              drafter returned "blocked" this run (--drafter-blocked)
  proof       proof slot that match_proof.py returned as flag with propose_swap true
  dependency  row on a dependency hold ("On hold:" reason) whose Notes already hold a planner
              "Proposed swap" (the planner proposes these after the deadline; this script never does)
Teaser rows waiting on a blog link get a conditional swap ("If the <blog> link is not in Notes ...").

For each candidate the script picks, in one pass so the run never doubles up:
  type     one of swaps.types: the one used least in the row's plan week and the next (calendar
           rows, swaps already proposed in Notes and swaps chosen this run), ties in config order
  chapter  a long-form chapter (swaps.chapters minus swaps.excluded_chapters) not in Sources or swap
           Notes of rows from no_repeat_weeks (default 8) before the row to 14 days after, and not
           chosen for another swap this run. None when no chapters are configured.
chapter is the first free chapter; chapters_available lists all free ones. The orchestrator may pick
another listed chapter that suits the type better (chapter-map.md), as long as no other swap this run
uses it. If the row's Notes already hold "Proposed swap: <type> on <angle> (<source label> ch<N>)",
that proposal is kept (existing: true).

fallback: true when the row's Notes do not yet hold "Fallback draft", up to max_fallbacks per run,
nearest date first. The orchestrator drafts a fallback post for these (make_bundles.py fallback).

Prints {"swaps": [...], "fallbacks_skipped": [...]}. Cancelled rows are never candidates and never
named. The script writes nothing.
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CANON = ["Proposed", "Planned", "Draft ready", "Approved", "Posted", "Cancelled"]
VALUE_FLAGS = {"--config", "--drafter-blocked", "--as-of", "--days", "--max-fallbacks"}
CH = re.compile(r"\bch(?:apter)?\s?(\d+)\b", re.I)


def load_config(argv):
    p = argv[argv.index("--config") + 1] if "--config" in argv and argv.index("--config") + 1 < len(argv) else None
    if not p:
        for c in (os.path.join(HERE, "workspace.json"), "workspace.json"):
            if os.path.exists(c):
                p = c
                break
    return json.load(open(p, encoding="utf-8")) if p else {}


def cfg_get(cfg, path, default):
    cur = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or cur.get(k) is None:
            return default
        cur = cur[k]
    return cur


def statuses(cfg):
    s = cfg_get(cfg, "calendar.statuses", None)
    if isinstance(s, dict):
        return {k: s.get(k, k) for k in CANON}
    if isinstance(s, list) and len(s) == len(CANON):
        return dict(zip(CANON, s))
    return {k: k for k in CANON}


def load(p):
    v = json.load(open(p, encoding="utf-8"))
    return v.get("values", v) if isinstance(v, dict) else v


def parse_date(s):
    s = (s or "").strip()
    for f in ("%a %d %b %y", "%d %b %y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.title() if "%b" in f else s, f).date()
        except ValueError:
            pass
    return None


def fmt(d):
    return f"{d.day:02d} {d.strftime('%b').upper()} {d.strftime('%y')}"


def arg(argv, k, default=None):
    return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else default


def main(argv):
    cfg = load_config(argv)
    st = statuses(cfg)
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_FLAGS
        else:
            pos.append(a)
    values = load(pos[0])
    sel = json.load(open(pos[1], encoding="utf-8"))
    match = json.load(open(pos[2], encoding="utf-8"))
    as_of = date.fromisoformat(arg(argv, "--as-of")) if "--as-of" in argv else date.today()
    days = int(arg(argv, "--days", cfg_get(cfg, "run.swap_days", 5)))
    cap = int(arg(argv, "--max-fallbacks", cfg_get(cfg, "run.max_fallbacks", 4)))
    label = cfg_get(cfg, "swaps.source_label", "Long-form")
    types = list(cfg_get(cfg, "swaps.types", ["Industry POV", "Poll", f"{label} push"]))
    excluded = {str(c) for c in cfg_get(cfg, "swaps.excluded_chapters", [])}
    chapters = [str(c) for c in cfg_get(cfg, "swaps.chapters", []) if str(c) not in excluded]
    weeks_back = int(cfg_get(cfg, "visuals.no_repeat_weeks", 8))
    teaser = re.compile(cfg_get(cfg, "calendar.teaser_regex", r"LinkedIn teaser"), re.I)
    blog_id = re.compile(cfg_get(cfg, "calendar.blog_id_regex", r"^(Blog \d+)"), re.I)
    existing_re = re.compile(r"Proposed swap: (" + "|".join(re.escape(t) for t in types) + r") on (.+?) \("
                             + re.escape(label) + r" ch(\w+)\)", re.I)

    def kind(ct):
        c = (ct or "").lower()
        return next((t for t in types if t.lower() in c), None)

    hdr = values[0]
    rows = {}
    for n, r in enumerate(values[1:], start=2):
        r = list(r) + [""] * (len(hdr) - len(r))
        d = dict(zip(hdr, r))
        d["_row"], d["_date"] = n, parse_date(d.get("Date"))
        rows[n] = d

    dblocked = [x for x in (arg(argv, "--drafter-blocked", "") or "").split(",") if x]
    cands = []
    for it in sel.get("rows", []):
        if it.get("action") == "draft" and it.get("row_id") in dblocked:
            it = {**it, "action": "blocked", "reason": "drafter returned blocked"}
        if it.get("action") != "blocked":
            continue
        r = rows.get(it["row"])
        if not r or r.get("Status") == st["Cancelled"] or not r["_date"] or r["_date"] < as_of:
            continue
        if (it.get("reason") or "").startswith("On hold:"):
            if existing_re.search(r.get("Notes", "")):
                cands.append((r, "dependency"))
        elif (r["_date"] - as_of).days <= days:
            cands.append((r, "blocked"))
    for s in match.get("slots", []):
        r = rows.get(s.get("row"))
        if not r or r.get("Status") == st["Cancelled"]:
            continue
        if s.get("action") == "flag" and (s.get("propose_swap") or existing_re.search(r.get("Notes", ""))):
            if r["_date"] and 0 <= (r["_date"] - as_of).days <= days:
                cands.append((r, "proof"))
    cands.sort(key=lambda c: (c[0]["_date"], c[0]["_row"]))

    chosen, out, skipped = [], [], []
    n_fb = 0
    for r, reason in cands:
        notes = r.get("Notes", "")
        m = existing_re.search(notes)
        item = {"row": r["_row"], "row_id": r.get("Row ID"), "date": fmt(r["_date"]),
                "days_to": (r["_date"] - as_of).days, "reason": reason,
                "original": {"content_type": r.get("Content type"), "title": r.get("Title / angle")}}
        ct = r.get("Content type", "")
        if teaser.search(ct):
            b = blog_id.search(ct)
            name = b.group(1) if b else "blog"
            blog = next((x for x in rows.values() if b and x is not r and blog_id.search(x.get("Content type", "") or "")
                         and blog_id.search(x.get("Content type", "")).group(1).lower() == name.lower()
                         and not teaser.search(x.get("Content type", ""))), None)
            when = blog["_date"] if blog and blog["_date"] else r["_date"]
            item["conditional"] = f"If the {name} link is not in Notes on the blog row by the morning of {fmt(when)}"
        if m:
            t = next((k for k in types if k.lower() == m.group(1).lower()), m.group(1))
            item.update(existing=True, type=t, angle=m.group(2), chapter=m.group(3))
        else:
            wk = str(r.get("Week", "")).strip()
            nxt = str(int(wk) + 1) if wk.isdigit() else ""
            counts = {t: 0 for t in types}
            for x in rows.values():
                if str(x.get("Week", "")).strip() in (wk, nxt) and x.get("Status") != st["Cancelled"]:
                    em = existing_re.search(x.get("Notes", ""))
                    if em:
                        counts[next(k for k in types if k.lower() == em.group(1).lower())] += 1
                    elif kind(x.get("Content type")):
                        counts[kind(x.get("Content type"))] += 1
            for c in chosen:
                if c["week"] in (wk, nxt):
                    counts[c["type"]] = counts.get(c["type"], 0) + 1
            t = min(types, key=lambda k: (counts[k], types.index(k)))
            used = {str(c["chapter"]) for c in chosen if c["chapter"] is not None}
            for x in rows.values():
                if x["_date"] and r["_date"] - timedelta(weeks=weeks_back) <= x["_date"] <= r["_date"] + timedelta(days=14):
                    used |= set(CH.findall(x.get("Sources", "")))
                    em = existing_re.search(x.get("Notes", ""))
                    if em:
                        used.add(em.group(3))
            free = [c for c in chapters if c not in used]
            item.update(existing=False, type=t, chapter=free[0] if free else None, chapters_available=free, angle=None)
        chosen.append({"week": str(r.get("Week", "")).strip(), "type": item["type"], "chapter": item["chapter"]})
        if "Fallback draft" in notes:
            item["fallback"] = False
        elif n_fb < cap:
            item["fallback"] = True
            n_fb += 1
        else:
            item["fallback"] = False
            skipped.append(item["row_id"])
        out.append(item)

    print(json.dumps({"as_of": fmt(as_of), "source_label": label, "swaps": out, "fallbacks_skipped": skipped},
                     indent=2, ensure_ascii=False))
    return 0


def _usage_ok(argv, n):
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_FLAGS
        else:
            pos.append(a)
    if "-h" in argv or "--help" in argv or len(pos) < n:
        sys.stderr.write((__doc__ or "").strip() + "\n")
        return False
    return True


if __name__ == "__main__":
    if not _usage_ok(sys.argv, 3):
        sys.exit(2)
    sys.exit(main(sys.argv))
