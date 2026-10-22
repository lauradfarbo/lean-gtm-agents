#!/usr/bin/env python3
"""Validate a workspace.json before any agent uses it (workspace-setup).

Usage:
  python3 check_workspace.py workspace.json

Checks:
  errors    required sections and sources missing, unknown platform or kind, a write target
            (calendar, proof_log, drafts_folder, briefs_folder) with no TEST copy, placeholder
            values such as "<Sheet ID>", regexes that do not compile, bad word counts or dates
  warnings  recommended sources missing, docs with no expect_phrase, a missing approver,
            empty competitor or avoid lists
Prints {"ok": bool, "errors": [...], "warnings": [...], "sources": {...}}. Exit 1 on any error.
Writes nothing.
"""
import json
import re
import sys
from datetime import date

PLATFORMS = {"google_drive", "notion", "github", "sharepoint", "local", "url", "manual"}
KINDS = {"doc", "table", "file", "folder", "repo"}
REQUIRED = ["rules", "voice_guide", "facts_sheet", "calendar", "drafts_folder", "briefs_folder"]
RECOMMENDED = ["plan_rules", "proof_log", "long_form", "assets", "agent_register"]
WRITE_TARGETS = ["calendar", "proof_log", "drafts_folder", "briefs_folder"]
PLACEHOLDER = re.compile(r"^<.*>$|https?://www\.notion\.so/<")


def is_placeholder(v):
    return isinstance(v, str) and bool(PLACEHOLDER.search(v.strip()))


def check_regex(where, pattern, errors):
    try:
        re.compile(pattern, re.I)
    except re.error as e:
        errors.append(f"{where}: regex does not compile ({e}).")


def main(path):
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "errors": [f"Cannot read {path}: {e}"], "warnings": []}))
        return 1
    errors, warnings, summary = [], [], {}

    for section in ("company", "sources", "writing", "facts", "calendar"):
        if section not in cfg:
            errors.append(f"Section '{section}' is missing.")
    company = cfg.get("company", {})
    if not company.get("name"):
        errors.append("company.name is empty.")
    if not company.get("approver", {}).get("name"):
        warnings.append("No approver named. Notes and the brief will say 'the approver'.")

    sources = cfg.get("sources", {})
    for key in REQUIRED:
        if key not in sources:
            errors.append(f"Required source '{key}' is missing.")
    for key in RECOMMENDED:
        if key not in sources:
            warnings.append(f"Recommended source '{key}' is missing.")
    for key, s in sources.items():
        if key in ("shadow", "other"):
            continue
        if not isinstance(s, dict):
            errors.append(f"sources.{key} must be an object.")
            continue
        kind, plat = s.get("kind"), s.get("platform")
        if kind not in KINDS:
            errors.append(f"sources.{key}.kind '{kind}' is not one of {sorted(KINDS)}.")
        if plat not in PLATFORMS:
            errors.append(f"sources.{key}.platform '{plat}' is not one of {sorted(PLATFORMS)}.")
        if not s.get("live") or is_placeholder(s.get("live")):
            errors.append(f"sources.{key}.live is empty or still a placeholder.")
        if key in WRITE_TARGETS and (not s.get("test") or is_placeholder(s.get("test"))):
            errors.append(f"sources.{key} is written by agents but has no TEST copy.")
        if kind == "doc" and not s.get("expect_phrase"):
            warnings.append(f"sources.{key} has no expect_phrase, so a cut-off read cannot be caught.")
        if kind == "table" and not s.get("tab") and plat == "google_drive":
            warnings.append(f"sources.{key} has no tab name.")
        summary[key] = f"{plat}:{kind}"
    for i, s in enumerate(sources.get("other", []) or []):
        if not s.get("live") or not s.get("use"):
            warnings.append(f"sources.other[{i}] needs 'live' and 'use'.")

    w = cfg.get("writing", {})
    if w.get("spelling") not in ("US", "UK"):
        errors.append("writing.spelling must be US or UK.")
    if w.get("units") not in ("metric", "imperial"):
        errors.append("writing.units must be metric or imperial.")
    for t, rng in (w.get("word_count") or {}).items():
        if not (isinstance(rng, list) and len(rng) == 2 and 0 < rng[0] < rng[1]):
            errors.append(f"writing.word_count.{t} must be [min, max].")
    if not w.get("competitors"):
        warnings.append("writing.competitors is empty: no competitor names will be caught.")
    if not w.get("avoid_terms"):
        warnings.append("writing.avoid_terms is empty.")
    for r in w.get("custom_rules", []) or []:
        if r.get("level") not in ("fail", "warn"):
            errors.append(f"custom rule {r.get('id')}: level must be fail or warn.")
        check_regex(f"custom rule {r.get('id')}", r.get("regex", ""), errors)
        if r.get("unless_regex"):
            check_regex(f"custom rule {r.get('id')} unless", r["unless_regex"], errors)
        if not r.get("message"):
            errors.append(f"custom rule {r.get('id')}: message is empty.")
    for r in w.get("on_hold_topics", []) or []:
        check_regex("on_hold_topics", r.get("regex", ""), errors)
    for c in (w.get("hashtags") or {}).get("conditional", []) or []:
        check_regex("hashtags.conditional", c.get("if_regex", ""), errors)

    cal = cfg.get("calendar", {})
    for k in ("team_owned_regex", "teaser_regex", "event_live_regex"):
        if cal.get(k):
            check_regex(f"calendar.{k}", cal[k], errors)

    plan = cfg.get("plan", {})
    if plan.get("week1_monday"):
        try:
            d = date.fromisoformat(plan["week1_monday"])
            if d.weekday() != 0:
                errors.append("plan.week1_monday is not a Monday.")
        except ValueError:
            errors.append("plan.week1_monday must be YYYY-MM-DD.")
    for dep in plan.get("dependencies", []) or []:
        try:
            date.fromisoformat(dep.get("deadline", ""))
        except ValueError:
            errors.append(f"plan dependency {dep.get('fact_id')}: deadline must be YYYY-MM-DD.")

    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings, "sources": summary},
                     indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.stderr.write((__doc__ or "").strip() + "\n")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
