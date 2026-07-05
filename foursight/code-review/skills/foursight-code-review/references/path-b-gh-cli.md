# Path B — Local `gh` CLI

**When to use:** Only if GitHub MCP tools are not available in your current tool set. **Always set `GH_PAGER=cat`** before running `gh` commands to prevent pager issues in non-interactive terminals.

## Gathering PR Context

```bash
export GH_PAGER=cat

# Metadata
gh pr view <target> --json number,title,body,baseRefName,headRefName,files,url

# Diff
gh pr diff <target>

# Existing comments (for dedup)
gh pr view <target> --json comments,reviews
gh api repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '[.[] | {author: .user.login, body: .body, path: .path, line: .line}]'
```

## After Gathering

Dispatch the subagents immediately after this data is available.
