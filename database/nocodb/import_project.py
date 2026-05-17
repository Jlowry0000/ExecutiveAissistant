#!/usr/bin/env python3
"""
NocoDB Project Import Script
Reads the project export tar.gz and imports it via NocoDB REST API.
"""
import os
import sys
import tarfile
import json
import requests
from pathlib import Path

NOCODB_URL = os.environ.get("NOCODB_URL", "http://localhost:8080")
EMAIL = os.environ.get("NOCODB_EMAIL", "admin@nocodb.com")
PASSWORD = os.environ.get("NOCODB_PASSWORD", "changeme")


def wait_for_nocodb(timeout=60):
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{NOCODB_URL}/api/v1/health", timeout=5)
            if r.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False


def authenticate():
    resp = requests.post(
        f"{NOCODB_URL}/api/v1/auth/signin",
        json={"email": EMAIL, "password": PASSWORD}
    )
    resp.raise_for_status()
    return resp.json()["token"]


def import_project(token, tar_gz_path):
    with tarfile.open(tar_gz_path, "r:gz") as tar:
        # Extract metadata
        meta = json.loads(tar.extractfile("meta.json").read())

        headers = {
            "xc-token": token,
            "Content-Type": "application/json"
        }

        for member in tar.getmembers():
            if member.name.endswith(".json") and member.name != "meta.json":
                data = json.loads(tar.extractfile(member).read())
                # Route to correct NocoDB import endpoint based on filename
                if "tables" in member.name:
                    # Table definitions
                    requests.post(
                        f"{NOCODB_URL}/api/v1/tables",
                        headers=headers,
                        json=data
                    )
                elif "views" in member.name:
                    requests.post(
                        f"{NOCODB_URL}/api/v1/views",
                        headers=headers,
                        json=data
                    )


if __name__ == "__main__":
    export_path = Path(__file__).parent / "project-export.tar.gz"
    if not export_path.exists():
        print(f"Export not found: {export_path}")
        print("Please place project-export.tar.gz in the same directory as this script.")
        sys.exit(1)

    if not wait_for_nocodb():
        print("NocoDB not available. Ensure it's running.")
        sys.exit(1)

    token = authenticate()
    import_project(token, export_path)
    print("NocoDB project imported successfully.")