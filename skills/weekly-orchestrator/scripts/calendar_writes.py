#!/usr/bin/env python3
"""Column lock for calendar writes (weekly orchestrator). The orchestrator is the only writer to
the calendar, and every write goes through this script first.

Usage:
  python3 calendar_writes.py plan before.json writes.json [--config workspace.json]
  python3 calendar_writes.py guard before.json writes.json fresh_b.json fresh_jm.json [--config workspace.json]
  python3 calendar_writes.py verify before.json after.json writes.json [--guard guard.json] [--config workspace.json]
  python3 calendar_writes.py shadow before.json writes.json [--config workspace.json]
  python3 calendar_writes.py verify before.json after.json --shadow [--config workspace.json]

before.json / after.json: the calendar table, {"values": [[headers], [row 2], ...]}, header row first.
writes.json: [{"row": 25, "col": "Notes", "value": "...", "by": "planner"}, ...]
  A Status write also carries "check": "pass" (the checker verdict) and needs a Draft URL write for the row.
  col is the header name. Notes and Sources are append-only: give only the new sentence(s);
  the script joins them to the existing text with a space (Sources with "; ").

Config (workspace.json, all optional, generic defaults):
  sources.calendar.tab           tab name used in ranges (default "Calendar")
  calendar.statuses              [Proposed, Planned, Draft ready, Approved, Posted, Cancelled] labels, in that order
  calendar.proof_types           {"Partner": "Partner Win", "Customer": "Customer Proof"}
  calendar.proof_placeholders    {"Partner Win": "Partner news (to confirm)", ...}
  calendar.formula_columns       columns that recalculate on their own (default ["Action needed", "Draft"])

Allowed writes:
  Status          only to Draft ready, only from Planned
  Visual, What's missing, Draft URL       set
  Notes, Sources                           append only
  Original draft  only if empty (written once)
  Final text      only if empty and Status is Posted
  Proof item      proof slots only
  Title / angle   only while it holds a proof placeholder
Everything else is refused: Date, What to post, Pillar, Channel, Action needed, Draft, Row ID,
Week, AM/PM, Content type, Spec, Published link, and any row that does not exist.
Rows with Status Cancelled (set by a person) are never written.

guard: rows can move while a run is in progress (a person deletes, inserts or sorts rows).
  plan prints "guard_ranges", for example ["Calendar!B13:B20", "Calendar!J13:M20"] (Status, and
  Notes, What's missing, Sources and Row ID of the target rows). Read each range just before
  writing, save each exactly as returned ({"range": ..., "values": ...}) and run guard with them.
  For each accepted write it confirms the Row ID still matches the snapshot and that Status has
  not changed (a person may have set Cancelled); if not, the write is refused. Notes and Sources
  are re-appended to the current cell value, so a person's edit made during the run is kept. A
  What's missing cell a person changed during the run is refused.
  guard prints {"accepted", "refused", "changed_by_person", "plan_refused"} and exits 1 only when
  "refused" is not empty. Write only guard's accepted values, save its output as guard.json and
  pass it to verify with --guard. With --guard, verify matches rows by Row ID and lists
  deleted_row_ids, added_row_ids and a count of moved_rows instead of every shifted cell.

plan prints {"accepted": [...], "refused": [...], "guard_ranges": [...]}; exit 1 if any refused.
verify prints every cell that changed between before and after and is not an accepted write; exit 1 if any.
shadow runs the same lock check and prints {"would_write", "would_refuse", "brief_lines"}: one plain
  line per cell for the shadow brief. Nothing is written in shadow mode.
verify --shadow works on any table saved the same way (calendar, proof log): every changed cell is
  reported, because a shadow run writes nothing.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANON = ["Proposed", "Planned", "Draft ready", "Approved", "Posted", "Cancelled"]
SET = {"Visual", "What's missing", "Draft URL"}
APPEND = {"Notes": " ", "Sources": "; "}
VALUE_FLAGS = {"--config", "--guard"}


def load_config(argv):
    p = argv[argv.index("--config") + 1] if "--config" in argv and argv.index("--config") + 1 < len(argv) else None
    if not p:
        for c in (os.path.join(HERE, "workspace.json"), "workspace.json"):
            if os.path.exists(c):
                p = c
                break
    if not p:
        return {}
    return json.load(open(p, encoding="utf-8"))


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


class Ctx:
    def __init__(self, cfg):
        self.st = statuses(cfg)
        self.proof_types = list(cfg_get(cfg, "calendar.proof_types", {"Partner": "Partner Win", "Customer": "Customer Proof"}).values())
        self.placeholders = tuple(cfg_get(cfg, "calendar.proof_placeholders", {}).values())
        self.tab = cfg_get(cfg, "sources.calendar.tab", "Calendar")
        self.formula = set(cfg_get(cfg, "calendar.formula_columns", ["Action needed", "Draft"]))


def load(p):
    v = json.load(open(p, encoding="utf-8"))
    return v.get("values", v) if isinstance(v, dict) else v


def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def grid(values):
    hdr = values[0]
    return hdr, [list(r) + [""] * (len(hdr) - len(r)) for r in values]


def plan(before, writes, cx):
    hdr, g = grid(before)
    acc, ref = [], []
    merged = {}
    rid_i = hdr.index("Row ID") if "Row ID" in hdr else None
    st = cx.st
    for w in writes:
        row, col, val = int(w["row"]), w["col"], w.get("value", "")
        why = None
        if col not in hdr:
            why = f"Unknown column '{col}'."
        elif row < 2 or row > len(g):
            why = f"Row {row} does not exist; the orchestrator never adds rows."
        if why:
            ref.append({**w, "reason": why})
            continue
        ci = hdr.index(col)
        cur = merged.get((row, col), g[row - 1][ci])
        r = dict(zip(hdr, g[row - 1]))
        ct = r.get("Content type", "")
        if r.get("Status") == st["Cancelled"]:
            ref.append({**w, "reason": "Status is Cancelled (set by a person); agents never write to the row."})
            continue
        if col == "Status":
            if val != st["Draft ready"]:
                why = f"Agents set Status only to {st['Draft ready']} (asked: '{val}')."
            elif r.get("Status") != st["Planned"]:
                why = f"Status is '{r.get('Status')}', not {st['Planned']}."
            elif w.get("check") != "pass":
                why = "Draft ready needs the compliance checker's pass on this write (\"check\": \"pass\")."
            elif not any(int(x["row"]) == row and x["col"] == "Draft URL" for x in writes):
                why = "Draft ready needs a Draft URL write for the same row in this batch."
        elif col in SET:
            pass
        elif col in APPEND:
            if val.strip() and val.strip() in cur:
                continue  # already there: skip silently, no duplicate notes
            val = (cur + APPEND[col] + val).strip("; ").strip() if cur.strip() else val
        elif col == "Original draft":
            if cur.strip():
                why = "Original draft is written once and never overwritten."
        elif col == "Final text":
            if r.get("Status") != st["Posted"]:
                why = "Final text is copied only when Status is Posted."
            elif cur.strip():
                why = "Final text is already filled."
        elif col == "Proof item":
            if not any(p and p in ct for p in cx.proof_types):
                why = "Proof item is only for proof slots."
        elif col == "Title / angle":
            if cur not in cx.placeholders:
                why = "Title / angle changes only while it holds the proof placeholder; a person wrote this title."
        else:
            why = f"Column '{col}' is locked for agents."
        if why:
            ref.append({**w, "reason": why})
            continue
        merged[(row, col)] = val
    for (row, col), val in merged.items():
        acc.append({"range": f"{cx.tab}!{col_letter(hdr.index(col))}{row}", "row": row, "col": col, "value": val,
                    "row_id": g[row - 1][rid_i] if rid_i is not None else ""})
    return acc, ref


def guard_ranges(acc, hdr, cx):
    """Ranges to read fresh just before writing: Status and Notes to Row ID of the target rows."""
    if not acc:
        return []
    lo, hi = min(a["row"] for a in acc), max(a["row"] for a in acc)
    b = col_letter(hdr.index("Status"))
    return [f"{cx.tab}!{b}{lo}:{b}{hi}",
            f"{cx.tab}!{col_letter(hdr.index('Notes'))}{lo}:{col_letter(hdr.index('Row ID'))}{hi}"]


def parse_a1(rng):
    m = re.search(r"!\$?([A-Z]+)\$?(\d+)", rng or "")
    if not m:
        return None, None
    c = 0
    for ch in m.group(1):
        c = c * 26 + ord(ch) - 64
    return c - 1, int(m.group(2))


def guard(before, writes, fresh_list, cx):
    """Re-check every accepted write against fresh reads of guard_ranges."""
    hdr, g = grid(before)
    acc, ref = plan(before, writes, cx)
    fresh, covered = {}, set()
    for raw in fresh_list:
        rng = raw.get("range", "") if isinstance(raw, dict) else ""
        vals = raw.get("values", []) if isinstance(raw, dict) else raw
        c0, r0 = parse_a1(rng)
        if c0 is None:
            raise SystemExit("guard: a fresh read has no range (save each read exactly as returned).")
        m = re.search(r":\$?([A-Z]+)\$?(\d+)", rng)
        c1 = parse_a1("!" + m.group(1) + m.group(2))[0] if m else c0
        r1 = int(m.group(2)) if m else r0 + len(vals) - 1
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                covered.add((r, c))
                row = vals[r - r0] if r - r0 < len(vals) else []
                fresh[(r, c)] = row[c - c0] if c - c0 < len(row) else ""
    rid_i, st_i = hdr.index("Row ID"), hdr.index("Status")
    ok, bad, changed = [], [], []
    seen = set()
    for a in acc:
        row, col = a["row"], a["col"]
        ci = hdr.index(col)
        if (row, rid_i) not in covered:
            bad.append({**a, "reason": "Row not in the fresh read; read guard_ranges again."})
            continue
        now_id = fresh.get((row, rid_i), "")
        if now_id != a["row_id"]:
            bad.append({**a, "reason": f"Row ID changed: expected {a['row_id']}, found '{now_id}' (row deleted, inserted or sorted during the run). Not written."})
            continue
        if (row, st_i) not in covered:
            bad.append({**a, "reason": "Status not in the fresh reads; read every guard_ranges range and pass each file."})
            continue
        if fresh[(row, st_i)] != g[row - 1][st_i]:
            bad.append({**a, "reason": f"Status changed during the run ('{g[row - 1][st_i]}' to '{fresh[(row, st_i)]}'). Not written."})
            continue
        b = g[row - 1][ci]
        if (row, ci) in covered:
            cur = fresh[(row, ci)]
            if cur != b:
                if (row, col) not in seen:
                    changed.append({"cell": a["range"], "row_id": a["row_id"], "col": col})
                    seen.add((row, col))
                if col in APPEND:
                    add = [w.get("value", "").strip() for w in writes if int(w["row"]) == row and w["col"] == col]
                    add = [x for x in add if x and x not in cur]
                    val = cur
                    for x in add:
                        val = (val + APPEND[col] + x).strip("; ").strip() if val.strip() else x
                    if val == cur:
                        continue
                    a = {**a, "value": val}
                else:
                    bad.append({**a, "reason": f"{col} was changed by a person during the run. Not written."})
                    continue
        ok.append(a)
    return ok, bad, changed, ref


def positional(argv):
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_FLAGS
        else:
            pos.append(a)
    return pos


def main(argv):
    cx = Ctx(load_config(argv))
    pos = positional(argv)
    need = {"plan": 3, "verify": 3 if "--shadow" in argv else 4, "shadow": 3, "guard": 4}
    if not pos or pos[0] not in need or len(pos) < need[pos[0]]:
        sys.stderr.write(__doc__.strip() + "\n")
        return 2
    mode = pos[0]
    if mode == "plan":
        before = load(pos[1])
        acc, ref = plan(before, json.load(open(pos[2], encoding="utf-8")), cx)
        print(json.dumps({"accepted": acc, "refused": ref, "guard_ranges": guard_ranges(acc, grid(before)[0], cx)},
                         indent=2, ensure_ascii=False))
        return 1 if ref else 0
    if mode == "guard":
        fresh = [json.load(open(p, encoding="utf-8")) for p in pos[3:]]
        ok, bad, changed, pref = guard(load(pos[1]), json.load(open(pos[2], encoding="utf-8")), fresh, cx)
        print(json.dumps({"accepted": ok, "refused": bad, "changed_by_person": changed, "plan_refused": pref},
                         indent=2, ensure_ascii=False))
        return 1 if bad else 0
    if mode == "shadow":
        before = load(pos[1])
        writes = json.load(open(pos[2], encoding="utf-8"))
        acc, ref = plan(before, writes, cx)
        hdr, g = grid(before)
        rid = hdr.index("Row ID") if "Row ID" in hdr else None
        lines, raw = [], {}
        for w in writes:
            if w.get("col") in APPEND:
                raw.setdefault((int(w["row"]), w["col"]), []).append(w.get("value", "").strip())
        for a in acc:
            who = g[a["row"] - 1][rid] if rid is not None else f"row {a['row']}"
            if a["col"] in APPEND:
                label, val = f"{a['col']} (add)", " ".join(raw.get((a["row"], a["col"]), [a["value"]]))
            else:
                label, val = a["col"], a["value"]
            val = val.replace("\n", " ")
            lines.append(f"{who} {label}: {val[:160] + ('...' if len(val) > 160 else '')}")
        for r in ref:
            ok_row = rid is not None and 2 <= int(r["row"]) <= len(g)
            if ok_row and g[int(r["row"]) - 1][hdr.index("Status")] == cx.st["Cancelled"]:
                continue  # Cancelled rows are never mentioned in agent output
            who = g[int(r["row"]) - 1][rid] if ok_row else f"row {r['row']}"
            lines.append(f"{who} {r['col']}: would be refused ({r['reason']})")
        print(json.dumps({"mode": "shadow", "would_write": acc, "would_refuse": ref, "brief_lines": lines},
                         indent=2, ensure_ascii=False))
        return 0
    # verify
    before, after = load(pos[1]), load(pos[2])
    acc, _ = plan(before, [] if "--shadow" in argv else json.load(open(pos[3], encoding="utf-8")), cx)
    gd = {}
    if "--guard" in argv:
        gd = json.load(open(argv[argv.index("--guard") + 1], encoding="utf-8"))
        acc = gd.get("accepted", [])
    ok = {(a["row"], a["col"]): a["value"] for a in acc}
    hdr, gb = grid(before)
    person, person_rows = set(), set()
    if gd:
        person = {c["cell"].split("!")[-1] for c in gd.get("changed_by_person", [])}
        person_rows = {int(r["row"]) for r in gd.get("refused", []) if "changed during the run" in r.get("reason", "")}
    by_person = []
    _, ga = grid(after)
    bad, mismatched = [], []
    moved = {}
    if gd and "Row ID" in hdr:
        # Match rows by Row ID, so a row deleted or inserted by a person is reported once,
        # not as hundreds of changed cells. Cell names use the before-row number.
        rid = hdr.index("Row ID")
        aft = {}
        for r in ga[1:]:
            r = list(r) + [""] * (len(hdr) - len(r))
            if r[rid]:
                aft[r[rid]] = r
        bef_ids = [r[rid] for r in gb[1:] if r[rid]]
        moved = {"deleted_row_ids": [x for x in bef_ids if x not in aft],
                 "added_row_ids": [x for x in aft if x not in set(bef_ids)]}
        pairs = []
        for i in range(1, len(gb)):
            if gb[i][rid] in aft:
                pairs.append((i, gb[i], aft[gb[i][rid]]))
            elif not gb[i][rid] and i < len(ga) and not (list(ga[i]) + [""] * len(hdr))[rid]:
                pairs.append((i, gb[i], ga[i]))  # rows without a Row ID: compare by position
        new_pos = {r[rid]: n for n, r in enumerate(ga) if len(r) > rid and r[rid]}
        old_pos = {r[rid]: n for n, r in enumerate(gb) if r[rid]}
        moved["moved_rows"] = sum(1 for x in bef_ids if x in new_pos and new_pos[x] != old_pos[x])
        ga_by_before = {i: ra for i, _, ra in pairs}
        ga = [ga[0]] + [ga_by_before.get(i, [""] * len(hdr)) for i in range(1, len(gb))]
    for i in range(1, max(len(gb), len(ga))):
        rb = gb[i] if i < len(gb) else [""] * len(hdr)
        ra = ga[i] if i < len(ga) else [""] * len(hdr)
        ra = list(ra) + [""] * (len(hdr) - len(ra))
        if moved and not any(ra) and rb[hdr.index("Row ID")] in moved.get("deleted_row_ids", []):
            continue
        for ci, h in enumerate(hdr):
            if h in cx.formula:
                continue
            if (rb[ci] or "") != (ra[ci] or ""):
                cell = f"{col_letter(ci)}{i + 1}"
                if (i + 1, h) in ok:
                    if ok[(i + 1, h)] != ra[ci]:
                        mismatched.append({"cell": cell, "col": h})
                elif cell in person or (i + 1) in person_rows:
                    by_person.append({"cell": cell, "col": h})
                else:
                    bad.append({"cell": cell, "col": h, "before": rb[ci][:60], "after": ra[ci][:60]})
    missing = []
    if len(ga) >= max([a["row"] for a in acc] + [0]):
        missing = [{"cell": a["range"]} for a in acc
                   if (list(ga[a["row"] - 1]) + [""] * len(hdr))[hdr.index(a["col"])] != a["value"]]
    out = {"unexpected_changes": bad, "value_mismatch": mismatched, "not_written": missing}
    if gd:
        out["changed_by_person_during_run"] = by_person
        out.update(moved)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 1 if bad or mismatched or missing or moved.get("deleted_row_ids") or moved.get("added_row_ids") else 0


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv or len(positional(sys.argv)) < 1:
        sys.stderr.write((__doc__ or "").strip() + "\n")
        sys.exit(2)
    sys.exit(main(sys.argv))
