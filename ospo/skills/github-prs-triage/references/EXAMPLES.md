# GitHub Pull Requests Triage - Examples

## Example 1: Basic Triage Run

### Input

```bash
python3 scripts/triage_prs.py --repo octocat/hello-world --out ./triage-output
```

### Output Directory Structure

```
triage-output/
├── pulls.json
├── labels.json
├── templates/
│   └── PULL_REQUEST_TEMPLATE.md
├── proposals.json
├── report.md
└── apply.sh
```

## Example 2: Sample `proposals.json`

```json
[
  {
    "number": 101,
    "url": "https://github.com/octocat/hello-world/pull/101",
    "title": "Add dark mode support",
    "proposed_labels": ["needs-triage", "needs-info"],
    "proposed_comment": "Thanks for the pull request. To help us review it faster, could you please update the PR description to follow the repository's PR template and include the missing sections (for example: Description, Testing, Screenshots)? Thanks!",
    "reasons": [
      "Pull request has no labels",
      "Pull request appears not to follow the pull request template"
    ]
  },
  {
    "number": 102,
    "url": "https://github.com/octocat/hello-world/pull/102",
    "title": "Fix typo in README",
    "proposed_labels": [],
    "proposed_comment": "",
    "reasons": []
  }
]
```

## Example 3: Sample `report.md`

```markdown
# Pull requests triage report for `octocat/hello-world`

Generated: 2026-01-14 08:00 UTC

| PR | Title | Proposed labels | Proposed comment | Reasons |
|---:|---|---|---|---|
| [101](https://github.com/octocat/hello-world/pull/101) | Add dark mode support | needs-triage, needs-info | Thanks for the pull request... | Pull request has no labels; Pull request appears not to follow the pull request template |
| [102](https://github.com/octocat/hello-world/pull/102) | Fix typo in README |  |  |  |

## Notes

- This report is auto-generated. Review proposals before applying them.
- Run `bash ./apply.sh` to apply proposed labels/comments via `gh`.
```

## Example 4: Sample `apply.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO='octocat/hello-world'

gh pr edit -R "$REPO" 101 --add-label 'needs-triage' --add-label 'needs-info'
gh pr comment -R "$REPO" 101 --body 'Thanks for the pull request. To help us review it faster, could you please update the PR description to follow the repository'\''s PR template and include the missing sections (for example: Description, Testing, Screenshots)? Thanks!'
```

## Example 5: Reviewing and Refining Proposals

After running the script, you can manually edit `proposals.json` to:

1. **Remove unwanted labels**: Delete entries from `proposed_labels` array
2. **Edit comments**: Modify `proposed_comment` text
3. **Skip PRs**: Set both `proposed_labels` to `[]` and `proposed_comment` to `""`

Then regenerate `apply.sh` or manually run `gh` commands.

## Example 6: Dry Run (Review Only)

To review without applying:

```bash
# Generate proposals
python3 scripts/triage_prs.py --repo octocat/hello-world --out ./triage-output

# Review the report
cat ./triage-output/report.md

# Review individual proposals
cat ./triage-output/proposals.json | jq '.[] | select(.proposed_labels | length > 0)'
```
