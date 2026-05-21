#!/usr/bin/env bash
# Check the status of the local test GeoServer.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Container Status ==="
docker compose -f "$PROJECT_DIR/docker-compose.yml" ps

echo ""
echo "=== Health Check ==="
if curl -sf http://localhost:8600/geoserver/rest/about/version.json \
    -u admin:geoserver \
    -H "Accept: application/json" 2>/dev/null | python3 -m json.tool 2>/dev/null; then
    echo ""
    echo "GeoServer is healthy and responding."
else
    echo "GeoServer is not responding."
fi
