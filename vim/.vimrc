syntax on "pretty syntax

:set number "Line numbers

:set ai "autoindent
:set tabstop=4 "set tabs to 4 characters
:set shiftwidth=4
:set expandtab "Turns tabs to spaces
:set softtabstop=4 "spaces feel like tabs

:set autoread "Update the file with changs live

:set hlsearch "Highlight all search matches
:set smartcase "Make searches case insensitive
:set incsearch "Show matches while typing the search string

:set laststatus=2 "Keeps statusline on alllll the time

set statusline=
set statusline +=%1*\ %n\ %*            "buffer number
set statusline +=%5*%{&ff}%*            "file format
set statusline +=%3*%y%*                "file type
set statusline +=%4*\ %<%F%*            "full path
set statusline +=%2*%m%*                "modified flag
set statusline +=%1*%=%5l%*             "current line
set statusline +=%2*/%L%*               "total lines
set statusline +=%1*%4v\ %*             "virtual column number
set statusline +=%2*0x%04B\ %*          "character under cursor

au BufWritePre * :%s/\s\+$//e  " clear white space in the end of lines

" show trailing whitespace
set list lcs=trail:·,precedes:«,extends:»,tab:▸\

set mouse=a " Allow scrolling with a mouse

set clipboard=unnamedplus "For yanking to global clipboard

"Auto-update changes to vimrc
augroup myvimrc
    au!
    au BufWritePost .vimrc,_vimrc,vimrc,.gvimrc,_gvimrc,gvimrc so $MYVIMRC | if has('gui_running') | so $MYGVIMRC | endif
augroup END

"Lets you know when the file has changed in the background
:au FileChangedShell * echo "Warning: File changed on disk"
