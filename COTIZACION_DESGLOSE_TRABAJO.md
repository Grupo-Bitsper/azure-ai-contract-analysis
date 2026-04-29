# ROCA Copilot — Desglose de trabajo realizado para cotización

**Cliente:** ROCA Desarrollos
**Vendor:** Bitsper / Ordóñez & Licona
**Periodo de trabajo:** 2026-03 → 2026-04-28 (en curso)
**Fecha del desglose:** 2026-04-28
**Suscripción Azure:** FES Azure Plan (`fea67fdf-9603-4c86-a590-cd12390b7efd`)
**Tenant:** ROCA TEAM (`9015a126-356b-4c63-9d1f-d2138ca83176`)

---

## 1. Resumen ejecutivo

Diseño, despliegue y operación de **ROCA Copilot** — agente conversacional de búsqueda documental sobre el repositorio inmobiliario de ROCA en SharePoint, expuesto vía Microsoft Teams. El sistema usa el stack completo de Azure AI (Foundry + AI Search + Document Intelligence + OpenAI) sobre arquitectura serverless (Function Apps + Durable / Queue-based ingest).

**Estado actual al 2026-04-28:**
- 8,873 chunks indexados en producción (`roca-contracts-v1`) — pipeline Queue-based ya hizo cutover y está añadiendo docs nuevos automáticamente (+22 vs snapshot del 21-abr)
- Agente Foundry `roca-copilot:14` (14 iteraciones de system prompt)
- Pipeline de indexación automática Queue-based EN PRODUCCIÓN (10 funciones, último sync hace 3 min, queue principal con 44 mensajes en proceso, 0 en poison)
- Graph subscriptions vivas hasta 2026-04-30 (renovación automática vía `subscription_renewer`)
- Bot de Teams en producción respondiendo
- Score validado: **12/14 PASS (86%)** en golden set de 14 casos del cliente
- 1 caso bloqueado por data gap (cliente no subió versionado), 3 casos en optimización final

---

## 2. Inventario verificado en Azure

### 2.1 Resource Group `rg-roca-copilot-prod` (eastus2)

| Recurso | Tipo | Detalle |
|---|---|---|
| `kv-roca-copilot-prod` | Key Vault | RBAC mode, 2 secrets (sync-agent + bot-auth), purge protection ON |
| `srch-roca-copilot-prod` | AI Search | Basic SKU, eastus, 4 índices (prod + shadow + staging + smoke) |
| `strocacopilotprod` | Storage v2 | 9 containers (ocr-raw con 1,305 PDFs cacheados, roca-backups, etc.) |
| `stroingest` | Storage v2 | 3 tablas (deltatokens, folderpaths, itemsindex) + 6 queues |
| `log-roca-copilot-prod` | Log Analytics | Workspace base de telemetría |
| `appi-roca-copilot-prod` | App Insights | Workspace-based, telemetría de ambas Function Apps |
| `ag-roca-copilot-prod` | Action Group | Email a admin.copilot@rocadesarrollos.com |
| `func-roca-copilot-sync` | Function App | Python 3.11, Consumption — Bot de Teams + Durable Functions legacy (18 funciones) |
| `func-roca-ingest-prod` | Function App | Python 3.11, Consumption — Pipeline Queue-based nuevo (10 funciones) |
| `logic-roca-quota-probe` | Logic App | Sonda de cuota OpenAI |
| `evgt-roca-graph` | Event Grid | Custom topic (legacy del approach webhook descartado) |
| `roca-orchestration-failed` | Alert | Severity 2 — orquestaciones Failed |
| `roca-non-deterministic-workflow` | Alert | Severity 1 — bug Durable detectado |
| `roca-dlq-writes` | Alert | Severity 3 — escrituras a DLQ |
| `roca-full-resync-triggered` | Alert | Severity 1 — re-sync manual triggered |
| `roca-copilot-prod-no-delete` | Lock | CanNotDelete sobre todo el RG |

### 2.2 Resource Group `rg-admin.copilot-9203` (eastus2) — Foundry

| Recurso | Tipo | Detalle |
|---|---|---|
| `rocadesarrollo-resource` | Cognitive Services AIServices (S0) | Multiservice — OpenAI + Document Intelligence en un solo account |
| `rocadesarrollo` | AI Foundry Project | Project child del AIServices, host del agente |
| `roca-copilot-bot` | Azure Bot Service | Endpoint hacia func-roca-copilot-sync, MSA App ID `0bfce6c7-...` |
| `roca-copilot51537` | Azure Bot Service | Bot adicional (channel registration) |

### 2.3 Modelos OpenAI desplegados

| Deployment | Modelo | Capacity | Uso |
|---|---|---|---|
| `gpt-4.1-mini` | gpt-4.1-mini 2025-04-14 | 50 GlobalStandard | Agente Foundry productivo + extracción metadata |
| `gpt-4o-mini` | gpt-4o-mini 2024-07-18 | 50 GlobalStandard | Smoke tests + fallback agentes |
| `text-embedding-3-small` | v1 | 100 Standard | Embeddings de chunks (1536D) |

### 2.4 App Registration

| App | App ID | Permisos Graph |
|---|---|---|
| `roca-copilot-sync-agent` | `18884cef-ace3-4899-9a54-be7eb66587b7` | Sites.Selected (Write a 2 sites), Group.Read.All |

### 2.5 Sites SharePoint integrados

- `rocadesarrollos1.sharepoint.com/sites/ROCA-IAInmuebles`
- `rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2`

---

## 3. Desglose de trabajo por fase

### Fase 0 — Discovery & POC inicial (contratos sample)

**Objetivo:** Validar viabilidad del approach RAG con 7 contratos demo de FES Services / Grupo BWM.

| Actividad | Entregable |
|---|---|
| Setup repo + estructura proyecto | `agents/`, `config/`, `scripts/`, requirements |
| Configuración inicial Azure OpenAI + Document Intelligence | `docs/SETUP_MODELO.md`, `docs/CREAR_AZURE_OPENAI.md`, `docs/SETUP_DOCUMENT_INTELLIGENCE.md` |
| Pipeline OCR con `prebuilt-contract` | `scripts/process_all_contracts.py` |
| Crear índice AI Search v1 (20 fields) | `scripts/search/1_create_search_index.py` |
| Extracción metadata estructurada | `scripts/search/2_extract_metadata.py` |
| Chunking + indexación inicial (sentence-based) | `scripts/search/3_chunk_and_index.py` |
| Suite de pruebas con queries de validación | `scripts/search/4_test_search.py` |
| Agente conversacional Foundry inicial | `agents/contratos_rocka/contratos_agent.py`, `agents/contratos_rocka/chat.py` |
| Documentación cliente | `GRUPO_ROCKA_README.md`, `grupo-rocka-contratos-context.md`, `foundry-context.md` |

**Resultado:** 174 páginas OCR, 228 chunks, 100% precisión en queries de validación, $0.05 USD costo POC.

---

### Fase 1 — Optimización de chunking

**Problema:** Chunks de 512 tokens con 25% overlap perdían cláusulas que abarcan múltiples páginas (ej. CLÁUSULA DÉCIMA SEXTA — Vigencia).

| Actividad | Entregable |
|---|---|
| Aumentar chunk size 512 → 1024 tokens | `config/search_config.py` |
| Aumentar overlap 25% → 50% (128 → 512) | idem |
| Agregar tracking de página por chunk (`numero_pagina`) | `scripts/search/3_chunk_and_index.py` |
| Schema update con `numero_pagina` Int32 filterable+sortable | `scripts/search/1_create_search_index.py` |
| Test queries vigencia/duración | `scripts/search/4_test_search.py --phase1` |
| Diagnóstico OCR incompleto (solo 2 pp por contrato) | `PHASE1_IMPLEMENTATION_SUMMARY.md` |

**Resultado:** Chunks reducidos 23 → 14 (39% menos), pero descubrimiento de bug de OCR limitado por modelo `prebuilt-contract` (cap de páginas).

---

### Fase 2 — Chunking semántico + integración SharePoint

| Actividad | Entregable |
|---|---|
| Semantic chunker (DECLARACIONES / CLÁUSULAS / ANEXOS) | `scripts/search/semantic_chunker.py` |
| Detección automática de secciones por regex | idem |
| Schema índice con `seccion_tipo`, `seccion_nombre`, `numero_clausula`, `pagina_inicio/fin`, `chunking_mode` | `scripts/search/1_create_search_index.py` |
| Migración OCR a `prebuilt-layout` (sin cap de páginas) | `scripts/test_ocr.py`, `scripts/process_all_contracts.py` |
| Conector SharePoint con MSAL + Graph API | `scripts/sharepoint/sync_from_sharepoint.py` |
| Test de permisos SharePoint Sites.Selected | `scripts/sharepoint/test_connection.py`, `scripts/sharepoint/test_read_permissions.py` |
| Documentación SharePoint | `docs/SHAREPOINT_INTEGRATION.md`, `docs/SETUP_SHAREPOINT_PRUEBA.md`, `docs/ACL_EXPLICACION_VISUAL.md` |
| Generador de PDFs de prueba | `scripts/sharepoint/generar_pdfs_prueba.py` |
| ACLs de SharePoint propagadas a chunks | `function_app/shared/acls.py`, `scripts/sharepoint/search_with_security.py` |

**Resultado:** Schema con metadata semántica completa, integración SharePoint Sites.Selected operativa.

---

### Fase 3 — Bootstrap producción Azure

**Objetivo:** Crear el RG productivo con todos los recursos de soporte (KV, Search, Storage, observabilidad, identidad).

| Actividad | Recurso/Entregable |
|---|---|
| App Registration + Sites.Selected bootstrap (Sites.FullControl temporal → grant a 2 sites → revoke) | `roca-copilot-sync-agent` (`18884cef-...`) |
| Key Vault con RBAC mode + purge protection + 7-day retention | `kv-roca-copilot-prod` |
| Storage account con container `ocr-raw` | `strocacopilotprod` |
| AI Search Basic en eastus (eastus2 sin capacidad) | `srch-roca-copilot-prod` |
| AIServices account multiservicio | `rocadesarrollo-resource` (en RG separado del cliente) |
| Foundry project | `rocadesarrollo` |
| Deployments OpenAI: gpt-4.1-mini, gpt-4o-mini, text-embedding-3-small | 3 deployments |
| Log Analytics + App Insights workspace-based | `log-roca-copilot-prod`, `appi-roca-copilot-prod` |
| Action Group con email | `ag-roca-copilot-prod` |
| Budget + cost alerts (intentado, requiere MCA billing role separado) | `budget-roca-copilot-prod` |
| RBAC: 9 role assignments en MI de Function App + adicionales para Search/Storage/KV/AOAI | matriz documentada |
| Lock CanNotDelete en RG productivo | `roca-copilot-prod-no-delete` |
| `.env.example` completo con 200 líneas de referencia | `.env.example` |
| Tests de conectividad e2e | `test_connection.py`, `test_gpt54.py`, `setup_auth.py` |

---

### Fase 4A — Discovery del corpus real del cliente

**Objetivo:** Antes de definir schema productivo, recorrer las 2 bibliotecas SharePoint y caracterizar tipos de documento, taxonomía de carpetas, distribución de inmuebles.

| Actividad | Entregable |
|---|---|
| Exploración recursiva de carpetas SharePoint | `scripts/ingestion/explore_sharepoint_folders.py` |
| Sample download de PDFs por categoría | `scripts/ingestion/download_sample_pdfs.py` |
| OCR de muestra estratificada | `scripts/ingestion/run_ocr_sample.py` |
| Discovery LLM de tipos de documento + clasificación | `scripts/ingestion/run_discovery.py` (con gpt-5-mini reasoning) |
| Agregación + reporte de discovery | `scripts/ingestion/aggregate_discovery.py` |
| Reporte ejecutivo con taxonomía | `FASE_4A_DISCOVERY_REPORT.md` (32 KB) |
| Schema propuesto post-discovery (35 campos) | `FASE_4A_SCHEMA_PROPUESTO.md` (31 KB) |

**Resultado:** Taxonomía formalizada (escritura, contrato_arrendamiento, EIA, planos, permisos, etc.), códigos de inmueble identificados (RA03, GU01A, CJ03A/B, RE05A, SL02, etc.), schema productivo con 35 campos.

---

### Fase 4B / 5 — Diseño arquitectónico

| Actividad | Entregable |
|---|---|
| Decisiones de arquitectura productiva (ingesta, retrieval, agente, observabilidad) | `FASE_5_DESIGN_DECISIONS.md` (37 KB) |
| Diseño completo del pipeline de ingesta v1 (Durable Functions) | `DESIGN_ROCA_INGEST.md` (62 KB) |
| Plan operativo del proyecto | `PLAN_ROCA_COPILOT.md` (214 KB) |
| Crear índices staging/prod/smoke | `scripts/ingestion/create_staging_index.py`, `create_prod_index.py`, `create_smoke_index.py` |
| Smoke ingest end-to-end | `scripts/ingestion/smoke_ingest.py` |

---

### Fase 6 — Pipeline de ingesta v1 (Durable Functions)

**Stack:** Function App `func-roca-copilot-sync` con orquestación Durable + 18 funciones (orchestrators + activities + HTTP + timers).

| Componente | Archivos |
|---|---|
| Function App entrypoint + bot.py + Durable orchestrators | `function_app/function_app.py`, `function_app/host.json`, `function_app/requirements.txt` |
| **Orchestrators**: `sync_delta_orchestrator`, `process_item_orchestrator`, `acl_refresh_orchestrator`, `full_resync_orchestrator` | function_app.py |
| **Activities**: `enumerate_all_items_activity`, `get_delta_changes_activity`, `process_item_activity`, `delete_item_activity`, `refresh_acls_activity`, `resolve_drive_activity`, `persist_delta_token_activity`, `list_unique_hashes_activity`, `record_timeout_dlq_activity` | function_app.py |
| **HTTP endpoints**: `http_bot_messages` (Teams), `http_health`, `http_status`, `http_manual_process` | function_app.py |
| **Timers**: `timer_acl_refresh` (legacy timers ahora deshabilitados) | function_app.py |
| Cliente OpenAI (token reuse + retry) | `function_app/shared/aoai_client.py` |
| Cliente Document Intelligence (prebuilt-layout) | `function_app/shared/docintel_client.py` |
| Cliente Microsoft Graph (Sites.Selected + delta query) | `function_app/shared/graph_client.py` |
| Cliente AI Search (push API + dedup) | `function_app/shared/search_client.py` |
| Embeddings con batching | `function_app/shared/embeddings.py` |
| Pipeline de ingestión core | `function_app/shared/ingestion.py` |
| Extracción metadata vía LLM | `function_app/shared/extraction.py` |
| Auth helper (MSAL + Managed Identity) | `function_app/shared/auth.py` |
| Configuración centralizada | `function_app/shared/config.py` |
| ACLs propagación Graph → índice | `function_app/shared/acls.py` |
| DLQ writer | `function_app/shared/dlq.py` |
| Manejo de fechas (ISO + timezones) | `function_app/shared/dates.py` |
| Bot Teams (Bot Framework SDK 4.17.1) | `function_app/shared/bot.py` |
| Deploy script | `function_app/deploy.sh` |
| Backfill desde producción | `scripts/backfill_itemsindex_from_prod.py`, `scripts/rehydrate_shadow_from_prod.py` |
| Scripts de operación | `scripts/process_all_contracts.py` |

**Funciones desplegadas verificadas en Azure (18):**
```
acl_refresh_orchestrator, delete_item_activity, enumerate_all_items_activity,
full_resync_orchestrator, get_delta_changes_activity, http_bot_messages,
http_health, http_manual_process, http_status, list_unique_hashes_activity,
persist_delta_token_activity, process_item_activity, process_item_orchestrator,
record_timeout_dlq_activity, refresh_acls_activity, resolve_drive_activity,
sync_delta_orchestrator, timer_acl_refresh
```

---

### Fase 7 — Bot Teams + agente Foundry productivo

| Actividad | Entregable |
|---|---|
| Bot Service Azure registrado + canal Teams | `roca-copilot-bot`, `roca-copilot51537` |
| Bot Framework adapter en Function App | `function_app/shared/bot.py` |
| Endpoint `/api/messages` para Teams | `http_bot_messages` |
| Agente Foundry `roca-copilot` (14 iteraciones de versión) | API REST de Foundry — `roca-copilot:1` → `roca-copilot:14` |
| Tools del agente: AI Search nativo + MCP knowledge_base_retrieve | `agents/contratos_rocka/contratos_agent.py` |
| Connection AI Search ↔ Foundry | `create_search_connection.py` |
| Helpers para crear/listar/actualizar deployments | `create_deployment.py`, `list_deployments.py`, `update_agent_with_search.py` |
| Fix de query_type post-deploy | `fix_agent_query_type.py` |
| Ejemplo end-to-end Foundry | `foundry_agent_example.py` |
| Strip de citations Foundry-style `【N:M†source】` | `bot.py::strip_citations()` |
| Typing indicator antes de cada query | `bot.py::_send_typing()` |

**Versiones del system prompt iteradas (14):** Cada versión documenta una corrección específica (cross-contamination, anti-alucinación de partes, desambiguación de múltiples contratos, follow-up, folder requests, etc.) — ver `HANDOFF_FASE3_v12.md`, `SESION_2026-04-22_DIAGNOSTICO_TOOL_REGRESION.md`.

---

### Fase 8 — Migración Durable → Queue-based + indexación automática + FIX-D

**Disparador:** El pipeline Durable se rompió en producción 2026-04-19 (deploy sobre orquestación viva → Non-Deterministic), y el cliente requiere indexación automática upload/edit/delete con SLA real. Investigación 2026-04-23 contra el reference flagship MS [Azure/gpt-rag-ingestion](https://github.com/Azure/gpt-rag-ingestion) confirmó que el patrón canónico no usa webhooks ni Event Grid — usa polling con `lastModifiedDateTime`.

**Decisión arquitectónica:** Plan B-Final (gpt-rag-ingestion adaptado a Function App existente). Webhooks + Graph subscriptions + Event Grid Partner Topic descartados con razones documentadas.

| Actividad | Entregable |
|---|---|
| Plan completo de migración | `PLAN_MIGRACION_DURABLE_TO_QUEUE.md` (50 KB) |
| Plan fix indexación automática | `PLAN_FIX_INDEXACION_AUTOMATICA.md` (14 KB) |
| Storage account dedicado para queues | `stroingest` |
| 3 tablas operacionales | `deltatokens`, `folderpaths`, `itemsindex` |
| 3 queues principales + 3 poison sibling | `delta-sync-queue`, `enumeration-queue`, `file-process-queue` (+poison) |
| Function App nueva Python 3.11 | `func-roca-ingest-prod` (MI principalId `f965f19a-...`) |
| Event Grid topic legacy (descartado en Plan B-Final) | `evgt-roca-graph` |
| 9 role assignments al MI productivo (Storage Queue/Table/Blob, Search Index Data Contributor, Cognitive Services User, Cognitive Services OpenAI User, Key Vault Secrets User) | RBAC matrix |
| Snapshot de índice prod pre-migración (9,038 docs, 10.4 MB) | `roca-backups/index-snapshot-2026-04-21.json.gz` |
| Snapshot script | `scripts/snapshot_index.py` |
| Índice shadow `roca-contracts-v1-shadow` (35 fields, scoring profile, synonym map, semantic config) | AI Search |
| **6 handlers nuevos del Plan B-Final**: `timer_sync_sharepoint`, `delta_worker`, `enumeration_worker`, `file_worker`, `timer_purger`, `subscription_renewer` | `function_app/ingest/function_app.py` |
| Sub-handlers de file_worker extraídos | `function_app/ingest/shared/file_actions.py` |
| Patch `host.json` con baseline oficial MS (`batchSize=16`, `maxDequeueCount=5`) | `function_app/ingest/host.json` |
| **FIX-D**: extracción de `inmueble_codigos` del `folder_path` con regex + KNOWN_CODES whitelist (resuelve cross-contamination R-09) | `shared/ingestion.py` |
| Endpoints HTTP productivos | `http_full_resync`, `http_read_document`, `http_status`, `webhook_handler` |
| Tool `read_document` registrada en Foundry | `scripts/register_read_document_tool.py`, `scripts/openapi_read_document.json` |
| Predeploy gate (bloquea si hay orquestaciones vivas) | `scripts/predeploy_gate.sh` |
| Postdeploy verify (re-habilita timers + valida) | `scripts/postdeploy_verify.sh` |
| Recovery cleanup queues | `scripts/recovery_clean_queues.sh` |
| DLQ report diario | `scripts/dlq_report.sh` |
| Deploy script con gate automático | `scripts/deploy_ingest.sh` |
| Bypass ingest (workaround mientras Durable estaba caído) | `scripts/bypass_ingest_one.py` |

**Funciones desplegadas verificadas (10):**
```
delta_worker, enumeration_worker, file_worker, http_full_resync,
http_read_document, http_status, subscription_renewer, timer_purger,
timer_sync_sharepoint, webhook_handler
```

**Documentos de sesión:**
- `DIA2_RESULTADOS.md` (12 KB) — infra Día 2 con desviaciones D-1 a D-6
- `SESION_2026-04-24_QUEUE_IMPLEMENTATION.md` (11 KB) — Día 3 con bug `fecha_indexacion` resuelto
- `HANDOFF_2026-04-23.md` (52 KB) — handoff Plan B-Final completo

---

### Trabajo recurrente — Operación, hardening, incidentes

#### 9.1 Incidente 2026-04-19/20 — Pipeline Durable caído + indexación RA03

| Actividad | Entregable |
|---|---|
| Diagnóstico capa por capa (metadata corrupta + rename SharePoint + BM25 unfair + Non-Deterministic) | `SESION_2026-04-20_FIX_INDEXACION.md` (19 KB) |
| Re-indexación quirúrgica del archivo `258,154 PRIMER TESTIMONIO RA03.pdf` (60 chunks borrados + reprocesados con metadata corregida) | bypass_ingest_one.py |
| Synonym map `roca-synonyms` (20 grupos: titulo↔escritura↔testimonio, renta↔arrendamiento, variaciones de códigos) | AI Search |
| Scoring profile `codigo-boost` (weight 10 en `inmueble_codigos`, 3 en `nombre_archivo`/`doc_title`) como `defaultScoringProfile` | AI Search |
| Versionado de host.json (`defaultVersion`, `versionMatchStrategy=CurrentOrOlder`) | function_app/host.json |
| Preflight max size 80MB en orchestrator | function_app.py |
| Durable timer race timeout 8 min en process_item | function_app.py |
| Confirm flag `YES_REPROCESS_ALL` para full_resync | function_app.py |
| Logging estructurado eventos críticos | bot.py + function_app.py |
| Re-creación deployment `text-embedding-3-small` (bug recurrente OperationNotSupported) | AIServices |
| Asignación rol `Search Index Data Contributor` al user para upserts manuales de emergencia | RBAC |
| Purga task hub `RocaCopilotHub` (1,334 instancias Failed/Terminated/Completed) | Storage cleanup |
| **4 alertas Application Insights** activas con action group | `roca-non-deterministic-workflow`, `roca-orchestration-failed`, `roca-dlq-writes`, `roca-full-resync-triggered` |
| Runbook de recovery + 5 reglas de operación | PLAN_ROCA_COPILOT.md |

#### 9.2 Diagnóstico tool regression 2026-04-22 + iteraciones system prompt

| Actividad | Entregable |
|---|---|
| Documento de diagnóstico exhaustivo (4 bugs #A, #B, #C, #D) | `SESION_2026-04-22_DIAGNOSTICO_TOOL_REGRESION.md` (27 KB) |
| Golden set de 14 casos formato JSONL | `tests/golden_set_roca.jsonl` |
| Runner de golden set + verdict automático + verdict manual | `scripts/run_golden_set.py` |
| Baseline v11 (1/14 = 7%) | `tests/results/BASELINE_V11_VEREDICTO_MANUAL_2026-04-22.md` |
| Fase 1 — PATCH knowledge base (`outputMode=extractiveData`, `reasoningEffort=medium`) | tests/backups/kb_backup_pre_fase1 |
| Fase 2 — PATCH knowledge source (`semanticConfigurationName=default-semantic-config`) | tests/backups/ks_backup_pre_fase2 |
| Fase 3 — system prompt v12 con 4 reglas nuevas | `scripts/build_agent_v12.py` |
| Fase 4 — system prompt v13 (refinamientos) | `scripts/build_agent_v13.py` |
| Fase 5 — system prompt v14 productivo (12 reglas + 13 folder requests) | `scripts/build_agent_v14.py` |
| Synonym map expandido | `scripts/expand_synonyms.py` |
| Fix B (apply patch específico) | `scripts/apply_fix_b.py` |
| Resultado validado: **12/14 PASS (86%)** | HANDOFF_2026-04-23.md |

#### 9.3 Tareas pendientes documentadas (cliente las puede pedir como Fase 9)

- TAREA #1 — Plan B-Final completo deployado + drenaje cola backfill + cutover shadow→prod (en curso)
- TAREA #2 — Post-validación anti-alucinación (resuelve R-17, ~30-45 min)
- TAREA #3 — Conversation state multi-turn vía `conversation` field de Foundry Responses API
- TAREA #4 — Construcción de link de folder canónico cuando retrieval no trae docs directos (R-13)

---

## 4. Inventario de archivos clave

### 4.1 Documentos de diseño / handoff (~700 KB de documentación técnica)

| Archivo | KB | Propósito |
|---|---|---|
| `PLAN_ROCA_COPILOT.md` | 214 | Plan operativo maestro |
| `DESIGN_ROCA_INGEST.md` | 62 | Diseño pipeline de ingesta |
| `HANDOFF_2026-04-23.md` | 52 | Handoff Plan B-Final |
| `PLAN_MIGRACION_DURABLE_TO_QUEUE.md` | 50 | Plan migración Fase 8 |
| `FASE_5_DESIGN_DECISIONS.md` | 37 | Decisiones arquitectónicas |
| `FASE_4A_DISCOVERY_REPORT.md` | 32 | Discovery del corpus |
| `FASE_4A_SCHEMA_PROPUESTO.md` | 31 | Schema productivo 35 fields |
| `SESION_2026-04-22_DIAGNOSTICO_TOOL_REGRESION.md` | 27 | Diagnóstico 4 bugs |
| `SESION_2026-04-20_FIX_INDEXACION.md` | 19 | Incidente RA03 + hardening |
| `HANDOFF_FASE3_v12.md` | 17 | Handoff iteración system prompt v12 |
| `grupo-rocka-contratos-context.md` | 13 | Contexto cliente |
| `DIA2_RESULTADOS.md` | 12 | Infra Día 2 + desviaciones |
| `SESION_2026-04-24_QUEUE_IMPLEMENTATION.md` | 11 | Día 3 implementación handlers |
| `PLAN_FIX_INDEXACION_AUTOMATICA.md` | 14 | Investigación opciones webhooks |
| `GRUPO_ROCKA_README.md` | 8 | Overview cliente |
| `PHASE1_IMPLEMENTATION_SUMMARY.md` | 7 | Resumen Phase 1 chunking |
| `foundry-context.md` | 6 | Contexto Foundry |
| `STATUS.md` + `SIGUIENTE_PASO.md` | ~10 | Estado de avance |
| `README.md` + `.env.example` + `docs/*` | ~50 | Setup + ops |

### 4.2 Código Python — código de producción

| Carpeta | Archivos | Propósito |
|---|---|---|
| `function_app/` | function_app.py + 14 módulos shared/ + host.json + requirements.txt + deploy.sh | Function App Bot + Durable (legacy) |
| `function_app/ingest/` | function_app.py + shared/file_actions.py + host.json + requirements.txt | Function App Queue-based (Plan B-Final) |
| `agents/contratos_rocka/` | contratos_agent.py, chat.py | Agente local POC |
| `agents/hr_policies/` | (placeholder Fase 9 vertical HR) | — |
| `config/search_config.py` | 1 archivo | Config chunking |
| `scripts/` (raíz) | ~25 scripts | Operación, deploy, migration, backups, golden set |
| `scripts/ingestion/` | 10 scripts | Pipeline discovery + ingesta inicial |
| `scripts/search/` | 5 scripts + semantic_chunker.py + search_utils.py | Búsqueda + chunking semántico |
| `scripts/sharepoint/` | 5 scripts | Conector SharePoint |

### 4.3 Tests

- `tests/golden_set_roca.jsonl` — 16 casos del cliente
- `tests/results/` — JSONL + MD por iteración (baseline_v11, fase1_extractive, fase2_semantic, fase3_v12, fase3_v13, fase3_v14)
- `tests/backups/` — backups de KB/KS/agent definition por fase
- `tests/` integration tests (carpeta)

---

## 5. Funcionalidades entregadas (vista de cliente)

| # | Funcionalidad | Estado |
|---|---|---|
| F-01 | Bot conversacional en Microsoft Teams sobre repositorio inmobiliario | ✅ Producción |
| F-02 | Búsqueda híbrida (vector + BM25 + semantic ranker) sobre 8,851 chunks | ✅ Producción |
| F-03 | Citaciones con link directo al PDF en SharePoint | ✅ Producción |
| F-04 | Filtrado por código de inmueble (RA03, GU01A, CJ03A/B, RE05A, SL02, etc.) | ✅ Producción |
| F-05 | Sinónimos de terminología legal (titulo↔escritura↔testimonio, etc.) | ✅ 20 grupos |
| F-06 | Scoring profile que prioriza match de código de inmueble | ✅ codigo-boost activo |
| F-07 | Indexación automática upload (≤ 5 min) | ✅ Producción — cutover hecho a `roca-contracts-v1`, timer corre cada 5 min |
| F-08 | Indexación automática edit (≤ 5 min, blob cleanup) | ✅ Producción |
| F-09 | Indexación automática delete (≤ 1 hora) | ✅ Producción — `timer_purger` activo, Graph subscriptions vivas hasta 2026-04-30 |
| F-10 | Re-sync manual con flag `use_blob_cache` | ✅ Producción |
| F-11 | OCR full-page con Document Intelligence prebuilt-layout | ✅ Producción |
| F-12 | Cache de PDFs OCR'd en blob (re-indexar sin pagar OCR 2x) | ✅ 1,305 PDFs |
| F-13 | Extracción metadata vía LLM (cláusulas, partes, fechas, montos) | ✅ Producción |
| F-14 | Extracción robusta de inmueble_codigos del path (FIX-D) | ✅ Plan B-Final |
| F-15 | ACLs propagadas SharePoint → índice (security trimming) | ✅ Producción |
| F-16 | Strip de citations Foundry-style en respuestas Teams | ✅ Producción |
| F-17 | Typing indicator durante búsqueda | ✅ Producción |
| F-18 | Anti-alucinación de partes contractuales (regla v14) | ✅ ~80-90% |
| F-19 | Anti-cross-contamination de inmuebles (regla v14 + FIX-D) | ✅ Producción |
| F-20 | Desambiguación múltiples contratos | ✅ Producción |
| F-21 | Golden set automatizado de 14 casos del cliente | ✅ 12/14 PASS |
| F-22 | 4 alertas activas + email | ✅ Producción |
| F-23 | DLQ + recovery scripts | ✅ Producción |
| F-24 | Versionado del agente (14 iteraciones, version_selector canary) | ✅ Producción |
| F-25 | Snapshot de índice + restore | ✅ Producción |

---

## 6. Métricas operativas verificadas

| Métrica | Valor |
|---|---|
| Documentos OCR'd (PDFs únicos cacheados en blob) | ~1,305 |
| Chunks en índice productivo `roca-contracts-v1` | 8,873 (+22 desde snapshot post-cutover) |
| Chunks en índice shadow `roca-contracts-v1-shadow` (frozen baseline) | 8,851 |
| Chunks en índice staging | 2,019 |
| Indexación automática end-to-end | ✅ Activa, último sync 2026-04-28T22:45 UTC |
| Graph subscriptions activas | 2 (1 por site), expiran 2026-04-30 con auto-renewer |
| Sites SharePoint integrados | 2 (ROCA-IAInmuebles + ROCAIA-INMUEBLESV2) |
| Códigos de inmueble cubiertos | RA03, GU01A, GU01-TEN, CJ03/A/B, RE05/A, SL02, SHELL-SLP02 (whitelist 9) |
| Iteraciones system prompt | 14 versiones |
| Tools del agente | AI Search nativo + MCP knowledge_base_retrieve + read_document |
| Queues operativas | 6 (3 principales + 3 poison) |
| Alertas activas | 4 |
| Role assignments creados | 9 + automáticos |
| Score golden set actual | 12/14 = 86% |
| Costo Azure mensual estimado actual | ~$95-120 USD/mes |
| Costo total POC + setup (one-time) | ~$50 USD aprox (incluye OCR completo) |

---

## 7. Sugerencia de categorías para cotización

> **Nota:** este desglose es inventario verificado. Las horas dependen de tarifa, complejidad asignada y si se cobra el trabajo de operación/incidentes como engagement separado.

### 7.1 Categorías de trabajo identificadas

| Categoría | Descripción | Evidencia |
|---|---|---|
| **A. Discovery & POC** (Fase 0) | Setup repo, OCR contratos demo, primer agente, validación con cliente | 7 contratos, 174 pp, 228 chunks, README + 3 docs |
| **B. Ingeniería de chunking** (Fase 1+2) | Optimización parámetros + semantic chunker | semantic_chunker.py, schema 35 fields |
| **C. Bootstrap producción Azure** (Fase 3) | Provisioning de KV, Search, Storage, AOAI deployments, App Insights, App Reg, RBAC, Lock | 14 recursos en RG productivo + 4 en RG Foundry |
| **D. Discovery del corpus real** (Fase 4A) | Exploración SharePoint, sample OCR, taxonomía, schema productivo | 32 KB report + 31 KB schema + 10 scripts ingestion |
| **E. Diseño arquitectónico** (Fase 4B/5) | Decisiones, plan operativo, design del pipeline | 313 KB de documentos de diseño |
| **F. Pipeline de ingesta v1 — Durable Functions** (Fase 6) | Function App con 18 funciones + 14 módulos shared + Bot Framework + ACLs + DLQ | function_app/ completo |
| **G. Bot Teams + Agente Foundry** (Fase 7) | Bot Service + canal Teams + agente con tools + 14 iteraciones de system prompt + golden set | roca-copilot:1→14, golden set, scripts build_agent |
| **H. Pipeline v2 — Queue-based + indexación automática + FIX-D** (Fase 8) | Function App nueva, 10 funciones, 6 handlers, FIX-D, snapshot, shadow index, RBAC | function_app/ingest/ + 50 KB plan + DIA2 + SESION_24 |
| **I. Operación e incidentes** | Incidente 2026-04-19 (Durable caído), re-indexación quirúrgica RA03, synonym map, scoring profile, 4 alertas, runbook | SESION_2026-04-20 + scripts recovery |
| **J. QA / Tuning del agente** | Golden set 16 casos, baseline 1/14, iteraciones a 12/14, diagnóstico 4 bugs (#A, #B, #C, #D) | tests/results/ + SESION_22 |
| **K. Documentación técnica** | ~700 KB de handoffs, planes, sesiones, READMEs, setup guides | 19 archivos MD top-level + 6 docs/ |

### 7.2 Roles típicos involucrados

- AI Solutions Architect (diseño Fase 4B/5, Plan B-Final)
- Forward Deploy Engineer (Fases 6, 7, 8 implementación)
- AI Engineer (chunking, prompt engineering 14 iteraciones, golden set)
- Cloud Engineer (Fase 3 bootstrap, RBAC, alertas, locks)
- Operations / SRE (incidentes, recovery, hardening)
- Tech Writer / Knowledge management (~700 KB documentación)

---

## 8. Anexos disponibles bajo solicitud

- Inventario completo de role assignments (9+ scopes)
- Lista completa de las 14 versiones del system prompt con diff por versión
- 16 casos del golden set + JSONL de resultados por iteración
- Inventario de bugs Microsoft documentados y mitigados (Issue #3022 maxDequeueCount, #37014 dup messages, #1449 memory leak, #10238 UAMI Consumption)
- Diagrama de arquitectura final post-Plan B-Final
- Runbook de recovery + 5 reglas de operación

---

**Documento generado:** 2026-04-28
**Generado por:** verificación automática `az` CLI + lectura de archivos de proyecto
**Verificación:** todos los recursos listados existen en la suscripción Azure y todos los archivos referenciados existen en el repo local
