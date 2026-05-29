#!/usr/bin/env bash
# Start a local Kartoza GeoServer for testing.
#
# After starting, the GeoServer is available at:
#   URL:      http://localhost:8600/geoserver
#   Username: admin
#   Password: geoserver
#
# A GeoTUI connection is automatically added to config.json.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting Kartoza GeoServer test instance..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

echo ""
echo "Waiting for GeoServer to be healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8600/geoserver/web/ > /dev/null 2>&1; then
        echo "GeoServer is ready!"
        echo ""
        echo "  URL:      http://localhost:8600/geoserver"
        echo "  Username: admin"
        echo "  Password: geoserver"
        echo ""

        # Add test connection to GeoTUI config
        nix --extra-experimental-features 'nix-command flakes' develop "$PROJECT_DIR" -c python3 "$SCRIPT_DIR/add_test_connection.py"
        exit 0
    fi
    echo "  Waiting... ($i/30)"
    sleep 5
done

echo "ERROR: GeoServer did not become healthy in time."
echo "Check logs with: docker compose -f $PROJECT_DIR/docker-compose.yml logs"
exit 1
