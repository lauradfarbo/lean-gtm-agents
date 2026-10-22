#!/usr/bin/env python3
"""Mechanical checks for a LinkedIn draft, using the client's rules from workspace.json.

Usage:
  python3 check_draft.py draft.json --config workspace.json [--facts facts.json]

draft.json:
{
  "post": "full post text, hashtags included",
  "first_comment": "optional text of the first comment",
  "type": "post | founder | poll | video",
  "poll_question": "poll only",
  "poll_options": ["poll only", "..."]
}

workspace.json: the client config. Every client rule comes from its "writing" section
(competitors, avoid_terms, spelling US or UK, spelling_allow, units metric or imperial,
word_count, opening_max_words, hashtags, link_in_first_comment, date_words_warn,
custom_rules, on_hold_topics, emoji, no_em_dash) and company.people_first_mention.
A missing optional key skips that check. Exceptions: em dashes fail unless no_em_dash is
false, links in the body fail unless link_in_first_comment is false, and a missing
date_words_warn uses a built-in launch and availability word list.

facts.json (optional): the facts sheet, either {"values": [[headers], ...]} with the column
names from the config's "facts" section, or a list of objects. A topic in
writing.on_hold_topics is on hold unless its fact_id is approved in this file. Without
the file, every on-hold topic is treated as on hold.

Built-in generic checks: em dash, en dash used as a dash, links in the body, poll limits
(question 140 characters, 2 to 4 options of 30 characters), figures (warning).

Prints a JSON report. Exit code 1 if any check fails, 2 on a usage error.
Fails break a hard rule. Warnings need the drafter or a person to confirm.
This script does not judge claims against the facts sheet; the drafter and the
compliance checker do that.
"""
import json
import re
import sys

# Spelling: the pattern list for the variety that is NOT allowed.
UK_SPELLINGS = [  # failed when writing.spelling is US
    r"\bcolour(s|ed|ful|ing)?\b", r"\bcentre(s|d)?\b", r"\borganis\w*", r"\banalys(e|ed|es|ing)\b",
    r"\boptimis\w*", r"\bprioritis\w*", r"\brecognis\w*", r"\bminimis\w*", r"\bmaximis\w*",
    r"\bstandardis\w*", r"\bsummaris\w*", r"\bcustomis\w*", r"\bauthoris\w*", r"\butilis\w*",
    r"\brealis(e|es|ed|ing)\b", r"\bbehaviour\w*", r"\bfavour\w*", r"\blabour\b", r"\bdefence\b",
    r"\bcatalogue\b", r"\bgrey\b", r"\baluminium\b", r"\bfulfil\b", r"\btravelled\b",
    r"\bmodelling\b", r"\blitre(s)?\b", r"\bmetre(s)?\b", r"\bcentimetre\w*", r"\bkilometre\w*",
    r"\bmillimetre\w*", r"\bprogramme(s)?\b", r"\benrol(s|ment)?\b", r"\bjudgement\b",
    r"\bpractise(s|d)?\b", r"\bhumour\w*", r"\bneighbour\w*", r"\bhonour\w*", r"\bspelt\b",
    r"\bwhilst\b", r"\bamongst\b", r"\bcheque\b", r"\btyre(s)?\b",
]
US_SPELLINGS = [  # failed when writing.spelling is UK
    r"\bcolor(s|ed|ful|ing)?\b", r"\bcenter(s|ed)?\b", r"\borganiz\w*", r"\banalyz(e|ed|es|ing)\b",
    r"\boptimiz\w*", r"\bprioritiz\w*", r"\brecogniz\w*", r"\bminimiz\w*", r"\bmaximiz\w*",
    r"\bstandardiz\w*", r"\bsummariz\w*", r"\bcustomiz\w*", r"\bauthoriz\w*", r"\butiliz\w*",
    r"\brealiz(e|es|ed|ing)\b", r"\bbehavior\w*", r"\bfavor\w*", r"\blabor\b", r"\bdefense\b",
    r"\bcatalog\b", r"\bgray\b", r"\baluminum\b", r"\bfulfill\b", r"\btraveled\b",
    r"\bmodeling\b", r"\bliter(s)?\b", r"\bcentimeter\w*", r"\bkilometer\w*", r"\bmillimeter\w*",
    r"\benrollment\b", r"\bhumor\w*", r"\bneighbor\w*", r"\bhonor\w*",
]

# Units: the pattern list for the system that is NOT allowed. (pattern, level)
IMPERIAL = [  # failed when writing.units is metric
    (r"\bmiles?\b", "fail"), (r"\bfeet\b", "fail"), (r"\d+\s*ft\b", "fail"), (r"\binch(es)?\b", "fail"),
    (r"\d+\s*lbs?\b", "fail"), (r"°\s*f\b", "fail"), (r"\bfahrenheit\b", "fail"), (r"\bmph\b", "fail"),
    (r"\bgallons?\b", "fail"), (r"\bounces?\b", "fail"), (r"\d+\s*oz\b", "fail"), (r"\byards?\b", "fail"),
    (r"\bsquare feet\b|\bsq\.? ?ft\b", "fail"), (r"\d+\s*pounds?\b(?! sterling)", "warn"),
]
METRIC = [  # failed when writing.units is imperial
    (r"\d+\s*(km|kg|cm|mm|ml|kwh/m2)\b", "fail"), (r"\bkilomet(er|re)s?\b", "fail"),
    (r"\bkilograms?\b", "fail"), (r"\bcentimet(er|re)s?\b", "fail"), (r"\bmillimet(er|re)s?\b", "fail"),
    (r"\blit(er|re)s?\b", "fail"), (r"°\s*c\b", "fail"), (r"\bcelsius\b", "fail"), (r"\bkm/h\b", "fail"),
    (r"\bsquare met(er|re)s?\b", "fail"),
]

DEFAULT_DATE_WORDS = ["launch", "available", "availability", "shipping", "ships", "pre-order",
                      "preorder", "in stock", "delivery", "deliveries", "general availability",
                      "goes on sale"]
QUARTER = r"\bq[1-4]\s*20\d\d\b"

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF"
    "\U00002B00-\U00002BFF\U0000FE0F]"
)
LINK = r"https?://|www\."


def words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-\.%]*", text)


def body_without_hashtags(post):
    lines = post.rstrip().split("\n")
    while lines and (lines[-1].strip() == "" or all(t.startswith("#") for t in lines[-1].split())):
        lines.pop()
    return "\n".join(lines)


def term_re(term):
    return r"(?<![\w-])" + re.escape(term.lower()) + r"(?![\w-])"


def safe_search(pattern, text, flags=re.I):
    try:
        return re.search(pattern, text, flags)
    except re.error:
        return None


def load_rows(data):
    """Return a list of dicts from {"values": [...]}, a bare values list or a list of objects."""
    if isinstance(data, dict):
        data = data.get("values", [])
    if not data:
        return []
    if isinstance(data[0], dict):
        return data
    hdr = [str(h) for h in data[0]]
    return [dict(zip(hdr, list(r) + [""] * (len(hdr) - len(r)))) for r in data[1:]]


def approved_fact_ids(facts_rows, cfg):
    fc = cfg.get("facts", {}) or {}
    id_col = fc.get("id_col", "ID")
    status_col = fc.get("status_col", "Status")
    ok = {v.strip().lower() for v in fc.get("approved_values", ["Approved", "Approved with edits"])}
    ids = set()
    for r in facts_rows:
        fid = str(r.get(id_col, r.get("id", ""))).strip()
        if not fid:
            continue
        status = r.get(status_col, r.get("status"))
        if status is None or str(status).strip().lower() in ok:
            # A row with no status column is from facts_approved.json: approved by definition.
            ids.add(fid)
    return ids


def check(d, cfg, facts_ids):
    w = cfg.get("writing", {}) or {}
    company = cfg.get("company", {}) or {}
    post = d.get("post", "") or ""
    comment = d.get("first_comment", "") or ""
    kind = d.get("type", "post") or "post"
    low = post.lower()
    both = low + "\n" + comment.lower()
    fails, warns = [], []

    # Word count.
    body = body_without_hashtags(post)
    wc = len(words(body))
    counts = w.get("word_count") or {}
    rng = counts.get(kind) or (counts.get("post") if kind == "video" else None)
    if rng and len(rng) == 2:
        lo, hi = rng
        if wc < lo or wc > hi:
            fails.append(f"Word count {wc} (body, hashtags excluded); must be {lo} to {hi}.")

    # Opening.
    first = next((l for l in post.split("\n") if l.strip()), "")
    first_sentence = re.split(r"(?<=[.?!:])\s", first.strip())[0]
    omax = w.get("opening_max_words")
    if omax and len(words(first_sentence)) >= omax:
        fails.append(f"Opening sentence has {len(words(first_sentence))} words; must be under {omax}.")
    if len(first) > 140:
        warns.append(f"Opening line is {len(first)} characters; LinkedIn may cut it before 'more' (about 140).")

    # Punctuation and emoji.
    if w.get("no_em_dash", True) is not False and ("\u2014" in post or "\u2014" in comment):
        fails.append("Em dash found. Use a comma, colon or period.")
    if re.search(r"\s–\s", post + "\n" + comment):
        fails.append("En dash used as a dash. Use a comma, colon or period.")
    if w.get("emoji") is False and (EMOJI.search(post) or EMOJI.search(comment)):
        fails.append("Emoji found.")
    if "!" in post:
        warns.append("Exclamation mark found: only for rare celebratory posts.")

    # Names and terms.
    for c in w.get("competitors") or []:
        if c and re.search(term_re(c), both):
            fails.append(f"Company name '{c}' found. Never name a competitor or consumer brand.")
    for a in w.get("avoid_terms") or []:
        if a and re.search(term_re(a), both):
            fails.append(f"Avoid-list term '{a}'.")

    # Spelling.
    variety = str(w.get("spelling") or "").upper()
    allow = [s.lower() for s in (w.get("spelling_allow") or [])]
    bad = UK_SPELLINGS if variety == "US" else US_SPELLINGS if variety == "UK" else []
    want = "US" if variety == "US" else "UK"
    seen = set()
    for p in bad:
        for m in re.finditer(p, both):
            word = m.group(0)
            if word in seen or any(word in a for a in allow):
                continue
            seen.add(word)
            fails.append(f"Spelling '{word}' is not {want} spelling.")

    # Units.
    system = str(w.get("units") or "").lower()
    unit_list = IMPERIAL if system == "metric" else METRIC if system == "imperial" else []
    for p, level in unit_list:
        m = re.search(p, both)
        if m:
            msg = f"Unit '{m.group(0).strip()}' found; use {system} units."
            (fails if level == "fail" else warns).append(msg if level == "fail" else msg + " Confirm it is not a weight.")

    # Dates that suggest a launch, availability or delivery.
    date_words = w.get("date_words_warn")
    if date_words is None:
        date_words = DEFAULT_DATE_WORDS
    for dw in date_words:
        m = re.search(r"\b" + re.escape(dw.lower()) + r"\w*", both)
        if m:
            warns.append(f"'{m.group(0)}' found: no launch, availability or delivery dates. Confirm it is not a product date.")
    m = re.search(QUARTER, both)
    if m:
        warns.append(f"'{m.group(0)}' found: no launch, availability or delivery dates. Confirm it is not a product date.")

    # Client claim rules.
    for r in w.get("custom_rules") or []:
        pat = r.get("regex")
        if not pat or not safe_search(pat, post + "\n" + comment):
            continue
        if r.get("unless_regex") and safe_search(r["unless_regex"], post + "\n" + comment):
            continue
        msg = f"{r.get('id', 'Rule')}: {r.get('message', 'custom rule matched.')}"
        (warns if str(r.get("level", "fail")).lower() == "warn" else fails).append(msg)

    # On-hold topics.
    for t in w.get("on_hold_topics") or []:
        pat = t.get("regex")
        if not pat or not safe_search(pat, post + "\n" + comment):
            continue
        fid = t.get("fact_id")
        if fid and facts_ids is not None and fid in facts_ids:
            continue  # fact approved: topic no longer on hold
        fails.append(t.get("message") or "Topic mentioned while it is on hold.")

    # Figures.
    if re.search(r"\d+(\.\d+)?\s*%|\b\d+x\b|[$£€]\s?\d", post):
        warns.append("Figure found: it must map to an approved fact with a traceable reference, and the source must be named.")

    # Links.
    if re.search(LINK, post) and w.get("link_in_first_comment", True) is not False:
        fails.append("Link in the post body. External links go in the first comment.")
    if w.get("link_in_first_comment") and re.search(LINK, comment) and "first comment" not in low:
        fails.append("First comment has a link but the post does not say 'Link in the first comment'.")

    # First mention of people.
    pfm = company.get("people_first_mention") or w.get("people_first_mention") or {}
    for key, full in pfm.items():
        m = re.search(r"\b" + re.escape(key) + r"\b", post)
        if not m:
            continue
        i = post.find(full)
        if i < 0 or not (i <= m.start() < i + len(full)):
            fails.append(f"First mention of {key} must be '{full}'.")

    # Hashtags.
    h = w.get("hashtags") or {}
    tags = re.findall(r"#\w+", post)
    tail = post.rstrip().split("\n")[-1] if post.strip() else ""
    tail_tags = re.findall(r"#\w+", tail)
    hmin, hmax = h.get("min"), h.get("max")
    if hmin is not None or hmax is not None:
        lo, hi = hmin or 0, hmax if hmax is not None else 99
        if not (lo <= len(tail_tags) <= hi):
            fails.append(f"{len(tail_tags)} hashtags on the last line; need {lo} to {hi} at the end.")
    tags_low = {t.lower() for t in tags}
    for req in h.get("required") or []:
        if req.lower() not in tags_low:
            fails.append(f"Missing {req}.")
    if tags and len(tags) != len(tail_tags):
        warns.append("Hashtags found inside the body; keep them at the end.")
    for c in h.get("conditional") or []:
        if c.get("tag") and c.get("if_regex") and safe_search(c["if_regex"], body) \
                and c["tag"].lower() not in tags_low:
            warns.append(f"Post matches '{c['if_regex']}': add {c['tag']}.")

    # Polls.
    if kind == "poll":
        q = d.get("poll_question", "") or ""
        opts = d.get("poll_options", []) or []
        if not q or len(q) > 140:
            fails.append("Poll question missing or over 140 characters.")
        if not (2 <= len(opts) <= 4):
            fails.append("Poll needs 2 to 4 options.")
        for o in opts:
            if len(o) > 30:
                fails.append(f"Poll option over 30 characters: '{o}'.")

    return {"word_count": wc, "pass": not fails, "fails": fails, "warnings": warns}


def arg_value(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def main(argv):
    with open(argv[1], encoding="utf-8") as f:
        d = json.load(f)
    with open(arg_value(argv, "--config"), encoding="utf-8") as f:
        cfg = json.load(f)
    facts_ids = None
    fp = arg_value(argv, "--facts")
    if fp:
        with open(fp, encoding="utf-8") as f:
            facts_ids = approved_fact_ids(load_rows(json.load(f)), cfg)
    report = check(d, cfg, facts_ids)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


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
    if not _usage_ok(sys.argv, 1):
        sys.exit(2)
    sys.exit(main(sys.argv))
