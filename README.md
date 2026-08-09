# dotfiles

Personal macOS dotfiles and public-safe agent setup.

## Install

```bash
./install.sh
```

The installer symlinks shell, git, tmux, vim, Claude Code, Codex, omp, Herdr, and shared public agent skill files into `~`.

## Agent Config

- `AGENTS.md` contains tool-agnostic repo instructions.
- `claude/` contains Claude Code instructions, settings, hooks, and MCP templates.
- `codex/` contains Codex user instructions, RTK guidance, agent profiles, hooks, and a MCP config template.
- `omp/` contains the Oh My Pi agent config and codex subagent definitions (`~/.omp/agent/`).
- `herdr/` contains the Herdr terminal-multiplexer config (`~/.config/herdr/config.toml`).
- `agents/skills/` contains public-safe skills shared by Claude Code and Codex.

Real MCP credentials are not committed. Use:

- `codex/config.toml.template` as a source for `~/.codex/config.toml`
- `claude/mcp_servers.json.template` and `claude/mcp-setup.md` as Claude Code setup references

Keep secrets in local-only files such as `~/.zshrc_secrets`, `~/.codex/config.toml`, and `~/.claude.json`.
