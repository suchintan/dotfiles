#!/bin/bash
# Appends Claude Code bash commands to zsh history file
set -e

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

HISTFILE="${HOME}/.zsh_history"
TIMESTAMP=$(date +%s)

# Zsh extended history format: ": timestamp:0;command"
# For multiline commands, inner newlines are escaped as backslash-newline
ESCAPED=$(printf '%s' "$COMMAND" | sed '$!s/$/\\/')
printf ': %s:0;%s\n' "$TIMESTAMP" "$ESCAPED" >> "$HISTFILE"

exit 0
