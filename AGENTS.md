# AGENTS.md

Agent-agnostic playbook for `RobotX-Workshops/tello-sim`. Claude skills,
Codex, and any future agent read this file directly — it is the single
source of truth for per-PR and per-issue mechanics. Skills under
`.claude/skills/` are thin adapters and must not restate these commands.

Section numbers are stable. Other documents cite them (`AGENTS.md §5
Step 6`); renumbering breaks those references.

## Project shape

Pure-Python drone simulator. No ROS, no compiled packages, no monorepo.

| Fact | Value |
| --- | --- |
| Package | `tello_sim/` |
| Client | `tello_sim_client.py`, `simulator_client.py`, `sim_connection.py` (repo root) |
| Examples | `examples/` |
| Interpreter | `./venv/bin/python` (Python 3.13) |
| Runtime deps | `requirements.txt` — ursina, PyOpenGL, numpy, opencv-python |
| Test suite | **none yet** |
| Lint config | **none** — `ruff` runs on its defaults |
| Default branch | `main` |

Files that do **not** exist in this repo, despite being referenced by
ported skills: `CLAUDE.md`, `CONTRIBUTING.md`, `.pre-commit-config.yaml`,
`pyproject.toml`, `bin/`, `.github/copilot-instructions.md`. Do not follow
instructions to read them; do not invent them. Anything ROS-flavoured
(`colcon`, `ament_*`, `car.launch.py`, `source ROS`) is residue from the
upstream `tron-roboracer` port and does not apply here.

## §1 Auth

```bash
gh auth status                                  # must be logged in
ME=$(gh api user -q .login)
OWNER=$(gh repo view --json owner -q .owner.login)
REPO=$(gh repo view --json name  -q .name)
```

Use `$ME` rather than `@me` — `@me` re-resolves per request and can drift
if auth context changes mid-run. `gh pr list` / `gh issue list` derive the
repo automatically; `gh api repos/...` needs `$OWNER` / `$REPO` spelled out.

## §2 Pre-push gate

Run before **every** push, including rebase-only and amend-only pushes.
Never bypass with `--no-verify`. Never silence a failure by deleting a
test, loosening a lint rule, or disabling a check — fix the cause.

```bash
# 1. Syntax / import-time integrity across everything we ship.
./venv/bin/python -m compileall -q \
  tello_sim tello_sim_client.py simulator_client.py sim_connection.py examples

# 2. Lint. No repo config, so ruff uses its defaults. The shipped tree
#    is NOT ruff-clean (see the baseline table below), so a whole-tree
#    run reports pre-existing findings. Gate on your diff, not the tree:
ruff check --output-format=concise $(git diff --name-only origin/main -- '*.py')
#    NOTE: `git diff --name-only` does not list *untracked* files, so a new
#    module you have not `git add`ed yet is silently skipped. If your change
#    adds files, `git add` them first or pass them to ruff explicitly.
#    A whole-tree `ruff check tello_sim *.py examples` is still useful to
#    eyeball, but read it against the baseline below.

# 3. Targeted runtime check — only for the modules you touched, and only
#    those that import cleanly headless (ursina opens a window). Derive
#    the list from your diff rather than hard-coding it:
#      for m in $(git diff --name-only origin/main -- 'tello_sim/*.py'); do ... ; done
#    ursina_adapter is the one module that imports package-qualified, so
#    it stands in as the example here — substitute the modules you edited:
./venv/bin/python -c 'import tello_sim.ursina_adapter'
```

Step 3 is deliberately narrow because the package does **not** import
uniformly. `tello_sim.ursina_adapter` is the only module that imports
cleanly package-qualified. `command_server.py`, `tello_drone_sim.py`, and
`run_sim.py` use flat sibling imports (`from ursina_adapter import
UrsinaAdapter`), so `import tello_sim.command_server` raises
`ModuleNotFoundError: No module named 'ursina_adapter'`. Import those from
inside `tello_sim/` instead:

```bash
(cd tello_sim && PYTHONPATH=. ../venv/bin/python -c 'import command_server')
```

Do not rewrite those imports to make step 3 uniform — `run_sim.py` is
launched from inside the package and the flat form is what it relies on.
That refactor is its own PR.

**The tree is not ruff-clean.** These findings pre-date the current work
and are present on `origin/main`:

| Finding | Location |
| --- | --- |
| `F403` star-import from ursina | `tello_sim/command_server.py:5` |
| `F401` unused `time` | `examples/3_drone_information.py:2` |
| `F401` unused `typing.cast` | `examples/6_record_video.py:4` |

The gate is therefore **"no new findings in the files you touched"**, not
a clean tree. Compare against the baseline rather than the absolute count:

```bash
ruff check --output-format=concise $(git diff --name-only origin/main -- '*.py')
```

Clearing a pre-existing finding you happen to be next to is fine. Do not
turn a review-resolution PR into a repo-wide lint sweep — that belongs in
its own PR.

There is no test suite. If your change adds testable non-graphical logic,
adding tests is welcome but is not gated — say so in the PR body rather
than claiming a suite ran.

Auto-fixable lint (`ruff check --fix`) may be applied and committed.
Non-auto-fixable **new** failures block the push.

### §2.1 Detect concurrent commits before `--force-with-lease`

Applies whenever a push rewrites history (amend, rebase, squash) on a
branch that already exists on `origin` — i.e. every review-resolution
round. It does **not** apply to the first `git push -u` of a
never-pushed branch.

`--force-with-lease` compares against your *remote-tracking* ref, so a
stale `origin/<branch>` makes the lease vacuously true and you can
clobber a commit someone (or another agent) pushed while you worked.
Refresh the ref first, then confirm nothing new arrived:

```bash
git fetch origin "$BRANCH"
LOCAL_BASE=$(git rev-parse "origin/$BRANCH")
# ... your amend / rebase happens here ...
git fetch origin "$BRANCH"
if [ "$(git rev-parse "origin/$BRANCH")" != "$LOCAL_BASE" ]; then
  echo "origin/$BRANCH moved underneath us — re-read before pushing"; exit 1
fi
git push --force-with-lease origin "HEAD:$BRANCH"
```

Always `--force-with-lease`, never bare `--force`.

## §3 CI workflows

Two workflows, both unconditional on path — every PR triggers both.

**`Claude Code Review`** (`.github/workflows/claude-code-review.yml`)
— triggers on `pull_request` `[opened, synchronize]`. Job `secrets-gate`
checks for `CLAUDE_CODE_OAUTH_TOKEN` and emits `ok`; job `claude-review`
runs only when `ok == 'true'` (so it is a no-op skip until the secret is
set, and on fork PRs which get no secrets). It posts an adversarial
review as a PR comment whose first line is machine-parsed:

```text
<!-- bot-review-marker: claude blocking=N nonblocking=N suspect=N sha=<7-char-short> -->
```

The reviewer brief is `.claude/prompts/adversarial_reviewer.md`.

**`Bot Blocking Gate`** (`.github/workflows/bot-blocking-gate.yml`)
— triggers on `pull_request_target` `[opened, synchronize, reopened]` and
on `workflow_run` completion of *Claude Code Review*. It parses the latest
marker on the current head SHA and POSTs a check-run named **`Bot Blocking
Gate`** to that SHA. Fails closed on `blocking>0`, a malformed marker, a
missing marker, or while the review is still running; passes on
`blocking=0`, and on fork PRs where `claude-review` legitimately skipped.

Two naming traps:

- The POSTed check-run is `Bot Blocking Gate`. The job-level check is
  `gate`. Branch protection must require the former.
- Because both triggers load the workflow from the **default branch**, a
  fix to `bot-blocking-gate.yml` only takes effect once merged to `main`.
  A PR cannot fix its own gate.

`main` currently has **no required status checks** configured, so a red
`gate` does not block merge today. `docs/claude_code_review.md` covers
token setup and how to make the gate required.

## §4 Commit and PR conventions

- Conventional-commit subjects: `type(scope): summary`, imperative, ≤70
  chars. Types in use: `feat`, `fix`, `docs`, `perf`, `refactor`, `chore`.
- Stage explicit paths. Never `git add -A`.
- Branch from `origin/main`, never from another feature branch.
- PRs open **ready-for-review**, not draft — the bots need a non-draft PR.
- Co-author trailer on agent-authored commits:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- PR bodies end with:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- Heredoc PR bodies must start at column 0, or the whole body renders as
  a code block and `Closes #N` stops being detected as a closing keyword.

## §5 Review-thread resolution

Applies to threads from **every** reviewer — CodeRabbit, Copilot,
`claude[bot]`, and humans all count equally.

### Step 1 — enumerate unresolved threads

```bash
gh api graphql -f query='
  query($o:String!,$r:String!,$n:Int!,$c:String){repository(owner:$o,name:$r){
    pullRequest(number:$n){reviewThreads(first:100,after:$c){
      pageInfo{hasNextPage endCursor} nodes{
      id isResolved isOutdated path line
      comments(first:20){nodes{author{login} body}}}}}}}' \
  -f o="$OWNER" -f r="$REPO" -F n="$PR" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[]
         | select(.isResolved==false)]'
```

`first:100` is one page. A PR with more than 100 threads truncates
silently, so a partial page can falsely read as "zero unresolved". When
`pageInfo.hasNextPage` is `true`, re-run passing `-f c="<endCursor>"`
and accumulate the pages before deciding. The same applies to Step 6.

Thread `id` values are opaque node IDs (`PRRT_...`) — carry them through;
they are the handle for Step 5.

### Step 2 — assess each thread (verdict table)

Mirrors `.claude/prompts/adversarial_implementer.md`. Pick exactly one:

| Verdict | When | Action |
| --- | --- | --- |
| **fix** | The finding is real | Edit the code. Record `FIXED <file:line> — <what changed>` |
| **already-fixed** | A prior commit in this PR addressed it | Record `ALREADY-FIXED <file:line> — <where>` |
| **push-back** | False positive, by design, or contradicts repo convention | Reply with evidence — cite `file:line` or the doc section that disproves it. Record `PUSH-BACK <file:line> — <reason> — <citation>` |

"I disagree" is not a reply. Capitulating by default pollutes the
codebase; being defensive by default leaves real bugs in. Converge on
real defects. `SUSPECT`-labelled findings must be investigated, but the
bar for changing code is "I confirmed the smell is real".

Bot suggestions that contradict this repo's documented conventions are
push-backs, not fixes — cite the section here in AGENTS.md.

### Step 3 — commit the fixes

Group related fixes; do not make one commit per comment. Run the §2
pre-push gate.

### Step 4 — reply to each thread

Every thread gets a reply before it is resolved, so the record shows why:

```bash
gh api graphql -f query='
  mutation($t:ID!,$b:String!){
    addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$t, body:$b}){
      comment{id}}}' \
  -f t="$THREAD_ID" -f b="$REPLY_BODY"
```

### Step 5 — resolve each thread

```bash
gh api graphql -f query='
  mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}' \
  -f t="$THREAD_ID"
```

Resolve threads you fixed **and** threads you pushed back on — an
unresolved thread is an open question, and a reasoned push-back is an
answer. Leave a thread unresolved only when it genuinely needs the user.

### Step 6 — verify zero unresolved threads

Mandatory before reporting. Re-run the Step 1 query and assert the result
is empty:

```bash
gh api graphql -f query='
  query($o:String!,$r:String!,$n:Int!,$c:String){repository(owner:$o,name:$r){
    pullRequest(number:$n){reviewThreads(first:100,after:$c){
      pageInfo{hasNextPage endCursor} nodes{isResolved}}}}}' \
  -f o="$OWNER" -f r="$REPO" -F n="$PR" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[]
         | select(.isResolved==false)] | length'
```

As in Step 1, this is one page of 100. If `pageInfo.hasNextPage` is
`true`, page through with `-f c="<endCursor>"` and sum the counts —
a zero on the first page alone does **not** prove the PR is clean.

A non-zero count means the PR is not done. Either finish the remaining
threads or report `blocked-<reason>` naming them. Never report success
with threads still open.

### Step 7 — push

Per §2 and §2.1. Pushing a new head SHA invalidates every bot marker on
the old SHA, so the gate re-evaluates and the bots re-review. That is
expected — do not wait for the new round in a bulk run (see the
no-waiting-on-CI rule in `docs/agent-workflows/pr-resolution.md`).

### Idempotency when posting comments

A network blip after a successful POST but before the ack must not
double-post. Before posting an issue-level comment, check for an
identical body from `$ME` in the last 60s. Pipe to a real `jq` with
`--arg` — comment bodies contain quotes, backticks, and newlines that
break a shell-interpolated `gh api --jq` filter (which accepts a single
filter and does not proxy jq's `--arg`):

```bash
existing=$(gh api --paginate "repos/$OWNER/$REPO/issues/$N/comments?per_page=100" \
  | jq -s 'add' \
  | jq -r --arg me "$ME" --arg body "$BODY" \
      '[.[] | select(.user.login == $me and .body == $body
        and ((.created_at | fromdateiso8601) > (now - 60)))][0].html_url // empty')
[ -z "$existing" ] && gh issue comment "$N" --body "$BODY"
```

## §6 Conflict resolution

Default to **rebase** onto `origin/main` for PR branches:

```bash
git fetch origin main
git rebase origin/main
```

On conflict: resolve the markers, `git add <file>`, then
`git rebase --continue`. **Not** `git commit` — that is the merge-workflow
reflex and it breaks a rebase.

```bash
git merge origin/main      # merge alternative
# resolve markers, then:
git add <file> && git commit
```

Use merge only when the branch is shared with another person or agent and
rewriting its history would disrupt them.

Resolve conflicts on the merits — read both sides. If a conflict is
genuinely ambiguous (two intentional changes to the same logic, and the
correct combination is a judgment call), stop and report
`blocked-ambiguous` with the `file:line` and the question. Do not guess,
and do not blanket `--ours` / `--theirs`.

After any rebase, push unconditionally per §2.1 — do not try to detect
whether the rebase was a no-op.

## §7 Ground rules

- Never bypass a check: no `--no-verify`, no deleting or skipping tests,
  no loosening lint rules, no removing a required status check.
- Never plain `--force`. Always `--force-with-lease`.
- Ambiguity → stop and report `blocked-<reason>` with a concrete "what I'd
  need to know". A vapor PR is worse than no PR.
- Stage explicit paths; never `git add -A`.
- Skip any branch already checked out in another worktree unless the
  orchestrator explicitly directs reuse.
- When in doubt, ask. Don't guess.

## See also

- [docs/agent-workflows/pr-resolution.md](docs/agent-workflows/pr-resolution.md) — bulk + single PR resolution contract
- [docs/claude_code_review.md](docs/claude_code_review.md) — review bot token setup, gate enforcement
- [.claude/prompts/adversarial_reviewer.md](.claude/prompts/adversarial_reviewer.md) — reviewer brief
- [.claude/prompts/adversarial_implementer.md](.claude/prompts/adversarial_implementer.md) — implementer stance
