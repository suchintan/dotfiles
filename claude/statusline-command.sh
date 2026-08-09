#!/usr/bin/env bash
# Claude Code statusLine — af-magic theme inspired
# user@host | cwd (git-branch) | model | ctx: 42%

input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')

# user@host (mirrors af-magic RPS1)
user_host="$(whoami)@$(hostname -s)"

# Get git branch
git_branch=""
if git -C "$cwd" --no-optional-locks rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    git_branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
        || git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
fi

# Colors matching af-magic palette
GRAY='\033[38;5;237m'
BLUE='\033[38;5;32m'
GREEN='\033[38;5;78m'
PURPLE='\033[38;5;105m'
CYAN='\033[38;5;75m'
ORANGE='\033[38;5;214m'
RESET='\033[0m'

# user@host segment (grey, like af-magic RPS1)
host_segment="${GRAY}${user_host}${RESET}"

# Shorten $HOME to ~
cwd="${cwd/#$HOME/~}"

# cwd segment (blue, like af-magic left prompt %~)
cwd_segment="${BLUE}${cwd}${RESET}"

# Git branch segment (green with parens, like af-magic git prompt)
git_segment=""
if [ -n "$git_branch" ]; then
    git_segment=" ${CYAN}(${GREEN}${git_branch}${CYAN})${RESET}"
fi

# Model (purple, like af-magic prompt char color)
model_segment=""
if [ -n "$model" ]; then
    model_segment="${PURPLE}${model}${RESET}"
fi

# Context usage — orange when >= 80%
ctx_segment=""
if [ -n "$used_pct" ]; then
    used_int=${used_pct%.*}
    if [ "${used_int:-0}" -ge 80 ] 2>/dev/null; then
        ctx_segment="${ORANGE}ctx: ${used_pct}%${RESET}"
    else
        ctx_segment="${CYAN}ctx: ${used_pct}%${RESET}"
    fi
fi

# Plan usage (Pro/Max only — may be absent)
five_h=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
seven_d=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

RED='\033[38;5;196m'
YELLOW='\033[38;5;220m'

# Battery bar: drains as remaining decreases. Expects used_percentage.
# Args: $1 label, $2 used_percentage
battery_segment() {
    local label="$1"
    local used="$2"
    local used_int=${used%.*}
    used_int=${used_int:-0}
    [ "$used_int" -gt 100 ] 2>/dev/null && used_int=100
    [ "$used_int" -lt 0 ] 2>/dev/null && used_int=0

    local remaining=$((100 - used_int))
    local cells=10
    local filled=$(( (remaining + 5) / 10 ))
    [ "$filled" -gt "$cells" ] && filled=$cells
    [ "$filled" -lt 0 ] && filled=0
    local empty=$((cells - filled))

    local color
    if [ "$remaining" -le 15 ]; then
        color="$RED"
    elif [ "$remaining" -le 35 ]; then
        color="$ORANGE"
    elif [ "$remaining" -le 60 ]; then
        color="$YELLOW"
    else
        color="$GREEN"
    fi

    local bar=""
    local i=0
    while [ "$i" -lt "$filled" ]; do bar+="█"; i=$((i+1)); done
    i=0
    while [ "$i" -lt "$empty" ]; do bar+="░"; i=$((i+1)); done

    printf "%b%s%b %b[%s]%b %b%d%%%b" \
        "$CYAN" "$label" "$RESET" \
        "$color" "$bar" "$RESET" \
        "$color" "$remaining" "$RESET"
}

plan_line=""
if [ -n "$five_h" ] || [ -n "$seven_d" ]; then
    if [ -n "$five_h" ]; then
        plan_line+="$(battery_segment "5h" "$five_h")"
    fi
    if [ -n "$seven_d" ]; then
        [ -n "$plan_line" ] && plan_line+="  "
        plan_line+="$(battery_segment "7d" "$seven_d")"
    fi
fi

# Line 1: user@host | model | ctx
# Line 2: cwd (branch)
# Line 3: battery (if present)
sep="${GRAY} | ${RESET}"

line1="${host_segment}"
[ -n "$model_segment" ] && line1+="${sep}${model_segment}"
[ -n "$ctx_segment" ] && line1+="${sep}${ctx_segment}"

line2="${cwd_segment}${git_segment}"

printf "%b\n" "$line1"
printf "%b\n" "$line2"
[ -n "$plan_line" ] && printf "%b\n" "$plan_line"
exit 0
