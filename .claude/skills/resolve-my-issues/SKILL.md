---
name: resolve-my-issues
description: Walk every open GitHub issue authored by the current user, fan out one Agent per issue in its own git worktree; each resumes any in-flight PR or stray branch, or implements the fix fresh, and opens a ready-for-review PR with `Closes #N` when none yet exists. Pipelined dispatch loop — push and move on, don't block on CI.
---

# resolve-my-issues

Dispatch loop for grinding through a backlog of your open issues in this repo. The outer orchestrator enumerates the queue and **fans out one Agent per issue in parallel, each in its own git worktree**; each agent resumes any in-flight PR or stray branch, or implements the fix fresh, then opens or pushes a ready-for-review PR with `Closes #<N>` in the body so the standing adversarial review loop (CodeRabbit + Claude Code review workflow) kicks in immediately. The outer orchestrator only does enumeration, dispatch, and final reporting — it never touches branches itself.

This skill is the **outer orchestration**. Per-issue mechanics (auth, pre-push gate, CI triggers by path, conflict resolution, comment-resolution verdict table for any review feedback the agent receives mid-flight) live in [AGENTS.md](../../../AGENTS.md) and [CLAUDE.md](../../../CLAUDE.md) and must not be duplicated here — when AGENTS.md is updated, this skill must follow the updated commands. Companion to [resolve-my-prs](../resolve-my-prs/SKILL.md): same fan-out shape, the input queue is open issues instead of open PRs; the per-agent terminal action is `gh pr create` (fresh path) or `git push --force-with-lease` (resume path).

## When to use

- Invoked manually as `/resolve-my-issues` when you want to grind through your open-issue backlog in one sitting.
- Not for one-off issue work. If you're implementing a single ticket, do that in plain conversation. The overhead of the dispatch loop only pays off when there are several issues to work in parallel.

## Scope (hard limits)

- **Only issues authored by the current GitHub user.** Determined by `gh api user -q .login` at the start of the run and never widened.
- **Only open issues.**
- **Resume in-flight work when found.** If a PR is in flight that closes the issue (via `closingIssuesReferences`), the agent checks out that PR, rebases on `origin/main`, finishes any missing implementation, and processes open review threads (per `/resolve-my-prs` + AGENTS.md §5). If there is no linked PR but a branch matching `issue-${N}-*` exists on `origin`, the agent rebases it, finishes the work, and opens the PR. Only worktree collisions (the branch is already checked out elsewhere on this machine) cause a skip.
- **Each agent branches from `origin/main`.** Never branch off an unrelated feature branch.
- **Always `--force-with-lease` if a push ever rewrites history.** Never plain `--force`. (First-pass `git push -u` is non-rewriting and doesn't need `--force-with-lease`.)
- **Never bypass checks.** No `--no-verify`, no disabling lint rules, no skipping/deleting tests to make CI green. Fix the underlying issue.

## Pre-flight (once per invocation, in the outer orchestrator)

The outer orchestrator stays in the main checkout. It only runs read-only `gh` and `git` commands. Per-issue worktrees are created by each fanned-out Agent via `isolation: "worktree"` — the orchestrator does **not** create them itself.

Parallel fan-out is the only mode this skill describes. If a user explicitly asks for sequential processing, ignore the skill and process the queue one issue at a time in plain conversation — the per-issue template below is parameterised for a single `${N}` and would need rewriting to drive a loop.

1. Auth — per [AGENTS.md §1](../../../AGENTS.md):

   ```bash
   gh auth status
   ```

2. Identify yourself and lock the author scope:

   ```bash
   ME=$(gh api user -q .login)
   ```

3. Derive the repo slug from git context once so every downstream `gh api` call has explicit `OWNER` / `REPO` strings (`gh pr list` / `gh issue list` auto-derive, but `gh api repos/...` needs them spelled out):

   ```bash
   OWNER=$(gh repo view --json owner -q .owner.login)
   REPO=$(gh repo view --json name  -q .name)
   ```

4. Pull the candidate queue using the locked `$ME` scope. Prefer `gh issue list` over `gh api search/issues` — the Search API caps results at 1000 regardless of pagination and lags behind index updates, while `gh issue list` hits the REST issues endpoint directly (no cap, no indexing lag):

   ```bash
   gh issue list --author "$ME" --state open --limit 1000 \
     --json number,title,url,labels,body
   ```

   Use `$ME` consistently rather than `@me` — `@me` resolves at request time and could drift if auth context changes mid-run.

5. Annotate (do **not** drop) issues with an open PR already targeting them. The canonical edge lives on the PR side as `closingIssuesReferences`:

   ```bash
   gh pr list --state open --limit 500 \
     --json number,url,headRefName,closingIssuesReferences \
     --jq '[.[] | {prNumber: .number, prUrl: .url, prHead: .headRefName,
                   issueNumbers: [.closingIssuesReferences[].number]}]'
   ```

   Build an `issue → {prNumber, prUrl, prHead}` map from that output (any issue listed in `issueNumbers` is closed-by that PR). For each such issue, attach `EXISTING_PR_NUMBER`, `EXISTING_PR_URL`, `EXISTING_PR_HEAD` to the queue item so the per-issue Agent receives them in its prompt and resumes that PR instead of opening a new one. **Do not** flatten to a bare number list — the URL and head ref must survive into the prompt.

6. For each remaining queue item with no linked open PR, look for a stray remote branch matching `issue-${N}-*` (a previous run that pushed but never opened the PR, or a hand-pushed WIP):

   ```bash
   git ls-remote --heads origin "issue-${N}-*" \
     | awk '{print $2}' | sed 's|refs/heads/||'
   ```

   - Zero matches → no annotation; the agent will branch fresh from `origin/main`.
   - Exactly one match → attach `EXISTING_BRANCH=<name>` to the queue item.
   - Multiple matches → pick the most recent by commit date. Since step 7 only fetches `main`, the remote-tracking refs for these branches don't exist locally yet, so `git for-each-ref` would silently return nothing. Fetch the matching branches first, then sort:

     ```bash
     git fetch origin --no-tags "+refs/heads/issue-${N}-*:refs/remotes/origin/issue-${N}-*"
     ALL=$(git for-each-ref --sort=-committerdate \
       --format='%(refname:short)' "refs/remotes/origin/issue-${N}-*" \
       | sed 's|origin/||')
     # Note: --sort=-committerdate reflects when commits were locally created/rebased.
     # For force-pushed branches, this is equivalent to the most recent push time
     # (a rebase always produces new commit objects with a fresh committer date),
     # so it reliably picks the most recently worked branch in this workflow.
     BEST=$(echo "$ALL" | head -1)
     OTHERS=$(echo "$ALL" | tail -n +2 | paste -sd ',')   # comma-joined
     ```

     Attach `$BEST` as `EXISTING_BRANCH`, `RESUME_HINT=multiple-branches-found`, and `EXISTING_BRANCH_OTHERS=$OTHERS` (comma-separated names of the non-picked branches) so the agent can surface the discarded names in its report. The orchestrator owns the enumeration — the agent must NOT independently re-run `git ls-remote` to recover them.

7. Refresh `main` once up front so each agent's worktree base is fresh:

   ```bash
   git fetch origin main
   ```

8. Remember where you started — `ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)` — so you can return at the end. Note that on a detached HEAD this returns the literal string `HEAD`; the restore step below guards against that.

## Parallel fan-out (one Agent per issue, capped concurrency)

After the queue is enumerated and filtered, **fan out**: send a message containing up to `MAX_CONCURRENT` `Agent` tool calls. Each call MUST include:

- `subagent_type: "general-purpose"`
- `isolation: "worktree"` — each agent gets its own worktree off `origin/main`
- `run_in_background: true` — **critical**. Without this, multiple `Agent` calls in one message run concurrently but the orchestrator's turn blocks until every one returns synchronously. With `run_in_background: true`, each agent fires a completion notification when done; the orchestrator's turn ends immediately after dispatch and is re-invoked on each completion. The notification model is what enables the "push and move on" semantics and lets the orchestrator interleave other work while agents grind.

**Concurrency cap: `MAX_CONCURRENT = 4`.** Dispatch at most 4 Agent calls in the first message. On each completion notification, if the queue still has items, dispatch one replacement Agent so the in-flight count stays ≈4 until the queue drains. The notification-driven backfill preserves "push and move on" — no polling, no sleep. **Rationale:** an unbounded 17-issue / 10-PR burst dispatch previously exhausted the Anthropic session budget mid-run (9 of 10 PR agents returned the `You've hit your session limit` sentinel) and saturated the laptop's worktree / I/O. If session-limit errors still occur with cap=4, lower it further rather than raising it. Pre-flight heads-up: when the filtered queue exceeds `MAX_CONCURRENT`, the orchestrator prints `"Dispatching N items in batches of <MAX_CONCURRENT> — will take ~X minutes"` (interpolating the actual cap value) so the user knows the run is paced and the message stays correct if the cap is ever lowered.

The orchestrator's job after fan-out: wait for each completion notification, dispatch a replacement Agent if any items remain in the queue, accumulate the per-issue reports, and once all agents have reported, print the dispatch summary. It does **not** touch any branch itself.

### Worktree-collision rule

Before dispatching, run `git worktree list --porcelain` and skip any issue whose target branch is already checked out elsewhere on this machine. The target branch is `EXISTING_PR_HEAD` if set, else `EXISTING_BRANCH` if set, else any branch matching `issue-${N}-*` (fresh-branch case — defensive). Mark `blocked-active-worktree` in the final report. Fanning out an agent that fights with the user's live edits is worse than skipping.

### Per-issue Agent prompt template

Each fanned-out Agent receives a prompt built from this template, with `${N}`, `${TITLE}`, `${ISSUE_URL}`, `${ME}`, `${OWNER}/${REPO}` filled in by the outer orchestrator. The orchestrator also substitutes the resume-related placeholders — any of which may be empty when the issue has no in-flight work: `${EXISTING_PR_NUMBER}`, `${EXISTING_PR_URL}`, `${EXISTING_PR_HEAD}`, `${EXISTING_BRANCH}`, `${EXISTING_BRANCH_OTHERS}` (comma-separated names of `issue-${N}-*` branches the orchestrator detected but did NOT pick — empty unless `RESUME_HINT=multiple-branches-found`), `${RESUME_HINT}` (e.g. `multiple-branches-found`).

```text
You are processing a single open GitHub issue (#${N}, "${TITLE}",
${ISSUE_URL}) for user `${ME}` in repo `${OWNER}/${REPO}`. You are
running in a fresh git worktree off origin/main (created by
isolation: "worktree"). Your goal is to implement the change the issue
asks for and open a ready-for-review PR with `Closes #${N}` in the body,
or — when the orchestrator has detected in-flight work — to resume an
existing PR or stray branch instead of opening a new one (see Phase 2b).

Read these BEFORE doing anything — they own all per-issue mechanics:
- AGENTS.md §1 (auth), §2 (pre-push: source ROS, run pre-commit, targeted
  colcon test; concurrent-push gate inapplicable — see Phase 3 comment
  before `git push -u`), §3 (CI workflows + which fire for which paths),
  §6 (conflict resolution).
- CLAUDE.md — full project reference: topic namespacing, package layout,
  hardware, sensor fusion, control modes, and the "Adversarial Code
  Review" section (which governs how to handle any review feedback your
  PR receives mid-flight).
- CONTRIBUTING.md — coding conventions and the language-choice rule
  (runtime nodes reachable from car.launch.py are C++ / rclcpp /
  ament_cmake; ament_python is for off-car tooling only).

This prompt does NOT restate the commands in AGENTS.md. Follow them
directly from the source so you stay in sync with future edits.

Phase 0 — re-derive shell variables.
  The outer orchestrator substituted the brace-form `${ME}`, `${OWNER}`,
  `${REPO}` placeholders into this prompt, but several shell snippets
  below still reference `$ME` / `$OWNER` / `$REPO` as live shell
  variables (passed via `jq --arg`, used inside URLs, etc.). Re-bind
  them in your shell so both forms behave identically regardless of
  what the orchestrator literally substituted:
    ME=$(gh api user -q .login)
    OWNER=$(gh repo view --json owner -q .owner.login)
    REPO=$(gh repo view --json name  -q .name)

Phase 1 — understand the issue.
  1. `gh issue view ${N} --comments` — read the body AND every comment.
  2. Follow every cross-reference: linked issues, linked PRs (merged or
     closed), docs paths, file:line citations. Read them in full.
  3. Identify the code paths the issue touches. Use grep / read to
     verify the issue's claims (function names, file paths, types) are
     still accurate — issues can rot between filing and pickup.
  4. If after this honest read the issue's intent is still ambiguous
     (e.g. competing interpretations, missing acceptance criteria, the
     described symptom no longer reproduces on main), STOP. Do not
     guess. Do not open a draft "best guess" PR. Return
     `blocked-ambiguous` with a one-paragraph "what I'd need to know to
     proceed" note in the report. Vapor PRs are worse than no PR.

Phase 2 — if the change is already in main.
  If your investigation reveals the issue is already addressed by code
  currently on main (commit / file:line), do NOT open a PR. Instead:
    - **Idempotency guard before posting** — same pattern as
      /resolve-my-prs: fetch recent issue comments and skip the POST if
      `${ME}` already commented an identical body in the last 60s
      (network blip after a successful POST but before the agent's ack
      lands must not double-post). Critical: pipe through a real `jq`
      invocation with `--arg me "$ME" --arg body "$BODY"` — issue bodies
      routinely contain double quotes, backticks, code fences, and
      newlines, all of which would break a `gh api --jq` filter that
      shell-interpolates `${BODY}` directly into the filter string
      (`gh api --jq` accepts only a single filter and does NOT proxy
      jq's `--arg`):
        BODY="<comment body>"
        existing=$(gh api --paginate "repos/${OWNER}/${REPO}/issues/${N}/comments?per_page=100" \
          | jq -s 'add' \
          | jq -r --arg me "$ME" --arg body "$BODY" \
              '[.[] | select(.user.login == $me and .body == $body
                and ((.created_at | fromdateiso8601) > (now - 60)))][0].html_url // empty')
        if [ -z "${existing}" ]; then
          gh issue comment ${N} --body "${BODY}"
        fi
    - Post an issue comment naming the addressing commit SHA / file:line.
    - Return `no-op-already-addressed` in the report. Do not close the
      issue — leave that call to the user.

Phase 2b — resume existing in-flight work (when applicable).
  The orchestrator may have detected pre-existing work and passed it in
  via the placeholders below. Pick exactly one branch:

  (A) ${EXISTING_PR_URL} is non-empty — an open PR already targets this
      issue. RESUME it; do NOT open a new branch.
        gh pr checkout ${EXISTING_PR_NUMBER}
        git fetch origin main
        git rebase origin/main      # On conflict: resolve markers, git add <file>, git rebase --continue (NOT git commit)
      Re-read the issue body + acceptance criteria, then read the PR's
      diff (`gh pr diff ${EXISTING_PR_NUMBER}`). Decide:
        - Implementation incomplete vs. the issue → finish the missing
          work, commit (specific paths, never `git add -A`).
        - There are open review threads (human or bot) → run the
          per-PR comment-resolution loop. The flow is owned by
          `.claude/skills/resolve-my-prs/SKILL.md` (read it as a plain
          file — do NOT invoke it as a skill; invoking it as a skill
          would fan out over ALL open PRs, not just this one) + AGENTS.md
          §5 (assess-reply-resolve verdict table + GraphQL
          resolveReviewThread mutation). Follow those directly; do NOT
          re-derive the steps here.
      Pre-push gate per AGENTS.md §2 (source ROS, run pre-commit,
      targeted colcon test). Always push after a rebase — if origin/main
      had new commits, rebase rewrote the PR's SHAs and the remote is
      diverged; even when origin/main was already an ancestor (rebase
      no-op) the push is a safe no-op too. Either way, push
      unconditionally — do not try to skip it based on a divergence
      check:
        git push --force-with-lease origin "HEAD:${EXISTING_PR_HEAD}"    # safe on rewrite AND on no-op
      Return outcome:
        - `pr-resumed` with the PR URL if you pushed new implementation
          commits or resolved review threads.
        - `pr-resumed-noop` with the PR URL if after rebase + read the
          PR is complete with no unresolved threads (rebase-only push,
          no new implementation or thread work).
        - `blocked-ambiguous` (or `blocked-<reason>`) if you encounter
          open review threads you cannot resolve without user input, or
          any other blocker (genuine ambiguous conflict, missing
          information) — include a "what I'd need to know" note in the
          report. Do not guess or paper over the blocker.
      Do NOT execute Phase 3 in this branch — the PR already exists.

  (B) ${EXISTING_BRANCH} is non-empty (and ${EXISTING_PR_URL} is empty)
      — a stray branch from a prior run / WIP push exists with no PR.
      Resume it (fetch the branch first — isolation: "worktree" only
      fetches main, so origin/${EXISTING_BRANCH} won't exist locally):

        ```bash
        BRANCH_OK=true
        git fetch origin "+refs/heads/${EXISTING_BRANCH}:refs/remotes/origin/${EXISTING_BRANCH}" \
          || { echo "Branch ${EXISTING_BRANCH} gone on remote; treating as fresh"; \
               BRANCH_OK=false; }
        if [ "$BRANCH_OK" = "true" ]; then
          git checkout -B ${EXISTING_BRANCH} origin/${EXISTING_BRANCH}
          git fetch origin main
          git rebase origin/main
        fi
        ```

      Guard semantics: if the fetch failed (branch deleted in the window
      between the orchestrator's `ls-remote` and this agent's start),
      `BRANCH_OK` is false — skip ALL remaining Phase 2b(B) steps and fall
      through to Phase 2b(C) / Phase 3 instead. This uses a sentinel
      variable (`BRANCH_OK`) that is NOT in the orchestrator's substitution
      list, so the condition survives template substitution and actually
      tracks the fetch exit status (unlike testing `${EXISTING_BRANCH}`
      directly, which would be baked to a non-empty literal and always be
      true).

      Rebase-conflict caveat: AGENTS.md §6 is a merge workflow; on rebase
      conflicts use `git add <file> && git rebase --continue` (NOT `git
      commit`).

      After the rebase completes (i.e. `BRANCH_OK=true`), do the following:

      - **Multiple-branch hint.** If `${RESUME_HINT}` equals
        `"multiple-branches-found"`, note in your final report that multiple
        `issue-${N}-*` branches existed and you picked the most recent —
        surface the non-picked branch names from `${EXISTING_BRANCH_OTHERS}`
        (already comma-separated by the orchestrator; do NOT re-derive via
        `git ls-remote`) so the user can clean up.

      - **Finish missing work.** Read the diff vs `origin/main` (`git diff
        origin/main`). Finish any missing implementation, commit specific
        paths (never `git add -A`).

      - **Pre-push gate.** Run Phase 3's pre-push gate: source ROS, run
        `pre-commit`, targeted `colcon test` on touched packages — per
        AGENTS.md §2. This is mandatory even on a rebase-only push.

      - **Push.** Always use `git push --force-with-lease` after the rebase,
        regardless of whether you think the rebase rewrote history — same
        unconditional rule as Phase 2b(A), and it eliminates the
        fast-forward-vs-divergent detection ambiguity. For the branch name,
        substitute `${EXISTING_BRANCH}` (already `issue-${N}-<existing-slug>`)
        for every literal `issue-${N}-<slug>` occurrence in Phase 3's `git
        push` and `gh pr list --head` commands — do NOT derive a fresh slug
        from the issue title or you will push to a duplicate branch.

      - **Open PR if needed.** Run the PR-creation idempotency guard from
        Phase 3 (`gh pr list --head ... --state open`). The guard already
        handles the "branch pushed previously but PR never opened" case —
        reuse it as-is.

      - **Return outcome:**
        - `branch-resumed` if you pushed new implementation commits or opened
          a PR for the first time.
        - `branch-resumed-noop` if after rebase + read the branch was already
          complete AND a PR already existed (rebase-only push + idempotent
          PR-reuse, no new implementation work). Note: if the branch was
          complete but no PR yet existed, the Phase 3 idempotency guard opens
          one — that is still `branch-resumed` (a PR was opened), not a noop.
          `branch-resumed-noop` is reserved for the edge case where an
          existing PR (unlinked via `closingIssuesReferences`) was found by
          the guard. Mirrors the `pr-resumed` / `pr-resumed-noop` split in
          Phase 2b(A) so the final report can tell the user which resumes
          were substantive.
        - `blocked-ambiguous` (or `blocked-<reason>`) if you encounter open
          review threads you cannot resolve or any other blocker that requires
          user input — include a "what I'd need to know" note in the report.

      If `BRANCH_OK=false` (fetch failed), skip all steps above and treat as
      Phase 2b(C) below.

  (C) Both placeholders empty — no resume; proceed to Phase 3 fresh.

Phase 3 — implement (fresh branch path).
  Branch naming: `issue-${N}-<slug>` where <slug> is the issue title in
  kebab-case, alphanumerics + dashes only, trimmed to ≤40 chars total
  for the branch name. Example: `issue-142-slam-amcl-lose-lock-bag`.

  Workflow:
    git checkout -b issue-${N}-<slug> origin/main
    # ...implement the change, following CONTRIBUTING.md conventions...
    # ...add/update tests where the change has testable behavior...
    git add <specific paths>      # never `git add -A`
    git commit -m "<conventional commit subject>"
    # Pre-push gate per AGENTS.md §2: source ROS, run pre-commit,
    # targeted colcon test on touched packages. The first push of a
    # never-pushed branch is not a history rewrite, so the AGENTS.md §2
    # "Detect Concurrent Commits Before --force-with-lease" subsection
    # does NOT apply here — it only fires on later amend/rebase rounds
    # when this branch is force-pushed during review resolution.
    git push -u origin issue-${N}-<slug>
    # Idempotency guard against duplicate PR creation: if a previous
    # invocation crashed after `git push -u` but before `gh pr create`
    # acked (or returned an open PR for the same head), short-circuit
    # and reuse the existing PR URL instead of opening a duplicate.
    existing_pr=$(gh pr list --head "issue-${N}-<slug>" --state open \
                    --json url -q '.[0].url')
    if [ -n "${existing_pr}" ]; then
      echo "duplicate PR for branch; reusing ${existing_pr}"
    else
    # CRITICAL: the HEREDOC body MUST start at column 0 — leading
    # whitespace would render the entire PR body as a markdown code
    # block and `Closes #${N}` would no longer be detected as a closing
    # keyword. Either keep the body at column 0 as shown below, or use
    # a tab-stripping heredoc (`<<-'EOF'` with hard-tab indents only).
gh pr create --title "<scope>: <one-line summary under 70 chars>" \
  --body "$(cat <<'EOF'
Closes #${N}

## Summary
- <bullet describing the change>

## Test plan
- [ ] <how a human verifies this works end-to-end>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
    fi

  Open the PR ready-for-review (NOT draft). The CodeRabbit + Claude
  review workflow needs a non-draft PR to fire.

Standing user conventions for this project (these are NOT in AGENTS.md
and trump bot suggestions to the contrary — push back when bots violate
them, citing this skill):
  - Required config fields must NOT have defaults — fail-fast at boot
    is intentional. Reject "add a default for safety" suggestions on
    caller-required params.
  - Editing a YAML value: change only the value line. Never strip the
    surrounding comments.
  - Vehicle dimensions (wheelbase, track, max steering) live in
    src/tron_racer_bringup/config/default/description/car.yaml. Consumer
    nodes receive them via launch-file param passing, never via literal
    duplication.
  - Runtime nodes reachable from car.launch.py are C++ (rclcpp /
    ament_cmake). ament_python is for off-car tooling only.

If `gh pr create` lands but the bots have already posted findings by
the time you would return, do NOT loop into addressing them in this
run. Open-issue dispatch and per-PR review resolution are separate
phases — the user runs /resolve-my-prs afterwards to grind review
feedback. Return immediately so the orchestrator can move on. The same
"no waiting on CI" rule from resolve-my-prs applies here.

If anything along the way blocks progress in a way you can't resolve
without user input (genuine ambiguous conflict in dependencies you had
to touch, a missing secret, a required external API key, an
upstream-submodule decision), STOP and return `blocked-<reason>` with
the specific file:line / failing command / question the user needs to
answer. Do not paper over blockers.

Return EXACTLY this report shape (one fenced block, ≤250 words):
  Issue: #${N}
  Outcome: <pr-opened | pr-resumed | pr-resumed-noop | branch-resumed |
            branch-resumed-noop | no-op-already-addressed |
            blocked-ambiguous | blocked-<reason>>
  PR: <PR URL or '-'>
  Branch: <branch name or '-'>
  SHA: <pushed sha or '-'>
  Worktree: <absolute path from `git rev-parse --show-toplevel` inside this agent's worktree>
  Local branches: <comma-separated list of local branches you created (typically the same as `Branch`), or '-'>
  Notes: <one line for the orchestrator's final dispatch summary; for
         blocked-ambiguous, this is the "what I'd need to know" prompt>

The `Worktree` and `Local branches` fields drive the orchestrator's
post-fan-out Cleanup pass — without them it cannot reap the worktree the
harness created for you. Always populate both, even on `no-op` outcomes.
```

### What the outer orchestrator does between fan-out and reporting

- Do **not** poll the agents. With `run_in_background: true` on every dispatch (see above), each agent fires a completion notification when done and the orchestrator's turn is re-invoked.
- **On each completion notification, if the queue still has issues, dispatch one replacement Agent** before accumulating the report, so the in-flight count stays ≈`MAX_CONCURRENT` (see "Parallel fan-out" for the full cap semantics). Skipping this step collapses the run back to "one batch of 4, then idle" — the exact bursty pattern the cap was added to prevent.
- Do **not** check CI yourself for opened PRs. Each agent returned without waiting; review-comment resolution + CI babysitting is what `/resolve-my-prs` is for. Hand the user the merge-time work as a queue, not a live status board.
- When **all** agents have reported (queue empty AND no in-flight Agents), group their outcomes (see "Final report" below).

## Cleanup pass

Before printing the dispatch summary, reap every worktree + local branch the fan-out left behind. The opened PR's branch lives on `origin` — the local copy is dead weight (see `bin/cleanup_agent_worktrees.sh` for why this matters).

For each issue whose reported `Outcome` is a **success outcome** — `pr-opened`, `no-op-already-addressed`, `pr-resumed`, `pr-resumed-noop`, `branch-resumed`, or `branch-resumed-noop` — run:

```bash
git worktree unlock "${WORKTREE}" 2>/dev/null || true
git worktree remove --force "${WORKTREE}" 2>/dev/null || true
if [[ "${LOCAL_BRANCHES}" != "-" ]]; then
    IFS=',' read -ra _bs <<< "${LOCAL_BRANCHES}"
    for b in "${_bs[@]}"; do
        b="${b// /}"  # trim whitespace (field may be written as "b1, b2")
        [[ -z "$b" ]] && continue
        git branch -D -- "$b" 2>/dev/null || true
    done
fi
```

where `${WORKTREE}` and `${LOCAL_BRANCHES}` come from the per-issue report's new fields. Every command is best-effort (`|| true`) — a failure here must never abort the run.

**Skip cleanup for any `blocked-<reason>` outcome.** The user needs to be able to `cd` into the worktree and finish by hand.

After the loop, finish with `git worktree prune || true` and print a single status line at the top of the upcoming dispatch summary:

```text
🧹 Cleaned <N> worktrees, <M> branches (kept <K> for blocked issues).
```

## Final report

Once every agent in scope has reported, restore your starting branch (`[ "$ORIGINAL_BRANCH" = "HEAD" ] || git checkout "$ORIGINAL_BRANCH"` — skip the restore on a detached-HEAD start so we don't re-detach unnecessarily) and print the **dispatch summary**. Group by outcome — issues are independent and don't have an inherent order, so this is a summary, not a merge order:

1. **PRs opened** — fresh-branch outcomes (`pr-opened`). One line each: `#<issue> → <PR URL> — <one-line scope>`. Suggest the user kick off `/resolve-my-prs` next to grind review feedback as the bots come back.
2. **Resumed in-flight PRs** — `pr-resumed`, `pr-resumed-noop`, `branch-resumed`, `branch-resumed-noop`. One line each: `#<issue> → <PR URL> — <what changed | noop>`. These already have active CI and open (or incoming) review threads. Suggest the user kick off `/resolve-my-prs` next to grind review feedback as the bots come back.
3. **No-ops** — issues already addressed in main, with the addressing commit/file:line the agent cited. The user decides whether to close.
4. **Blocked** — `blocked-active-worktree`, `blocked-ambiguous`, or `blocked-<reason>`, with each agent's "what I'd need to know" note quoted so the user can resolve and re-run.

## Ground rules (recap)

- **Outer orchestrator never touches branches.** Enumerate, filter, fan out, collect reports, print summary. That's it.
- **At most 4 Agents per message, with backfill on completion** (`MAX_CONCURRENT = 4`). Each call uses `isolation: "worktree"` AND `run_in_background: true` so they actually run in parallel and the orchestrator's turn doesn't block on the slowest agent. Backfill on every completion notification until the queue drains — never dispatch the whole queue at once (see "Parallel fan-out" for the session-budget rationale).
- **Resume in-flight work when found.** Issue with an open linked PR → agent checks out the PR, rebases, finishes any missing work, and processes open review threads (per `/resolve-my-prs` + AGENTS.md §5). Issue with an `issue-${N}-*` branch but no PR → agent rebases, finishes, opens the PR via Phase 3's idempotency-guarded create. Only worktree collisions cause a skip.
- **Skip issues whose target branch is already checked out in another worktree** — mark `blocked-active-worktree`.
- **Ambiguity → bail, never guess.** `blocked-ambiguous` with a concrete "what I'd need to know" note is the correct outcome when intent is unclear. A vapor PR is worse than no PR.
- **No-PR-if-no-diff.** If the issue is already addressed in main, comment on the issue and return `no-op-already-addressed`. Do not close the issue.
- **Ready-for-review, not draft.** The bots need a non-draft PR to fire.
- Scope is strict: open issues authored by `$ME` only. No exceptions.
- Follow [AGENTS.md](../../../AGENTS.md) for project-specific commands and conventions.
- Always branch from `origin/main`. Never branch off another feature branch.
- Run `pre-commit` (and targeted `colcon test` when relevant) locally before pushing — per AGENTS.md §2.
- Never bypass a check by disabling, skipping, or deleting tests / lint rules / required status checks. Fix the underlying issue.
- Pipeline across issues: each per-issue Agent opens the PR and returns without waiting for CI or bot reviews; addressing review feedback is `/resolve-my-prs`'s job.
- When in doubt — stop and ask. Don't guess.

## See also

- [resolve-my-prs](../resolve-my-prs/SKILL.md) — the companion skill that grinds review feedback on the PRs this one opens.
- [AGENTS.md](../../../AGENTS.md) — full per-PR playbook (auth, pre-push, CI triggers, conflict resolution).
- [CLAUDE.md](../../../CLAUDE.md) — project reference + "Adversarial Code Review" section (the push-back-vs-capitulate stance for any review feedback the agent receives mid-flight).
- [CONTRIBUTING.md](../../../CONTRIBUTING.md) — coding conventions and the language-choice rule (runtime nodes are C++).
