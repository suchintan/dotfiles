@RTK.md

# Codex User Instructions

## Defaults

- Be concise and direct.
- Prefer practical edits over long proposals when the requested change is clear.
- Use `uv` for Python dependency management.
- Use `nvm` for Node versions when projects define `.nvmrc`.
- Do not read or reference `~/.zshrc_secrets` unless explicitly requested.

## Skills

- Public dotfiles skills are installed from `~/Development/dotfiles/agents/skills`.
- Private personal skills are authored in `~/Development/obsidian/agents/skills/<name>/SKILL.md`.
- After adding, renaming, or removing private skills, run `~/Development/obsidian/agents/sync-skills.sh`.
- Never write private personal skills directly to `~/.claude/skills/` or `~/.codex/skills/`.

## Public Repo Safety

- Treat `~/Development/dotfiles` as public.
- Use templates and placeholders for MCP/API credentials.
- Keep real Codex MCP credentials in `~/.codex/config.toml`, not in the repo.
