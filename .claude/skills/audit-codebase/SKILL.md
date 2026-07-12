---
name: audit-codebase
description: Deep audit of the full codebase for bugs, bad practices, and improvement opportunities. Files one GitHub issue per confirmed finding so the backlog feeds directly into /resolve-my-issues.
---

# audit-codebase

Sweeps the repo for real bugs and bad practices across four areas: C++ runtime nodes, CI/GitHub Actions workflows, Claude skills and agent docs, and launch/config files. Files one GitHub issue per confirmed finding. Designed to feed the `/resolve-my-issues` backlog.

## When to use

- Before a sprint to surface latent problems for the team to fix.
- After a large refactor to check that conventions were followed everywhere.
- Periodically (e.g. monthly) as a hygiene pass.
- After merging several PRs that touched different parts of the stack.

Not for reviewing a specific PR diff — use `/local-pr-review` for that.

## Scope

By default the audit covers all four areas. Narrow scope with an optional argument:

- `/audit-codebase` — all four areas
- `/audit-codebase cpp` — C++ runtime nodes only
- `/audit-codebase ci` — CI/GitHub Actions only
- `/audit-codebase skills` — Claude skills, AGENTS.md, CLAUDE.md only
- `/audit-codebase launch` — launch files and YAML configs only

## Pre-flight (outer orchestrator)

The outer orchestrator stays in the main checkout. It only runs read-only `gh` and `git` commands.

0. Determine scope: parse the invocation argument to build the `AREAS` list before doing anything else.
   - `/audit-codebase` → `AREAS=(cpp ci skills launch)`
   - `/audit-codebase cpp` → `AREAS=(cpp)`
   - `/audit-codebase ci` → `AREAS=(ci)`
   - `/audit-codebase skills` → `AREAS=(skills)`
   - `/audit-codebase launch` → `AREAS=(launch)`

   Only areas in `AREAS` get an agent dispatched. All subsequent steps (dispatch, report) reference `AREAS` — do not hard-code four areas.

1. Auth:

   ```bash
   gh auth status
   ```

2. Identify yourself and the repo:

   ```bash
   ME=$(gh api user -q .login)
   OWNER=$(gh repo view --json owner -q .owner.login)
   REPO=$(gh repo view --json name -q .name)
   ```

3. Fetch the current open-issue list so agents can deduplicate:

   ```bash
   gh issue list --state open --limit 1000 --json number,title \
     | jq -r '.[].title'
   ```

   Pass this list into the agent prompt so it can skip filing duplicates without making extra API calls.

4. Fetch main:

   ```bash
   git fetch origin main
   ```

## Agent dispatch

Fan out **one Agent per scope area** in parallel (up to 4 — one per area, so no batching needed). Each call MUST use:

- `subagent_type: "general-purpose"`
- `isolation: "worktree"` — agent gets a fresh worktree off `origin/main`
- `run_in_background: true`

Each agent receives the prompt below with `${AREA}`, `${ME}`, `${OWNER}/${REPO}`, and `${OPEN_ISSUE_TITLES}` filled in.

### Per-area Agent prompt template

```text
You are auditing the `${OWNER}/${REPO}` repository for real bugs, bad
practices, and improvement opportunities. Your job is to find confirmed
problems and file one GitHub issue per finding.

Area: ${AREA}

ME: ${ME}
REPO: ${OWNER}/${REPO}

Start by reading CLAUDE.md, CONTRIBUTING.md, AGENTS.md, and
.github/copilot-instructions.md in full before looking at any source files.

## What to look for in area: ${AREA}

### cpp — C++ runtime nodes (`src/`)
Any node reachable from `car.launch.py` must be C++ (rclcpp/ament_cmake).
Look for:
- Logic bugs: off-by-one, wrong math, incorrect edge-case handling
- Memory issues: raw owning pointers, missing nullptr checks on critical paths,
  use-after-move
- ROS 2 bad practices: spinning in callbacks, blocking calls on the main
  executor thread, QoS durability/reliability mismatches causing silent drops
- Parameter handling: missing declarations, no bounds validation on
  safety-critical params (steering limits, speed limits)
- Missing error handling on hardware interface calls (VESC, PCA9685, lidar)
- Header guard format: must be `PACKAGE__FILENAME_HPP_` (double underscore,
  package-relative). CI uses `--root=src/<package>/include`.

Key packages: `tron_racer_control`, `scan_transformer`, `pure_pursuit`,
`tron_sim_helpers`, `sensor_fusion_calibration`. Submodules under `src/` are
in scope if they carry project-specific changes.

Before checking submodule scope, initialise them (worktrees do not init
submodules automatically):

  ```bash
  git submodule update --init
  ```

### ci — CI/GitHub Actions (`.github/workflows/`)

Look for:

- Unpinned action versions (SHA pinning is best practice for supply-chain
  security)
- Secrets exposed in logs
- Missing `permissions:` blocks (principle of least privilege)
- `pull_request_target` with checkout of untrusted code (RCE vector)
- Workflow files that run on both `push` to `main` AND `pull_request`
  simultaneously without a guard — potential double-billing
- Container credential injection correctness (GHCR pulls on Blacksmith runners)
- Missing `timeout-minutes` on long-running jobs

### skills — Claude skills / agent docs

Files: `.claude/skills/**/*.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`

Look for:

- Instructions that contradict each other across files
- Missing or stale cross-references (link targets that no longer exist)
- Skills that reference commands, file paths, or topic names that no longer
  exist in the repo
- `resolve-my-prs` / `resolve-my-issues` / [pr-resolution.md](docs/agent-workflows/pr-resolution.md): logic gaps,
  incorrect git commands, race conditions in the described workflows
- AGENTS.md pre-push gate: is the described `pre-commit` + `colcon test`
  sequence accurate for the current CI setup?

### launch — Launch / config files (`src/tron_racer_bringup/`)

Look for:

- Launch arguments with no defaults that would silently fail at runtime
- YAML configs with physically implausible values (negative frequencies, zero
  covariances on active sensors)
- Topic remapping mismatches between launch files and node subscriptions
  (use `git grep` to cross-check remap targets against node source files)
- Missing `use_sim_time` propagation to nodes that depend on it
- Spawn pose fallback chain correctness (spawn.yaml → track.yaml midpoint
  → (0,0,0))

## What counts as a real finding

File an issue ONLY if:

- You read the actual file and confirmed the problem in the current code on main
- The finding is actionable: state the file:line and what the correct
  behavior is
- It is not already tracked — check these existing open issue titles first
  (do NOT re-query GitHub; use the list provided):

${OPEN_ISSUE_TITLES}

Do NOT file issues for:

- Style preferences with no correctness implication
- Hypothetical problems you didn't verify in the actual source
- Things already documented as known limitations
- Duplicates of the titles above — exact title match, or a title that shares
  the same package token and the same first five words as an existing title
  (split on whitespace; `area(package):` counts as word 1)

## Idempotency guard before filing each issue

Even though the list above was current at dispatch time, race conditions are
possible (another agent may file first). Before each `gh issue create`, run:

  ```bash
  gh issue list --state open --limit 1000 --json number,title \
    | jq -r '.[].title'
  ```

and skip if an exact title already exists, or if the title shares the same package token and the same first five words (split on whitespace; `area(package):` counts as word 1).

## Issue format

Title: `<area>(<package-or-file>): <concise description>`
  e.g. `cpp(scan_transformer): off-by-one in angle filter`, `ci(ros2-ci.yml): missing timeout-minutes`, `skills(audit-codebase): stale cross-reference`

Body (required sections):

- **What**: one sentence describing the problem
- **Where**: `file:line` citation
- **Why it matters**: concrete failure mode or risk (not vague)
- **Fix**: specific change required

## Report format

After filing all issues (or finding none), print:

```text
Area: ${AREA}
Issues filed: <N>
  - #<number>: <title>
  ...
Skipped (duplicate or unconfirmed):
  - <description> — <reason>
```

## What the outer orchestrator does between fan-out and reporting

With `run_in_background: true`, each agent fires a completion notification when done and the orchestrator's turn is re-invoked on each notification — the orchestrator's turn ends immediately after dispatch. Do **not** poll agents or block on the slowest one.

On each completion notification:

1. Accumulate the area report (issues filed, skipped list) from the completed agent. Track a counter initialised to `len(AREAS)` and decrement it on each notification.
2. When the counter reaches zero (all areas have reported), proceed to the final report below.

> **Note:** All areas are dispatched upfront in a single fan-out; there is no queue and no replacement logic. If an area never produces a completion notification (silent failure), re-run the skill scoped to that area (e.g. `/audit-codebase cpp`).

## Collecting results

After all agents in `AREAS` report back, the outer orchestrator:

1. Aggregates all filed issue numbers and titles into a single summary.
2. Deduplicates across areas: compare filed titles across all area reports using
   the same rule as the idempotency guard (exact match, or same package token
   and same first five words). If the same title (or a near-match) appears in
   multiple area reports, flag it as a cross-area duplicate in the summary.
3. Prints the final report:

```text
Audit complete.

Total issues filed: <N>
  <area>: <n> issues   (one line per area in AREAS)

Filed:
  - #<number>: <title>
  ...

Skipped / not confirmed:
  - <description> — <reason>

Next step: run /resolve-my-issues to implement fixes.
```

## Ground rules

- **Outer orchestrator never touches files.** Read-only `gh` and `git` commands only.
- **Confirm before filing.** Agents must read the actual source before filing — no filing based on pattern-matching filenames or guessing.
- **No duplicate issues.** Check the live list before every `gh issue create`.
- **One issue per finding.** Do not bundle unrelated findings into a single issue — `/resolve-my-issues` dispatches one agent per issue, so granularity matters.
- **Scope is bounded.** Only files in this repo (not submodules that have their own upstream) unless the submodule carries project-specific changes. To test (after `git submodule update --init`): inside the submodule directory, first run `git fetch origin` so the remote-tracking refs exist (worktree-initialised submodules are in detached HEAD with no fetched refs), then resolve the upstream default branch via `UP=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)` (handles submodules whose default branch is `master` rather than `main`), then run `git log --oneline "$UP"..HEAD`; if the output is non-empty, the submodule has local commits that diverge from upstream and is in scope. An empty output means upstream-only content — skip it.
- When in doubt about whether a finding is real — skip it. A missed finding is better than a false-positive issue that wastes an agent's time.

## See also

- [resolve-my-issues](../resolve-my-issues/SKILL.md) — implement the filed issues
- [resolve-my-prs](../resolve-my-prs/SKILL.md) — resolve review comments on the resulting PRs
- [resolve-pr](../resolve-pr/SKILL.md) — resolve review comments on a single named PR
- [local-pr-review](../local-pr-review/SKILL.md) — adversarial review of a specific PR diff
- [AGENTS.md](../../../AGENTS.md) — pre-push gate, CI commands, comment-resolution protocol
- [CLAUDE.md](../../../CLAUDE.md) — project conventions (topic namespacing, hardware, package roles)
- [CONTRIBUTING.md](../../../CONTRIBUTING.md) — coding conventions and language-choice rule
