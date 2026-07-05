#!/usr/bin/env bash
# detect-repo-state.sh
# Determines the local repository state for PR review (Step 0).
#
# Usage: bash detect-repo-state.sh <owner/repo> [pr-head-branch]
#
# Outputs a single-line JSON object:
#   situation  — one of: head-branch-checked-out | correct-repo-different-branch |
#                        renamed-repo | possible-fork | different-repo | not-in-git-repo
#   action     — recommended next action
#   note       — optional extra context (e.g. matching SHA, branch name)

TARGET_REPO="${1:-}"
PR_HEAD_BRANCH="${2:-}"

if [[ -z "$TARGET_REPO" ]]; then
  echo '{"error":"Usage: detect-repo-state.sh <owner/repo> [pr-head-branch]"}' >&2
  exit 1
fi

# Build canonical HTTPS URL for the target
github_url() { echo "https://github.com/${1}.git"; }

# Normalise a remote URL: strip .git, convert SSH to HTTPS, lowercase
normalize_remote() {
  echo "$1" \
    | sed 's/\.git$//' \
    | sed 's|^git@github\.com:|https://github.com/|' \
    | tr '[:upper:]' '[:lower:]'
}

# Emit result JSON and exit
result() {
  local situation="$1" action="$2" note="${3:-}"
  # Escape double-quotes in note
  note="${note//\"/\\\"}"
  printf '{"situation":"%s","action":"%s","note":"%s"}\n' "$situation" "$action" "$note"
}

# ── 1. Are we inside a git repo at all? ───────────────────────────────────────
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  result "not-in-git-repo" "clone" "Not inside any git repository."
  exit 0
fi

CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "")"
ORIGIN_URL="$(git remote get-url origin 2>/dev/null || echo "")"

# ── 2. PR head branch already checked out? ───────────────────────────────────
if [[ -n "$PR_HEAD_BRANCH" && "$CURRENT_BRANCH" == "$PR_HEAD_BRANCH" ]]; then
  result "head-branch-checked-out" "use-local-as-is" \
    "Branch '$PR_HEAD_BRANCH' is already checked out locally."
  exit 0
fi

# ── 3. Does origin match the target repo? ────────────────────────────────────
NORM_ORIGIN="$(normalize_remote "$ORIGIN_URL")"
NORM_TARGET="$(normalize_remote "https://github.com/${TARGET_REPO}")"

ORIGIN_PATH="$(echo "$NORM_ORIGIN" | sed 's|.*github\.com/||')"
TARGET_PATH="$(echo "$NORM_TARGET" | sed 's|.*github\.com/||' | tr '[:upper:]' '[:lower:]')"

if [[ "$ORIGIN_PATH" == "$TARGET_PATH" ]]; then
  result "correct-repo-different-branch" "git-fetch-and-diff" \
    "Inside the target repo on branch '$CURRENT_BRANCH'. Run: git fetch origin"
  exit 0
fi

# ── 4. Possible rename — compare HEAD SHAs via ls-remote ─────────────────────
TARGET_URL="$(github_url "$TARGET_REPO")"
ORIGIN_HEAD=""
TARGET_HEAD=""

if git ls-remote "$ORIGIN_URL" HEAD >/dev/null 2>&1 \
   && git ls-remote "$TARGET_URL" HEAD >/dev/null 2>&1; then
  ORIGIN_HEAD="$(git ls-remote "$ORIGIN_URL" HEAD 2>/dev/null | awk '{print $1}')"
  TARGET_HEAD="$(git ls-remote "$TARGET_URL" HEAD 2>/dev/null | awk '{print $1}')"
  if [[ -n "$ORIGIN_HEAD" && "$ORIGIN_HEAD" == "$TARGET_HEAD" ]]; then
    result "renamed-repo" "use-local-as-is" \
      "HEAD SHAs match ($ORIGIN_HEAD) — repository was likely renamed from '$ORIGIN_PATH' to '$TARGET_PATH'. Using local checkout."
    exit 0
  fi
fi

# ── 5. Possible fork — same repo name, different owner ───────────────────────
ORIGIN_REPO_NAME="$(echo "$ORIGIN_PATH" | cut -d'/' -f2)"
TARGET_REPO_NAME="$(echo "$TARGET_PATH" | cut -d'/' -f2)"

if [[ "$ORIGIN_REPO_NAME" == "$TARGET_REPO_NAME" ]]; then
  result "possible-fork" "fetch-pr-refs" \
    "Repo names match but owners differ ('$ORIGIN_PATH' vs '$TARGET_PATH'). Try fetching PR refs from upstream or the PR URL before cloning."
  exit 0
fi

# ── 6. Unrelated repo — clone required ───────────────────────────────────────
result "different-repo" "clone" \
  "Local origin ('$ORIGIN_PATH') does not match target ('$TARGET_PATH'). Cloning is required."
exit 0
