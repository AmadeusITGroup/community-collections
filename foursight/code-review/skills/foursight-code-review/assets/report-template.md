# PR Review Report

## Executive Summary

{One paragraph summary: total findings count, breakdown by criticality, overall merge recommendation}

**Verdict**: ✅ Ready to merge | ⚠️ Merge after fixes | ❌ Requires changes

| Criticality | Count |
|-------------|-------|
| 🔴 Critical | {n} |
| 🟠 Major    | {n} |
| 🟡 Minor    | {n} |
| 🟢 Suggestion | {n} |

---

## Blocking Issues

Issues that must be resolved before merging.

{List blocking findings here, or "No blocking issues found." Each finding uses the format below.}

### Finding Format

Every finding must include an **ID** for easy reference. Use the format `<Category><Number>` where Category is a short prefix and Number is sequential within that category:

| Category | Prefix |
|----------|--------|
| QA | `QA` |
| Technical Debt | `TD` |
| Functional | `FN` |
| Architecture | `AR` |

Example:

> **FN1** 🟠 Major — `src/handler.ts:42` — Missing null check on user input
>
> The `processOrder()` function does not validate that `order.items` is non-empty before iterating. This will throw at runtime for empty orders.
>
> **Recommendation:** Add a guard clause at the top of `processOrder()`.

Use this format consistently for all findings in every section below.

---

## Risk Assessment & Manual Testing Guidance

### Blast Radius

{Describe the scope of impact: is it isolated to a single module/feature, does it affect multiple areas, or is it a cross-cutting change with global impact?}

**Impact scope**: 🔵 Isolated (single module) | 🟠 Multi-area | 🔴 Global (cross-cutting)

### High-Risk Areas

{List the specific areas/flows where the code changes introduce the most risk. For each area, explain WHY it is at risk — e.g., complex logic change, missing test coverage, behavioral change in shared code, implicit contract change.}

| Risk Area | Risk Level | Why | Files |
|-----------|-----------|-----|-------|
| {area}    | 🔴 High / 🟠 Medium / 🟡 Low | {reason} | {files} |

### Manual Testing Recommendations

{Provide concrete, actionable testing guidance based on the risk analysis above.}

**If impact is global (🔴):** A full non-regression test pass is recommended before merge. Pay special attention to the high-risk areas listed above.

**Targeted test scenarios:**

| # | Scenario | Priority | Related Risk Area | Steps / Focus |
|---|----------|----------|-------------------|---------------|
| 1 | {scenario} | 🔴 Must-test / 🟠 Should-test / 🟡 Nice-to-test | {area from table above} | {what to verify} |

{If certain functionality cannot be validated by automated tests alone, explain why manual verification is necessary (e.g., UI behavior, third-party integration, timing-sensitive flows).}

---

## Non-Blocking Findings

### QA Review

{QA findings with criticality 🟡 Minor or 🟢 Suggestion, or "No findings."}

### Technical Debt Review

{Tech Debt findings with criticality 🟡 Minor or 🟢 Suggestion, or "No findings."}

### Functional Review

{Functional findings with criticality 🟡 Minor or 🟢 Suggestion, or "No findings."}

### Architecture Review

{Architecture findings with criticality 🟡 Minor or 🟢 Suggestion, or "No findings."}

---

## Pre-existing Issues

Issues that were present before this PR. Not blocking for this review.

{List pre-existing findings, or "No pre-existing issues identified."}

---

## Positive Highlights

Good practices and patterns observed in this PR.

{Consolidated highlights from all four subagents}

---

## Testing Verdict

{One-line summary: Can this PR be validated with automated tests alone, or does it require manual testing?}

- **Automated coverage sufficient**: Yes / Partial / No
- **Manual testing required**: Yes / No
- **Non-regression scope**: None / Targeted / Full
