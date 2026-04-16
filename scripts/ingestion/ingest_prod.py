"""
Fase 4B — Ingesta completa de los 38 docs únicos al índice `roca-contracts-v1`.

Diferencias vs smoke_ingest.py:
- Usa el índice de producción con vectorizer integrado
- Lee `_sharepoint_metadata.json` para `sharepoint_url` REAL (no placeholder)
- Procesa los 38 canonicals del dedup map (no una lista hardcoded de 5)
- Pre-computa embeddings (a pesar del vectorizer integrado del índice, el upload
  requiere el vector ya calculado — el vectorizer del índice es para queries, no ingesta)
- Incluye todos los campos de Capa 1 y Capa 2 basados en discovery JSONs
- Campos de security trimming (group_ids, user_ids) quedan vacíos — Fase 5 los poblará
- Versionado inicial: version_number=1, is_latest_version=true para todos

Idempotente: re-ejecutable (merge_or_upload_documents).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

SEARCH_ENDPOINT = "https://srch-roca-copilot-prod.search.windows.net"
SEARCH_SERVICE_NAME = "srch-roca-copilot-prod"
SEARCH_RG = "rg-roca-copilot-prod"
INDEX_NAME = "roca-contracts-v1"

AZURE_OPENAI_ENDPOINT = "https://rocadesarrollo-resource.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2024-10-21"
EMBED_DEPLOYMENT = "text-embedding-3-small"
EMBED_DIM = 1536
AOAI_ACCOUNT_NAME = "rocadesarrollo-resource"
AOAI_ACCOUNT_RG = "rg-admin.copilot-9203"

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
OCR_DIR = SAMPLE_DIR / "ocr_raw"
DISCOVERY_DIR = SAMPLE_DIR / "discovery"
METADATA_PATH = SAMPLE_DIR / "_sharepoint_metadata.json"
DEDUP_MAP_PATH = SAMPLE_DIR / "_content_hash_dedup.json"

CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200
MAX_CHUNKS_PER_DOC = 60  # cap para el contrato grande y título de propiedad (464 pages)
EMBED_BATCH_SIZE = 16


# --- Auth ---


def get_search_admin_key() -> str:
    env_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    if env_key and not env_key.startswith("__"):
        return env_key
    return subprocess.check_output(
        [
            "az","search","admin-key","show",
            "--service-name",SEARCH_SERVICE_NAME,
            "--resource-group",SEARCH_RG,
            "--query","primaryKey","-o","tsv",
        ], text=True,
    ).strip()


def get_aoai_key() -> str:
    return subprocess.check_output(
        [
            "az","cognitiveservices","account","keys","list",
            "--name",AOAI_ACCOUNT_NAME,
            "--resource-group",AOAI_ACCOUNT_RG,
            "--query","key1","-o","tsv",
        ], text=True,
    ).strip()


# --- Chunking ---


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


def build_metadata_header(
    *,
    nombre_archivo: str,
    doc_type: str,
    inmueble_codigos: list[str],
    arrendador_nombre: str | None,
    arrendatario_nombre: str | None,
    propietario_nombre: str | None,
    contribuyente_rfc: str | None,
    fecha_emision: str | None,
    fecha_vencimiento: str | None,
    es_vigente: bool | None,
    autoridad_emisora: str | None,
    folder_path: str,
    sharepoint_url: str,
    fecha_procesamiento_iso: str,
    chunk_id: int,
    total_chunks: int,
) -> str:
    """Prepend metadata structured block al content para que el modelo lo lea como texto.

    Fix de Fase 4B 2026-04-15: el tool azure_ai_search de Foundry solo expone el campo
    `content` al modelo por default, NO los demás campos tipados. Al meter los metadata
    en el content, el modelo los ve y los respeta (cita URLs reales, respeta es_vigente,
    etc.) en lugar de alucinar o extraer del texto OCR crudo.

    Fix 2 (2026-04-15 post-smoke): agregar `fecha_procesamiento` al header como referencia
    temporal "aproximadamente hoy" sin hardcoding. El agente usa este campo como proxy de
    la fecha actual para calcular vigencia dinámicamente. Cuando Fase 5 re-ingesta los
    docs periódicamente, esta fecha se actualiza automáticamente.

    Fix 3 (2026-04-15 post-smoke): cuando `es_vigente is None` (sin fecha_vencimiento
    explícita), el header lo marca como "DESCONOCIDO" con aviso de que el agente debe
    calcular manualmente si el texto OCR menciona vigencia relativa (ej: "VIGENCIA 36
    meses"), o advertir al usuario si no puede.
    """

    def _fmt(v):
        if v is None or v == "" or v == []:
            return "n/a"
        return str(v)

    # ISO fecha legible (YYYY-MM-DD) para las comparaciones temporales del modelo
    fecha_proc_short = fecha_procesamiento_iso[:10] if fecha_procesamiento_iso else "desconocida"

    vigente_str = (
        "DESCONOCIDO — el documento NO tiene fecha_vencimiento explícita en los metadatos. "
        "Si el texto OCR menciona vigencia relativa (ej: 'VIGENCIA 730 DIAS', 'válido por 36 meses'), "
        "calcula la fecha de vencimiento sumando al fecha_emision y compara contra fecha_procesamiento. "
        "Si no puedes calcularla, ADVIERTE al usuario que es necesario verificar manualmente."
    )
    if es_vigente is True:
        vigente_str = (
            f"true (vigente al momento de la ingesta — vencimiento: {fecha_vencimiento or 'sin fecha explícita'}, "
            f"calculado contra fecha_procesamiento {fecha_proc_short})"
        )
    elif es_vigente is False:
        vigente_str = (
            f"false (VENCIDA/NO VIGENTE — venció: {fecha_vencimiento or 'fecha desconocida'}, "
            f"calculado contra fecha_procesamiento {fecha_proc_short}). "
            f"NO reclasificar como vigente bajo ninguna circunstancia."
        )

    codigos_str = ", ".join(inmueble_codigos) if inmueble_codigos else "n/a"

    header = (
        "[METADATOS ESTRUCTURADOS DEL DOCUMENTO]\n"
        f"archivo: {_fmt(nombre_archivo)}\n"
        f"tipo_documento: {_fmt(doc_type)}\n"
        f"inmuebles_codigos: {codigos_str}\n"
        f"arrendador: {_fmt(arrendador_nombre)}\n"
        f"arrendatario: {_fmt(arrendatario_nombre)}\n"
        f"propietario: {_fmt(propietario_nombre)}\n"
        f"contribuyente_rfc: {_fmt(contribuyente_rfc)}\n"
        f"fecha_emision: {_fmt(fecha_emision)}\n"
        f"fecha_vencimiento: {_fmt(fecha_vencimiento)}\n"
        f"es_vigente: {vigente_str}\n"
        f"fecha_procesamiento: {fecha_proc_short} (⚠ esta es la referencia temporal 'aproximadamente hoy' — úsala para calcular vigencia contra las fechas del documento. Puede estar desactualizada por días o semanas.)\n"
        f"autoridad_emisora: {_fmt(autoridad_emisora)}\n"
        f"folder_sharepoint: {_fmt(folder_path)}\n"
        f"sharepoint_url: {_fmt(sharepoint_url)}\n"
        "[FIN METADATOS]\n\n"
        f"[CONTENIDO DEL DOCUMENTO — chunk {chunk_id + 1} de {total_chunks}]\n"
    )
    return header


# --- Metadata parsing ---


def _normalize_date(s: str | None) -> str | None:
    """Normaliza a Edm.DateTimeOffset (ISO con TZ). Rechaza placeholders del modelo
    como '2021-__-__' que no son fechas válidas."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    # Rechazar placeholders del modelo (partes faltantes con _, X, ?)
    if "_" in s or "?" in s:
        return None
    # Rechazar si contiene X/XX/XXXX en posiciones de fecha (pero permitir X si es parte del año)
    import re
    if re.search(r"\dX|X\d|XX", s.upper()):
        return None
    try:
        dt_str = s
        if "T" not in dt_str:
            dt_str = dt_str + "T00:00:00"
        if not dt_str.endswith("Z") and "+" not in dt_str[10:]:
            dt_str = dt_str + "Z"
        # Validar con fromisoformat — si no parsea, retornar None
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt_str
    except Exception:
        return None


def _compute_end_from_duration(start_iso: str | None, duracion_texto: str | None) -> str | None:
    """Calcula fecha_fin sumando una duración relativa (ej: '36 meses', '730 días', '2 años')
    a una fecha de inicio. Fix 2026-04-15: gpt-4.1-mini extrae 'duracion_texto' pero no hace
    la aritmética, así que la hacemos en código.

    Retorna ISO string o None si no se puede calcular.
    """
    import re

    if not start_iso or not duracion_texto:
        return None
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except Exception:
        return None

    # Normalizar texto
    text = duracion_texto.lower().strip()
    # Reemplazar palabras de números por dígitos (casos comunes)
    word_to_num = {
        "uno": "1", "un": "1", "una": "1",
        "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5",
        "seis": "6", "siete": "7", "ocho": "8", "nueve": "9", "diez": "10",
        "doce": "12", "dieciocho": "18", "veinte": "20", "treinta": "30",
        "treinta y seis": "36", "cuarenta y ocho": "48", "setenta y dos": "72",
    }
    for word, num in word_to_num.items():
        text = re.sub(rf"\b{word}\b", num, text)

    m = re.search(r"(\d+)\s*(d[ií]as?|mes(?:es)?|a[nñ]os?|semanas?)", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)

    try:
        if unit.startswith("d"):
            end = start + timedelta(days=n)
        elif unit.startswith("mes"):
            # Suma de meses manual (sin dateutil)
            month0 = start.month + n
            year = start.year + (month0 - 1) // 12
            month = ((month0 - 1) % 12) + 1
            is_leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
            days_in_month = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
            day = min(start.day, days_in_month)
            end = start.replace(year=year, month=month, day=day)
        elif unit.startswith("a"):
            is_leap = (start.year + n) % 4 == 0 and ((start.year + n) % 100 != 0 or (start.year + n) % 400 == 0)
            # manejar 29 feb en años no bisiestos
            day = start.day
            if start.month == 2 and start.day == 29 and not is_leap:
                day = 28
            end = start.replace(year=start.year + n, day=day)
        elif unit.startswith("sem"):
            end = start + timedelta(weeks=n)
        else:
            return None
    except Exception:
        return None

    return end.strftime("%Y-%m-%dT%H:%M:%SZ")


# normalización del doc_type al enum del schema
DOC_TYPE_NORMALIZE = {
    "contrato_arrendamiento": "contrato_arrendamiento",
    "contrato_compraventa": "contrato_compraventa",
    "contrato_desarrollo_inmobiliario": "contrato_desarrollo_inmobiliario",
    "licencia_construccion": "licencia_construccion",
    "constancia_situacion_fiscal": "constancia_situacion_fiscal",
    "constancia_uso_suelo": "constancia_uso_suelo",
    "constancia_curp": "constancia_curp",
    "plano_arquitectonico": "plano_arquitectonico",
    "estudio_ambiental": "estudio_ambiental",
    "estudio_geotecnico": "estudio_geotecnico",
    "poder_legal": "poder_legal",
    "escritura_publica": "escritura_publica",
    "escritura_publica_acta_asamblea": "escritura_publica",
    "acta_asamblea": "acta_asamblea",
    "factura_electronica": "factura_electronica",
    "recibo_servicio": "recibo_servicio",
    "estados_financieros_auditados": "estados_financieros_auditados",
    "garantia_corporativa": "garantia_corporativa",
    "poliza_seguro": "poliza_seguro",
    "titulo_propiedad": "titulo_propiedad",
}


def extract_metadata(discovery: dict) -> dict:
    model_output = discovery.get("model_output") or {}

    raw_type = (model_output.get("tipo_documento") or "otro").lower().strip().replace(" ", "_")
    doc_type = DOC_TYPE_NORMALIZE.get(raw_type, "otro")

    codigos = model_output.get("codigos_inmueble") or []
    if not isinstance(codigos, list):
        codigos = []
    codigos_clean = [str(c).strip()[:200] for c in codigos if c and str(c).strip()]
    codigo_principal = codigos_clean[0] if codigos_clean else None

    entidades = model_output.get("entidades_clave") or []
    arrendador = arrendatario = propietario = contribuyente_rfc = None
    for e in entidades if isinstance(entidades, list) else []:
        if not isinstance(e, dict):
            continue
        rol = (e.get("rol") or "").lower()
        nombre = (e.get("nombre") or "").strip()[:500]
        rfc_val = (e.get("rfc") or "")
        rfc = str(rfc_val).upper().replace(" ", "").strip() if rfc_val else None
        if "arrendador" in rol and not arrendador and nombre:
            arrendador = nombre
        if ("arrendatario" in rol or "inquilino" in rol) and not arrendatario and nombre:
            arrendatario = nombre
        if "propietario" in rol and not propietario and nombre:
            propietario = nombre
        if ("contribuyente" in rol or "persona moral" in rol) and rfc and not contribuyente_rfc:
            contribuyente_rfc = rfc

    vigencia = model_output.get("vigencia") or {}
    fecha_inicio = vigencia.get("inicio_iso") if isinstance(vigencia, dict) else None
    fecha_fin = vigencia.get("fin_iso") if isinstance(vigencia, dict) else None
    duracion_texto = vigencia.get("duracion_texto") if isinstance(vigencia, dict) else None

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
        if not fecha_emision:
            for f in fechas:
                if isinstance(f, dict) and f.get("fecha_iso"):
                    fecha_emision = f["fecha_iso"]
                    break

    if fecha_inicio and not fecha_emision:
        fecha_emision = fecha_inicio

    # Fix 2026-04-15 post-smoke: si el discovery NO calculó fecha_fin pero sí dio duracion_texto
    # + una fecha de referencia (inicio o emisión), calcularla en código. El modelo reconoce "36
    # meses" pero no hace la aritmética confiablemente.
    if not fecha_fin and duracion_texto:
        ref_start = fecha_inicio or fecha_emision
        calculated_end = _compute_end_from_duration(ref_start, duracion_texto)
        if calculated_end:
            fecha_fin = calculated_end

    # Lógica de vigencia (fix 2026-04-15 post-smoke):
    # - Solo true/false cuando hay `fecha_vencimiento` explícita que podamos comparar.
    # - None (desconocido) cuando no hay fecha_vencimiento — NUNCA asumir vigente.
    # - El agente maneja el caso None interpretando `fecha_procesamiento` vs `fecha_emision`
    #   en el metadata header, y aplicando reglas estrictas.
    es_vigente = None
    if fecha_fin:
        try:
            fin_dt = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            if fin_dt.tzinfo is None:
                fin_dt = fin_dt.replace(tzinfo=timezone.utc)
            es_vigente = fin_dt > datetime.now(timezone.utc)
        except Exception:
            es_vigente = None

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
        "extraction_notes": (model_output.get("notas") or "")[:4000],
    }


def parent_id_from_hash(content_hash: str, version: int = 1) -> str:
    return f"doc_{content_hash[:16]}_v{version}"


# --- Embeddings ---


def embed_batch(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
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


# --- Main ---


def main() -> int:
    print(f"Fase 4B — Ingesta completa al índice '{INDEX_NAME}'")

    # Cargar todos los insumos
    dedup_info = json.loads(DEDUP_MAP_PATH.read_text())
    canonical_by_stem = dedup_info["canonical_by_stem"]
    by_hash = dedup_info["by_hash"]
    stem_to_hash = dedup_info["stem_to_hash"]

    sp_meta = json.loads(METADATA_PATH.read_text())
    print(f"  canonicals: {len(set(canonical_by_stem.values()))}")
    print(f"  sp_metadata entries: {len(sp_meta)}")

    # Clientes
    search = SearchClient(
        endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=AzureKeyCredential(get_search_admin_key())
    )
    aoai = AzureOpenAI(
        api_key=get_aoai_key(),
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )

    all_docs: list[dict] = []
    total_chunks = 0
    processed_canonicals = set()

    # Iterar por los canonicals (no duplicados)
    canonicals = sorted(set(canonical_by_stem.values()))
    print(f"\n  Procesando {len(canonicals)} docs canónicos...")

    for i, stem in enumerate(canonicals, start=1):
        ocr_path = OCR_DIR / f"{stem}.json"
        disc_path = DISCOVERY_DIR / f"{stem}_discovery.json"

        if not ocr_path.exists():
            print(f"  [{i}/{len(canonicals)}] [skip] OCR missing: {stem[:60]}")
            continue
        if not disc_path.exists():
            print(f"  [{i}/{len(canonicals)}] [skip] discovery missing: {stem[:60]}")
            continue

        sp = sp_meta.get(stem)
        if not sp:
            print(f"  [{i}/{len(canonicals)}] [skip] sharepoint metadata missing: {stem[:60]}")
            continue

        ocr = json.loads(ocr_path.read_text())
        discovery = json.loads(disc_path.read_text())

        content = ocr.get("content") or ""
        content_hash = sp.get("contentHash") or stem_to_hash.get(stem) or ""
        parent_id = parent_id_from_hash(content_hash)

        meta = extract_metadata(discovery)

        # alternative_urls: todas las demás copias físicas del mismo hash
        alternative_urls = []
        group_stems = by_hash.get(content_hash, [])
        for g in group_stems:
            if g == stem:
                continue
            g_sp = sp_meta.get(g)
            if g_sp and g_sp.get("webUrl"):
                alternative_urls.append(g_sp["webUrl"])

        raw_chunks = chunk_text(content)
        if len(raw_chunks) > MAX_CHUNKS_PER_DOC:
            print(f"  [{i}/{len(canonicals)}] chars={len(content)} chunks={len(raw_chunks)} → CAP a {MAX_CHUNKS_PER_DOC}")
            raw_chunks = raw_chunks[:MAX_CHUNKS_PER_DOC]

        site_name = sp.get("siteName", "unknown")
        folder_path = (sp.get("relPath") or "").replace("\\", "/")
        nombre_archivo = sp.get("name", "")
        doc_title = nombre_archivo.rsplit(".", 1)[0] if nombre_archivo else stem[:200]
        sharepoint_url = sp.get("webUrl", "")

        print(
            f"  [{i}/{len(canonicals)}] {doc_title[:50]} "
            f"({meta['doc_type']}, {len(raw_chunks)} chunks, alts={len(alternative_urls)})"
        )

        # fecha_procesamiento es la referencia temporal "aproximadamente hoy" que ve el modelo
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        extracted_metadata_str = json.dumps(discovery.get("model_output") or {}, ensure_ascii=False)

        # Prepend metadata header a cada chunk para que el modelo lo lea como texto
        chunks = []
        for cid, raw in enumerate(raw_chunks):
            header = build_metadata_header(
                nombre_archivo=nombre_archivo,
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
                sharepoint_url=sharepoint_url,
                fecha_procesamiento_iso=now_iso,
                chunk_id=cid,
                total_chunks=len(raw_chunks),
            )
            chunks.append(header + raw)

        # Embed los chunks (con metadata header incluido)
        vectors = embed_batch(aoai, chunks)

        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            doc = {
                "id": f"{parent_id}__{idx:04d}",
                "parent_document_id": parent_id,
                "content_hash": content_hash,
                "chunk_id": idx,
                "total_chunks": len(chunks),
                "content": chunk,
                "content_vector": vec,
                "sharepoint_url": sharepoint_url,
                "alternative_urls": alternative_urls,
                "nombre_archivo": nombre_archivo,
                "site_origen": site_name,
                "folder_path": folder_path,
                "fecha_procesamiento": now_iso,
                "group_ids": [],  # Fase 5 lo poblará
                "user_ids": [],
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
            all_docs.append(doc)

        total_chunks += len(chunks)
        processed_canonicals.add(stem)

    print(f"\n[upsert] {len(all_docs)} chunks en batches de 100...")
    success = 0
    failed = 0
    for i in range(0, len(all_docs), 100):
        batch = all_docs[i : i + 100]
        try:
            result = search.merge_or_upload_documents(documents=batch)
            ok = sum(1 for r in result if r.succeeded)
            success += ok
            print(f"  batch {i//100 + 1}: {ok}/{len(batch)} OK")
            for r in result:
                if not r.succeeded:
                    print(f"    ! {r.key}: {r.error_message}")
                    failed += 1
        except Exception as e:
            print(f"  batch {i//100 + 1} falló: {e}")
            failed += len(batch)

    print("\n=== Resumen Ingesta ===")
    print(f"  canonicals procesados: {len(processed_canonicals)}/{len(canonicals)}")
    print(f"  chunks totales:        {total_chunks}")
    print(f"  upsert OK:             {success}")
    print(f"  upsert fallidos:       {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
