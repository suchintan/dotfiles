# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="af-magic"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in ~/.oh-my-zsh/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment the following line to disable bi-weekly auto-update checks.
# DISABLE_AUTO_UPDATE="true"

# Uncomment the following line to automatically update without prompting.
# DISABLE_UPDATE_PROMPT="true"

# Uncomment the following line to change how often to auto-update (in days).
# export UPDATE_ZSH_DAYS=13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS=true

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in ~/.oh-my-zsh/plugins/*
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git you-should-use zsh-syntax-highlighting colored-man-pages colorize pip python brew macos zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
#
HISTSIZE=100000
SAVEHIST=100000
setopt APPEND_HISTORY
setopt EXTENDED_HISTORY
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY
setopt HIST_EXPIRE_DUPS_FIRST
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE                 # prefix sensitive commands with a space
setopt HIST_REDUCE_BLANKS
setopt HIST_SAVE_NO_DUPS
#setopt PROMPT_SUBST
#PROMPT='%n@%m: ${(%):-%~} '


alias dev='cd ~/Development'
alias search='cd ~/Development/product-search-service'
alias datascience='cd ~/Development/datascience'
alias dynamodb='cd ~/Development/dynamodb_local_latest && java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb'
alias elasticsearch='docker run -p 9200:9200 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:7.8.0'

alias initPlot='echo "x <- seq(0, 480, 1)" > plot.r && echo "plot(x, 2.0 - (2 / (1 + exp(-x * 0.01))), type=\"l\")" >> plot.r'
alias plot='Rscript plot.r && open Rplots.pdf'
alias cleanupPlot='rm plot.r && rm Rplots.pdf'
alias pytest='python -m pytest'

function codex-resume() {
    local resume_id="$1"

    if [[ -z "$resume_id" ]]; then
        printf "Codex resume id: "
        read -r resume_id
    fi

    if [[ -z "$resume_id" ]]; then
        echo "Usage: codex-resume <resume-id>"
        return 1
    fi

    codex -c model_reasoning_effort="xhigh" --ask-for-approval never --sandbox danger-full-access -c model_reasoning_summary="detailed" -c model_supports_reasoning_summaries=true resume "$resume_id"
}

function codex-session-for-worktree() {
    local codex_home="${CODEX_HOME:-$HOME/.codex}"
    local state_db="$codex_home/state_5.sqlite"
    local id_only=0

    if [[ "$1" == "--id-only" ]]; then
        id_only=1
        shift
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "codex-session-for-worktree: python3 is required"
        return 1
    fi
    if [[ ! -f "$state_db" ]]; then
        echo "codex-session-for-worktree: Codex state DB not found at $state_db"
        return 1
    fi

    CODEX_STATE_DB="$state_db" CODEX_ID_ONLY="$id_only" python3 - "$PWD" <<'PY'
import os
import sqlite3
import subprocess
import sys
import time


def run(args, cwd=None):
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


start_cwd = os.path.abspath(sys.argv[1])
repo = run(["git", "rev-parse", "--show-toplevel"], start_cwd)
if not repo:
    print("codex-session-for-worktree: not inside a git worktree", file=sys.stderr)
    sys.exit(1)

branch = run(["git", "branch", "--show-current"], repo)
head = run(["git", "rev-parse", "HEAD"], repo)
origin = run(["git", "config", "--get", "remote.origin.url"], repo)
status = run(["git", "status", "--porcelain=v1"], repo)
changed = []
for line in status.splitlines():
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if path:
        changed.append(path)

db_path = os.environ["CODEX_STATE_DB"]
id_only = os.environ.get("CODEX_ID_ONLY") == "1"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """
    select id, rollout_path, cwd, title, git_sha, git_branch, git_origin_url, updated_at
    from threads
    where archived = 0
    order by updated_at desc
    limit 500
    """
).fetchall()

matches = []
for row in rows:
    cwd = os.path.abspath(row["cwd"] or "")
    in_repo = cwd == repo or cwd.startswith(repo + os.sep) or start_cwd == cwd
    branch_match = bool(branch and row["git_branch"] == branch)
    head_match = bool(head and row["git_sha"] == head)
    origin_match = bool(origin and row["git_origin_url"] == origin)

    path_hits = 0
    rollout_path = row["rollout_path"] or ""
    if changed and rollout_path and os.path.exists(rollout_path):
        try:
            with open(rollout_path, "r", encoding="utf-8", errors="ignore") as fh:
                rollout = fh.read()
            path_hits = sum(1 for path in changed if path in rollout)
        except OSError:
            path_hits = 0

    if in_repo or branch_match or head_match or origin_match or path_hits:
        age_penalty = max(0, int(time.time()) - int(row["updated_at"] or 0)) / 86400
        score = (
            (100 if in_repo else 0)
            + (40 if branch_match else 0)
            + (30 if head_match else 0)
            + (20 if origin_match else 0)
            + (25 * path_hits)
            - min(age_penalty, 30)
        )
        matches.append((score, path_hits, row))

if not matches:
    print("codex-session-for-worktree: no matching Codex session found", file=sys.stderr)
    sys.exit(1)

matches.sort(key=lambda item: (item[0], item[2]["updated_at"]), reverse=True)
score, path_hits, best = matches[0]

print(best["id"])
if id_only:
    sys.exit(0)
print(f"title: {best['title']}")
print(f"cwd: {best['cwd']}")
print(f"branch: {best['git_branch'] or '(unknown)'}")
print(f"head: {best['git_sha'] or '(unknown)'}")
print(f"dirty_files: {len(changed)}")
print(f"dirty_file_hits_in_rollout: {path_hits}")
print(f"updated_at: {time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(int(best['updated_at'])))}")

if len(matches) > 1:
    print("alternates:")
    for alt_score, alt_hits, alt in matches[1:4]:
        print(f"  {alt['id']} hits={alt_hits} updated={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(alt['updated_at'])))} title={alt['title'][:80]}")
PY
}

alias codex-worktree-session=codex-session-for-worktree

function codex-resume-worktree() {
    local session_id
    session_id="$(codex-session-for-worktree --id-only)" || return $?
    if [[ -z "$session_id" ]]; then
        echo "codex-resume-worktree: could not determine a session id"
        return 1
    fi
    codex -c model_reasoning_effort="xhigh" --ask-for-approval never --sandbox danger-full-access -c model_reasoning_summary="detailed" -c model_supports_reasoning_summaries=true resume "$session_id"
}

alias codex-worktree-resume=codex-resume-worktree

function ikonomos-codex() {
    CODEX_HOME="$HOME/.codex-ikonomos" codex "$@"
}

function skyvern-ai-codex() {
    CODEX_HOME="$HOME/.codex-skyvern-ai" codex "$@"
}

function skyvern-ai-s-codex() {
    CODEX_HOME="$HOME/.codex-skyvern-ai-s" codex "$@"
}

alias codex-skyvern-ai=skyvern-ai-codex
alias codex-skyvern-ai-s=skyvern-ai-s-codex


export PATH=$PATH:$HOME/bin

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

[[ -f "$HOME/.zshrc_secrets" ]] && source "$HOME/.zshrc_secrets" # store all secrets here

# automatic python virtual env
function auto_python_env {
    if [[ -f ".venv/bin/activate" ]]; then
        source ".venv/bin/activate"
    elif [[ -f "pyproject.toml" ]] && command -v poetry >/dev/null 2>&1; then
        local poetry_env
        poetry_env=$(poetry env info --path 2>/dev/null)
        [[ -n "$poetry_env" && -f "$poetry_env/bin/activate" ]] && source "$poetry_env/bin/activate"
    fi
}

auto_python_env

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"

# Docker Aliases
function dk() {
    docker kill "$1" | xargs docker rm
}
alias dk=dk


[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
function cd {
    __zoxide_z "$@"
    auto_python_env
}

eval "$(zoxide init zsh)"



eval "$(gh copilot alias -- zsh)"

alias ai='ghcs'

alias llms='llm -c --system "be very concise when answering, and try to just give the commandline argument if asked. Dont decorate the output in any markup."'
alias llmq='llm -c --system "be very concise when answering, and try to just answer the question. Dont decorate the output in any markup"'

export PATH="$HOME/.local/bin:$PATH"

# bun completions
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Browser-Use
export PATH="$HOME/.browser-use-env/bin:$PATH"
