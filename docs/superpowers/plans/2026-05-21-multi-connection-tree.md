# Multi-Connection Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-connection right pane with a multi-connection tree where all saved GeoServer connections appear as expandable child nodes under a "GeoServer" root, with lazy connection on expand and color-coded connection states.

**Architecture:** The `GeoServerTree` widget is rewritten to manage multiple connections. A `TreeNodeData` dataclass tags each tree node with its type and parent connection ID. Expanding a connection node lazily triggers `test_connection()` + `get_full_tree()`. All existing actions (F5, F8, F2 create) are updated to detect which connection owns the selected node via `_get_selected_connection()`. The `DualPane` and `App` are simplified since the tree now self-manages its connections from `ConfigManager`.

**Tech Stack:** Python 3.10+, Textual Tree widget, asyncio workers, httpx

---

## File Structure

| File | Change | Responsibility |
|------|--------|----------------|
| `src/geotui/widgets/geoserver_tree.py` | Rewrite | Multi-connection tree with lazy loading |
| `src/geotui/widgets/dual_pane.py` | Modify | Remove set_connection, simplify pane type detection |
| `src/geotui/app.py` | Modify | Remove single-connection restore, pass config_manager to tree |
| `tests/unit/test_multi_conn_tree.py` | Create | Tests for multi-connection tree |
| `tests/unit/test_geoserver_tree.py` | Rewrite | Update existing tests for new API |

---

## Task 1: TreeNodeData model and connection state tracking

**Files:**
- Modify: `src/geotui/widgets/geoserver_tree.py`
- Create: `tests/unit/test_multi_conn_tree.py`

- [ ] **Step 1: Write failing tests for TreeNodeData**

```python
# tests/unit/test_multi_conn_tree.py
"""Tests for multi-connection tree."""

from pathlib import Path

import pytest

from geotui.widgets.geoserver_tree import TreeNodeData


class TestTreeNodeData:
    def test_connection_node(self) -> None:
        data = TreeNodeData(
            node_type="connection",
            name="Production",
            connection_id="abc123",
        )
        assert data.node_type == "connection"
        assert data.connection_id == "abc123"

    def test_workspace_node(self) -> None:
        data = TreeNodeData(
            node_type="workspace",
            name="my_ws",
            connection_id="abc123",
        )
        assert data.node_type == "workspace"

    def test_root_node(self) -> None:
        data = TreeNodeData(
            node_type="root",
            name="GeoServer",
            connection_id="",
        )
        assert data.node_type == "root"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_multi_conn_tree.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Add TreeNodeData to geoserver_tree.py**

Add at the top of `src/geotui/widgets/geoserver_tree.py`, after imports:

```python
@dataclass
class TreeNodeData:
    """Data attached to each tree node for identification.

    Attributes:
        node_type: One of 'root', 'connection', 'workspace',
            'datastore', 'coveragestore', 'wmsstore', 'layer', 'coverage', 'error'.
        name: Display name of the node.
        connection_id: ID of the Connection this node belongs to.
        resource: Optional GeoServerResource for workspace/store/layer nodes.
    """

    node_type: str
    name: str
    connection_id: str
    resource: GeoServerResource | None = None
```

Add `from dataclasses import dataclass` to imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_multi_conn_tree.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add src/geotui/widgets/geoserver_tree.py tests/unit/test_multi_conn_tree.py
git commit -m "feat: add TreeNodeData model for multi-connection tree"
```

---

## Task 2: Rewrite GeoServerTree for multi-connection

This is the core task. The `GeoServerTree` widget is rewritten to:
- Accept a `ConfigManager` instead of a single `Connection`
- Show all connections under a "GeoServer" root
- Track connection states (untested/connected/failed)
- Lazy-load on expand

**Files:**
- Modify: `src/geotui/widgets/geoserver_tree.py`
- Modify: `tests/unit/test_multi_conn_tree.py`

- [ ] **Step 1: Write failing tests for multi-connection tree**

Append to `tests/unit/test_multi_conn_tree.py`:

```python
from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def two_conn_config(tmp_path: Path) -> ConfigManager:
    """Config with two connections."""
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(Connection(name="Production", url="https://192.0.2.1:9999"))
    cm.add_connection(Connection(name="Staging", url="https://192.0.2.2:9999"))
    return cm


@pytest.fixture
def empty_config(tmp_path: Path) -> ConfigManager:
    """Config with no connections."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestMultiConnectionTree:
    @pytest.mark.asyncio
    async def test_tree_shows_all_connections(
        self, two_conn_config: ConfigManager
    ) -> None:
        """All saved connections appear as tree nodes."""
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            from textual.widgets import Tree
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            tree = tree_widget.query_one("#gs-tree", Tree)
            # Root should have 2 connection children
            assert len(tree.root.children) == 2

    @pytest.mark.asyncio
    async def test_empty_config_shows_message(
        self, empty_config: ConfigManager
    ) -> None:
        """No connections shows help message."""
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test() as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            no_conn = tree_widget.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_connection_names_visible(
        self, two_conn_config: ConfigManager
    ) -> None:
        """Connection names appear in the tree."""
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            from textual.widgets import Tree
            tree = tree_widget.query_one("#gs-tree", Tree)
            names = {child.data.name for child in tree.root.children if child.data}
            assert "Production" in names
            assert "Staging" in names

    @pytest.mark.asyncio
    async def test_connection_nodes_start_untested(
        self, two_conn_config: ConfigManager
    ) -> None:
        """Connection nodes start in 'untested' state."""
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            for conn_id in tree_widget._connection_states:
                assert tree_widget._connection_states[conn_id] == "untested"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_multi_conn_tree.py::TestMultiConnectionTree -v`
Expected: FAIL (old API doesn't match)

- [ ] **Step 3: Rewrite GeoServerTree**

Replace the core of `GeoServerTree` in `src/geotui/widgets/geoserver_tree.py`. The key changes:

**Remove:**
- `connection: reactive[Connection | None]` reactive
- `watch_connection()` watcher
- `_load_tree(conn)` single-connection loader

**Add:**
- `__init__(self, config_manager: ConfigManager, **kwargs)` - accepts ConfigManager
- `_connections: dict[str, Connection]` - all connections by ID
- `_connection_states: dict[str, str]` - "untested" / "connected" / "failed"
- `_connection_errors: dict[str, str]` - error messages for failed connections
- `refresh_connections()` - reloads connection list from ConfigManager, rebuilds tree
- `on_tree_node_expanded(event)` - triggers lazy connection + tree fetch
- `_get_selected_connection() -> tuple[Connection, str] | None` - walks tree to find connection
- `_fetch_connection_tree(conn_id)` - async worker to test + load one connection

**Compose:** The tree root is "GeoServer". On mount, call `refresh_connections()` which adds one child node per connection. No connection attempts until expanded.

**on_tree_node_expanded:** When a connection node is expanded:
1. If state is "untested" or "failed": run `_fetch_connection_tree(conn_id)` as worker
2. If state is "connected": already loaded, do nothing

**_fetch_connection_tree(conn_id):**
1. Call `test_connection(conn)`
2. If fails: set state to "failed", add red error child node, return
3. If succeeds: set state to "connected", fetch `get_full_tree()`, populate children

**_get_selected_connection():** Walk from cursor node up through parents until finding a node with `TreeNodeData.node_type == "connection"`, return its Connection and workspace name.

**Update all action methods** (action_copy_from_local, action_delete_selected, action_create_workspace, action_create_store) to use `_get_selected_connection()` instead of `self.connection`.

The full implementation is too large to include inline. The subagent implementing this task should:
1. Read the current geoserver_tree.py completely
2. Rewrite it preserving: CSS, action panel logic, all action methods
3. Replace: connection management, tree building, node data model
4. Update: all methods that reference `self.connection` to use `_get_selected_connection()`

Key patterns to preserve:
- `_show_fields()` / `_get_field_values()` / `_hide_action_panel()` action panel
- `_do_create()` dispatch
- `action_copy_from_local()` / `_run_copy_publish()` publish workflow
- `action_delete_selected()` / `_do_delete()` delete workflow
- All CSS styling

Key patterns to change:
- `self.connection` -> `conn` from `_get_selected_connection()`
- `self.refresh_tree()` -> `self._refresh_connection(conn_id)`
- Tree population: per-connection subtree instead of global tree

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_multi_conn_tree.py -v`
Expected: PASS

- [ ] **Step 5: Lint, format, commit**

```
git add src/geotui/widgets/geoserver_tree.py tests/unit/test_multi_conn_tree.py
git commit -m "feat: multi-connection tree with lazy loading and state tracking"
```

---

## Task 3: Update DualPane and App

**Files:**
- Modify: `src/geotui/widgets/dual_pane.py`
- Modify: `src/geotui/app.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_multi_conn_tree.py`:

```python
from geotui.widgets.dual_pane import DualPane


class TestDualPaneMultiConn:
    @pytest.mark.asyncio
    async def test_pane_type_geoserver_with_connections(
        self, two_conn_config: ConfigManager
    ) -> None:
        """Pane type is 'geoserver' when connections exist."""
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            assert dual_pane.get_active_pane_type() == "geoserver"

    @pytest.mark.asyncio
    async def test_pane_type_local_with_no_connections(
        self, empty_config: ConfigManager
    ) -> None:
        """Pane type is 'local' when no connections exist."""
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test() as pilot:
            await pilot.pause()
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            assert dual_pane.get_active_pane_type() == "local"
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Update DualPane**

In `src/geotui/widgets/dual_pane.py`:

- Remove `set_connection()` method
- Update `compose()`: pass `config_manager` to GeoServerTree
  ```python
  yield GeoServerTree(config_manager=self._config_manager, id="right-pane")
  ```
- Add `__init__` to accept config_manager:
  ```python
  def __init__(self, config_manager: ConfigManager, **kwargs):
      super().__init__(**kwargs)
      self._config_manager = config_manager
  ```
- Update `get_active_pane_type()`: return "geoserver" if config has any connections
  ```python
  def get_active_pane_type(self) -> str:
      right = self.query_one("#right-pane", GeoServerTree)
      if self.active_pane == "right" and right._connections:
          return "geoserver"
      # Also check focus
      ...same focus-walk logic but check _connections...
      return "local"
  ```

- [ ] **Step 4: Update App**

In `src/geotui/app.py`:

- Update `compose()`: pass config_manager to DualPane
  ```python
  yield DualPane(config_manager=self.config_manager)
  ```
- Remove from `on_mount()`: the active connection restore loop (tree self-manages)
- Keep splash screen in `on_mount()`
- Update `action_copy()`: check `_get_selected_connection()` instead of `tree.connection`
  ```python
  def action_copy(self) -> None:
      tree = self.query_one("#right-pane", GeoServerTree)
      selected = tree._get_selected_connection()
      if selected is None:
          self.notify(_("Select a workspace in the GeoServer tree"), severity="error")
          return
      tree.action_copy_from_local()
  ```
- Update `action_delete()`: similar pattern

- [ ] **Step 5: Run tests**

Run: `pytest tests/ --no-header -q`
Expected: All pass

- [ ] **Step 6: Lint, format, commit**

```
git add src/geotui/widgets/dual_pane.py src/geotui/app.py tests/unit/test_multi_conn_tree.py
git commit -m "feat: wire DualPane and App for multi-connection tree"
```

---

## Task 4: Update existing tests

**Files:**
- Modify: `tests/unit/test_geoserver_tree.py`
- Modify: `tests/unit/test_f5_copy.py`
- Modify: `tests/unit/test_geoserver_actions.py`
- Modify: `tests/unit/test_context_menu.py`
- Modify: `tests/unit/test_app.py`

- [ ] **Step 1: Update all tests that use the old single-connection API**

Tests that call `dual_pane.set_connection(conn)` or check `tree.connection` need updating. The new pattern:
- Instead of setting a single active connection, add connections to ConfigManager
- Instead of checking `tree.connection`, check `tree._connections`
- Tests for F5/F8/F2 that need a connected server should add a connection and note that the tree won't auto-connect (lazy loading)

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ --no-header -q`
Expected: All pass

- [ ] **Step 3: Commit**

```
git add tests/
git commit -m "test: update existing tests for multi-connection tree API"
```

---

## Task 5: Settings screen integration

When connections are added/removed in F9 settings, the tree should refresh.

**Files:**
- Modify: `src/geotui/screens/settings.py`
- Modify: `src/geotui/widgets/geoserver_tree.py`

- [ ] **Step 1: Write failing test**

```python
# Append to tests/unit/test_multi_conn_tree.py
class TestSettingsIntegration:
    @pytest.mark.asyncio
    async def test_adding_connection_updates_tree(
        self, empty_config: ConfigManager
    ) -> None:
        """Adding a connection in config refreshes the tree."""
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            # Initially no connections
            from textual.widgets import Tree
            tree = tree_widget.query_one("#gs-tree", Tree)
            assert len(tree.root.children) == 0
            # Add a connection via config
            empty_config.add_connection(
                Connection(name="New", url="https://192.0.2.1:9999")
            )
            tree_widget.refresh_connections()
            await pilot.pause()
            assert len(tree.root.children) == 1
```

- [ ] **Step 2: Update settings.py**

After successful connection test (Connect button), after add/remove/update connection, call:
```python
try:
    tree = self.app.query_one("#right-pane", GeoServerTree)
    tree.refresh_connections()
except Exception:
    pass
```

- [ ] **Step 3: Run tests, lint, commit**

```
git add src/geotui/screens/settings.py src/geotui/widgets/geoserver_tree.py tests/
git commit -m "feat: settings changes refresh connection tree"
```

---

## Task 6: BDD feature, docs, version bump

**Files:**
- Create: `tests/bdd/features/multi_connection_tree.feature`
- Modify: `SPECIFICATION.md`

- [ ] **Step 1: Write BDD feature**

```gherkin
Feature: Multi-Connection Tree
  As a GeoServer administrator
  I want to see all my GeoServer connections in one tree
  So that I can manage multiple servers from one interface

  Scenario: All connections shown on startup
    Given I have 3 saved GeoServer connections
    When the application starts
    Then I should see 3 connection nodes in the tree

  Scenario: Expanding connection triggers lazy load
    Given I have a saved GeoServer connection
    When I expand the connection node
    Then a connection attempt is made
    And workspaces appear if successful

  Scenario: Failed connection shown in red
    Given I have a connection to an unreachable server
    When I expand the connection node
    Then the node should be shown in red
    And an error message should appear as a child node

  Scenario: R key retries failed connection
    Given I have a failed connection node
    When I press R on the failed node
    Then a new connection attempt is made
```

- [ ] **Step 2: Update SPECIFICATION.md**

Add FR-012: Multi-Connection Tree. Update version history with 0.6.0.

- [ ] **Step 3: Version bump to 0.6.0**

Update `__init__.py`, `pyproject.toml`, `flake.nix`.

- [ ] **Step 4: Full CI check, commit, push**

```
git add -A
git commit -m "release: v0.6.0 - multi-connection tree"
git push
```
