# AGENTS.md

Read `CLAUDE.md` for this repository's agent instructions.

## Secrets Policy

This repository is PUBLIC. Treat every committed byte as permanently world-readable.

- Never commit secret values: API keys, tokens, passwords, private keys, certificates, cookies, or `.env` contents.
- Environment variable *names* are fine. Values are not.
- Commit secret-bearing configs only as `*.template` files with placeholder values. Keep the real files local and listed in `.gitignore` (`codex/config.toml`, `claude/mcp_servers.json`).
- Keep local secrets in `~/.zshrc_secrets`, `~/.codex/config.toml`, and `~/.claude.json`. Never copy their contents into this repository. Never read `~/.zshrc_secrets`.
- Before you commit: scan the staged diff for secret patterns (`ghp_`, `gho_`, `sk-`, `AKIA`, `xox`, `-----BEGIN`, `api_key`, `secret`, `password`).
- Before you push: run `trufflehog git "file://$PWD" --no-update` and require zero new findings.
- Known historical finding: one GitHub PAT in `bash/.zshrc` history (added and removed 2021-11-03, commits `f460b6e`/`69a33f7`). It is revoked and returns HTTP 401 (verified 2026-08-09). Do not re-report it. Do not rewrite history for it without explicit owner approval.
- If a secret lands in a commit: revoke or rotate the credential FIRST, then remove it from the tree and push. History rewrite is optional cleanup and requires explicit owner approval (force push).
- Do not weaken the secret entries in `.gitignore`.
