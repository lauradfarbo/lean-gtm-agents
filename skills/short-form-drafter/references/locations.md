# Locations used by the drafter

Locations come from `workspace.json` (`sources.<key>`), live or test. The person running the skill says which set to use; if they do not say, ask. Use `test` until the agent register records a passing test for this skill.

| Key | Reads | Writes | Notes |
| --- | --- | --- | --- |
| `sources.rules` | Yes | No | Wins over every other file. Check `expect_phrase` |
| `sources.voice_guide` | Yes | No | Tone, mechanics, examples, avoid list, pre-publish checklist |
| `sources.facts_sheet` | Yes | No | Only rows whose Status is in `facts.approved_values`. Column names from `facts.*` |
| `sources.long_form` | Yes | No | Read one chapter only, through the chapter map named in `sources.long_form.chapter_map` |
| `sources.assets` | Yes | No | Listing only (`assets.txt`), subfolders included |
| `sources.other` | When relevant | No | For example a website repo for the published blog text of a teaser |
| `sources.calendar` | Yes | Yes | Only the cells in SKILL.md, "Calendar writes" |
| `sources.proof_log` | Yes | No | Read only, for gratitude posts that may thank a signed-off organization |
| `sources.drafts_folder` | Yes | Yes | One doc per plan week, one tab per post |

When the weekly orchestrator calls the drafter, the subagent reads only its local bundle and writes nothing.
