# Fase 5 (FIX-B) — Veredicto manual scoring profile (2026-04-22 21:20)

**Corrida:** `tests/results/fase5_fix_b_2026-04-22_2120.jsonl`
**Agente:** `roca-copilot:13` (sin cambios)
**Cambio:** scoring profile `codigo-boost` del índice `roca-contracts-v1`:
- `inmueble_codigos`: 10.0 → 2.0
- `doc_title`: 3.0 → 2.0
- `nombre_archivo`: 3.0 → 2.0
- `content`: 1.0 (sin cambio)

**Auto-verdict:** PASS=13 / PARTIAL=1 / FAIL=1 / SKIP=1
**Manual:** PASS=12 / PARTIAL=1 / FAIL=2 / SKIP=1

> Score gradable manual: **12/14 = 85.7% PASS** (+1 vs FIX-A)

---

## Tabla comparativa completa

| Caso | Baseline | Fase 3 | Fase 4 (FIX-A) | **Fase 5 (FIX-B)** | Δ vs FIX-A |
|---|---|---|---|---|---|
| R-04 | PASS | PASS | PASS | **PASS** | = |
| R-05 | FAIL | FAIL | PASS | **PASS** | = |
| R-06 | FAIL | PARCIAL | PASS | **PASS** | = (auto FAIL es falso negativo — Supplier es arrendatario real) |
| R-07 | FAIL | FAIL | PASS | **PASS** | = |
| R-08 | SKIP | SKIP | SKIP | SKIP | = |
| R-09 | FAIL | PARCIAL | FAIL | **FAIL** ❌ | = (sigue cross-contam SL02) |
| R-10 | PARCIAL | PASS | PASS | **PASS** | = |
| R-11 | FAIL | FAIL | PASS | **PASS** | = |
| R-12 | FAIL | FAIL | PASS | **PASS** (cita IMSS SIROC vs pavimentos) | mejora cualitativa |
| R-13 | FAIL | FAIL | PARCIAL | **PARCIAL** | = (necesita synonym map) |
| R-14 | FAIL | FAIL | PASS | **PASS** | = |
| R-15 | PARCIAL | FAIL | PASS | **PASS** | = |
| R-16 | FAIL | PARCIAL | PASS | **PASS** | = |
| R-17 | FAIL | PARCIAL | FAIL | **FAIL** ❌ | = (auto PASS es falso positivo — agente dice "no encontré") |
| R-18 | FAIL | FAIL | PASS | **PASS** | = |
| R-19 | FAIL | FAIL | PARCIAL | **PASS** ✅ | **+1** (AXA TSA831840000 con todos los detalles) |

### Score evolución

| Métrica | Baseline | Fase 3 | Fase 4 (FIX-A) | **Fase 5 (FIX-B)** |
|---|---|---|---|---|
| PASS | 1/14 (7%) | 2/14 (14%) | 11/14 (79%) | **12/14 (86%)** |
| PASS+PARCIAL | 3/14 (21%) | 6/14 (43%) | 13/14 (93%) | **13/14 (93%)** |

---

## Análisis caso a caso

### ✅ R-19 destrabado (mejora principal de FIX-B)

Antes (FIX-A): "Encuentro MAPFRE + AXA Seguros vencidas" sin número de póliza específico.

Ahora (FIX-B):
> "1. Póliza emitida por MAPFRE México S.A. con número 3932200000952, vigencia 24-feb-2023 al 1-sep-2023, suma asegurada principal de aproximadamente 38,900,315.86 USD.
> 2. Póliza de obra civil emitida por AXA Seguros, **número TSA831840000**, vigencia 3-jun-2022 al 20-sep-2022, suma asegurada **13,862,001.89 MXN** para obra civil en construcción."

Doc esperado del golden set: `Poliza TSA831840000.pdf` con suma $13.86M MXN, vigencia 3-jun-2022 a 20-sep-2022 (VENCIDA). **Match exacto.**

Por qué FIX-B lo destrabó: bajar el boost de `nombre_archivo` y `doc_title` de 3x a 2x permitió que chunks con el contenido específico (número de póliza, suma) rankearan más alto que chunks con solo el título.

### ✅ R-12 mejora cualitativa

Antes (FIX-A): citaba `DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf` como ejemplo. Ahora cita `SIROC ROCA RA03-TEN (RF).pdf` (registro de obra IMSS, vencido 2022) — semánticamente más relacionado con "permisos que vencen".

### ❌ R-09 NO se resolvió con FIX-B

Sigue devolviendo `Manifestación de Impacto Ambiental.pdf` del folder `P4-SL02-INV-YANFENG1` (San Luis Potosí, proyecto Logistik I de Desarrolladora A 45/Avante 44). El doc tiene `RA03` espurio en `inmueble_codigos` (extraído del contenido OCR via LLM en la ingesta).

**Por qué FIX-B no fue suficiente:** bajar boost de 10x a 2x reduce la prioridad por código pero el semantic ranker L2 (cross-encoder Bing) elige el doc porque su CONTENIDO es semánticamente muy relevante a "estudio de impacto ambiental". Mientras el doc tenga `RA03` en metadata Y contenido relevante a la query, va a aparecer en top-k.

**Solución de raíz:** **FIX-D — re-ingesta extrayendo `inmueble_codigos` del `folder_path`, no del contenido.** Eso eliminaría el RA03 espurio de la metadata del doc SL02 → no aparecería en queries de RA03.

### ❌ R-17 sigue FAIL

Auto-verdict matchea "servidumbre" porque está en la frase "no se encontraron documentos... que mencionen 'servidumbre de paso'". Falso positivo conocido del verdict.

Respuesta real: "No se encontraron documentos específicos del inmueble RA03 que mencionen 'servidumbre de paso' en el contenido textual."

Doc esperado: `RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf`.

Posibles causas (NO confirmado todavía):
1. Synonym map no tiene grupo `servidumbre paso ↔ acometida ↔ paso acometida`
2. El doc puede no tener literal "servidumbre de paso" en chunks (necesita validar)
3. El doc puede ser PDF escaneado sin OCR adecuado (extracted_text < 500 chars)

**Próximo:** validar #2 y #3 con queries directas al índice.

### ⚠️ R-13 PARCIAL persiste

Devuelve carpeta raíz `P03-RA03` sin la subcarpeta canónica `72. Cartas de entrega - recepción de inmuebles`.

**Solución:** synonym map añadir grupo `cierre proyecto ↔ cartas entrega ↔ entregas edificio ↔ entrega recepción inmuebles`.

---

## Costos y rollback

- Costo Azure: $0 (cambio de scoring profile no requiere re-indexación)
- Tiempo invertido: 15 min
- Backup: `tests/backups/index_pre_fix_b.json` (rollback con un PUT)
- Build script: `scripts/apply_fix_b.py`

---

## Decisión GO/NO-GO

✅ **GO** — score mejorado a 12/14 (86%). Sin regresiones. R-19 destrabado limpio.

**Próximos pasos en orden:**

1. **Ampliar synonym map** (5 min) — grupos `cierre proyecto/cartas entrega` y `servidumbre/acometida`. Predicción: R-13 a PASS, R-17 posible PASS si el doc tiene chunks indexados.
2. **Validar R-17 indexación** (15 min) — query directa al índice por `nombre_archivo eq 'RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf'` para ver si tiene chunks con texto.
3. **FIX-D re-ingesta** (4-6 horas) — solo si después de 1+2 R-09 sigue FAIL. Resuelve cross-contamination de raíz para todos los casos similares.
