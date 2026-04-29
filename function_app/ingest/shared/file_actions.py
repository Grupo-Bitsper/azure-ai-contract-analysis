"""Sub-handlers del file_worker — extraídos por longitud (~230 líneas).

Cada función asume que el payload fue validado por file_worker (action conocida,
no deshabilitada por DISABLE_ACTIONS). Emiten logs estructurados y re-lanzan
excepciones para que el runtime de Functions aplique retry/poison queue
semantics (maxDequeueCount=5 en host.json).

Acciones:
  upsert        — download + OCR + extract + chunk + embed + index (~130 líneas)
  rename        — patch nombre_archivo + sharepoint_url en todos los chunks
  move          — patch folder_path en todos los chunks
  delete        — borra chunks por content_hash y limpia itemsindex
  folder_rename — propaga como N moves individuales vía itemsindex
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from . import (
    config,
    graph_client,
    ingestion,
    queue_storage,
    search_client,
    table_storage,
)
from .docintel_client import analyze_pdf_bytes
from .embeddings import embed_batch
from .extraction import run_extraction

logger = logging.getLogger(__name__)


def _log(level: str, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    getattr(logger, level)(json.dumps(payload, ensure_ascii=False, default=str))


# ── upsert ────────────────────────────────────────────────────────────────────

def handle_upsert(payload: dict, correlation_id: str) -> None:
    """Download + OCR + extract + chunk + embed + index.

    Dedup: si content_hash ya existe en el índice, solo mergea alternative_urls
    y sale (EC-11). Evita re-OCR costoso de PDFs reuploaded con mismo contenido.

    Preflight: si size > PREFLIGHT_MAX_SIZE_MB, skip + log warning (EC-09).
    """
    drive_id = payload["drive_id"]
    drive_item_id = payload["drive_item_id"]
    size_bytes = payload.get("size_bytes") or 0
    target_index = payload.get("target_index") or config.TARGET_INDEX_NAME

    # EC-09: preflight size check
    max_bytes = config.PREFLIGHT_MAX_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        _log("warning", "upsert_preflight_oversize",
             correlation_id=correlation_id, drive_item_id=drive_item_id,
             size_mb=size_bytes // (1024 * 1024))
        return

    tmp_path: str | None = None
    try:
        tmp_path, content_hash = graph_client.stream_download_to_temp(
            drive_id, drive_item_id
        )

        # EC-11: dedup — si el mismo content_hash ya está indexado, solo mergea
        # alternative_urls (sin re-OCR). Maneja el caso de un file duplicado
        # subido a dos paths distintos.
        existing_chunks = search_client.find_by_content_hash(content_hash, target_index)
        if existing_chunks:
            new_url = payload.get("web_url", "")
            if new_url:
                existing_urls = set(existing_chunks[0].get("alternative_urls") or [])
                existing_urls.add(new_url)
                search_client.patch_document_fields(
                    content_hash,
                    {"alternative_urls": list(existing_urls)},
                    target_index,
                )
            _log("info", "upsert_dedup_hit",
                 correlation_id=correlation_id, content_hash=content_hash,
                 drive_item_id=drive_item_id)
            return

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
        ocr_result = analyze_pdf_bytes(pdf_bytes)

        model_output = run_extraction(ocr_result)
        metadata = ingestion.extract_metadata(model_output)

        ocr_text = ocr_result.get("content") or ""
        chunks = ingestion.chunk_text(ocr_text)
        if not chunks:
            _log("warning", "upsert_empty_ocr",
                 correlation_id=correlation_id, drive_item_id=drive_item_id)
            return

        total_chunks = len(chunks)
        parent_doc_id = ingestion.parent_id_from_hash(content_hash)
        now_iso = datetime.now(timezone.utc).isoformat()
        name = payload.get("name", "")
        web_url = payload.get("web_url", "")
        # DECISION: folder_path viene del parent_path del delta (ya normalizado),
        # no del parent_folder_id (que es un opaque ID no legible).
        folder_path = payload.get("parent_folder_id", "")

        headers = [
            ingestion.build_metadata_header(
                nombre_archivo=name,
                doc_type=metadata["doc_type"],
                inmueble_codigos=metadata["inmueble_codigos"],
                arrendador_nombre=metadata["arrendador_nombre"],
                arrendatario_nombre=metadata["arrendatario_nombre"],
                propietario_nombre=metadata["propietario_nombre"],
                contribuyente_rfc=metadata["contribuyente_rfc"],
                fecha_emision=metadata["fecha_emision"],
                fecha_vencimiento=metadata["fecha_vencimiento"],
                es_vigente=metadata["es_vigente"],
                autoridad_emisora=metadata["autoridad_emisora"],
                folder_path=folder_path,
                sharepoint_url=web_url,
                fecha_procesamiento_iso=now_iso,
                chunk_id=i,
                total_chunks=total_chunks,
            )
            for i in range(total_chunks)
        ]
        full_texts = [h + c for h, c in zip(headers, chunks)]

        vectors = embed_batch(full_texts)

        docs = []
        for i, (text, vector) in enumerate(zip(full_texts, vectors)):
            docs.append({
                "id": f"{parent_doc_id}__{i:04d}",
                "parent_document_id": parent_doc_id,
                "content_hash": content_hash,
                "chunk_id": i,
                "total_chunks": total_chunks,
                "content": text,
                "content_vector": vector,
                "nombre_archivo": name,
                "sharepoint_url": web_url,
                "folder_path": folder_path,
                "sp_site_id": payload.get("site_id", ""),
                "sp_list_id": "",
                "sp_list_item_id": "",
                "doc_type": metadata["doc_type"],
                "inmueble_codigos": metadata["inmueble_codigos"],
                "inmueble_codigo_principal": metadata["inmueble_codigo_principal"],
                "arrendador_nombre": metadata["arrendador_nombre"],
                "arrendatario_nombre": metadata["arrendatario_nombre"],
                "propietario_nombre": metadata["propietario_nombre"],
                "contribuyente_rfc": metadata["contribuyente_rfc"],
                "fecha_emision": metadata["fecha_emision"],
                "fecha_vencimiento": metadata["fecha_vencimiento"],
                "es_vigente": metadata["es_vigente"],
                "autoridad_emisora": metadata["autoridad_emisora"],
                "extraction_confidence": metadata["extraction_confidence"],
                "extraction_notes": metadata["extraction_notes"],
                "fecha_procesamiento": now_iso,
            })

        ok, failed, errors = search_client.upsert_documents(docs, target_index)
        if errors:
            _log("error", "upsert_search_errors",
                 correlation_id=correlation_id, errors=errors[:3])
            raise RuntimeError(f"Search upsert had {failed} failures")

        table_storage.upsert_item_index(
            drive_id=drive_id,
            drive_item_id=drive_item_id,
            content_hash=content_hash,
            name=name,
            folder_path=folder_path,
            parent_document_id=parent_doc_id,
            total_chunks=total_chunks,
            last_modified_utc=payload.get("last_modified_utc", ""),
        )
        _log("info", "upsert_done",
             correlation_id=correlation_id, drive_item_id=drive_item_id,
             chunks=ok, content_hash=content_hash, index=target_index)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ── rename ────────────────────────────────────────────────────────────────────

def handle_rename(payload: dict, correlation_id: str) -> None:
    """EC-03: rename → patch nombre_archivo + sharepoint_url en todos los chunks."""
    drive_id = payload["drive_id"]
    drive_item_id = payload["drive_item_id"]
    existing = table_storage.get_item_index(drive_id, drive_item_id)
    if not existing:
        _log("warning", "rename_no_index_entry",
             correlation_id=correlation_id, drive_item_id=drive_item_id)
        return

    content_hash = existing["content_hash"]
    new_name = payload["new_name"]
    new_web_url = payload.get("new_web_url", "")

    ok, failed = search_client.patch_document_fields(
        content_hash,
        {"nombre_archivo": new_name, "sharepoint_url": new_web_url},
    )
    table_storage.upsert_item_index(
        drive_id=drive_id,
        drive_item_id=drive_item_id,
        content_hash=content_hash,
        name=new_name,
        folder_path=existing.get("folder_path", ""),
        parent_document_id=existing.get("parent_document_id", ""),
        total_chunks=existing.get("total_chunks", 0),
        last_modified_utc=existing.get("last_modified_utc", ""),
    )
    _log("info", "rename_done",
         correlation_id=correlation_id, drive_item_id=drive_item_id,
         patched=ok, new_name=new_name)


# ── move ──────────────────────────────────────────────────────────────────────

def handle_move(payload: dict, correlation_id: str) -> None:
    """EC-04: move → patch folder_path en todos los chunks."""
    drive_id = payload["drive_id"]
    drive_item_id = payload["drive_item_id"]
    existing = table_storage.get_item_index(drive_id, drive_item_id)
    if not existing:
        _log("warning", "move_no_index_entry",
             correlation_id=correlation_id, drive_item_id=drive_item_id)
        return

    content_hash = existing["content_hash"]
    new_folder_path = payload.get("new_folder_path", "")

    ok, failed = search_client.patch_document_fields(
        content_hash, {"folder_path": new_folder_path},
    )
    table_storage.upsert_item_index(
        drive_id=drive_id,
        drive_item_id=drive_item_id,
        content_hash=content_hash,
        name=existing.get("name", ""),
        folder_path=new_folder_path,
        parent_document_id=existing.get("parent_document_id", ""),
        total_chunks=existing.get("total_chunks", 0),
        last_modified_utc=existing.get("last_modified_utc", ""),
    )
    _log("info", "move_done",
         correlation_id=correlation_id, drive_item_id=drive_item_id,
         patched=ok, new_path=new_folder_path)


# ── delete ────────────────────────────────────────────────────────────────────

def handle_delete(payload: dict, correlation_id: str) -> None:
    """EC-06: delete → borra chunks por content_hash + limpia itemsindex.

    Usa content_hash (siempre poblado en todos los chunks), no sp_list_item_id
    (que estaba vacío en el pipeline viejo y causaba el bug de chunks huérfanos).
    """
    drive_id = payload["drive_id"]
    drive_item_id = payload["drive_item_id"]
    existing = table_storage.get_item_index(drive_id, drive_item_id)
    if not existing:
        _log("info", "delete_no_index_entry",
             correlation_id=correlation_id, drive_item_id=drive_item_id)
        return

    content_hash = existing["content_hash"]
    ok, failed = search_client.delete_by_content_hash(content_hash)
    table_storage.delete_item_index(drive_id, drive_item_id)
    _log("info", "delete_done",
         correlation_id=correlation_id, drive_item_id=drive_item_id,
         deleted=ok, content_hash=content_hash)


# ── folder_rename ─────────────────────────────────────────────────────────────

def handle_folder_rename(payload: dict, correlation_id: str) -> None:
    """EC-05: folder rename → encola move por cada hijo conocido en itemsindex."""
    drive_id = payload["drive_id"]
    old_path = payload["old_path"]
    new_path = payload["new_path"]

    descendants = table_storage.list_descendant_items(drive_id, old_path)
    count = 0
    for d in descendants:
        updated_path = new_path + d.get("folder_path", old_path)[len(old_path):]
        queue_storage.enqueue_move(
            drive_id=drive_id,
            drive_item_id=d["RowKey"],
            new_parent_folder_id=d.get("PartitionKey", ""),
            new_folder_path=updated_path,
            correlation_id=correlation_id,
        )
        count += 1
    _log("info", "folder_rename_dispatched",
         correlation_id=correlation_id,
         old_path=old_path, new_path=new_path, children=count)
