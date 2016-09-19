function current_git_branch {
    echo `git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/[\1]/'`
}
export CLICOLOR=1
export PS1="\[\033[36m\]\w \[\033[33m\]\$(current_git_branch)\[\033[00m\]$\[\033[00m\] "

# Predictable SSH authentication socket location.
SOCK="/tmp/ssh-agent-$USER-screen"
if test $SSH_AUTH_SOCK && [ $SSH_AUTH_SOCK != $SOCK ]
then
    rm -f /tmp/ssh-agent-$USER-screen
    ln -sf $SSH_AUTH_SOCK $SOCK
    export SSH_AUTH_SOCK=$SOCK
fi

alias fanmgmt='cd ~/projects/HearsayLabs/fanmgmt'
alias poly='cd ~/projects/project-poly'
alias activities='cd ~/projects/hearsay-activities'
alias service-restart='sudo service uwsgi restart && sudo service nginx restart'
alias gfu="git fetch upstream && git rebase upstream/master"
alias clip="nc localhost 8377" # for clipper
alias ag='ag --path-to-agignore=~/.agignore'
alias vim="/Applications/MacVim.app/Contents/MacOS/Vim"
alias dotfiles='cd ~/projects/dotfiles'

export HISTCONTROL=ignoredups:erasedups  # no duplicate entries
export HISTSIZE=100000                   # big big history
export HISTFILESIZE=100000               # big big history
shopt -s histappend                      # append to history, don't overwrite it

# Save and reload the history after each command finishes
export PROMPT_COMMAND="history -a; history -c; history -r; $PROMPT_COMMAND"

export JAVA_HOME=$(/usr/libexec/java_home -v 1.7)
setjdk() {
    export JAVA_HOME=$(/usr/libexec/java_home -v $1)
}
