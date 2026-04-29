"""func-roca-ingest-prod — Pipeline de indexación SharePoint → AI Search.

8 handlers en este archivo:
  1. webhook_handler       HTTP  — recibe eventos Graph/EventGrid
  2. delta_worker          Queue — procesa delta-sync-queue
  3. enumeration_worker    Queue — procesa enumeration-queue (full enum de drive)
  4. file_worker           Queue — procesa file-process-queue (upsert/rename/move/delete)
  5. subscription_renewer  Timer — renueva Graph subscriptions diariamente
  6. http_full_resync      HTTP  — encola enumeración de todos los drives
  7. http_status           HTTP  — devuelve estado de colas + deltatokens
  8. http_read_document    HTTP  — lee texto OCR de un doc para la tool del agente

NO tocar func-roca-copilot-sync (bot de Teams). Este es un Function App separado.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import azure.functions as func

# Capture any import error and surface it to App Insights before crashing
_IMPORT_ERROR: str | None = None
try:
    from shared import config  # Step 1: just config (reads env vars)
    logging.warning("DIAG: config OK")
    from shared import auth  # Step 2: auth (msal, azure-identity)
    logging.warning("DIAG: auth OK")
    from shared import graph_client, ingestion, search_client, table_storage, queue_storage
    logging.warning("DIAG: shared modules OK")
    from shared import file_actions
    logging.warning("DIAG: file_actions OK")
    from shared.docintel_client import analyze_pdf_bytes, analyze_pdf_url
    logging.warning("DIAG: docintel OK")
    from shared.embeddings import embed_batch
    logging.warning("DIAG: embeddings OK")
    from shared.extraction import run_extraction
    logging.warning("DIAG: extraction OK — ALL IMPORTS OK")
except Exception as _exc:
    _IMPORT_ERROR = "".join(traceback.format_exception(type(_exc), _exc, _exc.__traceback__))
    logging.error("STARTUP IMPORT ERROR:\n%s", _IMPORT_ERROR)
    raise

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
logger = logging.getLogger(__name__)


# ── Logging estructurado ─────────────────────────────────────────────────────

def _log(level: str, event: str, **fields: Any) -> None:
    """Emite un log JSON queryable en App Insights. correlation_id es obligatorio."""
    payload = {"event": event, **fields}
    msg = json.dumps(payload, ensure_ascii=False, default=str)
    getattr(logger, level)(msg)


# ── timer_sync_sharepoint ────────────────────────────────────────────────────

# DECISION: schedule cada 5 min en vez de cada 1 min — delta-sync-queue ya
# es drenada continuamente por delta_worker; más frecuencia solo mete ruido.
# Graph delta con token fresco responde en <1s sin cambios → near-zero cost.
@app.schedule(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def timer_sync_sharepoint(timer: func.TimerRequest) -> None:
    """Polling fallback: cada 5 min encola delta-sync por cada drive monitoreado.

    Propósito: redundancia contra falla silenciosa de Graph subscriptions
    (expiry sin renovar, Event Grid down, webhook ACK perdido). El
    subscription_renewer cubre el caso "sub expirada". Este timer cubre
    el caso "sub activa pero no llega el webhook".
    """
    correlation_id = str(uuid.uuid4())
    enqueued = 0
    for site_name in config.SP_SITES:
        try:
            site_id = graph_client.get_site_id(site_name)
            drive_id = graph_client.get_default_drive_id(site_id)
            queue_storage.enqueue_delta_sync(
                site_id=site_id,
                drive_id=drive_id,
                source="timer",
                correlation_id=correlation_id,
            )
            enqueued += 1
        except Exception as exc:
            _log("error", "timer_sync_site_error",
                 site=site_name, detail=str(exc),
                 correlation_id=correlation_id)

    _log("info", "timer_sync_done",
         correlation_id=correlation_id, enqueued=enqueued,
         sites=list(config.SP_SITES))


# ── 1. webhook_handler ───────────────────────────────────────────────────────

@app.route(route="webhook/graph", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def webhook_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Acepta callbacks de Graph change notifications (directo o vía Event Grid).

    GET  → validación de Graph webhook (devuelve validationToken)
    POST → notificación de cambio → encola a delta-sync-queue
    """
    # Validation handshake (Graph Direct webhooks + Event Grid partner topic)
    validation_token = req.params.get("validationToken")
    if validation_token:
        _log("info", "webhook_validation", token_len=len(validation_token))
        return func.HttpResponse(
            validation_token,
            status_code=200,
            mimetype="text/plain",
        )

    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse("Bad JSON", status_code=400)

    # Soporta formato CloudEvent (Event Grid) y formato Graph directo
    notifications = body.get("value", [body] if "subscriptionId" in body else [])
    enqueued = 0
    for notif in notifications:
        client_state = notif.get("clientState") or notif.get("data", {}).get("clientState", "")
        if client_state != config.CLIENT_STATE:
            _log("warning", "webhook_client_state_mismatch", received=client_state)
            continue

        resource = notif.get("resource") or notif.get("data", {}).get("resource", "")
        sub_id = notif.get("subscriptionId") or notif.get("data", {}).get("subscriptionId")
        correlation_id = str(uuid.uuid4())

        # Extraer drive_id del resource path: /drives/{id}/root
        drive_id = None
        if "/drives/" in resource:
            parts = resource.split("/drives/")
            drive_id = parts[1].split("/")[0] if len(parts) > 1 else None

        if not drive_id:
            _log("warning", "webhook_no_drive_id", resource=resource)
            continue

        # Resolver site_id a partir del drive_id (necesario para delta lookup)
        site_id = notif.get("tenantId") or "unknown"
        queue_storage.enqueue_delta_sync(
            site_id=site_id,
            drive_id=drive_id,
            source="webhook",
            correlation_id=correlation_id,
            subscription_id=sub_id,
        )
        enqueued += 1
        _log("info", "webhook_enqueued", correlation_id=correlation_id,
             drive_id=drive_id, sub_id=sub_id)

    return func.HttpResponse(json.dumps({"enqueued": enqueued}),
                             status_code=202, mimetype="application/json")


# ── 2. delta_worker ──────────────────────────────────────────────────────────

# DECISION: connection="AzureWebJobsStorage" y queue_name hardcoded según
# signatures validados del plan. Los settings AzureWebJobsStorage__queueServiceUri
# ya están configurados para MI identity-based contra stroingest.
@app.queue_trigger(arg_name="msg", queue_name="delta-sync-queue",
                   connection="AzureWebJobsStorage")
def delta_worker(msg: func.QueueMessage) -> None:
    """Lee el delta de Graph para el drive y clasifica cada cambio.

    Por cada item del delta:
      - deleted (archivo)  → encola delete en file-process-queue
      - deleted (folder)   → enumera descendientes vía itemsindex, delete cada uno
      - folder nuevo/rename → upsert folderpaths, si cambió path → folder_rename
      - archivo nuevo      → enqueue upsert
      - archivo edit       → enqueue upsert (dedup en file_worker)
      - archivo rename     → enqueue rename (sin re-OCR)
      - archivo move       → enqueue move (sin re-OCR)

    Al final persiste el nuevo deltaLink en table deltatokens.
    EC-15: si Graph devuelve 410 (token expired), limpia token + encola enumeration.
    """
    payload = json.loads(msg.get_body().decode("utf-8"))
    correlation_id: str = payload.get("correlation_id") or str(uuid.uuid4())
    drive_id: str = payload["drive_id"]
    site_id: str = payload["site_id"]

    _log("info", "delta_worker_start", correlation_id=correlation_id,
         drive_id=drive_id, source=payload.get("source"))

    delta_link = table_storage.get_delta_link(site_id, drive_id)

    try:
        items = list(graph_client.iter_delta_changes(drive_id, delta_link))
    except RuntimeError as exc:
        if "410" in str(exc):
            _log("warning", "delta_410_gone", correlation_id=correlation_id,
                 drive_id=drive_id)
            table_storage.save_delta_link(site_id, drive_id, "", 0)
            queue_storage.enqueue_enumeration(
                site_id=site_id, drive_id=drive_id,
                reason="delta_410_recovery", correlation_id=correlation_id,
            )
            return
        raise

    # Extraer nuevo deltaLink del marcador especial
    new_delta_link = delta_link
    real_items = []
    for item in items:
        if "__final_delta_link__" in item:
            new_delta_link = item["__final_delta_link__"]
        else:
            real_items.append(item)

    changes_count = 0
    for item in real_items:
        item_id = item.get("id")
        if not item_id:
            continue

        mime = (item.get("file") or {}).get("mimeType", "")
        is_folder = "folder" in item
        is_deleted = "deleted" in item

        # EC-08: skip non-PDF files (folders sí se procesan para path tracking)
        if not is_folder and not is_deleted and mime != "application/pdf":
            _log("info", "delta_skip_non_pdf", correlation_id=correlation_id,
                 item_id=item_id, mime=mime)
            continue

        if is_deleted:
            if is_folder:
                # EC-07: folder delete → propagar deletes a hijos vía itemsindex
                old_path = table_storage.get_folder_path(drive_id, item_id)
                if old_path:
                    descendants = table_storage.list_descendant_items(drive_id, old_path)
                    for d in descendants:
                        queue_storage.enqueue_delete(
                            drive_id=drive_id,
                            drive_item_id=d["RowKey"],
                            correlation_id=correlation_id,
                        )
            else:
                queue_storage.enqueue_delete(
                    drive_id=drive_id,
                    drive_item_id=item_id,
                    correlation_id=correlation_id,
                )
            changes_count += 1
            continue

        if is_folder:
            parent = item.get("parentReference") or {}
            parent_path = parent.get("path", "").split("root:")[-1].lstrip("/")
            folder_path = f"{parent_path}/{item.get('name', '')}".lstrip("/")
            old_path = table_storage.get_folder_path(drive_id, item_id)
            table_storage.upsert_folder_path(
                drive_id, item_id, folder_path, parent.get("id", "")
            )
            # EC-05: folder rename detectado
            if old_path and old_path != folder_path:
                queue_storage.enqueue_folder_rename(
                    drive_id=drive_id,
                    folder_item_id=item_id,
                    old_path=old_path,
                    new_path=folder_path,
                    correlation_id=correlation_id,
                )
                changes_count += 1
            continue

        # Archivo: clasificar upsert / rename / move
        existing = table_storage.get_item_index(drive_id, item_id)
        name = item.get("name", "")
        parent_ref = item.get("parentReference") or {}
        parent_folder_id = parent_ref.get("id", "")
        parent_path = parent_ref.get("path", "").split("root:")[-1].lstrip("/")
        web_url = item.get("webUrl", "")
        last_mod = item.get("lastModifiedDateTime", "")
        size_bytes = (item.get("size") or 0)

        if existing:
            name_changed = existing.get("name") != name
            # DECISION: comparamos parent_folder_id reconstruido desde folder_path
            # del itemsindex — el pipeline actual no guarda parent_folder_id directo.
            existing_folder = existing.get("folder_path", "")
            parent_changed = existing_folder != parent_path

            if name_changed and not parent_changed:
                queue_storage.enqueue_rename(
                    drive_id=drive_id, drive_item_id=item_id,
                    new_name=name, new_web_url=web_url,
                    correlation_id=correlation_id,
                )
            elif parent_changed:
                queue_storage.enqueue_move(
                    drive_id=drive_id, drive_item_id=item_id,
                    new_parent_folder_id=parent_folder_id,
                    new_folder_path=parent_path,
                    correlation_id=correlation_id,
                )
            else:
                # Posible edit de contenido — dedup en _handle_upsert decide
                queue_storage.enqueue_upsert(
                    site_id=site_id, drive_id=drive_id, drive_item_id=item_id,
                    name=name, web_url=web_url, size_bytes=size_bytes,
                    last_modified_utc=last_mod, parent_folder_id=parent_folder_id,
                    correlation_id=correlation_id,
                )
        else:
            queue_storage.enqueue_upsert(
                site_id=site_id, drive_id=drive_id, drive_item_id=item_id,
                name=name, web_url=web_url, size_bytes=size_bytes,
                last_modified_utc=last_mod, parent_folder_id=parent_folder_id,
                correlation_id=correlation_id,
            )
        changes_count += 1

    if new_delta_link:
        table_storage.save_delta_link(site_id, drive_id, new_delta_link, changes_count)

    _log("info", "delta_worker_done", correlation_id=correlation_id,
         drive_id=drive_id, changes=changes_count)


# ── 3. enumeration_worker ────────────────────────────────────────────────────

@app.queue_trigger(arg_name="msg", queue_name="enumeration-queue",
                   connection="AzureWebJobsStorage")
def enumeration_worker(msg: func.QueueMessage) -> None:
    """Enumera todos los PDFs de un drive y encola upserts a file-process-queue.

    Se dispara por:
      - delta_worker ante un 410 Gone (token expirado, resync requerido)
      - http_full_resync (trigger admin manual)

    Sin límite de HTTP timeout — corre hasta MAX_ENUM_ITEMS items por invocación.
    """
    payload = json.loads(msg.get_body().decode("utf-8"))
    correlation_id: str = payload.get("correlation_id") or str(uuid.uuid4())
    drive_id: str = payload["drive_id"]
    site_id: str = payload["site_id"]
    target_index: str = payload.get("target_index") or config.TARGET_INDEX_NAME

    _log("info", "enumeration_start", correlation_id=correlation_id,
         drive_id=drive_id, reason=payload.get("reason"),
         target_index=target_index)

    count = 0
    for item in graph_client.list_drive_items_recursive(
        drive_id, max_items=config.MAX_ENUM_ITEMS
    ):
        queue_storage.enqueue_upsert(
            site_id=site_id,
            drive_id=drive_id,
            drive_item_id=item["id"],
            name=item.get("name", ""),
            web_url=item.get("webUrl", ""),
            size_bytes=item.get("size") or 0,
            last_modified_utc=item.get("lastModifiedDateTime", ""),
            parent_folder_id=(item.get("parentReference") or {}).get("id", ""),
            correlation_id=correlation_id,
            target_index=target_index,
        )
        count += 1

    _log("info", "enumeration_done", correlation_id=correlation_id,
         drive_id=drive_id, items_enqueued=count)


@app.route(route="admin/full-resync", methods=["POST"])
def http_full_resync(req: func.HttpRequest) -> func.HttpResponse:
    """Encola enumeración completa de todos los drives configurados.

    Body JSON requerido: {"confirm": "YES_REPROCESS_ALL"}
    Opcional: {"target_index": "roca-contracts-v1-shadow"}
    """
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse("JSON inválido", status_code=400)

    if body.get("confirm") != "YES_REPROCESS_ALL":
        return func.HttpResponse(
            '{"error": "confirm=YES_REPROCESS_ALL requerido"}',
            status_code=400, mimetype="application/json",
        )

    target_index = body.get("target_index") or config.TARGET_INDEX_NAME
    correlation_id = str(uuid.uuid4())
    enqueued_sites = []

    for site_name in config.SP_SITES:
        try:
            site_id = graph_client.get_site_id(site_name)
            drive_id = graph_client.get_default_drive_id(site_id)
            queue_storage.enqueue_enumeration(
                site_id=site_id, drive_id=drive_id,
                reason="manual_resync", correlation_id=correlation_id,
                target_index=target_index,
            )
            enqueued_sites.append(site_name)
        except Exception as exc:
            _log("error", "full_resync_site_error", site=site_name,
                 detail=str(exc), correlation_id=correlation_id)

    _log("info", "full_resync_enqueued", correlation_id=correlation_id,
         sites=enqueued_sites, target_index=target_index)
    return func.HttpResponse(
        json.dumps({"correlation_id": correlation_id, "enqueued_sites": enqueued_sites,
                    "target_index": target_index}),
        status_code=202, mimetype="application/json",
    )


# ── 4. file_worker ───────────────────────────────────────────────────────────

@app.queue_trigger(arg_name="msg", queue_name="file-process-queue",
                   connection="AzureWebJobsStorage")
def file_worker(msg: func.QueueMessage) -> None:
    """Dispatcher por action: upsert / rename / move / delete / folder_rename.

    Los sub-handlers viven en shared.file_actions para mantener este archivo
    legible. En host.json: batchSize=4, maxDequeueCount=5 → fallos permanentes
    van a file-process-queue-poison tras 5 intentos.
    """
    payload = json.loads(msg.get_body().decode("utf-8"))
    action: str = payload.get("action", "upsert")
    correlation_id: str = payload.get("correlation_id") or str(uuid.uuid4())
    drive_id: str = payload.get("drive_id", "")

    if action in config.DISABLE_ACTIONS:
        _log("warning", "file_worker_action_disabled",
             action=action, correlation_id=correlation_id)
        return

    _log("info", "file_worker_start",
         action=action, correlation_id=correlation_id, drive_id=drive_id)

    if action == "upsert":
        file_actions.handle_upsert(payload, correlation_id)
    elif action == "rename":
        file_actions.handle_rename(payload, correlation_id)
    elif action == "move":
        file_actions.handle_move(payload, correlation_id)
    elif action == "delete":
        file_actions.handle_delete(payload, correlation_id)
    elif action == "folder_rename":
        file_actions.handle_folder_rename(payload, correlation_id)
    else:
        _log("error", "file_worker_unknown_action",
             action=action, correlation_id=correlation_id)


# ── 5. timer_purger ──────────────────────────────────────────────────────────

# DECISION: solo purga el índice en TARGET_INDEX_NAME (shadow durante migración).
# Cutover a prod se hará después de validación manual — el purger seguirá
# apuntando a shadow hasta que se cambie el setting. Guardrails anti-wipeout:
#   1. Si itemsindex está vacío (0 valid hashes) → skip (sospechoso, no borrar nada).
#   2. Si > 50% del índice sería marcado huérfano → skip + alerta (regression).
#   3. Respeta config.TARGET_INDEX_NAME — nunca toca otros índices.
@app.schedule(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def timer_purger(timer: func.TimerRequest) -> None:
    """Cada 1h: borra chunks huérfanos del índice shadow.

    Un chunk es huérfano si su content_hash no tiene entry en itemsindex
    (el item fue borrado de SharePoint pero el delta-worker no capturó
    el evento delete, o el proceso falló). Esta función es la red de
    seguridad para mantener el índice en sync con la verdad (SharePoint).
    """
    correlation_id = str(uuid.uuid4())
    target_index = config.TARGET_INDEX_NAME

    # 1) Build valid_hashes desde itemsindex (fuente de verdad del pipeline)
    valid_hashes: set[str] = set()
    try:
        from azure.data.tables import TableServiceClient
        tbl_svc = TableServiceClient(
            endpoint=f"https://{config.INGEST_STORAGE_ACCOUNT}.table.core.windows.net",
            credential=auth.get_mi_credential(),
        )
        entities = tbl_svc.get_table_client(config.TABLE_ITEMSINDEX).list_entities(
            select=["content_hash"]
        )
        for e in entities:
            h = e.get("content_hash")
            if h:
                valid_hashes.add(h)
    except Exception as exc:
        _log("error", "purger_itemsindex_read_failed",
             correlation_id=correlation_id, detail=str(exc))
        return

    # GUARDRAIL 1: si no hay items válidos, no borrar nada (sospechoso)
    if not valid_hashes:
        _log("info", "purger_skip_empty_itemsindex",
             correlation_id=correlation_id, target_index=target_index)
        return

    # 2) Escanear índice shadow para obtener set de content_hashes presentes
    from azure.search.documents import SearchClient
    sc = SearchClient(
        endpoint=config.SEARCH_ENDPOINT,
        index_name=target_index,
        credential=auth.get_mi_credential(),
    )
    try:
        results = sc.search(search_text="*", select=["content_hash"], top=1000)
        index_hashes: set[str] = set()
        for r in results:
            h = r.get("content_hash")
            if h:
                index_hashes.add(h)
    except Exception as exc:
        _log("error", "purger_search_scan_failed",
             correlation_id=correlation_id, target_index=target_index,
             detail=str(exc))
        return

    orphans = index_hashes - valid_hashes
    if not orphans:
        _log("info", "purger_no_orphans",
             correlation_id=correlation_id, target_index=target_index,
             index_hashes_count=len(index_hashes),
             valid_hashes_count=len(valid_hashes))
        return

    # GUARDRAIL 2: si >50% del índice sería huérfano, skip (regression suspect)
    orphan_ratio = len(orphans) / max(len(index_hashes), 1)
    if orphan_ratio > 0.5:
        _log("error", "purger_skip_too_many_orphans",
             correlation_id=correlation_id, target_index=target_index,
             orphan_count=len(orphans), index_hashes_count=len(index_hashes),
             orphan_ratio=round(orphan_ratio, 3))
        return

    deleted_chunks = 0
    failed_hashes = []
    for h in orphans:
        try:
            ok, failed = search_client.delete_by_content_hash(h, target_index)
            deleted_chunks += ok
            if failed:
                failed_hashes.append(h)
        except Exception as exc:
            _log("error", "purger_delete_failed",
                 correlation_id=correlation_id, content_hash=h, detail=str(exc))
            failed_hashes.append(h)

    _log("info", "purger_done",
         correlation_id=correlation_id, target_index=target_index,
         orphan_hashes=len(orphans), chunks_deleted=deleted_chunks,
         failed_hashes=len(failed_hashes))


# ── 6. subscription_renewer ──────────────────────────────────────────────────

# DECISION: schedule 03:00 UTC según plan (no 06:00 UTC del backup viejo).
# DECISION: handler CREA subs si no existen Y renueva las existentes — necesario
# porque el tenant actualmente tiene 0 subs activas (plan update §1).
@app.schedule(schedule="0 0 3 * * *", arg_name="timer", run_on_startup=False)
def subscription_renewer(timer: func.TimerRequest) -> None:
    """Diario 03:00 UTC: garantiza que hay subscriptions Graph activas por drive.

    Por cada site configurado:
      - Si hay subscription_id en deltatokens → PATCH para extender expiración
      - Si la renew retorna 404 (sub borrada) → POST para crear una nueva
      - Si no hay entry en la tabla → POST para crear inicial

    Graph subs para /drives/{id}/root tienen expiration max de ~2.93 días.
    Target: expiration = now + 3 días (clamp a 2.9 días si Graph rechaza).
    """
    now = datetime.now(timezone.utc)
    # Graph limita expiración de driveItem subs a ~4230 min (2.93 días). 2.5 días
    # es seguro y deja margen > 24h para la siguiente corrida del renewer.
    new_expiry = (now + timedelta(hours=60)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    correlation_id = str(uuid.uuid4())
    webhook_url = f"https://func-roca-ingest-prod.azurewebsites.net/api/webhook/graph"

    created = 0
    renewed = 0
    failed = 0

    for site_name in config.SP_SITES:
        try:
            site_id = graph_client.get_site_id(site_name)
            drive_id = graph_client.get_default_drive_id(site_id)

            existing = None
            for entry in table_storage.list_all_subscriptions():
                if entry.get("PartitionKey") == site_id and entry.get("RowKey") == drive_id:
                    existing = entry
                    break

            sub_id = (existing or {}).get("subscription_id")
            if sub_id:
                try:
                    graph_client.renew_subscription(sub_id, new_expiry)
                    table_storage.save_subscription(
                        site_id, drive_id, sub_id, new_expiry
                    )
                    renewed += 1
                    _log("info", "subscription_renewed",
                         correlation_id=correlation_id,
                         site=site_name, sub_id=sub_id, new_expiry=new_expiry)
                    continue
                except RuntimeError as exc:
                    if "404" not in str(exc):
                        raise
                    _log("warning", "subscription_expired_recreating",
                         correlation_id=correlation_id,
                         site=site_name, old_sub_id=sub_id)

            # Crear subscription nueva
            new_sub = graph_client.create_subscription(
                drive_id=drive_id,
                notification_url=webhook_url,
                expiration_dt=new_expiry,
                client_state=config.CLIENT_STATE,
            )
            table_storage.save_subscription(
                site_id, drive_id, new_sub["id"], new_expiry
            )
            created += 1
            _log("info", "subscription_created",
                 correlation_id=correlation_id, site=site_name,
                 sub_id=new_sub["id"], new_expiry=new_expiry)

        except Exception as exc:
            failed += 1
            _log("error", "subscription_renew_site_failed",
                 correlation_id=correlation_id, site=site_name,
                 detail=str(exc))

    _log("info", "subscription_renewer_done",
         correlation_id=correlation_id,
         created=created, renewed=renewed, failed=failed)


# ── 7. http_status ───────────────────────────────────────────────────────────


@app.route(route="status", methods=["GET"])
def http_status(req: func.HttpRequest) -> func.HttpResponse:
    """Devuelve estado operativo: profundidades de colas + último delta por drive."""
    from azure.storage.queue import QueueServiceClient

    q_svc = QueueServiceClient(
        account_url=f"https://{config.INGEST_STORAGE_ACCOUNT}.queue.core.windows.net",
        credential=auth.get_mi_credential(),
    )
    queue_depths: dict[str, int] = {}
    for qname in [config.DELTA_SYNC_QUEUE, config.FILE_PROCESS_QUEUE,
                  config.ENUMERATION_QUEUE,
                  f"{config.DELTA_SYNC_QUEUE}-poison",
                  f"{config.FILE_PROCESS_QUEUE}-poison"]:
        try:
            props = q_svc.get_queue_client(qname).get_queue_properties()
            queue_depths[qname] = props.approximate_message_count
        except Exception:
            queue_depths[qname] = -1

    delta_entries = table_storage.list_all_subscriptions()
    deltas = [
        {
            "drive_id": e.get("RowKey"),
            "site_id": e.get("PartitionKey"),
            "last_sync_utc": e.get("last_sync_utc"),
            "last_changes_count": e.get("last_changes_count"),
            "subscription_expires_utc": e.get("subscription_expires_utc"),
        }
        for e in delta_entries
    ]

    return func.HttpResponse(
        json.dumps({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "queue_depths": queue_depths,
            "delta_tokens": deltas,
            "target_index": config.TARGET_INDEX_NAME,
        }, ensure_ascii=False),
        status_code=200, mimetype="application/json",
    )


# ── 8. http_read_document ─────────────────────────────────────────────────────


@app.route(route="read_document/{content_hash}", methods=["GET"])
def http_read_document(req: func.HttpRequest) -> func.HttpResponse:
    # NOTA: path param se lee vía req.route_params, NO como arg de la función.
    # En Azure Functions Python v2 Flex, pasar `content_hash: str` como 2º arg
    # rompe el worker indexing silente y el app reporta "0 functions found".
    content_hash = req.route_params.get("content_hash", "")
    """Lee el texto completo de un documento desde los chunks del índice.

    Uso por el agente Foundry (tool read_document): después de que search_index
    identifique un documento, el agente llama esta tool para leer el contenido
    completo y extraer firmantes, fechas, notaría u otros detalles específicos.

    La respuesta reconstruye el texto de los chunks ordenados por chunk_id —
    no re-OCR, no re-descarga. Respuesta en <200ms.

    Query params:
      page_range  (opcional): "1-5" para primeras 5 páginas equivalentes.
                  Cada chunk ≈ 2000 chars ≈ ~1-2 páginas.
    """
    if not content_hash or len(content_hash) < 16:
        return func.HttpResponse(
            json.dumps({"error": "content_hash inválido"}),
            status_code=400, mimetype="application/json",
        )

    index_name = req.params.get("index") or config.TARGET_INDEX_NAME
    chunks = search_client.read_chunks_by_hash(content_hash, index_name)
    if not chunks:
        return func.HttpResponse(
            json.dumps({"error": f"Documento {content_hash} no encontrado en índice {index_name}"}),
            status_code=404, mimetype="application/json",
        )

    # Aplicar page_range (aproximado: cada chunk ≈ 1 página)
    page_range = req.params.get("page_range")
    total_chunks = chunks[0].get("total_chunks") or len(chunks)
    pages_returned = f"1-{total_chunks}"
    if page_range:
        try:
            start_page, end_page = map(int, page_range.split("-"))
            chunks = chunks[start_page - 1 : end_page]
            pages_returned = page_range
        except (ValueError, IndexError):
            pass

    # Reconstruir texto (quitando el header de metadatos ya estructurado —
    # el agente los recibe en el JSON de search_index; aquí queremos el texto puro)
    text_parts = []
    for c in chunks:
        raw = c.get("content") or ""
        # Strip metadata header, keep OCR text
        if "[CONTENIDO DEL DOCUMENTO" in raw:
            raw = raw.split("[CONTENIDO DEL DOCUMENTO")[1]
            raw = raw.split("]\n", 1)[-1] if "]\n" in raw else raw
        text_parts.append(raw.strip())

    full_text = "\n\n---\n\n".join(text_parts)

    meta = chunks[0]
    return func.HttpResponse(
        json.dumps({
            "document_id": content_hash,
            "title": meta.get("nombre_archivo") or content_hash,
            "folder_path": meta.get("folder_path") or "",
            "source_url": meta.get("sharepoint_url") or "",
            "total_chunks": total_chunks,
            "pages_returned": pages_returned,
            "index_used": index_name,
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
            "text": full_text,
        }, ensure_ascii=False),
        status_code=200, mimetype="application/json",
    )
