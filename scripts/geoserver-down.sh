#!/usr/bin/env bash
# Stop and destroy the local test GeoServer.
# Removes the container and its data volume.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping GeoServer test instance..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" down -v

echo "GeoServer stopped and data removed."
