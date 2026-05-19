-- GeoTUI - Neovim project-specific configuration
-- All shortcuts under <leader>p (project)

local wk_ok, wk = pcall(require, "which-key")

local function map(key, cmd, desc)
  vim.keymap.set("n", "<leader>p" .. key, cmd, { desc = desc, silent = true })
end

-- Run the application
map("r", "<cmd>!python -m geotui<CR>", "Run GeoTUI")
map("R", "<cmd>split | terminal python -m geotui<CR>", "Run GeoTUI (terminal)")

-- Testing
map("t", "<cmd>split | terminal pytest<CR>", "Run all tests")
map("u", "<cmd>split | terminal pytest tests/unit/<CR>", "Run unit tests")
map("b", "<cmd>split | terminal pytest tests/bdd/<CR>", "Run BDD tests")
map("c", "<cmd>split | terminal pytest --cov=geotui --cov-report=html<CR>", "Run tests with coverage")
map("C", "<cmd>!xdg-open htmlcov/index.html<CR>", "Open coverage report")

-- Linting and formatting
map("l", "<cmd>split | terminal ruff check src/ tests/<CR>", "Lint code")
map("f", "<cmd>split | terminal ruff format src/ tests/<CR>", "Format code")
map("m", "<cmd>split | terminal mypy src/ --ignore-missing-imports<CR>", "Type check")

-- Documentation
map("d", "<cmd>split | terminal cd docs && mkdocs serve<CR>", "Serve docs")
map("D", "<cmd>split | terminal cd docs && mkdocs build<CR>", "Build docs")

-- i18n
map("i", "<cmd>split | terminal msgfmt -o src/geotui/i18n/locales/pt/LC_MESSAGES/geotui.mo src/geotui/i18n/locales/pt/LC_MESSAGES/geotui.po && msgfmt -o src/geotui/i18n/locales/es/LC_MESSAGES/geotui.mo src/geotui/i18n/locales/es/LC_MESSAGES/geotui.po<CR>", "Compile translations")

-- Build and package
map("B", "<cmd>split | terminal python -m build<CR>", "Build package")
map("P", "<cmd>split | terminal pip install -e '.[dev,docs,i18n]'<CR>", "Install dev deps")

-- Git
map("gs", "<cmd>!git status<CR>", "Git status")
map("gd", "<cmd>!git diff<CR>", "Git diff")

-- Textual dev tools
map("x", "<cmd>split | terminal textual console<CR>", "Textual console")

-- Register with which-key if available
if wk_ok then
  wk.add({
    { "<leader>p", group = "GeoTUI Project" },
    { "<leader>pg", group = "Git" },
  })
end

-- Python LSP settings
vim.g.python3_host_prog = vim.fn.exepath("python3")

-- File type associations
vim.filetype.add({
  extension = {
    tcss = "css",
    feature = "cucumber",
  },
})
