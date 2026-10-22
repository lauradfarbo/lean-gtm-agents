#!/usr/bin/env python3
"""Extract the full text of a Google Doc from a Docs read_doc result (weekly orchestrator).

Usage:
  python3 doc_text.py read_doc.json out.md [--expect "last words"]

read_doc.json: the Docs read_doc result exactly as returned or saved by the tool. Accepts the
  document object itself or {"content": <document>}. Reads every tab (and child tab) in order,
  then the legacy body if there are no tabs. Tables are written one row per line, cells joined
  with " | ".
--expect: text the document must contain near its end (the source's expect_phrase in
  workspace.json). Exit 1 if it is missing, so a cut-off file never reaches a subagent.

Why: a Drive text export can cut long Docs off. read_doc returns the whole document, and this
script turns it into plain text without retyping anything. Prints the character count and the
last line. Writes only out.md.
"""
import json
import sys


def para_text(p):
    out = []
    for el in p.get("elements", []):
        tr = el.get("textRun")
        if tr:
            out.append(tr.get("content", ""))
    return "".join(out)


def walk(content, lines):
    for block in content or []:
        if "paragraph" in block:
            lines.append(para_text(block["paragraph"]).rstrip("\n"))
        elif "table" in block:
            for row in block["table"].get("tableRows", []):
                cells = []
                for cell in row.get("tableCells", []):
                    sub = []
                    walk(cell.get("content", []), sub)
                    cells.append(" ".join(x for x in sub if x.strip()))
                lines.append(" | ".join(cells))
        elif "tableOfContents" in block:
            walk(block["tableOfContents"].get("content", []), lines)


def tabs(tab_list, lines):
    for t in tab_list or []:
        body = t.get("documentTab", {}).get("body", {})
        walk(body.get("content", []), lines)
        tabs(t.get("childTabs", []), lines)


def main(argv):
    if len(argv) < 3 or argv[1].startswith("--") or "-h" in argv or "--help" in argv:
        sys.stderr.write(__doc__.strip() + "\n")
        return 2
    raw = json.load(open(argv[1], encoding="utf-8"))
    doc = raw.get("content", raw) if isinstance(raw, dict) else raw
    if isinstance(doc, str):
        doc = json.loads(doc)
    lines = []
    if doc.get("tabs"):
        tabs(doc["tabs"], lines)
    else:
        walk(doc.get("body", {}).get("content", []), lines)
    text = "\n".join(lines).strip() + "\n"
    open(argv[2], "w", encoding="utf-8").write(text)
    last = [x for x in text.splitlines() if x.strip()][-1] if text.strip() else ""
    print(json.dumps({"chars": len(text), "last_line": last[:200]}))
    if "--expect" in argv:
        want = argv[argv.index("--expect") + 1]
        if want not in text:
            print(f"MISSING: expected text not found: {want}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
