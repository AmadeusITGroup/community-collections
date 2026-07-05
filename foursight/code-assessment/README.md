# FourSight Code Assessment

Use this collection when you need comprehensive codebase assessment with ruthlessly prioritized findings focused on high-impact improvements.

## Why use it

This collection helps you:
- assess overall code quality and health of a project or module
- identify the most impactful improvements (critical bugs, major debt, quick wins)
- audit test quality and coverage gaps across the codebase
- detect code duplication and convention violations project-wide
- validate functional correctness and identify missing edge cases
- evaluate architectural consistency and identify structural improvements
- onboard onto a new codebase by understanding its strengths and weaknesses
- get a roadmap you can act on *today* rather than an exhaustive (but overwhelming) catalog

## Assessment Philosophy

The assessment focuses on findings that matter most — those that meaningfully improve quality, reliability, or maintainability. Rather than overwhelming reports:
- **Critical and Major findings** receive full analysis, concrete recommendations, and file-level detail
- **Quick wins** (high impact, low effort) are highlighted for immediate action
- **Minor issues** are grouped by theme into a compact summary, so you understand what debt exists without wading through dozens of low-severity items

## Contents

| Item | Type | Purpose |
|------|------|---------|
| `foursight-code-assessment` | Skill | Orchestrate parallel codebase assessment by four specialized subagents — QA, Technical Debt, Functional, and Architecture |
| Shared agents | Agents | QA, Technical Debt, Functional, and Architecture evaluation specialists |

## Prerequisites

- Git repository with source code to assess
- Local access to the codebase (current working directory)

## How to use it

In GitHub Copilot Chat or other compatible environments, run:

```text
/foursight-code-assessment
```

Specify the scope you want to assess:
- **Full project**: the entire repository (default)
- **Module/directory**: a specific path (e.g., `src/services/`)
- **Technology/layer**: a specific layer (e.g., "all API controllers")

## Expected output

You will receive a comprehensive report with:
- **Executive summary** with health scores across four dimensions (Test Coverage, Code Quality, Functional Correctness, Architecture)
- **Quick wins** — low-effort, high-impact fixes to tackle first
- **Critical and Major findings** — detailed analysis with file references and recommendations
- **Improvement roadmap** — prioritized action plan (Quick Wins → Critical → High-Impact → Refinements)
- **Minor issues recap** — grouped themes with representative file locations
- **Positive highlights** — strengths to build on
