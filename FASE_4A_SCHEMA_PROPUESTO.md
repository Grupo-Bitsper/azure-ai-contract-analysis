# Fase 4A — Schema propuesto para `roca-contracts-v1` (Azure AI Search)

> **Este es el documento que el usuario aprueba antes de arrancar Fase 4B.** Léelo con `FASE_4A_DISCOVERY_REPORT.md` al lado — cada decisión de campo está justificada con evidencia real de la muestra.
>
> **Versión 2 · 2026-04-15** — muestra ampliada a 45 PDFs (38 únicos por hash). Cambios respecto a v1: agregados los campos `content_hash` y `alternative_urls` en Capa 1 como respuesta al hallazgo de duplicación masiva en SharePoint (§14 del reporte); `parent_document_id` ahora se deriva del `content_hash`, NO del path. Detalles de la ampliación y el hallazgo en la sección §0.1 abajo.
>
> Muestra: 45 PDFs reales descargados vía sync robot desde 4 drives de `ROCA-IAInmuebles` + 1 drive de `ROCAIA-INMUEBLESV2`, cubriendo 8+ tipos de documento heterogéneos.

## 0.1 — Cambios de v1 → v2 tras ampliación de muestra (2026-04-15)

La muestra original de 18 PDFs tenía sesgos evidentes:
- Solo cubría 6 carpetas canónicas del site 1 (el drive principal `Documentos`).
- Site 2 solo aportó 5 docs de FESWORLD, todos planos.
- No tocaba los drives secundarios del site 1 (`Biblioteca de suspensiones de conservación`, `Documentos semantica copilot`).

Se amplió la muestra a **45 PDFs** cubriendo:
- 5 carpetas canónicas del drive `Documentos` del site 1 (más cobertura)
- Carpeta `Principal` del mismo drive (no tocada antes)
- Drive `Biblioteca de suspensiones de conservación` (12 PDFs — INE, CURP, Opinión SAT, Estados Financieros, Título de Propiedad, etc.)
- Drive `Documentos semantica copilot` (1 PDF)
- 6 proyectos distintos dentro de FESWORLD (antes solo 3)

**Hallazgo crítico de la ampliación**: 12 de los 45 PDFs (27%) son **duplicados exactos por hash** — el mismo archivo físico subido a múltiples carpetas/drives de SharePoint con nombres radicalmente distintos (ej: un PDF llamado `7-ELEVEN_CLTXX170_GESTORIA_PERMISO_DE_CONSTRUCCION` es byte-idéntico a `RA03_LICENCIA_DE_CONSTRUCCION` en otra carpeta).

**Implicación directa para el schema**: `nombre_archivo` y `sharepoint_url` NO son identificadores confiables del documento lógico. Se agrega `content_hash` como identificador canónico, y `parent_document_id` se deriva de él. Fase 5 (Logic App) debe hacer dedup por hash en la ingesta para evitar re-OCR redundante (~27% de ahorro estimado: $30-50 USD por corrida inicial en los ~10K docs de producción).

---

## 0. Principios de diseño (heredados del plan, confirmados por los datos)

1. **3 capas de schema.** Capa 1 inmutable (núcleo), Capa 2 metadata común filtrable, Capa 3 JSON libre para lo raro. Esta estructura ya era decisión del plan original y **los datos la confirman**: ningún campo aplica a 100% de los tipos pero algunos sí aplican a ≥50% — exactamente el caso de Capa 2.
2. **Security trimming siempre.** `group_ids` y `user_ids` son `filterable=true, retrievable=false`. Esto está decidido desde Fase 2 y no se cuestiona aquí.
3. **Vector size 1536** para `content_vector` — dimensión nativa de `text-embedding-3-small`, el modelo desplegado en Fase 3.
4. **Versionado por documento lógico.** Campos `parent_document_id`, `version_number`, `is_latest_version` en Capa 1 para soportar R-07 / R-08. SharePoint Drive API da versiones nativas — el Logic App de Fase 5 las lee y escribe múltiples documentos en el índice.
5. **Chunking por documento.** Un PDF grande (ej: poder legal de 47 páginas, 89K caracteres) genera N chunks con el mismo `parent_document_id` pero distinto `chunk_id`. `total_chunks` permite reconstruir el doc padre.
6. **Los códigos de inmueble son `Collection`**, no string — la muestra confirma que un solo doc puede referenciar múltiples inmuebles (ej: el contrato RA03 menciona `RA03`, `RA03-INV`; un poder legal menciona `ESCRITURA 1,442`, `ESCRITURA 27,748`, `VOLUMEN 015`, etc.).

---

## 1. Capa 1 — Núcleo inmutable (15 campos)

Aplica a **todo** documento indexado. Estos campos no cambian con el tipo y no se renombran a futuro — cualquier migración posterior los preserva.

| # | Campo | Tipo | key | searchable | filterable | sortable | retrievable | facetable | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Edm.String` | ✓ | — | ✓ | — | ✓ | — | PK del chunk. Formato `{parent_document_id}__{chunk_id:04d}`. |
| 2 | `parent_document_id` | `Edm.String` | — | — | ✓ | ✓ | ✓ | ✓ | **v2**: hash estable derivado del `content_hash` + `version_number` (NO del path SharePoint). Agrupa chunks del mismo doc lógico aunque exista en múltiples carpetas. Filtra para R-07. |
| 2a | **`content_hash`** | `Edm.String` (filterable, retrievable) | — | — | ✓ | — | ✓ | — | **NUEVO v2**. MD5 o SHA-1 del binario del PDF. Identificador canónico del documento físico. En Fase 5, la ingesta compara este hash antes de re-OCRear — si ya existe, solo agrega un `sharepoint_url` alternativo al doc existente. Justificación: el 27% del dataset real son duplicados byte-idénticos con nombres distintos (ver §14 del reporte). |
| 3 | `chunk_id` | `Edm.Int32` | — | — | ✓ | ✓ | ✓ | — | Índice del chunk dentro del doc padre (0, 1, 2…). |
| 4 | `total_chunks` | `Edm.Int32` | — | — | — | — | ✓ | — | Total de chunks del doc padre — permite reconstruir. |
| 5 | `content` | `Edm.String` | — | ✓ (analyzer `es.microsoft`) | — | — | ✓ | — | Texto del chunk, ~500-1000 tokens. |
| 6 | `content_vector` | `Collection(Edm.Single)` (dim=1536, HNSW) | — | ✓ (vector) | — | — | — | — | Embedding `text-embedding-3-small`. No retrievable — se busca pero no se devuelve. |
| 7 | `sharepoint_url` | `Edm.String` | — | — | ✓ | — | ✓ | — | `webUrl` **primario** del archivo en Graph — la ubicación canónica del documento. El agente lo devuelve como citation principal. |
| 7a | **`alternative_urls`** | `Collection(Edm.String)` (retrievable) | — | — | ✓ | — | ✓ | — | **NUEVO v2**. URLs adicionales donde el mismo `content_hash` vive en SharePoint. Ej: un título de propiedad que está en `Principal/` y también en `Biblioteca de suspensiones/` debe aparecer como 1 solo doc en el índice con 2 URLs. Respeta R-10 (citación exacta) permitiendo al agente decir "este doc está en X y también en Y". |
| 8 | `nombre_archivo` | `Edm.String` | — | ✓ (analyzer `es.microsoft`) | ✓ | ✓ | ✓ | — | Nombre base del archivo sin path. Crítico para planos (ver §4). |
| 9 | `site_origen` | `Edm.String` | — | — | ✓ | — | ✓ | ✓ | `ROCA-IAInmuebles` o `ROCAIA-INMUEBLESV2`. Facet para dashboards. |
| 10 | `folder_path` | `Edm.String` | — | ✓ (analyzer `es.microsoft`) | ✓ | — | ✓ | — | Ruta completa dentro del site (ej: `/30. Contrato de arrendamiento y anexos/Arrendatario/1. PODER REP LEGAL/...`). Capa semántica por sí misma: el folder ya clasifica. |
| 11 | `fecha_procesamiento` | `Edm.DateTimeOffset` | — | — | ✓ | ✓ | ✓ | — | Cuándo lo indexó el pipeline. Útil para auditoría y diff versus SharePoint. |
| 12 | `group_ids` | `Collection(Edm.String)` | — | — | ✓ | — | **✗ retrievable=false** | — | Entra ID group object IDs con permiso de lectura. Usado solo para `search.in(group_ids, ...)` security trimming. |
| 13 | `user_ids` | `Collection(Edm.String)` | — | — | ✓ | — | **✗ retrievable=false** | — | Entra ID user object IDs con grant individual directo (scenario "Shared with X"). |

### Versionado (sub-bloque de Capa 1)

| # | Campo | Tipo | Descripción |
|---|---|---|---|
| 14 | `version_number` | `Edm.Int32` | Número de versión SharePoint (1, 2, 3…). Viene de Graph `/drive/items/{id}/versions`. |
| 15 | `is_latest_version` | `Edm.Boolean` (filterable) | `true` sólo para la última. Filtro explícito para R-07 (el agente siempre filtra por `is_latest_version eq true` por default; el usuario puede pedir "versiones anteriores" y se relaja). |

**Por qué `is_latest_version` y no calcularlo:** Azure AI Search no tiene `MAX(version_number) GROUP BY parent_document_id` nativo. Almacenar el flag pre-calculado en ingesta elimina un round-trip y evita queries costosas. El flag se recalcula cuando una nueva versión entra (la versión anterior pasa a `false` en el mismo batch).

**Diagnóstico (Capa 1 — no elevado a Capa 2 porque es útil solo para el pipeline, no para el usuario final):**

| # | Campo | Tipo | Rationale |
|---|---|---|---|
| 16 | `extraction_confidence` | `Edm.String` (`alta` / `media` / `baja`) | Salida del field `confianza` del discovery prompt. 17/18 docs reales salieron con `alta`. Permite re-run selectivo en Fase 5 si aparecen docs con `baja`. |
| 17 | `extraction_notes` | `Edm.String` | Campo `notas` del discovery — observaciones del modelo ("documento ilegible en página 3", etc). |

---

## 2. Capa 2 — Metadata común (12 campos)

**Criterio de inclusión**: aparece en ≥50% de los docs con valor no-null **Y** el negocio lo quiere como filtro/facet. Campos con <50% density quedan en Capa 3.

### Observación cruda del reporte (§4 del discovery report)

| Campo del discovery | % docs con valor | ¿a Capa 2? |
|---|---|---|
| `tipo_documento` | 100% | ✓ (universal) |
| `codigos_inmueble` | 78% | ✓ (filtro primario de negocio) |
| `entidades_clave` | 100% | Parcial — ver §2.2 |
| `fechas_importantes` | 100% | Parcial — ver §2.3 (extraer 2 escalares) |
| `vigencia` | 100% reportado pero **57% útil** (en planos/CSFs los valores fueron null-dentro-de-objeto) | ✓ para `fecha_vencimiento` |
| `autoridad_emisora` | 56% | ✓ (límite del criterio; útil para licencias/CSFs) |
| `monto_principal` | 39% | ✗ → Capa 3 |

### 2.1 Campos universales / de alta densidad

| # | Campo | Tipo | searchable | filterable | facetable | Rationale |
|---|---|---|---|---|---|---|
| 18 | `doc_type` | `Edm.String` | — | ✓ | ✓ | Enum cerrado (**v2 ampliado con la muestra de 38 únicos — 17 tipos observados**): `contrato_arrendamiento`, `contrato_compraventa`, `contrato_desarrollo_inmobiliario`, `licencia_construccion`, `constancia_situacion_fiscal`, `constancia_uso_suelo`, `constancia_curp`, `plano_arquitectonico`, `estudio_ambiental`, `estudio_geotecnico`, `poder_legal`, `escritura_publica`, `acta_asamblea`, `factura_electronica`, `recibo_servicio`, `estados_financieros_auditados`, `garantia_corporativa`, `poliza_seguro`, `titulo_propiedad`, `otro`. 20 valores explícitos + `otro` como fallback. Normalización: el discovery prompt devuelve strings libres, la ingesta los mapea a este enum; si algún doc cae en `otro` se agrega al enum en un schema bump. |
| 19 | `inmueble_codigos` | `Collection(Edm.String)` | ✓ (analyzer `keyword` + `standard`) | ✓ | ✓ | Lista de códigos identificadores **sin normalización destructiva**: almacenar tanto `RA03` como `RA03-INV` como `RA03-FOAM-100-32`. El analyzer `keyword` permite match exacto; `standard` permite búsqueda por prefijo. **Evidencia**: el contrato `RA03_Contrato_v2_final` menciona `RA03-INV` en el texto; el plano `RA03-FOAM-100-32` es un drawing number, no un inmueble puro. Ambos deben ser encontrables. |
| 20 | `inmueble_codigo_principal` | `Edm.String` | ✓ (analyzer `keyword`) | ✓ | ✓ | **El primer código de la lista** después de ordenar por prioridad (prefijos conocidos: RA, RE, GU, SL > otros). Permite agregaciones "¿cuántos docs tiene RA03?" sin multi-valued aggregation. |
| 21 | `doc_title` | `Edm.String` | ✓ (analyzer `es.microsoft`) | — | — | Título legible — preferentemente el campo `titulo` de `metadata_extra` (7/18 docs lo tienen explícito), fallback al `nombre_archivo` sin extensión. |

### 2.2 Partes / entidades (de-normalizadas a 2 escalares)

La lista completa de `entidades_clave` vive en Capa 3 (variabilidad alta). Pero el negocio necesita filtrar por quién firma, así que promovemos **dos entidades por rol**:

| # | Campo | Tipo | filterable | Rationale |
|---|---|---|---|---|
| 22 | `arrendador_nombre` | `Edm.String` | ✓ (+ searchable analyzer `es.microsoft`) | Solo para `doc_type=contrato_arrendamiento`. **Evidencia**: `RA03_Contrato_v2_final` lo tiene explícito como "BANCO ACTINVER, S.A. … Fiduciario" (rol `Arrendador (fiduciario)`). |
| 23 | `arrendatario_nombre` | `Edm.String` | ✓ (+ searchable) | Complementa el anterior. Para otros `doc_type` es null. |
| 24 | `contribuyente_rfc` | `Edm.String` | ✓ | Solo para `doc_type=constancia_situacion_fiscal` / `factura_electronica`. **Evidencia**: 14 RFCs únicos detectados por regex en la muestra; los top 5 (`MOP210705IC6`, `YSM200512G37`, `TME840315KT6`, `GSE990319JR6`, `SCH1906128R1`) identifican al contribuyente del doc. **Normalización**: uppercase, sin espacios. |
| 25 | `propietario_nombre` | `Edm.String` | ✓ | Para licencias/permisos — el "propietario del predio" según el discovery (ej: `RC. INMUEBLES INDUSTRIALES S.A. DE C.V.` en una licencia de Tlaquepaque). |

### 2.3 Fechas (de-normalizadas a escalares + literales)

| # | Campo | Tipo | Rationale |
|---|---|---|---|
| 26 | `fecha_emision` | `Edm.DateTimeOffset` (filterable, sortable) | Fecha principal del documento. Viene del `fecha_iso` del discovery con fallback a parse de `texto_literal`. **Evidencia formatos reales**: `"12 DE MARZO DE 2021"`, `"29 de junio de 2022"`, `"20-04-2023"`, `"05 de Julio de 2024"` — normalizar TODO a ISO `YYYY-MM-DD`. |
| 27 | `fecha_vencimiento` | `Edm.DateTimeOffset` (filterable, sortable) | Para licencias/contratos/pólizas. Null para CSFs/escrituras/planos. **Evidencia**: licencia GU01-A dice `"VIGENCIA 730 Dias, 20-04-2023"` — el modelo lo colocó correctamente en `vigencia.fin_iso`. |
| 28 | `es_vigente` | `Edm.Boolean` (filterable) | Pre-calculado en ingesta: `fecha_vencimiento > today` **O** `fecha_vencimiento IS NULL` (docs sin expiración se consideran vigentes). El cálculo se refresca cada corrida del Logic App (Fase 5) y al menos diariamente (requirement del Plan §5 R-04 / R-12). |

### 2.4 Autoridad / emisor

| # | Campo | Tipo | Rationale |
|---|---|---|---|
| 29 | `autoridad_emisora` | `Edm.String` (filterable, facetable, searchable analyzer `es.microsoft`) | 56% de docs reales tienen valor — casi exclusivamente licencias (Municipios, SEMARNAT) y CSFs (SAT). **Decisión de normalización**: NO normalizar con diccionario, dejar como string libre. Razón: el modelo produjo `"SAT"`, `"Servicio de Administración Tributaria (SAT)"`, `"SAT (Servicio de Administración Tributaria) / SHCP"` — son equivalentes pero la normalización requiere mantenimiento de un diccionario vivo. Mejor: analyzer `es.microsoft` + semantic ranking las agrupa naturalmente en queries. |

**Campos descartados de Capa 2**:

- `monto_principal` → Capa 3. Solo 39% de docs tienen valor y los casos son heterogéneos (renta mensual, depósito garantía, valor declarado, valor de contrato). Filtrar por monto no es un caso de uso de R-01..R-19.
- `vigencia` como objeto → se descompone en `fecha_emision`, `fecha_vencimiento`, `es_vigente` escalares. El objeto `{inicio_iso, fin_iso, duracion_texto}` se preserva completo en Capa 3 para no perder `duracion_texto`.

---

## 3. Capa 3 — Metadata flexible JSON (1 campo)

| # | Campo | Tipo | searchable | retrievable | Rationale |
|---|---|---|---|---|---|
| 30 | `extracted_metadata` | `Edm.String` (stringified JSON) | ✓ (analyzer `standard` — busca tokens, no estructura) | ✓ | Dump completo del output del discovery prompt: la lista full de `entidades_clave`, `fechas_importantes`, `monto_principal`, y el objeto `metadata_extra` con campos que el modelo detectó libremente. **No se parsea en el índice** — el agente lo recibe como string y lo presenta crudo, o extrae campos con una función de post-proceso si el usuario lo pide. |

### Campos reales observados en `metadata_extra` del discovery (evidencia para documentar qué vive en Capa 3)

Del reporte §9, los top keys que el modelo usó:

```
titulo (7), ubicacion (7), nombre_archivo (6), escala (5), proyecto (4), numero_dibujo (4),
uso_suelo (3), telefono (3), superficie_m2 (3), idCIF (3), regimen_capital (3),
codigo_postal (3), actividades_economicas (3), obligaciones (3), cadena_original_sello (3),
no_dibujo (3), folio (2), colonia (2), municipio (2), clave_catastral (2),
observaciones_tecnicas (2), numero_escritura (2), volumenes (2), nombre_comercial (2),
correo_electronico (2), rfc (2), paginas_detectadas (2), tipo_plano (2), ingenieria_por (2)
```

**Observación crítica**: `clave_catastral`, `numero_escritura`, `superficie_m2`, `idCIF` son campos que podrían promoverse a Capa 2 si el negocio los pide como filtros en Fase 6. La Capa 3 JSON es un **staging area** para eso — sin re-OCRear.

**Recomendación**: dejar TODO en Capa 3 por ahora, y promover selectivamente en Fase 4B (después de validar queries) o Fase 6 (después de feedback del negocio sobre R-11/R-13).

---

## 4. Campos especiales para planos arquitectónicos (caso degenerate)

7/18 docs de la muestra son `plano_arquitectonico` — la categoría más grande. **Los planos tienen texto mínimo** (3-5K chars), el embedding sobre ese texto es ruidoso (números de cota, códigos de dibujo, siglas de ingeniería), y el contenido visual (el dibujo) no se captura en `content_vector`.

### Estrategia de indexing para `plano_arquitectonico`

1. **El `content` field contiene todo el texto plano del OCR** — para que el semantic ranker lo use como señal débil.
2. **El `folder_path` contiene la semántica fuerte** — ej: `/65. Planos arquitectonicos (As built)/100.- ARQUITECTONICOS PDF/` — analyzer `es.microsoft` indexa las palabras `planos arquitectonicos as built arquitectonicos` y el usuario puede preguntar "muéstrame los planos arquitectónicos de RA03" y el matching ocurre por `folder_path` + `inmueble_codigos=['RA03']`.
3. **Campos específicos de plano en Capa 3**: `escala`, `numero_dibujo`, `proyecto`, `ingenieria_por`, `tipo_plano` — el modelo los detectó en 4-5 de los 7 planos. Recuperables por búsqueda de string dentro del JSON (menos preciso pero suficiente para el caso de uso "dame los planos estructurales de FESWORLD").
4. **No generar embeddings separados por sección** — los planos son de 1 página, un solo chunk por doc.

### R-13 (localización de carpeta de cierre de proyecto) está cubierto por `folder_path`

El plan originalmente preguntaba "cómo ubicamos la carpeta de cierre de proyecto" — la respuesta **basada en los datos reales** es: `folder_path` contiene la carpeta canónica (`65. Planos arquitectonicos (As built)`, `07. Permisos de construcción`, etc.) y se puede filtrar por `folder_path contains "65."` directamente.

---

## 5. Semantic configuration

```json
{
  "name": "default-semantic-config",
  "prioritizedFields": {
    "titleField": { "fieldName": "doc_title" },
    "prioritizedContentFields": [
      { "fieldName": "content" }
    ],
    "prioritizedKeywordsFields": [
      { "fieldName": "doc_type" },
      { "fieldName": "inmueble_codigos" },
      { "fieldName": "autoridad_emisora" },
      { "fieldName": "folder_path" }
    ]
  }
}
```

Razón: el semantic ranker usa `prioritizedKeywordsFields` para boost relevance. `inmueble_codigos` y `doc_type` son las señales más fuertes del dataset (filtros directos de negocio), `folder_path` es la señal estructural de SharePoint que los docs respetan religiosamente.

---

## 6. Vector configuration (HNSW + integrated vectorizer)

⚠ **CRÍTICO v2 — aprendido en smoke test 2026-04-15**: el índice de producción **DEBE** tener un **vectorizer integrado** (`vectorizers` section) para que el tool `azure_ai_search` de Foundry agents pueda usar `query_type=vector_semantic_hybrid`. Sin vectorizer, el agent falla con "Query type vector_semantic_hybrid requires a vector field with integrated vectorizer, but none was found" — error que el playground muestra engañosamente como "Access denied". El índice smoke `roca-contracts-smoke` se creó sin vectorizer y tuvimos que bajar a `query_type=semantic` para hacer que funcionara. En Fase 4B, el índice de producción `roca-contracts-v1` debe incluir el vectorizer.

```json
{
  "vectorSearch": {
    "algorithms": [
      {
        "name": "hnsw-default",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ],
    "vectorizers": [
      {
        "name": "aoai-vectorizer",
        "kind": "azureOpenAI",
        "azureOpenAIParameters": {
          "resourceUri": "https://rocadesarrollo-resource.openai.azure.com",
          "deploymentId": "text-embedding-3-small",
          "modelName": "text-embedding-3-small",
          "authIdentity": null
        }
      }
    ],
    "profiles": [
      {
        "name": "vector-profile-default",
        "algorithm": "hnsw-default",
        "vectorizer": "aoai-vectorizer"
      }
    ]
  }
}
```

El `content_vector` campo debe tener `vectorSearchProfileName: "vector-profile-default"` (con el vectorizer asociado vía el profile).

**Auth del vectorizer**: usar `authIdentity: null` deja al search service usar su System-Assigned MI para llamar a Azure OpenAI. El MI del search service (`c9181743-c085-4885-8ff7-81392e0d2d5a`, ya documentado en Fase 3) necesita el rol `Cognitive Services OpenAI User` sobre `rocadesarrollo-resource`. Si ese rol no está asignado todavía, Fase 4B lo debe asignar antes de crear el índice.

Defaults conservadores — `m=4` es el mínimo recomendado por Microsoft para datasets <1M chunks. Subir a `m=8` si en Fase 4B la recall@10 queda <0.85 sobre las queries R-04/R-05/R-17.

---

## 7. Cross-check con los requisitos R-01..R-19 del plan

| R | Caso | Cómo lo cubre el schema |
|---|---|---|
| R-01 | Búsqueda por inmueble | `inmueble_codigos` (Collection) + `inmueble_codigo_principal` |
| R-02 | Búsqueda por tipo de doc | `doc_type` (facetable) |
| R-03 | Búsqueda por rango de fecha | `fecha_emision` + `fecha_vencimiento` (filterable/sortable) |
| R-04 | Permisos vigentes por inmueble | `doc_type=licencia_construccion AND inmueble_codigos/any(c: c eq 'X') AND es_vigente eq true` |
| R-05 | Contratos de arrendamiento por inquilino | `doc_type=contrato_arrendamiento AND arrendatario_nombre eq 'X'` |
| R-06 | Docs emitidos por autoridad X | `autoridad_emisora eq 'SAT'` |
| R-07 | Última versión | `is_latest_version eq true` |
| R-08 | Comparación entre versiones | Query por `parent_document_id`, recupera todas las `version_number`, diffs se hacen en el agente |
| R-09 | Búsqueda libre semántica | `content` + `content_vector` con semantic ranker |
| R-10 | Citación exacta | `sharepoint_url` + `nombre_archivo` + `folder_path` — todo retrievable |
| R-11 | Checklist de permisos requeridos | Out of schema (negocio). El schema NO lo cubre — depende del listado maestro que falta. Ver recomendación 2 del plan §8.5. |
| R-12 | Permisos próximos a vencer | `fecha_vencimiento le <today+30d> AND fecha_vencimiento ge <today>` |
| R-13 | Carpeta de cierre de proyecto | `folder_path` contains match |
| R-14 | Dueño / RFC | `contribuyente_rfc` + `extracted_metadata` para detalle |
| R-15 | Superficie / medidas | `extracted_metadata.superficie_m2` — Capa 3 por ahora, promoción a Capa 2 si se usa como filtro |
| R-16 | Docs nuevos | `fecha_procesamiento` sortable descending |
| R-17 | Docs faltantes por inmueble | Requiere cruzar `inmueble_codigos` contra lista maestra de R-11 — lógica en el agente, schema solo provee los filtros |
| R-18 | Ubicación geográfica (municipio) | `extracted_metadata.municipio` — Capa 3, promoción futura |
| R-19 | Búsqueda por número de escritura | `extracted_metadata.numero_escritura` — buscable como string dentro del JSON stringified |

**R cubiertos out-of-the-box con este schema**: 14/19.
**R que requieren Capa 3 + lógica del agente**: 3 (R-15, R-18, R-19).
**R que requieren input del negocio (no schema)**: 2 (R-11, R-17).

---

## 8. Trade-offs explícitos que el usuario debe revisar

### 8.1 Desnormalización de entidades a `arrendador_nombre` / `arrendatario_nombre` / `propietario_nombre` / `contribuyente_rfc`

- **Pro**: filtros directos, sin multi-valued aggregation, facets útiles.
- **Contra**: si un doc tiene 2 arrendadores (co-propiedad), solo capturamos el primero. La lista completa sigue en Capa 3 pero los filtros no la ven.
- **Alternativa**: usar `Collection(Edm.String)` para cada rol. Ruido visual pero más preciso.
- **Recomendación**: **empezar con escalares**, promover a Collection solo si Fase 4B detecta casos multi-parte reales.

### 8.2 `inmueble_codigos` SIN normalización destructiva

- **Pro**: preservamos literal — `RA03-INV`, `RA03-FOAM-100-32`, `RA03` coexisten.
- **Contra**: filtrar "todo lo que es RA03" requiere `any(c: startswith(c, 'RA03'))` que es más costoso que `eq`.
- **Alternativa**: almacenar también `inmueble_codigos_base` con solo el prefijo (`RA03`, `RE05A`, `GU01A`).
- **Recomendación**: **agregar `inmueble_codigos_base: Collection(Edm.String)`** como campo derivado para facilitar facets y counts agregados por inmueble raíz.

### 8.3 `content_vector` con `text-embedding-3-small` (1536 dims)

- **Pro**: barato, ya desplegado en Fase 3, nativo de Azure OpenAI.
- **Contra**: no es el mejor estado del arte para español legal técnico.
- **Alternativa**: `text-embedding-3-large` (3072 dims). Triplica costo de storage y de indexing.
- **Recomendación**: **mantener small**. Si R-04/R-05/R-17 fallan en recall en Fase 4B, revisamos.

### 8.4 `extracted_metadata` como `Edm.String` stringified vs Complex Type

- **Pro** (stringified): simple, infinitamente flexible, sin schema bumps.
- **Contra**: no se puede filtrar/facetar por sub-campos. Solo full-text sobre el JSON.
- **Alternativa** (Complex Type): nested object `Edm.ComplexType` con sub-campos. Requiere declarar cada sub-campo en el schema, lo cual rompe el propósito de "Capa 3 flexible".
- **Recomendación**: **mantener stringified**. Los sub-campos que realmente importen se promueven a Capa 2 en corridas de schema bump incrementales.

### 8.5 Storage cost estimado

Con 10K documentos estimados en producción, ~5 chunks/doc promedio, ~1-2KB de metadata por chunk + 1536×4 bytes de vector = ~8KB por chunk:
- 50K chunks × 8KB = **400 MB** → dentro del free tier de AI Search Basic (2 GB storage). Sin preocupación.

---

## 9. Lista exhaustiva de campos propuestos (resumen canónico)

| # | Campo | Capa | Tipo | Rationale corto |
|---|---|---|---|---|
| 1 | `id` | 1 | Edm.String (key) | PK |
| 2 | `parent_document_id` | 1 | Edm.String | derivado de content_hash, agrupa chunks+versiones |
| 2a | **`content_hash`** | 1 | Edm.String | **NUEVO v2** — MD5/SHA-1 del PDF, canonical ID |
| 3 | `chunk_id` | 1 | Edm.Int32 | índice chunk |
| 4 | `total_chunks` | 1 | Edm.Int32 | recon doc padre |
| 5 | `content` | 1 | Edm.String (es.microsoft) | texto del chunk |
| 6 | `content_vector` | 1 | Collection(Edm.Single) dim 1536 | embedding |
| 7 | `sharepoint_url` | 1 | Edm.String | citation primaria |
| 7a | **`alternative_urls`** | 1 | Collection(Edm.String) | **NUEVO v2** — URLs extras del mismo doc físico |
| 8 | `nombre_archivo` | 1 | Edm.String | file name |
| 9 | `site_origen` | 1 | Edm.String | facet site |
| 10 | `folder_path` | 1 | Edm.String (es.microsoft) | carpeta canónica |
| 11 | `fecha_procesamiento` | 1 | Edm.DateTimeOffset | cuándo se indexó |
| 12 | `group_ids` | 1 | Collection(Edm.String) retrievable=false | security trim |
| 13 | `user_ids` | 1 | Collection(Edm.String) retrievable=false | security trim |
| 14 | `version_number` | 1 | Edm.Int32 | v1, v2, v3 |
| 15 | `is_latest_version` | 1 | Edm.Boolean | flag R-07 |
| 16 | `extraction_confidence` | 1 | Edm.String | diagnóstico |
| 17 | `extraction_notes` | 1 | Edm.String | diagnóstico |
| 18 | `doc_type` | 2 | Edm.String | enum cerrado |
| 19 | `inmueble_codigos` | 2 | Collection(Edm.String) | multi-code |
| 20 | `inmueble_codigo_principal` | 2 | Edm.String | primary code |
| 21 | `doc_title` | 2 | Edm.String (es.microsoft) | título legible |
| 22 | `arrendador_nombre` | 2 | Edm.String | solo contratos |
| 23 | `arrendatario_nombre` | 2 | Edm.String | solo contratos |
| 24 | `contribuyente_rfc` | 2 | Edm.String | RFC normalizado |
| 25 | `propietario_nombre` | 2 | Edm.String | licencias |
| 26 | `fecha_emision` | 2 | Edm.DateTimeOffset | ISO |
| 27 | `fecha_vencimiento` | 2 | Edm.DateTimeOffset | ISO |
| 28 | `es_vigente` | 2 | Edm.Boolean | pre-calculado |
| 29 | `autoridad_emisora` | 2 | Edm.String (es.microsoft) | libre |
| 30 | `extracted_metadata` | 3 | Edm.String (JSON) | flexible |

**Total v2: 32 campos** (30 originales + `content_hash` + `alternative_urls`). + `inmueble_codigos_base` opcional → 33.

---

## 10. Qué NO está en este schema (intencionalmente)

- **`monto_principal`** → en Capa 3. Densidad 39%, no es caso de filtro de negocio.
- **RFCs de todas las partes como Collection retrievable** → solo el `contribuyente_rfc` principal. Los otros están en Capa 3 (no retrievable como filtros primarios, solo buscables dentro del JSON). Decisión de privacidad: minimizar la superficie de datos personales expuestos por default.
- **Complex types anidados** → todo es plano + JSON stringified en Capa 3. Evita la ceremonia de schema complex types.
- **Campos de compliance específicos** (`cumple_norma_X`, `riesgo_ambiental`, etc.) → fuera de scope de Fase 4A. Si el negocio los pide en Fase 6, se añaden como bump de schema `v2`.
- **Índices separados por `doc_type`** → descartado. Un solo índice con `doc_type` filtrable cubre todos los casos y simplifica el Logic App de Fase 5.

---

## 11. Cómo aprobar / objetar este schema

Opciones del plan (§4A review workflow):
- **Aprobación directa**: nueva sesión de Claude con `"Schema Fase 4A aprobado. Arranca Fase 4B."`
- **Edición directa**: editar este archivo, agregar comentarios `> CAMBIO: X porque Y`, luego pedir a Claude aplicar ediciones.
- **Sesión read-only de discusión**: nueva sesión con prompt tipo "audit" para explorar dudas sin ejecutar nada.
- **Ampliar la muestra**: pedir a Claude descargar 10 PDFs más con criterios específicos y re-correr discovery sin tocar la infra.

Cambios recomendados antes de Fase 4B (por el propio Claude, como honestidad forense):

1. **Ampliar muestra del site 2** — solo 5 docs de FESWORLD, todos de ingeniería, 0 contratos. Antes de materializar el índice, descargar 5-10 docs más del site 2 fuera de FESWORLD para validar que los filtros funcionan.
2. **Muestra de estudio ambiental con n=1 es insuficiente** — los campos específicos (`consultora`, `fase_estudio`, `coordenadas`) se fuerzan desde un solo ejemplo. Si R-09/R-15 dependen de esto, descargar 3-4 estudios más de otras carpetas `11.*` en otros inmuebles antes de decidir promociones a Capa 2.
3. **Validar el manejo de poderes legales** — los 2 docs de poderes legales requirieron `max_completion_tokens=12000` por el volumen de reasoning. En Fase 5 el Logic App debe tener ese budget también, o un fallback de chunking antes del discovery prompt.

---

_Fin del schema propuesto. Este documento + el reporte de discovery son la base para Fase 4B._
