"""
Smoke test (mini-Fase 4B) — ingesta 5 docs representativos al índice
`roca-contracts-smoke` usando los OCRs y discovery JSONs YA procesados.

Pipeline:
1. Para cada doc seleccionado, leer OCR JSON (`ocr_raw/{stem}.json`) y discovery
   JSON (`discovery/{stem}_discovery.json`).
2. Chunk simple por caracteres (~1000 chars con overlap 150) — suficiente para smoke.
3. Embeddings con text-embedding-3-small.
4. Upsert al índice con merge semantics.

Idempotente: si un chunk con mismo id existe, se sobrescribe.
NO descarga nada, NO llama Document Intelligence, NO llama gpt-5-mini para discovery.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

SEARCH_ENDPOINT = "https://srch-roca-copilot-prod.search.windows.net"
SEARCH_SERVICE_NAME = "srch-roca-copilot-prod"
SEARCH_RG = "rg-roca-copilot-prod"
INDEX_NAME = "roca-contracts-smoke"

AZURE_OPENAI_ENDPOINT = "https://rocadesarrollo-resource.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2024-10-21"
EMBED_DEPLOYMENT = "text-embedding-3-small"
EMBED_DIM = 1536
AOAI_ACCOUNT_NAME = "rocadesarrollo-resource"
AOAI_ACCOUNT_RG = "rg-admin.copilot-9203"

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
OCR_DIR = SAMPLE_DIR / "ocr_raw"
DISCOVERY_DIR = SAMPLE_DIR / "discovery"

CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200
MAX_CHUNKS_PER_DOC = 40  # smoke: cap para evitar docs monstruo como el título de propiedad de 464 páginas
EMBED_BATCH_SIZE = 16  # Azure OpenAI limita por tokens/request

# Los 5 docs representativos (stems sin .pdf) — cubren 5 tipos distintos
SMOKE_DOC_STEMS = [
    "ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Contratos__RA03_Contrato_v2_final",
    "ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_RE05A",
    "ROCA-IAInmuebles__33._Constancia_situacion_fiscal__MLD-_Constancia_Maquimex",
    "ROCA-IAInmuebles__65._Planos_arquitectonicos_As_built__100.-_ARQUITECTONICOS_PDF__RA03-FOAM-100-32_DESPLANTE_DE_MUROS_AS_BUILT",
    # Canonical del grupo 5 de duplicados (título de propiedad) — el de Principal es duplicado
    "ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ACTINVER_P03RA03_Juridico_TituloDePropiedad_05012026_2D07B6D6-3658-4953-9D53-44B4F173D4FE2026-01-20T11-14-10",
]


# --- Helpers -----------------------------------------------------------------


def get_search_admin_key() -> str:
    env_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    if env_key and not env_key.startswith("__"):
        return env_key
    return subprocess.check_output(
        [
            "az",
            "search",
            "admin-key",
            "show",
            "--service-name",
            SEARCH_SERVICE_NAME,
            "--resource-group",
            SEARCH_RG,
            "--query",
            "primaryKey",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()


def get_aoai_key() -> str:
    return subprocess.check_output(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--name",
            AOAI_ACCOUNT_NAME,
            "--resource-group",
            AOAI_ACCOUNT_RG,
            "--query",
            "key1",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()


def compute_hash(pdf_path: Path) -> str:
    h = hashlib.md5()
    with open(pdf_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chunk_text(text: str, size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks


# --- Metadata parsing from discovery -----------------------------------------


def extract_metadata_for_chunk(discovery: dict, ocr_meta: dict) -> dict:
    """Derive Capa 2 fields from the discovery output (already structured JSON)."""
    model_output = discovery.get("model_output") or {}

    doc_type = (model_output.get("tipo_documento") or "otro").lower().strip()
    # normaliza espacios
    doc_type = doc_type.replace(" ", "_")

    codigos = model_output.get("codigos_inmueble") or []
    if not isinstance(codigos, list):
        codigos = []
    codigos_clean = [str(c).strip() for c in codigos if c and str(c).strip()]
    codigo_principal = codigos_clean[0] if codigos_clean else None

    entidades = model_output.get("entidades_clave") or []
    arrendador = None
    arrendatario = None
    propietario = None
    contribuyente_rfc = None

    for e in entidades if isinstance(entidades, list) else []:
        if not isinstance(e, dict):
            continue
        rol = (e.get("rol") or "").lower()
        nombre = (e.get("nombre") or "").strip()
        rfc = (e.get("rfc") or "").upper().replace(" ", "").strip() or None
        if "arrendador" in rol and not arrendador:
            arrendador = nombre
        if ("arrendatario" in rol or "inquilino" in rol) and not arrendatario:
            arrendatario = nombre
        if "propietario" in rol and not propietario:
            propietario = nombre
        if ("contribuyente" in rol or "persona moral" in rol) and rfc and not contribuyente_rfc:
            contribuyente_rfc = rfc

    vigencia = model_output.get("vigencia") or {}
    fecha_inicio = None
    fecha_fin = None
    if isinstance(vigencia, dict):
        fecha_inicio = vigencia.get("inicio_iso")
        fecha_fin = vigencia.get("fin_iso")

    # fallback a fechas_importantes para fecha_emision
    fecha_emision = None
    fechas = model_output.get("fechas_importantes") or []
    if isinstance(fechas, list):
        for f in fechas:
            if not isinstance(f, dict):
                continue
            iso = f.get("fecha_iso")
            desc = (f.get("descripcion") or "").lower()
            if iso and ("emis" in desc or "firma" in desc or "expedic" in desc):
                fecha_emision = iso
                break
        if not fecha_emision and fechas:
            for f in fechas:
                if isinstance(f, dict) and f.get("fecha_iso"):
                    fecha_emision = f["fecha_iso"]
                    break

    if fecha_inicio and not fecha_emision:
        fecha_emision = fecha_inicio

    # es_vigente: si fecha_fin > today o fecha_fin es null y fecha_emision existe
    es_vigente = None
    if fecha_fin:
        try:
            fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            if fin_dt.tzinfo is None:
                fin_dt = fin_dt.replace(tzinfo=timezone.utc)
            es_vigente = fin_dt > datetime.now(timezone.utc)
        except Exception:
            es_vigente = None
    elif fecha_emision:
        es_vigente = True  # sin fecha de vencimiento => asumimos vigente

    return {
        "doc_type": doc_type,
        "inmueble_codigos": codigos_clean,
        "inmueble_codigo_principal": codigo_principal,
        "arrendador_nombre": arrendador,
        "arrendatario_nombre": arrendatario,
        "propietario_nombre": propietario,
        "contribuyente_rfc": contribuyente_rfc,
        "fecha_emision": _normalize_date(fecha_emision),
        "fecha_vencimiento": _normalize_date(fecha_fin),
        "es_vigente": es_vigente,
        "autoridad_emisora": (model_output.get("autoridad_emisora") or None),
        "extraction_confidence": (model_output.get("confianza") or "media"),
        "extraction_notes": (model_output.get("notas") or ""),
    }


def _normalize_date(s: str | None) -> str | None:
    """Convierte fecha ISO a formato Edm.DateTimeOffset (con timezone)."""
    if not s or not isinstance(s, str):
        return None
    try:
        if "T" not in s:
            s = s + "T00:00:00"
        if not s.endswith("Z") and "+" not in s[10:]:
            s = s + "Z"
        return s
    except Exception:
        return None


def derive_paths(stem: str) -> tuple[str, str, str, str]:
    """De stem {site}__{folder}__{...}__{filename} deriva site, folder, sharepoint_url placeholder, nombre_archivo."""
    parts = stem.split("__")
    site = parts[0] if parts else "unknown"
    folder = parts[1] if len(parts) > 1 else ""
    filename = parts[-1] if parts else stem
    # para smoke, construimos un URL placeholder (en Fase 5 viene de Graph API)
    folder_path = " / ".join(parts[1:-1]) if len(parts) > 2 else folder
    sharepoint_url = f"https://rocadesarrollos1.sharepoint.com/sites/{site}/{folder}/{filename}.pdf"
    return site, folder_path, sharepoint_url, f"{filename}.pdf"


# --- Embeddings --------------------------------------------------------------


def embed_batch(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed en sub-batches para respetar rate limit de Azure OpenAI."""
    import time

    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        sub = texts[i : i + EMBED_BATCH_SIZE]
        for attempt in range(3):
            try:
                response = client.embeddings.create(model=EMBED_DEPLOYMENT, input=sub)
                all_vectors.extend([d.embedding for d in response.data])
                break
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 10 * (attempt + 1)
                print(f"    [warn] embed retry {attempt+1}/3 tras {wait}s: {type(e).__name__}")
                time.sleep(wait)
    return all_vectors


# --- Main --------------------------------------------------------------------


def main() -> int:
    print(f"Smoke ingest — {len(SMOKE_DOC_STEMS)} docs al índice '{INDEX_NAME}'")

    # Clientes
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=AzureKeyCredential(get_search_admin_key())
    )
    aoai = AzureOpenAI(
        api_key=get_aoai_key(), api_version=AZURE_OPENAI_API_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT
    )

    all_docs: list[dict] = []
    total_chunks = 0

    for stem in SMOKE_DOC_STEMS:
        ocr_path = OCR_DIR / f"{stem}.json"
        disc_path = DISCOVERY_DIR / f"{stem}_discovery.json"
        pdf_path = SAMPLE_DIR / f"{stem}.pdf"
        if not pdf_path.exists():
            pdf_path = SAMPLE_DIR / f"{stem}.PDF"

        if not ocr_path.exists():
            print(f"  ! {stem}: OCR no existe, skip")
            continue
        if not disc_path.exists():
            print(f"  ! {stem}: discovery no existe, skip")
            continue
        if not pdf_path.exists():
            print(f"  ! {stem}: PDF no existe en disco, skip")
            continue

        print(f"\n[{stem[:70]}…]")

        ocr = json.loads(ocr_path.read_text())
        discovery = json.loads(disc_path.read_text())
        content = ocr.get("content") or ""
        content_hash = compute_hash(pdf_path)
        parent_id = f"doc_{content_hash[:16]}"

        meta = extract_metadata_for_chunk(discovery, ocr.get("_meta", {}))
        site, folder_path, sharepoint_url, nombre_archivo = derive_paths(stem)

        chunks = chunk_text(content)
        if len(chunks) > MAX_CHUNKS_PER_DOC:
            print(f"  chars={len(content)}  chunks={len(chunks)} → CAP a {MAX_CHUNKS_PER_DOC}")
            chunks = chunks[:MAX_CHUNKS_PER_DOC]
        print(f"  chars={len(content)}  chunks={len(chunks)}  doc_type={meta['doc_type']}  codigos={meta['inmueble_codigos'][:3]}")

        if not chunks:
            continue

        # Embed en batch
        print(f"  embedding {len(chunks)} chunks...")
        vectors = embed_batch(aoai, chunks)

        # Construir documentos del índice
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            doc = {
                "id": f"{parent_id}__{i:04d}",
                "parent_document_id": parent_id,
                "content_hash": content_hash,
                "chunk_id": i,
                "total_chunks": len(chunks),
                "content": chunk,
                "content_vector": vec,
                "sharepoint_url": sharepoint_url,
                "alternative_urls": [],
                "nombre_archivo": nombre_archivo,
                "site_origen": site,
                "folder_path": folder_path,
                "fecha_procesamiento": now_iso,
                "doc_type": meta["doc_type"],
                "inmueble_codigos": meta["inmueble_codigos"],
                "inmueble_codigo_principal": meta["inmueble_codigo_principal"],
                "doc_title": nombre_archivo.rsplit(".", 1)[0],
                "arrendador_nombre": meta["arrendador_nombre"],
                "arrendatario_nombre": meta["arrendatario_nombre"],
                "propietario_nombre": meta["propietario_nombre"],
                "contribuyente_rfc": meta["contribuyente_rfc"],
                "fecha_emision": meta["fecha_emision"],
                "fecha_vencimiento": meta["fecha_vencimiento"],
                "es_vigente": meta["es_vigente"],
                "autoridad_emisora": meta["autoridad_emisora"],
                "extraction_confidence": meta["extraction_confidence"],
                "extraction_notes": meta["extraction_notes"],
                "extracted_metadata": json.dumps(discovery.get("model_output") or {}, ensure_ascii=False),
            }
            all_docs.append(doc)

        total_chunks += len(chunks)

    print(f"\n[upsert] {len(all_docs)} chunks totales → índice...")
    if all_docs:
        # upsert en batches de 100
        for i in range(0, len(all_docs), 100):
            batch = all_docs[i : i + 100]
            result = search_client.merge_or_upload_documents(documents=batch)
            ok = sum(1 for r in result if r.succeeded)
            print(f"  batch {i//100 + 1}: {ok}/{len(batch)} OK")

    print("\n=== Resumen ===")
    print(f"  docs fuente: {len(SMOKE_DOC_STEMS)}")
    print(f"  chunks totales indexados: {total_chunks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
