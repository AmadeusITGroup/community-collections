# GitHub Pull Requests Triage - Technical Reference

## Overview

This skill uses the `gh` CLI to export GitHub pull requests, labels, and PR templates, then generates triage proposals with labels and comments.

## Prerequisites

- **gh CLI**: Install from https://cli.github.com/
- **Authentication**: Run `gh auth login` before using this skill
- **Python 3.8+**: Required to run the triage script

## Script Usage

```bash
python3 scripts/triage_prs.py --repo OWNER/REPO --out ./output-dir
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--repo` | Yes | Repository in `OWNER/REPO` format |
| `--out` | Yes | Output directory for generated files |

## Output Files

| File | Description |
|------|-------------|
| `pulls.json` | All open pull requests |
| `labels.json` | All repository labels |
| `templates/` | Downloaded PR templates |
| `proposals.json` | Proposed labels/comments per PR |
| `report.md` | Human-readable triage report |
| `apply.sh` | Executable script to apply proposals |

## Label Matching Logic

The script automatically detects existing labels that match common triage patterns:

| Pattern | Example matches |
|---------|-----------------|
| `needs.*info` | "needs-info", "needs more info" |
| `triage` | "triage", "needs-triage" |
| `incomplete` | "incomplete" |

## Template Adherence Detection

The script extracts markdown headings from PR templates and checks if each PR body contains those headings. Missing headings trigger a "needs-info" label proposal and a comment asking the author to update the PR description.

## gh CLI Commands Used

```bash
# List PRs with pagination
gh api repos/OWNER/REPO/pulls -f state=open -f per_page=100 --paginate --slurp

# List labels
gh api repos/OWNER/REPO/labels -f per_page=100 --paginate --slurp

# Get PR template contents
gh api repos/OWNER/REPO/contents/.github/PULL_REQUEST_TEMPLATE.md -H "Accept: application/vnd.github.raw"

# Apply label (generated in apply.sh)
gh pr edit -R OWNER/REPO 123 --add-label "needs-triage"

# Add comment (generated in apply.sh)
gh pr comment -R OWNER/REPO 123 --body "..."
```

## Error Handling

- Script exits with error if `gh auth status` fails
- API errors are reported with the failing endpoint
- Missing templates are silently skipped (not all repos have them)
