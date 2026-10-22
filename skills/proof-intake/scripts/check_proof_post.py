#!/usr/bin/env python3
"""Proof checks for a Partner Win or Customer Proof draft. Run after check_draft.py.

Usage:
  python3 check_proof_post.py draft.json proof_item.json --config workspace.json [--facts facts.json] [--live]

draft.json: same file as for check_draft.py ("post", "first_comment", "type").
proof_item.json: the proof log row as an object with the proof log headers as keys.
workspace.json: the client config. Uses company.name, company.people,
  company.people_first_mention and calendar.proof_types.
facts.json (optional): approved facts ([{"id","claim"}] or the facts sheet). Capitalized
  words in approved claims count as known, so product names do not raise name warnings.
--live: the draft is for the live calendar.

Fails:
- The proof item is not signed off (Sign-off status must be Yes).
- The proof item Type is not a key of calendar.proof_types.
- The organization is not named exactly as in the proof log.
- Text in quotation marks that is not the approved quote, word for word.
- The approved quote is used without its attribution as written in the proof log.
- A TEST item (Organization ending in "(TEST ...)") reaches a live draft (--live).
Warnings:
- Figures in the post that do not appear in What happened (they must map to a fact ID).
- Capitalized words that are not in the proof item, the company name, company.people or
  approved facts: check they are not names.
"""
import json
import re
import sys

ALWAYS_KNOWN = {"LinkedIn", "The", "This", "That", "These", "Those", "We", "Our", "It", "Its",
                "They", "Their", "What", "When", "Where", "Why", "How", "Who", "If", "And", "But",
                "For", "With", "Link", "Read", "Join", "Find", "Today", "Monday", "Tuesday",
                "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
TEST_MARK = re.compile(r"\s*\(TEST\b[^)]*\)\s*$", re.I)


def split_quote(q):
    m = re.match(r'^[“"](.+?)[”"]\s*(?:-|–|,|\()\s*(.+?)\)?\s*$', (q or "").strip(), re.S)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", "")


def arg_value(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def fact_words(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("values", [])
    text = []
    if data and isinstance(data[0], dict):
        text = [str(r.get("claim", r.get("Claim", ""))) for r in data]
    elif data:
        hdr = [str(h) for h in data[0]]
        ci = hdr.index("Claim") if "Claim" in hdr else None
        text = [str(r[ci]) for r in data[1:] if ci is not None and len(r) > ci]
    return set(re.findall(r"[A-Z][A-Za-z]+", " ".join(text)))


def main(argv):
    d = json.load(open(argv[1], encoding="utf-8"))
    item = json.load(open(argv[2], encoding="utf-8"))
    cfg = json.load(open(arg_value(argv, "--config"), encoding="utf-8"))
    live = "--live" in argv
    company = cfg.get("company", {}) or {}
    proof_types = (cfg.get("calendar", {}) or {}).get("proof_types") or {"Partner": "Partner Win",
                                                                        "Customer": "Customer Proof"}
    post = d.get("post", "") or ""
    fails, warns = [], []

    if str(item.get("Sign-off status", "")).strip().lower() != "yes":
        fails.append("Proof item is not signed off (Sign-off status must be Yes). Do not draft.")
    typ = str(item.get("Type", "")).strip().lower()
    if typ not in {k.lower() for k in proof_types}:
        fails.append(f"Proof item Type '{item.get('Type', '')}' is not one of: {', '.join(proof_types)}.")

    org = str(item.get("Organization", "")).strip()
    org_name = TEST_MARK.sub("", org)
    if not org_name:
        fails.append("Proof item has no Organization.")
    elif org_name not in post:
        fails.append(f"Organization not named exactly as in the proof log: '{org_name}'.")
    if live and TEST_MARK.search(org):
        fails.append("TEST item used for a live draft.")

    quote, attribution = split_quote(item.get("Approved quote (verbatim)", ""))
    quoted = [q.strip() for q in re.findall(r'[“"]([^”"]+)[”"]', post)]
    for q in quoted:
        if not quote or q != quote:
            fails.append(f"Quoted text is not the approved quote word for word: '{q[:60]}'.")
    if quote and quote in post and attribution.split(",")[0].strip() not in post:
        fails.append(f"Approved quote used without its attribution: '{attribution}'.")

    happened = str(item.get("What happened", ""))
    for n in re.findall(r"\d+(?:[.,]\d+)?\s*%?", post):
        n = n.strip()
        if n and n not in happened and n not in quote:
            warns.append(f"Figure '{n}' is not in What happened: it must map to a fact ID or be removed.")

    people = list(company.get("people") or []) + list((company.get("people_first_mention") or {}).values())
    known_text = " ".join([org, attribution, happened, str(company.get("name", ""))] + people)
    known = set(re.findall(r"[A-Z][A-Za-z]+", known_text)) | ALWAYS_KNOWN
    fp = arg_value(argv, "--facts")
    if fp:
        known |= fact_words(fp)
    body = re.sub(r"#\w+", "", post)
    for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", body):
        name = m.group(0)
        if name in known:
            continue
        prev = body[:m.start()].rstrip()
        if prev and prev[-1] not in ".!?:\n\"“":
            warns.append(f"Capitalized word '{name}' is not in the proof item: check it is not a name.")
    warns = sorted(set(warns))

    report = {"pass": not fails, "fails": fails, "warnings": warns}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not fails else 1


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
