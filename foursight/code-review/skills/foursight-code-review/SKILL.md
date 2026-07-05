---
name: foursight-code-review
description: 'Parallel PR review with specialized subagents for QA, Technical Debt, Functional, and Architecture analysis. Use when reviewing pull requests, checking test quality, detecting tech debt, validating functional completeness, or verifying architectural consistency.'
argument-hint: 'Provide a PR URL or branch name to review'
license: SEE LICENSE IN LICENSE
metadata:
  author: 'gblanc'
  version: '1.0.0'
compatibility: 'Requires git. Works with GitHub Copilot and other Agent Skills-compatible tools.'
---

# PR Review Skill

Orchestrates a parallel PR review by dispatching four specialized subagents — QA, Technical Debt, Functional, and Architecture — then consolidates their findings into a single prioritized report.

## When to Use

- Review a pull request before merge
- Audit test quality and coverage gaps
- Detect code duplication or convention violations
- Validate functional completeness against PR description
- Verify architectural consistency and pattern reuse

## Bundled Resources

This skill bundles scripts and references alongside this SKILL.md. When you need to execute a bundled script, derive the absolute path from the location where this SKILL.md was loaded. For example, if this SKILL.md was loaded from `/path/to/foursight-code-review/SKILL.md`, the scripts directory is `/path/to/foursight-code-review/scripts/`.

## Procedure

### 0. Detect Repository State

Before gathering PR context, determine where you're running and whether a local clone is available. This avoids slow remote fetches when the repo is already local, and avoids failures when it isn't.

**If the user provides only a PR number (no URL), assume it belongs to the current repository** — derive `owner/repo` from `git remote get-url origin` in the current working directory.

**Always determine the target `owner/repo` first** (from the PR URL, or from `git remote get-url origin` when only a PR number is given), then run the detection script below. MCP availability affects how you *gather PR data* in Step 1, **not** whether you check the repository state here.

#### Run the detection script

Once you have `<owner/repo>` (and optionally the PR head branch), run:

```bash
bash <this-skill-directory>/scripts/detect-repo-state.sh <owner/repo> [pr-head-branch]
```

Where `<this-skill-directory>` is the absolute path to the directory containing this SKILL.md.

The script outputs a JSON object. Use the `situation` field to determine your next action:

| `situation` | What it means | Action |
|-------------|---------------|--------|
| `head-branch-checked-out` | PR head branch is already checked out locally (including fork checkouts) | Use the local repo as-is. Do not clone. |
| `correct-repo-different-branch` | Inside the target repo on a different branch | Run `git fetch origin` then diff against remote refs — no checkout needed. |
| `renamed-repo` | Origin and target HEAD SHAs match — repo was renamed | Use the local repo as-is. The `note` field confirms the matching SHA. |
| `possible-fork` | Same repo name but different owner — likely a fork | Fetch PR refs from `upstream` or the PR URL; diff locally. Do not clone. |
| `different-repo` | Local origin does not match the target | **Clone the target repo.** Follow the [external repository review procedure](./references/external-repo-review.md). **Do not skip this step.** |
| `not-in-git-repo` | Not inside any git repository | **Clone the target repo.** Follow the [external repository review procedure](./references/external-repo-review.md). **Do not skip this step.** |

When a shallow clone is created, inform the user: "Cloned `<owner>/<repo>` into `/tmp/pr-review-<owner>-<repo>` for faster diff access."

### 0b. Read Repository Instruction Files

After confirming you have access to the correct repository (either local or freshly cloned), check for and read the repository's instruction files: `.github/copilot-instructions.md`, `.github/instructions/*.md`, `AGENTS.md`, `.github/AGENTS.md`. Extract any coding conventions, architecture rules, test expectations, or review guidance. Pass these as a `repo_conventions` block to each subagent in Step 3.

For external repos this is covered by the [external repository review procedure](./references/external-repo-review.md). For the current workspace, run the same file checks described in that reference (Step 2) without needing to clone.

### 1. Gather Context

Collect only the minimum context required to dispatch the subagents:
- PR number or branch under review
- Base branch
- PR title and description, or inferred intent from commits
- Changed file list
- Full diff
- Existing PR comments and review comments (to avoid duplicate feedback)

The goal of this phase is speed. Do not inspect individual repository files before dispatch.

**Self-check: if you're about to read individual source files before launching the 4 subagents, stop — you're doing it wrong. Dispatch first, verify later.**

**Deduplication**: Before dispatching subagents, collect existing PR comments when possible (paths A and B). Check whether an existing comment already covers the same issue (same file, same concern). Pass only deduplicated context to subagents so they skip already-reported findings.

**Tool detection (mandatory before choosing a path):** Before gathering any PR data, search for available GitHub MCP tools (names containing `pull_request`, `issue`, `actions`). If any `pull_request_read` or `list_pull_requests` tools exist in your current tool set, you **must** use Path A. Only fall through to Path B or C if MCP tools are genuinely unavailable.

Use the first available source and stop as soon as one succeeds. **Do not skip Path A if MCP tools are available.** The `gh` CLI is slower and provides less structured data.

| Priority | Path | When to use | Reference |
|----------|------|-------------|-----------|
| 1 | **Path A — GitHub MCP** | `pull_request_read` or `list_pull_requests` tools are available | [path-a-mcp.md](./references/path-a-mcp.md) |
| 2 | **Path B — Local `gh` CLI** | MCP tools unavailable, `gh` CLI installed | [path-b-gh-cli.md](./references/path-b-gh-cli.md) |
| 3 | **Path C — Local `git` only** | Neither MCP tools nor `gh` CLI available | [path-c-git-only.md](./references/path-c-git-only.md) |

Read **only** the reference file for the path you selected. Do not read the others.

### 2. Prepare Context for Dispatch

Before dispatching subagents, process the raw context to reduce noise and improve focus.

#### a) Classify changed files

Group the changed file list into categories:

| Category | Matching patterns | Primary consumers |
|----------|-------------------|-------------------|
| `test_files` | `*.test.*`, `*.spec.*`, `__tests__/**`, `tests/**`, `test/**` | QA |
| `source_files` | Application code not matching other categories | Functional, Tech Debt, Architecture |
| `config_files` | `*.config.*`, `tsconfig*`, `package.json`, `.eslintrc*`, CI files | Tech Debt |
| `docs_files` | `*.md`, `docs/**`, `README*` | — (informational only) |

Pass each subagent the file categories relevant to it — QA gets `test_files` + related `source_files`, Architecture skips `test_files`, etc.

#### b) Strip noise from the diff

Remove diff hunks for files that never yield useful findings:
- Lock files: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- Generated/compiled output: `dist/`, `build/`, `bin/`, `obj/`, `.min.js`, `.min.css`
- Binary files and compiled executables (`.exe`, `.dll`, `.pdb`)

If the only changes are in noise files, note "PR contains only dependency/build changes" and skip the review.

#### c) Summarize PR intent

Derive a one-line intent statement from the PR title + body + first commit message. Pass it alongside the raw context so subagents don't independently re-interpret the same description.

#### d) Detect PR size and select subagents

Not every PR needs all four subagents:

| PR profile | Subagents to dispatch |
|------------|-----------------------|
| **Docs/config only** (no source or test files changed) | Skip all — report "No code changes to review" |
| **No test files changed** | Dispatch QA with `source_files` only — its focus shifts to identifying missing test coverage for the changed code rather than reviewing existing tests |
| **Small PR** (≤ 3 files, < 50 changed lines) | Run all 4 but allow consolidated output (subagents may return empty findings) |
| **Standard PR** | All 4 subagents |

### 3. Dispatch Parallel Subagents

Run the selected subagents **in parallel**. Each receives the prepared context from Step 2 and returns a structured findings list.

Use these exact registered agent names when invoking subagents:

| Subagent | Focus | Registered Agent Name |
|----------|-------|-----------------------|
| **QA Review** | Test quality, coverage gaps, test utils reuse | `Code Review - QA` |
| **Technical Debt Review** | Code duplication, conventions, maintainability | `Code Review - Technical Debt` |
| **Functional Review** | Functional correctness, edge cases, missing logic | `Code Review - Functional` |
| **Architecture Review** | Architectural consistency, pattern reuse, module boundaries | `Code Review - Architecture` |

Do not use shorthand handles or inferred filenames when invoking the agents. The subagent runner resolves the exact registered name.

Pass to each subagent:
- The prepared context packet from Step 2 (classified files, cleaned diff, intent summary)
- The review category for that subagent
- Access to the repository for broader context when needed

Launch the subagents as soon as the prepared context is available.
Do not block dispatch on manual review of the diff by the parent agent.

### 4. Consolidate Report

Once all subagents return, merge their findings into a single report using the [report template](./assets/report-template.md).

For **each finding**, determine:

| Field | Description |
|-------|-------------|
| **Category** | QA / Technical Debt / Functional / Architecture |
| **Criticality** | 🔴 Critical, 🟠 Major, 🟡 Minor, 🟢 Suggestion |
| **Blocking** | Yes / No — whether this should block the PR from merging |
| **Pre-existing** | Yes / No — whether the issue existed before this PR |
| **File(s)** | Affected file(s) and line(s) |
| **Description** | Clear explanation of the issue |
| **Recommendation** | Actionable fix or improvement |

#### Build the Risk Assessment & Manual Testing Guidance

After merging findings, build the **Risk Assessment & Manual Testing Guidance** section by combining inputs from the Functional and Architecture subagents:

1. **Determine blast radius** — Use the Architecture agent's blast radius assessment combined with the Functional agent's risk areas. Pick the highest impact scope reported:
   - 🔵 **Isolated** — single module, no shared code touched
   - 🟠 **Multi-area** — shared code used by a few specific features
   - 🔴 **Global** — foundational/cross-cutting code that could affect any part of the system

2. **Consolidate high-risk areas** — Merge the Functional agent's risk table with the Architecture agent's dependent module analysis. Each row should state the area, risk level, a concrete "why" tied to the code change, and the affected files.

3. **Derive manual testing recommendations**:
   - If blast radius is 🔴 **Global**: explicitly recommend a **full non-regression test pass** and explain which cross-cutting change drives this.
   - If blast radius is 🟠 **Multi-area**: recommend **targeted non-regression** on the listed affected areas.
   - If blast radius is 🔵 **Isolated**: recommend **targeted testing** of the specific feature only.
   - List concrete test scenarios ordered by priority (🔴 Must-test → 🟠 Should-test → 🟡 Nice-to-test), each linked to a risk area.
   - For each scenario, describe what to verify and explain why manual testing is needed if automated coverage is insufficient.

4. **Set the Testing Verdict** at the bottom of the report:
   - **Automated coverage sufficient**: Yes / Partial / No
   - **Manual testing required**: Yes / No
   - **Non-regression scope**: None / Targeted / Full

### 5. Classify Criticality

Use the [criticality guide](./references/criticality-guide.md) to assign severity:

- **🔴 Critical** → Security flaw, data loss risk, broken core functionality, tests asserting wrong behavior. **Always blocking.**
- **🟠 Major** → Significant coverage gap, convention violation impacting maintainability, functional gap for common cases. **Usually blocking.**
- **🟡 Minor** → Missing edge case test, minor duplication, cosmetic functional gap. **Not blocking.**
- **🟢 Suggestion** → Improvement opportunity, optional refactor, nice-to-have test. **Not blocking.**

### 6. Determine Pre-existing Status

For each finding, check whether the issue was introduced by the PR or already existed:
- Run `git diff` against the base branch to confirm
- If the issue is in unchanged code, mark as **Pre-existing: Yes**
- Pre-existing critical/major issues should be flagged but marked as **not blocking** for this PR

### 7. Present Report

Output the consolidated report with:
1. **Executive Summary** — one-paragraph overview with counts by criticality
2. **Blocking Issues** — items that must be resolved before merge
3. **Risk Assessment & Manual Testing Guidance** — blast radius, high-risk areas, and concrete manual test scenarios with priorities
4. **Non-Blocking Findings** — organized by category (QA → Tech Debt → Functional → Architecture)
5. **Pre-existing Issues** — known issues not introduced by this PR
6. **Positive Highlights** — good patterns and practices observed
7. **Testing Verdict** — whether automated tests suffice, whether manual testing is required, and non-regression scope

### 8. Save Report

Save the consolidated report as a Markdown file in the `.ai/review/` directory at the repository root (create the directory if it doesn't exist).

Name the file based on the PR context: `.ai/review/pr-review-<PR-number>.md` (e.g., `.ai/review/pr-review-42.md`). If the PR number is not available, use the branch name: `.ai/review/pr-review-<branch>.md`.

### 9. Offer to Publish Review Comments

After presenting the report, **ask the user** whether they want to publish the review findings as comments on the pull request. Offer two options:

1. **Via GitHub MCP** — Use `pull_request_review_write` to submit a structured PR review with inline comments on specific files/lines. This is the preferred method when MCP tools are available.
2. **Via `gh` CLI** — Set `export GH_PAGER=cat` first, then use `gh pr review <number> --comment --body "..."` to post a summary comment, or `gh api` to post individual line comments.

Do **not** publish comments automatically — always wait for explicit user confirmation and let them choose the method.
