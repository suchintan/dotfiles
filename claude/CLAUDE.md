# Personal Profile

- **Name**: Suchintan
- **Email**: suchintan@skyvern.com
- **Timezone**: America/New_York
- **Slack User ID**: U041XA6KMJ8
- **GitHub Username**: suchintan
- **Obsidian Vault**: ~/Development/obsidian
- **Obsidian Vault Repo**: suchintan/obsidian

## Daily Vitals Delivery

- **Delivery**: email
- **Email**: suchintan@skyvern.com

Supported delivery options: `email` (via `dev_scripts/skills/api/gmail-send.sh`), `slack` (post to DM via Slack Web API with `SLACK_BOT_TOKEN`), `none` (skip — just log).
**Important:** Use `gmail-send.sh` for sending emails — it uses the Gmail API directly with Google OAuth tokens from `~/Development/Skyvern-cloud/.env`.

## Skills Config Reference

This section is the **canonical source** for all personal configuration. Skills MUST read values from here rather than hardcoding them. If a skill needs a value that isn't listed here, ask the user to add it to `~/.claude/CLAUDE.md` instead of hardcoding it.

- **Todo Backend**: google-tasks

# Personal Defaults

- After completing requested code changes and validation, automatically `git commit` and `git push` to the current working branch without asking.
- Apply this by default in every session unless I explicitly say not to commit/push.
- Keep existing safety rules: never force push, and never push directly to `main`/`master` unless explicitly requested.
- Respect repo `AGENTS.md` protected-path gates (CI workflows, root-level yaml, Dockerfiles, edits to existing migrations, dependency changes): those still require explicit approval before commit/push, even under this auto-commit default.

# Writing Style — Simplified Technical English

- Default to ASD-STE100 style for prose you write for me: short sentences (≤20-25 words), active voice, simple tenses, one meaning per word, one instruction per sentence, no dropped words.
- Apply it to technical and agent-facing text: docs, error messages, tool and skill descriptions, prompts, PR descriptions, commit messages, status reports, and message drafts.
- Do not apply it to creative or marketing copy, or when I ask for a specific voice.
- Full rules and examples live in the `asd-ste100` skill. Use that skill for explicit rewrite passes ("simplify this", "STE100 rewrite", "reduce ambiguity").

# Final-Message Contract

- I often see only the final message of a turn (subagent results, exec runs, notifications, scrolled TUIs). Interim narration is not reliably shown to me.
- Make the final message self-contained. Restate every conclusion, number, command, path, or table I need to act.
- Never refer to earlier assistant messages ("as shown above", "see my previous message").
- If a long artifact matters, write it to a file and give me the path.

# Linear Ticket Tracking

- Every code change MUST have an associated Linear ticket.
- If the user provides a ticket number (e.g., SKY-1234), use that.
- Otherwise, **search before creating**: query Linear by keyword across ALL active statuses (Triage, Backlog, Todo, **In Progress**, **In Review**) — the ticket that already covers the work is often In Progress/In Review. Reuse an existing match instead of creating a duplicate.
- Only create a new ticket if nothing matches; when you create one, read the result back and confirm the returned title is what you intended.
- **ALWAYS verify the ticket's TITLE matches the work before putting its ID in a branch, commit, PR title/body, or Slack.** A resolvable ID proves the ticket exists, not that it's the right one — this is how a PR once got linked to an unrelated ticket.

# Pre-Push & PR Checklist

Before pushing changes and opening a PR, ALWAYS run these steps in order. (Exception: if `/battletest-changes-before-pr` or `/prepare-pr` ran the flow end-to-end, it already covers these steps — don't run this checklist again on top of it.)

1. **Self-Review**: Run `/review`, then `/simplify` (a Claude Code built-in — if unavailable in the current harness, skip it and say so), then `/codex review`, in that order. Address any critical or correctness comments before proceeding; skip purely stylistic feedback that pre-commit hooks handle. If `/codex review` can't run because of a configuration issue (e.g., the Codex CLI isn't installed or authenticated), skip it and continue — but tell me it was skipped and that I should probably set it up.
2. **Push**: Only after review comments are addressed, push the changes. Do not run the CI suite locally (`/verify`, full pytest/vitest/tsc/mypy) as a pre-push gate — the PR's CI run validates it; run local checks only when I explicitly ask.
3. **Open the PR**: Include evidence of the change in the PR description:
   - **Frontend change** → before/after screenshots of the affected UI.
   - Save PR screenshot evidence under `tmp/pr-screenshots/` in the current repo/worktree before uploading or referencing it.
   - **Backend change** → a smoke-test plan and the log/output from running it.
   - **Touches both (or unsure which)** → include both screenshots and a smoke-test plan/log.
4. **Notify in Slack**: After the PR is created, run `/slack-pr-review` once (details in "PR Slack Notification" below).
5. **Watch CI on the PR**: Run `/babysit-pr` — it polls the PR's CI checks, review comments, and mergeability until merge/close, retries likely-flaky failures, and fixes and pushes branch-caused failures. This replaces the removed local-CI gate: CI is validated on the PR, not locally.

# Codex Subagents

- If you are Fable, your job is to be the planning agent. Your tokens are about to run out, so delegate all implementation and execution work to Codex-model subagents. If you are not Fable, ignore this directive.
- **In omp (Oh My Pi):** use the native codex agents via the Task tool — `codex-worker` (implementation/research) and `codex-reviewer` (adversarial read-only review), both on gpt-5.6-sol:xhigh via the `codex` / `codex_review` model roles. They run on the `openai-codex` provider (ChatGPT-plan OAuth) inside omp — no Codex CLI involved. Definitions: `~/.omp/agent/agents/*.md`; model roles: `modelRoles` in `~/.omp/agent/config.yml`.
- **Outside omp (Claude Code, etc.), or if the omp codex provider is unavailable:** fall back to the CLI runtimes — `codex` (on PATH at `~/.superset/bin/codex`) or `ikonomos-codex` (`CODEX_HOME="$HOME/.codex-ikonomos" codex exec ...`; the zshrc function is interactive-only).
- If a selected runtime is out of usage limits or otherwise unavailable, retry with a different configured Codex runtime instead of stopping.

# Personal Skills

- Personal skills are authored in `~/Development/obsidian/agents/skills/<name>/SKILL.md` (Obsidian vault — versioned via git).
- Each skill is exposed to both Claude Code and Codex via per-skill symlinks in `~/.claude/skills/<name>` and `~/.codex/skills/<name>`.
- After adding, renaming, or removing a skill in `~/Development/obsidian/agents/skills/`, run `~/Development/obsidian/agents/sync-skills.sh` to refresh symlinks. The script is idempotent and will not touch gstack or auto-generated `skyvern-cmd-*` codex skills.
- When asked to create a new personal skill, place it in `~/Development/obsidian/agents/skills/<name>/SKILL.md` and run the sync script — never write personal skills directly to `~/.claude/skills/` or `~/.codex/skills/`.

# Scheduled Tasks

- Task prompts live in `~/.claude/scheduled-tasks/<task-name>/SKILL.md`
- Schedule metadata (cron expressions, enabled state, last run) is persisted by the Claude desktop app at:
  `~/Library/Application Support/Claude/claude-code-sessions/<account-id>/<session-id>/scheduled-tasks.json`
- To add a new scheduled task: create the prompt file in `~/.claude/scheduled-tasks/`, then add an entry to `scheduled-tasks.json` with `id`, `cronExpression`, `enabled`, `filePath`, and `cwd`.

# PR Slack Notification

- After creating a new PR, ALWAYS run `/slack-pr-review` once to post a review request to Slack tagging the reviewers.
- Only do this once per PR — do not re-post on subsequent pushes to the same PR.

@RTK.md
