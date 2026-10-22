#!/usr/bin/env python3
"""Match proof log items to proof slots (for example Partner Win and Customer Proof) on the calendar.

Usage:
  python3 match_proof.py calendar.json proof_log.json --config workspace.json [--as-of YYYY-MM-DD] [--horizon 14] [--shadow]

calendar.json: the Calendar tab as {"values": [[headers], ...]} (A1:V), header row first.
proof_log.json: the Proof log tab (A1:J), header row first.
workspace.json: the client config. Uses calendar.proof_types (proof log Type to content type),
  calendar.proof_placeholders (placeholder titles), run.swap_days (default 5) and
  company.approver.name (whose notes on a slot are conditions).
--as-of: run date. Defaults to today. Use only for tests.
--shadow: shadow mode. Slots are proof rows with any Status except Proposed or Cancelled, and the
  Proof item cell may be filled. A slot whose proof item a person already chose (row number in
  Proof item, or the proof log's "Used in calendar row" naming this Row ID) is drafted from that
  item if it is still signed off and public by the slot date; otherwise the slot is flagged with
  chosen_item_unusable and is never matched to a different item.

Prints a JSON plan. It writes nothing; the skill acts on the plan.
Rules:
- An item is usable when Sign-off status is Yes, Organization, What happened and Sign-off from are
  filled, Can go public from is a date on or before the slot date, and "Used in calendar row" is empty.
- A quote is usable only if it carries an attribution after it (dash, comma or brackets).
- Slots are Planned rows whose Content type is a proof type, Proof item (R) empty, dated from the
  run date to run date + horizon days. Cancelled rows are never slots and never reported.
- Slots are filled in date order with the earliest-logged usable item of the matching type.
- Each slot reports title_placeholder: true when Title / angle still holds the configured placeholder.
- A pending item reports signoff_cutoff (slot date minus swap_days) and cutoff_passed.
- already_flagged: the slot's Notes already hold a Proof intake note naming every relevant item
  (and, for a pending item past its cut-off, saying so), and no swap is newly due.
- An unfilled slot is flagged. A swap is proposed when the slot is swap_days away or fewer,
  or when a matching item has Sign-off status No.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta

DEFAULT_PROOF_TYPES = {"Partner": "Partner Win", "Customer": "Customer Proof"}


def parse_date(s):
    s = str(s or "").strip()
    if not s:
        return None
    for fmt in ("%a %d %b %y", "%d %b %y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s.title() if "%b" in fmt or "%B" in fmt or "%a" in fmt else s, fmt).date()
        except ValueError:
            continue
    return None


def fmt(d):
    return f"{d.day:02d} {d.strftime('%b').upper()} {d.strftime('%y')}"  # 03 NOV 26


def rows_as_dicts(values):
    if isinstance(values, dict):
        values = values.get("values", [])
    if not values:
        return []
    hdr = values[0]
    out = []
    for n, r in enumerate(values[1:], start=2):
        r = list(r) + [""] * (len(hdr) - len(r))
        out.append({"_row": n, **{h: (str(r[i]) if r[i] is not None else "") for i, h in enumerate(hdr)}})
    return out


def quote_ok(q):
    q = q.strip()
    if not q:
        return True, ""
    m = re.match(r'^[“"](.+?)[”"]\s*(?:-|–|,|\()\s*(.+?)\)?\s*$', q, re.S)
    if not m:
        return False, "Quote has no attribution after it, or is not in quotation marks"
    return True, ""


def arg_value(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def main(argv):
    cal_path, log_path = argv[1], argv[2]
    cfg = json.load(open(arg_value(argv, "--config"), encoding="utf-8"))
    cal_cfg = cfg.get("calendar", {}) or {}
    proof_types = cal_cfg.get("proof_types") or DEFAULT_PROOF_TYPES
    type_map = {k.strip().lower(): v for k, v in proof_types.items()}
    placeholders = cal_cfg.get("proof_placeholders") or {}
    swap_days = int((cfg.get("run", {}) or {}).get("swap_days", 5))
    approver = str(((cfg.get("company", {}) or {}).get("approver", {}) or {}).get("name", "")).strip()
    approver_first = approver.split()[0] if approver else ""

    as_of = date.today()
    horizon = 14
    if arg_value(argv, "--as-of"):
        as_of = datetime.strptime(arg_value(argv, "--as-of"), "%Y-%m-%d").date()
    if arg_value(argv, "--horizon"):
        horizon = int(arg_value(argv, "--horizon"))
    shadow = "--shadow" in argv
    cal = rows_as_dicts(json.load(open(cal_path, encoding="utf-8")))
    log = rows_as_dicts(json.load(open(log_path, encoding="utf-8")))

    items, problems = [], []
    for it in log:
        if not any(str(v).strip() for k, v in it.items() if k != "_row"):
            continue
        typ = type_map.get(it.get("Type", "").strip().lower())
        pub = parse_date(it.get("Can go public from", ""))
        signoff = it.get("Sign-off status", "").strip().capitalize()
        used = it.get("Used in calendar row (agent fills)", "").strip()
        q_ok, q_issue = quote_ok(it.get("Approved quote (verbatim)", ""))
        issues = []
        if not typ:
            issues.append("Type must be one of: " + ", ".join(proof_types))
        if signoff == "Yes":
            if not it.get("Organization", "").strip():
                issues.append("Organization is empty")
            if not it.get("What happened", "").strip():
                issues.append("What happened is empty")
            if not it.get("Sign-off from (name)", "").strip():
                issues.append("Sign-off from (name) is empty")
            if not pub:
                issues.append("Can go public from is missing or not a date")
        items.append({
            "proof_row": it["_row"], "type": typ, "organization": it.get("Organization", ""),
            "signoff": signoff or "Blank", "public_from": pub, "used": used,
            "quote_usable": q_ok, "quote_issue": q_issue, "issues": issues,
            "logged": parse_date(it.get("Date logged", "")) or date.max,
        })
        if issues or not q_ok:
            problems.append({"proof_row": it["_row"], "organization": it.get("Organization", ""),
                             "issues": issues + ([q_issue + ": draft without the quote"] if not q_ok else [])})

    slots = []
    for r in cal:
        d = parse_date(r.get("Date", ""))
        if not d or r.get("Content type", "").strip() not in type_map.values():
            continue
        status = r.get("Status", "").strip()
        if shadow:
            if status in ("Proposed", "Cancelled", ""):
                continue
        elif status != "Planned" or r.get("Proof item", "").strip():
            continue
        if as_of <= d <= as_of + timedelta(days=horizon):
            m = re.search(r"range=[A-Z]+(\d+)|\brow (\d+)", r.get("Proof item", ""), re.I)
            chosen = int(m.group(1) or m.group(2)) if m else None
            slots.append({"row": r["_row"], "row_id": r.get("Row ID", ""), "date": d,
                          "type": r["Content type"].strip(), "notes": r.get("Notes", ""),
                          "title": r.get("Title / angle", ""), "live_status": status, "chosen": chosen})
    slots.sort(key=lambda s: s["date"])

    def person_note(notes):
        if not approver_first:
            return ""
        keys = {approver_first, approver} - {""}
        return " ".join(x for x in re.split(r"(?<=\.)\s+", notes)
                        if any(x.startswith(k + ",") or f"({k}," in x for k in keys))

    taken = set()
    plan = []
    no_flagged_types = set()
    for s in slots:
        cands = [i for i in items if i["type"] == s["type"] and not i["used"] and not i["issues"]
                 and i["signoff"] == "Yes" and i["public_from"] and i["public_from"] <= s["date"]
                 and i["proof_row"] not in taken]
        cands.sort(key=lambda i: (i["logged"], i["proof_row"]))
        chosen_by_person = []
        if shadow:
            chosen_by_person = [i for i in items if i["proof_row"] == s["chosen"]
                                or (s["row_id"] and i["used"].startswith(s["row_id"]))]
            if chosen_by_person:
                # A person already chose the proof for this slot: draft from that item or flag; never rematch.
                cands = [i for i in chosen_by_person if i["type"] == s["type"] and not i["issues"]
                         and i["signoff"] == "Yes" and i["public_from"] and i["public_from"] <= s["date"]
                         and i["proof_row"] not in taken]
        days = (s["date"] - as_of).days
        placeholder = placeholders.get(s["type"], "")
        entry = {"row": s["row"], "row_id": s["row_id"], "date": fmt(s["date"]), "type": s["type"],
                 "days_to_slot": days, **({"live_status": s["live_status"]} if shadow else {}),
                 "title_placeholder": bool(placeholder) and s["title"].strip() == placeholder.strip(),
                 "person_note": person_note(s["notes"])}
        if cands:
            c = cands[0]
            taken.add(c["proof_row"])
            entry.update(action="draft", proof_row=c["proof_row"], organization=c["organization"],
                         use_quote=c["quote_usable"], public_from=fmt(c["public_from"]),
                         do_not_post_before=fmt(c["public_from"]) if c["public_from"] > as_of else "")
        elif chosen_by_person:
            c = chosen_by_person[0]
            entry.update(action="flag", propose_swap=False, already_flagged=False, signoff_no=[], pending=[],
                         public_after_slot=[],
                         chosen_item_unusable={"proof_row": c["proof_row"], "organization": c["organization"],
                                               "signoff": c["signoff"], "issues": c["issues"],
                                               "public_from": fmt(c["public_from"]) if c["public_from"] else ""})
        else:
            no_items = [i for i in items if i["type"] == s["type"] and not i["used"] and i["signoff"] == "No"]
            waiting = [i for i in items if i["type"] == s["type"] and not i["used"]
                       and i["signoff"] not in ("Yes", "No")]
            later = [i for i in items if i["type"] == s["type"] and not i["used"] and i["signoff"] == "Yes"
                     and i["public_from"] and i["public_from"] > s["date"] and i["proof_row"] not in taken]
            first_no = bool(no_items) and s["type"] not in no_flagged_types
            if first_no:
                no_flagged_types.add(s["type"])
            cutoff = s["date"] - timedelta(days=swap_days)
            cutoff_passed = as_of > cutoff
            cutoff_text = f"cut-off of {fmt(cutoff)} has passed"
            # Flag again only when something changed: an item not yet named in Notes, a pending
            # item whose cut-off has now passed, or a swap now due and not yet proposed.
            named = no_items if first_no else []
            new_items = [i for i in named + waiting + later
                         if f"Proof log row {i['proof_row']}" not in s["notes"]]
            newly_late = [i for i in waiting if cutoff_passed and cutoff_text not in s["notes"]]
            swap = (days <= swap_days or first_no) and "Proposed swap" not in s["notes"]
            already = "Proof intake" in s["notes"] and not new_items and not newly_late and not swap
            entry.update(
                action="flag",
                propose_swap=swap,
                already_flagged=already,
                signoff_no=[{"proof_row": i["proof_row"], "organization": i["organization"]} for i in no_items] if first_no else [],
                pending=[{"proof_row": i["proof_row"], "organization": i["organization"], "signoff": i["signoff"],
                          "signoff_cutoff": fmt(cutoff), "cutoff_passed": cutoff_passed} for i in waiting],
                public_after_slot=[{"proof_row": i["proof_row"], "organization": i["organization"],
                                    "public_from": fmt(i["public_from"])} for i in later],
            )
        plan.append(entry)

    waiting_items = []
    for i in items:
        if i["signoff"] == "Yes" and not i["used"] and not i["issues"] and i["proof_row"] not in taken:
            later_slot = next((r for r in sorted(cal, key=lambda r: parse_date(r.get("Date", "")) or date.max)
                               if r.get("Content type", "").strip() == i["type"] and r.get("Status") == "Planned"
                               and not r.get("Proof item", "").strip()
                               and parse_date(r.get("Date", "")) and i["public_from"]
                               and parse_date(r.get("Date", "")) >= i["public_from"]
                               and parse_date(r.get("Date", "")) > as_of + timedelta(days=horizon)), None)
            waiting_items.append({"proof_row": i["proof_row"], "organization": i["organization"],
                                  "next_slot": later_slot["Row ID"] if later_slot else "none in calendar",
                                  "next_slot_date": fmt(parse_date(later_slot["Date"])) if later_slot else ""})

    mark_no = [{"proof_row": i["proof_row"], "organization": i["organization"]}
               for i in items if i["signoff"] == "No" and not i["used"]]

    out = {"mode": "shadow" if shadow else "normal", "as_of": fmt(as_of), "horizon_days": horizon,
           "swap_days": swap_days, "slots": plan, "signed_off_waiting": waiting_items,
           "mark_not_used_signoff_no": mark_no, "proof_log_problems": problems}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _usage_ok(argv, n, required=("--config",)):
    """Print the usage message instead of a traceback when arguments are missing."""
    flags_no_value = {"--shadow", "--live", "--help", "-h"}
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a not in flags_no_value
        else:
            pos.append(a)
    missing = [r for r in required if arg_value(argv, r) is None]
    if "-h" in argv or "--help" in argv or len(pos) < n or missing:
        sys.stderr.write((__doc__ or "").strip() + "\n")
        return False
    return True


if __name__ == "__main__":
    if not _usage_ok(sys.argv, 2):
        sys.exit(2)
    sys.exit(main(sys.argv))
