---
name: resolve-my-prs
description: Claude adapter for the repo's agent-agnostic bulk PR resolution workflow.
---

# resolve-my-prs

This is a Claude-specific adapter. The repo policy and orchestration contract
live in [docs/agent-workflows/pr-resolution.md](../../../docs/agent-workflows/pr-resolution.md)
and [AGENTS.md](../../../AGENTS.md). Read both before dispatching any work.

## Claude Adapter Mapping

- Treat `docs/agent-workflows/pr-resolution.md` as the canonical bulk-PR
  workflow.
- Use Claude background Agents only as the runtime mechanism for the document's
  "Bulk PR Flow" and "Per-PR Worker Contract".
- Dispatch at most 4 concurrent Agents.
- Use `isolation: "worktree"` for every per-PR Agent.
- Use `run_in_background: true` for bulk first-pass and circle-back Agents.
- Skip PRs whose branch is already checked out in another local worktree.
- Keep per-PR mechanics in AGENTS.md; do not duplicate commands here.

## Prompt Stub

For each PR, pass the worker enough identity context to execute the canonical
workflow:

```text
You are processing PR #${N} on branch `${BRANCH}` for `${ME}` in
`${OWNER}/${REPO}`.

Follow docs/agent-workflows/pr-resolution.md and AGENTS.md directly. You are a
per-PR worker in an isolated worktree. Assess and resolve every review thread
regardless of author — CodeRabbit, Copilot, Claude, and human reviewers all
count; verify zero unresolved threads remain (AGENTS.md §5 Step 6) before
reporting. Return the normalized per-PR report described by
docs/agent-workflows/pr-resolution.md.
```

For circle-back rounds, prepend:

```text
Previous push SHA for this PR: ${PREV_SHA}. Use this SHA when matching the CI
run from the prior pass.
```

## Cleanup

Follow the "Cleanup" section of `docs/agent-workflows/pr-resolution.md` (the
all-or-nothing skip rule and discovery commands). Map the reaping step to
Claude's `/cleanup-worktrees` and `/cleanup-branches` skills — invoke them only
when NO PR in the run is `blocked-<reason>`.

## Final Reporting

After all first-pass and circle-back work completes, report the merge order and
blocked PRs using the rules in `docs/agent-workflows/pr-resolution.md`.
