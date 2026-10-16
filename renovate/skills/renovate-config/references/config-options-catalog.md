# Renovate Configuration Catalog

Use this focused catalog when building repository-level `renovate.json` files. Verify less common options against the official Renovate documentation before using them.

## Baseline

- Add `"$schema": "https://docs.renovatebot.com/renovate-schema.json"` as the first key.
- Start with `config:recommended` unless the repository has a documented alternative policy.
- Keep `packageRules` focused: each rule should include one or more `match...` fields and describe a single policy.

## PR Volume and Visibility

| Goal                               | Option                | Recommended starting value      |
| ---------------------------------- | --------------------- | ------------------------------- |
| Limit concurrent pull requests     | `prConcurrentLimit`   | `3`                            |
| Limit hourly pull-request creation | `prHourlyLimit`       | `3`                             |
| Identify Renovate pull requests    | `labels`              | `["renovate"]`              |
| Track deferred updates             | `dependencyDashboard` | Enabled by `config:recommended` |

## Update Grouping

- Use `packageRules` with `matchManagers` and `matchUpdateTypes` to group non-major updates per ecosystem.
- Keep major updates separate unless the repository explicitly accepts grouped breaking changes.
- Use `groupName` for a readable, stable PR grouping label.

```json
{
  "packageRules": [
    {
      "description": "Group non-major npm updates",
      "matchManagers": ["npm"],
      "matchUpdateTypes": ["minor", "patch"],
      "groupName": "npm non-major dependencies"
    }
  ]
}
```

## Stability and Scheduling

- For npm packages, `minimumReleaseAge: "3 days"` protects against packages that may still be unpublished.
- Use `schedule` to reduce CI contention, not to delay risky releases.
- Prefer Cron syntax for new schedules. Renovate requires a five-part expression with `*` for minutes.
- Keep scheduling windows at least three to four hours unless Renovate runs frequently enough to hit a narrower window.

## Lock-file Maintenance

Configure dedicated lock-file refreshes at the root level. This applies to all supported lock files found by Renovate.

```json
{
  "lockFileMaintenance": {
    "enabled": true,
    "schedule": ["before 5am on monday"]
  }
}
```

Do not place `lockFileMaintenance` inside a `packageRules` entry.

## Further Reading

- https://docs.renovatebot.com/configuration-options/
- https://docs.renovatebot.com/config-validation/
- https://docs.renovatebot.com/noise-reduction/
