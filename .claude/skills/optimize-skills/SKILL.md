---
name: optimize-skills
description: Compress .claude/skills/**/SKILL.md files for token efficiency, deduplicate instructions across skills, and audit dead references (filing GitHub issues for each found, not fixing inline).
---

# optimize-skills

Applies token-cost optimization to `.claude/skills/**/SKILL.md` files. Beyond prose compression, it detects instructions duplicated across skills, extracts them to the appropriate shared file, and audits dead cross-references (filing issues rather than fixing inline).

## When to use

- After adding a new skill that may repeat instructions already in `AGENTS.md` or `docs/agent-workflows/pr-resolution.md`.
- Before a heavy multi-agent session to reduce per-agent context load.
- Periodically as a maintenance pass.

## What it does

Three passes, in order:

### Pass 1 — Prose compression

Apply to every `.claude/skills/**/SKILL.md` file:

1. Strip filler phrases ("It is important to note that", "In order to", "Please be aware that", "As mentioned above", "Note that", "Keep in mind that")
2. Collapse redundant restatements — keep the more specific one
3. Convert prose lists to bullet/table form
4. Shorten section headers to ≤5 words
5. Drop motivational language; keep rationale only when it constrains agent behavior
6. Preserve exactly: commands, flags, file paths, topic names, param names, decision rationale, cross-reference links, code blocks, tables, warnings
7. Do not reorder sections
8. Target ≥25% token reduction per file; note if not achievable without information loss
9. Never change meaning — when in doubt keep the longer phrasing

### Pass 2 — Deduplication

Scan all skill files for instructions that are identical or near-identical across two or more files. For each duplicated block:

- If the block belongs in `AGENTS.md` (project-wide command or convention): remove from skill files, add a reference link pointing to the relevant AGENTS.md section.
- If the block belongs in `docs/agent-workflows/pr-resolution.md` (per-PR agent mechanics): remove from skill files, add a reference link. `shared/per-pr-agent.md` is only a forwarding stub — do not add mechanics there.
- If the block is skill-specific but repeated across two skills: extract to a new `shared/<topic>.md` file and replace both occurrences with a reference link. Only do this when the extraction is cleaner than the duplication — don't split a 3-line block into a shared file.

Do NOT deduplicate:

- Ground-rules recaps at the end of skills (these are intentional quick-reference summaries, not real duplication)
- Scope/hard-limits sections (each skill needs its own, even if similar)

### Pass 3 — Dead reference audit

For every markdown link `[text](path)` in every skill file:

- Check that the target file exists: `test -f <resolved-path>`
- Check that if the link contains a `#section` anchor, the section heading exists in the target file
- For links to AGENTS.md sections (`§N` format), verify the section numbering is still accurate

File a GitHub issue for each dead reference found (do not fix them inline — dead references indicate that source content moved, which may need a judgment call about where to redirect). For `§N` AGENTS.md links: `grep -n '^## ' AGENTS.md | grep -n .` to enumerate sections and confirm the cited number still matches the heading; mismatch is a dead reference.

Use `gh issue create` (check for an existing open issue with the same title first to stay idempotent):

```bash
TITLE="docs(<skill-file>): dead reference to <target>"
if ! gh issue list --state open --search "in:title \"${TITLE}\"" --json title \
     | jq -e '.[] | select(.title == "'"${TITLE}"'")' >/dev/null; then
  gh issue create --title "${TITLE}" --body "$(cat <<'EOF'
- **Where**: .claude/skills/<skill>/SKILL.md:<line>
- **Link**: [text](path)
- **Problem**: target file/section does not exist
- **Fix**: update link to <correct-path>, or remove if content was deleted
EOF
)"
fi
```

## Pre-flight (outer orchestrator)

1. Auth: `gh auth status`
2. Identify repo:

   ```bash
   OWNER=$(gh repo view --json owner -q .owner.login)
   REPO=$(gh repo view --json name -q .name)
   ```

3. Enumerate skill files (exclude `optimize-skills` itself to avoid self-alteration):

   ```bash
   SKILL_FILES=$(find .claude/skills -name "SKILL.md" | grep -v '/optimize-skills/' | sort)
   if [ -z "$SKILL_FILES" ]; then
     echo "ERROR: no skill files found under .claude/skills/" >&2
     exit 1
   fi
   ```

4. Fetch main: `git fetch origin main`

## Agent dispatch

Dispatch agents in two waves:

**Wave 1 — Compression (parallel, one agent per skill file, cap=4 with backfill):**
Each agent gets one SKILL.md file, applies Pass 1, commits, and pushes its own branch.
Batching: dispatch the first 4 Wave 1 agents concurrently; each time one completes, dispatch the next queued file until all are processed.

**Wave 2 — Deduplication + reference audit (single agent, after Wave 1 completes):**
One agent reads all the compressed files, performs Pass 2 and Pass 3, commits any deduplication changes, and files GitHub issues for dead references. Wave 2 starts in a worktree off `origin/main` — it must fetch and merge every Wave 1 branch before reading any skill files, so it sees the compressed versions rather than the pre-compression originals.

Each Wave 1 agent call MUST use:

- `subagent_type: "general-purpose"`
- `isolation: "worktree"`
- `run_in_background: true`

### Outer orchestrator template

```text
# Pre-flight already completed. OWNER, REPO, and SKILL_FILES are set.
# Now dispatch Wave 1, then Wave 2.

# --- Wave 1 dispatch ---
# Substitute ${SKILL_NAME} with the actual directory name for each skill before
# dispatching — do NOT pass template variables literally to sub-agents.
WAVE1_REPORTS=()
WAVE1_QUEUE=()
for skill_md in ${SKILL_FILES}; do
  SKILL_NAME=$(dirname "$skill_md" | xargs basename)
  WAVE1_QUEUE+=("$SKILL_NAME")
done

# Dispatch up to 4 agents concurrently; backfill as each completes.
# Each Agent(...) call uses run_in_background: true so the orchestrator
# continues without blocking on any single agent.
#
# For each SKILL_NAME in WAVE1_QUEUE, dispatch (concrete example — substitute
# ${SKILL_NAME}=resolve-pr, ${OWNER}=RobotX-Workshops, ${REPO}=tron-roboracer
# before invoking; the full Wave 1 per-file prompt body is in the template
# section below):
#   Agent(
#     subagent_type="general-purpose",
#     isolation="worktree",
#     run_in_background=true,
#     prompt="You are compressing `.claude/skills/resolve-pr/SKILL.md` in
#             `RobotX-Workshops/tron-roboracer` for token efficiency. ...
#             (rest of Wave 1 per-file template, with ${SKILL_NAME},
#             ${OWNER}, ${REPO} all replaced by literal strings)"
#   )
#
# Maintain an active-count counter. When active_count < 4 and the queue is
# non-empty, dispatch the next agent. When active_count == 4, wait for any
# one completion notification before dispatching the next.
#
# Collect each Wave 1 agent's report in WAVE1_REPORTS[].

# --- Wait for all Wave 1 agents to finish ---
# Wait until all dispatched Wave 1 agents have returned their reports.
# (run_in_background agents deliver one notification per completion.)

# --- Extract Wave 1 branch names ---
# Parse each report for the "Branch: <branch>" line:
WAVE1_BRANCHES=()
for report in "${WAVE1_REPORTS[@]}"; do
  branch=$(echo "$report" | grep '^Branch:' | awk '{print $2}')
  WAVE1_BRANCHES+=("$branch")
done

# --- Dispatch Wave 2 ---
# Substitute ${OWNER}, ${REPO}, and ${WAVE1_BRANCHES} (as a space-separated
# list of branch names) into the Wave 2 prompt before dispatching.
Agent(
  subagent_type: "general-purpose",
  isolation: "worktree",
  run_in_background: false,   # wait for Wave 2 before reporting
  prompt: <Wave 2 template with ${OWNER}, ${REPO}, and
           ${WAVE1_BRANCHES} substituted to their actual values>
)
```

### Wave 1 per-file Agent prompt template

```text
You are compressing `.claude/skills/${SKILL_NAME}/SKILL.md` in
`${OWNER}/${REPO}` for token efficiency.

Apply all 9 compression rules exactly:
1. Strip filler phrases ("It is important to note that", "In order to",
   "Please be aware that", "As mentioned above", "Note that", "Keep in mind that")
2. Collapse redundant restatements — keep the more specific one
3. Convert prose lists to bullet/table form
4. Shorten section headers to ≤5 words
5. Drop motivational language; keep rationale only when it constrains agent behavior
6. Preserve exactly: commands, flags, file paths, topic names, param names,
   decision rationale, cross-reference links, code blocks, tables, warnings
7. Do not reorder sections
8. Target ≥25% token reduction per file; note if not achievable without information loss
9. Never change meaning — when in doubt keep the longer phrasing

Steps:
1. Read `.claude/skills/${SKILL_NAME}/SKILL.md` in full.
2. Rewrite it applying all 9 compression rules.
3. Compute approximate reduction: (original_chars - new_chars) / original_chars.
   Target ≥25%. If not reachable without information loss, compress as far as
   possible and note why.
4. Write the compressed version back to the same path.
5. Run the full pre-commit suite (per AGENTS.md §2 — `--all-files` is the only
   acceptable pre-push command; C++ hooks require ROS 2 sourced first):
     source /opt/ros/jazzy/setup.bash
     pre-commit run --all-files
   Fix any remaining failures before proceeding.
6. Stage and commit (only the target file — do NOT use `git add -u`, which
   would bundle pre-commit housekeeping on unrelated files into this commit):
     git add .claude/skills/${SKILL_NAME}/SKILL.md
     git commit -m "docs(skills): compress ${SKILL_NAME}/SKILL.md for token efficiency"
7. Push: git push -u origin HEAD

Report format:
Skill: ${SKILL_NAME}
Branch: <branch>
Worktree: <absolute path>
Local branches: <branch>
Original chars: <N>
Compressed chars: <N>
Reduction: <N>%
Notes: <one line>
```

### Wave 2 deduplication + audit Agent prompt template

```text
You are performing deduplication and dead-reference audit across all Claude
skill files in `${OWNER}/${REPO}`.

Step 0 — Fetch Wave 1 compressed versions:
  Wave 1 pushed per-skill branches: ${WAVE1_BRANCHES} (space-separated list).
  Iterate over every branch, fetching and merging each so you see the
  compressed files:
    for branch in ${WAVE1_BRANCHES}; do
      git fetch origin "${branch}"
      git merge --no-ff "origin/${branch}" -m "merge: integrate Wave 1 compression from ${branch}" \
        || { git merge --abort; echo "Merge conflict on ${branch} — aborting."; exit 1; }
    done
  Only after merging all Wave 1 branches should you read any skill files.

Read AGENTS.md, CLAUDE.md, and all files under `.claude/skills/` after
completing Step 0.

Pass 2 — Deduplication:
- Find instruction blocks that are identical or near-identical across two or
  more skill files.
- For blocks that belong in AGENTS.md: remove from skill files, add a
  reference link.
- For blocks that belong in docs/agent-workflows/pr-resolution.md: remove from
  skill files, add a reference link (not to the `shared/per-pr-agent.md` stub).
- For blocks shared between exactly two skills and worth extracting: create
  `.claude/skills/shared/<topic>.md` and replace both with a reference link.
- Do NOT deduplicate: ground-rules recaps, scope/hard-limits sections.

Pass 3 — Dead reference audit:
- For every markdown link in every skill file, verify the target exists
  (`test -f <resolved-path>`; for `#anchor` links, grep the target file
  for the heading; for `AGENTS.md §N` links, enumerate AGENTS.md `^## `
  headings and confirm the cited number still matches).
- File a GitHub issue for each dead reference (idempotent — skip if an
  open issue with the same title already exists):
    TITLE="docs(<skill-file>): dead reference to <target>"
    if ! gh issue list --state open --search "in:title \"${TITLE}\"" --json title \
         | jq -e '.[] | select(.title == "'"${TITLE}"'")' >/dev/null; then
      gh issue create --title "${TITLE}" --body "$(cat <<'EOF'
    - **Where**: .claude/skills/<skill>/SKILL.md:<line>
    - **Link**: [text](path)
    - **Problem**: target file/section does not exist
    - **Fix**: update link to <correct-path>, or remove if content was deleted
    EOF
    )"
    fi
  Collect the created issue numbers for the report.

Commit any file changes from Pass 2 (per AGENTS.md §2 — `--all-files` is the
only acceptable pre-push command; C++ hooks require ROS 2 sourced first):
  source /opt/ros/jazzy/setup.bash
  pre-commit run --all-files
  Stage only the dedup changes — do NOT use `git add -u`, which would bundle
  unrelated pre-commit housekeeping into this commit (same rule as Wave 1):
    git add .claude/skills/
  If pre-commit auto-fixed any file under `.claude/skills/` (in scope for this
  commit), the `git add .claude/skills/` above already picks it up. If
  pre-commit auto-fixed files outside `.claude/skills/`, leave them
  unstaged — re-running `pre-commit run --all-files` after the commit must
  pass on its own so the push isn't shipping pending fixes.
  git commit -m "docs(skills): deduplicate cross-skill instructions"
  git push -u origin HEAD

Open a PR for all changes (idempotent — skip creation if a PR already exists for this branch):
  EXISTING_PR=$(gh pr list --head "$(git branch --show-current)" --json number -q '.[0].number' 2>/dev/null)
  if [ -n "$EXISTING_PR" ]; then
    PR_URL=$(gh pr view "$EXISTING_PR" --json url -q .url)
    echo "PR already exists: $PR_URL"
  else
    PR_URL=$(gh pr create --base main \
      --title "docs(skills): optimize-skills wave 2 deduplication + audit" \
      --body "Deduplication and dead-reference audit pass. Wave 1 branches merged in.")
  fi

Report format:
Deduplication:
  Blocks extracted: <N>
  Files modified: <list>

Dead references:
  Issues filed: <N>
    - #<number>: <title>
  None found: <yes/no>

Branch: <branch>
Worktree: <absolute path>
Local branches: <branch>
PR: $PR_URL
```

## Final report

After both waves complete:

```text
Optimize-skills complete.

Wave 1 — Compression:
  <skill>: <N>% reduction
  ...
  Total: <original> → <compressed> chars (<pct>%)

Wave 2 — Deduplication + audit:
  Blocks deduplicated: <N>
  Dead reference issues filed: <N>
  PR: <url from Wave 2 gh pr create>

Next step: run /resolve-my-prs to address any review comments.
```

## Ground rules

- **Preserve all information.** A 0% reduction is acceptable; information loss is not.
- **One commit per logical change** (one per compressed file, one for deduplication batch).
- **pre-commit must pass** before every push.
- **Always `--force-with-lease`** if rebasing is needed.
- **Dead references → issues, not inline fixes.** The agent filing the issue may not know where the content moved.
- When in doubt about whether a phrase is load-bearing — keep it.

## See also

- [AGENTS.md](../../../AGENTS.md) — pre-push gate and commit conventions
- [docs/agent-workflows/pr-resolution.md](../../../docs/agent-workflows/pr-resolution.md) — canonical destination for per-PR agent mechanics (`shared/per-pr-agent.md` is only a forwarding stub)
