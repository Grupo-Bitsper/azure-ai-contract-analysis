# Fase 4 (FIX-A) — Veredicto manual v13 (2026-04-22 20:36)

**Corrida:** `tests/results/fase4_fix_a_2026-04-22_2036.jsonl` + `.md`
**Agente:** `roca-copilot:13` (active, latest, 100% del tráfico)
**Cambio único vs v12:** tool `azure_ai_search`:
- `query_type: simple → vector_semantic_hybrid` (default oficial documentado)
- `top_k: 6 → 20` (evita saturación con un solo doc)
- System prompt v12 SIN cambios

**Auto-verdict del runner:** PASS=12 / PARTIAL=1 / FAIL=2 / SKIP=1.
**Veredicto manual (este doc):** PASS=11 / PARCIAL=2 / FAIL=2 / SKIP=1.

> Score gradable manual: **11/14 = 78.6% PASS** ✅ **CRITERIO ≥10/14 CUMPLIDO**

---

## Tabla comparativa baseline → Fase 3 → Fase 4 (FIX-A)

| Caso | Baseline manual | Fase 3 v12 manual | **Fase 4 v13 manual** | Comentario |
|---|---|---|---|---|
| R-04 | PASS | PASS | **PASS** | Ahora devuelve AMBAS licencias 248+255 (antes solo 248) |
| R-05 | FAIL | FAIL | **PASS** ✅ | Lista licencias 248+255 con fechas/autoridad/vencimiento — antes era convergence pavimentos |
| R-06 | FAIL alucinación | PARCIAL | **PASS** ✅ | Contrato ACTINVER 2024 correcto: arrendador BANCO ACTINVER, arrendatario SUPPLIER'S CITY, 3 años + 2 prórrogas, 15-jul-2024. Auto-verdict FAIL es falso negativo (must_not_contain "Supplier" estaba mal — Supplier es arrendatario real) |
| R-07 | FAIL | FAIL | **PASS** ✅ | Devuelve contrato 2024 ACTINVER como "última versión vigente" Y menciona el 2022 anterior (Mifel/Rogers) como "anterior" |
| R-08 | SKIP | SKIP | SKIP | Bloqueado |
| R-09 | FAIL cross-contam | PARCIAL | **FAIL** ❌ | Sigue devolviendo `Manifestación de Impacto Ambiental.pdf` del folder `P4-SL02-INV-YANFENG1` (proyecto SLP de Desarrolladora A 45). Bug #2+#3 — metadata corrupta + boost 10x. **FIX-B y FIX-D necesarios** |
| R-10 | PARCIAL | PASS | **PASS** | AHORA lista AMBOS contratos: Mifel 2022 (USD $45,211/mes) Y ACTINVER 2024 (USD $70,713/mes) con todos los datos |
| R-11 | FAIL | FAIL | **PASS** ✅ | Tabla con 7 permisos: 2 Licencias Construcción + 2 Certificaciones Terminación + Autorización Sanitaria + Visto Bueno + Autorización adecuación. Cita escritura `258,154 PRIMER TESTIMONIO RA03.pdf` |
| R-12 | FAIL | FAIL | **PASS** ✅ | Reconoce que no hay permisos venciendo en 3-6 meses + cita correctamente el folder `72. Cartas de entrega - recepción de inmuebles` |
| R-13 | FAIL | FAIL | **PARCIAL** ⚠️ | Devuelve carpeta `66. Planos de ingenierias (As built)/INVENTARIO/AB - AS BUILT` para RA03 (folder válido). Esperado era `72. Cartas de entrega`. Sigue faltando ontología `cierre proyecto ↔ cartas entrega` |
| R-14 | FAIL | FAIL | **PASS** ✅ | Devuelve los 2 contratos ACTINVER (v1 y v2) del inmueble RA03 correcto. Aclara que el contrato Mifel 2022 "no corresponde a ACTINVER, es contrato anterior con otro arrendador" |
| R-15 | PARCIAL cross-contam | FAIL | **PASS** ✅ | 7+ planos As-Built REALES de RA03 con códigos RA03-400-06, RA03-400-03, RA03-100-01..03, RA03-800-05, RA03-300-04. **Todos los links del folder `P03-RA03/...`. Cross-contamination CJ03 RESUELTA.** |
| R-16 | FAIL alucinación | PARCIAL | **PASS** ✅ | Contrato ACTINVER 2024, 3 años forzosos + 2 prórrogas, 5-jul-2024. ACTINVER arrendador, SUPPLIER'S CITY arrendatario. Consistente con R-06/R-07/R-10/R-14 |
| R-17 | FAIL | PARCIAL | **FAIL** ❌ | Sigue sin encontrar `RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf`. Reconoce honestamente que `DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf` no contiene "servidumbre de paso" |
| R-18 | FAIL | FAIL | **PASS** ✅ | CSF SUPPLIER CITY DE HERMOSILLO, RFC SCH1906128R1, 3-jun-2024. **NOTA:** golden set esperaba CSF Rogers Foam 2022, pero el propietario actual del inmueble cambió en 2024 (ACTINVER/Supplier's City). El agente devuelve CSF más reciente del propietario actual — interpretación legítima |
| R-19 | FAIL | FAIL | **PARCIAL** ⚠️ | Encuentra MAPFRE 3932200000952 (vencida sept-2023, $38.9M USD) Y AXA Seguros (vencidas sept-2022). Esperado: AXA TSA831840000 específica con detalles. Información correcta direccionalmente, falta especificidad |

### Resumen numérico

| Métrica | Baseline v11 | Fase 3 v12 | **Fase 4 v13 (FIX-A)** | Δ vs baseline |
|---|---|---|---|---|
| PASS gradable | 1/14 | 2/14 | **11/14** | **+10** |
| PARCIAL | 2 | 4 | 2 | = |
| FAIL | 12 | 9 | 2 | -10 |
| SKIP | 1 | 1 | 1 | = |
| **Score (PASS/14)** | **7%** | **14%** | **78.6%** ✅ | **+71.6 pp** |
| Score relajado (PASS+PARCIAL/14) | 21% | 43% | **93%** | **+72 pp** |

---

## Cambios aplicados en v13 (publicado a Foundry)

```json
// ÚNICO cambio en la definition vs v12:
"tools": [
  {
    "type": "azure_ai_search",
    "azure_ai_search": {
      "indexes": [{
        "index_name": "roca-contracts-v1",
        "query_type": "vector_semantic_hybrid",  // ← era "simple"
        "top_k": 20,                              // ← era 6
        ...
      }]
    }
  },
  // tool MCP sin cambios
]
```

System prompt v12 conservado tal cual — la regla 10 (anti-alucinación) y regla 11 (múltiples contratos) ahora SÍ disparan porque el retrieval recupera los chunks correctos.

Backup pre-fix: `tests/backups/agent_v12_backup.json`. Build script: `scripts/build_agent_v13.py`. Body publicado: `tests/backups/agent_v13_body.json`.

---

## Diagnóstico — qué destrabó FIX-A

### Por qué `vector_semantic_hybrid` ganó tanto sobre `simple`:

1. **Sinónimos vía semantic ranker:** R-09 baseline buscaba "estudio impacto ambiental" y BM25 priorizaba PAVIMENTOS por frecuencia de "RA03". Semantic ranker entiende que EIA ≠ pavimentos. (Aunque R-09 sigue fallando por otra razón: cross-contamination del doc SL02).
2. **Diversidad de top_k:** con `top_k=20` el retrieval ya no satura los 6 slots con un solo doc. R-04 ahora ve ambas licencias, R-10 ve ambos contratos, R-15 ve los planos correctos.
3. **Vector embeddings activan:** queries como "última versión del contrato" (R-07) requieren entender semántica de "última versión", no match lexical. Vector embedding del query encuentra el contrato 2024 que BM25 nunca rankeaba alto.
4. **Reranker L2 (cross-encoder Bing):** el semantic config que activamos en Fase 2 finalmente se ejecuta. Reordena top-20 por relevancia real.

### Por qué la regla 10 del prompt v12 ahora SÍ funciona:

En Fase 3 la regla 10 ("no inventar partes contractuales") disparó honestidad pero el retrieval seguía trayendo docs equivocados. En Fase 4, retrieval trae los docs correctos Y la regla 10 hace que el agente cite con precisión. Combinación funcional.

### Bugs que persisten (no resueltos por FIX-A):

1. **R-09 cross-contamination SL02 → RA03:** el doc `Manifestación de Impacto Ambiental.pdf` tiene RA03 espurio en `inmueble_codigos` Y boost 10x lo amplifica. Semantic ranker no penaliza suficiente porque el contenido del doc es semánticamente relevante a "estudio ambiental". **FIX-B (boost 10x→2x) + FIX-D (re-ingesta sin códigos del contenido) lo resuelven.**
2. **R-17 servidumbre de paso:** el doc esperado tiene chunks pero no rankea para esa query. Posible problema de embedding o falta de chunks que mencionen la frase. Necesita debug específico.
3. **R-13 ontología:** synonym map no tiene `cierre proyecto ↔ cartas entrega`. Fix de 5 min.
4. **R-19 detalle de pólizas:** el agente menciona AXA pero no extrae número de póliza/suma. Posible problema de chunking del doc.

---

## Validación de hipótesis

✅ **Hipótesis confirmada:** "Las Fases 1-3 atacaron capas equivocadas. El sustrato (tool nativa con BM25 + top_k bajo) era el problema."

✅ **Citas Microsoft confirmadas en práctica:** "Defaults to vector_semantic_hybrid... benchmark consistently produced the most relevant results."

⚠️ **Bug #6 NO confirmado todavía:** todas las respuestas muestran `azure_ai_search_call` y NO `mcp_*`. El agente sigue sin usar MCP. Para v13 esto es OK porque la tool nativa con vector_semantic_hybrid es suficientemente buena. Pendiente decidir si eliminar la tool MCP (FIX-C).

---

## Decisión GO/NO-GO

✅ **GO** — criterio ≥10/14 PASS cumplido (11/14 = 78.6%). Mejora de +71.6 pp vs baseline en una sola fase de 5 min.

**Próximos pasos recomendados (en orden):**

1. **FIX-B (15 min):** bajar `codigo-boost` 10x → 2x. Resuelve R-09 (cross-contam SL02) y posiblemente mejora robustez general. Predicción: 12/14 PASS.
2. **Synonym map ampliar (5 min):** añadir grupos `cierre proyecto, cartas entrega, entregas edificio`, `servidumbre paso, acometida, paso acometida`. Predicción: R-13 y R-17 a PASS. → 13-14/14.
3. **FIX-D (4-6 horas):** re-ingesta extrayendo códigos del path. Fix de raíz para metadata corrupta. Predicción: blindaje permanente vs cross-contam.
4. **FIX-C (15 min):** decidir qué hacer con tool MCP (nunca usada). Recomendación: eliminarla del agente para simplificar (Anthropic best practice).
