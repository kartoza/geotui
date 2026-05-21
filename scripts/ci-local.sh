#!/usr/bin/env bash
# Run all CI checks locally (mirrors .github/workflows/ci.yml)
set -e

echo "=== Ruff Check ==="
ruff check src/ tests/

echo ""
echo "=== Ruff Format ==="
ruff format --check src/ tests/

echo ""
echo "=== Bandit ==="
bandit -r src/ -c pyproject.toml

echo ""
echo "=== Codespell ==="
codespell --skip '*.po,*.pot,*.mo,*.lock,docs/site' src/ tests/ docs/ README.md SPECIFICATION.md PACKAGES.md

echo ""
echo "=== Mypy ==="
mypy src/ --ignore-missing-imports

echo ""
echo "=== Pytest ==="
pytest --no-header -q

echo ""
echo "=== Docs Build ==="
cd docs && mkdocs build --strict

echo ""
echo "=== All CI checks passed ==="
