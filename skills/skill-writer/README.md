# Skill Writer

A style guide for writing agent instructions — the same way a coding style guide keeps a codebase readable, this keeps your skill library lean, reliable, and cheap to run.

- [`SKILL.md`](SKILL.md) — the principles reference for writing predictable, token-efficient skills
- [`GLOSSARY.md`](GLOSSARY.md) — the full vocabulary, via progressive disclosure

The skill is model-agnostic: it works with GitHub Copilot and any other agent.

## What a skill is

Think of a skill as a **standing instruction card** you hand to the agent before a task. This skill teaches you how to write those cards so the agent follows them reliably — and does not waste tokens reading things it does not need.

## The one big idea

> A skill should make the agent behave the same **way** every run, not produce the same output.

A code-review skill should always check security, performance, and style — in that order — every time. The findings differ per PR, but the *process* is the same. That is what you are designing for.

## Section by section

### Invocation (who fires the skill?)

Two options:

- **Agent fires it automatically** — you write a description like "Use when the user asks to review a PR." The agent reads that description on *every single turn*, even when it is not reviewing anything. That costs tokens (called *context load*).
- **You fire it manually by typing its name** — the agent never sees the description, zero token cost. But *you* have to remember the skill exists.

Practical rule: if the agent should detect when to use it on its own → model-invoked. If you will always know when you need it (like `/security-review`) → user-invoked, and save the tokens.

### Writing the description (for model-invoked skills)

The description is what the agent reads to decide "should I use this skill right now?" So it needs to be:

- Short — every word costs tokens on every turn
- Full of the exact words you would actually type (if you say "review this PR", the word "review" should be in the description)
- One trigger per distinct use case — do not say the same thing twice in different words

### Information hierarchy (what goes where in the skill file)

Three levels:

1. **Steps** — the ordered things the agent does. These go in the main `SKILL.md`.
2. **Rules/reference** — definitions, checklists, standards the agent looks up as needed. Also fine in `SKILL.md` if short.
3. **Detailed reference** — big tables, glossaries, long rule sets. Push these into a separate linked file (like `GLOSSARY.md`) so the main file stays readable.

### When to split a skill into two

Two reasons to split:

1. **The second half has a different trigger word** — e.g., "run tests" and "write tests" are different enough that two skills make sense.
2. **Seeing step 3 makes the agent rush step 2** — hiding the later step in a separate skill makes the agent do step 2 properly first.

### Leading words (the most powerful trick)

Instead of explaining a concept in 20 words, use one word the agent already understands.

- "look at everything carefully and do not skip files" → just say **thorough**
- "write a minimal first version that runs end-to-end" → just say **tracer bullet**

One word does the work of a paragraph. This saves tokens and makes behaviour more consistent.

### Pruning (keeping skills lean)

Four questions to ask of every line:

1. Is this still relevant to what the skill does today?
2. Does this appear anywhere else in the skill? (if yes, delete one copy)
3. Would the agent do this anyway without being told? (if yes, delete it — it is a no-op)
4. Can I move this to a linked file since only some runs need it?

## Why this matters for day-to-day engineering skills

| Problem | What this skill teaches you |
|---|---|
| Agent skips steps or finishes too early | Add a clear "done" condition to each step |
| Skill is slow / costs lots of tokens | Move reference to a linked file; cut no-ops |
| Agent fires the skill at the wrong time | Rewrite the description with your actual trigger words |
| Two skills do similar things | Check if one can call the other instead of duplicating |
| Skill worked 3 months ago but not now | Prune sediment — old rules that no longer apply |
