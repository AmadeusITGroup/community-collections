# GitHub Issues Triage - Examples

## Example 1: Basic Triage Run

### Input

```bash
python3 scripts/triage_issues.py --repo octocat/hello-world --out ./triage-output
```

### Output Directory Structure

```
triage-output/
├── issues.json
├── labels.json
├── templates/
│   └── bug_report.md
├── proposals.json
├── report.md
└── apply.sh
```

## Example 2: Sample `proposals.json`

```json
[
  {
    "number": 42,
    "url": "https://github.com/octocat/hello-world/issues/42",
    "title": "App crashes on startup",
    "proposed_labels": ["needs-triage", "needs-info"],
    "proposed_comment": "Thanks for opening this issue. To help us triage it faster, could you please update the issue to follow the repository's issue template and include the missing sections (for example: Steps to Reproduce, Expected Behavior, Actual Behavior)? Thanks!",
    "reasons": [
      "Issue has no labels",
      "Issue appears not to follow the issue template"
    ]
  },
  {
    "number": 43,
    "url": "https://github.com/octocat/hello-world/issues/43",
    "title": "Feature request: dark mode",
    "proposed_labels": [],
    "proposed_comment": "",
    "reasons": []
  }
]
```

## Example 3: Sample `report.md`

```markdown
# Issues triage report for `octocat/hello-world`

Generated: 2026-01-14 08:00 UTC

| Issue | Title | Proposed labels | Proposed comment | Reasons |
|---:|---|---|---|---|
| [42](https://github.com/octocat/hello-world/issues/42) | App crashes on startup | needs-triage, needs-info | Thanks for opening this issue... | Issue has no labels; Issue appears not to follow the issue template |
| [43](https://github.com/octocat/hello-world/issues/43) | Feature request: dark mode |  |  |  |

## Notes

- This report is auto-generated. Review proposals before applying them.
- Run `bash ./apply.sh` to apply proposed labels/comments via `gh`.
```

## Example 4: Sample `apply.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO='octocat/hello-world'

gh issue edit -R "$REPO" 42 --add-label 'needs-triage' --add-label 'needs-info'
gh issue comment -R "$REPO" 42 --body 'Thanks for opening this issue. To help us triage it faster, could you please update the issue to follow the repository'\''s issue template and include the missing sections (for example: Steps to Reproduce, Expected Behavior, Actual Behavior)? Thanks!'
```

## Example 5: Reviewing and Refining Proposals

After running the script, you can manually edit `proposals.json` to:

1. **Remove unwanted labels**: Delete entries from `proposed_labels` array
2. **Edit comments**: Modify `proposed_comment` text
3. **Skip issues**: Set both `proposed_labels` to `[]` and `proposed_comment` to `""`

Then regenerate `apply.sh` or manually run `gh` commands.

## Example 6: Dry Run (Review Only)

To review without applying:

```bash
# Generate proposals
python3 scripts/triage_issues.py --repo octocat/hello-world --out ./triage-output

# Review the report
cat ./triage-output/report.md

# Review individual proposals
cat ./triage-output/proposals.json | jq '.[] | select(.proposed_labels | length > 0)'
```
