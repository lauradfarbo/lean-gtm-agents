# Proof rules

The client's rules file states what counts as proof; it wins over this file. Type names, placeholders, the swap window and the approver come from `workspace.json`.

## Proof log columns

| Col | Column | Filled by | Notes |
| --- | --- | --- | --- |
| A | Date logged | Person | Date |
| B | Type | Person | A key of `calendar.proof_types`, for example `Partner` or `Customer` |
| C | Organization | Person | Exact public name |
| D | What happened | Person | Plain facts the organization agreed can be public |
| E | Approved quote (verbatim) | Person | `"Quote text" (Name, Role, Organization)` or blank |
| F | Sign-off from (name) | Person | Who signed off at the organization |
| G | Sign-off status | Person | `Yes`, `No` or `Pending` |
| H | Can go public from | Person | Date |
| I | Logged by | Person | A name in `company.people` |
| J | Used in calendar row (agent fills) | Proof intake | Row ID and date drafted, or "Not used: sign-off No" |

## Matching (match_proof.py does this)

- Each proof log Type fills the content type it maps to in `calendar.proof_types` (for example Partner to Partner Win, Customer to Customer Proof).
- Slots: Status `Planned`, Proof item empty, dated in the next 14 days.
- Earliest slot first, filled with the earliest-logged usable item whose go-public date is on or before the slot date.
- A note from the approver on a slot (a sentence in Notes starting "<approver first name>," or containing "(<approver first name>,", returned as `person_note`) is a condition, for example "the first partner at the partner's own event". Use an item there only if it meets the condition.
- A signed-off item that cannot be used yet waits for a later slot. Report it; write nothing in the proof log.

## Flags and swaps

Write one sentence per issue in Notes, prefixed "Proof intake DD MMM YY:". N is the proof log row. The swap window is `run.swap_days` (5 if not set).

| Situation | Notes | Swap |
| --- | --- | --- |
| No proof item for the type | "No signed-off <partner/customer> proof in the proof log for this slot." | Only if the slot is within the swap window |
| An item has Sign-off status No | "Proof log row N (<organization>) has sign-off No, so it is not used." | Yes, now |
| An item is Pending or blank, cut-off ahead | "Proof log row N (<organization>) is waiting for sign-off; it can fill this slot if signed off by <signoff_cutoff>." | Only if within the swap window |
| An item is Pending or blank, cut-off passed (`cutoff_passed` true) | "Proof log row N (<organization>) is waiting for sign-off; the sign-off cut-off of <signoff_cutoff> has passed." | Only if within the swap window |
| Signed off, but public after the slot | "Proof log row N (<organization>) can go public from DD MMM YY, after this slot." | Only if within the swap window |

The sign-off cut-off is the slot date minus the swap window. Swap proposal, added as one more sentence: "Proposed swap: <a type from `swaps.types`> on <one-line angle> (<`swaps.source_label`> ch N). <Approver> to approve by changing the row." Pick the type the nearby rows use least (check the same and the next week), and an angle from a chapter in `swaps.chapters`, not in `swaps.excluded_chapters`, and not used in Sources on the last 8 weeks of rows. When the weekly orchestrator runs, take the type and chapter from its swap output so swaps in one run never repeat; the orchestrator adds a fallback draft of the swap. Never change Status, Date, Content type or Title to make the swap. Never propose an anonymous customer or partner story.

## The post

- Partner Win: what the partnership is, in the proof log's words; why it matters to the partner's customers, using approved fact IDs; one call to action. Customer Proof: the use case or result exactly as stated; the problem it addresses for the audience in the voice guide; one call to action, usually a question.
- Name the organization once in full, exactly as in the proof log, early in the post. Suggest in the reviewer notes that the approver tags its company page.
- Approved quote: if used, on its own lines, in straight double quotation marks, word for word, followed by the attribution as written. At most one quote.
- Word count, opening, hashtags and links as in `writing.*` (the same rules as the short-form drafter). Add any hashtag a `writing.hashtags.conditional` rule asks for.
- No figures unless they are in What happened or on an approved fact.
- Visual: `Use: <file> (<visuals.asset_prefix>/<subfolder>)` only if a file for this organization exists, else `Needed: <organization> logo or photo, with their permission`.

## Title / angle (F)

Replace the placeholder only (`calendar.proof_placeholders` for the content type; `match_proof.py` returns `title_placeholder: true`): "<Short type>: <organization> <what, in 3 to 6 words>", for example "Partner news: Northgate Facilities joins as a reseller" or "Customer story: Harlow Council monthly energy reports". Never overwrite a title a person wrote.

## Proof item link (R)

For a Google Sheet: `https://docs.google.com/spreadsheets/d/<proof log>/edit#gid=<sources.proof_log.sheet_gid>&range=A<row>`. On another platform, the link to the record.

## Reviewer notes additions

Add under the standard reviewer notes: "Proof item: proof log row N, signed off by <name>, public from DD MMM YY." and "Do not post before DD MMM YY." when the public date is after the run date.
