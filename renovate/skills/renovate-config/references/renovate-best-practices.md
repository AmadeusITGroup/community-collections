# Renovate Best Practices

## Start From Evidence

- Inventory manifests, lock files, runtime declarations, container files, and CI workflows before proposing rules.
- Treat multiple lock files for one ecosystem as a configuration question, not an assumption.
- Preserve a working configuration unless the requested policy requires a change.

## Keep Updates Reviewable

- Group minor and patch updates by ecosystem when their tests cover the group.
- Keep major updates separate by default.
- Use `prConcurrentLimit` and `prHourlyLimit` to prevent CI and review overload.
- Add a stable label so dependency pull requests are easy to filter.

## Protect Supply Chain Changes

- Use `minimumReleaseAge: "3 days"` for npm when release timestamps are available.
- Do not enable automerge without a documented branch-protection and test policy.
- Keep private registry credentials out of repository configuration; use Renovate-supported encrypted configuration or platform secrets.

## Use Schedules Carefully

- Schedules allow branch creation only when Renovate runs during the configured window; they do not trigger Renovate runs.
- Prefer a broad, predictable maintenance window over a narrow window that Renovate may miss.
- Set `timezone` only when the schedule must follow a particular local timezone.

## Validate Before Delivery

- Validate JSON and use `renovate-config-validator` when available.
- Confirm every preset and option exists in the Renovate schema or official documentation.
- Re-read final rules for conflicting matches, especially grouping, automerge, and allowed-version policies.

## Official Sources

- https://docs.renovatebot.com/config-validation/
- https://docs.renovatebot.com/configuration-options/
- https://docs.renovatebot.com/key-concepts/pull-requests/
