"""bypass_ingest_one.py — indexa UN archivo de SharePoint sin pasar por Durable Functions.

Uso:
    python3 scripts/bypass_ingest_one.py "<substring del nombre>" "<site>"

Ejemplo:
    python3 scripts/bypass_ingest_one.py "258.154" "ROCAIA-INMUEBLESV2"

Requiere:
    - az login como admin.copilot@rocadesarrollos.com (o user con acceso al KV)
    - Módulos de function_app/shared/ en sys.path (los agrego al inicio)

Lo que hace:
    1. Busca el archivo en SharePoint vía Graph search
    2. Descarga, OCR, extrae metadata, vectoriza, upsert al índice
    3. Confirma que aparezca en AI Search
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# 1. Populate env vars from Function App settings
def _bootstrap_env():
    print("[0/7] Loading env from Function App app settings...")
    result = subprocess.run(
        ["az", "functionapp", "config", "appsettings", "list",
         "--name", "func-roca-copilot-sync",
         "--resource-group", "rg-roca-copilot-prod",
         "-o", "json"],
        capture_output=True, text=True, check=True,
    )
    settings = json.loads(result.stdout)
    needed = {
        "TARGET_INDEX_NAME", "SEARCH_ENDPOINT", "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION", "DISCOVERY_DEPLOYMENT", "EMBED_DEPLOYMENT",
        "DOC_INTEL_ENDPOINT", "KV_URL", "KV_SECRET_NAME", "SP_APP_ID",
        "SP_TENANT_ID", "SP_HOSTNAME", "STORAGE_ACCOUNT", "OCR_CONTAINER",
        "DLQ_QUEUE", "MAX_COMPLETION_TOKENS", "CHUNK_SIZE_CHARS",
        "CHUNK_OVERLAP_CHARS", "MAX_CHUNKS_PER_DOC",
    }
    for s in settings:
        if s["name"] in needed:
            os.environ[s["name"]] = s["value"]
    missing = needed - set(os.environ.keys())
    if missing:
        raise RuntimeError(f"Missing env: {missing}")

_bootstrap_env()

# 2. Make function_app/shared importable (usa deps de pip --user, no las linux de .python_packages)
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "function_app"))

import requests
from shared import (
    auth, config, docintel_client, embeddings, graph_client, ingestion,
    search_client,
)
from shared import acls as acls_mod
from shared.dates import now_iso
from shared.extraction import run_extraction


def find_item_in_sharepoint(site_name: str, substring: str) -> dict | None:
    """Busca un item en SharePoint por substring del nombre."""
    print(f"[1/7] Resolviendo site '{site_name}' y drive default...")
    site_id = graph_client.get_site_id(site_name)
    drive_id = graph_client.get_default_drive_id(site_id)
    print(f"      site_id={site_id[:40]}...")
    print(f"      drive_id={drive_id[:40]}...")

    print(f"[2/7] Buscando items con '{substring}' en el nombre...")
    # Si el substring incluye '/', lo tratamos como path al folder y listamos directo
    matches = []
    if "/" in substring:
        folder_path, name_hint = substring.rsplit("/", 1)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}:/children"
        r = requests.get(url, headers={"Authorization": f"Bearer {auth.get_graph_token()}"}, timeout=30)
        r.raise_for_status()
        for it in r.json().get("value", []):
            if name_hint in (it.get("name") or "") and (it.get("file") or {}).get("mimeType") == "application/pdf":
                matches.append(it)
    else:
        # List recursive (lento pero funciona sin conocer path)
        for item in graph_client.list_drive_items_recursive(drive_id, max_items=10000):
            name_s = item.get("name") or ""
            if substring in name_s and (item.get("file") or {}).get("mimeType") == "application/pdf":
                matches.append(item)
                if len(matches) >= 5:
                    break
    items = matches
    if not matches:
        print(f"      ✗ No se encontró ningún PDF con '{substring}'")
        return None
    item = matches[0]
    print(f"      ✓ Encontrado: {item['name']}")
    print(f"        item_id: {item['id'][:40]}...")
    print(f"        size:    {item.get('size',0):,} bytes")
    print(f"        webUrl:  {item.get('webUrl','')[:120]}")
    return {
        "site_name": site_name,
        "site_id": site_id,
        "drive_id": drive_id,
        "item": item,
    }


def process_item_like_activity(payload: dict) -> dict:
    """Replica process_item_activity pero como función standalone."""
    from azure.storage.blob import BlobClient
    import logging

    site_name = payload["site_name"]
    site_id = payload["site_id"]
    drive_id = payload["drive_id"]
    item = payload["item"]
    item_id = item["id"]

    name = item.get("name") or item_id
    web_url = item.get("webUrl") or ""
    parent_ref = item.get("parentReference") or {}
    folder_path = (parent_ref.get("path") or "").split("root:", 1)[-1].lstrip("/")

    print(f"[3/7] Descargando PDF desde SharePoint...")
    tmp_path, content_hash = graph_client.stream_download_to_temp(drive_id, item_id)
    print(f"      hash={content_hash[:16]}... tmp={tmp_path}")

    try:
        # Dedup check
        existing = search_client.find_by_content_hash(content_hash)
        if existing:
            print(f"      ✓ DEDUP HIT: ya existen {len(existing)} chunks con este hash")
            current_urls = set(existing[0].get("alternative_urls") or [])
            current_urls.discard(existing[0].get("sharepoint_url") or "")
            if web_url and web_url != existing[0].get("sharepoint_url") and web_url not in current_urls:
                current_urls.add(web_url)
                patches = [{"id": c["id"], "alternative_urls": sorted(current_urls)} for c in existing]
                search_client.get_search_client().merge_documents(documents=patches)
                print(f"      → alternative_urls actualizado con nueva URL")
            return {"status": "ok", "mode": "dedup_hit", "content_hash": content_hash, "chunks": len(existing)}

        print(f"[4/7] Extrayendo ACLs...")
        list_id = parent_ref.get("sharepointIds", {}).get("listId") or ""
        list_item_id = parent_ref.get("sharepointIds", {}).get("listItemUniqueId") or ""
        if not list_id or not list_item_id:
            full_item = graph_client.get_item(drive_id, item_id)
            sp_ids = full_item.get("sharepointIds") or {}
            list_id = sp_ids.get("listId") or list_id
            list_item_id = sp_ids.get("listItemUniqueId") or list_item_id
        group_ids, user_ids = [], []
        if list_id and list_item_id:
            group_ids, user_ids = acls_mod.extract_principals_for_item(
                site_id=site_id, list_id=list_id, list_item_id=list_item_id,
            )
        print(f"      groups={len(group_ids)}, users={len(user_ids)}")

        # Cache PDF to blob
        blob_name = f"sample_discovery/{content_hash}.pdf"
        blob = BlobClient(
            account_url=f"https://{config.STORAGE_ACCOUNT}.blob.core.windows.net",
            container_name=config.OCR_CONTAINER,
            blob_name=blob_name,
            credential=auth.get_mi_credential(),
        )
        try:
            with open(tmp_path, "rb") as f:
                blob.upload_blob(f, overwrite=True)
            print(f"      ✓ PDF cached a blob {blob_name}")
        except Exception as e:
            print(f"      ⚠ Cache a blob falló: {e} — continuando con bytes")

        print(f"[5/7] Document Intelligence OCR (puede tardar 1-5 min)...")
        ocr_result = None
        try:
            sas_url = auth.generate_blob_read_sas(blob_name)
            ocr_result = docintel_client.analyze_pdf_url(sas_url)
        except Exception as e:
            print(f"      ⚠ SAS path falló ({e}) — usando bytes path")
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            ocr_result = docintel_client.analyze_pdf_bytes(pdf_bytes)
        print(f"      ✓ OCR completado, {len(ocr_result.get('content',''))} chars")

        print(f"[6/7] Extracción de metadata + embeddings...")
        extraction_output = run_extraction(ocr_result) or {}
        meta = ingestion.extract_metadata(extraction_output)

        content = ocr_result.get("content") or ""
        raw_chunks = ingestion.chunk_text(content)
        if len(raw_chunks) > config.MAX_CHUNKS_PER_DOC:
            raw_chunks = raw_chunks[:config.MAX_CHUNKS_PER_DOC]

        processing_iso = now_iso()
        headers_then_chunks = []
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
            return {"status": "skipped", "reason": "empty content", "content_hash": content_hash}

        vectors = embeddings.embed_batch(headers_then_chunks)
        print(f"      ✓ {len(vectors)} embeddings generados")

        print(f"[7/7] Upsert a AI Search {config.TARGET_INDEX_NAME}...")
        parent_id = ingestion.parent_id_from_hash(content_hash)
        doc_title = name.rsplit(".", 1)[0] if name else content_hash[:16]
        extracted_metadata_str = json.dumps(extraction_output, ensure_ascii=False)

        docs = []
        for idx, (chunk, vec) in enumerate(zip(headers_then_chunks, vectors)):
            docs.append({
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
            })

        ok, failed, errors = search_client.upsert_documents(docs)
        print(f"      ✓ upsert: ok={ok}, failed={failed}")
        return {
            "status": "ok" if failed == 0 else "error",
            "mode": "full_ingest",
            "content_hash": content_hash,
            "name": name,
            "chunks": len(docs),
            "upsert_ok": ok,
            "upsert_failed": failed,
            "doc_type": meta["doc_type"],
            "inmueble_codigos": meta["inmueble_codigos"],
        }

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 bypass_ingest_one.py '<substring>' [site_name]")
        sys.exit(1)
    substring = sys.argv[1]
    site_name = sys.argv[2] if len(sys.argv) >= 3 else "ROCAIA-INMUEBLESV2"

    payload = find_item_in_sharepoint(site_name, substring)
    if not payload:
        sys.exit(1)
    result = process_item_like_activity(payload)
    print()
    print("=" * 60)
    print("RESULTADO:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
