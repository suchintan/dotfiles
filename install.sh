#! /bin/bash

echo Deleting existing files

rm ~/.bashrc
rm ~/.vimrc
rm ~/.tmux.conf
rm ~/.gitconfig
rm ~/.zshrc
rm -r ~/.vim

CURRENT_DIR=$(pwd)

echo Porting new ones

ln -s $CURRENT_DIR/bash/.bashrc ~/.bashrc
ln -s $CURRENT_DIR/bash/.zshrc ~/.zshrc
ln -s $CURRENT_DIR/tmux/.tmux.conf ~/.tmux.conf
ln -s $CURRENT_DIR/vim/.vimrc ~/.vimrc
ln -s $CURRENT_DIR/vim/.ideavimrc ~/.ideavimrc
ln -s $CURRENT_DIR/git/.gitconfig ~/.gitconfig
ln -s $CURRENT_DIR/vim/.vim ~/.vim

echo Installing brew
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
brew tap caskroom/cask
brew install caskroom/cask/brew-cask

echo Installing brew stuff
brew install tmux
brew install rg

echo Installing Plug.vim

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

echo Installing zsh
brew install zsh
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions $ZSH_CUSTOM/plugins/zsh-autosuggestions
git clone https://github.com/MichaelAquilina/zsh-you-should-use.git $ZSH_CUSTOM/plugins/you-should-use
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"


echo Updating env to use new dotfiles
source ~/.zshrc
#tmux source-file ~/.tmux.conf
