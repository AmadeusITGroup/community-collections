# Path C — Local `git` Only

**When to use:** Only if neither MCP tools nor `gh` CLI are available. This is the last resort.

## Gathering PR Context

Keep to the minimum needed:

```bash
git fetch origin
git diff --name-only origin/<base>...origin/<head>
git diff --no-ext-diff --find-renames --unified=3 origin/<base>...origin/<head>
```

## Limitations

No existing-comment dedup is possible on this path — note this in the report.
