# Locations used by the weekly run

Locations come from `workspace.json` (`sources.<key>`), live or test. This file names the keys, never IDs or URLs. Each source's `platform` says how to read it (`docs/workspace-config.md`, "Adapter rules"). The person running the skill, or the scheduled task prompt, says `test`, `live`, `shadow` or `test shadow`. If it is not stated, ask.

For each key, `live` is the client's working file and `test` is its TEST copy. A read-only source with `test: null` uses the `live` location in every mode.

## Read only (every mode)

| Key | Saved as | Used by |
| --- | --- | --- |
| `sources.rules` | `rules.md` | Everyone. Wins over every other file |
| `sources.plan_rules` | `plan_rules.md` | Planner, calendar builder |
| `sources.voice_guide` | `voice.md` | Drafters, checker |
| `sources.facts_sheet` (`tab`, `range`) | `facts.json`, `facts_approved.json` | Drafters (approved rows only), checker, planner |
| `sources.long_form` | `long_form.md` | Drafters read one chapter only |
| `sources.long_form.chapter_map` | `chapter-map.md` | Drafters, swap angles |
| `sources.assets` | `assets.txt` | Drafters, checker, `visuals.py`. List every subfolder once per run |
| `sources.other[]` | as the step needs | For example, published blog text for a teaser (`blog.txt`) |
| `sources.agent_register` | not saved | Confirms a passing TEST run before a `live` run |

## Read and write

| Key | `test` | `live` | `shadow` | `test shadow` |
| --- | --- | --- | --- | --- |
| `sources.calendar` (`tab`, `range` A1:V) | `test`: read, write | `live`: read, write | `live`: read only | `test`: read only |
| Ideas and Milestones tabs of the calendar | `test`: read, write (tab guard) | `live`: read, write (tab guard) | `live`: read only | `test`: read only |
| `sources.proof_log` (`tab`, `range` A1:J) | `test`: read, write column J | `live`: read, write column J | `live`: read only | `test`: read only |
| `sources.drafts_folder` | `test`: write | `live`: write | never written | never written |
| `sources.briefs_folder` | `test`: read titles, write | `live`: read titles, write | `live`: list only (verify) | `test`: list only (verify) |
| `sources.shadow.drafts_folder` | not used | not used | `live`: write | `test`: write |
| `sources.shadow.briefs_folder` | not used | not used | `live`: read titles, write | `test`: read titles, write |
| `sources.shadow.review_sheet` (`tab`) | not used | not used | `live`: append A to H | `test`: append A to H |

The orchestrator is the only writer to these locations during a run. Subagents get local copies and write nothing.

Never write to the calendar, proof log, drafts folder or briefs folder (live or TEST) in a shadow run. If a shadow key is missing from the config, a shadow run cannot start: say so and offer `/setup-workspace update`.
