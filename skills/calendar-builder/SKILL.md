---
name: calendar-builder
description: Builds and extends the company's rolling 13-week content calendar from an approved content plan. Use when asked to "build the content calendar", "convert the content plan to a calendar", "extend the calendar", "run the monthly calendar update", "add a milestone", "propose rows for a trade show, launch, webinar or funding date", or "process new post ideas" from the Ideas tab.
---

# Calendar builder

**Purpose:** keep the company's content calendar as the single source of truth, always 13 weeks ahead. Convert the approved plan into rows once, then add new rows only as proposals for a person to approve. The calendar is kept by people who are not marketers, so keep everything a person sees plain and short.

Read `workspace.json` first. If there is none, run the `workspace-setup` skill. Every location, name, list and rule this skill uses comes from that file. Locations come from `sources.<key>`, live or test.

## Assumptions

- The company has an approved content plan (often a PDF) with a dated, week-by-week schedule.
- A plan rules doc (`sources.plan_rules`) sets the cadence, the playbook specs and the holiday shifts. The `plan` section of the config holds the part a script can test.
- One named person approves rows: `company.approver.name`, called the approver below.

## Inputs

| Input | Config key | Used for |
| --- | --- | --- |
| Approved content plan | Named by the person on the first run | First run only |
| Plan rules doc | `sources.plan_rules`, `plan` | Cadence, playbook specs, holiday shifts |
| Rules doc | `sources.rules`, `writing` | Writing and brand rules, competitor names |
| Facts sheet | `sources.facts_sheet`, `facts` | Checking ideas against approved claims |
| Calendar (Calendar, Ideas, Milestones tabs) | `sources.calendar` | Existing rows, last date covered, ideas, milestones |
| Long-form source and chapter map | `sources.long_form`, `swaps.source_label` | Chapters used recently |
| Published archive, performance report (optional) | `sources.other` | Pillars and chapters used recently, pillar weighting |

## Outputs

- New Calendar rows with Status `Proposed` (first run: `Planned` or `Posted`).
- Empty agent cells filled on rows a person added.
- Ideas rows set to `Scheduled` or `Parked`, Milestones rows set to Rows proposed `Yes`.
- A short summary for the weekly brief.

## Access

- Calendar: read and write cell ranges on the Calendar, Ideas and Milestones tabs only. On the first run, create the calendar file in the folder the person names.
- Every other source: read only.

## Hard rules

- Never publish, post, send email or submit anything.
- Never edit or delete an existing row. On monthly, milestone and ideas runs, only add new rows below the last row (see "Writing new rows"). One exception: on a row a person added directly to the Calendar, fill the empty agent cells (What to post, Pillar, Channel, Row ID, Week, Content type, Spec, Sources, What's missing). Never change anything the person entered.
- Every row added after the first run has Status `Proposed`. Agents never set `Planned`, `Approved`, `Posted` or `Cancelled`. A person sets `Cancelled` to drop a post; the row stays as history. The only exception is the first run, where the person running it states which rows are already posted.
- Skip `Cancelled` rows everywhere: never write to them, count them as free slots or mention them in any summary, brief or notification.
- Never write to the Action needed (G) or Draft (H) columns, or to the This Week tab. They are formulas.
- Every row has Sources filled. What's missing names exactly what a person must provide, in plain words.
- Never name or cite a company in `writing.competitors` in any title, angle or note.
- Never invent customers, partners, quotes or results. Proof rows (content types in `calendar.proof_types`) keep the title from `calendar.proof_placeholders` until proof intake links an approved proof log item.
- Work on the TEST calendar (`sources.calendar.test`) until the agent register records a passing test for the run mode in use.
- Writing standards for anything written into the calendar: `docs/agent-standards.md` and `writing.*` (spelling, units). No em dashes. Dates in prose as DD MMM YY with an uppercase month (13 OCT 26).

## Calendar schema

Read `references/calendar-schema.md` before writing anything. It defines the tabs, column order (A to V), Status values, pillar and "What to post" mappings, formulas, filter view and formatting. Do not add, remove or reorder columns.

## Platforms

The tested path is Google Sheets. For a Notion database or Excel Online, follow the adapter rules in `docs/workspace-config.md`: the same columns in the same order, the same never-overwrite rules, and the same guard and read-back checks. Formulas (Action needed, Draft, This Week) are replaced by the platform's equivalent (a Notion formula property or view, an Excel formula) or, where the platform has none, left to the agent to fill on each run. Run the TEST calendar on that platform before going live.

## Dry run (shadow mode)

When the weekly orchestrator runs in shadow mode, run the monthly, ideas and milestone modes as a dry run: read as normal, work out every row, cell and Ideas or Milestones update the run would write, and return them as a list (Row ID, date, What to post, title, What's missing, or the idea and Parked reason). Write nothing to any tab. The orchestrator puts the list in the shadow brief under "Calendar changes proposed (not written)".

## Writing new rows

Never append to the Calendar (Sheets `append_values`). The formulas in G2 and H2 return values down to the last row of the grid, so an append can land below them, hundreds of rows down.

1. Read Calendar column A and find the last row with a Date. The first new row is the one below it.
2. Write the new rows with Sheets `update_values` to an explicit range, for example `Calendar!A48:Q59`. Dates as `YYYY-MM-DD` so they are stored as real dates.
3. Put `null` in G, H and I (and any other cell to leave alone) so the formulas and empty cells are not overwritten. Never write an empty string to G or H: it breaks the formula.
4. Read back the new rows and the row above them. Confirm the row above is unchanged, Action needed shows "New slot: review, then set Planned" and Dates display as dates.
5. To fill empty cells on a person's row, write only those cells (for example `Calendar!C48:D48` and `Calendar!L48:Q48`). Never write a range that includes a cell the person filled. Read the row again just before writing and skip it if its Date, Status or the target cells changed.

## Mode 1: First run (convert the plan)

1. Read the plan in full. Locate the week-by-week schedule.
2. Extract one row per dated line item. Copy Content type, Channel(s), What to create (into Spec) and Draft title / angle verbatim, joining wrapped lines with a single space.
3. Split the date into Date (real date, year inferred from the plan's date range) and AM/PM (only where the plan marks AM or PM). Week is counted from `plan.week1_monday`.
4. Fill Pillar and What to post from the mappings. Set Status: rows the person names as already posted get `Posted`; all others `Planned`.
5. Build the calendar natively with the connectors. Do not upload an .xlsx: the Drive connector does not convert .xlsx to a Google Sheet reliably.
   - Drive `create_file` with contentMimeType `application/vnd.google-apps.spreadsheet`, the exact name given (for testing: `TEST - <company.name> Content Calendar`) and the folder named.
   - Sheets `update_spreadsheet`: create the five tabs in order.
   - Sheets `update_formulas`: write the Calendar tab in one call with verbatim titles, the G2 and H2 formulas, and `null` in G and H below row 2. Write the This Week link row, headers and formulas, the Ideas headers, the Milestones rows (dated milestones stated in the plan only) and the How to use text.
   - Sheets `update_spreadsheet`: apply formatting, dropdowns, filter, the filter view, freeze, conditional formats, the collapsed column group and warning-only protection.
   - `scripts/build_calendar.py` produces the same layout as an .xlsx, for an offline copy only.
6. Verify: export the calendar (Calendar tab as `calendar.json` in the `{"values": [...]}` shape, or the file as .xlsx), save the plan text with `pdftotext -layout`, and run:
   `python3 scripts/verify_calendar.py plan_layout.txt calendar.json --config workspace.json [--expect <row count stated in the plan>]`
   It compares every row's week, weekday, date, AM/PM, content type and title. Report each mismatch. Never fix a mismatch silently. If the plan's table layout differs from the default, set `plan.pdf` in the config (see the script's usage text).
7. Only after verification passes, clean the titles in column F: remove quote marks and replace proof titles with the placeholder from `calendar.proof_placeholders`. Column P keeps the verbatim content type for traceability.

## Mode 2: Monthly run (first run day of each month)

1. Read the Calendar tab. Find the last dated row and the highest Row ID.
2. Work out the weeks needed to restore a 13-week horizon from today.
3. For each new week, apply the cadence in the plan rules doc and the `plan` section of the config: `plan.posts_per_week`, the weekly proof slot (`plan.proof_slot`: weekday, and which proof type runs in odd and even weeks), the blog Publish and LinkedIn teaser pair (`plan.blog_pair`), the rotation slot and its types (`plan.rotation_slot`), types not repeated in one week (`plan.no_repeat_in_week`), the newsletter frequency, and anything else the plan rules doc sets. A missing key means the plan rules doc decides.
4. Shift any row that lands on a public holiday in `company.holiday_market` as the plan rules doc says (default: to the next working day that has no row of the same type). Say so in Notes.
5. Respect `plan.dependencies`: do not propose a row that needs a fact that is not yet Approved; propose it with What's missing naming the fact and its deadline instead.
6. Propose a clean title and angle for each row that continues the story arc and covers pillars and long-form chapters not used in the last 8 weeks.
7. Fill Pillar, What to post, Channel, Content type and Spec from the mappings and the plan rules playbook. Set Status `Proposed`. Leave G and H empty. For team-owned rows (content type matches `calendar.team_owned_regex`), write in Notes that the team writes it and agents do not draft it. For a teaser (`calendar.teaser_regex`), write in Notes that the agent drafts it once the published blog link is in Notes on the blog row. Fill Sources with the documents the row is based on (plan rules doc and version, long-form chapter, other reference). Fill What's missing with anything a person must provide before the post can be finished, such as proof log sign-off for proof slots.
8. Write the rows as set out in "Writing new rows". Do not touch existing rows.
9. Write a summary of proposed rows (dates, types, titles, rules applied, anything uncertain) for the next weekly brief.

## Guarding Ideas and Milestones writes

Someone may delete, insert or sort rows on the Ideas or Milestones tab while a run is in progress. Before writing any cell on those tabs:

1. Keep the tab as first read, saved exactly as returned (`ideas_before.json` or `milestones_before.json`).
2. Just before writing, read the same range again and save it (`ideas_fresh.json`). Put the planned writes in `tab_writes.json` (`[{"row": 5, "col": "Status", "value": "Scheduled"}]`).
3. Run `python3 scripts/tab_guard.py ideas_before.json ideas_fresh.json tab_writes.json --key "Idea (one line)" --config workspace.json` (Milestones: `--key "Milestone"`).
4. Write only the `accepted` ranges. For an idea or milestone whose write is skipped, do not add its Calendar rows either (run the guard before adding Calendar rows), so the next run picks it up cleanly. Pass `brief_lines` to the orchestrator for the brief.

## Mode 3: Milestone run

1. Read new rows on the Milestones tab where Rows proposed is blank. Skip any milestone whose Confirmed is `Cancelled`.
2. Propose supporting rows: a teaser before, a live post on the day, a recap after, and a press release Distribute (AM) and LinkedIn announcement (PM) pair only for genuine news (launch, funding, major partner).
3. Check each proposed date against existing rows and the cadence. Where a slot is taken, propose the nearest free slot and say so in Notes.
4. Start each new row's Notes with "Milestone: <milestone name exactly as on the Milestones tab>." so the planner can find the rows if the milestone is cancelled later.
5. Write the rows as `Proposed` (see "Writing new rows"), then set Rows proposed on the milestone to `Yes` (through the tab guard).

## Mode 4: Ideas run (every run day, before drafting)

1. Read the Ideas tab. Process rows where Idea is filled and Status is blank or `New`. Ignore `Declined` (people set Declined instead of deleting an idea).
2. For each idea, find the best slot: the Wanted by date if given, otherwise the nearest suitable slot in the next 13 weeks that fits the cadence and pillar balance. Prefer replacing nothing: use a free rotation slot, or propose in Notes a swap for a proof slot that has no approved proof.
3. Check the idea against the rules doc, `writing.*` and the facts sheet. If it needs a claim that is not Approved, a competitor name, a topic in `writing.on_hold_topics`, a launch, availability or delivery date, or anything else the rules forbid, do not schedule it: set Status `Parked` and explain in Agent note in one plain sentence.
4. Otherwise add a Calendar row (see "Writing new rows") with Status `Proposed`, a clean title and angle, Pillar, What to post, Channel, Content type, Sources (the idea's link plus reference files) and What's missing. In Notes write "From Ideas tab: <added by>, <date added>".
5. On the Ideas row set Status `Scheduled`, write the new Row ID in Calendar row and a one-line Agent note naming the proposed date. Check the row with the tab guard first.
6. Also check for rows a person added straight to the Calendar (Date filled, Row ID empty) and fill their empty agent cells as described in the hard rules, including What to post.

## Scripts

| Script | Use |
| --- | --- |
| `scripts/tab_guard.py` | Row guard for Ideas and Milestones writes. Exit 1 if any write was skipped |
| `scripts/verify_calendar.py` | First-run check: plan text against the calendar export, row by row. Exit 1 on any mismatch |
| `scripts/build_calendar.py` | Offline .xlsx copy of the calendar from a rows JSON file (see `examples/sample-rows.json`). Needs openpyxl. Never uploaded as the live calendar |

Run any script with no arguments to see its usage.

## Output to the person

End every run with: rows added (count and Row IDs), any mismatch or rule conflict found, and what needs a person's decision. Keep it brief.
