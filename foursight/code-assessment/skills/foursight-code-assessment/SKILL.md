---
name: foursight-code-assessment
description: 'Parallel codebase assessment with specialized subagents for QA, Technical Debt, Functional, and Architecture analysis. Use when analyzing a whole codebase for quality, performing code audits, assessing code health, identifying improvements, evaluating technical debt across a project, or when onboarding to a new codebase. Even if the user just says "review this project" or "what should we improve", this skill applies.'
argument-hint: 'Provide a path to the codebase or directory to assess'
license: SEE LICENSE IN LICENSE
metadata:
  author: 'Guillaume Blanc'
  version: '1.0.0'
compatibility: 'Requires git. Works with GitHub Copilot and other Agent Skills-compatible tools.'
---

# Code Assessment Skill

Orchestrates a parallel codebase assessment by dispatching four specialized subagents — QA, Technical Debt, Functional, and Architecture — then consolidates their findings into a single prioritized report focused on the most impactful improvements.

## Assessment Philosophy

The purpose of an assessment is to surface the findings that matter most — the ones that, if addressed, would meaningfully improve the project's quality, reliability, or maintainability. A long list of cosmetic issues buries the signal in noise.

Prioritize ruthlessly:
- **Critical and Major findings** get full analysis, concrete recommendations, and file-level detail.
- **Quick wins** (high impact, low effort) are called out explicitly so teams can act on them immediately.
- **Minor issues** are acknowledged but grouped into a compact summary by theme (e.g., "12 naming inconsistencies across the service layer") rather than itemized individually. The reader should know what categories of small debt exist and roughly where, without wading through dozens of low-severity line items.

The goal is a report the team can act on *today*, not an exhaustive catalog.

## When to Use

- Assess overall code quality of a project or module
- Audit test quality and coverage gaps across the codebase
- Detect code duplication and convention violations project-wide
- Validate functional correctness and identify missing edge cases
- Evaluate architectural consistency and identify structural improvements
- Onboard onto a new codebase by understanding its strengths and weaknesses
- Answer "what should we improve?" or "where is the technical debt?"

## Procedure

### 0. Determine Assessment Scope

Ask the user (or infer from context) what to assess:
- **Full project**: analyze the entire repository
- **Module/directory**: analyze a specific path (e.g., `src/services/`)
- **Technology/layer**: analyze a specific layer (e.g., "all API controllers", "the data access layer")

If no scope is specified, default to the full project rooted at the current working directory.

### 1. Read Repository Instruction Files

Check for and read the repository's instruction files: `.github/copilot-instructions.md`, `.github/instructions/*.md`, `AGENTS.md`, `.github/AGENTS.md`, `README.md`, `CONTRIBUTING.md`. Extract any coding conventions, architecture rules, test expectations, or review guidance. These represent intentional decisions — don't flag them as issues. Pass these as a `repo_conventions` block to each subagent in Step 4.

### 2. Scan and Categorize Files

Enumerate all files within the assessment scope and classify them:

| Category | Matching patterns | Primary consumers |
|----------|-------------------|-------------------|
| `test_files` | `*.test.*`, `*.spec.*`, `__tests__/**`, `tests/**`, `test/**` | QA |
| `source_files` | Application code not matching other categories | Functional, Tech Debt, Architecture |
| `config_files` | `*.config.*`, `tsconfig*`, `package.json`, `.eslintrc*`, CI files | Tech Debt |
| `docs_files` | `*.md`, `docs/**`, `README*` | — (informational only) |

#### Strip noise

Exclude files and directories that won't yield useful findings:
- Dependencies: `node_modules/`, `vendor/`, `.m2/`, `__pycache__/`
- Lock files: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- Generated/compiled output: `dist/`, `build/`, `target/`, `.min.js`, `.min.css`
- Binary files and media assets
- IDE/editor configuration: `.idea/`, `.vscode/` (except instruction files)

Report the scan summary to the user:

```
Scanning scope: <path>
  Source files: <n>
  Test files: <n>
  Config files: <n>
  Docs files: <n>
  Excluded: <n> (generated/vendor/binary)
```

If the scope contains only docs/config files, note "No source code to assess" and skip the review.

### 3. Build Common Context

Before dispatching subagents, the parent agent does the investigative groundwork once so that subagents can skip discovery and go straight to analysis. This avoids four agents independently re-reading the same files, re-mapping the same structure, and re-identifying the same tech stack.

Build a **common context block** that will be included verbatim in every subagent's prompt:

#### 3a. Project Map

Produce a concise structural overview of the codebase within scope:
- **Directory tree** (top 2-3 levels, omitting noise directories)
- **Key modules and their responsibilities** — e.g., "`src/services/` contains business logic", "`src/api/` contains REST controllers"
- **Entry points** — main files, server bootstraps, CLI entry points
- **Shared/cross-cutting code** — utilities, middleware, base classes, shared types that many modules depend on

#### 3b. Tech Stack Summary

Detect and document:
- Languages and versions (from config files, CI, or runtime manifests)
- Frameworks and libraries (e.g., Express, Spring Boot, React)
- Build tools and task runners (e.g., Webpack, Gradle, Make)
- Test frameworks and assertion libraries (e.g., Jest, JUnit, pytest)
- Linters, formatters, and static analysis tools already in use

#### 3c. Conventions and Patterns Already in Place

From Step 1's instruction files and from scanning the code itself, document:
- **Naming conventions** observed (files, functions, classes, variables)
- **Error handling patterns** (custom error classes, middleware, try/catch conventions)
- **Logging patterns** (structured logging, log levels, logger setup)
- **Dependency injection / wiring** patterns
- **API design conventions** (response shapes, middleware chains, auth patterns)

This prevents subagents from flagging intentional project decisions as issues and gives them a baseline to compare against.

#### 3d. Scoped File Lists

For each subagent, filter the categorized files from Step 2 to the set relevant to their scope:
- **QA**: `test_files` + the `source_files` they correspond to (so coverage gaps can be identified)
- **Tech Debt**: `source_files` + `config_files`
- **Functional**: `source_files` (focus on business logic, services, controllers)
- **Architecture**: `source_files` + `config_files` + project structure

#### 3e. Common Dispatch Preamble

Include the following instruction in every subagent context packet:

> **Common context**: You are receiving a pre-built project map, tech stack summary, and conventions list. Use these as your starting point — do not spend time rediscovering project structure or tech stack. Jump straight into analysis within your scope.
>
> **Prioritization**: Focus your analysis on findings that are 🔴 Critical or 🟠 Major — security flaws, correctness bugs, significant coverage gaps, structural problems that compound over time, and patterns that hurt the whole team's productivity. For 🟡 Minor and 🟢 Suggestion findings, report them as a grouped summary (e.g., "5 instances of inconsistent error handling in the controller layer — see files X, Y, Z") rather than individual write-ups. Also flag any **quick wins**: issues that are high impact but low complexity to fix.
>
> **Full codebase analysis**: Explore the codebase broadly within the defined scope, not just a diff. The goal is a comprehensive health assessment.

### 4. Dispatch Parallel Subagents

Run the selected subagents **in parallel**. Each receives the common context block from Step 3 plus their scoped file list, and returns a structured findings list.

Use these exact registered agent names when invoking subagents:

| Subagent | Focus | Registered Agent Name |
|----------|-------|-----------------------|
| **QA Review** | Test quality, coverage gaps, test utils reuse | `Code Review - QA` |
| **Technical Debt Review** | Code duplication, conventions, maintainability | `Code Review - Technical Debt` |
| **Functional Review** | Functional correctness, edge cases, missing logic | `Code Review - Functional` |
| **Architecture Review** | Architectural consistency, pattern reuse, module boundaries | `Code Review - Architecture` |

Do not use shorthand handles or inferred filenames when invoking the agents. The subagent runner resolves the exact registered name.

Pass to each subagent:
- The **common context block** (project map, tech stack, conventions, preamble) from Step 3
- The **scoped file list** for that subagent from Step 3d
- Full access to the repository for deeper exploration within scope if needed

Launch the subagents as soon as the common context is built.
Do not block dispatch on manual review of the code by the parent agent.

### 5. Consolidate Report

Once all subagents return, merge their findings into a single report using the [report template](./assets/report-template.md).

#### Triage: Separate Signal from Noise

Before writing the report, sort all subagent findings into two buckets:

**Bucket A — Featured findings** (🔴 Critical + 🟠 Major + Quick Wins):
These get full individual write-ups with file references, clear descriptions, and actionable recommendations. For each finding, determine:

| Field | Description |
|-------|-------------|
| **Category** | QA / Technical Debt / Functional / Architecture |
| **Criticality** | 🔴 Critical or 🟠 Major |
| **File(s)** | Affected file(s) and line(s) |
| **Description** | Clear explanation of the issue and why it matters |
| **Recommendation** | Actionable fix or improvement |
| **Complexity** | Low / Medium / High |
| **Regression Risk** | Low / Medium / High |

**Bucket B — Minor issues recap** (🟡 Minor + 🟢 Suggestion):
Group these by theme (e.g., "naming inconsistencies", "missing edge-case tests", "minor duplication") and present as a compact summary table. Each row should name the theme, count the occurrences, list a few representative files, and note the general recommendation. Do not write individual findings for minor items unless one is exceptionally noteworthy.

#### Identify Quick Wins

Scan all findings (including Major ones) for **quick wins** — improvements that are low complexity, low regression risk, but have outsized impact on code health, developer experience, or risk reduction. Examples:
- A missing null check on a widely-used utility
- A duplicated 3-line block that could be extracted into an existing helper
- A config value hardcoded in multiple places that already has an env var
- A test asserting the wrong expected value

Call these out in a dedicated "Quick Wins" section so they don't get lost in a longer roadmap.

#### Build the Improvement Roadmap

After triaging findings, build an **Improvement Roadmap** that focuses the team's energy where it counts:

1. **Quick Wins** — Low complexity, low regression risk, high impact. These can often be done in the same sprint without planning overhead.
2. **Critical Fixes** — 🔴 Critical findings (security risks, data loss, broken core functionality). Non-negotiable, address immediately.
3. **High-Impact Improvements** — 🟠 Major findings that significantly affect maintainability, reliability, or developer experience. These deliver the most value relative to their complexity.
4. **Refinements** — Summarize the themes from the minor issues recap with a general direction (e.g., "Standardize error handling across the service layer"). No need to list each minor finding again.

For each item in Quick Wins, Critical Fixes, and High-Impact Improvements, assess **complexity** (Low / Medium / High) and **regression risk** (Low / Medium / High). Never estimate time — complexity and regression risk give teams the information they need to plan without creating false precision.

#### Codebase Health Summary

Produce an overall health assessment:

| Dimension | Rating | Summary |
|-----------|--------|---------|
| **Test Coverage & Quality** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary from QA findings} |
| **Code Quality & Maintainability** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary from Tech Debt findings} |
| **Functional Correctness** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary from Functional findings} |
| **Architecture & Structure** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary from Architecture findings} |

### 6. Classify Criticality

Assign severity using these guidelines:

- **🔴 Critical** → Security flaw, data loss risk, broken core functionality, tests asserting wrong behavior.
- **🟠 Major** → Significant coverage gap, convention violation impacting maintainability, functional gap for common cases, architectural anti-pattern affecting multiple modules.
- **🟡 Minor** → Missing edge case test, minor duplication, cosmetic functional gap, naming inconsistency.
- **🟢 Suggestion** → Improvement opportunity, optional refactor, nice-to-have test.

When in doubt between Minor and Major, ask: "If a new developer joined the team tomorrow, would this issue confuse them, slow them down, or cause a bug within their first month?" If yes, it's Major.

### 7. Save and Present Report

Save the consolidated report as a Markdown file in the `.ai/review/` directory at the repository root (create the directory if it doesn't exist).

Name the file: `.ai/review/code-assessment.md`. If assessing a specific module, include it in the name: `.ai/review/code-assessment-<module>.md`.

Present the report to the user with:
1. Executive summary and health scores
2. Quick wins (these are the "do it now" items)
3. Critical and major findings in full detail
4. Improvement roadmap
5. Minor issues recap (compact table)
6. Positive highlights

The reader should be able to stop after the quick wins and critical findings and already have a clear action plan.
