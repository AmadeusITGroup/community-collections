# Codebase Assessment Report

## Executive Summary

{One paragraph summary: scope analyzed, key findings that matter most, and overall health. Lead with the most impactful discovery, not the total count of issues.}

| Criticality | Count |
|-------------|-------|
| 🔴 Critical | {n} |
| 🟠 Major    | {n} |
| 🟡 Minor + 🟢 Suggestion | {n} (summarized) |

---

## Codebase Health

| Dimension | Rating | Summary |
|-----------|--------|---------|
| **Test Coverage & Quality** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary} |
| **Code Quality & Maintainability** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary} |
| **Functional Correctness** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary} |
| **Architecture & Structure** | 🟢 Good / 🟡 Fair / 🔴 Poor | {one-line summary} |

---

## Quick Wins

High-impact improvements that are small effort. Act on these immediately.

| # | Finding | Category | Files | Why it matters | Complexity | Regression Risk |
|---|---------|----------|-------|----------------|------------|------------------|
| 1 | {description} | QA / TD / FN / AR | {files} | {impact if not fixed} | Low / Medium / High | Low / Medium / High |

---

## Critical Issues

Issues that require immediate attention — security flaws, data loss risks, broken core functionality.

{List critical findings here, or "No critical issues found."}

### Finding Format

Every finding must include an **ID** for easy reference. Use the format `<Category><Number>`:

| Category | Prefix |
|----------|--------|
| QA | `QA` |
| Technical Debt | `TD` |
| Functional | `FN` |
| Architecture | `AR` |

Example:

> **TD1** 🟠 Major — `src/utils/parser.ts:42-58` — Duplicated parsing logic
>
> The JSON parsing and validation logic in `parseInput()` is duplicated across three service files. The existing `ValidationUtils` class already provides this functionality.
>
> **Recommendation:** Replace inline parsing with `ValidationUtils.parseAndValidate()`.
> **Complexity:** Low | **Regression Risk:** Low

---

## Major Findings

Significant issues affecting maintainability, reliability, or developer experience.

{List major findings in full detail using the format above.}

---

## Improvement Roadmap

### Quick Wins

{Repeat the quick wins table from above — readers may jump straight to this section.}

### Critical Fixes

{🔴 Critical findings requiring immediate action, or "No critical fixes needed."}

| # | Finding | Complexity | Regression Risk | Impact | Files |
|---|---------|------------|-----------------|--------|-------|
| 1 | {description} | Low / Medium / High | Low / Medium / High | {expected impact} | {files} |

### High-Impact Improvements

{🟠 Major findings with significant maintainability/reliability impact}

| # | Finding | Complexity | Regression Risk | Impact | Files |
|---|---------|------------|-----------------|--------|-------|
| 1 | {description} | Low / Medium / High | Low / Medium / High | {expected impact} | {files} |

### Refinements

{General direction for minor issue themes — no need to re-list every item.}

| # | Theme | Count | Representative Files | Direction |
|---|-------|-------|---------------------|-----------|
| 1 | {theme, e.g., "Naming inconsistencies"} | {n} | {2-3 example files} | {what to standardize} |

---

## Minor Issues Summary

A compact recap of lower-severity findings, grouped by theme. These are worth addressing over time but should not distract from the critical and major work above.

| Theme | Category | Count | Representative Files | Recommendation |
|-------|----------|-------|---------------------|----------------|
| {e.g., "Inconsistent error handling"} | TD | {n} | {files} | {general guidance} |
| {e.g., "Missing edge-case tests"} | QA | {n} | {files} | {general guidance} |

---

## Detailed Findings

### QA Review

{QA findings (Critical + Major in full detail), or "No findings."}

### Technical Debt Review

{Tech Debt findings (Critical + Major in full detail), or "No findings."}

### Functional Review

{Functional findings (Critical + Major in full detail), or "No findings."}

### Architecture Review

{Architecture findings (Critical + Major in full detail), or "No findings."}

---

## Positive Highlights

{Good practices and patterns observed across all categories — proper abstractions, clean architecture, thorough testing, well-organized code.}
