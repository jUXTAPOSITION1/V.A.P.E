#!/usr/bin/env bash
# Commit whatever a scheduled VAPE workflow produced and get it onto the branch.
#
# Usage:  scripts/ci_commit_push.sh "<commit message>" <path> [path...]
# Env:    GITHUB_TOKEN (required)  GITHUB_REPOSITORY  GITHUB_REF_NAME
#
# Replaces the inline retry loop that every cycle workflow used to carry. That
# loop failed the whole job on 2026-07-26 despite the cycle itself succeeding,
# and it did so for a structural reason worth spelling out:
#
#   git pull --rebase   ->  conflict in a machine-written memory ledger
#                       ->  rebase stops, runner is left on a DETACHED HEAD
#   git push            ->  "fatal: You are not currently on a branch"
#   ...retry            ->  `git rebase --abort`, pull again, identical
#                           conflict, identical failure. Five times.
#
# Retrying a deterministic conflict can never succeed, so the retry budget was
# spent proving that. Two changes fix it:
#
#   1. Most of those conflicts aren't real. .gitattributes now teaches git how
#      to merge the append-only ledgers (`union`) and the JSON state blobs
#      (the driver registered below), so they resolve automatically.
#   2. When a conflict IS real, this aborts cleanly, restores the branch, and
#      reports it — instead of limping on detached HEAD and burning retries.
#
# Retries remain, but only for what they were ever good for: a genuine push
# race, where another job pushed between our fetch and our push.
set -euo pipefail

MESSAGE="${1:?usage: ci_commit_push.sh <message> <path> [path...]}"
shift
PATHS=("$@")
[ ${#PATHS[@]} -gt 0 ] || { echo "::error::no paths given to commit"; exit 2; }

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required to push}"
REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
BRANCH="${GITHUB_REF_NAME:-main}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

git config user.name "VAPE Bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# Register the JSON-state merge driver named in .gitattributes. Without this
# git silently ignores `merge=json-state` and falls back to a conflicting text
# merge — safe, but it would re-introduce the exact failure above.
git config merge.json-state.name "VAPE JSON state merge (newest ts per key wins)"
git config merge.json-state.driver "python3 '$REPO_ROOT/scripts/git_merge_json_state.py' %O %A %B"

# checkout@v7 can leave HEAD detached; committing there would strand the work.
if ! git symbolic-ref -q HEAD >/dev/null; then
  echo "[commit-push] HEAD is detached — reattaching to $BRANCH"
  git checkout -B "$BRANCH"
fi

git add -- "${PATHS[@]}" || true
if git diff --cached --quiet; then
  echo "[commit-push] nothing to commit"
  exit 0
fi
git commit -m "$MESSAGE"

# persist-credentials:false on checkout (see #157) means push has no credential
# unless it is re-injected here, scoped to this step only.
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"

for attempt in 1 2 3 4 5; do
  git fetch origin "$BRANCH"

  if ! git rebase "origin/$BRANCH"; then
    # A conflict git could not resolve even with .gitattributes in play. That
    # means a file we have no automatic policy for — treat it as real.
    conflicted="$(git diff --name-only --diff-filter=U || true)"
    echo "::error::unresolved conflict while rebasing onto origin/$BRANCH:"
    echo "$conflicted" | sed 's/^/  /'
    git rebase --abort || true
    # Leave the branch usable and the commit intact for the next scheduled run
    # rather than exiting mid-rebase on a detached HEAD.
    git checkout -B "$BRANCH" >/dev/null 2>&1 || true
    echo "::error::a human needs to resolve this; the commit is NOT pushed"
    exit 1
  fi

  if git push origin "HEAD:refs/heads/$BRANCH"; then
    echo "[commit-push] pushed on attempt $attempt"
    exit 0
  fi

  # Only a genuine push race gets here (someone pushed between our fetch and
  # our push), which a re-fetch/rebase really can fix.
  echo "[commit-push] push race, retry $attempt"
  sleep $((attempt * 3))
done

echo "::error::failed to push after 5 attempts -- changes were NOT pushed"
exit 1
