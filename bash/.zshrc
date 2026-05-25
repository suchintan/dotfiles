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

function ikonomos-codex() {
    CODEX_HOME="$HOME/.codex-ikonomos" codex "$@"
}


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
