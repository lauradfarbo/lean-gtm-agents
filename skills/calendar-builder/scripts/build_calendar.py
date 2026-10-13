#!/usr/bin/env python3
"""Build a content calendar workbook from a rows JSON file (offline copy only).

Usage: build_calendar.py rows.json out.xlsx

rows.json: {"rows": [{week, date (YYYY-MM-DD), ampm, content_type, channel,
            title, spec, status}], "milestones": [{milestone, type, start,
            end, confirmed, notes}]}
Pillar and Row ID are derived here so the rules live in one place.
"""
import json
import sys
from datetime import date

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

# Neutral defaults. Set client colours in the client workspace, not here.
HEADER, APPROVED, DRAFTED = "1F2933", "1E6B52", "E3EEF7"
STATUSES = ["Proposed", "Planned", "Drafted", "In review", "Approved", "Published", "Swapped"]
PILLARS = ["Partner & Customer Proof", "Thought Leadership", "Engagement",
           "Product & Brand Education", "Lead Generation", "PR & Press"]
COLS = ["Row ID", "Week", "Date", "AM/PM", "Content type", "Pillar", "Channel",
        "Title / angle", "Spec", "Source", "Proof item", "Status", "Draft link",
        "Flags", "Owner", "Published link", "Final text"]
WIDTHS = [9, 6, 14, 7, 26, 24, 24, 48, 60, 18, 16, 12, 18, 30, 12, 22, 40]


def pillar(ct):
    c = ct.lower()
    if "partner win" in c or "customer proof" in c:
        return "Partner & Customer Proof"
    if "press release" in c:
        return "PR & Press"
    if "poll" in c:
        return "Engagement"
    if "pov" in c:
        return "Thought Leadership"
    if any(k in c for k in ("guide", "newsletter", "event")):
        return "Lead Generation"
    if any(k in c for k in ("blog", "video", "gratitude", "year-in-review")):
        return "Product & Brand Education"
    raise ValueError(f"No pillar mapping for content type: {ct}")


def header(ws, cols, widths):
    ws.append(cols)
    for i, w in enumerate(widths, 1):
        cell = ws.cell(row=1, column=i)
        cell.fill = PatternFill("solid", fgColor=HEADER)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 24


def main(src, out):
    data = json.load(open(src))
    rows = data["rows"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Calendar"
    header(ws, COLS, WIDTHS)

    seq = {}
    for r in rows:
        if r["status"] not in STATUSES:
            raise ValueError(f"Bad status {r['status']}")
        wk = int(r["week"])
        seq[wk] = seq.get(wk, 0) + 1
        ws.append([f"W{wk:02d}-{seq[wk]:02d}", wk, date.fromisoformat(r["date"]),
                   r.get("ampm") or None, r["content_type"], pillar(r["content_type"]),
                   r["channel"], r["title"], r["spec"], None, None, r["status"],
                   None, None, None, None, None])

    n = len(rows) + 1
    band = PatternFill("solid", fgColor="F4F6F8")
    for i in range(2, n + 1):
        ws.cell(row=i, column=3).number_format = "ddd d mmm yy"
        for c in range(1, len(COLS) + 1):
            ws.cell(row=i, column=c).alignment = Alignment(vertical="top", wrap_text=c in (8, 9, 14, 17))
        if ws.cell(row=i, column=2).value % 2 == 0:
            for c in range(1, 12):
                ws.cell(row=i, column=c).fill = band

    dv = DataValidation(type="list", formula1='"' + ",".join(STATUSES) + '"', allow_blank=False,
                        showErrorMessage=True, errorTitle="Status", error="Choose a value from the list.")
    ws.add_data_validation(dv)
    dv.add(f"L2:L1000")
    pv = DataValidation(type="list", formula1='"' + ",".join(PILLARS) + '"', allow_blank=True)
    ws.add_data_validation(pv)
    pv.add("F2:F1000")
    av = DataValidation(type="list", formula1='"AM,PM"', allow_blank=True)
    ws.add_data_validation(av)
    av.add("D2:D1000")

    colors = {"Proposed": ("FFF4D6", "000000"), "Drafted": (DRAFTED, "000000"),
              "In review": ("FBE7B0", "000000"), "Approved": (APPROVED, "FFFFFF"),
              "Published": ("E3E3E3", "5F5F5F"), "Swapped": ("F8D7D3", "000000")}
    for s, (bg, fg) in colors.items():
        ws.conditional_formatting.add("L2:L1000", FormulaRule(
            formula=[f'$L2="{s}"'], fill=PatternFill("solid", fgColor=bg),
            font=Font(color=fg, bold=s == "Approved")))
    ws.freeze_panes = "F2"
    ws.auto_filter.ref = f"A1:Q{n}"

    ms = wb.create_sheet("Milestones")
    mcols = ["Milestone", "Type", "Start date", "End date", "Confirmed", "Notes", "Rows proposed"]
    header(ms, mcols, [40, 14, 14, 14, 11, 60, 14])
    for m in data.get("milestones", []):
        ms.append([m["milestone"], m["type"], date.fromisoformat(m["start"]),
                   date.fromisoformat(m["end"]) if m.get("end") else None,
                   m["confirmed"], m.get("notes"), m.get("rows_proposed")])
    for i in range(2, 200):
        ms.cell(row=i, column=3).number_format = "ddd d mmm yy"
        ms.cell(row=i, column=4).number_format = "ddd d mmm yy"
        ms.cell(row=i, column=6).alignment = Alignment(wrap_text=True, vertical="top")
    for rng, vals in (("B2:B200", "Trade show,Launch,Webinar,Funding,Partner,Product"),
                      ("E2:E200", "Yes,No"), ("G2:G200", "Yes")):
        v = DataValidation(type="list", formula1=f'"{vals}"', allow_blank=True)
        ms.add_data_validation(v)
        v.add(rng)
    ms.freeze_panes = "A2"

    key = wb.create_sheet("Key")
    header(key, ["Status", "Set by", "Meaning"], [14, 30, 70])
    for row in [
        ("Proposed", "Calendar builder", "New row awaiting approval. Drafting agents ignore it."),
        ("Planned", "Approver", "Approved slot, ready to draft."),
        ("Drafted", "Drafting agent", "Draft linked in Draft link, awaiting review."),
        ("In review", "Approver", "Being edited."),
        ("Approved", "Approver", "Ready to post."),
        ("Published", "Approver", "Live. Published link and Final text filled in."),
        ("Swapped", "Agent (as proposal) or approver", "Slot replaced. See Flags for the reason."),
    ]:
        key.append(row)
    key.append([])
    key.append(["Rules", "", "Agents never set Approved or Published. Agents never edit or delete Planned rows. "
                "Pillar is inferred from content type; the approver may override it. Row ID never changes."])
    key.cell(row=key.max_row, column=1).font = Font(bold=True)
    for r in key.iter_rows(min_row=2):
        for c in r:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(out)
    print(f"Wrote {out}: {len(rows)} rows, {len(data.get('milestones', []))} milestones")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
