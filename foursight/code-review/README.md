# FourSight Code Review

Use this collection when you need to review pull requests with specialized analysis across multiple dimensions — QA quality, technical debt, functional completeness, and architectural consistency.

## Why use it

This collection helps you:
- review pull requests with parallel multi-perspective analysis
- audit test quality and coverage before merge
- detect code duplication and technical debt patterns
- validate functional completeness against PR description
- verify architectural consistency and pattern reuse
- consolidate independent findings into a single prioritized report

## Contents

| Item | Type | Purpose |
|------|------|---------|
| `foursight-code-review` | Skill | Orchestrate parallel PR review by four specialized subagents — QA, Technical Debt, Functional, and Architecture |
| `foursight-code-review` | Agent | Main orchestration agent that coordinates the four specialized review agents |
| `code-review-qa` | Agent | QA engineer persona — audits test quality, coverage gaps, and edge cases |
| `code-review-tech-debt` | Agent | Technical debt reviewer — detects duplication, conventions, and maintainability issues |
| `code-review-functional` | Agent | Functional analyst — validates feature completeness and correctness |
| `code-review-architecture` | Agent | Architect persona — ensures consistency and pattern reuse |

## Prerequisites

- Git access to the repository you're reviewing
- GitHub CLI (`gh`) installed and authenticated for remote repositories
- Access to the pull request URL or branch name

## How to use it

In GitHub Copilot Chat or other compatible environments, run:

```text
/foursight-code-review
```

Provide the pull request you want to review, such as:
- a pull request URL (e.g., `https://github.com/OWNER/REPO/pull/123`)
- a PR number for the current repository (e.g., `123`)
- a branch name for review

## Expected output

You will receive:
- a concise, prioritized report consolidating all four perspectives
- independent findings from each subagent grouped by theme
- severity-ranked recommendations and actionable next steps
- concrete file and line references where relevant
