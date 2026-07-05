# Pull Requests Triage Report for `{{REPO}}`

Generated: {{TIMESTAMP}}

## Summary

- **Total PRs reviewed:** {{TOTAL_PRS}}
- **PRs with proposed labels:** {{PRS_WITH_LABELS}}
- **PRs with proposed comments:** {{PRS_WITH_COMMENTS}}
- **PRs following template:** {{PRS_FOLLOWING_TEMPLATE}}

## Proposals

| PR | Title | Proposed Labels | Proposed Comment | Reasons |
|---:|-------|-----------------|------------------|---------|
{{#PROPOSALS}}
| [{{NUMBER}}]({{URL}}) | {{TITLE}} | {{LABELS}} | {{COMMENT}} | {{REASONS}} |
{{/PROPOSALS}}

## Template Adherence Analysis

{{TEMPLATE_ANALYSIS}}

## Notes

- This report is auto-generated. Review proposals before applying them.
- Run `bash ./apply.sh` to apply proposed labels/comments via `gh`.
- Edit `proposals.json` to refine proposals before applying.
