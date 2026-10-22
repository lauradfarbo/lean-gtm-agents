---
name: workspace-setup
description: First-run setup for the lean GTM agents. Points the orchestrator and every agent at the client's own calendar, rules, voice guide, facts, proof log, assets and folders, wherever they live (Google Drive, Notion, GitHub, SharePoint, a local folder or a URL), and writes the workspace.json every skill reads. Use when asked to "set up the agents", "/setup-workspace", "connect our files", "point the agents at our docs", "change where the calendar lives", "check the workspace config", or when any skill finds no workspace.json.
---

# Workspace setup

Run this before anything else. It asks where the client's material lives, confirms each source can be read (and written, where agents write), and saves `workspace.json`. Every other skill and agent reads that file and nothing else to find the client's material. Setup never publishes, posts or sends anything, and it writes only the config, its check report and, on request, empty TEST copies.

## Modes

- **New** (default): no config yet. Interview, check, save.
- **Update**: change one or more sources or rules. Read the current config first and change only what the person names.
- **Check** (`/setup-workspace check`): read the config, run `scripts/check_workspace.py` and test every source. Change nothing.

## Hard rules

- Ask; never assume. If the person does not know where something lives, mark it missing and say which agent cannot run without it.
- Request the narrowest access that works: read-only for reference sources, write only on the calendar, proof log (one column), drafts folder and briefs folder.
- Never copy client material into the plugin or this repo. The config holds locations and rules, not content.
- Never enter credentials. If a connector needs sign-in, ask the person to connect it.
- Every write location gets a TEST copy before the first run. If none exists, offer to create one named `TEST - <original name>` (empty structure only, no client data copied without the person's yes).
- Writing standards for anything setup writes: `docs/agent-standards.md`.

## Step 1: Opening prompt

Start with this message, adapted to the person's words, then ask the questions in Step 2 a few at a time.

> Before the agents can plan, draft or check anything, they need to know where your material lives. I will ask where each item is kept: a Google Drive or SharePoint link, a Notion page or database, a GitHub repo and path, a folder on your computer, or a web address. If something does not exist yet, say so and I will note which agent waits for it. Nothing is published, posted or sent at any point.

## Step 2: Questions

Group them so the person answers 3 or 4 at a time. Use the question tool where the session has one.

1. **Company and approver.** Company name as used in posts, brand hashtag, the one person who approves rows and drafts (name and role), team members who may be named in posts, main market for public holidays, timezone.
2. **Channels in scope.** Start with one (usually LinkedIn).
3. **Reference sources** (read-only). For each: where it lives and its current version.
   - Rules file: brand, claim and legal rules. It wins over every other file.
   - Plan rules: cadence, playbook specs, holiday shifts, story arc, open dependencies.
   - Voice guide (build one with the `brand-voice-guide` skill if none exists).
   - Facts sheet: one row per approved claim, with an ID, the claim, Status and approver comments.
   - Long-form source: the guide, white paper or book drafts draw angles from, and its chapter list.
   - Assets folder: photos, videos and graphics posts may use.
   - Anything else the agents should read: a website repo for published blogs, a Notion wiki, a product sheet. Ask "Is there anything else you would want a new marketer to read first?"
4. **Working files** (agents write). The content calendar, the proof log, the drafts folder and the briefs folder. For each, the live location and the TEST copy. If there is no calendar yet, the `calendar-builder` skill creates one from an approved plan after setup.
5. **Writing rules a script can check.** Spelling variety, units, date style, word counts, required hashtags, competitor and brand names never to mention, the avoid list, any claim rules (wording that is never allowed, and the approved wording to use instead), and topics on hold. Offer to draft these from the rules file and voice guide, then confirm each list with the person.
6. **Cadence.** Week 1 Monday of the plan, posts per week, recurring slots (proof slot, blog pair, rotation slot), and dated dependencies. Offer to read these from the plan rules.
7. **Visuals.** Whether drafts may propose AI image prompts and with which tool, any product reference photo, and which post types need a real photo.
8. **Where to save the config.** A folder the person controls (Drive, Notion, private repo or a connected local folder). Not this repo.

## Step 3: Check each source

For each source, read it once with the right connector and record the result. Use the platform rules in `docs/workspace-config.md` ("Adapter rules").

| Kind | Check |
| --- | --- |
| doc | Read the full text. It must contain `expect_phrase` (ask the person for a phrase near the end). Record the character count |
| table | Read the header row. Compare it with the schema the agent expects (`calendar-schema.md`, `proof-rules.md`, the `facts` section). List missing or renamed columns |
| file | Read the first and last page or section. Build or confirm the chapter map (`templates/chapter-map.md`) |
| folder | List it, subfolders included. Record the file count |
| write targets | Confirm the TEST copy exists and the connector can write to it. Do not write to the live copy |

If a connector is missing, look for one and offer it to the person. If none exists, record the source as `manual` and say which step a person does by hand.

## Step 4: Save and validate

1. Write the config as JSON, keys in the order of `templates/workspace.example.json`.
2. Run `python3 scripts/check_workspace.py workspace.json`. Fix every error with the person. Warnings are listed in the summary.
3. Save the file to the location from question 8 and read it back.
4. Add a line to the agent register: date, "workspace-setup", mode, sources checked, result.

## Step 5: Scheduled run prompt (optional)

If the person wants a weekly run, write the prompt for them to schedule, for example:

```
Run /weekly-run test --config <config location>. Follow the weekly-orchestrator skill. Never publish, post or send anything.
```

Say that `test` changes to `live` only after the agent register records a passing TEST run, and that the person sets the schedule themselves.

## Output to the person

Up to eight lines: where the config is saved, each source with its check result (ok, missing, cut off, columns differ, no TEST copy), what each missing item blocks, and the next step (usually: build the calendar, or run `/weekly-run test`).
