"""Metadata extraction — gpt-4.1-mini call ported 1:1 from run_discovery.py.

Naming note (clarification from Fase 5.5 review): the function was
originally called `run_discovery` because it reused the same prompt that
F4A used to "discover" what metadata fields naturally emerged from the
ROCA dataset. At runtime in Fase 5, however, the prompt is FIXED and
validated — this module performs **extraction** of structured metadata
against the already-validated schema, not open-ended discovery per-item.
Renamed from discovery.py → extraction.py (2026-04-15 Fase 5.5) to avoid
confusion about per-item schema re-discovery, which is NOT happening.

D-9 resolution: uses gpt-4.1-mini (not gpt-5-mini which was removed from
the account). max_completion_tokens=4000 is sufficient because gpt-4.1 is
NOT a reasoning model and doesn't burn invisible reasoning tokens.
"""

from __future__ import annotations

import json

from . import aoai_client, config

MAX_CONTENT_CHARS = 120_000
MAX_TABLES_IN_PROMPT = 10

SYSTEM_PROMPT = (
    "Eres un analista experto en documentos legales, fiscales y técnicos de "
    "bienes raíces en México. Responde siempre en JSON válido sin markdown."
)

EXTRACTION_PROMPT = """Analiza este documento extraído por OCR. Identifica y regresa en JSON:

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
- `notas`: string corto con cualquier observación relevante

Responde EXCLUSIVAMENTE con JSON válido. No incluyas markdown ni explicación.
Si un campo no aplica o no está en el documento, usa null o [].
No inventes datos que no aparezcan en el texto.

=== TEXTO DEL DOCUMENTO (extraído por Azure Document Intelligence prebuilt-layout) ===

"""


def _summarize_table(table: dict) -> str:
    rows = table.get("rowCount", 0)
    cols = table.get("columnCount", 0)
    cells = table.get("cells", [])
    grid: list[list[str]] = [[""] * cols for _ in range(rows)]
    for c in cells:
        r = c.get("rowIndex", 0)
        k = c.get("columnIndex", 0)
        content = (c.get("content") or "").replace("\n", " ").strip()
        if 0 <= r < rows and 0 <= k < cols:
            grid[r][k] = content
    lines = [" | ".join(row) for row in grid if any(cell for cell in row)]
    return "\n".join(lines[:40])


def build_extraction_prompt_text(ocr: dict) -> str:
    content = ocr.get("content") or ""
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + "\n[... TRUNCADO POR LÍMITE DE TOKENS ...]"
    tables = ocr.get("tables") or []
    table_block = ""
    if tables:
        table_block = "\n\n=== TABLAS DETECTADAS ===\n"
        for i, t in enumerate(tables[:MAX_TABLES_IN_PROMPT], start=1):
            table_block += f"\n-- Tabla {i} (rows={t.get('rowCount')}, cols={t.get('columnCount')}) --\n"
            table_block += _summarize_table(t)
        if len(tables) > MAX_TABLES_IN_PROMPT:
            table_block += f"\n[... {len(tables) - MAX_TABLES_IN_PROMPT} tablas adicionales omitidas ...]"
    return EXTRACTION_PROMPT + content + table_block


def run_extraction(ocr: dict) -> dict | None:
    """Sends the OCR content through gpt-4.1-mini and returns the parsed
    JSON model_output (or None if the model failed or returned unparseable
    output). Mirrors the output shape of run_discovery.py from Fase 4A."""
    prompt = build_extraction_prompt_text(ocr)
    client = aoai_client.get_aoai_client()
    response = client.chat.completions.create(
        model=config.DISCOVERY_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=config.MAX_COMPLETION_TOKENS,
    )
    raw = response.choices[0].message.content or ""
    if not raw.strip():
        return None
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip("`").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None
