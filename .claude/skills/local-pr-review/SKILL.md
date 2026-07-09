---
name: local-pr-review
description: Run the adversarial Claude review locally in a git worktree before a push, looping reviewer ↔ implementer until consensus. Drop-in replacement for the GitHub Actions claude-code-review run so CI runner minutes aren't burned on every PR sync. Invoked by the pre-push hook and the gh-pr-create wrapper, but also runnable as /local-pr-review.
---

# local-pr-review

Mirror of [.github/workflows/claude-code-review.yml](../../../.github/workflows/claude-code-review.yml)
run locally, in an isolated git worktree, with the implementer agent in
the same session pushing back on weak findings and fixing real ones.
Loops until reviewer and implementer agree, then fast-forwards the
original branch and exits 0 so the push proceeds.

## When to use

- Pre-push hook fires this automatically when pushing a branch that has
  an open PR (see [bin/pre_push_claude_review.sh](../../../bin/pre_push_claude_review.sh)).
- [bin/gh-pr-create-with-review.sh](../../../bin/gh-pr-create-with-review.sh)
  fires it before creating a new PR.
- Manually as `/local-pr-review` against the current branch.

## Inputs

Caller may pass `BASE_REF` and `HEAD_REF` via env. If absent:

```bash
BASE_REF=${BASE_REF:-$(git merge-base HEAD origin/main)}
HEAD_REF=${HEAD_REF:-HEAD}
BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

## Flow

### 1. Pre-flight

- Refuse to run on `main` — there's no PR concept.
- `git fetch origin main` so the merge-base is fresh.
- Show a one-line banner: `=== LOCAL ADVERSARIAL REVIEW: ${BRANCH}
  (BASE..HEAD = ${BASE_REF:0:7}..${HEAD_REF:0:7}) ===`.
- Print the bypass hint: `Bypass with CLAUDE_LOCAL_REVIEW=0 or git push
  --no-verify.`

### 2. Worktree

Reuse the worktree pattern from
[.claude/skills/resolve-my-prs/SKILL.md](../resolve-my-prs/SKILL.md):
each `Agent` call uses `isolation: "worktree"`. The worktree is
checked out to `HEAD_REF`. No manual `git worktree add` from the skill.

If the current branch is already checked out in another worktree
(`git worktree list --porcelain | grep "branch refs/heads/${BRANCH}"`
returns a path other than the current one), abort with
`blocked-active-worktree` so the user resolves by hand.

### 3. Reviewer pass

Spawn a `claude` subagent (`subagent_type: claude`, `isolation:
"worktree"`, **NOT** `run_in_background` — the loop is foreground so
the user sees each turn live). Prompt body:

```text
You are running inside an isolated git worktree off branch ${BRANCH}.
Read the adversarial reviewer prompt at .claude/prompts/adversarial_reviewer.md
and follow it exactly. The diff under review:

  git diff ${BASE_REF}..${HEAD_REF}

Iteration: ${ITER} of max ${MAX_ITER}.
Previous iterations' findings + implementer verdicts are in HISTORY.md
at the repo root of the worktree (read it before starting if it
exists — do not re-flag items already pushed back on with citation
unless the implementer's citation is itself wrong).

Output the review verbatim in the format the prompt file specifies.
Do NOT post to GitHub — this is a local run. Print to stdout only.
```

After the agent returns, append its output to `HISTORY.md` in the
worktree under `## Reviewer iteration ${ITER}`. Print the banner
`=== ITERATION ${ITER} — REVIEWER ===` followed by the agent's full
output so the user can read it live.

### 4. Convergence check

Parse the `bot-review-marker` HTML comment:

```regex
blocking=(\d+) nonblocking=(\d+) suspect=(\d+)
```

If `blocking == 0` AND `nonblocking == 0` (suspect items are advisory):
**converged**. Print `=== CONVERGED at iteration ${ITER} ===`, jump to
step 6.

If the reviewer's findings are byte-identical to the previous
iteration's findings: **stable disagreement**. Print the unresolved
list and exit with status 2 so the hook surfaces it to the user
("reviewer and implementer can't agree — review the report and decide
whether to bypass").

### 5. Implementer pass

Spawn a second `claude` subagent in the same worktree. Prompt body:

```text
You are running inside an isolated git worktree off branch ${BRANCH}.
Read the adversarial implementer prompt at
.claude/prompts/adversarial_implementer.md and follow it exactly.

The reviewer's findings for this iteration are in HISTORY.md under
"## Reviewer iteration ${ITER}". Walk each finding, decide
fix/already-fixed/push-back per the prompt's verdict table, and edit
files in this worktree for every "fix" verdict. Do NOT commit — the
orchestrator will amend the loop's work into a single commit at the
end.

Output the verdict report verbatim and append it to HISTORY.md under
"## Implementer iteration ${ITER}". Print to stdout for the user.
```

Print `=== ITERATION ${ITER} — IMPLEMENTER ===` banner. Increment
`ITER` and loop to step 3.

### 6. Hard cap

`MAX_ITER = 5`. If reached without convergence, print the outstanding
findings and exit with status 2. Do not loop forever — the user can
inspect, decide, and re-push.

### 7. Settling the worktree back into the original branch

When converged:

1. In the worktree, stage every edit the implementer made:
   `git add -A`.
2. If the worktree's index is non-empty, amend onto a single fixup
   commit: `git commit --no-verify -m "fixup! adversarial review
   iteration loop"`. (`--no-verify` is intentional here — pre-commit
   hooks are about *intent*, this commit is a mechanical re-shape of
   the diff the user is about to push.)
3. Back in the main checkout, fast-forward `${BRANCH}` to the
   worktree's HEAD: `git fetch <worktree-path> HEAD:${BRANCH}` (or
   `git update-ref refs/heads/${BRANCH} <new-sha>` if the main
   checkout is on a different branch).
4. If the implementer made no edits in any iteration (clean pass on
   the first reviewer round), skip the fixup commit and the
   fast-forward — nothing to settle.
5. Print `=== LOCAL REVIEW PASSED — push proceeding ===` and exit 0.

## Bypass channels

- `CLAUDE_LOCAL_REVIEW=0` env — skill exits 0 immediately when set.
  The pre-push hook short-circuits before calling the skill, so this
  is the fast path.
- `git push --no-verify` — pre-commit framework skips the hook entirely.
- Skill caller may pass `LOCAL_REVIEW_MAX_ITER=N` to override the cap.

## Outputs

- Exit 0 → converged (or bypassed), push proceeds.
- Exit 2 → unresolved findings, push aborted, user decides next step.
- Exit non-zero non-2 → setup error (no worktree, no `claude` binary,
  etc.) — pre-push hook surfaces with a clear message.

## Ground rules

- **Foreground only.** Never `run_in_background`. The user must see
  each iteration as it happens.
- **The skill does not push.** It returns control to the pre-push
  hook (or wrapper), which pushes only if the skill exited 0.
- **The skill does not post to GitHub.** The matching workflow run
  will still fire on the actual push; this is local-only.
- **One commit max.** Don't litter the branch with per-iteration
  commits — fold all implementer edits into one fixup at the end.
- **Honour the standing conventions in [.claude/prompts/adversarial_implementer.md](../../prompts/adversarial_implementer.md).**
  Reviewer suggestions that contradict them must be pushed back, not
  capitulated to.

## See also

- [.claude/prompts/adversarial_reviewer.md](../../prompts/adversarial_reviewer.md) — reviewer prompt body (single source of truth)
- [.claude/prompts/adversarial_implementer.md](../../prompts/adversarial_implementer.md) — implementer prompt body
- [bin/pre_push_claude_review.sh](../../../bin/pre_push_claude_review.sh) — pre-push hook caller
- [bin/gh-pr-create-with-review.sh](../../../bin/gh-pr-create-with-review.sh) — `gh pr create` wrapper
- [.github/workflows/claude-code-review.yml](../../../.github/workflows/claude-code-review.yml) — the CI workflow this mirrors
