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
touch ~/.zshrc_secrets

echo Installing brew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/suchintan/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew tap caskroom/cask
brew install caskroom/cask/brew-cask

echo Installing brew stuff
brew install tmux
brew install rg
brew install tree
brew install python

echo Installing DS stuff
brew install jupyter
pip3 install jupyterthemes


echo Installing zsh
brew install zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions $ZSH_CUSTOM/plugins/zsh-autosuggestions
git clone https://github.com/MichaelAquilina/zsh-you-should-use.git $ZSH_CUSTOM/plugins/you-should-use
ln -s $CURRENT_DIR/bash/.zshrc ~/.zshrc

echo installing helpers
brew install --cask rectangle
brew install --cask visual-studio-code
brew install --cask slack
brew install --cask postman
brew install --cask iterm2
brew install --cask flux
brew install --cask vlc
brew install --cask istat-menus
brew install --cask signal
brew install --cask jumpcut
brew install node
brew install gh
#curl -s 'https://api.macapps.link/en/vscode-postman-iterm-flux-istatmenus-vlc-slack' | sh

echo Installing Plug.vim

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

echo Please open .vimrc and run :PlugInstall to finish installing plug

echo Updating env to use new dotfiles
source ~/.zshrc
#tmux source-file ~/.tmux.conf
