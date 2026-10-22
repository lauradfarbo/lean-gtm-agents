# Changelog

## 1.0.0 (21 OCT 26)

First release as an installable plugin.

Added:

- `.claude-plugin/plugin.json`, `commands/`, `agents/`.
- `workspace-setup` skill and `/setup-workspace` command: opening interview that points every agent at the client's sources (Google Drive, Notion, GitHub, SharePoint, local folder or URL), and `check_workspace.py`.
- `workspace.json` config (`docs/workspace-config.md`, `templates/workspace.example.json`): all client rules, locations and cadence in one file.
- `weekly-orchestrator` skill and `/weekly-run` command, with the `planner`, `drafter`, `proof-drafter` and `compliance-checker` subagents.
- `short-form-drafter` and `proof-intake` skills.
- Column lock, Row ID guard and read-back verify on every calendar write; tab guard on Ideas and Milestones.
- Shadow mode, missed-run recovery, same-day rerun stop, evergreen swaps with fallback drafts, visual no-repeat window.
- `templates/chapter-map.md`.
- Tests with fictional fixtures (`tests/`).

Changed:

- `calendar-builder`: 22-column schema with This Week, Ideas, Milestones and How to use tabs; Cancelled status; ideas and milestone runs; offline builder and verify script updated.
- `docs/agent-standards.md`: one-writer rule, guarded writes, Cancelled handling, claims and proof, config checks.
- US spelling throughout the repo.

## 0.1.0

`brand-voice-guide` and the first `calendar-builder`.
