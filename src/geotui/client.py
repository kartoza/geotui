"""GeoServer REST API client.

Provides async methods for connection testing and fetching GeoServer
resources (workspaces, stores, layers) via the REST API.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx

from geotui.config import Connection


@dataclass
class ConnectionResult:
    """Result of a GeoServer connection test.

    Attributes:
        success: Whether the connection was successful.
        message: Human-readable result message.
        version: GeoServer version string if connected.
    """

    success: bool
    message: str
    version: str = ""


@dataclass
class GeoServerResource:
    """A resource in the GeoServer hierarchy.

    Attributes:
        name: Resource name.
        resource_type: Type of resource (workspace, datastore, coveragestore, wmsstore, layer, coverage, wms_layer).
        children: Child resources.
        href: REST API href for this resource.
    """

    name: str
    resource_type: str
    children: list["GeoServerResource"] = field(default_factory=list)
    href: str = ""


class GeoServerClient:
    """Async client for GeoServer REST API.

    Provides methods to fetch the resource hierarchy:
    workspaces -> stores -> layers.

    Args:
        conn: Connection configuration.
        timeout: Request timeout in seconds.
    """

    def __init__(self, conn: Connection, timeout: float = 10.0) -> None:
        """Initialize the client.

        Args:
            conn: Connection configuration.
            timeout: Request timeout in seconds.
        """
        self._conn = conn
        self._base_url = conn.url.rstrip("/")
        self._timeout = timeout
        self._auth = httpx.BasicAuth(conn.username, conn.password)

    async def _get(self, path: str) -> Any:
        """Make an authenticated GET request to the REST API.

        Args:
            path: API path relative to base URL.

        Returns:
            Parsed JSON response or None on failure.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, verify=True
            ) as client:
                response = await client.get(
                    f"{self._base_url}{path}",
                    auth=self._auth,
                    headers={"Accept": "application/json"},
                )
                if response.status_code == 200:
                    return response.json()
        except httpx.RequestError:
            pass
        return None

    async def get_workspaces(self) -> list[GeoServerResource]:
        """Fetch all workspaces.

        Returns:
            List of workspace resources.
        """
        data = await self._get("/rest/workspaces.json")
        if not data:
            return []

        workspaces_data = data.get("workspaces", {})
        if not workspaces_data:
            return []

        workspace_list = workspaces_data.get("workspace", [])
        if isinstance(workspace_list, dict):
            workspace_list = [workspace_list]

        return [
            GeoServerResource(
                name=ws.get("name", ""),
                resource_type="workspace",
                href=ws.get("href", ""),
            )
            for ws in workspace_list
            if ws.get("name")
        ]

    async def get_datastores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch data stores for a workspace.

        Args:
            workspace: Workspace name.

        Returns:
            List of datastore resources.
        """
        data = await self._get(f"/rest/workspaces/{workspace}/datastores.json")
        if not data:
            return []

        stores_data = data.get("dataStores", {})
        if not stores_data:
            return []

        store_list = stores_data.get("dataStore", [])
        if isinstance(store_list, dict):
            store_list = [store_list]

        return [
            GeoServerResource(
                name=s.get("name", ""),
                resource_type="datastore",
                href=s.get("href", ""),
            )
            for s in store_list
            if s.get("name")
        ]

    async def get_coveragestores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch coverage stores for a workspace.

        Args:
            workspace: Workspace name.

        Returns:
            List of coveragestore resources.
        """
        data = await self._get(f"/rest/workspaces/{workspace}/coveragestores.json")
        if not data:
            return []

        stores_data = data.get("coverageStores", {})
        if not stores_data:
            return []

        store_list = stores_data.get("coverageStore", [])
        if isinstance(store_list, dict):
            store_list = [store_list]

        return [
            GeoServerResource(
                name=s.get("name", ""),
                resource_type="coveragestore",
                href=s.get("href", ""),
            )
            for s in store_list
            if s.get("name")
        ]

    async def get_wmsstores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch WMS stores for a workspace.

        Args:
            workspace: Workspace name.

        Returns:
            List of wmsstore resources.
        """
        data = await self._get(f"/rest/workspaces/{workspace}/wmsstores.json")
        if not data:
            return []

        stores_data = data.get("wmsStores", {})
        if not stores_data:
            return []

        store_list = stores_data.get("wmsStore", [])
        if isinstance(store_list, dict):
            store_list = [store_list]

        return [
            GeoServerResource(
                name=s.get("name", ""),
                resource_type="wmsstore",
                href=s.get("href", ""),
            )
            for s in store_list
            if s.get("name")
        ]

    async def get_layers_for_datastore(
        self, workspace: str, store: str
    ) -> list[GeoServerResource]:
        """Fetch feature type layers for a data store.

        Args:
            workspace: Workspace name.
            store: Data store name.

        Returns:
            List of layer resources.
        """
        data = await self._get(
            f"/rest/workspaces/{workspace}/datastores/{store}/featuretypes.json"
        )
        if not data:
            return []

        ft_data = data.get("featureTypes", {})
        if not ft_data:
            return []

        ft_list = ft_data.get("featureType", [])
        if isinstance(ft_list, dict):
            ft_list = [ft_list]

        return [
            GeoServerResource(
                name=ft.get("name", ""),
                resource_type="layer",
                href=ft.get("href", ""),
            )
            for ft in ft_list
            if ft.get("name")
        ]

    async def get_coverages(
        self, workspace: str, store: str
    ) -> list[GeoServerResource]:
        """Fetch coverages for a coverage store.

        Args:
            workspace: Workspace name.
            store: Coverage store name.

        Returns:
            List of coverage resources.
        """
        data = await self._get(
            f"/rest/workspaces/{workspace}/coveragestores/{store}/coverages.json"
        )
        if not data:
            return []

        cov_data = data.get("coverages", {})
        if not cov_data:
            return []

        cov_list = cov_data.get("coverage", [])
        if isinstance(cov_list, dict):
            cov_list = [cov_list]

        return [
            GeoServerResource(
                name=c.get("name", ""),
                resource_type="coverage",
                href=c.get("href", ""),
            )
            for c in cov_list
            if c.get("name")
        ]

    async def get_full_tree(self) -> list[GeoServerResource]:
        """Fetch the full resource hierarchy.

        Builds a tree: workspaces -> stores -> layers/coverages.

        Returns:
            List of workspace resources with populated children.
        """
        workspaces = await self.get_workspaces()

        for ws in workspaces:
            datastores = await self.get_datastores(ws.name)
            for ds in datastores:
                ds.children = await self.get_layers_for_datastore(ws.name, ds.name)

            coveragestores = await self.get_coveragestores(ws.name)
            for cs in coveragestores:
                cs.children = await self.get_coverages(ws.name, cs.name)

            wmsstores = await self.get_wmsstores(ws.name)

            ws.children = datastores + coveragestores + wmsstores

        return workspaces


async def test_connection(conn: Connection, timeout: float = 10.0) -> ConnectionResult:
    """Test a GeoServer connection by querying the REST API.

    Validates credentials by hitting /rest/about/version.json which
    requires authentication on most GeoServer installations.

    Args:
        conn: Connection configuration to test.
        timeout: Request timeout in seconds.

    Returns:
        ConnectionResult with success status and details.
    """
    if not conn.url:
        return ConnectionResult(success=False, message="URL is required")

    url = conn.url.rstrip("/")
    endpoint = f"{url}/rest/about/version.json"

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            verify=True,
        ) as client:
            response = await client.get(
                endpoint,
                auth=httpx.BasicAuth(conn.username, conn.password),
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    resources = data.get("about", {}).get("resource", [])
                    version = ""
                    for resource in resources:
                        if resource.get("@name") == "GeoServer":
                            version = resource.get("Version", "unknown")
                            break
                    return ConnectionResult(
                        success=True,
                        message=f"Connected to GeoServer {version}",
                        version=version,
                    )
                except (ValueError, KeyError):
                    return ConnectionResult(
                        success=True,
                        message="Connected (could not parse version)",
                    )
            elif response.status_code == 401:
                return ConnectionResult(
                    success=False,
                    message="Authentication failed: invalid credentials",
                )
            elif response.status_code == 403:
                return ConnectionResult(
                    success=False,
                    message="Access forbidden: insufficient permissions",
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"Server returned HTTP {response.status_code}",
                )
    except httpx.ConnectTimeout:
        return ConnectionResult(
            success=False,
            message="Connection timed out",
        )
    except httpx.ConnectError:
        return ConnectionResult(
            success=False,
            message=f"Cannot connect to {url}",
        )
    except httpx.RequestError as e:
        return ConnectionResult(
            success=False,
            message=f"Request error: {e}",
        )
