syntax on "pretty syntax

let mapleader=","

set number "Line numbers
set cursorline "highlight current line

set ai "autoindent
set tabstop=4 "set tabs to 4 characters
set shiftwidth=4
set expandtab "Turns tabs to spaces
set softtabstop=4 "spaces feel like tabs

set shortmess+=A " No .swp warning

set hlsearch "Highlight all search matches
set ignorecase "Make searches case insensitive
set smartcase "Don't ignore case if we have a capital letter
set incsearch "Show matches while typing the search string

set laststatus=2 "Keeps statusline on alllll the time

if exists('+colorcolumn')
    set colorcolumn=120        " Highlight the column after `textwidth`
endif

au BufWritePre * :%s/\s\+$//e  " clear white space in the end of lines

" show trailing whitespace
set list lcs=trail:·,precedes:«,extends:»,tab:▸\

set mouse=a " Allow scrolling with a mouse

if has("mouse_sgr")
    set ttymouse=sgr "This one makes mouse work past the 220th column
else
    set ttymouse=xterm2 "match iterm2 mouse settings
end

" Set splits to be more natural
set splitbelow
set splitright

" Change wildmenu (tab completion shows more naturally)  so that it works like the terminal
set wildmenu
set wildmode=list:longest

" Ignore pyc and o files when showing files in wildmenu
:set wildignore=*.o,*.pyc

" Return to last edit position when opening files, except git commit message
autocmd BufReadPost *
    \ if &ft != 'gitcommit' && line("'\"") > 0 && line("'\"") <= line("$") |
    \   exe "normal g`\"" |
    \ endif

" Set colourscheme
colorscheme elflord

set runtimepath^=~/.vim/bundle/ctrlp.vim,~/.vim/bundle/vim-airline.vim,~/.vim/bundle/YouCompleteMe.vim


call plug#begin('~/.vim/plugged')
" Fuzzy file finder
Plug 'ctrlpvim/ctrlp.vim'

" Fancy statusline
Plug 'bling/vim-airline'

" Suggestions
Plug 'Valloric/YouCompleteMe', { 'do': './install.py' }

" Syntastic: Code Linting
Plug 'scrooloose/syntastic', { 'for': ['php', 'python', 'javascript', 'css'] }

" Ag within vim
Plug 'rking/ag.vim'

call plug#end()

let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlPMixed'

" Move to the next buffer
nmap <leader>l :bnext<CR>

" Move to the previous buffer
nmap <leader>p :bprevious<CR>

" Close the current buffer and move to the previous one
" This replicates the idea of closing a tab
nmap <leader>q :bp <BAR> bd #<CR>

" Show all open buffers and their status
nmap <leader>bl :ls<CR>

nnoremap <leader>y :call system('nc localhost 8377', @0)<CR>

let g:airline#extensions#tabline#enabled = 1

" If we have The Silver Searcher
if executable('ag')
    " Use ag over grep
    set grepprg=ag\ --nogroup\ --nocolor

    " Use ag in CtrlP for listing files. Lightning fast and respects .gitignore
    let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'

    " ag is fast enough that CtrlP doesn't need to cache
    let g:ctrlp_use_caching = 0
endif
