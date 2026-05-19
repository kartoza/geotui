" GeoTUI - Neovim project configuration
" All shortcuts under <leader>p

" Load project-specific Lua config
if filereadable('.nvim.lua')
  luafile .nvim.lua
endif
