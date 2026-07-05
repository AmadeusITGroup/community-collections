# External Repository Review Procedure

When the PR targets a repository that is **not** the current workspace, follow this procedure before gathering PR context (Step 1).

## 1. Clone the Target Repository

Create a shallow, single-branch clone into a temporary directory:

```bash
git clone --depth=50 --single-branch --branch <head-branch> \
  https://github.com/<owner>/<repo>.git /tmp/pr-review-<owner>-<repo>
```

Then `cd` into the cloned directory so all subsequent git commands and file reads operate on the correct codebase.

Inform the user: _"Cloned `<owner>/<repo>` into `/tmp/pr-review-<owner>-<repo>` for this review."_

**If the clone already exists** (e.g., from a previous review), reuse it:

```bash
cd /tmp/pr-review-<owner>-<repo>
git fetch origin <head-branch>
git checkout <head-branch>
git pull --ff-only
```

## 2. Read Repository Instruction Files

After cloning (or confirming you are inside the correct repo), **read the repository's own instruction files** before dispatching subagents. These files contain project-specific conventions, architectural decisions, and review expectations that subagents must respect.

Check for and read these files **in this order** (skip any that don't exist):

| Priority | Path | Purpose |
|----------|------|---------|
| 1 | `.github/copilot-instructions.md` | Project-wide coding conventions and standards |
| 2 | `.github/instructions/*.md` | Scoped instructions for specific file patterns or areas |
| 3 | `AGENTS.md` (repo root) | Agent-specific behavioral guidance |
| 4 | `.github/AGENTS.md` | Alternative location for agent guidance |

Check for the existence of these files using the file-reading tools available on your platform (e.g., `list_dir`, `read_file`, or equivalent).

Read each discovered file and extract:
- **Coding conventions** — naming, formatting, patterns to follow or avoid
- **Architecture rules** — module boundaries, dependency directions, required patterns
- **Test expectations** — coverage requirements, test framework preferences, fixture conventions
- **Review-specific guidance** — anything explicitly addressing PR reviews or quality gates

## 3. Pass Repo Conventions to Subagents

Include a `repo_conventions` section in the context packet dispatched to each subagent. Structure it as:

```
### Repository Conventions (from instruction files)

- [convention 1 from copilot-instructions.md]
- [convention 2 from AGENTS.md]
- [scoped rule from instructions/api.instructions.md — applies to: src/api/**]
...
```

Subagents must treat these conventions as **authoritative** when evaluating findings. A pattern that violates the repository's own documented conventions is at minimum 🟡 Minor; a pattern that violates a convention marked as mandatory or critical is 🟠 Major.

## 4. Return to the Review Flow

After completing steps 1–3, continue with Step 1 (Gather Context) of the main skill. The cloned repo and extracted conventions are now available for the remainder of the review.
