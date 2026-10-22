# Subagents: bundles and prompts

Each subagent gets a folder with only what it needs, and a short prompt. Subagents write nothing to any platform. They return JSON; the main session writes.

Run folder: `weekly/<run date YYYY-MM-DD>/` in the session workspace. Shared files, saved once per run in `shared/` (read rules in SKILL.md, "Saving source data for the scripts"):

| File | From |
| --- | --- |
| `workspace.json` | The config, as loaded in step 1. Copied into every bundle |
| `calendar.json` | `sources.calendar` A1:V (also kept as `before.json`) |
| `proof_log.json` | `sources.proof_log` A1:J |
| `facts.json` | `sources.facts_sheet` (`tab`, `range`) |
| `facts_approved.json` | Rows of facts.json whose Status is in `facts.approved_values`, as `[{"id","claim","comments"}]` (`comments` from `facts.comments_col`). `make_bundles.py` writes it |
| `rules.md`, `plan_rules.md`, `voice.md` | `sources.rules`, `sources.plan_rules`, `sources.voice_guide`, each checked for its `expect_phrase`. Google Docs: Docs `read_doc`, saved as returned, then `python3 scripts/doc_text.py <saved>.json <name>.md --expect "<expect_phrase>"`. Never Drive `read_file_content` for a Doc. Other platforms: the text as returned. Stop the run if a check fails |
| `assets.txt` | `sources.assets` listing: one line per file, `<subfolder>/<file name>` |
| `milestones.json` | Milestones tab of the calendar, A1:G (the planner lists rows of cancelled milestones) |
| `long_form.md` | Text of `sources.long_form`, once per run, so drafters need no connector |
| `chapter-map.md` | The client's chapter map (`sources.long_form.chapter_map`; template in `templates/chapter-map.md`) |

Build every bundle with `python3 scripts/make_bundles.py <run dir> <plugin root> plan|draft|proof|fallback|redraft|check ...` (see its header). It copies shared files, `workspace.json` included, and never retypes them.

Every subagent is a plugin agent with Read, Bash and Glob only, so none can reach a connector: `planner`, `compliance-checker`, `drafter` and `proof-drafter`. If a plugin agent type is not listed (for example before the plugin is reinstalled), stop and tell the person. On TEST only, a general-purpose subagent with the agent file's body pasted at the top of its prompt may stand in, and the brief says so.

In every prompt, `<spelling>` is `writing.spelling` from `workspace.json` (US or UK).

## Planner

Bundle `plan/`: workspace.json, calendar.json, facts.json, proof_log.json, milestones.json, plan_rules.md, rules.md, `scripts/plan_check.py`.
Agent: `planner`.
Prompt: `Plan bundle: <abs path>/plan. Run date: <YYYY-MM-DD>. Follow your instructions and return only the JSON. Use <spelling> spelling as set in workspace.json.`

## Short-form drafter (one per `draft` row)

Bundle `draft/<Row ID>/`: workspace.json, `row.json` (the row as an object with the calendar headers as keys, plus `_row`), rules.md, voice.md, facts_approved.json, assets.txt, long_form.md, chapter-map.md, `recent.txt` (Row ID, Content type and Sources of rows of the same content type, and of long-form source rows, from `visuals.no_repeat_weeks` weeks before to 14 days after the row), `visuals_recent.txt` (Row ID, date and Visual of every other row within `visuals.no_repeat_weeks` either side), and copies of the short-form-drafter skill's `SKILL.md` (as `drafter_skill.md`), its `references/` files and `scripts/check_draft.py`. Teasers add `blog.txt` (the published blog text, read by the main session from the link in `blog_link`, or from a `sources.other` repo).
Agent: `drafter`.
Prompt:

```
You are the short-form drafter, called by the weekly orchestrator. Draft one post for row <Row ID>.
Bundle: <abs path>/draft/<Row ID>. Read workspace.json, then rules.md and voice.md; rules.md wins. Follow steps 1 to 8 of drafter_skill.md, using post-types.md and chapter-map.md from the bundle. Use <spelling> spelling as set in workspace.json.
Read one chapter of long_form.md only. Write nothing outside the bundle.
State only claims from facts_approved.json. Run check_draft.py with --config workspace.json --facts facts_approved.json on your draft and fix every fail.
Return only this JSON:
{"row_id","type":"post|founder|poll|video","post","first_comment","alternate_hook","poll_question","poll_options","visual","visual_alternatives":[],"image_prompt","image_alt_prompt","image_alt_subject","fact_ids":[],"sources":"<documents with version and long-form chapter>","flags":["one sentence each, or empty"],"word_count","script":"video rows only: shot list and script","blocked":"empty, or the exact item a person must provide if the row cannot be drafted"}
```

When `visuals.ai_image_tool` is null, `image_prompt`, `image_alt_prompt` and `image_alt_subject` stay empty and the visual is a `Use:` file or `Needed: <photo or graphic>`.

## Fallback drafter (one per swap with `fallback: true`)

Bundle `fallback/<Row ID>/`: built with `make_bundles.py ... fallback --rows <ids> --swaps swaps_final.json`. As for the drafter, but row.json carries the swap (a Content type from `swaps.types`; the angle as Title / angle) and `fallback.json` holds the original row and the long-form chapter.
Agent: `drafter`.
Prompt: the drafter prompt, with "Draft one post for row <Row ID>" replaced by:

```
Draft one fallback post for row <Row ID>: the proposed swap in fallback.json, not the original row. Use the content type and angle in row.json and read long_form.md chapter <N> only. The post must stand on its own: never mention the original topic, the swap or why it was made.
```

Save the return as `returns/<Row ID>-fb.json`. The checker and any redraft work as for any draft (check bundle `--suffix -fb --content-type "<swap type>"`; redraft `--from fallback/<Row ID>`).

## Proof drafter (one per `draft` slot in the match plan)

Bundle `proof/<Row ID>/`: as for the drafter, but with proof intake's `SKILL.md` (as `proof_skill.md`), `proof_item.json` (the proof log row as an object), `references/proof-rules.md` and `scripts/check_proof_post.py`.
Agent: `proof-drafter`.
Prompt: as for the drafter, but start with "You are proof intake, called by the weekly orchestrator. Follow step 3 of proof_skill.md and proof-rules.md. Use only proof_item.json for the organization, what happened and the quote." Add `"proof_row": <N>` to the returned JSON. Run `check_proof_post.py draft.json proof_item.json --config workspace.json --facts facts_approved.json` (add `--live` whenever the run reads the live calendar, shadow runs included).

## Compliance checker (one per draft)

Bundle `check/<Row ID>/` (or `check/<Row ID>-2/` for a redraft): `draft.json` built from the drafter's JSON with only row_id, content_type, type, post, first_comment, alternate_hook, visual, visual_alternatives, image_prompt, image_alt_prompt, image_alt_subject, poll_question, poll_options, fact_ids. Never include flags, sources or any note from the drafter. Add workspace.json, facts.json, rules.md, voice.md, assets.txt, visuals_recent.txt, `proof_item.json` for proof posts, and copies of `scripts/check_compliance.py` and `scripts/check_draft.py`.
Agent: `compliance-checker`.
Prompt: `Check bundle: <abs path>/check/<Row ID>. Follow your instructions and return only the JSON. Use <spelling> spelling as set in workspace.json.`

## Redraft (one per failed draft, once)

Bundle `redraft/<Row ID>-2/`: `make_bundles.py ... redraft --from draft/<Row ID> --previous <failed draft JSON> --fixes <checker fixes JSON>` (use `--from proof/<Row ID>` for a proof post, `--from fallback/<Row ID>` for a fallback). It copies the original bundle, workspace.json included, and adds `previous.json` and `fixes.json`.
Agent: a fresh `drafter` or `proof-drafter`.
Prompt: the drafter prompt plus: `A compliance check failed. Apply every fix in fixes.json to previous.json. Keep everything else unless a fix requires a change. Return the same JSON.`
