---
name: weekly-orchestrator
description: Runs the weekly content run. Use when asked to "run the weekly run", "/weekly-run", "run this week's content", "draft next week", "do the Monday run", "recover the missed run", or when the scheduled weekly task fires. Calls the calendar builder, planner, proof intake, short-form drafters and compliance checker, writes their results to the calendar as the only writer, and writes the weekly brief for the approver. Never publishes.
---

# Weekly orchestrator

Run one week of the content system. Find the rows due in the next two plan weeks, have each one drafted in its own subagent, check every draft independently, write the results to the calendar, and write a one-page brief for the approver. This skill is the only writer to the calendar during the run. It never publishes, posts, sends email or submits anything.

## Purpose, assumptions, inputs, outputs, access

- **Purpose:** turn the calendar's Planned rows for the next two plan weeks into checked drafts and a brief, without publishing anything.
- **Assumptions:** `workspace.json` exists and passes `check_workspace.py`; the calendar follows `calendar-builder/references/calendar-schema.md`; the agent register records a passing TEST run before any `live` run.
- **Inputs:** every source in `workspace.json` (`references/locations.md` lists which are read in each mode).
- **Outputs:** one draft doc per plan week (one tab per post), calendar cells allowed by the column lock, the proof log's "Used in calendar row" column, and one brief per run. In shadow mode, only the shadow locations.
- **Access:** read-only on every reference source; write only on the calendar, the proof log (one column), the drafts folder and the briefs folder of the mode in use. Subagents get Read, Bash and Glob on a local bundle only.

## Hard rules

- Never publish, post, send email or submit anything.
- Read `workspace.json` first. Read the client's rules file (`sources.rules`) before any other source: it wins over every other file, including this skill.
- Spelling, units, date style, hashtags and word counts come from `writing.*` in `workspace.json`. They apply to drafts, tabs, Notes and the brief. State the spelling variety in every subagent prompt.
- One writer: only the main session writes to the calendar, the draft docs, the proof log and the brief. Subagents get a local bundle, return JSON and write nothing.
- Every calendar write goes through `scripts/calendar_writes.py plan` first, then `scripts/calendar_writes.py guard` on a fresh read just before writing (the Row ID and Status of each target row must still match the snapshot), and every run ends with `scripts/calendar_writes.py verify` on a read-back. Never write a refused cell. Never write formula columns (Action needed, Draft) or a summary tab such as This Week.
- Cancelled: only a person sets Status `Cancelled`. Never draft, flag, swap, note or write to a Cancelled row, and never count it as overdue. Cancelled rows appear nowhere in agent output: not in the brief, the run summary, the output to the person or any notification.
- Status: set only `Draft ready`, only on a Planned row whose draft passed the compliance checker. Never set Proposed on an existing row, and never set Planned, Approved, Posted or Cancelled. Never draft a Proposed or Cancelled row.
- Claims: drafts state only claims from approved facts sheet rows (`facts.approved_values`). Proof posts use only signed-off proof log items, and quotes word for word. Never invent a customer, partner, quote or result.
- Visuals: no assets folder file and no AI image subject is used twice within `visuals.no_repeat_weeks` either side, including twice in one run (`scripts/visuals.py`). When no unused file fits and `visuals.ai_image_tool` is set, the draft carries an image prompt and an alternative prompt in its tab, and the Visual column says "Needed: <AI image tool> image of <subject>. Prompt in draft tab." When `visuals.ai_image_tool` is null, there are no image prompts: the Visual column says "Needed: <photo or graphic>."
- A draft that fails the compliance checker gets one redraft. If the redraft fails, the tab is written with the failures under "Flags for the approver", one sentence goes in Notes, and Status stays Planned.
- Team-owned rows (content type matches `calendar.team_owned_regex`) are never drafted.
- Evergreen swaps: every row `run.swap_days` days away or fewer that cannot be drafted this run gets a specific swap proposal in Notes (a type from `swaps.types`, with an angle and a long-form source chapter), and a fallback draft of that swap in the week's draft doc. A fallback never changes Status, Draft URL, Original draft, Visual, Content type, Date or Title: it is a Notes line with the tab link. The approver decides whether to swap. Rows held by a `plan.dependencies` item keep the approver's deadline: the planner proposes their swap, and the fallback follows once it is in Notes.
- Mode: use the TEST locations unless the person (or the scheduled task prompt) says `live`, `shadow` or `test shadow`. If it is not stated, ask. Use `live` only when the agent register records a passing TEST run with the current config.
- **Shadow mode** (`shadow` or `test shadow`): read `references/shadow-mode.md` first and follow it wherever it differs from the steps below. A shadow run writes nothing to the calendar, the proof log, the drafts folder or the briefs folder, live or TEST. Its only writes are shadow draft docs, the shadow brief and new rows on the shadow review sheet.
- One run per day: if a brief for this run date and mode already exists, stop and tell the person, unless they said `rerun`.

## Files

Read `references/locations.md` for which `sources.*` keys each mode reads and writes. Read `references/brief-format.md` before writing the brief and `references/subagent-prompts.md` before starting subagents. The drafting skills' own references apply to drafts and doc tabs (`short-form-drafter/references/draft-doc-format.md`). The config keys are explained in `docs/workspace-config.md`.

## Saving source data for the scripts

Scripts read local files and never talk to a platform. Work in `weekly/<run date YYYY-MM-DD>/` in the session workspace. Save every read exactly as returned: if the tool saved a large result to a file, copy that file; otherwise write the response with the Write tool. Never edit saved data by hand.

- **Google Sheets:** the `get_values` response as returned. This is the table shape every script reads: `{"values": [[headers], [row 2], ...]}`.
- **Other tables** (Notion database, Excel file, CSV): convert to the same shape, columns in schema order, header row first. Keep `_source_row.json` (Row ID to page ID or row number) in the run folder so writes go back to the right record.
- **Google Docs:** Docs `read_doc`, saved as returned, then `python3 scripts/doc_text.py <saved>.json <name>.md --expect "<expect_phrase>"`. Never Drive `read_file_content` for a Doc: it can cut long Docs off.
- **Notion pages, GitHub files, SharePoint or OneDrive files, local files, URLs:** save the text as returned as `<name>.md`, then confirm it contains the source's `expect_phrase`.
- **Folders:** one `<subfolder>/<file name>` per line.

If any doc lacks its `expect_phrase`, treat it as cut off and stop the run.

## Steps

1. **Load the config.**
   - Take `workspace.json` from `--config`. If none is given, ask the person where it is. If none exists, run the `workspace-setup` skill first and start this run again afterward.
   - Read it, save it as `weekly/<run date>/shared/workspace.json`, and run `python3 skills/workspace-setup/scripts/check_workspace.py shared/workspace.json`. Stop on any error and tell the person; list warnings in Run details.
   - Note the mode and the run date (today, or `--as-of` in TEST runs).
2. **Same-day check and missed runs.** List the briefs folder of the mode in use and collect the dates in brief titles. If a brief for the run date already exists, stop and tell the person: "A brief for DD MMM YY already exists: <link>. Say rerun to run again." With `rerun`, continue; the brief name gets ` (2)` (or the next free number).
3. **Calendar builder first** (main session, its own rules): on the first run day of the month, the monthly run; every run day, the ideas run; any milestone with Rows proposed blank and Confirmed not Cancelled, the milestone run. Every Ideas and Milestones write goes through the builder's `scripts/tab_guard.py`. Collect its summary of proposed rows and any `brief_lines` from skipped tab writes for the brief. On a manual run that is not the run day (`run.weekday`), run only the ideas run.
4. **Snapshot.** Read each source per the adapter rules above and save it as named in `references/subagent-prompts.md`: calendar (also `before.json`), proof log, facts sheet, milestones, rules, plan rules, voice guide, the assets folder listing (all subfolders) and the long-form source once (`long_form.md`). Copy the client's chapter map (`sources.long_form.chapter_map`) as `chapter-map.md`. Read each `sources.other` entry only when a step needs it (for example, published blog text for a teaser).
5. **Select.** Run `python3 scripts/select_rows.py before.json --config shared/workspace.json --facts shared/facts.json --as-of <date> --briefs <dates>`. Save the output as `select.json`.
   - Rows with action `cancelled` are skipped everywhere: no draft, no note, no swap, and no mention in the brief or any output.
   - From `before.json`, list Approved rows dated within 2 days of the run date whose What's missing cell is not empty. They go in the brief under Needs the approver.
6. **Final text.** For each `final_text` row, read its draft tab (Docs `read_doc`, the tab in Draft URL), save it, and run `python3 scripts/extract_final.py <doc>.json <tab URL>`. Add a `Final text` write with the output exactly.
7. **Planner and proof match, in parallel.** Start the planner agent with the plan bundle. Save its JSON return as `plan/return.json`, and each drafter and checker return in `returns/`, before acting on it. In the main session, run proof intake's `match_proof.py` with `--config shared/workspace.json` (proof-intake SKILL.md step 2) on the same snapshot and save `match.json`.
8. **Draft, in parallel.** Start one subagent per row in one message: a drafter for each `draft` row, and a proof drafter for each `proof` slot the match plan says to draft. Each gets only its own bundle, built with `scripts/make_bundles.py` (subagent-prompts.md). Rows with action `proposed`, `blocked`, `team_owned`, `in_review` or `cancelled` are not drafted. Save each return in `returns/`.
9. **Swaps and fallbacks.** Run `python3 scripts/swap_slots.py before.json select.json match.json --config shared/workspace.json --drafter-blocked <Row IDs whose drafter returned blocked> --as-of <date>`. For each swap with `existing: false`, write a one-line angle for its type and chapter (`chapter-map.md`; you may pick another chapter from `chapters_available` that suits the type better, never one another swap uses) and save all swaps with angles as `swaps_final.json`. Then start one drafter per swap with `fallback: true`, in one message, on bundles from `make_bundles.py ... fallback --rows <ids> --swaps swaps_final.json`. Rows in `fallbacks_skipped` get the swap note only; list them in the brief.
10. **Visuals.** Run `python3 scripts/visuals.py before.json shared/assets.txt returns/<every draft and fallback return, oldest first> --config shared/workspace.json`. For each `resolved` item, write its `visual` and pruned `visual_alternatives` back into that return before building its check bundle; when `changed` is true, say so in the tab's Flags for the approver. When an item has `swap_prompts: true`, also swap `image_prompt` and `image_alt_prompt` in the return. Real drafts are resolved before fallbacks, so a fallback never takes a real draft's file. An `unresolved` draft is treated as a failed check with the fix "pick an unused visual or give an image prompt" (or "name the photo or graphic needed" when there is no AI image tool) and goes to the redraft in step 12.
11. **Check, in parallel.** For each returned draft, fallbacks included, build a check bundle and start a compliance-checker agent per draft, all in one message. Fallback check bundles use `--suffix -fb --content-type "<swap type>"`. The checker never sees the drafter's notes, flags, sources or reasoning.
12. **Redraft once.** For each failed draft, start a fresh drafter subagent with the draft and the numbered fixes. After the redrafts return, run `scripts/visuals.py` again on all final returns (each redraft after the draft it replaces) and apply its output as in step 10. Check each redraft with a fresh compliance-checker agent. Any draft whose visual changes on this pass, redrafted or not, is checked again with a fresh checker before step 13. A second failure stops there (hard rules). Fallbacks follow the same rule.
13. **Write the drafts.** In the main session, one row at a time: find or create the week's draft doc and add the post tab (draft-doc-format.md). Put the checker result on the "Checker:" line. For an AI image visual, add the "Image prompt:", "Alternative prompt:" and "Other visual options:" lines. Failed drafts are written too, with "Checker: failed twice" and the fixes under "Flags for the approver". Fallback tabs use the fallback tab name and the fallback reviewer line (draft-doc-format.md).
14. **Collect writes** in `writes.json` (format in the `calendar_writes.py` header). `<approver>` is `company.approver.name`; `<source label>` is `swaps.source_label`.
    - Passed drafts: Status `Draft ready` (with `"check": "pass"` on that write), Draft URL, Original draft (only if empty), Visual, Sources (append), Notes (append the drafter's flags), What's missing (clear what the draft resolved). Proof drafts also Proof item and the title placeholder, per proof-intake SKILL.md step 5.
    - Failed drafts: Draft URL, Visual, Notes: "Orchestrator DD MMM YY: draft failed the compliance check twice (<short reasons>); not set to Draft ready. <approver> to review the tab."
    - Blocked rows: What's missing (only if empty) and one Notes sentence, unless Notes already says it.
    - Swaps, one Notes append per row from `swaps_final.json` unless `existing` is true: "Orchestrator DD MMM YY: Proposed swap: <type> on <angle> (<source label> chN). <approver> to approve by changing the row." For teasers, start with the `conditional` text: "Orchestrator DD MMM YY: If the <blog> link is not in Notes on the blog row by the morning of DD MMM YY, proposed swap: ...". Proof slots use the same type and chapter in proof intake's own sentence (prefix "Proof intake DD MMM YY:"), one sentence in all, not two.
    - Fallback drafts: Notes append "Orchestrator DD MMM YY: Fallback draft for the proposed swap: <tab link> (checker: passed | passed after redraft | failed twice). Visual: <the fallback's Visual line, which ends with a period> Status stays Planned until <approver> swaps the row." Nothing else on the row. The Visual part lets later runs see the file or image subject.
    - Proposed rows due in the window: Notes "Orchestrator DD MMM YY: due DD MMM YY and still Proposed, so not drafted. <approver> to set Planned or move it." unless already there, or unless the row is listed under a cancelled milestone in the planner's `cancelled_milestones` (the brief lists those once instead).
    - Planner `row_updates` (Notes append; What's missing only if the cell is empty) and proof intake flags.
    - Final text writes.
15. **Lock check, Row ID guard and write.**
    - Run `python3 scripts/calendar_writes.py plan before.json writes.json --config shared/workspace.json`. Report every refused write in the brief and never retry it.
    - Just before writing, read each of the plan's `guard_ranges` (Status, and Notes to Row ID, of the target rows), save each exactly as returned (`fresh_b.json`, `fresh_jm.json`), and run `python3 scripts/calendar_writes.py guard before.json writes.json fresh_b.json fresh_jm.json --config shared/workspace.json > guard.json`.
    - Write only guard's `accepted` cells, each to its exact range and value (Sheets `update_values`; for another platform, the record in `_source_row.json`). Never write a cell from `refused`. Guard's `refused` items (Row ID or Status changed during the run) go at the top of the brief, with a line asking the approver to set Cancelled instead of deleting rows. `plan_refused` repeats the column-lock refusals already reported.
    - Write the proof log's "Used in calendar row" column as proof intake says (the only write outside the calendar, docs and brief), then read it back.
16. **Verify.** Read the calendar again, save it as `after.json`, and run `python3 scripts/calendar_writes.py verify before.json after.json writes.json --guard guard.json --config shared/workspace.json`. Cells a person changed during the run are listed under `changed_by_person_during_run`; report them in Run details. `deleted_row_ids`, `added_row_ids` and the `moved_rows` count go at the top of the brief. Any unexpected change goes at the top of the brief and in the output to the person.
17. **Brief.** Write the brief in the briefs folder of the mode in use (brief-format.md).

## Missed runs

If `missed_runs` is not empty, the scheduled run did not happen (computer off, app closed, connector signed out). This run recovers it: the selection covers overdue and due rows. Name each missed run day in the brief. Overdue rows are listed, never drafted.

## Dates

Every date an agent writes (Notes, brief, doc names, tab names, review rows, output to the person) is DD MMM YY with a leading zero and an uppercase month: 03 NOV 26, never 3 NOV 26. Tab names add the weekday: TUE 03 NOV 26. The scripts print dates this way.

## Output to the person

Up to eight lines: rows set to Draft ready (Row ID, date, tab link), fallback drafts (Row ID, swap type, tab link), AI images to make, rows blocked or failed with the reason, Approved rows due within 2 days with something still missing, refused or guarded writes, missed runs, and the brief link. Never mention Cancelled rows. Dates DD MMM YY with an uppercase month, spelling per `writing.spelling`, no em dashes.
