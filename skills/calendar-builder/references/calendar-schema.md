# Content calendar schema

## Calendar tab columns (fixed order)

| # | Column | Filled by | Rule |
| --- | --- | --- | --- |
| A | Row ID | Calendar builder | `W{week:02d}-{seq:02d}`, sequence within the week in date order. Never reused or renumbered. |
| B | Week | Approver or builder | Plan week number (integer) |
| C | Date | Approver or builder | Real date, displayed as `ddd d mmm yy` |
| D | AM/PM | Approver or builder | `AM`, `PM` or blank |
| E | Content type | Approver or builder | Verbatim from the plan |
| F | Pillar | Builder, approver confirms | From the mapping below |
| G | Channel | Approver or builder | Verbatim from the plan |
| H | Title / angle | Approver or builder | The brief drafters write to |
| I | Spec | Approver or builder | Format, word count and destination |
| J | Source | Approver or agent | Source section or reference file |
| K | Proof item | Proof intake | Link to the proof log row (proof rows only) |
| L | Status | Agents and approver | Dropdown, values below |
| M | Draft link | Drafting agents | Link to the draft |
| N | Flags | Planner | Risks and gaps |
| O | Owner | Approver | Who reviews and posts |
| P | Published link | Approver | Live post URL |
| Q | Final text | Approver | Text as published, for later learning |

## Status values

| Value | Set by | Meaning |
| --- | --- | --- |
| Proposed | Calendar builder | New row awaiting approval. Drafters ignore it. |
| Planned | Approver | Approved slot, ready to draft |
| Drafted | Drafting agent | Draft linked, awaiting review |
| In review | Approver | Being edited |
| Approved | Approver | Ready to post |
| Published | Approver | Live; Published link and Final text filled |
| Swapped | Agent (as proposal) or approver | Slot replaced; see Flags |

## Pillar mapping (by content type)

Adjust the keywords to the client's plan. Every content type must map to exactly one pillar; the build fails on an unmapped type rather than guessing.

| Content type contains | Pillar |
| --- | --- |
| Partner Win, Customer Proof | Partner & Customer Proof |
| Press Release | PR & Press |
| Blog, Video, Gratitude, Year-in-review | Product & Brand Education |
| Guide, Newsletter, Event | Lead Generation |
| Poll | Engagement |
| POV | Thought Leadership |

## Milestones tab columns

Milestone, Type (Trade show, Launch, Webinar, Funding, Partner, Product), Start date, End date, Confirmed (Yes, No), Notes, Rows proposed (Yes or blank).

## Formatting

Colours below are neutral defaults. Replace them with the client's palette in the client workspace, not in this repo.

- Header row: dark fill `#1F2933`, white bold text, frozen. Columns A to E frozen.
- Filter on the header row.
- Status colours: Proposed amber tint, Planned white, Drafted light blue `#E3EEF7`, In review light amber, Approved dark green `#1E6B52` with white text, Published grey, Swapped light red.
- Alternate light banding by week so weeks read as blocks.
- Wrap Title / angle, Spec, Flags and Final text.
