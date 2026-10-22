# Weekly brief

One doc per run in the briefs folder of the mode in use (`references/locations.md`). The approver (`company.approver.name`) reads it early in the week. One page: short lines, no padding, nothing the approver has to decode.

## Name

`Weekly brief - DD MMM YY` (the run date). A rerun on the same day (the person said `rerun`) adds ` (2)`, then ` (3)`. On TEST, prefix `TEST - `. Simulated test runs (`--as-of`) add ` (simulated)`, for example `TEST - Weekly brief - 30 NOV 26 (simulated)`.

## Create

- **Google Drive:** Drive `create_file` with the title, parentId (the briefs folder) and contentMimeType `text/plain`, textContent = the brief below. It converts to a Google Doc. Then make the section headings bold with Docs `update_doc` (optional).
- **Other platforms** (Notion page, Word Online, local folder): create one page or file with the same title and text, then read it back.

## Text

`<approver>` is `company.approver.name`. `<image tool>` is `visuals.ai_image_tool`.

```
Weekly brief: <run day DD MMM YY>, covering <first date> to <last date>
<one line: N drafts ready for review, N blocked, N need <approver>'s decision>

Missed runs
<only if missed_runs is not empty: "No run on <DDD> DD MMM YY. This run covers those rows.">

Ready for review
<Row ID>, <DDD DD MMM YY>, <what to post>: <draft tab link>. <flag for the approver, if any>

Fallback drafts (swap proposed)
<Row ID>, <DDD DD MMM YY>, <swap type> instead of <original content type>: <fallback tab link>. <checker result>. To use it, change the row, then set Approved.

Needs <approver>
<one line per decision: Proposed rows due soon, swap proposals, facts to approve, drafts that failed the check twice, rows of a cancelled milestone (one line per milestone)>
<Approved rows due within 2 days with What's missing filled: "<Row ID>, <DDD DD MMM YY>: Approved, but What's missing still says '<text>'. Clear it or move the row.">

Images to make (<image tool>)
<Row ID>, <DDD DD MMM YY>, <subject from the Visual column>: <draft tab link>. <if visuals.product_reference_photo is set and the prompt names it: "Attach the product reference photo.">

Blocked
<Row ID>, <date>: <what is missing, in plain words, and who provides it>

Proof slots
<Row ID>, <date>: <drafted from proof log row N | flagged: reason | swap proposed>

Risks (planner)
<one sentence each, from the planner's brief_risks and row notes on rows not already listed above>

Calendar changes proposed
<from the calendar builder: new Proposed rows, ideas scheduled or parked>

Team-owned this period
<rows matching calendar.team_owned_regex in the window, with date: the team writes these>

Overdue
<rows dated before the run date and not Posted or Cancelled: Row ID, date, Status. "Set Posted if it went out, move it, or set Cancelled.">

Run details
Files: <TEST or live>. Config: <workspace.json location, updated date>; check_workspace: <clean | N warnings: list>. <title of each doc source read, as in sources.*.title>.
Checker: <N passed first time, N passed after one redraft, N failed twice>.
Calendar writes: <N cells written>; refused: <none | list>; Row ID guard: <clean | list>; verify: <clean | list>; changed by a person during the run: <none | cells>; rows deleted or added during the run: <none | Row IDs, and N rows moved>.
Ideas and Milestones writes skipped: <none | tab_guard brief_lines>.
Final text copied: <Row IDs or none>.
```

## Rules

- Leave out a section when it has nothing in it, except Ready for review and Run details.
- Leave out "Images to make" when `visuals.ai_image_tool` is null; list the photos or graphics needed under Needs the approver instead.
- Cancelled rows appear nowhere in the brief: no section, no count, no line. A cancelled milestone's remaining rows that are not yet Cancelled are listed once under Needs the approver so the approver can cancel them in one go.
- Every swap proposed this run also gets a line under Needs the approver.
- A proof slot waiting for sign-off whose cut-off date has passed says so: "the sign-off cut-off of DD MMM YY has passed".
- In Run details, the Checker line counts fallback drafts separately: "Checker: drafts <...>; fallbacks <...>".
- A Row ID guard refusal or a verify problem goes at the very top of the brief, above the first line.
- Never paste a draft into the brief; link the tab.
- Dates DD MMM YY with an uppercase month, spelling per `writing.spelling`, no em dashes.

## Shadow brief

Name: `SHADOW - Weekly brief - DD MMM YY`; on TEST, `TEST - SHADOW - Weekly brief - DD MMM YY` (add ` (simulated)` for `--as-of` runs). Folder: `sources.shadow.briefs_folder` for the mode in use. The person testing the system reads it, not the approver.

Same text as above, with these changes:

- First line: `Shadow run: nothing was written to the live calendar, proof log, drafts folder or briefs folder.` On TEST, say TEST instead of live.
- Ready for review: add the live status to each line: `<Row ID>, <DDD DD MMM YY>, <what to post> (live: <status>): <draft tab link>. <flag>`.
- Rename "Needs <approver>" to "Would need <approver>" and "Calendar changes proposed" to "Calendar changes proposed (not written)".
- Add a section after Overdue:

```
Calendar writes not made
<one line per brief_lines entry from calendar_writes.py shadow, then the proof log writes; "None" if empty>
```

- Run details: `Files: shadow (live reads) | test shadow (TEST reads).` and `Verify: calendar <clean | list>; proof log <clean | list>; live drafts and briefs folders <unchanged | list>.` Add `Review rows added: N (shadow review sheet).`
- Final text copied: `not copied in shadow (<Row IDs>)`.
