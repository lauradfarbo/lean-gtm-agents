# Lean GTM Agents

AI agents that run go-to-market for founder-led teams with no marketing hire. Built, not just planned.

## Who this is for

Early-stage founders and scaleups with two to ten people, a warm audience that needs to stay warm, and nobody whose job is marketing. The founders already know what to say. What they lack is the time to plan it, write it, check it and keep it consistent every week.

These agents take on the recurring work. A person still approves everything that leaves the building.

## Design principles

1. **Draft, never publish.** Agents draft, check and flag. A person approves and posts. No agent sends, posts or submits anything.
2. **Start with the highest recurring time cost.** Build the agent that gives back the most hours a week first, not the most interesting one.
3. **Use the tools the team already pays for.** Google Workspace or Microsoft 365, the CRM already in place, and the assistant the founders already use.
4. **One source of truth per job.** The content calendar is a sheet. The brand voice is one guide. Agents read from them and write proposals back, never around them.
5. **Client material stays out of this repo.** Skills here are generic. Each client's voice guide, calendar and reference files live in that client's own workspace.
6. **Document every agent.** Assumptions, inputs, outputs, access and test status are written down before the agent touches live systems. See [docs/agent-standards.md](docs/agent-standards.md).

## Work streams

A typical small-team GTM operation breaks into these streams. Each becomes one or more skills.

| Stream | What the agent does | Status |
| --- | --- | --- |
| Brand voice | Builds the voice guide every drafting agent writes against | Built: [`brand-voice-guide`](skills/brand-voice-guide/) |
| Content calendar | Converts an approved plan into a rolling 13-week calendar sheet and proposes new rows | Built: [`calendar-builder`](skills/calendar-builder/) |
| Content execution | Drafts posts and blogs against the calendar and the voice guide | Planned |
| Repurposing | Turns long-form assets into posts, scripts and newsletter sections | Planned |
| Video support | Drafts scripts and edit notes for talking-head video | Planned |
| Social listening | Finds relevant conversations and drafts comment suggestions for a person to post | Planned |
| CRM hygiene | Enriches and de-duplicates a warm contact list | Planned |
| Newsletter | Drafts a periodic newsletter to warm contacts | Planned, depends on CRM hygiene |
| LLM visibility | Audits site and blog structure so content surfaces in AI answers | Planned |

Automated LinkedIn prospecting is deliberately excluded. Automating connection requests puts the founder's account at risk.

## Repository layout

```
lean-gtm-agents/
  README.md
  docs/
    agent-standards.md        How every agent is documented, tested and approved
  skills/
    brand-voice-guide/
      SKILL.md                Method for building a social voice guide
      templates/              Blank voice guide to fill in
      examples/               Worked example for a fictional company
    calendar-builder/
      SKILL.md                Builds and extends a 13-week content calendar sheet
      references/             Sheet schema
      scripts/                Offline .xlsx builder
      examples/               Sample rows for testing
```

## Using a skill

Each folder under `skills/` is a self-contained skill: a `SKILL.md` with a name and description, plus any references, templates and scripts it needs. Load the folder into Claude (Cowork, Claude Code or a plugin) and point it at the client's own reference files. Nothing in a skill should need editing to work for a new client. If it does, that is a bug in the skill.

## Status

Private, phase 0. Skills are tested on sample data and test files before they run against a live workspace.
