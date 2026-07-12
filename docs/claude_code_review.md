# Claude Code Review Workflow

The automated review process (ported from
[RobotX-Workshops/tron-roboracer](https://github.com/RobotX-Workshops/tron-roboracer))
has two workflows:

- **`Claude Code Review`** (`.github/workflows/claude-code-review.yml`) runs
  [`anthropics/claude-code-action`](https://github.com/anthropics/claude-code-action)
  on every pull request (`opened` and `synchronize`) and posts an adversarial
  review as a PR comment. The reviewer brief lives in
  `.claude/prompts/adversarial_reviewer.md`; the first line of every review is
  a machine-readable marker:
  `<!-- bot-review-marker: claude blocking=N nonblocking=N suspect=N sha=<short> -->`
- **`Bot Blocking Gate`** (`.github/workflows/bot-blocking-gate.yml`) parses
  that marker and POSTs a check-run named `Bot Blocking Gate` to the PR's head
  SHA: failure while `blocking>0` (or while the review is still running /
  missing), success once a review on the current head SHA reports
  `blocking=0`. Bot reviews are only comments — this check is what gives the
  "Blocking" findings teeth at the GitHub layer.

## 1. Generate a Claude Code OAuth token

**Prerequisite:** a Claude.ai account with Claude Code access (a Pro, Max, or
Team subscription, or an account with Anthropic API billing enabled).

1. Install the Claude Code CLI locally if you don't already have it:

   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. Run the token-setup command and follow the browser OAuth flow:

   ```bash
   claude setup-token
   ```

   The CLI prints a long-lived OAuth token. Copy it — it will not be shown
   again. Rotate it yearly, or immediately if you suspect it has leaked.

## 2. Store the token as a GitHub secret

1. In the GitHub repository, go to **Settings → Secrets and variables →
   Actions**.
2. Add a repository secret named `CLAUDE_CODE_OAUTH_TOKEN` with the token as
   its value. (For multiple repos, use an organization secret instead.)

Until the secret exists, the review job skips (the `secrets-gate` job emits
`ok=false`) and the gate passes fork PRs by absence.

## 3. Make the gate required (branch protection)

The gate only blocks merges once branch protection requires it. In
**Settings → Branches → Branch protection rules** for `main`, enable
**Require status checks to pass** and add the check named exactly
**`Bot Blocking Gate`** — the POST'd check-run name, *not* the job name
`gate`. Equivalent CLI:

```bash
gh api -X PUT repos/RobotX-Workshops/tello-sim/branches/main/protection/required_status_checks/contexts \
  --input - <<< '["Bot Blocking Gate"]'
```

Note: the gate's `workflow_run` trigger uses the workflow definition on the
default branch, so require the check only **after** `bot-blocking-gate.yml`
has been merged to `main` — otherwise open PRs wait on a check that can never
report.

## 4. Verify

1. Open a new pull request, or push a commit to an existing one.
2. Under the **Actions** tab, watch **Claude Code Review** run, then **Bot
   Blocking Gate** re-evaluate when it completes.
3. The PR checks section should show `Bot Blocking Gate` — green when the
   latest review on the head SHA reports `blocking=0`.

## Rotating or revoking the token

1. Run `claude setup-token` again to mint a fresh token.
2. Update the `CLAUDE_CODE_OAUTH_TOKEN` secret with the new value.
3. Sign out of the old Claude Code session at <https://claude.ai/settings> to
   invalidate the previous token.

## Troubleshooting

- **Workflow fails with 401 / authentication error:** the secret is missing,
  misnamed, expired, or revoked. Re-run `claude setup-token` and update it.
- **No review comment appears on the PR:** check the workflow logs — the
  action will not call `gh pr comment` if it could not authenticate or the
  prompt produced no output. The workflow needs `pull-requests: write` and
  `issues: write`, both already declared in the YAML.
- **Gate stuck on "Awaiting Claude Code Review":** expected right after a
  push; it re-evaluates automatically when the review completes. If it
  persists past ~10 minutes, check the Claude Code Review run.
- **Gate fails with "No bot review marker":** the review ran but its comment
  is missing the marker line (or was deleted), or the marker's `sha=` doesn't
  match the current head. Re-run the Claude Code Review workflow.
