---
name: proof-intake
description: Fills the Partner Win and Customer Proof calendar slots from signed-off proof log items only, drafting the LinkedIn post into the weekly draft doc. Use when asked to "run proof intake", "check the proof log", "draft the partner post", "draft the customer story", "fill the proof slots", "process new proof", or when the weekly orchestrator calls proof intake. Flags empty slots and proposes swaps; never invents a customer, partner or quote.
---

# Proof intake

Match items in the proof log to the proof slots on the content calendar (the content types in `calendar.proof_types`, usually Partner Win and Customer Proof). Draft a post only from a signed-off item. With no usable proof, flag the slot and propose a swap. This skill never publishes, and never writes a quote, name or result that is not in the proof log.

Read `workspace.json` first. If there is none, run the `workspace-setup` skill and stop.

## Purpose, inputs, outputs, access

- **Purpose:** turn signed-off proof into review-ready posts, and flag proof slots that cannot run.
- **Assumptions:** the calendar has the A to V schema and the proof log has the A to J columns in `references/proof-rules.md`.
- **Inputs:** `workspace.json`, the calendar, the proof log, the rules file, the voice guide, approved facts and the assets listing. See `references/locations.md`.
- **Outputs:** one tab per drafted slot in the week's draft doc; on the calendar, the cells listed under "Writes"; on the proof log, column J only.
- **Access:** read-only on reference sources; write on the calendar (listed cells), the proof log (column J) and the drafts folder.

## Hard rules

- Never publish, post, send email or submit anything.
- Read the rules file and the voice guide before writing. The rules file wins over every other file, including this skill.
- Draft only from a proof log item with Sign-off status `Yes`; Organization, What happened and Sign-off from filled; and Can go public from on or before the slot date. Anything else is not proof.
- Use the organization's name exactly as in the proof log. Name no other customer, partner, person or company.
- Use the approved quote word for word, with its attribution exactly as written, or not at all. Never shorten, tidy or paraphrase it into quotation marks. Never write a quote.
- State what happened only as the proof log states it. No added figures, results, scope, dates or adjectives the item does not give. Claims about the company need a fact ID whose Status is in `facts.approved_values`, as in the short-form drafter.
- Every other content rule applies: `writing.competitors`, `writing.custom_rules`, `writing.on_hold_topics`, no launch, availability or delivery dates, and the spelling and units in the config.
- If the go-public date is after the run date, the draft is allowed, but the reviewer notes and Notes say "Do not post before DD MMM YY".
- Never generate images or video, and never use an AI image prompt for a proof post: it shows a real organization. The visual is an assets file for that organization (not used on another row within `visuals.no_repeat_weeks` weeks) or `Needed: <organization> logo or photo, with their permission`.
- Skip `Cancelled` rows and never mention them in any output.
- Use TEST files until the agent register records a passing test for this skill.

## Writes

- **Calendar**, on the slot row only: Status (B, `Draft ready` only), Title / angle (F, only while it reads the placeholder in `calendar.proof_placeholders`), Visual (I), Notes (J, append only), What's missing (K, this row only), Sources (L, append only), Proof item (R), Draft URL (U) and Original draft (V, write once). Never write G, H, formula columns or any other tab. Never change Status to anything else, and never change Content type or Date to make a swap.
- **Proof log**: only "Used in calendar row (agent fills)" (column J).
- Before each write, re-read the row and confirm its Row ID and Status are unchanged; after it, read back and confirm.

## Files

Read `references/locations.md` for the `sources.*` keys, `references/proof-rules.md` for matching, flags, swaps and the post shape, and `references/draft-doc-format.md` before creating docs or tabs.

## Steps

1. **Read** the calendar (A1:V) and the proof log (A1:J). Save both as JSON in the `{"values": [...]}` shape.
2. **Match**: run `python3 scripts/match_proof.py calendar.json proof_log.json --config workspace.json` (add `--as-of YYYY-MM-DD` only for tests). The plan lists, for each proof slot in the next 14 days, `draft` with a proof row or `flag` with the reasons, plus items to mark as not used and proof log problems. Follow the plan. If a slot's `person_note` sets a condition (for example a specific partner or event), check the item meets it; if not, treat the slot as `flag` and say why.
3. **For each `draft` slot**, in its own subagent when there are several (one row, one proof item, the rules, voice guide and approved facts only):
   1. Write the post as set out in proof-rules.md, plus one alternate hook, the first comment (only if the item gives a public link) and the visual line.
   2. Save the draft and the proof item as JSON. Run `python3 scripts/check_draft.py draft.json --config workspace.json --facts facts.json`, then `python3 scripts/check_proof_post.py draft.json proof_item.json --config workspace.json` (add `--live` on the live calendar). Fix every fail and resolve every warning, as in the drafter.
   3. Check each sentence: it maps to the proof item or to a fact ID. Remove anything that does not.
   4. Repeat the checks once if anything changed. If still failing, do not set Draft ready: write the tab with the failures under "Flags for the approver", add one sentence to Notes and stop for this row.
4. **Write the doc tab** in the week's draft doc (draft-doc-format.md). Short type in the tab name: `Partner news` or `Customer story`, or the client's equivalent.
5. **Write the calendar row**: U tab link; V post text (only if empty); I visual; R the proof log row link; F the new title (only when `title_placeholder` is true; proof-rules.md); L append "; Proof intake: Proof log row N, <rules title>, <voice guide title>; Facts <IDs>"; J append "Proof intake DD MMM YY: drafted from proof log row N." plus "Do not post before DD MMM YY." if needed; K clear the proof request; B `Draft ready`.
6. **Write the proof log**: J on the used item = "<Row ID> (drafted DD MMM YY)".
7. **For each `flag` slot**: append one sentence to Notes per proof-rules.md, with the swap proposal when `propose_swap` is true. Skip if `already_flagged` is true. Leave K as it is (it already names what a person must provide); add to K only if it is empty.
8. **For each item in `mark_not_used_signoff_no`**: J = "Not used: sign-off No (DD MMM YY)".
9. **For `proof_log_problems`**: do not edit the item. Report each in the output so a person fixes it.

## Called by the weekly orchestrator

The weekly orchestrator runs step 2 in the main session and step 3 in a subagent per slot. The subagent gets a local bundle (`workspace.json`, `row.json`, `proof_item.json`, rules, voice guide, approved facts, assets listing), uses only Read, Bash and Glob, writes nothing and returns JSON as set out in the orchestrator's subagent prompts. The orchestrator runs the independent compliance checker, then does steps 4 to 9 as the only writer.

## Output to the person

One line per proof slot: Row ID, date, result (Draft ready, flagged, swap proposed), the tab link or the reason, and the proof log row used. Then one line per proof log problem and per signed-off item waiting for a later slot. Brief. Dates in DD MMM YY with an uppercase month.
