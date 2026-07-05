---
name: triage-github-issues-backlog
description: Prepare inputs and run the GitHub Issues Triage skill to export issues/labels/templates and generate proposed labels/comments plus an apply script.
---

# Triage the GitHub issues backlog for a repository.

## What you should do

1. Ask for (or confirm) the repository coordinates in `OWNER/REPO` format.
2. Ensure the user intends to use `gh` CLI and is authenticated (`gh auth status`).
3. Use the `github-issues-triage` skill to:
   - Export all open issues to a JSON file (handle pagination)
   - Export all labels
   - Export issue templates
   - Generate a markdown report with proposed labels/comments
   - Generate a runnable `gh`-based `apply.sh` script

## Inputs

- Repository: `OWNER/REPO`
- Output directory (suggestion): `./triage-issues`

## Output

- `triage-issues/issues.json`
- `triage-issues/labels.json`
- `triage-issues/templates/`
- `triage-issues/proposals.json`
- `triage-issues/report.md`
- `triage-issues/apply.sh`
