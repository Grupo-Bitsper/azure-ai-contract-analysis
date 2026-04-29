"""AI Search client para el pipeline de ingest.

Extiende el cliente base con los métodos que el pipeline nuevo necesita:
- delete_by_content_hash: FIX del bug preexistente (D-1 del DESIGN, sección 10.1)
- patch_document_fields:  para rename/move sin re-OCR
- read_chunks_by_hash:    para http_read_document (reconstruye texto del doc)

El TARGET_INDEX_NAME viene de config — empieza en shadow, se cambia a prod en cutover.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from . import auth, config

_clients: dict[str, SearchClient] = {}
_client_lock = Lock()


def get_search_client(index_name: str | None = None) -> SearchClient:
    name = index_name or config.TARGET_INDEX_NAME
    with _client_lock:
        if name not in _clients:
            _clients[name] = SearchClient(
                endpoint=config.SEARCH_ENDPOINT,
                index_name=name,
                credential=auth.get_mi_credential(),
            )
        return _clients[name]


# ── Write operations ──────────────────────────────────────────────────────────

def upsert_documents(docs: list[dict], index_name: str | None = None) -> tuple[int, int, list[str]]:
    client = get_search_client(index_name)
    result = client.merge_or_upload_documents(documents=docs)
    ok = sum(1 for r in result if r.succeeded)
    errors = [f"{r.key}: {r.error_message}" for r in result if not r.succeeded]
    return ok, len(errors), errors


def delete_by_content_hash(content_hash: str, index_name: str | None = None) -> tuple[int, int]:
    """Borra todos los chunks de un documento por content_hash.

    FIX del bug preexistente: el pipeline viejo intentaba borrar por sp_list_item_id
    (siempre vacío). Este método usa content_hash que SÍ está poblado en todos los chunks.
    """
    client = get_search_client(index_name)
    results = client.search(
        search_text="*",
        filter=f"content_hash eq '{content_hash}'",
        top=200,
        select=["id"],
    )
    chunk_ids = [{"id": r["id"]} for r in results]
    if not chunk_ids:
        return 0, 0
    result = client.delete_documents(documents=chunk_ids)
    ok = sum(1 for r in result if r.succeeded)
    failed = sum(1 for r in result if not r.succeeded)
    return ok, failed


def patch_document_fields(content_hash: str, fields: dict, index_name: str | None = None) -> tuple[int, int]:
    """Aplica un patch parcial a todos los chunks de un documento.
    Usado para rename (actualiza nombre_archivo + sharepoint_url) y
    move (actualiza folder_path) sin re-OCR.
    """
    client = get_search_client(index_name)
    results = client.search(
        search_text="*",
        filter=f"content_hash eq '{content_hash}'",
        top=200,
        select=["id"],
    )
    patches = [{"id": r["id"], **fields} for r in results]
    if not patches:
        return 0, 0
    result = client.merge_documents(documents=patches)
    ok = sum(1 for r in result if r.succeeded)
    failed = sum(1 for r in result if not r.succeeded)
    return ok, failed


# ── Read operations ───────────────────────────────────────────────────────────

def find_by_content_hash(content_hash: str, index_name: str | None = None) -> list[dict]:
    """Dedup check: retorna chunks existentes para el hash dado."""
    client = get_search_client(index_name)
    results = client.search(
        search_text="*",
        filter=f"content_hash eq '{content_hash}'",
        top=100,
        select=["id", "content_hash", "sharepoint_url", "alternative_urls",
                "parent_document_id", "chunk_id"],
    )
    return [dict(r) for r in results]


def read_chunks_by_hash(content_hash: str, index_name: str | None = None) -> list[dict]:
    """Lee todos los chunks de un documento ordenados por chunk_id.
    Usado por http_read_document para reconstruir el texto completo
    sin re-OCR (los chunks ya tienen el texto procesado).
    """
    client = get_search_client(index_name)
    results = client.search(
        search_text="*",
        filter=f"content_hash eq '{content_hash}'",
        top=200,
        select=["id", "chunk_id", "total_chunks", "content",
                "nombre_archivo", "sharepoint_url", "folder_path"],
        order_by=["chunk_id asc"],
    )
    chunks = [dict(r) for r in results]
    chunks.sort(key=lambda c: c.get("chunk_id", 0))
    return chunks
