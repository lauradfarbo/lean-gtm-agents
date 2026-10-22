# Workspace config (`workspace.json`)

Every skill, agent and script in this plugin reads one file, `workspace.json`, to learn where the client's material lives and which rules apply. Nothing client-specific is written into the plugin itself. The `workspace-setup` skill (`/setup-workspace`) builds this file by interview; you can also copy `templates/workspace.example.json` and fill it in by hand.

The file lives in the client's own workspace (a Drive folder, a Notion page, a private repo or a connected local folder), never in this repo. Each run is told where it is: `/weekly-run test --config <location>`, or the location saved in the scheduled task prompt that setup writes.

## Sections

### `company`

| Key | Meaning |
| --- | --- |
| `name` | Company name as it appears in posts |
| `hashtag` | The brand hashtag, if any |
| `approver.name`, `approver.role` | The one person who approves rows and drafts. Agents write "<approver> to approve" in Notes and the brief |
| `people` | Team names that may appear in posts. Names outside this list and the proof item raise a warning |
| `people_first_mention` | Optional. First-mention forms, for example `{"Priya": "Priya Nair, co-founder"}` |
| `timezone`, `holiday_market` | Run timezone, and the market whose public holidays shift posting dates (US, UK, NL and so on) |

### `run`

Run day, how far ahead to draft (`horizon_days`, 13 = the next two plan weeks), how many weeks the planner checks, how close a blocked row must be before a swap is proposed (`swap_days`), the fallback cap, and the default mode. The default is always `test` until the agent register records a passing test.

### `sources`

One entry per file the agents use. Every entry has:

| Key | Meaning |
| --- | --- |
| `kind` | `doc` (read as text), `table` (rows with a header), `file` (PDF or long-form), `folder` (listing), `repo` |
| `platform` | `google_drive`, `notion`, `github`, `sharepoint`, `local` (a connected folder) or `url` |
| `live`, `test` | The ID, URL, repo path or local path. `test` is the TEST copy; `null` means the same file is used in test runs (read-only sources only) |
| `title` | Human name with version, quoted in Sources and the brief |
| `expect_phrase` | Words near the end of a doc. A read that does not contain them is treated as cut off and the run stops |
| `tab`, `range` | Tables only |
| `sheet_gid` | Google Sheets tables only, optional: the tab's gid, used to build row links (for example the Proof item link) |

Required: `rules`, `voice_guide`, `facts_sheet`, `calendar`, `drafts_folder`, `briefs_folder`. Recommended: `plan_rules`, `proof_log`, `long_form`, `assets`, `agent_register`. Optional: `shadow`, `other` (any further reference: a website repo, a Notion wiki, a product sheet).

#### Where each source can live

| Source | Read from | Write to |
| --- | --- | --- |
| Rules, plan rules, voice guide | Google Docs, Notion page, GitHub file, SharePoint or OneDrive file, local Markdown, public URL | Never written |
| Facts sheet | Google Sheet, Notion database, Excel file, CSV in a repo | Never written |
| Long-form source and chapter map | PDF or doc anywhere a connector can read | Never written |
| Assets | Google Drive folder, SharePoint folder, local folder, repo folder | Never written |
| Calendar, proof log | Google Sheet (tested). Notion database or Excel Online (adapter, see below) | Agents write only the cells in `calendar-schema.md` |
| Drafts, briefs | Google Docs (tested). Notion pages or Word Online (adapter) | One doc per week, one brief per run |

The calendar, proof log, drafts and briefs path is built and tested on Google Workspace. The other platforms are supported through the adapter rules below and must pass the TEST run before going live.

#### Adapter rules (any platform)

Scripts never talk to a platform. They read local JSON in one shape, so any source can feed them:

- **Tables** are saved as `{"values": [["Header A", "Header B"], ["row 2 a", "row 2 b"]]}`, header row first, row 2 is the first data row. This is the Google Sheets `get_values` shape. For a Notion database, Excel file or CSV, convert to this shape with the columns in the schema order, and keep a `_source_row` key map (Row ID to page ID or row number) in the run folder so writes go back to the right record.
- **Docs** are saved as plain text or Markdown. For Google Docs use Docs `read_doc` and `doc_text.py` (Drive text export can cut long docs off). For Notion, GitHub, SharePoint and local files, save the text as returned. Always check `expect_phrase`.
- **Folders** are saved as `assets.txt`, one `<subfolder>/<file name>` per line.
- **Writes** always pass the same three checks whatever the platform: `calendar_writes.py plan` (column lock), `calendar_writes.py guard` on a fresh read just before writing (Row ID and Status unchanged), then `calendar_writes.py verify` on a read-back.

### `writing`

Machine-readable rules for `check_draft.py` and `check_compliance.py`. The client's rules doc still wins; this section is the part a script can test.

| Key | Meaning |
| --- | --- |
| `spelling` | `US` or `UK`. The scripts fail the other variety |
| `units` | `metric` or `imperial`. The scripts fail the other system |
| `date_format`, `no_em_dash`, `emoji` | Output conventions |
| `word_count` | `[min, max]` per draft type (`post`, `founder`, `poll`) |
| `opening_max_words` | The first sentence must be shorter than this |
| `hashtags` | `min`, `max`, `required` tags, and `conditional` tags (`if_regex` in the post means `tag` should be added: a warning) |
| `link_in_first_comment` | Links go in the first comment, never the post body |
| `competitors` | Company and brand names that must never appear. Lower case |
| `avoid_terms` | Voice guide avoid list. Lower case |
| `date_words_warn` | Words that suggest a launch, availability or delivery date. Warning only |
| `custom_rules` | Client claim rules: `id`, `level` (`fail` or `warn`), `regex` (case-insensitive), optional `unless_regex`, and the `message` the drafter sees, which should name the approved wording |
| `on_hold_topics` | Topics not to mention while a fact (`fact_id`) is not Approved |

### `facts`

Column names on the facts sheet and the Status values that count as approved. Agents state only claims from approved rows.

### `calendar`

Content type patterns: team-owned rows (never drafted), proof types and their title placeholders, teaser rows (need the published blog link), event live and recap rows (need real photos), and the Status list.

### `plan`

Cadence rules `plan_check.py` can test: the Monday of plan week 1, intentional deviations by Row ID, posts per week, the weekly proof slot, the blog pair, the rotation slot, types not to repeat in one week, and dated dependencies (a fact that must be Approved by a deadline). Leave a key out to skip that check. Anything a script cannot test stays in the plan rules doc for the planner agent to judge.

### `swaps`

The evergreen post types used when a slot cannot run, the long-form source chapters a swap may draw on, and chapters never used for a swap (for example one that gives launch dates).

### `visuals`

How many weeks either side a file or AI image subject may not repeat, the assets folder label, the AI image tool (or `null` for none), an optional product reference photo note, the content types that need a real photo, aspect ratios, and brand colors for abstract images.

### Optional keys

Leave any of these out to use the default.

| Key | Default | Meaning |
| --- | --- | --- |
| `calendar.tabs` | Calendar, Ideas, Milestones | Tab names, if the client renamed them |
| `calendar.pillar_map` | Table in `calendar-schema.md` | `[[regex, pillar], ...]`, checked in order |
| `calendar.what_to_post_map` | Table in `calendar-schema.md` | `[[regex, text], ...]`, checked in order |
| `calendar.content_type_aliases` | None | `{"<client type name>": "<generic type in post-types.md>"}` |
| `calendar.blog_id_regex` | `^(Blog \d+)` | Pulls the blog ID out of a content type, to pair a teaser with its blog |
| `calendar.formula_columns` | Action needed, Draft | Columns agents never write |
| `writing.spelling_allow` | None | Words exempt from the spelling check (brand names, quoted titles) |
| `writing.product_timing` | `{"level": "fail"}` | Launch, availability and delivery timing: `level` fail, warn or off, optional `regex` and `message` |
| `plan.dependencies[].row_regex` | Label or fact ID | Which rows a dependency holds, matched on Content type, Title / angle or Notes |
| `plan.pdf` | Default layout | How `verify_calendar.py` reads the plan PDF: `row_regex`, `stop_regex`, `content_type_field`, `title_field` |
| `visuals.product_regex` | None | Words that mean an image prompt shows the product, so it must start from `product_reference_photo` |

## Changing the config

Re-run `/setup-workspace` and choose "update", or edit the file and run `/setup-workspace check`. Either way, record the change and a fresh TEST run in the agent register before the next live run.
