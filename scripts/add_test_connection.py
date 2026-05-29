#!/usr/bin/env python3
"""Add a Local Test GeoServer connection to GeoTUI config."""

import sys
import os

# Ensure src is on the path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_dir, "src"))

from geotui.config import ConfigManager, Connection

TEST_URL = "http://localhost:8600/geoserver"

cm = ConfigManager()

# Remove any existing test connection to avoid stale data
existing = cm.get_connection_by_name("Local Test GeoServer")
if existing:
    cm.remove_connection(existing.id)

conn = Connection(
    name="Local Test GeoServer",
    url=TEST_URL,
    username="admin",
    password="geoserver",
)
cm.add_connection(conn)

# Verify what was written
saved = cm.get_connection_by_name("Local Test GeoServer")
print(f"Connection saved: {saved.name}")
print(f"URL: {saved.url}")
assert saved.url == TEST_URL, f"URL mismatch: {saved.url} != {TEST_URL}"
print("Use F9 in GeoTUI to select and connect.")
