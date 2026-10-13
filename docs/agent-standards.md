# Agent standards

Every skill in this repo meets these standards before it runs against a client's live workspace.

## 1. Document the agent

Each `SKILL.md` states:

- **Purpose:** the job, in one sentence.
- **Assumptions:** what must already be true (an approved plan exists, a voice guide exists, the person has a Google account).
- **Inputs:** every file, sheet or connector it reads, and where it lives.
- **Outputs:** every file or row it writes, and its status when written.
- **Access:** the connectors it needs and the narrowest scope that works. Read-only wherever writing is not required.
- **Hard rules:** what it must never do.

## 2. Keep a person in the loop

- Agents draft, propose and flag. They never publish, post, send email or submit forms.
- Anything an agent adds to a shared calendar or tracker is marked `Proposed` until a person approves it.
- Agents never edit or delete rows or documents a person has approved.

## 3. Test before going live

1. Run on sample data or a copy prefixed `TEST -`.
2. Compare the output with the source, field by field, and report every mismatch rather than fixing it silently.
3. Record the result (date, mode, pass or fail, notes) in the client's agent register.
4. Only switch to the live file once the mode in use has a passing test.

## 4. Writing standards for agent output

These are defaults. A client's voice guide overrides them where it says so.

- Professional tone, short sentences, no filler.
- No em dashes.
- Metric units.
- Dates in prose as `DD MMM YY` with an uppercase month (13 OCT 26).
- One spelling variety per client, set in the client's voice guide.
- Every statistic carries its source.

## 5. Keep client material out of the repo

- Skills are generic. Client names, products, people, competitors, colours and reference files live in the client's workspace, never here.
- Worked examples use fictional companies.
- Before every commit, search the repo for client names, product names, people and brand colour codes. The `.gitignore` excludes a `clients/` folder for local working copies.
