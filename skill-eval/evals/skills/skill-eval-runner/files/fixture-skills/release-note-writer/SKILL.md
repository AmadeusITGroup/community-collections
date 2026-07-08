---
name: release-note-writer
description: "Turn a set of merged pull requests into a clean, grouped release-notes section. Triggers: user says 'write release notes', 'summarize this release', 'changelog for these PRs'."
user-invocable: true
metadata:
  author: Fixture Author
  version: "1.0.0"
---

# Release Note Writer

A small fixture skill used only as test material for skill-eval-runner evals. It is intentionally simple.

## When To Use This Skill

- User wants release notes or a changelog section built from a list of merged PRs
- User pastes PR titles/labels and asks for a grouped summary

## When NOT To Use This Skill

- There are no merged changes to summarize (tell the user there is nothing to release)
- User wants to actually cut/tag the release (this skill only writes the notes)

## Workflow

1. Read the merged PRs (from the prompt or a provided file).
2. Group them by change type: **Features**, **Fixes**, **Docs**, **Internal**.
3. Write one bullet per PR under its group, newest first, referencing the PR number.
4. Omit empty groups. If there are no user-facing changes, say so instead of inventing bullets.

## Output Format

A markdown section titled `## <version>` with one `### <group>` subsection per non-empty group.
