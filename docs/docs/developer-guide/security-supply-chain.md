# Security & Supply Chain

## Software Bill of Materials (SBOM)

Every pull request and release automatically generates a **CycloneDX JSON SBOM** listing all runtime and transitive dependencies. This is produced by the `cyclonedx-py` tool in the `pr-artifacts.yml` and `release.yml` GitHub Actions workflows.

The SBOM is attached as a build artifact to:

- Every PR (downloadable from the PR's Actions artifacts)
- Every GitHub Release (attached alongside binaries)

### Generating an SBOM Locally

```bash
pip install cyclonedx-bom
cyclonedx-py environment -o sbom.json --format json
```

## CVE & Vulnerability Scanning

### Automated PR Security Scanning

The `pr-artifacts.yml` workflow runs three security scanners on every pull request:

| Scanner | What it checks | Output |
|---------|---------------|--------|
| **pip-audit** | Known CVEs in Python dependencies (PyPI advisory database) | JSON + text report |
| **safety** | Dependency vulnerability database (Safety DB) | Console output |
| **bandit** | Static analysis of source code for security issues (OWASP patterns) | JSON + text report |

Results are automatically posted as a **sticky comment** on the PR with:

- A summary table of any findings (package, version, CVE ID, severity)
- A pass/fail status for each scanner
- Blocking status: PRs with **CRITICAL** vulnerabilities cannot be merged

### Running Security Scans Locally

```bash
# Dependency vulnerability audit
pip-audit --format json --output audit.json
pip-audit  # human-readable output

# Static security analysis
bandit -r src/ -c pyproject.toml
bandit -r src/ -f json -o bandit.json  # JSON output

# Safety check
safety check
```

## Dependency Management

### Runtime Dependencies

| Package | Version | Purpose | Security relevance |
|---------|---------|---------|-------------------|
| **textual** | >=1.0.0 | TUI framework | No network access |
| **rich** | >=13.0.0 | Terminal rendering | No network access |
| **httpx** | >=0.27.0 | Async HTTP client | GeoServer REST API calls (HTTPS enforced) |
| **pydantic** | >=2.0.0 | Data validation | Input validation and serialisation |
| **cryptography** | >=42.0.0 | Fernet encryption | Credential vault (AES-128-CBC + HMAC-SHA256) |
| **keyring** | >=25.0.0 | System keyring | Reserved for future OS keyring integration |
| **fpdf2** | >=2.8.0 | PDF generation | Report output only |
| **click** | >=8.0.0 | CLI framework | CLI argument parsing |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | >=8.0.0 | Test framework |
| **pytest-asyncio** | >=0.24.0 | Async test support |
| **pytest-bdd** | >=7.0.0 | BDD testing with Gherkin |
| **pytest-cov** | >=5.0.0 | Coverage measurement |
| **ruff** | >=0.8.0 | Linter and formatter |
| **mypy** | >=1.0.0 | Static type checking |
| **bandit** | >=1.7.0 | Security linting |
| **codespell** | - | Spell checking |

### Documentation Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **mkdocs** | >=1.6.0 | Documentation site generator |
| **mkdocs-material** | >=9.5.0 | Material theme |
| **mkdocstrings[python]** | >=0.27.0 | Auto-generate API docs from docstrings |

## CI/CD Pipeline Security

### Continuous Integration (`ci.yml`)

Every push and PR runs:

1. **Linting** — `ruff check` for code quality and `bandit` for security patterns
2. **Testing** — `pytest` across Python 3.10-3.13 on Linux, macOS, and Windows
3. **Type checking** — `mypy` with strict settings
4. **Docs build** — `mkdocs build --strict` to catch broken links

### PR Artifacts (`pr-artifacts.yml`)

Every PR additionally builds:

1. **Standalone binaries** — PyInstaller builds for Linux, macOS (Intel + ARM), Windows
2. **Python packages** — wheel and sdist
3. **SBOM** — CycloneDX JSON
4. **Security scan** — pip-audit + safety + bandit with PR comment report

### Release Pipeline (`release.yml`)

Triggered by `v*` tags, builds:

1. **Python packages** — wheel + sdist for PyPI
2. **Standalone binaries** — 4 platform builds (Linux x86_64, macOS x86_64, macOS ARM64, Windows x86_64)
3. **Linux packages** — .deb, .rpm, AppImage, Snap
4. **SBOM** — CycloneDX JSON attached to the GitHub Release

## Pre-commit Security Hooks

The `.pre-commit-config.yaml` includes security-focused hooks:

```yaml
# Security scanning on every commit
- repo: local
  hooks:
    - id: bandit
      name: bandit security scan
      entry: bandit -r src/ -c pyproject.toml
      language: system

# Secrets detection
- repo: https://github.com/pre-commit/pre-commit-hooks
  hooks:
    - id: detect-private-key  # Prevents committing private keys
```

## Credential Security

See the [Security page](../admin-guide/security.md) for details on:

- Fernet encryption (AES-128-CBC + HMAC-SHA256)
- PBKDF2-HMAC-SHA256 key derivation (600k iterations)
- Vault architecture and file permissions
- Threat model

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email [info@kartoza.com](mailto:info@kartoza.com) with details
3. Include steps to reproduce if possible
4. We will respond within 48 hours

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
