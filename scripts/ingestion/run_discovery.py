"""
Fase 4A.2b — Discovery prompt abierto con gpt-5-mini sobre los OCRs.

Por cada JSON en contratosdemo_real/ocr_raw/ extrae el texto (`content` field) y
un resumen estructurado de tables, y se lo manda a gpt-5-mini con un prompt
abierto pidiendo metadata en JSON. El objetivo NO es extraer con schema fijo — es
descubrir qué campos emergen naturalmente del dataset real.

Guarda cada respuesta en contratosdemo_real/discovery/{stem}_discovery.json junto
con el raw JSON devuelto por el modelo y los counts de tokens. Idempotente.

Gotchas críticos (ver memorias `feedback_gpt5_reasoning_tokens.md`):
- gpt-5-mini es reasoning model → `max_completion_tokens: 4000` para dejar espacio
  al overhead de reasoning tokens (200-500 invisibles antes del output).
- Con valores <500 el output queda vacío.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from openai import AzureOpenAI

# --- Constants ---------------------------------------------------------------

AZURE_OPENAI_ENDPOINT = "https://rocadesarrollo-resource.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2024-10-21"
# **2026-04-15 post-smoke**: gpt-5-mini fue eliminado del account cuando desplegamos gpt-4o-mini
# y gpt-4.1-mini (conflicto de capacity). Cambiamos a gpt-4.1-mini para discovery porque ya está
# desplegado, es más rápido (sin reasoning tokens invisibles), y es excelente para extracción
# estructurada. Fase 5 puede re-desplegar gpt-5-mini si se quiere, pero gpt-4.1-mini es buen default.
CHAT_DEPLOYMENT = "gpt-4.1-mini"

AOAI_ACCOUNT_NAME = "rocadesarrollo-resource"
AOAI_ACCOUNT_RG = "rg-admin.copilot-9203"

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
OCR_DIR = SAMPLE_DIR / "ocr_raw"
DISCOVERY_DIR = SAMPLE_DIR / "discovery"
DEDUP_MAP_PATH = SAMPLE_DIR / "_content_hash_dedup.json"  # trazabilidad del dedup

# límite de chars del content antes de truncar (aprox 4 chars por token → 100K tokens ≈ 400K chars)
MAX_CONTENT_CHARS = 120_000
MAX_TABLES_IN_PROMPT = 10

MAX_COMPLETION_TOKENS = 4000  # gpt-4.1-mini NO es reasoning model, 4000 es suficiente (vs gpt-5-mini que requería 12000)
SLEEP_BETWEEN_CALLS_S = 1.0  # rate limiting benigno

DISCOVERY_PROMPT = """Analiza este documento extraído por OCR. Identifica y regresa en JSON:

- `tipo_documento`: clasificación corta (ej: "contrato_arrendamiento", "licencia_construccion", "constancia_situacion_fiscal", "plano_arquitectonico", "estudio_ambiental", "poder_representante_legal"). Usa snake_case. Si no es claro, escribe "desconocido".
- `entidades_clave`: lista de objetos `{nombre, rol, rfc?, domicilio?}` de las personas o empresas mencionadas como partes (arrendador, arrendatario, propietario, contribuyente, contratista, autoridad, etc.)
- `fechas_importantes`: lista de objetos `{descripcion, fecha_iso, texto_literal}`. fecha_iso en formato YYYY-MM-DD si se puede deducir; si no, `null`. texto_literal es la cita tal como aparece en el doc.
- `codigos_inmueble`: lista de strings con cualquier código/identificador de propiedad o nave mencionado (ej: "RA03", "GU01-A", "RE05A", "FESWORLD", "NAVE-SC1"). Extrae todos los formatos que encuentres.
- `vigencia`: `{inicio_iso, fin_iso, duracion_texto}` si el documento declara un período (contratos, licencias, pólizas). Todos los campos pueden ser null.

  ⚠ IMPORTANTE sobre `vigencia.fin_iso`: si el documento expresa la vigencia de forma RELATIVA en lugar de una fecha explícita (ej: "VIGENCIA 730 DIAS", "válido por 36 meses", "vigente por 2 años", "vigencia de 1 año"), DEBES calcular la fecha exacta de vencimiento sumando el periodo declarado a la fecha de emisión/expedición del documento, y devolverla en `fin_iso` como YYYY-MM-DD. Guarda la expresión literal en `duracion_texto`. Ejemplos:
  - Doc dice: "Expedida el 20 de abril de 2023, vigencia 24 meses" → `inicio_iso: "2023-04-20"`, `fin_iso: "2025-04-20"`, `duracion_texto: "24 meses"`
  - Doc dice: "VIGENCIA 730 DIAS, fecha 04/10/2021" → `inicio_iso: "2021-10-04"`, `fin_iso: "2023-10-04"`, `duracion_texto: "730 días"`
  - Doc dice: "Vigente por 36 meses a partir del 15/08/2022" → `inicio_iso: "2022-08-15"`, `fin_iso: "2025-08-15"`, `duracion_texto: "36 meses"`

  Si el documento NO dice NADA sobre vigencia (ni relativa ni absoluta), deja `fin_iso: null`. NO inventes una fecha de vencimiento. Solo calcula si hay evidencia explícita del periodo en el texto.

- `autoridad_emisora`: string si aplica (para licencias, permisos, CSFs: ej "SAT", "Municipio de Ramos Arizpe", "SEMARNAT")
- `monto_principal`: objeto `{monto, moneda, concepto}` si el doc tiene una cifra monetaria principal (renta mensual, garantía, valor declarado)
- `metadata_extra`: objeto libre con cualquier otro campo que te parezca relevante y no encaje en los anteriores (ej: numero_escritura, numero_oficio, folio, referencia_catastral, superficie_m2, uso_suelo, clave_predial)
- `confianza`: string (`"alta"`, `"media"`, `"baja"`) sobre qué tan seguro estás de tu clasificación
- `notas`: string corto con cualquier observación relevante (ej: "documento ilegible en página 3", "es un anexo de contrato, no el contrato principal")

Responde EXCLUSIVAMENTE con JSON válido. No incluyas markdown ni explicación.
Si un campo no aplica o no está en el documento, usa null o [].
No inventes datos que no aparezcan en el texto.

=== TEXTO DEL DOCUMENTO (extraído por Azure Document Intelligence prebuilt-layout) ===

"""


# --- Dedup por hash ----------------------------------------------------------


def compute_pdf_hash(pdf_path: Path) -> str:
    h = hashlib.md5()
    with open(pdf_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_dedup_map(sample_dir: Path) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """Retorna (stem→canonical_stem, stem→hash, hash→[stems ordenados])."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    stem_to_hash: dict[str, str] = {}
    for p in sorted(sample_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() != ".pdf":
            continue
        h = compute_pdf_hash(p)
        stem_to_hash[p.stem] = h
        by_hash[h].append(p.stem)

    canonical: dict[str, str] = {}
    for h, stems in by_hash.items():
        # canonical = primer stem alfabéticamente (determinístico)
        stems.sort()
        for s in stems:
            canonical[s] = stems[0]

    return canonical, stem_to_hash, dict(by_hash)


# --- Auth --------------------------------------------------------------------


def get_aoai_key() -> str:
    env_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if env_key and not env_key.startswith("__"):
        return env_key
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


# --- OCR input preparation ---------------------------------------------------


def summarize_table(table: dict) -> str:
    """Aplana una tabla del Document Intelligence a texto tipo CSV corto."""
    rows = table.get("rowCount", 0)
    cols = table.get("columnCount", 0)
    cells = table.get("cells", [])
    # construir matriz
    grid: list[list[str]] = [[""] * cols for _ in range(rows)]
    for c in cells:
        r = c.get("rowIndex", 0)
        k = c.get("columnIndex", 0)
        content = (c.get("content") or "").replace("\n", " ").strip()
        if 0 <= r < rows and 0 <= k < cols:
            grid[r][k] = content
    lines = [" | ".join(row) for row in grid if any(cell for cell in row)]
    return "\n".join(lines[:40])  # max 40 rows per table en el prompt


def build_prompt_text(ocr: dict) -> tuple[str, dict]:
    """Construye el texto del prompt y métricas auxiliares."""
    content = ocr.get("content") or ""
    truncated = False
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + "\n[... TRUNCADO POR LÍMITE DE TOKENS ...]"
        truncated = True

    tables = ocr.get("tables") or []
    table_block = ""
    if tables:
        table_block = "\n\n=== TABLAS DETECTADAS ===\n"
        for i, t in enumerate(tables[:MAX_TABLES_IN_PROMPT], start=1):
            table_block += f"\n-- Tabla {i} (rows={t.get('rowCount')}, cols={t.get('columnCount')}) --\n"
            table_block += summarize_table(t)
        if len(tables) > MAX_TABLES_IN_PROMPT:
            table_block += f"\n[... {len(tables) - MAX_TABLES_IN_PROMPT} tablas adicionales omitidas ...]"

    full_prompt = DISCOVERY_PROMPT + content + table_block

    return full_prompt, {
        "content_chars": len(content),
        "content_truncated": truncated,
        "num_tables_included": min(len(tables), MAX_TABLES_IN_PROMPT),
        "num_tables_total": len(tables),
        "num_pages": len(ocr.get("pages", [])),
    }


# --- Main --------------------------------------------------------------------


def main() -> int:
    ocr_jsons = sorted(OCR_DIR.glob("*.json"))
    if not ocr_jsons:
        print(f"⚠ No hay JSONs en {OCR_DIR}", file=sys.stderr)
        return 1

    print(f"Fase 4A.2b — Discovery sobre {len(ocr_jsons)} OCR JSONs con gpt-5-mini")
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)

    # Dedup por hash: saltar copias no-canónicas del mismo archivo físico
    print("[dedup] Calculando content_hash de todos los PDFs...")
    canonical_map, stem_to_hash, by_hash = build_dedup_map(SAMPLE_DIR)
    unique_hashes = len(by_hash)
    dup_groups = sum(1 for stems in by_hash.values() if len(stems) > 1)
    print(f"  PDFs: {len(stem_to_hash)} → únicos por hash: {unique_hashes} ({dup_groups} grupos con duplicados)")

    # Persistir el mapa para trazabilidad (lo usa aggregate_discovery.py)
    DEDUP_MAP_PATH.write_text(
        json.dumps(
            {"canonical_by_stem": canonical_map, "stem_to_hash": stem_to_hash, "by_hash": by_hash},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    client = AzureOpenAI(
        api_key=get_aoai_key(),
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )

    processed = 0
    skipped = 0
    failed: list[str] = []
    empty_output: list[str] = []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_reasoning_tokens = 0

    dedup_skipped = 0
    for i, ocr_path in enumerate(ocr_jsons, start=1):
        stem = ocr_path.stem
        out_path = DISCOVERY_DIR / f"{stem}_discovery.json"

        # Dedup skip: si este stem es duplicado (hash apunta a otro canonical), saltar
        canonical = canonical_map.get(stem)
        if canonical and canonical != stem:
            print(f"  [{i}/{len(ocr_jsons)}] [skip-dup] {stem[:70]} → canonical: {canonical[:60]}")
            dedup_skipped += 1
            continue

        if out_path.exists():
            # verifica que no esté vacío por el gotcha de reasoning tokens
            try:
                existing = json.loads(out_path.read_text())
                if existing.get("model_output"):
                    print(f"  [{i}/{len(ocr_jsons)}] [skip] {stem}")
                    skipped += 1
                    continue
                else:
                    print(f"  [{i}/{len(ocr_jsons)}] [retry-empty] {stem}")
            except Exception:
                print(f"  [{i}/{len(ocr_jsons)}] [retry-corrupt] {stem}")

        try:
            ocr = json.loads(ocr_path.read_text())
        except Exception as e:
            print(f"      ! error leyendo OCR: {e}")
            failed.append(stem)
            continue

        prompt, meta = build_prompt_text(ocr)
        print(
            f"  [{i}/{len(ocr_jsons)}] [discover] {stem} "
            f"(chars={meta['content_chars']}, pages={meta['num_pages']}, "
            f"tables={meta['num_tables_total']}, truncated={meta['content_truncated']})"
        )

        try:
            response = client.chat.completions.create(
                model=CHAT_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un analista experto en documentos legales, fiscales y técnicos de bienes raíces en México. Responde siempre en JSON válido sin markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )
        except Exception as e:
            print(f"      ! llamada a gpt-5-mini falló: {e}")
            failed.append(stem)
            continue

        raw = response.choices[0].message.content or ""
        usage = response.usage.to_dict() if hasattr(response.usage, "to_dict") else dict(response.usage)

        total_prompt_tokens += usage.get("prompt_tokens", 0)
        total_completion_tokens += usage.get("completion_tokens", 0)
        reasoning = 0
        details = usage.get("completion_tokens_details") or {}
        if isinstance(details, dict):
            reasoning = details.get("reasoning_tokens", 0) or 0
        total_reasoning_tokens += reasoning

        # intenta parsear como JSON
        parsed = None
        parse_error = None
        if raw.strip():
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                # a veces el modelo mete markdown pese a la instrucción — sanitizamos
                stripped = raw.strip()
                if stripped.startswith("```"):
                    stripped = stripped.strip("`")
                    if stripped.lower().startswith("json"):
                        stripped = stripped[4:]
                    stripped = stripped.strip("`").strip()
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    parse_error = str(e)

        if not raw.strip():
            print(f"      ⚠ output vacío (reasoning={reasoning}, completion={usage.get('completion_tokens', 0)})")
            empty_output.append(stem)

        out_payload = {
            "source_pdf_stem": stem,
            "model": CHAT_DEPLOYMENT,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "ocr_meta": meta,
            "usage": usage,
            "reasoning_tokens": reasoning,
            "parse_error": parse_error,
            "model_output": parsed,
            "raw_output": raw,
        }
        out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2))

        processed += 1
        print(
            f"      ✓ prompt={usage.get('prompt_tokens', 0)} "
            f"completion={usage.get('completion_tokens', 0)} "
            f"reasoning={reasoning} "
            f"parsed={'OK' if parsed else ('ERR' if parse_error else 'EMPTY')}"
        )

        time.sleep(SLEEP_BETWEEN_CALLS_S)

    print("\n=== Resumen Discovery ===")
    print(f"  procesados:           {processed}")
    print(f"  skipped (ya existían):{skipped}")
    print(f"  skipped (duplicados): {dedup_skipped}")
    print(f"  fallidos:             {len(failed)}")
    print(f"  vacíos:               {len(empty_output)}")
    print(f"  tokens prompt     total: {total_prompt_tokens:,}")
    print(f"  tokens completion total: {total_completion_tokens:,}")
    print(f"    de los cuales reasoning: {total_reasoning_tokens:,}")

    if failed:
        for f in failed:
            print(f"    ! {f}")
    if empty_output:
        for f in empty_output:
            print(f"    ⚠ {f}")

    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
