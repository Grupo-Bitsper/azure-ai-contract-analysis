"""ROCA Copilot sync Function App — Durable Functions orchestrator.

Python v2 programming model. Reference architecture follows
Azure-Samples/MicrosoftGraphShadow (delta query + durable orchestration +
incremental state persistence).

Triggers:
    1. timer_sync_delta        Every 5 min → sync_delta_orchestrator
    2. timer_acl_refresh       Every 1 hour → acl_refresh_orchestrator
    3. timer_full_resync       Sunday 03:00 UTC → full_resync_orchestrator
    4. http_manual_process     On-demand (POST) → process_item_orchestrator
    5. http_status             On-demand (GET) → check orchestration status

Delta token state lives in a blob `delta-tokens/{drive_id}.token` in the
OCR container (same storage account). Simple and debuggable — Durable
Entities is a future optimization if contention becomes an issue.

WARNING: while TARGET_INDEX_NAME == roca-contracts-v1-staging, writes go to
the staging index. It flips to roca-contracts-v1 ONLY via explicit operator
action in Paso 5 (requires re-setting the app setting + restart).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests

import azure.durable_functions as df
import azure.functions as func
from azure.storage.blob import BlobClient

from shared import (
    acls as acls_mod,
    auth,
    config,
    dlq,
    docintel_client,
    embeddings,
    graph_client,
    ingestion,
    search_client,
)
from shared.dates import now_iso
from shared.extraction import run_extraction

# ============================================================================
# Retry policies — applied uniformly to all activity calls from orchestrators.
# Fase 5.5 review point #7: explicit retries from day one to avoid default
# behavior surprises.
# ============================================================================

RETRY_STANDARD = df.RetryOptions(
    first_retry_interval_in_milliseconds=5_000,
    max_number_of_attempts=3,
)
RETRY_FAST = df.RetryOptions(
    first_retry_interval_in_milliseconds=1_000,
    max_number_of_attempts=2,
)

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

log = logging.getLogger("roca-copilot-sync")
log.setLevel(logging.INFO)


# ============================================================================
# Delta token persistence (simple blob-based state)
# ============================================================================


def _delta_blob_client(drive_id: str) -> BlobClient:
    return BlobClient(
        account_url=f"https://{config.STORAGE_ACCOUNT}.blob.core.windows.net",
        container_name=config.OCR_CONTAINER,
        blob_name=f"delta-tokens/{drive_id}.token",
        credential=auth.get_mi_credential(),
    )


def read_delta_token(drive_id: str) -> str | None:
    try:
        bc = _delta_blob_client(drive_id)
        data = bc.download_blob().readall()
        return data.decode("utf-8").strip() or None
    except Exception:
        return None


def write_delta_token(drive_id: str, delta_link: str) -> None:
    bc = _delta_blob_client(drive_id)
    bc.upload_blob(delta_link.encode("utf-8"), overwrite=True)


# ============================================================================
# TIMER TRIGGERS
# ============================================================================


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer")
@app.durable_client_input(client_name="client")
async def timer_sync_delta(timer: func.TimerRequest, client: df.DurableOrchestrationClient):
    log.info("timer_sync_delta fired at %s", datetime.now(timezone.utc).isoformat())
    instance_id = await client.start_new("sync_delta_orchestrator", None, None)
    log.info("Started sync_delta_orchestrator: %s", instance_id)


@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer")
@app.durable_client_input(client_name="client")
async def timer_acl_refresh(timer: func.TimerRequest, client: df.DurableOrchestrationClient):
    log.info("timer_acl_refresh fired at %s", datetime.now(timezone.utc).isoformat())
    instance_id = await client.start_new("acl_refresh_orchestrator", None, None)
    log.info("Started acl_refresh_orchestrator: %s", instance_id)


@app.timer_trigger(schedule="0 0 3 * * 0", arg_name="timer")
@app.durable_client_input(client_name="client")
async def timer_full_resync(timer: func.TimerRequest, client: df.DurableOrchestrationClient):
    log.info("timer_full_resync fired at %s", datetime.now(timezone.utc).isoformat())
    instance_id = await client.start_new("full_resync_orchestrator", None, None)
    log.info("Started full_resync_orchestrator: %s", instance_id)


# ============================================================================
# HTTP TRIGGERS (manual dispatch + status)
# ============================================================================


@app.route(route="manual/process", methods=["POST"])
@app.durable_client_input(client_name="client")
async def http_manual_process(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    """Manually trigger a single-item process (used in Tests B, C).

    Body JSON:
        {
            "event_type": "file_upsert" | "acl_refresh" | "full_resync" | "sync_delta",
            "site_name": "ROCA-IAInmuebles" | "ROCAIA-INMUEBLESV2",
            "item_id": "<drive-item-id>"   (for file_upsert / acl_refresh)
        }
    """
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    event_type = body.get("event_type", "")
    if event_type == "sync_delta":
        instance_id = await client.start_new("sync_delta_orchestrator", None, None)
    elif event_type == "acl_refresh":
        instance_id = await client.start_new("acl_refresh_orchestrator", None, None)
    elif event_type == "full_resync":
        instance_id = await client.start_new("full_resync_orchestrator", None, None)
    elif event_type == "file_upsert":
        site_name = body.get("site_name")
        item_id = body.get("item_id")
        if not site_name or not item_id:
            return func.HttpResponse("file_upsert requires site_name + item_id", status_code=400)
        instance_id = await client.start_new(
            "process_item_orchestrator",
            None,
            {"site_name": site_name, "item_id": item_id},
        )
    else:
        return func.HttpResponse(f"Unknown event_type: {event_type}", status_code=400)

    return func.HttpResponse(
        json.dumps({"instance_id": instance_id, "event_type": event_type}),
        status_code=202,
        mimetype="application/json",
    )


@app.route(route="status/{instance_id}", methods=["GET"])
@app.durable_client_input(client_name="client")
async def http_status(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    instance_id = req.route_params.get("instance_id")
    status = await client.get_status(instance_id)
    if not status:
        return func.HttpResponse("Not found", status_code=404)
    payload = {
        "instance_id": instance_id,
        "runtime_status": str(status.runtime_status),
        "created": status.created_time.isoformat() if status.created_time else None,
        "last_updated": status.last_updated_time.isoformat() if status.last_updated_time else None,
        "input": status.input_,
        "output": status.output,
        "custom_status": status.custom_status,
    }
    return func.HttpResponse(json.dumps(payload, default=str), mimetype="application/json")


@app.route(route="health", methods=["GET"])
def http_health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(
            {
                "status": "ok",
                "target_index": config.TARGET_INDEX_NAME,
                "is_staging": config.target_is_staging(),
                "discovery_model": config.DISCOVERY_DEPLOYMENT,
                "embed_model": config.EMBED_DEPLOYMENT,
                "now": now_iso(),
            }
        ),
        mimetype="application/json",
    )


# ============================================================================
# TEAMS BOT — bridge al Agent Application roca-copilot (Responses API)
# ============================================================================

from types import SimpleNamespace

from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.core import TurnContext
from botbuilder.schema import Activity, ActivityTypes
from shared.bot import ask_roca_copilot

_BOT_CONFIG = SimpleNamespace(
    APP_ID=os.environ.get("BOT_APP_ID", ""),
    APP_PASSWORD=os.environ.get("BOT_APP_PASSWORD", ""),
    APP_TYPE="SingleTenant",
    APP_TENANTID="9015a126-356b-4c63-9d1f-d2138ca83176",
)
_BOT_ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(_BOT_CONFIG))


async def _bot_adapter_error(turn_context: TurnContext, error: Exception) -> None:
    log.error("[BOT-ERR] on_turn_error tipo=%s msg=%s", type(error).__name__, error, exc_info=error)


_BOT_ADAPTER.on_turn_error = _bot_adapter_error


def _bot_send_reply(service_url: str, conversation_id: str, activity_id: str, text: str) -> None:
    """Envía respuesta a Teams directamente vía HTTP (bypass MSAL/botbuilder outbound)."""
    tenant = "9015a126-356b-4c63-9d1f-d2138ca83176"
    token_resp = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ.get("BOT_APP_ID", ""),
            "client_secret": os.environ.get("BOT_APP_PASSWORD", ""),
            "scope": "https://api.botframework.com/.default",
        },
        timeout=10,
    )
    token_json = token_resp.json()
    if "access_token" not in token_json:
        log.error("[BOT-TOKEN] fallo HTTP=%s body=%s", token_resp.status_code, token_json)
        raise RuntimeError(f"Token error: {token_json.get('error')} — {token_json.get('error_description','')[:200]}")
    token = token_json["access_token"]
    url = f"{service_url.rstrip('/')}/v3/conversations/{conversation_id}/activities/{activity_id}"
    reply_resp = requests.post(
        url,
        json={"type": "message", "text": text, "replyToId": activity_id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    log.info("[BOT-REPLY] HTTP %s → %s", reply_resp.status_code, url)
    reply_resp.raise_for_status()


async def _bot_turn(turn_context: TurnContext) -> None:
    act = turn_context.activity
    log.info("[BOT] type=%s channelId=%s", act.type, act.channel_id)
    if act.type != ActivityTypes.message:
        return

    user_text = (act.text or "").strip()
    log.info("[BOT] user_text=%r", user_text[:100])
    if not user_text:
        return

    log.info("[BOT] llamando a ask_roca_copilot")
    try:
        answer = await asyncio.get_event_loop().run_in_executor(None, ask_roca_copilot, user_text)
        log.info("[BOT] respuesta len=%d", len(answer))
    except Exception:
        log.exception("[BOT] error en ask_roca_copilot")
        answer = "Error al consultar el agente. Intenta de nuevo en un momento."

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, _bot_send_reply,
            act.service_url, act.conversation.id, act.id, answer,
        )
        log.info("[BOT] respuesta enviada OK")
    except Exception:
        log.exception("[BOT] error en _bot_send_reply")


@app.route(route="messages", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def http_bot_messages(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint Bot Framework — Teams envía aquí cada mensaje del usuario."""
    log.info("[BOT-HTTP] POST /api/messages recibido")
    try:
        body = req.get_json()
        log.info("[BOT-HTTP] activity type=%s", body.get("type"))
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")
        log.info("[BOT-HTTP] auth_header presente=%s", bool(auth_header))
        response = await _BOT_ADAPTER.process_activity(auth_header, activity, _bot_turn)
        log.info("[BOT-HTTP] process_activity completado response=%s", response)
        if response:
            return func.HttpResponse(
                body=response.body,
                status_code=response.status,
                headers={"Content-Type": "application/json"},
            )
        return func.HttpResponse(status_code=201)
    except Exception:
        log.exception("[BOT-HTTP] excepción no manejada")
        return func.HttpResponse(status_code=500)


@app.timer_trigger(schedule="0 */4 * * * *", arg_name="timer_warmup",
                   run_on_startup=True)
def timer_bot_warmup(timer_warmup: func.TimerRequest) -> None:
    """Ping cada 4 min para mantener la función caliente (evita cold starts)."""
    log.info("Bot warmup ping — instancia activa.")


# ============================================================================
# ORCHESTRATORS
# ============================================================================


@app.orchestration_trigger(context_name="context")
def sync_delta_orchestrator(context: df.DurableOrchestrationContext):
    """Iterates both sites, fetches the drive delta page, dispatches
    process_item_activity for each changed file in parallel, then persists
    the new deltaLink. Idempotent by content_hash at the activity level."""
    summary: dict[str, Any] = {"sites": {}, "processed": 0, "errors": 0}
    for site_name in config.SP_SITES:
        drive_info = yield context.call_activity_with_retry(
            "resolve_drive_activity", RETRY_FAST, site_name
        )
        drive_id = drive_info["drive_id"]
        site_id = drive_info["site_id"]

        delta_result = yield context.call_activity_with_retry(
            "get_delta_changes_activity",
            RETRY_STANDARD,
            {"drive_id": drive_id},
        )
        changes = delta_result.get("changes", [])
        new_delta_link = delta_result.get("delta_link")

        tasks = []
        for change in changes:
            tasks.append(
                context.call_activity_with_retry(
                    "process_item_activity",
                    RETRY_STANDARD,
                    {
                        "site_name": site_name,
                        "site_id": site_id,
                        "drive_id": drive_id,
                        "item": change,
                    },
                )
            )
        results = yield context.task_all(tasks) if tasks else []

        ok = sum(1 for r in results if r.get("status") == "ok")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        errors = sum(1 for r in results if r.get("status") == "error")
        summary["sites"][site_name] = {
            "changes": len(changes),
            "ok": ok,
            "skipped": skipped,
            "errors": errors,
        }
        summary["processed"] += ok
        summary["errors"] += errors

        if new_delta_link:
            yield context.call_activity_with_retry(
                "persist_delta_token_activity",
                RETRY_FAST,
                {"drive_id": drive_id, "delta_link": new_delta_link},
            )
    return summary


@app.orchestration_trigger(context_name="context")
def acl_refresh_orchestrator(context: df.DurableOrchestrationContext):
    """Iterates all unique documents in the target index and refreshes ACLs
    (group_ids/user_ids) without re-running OCR/discovery/embeddings."""
    unique_hashes = yield context.call_activity_with_retry(
        "list_unique_hashes_activity", RETRY_FAST, None
    )
    tasks = [
        context.call_activity_with_retry("refresh_acls_activity", RETRY_STANDARD, payload)
        for payload in unique_hashes
    ]
    results = yield context.task_all(tasks) if tasks else []
    return {
        "docs_refreshed": sum(1 for r in results if r.get("status") == "ok"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
        "total": len(results),
    }


@app.orchestration_trigger(context_name="context")
def full_resync_orchestrator(context: df.DurableOrchestrationContext):
    """Enumerates all PDFs across both sites, fans-out process_item_activity
    per file. Dedup by content_hash inside the activity prevents redundant work.
    Safety net for missed delta events."""
    all_items: list[dict] = yield context.call_activity_with_retry(
        "enumerate_all_items_activity", RETRY_STANDARD, None
    )
    tasks = [
        context.call_activity_with_retry("process_item_activity", RETRY_STANDARD, payload)
        for payload in all_items
    ]
    results = yield context.task_all(tasks) if tasks else []
    return {
        "total_enumerated": len(all_items),
        "processed": sum(1 for r in results if r.get("status") == "ok"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
    }


@app.orchestration_trigger(context_name="context")
def process_item_orchestrator(context: df.DurableOrchestrationContext):
    """Wrapper for a single-file manual dispatch. Resolves the drive first,
    then calls process_item_activity."""
    input_data: dict = context.get_input()
    site_name = input_data["site_name"]
    item_id = input_data["item_id"]
    drive_info = yield context.call_activity_with_retry(
        "resolve_drive_activity", RETRY_FAST, site_name
    )
    result = yield context.call_activity_with_retry(
        "process_item_activity",
        RETRY_STANDARD,
        {
            "site_name": site_name,
            "site_id": drive_info["site_id"],
            "drive_id": drive_info["drive_id"],
            "item": {"id": item_id},
        },
    )
    return result


# ============================================================================
# ACTIVITIES
# ============================================================================


@app.activity_trigger(input_name="site_name")
def resolve_drive_activity(site_name: str) -> dict:
    site_id = graph_client.get_site_id(site_name)
    drive_id = graph_client.get_default_drive_id(site_id)
    return {"site_name": site_name, "site_id": site_id, "drive_id": drive_id}


@app.activity_trigger(input_name="payload")
def get_delta_changes_activity(payload: dict) -> dict:
    drive_id = payload["drive_id"]
    delta_link = read_delta_token(drive_id)

    changes: list[dict] = []
    final_delta: str | None = None
    for item in graph_client.iter_delta_changes(drive_id, delta_link):
        if "__final_delta_link__" in item:
            final_delta = item["__final_delta_link__"]
            continue
        if item.get("deleted"):
            continue
        file_info = item.get("file") or {}
        if file_info.get("mimeType") != "application/pdf":
            continue
        if item.get("size", 0) > 50 * 1024 * 1024:
            continue
        changes.append(
            {
                "id": item["id"],
                "name": item.get("name"),
                "webUrl": item.get("webUrl"),
                "size": item.get("size"),
                "parentReference": item.get("parentReference", {}),
            }
        )
    return {"changes": changes, "delta_link": final_delta}


@app.activity_trigger(input_name="payload")
def persist_delta_token_activity(payload: dict) -> dict:
    write_delta_token(payload["drive_id"], payload["delta_link"])
    return {"status": "ok"}


@app.activity_trigger(input_name="payload")
def list_unique_hashes_activity(payload: Any) -> list[dict]:
    """Returns one entry per unique content_hash with the SharePoint identity
    refs (sp_site_id, sp_list_id, sp_list_item_id) needed to re-fetch ACLs
    via Graph. Docs without those refs are skipped (legacy / manual imports)."""
    return search_client.list_unique_hashes_with_refs()


@app.activity_trigger(input_name="payload")
def refresh_acls_activity(payload: dict) -> dict:
    """G1 resolution (Fase 5.5): real ACL refresh. Re-fetches permissions
    from SharePoint via Graph using the identity refs stored in the index,
    expands SharePoint groups to Entra members, and updates `group_ids` /
    `user_ids` on all chunks of the document."""
    content_hash = payload["content_hash"]
    site_id = payload.get("sp_site_id") or ""
    list_id = payload.get("sp_list_id") or ""
    list_item_id = payload.get("sp_list_item_id") or ""
    if not (site_id and list_id and list_item_id):
        return {
            "status": "skipped",
            "reason": "missing sharepoint identity refs",
            "content_hash": content_hash,
        }
    try:
        group_ids, user_ids = acls_mod.extract_principals_for_item(
            site_id=site_id, list_id=list_id, list_item_id=list_item_id
        )
        ok, failed = search_client.update_acls_for_hash(content_hash, group_ids, user_ids)
        return {
            "status": "ok" if failed == 0 else "error",
            "content_hash": content_hash,
            "chunks_updated": ok,
            "chunks_failed": failed,
            "group_ids_count": len(group_ids),
            "user_ids_count": len(user_ids),
        }
    except Exception as e:
        logging.exception("refresh_acls_activity failed for hash %s", content_hash)
        dlq.send_dlq_message("acl_refresh", str(e), content_hash=content_hash)
        return {"status": "error", "error": str(e), "content_hash": content_hash}


@app.activity_trigger(input_name="payload")
def enumerate_all_items_activity(payload: Any) -> list[dict]:
    all_items: list[dict] = []
    for site_name in config.SP_SITES:
        try:
            site_id = graph_client.get_site_id(site_name)
            drive_id = graph_client.get_default_drive_id(site_id)
            for item in graph_client.list_drive_items_recursive(drive_id, max_items=500):
                if item.get("size", 0) > 50 * 1024 * 1024:
                    continue
                all_items.append(
                    {
                        "site_name": site_name,
                        "site_id": site_id,
                        "drive_id": drive_id,
                        "item": {
                            "id": item["id"],
                            "name": item.get("name"),
                            "webUrl": item.get("webUrl"),
                            "size": item.get("size"),
                            "parentReference": item.get("parentReference", {}),
                        },
                    }
                )
        except Exception as e:
            logging.exception("enumerate_all_items_activity failed for site %s", site_name)
            dlq.send_dlq_message("full_resync", str(e), site_id=site_name)
    return all_items


@app.activity_trigger(input_name="payload")
def process_item_activity(payload: dict) -> dict:
    """Core ingestion pipeline — matches ingest_prod.py 1:1 but reads from
    Graph instead of local disk, and populates group_ids/user_ids from ACLs.

    Dedup: if content_hash already exists in the target index, merge the new
    sharepoint_url into alternative_urls without re-running OCR/embeddings.
    """
    site_name = payload["site_name"]
    site_id = payload["site_id"]
    drive_id = payload["drive_id"]
    item_stub = payload["item"]
    item_id = item_stub["id"]

    try:
        # 1. Fetch full item metadata (need parentReference, webUrl, name)
        if not item_stub.get("webUrl"):
            full_item = graph_client.get_item(drive_id, item_id)
        else:
            full_item = item_stub

        name = full_item.get("name") or item_id
        web_url = full_item.get("webUrl") or ""
        parent_ref = full_item.get("parentReference") or {}
        folder_path = (parent_ref.get("path") or "").split("root:", 1)[-1].lstrip("/")

        # 2. Download bytes + compute hash
        pdf_bytes = graph_client.download_item_bytes(drive_id, item_id)
        content_hash = ingestion.md5_hash(pdf_bytes)

        # 3. Dedup check — if hash already in index, merge alternative_urls
        existing = search_client.find_by_content_hash(content_hash)
        if existing:
            current_urls = set(existing[0].get("alternative_urls") or [])
            current_urls.discard(existing[0].get("sharepoint_url") or "")
            if web_url and web_url != existing[0].get("sharepoint_url") and web_url not in current_urls:
                current_urls.add(web_url)
                patches = [
                    {"id": c["id"], "alternative_urls": sorted(current_urls)}
                    for c in existing
                ]
                search_client.get_search_client().merge_documents(documents=patches)
                return {
                    "status": "ok",
                    "mode": "dedup_hit_merge_urls",
                    "content_hash": content_hash,
                    "chunks": len(existing),
                    "new_alt_url": web_url,
                }
            return {
                "status": "skipped",
                "reason": "dedup_hit_no_changes",
                "content_hash": content_hash,
                "chunks": len(existing),
            }

        # 4. ACL extraction (D-7)
        list_id = parent_ref.get("sharepointIds", {}).get("listId") or ""
        list_item_id = parent_ref.get("sharepointIds", {}).get("listItemUniqueId") or ""
        if not list_id or not list_item_id:
            # Fallback: fetch the item again with sharepointIds expand
            full_item = graph_client.get_item(drive_id, item_id)
            sp_ids = (full_item.get("sharepointIds") or {})
            list_id = sp_ids.get("listId") or list_id
            list_item_id = sp_ids.get("listItemUniqueId") or list_item_id
        group_ids, user_ids = [], []
        if list_id and list_item_id:
            group_ids, user_ids = acls_mod.extract_principals_for_item(
                site_id=site_id, list_id=list_id, list_item_id=list_item_id
            )

        # 5. Upload raw bytes to blob (cache for re-indexing)
        blob_name = f"sample_discovery/{content_hash}.pdf"
        blob = BlobClient(
            account_url=f"https://{config.STORAGE_ACCOUNT}.blob.core.windows.net",
            container_name=config.OCR_CONTAINER,
            blob_name=blob_name,
            credential=auth.get_mi_credential(),
        )
        try:
            blob.upload_blob(pdf_bytes, overwrite=True)
        except Exception:
            logging.warning("Failed to cache raw PDF to blob %s", blob_name)

        # 6. Document Intelligence
        ocr_result = docintel_client.analyze_pdf_bytes(pdf_bytes)

        # 7. Extraction (gpt-4.1-mini) — fixed schema, not open-ended discovery
        extraction_output = run_extraction(ocr_result)
        if extraction_output is None:
            extraction_output = {}

        # 8. Extract typed metadata with F4B fixes
        meta = ingestion.extract_metadata(extraction_output)

        # 9. Chunking with metadata header
        content = ocr_result.get("content") or ""
        raw_chunks = ingestion.chunk_text(content)
        if len(raw_chunks) > config.MAX_CHUNKS_PER_DOC:
            raw_chunks = raw_chunks[: config.MAX_CHUNKS_PER_DOC]

        processing_iso = now_iso()
        headers_then_chunks: list[str] = []
        for cid, raw in enumerate(raw_chunks):
            header = ingestion.build_metadata_header(
                nombre_archivo=name,
                doc_type=meta["doc_type"],
                inmueble_codigos=meta["inmueble_codigos"],
                arrendador_nombre=meta["arrendador_nombre"],
                arrendatario_nombre=meta["arrendatario_nombre"],
                propietario_nombre=meta["propietario_nombre"],
                contribuyente_rfc=meta["contribuyente_rfc"],
                fecha_emision=meta["fecha_emision"],
                fecha_vencimiento=meta["fecha_vencimiento"],
                es_vigente=meta["es_vigente"],
                autoridad_emisora=meta["autoridad_emisora"],
                folder_path=folder_path,
                sharepoint_url=web_url,
                fecha_procesamiento_iso=processing_iso,
                chunk_id=cid,
                total_chunks=len(raw_chunks),
            )
            headers_then_chunks.append(header + raw)

        if not headers_then_chunks:
            return {
                "status": "skipped",
                "reason": "empty content after OCR",
                "content_hash": content_hash,
            }

        # 10. Embeddings
        vectors = embeddings.embed_batch(headers_then_chunks)

        # 11. Build docs + upsert
        parent_id = ingestion.parent_id_from_hash(content_hash)
        doc_title = name.rsplit(".", 1)[0] if name else content_hash[:16]
        extracted_metadata_str = json.dumps(extraction_output, ensure_ascii=False)

        docs = []
        for idx, (chunk, vec) in enumerate(zip(headers_then_chunks, vectors)):
            docs.append(
                {
                    "id": f"{parent_id}__{idx:04d}",
                    "parent_document_id": parent_id,
                    "content_hash": content_hash,
                    "chunk_id": idx,
                    "total_chunks": len(headers_then_chunks),
                    "content": chunk,
                    "content_vector": vec,
                    "sharepoint_url": web_url,
                    "alternative_urls": [],
                    "nombre_archivo": name,
                    "site_origen": site_name,
                    "folder_path": folder_path,
                    "fecha_procesamiento": processing_iso,
                    "group_ids": group_ids,
                    "user_ids": user_ids,
                    "sp_site_id": site_id,
                    "sp_list_id": list_id,
                    "sp_list_item_id": list_item_id,
                    "version_number": 1,
                    "is_latest_version": True,
                    "extraction_confidence": meta["extraction_confidence"],
                    "extraction_notes": meta["extraction_notes"],
                    "doc_type": meta["doc_type"],
                    "inmueble_codigos": meta["inmueble_codigos"],
                    "inmueble_codigo_principal": meta["inmueble_codigo_principal"],
                    "doc_title": doc_title,
                    "arrendador_nombre": meta["arrendador_nombre"],
                    "arrendatario_nombre": meta["arrendatario_nombre"],
                    "propietario_nombre": meta["propietario_nombre"],
                    "contribuyente_rfc": meta["contribuyente_rfc"],
                    "fecha_emision": meta["fecha_emision"],
                    "fecha_vencimiento": meta["fecha_vencimiento"],
                    "es_vigente": meta["es_vigente"],
                    "autoridad_emisora": meta["autoridad_emisora"],
                    "extracted_metadata": extracted_metadata_str,
                }
            )

        ok, failed, errors = search_client.upsert_documents(docs)

        return {
            "status": "ok" if failed == 0 else "error",
            "mode": "full_ingest",
            "content_hash": content_hash,
            "chunks": len(docs),
            "upsert_ok": ok,
            "upsert_failed": failed,
            "errors": errors[:5],
            "doc_type": meta["doc_type"],
            "group_ids_count": len(group_ids),
            "user_ids_count": len(user_ids),
            "es_vigente": meta["es_vigente"],
        }

    except Exception as e:
        logging.exception("process_item_activity failed for %s", item_id)
        dlq.send_dlq_message("file_upsert", str(e), site_id=site_id, item_id=item_id)
        return {"status": "error", "error": str(e), "item_id": item_id}
