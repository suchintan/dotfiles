@/Users/suchintan/.codex/RTK.md

# Personal Profile

- **Name**: Suchintan
- **Email**: suchintan@skyvern.com
- **Timezone**: America/New_York
- **Slack User ID**: U041XA6KMJ8
- **GitHub Username**: suchintan
- **Obsidian Vault**: ~/Development/obsidian
- **Obsidian Vault Repo**: suchintan/obsidian

## Skills Config Reference

- `~/.claude/CLAUDE.md` § "Skills Config Reference" is the single canonical source for personal configuration (todo backend, vitals delivery, etc.). Skills MUST read values from there rather than hardcoding them. If a needed value is missing, ask the user to add it there — never fork a second copy here.

# Personal Defaults

- Git safety: never force push; never push directly to `main`/`master` unless explicitly requested; never amend commits on shared branches.
- Respect repo `AGENTS.md` protected-path gates (CI workflows, root-level yaml, Dockerfiles, edits to existing migrations, dependency changes): those require explicit approval before commit/push.
- Spawned Codex worker subagents must NOT run git at all (no add/commit/amend/push) — the orchestrating session owns git. (A worker once amended a pushed commit and force-pushed a PR that was under review.)
- In interactive sessions, after completing requested code changes, `git commit` and `git push` to the current working branch without asking (subject to the gates above), unless the user says not to.

# User-Facing Writing

- Before drafting or revising prose for people, read and apply the `writing-user-facing-content` skill. This includes Notion documents, Slack messages, emails, customer updates, announcements, and similar content.
- Use the skill with the requested voice and channel. For technical prose, apply it together with the ASD-STE100 guidance in `~/.claude/CLAUDE.md`.

# Linear Ticket Tracking

- Every code change MUST have an associated Linear ticket.
- If the user provides a ticket number (e.g., SKY-1234), use that.
- Otherwise, **search before creating**: query Linear by keyword across ALL active statuses (Triage, Backlog, Todo, **In Progress**, **In Review**) — the ticket that already covers the work is often In Progress/In Review. Reuse an existing match instead of creating a duplicate.
- Only create a new ticket if nothing matches; when you create one, read the result back and confirm the returned title is what you intended.
- **ALWAYS verify the ticket's TITLE matches the work before putting its ID in a branch, commit, PR title/body, or Slack.** A resolvable ID proves the ticket exists, not that it's the right one.

# Pre-Push & PR Checklist

Before pushing changes and opening a PR, ALWAYS run these steps in order. (Exception: if `/battletest-changes-before-pr` or `/prepare-pr` ran the flow end-to-end, it already covers these steps — don't run this checklist again on top of it. If a referenced skill isn't available in the current tool, do the equivalent manually and flag it.)

1. **Self-Review**: Review the full diff before pushing (under Codex, use its native review; under Claude Code, `/review` → `/simplify` → `/codex review`). Address critical and correctness findings; skip purely stylistic feedback that pre-commit hooks handle.
2. **Push**: Only after review comments are addressed, push the changes. Do not run the CI suite locally (`/verify`, full pytest/vitest/tsc/mypy) as a pre-push gate — the PR's CI run validates it; run local checks only when I explicitly ask.
3. **Open the PR**: Include evidence of the change in the PR description:
   - **Frontend change** → before/after screenshots of the affected UI.
   - Save PR screenshot evidence under `tmp/pr-screenshots/` in the current repo/worktree before uploading or referencing it.
   - **Backend change** → a smoke-test plan and the log/output from running it.
   - **Touches both (or unsure which)** → include both screenshots and a smoke-test plan/log.
4. **Notify in Slack**: After the PR is created, run `/slack-pr-review` once (details in "PR Slack Notification" below).
5. **Watch CI on the PR**: Run `/babysit-pr` — it polls the PR's CI checks, review comments, and mergeability until merge/close, retries likely-flaky failures, and fixes and pushes branch-caused failures. This replaces the removed local-CI gate: CI is validated on the PR, not locally.

# Codex Subagents

- When using Codex subagents, run each subagent through one of the configured Codex runtimes: `codex` (on PATH at `~/.superset/bin/codex`) or `ikonomos-codex` (a `~/.zshrc` function — interactive shells only).
- If a selected runtime is out of usage limits or otherwise unavailable, retry with a different configured Codex runtime instead of stopping.

# Claude CLI Consults

- When consulting `claude` from Codex, keep Claude's built-in tools available by default. Do not pass `--tools ""` just to avoid subagents.
- If Claude appears broken because of custom agents, subagents, hooks, plugins, or slash commands, run it with `--safe-mode --disable-slash-commands --no-session-persistence` and a bounded shell `timeout`; this disables customizations while preserving built-in tools.
- Prefer a command shape like `timeout 180s claude --safe-mode --disable-slash-commands --no-session-persistence --permission-mode dontAsk -p "<prompt>"`.

# Personal Skills

- Personal skills are authored in `~/Development/obsidian/agents/skills/<name>/SKILL.md` (Obsidian vault — versioned via git).
- Each skill is exposed to both Claude Code and Codex via per-skill symlinks in `~/.claude/skills/<name>` and `~/.codex/skills/<name>`.
- After adding, renaming, or removing a skill in `~/Development/obsidian/agents/skills/`, run `~/Development/obsidian/agents/sync-skills.sh` to refresh symlinks. The script is idempotent and will not touch gstack or repo-owned Codex-only skills.
- When asked to create a new personal skill, place it in `~/Development/obsidian/agents/skills/<name>/SKILL.md` and run the sync script — never write personal skills directly to `~/.claude/skills/` or `~/.codex/skills/`.

# PR Slack Notification

- After creating a new PR, ALWAYS run `/slack-pr-review` once to post a review request to Slack tagging the reviewers.
- Only do this once per PR — do not re-post on subsequent pushes to the same PR.
