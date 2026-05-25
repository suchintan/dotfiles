# User Preferences for Claude Code

@RTK.md

## About Me
- Name: Suchintan Singh
- Primary dev directory: `~/Development`

## Communication Style
- Be concise - avoid excessive markup or decoration
- Give direct command-line answers when asked for commands
- Skip unnecessary explanations unless asked

## Python
- **Use `uv`** for dependency management and virtual environments
- Run tests with `python -m pytest`
- Do NOT use Poetry, conda, or pip directly

## Node.js
- Use `nvm` to switch Node versions when needed
- Check `.nvmrc` files in projects

## Git Workflow

### Branch Naming
- Create branches with `g br <name>` (creates `suchintan.<name>`)
- Switch to your branches with `g sb <name>`
- Main branch is `main`

### Preferred Commands
- `g pushf` - force push (uses --force-with-lease, safer)
- `g frb` - fetch and rebase on main before pushing
- `g pr` - push and create a PR (opens in browser)
- `g a` - amend the last commit
- `g c "message"` - quick commit-all
- `g p` - push to origin HEAD

### PR Workflow
1. `g frb` - rebase on latest main
2. `g p` - push to origin
3. `gh pr create` - create PR via GitHub CLI

### Checking Out OSS PRs
- Use `g oss-pr <number>` to fetch and checkout external PRs

## Secrets
- Never read or reference `~/.zshrc_secrets`
- Treat `~/Development/dotfiles` as a public repo. Do not commit real MCP credentials, API keys, OAuth tokens, cookies, private IDs, or local `.env` files.
- Keep real Claude Code MCP credentials in `~/.claude.json` or OAuth-managed Claude state. Use `claude/mcp_servers.json.template` for public examples only.

## Skills

- Public-safe dotfiles skills are installed from `~/Development/dotfiles/agents/skills`.
- Private personal skills live in `~/Development/obsidian/agents/skills`.
- Do not hardcode workspace-specific IDs, customer names, or private page/channel IDs into public skills.

## MCP Servers Setup

After installing dotfiles, configure MCP servers for Claude Code from the public templates:

- `~/Development/dotfiles/claude/mcp_servers.json.template`
- `~/Development/dotfiles/claude/mcp-setup.md`

Covered servers: context7, linear, notion, hex, pylon, skyvern, skyvern-staging, skyvern-local, datadog, exa, Redshift, Superhuman Mail, Figma, and Slack.

Keep rendered configs local because they may contain credentials.

### Verify MCP Servers
```bash
claude mcp list
```
