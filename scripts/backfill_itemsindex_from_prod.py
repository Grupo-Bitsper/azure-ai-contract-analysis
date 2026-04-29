"""Backfill itemsindex table desde prod (no shadow).

Fix del bug heredado de rehydrate_shadow_from_prod.py: el populate paso 3
matchó contra shadow (8851 chunks), dejando 128 archivos huérfanos sin
entry en itemsindex. Sin entry, rename/move/delete fallan silenciosos.

Este script enumera los 2 drives de SP via Graph, hace lookup contra prod
(roca-contracts-v1), y upserta entries en itemsindex. Idempotente.
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone

import requests
from azure.data.tables import TableServiceClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

SEARCH_ENDPOINT = "https://srch-roca-copilot-prod.search.windows.net"
PROD_INDEX = "roca-contracts-v1"
TABLE_ACCOUNT = "stroingest"
TABLE_ITEMSINDEX = "itemsindex"

SP_TENANT_ID = "9015a126-356b-4c63-9d1f-d2138ca83176"
SP_APP_ID = "18884cef-ace3-4899-9a54-be7eb66587b7"
SP_HOSTNAME = "rocadesarrollos1.sharepoint.com"
SP_SITES = ["ROCAIA-INMUEBLESV2", "ROCA-IAInmuebles"]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _az(*args: str) -> str:
    return subprocess.run(["az", *args], capture_output=True, text=True, check=True).stdout.strip()


def get_search_key() -> str:
    return _az("search", "admin-key", "show", "--service-name", "srch-roca-copilot-prod",
               "--resource-group", "rg-roca-copilot-prod", "--query", "primaryKey", "-o", "tsv")


def get_storage_conn() -> str:
    key = _az("storage", "account", "keys", "list", "--account-name", TABLE_ACCOUNT,
              "--resource-group", "rg-roca-copilot-prod", "--query", "[0].value", "-o", "tsv")
    return f"DefaultEndpointsProtocol=https;AccountName={TABLE_ACCOUNT};AccountKey={key};EndpointSuffix=core.windows.net"


def get_graph_token() -> str:
    secret = _az("keyvault", "secret", "show", "--vault-name", "kv-roca-copilot-prod",
                 "--name", "roca-copilot-sync-agent-secret", "--query", "value", "-o", "tsv")
    resp = requests.post(
        f"https://login.microsoftonline.com/{SP_TENANT_ID}/oauth2/v2.0/token",
        data={"client_id": SP_APP_ID, "client_secret": secret,
              "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def graph_get(url: str, token: str, params=None) -> dict:
    if not url.startswith("http"):
        url = f"{GRAPH_BASE}{url}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def build_prod_lookup(prod: SearchClient) -> dict[str, dict]:
    """Lookup {nombre_archivo: {content_hash, parent_document_id, total_chunks, folder_path}}."""
    lookup: dict[str, dict] = {}
    results = prod.search(
        search_text="*", filter="chunk_id eq 0",
        select=["nombre_archivo", "content_hash", "parent_document_id",
                "total_chunks", "folder_path"],
        top=None,
    )
    for page in results.by_page():
        for r in page:
            name = r.get("nombre_archivo")
            if name and name not in lookup:
                lookup[name] = {
                    "content_hash": r.get("content_hash"),
                    "parent_document_id": r.get("parent_document_id"),
                    "total_chunks": r.get("total_chunks") or 1,
                    "folder_path": r.get("folder_path") or "",
                }
    return lookup


def list_drive_pdfs(drive_id: str, token: str):
    queue = ["root"]
    while queue:
        current = queue.pop(0)
        url = (f"/drives/{drive_id}/items/{current}/children" if current != "root"
               else f"/drives/{drive_id}/root/children")
        next_url = url
        params = {"$top": "200"}
        while next_url:
            data = graph_get(next_url, token, params=params)
            for item in data.get("value", []):
                if "folder" in item:
                    queue.append(item["id"])
                    continue
                if (item.get("file") or {}).get("mimeType") == "application/pdf":
                    yield item
            next_url = data.get("@odata.nextLink")
            params = None


def get_site_drive(site_name: str, token: str) -> str:
    site = graph_get(f"/sites/{SP_HOSTNAME}:/sites/{site_name}", token)
    drives = graph_get(f"/sites/{site['id']}/drives", token)
    for d in drives.get("value", []):
        if d.get("name") == "Documentos":
            return d["id"]
    for d in drives.get("value", []):
        if d.get("driveType") == "documentLibrary":
            return d["id"]
    raise RuntimeError(f"No drive found for {site_name}")


def main() -> None:
    print(f"start {datetime.now(timezone.utc).isoformat()}")

    prod = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=PROD_INDEX,
                        credential=AzureKeyCredential(get_search_key()))
    tbl_svc = TableServiceClient.from_connection_string(get_storage_conn())
    tbl = tbl_svc.get_table_client(TABLE_ITEMSINDEX)
    token = get_graph_token()

    print("[1/3] reading itemsindex existing entries...")
    existing_keys: set[tuple[str, str]] = set()
    for e in tbl.list_entities(select=["PartitionKey", "RowKey"]):
        existing_keys.add((e["PartitionKey"], e["RowKey"]))
    print(f"  existing entries: {len(existing_keys)}")

    print("[2/3] building lookup from prod...")
    lookup = build_prod_lookup(prod)
    print(f"  unique nombres en prod: {len(lookup)}")

    print("[3/3] enumerating SP drives + upserting...")
    added = 0
    updated = 0
    skipped_no_match = 0
    by_site: dict[str, int] = {}
    for site_name in SP_SITES:
        drive_id = get_site_drive(site_name, token)
        print(f"  drive {site_name} ({drive_id[:30]}...)")
        site_count = 0
        for item in list_drive_pdfs(drive_id, token):
            name = item.get("name", "")
            match = lookup.get(name)
            if not match:
                skipped_no_match += 1
                continue
            parent_path = (item.get("parentReference") or {}).get("path", "").split("root:")[-1].lstrip("/")
            entity = {
                "PartitionKey": drive_id,
                "RowKey": item["id"],
                "content_hash": match["content_hash"],
                "sp_list_item_id": "",
                "name": name,
                "folder_path": parent_path or match["folder_path"],
                "parent_document_id": match["parent_document_id"],
                "total_chunks": match["total_chunks"],
                "last_indexed_utc": datetime.now(timezone.utc).isoformat(),
                "last_modified_utc": item.get("lastModifiedDateTime", ""),
            }
            tbl.upsert_entity(entity)
            if (drive_id, item["id"]) in existing_keys:
                updated += 1
            else:
                added += 1
            site_count += 1
            if site_count % 100 == 0:
                print(f"    ... {site_count}", flush=True)
        by_site[site_name] = site_count

    print()
    print("=" * 50)
    print(f"DONE {datetime.now(timezone.utc).isoformat()}")
    print(f"  added (new):      {added}")
    print(f"  updated (touch):  {updated}")
    print(f"  skipped no match: {skipped_no_match}")
    print(f"  by site:          {by_site}")
    print(f"  total processed:  {added + updated}")


if __name__ == "__main__":
    main()
