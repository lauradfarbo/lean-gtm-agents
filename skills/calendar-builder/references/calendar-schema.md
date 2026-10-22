# Content calendar schema

The calendar is used by people who are not marketers. People change Status and Notes only. Everything else is filled by agents or formulas.

Where a value below comes from `workspace.json`, the key is named in backticks. A missing optional key falls back to the default shown.

## Tabs (in order)

1. **This Week**: formula view of the next 14 days plus anything overdue. Draft links open the post's tab in the weekly draft doc. Row 1 links to the Calendar filter view where Status is changed. Never write to it.
2. **Calendar**: one row per line item.
3. **Ideas**: post ideas from the approver and the team.
4. **Milestones**: trade shows, launches, webinars, funding dates.
5. **How to use**: plain-language instructions for people.

## Calendar columns (fixed order, A to V)

Visible (A to L, dark header):

| Col | Column | Filled by | Rule |
| --- | --- | --- | --- |
| A | Date | Builder | Real date, written as `YYYY-MM-DD`, displayed `ddd d mmm yy` |
| B | Status | Agents and people | Dropdown, values below |
| C | What to post | Builder | Plain-language format from the mapping below |
| D | Pillar | Builder | From the pillar mapping; the approver may override |
| E | Channel | Builder | Verbatim from the plan |
| F | Title / angle | Builder | Clean title: no quote marks. Proof slots show the placeholder from `calendar.proof_placeholders` until proof intake links approved proof |
| G | Action needed | Formula | Single ARRAYFORMULA in G2. Team-owned rows (content type matches `calendar.team_owned_regex`) show "Team writes this: set Posted when live". Never write to G |
| H | Draft | Formula | Single ARRAYFORMULA in H2: a link to U, showing the first line of V (up to 80 characters) or "Open draft". Never write to H |
| I | Visual | Drafting agent | "Use: <file name> (<`visuals.asset_prefix`>/<subfolder>)", "Needed: <`visuals.ai_image_tool`> image of <subject>. Prompt in draft tab." (only when an AI image tool is set), "Needed: <photo, video or graphic>" or "None needed (LinkedIn renders the poll)". No file or AI image subject is reused within `visuals.no_repeat_weeks` weeks either side (default 8) |
| J | Notes | Planner, agents, people | One plain sentence per issue: blockers, swap proposals, team-owned rows |
| K | What's missing | Planner, proof intake, drafters | Exactly what a person must provide to finish the post (proof log sign-off, blog link, photos, a decision). Cleared by the agent once provided. Drives "Waiting on" in Action needed |
| L | Sources | Builder, drafters | Every document the row draws on, with version, plus facts sheet IDs once drafted (for example "Energy Reporting Without the Spreadsheet ch3; Plan Rules 1.0; Facts C02, M05"). Lets the team see when a source is out of date |

Agent columns (M to V, gray header, collapsed column group, warning-only protection):

| Col | Column | Filled by | Rule |
| --- | --- | --- | --- |
| M | Row ID | Builder | `W{week:02d}-{seq:02d}`. Never reused or renumbered |
| N | Week | Builder | Plan week number, counted from `plan.week1_monday` |
| O | AM/PM | Builder | `AM`, `PM` or blank |
| P | Content type | Builder | Verbatim from the plan; the key drafting agents use |
| Q | Spec | Builder | Verbatim "What to create" text from the plan. Word counts here are replaced by the voice guide's |
| R | Proof item | Proof intake | Link to the proof log row (proof slots only) |
| S | Published link | Agent, optional | Live post URL if the agent can find it |
| T | Final text | Agent | Copied from the draft tab (text above the dashed line) when Status becomes Posted |
| U | Draft URL | Drafting agent | Link to the post's tab in the weekly draft doc, for example `https://docs.google.com/document/d/<docId>/edit?tab=<tabId>` |
| V | Original draft | Drafting agent | The post text as first drafted. Written once, never overwritten. The learning agent compares it with Final text |

## Status values

The list comes from `calendar.statuses`. Defaults:

| Value | Set by | Meaning |
| --- | --- | --- |
| Proposed | Calendar builder | New row awaiting approval. Drafters ignore it |
| Planned | Approver | Approved slot, ready to draft |
| Draft ready | Drafting agent | Draft linked, awaiting review |
| Approved | Approver | Ready to post on the date |
| Posted | Approver | Live |
| Cancelled | Approver | Dropped. The row stays as history. Agents never draft, flag, write to or mention it. Use this instead of deleting a row |

Agents set only Proposed and Draft ready. A swap is proposed in Notes, never by changing Status. If the client uses other Status words, replace them in the formulas below as well.

## Pillar mapping (by content type)

Defaults. A client can replace them with `calendar.pillar_map`, a list of `[regex, pillar]` pairs checked in order (case-insensitive).

| Content type contains | Pillar |
| --- | --- |
| Partner Win, Customer Proof (the `calendar.proof_types` values) | Partner & Customer Proof |
| Press Release, Trade show | PR & Press |
| Blog, video, Gratitude, Year-in-review | Product & Brand Education |
| The long-form label (`swaps.source_label`), Newsletter, Event, Live event | Lead Generation |
| Poll | Engagement |
| POV | Thought Leadership |

## "What to post" mapping

Defaults. A client can replace them with `calendar.what_to_post_map`, a list of `[regex, text]` pairs checked in order.

| Content type | What to post |
| --- | --- |
| Press Release - Distribute | Press release: wires, trade press and website (post first) |
| Press Release - LinkedIn announcement | LinkedIn post: press release announcement (later the same day) |
| Partner Win | LinkedIn post: partner news |
| Customer Proof | LinkedIn post: customer story |
| Any video | LinkedIn video |
| Blog N - Publish | Blog article on website (post first) |
| Blog N - LinkedIn teaser | LinkedIn post: blog teaser (2 to 4 hours after the blog) |
| Trade show teaser, live, recap | LinkedIn post: <show> trade show |
| Long-form launch or push (contains `swaps.source_label`) | LinkedIn post: <label> promotion |
| Newsletter (any) | LinkedIn newsletter |
| Event announcement | LinkedIn post and LinkedIn Event listing |
| Event reminder | LinkedIn post: webinar reminder |
| Live event | Live webinar and LinkedIn post |
| Poll | LinkedIn poll |
| Industry POV | LinkedIn post: opinion |
| Gratitude post | LinkedIn post: thank you |
| Year-in-review | LinkedIn post: year in review |

## Formulas (write once, on build only)

Replace `<team_owned_regex>` with `calendar.team_owned_regex` (default `Publish|Newsletter|Distribute`).

Calendar!G2:
```
=ARRAYFORMULA(IF(A2:A="","",IF(B2:B="Posted","Done",IF(B2:B="Cancelled","Cancelled: no action",IF(A2:A<TODAY(),"Overdue: post it or update the status",IF(B2:B="Proposed","New slot: review, then set Planned",IF(REGEXMATCH(P2:P&"","<team_owned_regex>"),IF(A2:A=TODAY(),"Team: publish today, then set Posted","Team writes this: set Posted when live"),IF(B2:B="Approved",IF(A2:A=TODAY(),"Post today","Ready: post on the date"),IF(B2:B="Draft ready","Review the draft, then set Approved",IF(K2:K<>"","Waiting on: see What's missing",IF(A2:A-TODAY()<=7,"Draft due","")))))))))))
```

Calendar!H2:
```
=ARRAYFORMULA(IF(U2:U="","",HYPERLINK(U2:U,IF(V2:V="","Open draft",IF(LEN(REGEXEXTRACT(V2:V&"","^[^\n]*"))>80,LEFT(REGEXEXTRACT(V2:V&"","^[^\n]*"),77)&"...",REGEXEXTRACT(V2:V&"","^[^\n]*"))))))
```

A HYPERLINK built inside LET, HSTACK or MAP shows the text but is not clickable, so the Draft links use the plain ARRAYFORMULA pattern above.

### This Week tab

Layout: A1:J1 merged, light fill, bold, holding the filter view link (below). Headers in row 2, A2:L2: Date, Status, What to post, Channel, Title / angle, Action needed, What's missing, Draft, Visual, Notes, Draft URL, Original draft. Columns K and L are hidden helpers. Freeze rows 1 and 2. A3 and I3 use the same filter and sort, so their rows line up. The tab stays read-only because any typed value breaks its formulas.

This Week!A1 (replace `<sheetId>`, `<calendarGid>` and `<filterViewId>`):
```
=HYPERLINK("https://docs.google.com/spreadsheets/d/<sheetId>/edit#gid=<calendarGid>&fvid=<filterViewId>","To change a Status, click here. It opens the Calendar showing only these posts. Click a Draft link to open the post.")
```

This Week!A3 (columns A to G):
```
=IFERROR(CHOOSECOLS(SORT(FILTER({Calendar!A2:A,Calendar!B2:B,Calendar!C2:C,Calendar!E2:E,Calendar!F2:F,Calendar!G2:G,Calendar!K2:K},Calendar!A2:A<>"",Calendar!A2:A<=TODAY()+13,Calendar!B2:B<>"Cancelled",(Calendar!A2:A>=TODAY())+(Calendar!B2:B<>"Posted")),1,TRUE),1,2,3,4,5,6,7),"Nothing due in the next 14 days")
```

This Week!I3 (columns I to L: Visual, Notes, Draft URL, Original draft):
```
=IFERROR(CHOOSECOLS(SORT(FILTER({Calendar!I2:I,Calendar!J2:J,Calendar!U2:U,Calendar!V2:V,Calendar!A2:A},Calendar!A2:A<>"",Calendar!A2:A<=TODAY()+13,Calendar!B2:B<>"Cancelled",(Calendar!A2:A>=TODAY())+(Calendar!B2:B<>"Posted")),5,TRUE),1,2,3,4),"")
```

This Week!H3 (the clickable Draft link, same pattern as Calendar!H2):
```
=ARRAYFORMULA(IF(K3:K="","",HYPERLINK(K3:K,IF(L3:L="","Open draft",IF(LEN(REGEXEXTRACT(L3:L&"","^[^\n]*"))>80,LEFT(REGEXEXTRACT(L3:L&"","^[^\n]*"),77)&"...",REGEXEXTRACT(L3:L&"","^[^\n]*"))))))
```

### Filter view

Calendar filter view "This Week: update Status here" (`addFilterView`): range Calendar A:V, sort by column A ascending, filter on column A with CUSTOM_FORMULA:

```
=AND($A2<>"",$A2<=TODAY()+13,$B2<>"Cancelled",OR($A2>=TODAY(),$B2<>"Posted"))
```

It shows the same rows as This Week and only changes what the person who opens it sees.

When adding rows, write `null` to G and H: the formulas fill them. See "Writing new rows" in SKILL.md.

## Formatting

Neutral defaults. Replace them with the client's palette in their sheet, not in this repo.

| Element | Format |
| --- | --- |
| Visible header (A to L) | `#1F2933`, white bold text |
| Agent header (M to V) | `#6B7280`, white bold text |
| Proposed | `#FFF4CC` |
| Planned | White |
| Draft ready | `#E3EEF7` |
| Approved | `#1E6B52`, white bold text |
| Posted | `#E5E7EB` |
| Cancelled | `#E5E7EB`, gray strikethrough text |
| Overdue (date past, not Posted or Cancelled) | `#F8D7D3`, bold |
| Today's rows | Bold |
| Even weeks | Banded `#F5F7F9` |

- Freeze row 1 and columns A to B. Filter on A1:V.
- Action needed in bold. Wrap What to post, Title, Action needed, Visual, Notes, What's missing, Sources. What's missing in dark red text.
- Columns M to V in one collapsed column group with warning-only protection. G and H and the whole This Week tab are also warning-only protected.
- Dropdowns: Status (B) from `calendar.statuses`, AM/PM (O).

## Ideas tab columns (A to H)

Idea (one line), Added by, Date added, Wanted by, Link or source, Status, Calendar row, Agent note.

People fill Idea, Added by, Date added, Wanted by (optional) and Link or source (optional). The agent fills Status (`Scheduled` or `Parked`; people may set `Declined`; blank or `New` means new), Calendar row and Agent note. Columns G and H have warning-only protection.

## Milestones tab columns (A to G)

Milestone, Type (Trade show, Launch, Webinar, Funding, Partner, Product), Start date, End date, Confirmed (Yes, No, Cancelled), Notes, Rows proposed (Yes or blank).

A person sets Confirmed to Cancelled instead of deleting a milestone. The builder proposes no rows for it, and the planner handles its remaining rows.

## How to use tab

Plain lines for people, in this order:

1. This Week shows what is due in the next 14 days and anything overdue. Start there.
2. Rows marked Proposed are new slots from the agents. Read the title and Notes, then set Planned to approve or Cancelled to drop.
3. Agents draft Planned rows and set Draft ready. Click the Draft link to read the post.
4. To change a Status, use the link at the top of This Week. It opens the Calendar showing only this week's posts.
5. Set Approved when a draft is ready to post, and Posted once it is live.
6. To drop a post, set its Status to Cancelled. Do not delete the row.
7. Add post ideas on the Ideas tab. Set Declined on an idea instead of deleting it.
8. Add trade shows, launches and other dates on the Milestones tab. To cancel a milestone, set Confirmed to Cancelled. Do not delete the row.
9. Only change Status and Notes on the Calendar. Agents and formulas fill every other column.
