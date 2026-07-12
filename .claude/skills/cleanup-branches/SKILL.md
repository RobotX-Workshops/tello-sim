---
name: cleanup-branches
description: Remove local git branches that are stale — merged into main, deleted on remote, or orphaned from old agent/worktree runs (local-*, claude/*, worktree-*, agent-* prefixes).
---

# cleanup-branches

Clean up local branches that are no longer needed.

## When to use

- After merging a batch of PRs.
- When `git branch` output is cluttered with dozens of old branches.
- After running `/cleanup-worktrees` to remove the branches those worktrees were on.

## Procedure

1. Run `git fetch --prune` to sync remote tracking state.
2. Identify the default branch: run `git symbolic-ref refs/remotes/origin/HEAD | sed 's|.*/||'`; fall back to `gh repo view --json defaultBranchRef -q '.defaultBranchRef.name'` if the symbolic ref is unset.
3. Collect candidate branches into four mutually exclusive buckets (apply in order — the first matching bucket wins):
   - **Gone remotes (safe)**: branches whose upstream tracking branch no longer exists (`git for-each-ref --format='%(refname:short)%09%(upstream:track)' refs/heads | grep '\[gone\]' | awk -F'\t' '{print $1}'`) **and** that are also merged into the default branch (cross-check with `git branch --merged <default>`). Safe to delete — no unpushed work.
   - **Merged (remote still present)**: branches fully merged into the default branch (`git branch --merged <default>`), excluding the default branch itself, **and not** in the Gone-safe bucket above.
   - **Gone remotes (risky)**: gone-upstream branches that are **not** merged into the default and **do not** match the orphan patterns below. For each, run `git log <branch> --not --remotes --oneline` to count unpushed commits and surface this in the confirmation prompt as `unmerged — N unpushed commits`. Skip by default; require explicit opt-in per branch.
   - **Agent/worktree orphans**: branches matching `local-*`, `claude/*`, `worktree-*`, `agent-*` patterns that have no corresponding worktree (cross-reference `git worktree list`). These are treated as disposable even if unmerged — they are scratch branches by convention. **However, each branch must pass the open-PR guard in step 5 before force-deletion.** Note: an orphan-named branch that *still has an active worktree* will not match this bucket (worktree present) and will also not match the "Gone remotes (risky)" bucket (excluded by orphan pattern). Such branches are intentionally left uncategorized and will not appear in any deletion list — the active worktree is a signal that work is in progress.
4. Present the categorized list and ask the user to confirm. Show branch name and last commit date for each; for the "Gone remotes (risky)" bucket also show the unpushed commit count.
5. Delete confirmed branches:
   - **Gone remotes (safe)** and **Merged (remote still present)**: use `git branch -d <name>` (non-force). Git's own merge-tracking acts as a second-level safety net and will refuse to delete if the history was rewritten or the clone is shallow in a way that defeats `--merged` detection.
   - **Agent/worktree orphans**: before force-deleting, run the open-PR guard for each branch:

     ```bash
     open_prs=$(gh pr list --head <branch> --state open --json number -q '[.[].number | tostring] | join(",")')
     ```

     - If `open_prs` is **non-empty**: **skip the delete**. Surface the branch and PR number(s) in the report so the user can decide:

       ```text
       SKIPPED (open PR): <branch>  →  PR #<numbers>
       ```

     - If `open_prs` is **empty**: proceed with `git branch -D <name>` (force-delete). Unmerged deletion is intentional by convention for scratch branches that have no associated PR.

6. Report how many branches were removed, and list any orphan-pattern branches that were skipped due to open PRs.

## Safety

- Never delete the default branch or the currently checked-out branch.
- Never force-push or touch the remote — this is local-only cleanup.
- Always confirm before deleting. The user may want to keep some branches.
- For branches not yet merged and not in the orphan patterns, flag them as "unmerged — may contain unpushed work" and skip unless the user explicitly includes them. The "Gone remotes (risky)" sub-bucket in step 3 enforces this for gone-upstream branches; never collapse it back into the safe bucket.
- **Open-PR guard (orphan bucket):** `git branch -D` is never run on any orphan-pattern branch (`local-*`, `claude/*`, `worktree-*`, `agent-*`) without first running `gh pr list --head <branch> --state open --json number -q '[.[].number | tostring] | join(",")'`. A non-empty result means the branch backs a live PR and must be skipped, even though the worktree is gone. This guard applies to **all** orphan patterns reaching the force-delete (`-D`) path — not just `claude/*`. Do not regress this check: a worktree being pruned on one machine does not mean the PR is closed. Note: an orphan-named branch that lands in the "Gone remotes (safe)" bucket (merged into default with gone upstream) uses `git branch -d` (non-force) instead — git's own `--merged` check is the safety net there, not the PR guard, because a fully-merged branch cannot lose work.
