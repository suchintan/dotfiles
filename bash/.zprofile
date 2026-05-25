if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

# Obsidian exposes its CLI from the app bundle.
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"

[[ -f "$HOME/.zprofile.local" ]] && source "$HOME/.zprofile.local"
