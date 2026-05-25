#!/bin/bash
set -euo pipefail

echo "=== Removing existing dotfiles ==="

rm -f ~/.bashrc
rm -f ~/.vimrc
rm -f ~/.tmux.conf
rm -f ~/.gitconfig
rm -f ~/.zshrc
rm -f ~/.zprofile
rm -f ~/.ideavimrc
rm -rf ~/.vim
rm -f ~/.claude/CLAUDE.md
rm -f ~/.claude/settings.json
rm -f ~/.claude/RTK.md
rm -f ~/.claude/hooks/bash-history.sh
rm -f ~/.codex/AGENTS.md
rm -f ~/.codex/RTK.md

CURRENT_DIR=$(pwd)

echo "=== Creating symlinks ==="

ln -s "$CURRENT_DIR/bash/.bashrc" ~/.bashrc
ln -s "$CURRENT_DIR/bash/.zshrc" ~/.zshrc
ln -s "$CURRENT_DIR/bash/.zprofile" ~/.zprofile
ln -s "$CURRENT_DIR/tmux/.tmux.conf" ~/.tmux.conf
ln -s "$CURRENT_DIR/vim/.vimrc" ~/.vimrc
ln -s "$CURRENT_DIR/vim/.ideavimrc" ~/.ideavimrc
ln -s "$CURRENT_DIR/git/.gitconfig" ~/.gitconfig
ln -s "$CURRENT_DIR/vim/.vim" ~/.vim
mkdir -p ~/.claude
mkdir -p ~/.claude/hooks
mkdir -p ~/.codex
ln -s "$CURRENT_DIR/claude/CLAUDE.md" ~/.claude/CLAUDE.md
ln -s "$CURRENT_DIR/claude/settings.json" ~/.claude/settings.json
ln -s "$CURRENT_DIR/claude/RTK.md" ~/.claude/RTK.md
ln -s "$CURRENT_DIR/claude/hooks/bash-history.sh" ~/.claude/hooks/bash-history.sh
ln -s "$CURRENT_DIR/codex/AGENTS.md" ~/.codex/AGENTS.md
ln -s "$CURRENT_DIR/codex/RTK.md" ~/.codex/RTK.md
touch ~/.zshrc_secrets

echo "=== Installing public agent skills ==="

"$CURRENT_DIR/agents/sync-skills.sh"

echo "=== MCP config templates ==="
echo "Codex MCP template: $CURRENT_DIR/codex/config.toml.template"
echo "Claude MCP template: $CURRENT_DIR/claude/mcp_servers.json.template"
echo "Real MCP credentials are intentionally not overwritten by install.sh"

echo "=== Installing Homebrew ==="

if ! command -v brew >/dev/null 2>&1; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

echo "=== Installing CLI tools ==="

# Core utilities
brew install tmux
brew install tree
brew install jq
brew install wget
brew install fzf
brew install zoxide
brew install zsh
brew install ripgrep
brew install coreutils
brew install rtk
brew install git-lfs
git lfs install

# GitHub CLI + extensions
brew install gh
if ! gh extension list | grep -q "github/gh-copilot"; then
    gh extension install github/gh-copilot
fi

# Python ecosystem
brew install uv
brew install python@3.9
brew install pypy
brew install pyenv
brew install poetry
brew install pre-commit
brew install black
brew install mypy
brew install ipython
brew install virtualenv
brew install python-build
brew install python-lsp-server

# Node (via nvm)
brew install nvm
mkdir -p ~/.nvm

export NVM_DIR="$HOME/.nvm"
if [ -s "$(brew --prefix nvm)/nvm.sh" ]; then
    . "$(brew --prefix nvm)/nvm.sh"
    nvm install --lts
    nvm use --lts
    npm install -g @openai/codex @earendil-works/pi-coding-agent @bitwarden/cli agent-browser pnpm @googleworkspace/cli
fi

# AI / LLM tools
brew install llm

# Data tools
brew install duckdb
brew install csvkit
brew install jupyterlab
brew install poppler
brew install postgresql@14
brew install redis

# DevOps / Infra
brew install terraform
brew install helm
brew install k6
brew install heroku/brew/heroku
brew install protobuf
brew install twilio/brew/twilio

# Database clients
brew install microsoft/mssql-release/mssql-tools18

# Media / Misc
brew install ffmpeg
brew install qrencode
brew install zbar
brew install deno
brew install lnav
brew install scc
brew install fswatch
brew install trurl
brew install tursodatabase/tap/turso
brew install trufflehog
brew install jsonschema
brew install keyring
brew install openjdk
brew install squirrel-lang
brew install mcp-publisher

echo "=== Installing uv tools ==="

uv tool install --upgrade mempalace

echo "=== Installing macOS applications ==="

brew install --cask rectangle
brew install --cask raycast
brew install --cask alt-tab
brew install --cask maccy
brew install --cask jumpcut
brew install --cask docker
brew install --cask postman
brew install --cask dbvisualizer
brew install --cask ngrok
brew install --cask notion
brew install --cask discord
brew install --cask signal
brew install --cask loom
brew install --cask todoist-app
brew install --cask klogg
brew install --cask warp
brew install --cask windsurf
brew install --cask codex
brew install --cask iterm2
brew install --cask slack
brew install --cask visual-studio-code
brew install --cask vlc
brew install --cask flux
brew install --cask istat-menus
brew install --cask chatgpt
brew install --cask claude
brew install --cask google-chrome
brew install --cask linear-linear
brew install --cask obsidian
brew install --cask screen-studio
brew install --cask superhuman
brew install --cask tailscale
brew install --cask superwhisper

echo "=== macOS preferences ==="

defaults write -g KeyRepeat -int 1
defaults write -g InitialKeyRepeat -int 15

echo "=== Installing Oh-My-Zsh ==="

if [ ! -d "$HOME/.oh-my-zsh" ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

ZSH_CUSTOM_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
mkdir -p "$ZSH_CUSTOM_DIR/plugins"
[ -d "$ZSH_CUSTOM_DIR/plugins/zsh-syntax-highlighting" ] || git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM_DIR/plugins/zsh-syntax-highlighting"
[ -d "$ZSH_CUSTOM_DIR/plugins/zsh-autosuggestions" ] || git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM_DIR/plugins/zsh-autosuggestions"
[ -d "$ZSH_CUSTOM_DIR/plugins/you-should-use" ] || git clone https://github.com/MichaelAquilina/zsh-you-should-use.git "$ZSH_CUSTOM_DIR/plugins/you-should-use"

echo "=== Installing Vim plugins ==="

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
echo "Please open vim and run :PlugInstall to finish installing plugins"

echo "=== Setting up fzf ==="

$(brew --prefix)/opt/fzf/install --all

echo "=== Installing SDKMAN (Java version manager) ==="

curl -s "https://get.sdkman.io" | bash

echo "=== Done! ==="
echo "Restart your shell or run: source ~/.zshrc"
