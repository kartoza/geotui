# Multi-Connection Tree Design

**Date:** 2026-05-21
**Status:** Approved

## Overview

Replace the single-connection right pane with a multi-connection tree.
All saved GeoServer connections are listed as child nodes under a
"GeoServer" root. Expanding a node triggers a lazy connection attempt
and fetches the workspace/store/layer hierarchy.

## Tree Structure

```
GeoServer
  Production Server        [collapsed, grey - untested]
  Local Test GeoServer     [expanded, teal - connected]
      my_workspace
          postgis_store [vector]
              roads
              buildings
          dem_store [raster]
              elevation
  Staging                  [collapsed, red - failed]
      Connection failed: Authentication failed
```

## Connection States

| State | Color | Meaning |
|-------|-------|---------|
| Untested | Grey (#8A8B8B) | Never expanded, no connection attempted |
| Connected | Teal (#06969A) | Successfully connected, tree loaded |
| Failed | Red (#CC0403) | Last connection attempt failed |

## Behaviour

### Loading
- All saved connections listed on startup from ConfigManager
- No connection attempts until a node is expanded (lazy)
- Expanding a node triggers `test_connection()` then `get_full_tree()`
- If connection fails, node turns red with error as child text node

### Retry
- R key on a failed (red) connection node retries the connection
- F2 menu "Refresh" also retries the selected connection
- No automatic background retry/polling

### Actions
- F5 (Copy/Publish) targets whichever connection's workspace/store
  is highlighted in the tree
- F8 (Delete) works on any connection's resources
- F2 menu actions (Create Workspace, Create Store) apply to the
  connection that owns the selected node
- F9 (Settings) still manages connection CRUD; adding/removing
  connections in F9 updates the tree immediately

### Context Detection
- `_get_selected_connection()` walks up the tree from cursor to find
  which connection node owns the selected resource
- `_get_selected_workspace()` updated to also identify the parent
  connection
- `get_active_pane_type()` returns "geoserver" if any connections
  exist in config (not just if one is connected)

## Code Changes

### Modified Files

| File | Change |
|------|--------|
| `src/geotui/widgets/geoserver_tree.py` | Rewrite: single connection -> multi-connection tree |
| `src/geotui/widgets/dual_pane.py` | Update `get_active_pane_type()` and `set_connection()` |
| `src/geotui/app.py` | Remove single-connection restore on startup, tree loads from config |
| `src/geotui/screens/settings.py` | After connection CRUD, notify tree to refresh connection list |

### GeoServerTree Changes

**Removed:**
- `connection: reactive[Connection | None]` single connection reactive
- `set_connection()` / `watch_connection()` single connection methods

**Added:**
- `_connections: dict[str, Connection]` all saved connections keyed by ID
- `_clients: dict[str, GeoServerClient]` lazily created clients per connection
- `_connection_states: dict[str, str]` tracks "untested"/"connected"/"failed"
- `_get_selected_connection() -> tuple[Connection, str] | None` walks tree
  to find which connection owns the cursor node
- `refresh_connections()` reloads connection list from ConfigManager
- `on_tree_node_expanded()` triggers lazy connection + tree fetch

### Tree Node Data

Each tree node stores data identifying what it represents:

```python
@dataclass
class TreeNodeData:
    """Data attached to each tree node."""
    node_type: str  # "root", "connection", "workspace", "datastore", etc.
    name: str
    connection_id: str  # which connection this belongs to
    resource: GeoServerResource | None = None
```

### DualPane Changes

- Remove `set_connection()` (no longer needed)
- `get_active_pane_type()` returns "geoserver" if ConfigManager has
  any connections (tree always shows them)

### App Changes

- Remove `on_mount()` restore of single active connection
- Tree self-populates from ConfigManager on mount

## Error Handling

- Connection failure: node turns red, error message as child node
- Expanding a failed node with R: retries connection
- Network timeout during tree fetch: partial tree shown with error
- ConfigManager changes (F9): tree refreshes immediately via message

## Testing

- Unit tests for tree node data model
- Unit tests for connection state management
- Unit tests for `_get_selected_connection()` tree traversal
- Test lazy loading (expand triggers connection)
- Test failed state display
- Test F5/F8 with multi-connection (correct connection targeted)
- BDD feature: `multi_connection_tree.feature`
