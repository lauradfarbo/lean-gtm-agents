# Agent standards

Every skill and agent in this repo meets these standards before it runs against a client's live workspace.

## 1. Document the agent

Each `SKILL.md` and agent file states:

- **Purpose:** the job, in one sentence.
- **Assumptions:** what must already be true (a valid `workspace.json`, an approved plan, a voice guide).
- **Inputs:** every source it reads, by its `sources.*` key in the config.
- **Outputs:** every file, cell or row it writes, and the Status it sets.
- **Access:** the connectors it needs and the narrowest scope that works. Read-only wherever writing is not required. Subagents get Read, Bash and Glob on a local bundle and no connectors.
- **Hard rules:** what it must never do.

The client keeps an agent register (a sheet) with each agent's purpose, inputs, outputs, assumptions, access and test results.

## 2. Keep a person in the loop

- Agents draft, propose and flag. They never publish, post, send email or submit forms.
- Anything an agent adds to a shared calendar or tracker is `Proposed` until a person approves it. Agents set only `Proposed` (new rows) and `Draft ready` (a checked draft). People set Planned, Approved, Posted and Cancelled.
- Agents never edit or delete rows a person approved, and never write formula columns or summary tabs.
- A person drops a post by setting `Cancelled`, never by deleting the row. Agents skip Cancelled rows everywhere and leave them out of every brief, summary and notification.
- Swaps are proposed in Notes with a fallback draft. A person makes the swap.

## 3. One writer, guarded writes

- Only the main session writes. Subagents work on local copies and return JSON.
- Every calendar write passes three checks: the column lock (`calendar_writes.py plan`), the Row ID and Status guard on a fresh read just before writing (`calendar_writes.py guard`), and a read-back (`calendar_writes.py verify`). Ideas and Milestones writes pass `tab_guard.py`. A refused write is reported, never retried around.
- Append-only cells (Notes, Sources) are re-appended to the current value, so a person's edit during a run is kept. Write-once cells (Original draft) are never overwritten.

## 4. Claims and proof

- Drafts state only claims from approved facts sheet rows. Anything else is left out or flagged for the approver.
- Customer and partner posts use only signed-off proof log items. Organization names and quotes are used exactly as logged. Agents never invent a customer, partner, quote, figure or result.
- Every draft is checked by a separate compliance checker that never sees the drafter's reasoning. One redraft, then the draft is flagged and Status stays as it was.

## 5. Test before going live

1. Run `/setup-workspace check`: the config must pass `check_workspace.py`.
2. Run on TEST copies (prefix `TEST - `) or in shadow mode.
3. Compare the output with the source, field by field, and report every mismatch rather than fixing it silently.
4. Record the result (date, mode, pass or fail, notes) in the agent register.
5. Switch to the live files only once the mode in use has a passing test with the current config. Any config change needs a fresh TEST run.

## 6. Writing standards for agent output

Defaults. The client's rules file and `writing.*` in the config override them.

- Professional tone, short sentences, no filler.
- No em dashes.
- Metric units.
- Dates in prose as `DD MMM YY` with a leading zero and an uppercase month (03 NOV 26).
- One spelling variety per client, set in the config.
- Every statistic carries its source.

This repo itself is written in US English.

## 7. Keep client material out of the repo

- Skills are generic. Client names, products, people, competitors, colors, document IDs and reference files live in the client's workspace and `workspace.json`, never here.
- Worked examples and test fixtures use fictional companies.
- Before every commit, search the repo for client names, product names, people, document IDs and brand color codes. The `.gitignore` excludes `clients/`, `workspace.json` and `weekly/` run folders at the repo root.
