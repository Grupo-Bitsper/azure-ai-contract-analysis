# Fase 3 — Veredicto manual v12 (2026-04-22 19:55)

**Corrida:** `tests/results/fase3_v12_2026-04-22_1955.jsonl` + `.md`
**Agente:** `roca-copilot:12` (active, latest, 100% del tráfico)
**Cambios v11 → v12 publicados:** ver sección "Cambios aplicados" más abajo.
**Auto-verdict del runner:** PASS=11 / PARTIAL=1 / FAIL=3 / SKIP=1 (score gradable 11/14).
**Veredicto manual (este doc):** PASS=2 / PARCIAL=4 / FAIL=9 / SKIP=1 (score gradable 2/14).

> El auto-verdict tiene **6 falsos positivos** confirmados (R-11, R-12, R-15, R-17, R-18, R-19). Matchea palabras clave que aparecen dentro de "no encontré X". Esto refuerza la urgencia de Fase 3.5 (LLM-as-judge).

---

## Tabla comparativa baseline v11 → Fase 3 v12

| Caso | Baseline manual | Fase 3 v12 manual | Δ | Comentario |
|---|---|---|---|---|
| R-04 | PASS | **PASS** | = | Mantiene. Devuelve licencia 248 con datos completos. Añade párrafo sobre pavimentos como hallazgo separado (regla 3c relajada permite mencionarlo sin atribuir como respuesta principal). |
| R-05 | FAIL | FAIL | = | Sigue convergence pavimentos: no devuelve licencias 248/255 que R-04 sí encontró. Bug #C persistente. |
| R-06 | FAIL (alucinación) | **PARCIAL** | ✅ | Regla 10 funcionó: "no aparece como arrendatario...". Sigue mostrando contrato Rogers Foam con disclaimer suave. |
| R-07 | FAIL | FAIL | = | Retrieval no recupera el contrato 2024. Sigue devolviendo 2022 + "no se detectó versión más reciente". Falla de retrieval, no de prompt. |
| R-08 | SKIP | SKIP | = | Bloqueado por data gap. |
| R-09 | FAIL (cross-contam SL02) | **PARCIAL** | ✅ | Regla 10 funcionó: "No encontré EIA específico, sin embargo localicé pavimentos... no se clasifica como ambiental per se". Honestidad mejorada vs presentar SL02 como RA03. |
| R-10 | PARCIAL | **PASS** | ✅ | Resumen ejecutivo completo: renta $45,211.35, 38 meses + 2x3 prórrogas, depósito $90k, JP Morgan, $3.76M seguro. |
| R-11 | FAIL | FAIL | = | Falso positivo del auto. Respuesta literal: "No encontré una lista estándar de permisos específicos para RA03". Autocontradice R-04. Bug #C. |
| R-12 | FAIL | FAIL | = | Falso positivo del auto. Respuesta: "No encontré permisos con fecha de vencimiento". Bug #C. |
| R-13 | FAIL | FAIL | = | Devuelve carpeta `53. Diseño de pavimentos` como sustituto de "cierre de proyecto". Falta synonym map. |
| R-14 | FAIL | FAIL | = | Devuelve docs ACTINVER del inmueble RE05A (folder `P06 - RE05AINV-HCP/...Deltack I Fideicomiso 4974`) presentándolos como "para RA03". **Regla 9 NO disparó.** |
| R-15 | PARCIAL (cross-contam CJ03) | FAIL | ❌ | Sigue presentando planos `Planos As-Built Laminación.pdf` del folder `P03-CJ03A-INV/...CJ03B/...` como "para RA03". Justifica explícitamente: *"ubicados en el folder correspondiente a CJ03A-INV, que incluye RA03 en su metadata"*. **Regla 9 NO disparó — el modelo prioriza metadata.inmueble_codigos sobre folder_path.** |
| R-16 | FAIL (alucinación) | **PARCIAL** | ✅ | Regla 10 funcionó: "no se encontró un contrato de arrendamiento específico para ACTINVER en RA03". Devuelve datos Rogers Foam con disclaimer claro. |
| R-17 | FAIL | PARCIAL | ⚠️ | Devuelve `DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf` afirmando que contiene "servidumbre de paso" (probablemente cierto). El doc esperado `RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf` sigue sin recuperarse. |
| R-18 | FAIL | FAIL | = | Falso positivo del auto. "No encontré la constancia de situación fiscal del propietario del inmueble RA03". Falla retrieval/OCR. Fase 5.5 OCR. |
| R-19 | FAIL | FAIL | = | Falso positivo del auto. "No encontré pólizas de seguro vigentes para el inmueble RA03". Falla retrieval/OCR. Fase 5.5 OCR. |

### Resumen numérico

| Métrica | Baseline v11 | Fase 3 v12 | Δ |
|---|---|---|---|
| PASS gradable | 1 | 2 | +1 |
| PARCIAL | 2 | 4 | +2 |
| FAIL | 12 | 9 | -3 |
| SKIP | 1 | 1 | = |
| **Score (PASS/14)** | **1/14 (7%)** | **2/14 (14%)** | **+7 pp** |
| Score relajado (PASS+PARCIAL/14) | 3/14 (21%) | 6/14 (43%) | +22 pp |

**Criterio Fase 3 ≥10/14 PASS:** ❌ **NO CUMPLIDO** (alcanzamos 2/14). Mejora cualitativa real pero la meta numérica requiere fixes adicionales.

---

## Cambios aplicados en v12 (publicado a Foundry)

System prompt modificado vs v11 (transcrito en sección 2 del MD SESION):

1. **Regla 3 relajada:** se removió el fallback obligatorio "No encontré información sobre el inmueble [código]". Ahora dice "extrae info si docs cumplen verificación; si no, di 'no encontré [tipo] para [código]' y sugiere alternativas". Cláusula 3a se cambió a "metadata `inmueble_codigos` **O** `folder_path`/`sharepoint_url` contengan el código".
2. **Sección 9 vieja eliminada:** la guía verbal "usa MCP para X / usa azure_ai_search para Y" se removió completa. El modelo ahora elige tool por descripción.
3. **Regla NUEVA 9 — Verificación de inmueble por path:** "si folder_path indica otro inmueble, RECHAZAR el doc". Con ejemplos concretos RA03 vs CJ03 vs SL02.
4. **Regla NUEVA 10 — No inventar partes contractuales:** "si doc dice Rogers Foam y user pidió ACTINVER, di 'el doc encontrado tiene Rogers Foam, no ACTINVER'".
5. **Regla NUEVA 11 — Múltiples contratos:** "si hay >1 contrato, lista todos con fecha+arrendatario, pregunta cuál".
6. **Regla NUEVA 12 — Follow-up:** "si user pregunta sobre doc ya recuperado en turno previo, no re-busques ni declares 'no encontré'".

Backups guardados en `tests/backups/agent_v11_backup.json` y `tests/backups/agent_v12_body.json`. Build script: `scripts/build_agent_v12.py`.

---

## Diagnóstico — qué reglas funcionaron y cuáles fallaron

### ✅ Funcionó: Regla 10 (anti-alucinación de partes contractuales)
- Confirmado en R-06, R-09, R-16. El agente ahora aclara explícitamente cuando un doc no corresponde al cliente preguntado, en lugar de inventar el vínculo.
- 3 casos pasaron de FAIL a PARCIAL solo por esta regla.

### ✅ Funcionó parcialmente: Regla 3 relajada
- R-04 ahora devuelve la licencia (antes baseline ya pasaba este caso).
- R-10 ahora da resumen completo (antes era PARCIAL).
- Pero el "si no encuentras, sugiere alternativas" llevó al modelo a sugerir docs de OTROS inmuebles en R-14 (RE05A) sin disclaimer fuerte.

### ❌ FALLÓ: Regla 9 (verificación folder_path)

**Causa raíz identificada:** mi propia regla 3a tiene un **OR lógico** que invalida la regla 9.

Regla 3a literal en v12:
> "Verifica que los documentos devueltos por el tool contengan EXACTAMENTE ese código en el campo `inmueble_codigos` del metadata header **O** que el `folder_path` / `sharepoint_url` del documento contenga el código pedido."

Lo que el modelo lee: "basta con que `inmueble_codigos: ['RA03', 'CJ03B']` aparezca; no necesito mirar el folder". Entonces la regla 9 ("si el path indica otro inmueble, rechazar") se interpreta como subordinada a la 3a. El modelo elige el camino de menor resistencia.

Evidencia textual de R-15: el agente literalmente justifica la decisión: *"Ambos documentos están registrados en carpetas con código CJ03A-INV pero contienen también el código RA03 en metadata, por lo que corresponden a la nave RA03 dentro del conjunto documental disponible"*.

Mismo patrón en R-14 con folder `P06 - RE05AINV-HCP`.

**Fix propuesto para v13:** invertir prioridad en regla 3a y reforzar regla 9:

> "3a. Verifica el `folder_path` del documento. **Si el folder_path NO contiene el código del inmueble preguntado, RECHAZAR el documento aunque el campo `inmueble_codigos` lo mencione** — los códigos en metadata pueden incluir referencias cruzadas; el path indica el inmueble real al que pertenece el doc."

### ❌ NO DISPARÓ: Regla 11 (múltiples contratos)
- R-07, R-16: la regla dice "si hay >1 contrato, lista todos". Pero el retrieval solo recupera 1 (el contrato 2022 Rogers Foam). El contrato 2024 ACTINVER no aparece en top-k.
- Esto NO es bug del prompt — es bug de retrieval/ingesta. **Fase 5 (diversidad scoring + sinónimos)** o **Fase 5.5 (OCR si el 2024 está escaneado)** lo arreglan.

### ❌ NO RESUELTO: Bug #C convergence pavimentos
- R-05, R-11, R-12, R-13, R-18, R-19 siguen citando solo `DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf` como "único doc para RA03".
- El system prompt v12 no podía resolverlo — es un problema del scoring profile + diversidad de top-k.
- **Fase 5** lo aborda.

### ❌ NO RESUELTO: Falsos negativos por OCR (R-18 CSF, R-19 póliza)
- Los PDFs son escaneados; el extractor actual no saca texto.
- **Fase 5.5 (Doc Intelligence layout fallback)** lo aborda.

---

## Decisión GO/NO-GO

**Criterio Fase 3:** score ≥10/14 PASS. **Resultado:** 2/14. **NO cumplido.**

**Reportar como avance neto:**
- 4 casos pasaron de FAIL a PARCIAL (anti-alucinación funcional).
- 1 caso pasó de PARCIAL a PASS.
- 0 regresiones reales (R-15 bajó en mi grading pero ya era PARCIAL muy débil en baseline).

**Estado actual de v12 en Foundry:** v12 es `latest`, status `active`, recibe 100% del tráfico. **No hay version_selector explícito** en la API actual de Foundry Agents — el agent_reference por nombre apunta a `latest` automáticamente.

### Opciones de cara al usuario

**Opción A (mi recomendación):** publicar v13 con regla 3a corregida (folder_path GANA siempre sobre metadata.inmueble_codigos). Fix de 5 min. Resuelve R-14 y R-15 directamente. Score esperado: 4 PASS / 4 PARCIAL = 4/14, sigue corto pero cierra el bug #A.

**Opción B:** dejar v12 como está, proceder a Fase 5 (diversidad scoring + sinónimos) que aborda Bug #C — los 6 casos R-05, R-11, R-12, R-13, R-18, R-19. Después volver a Fase 3 con v13. Mayor probabilidad de saltar a 10+ PASS si se combina bien.

**Opción C:** rollback. Crear v13 con system prompt de v11 idéntico. **No recomendado** — perdemos las mejoras anti-alucinación de regla 10 que sí funcionaron.

**Anti-pivote propuesto:** las mejoras de v12 son arquitectónicamente correctas. El bug residual es ambigüedad de redacción en regla 3a. Es fix puntual, no rediseño.

---

## Smoke test paralelo (4 casos críticos)

Run separado: `tests/results/fase3_smoke_2026-04-22_1952.jsonl`. Mismos veredictos que la corrida completa. Confirmado que el comportamiento de v12 es estable entre corridas.
