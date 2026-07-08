---
name: commit-message-writer
description: "Write a clear Conventional Commits message from a set of staged changes. Triggers: user says 'write a commit message', 'draft a commit', or pastes a diff and asks how to describe it. Use whenever changes are staged and need a well-formed commit subject and body."
argument-hint: "Describe or paste the staged changes"
user-invocable: true
metadata:
  author: Fixture Author
  version: "2.1.0"
---

# Commit Message Writer

Turn a set of staged changes into a well-formed [Conventional Commits](https://www.conventionalcommits.org)
message: a `type(scope): subject` line, an optional body, and any required footers.

## When To Use This Skill

- The user has staged changes and wants a commit message drafted
- The user pastes a diff and asks how to describe it
- The user wants an existing commit message rewritten to follow Conventional Commits

## When NOT To Use This Skill

- The user wants to actually run `git commit` or push — this skill only drafts text
- The user wants a full changelog or release notes across many commits (that is a release task)
- There are no code or content changes to describe (e.g. a pure question about git)

---

## Change-Type Routing

Pick the commit `type` from the dominant change in the diff:

| Change observed | Commit type | Notes |
|-----------------|-------------|-------|
| New user-facing capability | `feat` | Triggers a MINOR version bump |
| Corrects broken behavior | `fix` | Triggers a PATCH version bump |
| Docs only, no code change | `docs` | |
| Restructure without behavior change | `refactor` | |
| Formatting/whitespace only | `style` | |
| Adds or fixes tests only | `test` | |
| Build, deps, or tooling | `chore` | |

## Formatting Rules

- **Subject line:** imperative mood, no trailing period, **≤ 50 characters**.
- **Body:** required when the change touches **more than one concern** or needs a "why"; wrap body lines at **72 characters**.
- **Breaking change:** if a public interface changes incompatibly, append a `BREAKING CHANGE:` footer AND mark the type with `!` (e.g. `feat!:`).
- **Scope:** optional; use the affected module/package name in parentheses, e.g. `fix(parser):`.

---

## References

| Reference | When to Read |
|-----------|-------------|
| [references/examples.md](references/examples.md) | When you need worked before/after commit-message examples, including breaking-change footers |
