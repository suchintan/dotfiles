# dotfiles

Personal macOS dotfiles and public-safe agent setup.

## Install

```bash
./install.sh
```

The installer symlinks shell, git, tmux, vim, Claude Code, Codex, and shared public agent skill files into `~`.

## Agent Config

- `AGENTS.md` contains tool-agnostic repo instructions.
- `claude/` contains Claude Code instructions, settings, hooks, and MCP templates.
- `codex/` contains Codex user instructions, RTK guidance, and a MCP config template.
- `agents/skills/` contains public-safe skills shared by Claude Code and Codex.

Real MCP credentials are not committed. Use:

- `codex/config.toml.template` as a source for `~/.codex/config.toml`
- `claude/mcp_servers.json.template` and `claude/mcp-setup.md` as Claude Code setup references

Keep secrets in local-only files such as `~/.zshrc_secrets`, `~/.codex/config.toml`, and `~/.claude.json`.
