# GitHub Issues Triage - Technical Reference

## Overview

This skill uses the `gh` CLI to export GitHub issues, labels, and issue templates, then generates triage proposals with labels and comments.

## Prerequisites

- **gh CLI**: Install from https://cli.github.com/
- **Authentication**: Run `gh auth login` before using this skill
- **Python 3.8+**: Required to run the triage script

## Script Usage

```bash
python3 scripts/triage_issues.py --repo OWNER/REPO --out ./output-dir
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--repo` | Yes | Repository in `OWNER/REPO` format |
| `--out` | Yes | Output directory for generated files |

## Output Files

| File | Description |
|------|-------------|
| `issues.json` | All open issues (PRs filtered out) |
| `labels.json` | All repository labels |
| `templates/` | Downloaded issue templates |
| `proposals.json` | Proposed labels/comments per issue |
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

The script extracts markdown headings from issue templates and checks if each issue body contains those headings. Missing headings trigger a "needs-info" label proposal and a comment asking the author to update the issue.

## gh CLI Commands Used

```bash
# List issues with pagination
gh api repos/OWNER/REPO/issues -f state=open -f per_page=100 --paginate --slurp

# List labels
gh api repos/OWNER/REPO/labels -f per_page=100 --paginate --slurp

# Get issue template contents
gh api repos/OWNER/REPO/contents/.github/ISSUE_TEMPLATE -H "Accept: application/vnd.github.raw"

# Apply label (generated in apply.sh)
gh issue edit -R OWNER/REPO 123 --add-label "needs-triage"

# Add comment (generated in apply.sh)
gh issue comment -R OWNER/REPO 123 --body "..."
```

## Error Handling

- Script exits with error if `gh auth status` fails
- API errors are reported with the failing endpoint
- Missing templates are silently skipped (not all repos have them)
