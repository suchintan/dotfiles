#!/bin/bash
set -euo pipefail

input=$(cat)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

if [ -z "$command" ]; then
  exit 0
fi

histfile="${HOME}/.zsh_history"
timestamp=$(date +%s)

# Zsh extended history format: ": timestamp:0;command".
escaped=$(printf '%s' "$command" | sed '$!s/$/\\/')
printf ': %s:0;%s\n' "$timestamp" "$escaped" >> "$histfile"
