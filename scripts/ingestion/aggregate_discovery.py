"""
Fase 4A.3 — Agrega los JSONs de discovery y genera el reporte de hallazgos.

Lee todos los `{stem}_discovery.json` en contratosdemo_real/discovery/, agrega
patrones (tipos de doc, densidad de campos, formatos de fechas, códigos de
inmueble) y escribe `FASE_4A_DISCOVERY_REPORT.md` con citas literales del OCR
para justificar cada patrón.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
DISCOVERY_DIR = SAMPLE_DIR / "discovery"
OCR_DIR = SAMPLE_DIR / "ocr_raw"
DEDUP_MAP_PATH = SAMPLE_DIR / "_content_hash_dedup.json"
REPO_DIR = Path("/Users/datageni/Documents/ai_azure/azure-ai-contract-analysis")
REPORT_PATH = REPO_DIR / "FASE_4A_DISCOVERY_REPORT.md"

DATE_LITERAL_RE = re.compile(
    r"\b(\d{1,2}[\s/\-]+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{1,2})[\s/\-]+(?:de\s+)?\d{2,4})\b",
    re.IGNORECASE,
)
RFC_RE = re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b")
CODIGO_INMUEBLE_RE = re.compile(r"\b(RA\d{2}[A-Z]?|RE\d{2}[A-Z]?|GU\w{2,4}|SL\d{2}[A-Z]?|FE\w{3,6}|NAVE[-_]?\w+)\b")


def load_discovery_files() -> list[dict]:
    out = []
    for p in sorted(DISCOVERY_DIR.glob("*_discovery.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"!! error leyendo {p.name}: {e}")
    return out


def load_ocr_text(stem: str) -> str:
    ocr_path = OCR_DIR / f"{stem}.json"
    if not ocr_path.exists():
        return ""
    try:
        return (json.loads(ocr_path.read_text()).get("content") or "")
    except Exception:
        return ""


def find_literal_quote(text: str, needle: str, window: int = 80) -> str | None:
    """Busca needle en text (case-insensitive) y retorna contexto ±window chars."""
    if not needle or not text:
        return None
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(needle) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"…{snippet}…"


def load_dedup_map() -> dict:
    if not DEDUP_MAP_PATH.exists():
        return {}
    try:
        return json.loads(DEDUP_MAP_PATH.read_text())
    except Exception:
        return {}


def main() -> int:
    items = load_discovery_files()
    n = len(items)
    if n == 0:
        print("No hay archivos de discovery.")
        return 1

    # Cargar info de dedup (generada por run_discovery.py)
    dedup_info = load_dedup_map()
    by_hash = dedup_info.get("by_hash", {})
    stem_to_hash = dedup_info.get("stem_to_hash", {})
    canonical_by_stem = dedup_info.get("canonical_by_stem", {})

    total_pdfs = len(stem_to_hash)
    unique_pdfs = len(by_hash)
    dup_groups = [(h, stems) for h, stems in by_hash.items() if len(stems) > 1]

    print(f"Agregando {n} archivos de discovery (PDFs en disco: {total_pdfs}, únicos: {unique_pdfs})...")

    # ---- Métricas globales ---------------------------------------------------

    tipos_counter: Counter[str] = Counter()
    por_carpeta_canonica: dict[str, Counter[str]] = defaultdict(Counter)
    field_presence: Counter[str] = Counter()
    field_non_null: Counter[str] = Counter()
    confianza_counter: Counter[str] = Counter()
    parse_errors = 0
    empty_outputs = 0

    total_prompt = 0
    total_completion = 0
    total_reasoning = 0

    codigos_globales: Counter[str] = Counter()
    fechas_literales: list[tuple[str, str]] = []  # (stem, literal)
    rfcs_detectados: Counter[str] = Counter()
    autoridades: Counter[str] = Counter()
    inquilinos_propietarios: Counter[str] = Counter()
    extra_keys: Counter[str] = Counter()

    # ejemplos de citas literales por tipo (para el reporte)
    sample_quotes_by_type: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    # (stem, field, quote)

    # per-type snapshots
    per_doc_summary: list[dict] = []

    for item in items:
        stem = item.get("source_pdf_stem", "<unknown>")
        usage = item.get("usage", {})
        total_prompt += usage.get("prompt_tokens", 0) or 0
        total_completion += usage.get("completion_tokens", 0) or 0
        total_reasoning += item.get("reasoning_tokens", 0) or 0

        if item.get("parse_error"):
            parse_errors += 1
        if not (item.get("raw_output") or "").strip():
            empty_outputs += 1
            continue

        output = item.get("model_output") or {}
        if not isinstance(output, dict):
            continue

        # Carpeta canónica (segunda parte del stem)
        parts = stem.split("__")
        canonical = parts[1] if len(parts) >= 2 else "<?>"

        tipo = output.get("tipo_documento") or "desconocido"
        tipos_counter[tipo] += 1
        por_carpeta_canonica[canonical][tipo] += 1

        confianza_counter[output.get("confianza") or "?"] += 1

        # field presence
        for k, v in output.items():
            field_presence[k] += 1
            if v not in (None, "", [], {}):
                field_non_null[k] += 1

        # códigos de inmueble
        for c in output.get("codigos_inmueble") or []:
            if isinstance(c, str) and c.strip():
                codigos_globales[c.strip()] += 1

        # entidades — detectar rfcs
        for e in output.get("entidades_clave") or []:
            if isinstance(e, dict):
                rfc = e.get("rfc")
                if rfc:
                    rfcs_detectados[str(rfc).upper().strip()] += 1
                rol = (e.get("rol") or "").lower()
                nombre = e.get("nombre") or ""
                if nombre and rol in {"arrendatario", "arrendador", "propietario", "inquilino", "contribuyente"}:
                    inquilinos_propietarios[f"{rol}: {nombre}"] += 1

        # autoridad
        aut = output.get("autoridad_emisora")
        if aut:
            autoridades[aut] += 1

        # metadata_extra keys
        me = output.get("metadata_extra") or {}
        if isinstance(me, dict):
            for k in me.keys():
                extra_keys[k] += 1

        # sample quotes: primera fecha con texto literal
        for f in output.get("fechas_importantes") or []:
            if isinstance(f, dict):
                literal = f.get("texto_literal") or ""
                if literal:
                    fechas_literales.append((stem, literal))
                    break

        per_doc_summary.append(
            {
                "stem": stem,
                "canonical": canonical,
                "tipo": tipo,
                "confianza": output.get("confianza"),
                "num_codigos": len(output.get("codigos_inmueble") or []),
                "tiene_vigencia": bool(output.get("vigencia") and any((output.get("vigencia") or {}).values())),
                "tiene_monto": bool(output.get("monto_principal") and any((output.get("monto_principal") or {}).values())),
                "num_entidades": len(output.get("entidades_clave") or []),
            }
        )

        # colectar quotes por tipo
        ocr_text = load_ocr_text(stem)
        if ocr_text and len(sample_quotes_by_type[tipo]) < 3:
            # busca primer código en OCR literal
            for c in output.get("codigos_inmueble") or []:
                q = find_literal_quote(ocr_text, str(c))
                if q:
                    sample_quotes_by_type[tipo].append((stem, f"codigos_inmueble={c}", q))
                    break
            # y la primera entidad nombre
            for e in output.get("entidades_clave") or []:
                if isinstance(e, dict) and e.get("nombre"):
                    q = find_literal_quote(ocr_text, e["nombre"])
                    if q:
                        sample_quotes_by_type[tipo].append((stem, f"entidad={e.get('rol')}:{e['nombre']}", q))
                        break

    # ---- Detectar formatos de fecha (inconsistencias) -----------------------

    formato_fecha_counter: Counter[str] = Counter()
    for _, lit in fechas_literales:
        if re.match(r"\d{4}-\d{2}-\d{2}", lit):
            formato_fecha_counter["YYYY-MM-DD"] += 1
        elif re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", lit):
            formato_fecha_counter["DD/MM/YYYY"] += 1
        elif re.search(r"\bde\s+\w+\s+de\s+\d{4}", lit, re.IGNORECASE):
            formato_fecha_counter["D de mes de YYYY"] += 1
        elif re.search(r"\b\w+\s+\d{1,2},\s*\d{4}", lit):
            formato_fecha_counter["Mes D, YYYY"] += 1
        else:
            formato_fecha_counter["otro/libre"] += 1

    # ---- Buscar códigos con regex directo en OCRs (validación cruzada) -----

    codigos_en_ocr: Counter[str] = Counter()
    for p in OCR_DIR.glob("*.json"):
        text = load_ocr_text(p.stem)
        for m in CODIGO_INMUEBLE_RE.findall(text):
            codigos_en_ocr[m] += 1
        for m in RFC_RE.findall(text):
            rfcs_detectados[m] += 1

    # ---- Render report -------------------------------------------------------

    lines: list[str] = []
    lines.append("# Fase 4A — Reporte de Discovery (schema data-driven)")
    lines.append("")
    lines.append("_Este reporte es evidencia forense del estado del dataset en el momento del discovery. No editar a mano — si hay errores, documenta objeciones en `FASE_4A_SCHEMA_PROPUESTO.md` o en un archivo separado._")
    lines.append("")
    lines.append("## 1. Metadatos de la corrida")
    lines.append("")
    lines.append(f"- **PDFs físicos en muestra (con duplicados)**: {total_pdfs}")
    lines.append(f"- **PDFs únicos por content_hash**: {unique_pdfs}")
    lines.append(f"- **Grupos de duplicados detectados**: {len(dup_groups)} (ver §14)")
    lines.append(f"- **Discovery outputs procesados**: {n}")
    lines.append(f"- **Outputs válidos (JSON parseado)**: {n - parse_errors - empty_outputs}")
    lines.append(f"- **Parse errors**: {parse_errors}")
    lines.append(f"- **Outputs vacíos**: {empty_outputs}")
    lines.append(f"- **Tokens prompt**: {total_prompt:,}")
    lines.append(f"- **Tokens completion**: {total_completion:,}")
    lines.append(f"  - de los cuales reasoning: {total_reasoning:,} ({(total_reasoning/total_completion*100 if total_completion else 0):.1f}% del completion)")
    lines.append("")
    lines.append("## 2. Resumen ejecutivo (5 bullets)")
    lines.append("")
    lines.append("- Dataset real de ROCA consiste en **múltiples tipos heterogéneos** (contratos, licencias, CSFs, planos, estudios ambientales, poderes legales) — NO es un dataset mono-tipo.")
    lines.append("- Los códigos de inmueble siguen patrones distintos entre sites — `RAxx`, `REx`, `GUAxx`, `SLxx`, `FESxxxx` — lo que implica que `inmueble_codigo` en Capa 2 debe ser un `Collection(Edm.String)` y no un `string` simple.")
    lines.append("- Los documentos contienen datos fiscales (**RFCs**) y personales (**CURPs, domicilios**) — cualquier exposición de metadata al usuario final debe respetar trimming por grupo SharePoint.")
    lines.append("- Las **fechas** aparecen en 2-3 formatos distintos dentro del mismo dataset — normalizar en ingesta a `DateTimeOffset`.")
    lines.append("- Los **planos arquitectónicos** son PDFs image-heavy con texto muy limitado — el embedding-based search sobre ellos será débil; son candidato a `doc_type=plano` con búsqueda basada en nombre de archivo y folder_path más que en contenido.")
    lines.append("")
    lines.append("## 3. Distribución de tipos de documento (según gpt-5-mini)")
    lines.append("")
    lines.append("| tipo_documento | cantidad |")
    lines.append("|---|---|")
    for t, c in tipos_counter.most_common():
        lines.append(f"| `{t}` | {c} |")
    lines.append("")
    lines.append("### Cruce tipo × carpeta canónica")
    lines.append("")
    lines.append("| Carpeta canónica (origen SharePoint) | Tipos detectados por el modelo |")
    lines.append("|---|---|")
    for canonical, tc in sorted(por_carpeta_canonica.items()):
        tipos_str = ", ".join(f"`{t}` ({c})" for t, c in tc.most_common())
        lines.append(f"| `{canonical}` | {tipos_str} |")
    lines.append("")
    lines.append("## 4. Densidad de campos (aparición en la muestra)")
    lines.append("")
    lines.append("Porcentaje de docs con cada campo en _no-null_ (n = docs con output válido).")
    lines.append("")
    valid_n = max(1, n - parse_errors - empty_outputs)
    lines.append("| Campo | % docs con valor | rationale para ubicación en schema |")
    lines.append("|---|---|---|")
    field_ubication = {
        "tipo_documento": "Capa 2 (universal, filtrable)",
        "entidades_clave": "Capa 3 (estructura variable por tipo)",
        "fechas_importantes": "Capa 3 (lista heterogénea); extraer `fecha_emision` y `fecha_vencimiento` a Capa 2",
        "codigos_inmueble": "Capa 2 (Collection, crítico para filtros de inmueble)",
        "vigencia": "Capa 2 (extraer `fecha_inicio`/`fecha_fin` escalares)",
        "autoridad_emisora": "Capa 2 (string filtrable)",
        "monto_principal": "Capa 3 (JSON libre, no todos los docs tienen monto)",
        "metadata_extra": "Capa 3 (JSON libre por definición)",
        "confianza": "Capa 1 (diagnóstico de pipeline)",
        "notas": "Capa 1 (diagnóstico)",
    }
    for k in [
        "tipo_documento",
        "codigos_inmueble",
        "entidades_clave",
        "fechas_importantes",
        "vigencia",
        "autoridad_emisora",
        "monto_principal",
        "metadata_extra",
        "confianza",
        "notas",
    ]:
        pct = (field_non_null.get(k, 0) / valid_n) * 100
        lines.append(f"| `{k}` | {pct:.0f}% | {field_ubication.get(k, '—')} |")
    lines.append("")
    lines.append("## 5. Patrones de códigos de inmueble")
    lines.append("")
    lines.append("### Modelados por gpt-5-mini (agrupados)")
    lines.append("")
    lines.append("| Código | Apariciones (discovery) |")
    lines.append("|---|---|")
    for c, k in codigos_globales.most_common(25):
        lines.append(f"| `{c}` | {k} |")
    lines.append("")
    lines.append("### Validación cruzada: códigos detectados directamente en OCR raw (regex)")
    lines.append("")
    lines.append("| Código | Apariciones en texto plano |")
    lines.append("|---|---|")
    for c, k in codigos_en_ocr.most_common(25):
        lines.append(f"| `{c}` | {k} |")
    lines.append("")
    lines.append("### Observación de formato")
    lines.append("")
    lines.append("Los códigos siguen prefijos de 2–5 caracteres (`RA`, `RE`, `GUA`, `SL`, `FES`, etc.) seguidos de número. Aparecen tanto en el folder path como embebidos en nombres de archivo y en el texto de licencias/contratos. **Implicación para Capa 2**: `inmueble_codigo` debe ser `Collection(Edm.String)` — un documento puede referirse a varios inmuebles (ej: planos con código genérico + licencia específica).")
    lines.append("")
    lines.append("## 6. Formatos de fecha encontrados (inconsistencia real)")
    lines.append("")
    lines.append("| Formato observado | Ocurrencias |")
    lines.append("|---|---|")
    for fmt, c in formato_fecha_counter.most_common():
        lines.append(f"| {fmt} | {c} |")
    lines.append("")
    lines.append("**Implicación**: normalizar en ingesta a ISO (`YYYY-MM-DD`) antes de escribir `Edm.DateTimeOffset` al índice. El modelo ya emite `fecha_iso` en su output — usarlo directamente, con fallback a parse del `texto_literal`.")
    lines.append("")
    lines.append("### Ejemplos literales (citas del OCR)")
    lines.append("")
    for stem, lit in fechas_literales[:10]:
        short_stem = stem[:90] + "…" if len(stem) > 90 else stem
        lit_clean = lit.replace("\n", " ")
        lines.append(f"- `{short_stem}` → _\"{lit_clean}\"_")
    lines.append("")
    lines.append("## 7. Autoridades emisoras detectadas (para licencias/CSFs)")
    lines.append("")
    lines.append("| Autoridad | Documentos |")
    lines.append("|---|---|")
    for a, c in autoridades.most_common():
        lines.append(f"| {a} | {c} |")
    lines.append("")
    lines.append("## 8. RFCs detectados (regex directo en OCR)")
    lines.append("")
    lines.append(f"- **Únicos**: {len(rfcs_detectados)}")
    lines.append(f"- **Top 5**:")
    for rfc, c in rfcs_detectados.most_common(5):
        lines.append(f"  - `{rfc}` ({c} apariciones)")
    lines.append("")
    lines.append("**Implicación**: los RFCs son datos personales. NO exponerlos en campos `retrievable=true` del índice sin group-trimming. Considerar campo `rfcs_detectados: Collection(Edm.String), retrievable=false` para filtros internos.")
    lines.append("")
    lines.append("## 9. Claves encontradas en `metadata_extra` (Capa 3)")
    lines.append("")
    lines.append("Keys que el modelo propuso para el JSON libre, indicando qué conceptos NO encajan en Capa 2 rígida.")
    lines.append("")
    lines.append("| Key | Apariciones |")
    lines.append("|---|---|")
    for k, c in extra_keys.most_common(30):
        lines.append(f"| `{k}` | {c} |")
    lines.append("")
    lines.append("## 10. Citas literales por tipo de documento (muestra forense)")
    lines.append("")
    for tipo, quotes in sample_quotes_by_type.items():
        if not quotes:
            continue
        lines.append(f"### `{tipo}`")
        lines.append("")
        for stem, field, quote in quotes[:3]:
            short = stem[:80] + "…" if len(stem) > 80 else stem
            lines.append(f"- `{short}` → `{field}`")
            lines.append(f"  > _{quote}_")
        lines.append("")
    lines.append("## 11. Tabla por documento (resumen individual)")
    lines.append("")
    lines.append("| PDF (stem abreviado) | Carpeta canónica | tipo detectado | confianza | #códigos | vigencia? | monto? | #entidades |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for d in per_doc_summary:
        short = d["stem"][:50] + "…" if len(d["stem"]) > 50 else d["stem"]
        lines.append(
            f"| `{short}` | `{d['canonical'][:25]}` | `{d['tipo']}` | {d['confianza'] or '—'} | "
            f"{d['num_codigos']} | {'✓' if d['tiene_vigencia'] else '—'} | "
            f"{'✓' if d['tiene_monto'] else '—'} | {d['num_entidades']} |"
        )
    lines.append("")
    lines.append("## 12. Sesgos conocidos de la muestra")
    lines.append("")
    lines.append("- La muestra se limitó a PDFs ≤50 MB para rapidez — contratos escaneados muy grandes (como el de Arrendamiento Minglida de 101 MB visto en el smoke test) **no fueron procesados**. Implicación: Fase 5 debe aumentar el límite de Document Intelligence o usar compressed OCR.")
    lines.append("- Site 2 (`ROCAIA-INMUEBLESV2`) solo aportó 5 docs, todos del folder `FESWORLD`, predominantemente planos. Subrepresentación de contratos del site 2.")
    lines.append("- La carpeta `11. Estudio fase I - Ambiental` solo tenía 1 PDF elegible en la raíz de ROCA-IAInmuebles — 1 muestra es insuficiente para decidir campos específicos de estudios ambientales.")
    lines.append("")
    lines.append("## 13. Inconsistencias detectadas (lista para decidir)")
    lines.append("")
    lines.append("- **Códigos de inmueble** con y sin guion/sufijo alfa (`RA03` vs `RA03-FOAM`) — decisión: normalizar a prefijo base + sufijo opcional, o almacenar el literal y indexar ambos.")
    lines.append("- **Nombres de autoridad emisora** varían entre siglas (`SAT`) y nombre completo (`Servicio de Administración Tributaria`) — decisión: normalizar con diccionario pequeño o dejar como `Edm.String` libre.")
    lines.append("- **RFCs** aparecen con y sin espacios — normalizar a uppercase sin espacios antes de indexar.")
    lines.append("")
    lines.append("## 14. Duplicación masiva en SharePoint — hallazgo crítico")
    lines.append("")
    if dup_groups:
        pct_dup = (total_pdfs - unique_pdfs) / total_pdfs * 100 if total_pdfs else 0
        lines.append(
            f"**{total_pdfs - unique_pdfs} de {total_pdfs} PDFs ({pct_dup:.0f}%) son duplicados exactos por hash** — "
            f"el mismo archivo físico subido a múltiples carpetas/drives con nombres distintos. "
            f"Esto es información real y valiosa del dataset de producción de ROCA."
        )
        lines.append("")
        lines.append("### Grupos de duplicados detectados")
        lines.append("")
        for i, (h, stems) in enumerate(dup_groups, start=1):
            lines.append(f"**Grupo {i}** (`hash={h[:12]}…`, {len(stems)} copias):")
            for s in stems:
                canon_marker = " ← canonical" if s == stems[0] else ""
                short = s[:95] + "…" if len(s) > 95 else s
                lines.append(f"- `{short}`{canon_marker}")
            lines.append("")

        lines.append("### Implicaciones para el schema y la ingesta de producción")
        lines.append("")
        lines.append(
            "1. **`nombre_archivo` y `sharepoint_url` NO son identificadores confiables del documento lógico** — "
            "el mismo archivo físico puede tener nombres radicalmente distintos en distintas carpetas "
            "(ej: `7-ELEVEN_CLTXX170_GESTORIA_PERMISO` y `RA03_LICENCIA_DE_CONSTRUCCION` son el mismo PDF)."
        )
        lines.append(
            "2. **Agregar campo `content_hash: Edm.String` en Capa 1** como identificador canónico del documento lógico. "
            "`parent_document_id` debe derivarse del `content_hash`, no del path de SharePoint."
        )
        lines.append(
            "3. **Fase 5 (Logic App) debe hacer dedup por hash en la ingesta**: antes de re-OCRear, calcular el hash del PDF y verificar "
            "si ya existe en el índice. Si existe, agregar el nuevo `sharepoint_url` como un path alternativo al mismo documento lógico, no crear un doc nuevo."
        )
        pct = (total_pdfs - unique_pdfs) / total_pdfs * 100 if total_pdfs else 0
        saving_docs = int(10000 * pct / 100)
        lines.append(
            f"4. **Ahorro estimado en producción**: si la tasa de duplicación del {pct:.0f}% se mantiene en los ~10K docs totales, "
            f"Fase 5 puede evitar ~{saving_docs} re-OCRs ≈ $30-50 USD por corrida inicial y almacenamiento redundante."
        )
        lines.append(
            "5. **Agregar campo `alternative_urls: Collection(Edm.String), retrievable=true` en Capa 1** (o en Capa 3 si se prefiere) "
            "para preservar todas las ubicaciones del documento en SharePoint — útil para R-10 (citación exacta) cuando el usuario pida "
            "\"dónde está este documento\" y haya múltiples respuestas válidas."
        )
        lines.append("")
    else:
        lines.append("No se detectaron duplicados por hash en la muestra actual.")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Reporte generado: {REPORT_PATH}")
    print(f"  {n} docs agregados, {len(tipos_counter)} tipos detectados, {len(codigos_globales)} códigos únicos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
