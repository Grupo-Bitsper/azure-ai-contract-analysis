"""Dead Letter Queue writer — Azure Storage Queue via MI.

Messages follow the shape:
    {
        "event_type": "file_upsert" | "acl_refresh" | "full_resync",
        "site_id": str,
        "item_id": str | None,
        "content_hash": str | None,
        "error": str,
        "timestamp": ISO,
        "attempts": int
    }

The alert rule (Paso 3) fires when the queue has >5 items in 1h.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from azure.storage.queue import QueueClient

from . import auth, config

log = logging.getLogger("roca-dlq")

_client: Optional[QueueClient] = None
_client_lock = Lock()


def get_dlq_client() -> QueueClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = QueueClient(
                account_url=f"https://{config.STORAGE_ACCOUNT}.queue.core.windows.net",
                queue_name=config.DLQ_QUEUE,
                credential=auth.get_mi_credential(),
                message_encode_policy=None,
            )
            try:
                _client.create_queue()
            except Exception:
                pass  # already exists
        return _client


def send_dlq_message(
    event_type: str,
    error: str,
    *,
    site_id: str | None = None,
    item_id: str | None = None,
    content_hash: str | None = None,
    attempts: int = 1,
) -> None:
    msg = {
        "event_type": event_type,
        "site_id": site_id,
        "item_id": item_id,
        "content_hash": content_hash,
        "error": error[:4000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attempts": attempts,
    }
    client = get_dlq_client()
    payload = base64.b64encode(json.dumps(msg).encode("utf-8")).decode("ascii")
    client.send_message(payload)
    # Structured log — the scheduled query alert rule matches on the
    # "[ROCA-DLQ-WRITE]" prefix to dispatch to Action Group ag-roca-copilot-prod.
    log.error(
        "[ROCA-DLQ-WRITE] event_type=%s site_id=%s item_id=%s hash=%s error=%s",
        event_type, site_id, item_id, content_hash, error[:200],
    )
