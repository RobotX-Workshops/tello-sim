---
name: rebase-pr
description: Claude adapter for rebasing one open-PR branch onto main with the repo's agent-agnostic workflow.
---

# rebase-pr

This is a Claude-specific adapter for a single named PR. The canonical workflow
is [docs/agent-workflows/branch-rebase.md](../../../docs/agent-workflows/branch-rebase.md)
plus [AGENTS.md](../../../AGENTS.md). This is rebase-only; for resolving review
comments use `/resolve-pr` instead.

## Argument Parsing

Accept any of these forms:

- `/rebase-pr 42`
- `/rebase-pr #42`
- `/rebase-pr https://github.com/owner/repo/pull/42`

Extract the PR number and run the "Single-PR Flow" from
`docs/agent-workflows/branch-rebase.md`.

## Claude Adapter Mapping

- Run only pre-flight checks in the outer Claude session.
- Dispatch one Claude Agent for the PR when a rebase is needed.
- Use `isolation: "worktree"` for the dispatched Agent.
- Use synchronous execution.
- Skip cleanup for any `blocked-*` outcome — including `blocked-rebase-conflict`
  and the catch-all `blocked-<reason>` — so the user can inspect the worktree.

## Prompt Stub

```text
You are rebasing PR #${N} on branch `${BRANCH}` onto main for `${ME}` in
`${OWNER}/${REPO}`.

Follow docs/agent-workflows/branch-rebase.md and AGENTS.md directly. You are a
per-PR worker in an isolated worktree. Return the normalized per-PR report
described by docs/agent-workflows/branch-rebase.md.
```
