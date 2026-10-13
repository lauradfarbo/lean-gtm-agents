---
name: calendar-builder
description: Builds and extends a rolling 13-week content calendar in Google Sheets from an approved content plan. Use when asked to "build the content calendar", "convert the content plan to a calendar", "extend the calendar", "run the monthly calendar update", "add a milestone", or "propose rows for a trade show, launch, webinar or funding date".
---

# Calendar builder

Keep the client's content calendar sheet as the single source of truth, always 13 weeks ahead. Convert the approved plan into rows once, then add new rows only as proposals for a person to approve.

## Assumptions

- The client has an approved content plan (often a PDF) with a dated, week-by-week schedule.
- The client keeps reference files in one shared folder: the plan, a plan rules file (cadence and playbook specs) and a writing rules file (brand and spelling rules).
- One named person approves rows. This skill calls them the approver.

## Hard rules

- Never publish, post, send email or submit anything.
- Never edit or delete an existing row. On monthly and milestone runs, only append rows.
- Every row added after the first run has Status `Proposed`. Never set `Approved` or `Published`; the approver sets those. The only exception is the first run, where the approver states which rows are already published.
- Never name competitors listed in the writing rules file in any title, angle or note.
- Never invent customers, partners, quotes or results. Partner and customer proof rows keep a placeholder title until an approved proof item is linked.
- Work on a copy named `TEST - [Client] Content Calendar` until the client's agent register records a passing test for the run mode in use.
- Writing standards: see `docs/agent-standards.md`. The client's writing rules file overrides them.

## Inputs

| Input | Location | Used for |
| --- | --- | --- |
| Approved content plan | Client reference folder | First run only |
| Plan rules file | Client reference folder | Cadence, playbook specs, holiday shifts |
| Writing rules file | Client reference folder | Brand, spelling and competitor rules |
| Content calendar sheet, Milestones tab | Client calendar folder | Existing rows, last date covered, milestones |
| Published archive | Client published folder | Themes and source sections used recently |
| Performance report (optional) | Client analytics folder | Weighting pillars once available |

## Access

- Google Drive: read the reference folder, create the calendar sheet.
- Google Sheets: append rows and write formatting on the calendar sheet only.

## Sheet schema

Read `references/calendar-schema.md` before writing anything. It defines the column order, Row ID format, Status values, pillar mapping and formatting. Do not add, remove or reorder columns.

## Mode 1: First run (convert the plan)

1. Read the plan in full with the Drive connector and locate the week-by-week schedule.
2. Extract one row per dated line item. Copy content type, channel, what to create (into Spec) and draft title (into Title / angle) verbatim, joining wrapped lines with a single space. Do not correct, shorten or improve any text.
3. Split each date into Date (a real date, year inferred from the plan's date range) and AM/PM (only where the plan marks it).
4. Assign Pillar from the content-type mapping in the schema reference.
5. Set Status: rows the approver names as already published get `Published`; all others get `Planned`.
6. Leave Source, Proof item, Draft link, Flags, Owner, Published link and Final text blank.
7. Prefill Milestones only with dated milestones stated in the plan.
8. Build the sheet natively. Do not upload an .xlsx: the Drive connector does not convert .xlsx to a Google Sheet reliably.
   - Drive `create_file` with contentMimeType `application/vnd.google-apps.spreadsheet`, the exact name given and the folder the person names.
   - Sheets `update_spreadsheet`: rename Sheet1 to Calendar, add Milestones and Key tabs.
   - Sheets `update_values`: write each tab in one call. Write dates as `YYYY-MM-DD` so Sheets stores real dates.
   - Sheets `update_spreadsheet`: apply the formatting, dropdowns, filter, freeze and conditional formats in the schema reference.
   - `scripts/build_calendar.py` produces the same layout as an .xlsx, for an offline copy only.
9. Verify: read the sheet back and compare it with the plan. Check the row count matches the plan's stated total and that every date, content type and title matches. Report each mismatch. Never fix a mismatch silently.

## Mode 2: Monthly run (first working Monday of each month)

1. Read the Calendar tab. Find the last dated row and the highest Row ID.
2. Work out the weeks needed to restore a 13-week horizon from today.
3. For each new week, apply the plan rules file: recurring slots by weekday, paired formats (for example a blog in the morning and its LinkedIn teaser in the afternoon), newsletter frequency, and holiday shifts for the client's main market.
4. Propose a title and angle for each row that continues the story arc and covers pillars and source sections not used in the last 8 weeks. Proof rows keep the placeholder title.
5. Fill Spec from the plan rules playbook entry for that content type. Set Status `Proposed`.
6. Append the rows. Do not touch existing rows.
7. Write a summary of proposed rows (dates, types, titles, rules applied, anything uncertain) for the approver.

## Mode 3: Milestone run

1. Read new rows on the Milestones tab where Rows proposed is blank.
2. Propose supporting rows: a teaser before, a live post on the day, a recap after, and a press release plus announcement pair only for genuine news (launch, funding, major partner).
3. Check each proposed date against existing rows and the cadence. Where a slot is taken, propose the nearest free slot and note the clash.
4. Append rows as `Proposed`, then set Rows proposed on the milestone to `Yes`.

## Output to the person

End every run with: rows added (count and Row IDs), any mismatch or rule conflict found, and what needs a decision. Keep it brief.
