# Path A — GitHub MCP

**When to use:** Whenever `pull_request_read` or `list_pull_requests` tools are present in your current tool set. These tools return structured data and are faster than CLI alternatives. **You must prefer this path over `gh` CLI or `git` commands when these tools exist.**

## Gathering PR Context

Run these calls **in parallel** to gather all PR context at once:

1. **PR metadata + diff + files** — Use `pull_request_read` with the PR number and `owner/repo` to get the PR title, body, base branch, head branch, changed files, and full diff.
2. **Existing PR comments** (for dedup) — Use `pull_request_read` or the appropriate MCP tool to retrieve existing review comments and conversation comments.
3. **Referenced issues** — If the PR title, body, or commit messages reference issues (e.g., `#123`, `fixes #456`, `closes #789`), use `issue_read` to fetch each referenced issue's title, body, and labels. Pass this context to subagents so they can validate the PR against the issue's requirements and acceptance criteria.

If `actions_list` or `get_job_logs` tools are also available, use them to check CI status and gather failure logs when CI has failed.

## Reading MCP Result Files Efficiently

The `pull_request_read` tool returns data in files (typically `content.txt` and `content.json`). Before reading these files, **count their lines first** (e.g., `wc -l`) for both files in a single command. Then:

- If a file is **≤ 3000 lines**, read it in a single call covering lines 1 to the end.
- If a file is **> 3000 lines**, read it in chunks of ~1000 lines.

This avoids the costly pattern of reading small files in many incremental chunks.

## After Gathering

Dispatch the subagents as soon as MCP results are available. **Do not fall through to Path B or C if Path A succeeds.**
