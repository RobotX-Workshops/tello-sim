# PR Resolution Workflow

Agent-agnostic contract for driving open pull requests to a mergeable
state: resolve every review thread, keep CI honest, report a merge order.

This document owns **orchestration**. Per-PR mechanics — auth, pre-push
gate, CI triggers, the review-thread verdict table, conflict resolution —
live in [AGENTS.md](../../AGENTS.md) and are not restated here. Agent
adapters (e.g. `.claude/skills/resolve-my-prs/SKILL.md`,
`.claude/skills/resolve-pr/SKILL.md`) map their runtime onto this
document and add nothing of their own.

## Scope

- **Only open PRs authored by `$ME`** (per AGENTS.md §1). Never widened.
- **Every review thread counts**, whatever the author — CodeRabbit,
  Copilot, `claude[bot]`, humans.
- **Never merge.** These flows leave PRs mergeable and report a
  recommended order. The human merges.
- **Never wait on CI.** Push and move on; a circle-back round picks up
  the results.

## Bulk PR Flow

### Pre-flight (orchestrator, once)

The orchestrator stays in the main checkout and runs read-only commands
only. It never edits a branch itself.

1. Auth and identity per AGENTS.md §1 (`$ME`, `$OWNER`, `$REPO`).

2. Enumerate the queue:

   ```bash
   gh pr list --author "$ME" --state open --limit 500 \
     --json number,title,headRefName,isDraft,mergeable,reviewDecision
   ```

3. Refresh the base once so every worker's worktree is current:

   ```bash
   git fetch origin main
   ```

4. Record `ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)` to restore
   at the end. On a detached HEAD this yields the literal `HEAD`; guard
   the restore against that.

5. Apply the worktree-collision rule (below) to each PR.

6. If the queue exceeds `MAX_CONCURRENT`, print
   `Dispatching N PRs in batches of <MAX_CONCURRENT>` so the pacing is
   visible.

### Worktree-collision rule

```bash
git worktree list --porcelain
```

A PR whose head branch is already checked out elsewhere on this machine
is **skipped** with outcome `blocked-active-worktree`. Fighting a live
checkout — the user's or another agent's — is worse than skipping.

Exception: the orchestrator may direct a worker to **reuse** a specific
existing worktree when that worktree is clean (`git status --porcelain`
empty). It then passes the absolute path as `REUSE_WORKTREE` and the
worker works there instead of creating one. A dirty worktree is never
reused — it is a collision.

### Dispatch

- `MAX_CONCURRENT = 4`. Dispatch at most 4 workers at once; on each
  completion, backfill one from the queue until it drains.
  Rationale: an unbounded burst has previously exhausted the session
  budget mid-run and saturated local I/O. If session-limit errors still
  appear, lower the cap — never raise it.
- Each worker runs in an isolated worktree off `origin/main` (or in its
  assigned `REUSE_WORKTREE`).
- Workers run in the background; the orchestrator collects completion
  notifications rather than polling.

### Between dispatch and reporting

- Do not poll workers.
- Do not check CI on their behalf. Each worker returns without waiting.
- Backfill on every completion until the queue is empty.
- When all workers have reported, run Cleanup, then Final Reporting.

## Single-PR Flow

Same contract, one PR, no fan-out:

1. Pre-flight steps 1, 3, 4 above for the single PR number.
2. Apply the worktree-collision rule. A collision here is fatal, not a
   skip — report it and stop so the user can resolve by hand.
3. Dispatch one worker, synchronously, so the user watches it live.
4. Circle back synchronously as well.
5. Skip cleanup on any `blocked-<reason>` outcome so the worktree
   survives for inspection.

## Per-PR Worker Contract

A worker owns exactly one PR. It reads AGENTS.md and follows it directly.

### Phase 0 — bind identity

Re-derive `$ME`, `$OWNER`, `$REPO` per AGENTS.md §1 inside the worker's
own shell. Do not rely on values the orchestrator interpolated into prose.

### Phase 1 — check out and rebase

```bash
gh pr checkout "$PR"
git fetch origin main
git rebase origin/main        # conflicts: AGENTS.md §6
```

### Phase 2 — read the whole picture

- `gh pr view "$PR" --comments` — body, timeline, review summaries.
- `gh pr diff "$PR"` — what the PR actually changes.
- Enumerate unresolved threads (AGENTS.md §5 Step 1).
- Check CI: `gh pr view "$PR" --json statusCheckRollup`.

Read failing-check logs before theorising:
`gh run view <run-id> --log-failed`.

### Phase 3 — resolve

Work AGENTS.md §5 Steps 2–6 end to end: assess each thread against the
verdict table, fix or push back, commit, reply, resolve, then **verify
zero unresolved threads**.

Fix genuinely failing CI that is caused by this PR. A check that is red
for a reason outside the PR's diff (broken workflow on `main`, missing
secret, an unrelated infra failure) is **not** the worker's to fix —
report it in `Notes` and carry on. Never edit a workflow outside the
PR's stated scope to turn a check green.

### Phase 4 — push

Pre-push gate per AGENTS.md §2, then push per §2.1
(`--force-with-lease` after any rebase or amend). Push unconditionally
after a rebase; do not try to detect a no-op.

Return immediately after pushing. Do not wait for the new CI round or
for the bots to re-review.

### Phase 5 — report

Return exactly this block, ≤250 words:

```text
PR: #<number>
Outcome: <resolved | resolved-noop | blocked-active-worktree | blocked-ambiguous | blocked-<reason>>
Branch: <head branch>
SHA: <pushed sha, or '-' if nothing was pushed>
Threads: <N resolved, M pushed-back, K left open>
CI: <state at hand-off, e.g. 'gate red — pre-existing, see Notes'>
Worktree: <absolute path from `git rev-parse --show-toplevel`>
Local branches: <comma-separated branches created, or '-'>
Notes: <one line for the summary; for blocked-*, the "what I'd need to know">
```

Outcome vocabulary:

| Outcome | Meaning |
| --- | --- |
| `resolved` | Threads addressed and/or fixes pushed |
| `resolved-noop` | Nothing to do — no unresolved threads, rebase clean |
| `blocked-active-worktree` | Head branch checked out elsewhere; skipped |
| `blocked-ambiguous` | Needs a user decision; question stated in `Notes` |
| `blocked-<reason>` | Any other hard stop, reason named |

`Worktree` and `Local branches` drive Cleanup and must be populated on
every outcome, including no-ops.

## Circle-back rounds

After the first pass, a pushed PR has a fresh CI round and possibly new
bot findings. A circle-back worker re-runs the Per-PR Worker Contract
against the new state.

The orchestrator passes the previous pushed SHA:

```text
Previous push SHA for this PR: ${PREV_SHA}.
```

The worker uses it to distinguish the CI run for *its* push from a stale
run for an earlier SHA:

```bash
gh run list --commit "$PREV_SHA" --json databaseId,name,conclusion,status
```

Stop circling back on a PR when a round produces `resolved-noop`, or
after **2** circle-back rounds — whichever comes first. A PR still
contested after that is reported as-is; a human decides.

## Cleanup

**All-or-nothing.** Run the reaping step only when **no** PR in the run
ended `blocked-<reason>` (any blocked variant, including
`blocked-active-worktree`). A blocked PR means the user needs to `cd`
into a worktree and finish by hand, and a partial sweep is more confusing
than none.

Discovery:

```bash
git worktree list --porcelain
git branch --merged origin/main
```

Never reap a worktree the orchestrator was told to reuse but did not
create, and never reap the main checkout.

When the run is fully clean, per reported worktree:

```bash
git worktree unlock "$WORKTREE" 2>/dev/null || true
git worktree remove --force "$WORKTREE" 2>/dev/null || true
# then each name from `Local branches`:
git branch -D -- "$b" 2>/dev/null || true
```

Every command is best-effort — a cleanup failure must never abort the
run. Finish with `git worktree prune || true` and print:

```text
🧹 Cleaned <N> worktrees, <M> branches (kept <K> for blocked PRs).
```

When reaping is skipped, say so and list what survived, one line per
blocked PR, so the kept worktrees are actionable rather than merely
counted:

```text
🧹 Cleanup skipped — <K> worktrees kept for blocked PRs:
  #<n> <branch> — <absolute worktree path>
```

## Final Reporting

Restore `ORIGINAL_BRANCH` (skipping the restore if it is the literal
`HEAD`), then report.

Unlike issues, PRs have a real ordering — report a **merge order**, not
just a summary.

1. **Merge order** — ready PRs, most-mergeable first. One line each:
   `#<n> <branch> — <one-line scope>`. Order by:
   - dependency first (a PR fixing CI or tooling that other PRs' checks
     depend on goes ahead of its dependents, and say why);
   - then smallest / lowest-risk diff;
   - then oldest.
   State any ordering constraint explicitly — an implicit order gets
   merged out of sequence.
2. **Blocked** — every `blocked-*` outcome with the worker's "what I'd
   need to know" quoted verbatim, plus that worker's absolute `Worktree`
   path and its `Local branches`. Cleanup was skipped, so these worktrees
   are still on disk and the path is the only way the user can `cd` in and
   finish by hand. Reporting the reason without the path leaves them
   hunting through `git worktree list`.
3. **Left open** — threads deliberately left unresolved, with the PR and
   the question.
4. **CI caveats** — checks red for reasons outside any PR's scope, so the
   user is not surprised at merge time.

Never claim a PR is mergeable without having verified zero unresolved
threads (AGENTS.md §5 Step 6).

## See also

- [AGENTS.md](../../AGENTS.md) — per-PR mechanics (§1 auth, §2 pre-push, §3 CI, §5 threads, §6 conflicts)
- [docs/claude_code_review.md](../claude_code_review.md) — review bot and gate setup
