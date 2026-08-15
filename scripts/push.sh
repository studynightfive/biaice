#!/usr/bin/env bash
# Member-6 push script (POSIX)
#
# Pushes the feature/m6-simulation branch to GitHub.
#
# Configure ONE of these before running:
#   1. export BIAICE_PUSH_TOKEN=ghp_xxx      (PAT, scopes: repo + workflow)
#   2. gh auth login                         (uses GCM)
#   3. configure a custom remote via BIAICE_REMOTE_URL
#
# Usage:
#   ./scripts/push.sh
#   BIAICE_REMOTE_URL=https://github.com/me/biaice-m6.git ./scripts/push.sh
#   BRANCH=my-fork ./scripts/push.sh
#
# Re-running is safe: remote URL is updated, working-tree check is enforced.

set -euo pipefail

BRANCH="${BRANCH:-feature/m6-simulation}"
DEFAULT_REMOTE="https://github.com/studynightfive/biaice.git"
REMOTE_URL="${BIAICE_REMOTE_URL:-$DEFAULT_REMOTE}"

if [[ -n "${BIAICE_PUSH_TOKEN:-}" ]]; then
    AUTH_REMOTE="$(echo "$REMOTE_URL" | sed -E "s#https://#https://x-access-token:${BIAICE_PUSH_TOKEN}@#")"
else
    AUTH_REMOTE="$REMOTE_URL"
fi

echo "[m6] branch    : $BRANCH"
echo "[m6] remote    : $REMOTE_URL"
if [[ -n "${BIAICE_PUSH_TOKEN:-}" ]]; then
    echo "[m6] auth      : PAT via URL"
else
    echo "[m6] auth      : git credential helper"
fi

current=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current" != "$BRANCH" ]]; then
    echo "[m6] error: not on $BRANCH (currently on $current)" >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "[m6] error: working tree is dirty" >&2
    git status --short >&2
    exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$AUTH_REMOTE"
else
    git remote set-url origin "$AUTH_REMOTE"
fi

git push -u origin "$BRANCH"

baseUrl=$(echo "$REMOTE_URL" | sed -E "s#\.git$##")
compareUrl="$baseUrl/compare/main...$BRANCH?expand=1"

cat <<MSG
[m6] pushed. Open a PR at:
[m6]   $compareUrl
[m6] Paste docs/delivery/pr-body.md as the PR description.
MSG
