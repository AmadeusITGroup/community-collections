---
name: renovate-log-analyzer
description: 'Analyze a Renovate run log to explain why dependency updates failed or were skipped, and enumerate the network calls Renovate made. Use when a user shares or points to a Renovate log and asks "why did renovate fail", "why wasnt X updated", "analyze this renovate log", or "what network calls did renovate make".'
argument-hint: "Point to the Renovate log file (LOG_LEVEL=debug preferred)"
metadata:
  author: "Mahesh GADAGI"
  version: "1.0.0"
compatibility: "Works with GitHub Copilot and other Agent Skills-compatible tools. Reads Renovate CI or self-hosted logs."
---

# Renovate Log Analyzer

Parse a Renovate run log and produce a structured report: run summary, configuration, extraction stats, issues/failures, PR actions, pending updates, **network calls**, and recommendations.

## Bundled and shared resources

- **Bundled asset** alongside this SKILL.md: `assets/report-template.md` (the report shape).
- **Bundled references** alongside this SKILL.md: `references/log-signal-patterns.md` and `references/network-call-patterns.md`. Derive their absolute path from where this SKILL.md was loaded.
- If any bundled asset or reference file cannot be located, inform the user which file is missing and proceed with best-effort analysis without it, clearly noting which sections are affected.

## Input

The user provides a Renovate log file. For logs exceeding 1000 lines, always use targeted `grep_search` instead of reading the whole file. Network-call detail requires the run to use `LOG_LEVEL=debug`. If the log level is not debug, skip Step 6, populate the Network Calls section with "Not available: log was not captured at LOG_LEVEL=debug", and advise the user to re-run Renovate with `LOG_LEVEL=debug` to obtain network call data.

## Procedure

### 1. Run context

Grep: `Repository started|renovateVersion|log-level`. Capture repo, version, log level.

### 2. Config loaded

Grep: `Post-massage config|Repository config`. Capture extends, packageRules, lockFileMaintenance, custom managers.

### 3. Extraction summary

Grep: `Dependency extraction complete` (per-manager stats) and `Found N package file`.

### 4. Failures & skips

Use the failure catalog in `references/log-signal-patterns.md`: `WARN:`, `ERROR:`, `skipReason`, `Package lookup failures` (and its `warnings[]`), `Could not resolve to a Repository`, `Found no results from datasource`, `Cannot access vulnerability alerts`, `unsupported/unversioned value`. For each, capture the package, datasource, and reason.

### 5. PR actions & pending updates

Grep: `Branch created|updated`, `PR created|updated|closed`, `packageFiles with updates`, `branchesInformation`.

### 6. Network calls (new capability)

Using `references/network-call-patterns.md`: grep request lines and the http-stats block. Group calls by host/datasource, tally counts, and flag retries, timeouts, and non-2xx responses. Cross-reference failing hosts with the lookup failures from Step 4.

### 7. Final status

Grep: `Repository finished` (result, status, durationMs) and `repository problems`.

## Output

Fill `assets/report-template.md`. Present the report in chat. On request, save it to `.ai/renovate/log-analysis-<repo-or-timestamp>.md` (create the directory if needed).

## Tips

- Large logs: use several targeted greps, not a full read.
- `branchesInformation` is the most compact source of proposed upgrades.
- Private-org lookup failures usually mean the bot lacks read access, not a config bug.
- `latest`-tagged deps are skipped intentionally without `pinDigests`.
