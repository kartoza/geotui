"""GeoServer REST API client.

Provides async methods for connection testing and fetching/creating
GeoServer resources (workspaces, stores, layers) via the REST API.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from geotui.config import Connection

logger = logging.getLogger("geotui.client")

# GeoServer resource names: alphanumeric, underscore, hyphen, dot
_RESOURCE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")
_MAX_NAME_LENGTH = 256


def validate_resource_name(name: str, kind: str = "resource") -> None:
    """Validate a GeoServer resource name.

    Args:
        name: The resource name to validate.
        kind: Human-readable kind for error messages (e.g. "workspace").

    Raises:
        ValueError: If the name is invalid.
    """
    if not name:
        raise ValueError(f"{kind} name cannot be empty")
    if len(name) > _MAX_NAME_LENGTH:
        raise ValueError(f"{kind} name exceeds {_MAX_NAME_LENGTH} characters")
    if not _RESOURCE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid {kind} name '{name}': "
            f"only letters, numbers, underscore, hyphen, and dot are allowed"
        )


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
            coveragestore, wmsstore, layer, coverage).
        children: Child resources.
        href: REST API href for this resource.
    """

    name: str
    resource_type: str
    children: list["GeoServerResource"] = field(default_factory=list)
    href: str = ""


@dataclass
class StoreType:
    """Definition of a GeoServer store type.

    Attributes:
        type_id: Internal type identifier.
        label: Human-readable label.
        category: 'vector', 'raster', or 'remote'.
        gs_type: GeoServer type string for REST API.
        fields: List of (field_name, label, placeholder) for the form.
        create_path: REST API path template (use {workspace}).
        payload_builder: Callable to build the JSON payload.
    """

    type_id: str
    label: str
    category: str
    gs_type: str
    fields: list[tuple[str, str, str]]


# ── VRT GeoServer type strings ─────────────────────────────
# These are the store type / driver identifiers GeoServer expects for VRT.
# Kept as module constants because the exact strings depend on the installed
# GDAL / OGR extensions and may need tuning per deployment.
VRT_COVERAGE_TYPE = "VRT"
OGR_DATASTORE_TYPE = "OGR"
OGR_VRT_DRIVER = "VRT"


# ── Store type registry ────────────────────────────────────

STORE_TYPES: list[StoreType] = [
    StoreType(
        type_id="shapefile",
        label="Shapefile",
        category="vector",
        gs_type="Shapefile",
        fields=[
            ("name", "Store Name", "my_shapefile"),
            ("path", "File Path", "file:data/myfile.shp"),
        ],
    ),
    StoreType(
        type_id="directory",
        label="Directory of Shapefiles",
        category="vector",
        gs_type="Directory of spatial files (shapefiles)",
        fields=[
            ("name", "Store Name", "my_directory"),
            ("path", "Directory Path", "file:data/shapefiles/"),
        ],
    ),
    StoreType(
        type_id="geopackage",
        label="GeoPackage",
        category="vector",
        gs_type="GeoPackage",
        fields=[
            ("name", "Store Name", "my_gpkg"),
            ("path", "Database Path", "file:data/myfile.gpkg"),
        ],
    ),
    StoreType(
        type_id="postgis",
        label="PostGIS",
        category="vector",
        gs_type="PostGIS",
        fields=[
            ("name", "Store Name", "my_postgis"),
            ("host", "Host", "localhost"),
            ("port", "Port", "5432"),
            ("database", "Database", "my_database"),
            ("user", "DB User", "postgres"),
            ("password", "DB Password", "password"),
        ],
    ),
    StoreType(
        type_id="geotiff",
        label="GeoTIFF",
        category="raster",
        gs_type="GeoTIFF",
        fields=[
            ("name", "Store Name", "my_raster"),
            ("path", "File Path", "file:data/raster/dem.tif"),
        ],
    ),
    StoreType(
        type_id="worldimage",
        label="WorldImage",
        category="raster",
        gs_type="WorldImage",
        fields=[
            ("name", "Store Name", "my_worldimage"),
            ("path", "File Path", "file:data/raster/image.png"),
        ],
    ),
    StoreType(
        type_id="imagemosaic",
        label="ImageMosaic",
        category="raster",
        gs_type="ImageMosaic",
        fields=[
            ("name", "Store Name", "my_mosaic"),
            ("path", "Directory Path", "file:data/mosaic/"),
        ],
    ),
    StoreType(
        type_id="wms",
        label="WMS",
        category="remote",
        gs_type="WMS",
        fields=[
            ("name", "Store Name", "remote_wms"),
            (
                "url",
                "Capabilities URL",
                "https://example.com/wms?request=GetCapabilities",
            ),
        ],
    ),
]

STORE_TYPE_MAP = {st.type_id: st for st in STORE_TYPES}


async def resolve_base_url(
    url: str, username: str, password: str, timeout: float = 10.0
) -> str:
    """Resolve the correct GeoServer REST API base URL.

    Tries the URL as-is first, then falls back to {url}/geoserver.

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
                probe = f"{candidate}/rest/about/version.json"
                try:
                    resp = await client.get(
                        probe,
                        auth=auth,
                        headers={"Accept": "application/json"},
                    )
                    logger.debug("resolve probe %s -> %s", probe, resp.status_code)
                    if resp.status_code == 200:
                        logger.info("Resolved base URL: %s", candidate)
                        return candidate
                except httpx.RequestError as exc:
                    logger.debug("resolve probe %s failed: %s", probe, exc)
                    continue
    except httpx.RequestError:
        pass

    logger.warning("Could not resolve base URL, falling back to: %s", base)
    return base


class GeoServerClient:
    """Async client for GeoServer REST API.

    Reuses a single httpx.AsyncClient for all requests.
    Use as an async context manager or call close() when done.

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
        self._username = conn.username
        self._password = conn.password
        self._auth = httpx.BasicAuth(conn.username, conn.password)
        self._resolved = False
        self._client: httpx.AsyncClient | None = None
        self._last_response_text = ""
        self._last_status_code = 0

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, verify=True)
        if not self._resolved:
            self._base_url = await resolve_base_url(
                self._base_url,
                self._username,
                self._password,
                self._timeout,
            )
            self._resolved = True
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GeoServerClient":
        """Enter async context."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        await self.close()

    # ── Generic HTTP methods ───────────────────────────────

    async def _get(self, path: str) -> Any:
        """Make an authenticated GET request.

        Args:
            path: API path relative to base URL.

        Returns:
            Parsed JSON response or None on failure.
        """
        client = await self._ensure_client()
        url = f"{self._base_url}{path}"
        logger.debug("GET %s", url)
        try:
            response = await client.get(
                url,
                auth=self._auth,
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                return response.json()
            logger.warning("GET %s -> %s", url, response.status_code)
        except httpx.RequestError as exc:
            logger.error("GET %s failed: %s", url, exc)
        return None

    async def _post(self, path: str, json_data: dict[str, Any]) -> bool:
        """Make an authenticated POST request.

        Args:
            path: API path relative to base URL.
            json_data: JSON body to send.

        Returns:
            True if the request returned 201 Created.
        """
        client = await self._ensure_client()
        url = f"{self._base_url}{path}"
        logger.debug("POST %s", url)
        try:
            response = await client.post(
                url,
                json=json_data,
                auth=self._auth,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if response.status_code == 201:
                return True
            logger.warning(
                "POST %s -> %s %s", url, response.status_code, response.text[:200]
            )
            return False
        except httpx.RequestError as exc:
            logger.error("POST %s failed: %s", url, exc)
            return False

    # ── Generic resource fetching ──────────────────────────

    async def _fetch_resources(
        self,
        path: str,
        outer_key: str,
        inner_key: str,
        resource_type: str,
    ) -> list[GeoServerResource]:
        """Fetch a list of resources from the REST API.

        All GeoServer list endpoints follow the same pattern:
        {outer_key: {inner_key: [{name, href}, ...]}}

        Args:
            path: REST API path.
            outer_key: Top-level JSON key.
            inner_key: Nested list key.
            resource_type: Type string for GeoServerResource.

        Returns:
            List of GeoServerResource objects.
        """
        data = await self._get(path)
        if not data:
            return []

        container = data.get(outer_key, {})
        if not container:
            return []

        items = container.get(inner_key, [])
        if isinstance(items, dict):
            items = [items]

        return [
            GeoServerResource(
                name=item.get("name", ""),
                resource_type=resource_type,
                href=item.get("href", ""),
            )
            for item in items
            if item.get("name")
        ]

    # ── Resource fetching ──────────────────────────────────

    async def get_workspaces(self) -> list[GeoServerResource]:
        """Fetch all workspaces."""
        return await self._fetch_resources(
            "/rest/workspaces.json", "workspaces", "workspace", "workspace"
        )

    async def get_datastores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch data stores for a workspace."""
        return await self._fetch_resources(
            f"/rest/workspaces/{workspace}/datastores.json",
            "dataStores",
            "dataStore",
            "datastore",
        )

    async def get_coveragestores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch coverage stores for a workspace."""
        return await self._fetch_resources(
            f"/rest/workspaces/{workspace}/coveragestores.json",
            "coverageStores",
            "coverageStore",
            "coveragestore",
        )

    async def get_wmsstores(self, workspace: str) -> list[GeoServerResource]:
        """Fetch WMS stores for a workspace."""
        return await self._fetch_resources(
            f"/rest/workspaces/{workspace}/wmsstores.json",
            "wmsStores",
            "wmsStore",
            "wmsstore",
        )

    async def get_layers_for_datastore(
        self, workspace: str, store: str
    ) -> list[GeoServerResource]:
        """Fetch feature type layers for a data store."""
        return await self._fetch_resources(
            f"/rest/workspaces/{workspace}/datastores/{store}/featuretypes.json",
            "featureTypes",
            "featureType",
            "layer",
        )

    async def get_coverages(
        self, workspace: str, store: str
    ) -> list[GeoServerResource]:
        """Fetch coverages for a coverage store."""
        return await self._fetch_resources(
            f"/rest/workspaces/{workspace}/coveragestores/{store}/coverages.json",
            "coverages",
            "coverage",
            "coverage",
        )

    async def get_full_tree(self) -> list[GeoServerResource]:
        """Fetch the full resource hierarchy using parallel requests.

        Returns:
            List of workspace resources with populated children.
        """
        workspaces = await self.get_workspaces()

        async def populate_workspace(ws: GeoServerResource) -> None:
            datastores, coveragestores, wmsstores = await asyncio.gather(
                self.get_datastores(ws.name),
                self.get_coveragestores(ws.name),
                self.get_wmsstores(ws.name),
            )

            layer_tasks = [
                self.get_layers_for_datastore(ws.name, ds.name) for ds in datastores
            ]
            coverage_tasks = [
                self.get_coverages(ws.name, cs.name) for cs in coveragestores
            ]

            if layer_tasks:
                layer_results = await asyncio.gather(*layer_tasks)
                for ds, layers in zip(datastores, layer_results, strict=True):
                    ds.children = layers

            if coverage_tasks:
                cov_results = await asyncio.gather(*coverage_tasks)
                for cs, covs in zip(coveragestores, cov_results, strict=True):
                    cs.children = covs

            ws.children = datastores + coveragestores + wmsstores

        await asyncio.gather(*(populate_workspace(ws) for ws in workspaces))
        return workspaces

    # ── Create operations ──────────────────────────────────

    async def create_workspace(self, name: str) -> bool:
        """Create a new workspace."""
        validate_resource_name(name, "workspace")
        return await self._post(
            "/rest/workspaces.json",
            {"workspace": {"name": name}},
        )

    async def create_datastore(
        self,
        workspace: str,
        name: str,
        store_type: str,
        params: dict[str, str],
    ) -> bool:
        """Create a datastore with the given connection parameters.

        Args:
            workspace: Target workspace name.
            name: Store name.
            store_type: GeoServer store type string.
            params: Connection parameter key-value pairs.

        Returns:
            True if created successfully.
        """
        validate_resource_name(workspace, "workspace")
        validate_resource_name(name, "datastore")
        return await self._post(
            f"/rest/workspaces/{workspace}/datastores.json",
            {
                "dataStore": {
                    "name": name,
                    "type": store_type,
                    "connectionParameters": {
                        "entry": [{"@key": k, "$": v} for k, v in params.items()]
                    },
                }
            },
        )

    async def create_coveragestore(
        self,
        workspace: str,
        name: str,
        store_type: str,
        url: str,
    ) -> bool:
        """Create a coverage store.

        Args:
            workspace: Target workspace name.
            name: Store name.
            store_type: GeoServer coverage store type (GeoTIFF, etc).
            url: Path to the coverage data.

        Returns:
            True if created successfully.
        """
        return await self._post(
            f"/rest/workspaces/{workspace}/coveragestores.json",
            {
                "coverageStore": {
                    "name": name,
                    "type": store_type,
                    "workspace": {"name": workspace},
                    "url": url,
                }
            },
        )

    async def create_wmsstore(
        self, workspace: str, name: str, capabilities_url: str
    ) -> bool:
        """Create a WMS store."""
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

    async def create_store_from_type(
        self,
        workspace: str,
        store_type: StoreType,
        field_values: dict[str, str],
    ) -> bool:
        """Create a store using the store type registry.

        Args:
            workspace: Target workspace.
            store_type: StoreType definition from the registry.
            field_values: Form field values keyed by field name.

        Returns:
            True if created successfully.
        """
        name = field_values.get("name", "")
        if not name:
            return False
        validate_resource_name(workspace, "workspace")
        validate_resource_name(name, "store")

        if store_type.category == "remote":
            return await self.create_wmsstore(
                workspace, name, field_values.get("url", "")
            )
        elif store_type.category == "raster":
            return await self.create_coveragestore(
                workspace,
                name,
                store_type.gs_type,
                field_values.get("path", ""),
            )
        else:
            # Vector stores
            if store_type.type_id == "postgis":
                params = {
                    "host": field_values.get("host", "localhost"),
                    "port": field_values.get("port", "5432"),
                    "database": field_values.get("database", ""),
                    "user": field_values.get("user", ""),
                    "passwd": field_values.get("password", ""),
                    "schema": "public",
                    "dbtype": "postgis",
                }
            elif store_type.type_id == "geopackage":
                params = {
                    "database": field_values.get("path", ""),
                    "dbtype": "geopkg",
                }
            else:
                params = {"url": field_values.get("path", "")}

            return await self.create_datastore(
                workspace, name, store_type.gs_type, params
            )

    # ── Publish helper methods ─────────────────────────────

    async def _put(self, path: str, data: bytes, content_type: str) -> int:
        """Make an authenticated PUT request with binary data.

        Args:
            path: API path relative to base URL.
            data: Raw bytes to send as the request body.
            content_type: MIME type for the Content-Type header.

        Returns:
            HTTP status code, or 0 on a request error.
        """
        client = await self._ensure_client()
        try:
            response = await client.put(
                f"{self._base_url}{path}",
                content=data,
                auth=self._auth,
                headers={"Content-Type": content_type},
            )
            self._last_response_text = response.text[:1024]
            self._last_status_code = response.status_code
            return response.status_code
        except httpx.RequestError as e:
            self._last_response_text = str(e)
            self._last_status_code = 0
            return 0

    async def _put_json(self, path: str, json_data: dict[str, Any]) -> bool:
        """Make an authenticated PUT request with a JSON body.

        Args:
            path: API path relative to base URL.
            json_data: JSON-serialisable body.

        Returns:
            True if the server responded with 200 OK.
        """
        client = await self._ensure_client()
        try:
            response = await client.put(
                f"{self._base_url}{path}",
                json=json_data,
                auth=self._auth,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def layer_exists(self, workspace: str, layer_name: str) -> bool:
        """Check whether a layer already exists in GeoServer.

        Args:
            workspace: Workspace name.
            layer_name: Layer name (without workspace prefix).

        Returns:
            True if the layer exists.
        """
        data = await self._get(f"/rest/layers/{workspace}:{layer_name}.json")
        return data is not None

    async def get_datastore_type(self, workspace: str, store: str) -> str | None:
        """Return the GeoServer type string for a datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.

        Returns:
            Type string (e.g. ``"Shapefile"``) or ``None`` if not found.
        """
        data = await self._get(f"/rest/workspaces/{workspace}/datastores/{store}.json")
        if not data:
            return None
        store_type: str | None = data.get("dataStore", {}).get("type")
        return store_type

    async def upload_shapefile(
        self,
        workspace: str,
        store: str,
        zip_data: bytes,
        update: bool,
    ) -> bool:
        """Upload a zipped shapefile to a GeoServer datastore.

        Sends the ZIP archive to the GeoServer file-upload endpoint using
        the ``file.shp`` method.  When *update* is ``True`` the
        ``update=overwrite`` query parameter is appended so that an existing
        store/layer is replaced rather than causing a conflict.

        Args:
            workspace: Target workspace name.
            store: Target datastore name.
            zip_data: Raw bytes of a ZIP archive containing the shapefile.
            update: If ``True``, overwrite an existing store/layer.

        Returns:
            True if the upload succeeded (HTTP 201 Created or 200 OK).
        """
        path = (
            f"/rest/workspaces/{workspace}/datastores/{store}/file.shp?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, zip_data, "application/zip")
        return status in (200, 201)

    async def create_featuretype(
        self,
        workspace: str,
        store: str,
        native_name: str,
        layer_name: str,
    ) -> bool:
        """Explicitly configure a feature type in an existing datastore.

        Required when uploading additional shapefiles to a datastore that was
        already created — GeoServer's configure=first only runs on store creation.

        Args:
            workspace: Target workspace name.
            store: Target datastore name.
            native_name: Shapefile stem (must match the file on disk).
            layer_name: Desired GeoServer layer name.

        Returns:
            True if the feature type was created (HTTP 201) or already existed.
        """
        path = f"/rest/workspaces/{workspace}/datastores/{store}/featuretypes"
        payload = {"featureType": {"name": layer_name, "nativeName": native_name}}
        return await self._post(path, payload)

    async def upload_gpkg(
        self,
        workspace: str,
        store: str,
        data: bytes,
        update: bool = False,
    ) -> bool:
        """Upload a GeoPackage file to a datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.
            data: GeoPackage file bytes.
            update: If True, overwrite existing.

        Returns:
            True if upload succeeded.
        """
        path = (
            f"/rest/workspaces/{workspace}/datastores/{store}/file.gpkg?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, data, "application/x-gpkg")
        return status in (200, 201)

    async def upload_geotiff(
        self,
        workspace: str,
        store: str,
        data: bytes,
        update: bool = False,
    ) -> bool:
        """Upload a GeoTIFF file to a coverage store.

        Args:
            workspace: Workspace name.
            store: Coverage store name.
            data: GeoTIFF file bytes.
            update: If True, overwrite existing.

        Returns:
            True if upload succeeded.
        """
        path = (
            f"/rest/workspaces/{workspace}/coveragestores/{store}"
            f"/file.geotiff?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, data, "image/tiff")
        return status in (200, 201)

    # ── VRT (GDAL/OGR Virtual Format) support ──────────────

    async def get_extension_support(self) -> dict[str, bool]:
        """Detect optional GeoServer extensions relevant to VRT publishing.

        Queries the server manifest and looks for the jars that provide GDAL
        coverage support (raster VRT) and the OGR datastore (vector VRT).

        Returns:
            Mapping with boolean ``"gdal"`` and ``"ogr"`` keys. Values are
            best-effort; ``False`` means "not detected", not a hard guarantee
            the extension is absent.
        """
        data = await self._get("/rest/about/manifest.json")
        names: list[str] = []
        if data:
            resources = data.get("about", {}).get("resource", [])
            names = [str(r.get("@name", "")) for r in resources]
        joined = " ".join(names).lower()
        return {
            "gdal": "gdal" in joined or "imageio-ext" in joined,
            "ogr": "gt-ogr" in joined or "ogr-bridj" in joined or "ogr-jni" in joined,
        }

    async def upload_resource(
        self,
        resource_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """Upload a file into the GeoServer data directory via the Resource API.

        Used for VRT *bundle* mode: the ``.vrt`` and every file it references
        are pushed into the data directory over REST (no server filesystem
        access required), after which a store can point at them.

        Args:
            resource_path: Path relative to the data directory root, e.g.
                ``"data/vrt/mystore/mosaic.vrt"``. Leading slashes are stripped.
            data: Raw file bytes.
            content_type: MIME type for the upload.

        Returns:
            True if the resource was stored (HTTP 200 or 201).
        """
        clean = resource_path.lstrip("/")
        status = await self._put(f"/rest/resource/{clean}", data, content_type)
        return status in (200, 201)

    async def create_vrt_coveragestore(
        self, workspace: str, name: str, url: str
    ) -> bool:
        """Create a raster VRT coverage store pointing at *url*.

        Requires the GDAL/ImageIO-Ext coverage extension on the server.

        Args:
            workspace: Target workspace.
            name: Coverage store name.
            url: ``file:`` URL to the ``.vrt`` (relative to the data dir or
                absolute on the server).

        Returns:
            True if created (HTTP 200/201).
        """
        return await self.create_coveragestore(workspace, name, VRT_COVERAGE_TYPE, url)

    async def create_coverage(
        self, workspace: str, store: str, native_name: str, layer_name: str
    ) -> bool:
        """Configure a coverage (layer) within a coverage store.

        Args:
            workspace: Target workspace.
            store: Coverage store name.
            native_name: Native coverage name as read from the source.
            layer_name: Desired published layer name.

        Returns:
            True if created (HTTP 201) or already present.
        """
        path = f"/rest/workspaces/{workspace}/coveragestores/{store}/coverages"
        payload = {"coverage": {"name": layer_name, "nativeName": native_name}}
        return await self._post(path, payload)

    async def create_ogr_vrt_datastore(
        self, workspace: str, name: str, datasource: str
    ) -> bool:
        """Create a vector OGR datastore backed by a VRT datasource.

        Requires the OGR datastore extension on the server.

        Args:
            workspace: Target workspace.
            name: Datastore name.
            datasource: ``file:`` URL / path to the ``.vrt`` datasource.

        Returns:
            True if created (HTTP 200/201).
        """
        params = {
            "DatasourceName": datasource,
            "DriverName": OGR_VRT_DRIVER,
            "namespace": workspace,
        }
        return await self.create_datastore(workspace, name, OGR_DATASTORE_TYPE, params)

    async def recalculate_bbox(self, workspace: str, layer_name: str) -> bool:
        """Recalculate bounding box for a layer.

        Args:
            workspace: Workspace name.
            layer_name: Layer name.

        Returns:
            True if successful.
        """
        return await self._put_json(
            f"/rest/layers/{workspace}:{layer_name}.json",
            {"layer": {"resource": {"recalculate": "nativebbox,latlonbbox"}}},
        )

    async def assign_style(
        self, workspace: str, layer_name: str, style_name: str
    ) -> bool:
        """Set the default style for a published layer.

        Args:
            workspace: Workspace that owns the layer.
            layer_name: Name of the layer (without workspace prefix).
            style_name: Name of the style to assign.

        Returns:
            True if GeoServer accepted the update (HTTP 200 OK).
        """
        return await self._put_json(
            f"/rest/layers/{workspace}:{layer_name}.json",
            {
                "layer": {
                    "defaultStyle": {"name": style_name},
                }
            },
        )

    # ── Delete operations ──────────────────────────────────

    async def _delete(self, path: str) -> bool:
        """Make an authenticated DELETE request.

        Args:
            path: API path relative to base URL.

        Returns:
            True if the request returned 2xx.
        """
        client = await self._ensure_client()
        url = f"{self._base_url}{path}"
        logger.debug("DELETE %s", url)
        try:
            response = await client.delete(url, auth=self._auth)
            logger.debug(
                "DELETE %s -> %s %s", url, response.status_code, response.text[:200]
            )
            return 200 <= response.status_code < 300
        except httpx.RequestError as exc:
            logger.error("DELETE %s failed: %s", url, exc)
            return False

    async def delete_datastore(
        self, workspace: str, store: str, recurse: bool = False
    ) -> bool:
        """Delete a datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.
            recurse: If True, also delete contained layers.

        Returns:
            True if deleted successfully.
        """
        path = f"/rest/workspaces/{workspace}/datastores/{store}"
        if recurse:
            path += "?recurse=true"
        return await self._delete(path)

    async def delete_coveragestore(
        self, workspace: str, store: str, recurse: bool = False
    ) -> bool:
        """Delete a coverage store.

        Args:
            workspace: Workspace name.
            store: Coverage store name.
            recurse: If True, also delete contained coverages.

        Returns:
            True if deleted successfully.
        """
        path = f"/rest/workspaces/{workspace}/coveragestores/{store}"
        if recurse:
            path += "?recurse=true"
        return await self._delete(path)

    async def delete_workspace(self, workspace: str, recurse: bool = False) -> bool:
        """Delete a workspace.

        Args:
            workspace: Workspace name.
            recurse: If True, also delete all contained stores and layers.

        Returns:
            True if deleted successfully.
        """
        path = f"/rest/workspaces/{workspace}"
        if recurse:
            path += "?recurse=true"
        return await self._delete(path)

    async def delete_layer(
        self,
        workspace: str,
        store: str,
        layer_name: str,
        resource_type: str = "layer",
    ) -> bool:
        """Delete a layer/coverage and its associated global layer entry.

        Uses the featuretype/coverage endpoint to delete the resource,
        then removes the global layer reference.

        Args:
            workspace: Workspace name.
            store: Parent store name.
            layer_name: Layer name.
            resource_type: 'layer' for featuretypes, 'coverage' for coverages.

        Returns:
            True if deleted successfully.
        """
        # First delete the global layer entry
        await self._delete(f"/rest/layers/{layer_name}")

        # Then delete the feature type or coverage from the store
        if resource_type == "coverage":
            path = (
                f"/rest/workspaces/{workspace}/coveragestores"
                f"/{store}/coverages/{layer_name}?recurse=true"
            )
        else:
            path = (
                f"/rest/workspaces/{workspace}/datastores"
                f"/{store}/featuretypes/{layer_name}?recurse=true"
            )
        return await self._delete(path)


async def test_connection(conn: Connection, timeout: float = 10.0) -> ConnectionResult:
    """Test a GeoServer connection by querying the REST API.

    Tries the URL as-is first, then falls back to {url}/geoserver.

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
    conn_detail = f"endpoint={endpoint}, user={conn.username}, password=***"

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=True) as client:
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
            message=f"Connection timed out ({conn_detail})",
        )
    except httpx.ConnectError as e:
        return ConnectionResult(
            success=False,
            message=f"Cannot connect to {url}: {e} ({conn_detail})",
        )
    except httpx.RequestError as e:
        return ConnectionResult(
            success=False,
            message=f"Request error: {e} ({conn_detail})",
        )
