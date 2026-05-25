# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For tool-agnostic agent instructions, see `AGENTS.md`.

## What This Is

Public-safe personal dotfiles repo for macOS. Configs are organized by tool in subdirectories and deployed to `~` via symlinks (not GNU stow). Run `./install.sh` on a fresh machine to set everything up.

## Structure

- `bash/` — `.zshrc` (primary shell), `.zprofile` (login shell PATH), `.bashrc` (legacy/fallback), `.profile`
- `vim/` — `.vimrc`, `.ideavimrc`, `.vim/` directory with vim-plug plugins
- `tmux/` — `.tmux.conf` (prefix is `C-a`, not `C-b`)
- `git/` — `.gitconfig` with custom aliases and branch naming conventions
- `claude/` — Claude Code config (`CLAUDE.md`, `settings.json`, `mcp_servers.json.template`, hooks, RTK guide)
- `codex/` — Codex user instructions, RTK guide, and public-safe `config.toml.template`
- `agents/` — Public-safe shared skills and the skill symlink sync script
- `install.sh` — Full bootstrap: symlinks → brew → cask apps → oh-my-zsh → vim-plug → fzf → sdkman

## Install Flow

`install.sh` runs in order:
1. Removes existing dotfiles from `~`, creates symlinks to this repo
2. Creates `~/.zshrc_secrets` (empty file for local secrets — never committed)
3. Symlinks Claude Code and Codex instruction files
4. Installs public-safe agent skills into `~/.claude/skills` and `~/.codex/skills`
5. Installs Homebrew, CLI tools (uv, fzf, zoxide, ripgrep, rtk, gh, git-lfs, llm, etc.), and cask apps
6. Installs oh-my-zsh with plugins (zsh-syntax-highlighting, zsh-autosuggestions, you-should-use)
7. Sets up vim-plug (user must run `:PlugInstall` manually in vim)
8. Sets up fzf shell integration
9. Installs SDKMAN for Java version management

## Key Conventions

- **Secrets** go in `~/.zshrc_secrets` (sourced by `.zshrc`, not version controlled). Never read or reference this file.
- **MCP credentials** stay in `~/.codex/config.toml`, `~/.claude.json`, or OAuth-managed Claude/Codex state. Commit only templates with placeholders.
- **Git branch naming**: `g br <name>` creates `suchintan.<name>` branches. All git aliases live in `git/.gitconfig`.
- **Git aliases use `user.main-branch`**: The `.gitconfig` stores the default branch name in a custom `user.main-branch` key so aliases like `frb` and `pff` work regardless of whether the repo uses `main` or `master`.
- **Python**: Use `uv` for dependency management.
- **Node**: Managed via `nvm` (installed by brew, loaded in `.zshrc`).
- **`.zshrc` overrides `cd`**: It uses `zoxide` under the hood and auto-activates `.venv` or poetry virtualenvs.
- **Shell history**: `.zshrc` ignores commands prefixed with a leading space. Use that for token-bearing commands.
- After modifying any dotfile, changes take effect immediately (symlinked). Shell restart needed for `.zshrc` changes.
- Before committing agent config changes, run a secret-pattern scan over the diff.
