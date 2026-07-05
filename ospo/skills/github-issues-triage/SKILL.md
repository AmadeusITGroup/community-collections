---
name: github-issues-triage
description: Triage a repository's open issue backlog by proposing priorities, labels, and comments. Detects already-triaged issues, identifies potential duplicates, and generates a gh-based apply script.
---

# GitHub Issues Triage

## Purpose

Use this skill to triage the backlog of **open** GitHub issues for a given repository. The script will:

- Export all open issues (with pagination), available labels, and issue templates
- **Propose priority** (critical/high/medium/low) based on content analysis
- Propose labels to apply to each issue
- Propose a gentle comment when an issue does not adhere to the issue templates
- **Skip already-triaged issues** (those with substantive labels)
- **Detect potential duplicates** based on title/content similarity
- Produce:
  - A markdown report with proposed labels/priorities/duplicates
  - A runnable script (using `gh`) to apply the labels and comments

## Requirements

- `gh` CLI installed and authenticated (`gh auth login`)
- Repository coordinates in `OWNER/REPO` format
- Python 3.8+

## Workflow

### Step 1: Export Repository Data

Run the triage script to export issues, labels, and templates:

```bash
python3 scripts/triage_issues.py --repo OWNER/REPO --out ./triage-output
```

See [scripts/triage_issues.py](scripts/triage_issues.py) for the export script.

**Outputs:**

| File | Description |
|------|-------------|
| `issues.json` | All open issues (PRs filtered out) |
| `labels.json` | All repository labels |
| `templates/` | Downloaded issue templates |
| `proposals.json` | Proposed labels/comments per issue |
| `report.md` | Human-readable triage report |
| `apply.sh` | Executable script to apply proposals |

### Step 2: Review and Refine Proposals

1. Review `labels.json` to understand the project's labeling taxonomy
2. Review templates under `templates/` to determine adherence criteria
3. Review each issue in `issues.json` and refine `proposals.json`

**Guidelines:**

- Prefer existing labels; do not invent new ones unless explicitly asked
- Be conservative: if uncertain, leave `proposed_labels` empty and note why
- If an issue does not follow templates, propose a respectful comment

### Step 3: Apply Labels and Comments

After reviewing `report.md` and `proposals.json`:

```bash
bash ./triage-output/apply.sh
```

## Key Features

### Priority Detection

The script analyzes issue title, body, and labels to propose a priority:

| Priority | Keywords detected |
|----------|-------------------|
| 🔴 Critical | security, vulnerability, CVE, production down, blocking, urgent |
| 🟠 High | regression, crash, bug, error, broken, important |
| 🟡 Medium | enhancement, feature request, improvement |
| 🟢 Low | typo, documentation, cosmetic, minor |

### Already-Triaged Detection

Issues are skipped if they have **substantive labels** (not just triage-related labels like "needs-triage" or "needs-info"). This prevents re-triaging issues that have already been processed.

### Duplicate Detection

The script compares issue titles and bodies using text similarity (threshold: 70%). Potential duplicates are flagged in the report for manual review.

## Example Output

### Sample `proposals.json`

```json
[
  {
    "number": 42,
    "url": "https://github.com/octocat/hello-world/issues/42",
    "title": "App crashes on startup",
    "proposed_labels": ["needs-triage", "high"],
    "proposed_priority": "high",
    "proposed_comment": "Thanks for opening this issue...",
    "reasons": ["Issue has no labels", "Detected priority: high"],
    "already_triaged": false,
    "potential_duplicates": [
      {"number": 38, "title": "Application crash at launch", "similarity": 0.75, "match_type": "title"}
    ]
  }
]
```

### Sample `report.md`

The report includes:
- **Summary**: Total issues, needs triage count, already triaged count
- **Priority breakdown**: Count per priority level
- **Issues needing triage**: Table sorted by priority
- **Potential duplicates**: Table showing similar issues
- **Already triaged**: Collapsed list of skipped issues

### Sample `apply.sh`

Only includes issues that need triage (skips already-triaged):

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO='octocat/hello-world'

gh issue edit -R "$REPO" 42 --add-label 'needs-triage' --add-label 'high'
gh issue comment -R "$REPO" 42 --body 'Thanks for opening this issue...'
```

## References

- [Technical Reference](references/REFERENCE.md) - Detailed script documentation
- [Examples](references/EXAMPLES.md) - Additional usage examples
- [Report Template](assets/report.template.md) - Template for report output
- [Proposals Schema](assets/proposals.schema.json) - JSON schema for proposals
