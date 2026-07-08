---
name: skill-eval-generator
description: "Generate evaluation test cases for any skill by browsing its SKILL.md and references. Produces evals.json with [auto]-prefixed expectations. Triggers: user says 'generate evals', 'create evals for skill', 'scaffold evals'; or after creating/updating a skill that needs test coverage. Use this skill whenever a skill exists but has no evals, or when evals need updating after skill changes."
argument-hint: "Provide a skill name to generate evals for"
disable-model-invocation: false
user-invocable: true
license: SEE LICENSE IN LICENSE
metadata:
  author: Cyril Colombel
  version: "1.1.0"
---

# Skill Eval Generator

## When To Use This Skill

- User wants to generate evaluation test cases for a skill
- A skill was just created or updated and needs eval coverage
- User asks to scaffold, create, or update evals for a specific skill
- Another skill (e.g., a generator) invokes `/skill-eval-generator` to create evals for its output

## When NOT To Use This Skill

- User wants to run existing evals (use `/skill-eval-runner`)
- User wants to manually write evals (just edit `evals/skills/{skill_name}/evals.json` directly)
- The skill doesn't exist yet (generate the skill first)

---

## Workflow Overview

Execute **4 phases in order**:

```
BROWSE → DESIGN → GENERATE → REPORT
```

| Phase | Actor | Output |
|-------|-------|--------|
| 1. Browse | You | Understanding of skill's testable surface area |
| 2. Design | You | List of eval scenarios with rationale + fixture candidates |
| 3. Generate | You | Fixtures created under `files/` + `evals/skills/{skill_name}/evals.json` written to disk |
| 4. Report | You | Summary to user with next steps |

---

## PHASE 1: BROWSE

> **Goal**: Read and understand the target skill's structure, capabilities, and testable surface area.

1. **Accept skill name** from user. Accept optional additional context (structured data, domain notes, scenario descriptions).
2. **Read `skills/{skill_name}/SKILL.md`** — understand what the skill does, how it works, when it triggers.
3. **Scan references** — read the skill's `## References` table. For each reference file, read at least the headings and structure. Read in full any reference that contains testable content (failure modes, routing tables, decision trees).
4. **Identify testable surface area** — look for these patterns in the skill:

| Pattern Found | Eval Opportunity |
|--------------|------------------|
| **Symptom routing table** | One eval per row: does it identify the right cause for each symptom? |
| **Child skill references** (`@child-expert`) | Routing eval: does it dispatch to the right child? |
| **Key baselines / thresholds** | Does it reference correct threshold values? |
| **"When NOT to use" section** | Negative eval: does it correctly decline irrelevant prompts? |
| **Description trigger phrases** | Triggering eval: does it activate for these phrases? |
| **Output format requirements** | Format eval: does output match the required structure? |
| **Decision branches / workflows** | Path eval: does it follow the right branch for a given input? |
| **Reference loading conditions** | Does it load the right reference at the right time? |

5. **If additional context was provided** (domain data, failure scenarios, incident descriptions), parse it as extra material for designing richer expectations. This context enriches the evals but is not required — the skill itself is the primary source.

### GATE 1: Browse Complete

- [ ] SKILL.md read and understood
- [ ] Key references scanned
- [ ] Testable surface area identified (at least 3 patterns)
- [ ] Additional context parsed (if provided)

---

## PHASE 2: DESIGN

> **Goal**: Design eval scenarios that test the skill's key behaviors.

For each testable pattern found in Phase 1, design one or more eval scenarios:

### Per-pattern eval design

**Symptom/scenario evals** (one per routing table row or failure scenario):
- Prompt: a realistic user message describing the symptom
- Expected output: what the skill should conclude (root cause, confidence, actions)
- Expectations: specific claims the response must make

**Overview eval** (one per skill):
- Prompt: a broad question about the skill's domain ("help me understand X issues in Y")
- Expected output: interactive guidance covering main scenarios
- Expectations: covers the top failure modes, provides actionable guidance

**Triggering evals** (from "When NOT to use" and description triggers):
- Positive: prompts that should activate the skill
- Negative: prompts that are close but shouldn't (adjacent domain, wrong system)

**Routing evals** (from child skill references):
- Prompt: symptom that should route to a specific child
- Expectations: response references or dispatches to the correct child

### Design principles

- **Specificity over breadth** — 6 specific evals that test distinct behaviors beat 12 vague ones
- **Expectations test understanding, not keywords** — "Response identifies X as root cause" is better than "Response mentions X"
- **Include at least one negative case** — something the skill should NOT do
- **Difficulty gradient** — include at least one easy case (clear symptom match) and one hard case (ambiguous or multi-cause)

### Recognize fixture needs

Many evals need an **input fixture** — a file (or file tree) the skill operates on. A fixture is what makes a data-driven eval reproducible; without one the eval either can't run or grades hollowly against no real input. As you design each eval, decide whether it needs a fixture and which **kind** it is.

This taxonomy names the common kinds. It is illustrative, not exhaustive: pick the closest kind, and if an eval needs a fixture that fits none of these, record it as a generic **"input file"** candidate — every fixture need must be recognized.

| Fixture kind | Recognize when the eval/skill… | Example |
|---|---|---|
| Observability data | references metrics, logs, query/monitor output | mock metrics JSON with a `results` array |
| Repo / code tree | inspects a repository, codebase, files, or structure | 2–3-package monorepo sample |
| Existing config / eval / data file | operates on a file that already exists (merge, edit, migrate) | a prior mixed-provenance `evals.json` |
| API / payload | consumes an API response or structured request | captured JSON request/response |
| Document / text corpus | summarizes, extracts from, or classifies documents | a sample document/snippet |

For each eval, note **whether it needs a fixture and which kind**. This list of *fixture candidates* feeds PHASE 3's **Create fixtures** step, where the fixtures are created.

### GATE 2: Design Complete

- [ ] At least 3 eval scenarios designed
- [ ] Mix of eval types (symptom, overview, triggering/routing where applicable)
- [ ] At least one negative or edge case
- [ ] Expectations are specific and verifiable
- [ ] Each eval assessed for a fixture need; every fixture candidate recorded with its kind (or a generic "input file")

---

## PHASE 3: GENERATE

> **Goal**: Create the input fixtures the evals need, then write evals.json to disk referencing them, respecting incremental merge rules.

### Eval directory resolution

Evals live in one of two layouts: the canonical `evals/skills/{skill_name}/` (preferred) or the colocated fallback `skills/{skill_name}/evals/` (used by some in-package skills). Resolve the target:

- **FULL mode** (no existing `evals.json` in either layout) → write to the canonical `evals/skills/{skill_name}/`.
- **INCREMENTAL mode** (an existing `evals.json` is found) → write back to whichever layout already holds it, so you never create a second copy that would make the runner warn about an ambiguous source. Canonical wins if both already exist.

### Check existing evals

1. Check if `evals.json` already exists in the resolved eval directory
   - If no → **FULL mode**: generate all evals fresh
   - If yes → **INCREMENTAL mode**: merge with existing entries

### Create fixtures (interactive)

Create the fixtures the evals need **before** writing `evals.json` (the next step), so each eval's `files` list can point at fixtures that already exist. Proposing a *relevant* fixture depends on the eval design, which is why this runs after PHASE 2 and before the write.

Fixtures live under `evals/skills/{skill_name}/files/`. Create that directory if it doesn't exist.

Handle the fixture candidates from PHASE 2 **one at a time**. For each:

1. **Existing-fixture check.** If a fixture already exists at the intended path, **skip creation** — leave it untouched (it may be human-refined real data) and reuse its path. Only missing fixtures proceed to the steps below. This mirrors the "never overwrite non-`[auto]`" rule for expectations.
2. **Propose 2–3 realistic scenarios**, each a one-line description grounded in the eval's purpose. Label them A/B/C.
   - *e.g. a monorepo-sampling eval → "A) 2-package JS monorepo (npm workspaces); B) Python namespace-package monorepo; C) mixed JS+Py monorepo."*
3. **Offer "Other → you describe"** so the human can supply the real scenario in their own words, and allow **skip**.
4. **Create the fixture from the chosen scenario** under `evals/skills/{skill_name}/files/…`, with content coherent to that choice. Because the content flows from a human-authorized pick (or their "Other" text), it is grounded in a real, chosen scenario rather than invented domain data.
5. **Keep fixtures minimal** — the smallest structure that exercises the eval (e.g. 2 packages, not 10). Do not over-produce.
6. **Record the resolved path** so the `evals.json` write below names the fixture just created or reused in that eval's `files` list.

A human may choose "Other" or **skip** any candidate. Skipping leaves that eval fixtureless — allowed, but flagged by GATE 3 so nothing is silently dropped.

### Write evals.json

Write to the skill's eval directory using the schema from [the runner's schemas.md](../skill-eval-runner/references/schemas.md):

```json
{
  "schema_version": "1.0.0",
  "skill_name": "{skill_name}",
  "skill_version": "{from skill's metadata.version, or '1.0.0'}",
  "description": "{what this eval set covers}",
  "evals": [...]
}
```

### Per-eval entry

Each eval entry:

```json
{
  "id": 1,
  "name": "descriptive-kebab-name",
  "prompt": "[auto] {realistic scenario prompt}",
  "expected_output": "{what a correct response looks like}",
  "expectations": [
    "[auto] {specific verifiable claim}",
    "[auto] {another verifiable claim}"
  ],
  "files": ["files/{fixture created or reused in the Create fixtures step}"]
}
```

Omit `files` (or use `[]`) for an eval with no fixture. When the **Create fixtures** step created or reused a fixture for this eval, list its path here, relative to the eval directory.

### Name generation

1. Take the core scenario description
2. Lowercase, remove punctuation
3. Extract first 5 significant words (skip stop words: a, an, the, is, are, was, were, in, on, for, with, to, of, and, or, but)
4. Join with hyphens
5. Deduplicate: if name exists, append `-2`, `-3`, etc.

### `[auto]` convention

All generated content is prefixed with `[auto]` to distinguish machine-generated from human-refined:

**Prefixed:** `prompt`, each entry in `expectations[]`

**Not prefixed:** `name`, `id`, `expected_output`, `skill_name`, `skill_version`, `description`

### Incremental merge rules

When updating existing `evals.json`:

- **Never overwrite** expectations or prompts that do NOT start with `[auto]` — these are human-refined
- **Replace** expectations and prompts that start with `[auto]` with new generated versions
- **Preserve** eval entries whose `name` does not match any generated name (manually added evals)
- **Add** new eval entries for scenarios not covered by existing evals (match by `name`)
- **Assign IDs** sequentially. For new entries in incremental mode, start from `max(existing IDs) + 1` to avoid collisions with manually added entries

### GATE 3: Generation Complete

- [ ] `evals/skills/{skill_name}/evals.json` written and valid JSON
- [ ] All auto-generated content has `[auto]` prefix
- [ ] Existing human-refined expectations preserved (incremental mode)
- [ ] All eval entries have unique IDs and names
- [ ] `files/` directory exists
- [ ] Every fixture candidate from PHASE 2 was resolved: a fixture was created, an existing one reused, or the human explicitly skipped it — none silently dropped
- [ ] Each eval's `files` list points at a fixture that exists on disk

---

## PHASE 4: REPORT

> **Goal**: Present results and guide user toward next steps.

Report to user:

```
Generated: evals/skills/{skill_name}/evals.json
  {N} eval(s) ({N_new} new, {N_updated} updated, {N_preserved} preserved)
  {N_auto} [auto] expectations (ready for human refinement)

Fixtures:
  Created:  {for each fixture created: - eval {id} ({name}): files/{path} — {kind}}
  Reused:   {for each existing fixture reused: - eval {id} ({name}): files/{path}}
  Skipped:  {for each fixture candidate the human skipped: - eval {id} ({name}): {kind} — no fixture; this eval has no input to grade against}

Next steps:
  1. Review [auto] prompts — replace with realistic scenario descriptions
  2. Review [auto] expectations — add business logic checks, remove weak ones
  3. Refine or replace created fixtures with real data where needed;
     supply fixtures for any skipped candidates above
  4. Run: /skill-eval-runner {skill_name}
```

---

## Common Mistakes to Avoid

| Mistake | Consequence | Correct Approach |
|---------|-------------|------------------|
| Generating evals without reading the skill first | Expectations don't match what the skill actually does | Always complete PHASE 1 before designing evals |
| Only testing the happy path | Misses regressions on edge cases | Include at least one negative and one ambiguous case |
| Expectations that test keywords, not understanding | False positives — any response mentioning the word passes | Write expectations that test conclusions and reasoning |
| Overwriting human-refined expectations | Destroys the most valuable eval content | Check `[auto]` prefix; never touch non-auto entries |
| Generating too many similar evals | Wastes execution time, doesn't add coverage | 6 diverse evals > 12 similar ones |
| Not reading references | Misses detailed testable content in failure-modes.md etc. | Scan all reference files during PHASE 1 |
| Fabricating fixture content without a human-authorized scenario | Fake domain data makes an eval pass hollowly | Always propose scenarios and create the fixture from the human's pick (or their "Other") |
| Overwriting an existing fixture | Destroys human-refined real data | Skip creation when a fixture already exists; reuse its path |

---

## Reference Documentation

| Reference | When to Read |
|-----------|-------------|
| [skill-eval-runner's references/schemas.md](../skill-eval-runner/references/schemas.md) | Authoritative field names for evals.json and all eval framework JSON files |
