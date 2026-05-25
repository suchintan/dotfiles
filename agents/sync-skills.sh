#!/bin/bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skills_dir="$root_dir/agents/skills"

install_skill_dir() {
  local target_dir="$1"
  mkdir -p "$target_dir"

  for skill_dir in "$skills_dir"/*; do
    [ -d "$skill_dir" ] || continue
    [ -f "$skill_dir/SKILL.md" ] || continue

    local name
    name="$(basename "$skill_dir")"
    local dest="$target_dir/$name"

    if [ -L "$dest" ]; then
      local existing
      existing="$(readlink "$dest")"
      if [ "$existing" = "$skill_dir" ]; then
        continue
      fi
      rm "$dest"
    elif [ -e "$dest" ]; then
      echo "Skipping $dest; existing non-symlink skill is left untouched"
      continue
    fi

    ln -s "$skill_dir" "$dest"
    echo "Linked $dest -> $skill_dir"
  done
}

install_skill_dir "$HOME/.claude/skills"
install_skill_dir "$HOME/.codex/skills"
