---
name: github-prs-triage
description: Triage a repository's open pull request backlog by proposing priorities, labels, and comments. Detects already-triaged PRs, identifies potential duplicates, and generates a gh-based apply script.
---

# GitHub Pull Requests Triage

## Purpose

Use this skill to triage the backlog of **open** GitHub pull requests for a given repository. The script will:

- Export all open pull requests (with pagination), available labels, and PR templates
- **Propose priority** (critical/high/medium/low) based on content analysis
- Propose labels to apply to each pull request
- Propose a gentle comment when a PR does not adhere to the PR template
- **Skip already-triaged PRs** (those with substantive labels)
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

Run the triage script to export PRs, labels, and templates:

```bash
python3 scripts/triage_prs.py --repo OWNER/REPO --out ./triage-output
```

See [scripts/triage_prs.py](scripts/triage_prs.py) for the export script.

**Outputs:**

| File | Description |
|------|-------------|
| `pulls.json` | All open pull requests |
| `labels.json` | All repository labels |
| `templates/` | Downloaded PR templates |
| `proposals.json` | Proposed labels/comments per PR |
| `report.md` | Human-readable triage report |
| `apply.sh` | Executable script to apply proposals |

### Step 2: Review and Refine Proposals

1. Review `labels.json` to understand the project's labeling taxonomy
2. Review templates under `templates/` to determine adherence criteria
3. Review each PR in `pulls.json` and refine `proposals.json`

**Guidelines:**

- Prefer existing labels; do not invent new ones unless explicitly asked
- Be conservative: if uncertain, leave `proposed_labels` empty and note why
- If a PR does not follow templates, propose a respectful comment

### Step 3: Apply Labels and Comments

After reviewing `report.md` and `proposals.json`:

```bash
bash ./triage-output/apply.sh
```

## Key Features

### Priority Detection

The script analyzes PR title, body, and labels to propose a priority:

| Priority | Keywords detected |
|----------|-------------------|
| 🔴 Critical | security, vulnerability, CVE, hotfix, production fix, blocking |
| 🟠 High | regression, bug fix, crash, error |
| 🟡 Medium | enhancement, feature, refactor, improvement |
| 🟢 Low | typo, documentation, chore, cleanup, style |

### Already-Triaged Detection

PRs are skipped if they have **substantive labels** (not just triage-related labels like "needs-triage" or "needs-info"). This prevents re-triaging PRs that have already been processed.

### Duplicate Detection

The script compares PR titles and bodies using text similarity (threshold: 70%). Potential duplicates are flagged in the report for manual review.

## Example Output

### Sample `proposals.json`

```json
[
  {
    "number": 101,
    "url": "https://github.com/octocat/hello-world/pull/101",
    "title": "Add dark mode support",
    "proposed_labels": ["needs-triage", "medium"],
    "proposed_priority": "medium",
    "proposed_comment": "Thanks for the pull request...",
    "reasons": ["Pull request has no labels", "Detected priority: medium"],
    "already_triaged": false,
    "potential_duplicates": []
  }
]
```

### Sample `report.md`

The report includes:
- **Summary**: Total PRs, needs triage count, already triaged count
- **Priority breakdown**: Count per priority level
- **PRs needing triage**: Table sorted by priority
- **Potential duplicates**: Table showing similar PRs
- **Already triaged**: Collapsed list of skipped PRs

### Sample `apply.sh`

Only includes PRs that need triage (skips already-triaged):

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO='octocat/hello-world'

gh pr edit -R "$REPO" 101 --add-label 'needs-triage' --add-label 'medium'
gh pr comment -R "$REPO" 101 --body 'Thanks for the pull request...'
```

## Output Format

Your final triage output should include:

- `report.md`:
  - A list of pull requests with proposed labels and proposed comments
  - Notes on template adherence problems and patterns
  - Any open questions or ambiguity
- `apply.sh`:
  - `gh pr edit` commands to apply labels
  - `gh pr comment` commands to add proposed comments

## References

- [Technical Reference](references/REFERENCE.md) - Detailed script documentation
- [Examples](references/EXAMPLES.md) - Additional usage examples
- [Report Template](assets/report.template.md) - Template for report output
- [Proposals Schema](assets/proposals.schema.json) - JSON schema for proposals
