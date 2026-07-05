# Issues Triage Report for `{{REPO}}`

Generated: {{TIMESTAMP}}

## Summary

- **Total issues reviewed:** {{TOTAL_ISSUES}}
- **Issues with proposed labels:** {{ISSUES_WITH_LABELS}}
- **Issues with proposed comments:** {{ISSUES_WITH_COMMENTS}}
- **Issues following template:** {{ISSUES_FOLLOWING_TEMPLATE}}

## Proposals

| Issue | Title | Proposed Labels | Proposed Comment | Reasons |
|------:|-------|-----------------|------------------|---------|
{{#PROPOSALS}}
| [{{NUMBER}}]({{URL}}) | {{TITLE}} | {{LABELS}} | {{COMMENT}} | {{REASONS}} |
{{/PROPOSALS}}

## Template Adherence Analysis

{{TEMPLATE_ANALYSIS}}

## Notes

- This report is auto-generated. Review proposals before applying them.
- Run `bash ./apply.sh` to apply proposed labels/comments via `gh`.
- Edit `proposals.json` to refine proposals before applying.
