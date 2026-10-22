#!/usr/bin/env python3
"""Build the subagent bundles for one weekly run (weekly orchestrator).

Usage:
  python3 make_bundles.py <run dir> <plugin root> plan|draft|proof|redraft|check|fallback [options]

  plan                                  -> <run dir>/plan/
  draft  --rows W09-03,W09-04           -> <run dir>/draft/<Row ID>/
  proof  --rows W09-01 --proof-rows 4   -> <run dir>/proof/<Row ID>/  (proof log row per slot, same order)
  redraft --from draft/<Row ID> --previous <file.json> --fixes <file.json>  -> <run dir>/redraft/<Row ID>-2/
  check  --draft <file.json> [--proof-row N] [--suffix -2] [--content-type T]  -> <run dir>/check/<Row ID><suffix>/
  fallback --rows W03-01 --swaps swaps_final.json  -> <run dir>/fallback/<Row ID>/
      A short-form drafter bundle for the proposed swap, not the original row. row.json takes the
      swap's type and its angle as Title / angle, with Status Planned and What's missing empty; the
      original row goes in fallback.json. swaps_final.json: swap_slots.py "swaps" with "angle" (and
      "chapter" when the config lists chapters) filled by the orchestrator.
      Check it with: check --draft <file> --suffix -fb --content-type "<swap type>".

  Add --shadow to draft and proof in a shadow run: row.json then carries Status Planned (so the
  drafting skill's Status check passes) and the real Status under "Live status". Nothing is written.

<run dir>/shared/ must hold workspace.json, calendar.json, proof_log.json, facts.json, rules.md,
plan_rules.md, voice.md and assets.txt, and may hold long_form.md (the long-form source as text),
the client's chapter map (file name from sources.long_form.chapter_map, default chapter-map.md;
copied into bundles as chapter-map.md) and milestones.json.
Every bundle gets workspace.json. Draft, proof and fallback bundles also get long_form.md and
chapter-map.md when present, recent.txt and visuals_recent.txt (Visual of every other row within
visuals.no_repeat_weeks either side). Check bundles get assets.txt and visuals_recent.txt.
The script writes facts_approved.json ([{"id", "claim", "comments"}], column names from facts.*)
in shared/ on first use. It copies files; it never edits them. Prints the bundle paths it made.
"""
import json
import os
import shutil
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
VALUE_FLAGS = {"--rows", "--proof-rows", "--from", "--previous", "--fixes", "--draft", "--proof-row",
               "--suffix", "--content-type", "--swaps", "--config"}
CHECK_KEYS = ("row_id", "content_type", "type", "post", "first_comment", "alternate_hook", "visual",
              "visual_alternatives", "image_prompt", "image_alt_prompt", "image_alt_subject",
              "poll_question", "poll_options", "fact_ids")


def cfg_get(cfg, path, default):
    cur = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or cur.get(k) is None:
            return default
        cur = cur[k]
    return cur


def load(p):
    v = json.load(open(p, encoding="utf-8"))
    return v.get("values", v) if isinstance(v, dict) else v


def table(values):
    hdr = values[0]
    out = []
    for n, r in enumerate(values[1:], start=2):
        r = list(r) + [""] * (len(hdr) - len(r))
        out.append({"_row": n, **dict(zip(hdr, r))})
    return out


def parse_date(s):
    for f in ("%a %d %b %y", "%d %b %y", "%Y-%m-%d"):
        try:
            return datetime.strptime((s or "").strip().title() if "%b" in f else (s or "").strip(), f).date()
        except ValueError:
            pass
    return None


def cp(src, dst_dir, name=None):
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy(src, os.path.join(dst_dir, name or os.path.basename(src)))


def cp_if(src, dst_dir, name=None):
    if os.path.exists(src):
        cp(src, dst_dir, name)


def arg(argv, k, default=None):
    return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else default


def write_recent_visuals(cal, rid, rd, path, weeks, cancelled):
    """visuals_recent.txt: Row ID | date | Visual of every other row within the window either side."""
    with open(path, "w", encoding="utf-8") as fh:
        for r in cal:
            d = parse_date(r.get("Date"))
            v = (r.get("Visual") or "").strip()
            for seg in (r.get("Notes") or "").split("Orchestrator "):
                if "Fallback draft" in seg and "Visual:" in seg:  # visual of a fallback draft
                    v = (v + " | Fallback " + seg.split("Visual:", 1)[1].split(" Status stays")[0]).strip(" |")
            if r.get("Row ID") == rid or not d or not rd or not v or r.get("Status") == cancelled:
                continue
            if rd - timedelta(weeks=weeks) <= d <= rd + timedelta(weeks=weeks):
                fh.write(f"{r.get('Row ID')} | {d.isoformat()} | {v}\n")


def main(argv):
    pos, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_FLAGS
        else:
            pos.append(a)
    run, root, mode = pos[0], pos[1], pos[2]
    sh = os.path.join(run, "shared")
    ws = os.path.join(sh, "workspace.json")
    if not os.path.exists(ws):
        sys.exit(f"{ws} is missing. Copy the run's workspace.json into shared/ first.")
    cfg = json.load(open(ws, encoding="utf-8"))
    sts = cfg_get(cfg, "calendar.statuses", None)
    cancelled = sts[5] if isinstance(sts, list) and len(sts) == 6 else (sts.get("Cancelled", "Cancelled") if isinstance(sts, dict) else "Cancelled")
    weeks = int(cfg_get(cfg, "visuals.no_repeat_weeks", 8))
    label = cfg_get(cfg, "swaps.source_label", "Long-form")
    who = cfg_get(cfg, "company.approver.name", "") or "The approver"
    chapter_map = os.path.basename(cfg_get(cfg, "sources.long_form.chapter_map", "chapter-map.md"))
    skills = os.path.join(root, "skills")
    orch = os.path.join(skills, "weekly-orchestrator", "scripts")

    fa = os.path.join(sh, "facts_approved.json")
    if not os.path.exists(fa):
        id_c = cfg_get(cfg, "facts.id_col", "ID")
        claim_c = cfg_get(cfg, "facts.claim_col", "Claim")
        st_c = cfg_get(cfg, "facts.status_col", "Status")
        com_c = cfg_get(cfg, "facts.comments_col", "Approver comments")
        ok = cfg_get(cfg, "facts.approved_values", ["Approved", "Approved with edits"])
        facts = table(load(os.path.join(sh, "facts.json")))
        keep = [{"id": f.get(id_c, ""), "claim": f.get(claim_c, ""), "comments": f.get(com_c, "")}
                for f in facts if f.get(st_c) in ok and f.get(id_c)]
        json.dump(keep, open(fa, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cal = table(load(os.path.join(sh, "calendar.json")))
    made = []

    if mode == "plan":
        d = os.path.join(run, "plan")
        for f in ("workspace.json", "calendar.json", "facts.json", "proof_log.json", "plan_rules.md", "rules.md", "milestones.json"):
            cp_if(os.path.join(sh, f), d)
        cp(os.path.join(orch, "plan_check.py"), d)
        made.append(d)

    swaps = {}
    if mode == "fallback":
        sw = json.load(open(arg(argv, "--swaps"), encoding="utf-8"))
        swaps = {x["row_id"]: x for x in (sw.get("swaps", sw) if isinstance(sw, dict) else sw)}
    if mode in ("draft", "proof", "fallback"):
        ids = [x for x in (arg(argv, "--rows", "") or "").split(",") if x]
        prows = [int(x) for x in (arg(argv, "--proof-rows", "") or "").split(",") if x]
        proof = table(load(os.path.join(sh, "proof_log.json"))) if mode == "proof" else []
        need_ch = bool(cfg_get(cfg, "swaps.chapters", []))
        for i, rid in enumerate(ids):
            row = next((r for r in cal if r.get("Row ID") == rid), None)
            if row is None:
                sys.exit(f"Row ID {rid} not found on the calendar.")
            d = os.path.join(run, mode, rid)
            os.makedirs(d, exist_ok=True)
            if "--shadow" in argv:
                row = {**row, "Live status": row.get("Status", ""), "Status": "Planned"}
            fb = None
            if mode == "fallback":
                x = swaps.get(rid)
                if not x or not x.get("angle") or (need_ch and not x.get("chapter")):
                    sys.exit(f"{rid}: no swap with angle{' and chapter' if need_ch else ''} in --swaps.")
                ch = f", {label} ch{x['chapter']}" if x.get("chapter") else ""
                fb = {"row_id": rid, "date": row.get("Date"), "original_content_type": row.get("Content type"),
                      "original_title": row.get("Title / angle"), "swap_type": x["type"], "angle": x["angle"],
                      "chapter": x.get("chapter"), "conditional": x.get("conditional", ""),
                      "note": "Fallback draft for a proposed swap. Draft the swap post, not the original row. "
                              f"{who} decides whether to use it; Status stays Planned."}
                row = {**row, "Content type": x["type"], "Title / angle": x["angle"],
                       "Spec": f"Fallback for {row.get('Content type')}: {x['type']}{ch}.",
                       "Status": "Planned", "What's missing": "", "Notes": ""}
            json.dump(row, open(os.path.join(d, "row.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            for f in ("workspace.json", "rules.md", "voice.md", "facts_approved.json", "assets.txt", "long_form.md"):
                cp_if(os.path.join(sh, f), d)
            cp_if(os.path.join(sh, chapter_map), d, "chapter-map.md")
            rd = parse_date(row.get("Date"))

            def near(r):
                rdt = parse_date(r.get("Date"))
                return r.get("Row ID") != rid and rdt and rd and rd - timedelta(weeks=weeks) <= rdt <= rd + timedelta(days=14)
            base = (row.get("Content type", "") or "").split(" - ")[0]
            recent = [r for r in cal if (r.get("Content type", "") or "").split(" - ")[0] == base and near(r)]
            lf_rows = [r for r in cal if label.lower() in ((r.get("Sources", "") or "") + (r.get("Content type", "") or "")).lower() and near(r)]
            with open(os.path.join(d, "recent.txt"), "w", encoding="utf-8") as fh:
                for r in {x["Row ID"]: x for x in recent + lf_rows if x.get("Status") != cancelled}.values():
                    fh.write(f"{r['Row ID']} | {r.get('Content type')} | {r.get('Sources')}\n")
            write_recent_visuals(cal, rid, rd, os.path.join(d, "visuals_recent.txt"), weeks, cancelled)
            if fb:
                json.dump(fb, open(os.path.join(d, "fallback.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            src = "proof-intake" if mode == "proof" else "short-form-drafter"
            cp_if(os.path.join(skills, src, "SKILL.md"), d, "proof_skill.md" if mode == "proof" else "drafter_skill.md")
            for sub in ("references", "scripts"):
                folder = os.path.join(skills, src, sub)
                if os.path.isdir(folder):
                    for f in os.listdir(folder):
                        if os.path.isfile(os.path.join(folder, f)):
                            cp(os.path.join(folder, f), d)
            if mode == "proof":
                cp_if(os.path.join(skills, "short-form-drafter", "references", "post-types.md"), d)
                n = prows[i]
                item = next(p for p in proof if p["_row"] == n)
                json.dump(item, open(os.path.join(d, "proof_item.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            made.append(d)

    if mode == "redraft":
        src = os.path.join(run, arg(argv, "--from"))
        d = os.path.join(run, "redraft", os.path.basename(src.rstrip("/")) + "-2")
        shutil.copytree(src, d, dirs_exist_ok=True)
        cp(ws, d)
        shutil.copy(arg(argv, "--previous"), os.path.join(d, "previous.json"))
        shutil.copy(arg(argv, "--fixes"), os.path.join(d, "fixes.json"))
        made.append(d)

    if mode == "check":
        dj = json.load(open(arg(argv, "--draft"), encoding="utf-8"))
        rid = dj["row_id"]
        row = next((r for r in cal if r.get("Row ID") == rid), {})
        if arg(argv, "--content-type"):
            dj["content_type"] = arg(argv, "--content-type")  # fallback drafts: the swap type
        dj.setdefault("content_type", row.get("Content type", ""))
        d = os.path.join(run, "check", rid + (arg(argv, "--suffix", "") or ""))
        os.makedirs(d, exist_ok=True)
        json.dump({k: dj.get(k) for k in CHECK_KEYS if k in dj}, open(os.path.join(d, "draft.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        for f in ("workspace.json", "facts.json", "rules.md", "voice.md", "assets.txt"):
            cp_if(os.path.join(sh, f), d)
        write_recent_visuals(cal, rid, parse_date(row.get("Date")), os.path.join(d, "visuals_recent.txt"), weeks, cancelled)
        for f in ("check_compliance.py", "check_draft.py"):
            cp_if(os.path.join(orch, f), d)
        if arg(argv, "--proof-row"):
            proof = table(load(os.path.join(sh, "proof_log.json")))
            item = next(p for p in proof if p["_row"] == int(arg(argv, "--proof-row")))
            json.dump(item, open(os.path.join(d, "proof_item.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        made.append(d)

    print(json.dumps({"bundles": made}, indent=1))
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
