#! /bin/bash

echo Deleting existing files

rm ~/.bashrc
rm ~/.vimrc
rm ~/.tmux.conf
rm ~/.gitconfig

CURRENT_DIR=$(pwd)

echo Porting new ones

ln -s $CURRENT_DIR/bash/.bashrc ~/.bashrc
ln -s $CURRENT_DIR/tmux/.tmux.conf ~/.tmux.conf
ln -s $CURRENT_DIR/vim/.vimrc ~/.vimrc
ln -s $CURRENT_DIR/git/.gitconfig ~/.gitconfig

echo Updating env to use new dotfiles

source ~/.bashrc
tmux source-file ~/.tmux.conf
#vimrc change check is within .vimrc itself
