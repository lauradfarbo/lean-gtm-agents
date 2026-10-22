# Weekly draft doc

One doc per plan week in the drafts folder (`sources.drafts_folder`), one tab per post. The approver reviews a whole week in one doc, edits in the tab, then copies the post text into LinkedIn. The steps below are for Google Docs; on another platform follow the adapter rules in `docs/workspace-config.md` and keep the same names and text.

## Names

- Doc: `Drafts - Week NN (DD MMM YY)`, where NN is the calendar's Week (column N, two digits) and the date is the Monday of that week. Example: `Drafts - Week 06 (09 NOV 26)`. Find an existing week's doc by the `Drafts - Week NN` prefix, and also accept a doc whose week number has no leading zero, rather than making a second doc for the same week.
- Tab: `DDD DD MMM YY - <short type> (<Row ID>)`. Examples: `TUE 10 NOV 26 - Poll (W06-01)`, `TUE 03 NOV 26 - POV (W05-02)`. Days 1 to 9 always have a leading zero.
- First tab (the default "Tab 1"): rename to `Week overview`.
- Fallback tab: `DDD DD MMM YY - FALLBACK <short swap type> (<Row ID>)`. Example: `MON 19 OCT 26 - FALLBACK Poll (W03-01)`. Its reviewer notes start with one extra line, above "First comment": `Fallback: proposed swap for <original content type>, not approved. Status stays Planned. To use it, change the row's Content type and Title / angle, then set Approved.`

## Find or create the doc

1. Drive `search_files`: `parentId = '<drafts folder>' and title contains 'Drafts - Week NN'`.
2. If none: Drive `create_file` with title, parentId and contentMimeType `text/plain`, textContent = the overview text below (it becomes Tab 1). Then rename Tab 1: Docs `update_doc` with `updateDocumentTabProperties` {tabProperties: {tabId: "t.0", title: "Week overview"}, fields: "title"}.
3. If a tab for the same Row ID already exists, do not overwrite it. Add a new tab with " v2" at the end of the title and say so in Notes.

## Add the post tab

1. Docs `update_doc`: `addDocumentTab` {tabProperties: {title: <tab name>}}. Keep the returned tabId.
2. Docs `update_doc`: `insertText` with `endOfSegmentLocation: {tabId}` and the tab text below.
3. Make the line "Notes for the reviewer (do not post)" bold. Nothing else: keep formatting plain so the post copies cleanly.
4. Tab link for the calendar: `https://docs.google.com/document/d/<docId>/edit?tab=<tabId>`.

## Tab text

```
<post text exactly as it should appear on LinkedIn, hashtags included>

----------
Notes for the reviewer (do not post)

First comment: <text with link, or "None">
Alternate hook: <one line>
Poll question and options: <poll only>
Visual: <Use: ..., Needed: <AI image tool> image of ... Prompt in draft tab., Needed: <real photo>, or None needed>
Image prompt: <AI image visuals only. Attach the product reference photo first when the prompt names it>
Alternative prompt: <AI image visuals only>
Other visual options: <visual_alternatives, or "None">
Word count: <n>
Facts used: <fact IDs, comma separated>
Sources: <documents with version, chapter>
Flags for the approver: <anything omitted or uncertain, one sentence each, or "None">
Checker: <pass, or the warnings confirmed>
```

Proof intake adds two lines after Sources: "Proof item: ..." and, when needed, "Do not post before DD MMM YY." (see proof intake's `proof-rules.md`).

Leave out the two prompt lines when the visual is not an AI image. Column I on the calendar gets only the Visual line; the prompts stay in the tab.

The approver copies everything above the dashed line. Edits go in the tab, not in LinkedIn, so Final text stays accurate.

## Week overview text

```
Drafts for Week NN, <Monday DD MMM YY> to <Sunday DD MMM YY>.
One tab per post. Edit in the tab, then set Status to Approved on the calendar.
Copy only the text above the dashed line into LinkedIn.
```
