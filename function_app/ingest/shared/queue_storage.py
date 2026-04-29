"""Queue Storage client — encola mensajes JSON en base64 al storage de ingest.

Azure Functions queue trigger decodifica base64 automáticamente (messageEncoding=base64
en host.json). Usamos el mismo encoding en el productor para consistencia.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from azure.storage.queue import QueueServiceClient, QueueClient

from . import auth, config

_service: Optional[QueueServiceClient] = None
_service_lock = Lock()


def _svc() -> QueueServiceClient:
    global _service
    with _service_lock:
        if _service is None:
            _service = QueueServiceClient(
                account_url=f"https://{config.INGEST_STORAGE_ACCOUNT}.queue.core.windows.net",
                credential=auth.get_mi_credential(),
            )
        return _service


def _q(name: str) -> QueueClient:
    return _svc().get_queue_client(name)


def _encode(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Enqueue helpers por tipo de mensaje ──────────────────────────────────────

def enqueue_delta_sync(
    site_id: str,
    drive_id: str,
    source: str = "manual",
    correlation_id: str | None = None,
    subscription_id: str | None = None,
) -> None:
    payload = {
        "version": "1.0",
        "source": source,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "site_id": site_id,
        "drive_id": drive_id,
        "subscription_id": subscription_id,
        "client_state": config.CLIENT_STATE,
        "change_type": "updated",
        "enqueued_at_utc": _now(),
        "attempt_count": 1,
    }
    _q(config.DELTA_SYNC_QUEUE).send_message(_encode(payload))


def enqueue_upsert(
    site_id: str,
    drive_id: str,
    drive_item_id: str,
    name: str,
    web_url: str,
    size_bytes: int,
    last_modified_utc: str,
    parent_folder_id: str,
    correlation_id: str,
    target_index: str | None = None,
) -> None:
    payload = {
        "version": "1.0",
        "action": "upsert",
        "correlation_id": correlation_id,
        "site_id": site_id,
        "drive_id": drive_id,
        "drive_item_id": drive_item_id,
        "name": name,
        "web_url": web_url,
        "size_bytes": size_bytes,
        "last_modified_utc": last_modified_utc,
        "parent_folder_id": parent_folder_id,
        "target_index": target_index or config.TARGET_INDEX_NAME,
        "enqueued_at_utc": _now(),
    }
    _q(config.FILE_PROCESS_QUEUE).send_message(_encode(payload))


def enqueue_rename(
    drive_id: str,
    drive_item_id: str,
    new_name: str,
    new_web_url: str,
    correlation_id: str,
) -> None:
    payload = {
        "version": "1.0",
        "action": "rename",
        "correlation_id": correlation_id,
        "drive_id": drive_id,
        "drive_item_id": drive_item_id,
        "new_name": new_name,
        "new_web_url": new_web_url,
        "enqueued_at_utc": _now(),
    }
    _q(config.FILE_PROCESS_QUEUE).send_message(_encode(payload))


def enqueue_move(
    drive_id: str,
    drive_item_id: str,
    new_parent_folder_id: str,
    new_folder_path: str,
    correlation_id: str,
) -> None:
    payload = {
        "version": "1.0",
        "action": "move",
        "correlation_id": correlation_id,
        "drive_id": drive_id,
        "drive_item_id": drive_item_id,
        "new_parent_folder_id": new_parent_folder_id,
        "new_folder_path": new_folder_path,
        "enqueued_at_utc": _now(),
    }
    _q(config.FILE_PROCESS_QUEUE).send_message(_encode(payload))


def enqueue_delete(
    drive_id: str,
    drive_item_id: str,
    correlation_id: str,
) -> None:
    payload = {
        "version": "1.0",
        "action": "delete",
        "correlation_id": correlation_id,
        "drive_id": drive_id,
        "drive_item_id": drive_item_id,
        "enqueued_at_utc": _now(),
    }
    _q(config.FILE_PROCESS_QUEUE).send_message(_encode(payload))


def enqueue_folder_rename(
    drive_id: str,
    folder_item_id: str,
    old_path: str,
    new_path: str,
    correlation_id: str,
) -> None:
    payload = {
        "version": "1.0",
        "action": "folder_rename",
        "correlation_id": correlation_id,
        "drive_id": drive_id,
        "folder_item_id": folder_item_id,
        "old_path": old_path,
        "new_path": new_path,
        "enqueued_at_utc": _now(),
    }
    _q(config.FILE_PROCESS_QUEUE).send_message(_encode(payload))


def enqueue_enumeration(
    site_id: str,
    drive_id: str,
    reason: str,
    correlation_id: str,
    target_index: str | None = None,
) -> None:
    payload = {
        "version": "1.0",
        "action": "enumerate",
        "correlation_id": correlation_id,
        "site_id": site_id,
        "drive_id": drive_id,
        "target_index": target_index or config.TARGET_INDEX_NAME,
        "max_items": config.MAX_ENUM_ITEMS,
        "reason": reason,
        "enqueued_at_utc": _now(),
    }
    _q(config.ENUMERATION_QUEUE).send_message(_encode(payload))
