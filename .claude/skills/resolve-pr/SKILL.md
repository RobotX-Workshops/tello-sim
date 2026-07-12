---
name: resolve-pr
description: Claude adapter for resolving one PR with the repo's agent-agnostic workflow.
---

# resolve-pr

This is a Claude-specific adapter for a single named PR. The canonical workflow
is [docs/agent-workflows/pr-resolution.md](../../../docs/agent-workflows/pr-resolution.md)
plus [AGENTS.md](../../../AGENTS.md).

## Argument Parsing

Accept any of these forms:

- `/resolve-pr 42`
- `/resolve-pr #42`
- `/resolve-pr https://github.com/owner/repo/pull/42`

Extract the PR number and run the "Single-PR Flow" from
`docs/agent-workflows/pr-resolution.md`.

## Claude Adapter Mapping

- Run only pre-flight checks in the outer Claude session.
- Dispatch one Claude Agent for the PR when work is needed.
- Use `isolation: "worktree"` for the dispatched Agent.
- Use synchronous execution for the first pass and any circle-back rounds.
- Inject the previous pushed SHA into circle-back prompts so CI matching uses the
  correct commit.
- Skip cleanup for `blocked-<reason>` outcomes so the user can inspect the
  worktree.

## Prompt Stub

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
