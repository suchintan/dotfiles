# Agent Skills

This directory contains public-safe skills that can be shared by Claude Code and Codex.

Install them with:

```bash
./agents/sync-skills.sh
```

The sync script symlinks each `agents/skills/<name>` directory into:

- `~/.claude/skills/<name>`
- `~/.codex/skills/<name>`

It skips an existing non-matching skill instead of overwriting it. Private skills should stay in `~/Development/obsidian/agents/skills`.
