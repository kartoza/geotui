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
        resource_type: Type of resource (workspace, datastore,
            coveragestore, wmsstore, layer, coverage, wms_layer).
        children: Child resources.
        href: REST API href for this resource.
    """

    name: str
    resource_type: str
    children: list["GeoServerResource"] = field(default_factory=list)
    href: str = ""


async def resolve_base_url(
    url: str, username: str, password: str, timeout: float = 10.0
) -> str:
    """Resolve the correct GeoServer REST API base URL.

    Tries the URL as-is first, then falls back to {url}/geoserver.
    This allows users to provide either the base domain or the full
    GeoServer path.

    Args:
        url: User-provided URL.
        username: GeoServer username.
        password: GeoServer password.
        timeout: Request timeout in seconds.

    Returns:
        The working base URL, or the original URL if neither works.
    """
    base = url.rstrip("/")
    auth = httpx.BasicAuth(username, password)
    candidates = [base]
    if not base.endswith("/geoserver"):
        candidates.append(f"{base}/geoserver")

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=True) as client:
            for candidate in candidates:
                try:
                    resp = await client.get(
                        f"{candidate}/rest/about/version.json",
                        auth=auth,
                        headers={"Accept": "application/json"},
                    )
                    if resp.status_code == 200:
                        return candidate
                except httpx.RequestError:
                    continue
    except httpx.RequestError:
        pass

    return base


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
        self._resolved = False

    async def _ensure_resolved(self) -> None:
        """Resolve the correct base URL on first use."""
        if not self._resolved:
            self._base_url = await resolve_base_url(
                self._base_url,
                self._conn.username,
                self._conn.password,
                self._timeout,
            )
            self._resolved = True

    async def _get(self, path: str) -> Any:
        """Make an authenticated GET request to the REST API.

        Args:
            path: API path relative to base URL.

        Returns:
            Parsed JSON response or None on failure.
        """
        await self._ensure_resolved()
        try:
            async with httpx.AsyncClient(timeout=self._timeout, verify=True) as client:
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

    # ── Create operations ──────────────────────────────────────

    async def _post(self, path: str, json_data: dict) -> bool:
        """Make an authenticated POST request.

        Args:
            path: API path relative to base URL.
            json_data: JSON body to send.

        Returns:
            True if the request returned 201 Created.
        """
        await self._ensure_resolved()
        try:
            async with httpx.AsyncClient(timeout=self._timeout, verify=True) as client:
                response = await client.post(
                    f"{self._base_url}{path}",
                    json=json_data,
                    auth=self._auth,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                return response.status_code == 201
        except httpx.RequestError:
            return False

    async def create_workspace(self, name: str) -> bool:
        """Create a new workspace.

        Args:
            name: Workspace name.

        Returns:
            True if created successfully.
        """
        return await self._post(
            "/rest/workspaces.json",
            {"workspace": {"name": name}},
        )

    async def create_datastore_shapefile(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create a Shapefile datastore.

        Args:
            workspace: Target workspace name.
            name: Store name.
            url: Path to shapefile (file:data/shapefiles/myfile.shp).

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/datastores.json",
            {
                "dataStore": {
                    "name": name,
                    "type": "Shapefile",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "url", "$": url},
                        ]
                    },
                }
            },
        )

    async def create_datastore_gpkg(
        self, workspace: str, name: str, database: str
    ) -> bool:
        """Create a GeoPackage datastore.

        Args:
            workspace: Target workspace name.
            name: Store name.
            database: Path to .gpkg file (file:data/myfile.gpkg).

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/datastores.json",
            {
                "dataStore": {
                    "name": name,
                    "type": "GeoPackage",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "database", "$": database},
                            {"@key": "dbtype", "$": "geopkg"},
                        ]
                    },
                }
            },
        )

    async def create_datastore_postgis(
        self,
        workspace: str,
        name: str,
        host: str,
        port: str,
        database: str,
        user: str,
        passwd: str,
        schema: str = "public",
    ) -> bool:
        """Create a PostGIS datastore.

        Args:
            workspace: Target workspace name.
            name: Store name.
            host: Database host.
            port: Database port.
            database: Database name.
            user: Database user.
            passwd: Database password.
            schema: Database schema.

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/datastores.json",
            {
                "dataStore": {
                    "name": name,
                    "type": "PostGIS",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "host", "$": host},
                            {"@key": "port", "$": port},
                            {"@key": "database", "$": database},
                            {"@key": "user", "$": user},
                            {"@key": "passwd", "$": passwd},
                            {"@key": "schema", "$": schema},
                            {"@key": "dbtype", "$": "postgis"},
                        ]
                    },
                }
            },
        )

    async def create_datastore_directory(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create a Directory of Shapefiles datastore.

        Args:
            workspace: Target workspace name.
            name: Store name.
            url: Path to directory (file:data/shapefiles/).

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/datastores.json",
            {
                "dataStore": {
                    "name": name,
                    "type": "Directory of spatial files (shapefiles)",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "url", "$": url},
                        ]
                    },
                }
            },
        )

    async def create_coveragestore_geotiff(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create a GeoTIFF coverage store.

        Args:
            workspace: Target workspace name.
            name: Store name.
            url: Path to GeoTIFF file (file:data/raster/dem.tif).

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/coveragestores.json",
            {
                "coverageStore": {
                    "name": name,
                    "type": "GeoTIFF",
                    "workspace": {"name": workspace},
                    "url": url,
                }
            },
        )

    async def create_coveragestore_worldimage(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create a WorldImage coverage store.

        Args:
            workspace: Target workspace name.
            name: Store name.
            url: Path to image file with world file.

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/coveragestores.json",
            {
                "coverageStore": {
                    "name": name,
                    "type": "WorldImage",
                    "workspace": {"name": workspace},
                    "url": url,
                }
            },
        )

    async def create_coveragestore_imagemosaic(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create an ImageMosaic coverage store.

        Args:
            workspace: Target workspace name.
            name: Store name.
            url: Path to mosaic directory.

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/coveragestores.json",
            {
                "coverageStore": {
                    "name": name,
                    "type": "ImageMosaic",
                    "workspace": {"name": workspace},
                    "url": url,
                }
            },
        )

    async def create_wmsstore(
        self, workspace: str, name: str, capabilities_url: str
    ) -> bool:
        """Create a WMS store.

        Args:
            workspace: Target workspace name.
            name: Store name.
            capabilities_url: GetCapabilities URL of the remote WMS.

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/wmsstores.json",
            {
                "wmsStore": {
                    "name": name,
                    "type": "WMS",
                    "capabilitiesURL": capabilities_url,
                }
            },
        )


# Supported store types for the UI
DATASTORE_TYPES = [
    ("Shapefile", "Single shapefile"),
    ("Directory of Shapefiles", "Directory of spatial files"),
    ("GeoPackage", "OGC GeoPackage"),
    ("PostGIS", "PostGIS database"),
]

COVERAGESTORE_TYPES = [
    ("GeoTIFF", "GeoTIFF raster"),
    ("WorldImage", "Image with world file"),
    ("ImageMosaic", "Image mosaic"),
]


async def test_connection(conn: Connection, timeout: float = 10.0) -> ConnectionResult:
    """Test a GeoServer connection by querying the REST API.

    Tries the URL as-is first, then falls back to {url}/geoserver.
    Validates credentials by hitting /rest/about/version.json.

    Args:
        conn: Connection configuration to test.
        timeout: Request timeout in seconds.

    Returns:
        ConnectionResult with success status and details.
    """
    if not conn.url:
        return ConnectionResult(success=False, message="URL is required")

    url = await resolve_base_url(conn.url, conn.username, conn.password, timeout)
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
