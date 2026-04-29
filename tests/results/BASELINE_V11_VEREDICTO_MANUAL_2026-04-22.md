# Baseline v11 — Veredicto manual 2026-04-22

**Corrida:** sin middleware (`--no-middleware`), 16 casos, 2 runs (8 + 8 por throttling 429).
**JSONL consolidado:** `baseline_v11_CONSOLIDATED_2026-04-22.jsonl`.
**Importante:** el auto_verdict heurístico del script dio **6 PASS** y **1 FAIL**. Al leer las respuestas completas encontré múltiples falsos positivos. Este documento registra el veredicto MANUAL (yo como judge).

## Score real

| Veredicto | Cuenta | Casos |
|---|---|---|
| PASS genuino | 1 | R-04 |
| PARCIAL | 2 | R-10, R-15 |
| FALLA | 12 | R-05, R-06, R-07, R-09, R-11, R-12, R-13, R-14, R-16, R-17, R-18, R-19 |
| BLOQUEADO | 1 | R-08 |

**Score gradable: 1/14 = 7%** (excluyendo R-08 bloqueado y contando PARCIAL como fail).

Esto confirma la matriz del cliente: **el agente v11 actual está profundamente degradado.**

## Hallazgos nuevos (no estaban en diagnóstico previo)

### Bug #A — Cross-contamination de inmuebles (viola regla 3 del system prompt)
El retrieval trae documentos de OTROS inmuebles sin que el agente lo detecte:

- **R-09:** pregunta EIA de RA03 → devuelve `Manifestación de Impacto Ambiental.pdf` del folder `P4-SL02-INV-YANFENG1` (San Luis Potosí, inmueble SL02). El link lo delata.
- **R-15:** pregunta planos As-Built de RA03 → devuelve `Planos As-Built Laminación.pdf` y `Planos As-Built Montaje.pdf` del folder `P03-CJ03A-INV/66. Planos as built/CJ03B - AS BUILT LAMINACIÓN` (inmueble CJ03). El agente dice "Para RA03, los planos As-Built son..." y lista planos de CJ03.

**Causa raíz:** answerSynthesis del KB pierde el metadata header → el agente no puede aplicar filtrado estricto por código → termina citando docs de cualquier inmueble con cierta similitud semántica.

### Bug #B — Alucinación / invención de clientes (FALSEDADES FACTUALES)
- **R-06:** pregunta contrato ACTINVER → respuesta: *"El contrato de arrendamiento del cliente ACTINVER en el inmueble RA03 tiene un plazo inicial de 38 meses... 20 de mayo de 2022..."* con link al archivo `RA03 Lease Agreement (Signed).pdf`. **El arrendatario real de ese documento es Rogers Foam, no ACTINVER.** El agente inventa el vínculo.
- **R-16:** *"El contrato de arrendamiento del inmueble RA03, con arrendador Banca Mifel y arrendataria ACTINVER..."* **Inventa que ACTINVER es la arrendataria**, cuando en R-07 reconoció que la arrendataria es Rogers Foam. Autocontradicción intra-session.

**Severidad:** crítica. Cliente puede tomar decisiones legales basadas en info falsa.

### Bug #C — Retrieval scope degenerado ("convergence to pavimentos")
Casi todos los casos de fallo terminan respondiendo con el mismo documento: `DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf`. Casos: R-05, R-08, R-11, R-12, R-13, R-17.

**Causa probable:** el índice tiene muchos chunks de ese doc técnico (60 max por doc) y el embedding de "RA03" pesca ese doc por dominancia estadística. El query planner del KB con `reasoningEffort=low` no explora suficiente. Resultado: retriever monomaniaco.

### Bug #D — Tool calls invisibles en el response
El campo `output[].type` solo expone `message` y `mcp_list_tools`. Las invocaciones reales de `knowledge_base_retrieve` y `azure_ai_search` no son visibles en el raw output que el SDK de Responses devuelve al caller. Falta observabilidad — no podemos saber cuál tool invocó el agente en cada caso.

## Veredicto caso por caso (detalle)

### R-04 — PASS (único PASS genuino)
- **Devolvió:** `RA03_LICENCIA DE CONSTRUCCIÓN POR ADECUACIONES.pdf` con licencia 248, expediente 1052/2022, BANCA MIFEL, 326.265 m², link correcto. Contradice la matriz del cliente que decía "no encontré". **Funciona.**

### R-05 — FALLA
- **Esperado:** lista de permisos vigentes con nombre/autoridad/emisión/vencimiento.
- **Actual:** devuelve SOLO el estudio de pavimentos (que ni siquiera es un permiso). No devuelve las licencias 248/255 (aunque R-04 sí las devolvió en otra consulta). **Inconsistencia severa entre queries.**

### R-06 — FALLA (alucinación)
- **Esperado:** plazo del contrato ACTINVER.
- **Actual:** presenta contrato Mifel/Rogers con fechas 2022 como si fuera ACTINVER. Inventa cliente.

### R-07 — FALLA (doc desactualizado)
- **Esperado:** última versión del contrato (2024, ACTINVER).
- **Actual:** devuelve contrato Mifel 2022. El propio path del link delata: `Contrato anterior Rogers Foam / Salida en 2024` — existe un contrato nuevo pero el agente no lo indexa o no lo jerarquiza por fecha.

### R-08 — BLOQUEADO (data gap)
- Correcto decir "no encontré versión anterior para comparar" — no hay versionado.

### R-09 — FALLA (cross-contamination SL02)
- **Esperado:** EIA de RA03.
- **Actual:** EIA de SL02 (San Luis Potosí, inmueble distinto). El link es literal a `P4-SL02-INV-YANFENG1/...`.

### R-10 — PARCIAL
- **Esperado:** resumen ejecutivo con renta, plazo, renovaciones, incrementos, penalizaciones.
- **Actual:** resumen del contrato Mifel/Rogers 2022 (es un contrato válido de RA03). No aclara que hay más versiones. Data correcta pero incompleta.

### R-11 — FALLA (inconsistencia con R-04)
- **Esperado:** tabla con licencias 248 y 255.
- **Actual:** "no se encontraron permisos, solo pavimentos". R-04 sí devolvió 248. **Mismo índice, misma pregunta parafraseada, resultados distintos.** Clásico síntoma de retrieval no-determinista o reranking débil.

### R-12 — FALLA (inconsistencia con R-04)
- **Esperado:** 2 licencias con fechas de vencimiento.
- **Actual:** "no encontré permisos ni fechas". Igual que R-11.

### R-13 — FALLA (sin ontología)
- **Esperado:** link a folder `72. Cartas de entrega`.
- **Actual:** "no encontré carpeta 'cierre de proyecto'". Falta synonym map.

### R-14 — FALLA (contradicción con R-06)
- **Esperado:** LOI/contrato/renovaciones/anexos de ACTINVER.
- **Actual:** "no encontré documentos de ACTINVER, solo pavimentos". **Pero R-06 sí inventó un contrato ACTINVER.** Autocontradicción.

### R-15 — PARCIAL (cross-contamination CJ03)
- **Esperado:** planos As-Built de RA03.
- **Actual:** planos As-Built de CJ03 presentados como si fueran de RA03. Datos estructuralmente válidos (fechas 2024, vigencia) pero del inmueble equivocado.

### R-16 — FALLA (alucinación + autocontradicción)
- **Esperado:** contrato ACTINVER 2024, 3 años + 2 prórrogas.
- **Actual:** "arrendador Banca Mifel y arrendataria ACTINVER, 38 meses, 20-may-2022". Mezcla dos contratos inventando una relación que no existe.

### R-17 — FALLA (retrieval no full-text)
- **Esperado:** `RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf`.
- **Actual:** afirma que el estudio de pavimentos contiene "servidumbre de paso" — probablemente falso, y aunque sea cierto, omite el doc correcto.

### R-18 — FALLA
- **Esperado:** CSF Rogers Foam, RFC RFM030526L6A.
- **Actual:** "no encontré CSF".

### R-19 — FALLA
- **Esperado:** póliza AXA TSA831840000.
- **Actual:** "no encontré pólizas".

## Implicaciones para el plan de fases

Los Fix #1 + #2 (PATCH al KB + semanticConfig) siguen siendo necesarios PERO no suficientes. Los bugs #A (cross-contamination) y #B (alucinación de clientes) requieren:

- **Para #A:** validación post-retrieval — el agente debe verificar el folder_path del doc devuelto contra el código pedido, y rechazar docs con path no-coincidente. Esto NO se logra solo con `extractiveData`; necesita lógica en el system prompt o en el middleware.
- **Para #B:** instrucción explícita en system prompt de no atribuir partes contractuales sin evidencia textual directa del contrato. Considerar desambiguación obligatoria ("encontré 2 contratos para RA03: Mifel/Rogers 2022 y ACTINVER/Suppliers 2024 — ¿cuál quieres?").
- **Para #C:** aumentar diversidad del top-k (mandate distinct `content_hash` o `folder_path`) — evitar que un doc con muchos chunks sature.

## Decisión sobre Fase 0

Fase 0 COMPLETADA. Tenemos baseline numérico:
- **Total casos: 16**
- **PASS genuino: 1 (6.25%)**
- **PARCIAL: 2**
- **FALLA: 12**
- **BLOQUEADO: 1**

**Meta post-Fase 5: ≥14/16 PASS (87.5%).** Delta a cerrar: 13 casos.
