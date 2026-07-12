---
name: compress-docs
description: Rewrite docs to be dense and agent-readable — strip filler prose, collapse redundant explanations, preserve all facts/commands/file paths. No information loss, just tighter writing. Commits the result so the review loop catches regressions.
---

# compress-docs

Rewrites documentation files to minimize token cost without losing information. Every fact, command, file path, parameter name, and decision rationale is preserved — only the prose wrapping it is stripped.

## When to use

- Before a bulk `/resolve-my-issues` or `/resolve-my-prs` run to reduce per-agent context load.
- After adding a large new doc that grew organically and is wordier than needed.
- Periodically as a maintenance pass.

Not for rewriting skill files.

## Scope

Targets these files (all in this repo):

- `docs/*.md` — all files in the docs directory
- `AGENTS.md` — agent playbook (most frequently loaded, highest token impact)
- `CLAUDE.md` — project reference
- `CONTRIBUTING.md` — coding conventions
- `README.md` — top-level readme

Narrow scope with an optional argument:

- `/compress-docs` — all files above
- `/compress-docs agents` — AGENTS.md only
- `/compress-docs docs` — docs/*.md only
- `/compress-docs claude` — CLAUDE.md only

## Compression rules (agents must follow these exactly)

These rules define what "compress" means. Apply all of them:

1. **Strip filler phrases.** Remove: "It is important to note that", "Please be aware that", "In order to", "It should be mentioned that", "As mentioned above", "Note that", "Keep in mind that". Replace with the bare claim.

2. **Collapse redundant restatements.** If the same fact appears in two consecutive sentences or paragraphs, keep the more specific one and drop the other.

3. **Convert prose lists to bullet/table form.** "X does A, B, and C" → `- A\n- B\n- C`. Numbered steps stay numbered; unordered items become bullets.

4. **Shorten section headers.** "How to configure the EKF sensor fusion parameters" → "EKF config". Headers should be ≤5 words.

5. **Drop motivational language.** "This is really useful because..." / "The reason we chose X is that it gives us great flexibility..." → state the fact. Rationale is kept only when it is a constraint an agent needs to make correct decisions (e.g. "Use --force-with-lease not --force — plain --force overwrites concurrent pushes").

6. **Preserve exactly:**
   - Every command, flag, and argument
   - Every file path, line number, and topic name
   - Every parameter name and its value/unit
   - Every decision rationale that constrains agent behavior
   - Every cross-reference link (markdown `[text](path)`)
   - All code blocks verbatim
   - Tables (may reformat columns but not drop rows)
   - Warning/danger callouts

7. **Do not reorder sections.** Agents and humans have muscle memory for section order. Only compress within sections.

8. **Target: ≥25% token reduction per file.** If a file cannot reach 25% without losing information, compress as far as possible and note it in the report. Do not fabricate compression by dropping real content to hit the target.

9. **Never change meaning.** When in doubt between two phrasings, keep the longer one. The goal is removing words that add zero information, not paraphrasing.

## Pre-flight (outer orchestrator)

1. Auth:

   ```bash
   gh auth status
   ```

2. Identify repo:

   ```bash
   OWNER=$(gh repo view --json owner -q .owner.login)
   REPO=$(gh repo view --json name -q .name)
   ```

3. Fetch main:

   ```bash
   git fetch origin main
   ```

## Agent dispatch

First, enumerate the concrete file list from the scope (resolve globs at invocation time):

```bash
# Default scope — all files above; adjust if a narrowing arg was passed
mapfile -t FILES < <(find docs/ -maxdepth 1 -name '*.md' | sort)
FILES+=(AGENTS.md CLAUDE.md CONTRIBUTING.md README.md)
```

If a narrowing arg was given (e.g. `/compress-docs docs`), set `FILES` to only that subset before dispatching.

Dispatch **one Agent per file** in parallel (cap at `MAX_CONCURRENT = 4`). Batch the file list: dispatch the first min(4, remaining) files in one message, await all completions, then repeat until all files are processed. Each call MUST use:

- `subagent_type: "general-purpose"`
- `isolation: "worktree"` — agent gets its own worktree off `origin/main`
- `run_in_background: true`

Each agent receives the prompt below with `${FILE}`, `${OWNER}/${REPO}` filled in.

### Per-file Agent prompt template

```text
You are compressing `${FILE}` in `${OWNER}/${REPO}` to reduce token cost
without losing information.

Rules (follow all of them — read the full list in
.claude/skills/compress-docs/SKILL.md before starting):

1. Strip filler phrases (e.g. "It is important to note that", "In order to")
2. Collapse redundant restatements — keep the more specific one
3. Convert prose lists to bullet/table form
4. Shorten section headers to ≤5 words
5. Drop motivational language; keep rationale only when it constrains agent behavior
6. Preserve exactly: commands, flags, file paths, topic names, param names,
   decision rationale, cross-reference links, code blocks, tables, warnings
7. Do not reorder sections
8. Target ≥25% token reduction; note if not achievable without information loss
9. Never change meaning — when in doubt, keep the longer phrasing

Steps:
1. Read the current file in full.
2. Rewrite it applying all rules above.
3. Count approximate token reduction: (original_chars - new_chars) / original_chars.
   If < 25%, note why in the report.
4. Write the compressed version back to the same path.
5. Stage and commit:
   git add ${FILE}
   git commit -m "$(cat <<'EOF'
docs: compress ${FILE} for token efficiency

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
6. Push:
   if ! pre-commit run --all-files; then
     if ! git diff --quiet; then
       git add -u && git commit --amend --no-edit || exit 1
       pre-commit run --all-files || exit 1
     else
       exit 1
     fi
   fi
   git push -u origin HEAD

Pre-push note: `markdownlint --fix`, `trailing-whitespace`, and `end-of-file-fixer`
mutate files in-place and exit non-zero on first run; `check-yaml`, `validate-track-configs`,
and `pytest-hooks` may fail without modifying any file. The block above follows the
AGENTS.md §2 "Concurrent-push gate" pattern: non-auto-fixable failures cause `exit 1`;
auto-fixable changes are re-staged and amended before re-running to confirm clean.

Report format:
File: ${FILE}
Branch: $(git branch --show-current)
Worktree: <absolute worktree path>
Original chars: <N>
Compressed chars: <N>
Reduction: <N>%
Notes: <one line — e.g. "hit 31% reduction" or "capped at 18%: all remaining prose is load-bearing rationale">
```

## Collecting results

After all agents report back:

0. **Handle partial failure.** Collect all agent reports. An agent that crashed, failed pre-commit, or failed to push will not produce a valid `Branch:` line. For each such agent, note the file as `SKIPPED`. If any files were skipped, include them in the PR body under a `## Skipped files` heading with a one-line reason per file. Do not silently omit skipped files. If all agents failed, abort and print the list of failures instead of opening a PR.

1. Aggregate all branches. Each agent pushed its own branch. The outer orchestrator cherry-picks all agent commits onto a single dedicated branch and then opens one PR:

   ```bash
   # Create a single integration branch
   git checkout -b docs/compress-batch origin/main
   # Fetch all agent branches (they exist on origin, not as local refs)
   git fetch origin
   # Cherry-pick each agent's commit (collect branch names from agent reports)
   git cherry-pick origin/<agent-branch-1> || { git cherry-pick --abort; exit 1; }
   git cherry-pick origin/<agent-branch-2> || { git cherry-pick --abort; exit 1; }
   # ... repeat for each agent branch
   git push -u origin docs/compress-batch
   gh pr create \
     --base main \
     --head docs/compress-batch \
     --title "docs: compress documentation for token efficiency" \
     --body "Batch compression pass. No information removed — only filler prose, redundant restatements, and motivational language stripped. See per-file reduction stats in the PR description."
   ```

   If cherry-pick conflicts arise (two agents edited overlapping lines), resolve manually keeping both compressions, then continue.

2. Print final report:

```text
Compress-docs complete.

Files processed: <N>
Total reduction: <original_total_chars> → <compressed_total_chars> (<pct>%)

Per-file:
  AGENTS.md:       <N>% reduction
  CLAUDE.md:       <N>% reduction
  CONTRIBUTING.md: <N>% reduction
  README.md:       <N>% reduction
  docs/...:        <N>% reduction
  ...

PR: <url or 'none — all files were already compact'>
```

## Ground rules

- **Preserve all information.** A 0% reduction is acceptable; information loss is not.
- **One commit per file** — clean history, easy to revert a single file if the compression went too far.
- **pre-commit must pass** before pushing. Fix hook failures; do not skip.
- **Always `--force-with-lease` if rebasing is needed**, never `--force`.
- When in doubt about whether a phrase is load-bearing — keep it.

## See also

- [AGENTS.md](../../../AGENTS.md) — pre-push gate and commit conventions
