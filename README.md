# Lean GTM Agents

AI agents that run go-to-market for founder-led teams with no marketing hire. Built, tested and packaged as an installable Claude plugin.

## Who this is for

Early-stage founders and scaleups with two to ten people, a warm audience that needs to stay warm, and nobody whose job is marketing. The founders already know what to say. What they lack is the time to plan it, write it, check it and keep it consistent every week.

These agents take on the recurring work. A person still approves everything that leaves the building.

## Design principles

1. **Draft, never publish.** Agents draft, check and flag. A person approves and posts. No agent sends, posts or submits anything.
2. **Start with the highest recurring time cost.** Build the agent that gives back the most hours a week first, not the most interesting one.
3. **Use the tools the team already has.** The client's material stays where it lives: Google Drive, Notion, GitHub, SharePoint or a local folder. One setup step points the agents at it.
4. **One source of truth per job.** The content calendar is a sheet. The brand voice is one guide. Approved claims are one facts sheet. Agents read from them and write proposals back, never around them.
5. **One writer.** Subagents work on local copies and return results. Only the main session writes, and every write passes a column lock, a fresh-read guard and a read-back check.
6. **Client material stays out of this repo.** Skills are generic. Each client's config, voice guide, calendar and reference files live in that client's own workspace.
7. **Document and test every agent.** Assumptions, inputs, outputs, access and test status are written down, and every agent passes on TEST copies before it touches live files. See [docs/agent-standards.md](docs/agent-standards.md).

## Quick start

1. Install the plugin. In Claude Code: `/plugin marketplace add lauradfarbo/lean-gtm-agents`, then `/plugin install lean-gtm-agents@lean-gtm-agents`. In Cowork: upload a zip of this repo as a plugin.
2. Connect the connectors for where your material lives (Google Drive, Docs and Sheets are the tested path).
3. Run `/setup-workspace`. It asks where your calendar, rules, voice guide, facts sheet, proof log, long-form source, assets and folders are, checks each one, and saves `workspace.json` in your own workspace.
4. No voice guide yet? Ask for the `brand-voice-guide` skill. No calendar yet? Ask the `calendar-builder` skill to convert your approved content plan.
5. Run `/weekly-run test --config <location>` and review the brief. Switch to `live` only after a passing TEST run is recorded in your agent register.

## What is in the plugin

| Component | Type | What it does |
| --- | --- | --- |
| `workspace-setup` (`/setup-workspace`) | Skill and command | Opening interview that points every agent at the client's sources and writes `workspace.json` |
| `brand-voice-guide` | Skill | Builds the voice guide every drafting agent writes against |
| `calendar-builder` | Skill | Converts an approved plan into a rolling 13-week calendar sheet; adds monthly, milestone and idea rows as proposals |
| `weekly-orchestrator` (`/weekly-run`) | Skill and command | The weekly run: select rows, plan check, draft, check, redraft once, write, verify, brief |
| `planner` | Subagent | Checks the next four weeks against the plan rules and returns notes and risks |
| `short-form-drafter`, `drafter` | Skill and subagent | Drafts one LinkedIn post per calendar row from approved facts |
| `proof-intake`, `proof-drafter` | Skill and subagent | Fills partner and customer slots only from signed-off proof; flags and proposes swaps otherwise |
| `compliance-checker` | Subagent | Independent check of every draft; never sees the drafter's reasoning |

## How a weekly run works

```
/weekly-run
  1  load workspace.json, validate it, stop on errors
  2  same-day and missed-run check
  3  calendar builder: monthly, milestone and ideas runs (proposals only)
  4  snapshot every source to local files
  5  select rows due in the next two plan weeks
  6  planner and proof match                     (subagent, read-only)
  7  one drafter per row, swaps and fallbacks    (subagents, read-only)
  8  one compliance checker per draft            (subagents, read-only)
  9  one redraft for any failure, then flag
 10  write draft tabs, then calendar cells through the column lock and Row ID guard
 11  read back and verify
 12  one-page brief for the approver
```

## Where client material can live

| Material | Read from | Written by agents |
| --- | --- | --- |
| Rules, plan rules, voice guide | Google Docs, Notion, GitHub, SharePoint or OneDrive, local file, URL | No |
| Facts sheet, long-form source, assets | Any of the above, or a sheet or database | No |
| Calendar, proof log | Google Sheets (tested); Notion database or Excel Online through the adapter rules | Only allowed cells |
| Drafts, briefs | Google Docs (tested); Notion pages or Word Online through the adapter rules | One doc per week, one brief per run |

Details: [docs/workspace-config.md](docs/workspace-config.md).

## Work streams

| Stream | What the agent does | Status |
| --- | --- | --- |
| Setup | Points every agent at the client's sources | Built: `workspace-setup` |
| Brand voice | Builds the voice guide | Built: `brand-voice-guide` |
| Content calendar | Rolling 13-week calendar, proposals only | Built: `calendar-builder` |
| Content execution | Weekly plan check, drafts, proof posts, compliance check, brief | Built: `weekly-orchestrator` and agents |
| Repurposing | Turns long-form assets into posts, scripts and newsletter sections | Planned |
| Social listening | Finds conversations and drafts comment suggestions for a person to post | Planned |
| CRM hygiene | Enriches and de-duplicates a warm contact list | Planned |
| Newsletter | Drafts a periodic newsletter to warm contacts | Planned, depends on CRM hygiene |
| LLM visibility | Audits site and blog structure so content surfaces in AI answers | Planned |

Automated LinkedIn prospecting is deliberately excluded. Automating connection requests puts the founder's account at risk.

## Repository layout

```
lean-gtm-agents/
  .claude-plugin/plugin.json
  commands/            /setup-workspace, /weekly-run
  agents/              planner, drafter, proof-drafter, compliance-checker
  skills/
    workspace-setup/   setup interview and check_workspace.py
    brand-voice-guide/ method, template, worked example
    calendar-builder/  schema, tab guard, verify and offline builder scripts
    short-form-drafter/post types, draft doc format, check_draft.py
    proof-intake/      proof rules, matching and proof checks
    weekly-orchestrator/ run steps, brief format, shadow mode, bundle scripts
  templates/           workspace.example.json, chapter-map.md
  docs/                agent standards, workspace config reference
  tests/               fictional fixtures and test scripts
```

## Tests

```
bash tests/test_workspace.sh
bash tests/test_calendar.sh
bash tests/test_drafting.sh
bash tests/test_orchestrator.sh
```

All fixtures use Brightwell Analytics, a fictional company. Python 3 standard library only, except the offline calendar builder (openpyxl).

## Status

Version 1.0.0. The mechanics were proven on one client's live weekly run on Google Workspace before being generalized here. Other platforms follow the adapter rules and need their own passing TEST run.
