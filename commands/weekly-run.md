---
description: Run the weekly content run (drafts, checks, calendar updates and the weekly brief). Never publishes.
argument-hint: "[test|live|shadow|test shadow] [rerun] [--as-of YYYY-MM-DD] [--config <location>]"
---

Run the weekly-orchestrator skill from this plugin now.

Arguments: $ARGUMENTS

- `--config <location>` is where `workspace.json` lives (a Drive file, Notion page, repo path or local path). If it is not given, ask the person. If no config exists, run the workspace-setup skill first, then start this run.
- `test` uses the `test` location of every write source in `workspace.json`: calendar, proof log, drafts folder and briefs folder. `live` uses the `live` locations. If neither is given, ask which.
- `live` runs only when the agent register records a passing TEST run with the current config. If it does not, say so and offer a `test` run.
- `shadow` reads the live calendar and proof log and writes drafts, the brief and review rows to `sources.shadow.*` only (weekly-orchestrator `references/shadow-mode.md`). Nothing is written to the calendar, proof log, drafts folder or briefs folder.
- `test shadow` runs shadow mode on the TEST calendar and proof log, writing to the TEST shadow locations.
- `rerun` allows a second run on a day that already has a brief. Without it, the run stops and says a brief for that date exists. A rerun's brief name adds ` (2)`.
- `--as-of YYYY-MM-DD` simulates the run date. Use it only with `test` or `test shadow`.

Follow the skill's steps in order and finish with its short output to the person and the brief link. Never publish, post or send anything. Spelling, units and dates follow `writing.*` in `workspace.json`.
