---
name: mcp-setup
description: Configure or audit public-safe Claude Code and Codex MCP setup from the dotfiles templates.
---

# MCP Setup

Use this skill when configuring MCP servers for Claude Code or Codex from this dotfiles repo.

## Files

- Claude template: `claude/mcp_servers.json.template`
- Claude setup notes: `claude/mcp-setup.md`
- Codex template: `codex/config.toml.template`

## Rules

- Never commit rendered configs that contain real keys.
- Keep actual Codex credentials in `~/.codex/config.toml`.
- Keep actual Claude Code credentials in `~/.claude.json` or OAuth-managed Claude state.
- Use placeholders in repo files.

## Configured Server Coverage

The templates cover:

- context7
- linear
- notion
- pylon
- skyvern, skyvern-staging, skyvern-local
- datadog
- exa
- awslabs.redshift-mcp-server
- superhuman-mail
- figma
- slack-as-me
- hex
