# Locations used by proof intake

Locations come from `workspace.json` (`sources.<key>`), live or test. The person running the skill says which set to use; if they do not say, ask. Use `test` until the agent register records a passing test for this skill.

| Key | Reads | Writes | Notes |
| --- | --- | --- | --- |
| `sources.rules` | Yes | No | Wins over every other file |
| `sources.voice_guide` | Yes | No | Tone, mechanics, any partner or customer example, avoid list |
| `sources.facts_sheet` | Yes | No | Only rows whose Status is in `facts.approved_values` |
| `sources.assets` | Yes | No | Look for a logo or photo of the organization |
| `sources.calendar` | Yes | Yes | Only the cells in SKILL.md, "Writes" |
| `sources.proof_log` | Yes | Yes | Column J only. `sheet_gid` builds the Proof item link |
| `sources.drafts_folder` | Yes | Yes | One doc per plan week, one tab per post |

On the live calendar, run `check_proof_post.py` with `--live`. When the weekly orchestrator calls proof intake, the subagent reads only its local bundle and writes nothing.
