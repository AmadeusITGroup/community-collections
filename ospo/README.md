# Amadeus OSPO collection

Use this collection when you need to evaluate whether a repository is ready for InnerSource or Open Source adoption, or when you want to triage a GitHub backlog faster.

## Why use it

This collection helps you:
- assess repository readiness for InnerSource and Open Source practices
- review documentation, governance, security, contribution flow, and maturity
- triage issues and pull requests with proposed labels, priorities, and comments
- generate actionable reports and apply scripts without starting from scratch

## Contents

| Item | Type | Purpose |
|------|------|---------|
| `assess-innersource-readiness` | Prompt | Run a structured InnerSource readiness assessment for a repository |
| `assess-opensource-readiness` | Prompt | Run a structured Open Source readiness assessment for a repository |
| `triage-issues` | Prompt | Export and triage open GitHub issues with proposed labels and comments |
| `triage-pull-requests` | Prompt | Export and triage open GitHub pull requests with proposed labels and comments |
| `innersource-readiness` | Skill | Evaluate repository maturity, documentation, and cross-team contribution readiness |
| `open-source-readiness` | Skill | Evaluate open source readiness, community health, security, governance, and licensing |
| `github-issues-triage` | Skill | Generate issue triage reports and a `gh`-based apply script |
| `github-prs-triage` | Skill | Generate pull request triage reports and a `gh`-based apply script |

## Prerequisites

- For issue or pull request triage, install and authenticate the GitHub CLI with `gh auth login`
- For the triage workflows, Python 3.8+ is required
- Provide a repository to assess in one of these forms: the current workspace, `OWNER/REPO`, or a local repository path

## How to use it

In GitHub Copilot Chat, run one of the prompts below:

```text
/assess-innersource-readiness
/assess-opensource-readiness
/triage-issues
/triage-pull-requests
```

Provide the repository you want to evaluate, such as:
- the current workspace repository
- `OWNER/REPO`
- a local repository path

For issue or PR triage, make sure the GitHub CLI is installed and authenticated with `gh auth login`.

## Expected output

Depending on the prompt, you will receive a structured assessment or a triage package with:
- a concise report
- prioritized recommendations
- proposed labels, comments, and duplicate notes
- an apply script when relevant