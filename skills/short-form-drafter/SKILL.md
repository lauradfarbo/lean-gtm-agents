---
name: short-form-drafter
description: Drafts LinkedIn posts from content calendar rows into the weekly draft doc, one tab per post. Use when asked to "draft row W06-01", "draft this week's posts", "draft the long-form push", "write the LinkedIn post for this row", or when the weekly orchestrator calls the drafter for a Planned LinkedIn row. Covers teasers, press release announcements, long-form source pushes, industry POV, polls, event posts, gratitude, year-in-review and short video scripts. Not for Partner Win or Customer Proof (proof intake) or team-owned rows such as blogs, newsletters and press release distribution.
---

# Short-form drafter

Turn one Planned LinkedIn row on the content calendar into a review-ready draft: the post, one alternate hook, a visual, the facts used and the sources. The draft goes into the week's draft doc as its own tab. The approver (`company.approver.name`) reviews, edits in the tab and posts. This skill never publishes.

Read `workspace.json` first. If there is none, run the `workspace-setup` skill and stop.

## Purpose, inputs, outputs, access

- **Purpose:** one review-ready LinkedIn draft per Planned row, built only from approved facts.
- **Assumptions:** the calendar exists with the A to V schema, the rules file and voice guide exist, and the facts sheet has a Status column.
- **Inputs:** `workspace.json`, the rules file, the voice guide, approved facts, the assets folder listing, one chapter of the long-form source (through the client's chapter map), the calendar row and, for teasers, the published blog. See `references/locations.md`.
- **Outputs:** one tab in the week's draft doc; on the calendar row, the cells listed under "Calendar writes".
- **Access:** read-only on every reference source; write on the calendar (listed cells only) and the drafts folder.

## Hard rules

- Never publish, post, send email or submit anything.
- Read the rules file and the voice guide before writing. The rules file wins over every other file, including this skill.
- State only claims from facts sheet rows whose Status is in `facts.approved_values`. Anything else is omitted or written under "Flags for the approver". The long-form source supplies angles, not approved claims.
- Never name a company in `writing.competitors`, or any consumer brand. Compare categories, not companies.
- Never invent customers, partners, quotes, results, attendees, conversations or figures.
- No launch, availability or delivery dates unless the rules file allows them. Words in `writing.date_words_warn` are checked.
- Apply every client claim rule in `writing.custom_rules` and keep off every topic in `writing.on_hold_topics` while its fact is not approved. Use the approved wording each rule's message names.
- Agents never generate images or video. Visuals come from the assets folder; when no unused file fits and `visuals.ai_image_tool` is set, the draft gives an image prompt for the approver to run (`references/post-types.md`). Never reuse an assets file or an AI image subject used on another row within `visuals.no_repeat_weeks` weeks either side.
- Spelling variety and units follow `writing.spelling` and `writing.units`.
- Draft only rows with Status `Planned`. Ignore `Proposed` and `Cancelled`, and never mention a Cancelled row in any output. Never draft proof rows (`calendar.proof_types`) or team-owned rows (`calendar.team_owned_regex`).
- Use the TEST calendar and TEST drafts folder until the agent register records a passing test for this skill.

## Calendar writes

Only these cells on the row being drafted: Status (B, to `Draft ready` only), Visual (I), Notes (J, append only), What's missing (K, this row only), Sources (L, append only), Draft URL (U) and Original draft (V, write once, never overwrite). Never write G, H, formula columns or any other tab. Before writing, re-read the row and confirm its Row ID and Status are unchanged; after writing, read it back and confirm each cell.

## Files

Read `references/locations.md` for the `sources.*` keys this skill uses, `references/post-types.md` for what each content type needs, and `references/draft-doc-format.md` before creating docs or tabs. Read the client's chapter map (named in `sources.long_form.chapter_map`; template at `templates/chapter-map.md`) before using the long-form source.

## Steps for one row

**Fallback drafts.** When the bundle holds `fallback.json`, the orchestrator has proposed an evergreen swap for a row that cannot run. Draft the swap in `row.json` (a type from `swaps.types`, on its angle, from the long-form chapter in `fallback.json`), never the original row. The post stands on its own: no mention of the original topic, the swap or the reason. Skip the blocker check in step 2 for the original content type.

1. **Read the row** (Calendar A to V) and confirm: Status is `Planned`, Channel is LinkedIn, and the content type is one this skill drafts. If not, stop and report why.
2. **Check blockers** from post-types.md: a teaser needs the published blog link in Notes on the blog row; an event live or recap post needs approved event facts and real photos; a row on an on-hold topic is skipped. If blocked, do not draft. Write the exact item needed in What's missing and one sentence in Notes, then stop.
3. **Load context** (keep it lean): the rules file, the voice guide, the approved facts, the assets listing (all subfolders), the relevant long-form chapter only, and for teasers the published blog. Read Sources on earlier rows of the same type (`recent.txt` in a bundle) to avoid repeating an angle, and the Visual column of rows within the no-repeat window (`visuals_recent.txt`) to avoid repeating an image.
4. **Plan the post** before writing: the one idea, the hook, the fact IDs each claim will use, the call to action and the visual (post-types.md, "Visual line"). A claim with no fact ID does not go in.
5. **Write** the post, the alternate hook, the first comment (only if there is a link) and, for polls, the question and 2 to 4 options. For video types, write the shot list and script under the reviewer notes, and the caption post as the post.
6. **Check mechanically**: save the draft as JSON and run `python3 scripts/check_draft.py draft.json --config workspace.json --facts facts.json` (see the script header for the format; type is `post`, `founder`, `poll` or `video`). Fix every fail. Resolve every warning: change the text, or confirm it under "Checker" in the reviewer notes (for example "figure confirmed: fact C04 with source named").
7. **Check claims**: go sentence by sentence and confirm each factual statement maps to a fact ID. Remove or flag any that do not. Work through the voice guide's pre-publish checklist.
8. **Repeat 6 and 7** once if anything changed. If it still fails, do not set Draft ready: write the tab with the failures under "Flags for the approver", write one sentence in Notes, and leave Status as is.
9. **Write the doc tab** as set out in draft-doc-format.md and get the tab link.
10. **Write the calendar row**: U = tab link; V = post text exactly as in the tab (only if V is empty); I = the visual line (for an AI image, only "Needed: <AI image tool> image of <subject>. Prompt in draft tab."; the prompts stay in the tab); L = append "; Drafter: <documents and versions>; Facts <IDs>"; J = append one sentence per flag, prefixed "Drafter DD MMM YY:"; K = clear only what this draft resolved; B = `Draft ready` if steps 6 to 8 passed.

## Running for several rows

Draft each row in its own subagent with only that row and the files in step 3, so drafts do not borrow each other's angles. Subagents get a local bundle, use only Read, Bash and Glob, and return JSON: the post, hook, first comment, visual, visual alternatives, image prompts, fact IDs, sources, flags and checker result. The main session alone writes the doc tabs and the calendar, one row at a time. When the weekly orchestrator calls this skill, the drafter runs steps 1 to 8 only, writes nothing to any platform, and returns the JSON set out in the orchestrator's subagent prompts. The orchestrator's independent compliance checker then checks the draft before Status changes.

## Output to the person

One line per row: Row ID, date, result (Draft ready, blocked, or failed checks), the tab link, and any flag for the approver. Brief. Dates in DD MMM YY with an uppercase month.
