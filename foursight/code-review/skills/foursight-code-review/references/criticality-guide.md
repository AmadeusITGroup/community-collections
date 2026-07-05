# Criticality Guide

Reference for assigning criticality levels to PR review findings.

## 🔴 Critical — Always Blocking

The PR **must not** be merged until these are resolved.

| Category | Examples |
|----------|----------|
| **QA** | Tests assert wrong behavior; tests pass but validate the opposite of intent; mocking hides real bugs |
| **Tech Debt** | Security-sensitive code duplicated with subtle differences; violation of critical project convention (e.g., auth pattern) |
| **Functional** | Core feature doesn't work; data loss or corruption risk; security vulnerability introduced |

## 🟠 Major — Usually Blocking

The PR **should not** be merged without addressing these, unless there is a justified reason to defer.

| Category | Examples |
|----------|----------|
| **QA** | Significant coverage gap on new public API; tests only cover happy path for complex feature; test setup duplicates existing utility extensively |
| **Tech Debt** | Reinventing an existing project utility; major convention violation affecting consistency; function doing too many things (SRP violation) |
| **Functional** | Common user scenario unhandled; error path returns misleading message; missing validation on user-facing input |

## 🟡 Minor — Not Blocking

Should be improved but won't prevent merge.

| Category | Examples |
|----------|----------|
| **QA** | Missing edge case test for unlikely scenario; slightly redundant test; test name could be clearer |
| **Tech Debt** | Minor naming inconsistency; small duplication (< 5 lines); slightly verbose code |
| **Functional** | Cosmetic edge case; error message could be more helpful; minor UX gap |

## 🟢 Suggestion — Not Blocking

Optional improvements and nice-to-haves.

| Category | Examples |
|----------|----------|
| **QA** | Could add a test for documentation purposes; test structure could be improved |
| **Tech Debt** | Opportunity to extract a reusable utility; alternative pattern that's slightly cleaner |
| **Functional** | Enhancement idea beyond PR scope; future-proofing suggestion |

## Pre-existing Issue Handling

When a finding exists in code **not changed by the PR**:
- Mark as **Pre-existing: Yes**
- Keep the original criticality level for informational purposes
- Mark as **Blocking: No** regardless of criticality — the PR author is not responsible for pre-existing debt
- If the pre-existing issue is 🔴 Critical (e.g., security), add a note recommending a follow-up ticket
