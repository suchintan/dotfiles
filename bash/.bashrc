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
alias service-restart='sudo service uwsgi restart && sudo service nginx restart'
