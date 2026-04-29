"""Azure Table Storage client para los 3 tracking tables del pipeline.

- deltatokens:  PK=site_id, RK=drive_id  → deltaLink + subscripción Graph
- folderpaths:  PK=drive_id, RK=folder_item_id → full path para rename de carpetas
- itemsindex:   PK=drive_id, RK=drive_item_id → mapeo drive_item_id → content_hash

Todos los accesos son con Managed Identity (Table Data Contributor asignado en Día 2).
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceNotFoundError

from . import auth, config

_service: Optional[TableServiceClient] = None
_service_lock = Lock()


def _svc() -> TableServiceClient:
    global _service
    with _service_lock:
        if _service is None:
            _service = TableServiceClient(
                endpoint=f"https://{config.INGEST_STORAGE_ACCOUNT}.table.core.windows.net",
                credential=auth.get_mi_credential(),
            )
        return _service


def _tbl(name: str) -> TableClient:
    return _svc().get_table_client(name)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── deltatokens ──────────────────────────────────────────────────────────────

def get_delta_link(site_id: str, drive_id: str) -> str | None:
    try:
        e = _tbl(config.TABLE_DELTATOKENS).get_entity(
            partition_key=site_id, row_key=drive_id
        )
        return e.get("delta_link") or None
    except ResourceNotFoundError:
        return None


def save_delta_link(
    site_id: str,
    drive_id: str,
    delta_link: str,
    changes_count: int = 0,
) -> None:
    _tbl(config.TABLE_DELTATOKENS).upsert_entity({
        "PartitionKey": site_id,
        "RowKey": drive_id,
        "delta_link": delta_link,
        "last_sync_utc": _now_iso(),
        "last_changes_count": changes_count,
    })


def save_subscription(
    site_id: str,
    drive_id: str,
    subscription_id: str,
    expires_utc: str,
) -> None:
    try:
        e = _tbl(config.TABLE_DELTATOKENS).get_entity(
            partition_key=site_id, row_key=drive_id
        )
    except ResourceNotFoundError:
        e = {"PartitionKey": site_id, "RowKey": drive_id}
    e["subscription_id"] = subscription_id
    e["subscription_expires_utc"] = expires_utc
    _tbl(config.TABLE_DELTATOKENS).upsert_entity(e)


def list_all_subscriptions() -> list[dict]:
    return [dict(e) for e in _tbl(config.TABLE_DELTATOKENS).list_entities()]


# ── folderpaths ──────────────────────────────────────────────────────────────

def upsert_folder_path(drive_id: str, folder_item_id: str, path: str, parent_folder_id: str = "") -> None:
    _tbl(config.TABLE_FOLDERPATHS).upsert_entity({
        "PartitionKey": drive_id,
        "RowKey": folder_item_id,
        "path": path,
        "parent_folder_id": parent_folder_id,
        "last_updated_utc": _now_iso(),
    })


def get_folder_path(drive_id: str, folder_item_id: str) -> str | None:
    try:
        e = _tbl(config.TABLE_FOLDERPATHS).get_entity(
            partition_key=drive_id, row_key=folder_item_id
        )
        return e.get("path")
    except ResourceNotFoundError:
        return None


def list_descendant_items(drive_id: str, parent_path_prefix: str) -> list[dict]:
    """Retorna filas de itemsindex cuyos folder_path empiezan con el prefix dado.
    Usado por folder_rename para saber qué items actualizar."""
    filter_str = (
        f"PartitionKey eq '{drive_id}' and "
        f"folder_path ge '{parent_path_prefix}' and "
        f"folder_path lt '{parent_path_prefix}￿'"
    )
    return [dict(e) for e in _tbl(config.TABLE_ITEMSINDEX).query_entities(filter_str)]


# ── itemsindex ───────────────────────────────────────────────────────────────

def get_item_index(drive_id: str, drive_item_id: str) -> dict | None:
    try:
        return dict(_tbl(config.TABLE_ITEMSINDEX).get_entity(
            partition_key=drive_id, row_key=drive_item_id
        ))
    except ResourceNotFoundError:
        return None


def upsert_item_index(
    drive_id: str,
    drive_item_id: str,
    content_hash: str,
    name: str,
    folder_path: str,
    parent_document_id: str,
    total_chunks: int,
    last_modified_utc: str,
    sp_list_item_id: str = "",
) -> None:
    _tbl(config.TABLE_ITEMSINDEX).upsert_entity({
        "PartitionKey": drive_id,
        "RowKey": drive_item_id,
        "content_hash": content_hash,
        "sp_list_item_id": sp_list_item_id,
        "name": name,
        "folder_path": folder_path,
        "parent_document_id": parent_document_id,
        "total_chunks": total_chunks,
        "last_indexed_utc": _now_iso(),
        "last_modified_utc": last_modified_utc,
    })


def delete_item_index(drive_id: str, drive_item_id: str) -> None:
    try:
        _tbl(config.TABLE_ITEMSINDEX).delete_entity(
            partition_key=drive_id, row_key=drive_item_id
        )
    except ResourceNotFoundError:
        pass
