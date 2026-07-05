# Skill: Shipping a Change — Branch, Verify, Commit, PR, Merge

**Tier:** coding · **Status:** active

## When to use
Every change to this repo that isn't a direct-commit CI job
(`skillforge-harvest`/`toolcheck`/reputation-style pure-data updates, per
`skillforge/MANIFEST.md`'s commit policy). Anything touching code, the site,
or agent logic goes through this flow.

## Procedure (reproducible, grounded in this session's real workflow)

1. **Branch from current `main`, not from an old checkout.**
   `git fetch origin main && git checkout -B <branch> origin/main`. If a
   previous branch with the same name already has a merged PR behind it,
   don't stack new work on the stale branch — rebuild from current `main`
   and reapply just the new diff (see step 5).

2. **Make the change, then verify it yourself before asking anyone else to.**
   See the `coding-verification` skill for the exact checks — syntax,
   structure, headless-browser smoke test. Don't skip this because "it's a
   small change" — small changes are exactly the ones nobody double-checks
   otherwise.

3. **Write a commit message that explains *why*, not just *what*.** The diff
   already shows what changed; a good message says what problem it solves
   and any non-obvious reasoning (see this repo's commit history for the
   pattern — e.g. explaining *why* `escapeHtml()` was needed around a URL
   that was "already safe" at runtime).

4. **Push and open a PR against `main` — don't merge your own PR blindly.**
   Wait for the repo's actual CI signal (the `deploy/...` status check that
   confirms the site/worker still builds) before merging. A third-party
   advisory bot (e.g. CodeRabbit) that's still "in progress" after several
   minutes is not a merge gate — it's not required, and blocking
   indefinitely on a slow non-required check delays real fixes for no
   safety benefit. The real gate is the build/deploy check.

5. **Recognize and recover from squash-merge false conflicts.** If a PR
   shows `mergeable_state: "dirty"` but you're confident the actual file
   content doesn't conflict, check: `git diff <old_branch_commit>
   <main's_squashed_commit_with_same_title>` — if that diff is empty, this
   is the false-conflict case (the branch's history still has the
   pre-squash commit as an ancestor, different SHA, identical content).
   Recovery: extract the *new* commits' diff with `git diff
   <old_base>..<branch_head> --binary > /tmp/patch`, rebuild the branch
   fresh off current `origin/main`, `git apply /tmp/patch`, verify, commit,
   `git push --force-with-lease`. Never `--force` without `--with-lease` —
   the lease check aborts if someone else pushed to the branch in the
   meantime, protecting against clobbering unseen work.

6. **After merging, confirm the deploy actually landed — don't assume.**
   A merge succeeding on GitHub doesn't mean the site updated. Check the
   actual `pages build and deployment` (or equivalent) workflow run for that
   commit SHA. If it fails with a transient infrastructure error (e.g.
   GitHub's own "Deployment failed, try again later" with the *build* step
   having already succeeded), that's not a content bug — re-run just the
   failed job rather than re-diagnosing the code.

## Quality gates
- Never `git push --force` (without `--with-lease`) to a shared branch.
- Never skip the verification step in #2 "because CI will catch it" — CI in
  this repo checks that the site *builds*, not that a specific new feature
  *works*; logic verification is on you before the PR ever opens.
- Only merge a PR yourself when either explicitly asked to, or when the
  session's established pattern already covers it (e.g. "yes proceed" on a
  prior turn extending to a same-shaped follow-up) — otherwise flag it and
  let the human merge.

## Known limitations
- This flow assumes solo authorship on the branch. If two agents (or an
  agent and a human) push to the same branch concurrently, `--force-with-
  lease` will correctly reject a stale push, but resolving the actual
  conflict still needs a human decision about which changes win.

_Written for skillforge/memory/build_log.jsonl's coding-education track —
see skillforge/memory/BUILD_LEDGER.md._
