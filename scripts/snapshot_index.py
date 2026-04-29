"""Dump completo del índice AI Search a roca-backups container como .json.gz.

Uso:
    python scripts/snapshot_index.py                     # snapshot con timestamp auto
    python scripts/snapshot_index.py --tag pre-plan-b    # snapshot con tag custom

Salida:
    strocacopilotprod/roca-backups/index-snapshot-YYYY-MM-DD[-tag].json.gz
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import subprocess
import sys
from datetime import datetime, timezone

import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient

SEARCH_SERVICE = "srch-roca-copilot-prod"
SEARCH_RG = "rg-roca-copilot-prod"
INDEX_NAME = "roca-contracts-v1"
STORAGE_ACCOUNT = "strocacopilotprod"
BACKUP_CONTAINER = "roca-backups"
PAGE_SIZE = 1000
API_VERSION = "2024-07-01"


def get_admin_key() -> str:
    out = subprocess.run(
        ["az", "search", "admin-key", "show",
         "--service-name", SEARCH_SERVICE, "-g", SEARCH_RG,
         "--query", "primaryKey", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def dump_all_docs(api_key: str) -> list[dict]:
    base_url = f"https://{SEARCH_SERVICE}.search.windows.net/indexes/{INDEX_NAME}/docs"
    headers = {"api-key": api_key}
    all_docs: list[dict] = []
    skip = 0

    while True:
        params = {
            "api-version": API_VERSION,
            "$top": PAGE_SIZE,
            "$skip": skip,
        }
        resp = requests.get(base_url, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        batch = resp.json().get("value", [])
        if not batch:
            break
        all_docs.extend(batch)
        print(f"  dumped {len(all_docs)} chunks...", file=sys.stderr)
        if len(batch) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
        if skip >= 100000:
            print("WARNING: skip limit reached (100K), partial dump", file=sys.stderr)
            break

    return all_docs


def upload_snapshot(blob_name: str, payload: bytes) -> None:
    blob = BlobClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        container_name=BACKUP_CONTAINER,
        blob_name=blob_name,
        credential=DefaultAzureCredential(),
    )
    blob.upload_blob(payload, overwrite=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="", help="Sufijo opcional para el nombre (ej. pre-plan-b)")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    suffix = f"-{args.tag}" if args.tag else ""
    blob_name = f"index-snapshot-{ts}{suffix}.json.gz"

    print(f"[snapshot] indexando dump de {INDEX_NAME}...", file=sys.stderr)
    key = get_admin_key()
    docs = dump_all_docs(key)
    print(f"[snapshot] total: {len(docs)} chunks", file=sys.stderr)

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(json.dumps({
            "index_name": INDEX_NAME,
            "snapshot_utc": datetime.now(timezone.utc).isoformat(),
            "total_chunks": len(docs),
            "docs": docs,
        }, ensure_ascii=False).encode("utf-8"))
    payload = buf.getvalue()

    print(f"[snapshot] subiendo {len(payload)/1024/1024:.2f} MB a {blob_name}...", file=sys.stderr)
    upload_snapshot(blob_name, payload)
    print(f"[snapshot] OK → {STORAGE_ACCOUNT}/{BACKUP_CONTAINER}/{blob_name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
