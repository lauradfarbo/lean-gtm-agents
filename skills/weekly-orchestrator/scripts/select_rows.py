#!/usr/bin/env python3
"""Decide what the weekly run does with each calendar row (weekly orchestrator).

Usage:
  python3 select_rows.py calendar.json [--config workspace.json] [--facts facts.json] [--as-of YYYY-MM-DD]
                         [--horizon 13] [--briefs YYYY-MM-DD,...] [--rerun] [--shadow]

calendar.json: the calendar table, {"values": [[headers], [row 2], ...]}, header row first.
--briefs: dates of the weekly briefs already in the briefs folder of the mode in use (from their
  titles). A date may appear more than once when a rerun brief exists.
--rerun: the person said "rerun": a same-day brief does not stop the run.
--shadow: shadow mode. Rows that are Planned, Draft ready, Approved or Posted are all selected
  for drafting, because live rows are still produced by hand. Proposed and team-owned rows are
  still never drafted. Each item carries live_status.

Config (workspace.json, all optional, generic defaults):
  company.approver.name, run.horizon_days, run.weekday, channels,
  calendar.team_owned_regex, calendar.proof_types, calendar.teaser_regex, calendar.blog_id_regex,
  calendar.statuses, facts.id_col, facts.status_col, facts.approved_values,
  plan.dependencies (fact_id, label, optional row_regex, hold_regex): a Planned row whose Content
  type, Title / angle or Notes match row_regex, name the label or name the fact ID is blocked
  while the fact is not approved.

Prints a JSON plan. It writes nothing.

Row actions for rows dated from the run date to run date + horizon days, plus overdue rows:
  draft          Planned row on a configured channel for the short-form drafter
  proof          Planned proof slot for proof intake
  team_owned     content the team produces (team_owned_regex): never drafted
  proposed       Status Proposed: not drafted, flagged for the approver
  blocked        Planned, but a dependency is missing (reason given)
  in_review      Draft ready or Approved: nothing to do
  overdue        Date passed and not Posted: listed in the brief
Cancelled rows (set by a person) are skipped everywhere and never appear in this output, so they
never reach the brief, the run summary or a notification. "_internal" holds a count for run
checks only; never quote it.
Also:
  final_text       Posted rows with a Draft URL and an empty Final text (any date)
  missed_runs      run days since the last brief with no brief
  approved_gaps    Approved rows due within 2 days whose What's missing is still filled
  same_day_brief   true when a brief for the run date already exists; with "stop": true the
                   orchestrator stops and tells the person, unless they said "rerun"
  brief_suffix     "" for the first brief of the day, " (2)", " (3)" for reruns
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CANON = ["Proposed", "Planned", "Draft ready", "Approved", "Posted", "Cancelled"]
VALUE_FLAGS = {"--config", "--facts", "--as-of", "--horizon", "--briefs"}
URL = re.compile(r"https?://\S+")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


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


def approver(cfg, cap=True):
    n = cfg_get(cfg, "company.approver.name", "")
    return n if n else ("The approver" if cap else "the approver")


def parse_date(s):
    s = (s or "").strip()
    for f in ("%a %d %b %y", "%d %b %y", "%Y-%m-%d", "%d %b %Y"):
        try:
            return datetime.strptime(s.title() if "%b" in f else s, f).date()
        except ValueError:
            pass
    return None


def fmt(d):
    return f"{d.day:02d} {d.strftime('%b').upper()} {d.strftime('%y')}"  # zero-padded: 03 NOV 26


def arg(argv, k, default=None):
    return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else default


def facts_status(path, cfg):
    fv = json.load(open(path, encoding="utf-8"))
    fv = fv.get("values", fv) if isinstance(fv, dict) else fv
    hdr = [h.strip() for h in fv[0]]
    id_c, st_c = cfg_get(cfg, "facts.id_col", "ID"), cfg_get(cfg, "facts.status_col", "Status")
    i_id = hdr.index(id_c) if id_c in hdr else 0
    i_st = hdr.index(st_c) if st_c in hdr else 3
    out = {}
    for r in fv[1:]:
        r = list(r) + [""] * len(hdr)
        if r[i_id].strip():
            out[r[i_id].strip().upper()] = r[i_st].strip()
    return out


def depends(row, dep):
    text = " ".join(row.get(k, "") or "" for k in ("Notes", "Title / angle", "Content type")).lower()
    label = (dep.get("label") or "").lower()
    fid = (dep.get("fact_id") or "").lower()
    rx = dep.get("row_regex")
    if rx and re.search(rx, text, re.I):
        return True
    if label and label in text:
        return True
    if fid and re.search(r"\b" + re.escape(fid) + r"\b", text):
        return True
    hr = dep.get("hold_regex")
    return bool(hr and label and re.search(hr, row.get("Notes", "") or "", re.I) and label in text)


def main(argv):
    cfg = load_config(argv)
    st = statuses(cfg)
    who = approver(cfg)
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_FLAGS
        else:
            pos.append(a)
    v = json.load(open(pos[0], encoding="utf-8"))
    v = v.get("values", v) if isinstance(v, dict) else v
    as_of = date.fromisoformat(arg(argv, "--as-of")) if "--as-of" in argv else date.today()
    horizon = int(arg(argv, "--horizon", cfg_get(cfg, "run.horizon_days", 13)))
    shadow = "--shadow" in argv
    briefs = [date.fromisoformat(x) for x in (arg(argv, "--briefs", "") or "").split(",") if x.strip()]
    team = re.compile(cfg_get(cfg, "calendar.team_owned_regex", r"Publish|Newsletter|Distribute"), re.I)
    proof_types = [p for p in cfg_get(cfg, "calendar.proof_types", {"Partner": "Partner Win", "Customer": "Customer Proof"}).values() if p]
    proof_re = re.compile("|".join(re.escape(p) for p in proof_types), re.I) if proof_types else None
    teaser = re.compile(cfg_get(cfg, "calendar.teaser_regex", r"LinkedIn teaser"), re.I)
    blog_id = re.compile(cfg_get(cfg, "calendar.blog_id_regex", r"^(Blog \d+)"), re.I)
    channels = [c.lower() for c in cfg_get(cfg, "channels", ["LinkedIn"])]
    weekday = cfg_get(cfg, "run.weekday", "Monday").strip().lower()
    run_wd = WEEKDAYS.index(weekday) if weekday in WEEKDAYS else 0
    approved_vals = cfg_get(cfg, "facts.approved_values", ["Approved", "Approved with edits"])
    fstat = facts_status(arg(argv, "--facts"), cfg) if arg(argv, "--facts") else None
    deps = cfg_get(cfg, "plan.dependencies", [])
    open_deps = [d for d in deps if fstat is not None and fstat.get((d.get("fact_id") or "").upper()) not in approved_vals]

    hdr = v[0]
    rows = []
    for n, r in enumerate(v[1:], start=2):
        r = list(r) + [""] * (len(hdr) - len(r))
        d = dict(zip(hdr, r))
        d["_row"], d["_date"] = n, parse_date(d.get("Date"))
        rows.append(d)

    end = as_of + timedelta(days=horizon)
    plan, final_text, gaps = [], [], []
    cancelled = 0
    for r in rows:
        if not r["_date"]:
            continue
        s, ct = r.get("Status", ""), r.get("Content type", "")
        if s == st["Cancelled"]:
            cancelled += 1
            continue
        overdue = r["_date"] < as_of
        wm = (r.get("What's missing") or "").strip()
        if s == st["Approved"] and wm and 0 <= (r["_date"] - as_of).days <= 2:
            gaps.append({"row": r["_row"], "row_id": r.get("Row ID"), "date": fmt(r["_date"]), "whats_missing": wm,
                         "brief_line": f"{r.get('Row ID')} ({fmt(r['_date'])}) is Approved but What's missing still says: "
                                       f"\"{wm}\". {who} to confirm it is resolved before it posts."})
        if s == st["Posted"]:
            if r.get("Draft URL") and not r.get("Final text"):
                final_text.append({"row": r["_row"], "row_id": r.get("Row ID"), "draft_url": r.get("Draft URL")})
            if not (shadow and not overdue and r["_date"] <= end):
                continue
        if not overdue and r["_date"] > end:
            continue
        item = {"row": r["_row"], "row_id": r.get("Row ID"), "date": fmt(r["_date"]), "week": r.get("Week"),
                "content_type": ct, "status": s, "title": r.get("Title / angle")}
        if shadow:
            item["live_status"] = s
            if s in (st["Draft ready"], st["Approved"], st["Posted"]):
                s = st["Planned"]  # shadow drafts these too; nothing is written to the row
        dep = next((d for d in open_deps if depends(r, d)), None)
        if overdue:
            item["action"] = "overdue"
        elif team.search(ct):
            item["action"] = "team_owned"
        elif s == st["Proposed"]:
            item["action"] = "proposed"
            item["reason"] = f"Status is Proposed: {who} to review and set Planned before it can be drafted."
        elif s in (st["Draft ready"], st["Approved"]):
            item["action"] = "in_review"
        elif s != st["Planned"]:
            item["action"] = "blocked"
            item["reason"] = f"Status '{s}' is not one the run acts on."
        elif channels and not any(c in (r.get("Channel", "") or "").lower() for c in channels):
            item["action"] = "blocked"
            item["reason"] = "Channel is not one the agents draft for."
        elif proof_re and proof_re.search(ct):
            item["action"] = "proof"
        elif dep:
            item["action"] = "blocked"
            item["reason"] = f"On hold: {dep.get('label') or 'dependency'} (fact {dep.get('fact_id')}) is not approved. Not drafted."
        elif teaser.search(ct):
            m = blog_id.search(ct)
            blog = None
            if m:
                blog = next((b for b in rows if b is not r and blog_id.search(b.get("Content type", "") or "")
                             and blog_id.search(b.get("Content type", "")).group(1).lower() == m.group(1).lower()
                             and not teaser.search(b.get("Content type", "")) and b.get("Status") != st["Cancelled"]), None)
            link = URL.findall(blog.get("Notes", "")) if blog else []
            label = m.group(1) if m else "blog"
            if not link:
                item["action"] = "blocked"
                item["reason"] = f"Published {label} link is not in Notes on the blog row ({blog.get('Row ID') if blog else 'not found'})."
                item["whats_missing"] = f"Published {label} link in Notes on {blog.get('Row ID') if blog else 'the blog row'}."
            else:
                item["action"] = "draft"
                item["blog_link"] = link[-1]
                item["blog_row_id"] = blog.get("Row ID")
        else:
            item["action"] = "draft"
        plan.append(item)

    missed = []
    if briefs:
        last = max(briefs)
        d = last + timedelta(days=(run_wd - last.weekday()) % 7 or 7)
        while d <= as_of:
            if d not in briefs and d != as_of:
                missed.append(fmt(d))
            d += timedelta(days=7)

    same = briefs.count(as_of)
    rerun = "--rerun" in argv
    out = {"mode": "shadow" if shadow else "normal", "as_of": fmt(as_of), "window": f"{fmt(as_of)} to {fmt(end)}",
           "same_day_brief": same > 0, "stop": same > 0 and not rerun,
           "brief_suffix": f" ({same + 1})" if same and rerun else "",
           "rows": plan, "final_text": final_text, "missed_runs": missed, "approved_gaps": gaps,
           "counts": {a: sum(1 for p in plan if p["action"] == a) for a in
                      ("draft", "proof", "team_owned", "proposed", "blocked", "in_review", "overdue")},
           "_internal": {"cancelled_skipped": cancelled}}
    if out["stop"]:
        out["stop_message"] = f"A brief for {fmt(as_of)} already exists. Say rerun to run again."
    print(json.dumps(out, indent=2, ensure_ascii=False))
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
    if not _usage_ok(sys.argv, 1):
        sys.exit(2)
    sys.exit(main(sys.argv))
