---
name: cleanup-worktrees
description: Remove stale Claude Code agent worktrees under .claude/worktrees/ that are left over from finished agent runs. Reclaims disk space and prevents ripgrep search storms.
---

# cleanup-worktrees

Remove stale git worktrees left behind by Claude Code agents.

## When to use

- When the machine is sluggish or disk is filling up from accumulated agent worktrees.
- After a session that spawned many agents (e.g. `/resolve-my-prs`, `/resolve-my-issues`).
- Proactively before a heavy multi-agent session.

## Procedure

1. Run `git worktree list --porcelain` and identify every worktree under `.claude/worktrees/`.
2. For each, first check whether it carries a `locked` stanza in the porcelain output.
   The Claude Agent SDK **does** call `git worktree lock` for agent worktrees — the lock
   reason string has the form `claude agent <worktree-name> (pid <PID>)`, e.g.:

   ```text
   worktree /repo/.claude/worktrees/agent-ae42c326cd1d0b40a
   HEAD b460097be38f0beb61b14125e9c3314fcc58c8c4
   branch refs/heads/worktree-agent-ae42c326cd1d0b40a
   locked claude agent agent-ae42c326cd1d0b40a (pid 565)
   ```

   This was verified by running `git worktree list --porcelain` from the host while agents
   were active (observed 2026-05-25, Claude Agent SDK via `isolation: "worktree"`).

   However, a lock stanza persists even after a process dies — the SDK does not always unlock
   on crash. Therefore, when a `locked` stanza is present, first extract the PID from the
   reason string. If the reason does not match the expected `claude agent <name> (pid <PID>)`
   format (e.g. manually locked, different SDK version, or empty reason), **skip the worktree
   unconditionally** and add it to the skipped list annotated with
   `locked (unrecognized reason — manual review required)`.

   When a PID is successfully extracted, apply the following decision tree:

   **Step A — Platform check:** Determine whether `/proc` is available (Linux).
   - If `/proc` exists **and** `/proc/<PID>` does **not** exist: PID is definitively dead.
     Now check whether the worktree directory still exists (`test -d <path>`):
     - If the **directory is present**: measure size with `du -sk <path>` (kilobytes,
       portable) and record it for Step 6. Classify as **live-directory-stale** (see
       Step 4's `git worktree remove --force --force` for the removal primitive), include
       in cleanup candidates, and skip Step B entirely.
     - If the **directory is absent**: the path is already gone but the admin files under
       `.git/worktrees/<name>/` remain — and because the `locked` file is still present,
       `git worktree prune` will not remove them (locking explicitly prevents pruning).
       Classify as **gone-directory-locked** and include in cleanup candidates. Step 5
       will run `git worktree unlock <name>` on each such entry before `git worktree prune`
       to remove the remaining admin files. Skip Step B entirely.
   - If `/proc` exists **and** `/proc/<PID>` is present: PID is alive — fall through to
     Step B for identity verification (do **not** re-check `/proc/<PID>` in Step B; liveness
     is already confirmed here).
   - If `/proc` is not available (non-Linux): fall through to Step B for liveness checking via `ps -p` (with `kill -0` as a last resort).

   **Step B — Liveness re-check (non-Linux only) + identity verification (all platforms):**

   1. On Linux (where Step A already confirmed `/proc/<PID>` is present), the PID is
      alive — proceed directly to Step B.2 for identity verification. On non-Linux
      (no `/proc`), use `ps -p <PID>` (exit code 0 = process exists, non-zero = does
      not exist): if `ps -p <PID>` exits **0**, the process exists — proceed to Step B.2
      for identity verification. If `ps -p <PID>` exits non-zero, the process is dead
      (ESRCH). Do **not** use bare `kill -0 <PID>` here: its stderr messages are
      locale-dependent (e.g. `"Opération non permise"` on French macOS), making EPERM
      detection unreliable when `LANG` is not English. If `ps` is unavailable for any
      reason and `kill -0` must be used as a last resort, prefix it with `LANG=C` to force
      English error text: if `LANG=C kill -0 <PID>` exits **0** (no error), the process is
      alive — proceed to Step B.2 for identity verification. Treat "Operation not permitted"
      as **unverifiable** and "No such process" as dead.
   2. When the PID is confirmed alive (Step B.1 returned alive), verify process identity to guard against
      PID reuse on long-running machines. Check the **executable basename** (not a substring
      of the full cmdline, to avoid false-positive matches on path components like
      `/home/claude/node_modules/...`):
      - On Linux: `cat /proc/<PID>/comm 2>/dev/null` returns the executable basename (up
        to 15 chars — sufficient for `claude` and `node`).
      - On non-Linux: `ps -p <PID> -o comm=` returns the basename.
      Accept as a confirmed Claude agent if:
      - The basename is `claude` or `claude-code` (covers native binary and Homebrew installs).
      - The basename is `node` **and** the full cmdline contains `@anthropic-ai/claude-code`
        as a substring. Claude Code on Linux typically runs as
        `node .../node_modules/@anthropic-ai/claude-code/cli.js`; `@anthropic-ai/claude-code`
        is a reliable package-scoped indicator. Check with:
        `grep -aqF '@anthropic-ai/claude-code' /proc/<PID>/cmdline` on Linux (`-a` forces
        text-mode processing so `grep` does not silently skip the binary NUL-separated
        cmdline file; `-F` treats the pattern as a fixed string rather than a regex), or
        `ps -p <PID> -o args= | grep -qF '@anthropic-ai/claude-code'` on non-Linux.
        Do **not** use whitespace-delimited token matching (`(^| )claude-code( |$)` or
        equivalent awk field checks) — `claude-code` is a path component surrounded by `/`
        characters in the cmdline, not whitespace, so token-boundary patterns never match.
      If the process is alive but the command does not match, treat the
      worktree as **ambiguous** — add it to the skipped list with
      `locked (PID <PID> alive but not a Claude agent — manual review required)`.

   **Decision outcomes (in priority order):**

   - **Unverifiable** (`/proc` absent on non-Linux and the fallback `LANG=C kill -0` returned
     EPERM — meaning the process exists but its identity cannot be confirmed due to a UID
     mismatch): skip and add to the skipped list with
     `locked (PID <PID> unverifiable — possible remote-machine or cross-UID lock)`.
   - **PID alive + identity confirmed**: worktree belongs to a live agent run — collect in
     the **locked-live — skipped** list; do not touch it.
   - **PID alive + identity ambiguous**: skip with `locked (PID <PID> alive but not a
     Claude agent — manual review required)`.
   - **PID dead** (ESRCH on non-Linux only — documented here for completeness; the Linux
     `/proc/<PID>`-absent path is fully handled by Step A and must not be re-evaluated
     at this table): treat as stale — include in cleanup candidates. Classify as:
     - **live-directory-stale (agent orphan)** when the directory still exists (`test -d <path>`
       returns true) **and** the worktree name extracted from the lock reason matches `agent-*`
       (e.g. `claude agent agent-<hash> (pid <PID>)` → name `agent-<hash>`). The lock reason
       encodes the worktree name, but do not assume the name always matches `agent-*` — verify
       it explicitly with `[[ <name> == agent-* ]]`. If the name does **not** match `agent-*`,
       classify as **live-directory-stale (named)** instead (requires individual confirmation;
       do not batch-delete). The double `--force` in `git worktree remove --force --force`
       bypasses the lock directly for either sub-classification.
       Measure size with `du -sk <path>` (kilobytes, portable) and record it for Step 6.
       Do **not** unlock at this stage; removal is deferred to Step 4 after user confirmation.
     - **gone-directory-locked** when the directory is absent (`test -d <path>` returns false).
       Classify as **gone-directory-locked** and include in cleanup candidates.
       No Step 4 `remove` action is needed — the directory is already gone; the admin
       files are cleaned up by Step 5's unlock + prune sequence.

   For the remainder (no `locked` stanza), classify each into one of three stale buckets:

   - **gone-directory**: the worktree path no longer exists (`test -d <path>` returns false),
     or `git worktree list --porcelain` marks it `prunable`. Disk usage is zero — nothing
     to measure.
   - **live-directory-stale (agent orphan)**: the path still exists, carries no `locked`
     stanza, and the worktree name matches `agent-*`. These are scratch worktrees by convention.
     Measure size with `du -sk <path>` (kilobytes, portable across Linux and macOS) for
     accurate summation.
   - **live-directory-stale (named)**: the path still exists, carries no `locked` stanza,
     and the worktree name does **not** match `agent-*`. Measure size with `du -sk <path>`
     (kilobytes, portable) and record it for Step 6. Present these in a separate sub-list
     — they may contain in-progress feature work. Require individual per-worktree
     confirmation; do not batch-delete with the agent orphans.

3. Report the list of stale worktrees (name, branch, and size — empty for gone-directory
   entries) plus the full **skipped** section so the user knows which were excluded and why.
   Format per-entry sizes as KiB/MiB/GiB (prefer GiB when size ≥ 1048576 KiB,
   MiB when size ≥ 1024 KiB, otherwise KiB) before presenting the confirmation list (do not
   show raw byte counts). The skipped section must enumerate all four skip categories separately:
   - **locked-live**: PID alive + identity confirmed (name only — these are active agent runs).
   - **locked (unrecognized reason)**: reason string did not match the expected format —
     manual review required (name + raw reason string).
   - **locked (ambiguous)**: PID alive but not a Claude agent — manual review required
     (name + PID).
   - **locked (unverifiable)**: cross-UID or remote-machine lock, identity cannot be
     confirmed — manual review required (name + PID).
   Ask the user to confirm before removing.
4. Remove confirmed entries:
   - For **live-directory-stale**: use `git worktree remove --force --force <path>` as the
     single removal primitive — the double `--force` bypasses the lock check directly, so
     no separate `git worktree unlock` step is needed.
   - For **gone-directory** (unlocked): skip `remove` (the directory is already gone);
     they are cleaned up by Step 5's `git worktree prune`.
   - For **gone-directory-locked**: skip `remove` (directory already gone); Step 5 will
     first run `git worktree unlock <name>` to clear the lock, then `git worktree prune`
     removes the admin files. (`git worktree prune` does not accept `--force`; unlocking
     beforehand is the only way to prune a locked admin entry.)
5. For every **gone-directory-locked** entry confirmed in Step 3, run
   `git worktree unlock <name>` to remove the lock file. Then — regardless of whether any
   gone-directory-locked entries existed — run `git worktree prune` to clean up all dangling
   admin references in `.git/worktrees/` (both unlocked gone-directory entries and any
   just-unlocked locked ones). Do not conditionalize the prune on the existence of
   gone-directory-locked entries: unlocked gone-directory worktrees also need pruning
   and must not be skipped.
6. Report total disk space reclaimed. Sum the `du -sk` values recorded in Step 2 —
   these are already in KiB (1024-byte blocks). Pick the largest unit where the result
   is ≥ 1, checking in descending order: prefer GiB when total ≥ 1048576 KiB, MiB when
   total ≥ 1024 KiB, otherwise display in KiB. Do not re-run `du` at this step — the
   paths have already been deleted.

## Safety

- Never remove worktrees outside `.claude/worktrees/` — e.g. ones created by hand with
  `git worktree add` for a named feature branch, or kept under a sibling
  `<repo>-worktrees/` directory (such as `tron-roboracer-worktrees/`). These are out of
  scope regardless of their name.
- Always confirm with the user before deleting. Show what will be removed.
- Named worktrees (non-`agent-*` prefixed) may contain in-progress feature work — list them
  separately and let the user decide.
- For a `locked` worktree whose PID cannot be verified (e.g. running on a remote machine),
  default to **skipping** it and surface it in the skipped list with a note.
