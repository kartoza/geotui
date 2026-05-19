"""GeoServer REST API client for connection testing.

Provides async connection validation against GeoServer's REST API.
"""

from dataclasses import dataclass

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
