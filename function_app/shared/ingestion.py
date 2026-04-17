"""Ingestion helpers ported 1:1 from scripts/ingestion/ingest_prod.py.

Includes all F4B post-smoke fixes:
- build_metadata_header with fecha_procesamiento as temporal reference
- extract_metadata with proper es_vigente = None when unknown (no auto-true fallback)
- _normalize_date rejects malformed placeholders
- _compute_end_from_duration calculates fin_iso from duracion_texto
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from . import config
from .dates import compute_end_from_duration, normalize_date

# Catastral/folio identifiers: purely numeric or patterns like "002-247-009",
# "4084/2020", "F/1349". These are valid property identifiers but should never
# be chosen as inmueble_codigo_principal over a ROCA internal code (RA03, etc.).
_CATASTRAL_ONLY = re.compile(r'^[\d\s/\-,\.]+$')


# --- Chunking ---------------------------------------------------------------


def chunk_text(text: str) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    size = config.CHUNK_SIZE_CHARS
    overlap = config.CHUNK_OVERLAP_CHARS
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks


# --- Metadata header (prepended to each chunk's content) --------------------


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
    def _fmt(v):
        if v is None or v == "" or v == []:
            return "n/a"
        return str(v)

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

    return (
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


# --- Discovery JSON → typed metadata ----------------------------------------

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


def extract_metadata(model_output: dict | None) -> dict:
    """Takes the parsed JSON output of gpt-4.1-mini discovery and returns the
    typed metadata dict ready to be injected into a search document. Implements
    the F4B post-smoke es_vigente logic (None when unknown, never auto-true)."""
    model_output = model_output or {}

    raw_type = (model_output.get("tipo_documento") or "otro").lower().strip().replace(" ", "_")
    doc_type = DOC_TYPE_NORMALIZE.get(raw_type, "otro")

    codigos = model_output.get("codigos_inmueble") or []
    if not isinstance(codigos, list):
        codigos = []
    codigos_clean = [str(c).strip()[:200] for c in codigos if c and str(c).strip()]
    # Prefer ROCA internal codes (letters + digits) over catastral/folio numbers.
    # Sort: non-catastral codes first, catastral-only last.
    codigos_clean.sort(key=lambda c: 1 if _CATASTRAL_ONLY.match(c) else 0)
    codigo_principal = codigos_clean[0] if codigos_clean else None

    entidades = model_output.get("entidades_clave") or []
    arrendador = arrendatario = propietario = contribuyente_rfc = None
    for e in entidades if isinstance(entidades, list) else []:
        if not isinstance(e, dict):
            continue
        rol = (e.get("rol") or "").lower()
        nombre = (e.get("nombre") or "").strip()[:500]
        rfc_val = e.get("rfc") or ""
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

    if not fecha_fin and duracion_texto:
        ref_start = fecha_inicio or fecha_emision
        calculated_end = compute_end_from_duration(ref_start, duracion_texto)
        if calculated_end:
            fecha_fin = calculated_end

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
        "fecha_emision": normalize_date(fecha_emision),
        "fecha_vencimiento": normalize_date(fecha_fin),
        "es_vigente": es_vigente,
        "autoridad_emisora": model_output.get("autoridad_emisora") or None,
        "extraction_confidence": model_output.get("confianza") or "media",
        "extraction_notes": (model_output.get("notas") or "")[:4000],
    }


# --- Hashing + ids ----------------------------------------------------------


def md5_hash(data: bytes) -> str:
    h = hashlib.md5()
    h.update(data)
    return h.hexdigest()


def parent_id_from_hash(content_hash: str, version: int = 1) -> str:
    return f"doc_{content_hash[:16]}_v{version}"
