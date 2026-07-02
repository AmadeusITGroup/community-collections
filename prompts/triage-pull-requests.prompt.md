---
name: triage-github-pull-requests-backlog
description: Prepare inputs and run the GitHub Pull Requests Triage skill to export PRs/labels/templates and generate proposed labels/comments plus an apply script.
---

# Triage the GitHub pull requests backlog for a repository.

## What you should do

1. Ask for (or confirm) the repository coordinates in `OWNER/REPO` format.
2. Ensure the user intends to use `gh` CLI and is authenticated (`gh auth status`).
3. Use the `github-prs-triage` skill to:
   - Export all open pull requests to a JSON file (handle pagination)
   - Export all labels
   - Export PR templates
   - Generate a markdown report with proposed labels/comments
   - Generate a runnable `gh`-based `apply.sh` script

## Inputs

- Repository: `OWNER/REPO`
- Output directory (suggestion): `./triage-prs`

## Output

- `triage-prs/pulls.json`
- `triage-prs/labels.json`
- `triage-prs/templates/`
- `triage-prs/proposals.json`
- `triage-prs/report.md`
- `triage-prs/apply.sh`
