.PHONY: help install install-bin install-dev build standalone nix-build nix-run clean lint format test docs run

help:
	@echo "GeoTUI - Available commands:"
	@echo ""
	@echo "  make install      Install with pipx (recommended for CLI use)"
	@echo "  make install-bin  Copy standalone binary to /usr/local/bin"
	@echo "  make install-dev  Install in editable mode for development"
	@echo "  make build        Build wheel and source distribution"
	@echo "  make standalone   Build standalone executable (no Python needed, Linux only)"
	@echo "  make nix-build    Build via Nix flake (for NixOS)"
	@echo "  make nix-run      Run directly via Nix flake (for NixOS)"
	@echo "  make clean        Remove build artifacts"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Run ruff formatter"
	@echo "  make test         Run test suite"
	@echo "  make docs         Serve documentation locally"
	@echo "  make run          Run the app"

install:
	pipx install .

install-dev:
	pip install -e ".[dev]"

build:
	pip install --quiet build
	python -m build
	@echo "Artifacts in dist/"

standalone:
	pip install --quiet pyinstaller
	pyinstaller --onefile \
		--name geotui \
		--add-data "src/geotui/styles:geotui/styles" \
		--add-data "src/geotui/i18n:geotui/i18n" \
		src/geotui/__main__.py
	@echo "Executable: dist/geotui"

install-bin: standalone dist/geotui
	sudo cp dist/geotui /usr/local/bin/geotui
	@echo "Installed to /usr/local/bin/geotui"

nix-build:
	nix build .
	@echo "Executable: ./result/bin/geotui"

nix-run:
	nix run .

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info *.spec
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

test:
	pytest

docs:
	cd docs && mkdocs serve

run:
	python -m geotui