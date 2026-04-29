"""Rehidratar shadow index desde prod SIN re-OCR.

Este script reemplaza el Día 4 "backfill vía enumeration" del plan original.
Ahorra ~$50 USD en OCR + gpt-4.1-mini + embeddings re-procesando lo que ya existe.

Pasos:
  1. Drop all docs del shadow index (los 112 chunks parciales de la sesión previa)
  2. Copy todos los chunks de prod → shadow (bulk, batches de 1000)
  3. Populate itemsindex table vía Graph enumeration + shadow lookup por nombre_archivo

Uso:
    cd /Users/datageni/Documents/ai_azure/azure-ai-contract-analysis
    source venv/bin/activate
    python scripts/rehydrate_shadow_from_prod.py

Credenciales:
  - Azure Search: admin key vía az CLI
  - Microsoft Graph: client_credentials de roca-copilot-sync-agent
  - Azure Table Storage: DefaultAzureCredential (MI local via az login)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Iterator

import requests
from azure.core.credentials import AzureKeyCredential
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

# ─── Config ──────────────────────────────────────────────────────────────────

SEARCH_ENDPOINT = "https://srch-roca-copilot-prod.search.windows.net"
PROD_INDEX = "roca-contracts-v1"
SHADOW_INDEX = "roca-contracts-v1-shadow"
TABLE_ACCOUNT = "stroingest"
TABLE_ITEMSINDEX = "itemsindex"

SP_TENANT_ID = "9015a126-356b-4c63-9d1f-d2138ca83176"
SP_APP_ID = "18884cef-ace3-4899-9a54-be7eb66587b7"
SP_HOSTNAME = "rocadesarrollos1.sharepoint.com"
KV_URL = "https://kv-roca-copilot-prod.vault.azure.net/"

SP_SITES = ["ROCAIA-INMUEBLESV2", "ROCA-IAInmuebles"]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
REQUEST_TIMEOUT = 60

BATCH_SIZE = 500  # Search upload batch size


# ─── Search admin key vía az CLI ─────────────────────────────────────────────

def get_search_admin_key() -> str:
    result = subprocess.run(
        [
            "az", "search", "admin-key", "show",
            "--service-name", "srch-roca-copilot-prod",
            "--resource-group", "rg-roca-copilot-prod",
            "--query", "primaryKey", "-o", "tsv",
        ],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ─── KV secret vía az CLI ─────────────────────────────────────────────────────

def get_sp_secret() -> str:
    result = subprocess.run(
        [
            "az", "keyvault", "secret", "show",
            "--vault-name", "kv-roca-copilot-prod",
            "--name", "roca-copilot-sync-agent-secret",
            "--query", "value", "-o", "tsv",
        ],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ─── Graph token ─────────────────────────────────────────────────────────────

_graph_token_cache: dict[str, tuple[str, float]] = {}


def get_graph_token() -> str:
    now = time.time()
    cached = _graph_token_cache.get("t")
    if cached and cached[1] > now + 60:
        return cached[0]
    secret = get_sp_secret()
    resp = requests.post(
        f"https://login.microsoftonline.com/{SP_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": SP_APP_ID,
            "client_secret": secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    _graph_token_cache["t"] = (token, now + int(data.get("expires_in", 3600)))
    return token


def graph_get(path: str, params: dict | None = None) -> dict:
    url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {get_graph_token()}"},
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Graph GET {path} failed {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ─── Paso 1: Drop shadow docs ────────────────────────────────────────────────

def drop_shadow_docs(shadow: SearchClient) -> int:
    """Borra todos los docs del shadow en batches. Retorna count borrado."""
    total_deleted = 0
    while True:
        # Pagina de 1000 IDs
        results = list(shadow.search(
            search_text="*", select=["id"], top=1000,
        ))
        if not results:
            break
        docs = [{"id": r["id"]} for r in results]
        shadow.delete_documents(documents=docs)
        total_deleted += len(docs)
        print(f"  ... borrados {total_deleted}", flush=True)
        time.sleep(0.5)  # breve throttle
    return total_deleted


# ─── Paso 2: Copy prod → shadow ──────────────────────────────────────────────

# Campos que NO deben copiarse: metadatos sistema del search (@search.*)
METADATA_FIELDS = {
    "@search.score", "@search.rerankerScore",
    "@search.highlights", "@search.captions",
    "@search.answers",
}


def _upload_with_retry(shadow: SearchClient, batch: list[dict], max_retries: int = 5) -> None:
    """Upload batch con backoff exponencial para SSL transient errors."""
    for attempt in range(max_retries):
        try:
            shadow.upload_documents(documents=batch)
            return
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    retry {attempt + 1}/{max_retries} tras error: {type(exc).__name__}; wait {wait}s", flush=True)
            time.sleep(wait)


def copy_prod_to_shadow(prod: SearchClient, shadow: SearchClient) -> int:
    """Pagina prod vía by_page(), bulk upload a shadow con retry.

    Usa `by_page()` para forzar cursor-based pagination del SDK.
    Retry exponencial en cada batch: cubre SSL transient + throttling.
    """
    total_copied = 0

    # include_total_count para mostrar progreso (primera query adicional)
    meta = prod.search(search_text="*", top=1, include_total_count=True)
    list(meta)  # exhaust iterator to populate count
    total_prod = meta.get_count()
    print(f"  prod tiene {total_prod} docs, copiando en batches de {BATCH_SIZE}...")

    # Paginar todos los docs con retry en el iterador
    def _resilient_iter():
        """Retry del search paginado si falla SSL transient."""
        retry_count = 0
        while retry_count < 3:
            try:
                results = prod.search(search_text="*", top=None)
                for page in results.by_page():
                    yield from page
                return
            except Exception as exc:
                retry_count += 1
                print(f"  search retry {retry_count}/3 tras: {type(exc).__name__}", flush=True)
                time.sleep(5 * retry_count)
        raise RuntimeError("Max retries exceeded en search paginado")

    batch: list[dict] = []
    for doc in _resilient_iter():
        clean_doc = {k: v for k, v in doc.items() if k not in METADATA_FIELDS}
        batch.append(clean_doc)
        if len(batch) >= BATCH_SIZE:
            _upload_with_retry(shadow, batch)
            total_copied += len(batch)
            print(f"  ... copiados {total_copied}/{total_prod}", flush=True)
            batch = []

    if batch:
        _upload_with_retry(shadow, batch)
        total_copied += len(batch)
        print(f"  ... copiados {total_copied}/{total_prod}", flush=True)

    return total_copied


# ─── Paso 3: Populate itemsindex ─────────────────────────────────────────────

def get_site_id(site_name: str) -> str:
    data = graph_get(f"/sites/{SP_HOSTNAME}:/sites/{site_name}")
    return data["id"]


def get_default_drive_id(site_id: str) -> str:
    data = graph_get(f"/sites/{site_id}/drives")
    for d in data.get("value", []):
        if d.get("name") == "Documentos":
            return d["id"]
    for d in data.get("value", []):
        if d.get("driveType") == "documentLibrary":
            return d["id"]
    raise RuntimeError(f"No document library drive found for site {site_id}")


def list_drive_pdfs_recursive(drive_id: str, max_items: int = 10000) -> Iterator[dict]:
    queue: list[str] = ["root"]
    count = 0
    while queue and count < max_items:
        current = queue.pop(0)
        url = (f"/drives/{drive_id}/items/{current}/children"
               if current != "root"
               else f"/drives/{drive_id}/root/children")
        next_url: str | None = url
        params: dict | None = {"$top": "200"}
        while next_url:
            data = graph_get(next_url, params=params)
            for item in data.get("value", []):
                if "folder" in item:
                    queue.append(item["id"])
                    continue
                file_info = item.get("file") or {}
                if file_info.get("mimeType") == "application/pdf":
                    yield item
                    count += 1
                    if count >= max_items:
                        return
            next_link = data.get("@odata.nextLink")
            if not next_link:
                break
            next_url = next_link
            params = None


def build_nombre_archivo_lookup(shadow: SearchClient) -> dict[str, dict]:
    """Construye dict {nombre_archivo: {content_hash, parent_document_id, total_chunks, folder_path}}
    leyendo chunk_id=0 de cada doc. Usa by_page() para paginar completo."""
    lookup: dict[str, dict] = {}
    results = shadow.search(
        search_text="*",
        filter="chunk_id eq 0",
        select=["nombre_archivo", "content_hash", "parent_document_id",
                "total_chunks", "folder_path"],
        top=None,
    )
    count = 0
    for page in results.by_page():
        for r in page:
            name = r.get("nombre_archivo")
            if not name:
                continue
            if name not in lookup:
                lookup[name] = {
                    "content_hash": r.get("content_hash"),
                    "parent_document_id": r.get("parent_document_id"),
                    "total_chunks": r.get("total_chunks") or 1,
                    "folder_path": r.get("folder_path") or "",
                }
                count += 1
    print(f"  lookup construido: {count} archivos únicos por nombre_archivo")
    return lookup


def populate_itemsindex(tbl_svc: TableServiceClient, shadow: SearchClient) -> int:
    """Enumera los drives, por cada archivo busca content_hash en shadow y upsert a itemsindex."""
    lookup = build_nombre_archivo_lookup(shadow)
    tbl = tbl_svc.get_table_client(TABLE_ITEMSINDEX)

    total_populated = 0
    total_skipped = 0

    for site_name in SP_SITES:
        site_id = get_site_id(site_name)
        drive_id = get_default_drive_id(site_id)
        print(f"  Drive: {site_name} ({drive_id[:30]}...)")

        for item in list_drive_pdfs_recursive(drive_id, max_items=10000):
            name = item.get("name", "")
            match = lookup.get(name)
            if not match:
                total_skipped += 1
                continue

            parent_ref = item.get("parentReference") or {}
            parent_path = parent_ref.get("path", "").split("root:")[-1].lstrip("/")
            last_mod = item.get("lastModifiedDateTime", "")

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
                "last_modified_utc": last_mod,
            }
            tbl.upsert_entity(entity)
            total_populated += 1
            if total_populated % 100 == 0:
                print(f"    ... itemsindex populated {total_populated}", flush=True)

    print(f"  itemsindex: populated={total_populated} skipped={total_skipped} "
          f"(skipped = archivos en SharePoint sin match en shadow)")
    return total_populated


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-drop", action="store_true", help="No borrar shadow existente")
    parser.add_argument("--skip-copy", action="store_true", help="No copiar prod→shadow")
    parser.add_argument("--skip-populate", action="store_true", help="No populate itemsindex")
    args = parser.parse_args()

    admin_key = get_search_admin_key()
    prod = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=PROD_INDEX,
                        credential=AzureKeyCredential(admin_key))
    shadow = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SHADOW_INDEX,
                          credential=AzureKeyCredential(admin_key))

    cred = DefaultAzureCredential()
    tbl_svc = TableServiceClient(
        endpoint=f"https://{TABLE_ACCOUNT}.table.core.windows.net",
        credential=cred,
    )

    print("=" * 60)
    print(f"Rehydrate shadow from prod — start {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Paso 1
    if not args.skip_drop:
        print("\n[1/3] Drop existing docs del shadow...")
        deleted = drop_shadow_docs(shadow)
        print(f"  → eliminados {deleted} docs")
        time.sleep(2)  # wait for indexer to catch up
    else:
        print("\n[1/3] SKIPPED drop shadow")

    # Paso 2
    if not args.skip_copy:
        print("\n[2/3] Copiando prod → shadow...")
        copied = copy_prod_to_shadow(prod, shadow)
        print(f"  → copiados {copied} docs")
        print("  ... waiting 10s for shadow index to settle ...")
        time.sleep(10)
    else:
        print("\n[2/3] SKIPPED copy")

    # Paso 3
    if not args.skip_populate:
        print("\n[3/3] Populate itemsindex desde Graph + shadow lookup...")
        populated = populate_itemsindex(tbl_svc, shadow)
        print(f"  → populadas {populated} entries")
    else:
        print("\n[3/3] SKIPPED populate")

    # Verificación final
    print("\n" + "=" * 60)
    print("VERIFICACIÓN FINAL")
    print("=" * 60)
    prod_count = prod.get_document_count()
    shadow_count = shadow.get_document_count()
    print(f"  prod docs:   {prod_count}")
    print(f"  shadow docs: {shadow_count}")
    print(f"  parity:      {'✓' if prod_count == shadow_count else '✗ MISMATCH'}")
    print(f"  done {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
