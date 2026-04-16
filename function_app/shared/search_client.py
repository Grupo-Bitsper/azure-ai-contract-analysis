"""Azure AI Search client — AAD auth via Function App MI.

Target index is driven by TARGET_INDEX_NAME env var which starts at
`roca-contracts-v1-staging` and only flips to `roca-contracts-v1` on
explicit operator action during Paso 5.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from azure.search.documents import SearchClient

from . import auth, config

_client: Optional[SearchClient] = None
_client_lock = Lock()


def get_search_client() -> SearchClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = SearchClient(
                endpoint=config.SEARCH_ENDPOINT,
                index_name=config.TARGET_INDEX_NAME,
                credential=auth.get_mi_credential(),
            )
        return _client


def find_by_content_hash(content_hash: str) -> list[dict]:
    """Returns all chunks of the document matching the given content_hash
    (usually ≤60 chunks per doc). Used for dedup hit detection."""
    client = get_search_client()
    results = client.search(
        search_text="*",
        filter=f"content_hash eq '{content_hash}'",
        top=100,
        select=[
            # Only retrievable fields here. group_ids/user_ids are hidden
            # (retrievable=false) by design for security trimming; we don't
            # need them for the dedup merge path.
            "id",
            "content_hash",
            "sharepoint_url",
            "alternative_urls",
            "parent_document_id",
            "chunk_id",
            "sp_site_id",
            "sp_list_id",
            "sp_list_item_id",
        ],
    )
    return [dict(r) for r in results]


def upsert_documents(docs: list[dict]) -> tuple[int, int, list[str]]:
    """Upserts a batch of documents. Returns (succeeded_count, failed_count, errors)."""
    client = get_search_client()
    result = client.merge_or_upload_documents(documents=docs)
    ok = sum(1 for r in result if r.succeeded)
    errors = [f"{r.key}: {r.error_message}" for r in result if not r.succeeded]
    return ok, len(errors), errors


def update_acls_for_hash(content_hash: str, group_ids: list[str], user_ids: list[str]) -> tuple[int, int]:
    """Updates `group_ids` and `user_ids` on all chunks of a document identified
    by content_hash. Returns (updated_chunks, failed_chunks)."""
    chunks = find_by_content_hash(content_hash)
    if not chunks:
        return 0, 0
    patches = [
        {
            "id": c["id"],
            "group_ids": group_ids,
            "user_ids": user_ids,
        }
        for c in chunks
    ]
    client = get_search_client()
    result = client.merge_documents(documents=patches)
    ok = sum(1 for r in result if r.succeeded)
    failed = sum(1 for r in result if not r.succeeded)
    return ok, failed


def list_unique_hashes_with_refs() -> list[dict]:
    """Returns one entry per unique content_hash present in the index, with
    the SharePoint identity refs needed to look up permissions again via
    Graph. Used by acl_refresh_orchestrator."""
    client = get_search_client()
    results = client.search(
        search_text="*",
        top=5000,
        select=[
            "content_hash",
            "sp_site_id",
            "sp_list_id",
            "sp_list_item_id",
        ],
    )
    seen: dict[str, dict] = {}
    for r in results:
        h = r.get("content_hash")
        if not h or h in seen:
            continue
        site = r.get("sp_site_id") or ""
        list_id = r.get("sp_list_id") or ""
        item_id = r.get("sp_list_item_id") or ""
        if not (site and list_id and item_id):
            continue  # skip legacy docs without identity refs
        seen[h] = {
            "content_hash": h,
            "sp_site_id": site,
            "sp_list_id": list_id,
            "sp_list_item_id": item_id,
        }
    return list(seen.values())


def iter_indexed_docs(select_fields: list[str], top: int = 1000) -> list[dict]:
    """Iterates all documents in the current target index. Used by ACL refresh
    and full resync workflows. For the staging scale (<1000 chunks) a single
    page is sufficient."""
    client = get_search_client()
    results = client.search(
        search_text="*",
        top=top,
        select=select_fields,
    )
    return [dict(r) for r in results]
