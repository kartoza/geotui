# GeoTUI - Technical Specification

## Version: 0.1.0

## 1. Overview

GeoTUI is a Midnight Commander-style terminal user interface (TUI) application for managing GeoServer instances. It provides a dual-pane interface built with Python using the Textual and Rich frameworks.

## 2. Architecture

### 2.1 Component Diagram

```mermaid
graph TB
    subgraph Application
        A[GeoTUIApp] --> B[Header]
        A --> C[DualPane]
        A --> D[StatusBar]
        A --> E[Footer]
    end

    subgraph DualPane
        C --> F[FilePane Left]
        C --> G[FilePane Right]
    end

    subgraph FilePane
        F --> H[Pane Header]
        F --> I[DirectoryTree]
        F --> J[Pane Footer]
    end

    subgraph Support
        K[Theme Module] --> A
        L[i18n Module] --> A
    end
```

### 2.2 Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| TUI Framework | Textual |
| Rich Text | Rich |
| HTTP Client | httpx |
| Data Validation | Pydantic |
| Credential Encryption | cryptography (Fernet/PBKDF2) |
| Build System | Hatch |
| Dev Environment | Nix Flake |

## 3. User Stories

### US-001: Dual Pane Navigation
**As a** GeoServer administrator
**I want** a Midnight Commander-style dual pane interface
**So that** I can efficiently browse and manage files and resources side by side

**Acceptance Criteria:**
- Application displays two side-by-side panes
- Each pane shows a directory tree
- Tab key switches active pane
- Active pane is visually distinguished (yellow/orange border)
- Inactive pane has blue border

### US-002: Language Switching
**As a** non-English speaking user
**I want** to switch the interface language
**So that** I can use the application in my preferred language

**Acceptance Criteria:**
- Ctrl+L cycles through English, Portuguese, Spanish
- On startup, auto-detects system locale and selects matching language if supported
- GEOTUI_LANG environment variable overrides system locale detection
- All UI strings are translatable
- Footer binding labels update immediately when language changes
- Status bar text updates when language changes
- Modal screens (settings, context menu, etc.) use the current language when opened
- Translations use compiled GNU gettext .mo files for performance

### US-003: File Navigation
**As a** user
**I want** to browse the file system in each pane
**So that** I can find and manage files

**Acceptance Criteria:**
- Directory tree shows folders and files
- Arrow keys navigate the tree
- Enter opens/expands directories
- Current path shown in pane footer

### US-004: Function Key Operations
**As a** Midnight Commander user
**I want** familiar function key bindings
**So that** I can use muscle memory from MC

**Acceptance Criteria:**
- F1: Help
- F2: Menu
- F5: Copy
- F6: Move
- F7: Create directory
- F8: Delete
- F9: Settings
- F10: Quit

### US-005: Bulk Shapefile Publishing
**As a** GeoServer administrator
**I want** to bulk publish thousands of shapefiles
**So that** I can set up large datasets without manual layer-by-layer configuration

**Acceptance Criteria:**
- Can discover and publish 4000+ shapefiles in one operation
- Supports create and update (idempotent)
- Dry-run mode for validation
- Concurrent uploads with configurable limit

### US-006: Publish Reporting
**As a** GeoServer administrator
**I want** a detailed report after bulk publishing
**So that** I have an audit trail of what was uploaded

**Acceptance Criteria:**
- PDF report with branded header, detail table, summary stats
- Color-coded rows (green=success, red=error, grey=skip, blue=dry-run)
- JSON report for automation
- Report path displayed after completion

### US-007: CLI Bulk Publishing
**As a** DevOps engineer
**I want** to run bulk publish from the command line
**So that** I can integrate it into CI/CD pipelines

**Acceptance Criteria:**
- `geotui publish` command with all options
- Uses saved connections (no credentials in command args)
- Progress output and exit code on failure
- PDF and JSON reports generated

## 4. Functional Requirements

### FR-001: Application Launch
- Application starts in dark mode by default
- Left pane is active on launch
- Both panes show user's home directory initially

### FR-002: Theming
- Kartoza brand colors applied consistently
- Rounded corner borders on all panes
- Dark and light theme support

### FR-003: Internationalization
- Three languages: English (default), Portuguese, Spanish
- Runtime language switching without restart via Ctrl+L
- Compiled GNU gettext .mo files for translation loading
- Footer and status bar refresh immediately on language change
- Binding descriptions stored as specs and rebuilt on language switch
- GEOTUI_LANG environment variable for initial language selection

### FR-004: Security
- **Master Password Vault**: All connection passwords encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256) with PBKDF2-HMAC-SHA256 key derivation (600k iterations)
- **Startup Unlock**: TUI prompts for master password during startup; CLI prompts before accessing connections (3 attempts max)
- **Mandatory Vault Setup**: First-time users are taken directly to master password creation on first launch (min 8 characters, confirmation required). Users may cancel to proceed without encryption.
- **Password Change**: Re-encrypts all stored credentials with new key derived from new password
- **Vault Reset**: Wipes all connections when master password is forgotten (requires explicit confirmation)
- **File Permissions**: Config file restricted to 0o600, config directory to 0o700
- **Input Validation**: GeoServer resource names validated against `[a-zA-Z0-9_.\-]+` regex (max 256 chars)
- **No Command Injection**: Subprocess calls use list args, no shell=True
- HTTPS connections enforced (verify=True on all httpx calls)

### FR-005: Cross-Platform
- Windows (PowerShell) support
- Linux support
- macOS support

## 5. Non-Functional Requirements

### NFR-001: Performance
- Application launches in under 2 seconds
- UI responds to input within 100ms

### NFR-002: Testing
- Minimum 80% code coverage
- TDD and BDD test approaches
- Unit tests for all modules
- BDD features for user workflows

### NFR-003: Documentation
- mkdocs site with user, admin, and developer guides
- Google-style docstrings on all public functions
- Architecture diagrams in Mermaid

### NFR-004: CI/CD
- Pre-commit hooks for code quality
- GitHub Actions for PR validation
- Automated release with package building
- Documentation deployed to GitHub Pages

### FR-006: Connection Management
- Users can manage multiple GeoServer connection instances
- Each connection has: Name, URL, Username, Password
- Connections listed by name in settings screen (left panel)
- Selecting a connection shows its details (right panel, view mode)
- Inline edit form (no popups) for add/edit operations
- Connection testing via GeoServer REST API (/rest/about/version.json)
- Configuration persisted as JSON in XDG config directory
- Atomic file writes prevent corruption

### FR-007: Multi-Connection GeoServer Tree
- Right pane shows all saved connections under a "GeoServer" root node
- Each connection is a collapsible node with lazy loading on expand
- Connection states: grey (untested), teal (connected), red (failed)
- Expanding a connection node tests connectivity then fetches hierarchy
- Tree shows: Connection > Workspaces > Stores > Layers/Coverages
- Failed connections show red node with error message as child
- R key retries a failed connection
- F5/F8/F2 actions target whichever connection is highlighted
- No background polling - retry is manual only
- Adding/removing connections in F9 updates tree immediately

### FR-008: F5 Copy-to-Publish
- Midnight Commander F5 paradigm: select folder left, workspace/store right, F5
- Multi-format discovery: Shapefile, GeoPackage (.gpkg), GeoTIFF (.tif/.tiff)
- Vector formats auto-create one datastore per format type (e.g. folder_shapefiles);
  GeoTIFF rasters auto-create one coverage store per file via the `file.geotiff`
  REST endpoint
- Concurrent upload bounded by configurable concurrency (default: 4)
- Retry with exponential backoff on transient failures
- Idempotent: create new layers or update existing ones
- Progress in status bar + tree auto-refreshes as layers appear
- PDF + JSON report generated automatically after every publish
- Layer naming via basename strategy, collision detection before upload

### FR-009: Publish Reports
- PDF report with Kartoza + GeoTUI dual branding
- Three sections: job summary header, color-coded detail table, summary stats
- Handles 4000+ rows with paginated tables and repeating headers
- JSON report alongside PDF for programmatic consumption
- Reports saved to ~/.local/share/geotui/reports/
- Generated automatically after every F5 copy operation

### FR-010: CLI Interface
- `geotui publish` for headless/CI bulk publishing
- `geotui export` for workspace config export (stub)
- `geotui import-config` for config replay (stub)
- Uses saved connections from config.json
- Progress output and summary on completion

## 6. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-07-22 | GeoTIFF publishing wired into F5 pipeline (per-file coverage stores) |
| 0.6.0 | 2026-05-21 | Multi-connection tree, lazy loading, connection states |
| 0.5.0 | 2026-05-21 | F5 copy-to-publish, multi-format support, replaces F2 bulk publish |
| 0.4.0 | 2026-05-20 | Bulk shapefile publisher, PDF/JSON reports, CLI interface |
| 0.3.0 | 2026-05-19 | GeoServer resource tree in right pane, full REST API client |
| 0.2.0 | 2026-05-19 | Connection management, settings screen, GeoServer API client |
| 0.1.0 | 2026-05-19 | Initial release - dual pane MC-style interface |
