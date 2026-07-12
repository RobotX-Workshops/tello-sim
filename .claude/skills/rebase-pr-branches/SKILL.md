---
name: rebase-pr-branches
description: Claude adapter for the repo's agent-agnostic workflow that rebases all of the user's open-PR branches onto main.
---

# rebase-pr-branches

This is a Claude-specific adapter. The repo policy and orchestration contract live
in [docs/agent-workflows/branch-rebase.md](../../../docs/agent-workflows/branch-rebase.md)
and [AGENTS.md](../../../AGENTS.md). Read both before dispatching any work. This is
rebase-only; for resolving review comments across PRs use `/resolve-my-prs` instead.

## Claude Adapter Mapping

- Treat `docs/agent-workflows/branch-rebase.md` as the canonical bulk-rebase
  workflow.
- Use Claude background Agents only as the runtime mechanism for the document's
  "Bulk Flow" and "Per-PR Worker Contract".
- Dispatch at most 4 concurrent Agents.
- Use `isolation: "worktree"` for every per-PR Agent.
- Use `run_in_background: true` for bulk dispatch Agents.
- Skip PRs whose branch is already checked out in another local worktree.
- Keep per-PR mechanics in AGENTS.md; do not duplicate commands here.

## Prompt Stub

For each PR, pass the worker enough identity context to execute the canonical
workflow:

```text
You are rebasing PR #${N} on branch `${BRANCH}` onto main for `${ME}` in
`${OWNER}/${REPO}`.

Follow docs/agent-workflows/branch-rebase.md and AGENTS.md directly. You are a
per-PR worker in an isolated worktree. Return the normalized per-PR report
described by docs/agent-workflows/branch-rebase.md.
```

## Cleanup

Follow the "Cleanup" section of `docs/agent-workflows/branch-rebase.md` (the
all-or-nothing skip rule and discovery commands). Map the reaping step to Claude's
`/cleanup-worktrees` and `/cleanup-branches` skills — invoke them only when NO PR
in the run is in any `blocked-*` state (`blocked-rebase-conflict`,
`blocked-active-worktree`, or the catch-all `blocked-<reason>`).

## Final Reporting

After all dispatch work completes, report each PR's outcome and pushed SHA using
the report block in `docs/agent-workflows/branch-rebase.md`, and call out any
`blocked-*` PRs (`blocked-rebase-conflict`, `blocked-active-worktree`, or the
catch-all `blocked-<reason>`) that need human follow-up.
