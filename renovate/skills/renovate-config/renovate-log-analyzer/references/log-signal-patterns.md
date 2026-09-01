# Renovate Log Signal Patterns

Use these patterns to classify Renovate output before making recommendations. Quote the relevant log line and retain the package, manager, datasource, and repository context.

## Severity Signals

| Signal                | Meaning                                 | First check                                                 |
| --------------------- | --------------------------------------- | ----------------------------------------------------------- |
| `ERROR:`              | A run-level or dependency-level failure | The surrounding stack, package, and final repository result |
| `WARN:`               | A degraded action or recoverable issue  | Whether it prevented a branch or PR action                  |
| `repository problems` | Problems summarized at run completion   | The corresponding earlier warning or error                  |

## Update Suppression Signals

| Pattern                            | Typical interpretation                        | Follow-up                                             |
| ---------------------------------- | --------------------------------------------- | ----------------------------------------------------- |
| `skipReason`                       | Renovate intentionally skipped the update     | Capture the exact reason and matching rule            |
| `Found no results from datasource` | Datasource returned no usable release         | Confirm package name, registry, and datasource access |
| `unsupported/unversioned value`    | Existing dependency value cannot be versioned | Inspect the manifest value and versioning scheme      |
| `Package lookup failures`          | One or more dependency lookups failed         | Read the nested `warnings[]` values                   |

## Access and Repository Signals

| Pattern                              | Typical interpretation                                | Follow-up                                     |
| ------------------------------------ | ----------------------------------------------------- | --------------------------------------------- |
| `Could not resolve to a Repository`  | Repository metadata could not be resolved             | Check source URL, host rules, and token scope |
| `Cannot access vulnerability alerts` | Platform token lacks alert access                     | Check app installation and GitHub permissions |
| `401`, `403`, `404` near a lookup    | Authentication, authorization, or registry path issue | Identify the host and request endpoint        |

## Useful Context Patterns

- `Repository started` and `Repository finished` establish the run boundary.
- `Post-massage config` and `Repository config` reveal effective configuration.
- `Dependency extraction complete` and `Found N package file` show what Renovate discovered.
- `branchesInformation` summarizes proposed, pending, and suppressed updates.

Do not classify a warning as a configuration defect until the matching rule, datasource response, and final repository result support that conclusion.
