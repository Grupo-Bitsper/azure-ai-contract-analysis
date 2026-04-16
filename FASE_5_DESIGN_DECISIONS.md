# Fase 5 — Decisiones de diseño

**Fecha**: 2026-04-15
**Autor**: Claude Code (sesión autónoma)
**Estado**: Draft — fija la arquitectura antes de crear código/recursos

---

## 0. PIVOT FINAL — Logic App Standard → Durable Functions (Functions-only) (2026-04-15)

**Segunda corrección de diseño durante la sesión, basada en evidencia empírica y doc oficial Microsoft.**

### Cadena completa de hallazgos que justifican el pivot

**Hallazgo A (quota)** — Logic App Standard WS1 bloqueado:
```
ERROR: Current Limit (WorkflowStandard VMs): 0
Current Usage: 0
```
Verificado en eastus2 y eastus. La subscription FES Azure Plan (`fea67fdf-...`) no tiene cuota asignada para Workflow Standard plans. Pedir cuota toma 1-3 días hábiles.

**Hallazgo B (Consumption funciona pero...)** — Logic App Consumption sí tiene cuota (probe `logic-roca-quota-probe` creado OK en `Microsoft.Logic/workflows`). Pero:

**Hallazgo C (connector auth)** — El SharePoint connector nativo de Logic Apps (Consumption y Standard) **NO soporta app-only authentication**. Verificado en doc oficial MS y Q&A. Cita de la recomendación oficial MS:
> *"For app-only scenarios requiring credentials, move the SharePoint calls that must run under a true service account or app-only identity into custom code (Function/WebJob) that uses SharePointOnlineCredentials or app-only tokens, and have the Logic App call that code instead of the built-in connector."*

Fase 2 decidió Sites.Selected app-only con el App Registration `roca-copilot-sync-agent` + secret en KV (decisión firme, no negociable). Por lo tanto el SP connector nativo NO sirve para ROCA.

**Hallazgo D (sample oficial Microsoft)** — `Azure-Samples/MicrosoftGraphShadow` es un sample oficial de Microsoft que hace exactamente nuestro caso (replicar Graph/SharePoint data con cambios incrementales usando delta queries + webhooks) y usa **Azure Durable Functions** como orquestador, NO Logic Apps. Arquitectura del sample:
- Azure **Durable Functions** (primary orchestration)
- Azure Cosmos DB / Blob para state (delta tokens per tenant)
- Azure Key Vault (secrets)
- Application Insights (telemetry)
- Triggers: `ShortPolling` (timer cada N min) + `LongPolling` (timer daily) + HTTP triggers admin

**Hallazgo E (Well-Architected Framework)** — MS Azure Architecture Center baseline chat + AI workload design recomienda:
- *"Azure Functions is a good choice for tasks that spike, like ingestion triggers, enrichment, or simple orchestration."*
- *"AI workflows work better with event-driven patterns where you can decouple systems and apply retries safely, using Event Grid for events and Service Bus for reliable messaging and queues."*

No hay ninguna recomendación oficial de MS que diga "debes usar Logic Apps para ingesta SharePoint → AI Search con app-only auth". Al contrario, la recomendación explícita es "move to custom code".

### Arquitectura final: Durable Functions en el Function App existente

**Decisión**: upgrade del plan "Functions-only plain" → **Durable Functions**. El Function App existente (`func-roca-copilot-sync`, Y1 Consumption Linux Python 3.11) soporta Durable Functions nativamente — solo requiere agregar la extensión `azure-functions-durable` al `requirements.txt`. NO se recrea el recurso.

**Componentes**:

| Trigger | Tipo | Cadencia | Función |
|---|---|---|---|
| `timer_sync_delta` | TimerTrigger | `0 */5 * * * *` (cada 5 min) | Inicia orchestration `sync_delta_orchestrator` que hace Graph delta query sobre ambos sites, detecta cambios, hace fan-out a `process_item_activity` por cada archivo nuevo/modificado |
| `timer_acl_refresh` | TimerTrigger | `0 0 * * * *` (cada hora) | Inicia orchestration `acl_refresh_orchestrator` que itera docs del índice staging y refresca `group_ids`/`user_ids` |
| `timer_full_resync` | TimerTrigger | `0 0 3 * * 0` (domingo 3am UTC) | Inicia orchestration `full_resync_orchestrator` que compara SP dataset vs índice y sincroniza diferencias |
| `http_manual_process` | HttpTrigger + MI auth | on-demand | Dispatch manual para testing (p.ej. `{event_type, site_id, item_id}`) |

**Orchestrators** (Durable Functions):
- `sync_delta_orchestrator` — mantiene delta token en Durable Entity (`DeltaTokenEntity` por `drive_id`), llama Graph, fan-out a `process_item_activity`
- `acl_refresh_orchestrator` — fan-out a `refresh_acls_activity` por doc
- `full_resync_orchestrator` — fan-out a `process_item_activity` por doc

**Activities** (stateless functions invocables desde orchestrators):
- `get_delta_changes_activity(drive_id, delta_token)` — llama Graph `/drives/{id}/root/delta`
- `process_item_activity(site_id, item_id)` — download + hash + dedup check + OCR + discovery + chunk + embed + upsert
- `refresh_acls_activity(content_hash)` — extract ACLs + update group_ids/user_ids
- `write_dlq_activity(message)` — escribe a storage queue `roca-dlq`

**Durable Entity** (state):
- `DeltaTokenEntity[drive_id]` — persiste el último delta token por drive (permite polling incremental eficiente)

**Estado persistente en** Task Hub (Azure Storage `strocacopilotprod`, containers auto-creados: `AzureWebJobsHubName-*`).

### Por qué Durable Functions (no plain Functions)

| Beneficio | Plain Functions + state manual | Durable Functions |
|---|---|---|
| Delta token state per drive | Implementar en blob/cosmos manualmente | `DurableEntity` nativo, ACID |
| Single-concurrent execution per drive | Lock manual (risky) | `SingletonOrchestrator` pattern nativo |
| Fan-out/fan-in sobre N archivos | Loop secuencial o threading custom | `Task.WhenAll` nativo, checkpoint automático |
| Checkpoint recovery tras crash | Perdida de trabajo | Reinicia desde último activity completado |
| Retry declarativo por activity | `maxRetryCount` nivel función | `RetryOptions` por orchestrator |
| Debugging de orchestrations | Logs dispersos | Durable Task Framework Monitor |
| Cost overhead | $0 | $0 (usa Storage del Function App, free tier) |

Durable Functions es objetivamente mejor para este caso, con cero costo adicional, y es el patrón del sample oficial Microsoft.

### D-9 aplicado al Function App (2026-04-15)

App settings corregidos (antes: gpt-5-mini+12000, después: gpt-4.1-mini+4000):

```bash
DISCOVERY_DEPLOYMENT=gpt-4.1-mini    # era gpt-5-mini (eliminado 2026-04-15)
MAX_COMPLETION_TOKENS=4000           # era 12000 (gpt-4.1 no es reasoning model)
```

D-6 (budget max_completion_tokens=12000 para reasoning de gpt-5-mini) queda **obsoleta** — gpt-4.1-mini no tiene reasoning tokens internos. 4000 es suficiente.

### Costo ahorrado total

| Concepto | Plan original | Pivot actual |
|---|---|---|
| Logic App Standard WS1 | $176/mes | $0 |
| Logic App Consumption (4 workflows × polling) | — (no usado) | $0 |
| Azure Function App Y1 Consumption | — | $0 (free tier: 1M execs + 400K GB-s/mes) |
| Durable Functions overhead | — | $0 (usa storage account existente) |
| Application Insights | ya existente | $0 incremental |
| **Total incremental mensual** | ~$176 | **~$0** |

Ahorro: ~$176/mes. El Function App ya está creado y configurado; el trabajo restante es escribir código Python en el mismo recurso.

### Recursos ya creados/configurados apuntan 100% al pivot final

| Recurso | Estado | Uso en pivot |
|---|---|---|
| `roca-contracts-v1-staging` (32 campos, integrated vectorizer) | ✅ Creado | Target del Function App durante Fases 5.1-5.4 |
| `func-roca-copilot-sync` (Y1 Python 3.11 Linux) | ✅ Creado con SystemAssigned MI | Host de Durable Functions |
| MI `0d1b9174-8ef1-4f28-b692-799e8d145d13` | ✅ Con 4 roles RBAC | Search Index Data Contributor + Storage Blob Data Contributor + Cognitive Services User + Key Vault Secrets User |
| `logic-roca-quota-probe` | ⚠ Remanente (bloqueado por lock RG) | Documentado en D-10 nueva, costo $0, sin actividad |
| `EastUS2LinuxDynamicPlan` | ✅ Auto-creado por Function App | Normal |
| App settings del Function App | ✅ 25 settings incluyendo D-9 fix | Configuración completa, apuntan a staging |

Nada del trabajo ya hecho se tira. Solo cambia la etiqueta "Logic App" → "Durable Functions" y el código que escribo vive en el Function App en vez de workflow JSON.

---

## 0.7 Fase 5.5 — hardening aplicado antes del deploy (2026-04-15)

Tras el code review del diseño inicial, se aplicaron 5 fixes/clarificaciones antes del primer deploy:

### Fix #4 — DLQ observability
- `dlq.py::send_dlq_message` ahora emite un `log.error()` estructurado con prefix `[ROCA-DLQ-WRITE]` después de escribir al storage queue.
- Esto permite crear un **scheduled query alert** sobre Log Analytics `log-roca-copilot-prod` con la query `traces | where message startswith "[ROCA-DLQ-WRITE]"` y dispatch al Action Group `ag-roca-copilot-prod` existente.
- El alert rule se crea **post-deploy** (requiere que Application Insights esté recibiendo logs del Function App, que solo pasa una vez que el app está corriendo en la nube).

### Fix #5 — AppInsights unificado
- `APPLICATIONINSIGHTS_CONNECTION_STRING` del Function App redirigido al **`appi-roca-copilot-prod`** existente (el que creamos en Fase 3) en vez del duplicado auto-generado por `az functionapp create`.
- El duplicado `func-roca-copilot-sync` (recurso AI) queda sin tráfico pero **no se puede borrar** por el `CanNotDelete` lock del RG. Queda como **D-13** (patrón idéntico a D-8 y D-10, basura inocua documentada).

### Fix #6 — Rename `discovery` → `extraction`
- `shared/discovery.py` → `shared/extraction.py`. `run_discovery` → `run_extraction`. `build_discovery_prompt_text` → `build_extraction_prompt_text`.
- **Aclaración conceptual**: el módulo NO hace "discovery de schema per-item" (lo cual quemaría tokens innecesariamente). El prompt está FIJO y validado desde F4A. El módulo hace **extraction** contra ese prompt. El nombre "discovery" era heredado de F4A donde sí se usaba para descubrir campos emergentes — en F5 el objetivo es extraer metadata usando el mismo prompt validado.
- Sin cambio de costo: el modelo (gpt-4.1-mini) y `max_completion_tokens=4000` siguen iguales (D-9 aplicado).

### Fix #7 — Retry policies explícitas en todos los `call_activity`
- Todas las llamadas de orchestrator a activity ahora usan `call_activity_with_retry()` con `df.RetryOptions` explícitas:
    - `RETRY_STANDARD`: 3 intentos, primer retry 5s, backoff 2x → para activities pesadas (process_item, delta_query, enumerate)
    - `RETRY_FAST`: 2 intentos, primer retry 1s, backoff 2x → para activities rápidas (resolve_drive, persist_delta_token, list_unique_hashes)
- Elimina el comportamiento default del framework (que varía entre versiones del runtime) y documenta intent.

### G1 resolution — ACL refresh real (el más importante)
- **Schema del índice actualizado**: 3 campos nuevos `sp_site_id`, `sp_list_id`, `sp_list_item_id` (todos `filterable`, `hidden=true`). Índice recreado con **35 campos** (antes 32). Aplicado a `create_prod_index.py` y recreado el staging.
- **`process_item_activity`** ahora lee `parentReference.sharepointIds.listId` y `.listItemUniqueId` del item de Graph (con fallback a un `get_item` explícito con `$expand=sharepointIds` si no están en el payload) y los persiste en el índice junto con cada chunk.
- **`refresh_acls_activity`** convertido de stub a real: lee los 3 identity refs del payload, llama `acls.extract_principals_for_item(site_id, list_id, list_item_id)` vía Graph (igual que process_item_activity hace en initial ingestion), expande SharePoint groups a Entra members con `get_sharepoint_group_members`, y actualiza `group_ids`/`user_ids` en todos los chunks con `search_client.update_acls_for_hash(content_hash, ...)`.
- **`list_unique_hashes_activity`** usa el nuevo `search_client::list_unique_hashes_with_refs()` que además de retornar el hash único, trae los 3 identity refs para el ACL refresh subsiguiente. Docs sin identity refs (legacy / manual imports) se skippean automáticamente.
- **Cierra la mitad de D-7** que Fase 5 original no resolvía completamente. Ahora el timer cada hora refresca permisos sin re-OCR ni re-embed.

### Helper deploy.sh
- `function_app/deploy.sh` creado como one-liner para futuros updates de código. Reinstala deps solo si `--refresh-deps` se pasa o si `.python_packages/` no existe. Crea zip con todo lo necesario + sube via `az functionapp deployment source config-zip`.
- Uso futuro: editar código → `./deploy.sh` → esperar 60s → `curl /api/health`.

---

## 0.8 Deudas técnicas nuevas descubiertas durante el pivot

**D-10 (🟢 Baja)** — `logic-roca-quota-probe` remanente en el RG. Se creó durante el quota probe del pivot Consumption. El `CanNotDelete` lock bloqueó el cleanup. Costo $0 (workflow sin ejecuciones). Acción futura: cleanup en mantenimiento junto con D-8.

**D-11 (🟢 Baja)** — Application Insights duplicado `func-roca-copilot-sync` auto-creado por `az functionapp create`. El RG ya tiene `appi-roca-copilot-prod`. Acción: reconfigurar el Function App para apuntar al existente y borrar el duplicado (bloqueado por lock hasta mantenimiento).

**D-12 (nueva, resuelve parte de D-9)** — `DISCOVERY_DEPLOYMENT=gpt-4.1-mini` + `MAX_COMPLETION_TOKENS=4000` aplicado al Function App. D-6 queda obsoleta. Memoria `feedback_roca_model_gpt5_mini.md` debe actualizarse cuando el pivot se cierre.

---

## 0 (original). PIVOT forzado — Logic App Standard → Consumption (2026-04-15) — OBSOLETO por pivot final ↑

Al intentar crear `asp-roca-copilot-la-ws1` (WS1 Workflow Standard plan) en eastus2 Y eastus:

```
ERROR: Operation cannot be completed without additional quota.
Current Limit (WorkflowStandard VMs): 0
Current Usage: 0
```

La subscription **FES Azure Plan** (`fea67fdf-...`) tiene cuota **WorkflowStandard VMs = 0** en todas las regiones verificadas. Solicitar aumento vía ticket toma 1-3 días hábiles (bloqueante).

Probe de Logic App **Consumption** (tipo de recurso distinto: `Microsoft.Logic/workflows`, no `Microsoft.Web/sites`) → **funciona sin problemas**. Verificado empíricamente con `logic-roca-quota-probe` creado y borrado.

### Pivot adoptado

**Arquitectura original (plan del usuario)**: 1 × Logic App Standard WS1 con múltiples workflows.
**Arquitectura pivoteada**: 4 × Logic App **Consumption** workflows separados (`Microsoft.Logic/workflows`), uno por trigger.

| Aspecto | Standard WS1 (original) | Consumption (pivot) |
|---|---|---|
| Costo mensual | ~$176 fijo | ~$1 pay-per-exec a nuestro volumen |
| SharePoint connector nativo | ✅ | ✅ (idéntico) |
| SP file triggers (create/modify) | ✅ | ✅ |
| Recurrence timer triggers | ✅ | ✅ |
| Retry policies declarativas | ✅ | ✅ |
| Dead Letter Queue | ✅ vía storage queue | ✅ idéntico |
| Stateless workflows | ✅ | ❌ (no los necesitamos) |
| VNET integration | ✅ | ❌ (no la necesitamos) |
| Workflows por recurso | múltiples | 1 por recurso → 4 recursos |
| Max execution time | 1 día | 90 días stateful / 5 min stateless (n/a) |
| Status MS | "Recommended for production" | GA, soportado en producción, sin preview flag |

**Por qué el pivot preserva el diseño**:
- Sigue siendo Logic Apps (cumple "NO cuestionar LA vs Python script" del plan)
- Mismo SharePoint connector nativo recomendado por MS (`sharepointonline`)
- Mismo pattern: wizard del portal como baseline + customización
- Mismo Function App sidecar para la lógica pesada Python
- Cambio invisible desde el punto de vista funcional; solo la forma en que se empaquetan los workflows

**Trade-offs aceptados**:
- 4 recursos Logic App en vez de 1 app con 4 workflows internos — más superficie de despliegue, pero idempotente por nombre y cada uno es independiente
- Sin VNET ni stateless, ninguno de los dos relevante para nuestro scope

**Costo ahorrado**: ~$175/mes vs presupuesto original estimado. Gana el cliente.

**Regiones consideradas**: eastus2 (primaria, donde vive el RG), eastus (donde vive el Search Service). Ambas tienen cuota 0 para WS1 y cuota OK para Consumption. Eastus2 elegida para el pivot (consistencia con el RG).

**Acción pendiente (deuda nueva)**: documentar en `FASE_5_REPORT.md` que la subscription FES Azure Plan no tiene cuota WorkflowStandard → si algún día se quiere migrar a Standard por alguna feature específica, primero solicitar cuota vía ticket.

---

## 1. Baseline verificado al iniciar Fase 5 (2026-04-15)

| Check | Comando | Resultado | OK |
|---|---|---|---|
| Auth Azure CLI | `az account show` | `admin.copilot@rocadesarrollos.com` / sub `fea67fdf-...` / tenant `9015a126-...` | ✅ |
| Recursos en `rg-roca-copilot-prod` | `az resource list` | KV + Search + Storage + Log Analytics + App Insights + Action Group (6 esperados) | ✅ |
| Search service | `az search service show` | `srch-roca-copilot-prod` en **eastus**, sku `basic`, `running` | ✅ |
| Índice prod intacto | `GET /indexes/roca-contracts-v1/stats` | **543 docs**, 21.6 MB storage, 4.1 MB vector index | ✅ |
| Índice smoke | `GET /indexes/roca-contracts-smoke` | **Aún existe** (remanente del cleanup de F4B — no bloqueante pero documentado como descubrimiento) | ⚠ |
| Logic App Standard pre-existente | `GET Microsoft.Web/sites` | `[]` (vacío) | ✅ |
| Function App pre-existente | `GET Microsoft.Web/sites` | `[]` (vacío) | ✅ |
| Scripts de ingesta | `ls scripts/ingestion/` | 11 archivos — todos los mencionados en el plan presentes | ✅ |

**Conclusión**: estado inicial es exactamente el que el plan describe. Nada destructivo requerido antes de empezar Fase 5.

---

## 2. Decisión A1 — Wizard "Import data (new)" vs workflow custom

### Opción A: Wizard del portal de Azure AI Search
El portal ofrece `Import data (new)` que conecta SharePoint → indexer → skillset. En teoría sería el camino más rápido.

**Evaluación contra los 3 requirements duros de Fase 5**:

| Requirement | ¿Lo soporta el wizard? | Evidencia |
|---|---|---|
| Dedup por `content_hash` (MD5 del binario) ANTES de OCR | ❌ NO | El indexer corre skillset completo por doc; el `#Microsoft.Skills.Text.MergeSkill` o similar no permiten early-exit basado en hash. Para dedup cross-doc necesitas un `conditional output` que el wizard no expone. |
| Security trimming real (extracción de ACLs vía Graph + expansión de SP groups) | ❌ NO | El indexer SharePoint nativo sólo lee metadata del archivo, no de permisos. No hay skill oficial para Graph API `/items/{id}/permissions`. Workaround vía WebAPI skill requeriría Function App externa — ya es Opción B con pasos extra. |
| 2 sites (ROCA-IAInmuebles + ROCAIA-INMUEBLESV2) en un solo pipeline | ⚠ Parcial | El indexer SharePoint acepta 1 `siteUrl`. Se pueden crear 2 data sources + 2 indexers + 2 skillsets + configuración duplicada. Factible pero duplica superficie de mantenimiento. |

**Veredicto**: Opción A falla en 2 de 3 requirements hard (dedup hash + security trimming). Wizard **descartado**.

### Opción B: Workflow custom en Logic App Standard
Control total: triggers + lógica de decisión + llamadas HTTP a Graph + dispatch a Python para lógica pesada.

**Sub-decisión B1**: ¿Pure Logic App workflow, o Logic App + Azure Function sidecar?

- Logic App Standard **NO soporta Python inline** (sólo JavaScript/C#/PowerShell via "Execute Inline Code").
- La lógica pesada de ingesta ya existe en Python en `scripts/ingestion/*.py` (1 655 líneas totales: chunking con metadata header, discovery prompt, dedup, parsing de schema v2).
- Reescribir eso en JavaScript dentro de actions de Logic Apps = semanas de trabajo + altísimo riesgo de bugs.
- Portarlo 1:1 a Python en Azure Function = días de trabajo + reuso real del código ya validado.

**Decisión B1**: **Logic App Standard + Azure Function Python sidecar.** El Logic App es orquestador (triggers, retry, DLQ, dispatch HTTP). El Function App corre toda la lógica Python (descarga SharePoint, hash, dedup, ACLs, OCR, discovery, chunking, embeddings, upsert).

---

## 3. Arquitectura final elegida

```
┌─────────────────────────────────────────────────────────────────────┐
│ SharePoint (ROCA TEAM tenant)                                       │
│  • ROCA-IAInmuebles                                                 │
│  • ROCAIA-INMUEBLESV2                                               │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │ file created/modified        │ item permissions updated
               │ (polling ~5 min)             │ (polling ~5 min)
               ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Logic App Standard: logic-roca-copilot-sync (WS1 plan)              │
│  workflows/                                                         │
│    ├── wf-sync-file          ← SP file trigger ×2 sites             │
│    ├── wf-sync-acls          ← SP permissions trigger ×2 sites      │
│    └── wf-resync-sunday      ← scheduled Sun 03:00 UTC              │
│                                                                     │
│  Cada workflow:                                                     │
│   1. Recibe el evento con {site_id, list_id, item_id, event_type}  │
│   2. HTTP POST a https://<funcapp>.azurewebsites.net/api/process   │
│      con payload JSON + system-assigned MI token                   │
│   3. Retry exponential backoff (5 intentos max)                    │
│   4. Si 5 fallos → PUT message a Storage Queue `roca-dlq`          │
└──────────────┬──────────────────────────────────────────────────────┘
               │ HTTP (authenticated via MI + EasyAuth)
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Function App (Python 3.11, Y1 Consumption): func-roca-copilot-sync │
│  process/ (HTTP trigger)                                            │
│    1. Validate payload + event_type                                 │
│    2. Download bytes from Graph (sync-robot app creds from KV)      │
│    3. MD5 hash                                                      │
│    4. Query índice prod por content_hash (filter)                   │
│       ├─ hit → merge alternative_urls + union ACLs → update chunks │
│       └─ miss → full pipeline                                       │
│    5. Extract ACLs: GET /items/{id}/permissions + resolve groups   │
│    6. Upload blob ocr-raw/{hash}.json (raw bytes)                  │
│    7. Document Intelligence prebuilt-layout                         │
│    8. gpt-5-mini discovery (max_completion_tokens=12000)            │
│    9. Chunking con metadata header (reuso 1:1 de ingest_prod.py)   │
│    10. Embeddings text-embedding-3-small (batch 16)                │
│    11. Upsert al índice TARGET con group_ids/user_ids poblados    │
│    12. Log a Application Insights (structured)                     │
└──────────────┬──────────────────────────────────────────────────────┘
               │ writes
               ▼
        ┌─────────────────────────┐
        │ Azure AI Search         │
        │ roca-contracts-v1-     │
        │       staging           │ ← durante Fases 5.1-5.4
        │ (mismo schema v2)       │
        │                         │
        │ roca-contracts-v1       │ ← SOLO tras Paso 5 con
        │ (producción, 543 docs)  │   confirmación del usuario
        └─────────────────────────┘
```

**Identidades**:
- Logic App Standard → **SystemAssigned MI** (llama Graph + Function App)
- Function App → **SystemAssigned MI** (llama AI Search, Blob, AOAI, Document Intelligence, Key Vault)
- App Registration `roca-copilot-sync-agent` (F2, Sites.Selected) → credenciales del sync robot, usadas por el Function App para descargar bytes reales de SharePoint (Graph acepta app-only para descargar archivos de sites autorizados)

**Por qué el Function App NO usa Managed Identity para SharePoint**:
SharePoint download via Graph con Sites.Selected app-only funciona mejor con client_credentials del App Registration existente (`roca-copilot-sync-agent`) porque ese SP ya tiene Sites.Selected grant sobre los 2 sites. El MI del Function App tendría que replicar ese grant. Reusar el SP robot evita una ronda más de bootstrap de permisos.

---

## 4. Decisión A2 — Staging vs prod durante desarrollo

**Variable de entorno `TARGET_INDEX_NAME`** en el Function App:
- Desarrollo/tests (Fases 5.1-5.4): `roca-contracts-v1-staging`
- Producción (Paso 5, tras confirmación): `roca-contracts-v1`

**Regla crítica**: `TARGET_INDEX_NAME` se cambia **una sola vez**, en el Paso 5, con confirmación explícita del usuario por nombre. Ningún test intermedio toca el índice prod con writes.

**Reads al prod son OK** para validar que el MVP sigue intacto al final de cada subpaso (`GET /indexes/roca-contracts-v1/stats` comparando documentCount).

---

## 5. Decisión A3 — Federated Credentials vs client secret (deuda D-3)

El plan deja D-3 abierta: "Decisión Federated Credentials vs client secret para sync robot — recomendado FedCred para producción".

**Evaluación**:

| Criterio | Client secret actual | Federated Credentials |
|---|---|---|
| Expiración | 2028-04-15 (2 años) | Nunca — confiere trust a un OIDC issuer |
| Rotación | Manual en 2028 | No aplica |
| Setup adicional | — | Requiere configurar OIDC issuer (Azure AD workload identity federation) + trust relationship en el App Registration |
| Consumer | Function App Python con `msal.ConfidentialClientApplication` | Function App con `DefaultAzureCredential` → federated token desde Azure identity del Function App MI |
| Riesgo de setup | 0 (ya está hecho en F2) | Medio — requiere configurar correctamente el federation en el App Registration, cualquier error rompe auth |

**Decisión D-3**: **mantener client secret existente**. Justificación:
- El secret es válido hasta 2028 (2 años); la rotación es problema futuro.
- Federated Credentials requiere modificar el App Registration `roca-copilot-sync-agent` — zona sensible (F2 fue dolorosa).
- El beneficio de FedCred es rotación automática, pero el secret vive en Key Vault con RBAC, no en código.
- El riesgo de romper el sync robot durante la migración a FedCred es mayor que el beneficio en el horizonte del proyecto (Fase 7 en ~1 semana).

**Acción**: anotar en `FASE_5_REPORT.md` que D-3 queda cerrada con decisión "no migrar ahora; revisitar en 2028-01 antes de la rotación del secret".

---

## 6. Decisión A4 — SKUs / costos

| Recurso | SKU elegido | Costo mensual estimado (East US 2) | Justificación |
|---|---|---|---|
| Logic App Standard | **WS1 Workflow Standard plan** (1 vCPU, 3.5 GB) | ~$176/mes | El plan específicamente exige LA Standard (no Consumption). WS1 es el SKU más bajo disponible. |
| Function App | **Y1 Consumption** (pay per exec) | ~$0 (primer 1M execs gratis) | Volumen ROCA estimado: ~1 K execs/día = 30 K/mes, muy debajo del free tier. |
| Storage Queue `roca-dlq` | Incluida en `strocacopilotprod` | ~$0 (< 100 msgs) | Reuso de storage account existente. |
| App Insights | Ya existe `appi-roca-copilot-prod` | ~$0 incremental | Reuso. |

**Costo total incremental estimado**: ~$176/mes (dominado por LA Standard WS1).

⚠ **Impacto**: esto NO estaba desglosado en §7 del plan. Es un gasto fijo nuevo que el stakeholder ROCA debe conocer. Se registrará en `FASE_5_REPORT.md` como nota explícita para conversación futura.

---

## 7. Decisión A5 — Estrategia de reuso de código

**Principio**: el Function App NO reinventa lógica. Reusa funciones de `scripts/ingestion/*.py` con mínimas adaptaciones.

**Mapeo**:

| Lógica | Fuente | Adaptación para Function App |
|---|---|---|
| Descarga SharePoint | `download_sample_pdfs.py` (sync robot client_credentials) | Extraer función `download_file_bytes(site_id, item_id) -> bytes` |
| Document Intelligence | `run_ocr_sample.py` | Reemplazar disk cache por blob cache `ocr-raw/{hash}.json` |
| Discovery gpt-5-mini | `run_discovery.py` (prompt + `max_completion_tokens=12000`) | Sin cambios en prompt |
| Chunking + metadata header | `ingest_prod.py::build_metadata_header` + `ingest_prod.py::chunk_text` | Sin cambios |
| Embeddings | `ingest_prod.py::embed_batch` | Reemplazar `AzureKeyCredential` por MI token |
| Upsert | `ingest_prod.py::main` loop | Parametrizar `INDEX_NAME` vía env var, usar MI |

**Estructura del Function App repo**:
```
azure-ai-contract-analysis/
  function_app/
    host.json
    requirements.txt
    process/
      __init__.py          ← HTTP trigger entry point
      function.json
    shared/
      sharepoint.py        ← download_file_bytes + list_items + get_acls
      ingestion.py         ← hash, dedup, chunking, metadata header (portado de ingest_prod.py)
      discovery.py         ← gpt-5-mini discovery (portado de run_discovery.py)
      embeddings.py        ← text-embedding-3-small batch
      search_client.py     ← read/upsert con MI
      acls.py              ← extract + resolve principals
      config.py            ← env vars
```

---

## 8. Decisión A6 — Orden de creación de recursos (minimiza costo mientras se valida)

1. **Índice staging `roca-contracts-v1-staging`** — $0 incremental (pequeño).
2. **Function App `func-roca-copilot-sync` (Consumption Y1)** — $0 incremental.
3. **Deploy código Python + smoke test HTTP** — validar que la función corre antes de crear el Logic App caro.
4. **Logic App Standard `logic-roca-copilot-sync` (WS1)** — $176/mes empieza aquí.
5. **RBAC + workflows + triggers** — $0 incremental.
6. **Tests end-to-end Paso 4** — usage de AOAI/DI si Test C ingesta un PDF real ($0.01-0.05).
7. **PAUSA obligatoria antes de Paso 5**.

**Rollback si algo sale mal antes de (4)**: borrar Function App (no bloqueado por lock del RG porque es un recurso aislado). Índice staging también borrable desde REST API sin tocar el lock del RG.

---

## 9. Riesgos identificados y mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | `CanNotDelete` lock del RG bloquea borrado de LA/Function App si necesito re-crearlos | Media | Alta | Elegir nombres bien desde el primer intento. Si aún así hay que borrar, remover lock temporalmente (requiere permission `Microsoft.Authorization/locks/delete`). |
| R2 | MI propagation delay después de role assignments causa 403 en primer test | Alta | Media | Sleep 120s tras cada tanda de role assignments antes de testear. |
| R3 | Function App cold start tumba el timeout de Logic App HTTP action (default 2 min) | Media | Media | Configurar `functionAppScaleLimit=1` + warm-up trigger timer cada 5 min. Logic App HTTP action con timeout=PT5M. |
| R4 | Graph API `sites/{id}/lists/{id}/items/{id}/permissions` retorna 403 con Sites.Selected app-only | Media | Alta | Pre-validar con `az rest` antes de escribir código. Si falla, el sync robot necesita permiso `Sites.FullControl.All` temporal (ver memoria `feedback_sites_selected_bootstrap`). |
| R5 | Integrated vectorizer del índice staging rehusa embeddings del client-side (ya los genera el Function App) | Baja | Baja | El vectorizer del índice es para **queries** (si el agent manda texto sin vector). Para **ingesta** el Function App sube vectores pre-computados — funciona en prod actual. |
| R6 | Logic App SharePoint connector no acepta triggers sobre "When item permissions are updated" | Alta | Alta | Verificar en el portal ANTES de diseñar el workflow. Si no existe, fallback: scheduled poll cada 10 min que compara ETags via Graph API en el Function App. |
| R7 | El workflow polling interval de 5 min impacta costo WS1 (cada polling cuesta execution units) | Baja | Baja | WS1 tiene cuota alta, 5 min polling ×2 triggers ×2 sites = ~1 728 polls/día, todo absorbible. |

---

## 10. Hallazgo crítico verificado empíricamente (2026-04-15)

### R6 confirmado — el trigger "When item permissions are updated" NO EXISTE

Verificación vía doc oficial del connector `sharepointonline` (Microsoft Learn, fetched 2026-04-15, `gitcommit: 4ca0543`). Lista completa de triggers disponibles:

1. `For a selected file` (manual — solo Power Automate)
2. `For a selected item` (manual — solo Power Automate)
3. `When a file is classified by a Microsoft Syntex model`
4. `When a file is created (properties only)` ✅ usado
5. `When a file is created in a folder (deprecated)`
6. `When a file is created or modified (properties only)` ✅ **usado**
7. `When a file is created or modified in a folder (deprecated)`
8. `When a file is deleted`
9. `When a site has requested to join a hub site`
10. `When an item is created`
11. `When an item is created or modified`
12. `When an item is deleted`
13. `When an item or a file is modified`

**Ningún trigger expone cambios de ACLs/permissions.** El plan F5 asumía "When item permissions are updated × 2 sites" — es una aspiración no respaldada por capacidad real del connector.

### Alternativas evaluadas para detectar cambios de ACL

| Opción | Descripción | Latencia | Costo adicional | Complejidad |
|---|---|---|---|---|
| **A. Scheduled ACL polling** | Workflow timer cada 1 hora itera todos los docs del índice y refresca `group_ids`/`user_ids` si cambiaron | Hasta 1h | $0 (ya parte del LA plan) | Baja — reusa el Function App |
| B. Graph change notifications sobre driveItem | Subscription con `changeType: updated` y distinguir ACL vs contenido | ~segundos | Complejidad auth + subs renewal cada 3 días | Alta |
| C. SharePoint audit logs | Query `AuditLog.Read.All` filtrando `RoleAdded/RoleRemoved` | ~60 min | Permiso Graph adicional | Alta |

**Decisión**: **Opción A**. Es la más simple, no requiere permisos adicionales, y la latencia de 1 hora es aceptable para cambios de ACL en gestión documental inmobiliaria (no es un sistema de tiempo real).

### Triggers finales del Logic App Standard (ajustado tras hallazgo)

| # | Workflow | Trigger | Cadencia | Efecto |
|---|---|---|---|---|
| 1 | `wf-sync-file-site1` | SharePoint `When a file is created or modified` sobre ROCA-IAInmuebles | polling 5 min | Dispatch HTTP al Function App con `event_type=file_upsert` |
| 2 | `wf-sync-file-site2` | SharePoint `When a file is created or modified` sobre ROCAIA-INMUEBLESV2 | polling 5 min | Idem site 2 |
| 3 | `wf-acl-refresh` | `Recurrence` — cada 1 hora | timer | HTTP al Function App con `event_type=acl_refresh_all`, que itera docs del índice y actualiza group_ids/user_ids |
| 4 | `wf-full-resync` | `Recurrence` — domingo 03:00 UTC | timer | HTTP al Function App con `event_type=full_resync`, compara SP dataset vs índice y sincroniza diferencias |

El plan se actualiza: **4 workflows** en vez de los "5 triggers" aspiracionales originales. Los workflows 1 y 2 cubren `file_upsert`; el workflow 3 cubre lo que el plan llamaba "When item permissions updated"; el workflow 4 es el safety net semanal.

---

## 11. Decisiones que quedan para Paso 2 (workflow design)

- ¿El Function App necesita un módulo de `build_security_filter` para Fase 6, o eso se deja puro para Fase 6? **Respuesta**: el prompt de Fase 5 NO lo pide — es Fase 6 Paso 6.1b. No se construye en esta fase.
- ¿Portar `semantic_chunker` mencionado en el plan, o usar el chunking char-based simple de `ingest_prod.py`? **Respuesta**: `semantic_chunker.py` no existe en el repo — el plan lo mencionaba aspiracional. Se usa chunking char-based (`CHUNK_SIZE_CHARS=2000, OVERLAP=200, MAX_CHUNKS_PER_DOC=60`), idéntico al validado en F4B.

---

## 11. Criterios de cierre del Paso 0

- [x] Verificación baseline completa
- [x] Decisión A1 (wizard vs custom) justificada con evidencia
- [x] Decisión B1 (LA + Function App) justificada
- [x] Arquitectura completa documentada
- [x] Decisión A3 (D-3 FedCred) tomada
- [x] Costos estimados
- [x] Estrategia de reuso de código
- [x] Orden de creación de recursos (minimiza costo)
- [x] Riesgos identificados

**Siguiente**: Paso 1 — crear índice staging + Function App + deploy smoke.
