syntax on "pretty syntax

let mapleader=","

set number "Line numbers
set cursorline "highlight current line

set ai "autoindent
set tabstop=4 "set tabs to 4 characters
set shiftwidth=4
set expandtab "Turns tabs to spaces
set softtabstop=4 "spaces feel like tabs

set autoread "Update the file with changs live
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

"Lets you know when the file has changed in the background
:au FileChangedShell * echo "Warning: File changed on disk"

" Set splits to be more natural
set splitbelow
set splitright

" Change wildmenu so that it works like the terminal
set wildmenu
set wildmode=list:longest

" Set colourscheme
colorscheme elflord

set runtimepath^=~/.vim/bundle/ctrlp.vim,~/.vim/bundle/vim-airline.vim,~/.vim/bundle/YouCompleteMe.vim

let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlP'

:set wildignore=*.o,*.pyc

" Show control-p buffer and search em
map <c-b> :CtrlPBuffer<CR>

" Show control-p mixed mode and search em
map <c-m> :CtrlPMixed<CR>

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
