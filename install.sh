#! /bin/bash

echo Deleting existing files

rm ~/.bashrc
rm ~/.vimrc
rm ~/.tmux.conf
rm ~/.gitconfig
rm -r ~/.vim

CURRENT_DIR=$(pwd)

echo Porting new ones

ln -s $CURRENT_DIR/bash/.bashrc ~/.bashrc
ln -s $CURRENT_DIR/tmux/.tmux.conf ~/.tmux.conf
ln -s $CURRENT_DIR/vim/.vimrc ~/.vimrc
ln -s $CURRENT_DIR/git/.gitconfig ~/.gitconfig
ln -s $CURRENT_DIR/vim/.vim ~/.vim

echo Installing Plug.vim

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

./update_env.sh
