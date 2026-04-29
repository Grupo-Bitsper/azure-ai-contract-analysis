# ROCA Copilot — Plan de Implementación

**Estado**: Fases 1–9 COMPLETAS y en producción. El agente responde correctamente en Teams ✅, incluyendo queries de detalle (firmantes, notaría, fechas) gracias a Agentic Retrieval con MCP (Fase 8, 2026-04-22). Pipeline de ingesta migrado a queue-based con cutover validado y 84 huérfanos reconciliados (Fase 9, 2026-04-29).
**Última actualización**: 2026-04-29
**Dueño técnico**: Abraham Martínez (`admin.copilot@rocadesarrollos.com`)
**Stakeholders producto**: Moisés Rodriguez, Omar Villa (ROCA)
**Cuenta Azure**: FES Azure Plan (`fea67fdf-9603-4c86-a590-cd12390b7efd`) / Tenant ROCA TEAM SA DE CV (`9015a126-356b-4c63-9d1f-d2138ca83176`)

---

## 📍 Estado actual del proyecto (2026-04-29)

### Progreso por fase

| Fase                                                    | Estado      | Fecha cierre | Notas                                                                                                                                                                                                                                          |
| ------------------------------------------------------- | ----------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fase 1** — Setup base                                 | ✅ Completa | 2026-04-14   | Hardening aplicado 2026-04-15                                                                                                                                                                                                                  |
| **Fase 2** — Permisos SharePoint + Graph                | ✅ Completa | 2026-04-15   | End-to-end validado con client credentials                                                                                                                                                                                                     |
| **Fase 3** — Infraestructura de datos                   | ✅ Completa | 2026-04-15   | Budget diferido a deuda técnica con equipo ROCA                                                                                                                                                                                                |
| **Fase 4A** — Discovery de schema                       | ✅ Completa | 2026-04-15   | 45 PDFs totales / 38 únicos por hash, 17 tipos detectados, schema v2 con 35 campos                                                                                                                                                             |
| **Fase 4B** — Ingesta + validación                      | ✅ Completa | 2026-04-15   | Índice `roca-contracts-v1` con integrated vectorizer, agente `roca-copilot` con gpt-4.1-mini, 4/4 queries validadas end-to-end                                                                                                                 |
| **Fase 5** — Automatización (Durable Functions, legacy) | ✅ Reemplazada | 2026-04-15   | Pipeline original con `func-roca-copilot-sync`. Reemplazado por Fase 9 (queue-based) tras incidente Non-Det 2026-04-19. Timers `isDisabled: true`. Código activo solo para el bot (`http_bot_messages`).                                       |
| **Fase 6** — Validar agente en Playground               | ✅ Completa | 2026-04-15   | Agente validado con queries reales. `build_security_filter` pendiente como deuda                                                                                                                                                               |
| **Fase 7** — Publicación a Teams                        | ✅ Completa | 2026-04-16   | Bot funcional en Teams. Middleware Python en Function App. Foundry Responses API conectado                                                                                                                                                     |
| **Fase 8** — Agentic Retrieval con MCP                  | ✅ Completa | 2026-04-22   | Knowledge base + knowledge source sobre `roca-contracts-v1`, project connection MCP, agente `roca-copilot:11` con tools `[azure_ai_search, mcp]`. Resuelve el caso RA03 (detalles específicos del contenido). **Detalle completo en sección 10** |
| **Fase 9** — Pipeline queue-based + cutover             | ✅ Completa | 2026-04-29   | Nueva Function App `func-roca-ingest-prod` con 10 handlers queue/timer. Cutover ejecutado 2026-04-28 21:05 UTC. 84 huérfanos reconciliados al prod 2026-04-29. **Detalle completo en sección 11**                                              |

### Inventario de recursos creados (Fases 1–7)

**Resource group `rg-roca-copilot-prod`** (eastus2, tag `project=roca-prod`, CanNotDelete lock `roca-copilot-prod-no-delete`):

| Recurso                                   | Nombre                                | Región       | MI principalId | Fase   | Costo mensual                                         |
| ----------------------------------------- | ------------------------------------- | ------------ | -------------- | ------ | ----------------------------------------------------- |
| Key Vault RBAC + purge protection         | `kv-roca-copilot-prod`                | eastus2      | —              | F2     | ~$0.03/10K ops                                        |
| AI Search **Basic** + Semantic Std        | `srch-roca-copilot-prod`              | **eastus** ⚠ | `c9181743-...` | F3     | **~$75/mes**                                          |
| Storage V2 LRS Hot (bot + ocr cache)      | `strocacopilotprod`                   | eastus2      | `c39ba7f1-...` | F3     | ~$1-2/mes                                             |
| Container (storage)                       | `ocr-raw`                             | —            | —              | F3     | incluido                                              |
| **Storage account ingest pipeline**       | `stroingest`                          | eastus2      | —              | **F9** | **~$1/mes** (queues + tables)                         |
| 6 queues ingest (3 prod + 3 poison)       | `delta-sync-queue`, `enumeration-queue`, `file-process-queue` + poison | — | — | F9 | incluido       |
| Tables ingest (state)                     | `deltatokens`, `folderpaths`, `itemsindex` | —      | —              | F9     | incluido                                              |
| Log Analytics                             | `log-roca-copilot-prod`               | eastus2      | —              | F3     | ~$2-5/mes                                             |
| Application Insights (workspace-based)    | `appi-roca-copilot-prod`              | eastus2      | —              | F3     | incluido en Log Analytics                             |
| Action Group (email)                      | `ag-roca-copilot-prod`                | global       | —              | F3     | $0                                                    |
| **Function App bot (Durable, legacy)**    | `func-roca-copilot-sync`              | eastus2      | `0d1b9174-...` | F5     | **$0** Y1 Consumption. **Solo bot activo** — timers `isDisabled: true` post-F9 |
| **Function App ingest (queue-based)**     | `func-roca-ingest-prod`               | eastus2      | `a8bd493e-...` | **F9** | **$0** Flex Consumption (10 handlers: 3 queue workers, 3 HTTP, 3 timer, 1 webhook) |
| App Service Plan auto                     | `EastUS2LinuxDynamicPlan`             | eastus2      | —              | F5     | incluido                                              |
| App Service Plan ingest                   | `ASP-rgrocacopilotprod-d9c3`          | eastus2      | —              | F9     | incluido                                              |
| Event Grid Topic (legacy, abandonado)     | `evgt-roca-graph`                     | eastus2      | —              | F9 plan B descartado | $0 (sin subscriptions) |
| Logic App probe (residual)                | `logic-roca-quota-probe`              | eastus2      | —              | F5     | $0                                                    |
| Azure Bot Service                         | `roca-copilot-bot`                    | global       | —              | **F7** | **$0** (F0 free tier)                                 |
| 4 alertas Log Analytics                   | `roca-orchestration-failed`, `roca-non-deterministic-workflow`, `roca-dlq-writes`, `roca-full-resync-triggered` | — | — | F5/F9 | incluido |

⚠ `srch-roca-copilot-prod` vive en `eastus` (no eastus2) porque eastus2 retornó `InsufficientResourcesAvailable` para SKU Basic el 2026-04-15. Mismo RG, latencia cross-region irrelevante.

**Entra ID (tenant ROCA TEAM `9015a126-356b-4c63-9d1f-d2138ca83176`)**:

| Recurso                                    | IDs                                                                                       | Permisos                                                                                                  | Fase |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---- |
| App Registration `roca-copilot-sync-agent` | appId `18884cef-ace3-4899-9a54-be7eb66587b7`, spId `c14b0ac5-1f88-4eaf-860a-c96354267d86` | Sites.Selected + Group.Read.All (admin consent)                                                           | F2   |
| Secret en KV                               | `kv-roca-copilot-prod/roca-copilot-sync-agent-secret`                                     | Válido hasta 2028-04-15                                                                                   | F2   |
| SharePoint sites autorizados               | `ROCA-IAInmuebles` + `ROCAIA-INMUEBLESV2`                                                 | Write                                                                                                     | F2   |
| App Registration `roca-teams-bot-auth`     | appId `0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44`                                              | Sin Graph perms — solo autenticación Bot Framework (client credentials → `api.botframework.com/.default`) | F7   |
| Secret bot (App Setting, NO en KV)         | `BOT_APP_PASSWORD` en `func-roca-copilot-sync` App Settings                               | `<SECRET-EN-KEYVAULT-kv-roca-copilot-prod>` (40 chars exactos, sin prefijos)                               | F7   |

**AIServices `rocadesarrollo-resource`** (RG externo `rg-admin.copilot-9203`, eastus2 — proyecto Foundry `rocadesarrollo` vive ahí):

| Deployment                   | Modelo                 | Version      | SKU            | Capacity | Uso                                          | Costo mensual estimado         |
| ---------------------------- | ---------------------- | ------------ | -------------- | -------- | -------------------------------------------- | ------------------------------ |
| `gpt-4.1-mini`               | gpt-4.1-mini           | `2025-04-14` | GlobalStandard | 50K TPM  | Agente RAG + extracción metadata en pipeline | **~$5-15/mes** (pay-per-token) |
| `gpt-4o-mini`                | gpt-4o-mini            | —            | GlobalStandard | 50K TPM  | Disponible, sin uso activo                   | $0                             |
| `text-embedding-3-small`     | text-embedding-3-small | `1`          | Standard       | 100K TPM | Embeddings de chunks en pipeline             | **~$0.50-1/mes**               |
| Foundry agent `roca-copilot` | gpt-4.1-mini           | —            | —              | —        | Agente publicado a Teams                     | incluido en gpt-4.1-mini       |

⚠ **Historial de cambios de modelo (2026-04-15)**:

- `gpt-4o` fue eliminado (costo alto para el cliente)
- `gpt-5-mini` fue desplegado y luego eliminado del account por conflicto de capacity al desplegar gpt-4o-mini/gpt-4.1-mini (D-9)
- **Estado actual**: `gpt-4.1-mini` es el ÚNICO modelo chat activo para TODO (agente + pipeline de extracción). `max_completion_tokens=4000` (NO 12000 — gpt-4.1-mini no es reasoning model)

**Foundry project MI** (`rocadesarrollo`): principalId `8117b1a5-5225-4d9e-9071-ee9aa90b7eb0`, permisos Graph `GroupMember.Read.All` + `User.Read.All` (asignados, pendientes de validación runtime en Fase 6). **Fase 8** agregó `Search Index Data Reader` sobre `srch-roca-copilot-prod` (necesario para que la knowledge base use MI auth contra el índice).

**Recursos Fase 8 — Agentic Retrieval (creados 2026-04-22)**:

| Recurso | Identificador | Notas |
| --- | --- | --- |
| Knowledge Source (AI Search) | `roca-knowledge-source` | Wrapper sobre el índice `roca-contracts-v1`. Expone 8 sourceDataFields incluyendo `nombre_archivo`, `sharepoint_url`, `inmueble_codigo_principal`, `content` |
| Knowledge Base (AI Search) | `roca-knowledge-base` | LLM `gpt-4.1-mini` para query planning, `outputMode=answerSynthesis`, `retrievalReasoningEffort=low` |
| Project Connection (Foundry) | `roca-knowledge-mcp` | Tipo `RemoteTool` + auth `ProjectManagedIdentity`, target `srch-…/knowledgebases/roca-knowledge-base/mcp`, audience `https://search.azure.com/` |
| Foundry Agent Version | `roca-copilot:11` | Tools `[azure_ai_search, mcp(knowledge_base_retrieve)]`. `agent_endpoint.version_selector` → 100% a v11 |
| RBAC adicional | `Cognitive Services OpenAI User` para search MI sobre `rocadesarrollo-resource` | Necesario para que el knowledge base llame al LLM de query planning |

**Costo delta Fase 8**: ~$0-5/mes (free tier 50M agentic tokens cubre uso ROCA típico de ~17M/mes).

**Archivos del repo**:

- `/Users/datageni/Documents/ai_azure/.env.example` — referencia completa de Fases 1+2+3 (sin secretos)
- `/Users/datageni/Documents/ai_azure/.gitignore` — defensivo
- `/Users/datageni/Documents/ai_azure/azure-ai-contract-analysis/.gitignore` — repo real, `.env` ignorado

### Deuda técnica

| #    | Item                                                 | Estado      | Severidad | Detalle                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---- | ---------------------------------------------------- | ----------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D-1  | Budget $300/mes con alertas 50%/90%                  | ⏸ Abierta   | 🟡 Media  | Requiere que el Billing Account Owner del MCA asigne `Cost Management Contributor` al usuario técnico. Depende de equipo ROCA, no técnico.                                                                                                                                                                                                                                                                   |
| D-2  | Validación MI Foundry project                        | ✅ Resuelta | —         | El agente funciona en playground con el índice → MI validada implícitamente.                                                                                                                                                                                                                                                                                                                                 |
| D-3  | FedCred vs client secret sync robot                  | ✅ Cerrada  | —         | Decisión: mantener client secret (válido hasta 2028-04-15). FedCred es riesgo innecesario en este horizonte.                                                                                                                                                                                                                                                                                                 |
| D-4  | Rotación secret sync robot                           | ⏸ Operativa | 🟢 Baja   | Recordatorio: rotar antes de 2028-04-15. Secret vive en KV `kv-roca-copilot-prod`.                                                                                                                                                                                                                                                                                                                           |
| D-5  | RBAC del Function App MI                             | ✅ Resuelta | —         | 6 roles asignados: Search Index Data Contributor, Storage Blob Data Contributor (account), Storage Queue Data Contributor (account), Cognitive Services User, Key Vault Secrets User.                                                                                                                                                                                                                        |
| D-6  | max_completion_tokens gpt-5-mini                     | ✅ Obsoleta | —         | gpt-5-mini eliminado. gpt-4.1-mini usa 4000 tokens (no es reasoning model, no quema tokens internos).                                                                                                                                                                                                                                                                                                        |
| D-7  | Security trimming en `roca-contracts-v1`             | ⚠ Parcial   | 🟡 Media  | **Fase 5 resolvió la ingesta**: el pipeline SÍ puebla `group_ids`/`user_ids` via Graph API. **Fase 6.1b NO hecha**: el custom function tool `build_security_filter(user_id)` que ENFORCE el filtrado en query-time no está construido. Sin ese tool, el agente retorna todos los docs a cualquier usuario. **Aceptable para pruebas internas** donde todos ven todo. **Bloquea deploy a usuarios externos.** |
| D-8  | Role assignments redundantes en search service       | ⏸ Abierta   | 🟢 Baja   | Bloqueado por `CanNotDelete` lock del RG. Son aditivos, no causan daño. Cleanup en mantenimiento futuro.                                                                                                                                                                                                                                                                                                     |
| D-9  | gpt-5-mini eliminado del account                     | ✅ Resuelta | —         | Todo el código usa gpt-4.1-mini. Scripts, Function App, y agente actualizados.                                                                                                                                                                                                                                                                                                                               |
| D-10 | `logic-roca-quota-probe` residual                    | ⏸ Abierta   | 🟢 Baja   | $0 costo, sin ejecuciones. Bloqueado por lock del RG.                                                                                                                                                                                                                                                                                                                                                        |
| D-11 | AppInsights duplicado `func-roca-copilot-sync`       | ⏸ Abierta   | 🟢 Baja   | Telemetría redirigida a `appi-roca-copilot-prod`. Recurso duplicado sin tráfico, bloqueado por lock.                                                                                                                                                                                                                                                                                                         |
| D-15 | Concurrency limitada a 1                             | ⏸ Abierta   | 🟡 Media  | `maxConcurrentActivityFunctions=1` para evitar 429 de Azure OpenAI (50K TPM). Si ROCA aumenta la cuota del deployment `gpt-4.1-mini`, se puede subir a 2-3 para mayor velocidad.                                                                                                                                                                                                                             |
| D-16 | Packages pinneados                                   | ⏸ Operativa | 🟢 Baja   | `openai==1.55.3`, `azure-functions-durable==1.2.8`. Actualizar periódicamente con testing.                                                                                                                                                                                                                                                                                                                   |
| D-17 | `build_security_filter` custom function tool         | ⏸ Pendiente | 🟠 Alta   | Fase 6.1b. Necesario para que el agente filtre resultados por usuario (cada usuario solo ve docs a los que tiene permiso en SharePoint). **Obligatorio antes de exponer el agente a usuarios que NO deben ver todos los docs.**                                                                                                                                                                              |
| D-18 | `BOT_APP_PASSWORD` debe moverse a Key Vault          | ⏸ Abierta   | 🟡 Media  | Actualmente el secret vive en App Settings (texto plano). Moverlo a KV (`kv-roca-copilot-prod`) y referenciar desde App Settings como `@Microsoft.KeyVault(SecretUri=...)` elimina el riesgo de que el CLI corrompa el valor.                                                                                                                                                                                |
| D-19 | Logs de debug del bot en producción                  | ⏸ Abierta   | 🟢 Baja   | `function_app.py` y `shared/bot.py` tienen logs detallados (`[BOT]`, `[BOT-HTTP]`, `[BOT-REPLY]`) que generan ruido en Application Insights. Reducir nivel a DEBUG y filtrar en queries KQL una vez el bot esté estable en producción.                                                                                                                                                                       |
| D-20 | Pipeline `process_item_activity` OOM (exit code 137) | ✅ Resuelta | —         | Resuelto en F9: bot y pipeline ya están separados en 2 Function Apps distintas (`func-roca-copilot-sync` solo bot, `func-roca-ingest-prod` solo ingest). Preflight `>80MB → skip` + Document Intelligence split por `pypdf` siguen activos en el handler nuevo.                                                                                                                                              |
| D-21 | Delta token avanza aunque haya errores en el batch   | ✅ Obsoleta | —         | Pipeline Durable reemplazado por queue-based en F9. La nueva pipeline retiene mensajes en `file-process-queue` con `maxDequeueCount=5` antes de mandar a poison. El delta token solo avanza tras `delta_worker` enquoue exitoso.                                                                                                                                                                              |
| D-22 | Procesamiento fan-out por lotes para >500 items      | ✅ Obsoleta | —         | Pipeline Durable reemplazado en F9. Queue-based scalea naturalmente con `batchSize=4` y `maxDequeueCount=5`. Sin payload gigante en historial.                                                                                                                                                                                                                                                                  |
| D-23 | `http_full_resync` HTTP endpoint devuelve 404        | ⏸ Abierta   | 🟢 Baja   | Verificado 2026-04-29: POST `/api/admin/full-resync` → 404 aunque la función está registrada en `/admin/functions`. Otros 3 HTTP endpoints OK (status, read_document, webhook/graph). Probable conflict con reserved path `/api/admin/*` o cache de routes. **Workaround:** encolar mensajes manualmente a `enumeration-queue` con `az storage message put` (validado 2026-04-29).                              |
| D-24 | `roca-contracts-v1-shadow` index zombie              | ⏸ Cleanup   | 🟢 Baja   | Shadow index quedó sin uso post-cutover (F9). Tiene 8,851 docs sin vectores (`vectorIndexSize: 0` por bug del rehydrate script). Cero costo extra ($75/mes Basic ya pagado). Borrar después de 1-2 semanas de validación: `curl -X DELETE -H "api-key: $KEY" .../indexes/roca-contracts-v1-shadow?api-version=2024-07-01`                                                                                       |
| D-25 | Bug en `scripts/rehydrate_shadow_from_prod.py:195`   | 📝 Documentado | 🟢 Baja | El script hace `prod.search(search_text="*")` SIN `select=` explícito → SDK omite campos `retrievable: false` (incluido `content_vector`). El upload al shadow incluyó `content_vector: None` para todos los 9,038 chunks → vectorIndexSize:0. **No fixear** — el script ya no debe correr nunca más; F9 reemplazó el patrón completo. Documentado por si alguien intenta replicar.                          |
| D-26 | `acta-entrega-trabajo.pdf` (0 bytes) en SP            | ⏸ Cliente  | 🟢 Baja   | Detectado en F9 reconciliación: drive_item_id `0153D4Q72K3KZCBOGIIZBL5GAMLNJB` en SP tiene size=0 → Document Intelligence falla → 5 retries → poison queue. **Cliente debe re-subir o borrar el archivo.**                                                                                                                                                                                                  |

---

## ⚙️ Operaciones — Cómo funciona el pipeline en producción (F9 — queue-based)

### Flujo normal (steady state)

```
Cada 5 min: timer_sync_sharepoint (en func-roca-ingest-prod)
             └─ Por cada drive: GET delta link desde deltatokens table
             └─ Graph delta query → items modificados/borrados/renombrados/movidos
             └─ Encola UN mensaje por item al delta-sync-queue
             └─ Persiste new_delta_link a deltatokens table

Trigger queue: delta_worker (consume delta-sync-queue)
             └─ Clasifica el evento: upsert / rename / move / delete / folder_rename
             └─ Encola al file-process-queue con action=<tipo>

Trigger queue: file_worker (consume file-process-queue, batchSize=4)
             └─ Dispatcher por action:
                  upsert         → handle_upsert: download + dedup_check (content_hash) + OCR + extract + chunk + embed + upsert al índice + crea entry en itemsindex
                  rename         → handle_rename: lookup itemsindex → patch_document_fields(nombre_archivo, sharepoint_url)
                  move           → handle_move: lookup itemsindex → patch_document_fields(folder_path)
                  delete         → handle_delete: lookup itemsindex → delete_by_content_hash + cleanup itemsindex
                  folder_rename  → fan-out a N moves vía itemsindex.list_descendants
             └─ maxDequeueCount=5 → poison queue tras fallos

Cada 3 días 03:00 UTC: subscription_renewer
             └─ Crea + renueva Graph subscriptions para webhook/graph
             └─ Expiration target = now + 60h

Cada hora: timer_purger
             └─ Reconcilia índice prod vs SharePoint
             └─ Detecta huérfanos (items en índice que ya no están en SP) → batch DELETE
             └─ Guardrails: skip si itemsindex vacío o si >50% sería huérfano
```

**Configuración crítica** (en `func-roca-ingest-prod` app settings):

```
TARGET_INDEX_NAME=roca-contracts-v1   ← cambiado en cutover 2026-04-28 21:05 UTC
                                       ← antes apuntaba a roca-contracts-v1-shadow (legacy F9 day 3)
SP_HOSTNAME=rocadesarrollos1.sharepoint.com
SP_APP_ID=18884cef-ace3-4899-9a54-be7eb66587b7
DOC_INTEL_MODEL=prebuilt-layout
EMBED_DEPLOYMENT=text-embedding-3-small
DISCOVERY_DEPLOYMENT=gpt-4.1-mini
PREFLIGHT_MAX_SIZE_MB=80              ← skip docs grandes para evitar OOM
MAX_ENUM_ITEMS=10000
INGEST_STORAGE_ACCOUNT=stroingest
DELTA_SYNC_QUEUE=delta-sync-queue
FILE_PROCESS_QUEUE=file-process-queue
ENUMERATION_QUEUE=enumeration-queue
TABLE_DELTATOKENS=deltatokens
TABLE_FOLDERPATHS=folderpaths
TABLE_ITEMSINDEX=itemsindex
```

### Cómo subir un documento nuevo y que se indexe

1. Subir el PDF a cualquiera de los dos sites de SharePoint (`ROCA-IAInmuebles` o `ROCAIA-INMUEBLESV2`)
2. Esperar máximo **5 minutos**
3. `timer_sync_sharepoint` detecta el cambio en delta query → encola en `delta-sync-queue`
4. `delta_worker` clasifica como upsert → encola en `file-process-queue`
5. `file_worker` ejecuta `handle_upsert`: download → OCR → embed → indexa al prod
6. El agente en Foundry y bot Teams ya pueden responder preguntas sobre ese doc

**Latencia SLA:** upload/edit/rename/move ≤ 5 min; delete ≤ 1 hora (timer_purger fallback).

### Estado del índice (2026-04-29 — post-Fase 9 reconciliación)

| Métrica                                                  | Valor                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| Chunks en `roca-contracts-v1` (PROD)                     | **11,232** (creció +2,194 en F9 reconciliación)              |
| Storage size                                             | 323 MB                                                       |
| Vector index size                                        | **87 MB** (era 58 MB pre-F9)                                 |
| Chunks únicos por archivo (chunk_id=0)                   | 1,114 archivos únicos                                        |
| Inmuebles con código ROCA indexado                       | 32+ códigos únicos                                           |
| Sites sincronizados                                      | `ROCA-IAInmuebles` + `ROCAIA-INMUEBLESV2`                    |
| Graph subscriptions activas                              | 2 (una por drive, expiran cada 2.5 días, auto-renueva)       |
| Delta tokens activos                                     | 2 (uno por drive en `deltatokens` table)                     |
| `itemsindex` table entries                               | 1,588 (drive_id+drive_item_id → content_hash mapping)        |

**Índices secundarios (no usados en producción):**
- `roca-contracts-v1-shadow` — 8,851 docs sin vectores (zombie post-F9 cutover, D-24)
- `roca-contracts-v1-staging` — 2,019 docs (testbed)
- `roca-contracts-smoke` — 162 docs (smoke tests F4B)

---

## 🔧 Runbook de incidentes del pipeline

### Runbook activo (post-Fase 9 queue-based)

#### Force re-enumeration de un drive (workaround para D-23 http_full_resync 404)

```bash
# Encolar mensaje directo a enumeration-queue. El enumeration_worker enumera
# el drive completo via Graph y encola UN upsert por archivo a file-process-queue.
# El handle_upsert hace dedup por content_hash → solo procesa los faltantes.
# Idempotente: correr N veces produce el mismo resultado.

source venv/bin/activate
python3 <<'PY'
import json, uuid, base64, subprocess
from azure.storage.queue import QueueClient
key = subprocess.check_output(["az","storage","account","keys","list",
  "--account-name","stroingest","--resource-group","rg-roca-copilot-prod",
  "--query","[0].value","-o","tsv"], text=True).strip()
conn = f"DefaultEndpointsProtocol=https;AccountName=stroingest;AccountKey={key};EndpointSuffix=core.windows.net"
qc = QueueClient.from_connection_string(conn, "enumeration-queue")

# Site IDs (verificados en /api/status)
DRIVES = [
    {"site_id": "rocadesarrollos1.sharepoint.com,1fc5e500-0a8a-4631-9037-f83195ac7617,fb4f41ac-732b-4b9d-ab14-24dd18f3cbb9",
     "drive_id": "b!AOXFH4oKMUaQN_gxlax2F6xBT_src51LqxQk3Rjzy7lxm5V1kkkhS7e5-pH5h276"},
    {"site_id": "rocadesarrollos1.sharepoint.com,bb6f7d7f-c5ff-4f68-8a6c-05775b3661bd,7ca4e7eb-b066-411d-b826-f8f63a6b23e0",
     "drive_id": "b!f31vu__FaE-KbAV3WzZhvevnpHxmsB1BuCb49jprI-C9M2JHU1-MRJFrBHHF7EV0"},
]
cid = str(uuid.uuid4())
for d in DRIVES:
    payload = {**d, "reason": "manual_resync", "correlation_id": cid,
               "target_index": "roca-contracts-v1"}
    qc.send_message(base64.b64encode(json.dumps(payload).encode()).decode())
print("done, correlation_id:", cid)
PY
```

#### Verificar estado del pipeline

```bash
INGEST_KEY=$(az functionapp keys list --name func-roca-ingest-prod \
  --resource-group rg-roca-copilot-prod --query "masterKey" -o tsv)
curl -sS "https://func-roca-ingest-prod.azurewebsites.net/api/status?code=$INGEST_KEY" | python3 -m json.tool
```

Devuelve: `target_index`, `queue_depths` por queue, `delta_tokens` con `last_sync_utc` y `subscription_expires_utc`.

#### Limpiar poison queue tras incidente

```bash
# Inspeccionar primero qué hay en poison
source venv/bin/activate
python3 <<'PY'
import subprocess, base64, json
from azure.storage.queue import QueueClient
key = subprocess.check_output(["az","storage","account","keys","list",
  "--account-name","stroingest","--resource-group","rg-roca-copilot-prod",
  "--query","[0].value","-o","tsv"], text=True).strip()
conn = f"DefaultEndpointsProtocol=https;AccountName=stroingest;AccountKey={key};EndpointSuffix=core.windows.net"
qc = QueueClient.from_connection_string(conn, "file-process-queue-poison")
for m in qc.peek_messages(max_messages=10):
    p = json.loads(base64.b64decode(m.content).decode())
    print(f"  action={p.get('action')} name={p.get('name','?')[:60]}")
# qc.clear_messages()  # descomentar para limpiar
PY
```

#### Cambiar TARGET_INDEX_NAME (cutover entre índices)

```bash
# Riesgo: el módulo Python en memoria cachea el valor — restart obligatorio
az functionapp config appsettings set --name func-roca-ingest-prod \
  --resource-group rg-roca-copilot-prod \
  --settings TARGET_INDEX_NAME=<nombre-índice>
az functionapp restart --name func-roca-ingest-prod --resource-group rg-roca-copilot-prod
sleep 45  # cold start
# Verificar
curl -sS "https://func-roca-ingest-prod.azurewebsites.net/api/status?code=$INGEST_KEY" | python3 -c "import json,sys;print(json.load(sys.stdin)['target_index'])"
```

---

### Histórico de incidentes pre-F9 (legacy Durable Functions, info de referencia)

Los siguientes incidentes ocurrieron en el pipeline **legacy F5 Durable Functions** (`func-roca-copilot-sync`). Ese pipeline fue **reemplazado completamente por F9 queue-based** (`func-roca-ingest-prod`). Sus timers están `isDisabled: true`. Se mantienen aquí solo como referencia histórica de las lecciones aprendidas que motivaron la migración a queue-based.

| Fecha | Incidente | Causa raíz | Resolución |
|---|---|---|---|
| 2026-04-16 | Pipeline stopped, queue bloqueada por mensajes stale del `full_resync` | `az functionapp stop` mid-orchestration → mensajes work-items zombi referenciando blobs expirados | Stop+vaciar queue+terminate orchestrations+restart. Lección: nunca stop con orchestrations Running |
| 2026-04-17 | Solo 5 inmuebles indexados, 95% de docs en DLQ | Deployment `text-embedding-3-small` corrupto (`OperationNotSupported` aunque portal mostraba `Succeeded`) | Delete+recreate deployment + clear DLQ + trigger full_resync. Bug recurrente del embedding en Azure OpenAI |
| 2026-04-19 → 04-20 | Pipeline caído ~26h por non-deterministic workflow | Deploy sobre orchestration `Running` + bug `_is_compatible_version("")` con raise antes de yield | Orchestration versioning GA (Q1 2026) activado + `predeploy_gate.sh` obligatorio + retry policies + activity timeouts via durable timer |
| 2026-04-22 → 04-23 | Cross-contamination entre inmuebles + alucinación de partes contractuales | System prompt v11 sin reglas de verificación folder_path | Iteración v12-v15 del system prompt. 12/14 PASS golden set. Migración a Agentic Retrieval (F8) resolvió "doc found but can't answer details" |

**Fixes permanentes que sobreviven post-F9** (aplican al sistema actual aunque vengan del pipeline legacy):

- Document Intelligence split por páginas (50 págs/batch via `pypdf`) en `shared/docintel_client.py`
- Preflight filter PDFs >80 MB (skip + log)
- Sincronización de borrados SharePoint → AI Search por `content_hash` (no `sp_list_item_id`)
- `inmueble_codigo_principal` ordering: códigos ROCA primero, catastrales al final
- Bug de vigencia: `es_vigente=None` cuando falta `fecha_vencimiento`, `_compute_end_from_duration()` para "36 meses"

---

### REGLAS DE OPERACIÓN (sistema queue-based actual)

1. **NUNCA modificar `TARGET_INDEX_NAME` sin restart de la Function App**. El módulo Python en memoria cachea el valor; sin restart sigue escribiendo al índice viejo.
2. **NUNCA borrar `roca-contracts-v1` (prod)**. Hacer cambios siempre via re-enumeration sobre el mismo índice o via cutover a un nuevo índice (cambiar TARGET).
3. **NUNCA correr `scripts/rehydrate_shadow_from_prod.py`**. Tiene un bug conocido (D-25) que copia docs sin vectores. Si necesitas inicializar un índice desde cero, usa el flujo de enumeration_worker normal.
4. **SIEMPRE verificar `/api/status` post-deploy** del Function App ingest. `target_index` debe ser `roca-contracts-v1`, queues en 0 o cifras razonables.
5. **NUNCA lanzar full re-enumeration sin verificar dedup**. El `handle_upsert` SÍ tiene dedup por `content_hash`, así que es seguro encolar enumeration para ambos drives — los archivos sin cambios reales se saltan instantáneamente.

---

#### Apéndice — Detalles del incidente 2026-04-16 (legacy)

**Causa raíz**: stop manual de la Function App (`admin.copilot@rocadesarrollos.com`, 01:50 UTC) mientras el `full_resync` estaba a mitad de ejecución. Esto dejó cientos de mensajes `process_item_activity` en la queue `rocacopilothub-workitems` de storage. Al reiniciar, esos mensajes bloqueaban los nuevos mensajes del timer (los mensajes del 01:21 eran FIFO-primero y referenciaban blobs ya expirados → 404 → nadie avanzaba).

**Síntomas**:

- Function App en estado `Stopped` en el portal
- Orquestaciones `sync_delta_orchestrator` en estado `Running` pero sin avanzar más allá de `TaskScheduled resolve_drive_activity`
- `dequeueCount=0` en todos los mensajes de la `work-items` queue

**Procedimiento de recuperación**:

```bash
# 1. Levantar la app
az functionapp start --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod

# 2. Vaciar la work-items queue (elimina mensajes stale)
STORAGE_KEY=$(az functionapp config appsettings list \
  --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod \
  --query "[?name=='AzureWebJobsStorage'].value" -o tsv | \
  grep -oP 'AccountKey=\K[^;]+')
az storage message clear --queue-name "rocacopilothub-workitems" \
  --account-name strocacopilotprod --account-key "$STORAGE_KEY"

# 3. Terminar todas las orquestaciones Running (zombies + stuck)
MASTER_KEY=$(az functionapp keys list \
  --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod \
  --query "masterKey" -o tsv)
BASE="https://func-roca-copilot-sync.azurewebsites.net/runtime/webhooks/durabletask"
curl -s "${BASE}/instances?taskHub=RocaCopilotHub&connection=Storage&code=${MASTER_KEY}&top=100" | \
  python3 -c "import json,sys; [print(i['instanceId']) for i in json.load(sys.stdin) if i['runtimeStatus']=='Running']" | \
  while read id; do
    curl -s -o /dev/null -w "$id → %{http_code}\n" -X POST \
      "${BASE}/instances/${id}/terminate?taskHub=RocaCopilotHub&connection=Storage&code=${MASTER_KEY}&reason=cleanup"
  done

# 4. Restart para flush de estado interno
az functionapp restart --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod

# 5. Verificar: esperar el próximo ciclo del timer (máx 5 min) y confirmar
# que aparece una nueva instancia con runtimeStatus=Running y lastUpdatedTime avanzando
```

**Lección aprendida**: nunca hacer `az functionapp stop` mientras hay orchestrations `Running`. Drain primero con timers deshabilitados.

---

#### Apéndice — Detalles del incidente 2026-04-17 (legacy, embedding bug)

**Causa raíz**: El deployment `text-embedding-3-small` (Standard, 100K TPM) retornaba `OperationNotSupported` para **todas** las versiones de API. El deployment aparecía como `Succeeded` en el portal pero era funcionalmente inoperante. Como consecuencia, ~95% de los documentos fallaban en el paso de vectorización y se enviaban al DLQ sin indexarse. Los 5 inmuebles que sí funcionaban tenían sus vectores de una carga manual previa (Fase 4B).

**Síntomas**:
- El agente solo encontraba 5 inmuebles (RA03, GU01A, RE05A, CJ03A, SL02)
- DLQ con 32+ mensajes, todos con error `OperationNotSupported`
- `curl` directo al endpoint de embeddings con API key fallaba igual
- Índice con 1505 chunks totales pero solo ~300 con vectores válidos

**Procedimiento de recuperación**:

```bash
# 1. Borrar el deployment corrupto
az cognitiveservices account deployment delete \
  --name rocadesarrollo-resource \
  --resource-group rg-admin.copilot-9203 \
  --deployment-name text-embedding-3-small

# 2. Recrear el deployment
az cognitiveservices account deployment create \
  --name rocadesarrollo-resource \
  --resource-group rg-admin.copilot-9203 \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small \
  --model-version "1" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 100

# 3. Verificar que funciona (debe devolver vector de 1536 dims)
AOAI_KEY=$(az cognitiveservices account keys list \
  --name rocadesarrollo-resource --resource-group rg-admin.copilot-9203 --query key1 -o tsv)
curl -s -X POST \
  "https://rocadesarrollo-resource.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-10-21" \
  -H "api-key: $AOAI_KEY" -H "Content-Type: application/json" \
  -d '{"input": ["test"]}' | python3 -c "import json,sys; r=json.load(sys.stdin); print('OK dims:', len(r['data'][0]['embedding']))"

# 4. Limpiar DLQ
STORAGE_CONN=$(az functionapp config appsettings list \
  --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod \
  --query "[?name=='AzureWebJobsStorage'].value" -o tsv)
az storage message clear --queue-name roca-dlq --connection-string "$STORAGE_CONN"

# NOTA: el procedimiento legacy ya no aplica — pipeline reemplazado en F9
```

---

### Corrección adicional aplicada en Fase 4B post-smoke (2026-04-15)

**Bug crítico de vigencia encontrado por el usuario en el playground**: la query _"¿Qué licencias tenemos vencidas?"_ devolvió incorrectamente que la licencia RA03 de Ramos Arizpe (emitida 2021-10-04 con vigencia 36 meses) estaba "vigente". Causa raíz: el discovery original extraía `duracion_texto: "36 meses"` pero NO calculaba `fin_iso`, y el código de ingesta tenía un fallback buggy que marcaba `es_vigente=True` automáticamente cuando faltaba `fecha_vencimiento`.

**Fix aplicado** (sin hardcoding de fechas):

1. **`ingest_prod.py`** — quitar el fallback `es_vigente=True` automático. Sin fecha_vencimiento explícita → `es_vigente = None` (desconocido).
2. **`ingest_prod.py`** — nueva función `_compute_end_from_duration()` que calcula `fecha_vencimiento` sumando `duracion_texto` (parseando "36 meses", "730 días", "2 años", etc.) a `fecha_inicio` o `fecha_emision`. El modelo reconoce la duración pero no hace la aritmética — la hacemos en código.
3. **`ingest_prod.py`** — `_normalize_date()` ahora valida y rechaza placeholders malformados del modelo tipo `2021-__-__` o `2021-XX-XX`.
4. **`ingest_prod.py`** — `build_metadata_header()` ahora incluye `fecha_procesamiento` como referencia temporal "aproximadamente hoy" sin hardcoding. El agente la usa para calcular vigencia dinámicamente contra `fecha_vencimiento`. Cuando Fase 5 re-ingeste los docs periódicamente, esta fecha se actualiza automáticamente.
5. **`run_discovery.py`** — prompt actualizado con instrucción explícita de calcular `fin_iso` cuando el doc dice "VIGENCIA X meses/días/años" (aunque el fix principal lo hace el código Python como backstop).
6. **`run_discovery.py`** — cambio de modelo de `gpt-5-mini` a `gpt-4.1-mini` (D-9). `max_completion_tokens` bajó de 12000 a 4000 (sin reasoning tokens).

**Validación post-fix**: la misma query que el usuario reportó ahora devuelve:

- _"Licencia RA03 Ramos Arizpe: Fecha vencimiento 4 octubre 2024. Estado: Vencida (no vigente al 15 de abril de 2026)"_ ✅
- _"Licencia GU01-A Tlaquepaque: Fecha vencimiento 19 abril 2025. Estado: Vencida (no vigente al 15 de abril de 2026)"_ ✅

Costo del fix: ~$0.06 USD (re-discovery 20 docs + re-embeddings 543 chunks).

---

## 🚨 REGLA DE ORO DEL DEPLOYMENT 🚨

**La publicación del agente a Microsoft Teams / M365 Copilot es el ÚLTIMO paso del proyecto, JAMÁS antes.**

**ANTES** de publicar a cualquier canal donde lo vea el cliente, TODA la matriz R-01 a R-19 debe estar **100% validada en Azure AI Foundry Playground**. Sin excepciones.

Principio del equipo: _"Cuando deployemos algo, lo único que debemos hacer es picar un botón para que acabe en Teams"_. Esto significa:

- Toda complejidad, validación e iteración se absorbe en las fases previas
- La fase de publicación es trivial (un toggle, un click, un smoke test)
- **El cliente NUNCA ve el agente a medio camino** — solo ve el producto final ya validado
- Si encontramos bugs en playground → iteramos en playground → NO publicamos hasta que todo pase
- La publicación es de una sola dirección: no hay "despublicar y arreglar y republicar"

**Esta regla define el orden de fases del plan.**

---

## 1. Qué estamos construyendo

Un **agente inteligente de Azure AI Foundry** que responde preguntas sobre la documentación de inmuebles de ROCA almacenada en SharePoint, publicado en **Microsoft Teams**.

### Analogía simple

Es un **bibliotecario inteligente** que:

1. Vive dentro de Microsoft Teams
2. Tiene acceso a una biblioteca privada (los 2 sitios de SharePoint con docs de inmuebles)
3. Cuando alguien pregunta _"permisos vigentes de RA03"_, busca en la biblioteca indexada, encuentra los documentos relevantes, los lee, y responde con la info + liga al original

### Dominio

Gestión documental de inmuebles de ROCA (real estate). Inmuebles identificados con códigos tipo `RA03`. Documentos en scope: permisos de construcción, contratos de arrendamiento, estudios de impacto ambiental, planos arquitectónicos As-Built, pólizas de seguro, constancias fiscales, LOIs, renovaciones, anexos.

### Data sources (SharePoint)

- `https://rocadesarrollos1.sharepoint.com/sites/ROCA-IAInmuebles`
- `https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2`

### Canales de despliegue

- Microsoft Teams (canal principal — requisito R-03)
- Microsoft 365 Copilot (requisito R-03)

### Agente en producción

**`roca-copilot`** en el Foundry project `rocadesarrollo` (eastus2). Modelo: `gpt-4.1-mini`. Tool: `AzureAISearchTool` → `roca-contracts-v1` con `query_type=vector_semantic_hybrid`, top_k=6. Connection: `roca-search-prod` (authType=AAD). Publicado a Teams con Shared scope vía Azure Bot Service (2026-04-15).

> **Nota histórica**: el plan original referenciaba `asst_I1unL8WG7qDjaz8nNJ0PCkkw` (API legacy Assistants, no existía en Foundry v2). El agente smoke `roca-copilot-smoke` y el índice `roca-contracts-smoke` fueron creados y borrados durante F4B. El agente actual `roca-copilot` fue creado desde cero con las lecciones del smoke test.

---

## 2. Arquitectura

```
 ┌──────────────────────────────────────────────────────────────┐
 │                    Microsoft Teams (Shared scope)             │
 │                        (Usuario final)                        │
 └────────────────────────────┬─────────────────────────────────┘
                              │ POST activity (JWT Bot Framework)
                              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │   Azure Bot Service: roca-copilot-bot (F0 free, global)      │
 │   msaAppId: 0bfce6c7-...  msaAppType: SingleTenant           │
 │   Endpoint: func-roca-copilot-sync.azurewebsites.net/api/messages │
 └────────────────────────────┬─────────────────────────────────┘
                              │ POST /api/messages (JWT validado)
                              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │   Function App: func-roca-copilot-sync — http_bot_messages   │
 │   Python 3.11 · botbuilder-core 4.15 · CloudAdapter          │
 │                                                               │
 │   1. CloudAdapter valida JWT de Bot Framework (inbound)      │
 │   2. Extrae user_text del Activity                            │
 │   3. Pre-search por código de inmueble (RA03, GU01A...)       │
 │      en shared/bot.py — middleware con KNOWN_CODES            │
 │   4. POST a /openai/v1/responses con agent_reference          │
 │      (endpoint moderno — respeta agent_endpoint version_sel)  │
 │   5. Obtiene token de salida vía requests.post (client creds) │
 │   6. POST respuesta a Teams serviceUrl/v3/conversations/...   │
 └────────────────────────────┬──────────────────┬──────────────┘
                              │                  │
              Foundry API     │                  │ Token salida
                              ▼                  ▼
 ┌──────────────────────────────────┐  ┌──────────────────────────────┐
 │  Foundry Agent Service           │  │ login.microsoftonline.com    │
 │  POST /openai/v1/responses       │  │ /{tenant}/oauth2/v2.0/token  │
 │  agent_reference: roca-copilot   │  │ scope: api.botframework.com  │
 │                                  │  └──────────────────────────────┘
 │  agent_endpoint.version_selector │
 │  → 100% traffic a v11            │
 │                                  │
 │  Agent: roca-copilot:11          │
 │  Modelo: gpt-4.1-mini            │
 │  Tools:                          │
 │   ├─ azure_ai_search             │  → descubrimiento ("¿qué docs hay?")
 │   └─ mcp (knowledge_base_retrieve)│ → detalles (firmantes/notaría/etc)
 └────────────┬─────────────────────┘
              │ tool dispatch
   ┌──────────┴──────────┐
   ▼                     ▼
 ┌──────────────┐   ┌──────────────────────────────────────────────┐
 │ azure_ai_    │   │  Project Connection: roca-knowledge-mcp       │
 │ search tool  │   │  RemoteTool · ProjectManagedIdentity          │
 │ direct query │   │  target → AI Search MCP endpoint              │
 │ (single-shot)│   └────────────────┬─────────────────────────────┘
 │              │                    │ MCP
 │              │                    ▼
 │              │   ┌──────────────────────────────────────────────┐
 │              │   │ Knowledge Base (Agentic Retrieval, preview)  │
 │              │   │ roca-knowledge-base                           │
 │              │   │ - LLM gpt-4.1-mini → query planning           │
 │              │   │ - Descompone en subqueries paralelas          │
 │              │   │ - Semantic reranking por subquery             │
 │              │   │ - outputMode: answerSynthesis                 │
 │              │   │ - reasoningEffort: low                        │
 │              │   └────────────────┬─────────────────────────────┘
 │              │                    │
 │              │                    ▼
 │              │   ┌──────────────────────────────────────────────┐
 │              │   │ Knowledge Source: roca-knowledge-source       │
 │              │   │ Wrapper sobre el índice (sin re-indexar)      │
 │              │   └────────────────┬─────────────────────────────┘
 └──────┬───────┘                    │
        ▼                            ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    Azure AI Search (Basic tier)              │
 │              Índice: roca-contracts-v1 (35 campos, 9038 chunks)│
 │  - Hybrid search (vector + keyword)                           │
 │  - Semantic ranking (Standard, default-semantic-config)       │
 │  - Spanish analyzer (es.microsoft) + synonym map roca-synonyms│
 │  - Scoring profile default: codigo-boost                      │
 │  - Integrated vectorizer (text-embedding-3-small)             │
 │  - Security trimming: group_ids + user_ids (hidden)           │
 │  - Schema en 3 capas + 3 campos SP identity refs              │
 └────────────────────────────┬─────────────────────────────────┘
                              ▲
                              │ (indexación automática cada 5 min)
                              │
 ┌──────────────────────────────────────────────────────────────┐
 │  Function App Ingest: func-roca-ingest-prod (F9, queue-based)│
 │  (Flex Consumption Linux Python 3.11 — $0/mes free grant)    │
 │                                                               │
 │  Timers:                                                      │
 │   ⏱ timer_sync_sharepoint  cada 5 min (Graph delta → queue)  │
 │   ⏱ subscription_renewer   cada 3 días (Graph subs renewal)  │
 │   ⏱ timer_purger           cada 1 hora (orphan cleanup)      │
 │                                                               │
 │  Queue workers (en stroingest):                               │
 │   📬 delta_worker        ← delta-sync-queue (clasifica)      │
 │   📬 enumeration_worker  ← enumeration-queue (full enum)     │
 │   📬 file_worker         ← file-process-queue (batchSize=4)  │
 │      └─ Dispatch por action:                                  │
 │           upsert → download + OCR + chunk + embed + indexa   │
 │           rename → patch nombre_archivo + sharepoint_url     │
 │           move   → patch folder_path                          │
 │           delete → delete_by_content_hash                    │
 │           folder_rename → fan-out moves                      │
 │      └─ maxDequeueCount=5 → poison tras fallos               │
 │                                                               │
 │  HTTP endpoints:                                              │
 │   🔗 webhook_handler      Graph notifications validation     │
 │   🔗 http_status          queue depths + delta tokens        │
 │   🔗 http_read_document   reconstruye texto completo del doc │
 │   🔗 http_full_resync     ⚠ 404 abierto (D-23)               │
 │                                                               │
 │  TARGET_INDEX_NAME = roca-contracts-v1  ← cutover 2026-04-28 │
 │  Auth: MSAL client_credentials (sync robot) + MI para Azure  │
 │  State: deltatokens, folderpaths, itemsindex tables          │
 │  Código: function_app/ingest/ en el repo                     │
 └────────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                       SharePoint Online                      │
 │  - ROCA-IAInmuebles  (site 1)                                │
 │  - ROCAIA-INMUEBLESV2 (site 2)                               │
 │                                                               │
 │  Auth: Entra ID App Registration `roca-copilot-sync-agent`   │
 │        Sites.Selected (Application permission, READ only)    │
 │  Subscriptions: 2 activas, expiration auto-renewed cada 60h  │
 └──────────────────────────────────────────────────────────────┘

 NOTA: func-roca-copilot-sync (legacy F5 Durable) sigue activo
 SOLO para el bot HTTP (http_bot_messages). Los timers Durable
 (timer_sync_delta, timer_acl_refresh, timer_full_resync) están
 isDisabled: true desde F9. Su código de pipeline ya no se ejecuta.
```

### Piezas GA (no preview) que usamos

- ✅ Azure AI Search Basic tier (con integrated vectorizer + semantic ranking standard)
- ✅ Azure Functions Flex Consumption (Python 3.11) — pipeline ingesta queue-based en `func-roca-ingest-prod` (F9)
- ✅ Azure Functions Y1 Consumption (Python 3.11) — bot Teams en `func-roca-copilot-sync`
- ✅ Azure Storage Queues — backbone del pipeline F9 (3 queues + 3 poison + 3 tables en `stroingest`)
- ✅ Microsoft Graph API (delta query + subscriptions) con app-only `Sites.Selected`
- ✅ Azure OpenAI (gpt-4.1-mini + text-embedding-3-small)
- ✅ Azure Document Intelligence (prebuilt-layout)
- ✅ Azure AI Foundry Agent Service v1 (versionado, agent_endpoint con version_selector)
- ✅ Azure Bot Service (F0 free) — solo como router Teams → Function App
- ✅ `botbuilder-core==4.15.0` + `CloudAdapter` para validación JWT inbound
- ✅ HTTP directo (requests.post) para respuesta outbound a Teams (bypass MSAL)

### Piezas preview que SÍ usamos (con criterio)

- ⚠ **Agentic Retrieval / Foundry IQ Knowledge Base** (`api-version=2025-11-01-preview`). Justificación: la única alternativa GA es single-shot RAG, que demostró tener un agujero en queries de detalle (caso RA03). Si Microsoft hace breaking changes en el preview, el rollback es inmediato (`PATCH agent_endpoint` a v10) y el sistema vuelve al estado anterior sin pérdida de datos.
- ⚠ **Foundry Agent Endpoints V1Preview** (header `Foundry-Features: AgentEndpoints=V1Preview`). Necesario para `PATCH agent_endpoint.version_selector`. Mismo criterio de rollback que arriba.

### Piezas preview que explícitamente EVITAMOS

- ❌ Azure AI Search SharePoint indexer nativo (preview, no recomendado producción — verificado 2026-04-15)
- ❌ Foundry SharePoint Tool nativo (preview + no funciona en Teams)
- ❌ Logic Apps Standard (subscription sin cuota WorkflowStandard + SP connector no soporta app-only Sites.Selected — verificado 2026-04-15, ver FASE_5_DESIGN_DECISIONS.md)
- ❌ Copilot Retrieval API / Remote Knowledge Source (no permite schema propio ni enrichment custom)
- ❌ Foundry Activity Protocol directo a Teams (bug de plataforma MS cuando el agente tiene AI Search tool adjunto — mensajes no llegan, sin trazas, confirmado en múltiples reportes de comunidad)
- ❌ Endpoint legacy `/applications/{name}/protocols/openai/responses` para conexión bot↔agente (NO respeta `agent_endpoint.version_selector` — siempre resuelve a una version pinned histórica). Lección aprendida 2026-04-22.
- ❌ BotFrameworkAdapter (legacy, soporte expiró Dic 2025, falla JwtTokenValidation con SingleTenant)
- ❌ MSAL para token outbound (falla silenciosamente con `KeyError: 'access_token'` en este contexto)
- ❌ Tool custom OpenAPI `read_document` (patrón "search + read separados" desaconsejado por Anthropic; reemplazado por Agentic Retrieval que cumple el mismo objetivo de forma nativa)

---

## 3. Decisiones arquitectónicas clave

### Por qué Azure AI Search + pipeline custom (y no Foundry SharePoint Tool)

El Foundry SharePoint Tool nativo tiene una limitación crítica documentada: _"The tool doesn't work when the agent is published to Microsoft Teams"_. Como R-03 exige Teams, ese camino queda fuera. El `AzureAISearchTool` **sí** funciona en agentes publicados a Teams (confirmado por Microsoft Moderator en Q&A #5816041, marzo 2026).

### Por qué Azure Durable Functions (y no Logic App Standard)

> **Nota histórica**: el plan original especificaba Logic App Standard. Durante Fase 5 (2026-04-15) se descubrieron 3 hard-blockers que forzaron el pivot a Durable Functions. Documentación completa del pivot en `FASE_5_DESIGN_DECISIONS.md`.

**Blocker 1** — La subscription FES Azure Plan tiene `WorkflowStandard VMs = 0` en todas las regiones. Solicitar aumento de cuota toma 1-3 días (no viable para el timeline del proyecto).

**Blocker 2** — El SharePoint connector nativo de Logic Apps (Consumption y Standard) **NO soporta app-only authentication (Sites.Selected)**. Solo soporta OAuth delegado con usuario humano. Documentación oficial MS confirma: _"For app-only scenarios, move the SharePoint calls into custom code (Function/WebJob)"_.

**Blocker 3** — Microsoft tiene un **sample oficial** (`Azure-Samples/MicrosoftGraphShadow`) que resuelve exactamente nuestro caso (replicar datos de Graph con delta queries + webhooks) usando **Azure Durable Functions**, no Logic Apps.

**Resultado del pivot**: Durable Functions (Y1 Consumption) cuesta **$0/mes** vs $176/mes de Logic App Standard. Mismo patrón recomendado por Microsoft, validado con evidencia oficial.

### Por qué app permissions (Sites.Selected) y no delegated/OBO

- El pipeline corre en background (Function App), no hay un usuario logueado
- Sites.Selected es el permiso de menor privilegio: solo los 2 sites específicos, no todo el tenant
- No se puede usar OBO porque el Function App no tiene sesión de usuario

### 🔐 Security Trimming (production-grade) — paridad con permisos SharePoint

**El agente respeta los permisos individuales de SharePoint en cada query.** Esto NO es opcional ni "para v2" — se construye desde el día 1 porque los documentos de inmuebles contienen info sensible (contratos, términos comerciales, datos fiscales) y SharePoint tiene ACLs diferenciadas que DEBEN preservarse a nivel agente.

**Patrón usado**: Security Filter Pattern de Azure AI Search (GA, production-ready). Confirmado por Microsoft docs como el approach recomendado para producción hasta que el nuevo Entra native ACL enforcement salga de preview.

**Cómo se implementa**:

1. **Durante ingest (Durable Functions pipeline)** — se capturan los permisos SharePoint por archivo vía Graph API (`GET /sites/{siteId}/lists/{listId}/items/{itemId}/permissions`) y se almacenan como:
   - `group_ids`: Collection de Entra AD group object IDs con acceso
   - `user_ids`: Collection de user object IDs individuales
   - Los grupos SharePoint nativos (Owners/Members/Visitors) se resuelven a sus miembros Entra durante ingest y se expanden al campo correspondiente

2. **Durante query (Foundry agent)** — antes de cada `AzureAISearchTool` call, el agente invoca un custom function tool `build_security_filter(user_id)` que:
   - Llama Graph API `GET /users/{user_id}/transitiveMemberOf?$select=id` con el Project MI del agente
   - Retorna el filtro OData: `(group_ids/any(g:search.in(g, 'grp1,grp2,...')) or user_ids/any(u:search.in(u, 'userId')))`
   - El agente compone ese filtro con el filtro funcional (inmueble, doc_type, etc.) y lo pasa a Azure AI Search
   - Azure AI Search aplica el filtro SERVER-SIDE antes de retornar chunks

**Resultado**: Moisés (director legal) ve todos los contratos; Pedro (marketing) solo ve docs a los que sus grupos Entra tengan acceso en SharePoint. Cero leak entre usuarios. Paridad completa con SharePoint.

**Defense in depth**:

- `group_ids` y `user_ids` son `retrievable=false` → nunca salen al agente ni al usuario final, solo usan para filtrar internamente
- Si por alguna razón el Graph API falla al resolver grupos del usuario → fail-closed: query retorna cero resultados (el agente responde "no tienes acceso" en vez de leakear)
- El `timer_acl_refresh` (cada hora) re-lee los permisos de todos los docs en el índice → mantiene paridad con cambios de ACL en SharePoint

**Permisos extra requeridos**:

- App Registration (sync robot): `Group.Read.All` ya asignado junto con `Sites.Selected` desde Fase 2 ✅
- Project Managed Identity (Foundry agent): `GroupMember.Read.All` + `User.Read.All` (Application permissions, con admin consent)

### 🔐 Limitaciones conocidas del Security Trimming y sus mitigaciones

Ninguna de estas limitaciones es bloqueante, pero cada una tiene una mitigación explícita que hay que implementar o documentar:

| Limitación                                                                                 | Impacto                                                                                                                                  | Mitigación implementada                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1000 permission entries por archivo SharePoint**                                         | Si un archivo tiene >1000 asignaciones directas, las últimas se truncan                                                                  | (1) Monitoreo en Application Insights cuenta `permission_entries_per_doc`. Si un doc excede 900 (90% del límite) → alerta. (2) Recomendación formal a ROCA de usar grupos Entra (ver sección "Recomendaciones para ROCA"). (3) En la práctica, con buen uso de grupos, imposible llegar al límite.                        |
| **Lag de grupos dinámicos de Entra ID**                                                    | Grupos que agregan/quitan miembros automáticamente (ej: "todos los empleados de Legal") tardan 1-15 min en propagar cambios en Graph API | (1) Agente cachea filtro por usuario solo 5 minutos (no más), balance entre performance y frescura. (2) Documentar en user-facing docs: _"si un usuario fue agregado a un grupo y aún no ve docs en el agente, esperar 15 min"_. (3) Para cambios críticos, invalidar cache manualmente (`POST /agent/cache/invalidate`). |
| **Cambios de permisos en SharePoint** no se refrescan en tiempo real                       | Si cambian los permisos de un archivo en SharePoint, el índice sigue con los permisos viejos hasta el próximo `timer_acl_refresh`        | `timer_acl_refresh` (cada hora) re-sincroniza ACLs de todos los docs. Máximo 1 hora de lag para cambios de permisos.                                                                                                                                                                                                      |
| **Latencia extra en cada query (+100-200ms)** por llamada a Graph API para resolver grupos | Queries son ligeramente más lentos                                                                                                       | (1) Cache de 5 min por usuario reduce llamadas subsecuentes a 0ms. (2) Usuarios perciben <500ms total (aceptable). (3) Medido en Application Insights para alerta si excede 1 seg.                                                                                                                                        |
| **Grupos SharePoint nativos** (Site Owners/Members/Visitors) no son grupos Entra           | Logic App no puede filtrar directamente por ellos                                                                                        | Durante ingest, el Logic App **expande** cada grupo SharePoint nativo a la lista de sus miembros Entra y guarda cada uno en `user_ids`. Trade-off: si el grupo SP crece, hay que reindexar.                                                                                                                               |
| **Usuarios externos/guests** con acceso a un doc                                           | Pueden tener object IDs de distinto formato                                                                                              | Ingest captura también `@tenantid#extuserid`. Agente los resuelve igual al pedir su membership.                                                                                                                                                                                                                           |
| **Fail closed**: si Graph API falla, no retornar datos                                     | Si hay un outage de Graph, nadie ve nada (downtime degradado)                                                                            | Alerta crítica en Application Insights si `build_security_filter` falla >5% de las veces. Aceptable porque prefiere fail-closed a fuga.                                                                                                                                                                                   |

### Por qué formato texto plano en respuestas del agente

Microsoft confirmó que Foundry agents publicados a Teams fallan al renderizar markdown tables, citations complejas y estructuras. Workaround oficial: respuestas en texto plano. Esto afecta cómo se responde R-11 (checklist) y R-19 (lista pólizas) — los damos como listas línea-por-línea, no como tablas.

### Por qué Shared scope al publicar (y no Organization scope)

Reportes múltiples en Microsoft Q&A muestran que Organization scope falla silenciosamente con "Sorry, something went wrong". Workaround confirmado: usar Shared scope.

### 🤖 Teams Bot — Decisiones arquitectónicas (Fase 7, 2026-04-16)

#### Por qué middleware Python y no Foundry Activity Protocol directo

Azure AI Foundry expone dos vías para conectar un agente a Teams:

1. **Activity Protocol** (oficial, desde el portal Foundry "Publish to Teams"): Bot Service recibe el mensaje de Teams y lo reenvía al endpoint de Foundry vía la API de Activity Protocol. Simple de configurar pero **con un bug de plataforma confirmado**: cuando el agente tiene un `AzureAISearchTool` adjunto, los mensajes llegan al Bot Service pero nunca alcanzan Foundry — sin trazas, sin errores visibles, sin respuesta al usuario. Microsoft Community reporta el mismo issue (#5816041 y variantes). El portal Foundry publica el agente usando esta vía.

2. **Python middleware en Function App**: Teams → Bot Service (solo valida JWT inbound) → Function App → Foundry Responses API (HTTP directo) → respuesta directa a Teams. Completamente bajo nuestro control.

**Decisión**: middleware Python. La Activity Protocol está rota en producción con AI Search tool. El middleware es más trabajo pero funciona. Adicionalmente, nos da control total sobre timeouts, logging, formateo de respuesta y manejo de errores.

#### Por qué `CloudAdapter` y no `BotFrameworkAdapter`

`BotFrameworkAdapter` es el adaptador legacy de botbuilder. Su soporte oficial expiró en **diciembre 2025**. Específicamente, falla al validar el JWT inbound cuando el Bot Service está configurado como `SingleTenant` — lanza `PermissionError: Unauthorized Access` en `JwtTokenValidation.authenticate_request`. `CloudAdapter` + `ConfigurationBotFrameworkAuthentication` es el reemplazo oficial que maneja correctamente las validaciones de JWT para `SingleTenant`, `MultiTenant` y `UserAssignedMSI`.

```python
from types import SimpleNamespace
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication

_BOT_CONFIG = SimpleNamespace(
    APP_ID=os.environ.get("BOT_APP_ID", ""),
    APP_PASSWORD=os.environ.get("BOT_APP_PASSWORD", ""),
    APP_TYPE="SingleTenant",
    APP_TENANTID="9015a126-356b-4c63-9d1f-d2138ca83176",
)
_BOT_ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(_BOT_CONFIG))
```

#### Por qué `requests.post` directo para el token outbound (y no MSAL / SDK de botbuilder)

El flujo normal de botbuilder para enviar una respuesta a Teams: `turn_context.send_activity()` → `CloudAdapter.send_activities()` → `MicrosoftAppCredentials.get_access_token()` → MSAL `acquire_token_for_client()`. En este contexto (Function App con botbuilder 4.15 + Azure Functions Python v2), MSAL devuelve un dict de error sin `access_token` (causa exacta: interacción entre el event loop de asyncio de Azure Functions y la cache de tokens de MSAL). La excepción real es un `KeyError: 'access_token'` silencioso.

**Solución**: bypass completo del stack outbound de botbuilder. Se adquiere el token directamente con `requests.post` al endpoint de MSAL (equivalente a un `curl` — funciona siempre) y se envía la respuesta con otro `requests.post` directo al `serviceUrl` de Teams. Ninguna magia de SDK en el camino outbound.

```python
def _bot_send_reply(service_url, conversation_id, activity_id, text):
    tenant = "9015a126-356b-4c63-9d1f-d2138ca83176"
    token_resp = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ.get("BOT_APP_ID", ""),
            "client_secret": os.environ.get("BOT_APP_PASSWORD", ""),
            "scope": "https://api.botframework.com/.default",
        },
        timeout=10,
    )
    token = token_resp.json()["access_token"]
    url = f"{service_url.rstrip('/')}/v3/conversations/{conversation_id}/activities/{activity_id}"
    requests.post(
        url,
        json={"type": "message", "text": text, "replyToId": activity_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ).raise_for_status()
```

#### 🚨 Gotcha crítico — `BOT_APP_PASSWORD` debe ser exactamente el secret (sin prefijos)

**Problema encontrado**: al setear `BOT_APP_PASSWORD` con el Azure CLI, si el comando se ejecuta en un contexto donde el CLI muestra advertencias (ej: `WARNING: This command has been deprecated...`), esas advertencias **se pegan al valor de la variable de entorno** en el App Setting. El resultado: `os.environ.get("BOT_APP_PASSWORD")` devuelve 271 caracteres en vez de 40. Azure AD rechaza el `client_secret` corrupto con `AADSTS7000215: Invalid client secret`.

**Causa raíz**: la Azure CLI a veces emite su output de advertencias mezclado con el JSON de respuesta en algunos shells. El App Setting queda con el texto de warning concatenado al secret real.

**Cómo verificar**: en App Insights o logs de la Function App, loggear `len(os.environ.get("BOT_APP_PASSWORD", ""))`. Si es distinto de 40-41, el secret está corrupto.

**Cómo corregir** (con el secret exacto entre comillas, SIN ninguna redirección ni pipes):

```bash
az functionapp config appsettings set \
  --name func-roca-copilot-sync \
  --resource-group rg-roca-copilot-prod \
  --settings "BOT_APP_PASSWORD=<secret-exacto-40-chars>"
```

Verificar en Azure Portal → Function App → Configuration → `BOT_APP_PASSWORD` → longitud = 40-41 chars. El valor correcto es `<SECRET-EN-KEYVAULT-kv-roca-copilot-prod>`.

**Alternativa segura futura**: mover `BOT_APP_PASSWORD` a Key Vault (D-19) y referenciarlo desde App Settings como `@Microsoft.KeyVault(SecretUri=...)`. Así el CLI nunca toca el valor real.

#### Por qué `route="messages"` y no `route="api/messages"`

Azure Functions Python v2 agrega automáticamente el prefijo `/api/` a todas las rutas. Si se define `route="api/messages"`, la URL resultante es `/api/api/messages` (404). La ruta correcta es `route="messages"` → URL pública: `https://func-roca-copilot-sync.azurewebsites.net/api/messages`.

---

## 4. Schema del índice — diseño en 3 capas

El schema se descubre de los documentos reales (fase Discovery), no se diseña a priori. Pero sigue esta estructura de 3 capas para manejar tipos de documento futuros sin romper nada:

### Capa 1 — Campos núcleo (inmutables)

Aplican a CUALQUIER documento, para siempre.

| Campo                 | Tipo                                                      | Descripción                                                                                                                          |
| --------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `id`                  | string                                                    | Primary key del chunk                                                                                                                |
| `content`             | string (searchable)                                       | Texto del chunk                                                                                                                      |
| `content_vector`      | Collection(Single) 1536D                                  | Embedding                                                                                                                            |
| `sharepoint_url`      | string                                                    | Link al archivo original                                                                                                             |
| `nombre_archivo`      | string                                                    | Nombre del file                                                                                                                      |
| `site_origen`         | string                                                    | `ROCA-IAInmuebles` o `ROCAIA-INMUEBLESV2`                                                                                            |
| `folder_path`         | string                                                    | Ruta completa dentro del site                                                                                                        |
| `fecha_procesamiento` | DateTimeOffset                                            | Cuándo se indexó                                                                                                                     |
| `chunk_id`            | string                                                    | ID del chunk dentro del doc                                                                                                          |
| `total_chunks`        | int                                                       | Total chunks del doc padre                                                                                                           |
| `group_ids`           | Collection(Edm.String), filterable, **retrievable=false** | Entra AD group object IDs con permiso de lectura (desde SharePoint ACLs). Usado para security trimming, nunca expuesto en resultados |
| `user_ids`            | Collection(Edm.String), filterable, **retrievable=false** | Entra user object IDs con permiso individual directo (para "Shared with X"). Usado para security trimming, nunca expuesto            |

### Capa 2 — Metadata común (compartida entre tipos)

Campos que aparecen en la mayoría de docs de inmuebles. Se van agregando conforme Discovery los detecte.

| Campo               | Tipo                | Descripción                                                                                                                                |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `doc_type`          | string (filterable) | `permiso_construccion`, `contrato_arrendamiento`, `plano`, `poliza_seguro`, `estudio_impacto`, `csf`, `licencia_uso_suelo`, `folder`, etc. |
| `inmueble_codigo`   | string (filterable) | `RA03`, `RA04`, etc.                                                                                                                       |
| `fecha_emision`     | DateTimeOffset      | Cuándo se emitió el doc                                                                                                                    |
| `fecha_vencimiento` | DateTimeOffset      | Cuándo expira                                                                                                                              |
| `es_vigente`        | boolean             | Calculado en ingesta: `fecha_vencimiento > today`                                                                                          |
| `autoridad_emisora` | string              | Para permisos/licencias                                                                                                                    |
| `inquilino`         | string              | Para contratos de arrendamiento                                                                                                            |
| `propietario`       | string              | Para CSF y docs del dueño                                                                                                                  |

### Capa 3 — Metadata flexible (JSON libre)

Para cualquier campo que gpt-4o detecte y que no caiga en Capa 2. Cambia por doc, no bloquea ingesta.

| Campo                | Tipo                      | Descripción                          |
| -------------------- | ------------------------- | ------------------------------------ |
| `extracted_metadata` | string (JSON stringified) | Todo lo extra que gpt-4o identifique |

### Capa versiones (para R-07 y R-08)

| Campo                | Tipo    | Descripción                             |
| -------------------- | ------- | --------------------------------------- |
| `parent_document_id` | string  | ID del doc "familia" (agrupa versiones) |
| `version_number`     | int     | 1, 2, 3...                              |
| `is_latest_version`  | boolean | true si es la más reciente              |

SharePoint tiene versionado nativo de archivos que consumimos vía Graph API desde el Logic App. Conservamos versiones históricas en el índice (no sobrescribimos) para soportar R-08 (comparación).

---

## 5. Requisitos R-01 a R-19 — Mapeo a la arquitectura

### ✅ Cubiertos out-of-the-box (14 de 19)

| ID   | Caso                                 | Implementación                                                            |
| ---- | ------------------------------------ | ------------------------------------------------------------------------- |
| R-01 | Origen SharePoint                    | Logic App sync de los 2 sites → AI Search                                 |
| R-02 | Temas de la doc                      | gpt-4o + semantic search sobre el índice                                  |
| R-03 | Canal Teams/M365 Copilot             | Publicar con Shared scope + respuestas texto plano                        |
| R-04 | Búsqueda por tipo de doc             | Filtro `doc_type` + `inmueble_codigo`                                     |
| R-05 | Permisos vigentes                    | Filtro `es_vigente=true` + `inmueble=X` + `doc_type LIKE permiso*`        |
| R-06 | Contrato arrendamiento por inquilino | Filtro `inquilino=X` + `inmueble=X` + `es_vigente=true`                   |
| R-09 | Resumen impacto ambiental            | Semantic retrieval + gpt-4o summarization (5-7 puntos)                    |
| R-10 | Resumen contrato arrendamiento       | Igual que R-09 (renta, plazo, renovaciones, incrementos, penalizaciones)  |
| R-14 | Búsqueda combinada cliente+inmueble  | Filtro combinado + plain-text list con tipo + liga                        |
| R-15 | Planos arquitectónicos               | Filtro `doc_type=plano` + detección "As-Built" por gpt-4o                 |
| R-16 | Pregunta legal específica            | Semantic search + citation con URL                                        |
| R-17 | Keyword en contenido                 | **Hybrid search** (vector + keyword) — este es exactamente el caso de uso |
| R-18 | Info fiscal del propietario          | Filtro `doc_type=csf` + gpt-4o extrae razón social/RFC/fecha              |
| R-19 | Pólizas de seguro vigentes           | Filtro `doc_type=poliza` + `es_vigente=true` (formato lista plana)        |

### ⚠️ Cubiertos con diseño especial (4 de 19)

#### R-07 — Última versión del documento

- SharePoint tiene versionado nativo; el Logic App lo consume vía Graph API
- Campos: `version_number`, `is_latest_version`, `parent_document_id`
- Cuando sube versión nueva: marca la anterior como `is_latest_version=false`, no la borra
- Query del agente: filtro `parent_document_id=X AND is_latest_version=true`

#### R-08 — Comparación de versiones

- Conservamos versiones históricas (no sobrescribimos)
- Agente recibe query tipo "compara versiones de X"
- Hace 2 retrievals: latest + latest-1
- gpt-4o compara con prompt enfocado en: fechas, montos, plazos, penalizaciones
- Respuesta en texto plano, diferencias línea-por-línea
- Implementación: function tool `comparar_versiones` o manejo via prompt instructions (~2 hrs extra)

#### R-12 — Permisos próximos a vencer

- Inyección de `today` en el system prompt en cada request (variable dinámica del Foundry agent)
- Filtro: `fecha_vencimiento <= today + X months AND inmueble_codigo=RA03`
- Respuesta: lista plana con fecha de vencimiento

#### R-13 — Localización de carpeta de cierre de proyecto

- Logic App indexa también metadata de carpetas como "virtual documents":
  ```
  doc_type = "folder"
  folder_name = "Cierre de proyecto"
  inmueble_codigo = "RA03"
  sharepoint_url = "https://...Shared Documents/RA03/Cierre de Proyecto"
  content = "Carpeta de cierre de proyecto para el inmueble RA03"
  ```
- Implementación: paso extra en Logic App (~1 hr)

### ❗ Requiere input del negocio (1 de 19)

#### R-11 — Checklist de permisos requeridos por inmueble

**Bloqueante**: necesitamos la lista maestra de "qué permisos DEBE tener cualquier inmueble del portafolio". Eso no sale de los documentos — es regla de negocio.

**Solución técnica**:

1. Creamos `/templates/checklist_permisos.json` (versionado, en SharePoint o en el repo)
2. Formato:
   ```json
   {
     "permisos_requeridos": [
       { "nombre": "Licencia de uso de suelo", "autoridad": "Municipio" },
       { "nombre": "Permiso ambiental", "autoridad": "SEMARNAT" },
       { "nombre": "Permiso de construcción", "autoridad": "Municipio" }
     ]
   }
   ```
3. Agente hace 2 queries: lee checklist maestro + busca permisos existentes para RA03
4. Cruza y responde en texto plano:
   ```
   Licencia de uso de suelo: EXISTE (vence 2027-03-15)
   Permiso ambiental: FALTA
   Permiso de construcción: EXISTE (vence 2026-12-01)
   ```

**Acción pendiente**: solicitar a Legal/Operaciones de ROCA la lista completa de permisos obligatorios por tipo de inmueble.

---

## 6. Plan de ejecución — 7 fases

### Fase 1 — Limpieza y setup base `~30 min` _(Claude ejecuta)_ ✅ COMPLETA 2026-04-14 (hardening aplicado 2026-04-15)

- [x] Borrar resource group de la cuenta personal (`rg-abrahammartinez1811-0978`) — confirmado por usuario
- [x] Confirmar sesión `az login` activa en cuenta dev (FES Azure Plan) — `admin.copilot@rocadesarrollos.com`
- [x] Registrar providers: Microsoft.Search, Microsoft.Web, Microsoft.Storage, Microsoft.Insights, Microsoft.CognitiveServices, Microsoft.KeyVault
- [x] Crear resource group de producción: `rg-roca-copilot-prod` en eastus2 con tags `project=roca-copilot`, `env=prod`
- [x] **Production hardening aplicado 2026-04-15** (no estaba en el plan original):
  - Purge protection habilitado en `kv-roca-copilot-prod` (irreversible, previene eliminación forzada de secretos)
  - CanNotDelete lock `roca-copilot-prod-no-delete` sobre el RG (previene `az group delete` accidental)
- [ ] Habilitar Managed Identity en recursos relevantes _(diferido a Fase 3 — no hay recursos todavía)_
- [ ] Actualizar `.env.example` del repo con los nombres de recursos nuevos _(diferido a Fase 3)_

#### 📝 Post-mortem Fase 1 — Sección (E): Deuda técnica y hardening aplicado

Esta sección documenta las brechas de production-readiness que NO estaban en el plan original de Fase 1 y que se detectaron al revisar el estado después de completar Fase 2. Algunas se resolvieron en el momento, otras se difirieron a Fase 3 con compromiso explícito.

##### (E.1) ✅ RESUELTO 2026-04-15 — Purge protection en Key Vault

**Gap detectado**: al crear `kv-roca-copilot-prod` en Fase 2, Azure rechazó `--enable-purge-protection false` (bloqueo intencional de Microsoft), y omití la bandera dejándolo en default. El default es **soft-delete habilitado pero purge protection deshabilitado**, lo que significa que alguien con permisos podría ejecutar `az keyvault delete` seguido de `az keyvault purge` para eliminar permanentemente el vault y todos los secretos en cuestión de minutos, sin ventana de recovery.

**Riesgo para un cliente production**: pérdida irrecuperable del client secret del sync robot si hay error humano o incidente de seguridad. Regenerar el secret requiere re-hacer bootstrap de Sites.Selected + reconfigurar Logic App.

**Fix aplicado**: `az keyvault update --name kv-roca-copilot-prod --enable-purge-protection true`. Verificado con `az keyvault show`: `purgeProtection: true`, `retentionDays: 7`.

**Nota sobre irreversibilidad**: purge protection una vez habilitada NO se puede deshabilitar sobre el mismo vault. Implicación: si algún día se borra legítimamente este KV, hay que esperar los 7 días completos de soft-delete antes de que sea purgado automáticamente (o manualmente vía purge después del período). No impacta operaciones normales (create/read/update/delete de secretos individuales funciona sin restricción).

**Recomendación Microsoft oficial**: _"For production workloads, we recommend that you enable purge protection"_ — Azure Key Vault docs. Cumplido.

##### (E.2) ✅ RESUELTO 2026-04-15 — CanNotDelete lock sobre Resource Group

**Gap detectado**: el RG `rg-roca-copilot-prod` no tenía ningún resource lock, permitiendo que cualquier usuario con permisos Contributor o Owner ejecute `az group delete --name rg-roca-copilot-prod --yes` y elimine TODOS los recursos de ROCA Copilot en un solo comando (KV, App Registration resources, futuros AI Search, Blob, Logic App, etc.) sin fricción ni confirmación adicional.

**Riesgo para un cliente production**: incidente de un solo comando que destruye la infraestructura completa. Ya ocurrió en clientes reales, es por esto que los locks son estándar en production.

**Fix aplicado**: `az lock create --name roca-copilot-prod-no-delete --lock-type CanNotDelete --resource-group rg-roca-copilot-prod --notes "..."`. Verificado con `az lock list`.

**Nota sobre reversibilidad**: este lock es 100% reversible. Cuando sea legítimo borrar el RG (ej: decommissioning del proyecto al final de su vida útil), se quita con `az lock delete --name roca-copilot-prod-no-delete --resource-group rg-roca-copilot-prod`. NO impide ninguna operación sobre recursos individuales dentro del RG — solo el borrado del RG completo.

##### (E.3) 🟡 PARCIALMENTE RESUELTO 2026-04-15 — Budget alert + Action Group _(Action Group creado; Budget pendiente de re-auth del usuario)_

**Gap**: no hay monitoreo proactivo de costos. Si algo en el futuro se dispara en consumo (loop infinito en Logic App reprocesando los mismos PDFs, ataque DDoS a AI Search, picos imprevistos en gpt-4o), no hay alerta automática hasta que alguien revise manualmente la factura al mes siguiente.

**Riesgo para un cliente**: sorpresa en la factura, potencialmente significativa ($500-$2000 en un escenario malo). Para un proyecto con estimado $120-220/mes esto sería muy visible.

**Acción pendiente (Fase 3)**:

1. Crear un Budget sobre la suscripción o el RG con umbral mensual de ~$300 (40% buffer sobre estimado alto)
2. Crear un Action Group con email destination al usuario (`admin.copilot@rocadesarrollos.com`)
3. Configurar 2 alertas:
   - **50% del budget** ($150): warning temprano
   - **90% del budget** ($270): alerta crítica con email inmediato
4. Opcional: alerta de anomaly detection (`Azure Cost Management Anomaly Detection`) para detectar spikes no lineales

**Cuándo hacerlo**: como primer paso de Fase 3, antes de crear AI Search (el recurso más caro, $75/mes fijo).

**Estado 2026-04-15**:

- ✅ Action Group `ag-roca-copilot-prod` creado con email receiver `admin.copilot@rocadesarrollos.com`.
- ⚠ Budget `budget-roca-copilot-prod` bloqueado: las APIs `Microsoft.Consumption/budgets` y `Microsoft.CostManagement/budgets` retornaron `401 Unauthorized` con `Interactive authentication is needed` contra el token cacheado. Gotcha conocido de las APIs de billing/cost en Azure Plan — requieren claim MFA fresco. **Acción del usuario**: ejecutar `az logout && az login` interactivo y reintentar, o crear el Budget directamente en el portal de Cost Management (30 seg).

##### (E.4) ✅ RESUELTO 2026-04-15 — `.env.example` con recursos Fase 1 + 2 + 3

**Gap**: no existe un archivo de configuración de referencia en el repo que documente qué variables de entorno necesita cualquier script o herramienta de desarrollo local para conectarse a la infraestructura.

**Por qué se difirió**: crearlo en Fase 1 con solo 3 entradas (subscription ID, tenant, RG name) era churn; es más eficiente crearlo en Fase 3 cuando ya haya 10+ recursos que documentar (AI Search endpoint, Blob connection string reference en KV, App Insights instrumentation key, embeddings deployment name, etc.).

**Acción pendiente (Fase 3)**:

- Generar `.env.example` con todas las variables necesarias **nombradas** pero con valores placeholder
- Incluir comentarios explicando de dónde sale cada valor (Key Vault reference, portal, `az` command, etc.)
- Garantizar que `.env` real está en `.gitignore` (verificar antes de la primera vez que alguien use el `.env` local)

**Estado 2026-04-15**:

- ✅ Creado `/Users/datageni/Documents/ai_azure/.env.example` con todas las variables de Fases 1+2+3, valores no-secretos inlineados y placeholders explícitos (`__usar_managed_identity__`, `__leer_de_key_vault__`) para cualquier credencial.
- ✅ `.env` ya estaba ignorado en `azure-ai-contract-analysis/.gitignore` (líneas 15-16). Adicionalmente se creó `/Users/datageni/Documents/ai_azure/.gitignore` con `.env` como defensa por si alguien inicializa un repo en la raíz de ai_azure.

##### (E.5) ✅ RESUELTO 2026-04-15 — Habilitar MI en recursos relevantes

**Estado**: en Fase 1 no había recursos a los que habilitar MI. En Fase 2 se habilitó MI a nivel del Foundry project y del Key Vault (vía RBAC). Pero los recursos de Fase 3 (AI Search, Blob, App Insights, Logic App) van a necesitar su propio MI + role assignments para que se comuniquen entre sí sin client secrets.

**Acción pendiente (Fase 3)**: al crear cada recurso de Fase 3, habilitar System-Assigned MI y asignar los roles RBAC apropiados:

- Logic App MI → `Search Index Data Contributor` sobre AI Search
- Logic App MI → `Storage Blob Data Contributor` sobre Blob Storage
- Logic App MI → `Cognitive Services User` sobre `rocadesarrollo-resource` (AIServices)
- Logic App MI → `Key Vault Secrets User` sobre `kv-roca-copilot-prod` (para leer el client secret del sync app)

Esto ya está parcialmente documentado en la Fase 3 original, solo hay que asegurarse de ejecutarlo consistentemente.

**Estado 2026-04-15**:

- ✅ `srch-roca-copilot-prod` con System-Assigned MI `c9181743-c085-4885-8ff7-81392e0d2d5a`
- ✅ `strocacopilotprod` con System-Assigned MI `c39ba7f1-1898-4c15-bded-9bf4d2bc06eb`
- ⏸ Los 4 role assignments del Logic App MI quedan **documentados** en la sección Fase 3 con comandos template listos, pero NO se aplican todavía porque el Logic App no existe (lo crea Fase 5). Aplicar ahí después de habilitar el MI del Logic App.

##### (E.6) 📋 DEUDA CONOCIDA SIN ACCIÓN — Verificación trust-based del RG personal borrado

**Gap**: el borrado de `rg-abrahammartinez1811-0978` de la cuenta personal (subscription `aa6fedaa-b4e9-4a36-bdf1-dafb779b85ae`, tenant `27bb91cc-197f-4e7f-84a9-47eaf9935598`) fue confirmado verbalmente por el usuario pero **no verificado directamente por Claude** desde el contexto de ROCA, porque la sesión `az` solo tenía acceso al tenant ROCA. Para verificar formalmente se necesitaría `az login --tenant 27bb91cc-...` interactivo y luego `az group show`.

**Riesgo**: mínimo. Es una cuenta personal del usuario (no del cliente ROCA), y si por alguna razón no se borró, no afecta el proyecto ROCA Copilot en absoluto — solo sigue acumulando costo en la cuenta personal del usuario, problema 100% aislado.

**Acción**: ninguna requerida. Si el usuario quiere verificación formal, puede correr en cualquier momento:

```bash
az login --tenant 27bb91cc-197f-4e7f-84a9-47eaf9935598 --allow-no-subscriptions
az group show --name rg-abrahammartinez1811-0978 --subscription aa6fedaa-b4e9-4a36-bdf1-dafb779b85ae
```

Si retorna `ResourceGroupNotFound`, quedan 100% verificados.

---

**Estado final de Fase 1 después del hardening**:

- ✅ RG de producción creado, tagueado y protegido contra borrado accidental
- ✅ Providers registrados (6 en total)
- ✅ Key Vault con purge protection — protege secretos contra borrado forzado
- ✅ Sesión `az` verificada y persistente
- 🔄 5 items diferidos a Fase 3 con acción explícita documentada
- 📋 1 deuda conocida sin riesgo (cuenta personal del usuario)

---

**Entregable**: ambiente limpio, listo para construir.
**Bloqueantes**: confirmación explícita del usuario para borrar la cuenta personal.

---

### Fase 2 — Permisos SharePoint + Graph (Entra ID App Registrations) `~horas/días` _(usuario + posiblemente IT)_ ✅ COMPLETA 2026-04-15

**Recursos creados**:

- Key Vault: `kv-roca-copilot-prod` (RBAC mode, secret URI: `https://kv-roca-copilot-prod.vault.azure.net/secrets/roca-copilot-sync-agent-secret`)
- App Registration: `roca-copilot-sync-agent` (appId `18884cef-ace3-4899-9a54-be7eb66587b7`, spId `c14b0ac5-1f88-4eaf-860a-c96354267d86`)
- Foundry project MI: `8117b1a5-5225-4d9e-9071-ee9aa90b7eb0` (System-assigned, proyecto `rocadesarrollo`)

**Paso 2.1 — Sync robot App Registration** ✅:

- [x] Crear Entra ID App Registration llamada `roca-copilot-sync-agent` en tenant ROCA TEAM
- [x] Asignar permisos (Application permissions):
  - **`Sites.Selected`** (id `883ea226-0bf2-4a8f-9f9d-92c9162a727d`)
  - **`Group.Read.All`** (id `5b567255-7703-4780-807c-7be8301ae99b`)
- [x] Admin consent otorgado (verificado vía `appRoleAssignments`)
- [x] Client secret generado (2 años) y guardado en `kv-roca-copilot-prod/roca-copilot-sync-agent-secret`
- [x] Sites.Selected grant aplicado a ambos sites con rol `read`:
  - Site 1 `rocadesarrollos1.sharepoint.com,1fc5e500-0a8a-4631-9037-f83195ac7617,fb4f41ac-732b-4b9d-ab14-24dd18f3cbb9`
  - Site 2 `rocadesarrollos1.sharepoint.com,bb6f7d7f-c5ff-4f68-8a6c-05775b3661bd,7ca4e7eb-b066-411d-b826-f8f63a6b23e0`
  - Bootstrap: se usó `Sites.FullControl.All` temporal para hacer el PATCH de `/sites/{id}/permissions`, removido inmediatamente después
- [x] Test de acceso end-to-end: con client_credentials flow y `Sites.Selected`, lista drives de ambos sites y enumera folders reales (07. Permisos construcción, 11. Estudio ambiental, 30. Contratos arrendamiento, 33. CSF, 65. Planos As-Built, etc.)

**Paso 2.2 — Foundry agent Project Managed Identity** ✅:

- [x] System-assigned MI ya estaba habilitado en el Foundry project `rocadesarrollo` (principalId `8117b1a5-5225-4d9e-9071-ee9aa90b7eb0`)
- [x] Graph app roles asignados al MI vía `/servicePrincipals/{miId}/appRoleAssignments`:
  - **`GroupMember.Read.All`** (id `98830695-27a2-44f7-8c18-0c3ebc9698f6`)
  - **`User.Read.All`** (id `df021288-bdef-4463-88db-98f22de89214`)
- [x] Smoke test `/users/{id}/transitiveMemberOf` del endpoint Graph (con token delegated Global Admin) — funcional. Validación con token del MI real se hará en Fase 6 cuando el custom function tool se despliegue dentro del agente.

**Entregable**: ambos principals con permisos correctos. Sync robot puede leer los 2 sites + resolver grupos SharePoint. Foundry MI puede resolver grupos de cualquier usuario del tenant.
**Bloqueantes**: permisos de Global Admin para consentir las 4 permisos Graph. Si el usuario no es Global Admin, necesita coordinar con IT (esta es la conversación única con IT en todo el proyecto).

---

#### 📝 Post-mortem Fase 2 — Notas críticas para Fases 5 y 6

Estas 3 secciones aclaran malentendidos comunes sobre el estado real del security trimming después de Fase 2, y documentan decisiones operativas tomadas durante la ejecución.

##### (A) Estado real del security trimming después de Fase 2

**Fase 2 puso las LLAVES, NO la CERRADURA.** Nada del filtrado de ACLs funciona todavía. Esto es esperado y correcto — pero es crítico entender que **hoy no hay enforcement de permisos**.

El security trimming es un sistema de 3 piezas independientes que se construyen en fases distintas:

| Pieza                                           | Qué hace                                                                                                           | Dónde vive                                                                         | Cuándo se hace | Estado       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------------- | ------------ |
| **A. Permisos del robot para LEER ACLs**        | El sync app puede consultar SharePoint y resolver grupos Entra                                                     | App Registration `roca-copilot-sync-agent` con `Sites.Selected` + `Group.Read.All` | Fase 2         | ✅ Listo     |
| **B. Indexar ACLs junto con cada chunk**        | Cada documento indexado lleva sus `group_ids` y `user_ids` capturados en tiempo de ingest                          | Durable Functions pipeline — `refresh_acls_activity` (corre cada hora)             | Fase 5         | ✅ Listo     |
| **C. Aplicar filtro en cada query del usuario** | Antes de cada retrieval, se calcula qué grupos tiene el usuario y se compone filtro OData server-side en AI Search | Custom function tool `build_security_filter(user_id)` en el agente Foundry         | Fase 6.1b      | ❌ Pendiente |

**Implicación operativa**: el agente en producción (Fase 7 completa) hoy muestra TODOS los documentos a cualquier usuario autenticado porque la pieza C (filtro en query time) no existe aún. Aceptable para el equipo interno de ROCA donde todos ven todo. **Bloquea el acceso a usuarios externos o con perfiles de permiso diferenciado** — ver D-17.

##### (B) Propagación y cache de tokens del Managed Identity — gotcha para Fase 6

Cuando asignas un Graph app role a un Managed Identity (como se hizo con `GroupMember.Read.All` + `User.Read.All` sobre el MI del Foundry project), hay dos ventanas de tiempo que pueden causar fallos silenciosos en el primer test:

1. **Propagación del role assignment a Azure AD** — hasta **15 minutos** desde que se crea el `appRoleAssignment` hasta que está disponible en todos los servidores de autenticación del tenant. Este delay no se puede acelerar.
2. **Cache del token** — cuando el MI obtiene un access token, ese token tiene validez de ~1 hora e incluye los claims/roles que tenía el MI en el momento de emitirse. Si ya había un token en cache antes del cambio de permisos, ese token viejo NO verá los permisos nuevos hasta expirar.

**Por qué importa en Fase 6**: cuando se construya el custom function tool `build_security_filter` e intentemos la primera llamada a `/users/{id}/transitiveMemberOf` con el token del MI, si falla con `Forbidden` o `InsufficientPrivileges`, **la primera hipótesis debe ser propagación/cache, no debug en serio**. Esperar 15 minutos, forzar un token nuevo (en Python con `azure.identity` se hace instanciando un `DefaultAzureCredential()` fresco), y reintentar. Solo si persiste después de eso, investigar el assignment.

**No tiene nada que ver con los ACLs de SharePoint** — es una característica base de Azure AD al asignar permisos nuevos a cualquier principal.

##### (C) Dónde viven los IDs, secretos y configs del proyecto

Política de persistencia de datos operativos del proyecto ROCA Copilot:

| Tipo de dato                          | Ejemplo                                                            | Dónde vive                                                                    | Por qué                                                                                                                                                                          |
| ------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Secretos**                          | Client secret del sync app, connection strings, API keys           | Azure Key Vault `kv-roca-copilot-prod`                                        | Nunca en `.env`, git, plan, o memory. El Logic App y otros consumidores leen via su propio MI. Rotación independiente de código.                                                 |
| **IDs públicos**                      | `appId`, `spId`, site IDs, resource group name, principal IDs      | `PLAN_ROCA_COPILOT.md` (este archivo)                                         | No son secretos — cualquiera con acceso al tenant los descubre. Vivir en el plan los hace la fuente de verdad para futuros scripts de deploy, debugging y referencia del equipo. |
| **Config runtime**                    | Tenant ID, KV URI, nombres de recursos, endpoints                  | `.env.example` (plantilla en repo) + App Settings del Logic App en producción | `.env.example` es plantilla sin secretos para desarrolladores locales. Producción los lee de App Settings del Logic App (inyectados via Key Vault references).                   |
| **Preferencias/contexto del usuario** | Regla de Oro del deployment, decisiones de scope, feedback de ROCA | Memory files en `/Users/.../memory/`                                          | Persiste entre sesiones de Claude. NO para IDs ni secretos.                                                                                                                      |

**Decisión concreta tomada en Fase 2**:

- `.env.example` NO se genera todavía. Tiene más sentido crearlo en Fase 3 cuando haya más recursos (AI Search, Blob, App Insights) y más variables que documentar. Crearlo ahora con solo 5 entradas es churn.
- El workaround del bootstrap de Sites.Selected (uso temporal de `Sites.FullControl.All`) se guarda en memoria como feedback-type note, por si hay que replicarlo en otro proyecto futuro. Es un patrón oficial de Microsoft, pero no obvio.

##### (D) Deuda técnica y validaciones pendientes que pueden regresarnos a Fase 2

Fase 2 está funcionalmente completa — no bloquea Fase 3, 4, ni 5. Pero estos 3 puntos son cosas que podrían forzar un retorno a Fase 2 más adelante. Ordenados de más a menos probable:

**1. ⚠️ Validación end-to-end del MI del Foundry project** _(se resuelve en Fase 6, casi seguro)_

Los permisos Graph (`GroupMember.Read.All` + `User.Read.All`) están asignados al MI `8117b1a5-5225-4d9e-9071-ee9aa90b7eb0` y son visibles como authoritative en `appRoleAssignments`. **Pero el test real** — que el MI pueda obtener un token con sus nuevos roles y llamar `/users/{id}/transitiveMemberOf` exitosamente — solo se puede hacer desde dentro del compute del Foundry project, no desde `bash` externo. Esto se valida **automáticamente** en Fase 6 Paso 6.1b cuando se construye el custom function tool `build_security_filter`.

- **Si funciona en Fase 6**: cerramos este punto, sin acción adicional.
- **Si falla en Fase 6**: orden de debugging → (1) esperar 15 min por propagación del role assignment, (2) forzar token nuevo (no usar cache), (3) verificar que el `appRoleAssignment` sigue presente con `az rest GET /servicePrincipals/{miId}/appRoleAssignments`, (4) solo entonces sospechar assignment incorrecto y reasignar.

**Probabilidad de fallo**: baja. Los assignments están correctos. Pero hay que tener el diagnóstico listo.

**2. 🔄 Upgrade a Workload Identity Federation (Federated Credentials)** _(decisión en Fase 5, RECOMENDADO para production)_

Hoy el sync robot se autentica contra Entra ID usando un **client secret** de 2 años guardado en Key Vault. Es funcional, seguro en el corto plazo, pero **no es la mejor práctica production-grade**. La alternativa superior es **Workload Identity Federation**:

- El Logic App Standard (que se crea en Fase 5) obtiene su propio **System-Assigned Managed Identity**
- Se agrega un **Federated Credential** al App Registration `roca-copilot-sync-agent` que confía en el MI del Logic App como issuer
- El Logic App autentica al App Registration usando el token de su MI, **sin client secret**
- El client secret se **elimina completamente** de Key Vault y del App Registration

**Ventajas**:

- Cero secretos compartidos (nada que rotar, nada que fugar)
- Cero superficie de ataque por credential leak
- El ciclo de vida de la credencial está atado al ciclo de vida del recurso (si se borra el Logic App, se invalida solo)

**Cuándo decidir**: al arrancar Fase 5 Paso "Crear Logic App". Después de crear el Logic App y habilitarle MI, dos opciones:

- **Opción A** — dejar el client secret actual (más simple, ~0 min extra)
- **Opción B** — migrar a federated credentials (~10-15 min extra, mucho más seguro)

**Recomendación**: Opción B para cualquier proyecto production con datos sensibles. La migración es:

1. `az ad app federated-credential create` sobre el sync app apuntando al issuer `https://login.microsoftonline.com/{tenant}/v2.0` y subject al principal ID del Logic App MI
2. Configurar el workflow del Logic App para usar `ManagedIdentity` en vez de `ClientSecret` en la conexión a Graph
3. Validar end-to-end que el Logic App sigue leyendo los 2 sites con éxito
4. Borrar el secreto del KV (`az keyvault secret delete --name roca-copilot-sync-agent-secret`)
5. Borrar la credential password del App Registration (`az ad app credential delete --id {appId} --key-id {keyId}`)

**Si migramos en Fase 5**, el punto #3 (rotación de secret) desaparece automáticamente.

**3. 🔑 Rotación del client secret — fecha límite 2028-04-15** _(operativo, solo si NO migramos a federated credentials)_

El client secret tiene **validez de 2 años** desde 2026-04-15. Si llegamos a Fase 5 y elegimos Opción A (dejar el secret), hay que calendarizar:

- **Recordatorio 1**: 2028-02-15 (60 días antes de expirar) — generar nuevo secret, actualizar Key Vault, validar que el Logic App sigue funcionando, dejar ambos secrets activos ~7 días, luego borrar el viejo
- **Recordatorio 2**: 2028-04-01 (14 días antes) — verificación final
- **Si se olvida**: el sync robot empieza a fallar silenciosamente el 2028-04-15. Error típico: `AADSTS7000215: Invalid client secret provided`. El índice queda desactualizado hasta que alguien lo note.

**Acción**: si en Fase 5 elegimos Opción A, agregar este recordatorio al calendario del equipo (Moisés + Omar) y documentar en un runbook operativo el procedimiento de rotación.

**Si elegimos Opción B (federated credentials), este punto se cierra automáticamente** y no hay rotación que hacer.

---

**Ninguno de los 3 puntos bloquea arrancar Fase 3.** Fase 2 entregó lo que tenía que entregar.

---

### Fase 3 — Infraestructura de datos `~1 hora` _(Claude ejecuta)_ ✅ COMPLETA 2026-04-15 (Budget pendiente de re-auth del usuario)

- [x] Desplegar `text-embedding-3-small` en `rocadesarrollo-resource` (100K TPM, Standard, version `1`, Succeeded)
- [x] **DECISIÓN 2026-04-15**: Eliminar deployment `gpt-4o` y desplegar en su lugar `gpt-5-mini` (version `2025-08-07`, GlobalStandard 250K TPM) como único modelo chat del proyecto. Razón: minimización de costo al cliente ROCA y mejor relación costo/desempeño para RAG sobre inmuebles.
- [x] Crear Azure AI Search **Basic** tier `srch-roca-copilot-prod` en `rg-roca-copilot-prod`, System-Assigned MI (`c9181743-c085-4885-8ff7-81392e0d2d5a`), semantic ranking Standard habilitado.
  - **DESVIACIÓN**: creado en `eastus` (NO `eastus2`) porque eastus2 retornó `InsufficientResourcesAvailable` para Basic al momento de provisionar. Mismo RG, distinta región. Cross-region overhead entre Logic App (eastus2) y AI Search (eastus) es irrelevante para el caso de uso.
- [x] Crear Azure Blob Storage `strocacopilotprod` (Standard_LRS, Hot, System-Assigned MI `c39ba7f1-1898-4c15-bded-9bf4d2bc06eb`, TLS1_2 min, public access off). Container `ocr-raw` creado.
- [x] Crear Log Analytics workspace `log-roca-copilot-prod` (PerGB2018, 30-day retention) en eastus2 — prerequisito del App Insights workspace-based.
- [x] Crear Application Insights `appi-roca-copilot-prod` workspace-based en eastus2 (appId `732d89e9-8f2d-4eae-a9c1-cd31fb66c9c0`, iKey `2a7c7622-1eea-476e-86ca-5c9d08e86626`).
- [x] Action Group `ag-roca-copilot-prod` creado con email receiver `admin.copilot@rocadesarrollos.com`.
- [ ] **DEUDA TÉCNICA — conversación pendiente con el equipo ROCA**: Budget `budget-roca-copilot-prod` ($300/mes con alertas 50%/90% vinculadas al Action Group). **Causa raíz confirmada 2026-04-15 (NO es stale token)**: el billing account `ROCA TEAM SA DE CV` es un **Microsoft Customer Agreement (MCA)** (sufijo `_2019-05-31` en el billing account ID). En MCA los roles de billing viven en un sistema **separado de Azure RBAC**. `admin.copilot@rocadesarrollos.com` es `Owner` de la subscription (control de recursos) pero NO tiene rol de billing, por eso `Microsoft.Consumption/budgets` retorna `401` incluso para operaciones read-only. Verificado: `az login` interactivo NO lo desbloquea; `GET /providers/Microsoft.Consumption/budgets` también falla. **Resolución**: conversación con el Billing Account Owner del MCA de ROCA TEAM para asignar `Cost Management Contributor` al usuario sobre el billing scope, o que esa persona cree el Budget directamente. Mientras tanto, el Action Group ya está creado y listo para recibir el link cuando el Budget exista.

**Roles RBAC pendientes del Logic App MI** _(aplicar en Fase 5 cuando el Logic App exista — NO aplicables todavía porque el principal no existe)_:

- `Search Index Data Contributor` sobre `srch-roca-copilot-prod` (alcance AI Search completo)
- `Storage Blob Data Contributor` sobre `strocacopilotprod` (alcance storage account o container `ocr-raw`)
- `Cognitive Services User` sobre `rocadesarrollo-resource` (alcance AIServices account en `rg-admin.copilot-9203`)
- `Key Vault Secrets User` sobre `kv-roca-copilot-prod` (para leer `roca-copilot-sync-agent-secret`)

Comandos template para Fase 5 (reemplazar `$MI_PRINCIPAL_ID` con el `principalId` del Logic App MI una vez creado):

```bash
MI_PRINCIPAL_ID=<principalId del Logic App MI>
SEARCH_SCOPE=/subscriptions/fea67fdf-9603-4c86-a590-cd12390b7efd/resourceGroups/rg-roca-copilot-prod/providers/Microsoft.Search/searchServices/srch-roca-copilot-prod
STORAGE_SCOPE=/subscriptions/fea67fdf-9603-4c86-a590-cd12390b7efd/resourceGroups/rg-roca-copilot-prod/providers/Microsoft.Storage/storageAccounts/strocacopilotprod
AOAI_SCOPE=/subscriptions/fea67fdf-9603-4c86-a590-cd12390b7efd/resourceGroups/rg-admin.copilot-9203/providers/Microsoft.CognitiveServices/accounts/rocadesarrollo-resource
KV_SCOPE=/subscriptions/fea67fdf-9603-4c86-a590-cd12390b7efd/resourceGroups/rg-roca-copilot-prod/providers/Microsoft.KeyVault/vaults/kv-roca-copilot-prod

az role assignment create --assignee $MI_PRINCIPAL_ID --role "Search Index Data Contributor"  --scope $SEARCH_SCOPE
az role assignment create --assignee $MI_PRINCIPAL_ID --role "Storage Blob Data Contributor"  --scope $STORAGE_SCOPE
az role assignment create --assignee $MI_PRINCIPAL_ID --role "Cognitive Services User"        --scope $AOAI_SCOPE
az role assignment create --assignee $MI_PRINCIPAL_ID --role "Key Vault Secrets User"         --scope $KV_SCOPE
```

**Resumen de recursos Fase 3 (estado 2026-04-15)**:
| Recurso | Nombre | Ubicación | MI principalId |
|---|---|---|---|
| AI Search Basic | `srch-roca-copilot-prod` | eastus | `c9181743-c085-4885-8ff7-81392e0d2d5a` |
| Storage V2 LRS | `strocacopilotprod` | eastus2 | `c39ba7f1-1898-4c15-bded-9bf4d2bc06eb` |
| Log Analytics | `log-roca-copilot-prod` | eastus2 | — |
| Application Insights | `appi-roca-copilot-prod` | eastus2 | — |
| Action Group | `ag-roca-copilot-prod` | global | — |
| Budget | `budget-roca-copilot-prod` | RG | ⚠ deuda D-1 — bloqueado por MCA billing |
| OpenAI chat deployment | `gpt-5-mini` @ `rocadesarrollo-resource` | eastus2 | — |
| OpenAI embed deployment | `text-embedding-3-small` @ `rocadesarrollo-resource` | eastus2 | — |

**Entregable**: biblioteca lista, monitores prendidos, `.env.example` creado en `/Users/datageni/Documents/ai_azure/.env.example`.

#### Smoke tests end-to-end (2026-04-15)

Después de cerrar Fase 3 se corrieron smoke tests de todos los componentes críticos. Resultado: **6 de 6 PASS** (2 bugs encontrados y corregidos en el camino).

| #   | Componente                                                           | Resultado               | Notas                                                                                                                                                  |
| --- | -------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | SharePoint auth con sync robot (client_credentials)                  | ✅ PASS                 | Token Graph obtenido desde el secret en KV. Ambos sites accesibles.                                                                                    |
| 2   | Lista de drives en `ROCA-IAInmuebles`                                | ✅ PASS                 | 4 document libraries: `Documentos semantica copilot`, `Biblioteca de suspensiones de conservación`, `Lista de configuración de búsqueda`, `Documentos` |
| 3   | Lista de archivos reales en `30. Contrato de arrendamiento y anexos` | ✅ PASS                 | PDFs reales listables con size + mimeType. Ejemplo: `Contrato de Arendamiento Minglida.pdf` (101 MB), `Contrato Roca - Supplier's City.pdf` (4.2 MB)   |
| 4   | `gpt-5-mini` chat completion                                         | ✅ PASS (tras ajuste)   | Ver hallazgo #2 abajo — requirió subir `max_completion_tokens` a 500.                                                                                  |
| 5   | `text-embedding-3-small` embeddings                                  | ✅ PASS                 | Dimensiones 1536 confirmadas, response válida en primer intento.                                                                                       |
| 6   | Storage `ocr-raw` upload/read/delete (AAD auth)                      | ✅ PASS (tras fix RBAC) | Ver hallazgo #3 abajo — requirió asignar `Storage Blob Data Contributor` al usuario.                                                                   |
| 7   | AI Search service stats                                              | ✅ PASS                 | Service alive, 0 docs, 0 indexes, cuota 15 indexes max.                                                                                                |

#### Hallazgos críticos del smoke test (acciones correctivas aplicadas)

**Hallazgo #1 — SharePoint hostname incorrecto en docs/env**

- **Qué pasó**: el hostname correcto del tenant ROCA es **`rocadesarrollos1.sharepoint.com`** (con el `1`), no `rocadesarrollos.sharepoint.com`. Graph API retorna `invalidRequest — Invalid hostname for this tenancy` con el host equivocado.
- **Por qué**: el tenant tiene dominio custom `rocadesarrollos.com` pero el root onmicrosoft es `rocadesarrollos1.onmicrosoft.com` (con el `1`), y SharePoint URLs siempre se derivan del root onmicrosoft, no del custom domain.
- **Fix aplicado**: `.env.example` corregido. Memoria `project_roca_sharepoint_hostname.md` creada.
- **Impacto en fases siguientes**: cualquier Logic App connector, script de sync, o config de Foundry debe usar `rocadesarrollos1.sharepoint.com`.

**Hallazgo #2 — gpt-5-mini consume muchos reasoning tokens**

- **Qué pasó**: prompt trivial (`"Responde OK"`) con `max_completion_tokens: 50` retornó output vacío. El modelo quemó los 50 tokens en reasoning interno y no le sobró presupuesto para el output visible. Con `max_completion_tokens: 500` → reasoning=320, completion=332, output visible `"CDMX"`.
- **Por qué**: `gpt-5-mini` es un reasoning model (familia gpt-5). Antes de producir output visible, genera "reasoning tokens" internos que cuentan contra `max_completion_tokens` y contra el costo facturado.
- **Fix aplicado**: memoria `feedback_gpt5_reasoning_tokens.md` creada con reglas de presupuesto.
- **Impacto en fases siguientes**:
  - **NUNCA** poner `max_completion_tokens < 300` con gpt-5-mini.
  - ~~Para discovery de metadata sobre PDFs en Fase 4A: presupuestar `max_completion_tokens: 4000` (JSON grande + reasoning overhead).~~ **CORREGIDO 2026-04-15 tras Fase 4A**: `4000` es **insuficiente** para docs legales largos (46-47 páginas). Usar **`12000`** como default para discovery sobre PDFs grandes. Ver deuda D-6.
  - Para RAG queries en Fase 6 (respuestas al usuario final): `max_completion_tokens: 1500-2000` (pero validar con los docs reales en Fase 6 — puede requerir más).
  - Al estimar costos, sumar ~300-500 reasoning tokens fantasma por query.
  - Si se necesita respuesta corta con reasoning mínimo, usar parámetro `reasoning_effort: low` (cuando esté disponible en la API).

**Hallazgo #3 — `Owner` del RG ≠ data plane de Storage**

- **Qué pasó**: smoke test de blob storage (upload/read/delete con `--auth-mode login`) falló con "You do not have the required permissions". `admin.copilot@rocadesarrollos.com` es `Owner` del RG pero Owner es un rol **control plane** de RBAC — NO incluye permisos **data plane** sobre blobs.
- **Fix aplicado**: auto-asignado `Storage Blob Data Contributor` al usuario sobre `strocacopilotprod`. Smoke test pasó inmediatamente después de la propagación.
- **Impacto en fases siguientes**: el Logic App MI (Fase 5) necesitará `Storage Blob Data Contributor` sobre este storage — ya está documentado en los role assignments pendientes, pero este smoke test **confirma** que el patrón es necesario (no teórico). Cualquier script de desarrollo que use AAD también debe tener ese rol.

**Recursos de producción validados 2026-04-15**: Fases 1, 2 y 3 están efectivamente verificadas end-to-end antes de arrancar Fase 4A. No hay sorpresas escondidas.

---

### Fase 4A — Discovery (schema data-driven) `~2 horas` _(Claude ejecuta end-to-end)_

**Cambio 2026-04-15**: el plan original requería que el usuario bajara los PDFs manualmente "porque Fase 2 aún no estaba validada". Después del smoke test end-to-end que probó Sites.Selected + sync robot + Graph API, **esa restricción ya no aplica**. Claude usa el sync robot directamente para descargar la muestra de forma reproducible. Esto elimina el único bloqueante humano de Fase 4A y hace la muestra regenerable (re-correr el script con distintos parámetros sin re-trabajo manual).

**Paso 4A.1 — Descarga automatizada de muestra representativa** _(Claude ejecuta, ~5 min)_:

- [x] **2026-04-15** — Escribir `azure-ai-contract-analysis/scripts/ingestion/download_sample_pdfs.py`:
  - Lee el secret `roca-copilot-sync-agent-secret` del KV
  - Autentica contra Entra ID con `client_credentials` usando el sync robot
  - Usa `rocadesarrollos1.sharepoint.com` como hostname (ver memoria `project_roca_sharepoint_hostname.md`)
  - Recorre las carpetas canónicas de `ROCA-IAInmuebles`: `07. Permisos de construcción`, `11. Estudio fase I - Ambiental`, `30. Contrato de arrendamiento y anexos`, `33. Constancia situacion fiscal`, `65. Planos arquitectonicos (As built)`
  - Descarga 3–4 PDFs representativos por carpeta (filtro `application/pdf`, máximo 50 MB por archivo para no tardar)
  - Incluye también una muestra de 2–3 PDFs del site 2 (`ROCAIA-INMUEBLESV2` → `FESWORLD`)
  - Guarda en `/Users/datageni/Documents/ai_azure/contratosdemo_real/` con convención de nombre `{site}__{carpeta_origen}__{archivo_original}.pdf` para preservar la taxonomía original (crítico para validar el discovery)
  - Total esperado: 15–22 PDFs, ~200–500 MB
- [x] **2026-04-15** — Correr el script y verificar que la muestra esté balanceada — resultado v1: **18 PDFs, 35 MB, 6 carpetas canónicas**. **Ampliación v2 (misma fecha)**: **45 PDFs / 38 únicos por hash**, 9 fuentes (3 drives del site 1 explorados por primera vez). Se detectaron 5 grupos de duplicados (27% del dataset) que llevaron a agregar `content_hash` + `alternative_urls` al schema.

**Paso 4A.2 — OCR + discovery** _(Claude ejecuta, ~30–60 min dependiendo del tamaño)_:

- [x] **2026-04-15** — Correr OCR con Document Intelligence (`prebuilt-layout`) sobre la muestra. Guardar el JSON crudo del OCR en el container `ocr-raw` del storage para poder re-ingresar el pipeline sin re-pagar OCR. Script: `scripts/ingestion/run_ocr_sample.py`. Resultado: 18/18 procesados, 18 blobs en `ocr-raw/sample_discovery/` + 18 copias locales en `contratosdemo_real/ocr_raw/`.
- [x] **2026-04-15** — Correr prompt de discovery con `gpt-5-mini` (abierto, no estructurado). Script: `scripts/ingestion/run_discovery.py`. **Gotcha encontrado**: con `max_completion_tokens=4000` los 2 poderes legales largos (46-47 páginas, 89K-120K chars) quemaron los 4000 tokens enteros en reasoning interno sin producir output visible — se subió a **12000** y se reintentaron. Resultado final: 18/18 JSONs parseados OK, 0 vacíos.
- [x] **2026-04-15** — Agregar resultados y extraer patrones. Script: `scripts/ingestion/aggregate_discovery.py`. Reporte generado en `FASE_4A_DISCOVERY_REPORT.md` (8 tipos detectados, 81 códigos únicos, 14 RFCs, 3 formatos de fecha distintos).
- [x] **2026-04-15** — Redactar reporte de hallazgos con ejemplos reales — ver `FASE_4A_DISCOVERY_REPORT.md` §10 con citas literales por tipo de documento.
- [x] **2026-04-15** — Proponer schema final Capa 1 + Capa 2 + Capa 3 basado en data real — ver `FASE_4A_SCHEMA_PROPUESTO.md` **v2** (32 campos: 17 Capa 1 + 14 Capa 2 + 1 Capa 3). Cambios v1→v2: agregados `content_hash` y `alternative_urls` en Capa 1 como respuesta al hallazgo de duplicación del 27%; `parent_document_id` se deriva del hash, NO del path de SharePoint. Enum de `doc_type` ampliado a 21 valores (20 explícitos + `otro`) tras detectar 17 tipos distintos en la muestra ampliada.

#### Resultados Fase 4A (2026-04-15, iteración v2 con muestra ampliada)

**Cambio de iteración**: la primera corrida con 18 PDFs mostró sesgos evidentes (solo cubría el drive principal "Documentos" del site 1 y una sola carpeta del site 2). Se amplió la muestra a 9 fuentes distintas incluyendo 3 drives del site 1 que nunca habíamos explorado. Esta es la versión final.

**Muestra final**: **45 PDFs físicos / 38 únicos por content_hash** descargados vía sync robot (`roca-copilot-sync-agent`), total ~270 MB (~35 MB antes de descubrir los docs grandes de Principal/Biblioteca). Distribución por fuente:

| Fuente (drive / folder)                               | Site               | PDFs bajados | PDFs únicos             |
| ----------------------------------------------------- | ------------------ | ------------ | ----------------------- |
| `Documentos / 07. Permisos de construcción`           | ROCA-IAInmuebles   | 3            | 3                       |
| `Documentos / 11. Estudio fase I - Ambiental`         | ROCA-IAInmuebles   | 1            | 1                       |
| `Documentos / 30. Contrato de arrendamiento y anexos` | ROCA-IAInmuebles   | 4            | 3 (1 dup)               |
| `Documentos / 33. Constancia situacion fiscal`        | ROCA-IAInmuebles   | 4            | 4                       |
| `Documentos / 65. Planos arquitectonicos (As built)`  | ROCA-IAInmuebles   | 5            | 5                       |
| `Documentos / Principal`                              | ROCA-IAInmuebles   | 2            | 2                       |
| `Biblioteca de suspensiones de conservación / <root>` | ROCA-IAInmuebles   | 12           | 8 (4 dup)               |
| `Documentos semantica copilot / <root>`               | ROCA-IAInmuebles   | 1            | 1 (dup de 07. Permisos) |
| `Documentos / FESWORLD`                               | ROCAIA-INMUEBLESV2 | 13           | 11                      |
| **TOTAL**                                             |                    | **45**       | **38**                  |

**17 tipos de documento detectados por gpt-5-mini** sobre los 38 únicos (vs 8 en la v1):

| `tipo_documento`                   | Cantidad |
| ---------------------------------- | -------- |
| `plano_arquitectonico`             | 13       |
| `constancia_situacion_fiscal`      | 8        |
| `licencia_construccion`            | 3        |
| `estudio_ambiental`                | 1        |
| `acta_asamblea`                    | 1        |
| `escritura_publica`                | 1        |
| `contrato_arrendamiento`           | 1        |
| `escritura_publica_acta_asamblea`  | 1        |
| `constancia_curp`                  | 1        |
| `recibo_servicio`                  | 1        |
| `contrato_compraventa`             | 1        |
| `estados_financieros_auditados`    | 1        |
| `constancia_uso_suelo`             | 1        |
| `factura_electronica`              | 1        |
| `estudio_geotecnico`               | 1        |
| `contrato_desarrollo_inmobiliario` | 1        |
| `garantia_corporativa`             | 1        |

**Costo total Fase 4A (ambas iteraciones)**:

- **OCR Document Intelligence**: 45 PDFs OCR'd (~1,100 páginas totales incluyendo título de propiedad de 464 pp + escritura de ~400 pp) → ~$9.30 USD
- **gpt-5-mini discovery**: 354K prompt tokens + 105K completion (55K reasoning + 50K visible) → ~$0.15 USD
- **Embeddings**: $0 (Fase 4B)
- **Total Fase 4A v1+v2**: **~$9.50 USD**

**Entregables físicos**:

- `contratosdemo_real/*.pdf` — 45 PDFs (incluye duplicados físicos para evidencia)
- `contratosdemo_real/_content_hash_dedup.json` — mapa hash→canonical para trazabilidad
- `contratosdemo_real/ocr_raw/*.json` — 45 OCR JSONs (también en `strocacopilotprod/ocr-raw/sample_discovery/`)
- `contratosdemo_real/discovery/*_discovery.json` — 38 discovery outputs (dedup-aware)
- [`FASE_4A_DISCOVERY_REPORT.md`](FASE_4A_DISCOVERY_REPORT.md) — reporte agregado con evidencia forense + sección §14 de duplicación
- [`FASE_4A_SCHEMA_PROPUESTO.md`](FASE_4A_SCHEMA_PROPUESTO.md) — schema v2 en 3 capas (**32 campos**, +content_hash +alternative_urls)
- `scripts/ingestion/{download_sample_pdfs,run_ocr_sample,run_discovery,aggregate_discovery,explore_sharepoint_folders}.py` — 5 scripts one-shot idempotentes

**Hallazgos sorprendentes (v1 + v2)**:

1. **La carpeta canónica NO garantiza un solo tipo de doc**: el discovery por LLM es obligatorio, no opcional. Ej: carpeta `30. Contratos` contiene contratos, actas, escrituras, poderes legales — todos tipos distintos.
2. **Los poderes legales largos rompen el budget de reasoning tokens**: 2 de 18 en v1 y 0 de 20 en v2 con `max_completion_tokens=12000`. Queda documentado como deuda D-6 para Fase 5.
3. **Los "códigos de inmueble" son heterogéneos**: mezclan códigos reales (`RA03`, `RE05A`), drawing numbers, escrituras, claves catastrales, números de oficio, bitácoras. El schema maneja esto con `inmueble_codigos: Collection` sin normalización destructiva.
4. **🔑 Duplicación masiva en SharePoint — hallazgo más importante de la v2**: 7 de 45 PDFs (16%) son duplicados exactos por hash. El mismo archivo físico vive en múltiples drives/carpetas con nombres radicalmente distintos (ej: `7-ELEVEN_CLTXX170_GESTORIA_PERMISO_DE_CONSTRUCCION` es byte-idéntico a `RA03_LICENCIA_DE_CONSTRUCCION`). **Consecuencias en el schema**: agregados `content_hash` y `alternative_urls` en Capa 1. **Consecuencia en Fase 5**: el Logic App debe hacer dedup por hash antes de OCRear (ver paso 2 de la lista de steps de Fase 5). Ahorro estimado en producción: $30-50 USD + ~16% de latencia de ingesta.
5. **`nombre_archivo` y `sharepoint_url` NO son identificadores confiables** del documento lógico. `parent_document_id` se deriva del `content_hash`, no del path.
6. **El drive "Biblioteca de suspensiones de conservación" es un repositorio de respaldo**, no un corpus de documentos originales. Casi todo lo que sacamos de ahí es duplicado de otras carpetas canónicas con GUIDs como sufijo.

**Próximo paso concreto para el usuario**:

1. Abrir `FASE_4A_SCHEMA_PROPUESTO.md` y `FASE_4A_DISCOVERY_REPORT.md` en VS Code / Obsidian.
2. Decidir una de las 4 opciones del §11 del schema (aprobar, editar, discusión, o ampliar muestra).
3. Cuando esté conforme, abrir nueva sesión de Claude Code con:
   > _"Schema de Fase 4A aprobado. Arranca Fase 4B del plan. Lee `FASE_4A_SCHEMA_PROPUESTO.md` como source of truth del schema final, crea el índice `roca-contracts-v1` en `srch-roca-copilot-prod`, adapta los scripts de ingesta al schema, corre el pipeline completo sobre la muestra de `contratosdemo_real/` y valida con queries R-04, R-05, R-17."_

**Entregable**: muestra descargada + reporte de discovery + schema propuesto para revisión del usuario. **Sin bloqueantes humanos previos** — el usuario solo interviene al final para aprobar el schema propuesto.

**Entregables físicos de Fase 4A (archivos que el usuario revisa)**:

- `/Users/datageni/Documents/ai_azure/contratosdemo_real/` — los 15-22 PDFs reales descargados del SharePoint
- `/Users/datageni/Documents/ai_azure/contratosdemo_real/ocr_raw/{pdf}.json` — copia local del OCR de cada doc (fuente de verdad para inspeccionar qué "vio" el sistema)
- `/Users/datageni/Documents/ai_azure/contratosdemo_real/discovery/{pdf}_discovery.json` — salida del discovery prompt de gpt-5-mini por cada doc
- `/Users/datageni/Documents/ai_azure/azure-ai-contract-analysis/FASE_4A_DISCOVERY_REPORT.md` — reporte agregado de patrones reales con citas literales del OCR
- `/Users/datageni/Documents/ai_azure/azure-ai-contract-analysis/FASE_4A_SCHEMA_PROPUESTO.md` — propuesta concreta del schema Azure AI Search en 3 capas (este es el archivo que el usuario APRUEBA antes de Fase 4B)

#### Review workflow — cómo revisar y iterar el schema antes de Fase 4B

Fase 4A termina con un **STOP intencional**. Claude NO arranca Fase 4B sin tu aprobación explícita del schema. Esta pausa existe para que puedas revisar con calma, discutir con Claude si hay dudas, e iterar en los entregables basado en data real antes de materializar el índice y gastar más recursos.

**Opción A — Edición directa del schema (el camino rápido)**:

- Abre `FASE_4A_SCHEMA_PROPUESTO.md` en Obsidian o VS Code
- Edita directamente: cambia tipos de campo, agrega/quita campos, mueve cosas entre Capa 2 y Capa 3, agrega comentarios tipo `> CAMBIO: esto no tiene sentido porque...`
- En la siguiente sesión de Claude Code le dices: _"Lee el schema actualizado en `FASE_4A_SCHEMA_PROPUESTO.md` — ya lo edité. Aplica mis cambios y arranca Fase 4B."_
- Claude respeta tus ediciones como source of truth y materializa el índice con el schema final

**Opción B — Sesión de discusión read-only (el camino cuando tienes dudas)**:

Cuando NO entiendes una decisión del schema o quieres explorar alternativas antes de decidir, abre una nueva sesión de Claude Code con un prompt estilo "audit/discussion" (sin ejecución):

```
Context: Fase 4A del proyecto ROCA Copilot está completa. Tengo dudas sobre
el schema propuesto antes de aprobar Fase 4B.

Lee estos archivos como contexto:
- PLAN_ROCA_COPILOT.md (sección Fase 4A + schema en 3 capas)
- FASE_4A_DISCOVERY_REPORT.md
- FASE_4A_SCHEMA_PROPUESTO.md
- contratosdemo_real/discovery/*.json (los outputs del discovery)
- contratosdemo_real/ocr_raw/*.json (los OCRs raw — fuente de verdad)

Scope: READ ONLY. No edites NADA todavía.

Quiero discutir:
1. [tu pregunta concreta — ej: "por qué codigo_inmueble está en Capa 2 si
   solo aparece en 12 de 20 docs?"]
2. [otra pregunta]

Rules:
- Responde basado EXCLUSIVAMENTE en los documentos reales descargados, no
  en suposiciones genéricas sobre inmobiliarias
- Si te pregunto "¿qué pasa si agrego X campo?" contéstame con qué 3
  documentos reales lo justificarían o no, citando el texto literal del OCR
- Si no tienes evidencia en la muestra, di "no hay evidencia en los 20 PDFs
  descargados — necesitamos ampliar la muestra antes de decidir"
- No propongas cambios sin que yo los pida
- Si mi pregunta revela un gap en el discovery, puedes recomendar correr
  discovery sobre más docs (pero NO lo ejecutes — lo discutimos primero)
```

**Tipos de preguntas que puedes hacer en la sesión de discusión**:

| Pregunta                                                                                                 | Para qué sirve                                                       |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| "¿Por qué este campo está en Capa 2 y no Capa 3?"                                                        | Entender el rationale de data density                                |
| "Muéstrame los 3 docs donde aparece `vigencia_fin` y cítame el texto exacto"                             | Validar que el campo realmente existe y no es alucinación            |
| "¿Qué pasaría si agrego un campo `garantia_deposito`?"                                                   | Explorar extensiones basadas en tu conocimiento del negocio          |
| "El reporte dice que hay inconsistencias en fechas — muéstrame los 5 formatos distintos que encontraste" | Ver evidencia real antes de decidir normalización                    |
| "¿Este schema va a funcionar para el caso de R-07 (última versión del documento)?"                       | Cruzar el schema propuesto con los requisitos originales R-01 a R-19 |
| "Si en vez de 20 PDFs hubieras tenido 100, ¿qué patrón crees que saldría diferente?"                     | Detectar sesgos de muestra pequeña                                   |
| "¿Qué campos faltarían si mañana ROCA me pide agregar contratos de compraventa?"                         | Stress-test el schema contra futuros casos de uso                    |

**Opción C — Iterar el discovery sobre más documentos**:

Si al revisar el reporte te das cuenta de que la muestra de 15-22 PDFs es sesgada (ej: todos los contratos son del mismo cliente, ninguno es de cierto tipo, faltó representación de una taxonomía), puedes pedirle a Claude que:

- Amplíe la muestra con criterios específicos ("descarga 10 PDFs más enfocados en permisos de construcción que contengan planos arquitectónicos")
- Re-corra el discovery solo sobre los nuevos
- Agregue los hallazgos nuevos al reporte existente (append, no rewrite)
- Re-genere el schema propuesto con la nueva evidencia

Este loop es **barato** — cada iteración del discovery cuesta ~$2-5 USD y toma 10-15 min. Úsalo libremente antes de Fase 4B, donde los costos suben porque creas índices reales, corres embeddings sobre todo, y materializas infraestructura.

**Cómo se ve la aprobación final**:

Cuando estés conforme con el schema, abres una nueva sesión y le dices a Claude:

```
Schema de Fase 4A aprobado. Arranca Fase 4B del plan:
- Lee FASE_4A_SCHEMA_PROPUESTO.md como source of truth del schema final
- Crea el índice `roca-contracts-v1` en srch-roca-copilot-prod con ese schema
- Adapta los scripts de ingesta a ese schema
- Corre el pipeline completo sobre la muestra de contratosdemo_real/
- Valida con queries de prueba R-04, R-05, R-17
```

A partir de ahí Claude ejecuta Fase 4B sin más ceremonia. La decisión de arquitectura ya está tomada por ti.

**Regla importante**: NO modifiques `FASE_4A_DISCOVERY_REPORT.md` a mano. Ese archivo es evidencia forense del estado del dataset en el momento del discovery. Si encuentras errores en el reporte, documenta tu objeción como comentario en `FASE_4A_SCHEMA_PROPUESTO.md` (o en un archivo separado `FASE_4A_OBJECIONES.md`) — preservar el reporte original te permite trazar decisiones en auditorías futuras.

---

### Fase 4B — Schema validation + ingesta completa `~2 horas` _(Claude ejecuta, usuario valida)_ ✅ COMPLETA 2026-04-15

- [x] **2026-04-15** — Usuario aprueba el schema v2 (32 campos) implícitamente al aprobar Fase 4B
- [x] **2026-04-15** — Backfill de metadatos reales de SharePoint (script `backfill_sharepoint_metadata.py`): 38/38 PDFs matched con webUrl, itemId, driveId, parentPath, lastModifiedDateTime — guardado en `contratosdemo_real/_sharepoint_metadata.json`
- [x] **2026-04-15** — Cleanup smoke: agent `roca-copilot-smoke` (3 versiones) borrado, índice `roca-contracts-smoke` borrado, connection smoke borrada, query key y secret KV smoke borrados. Role assignments redundantes no se pudieron borrar por el `CanNotDelete` lock del RG (son aditivos, no causan daño).
- [x] **2026-04-15** — Asignar `Cognitive Services OpenAI User` al MI del search service (`c9181743-...`) sobre `rocadesarrollo-resource` — prerequisito del integrated vectorizer.
- [x] **2026-04-15** — Script `create_prod_index.py` crea `roca-contracts-v1` con **32 campos schema v2 completo + integrated vectorizer** (`aoai-vectorizer` → `text-embedding-3-small`) + semantic config + HNSW. Campos de security trimming (`group_ids`, `user_ids`) declarados pero vacíos (Fase 5 los poblará).
- [x] **2026-04-15** — Script `ingest_prod.py` procesa los 38 docs únicos con dedup por hash, reutiliza OCR + discovery ya procesados ($0 en re-OCR), chunking 2000 chars con overlap 200, cap 60 chunks por doc para docs monstruo (título de propiedad 464 pp, escritura 156, contrato 114), embeddings batch de 16 con retry, upsert en batches de 100. **543 chunks totales, 0 fallidos.**
- [x] **2026-04-15** — **FIX crítico**: el tool `azure_ai_search` de Foundry **solo expone el campo `content` al modelo**, NO los demás campos tipados del índice. Sin este fix, el agent alucinaba URLs y no respetaba `es_vigente`. Solución: prepender a cada chunk un bloque `[METADATOS ESTRUCTURADOS DEL DOCUMENTO]` con todos los campos relevantes (archivo, doc_type, inmuebles, partes, fechas, vigencia calculada con razón, autoridad, URL real) antes del texto OCR. Re-ingesta completa ($0.01 extra en embeddings).
- [x] **2026-04-15** — Crear connection `roca-search-prod` en Foundry project (authType=AAD, apunta a `srch-roca-copilot-prod` con ResourceId completo)
- [x] **2026-04-15** — Crear agente final `roca-copilot` v1: modelo `gpt-4.1-mini`, tool `Azure AI Search` → `roca-contracts-v1` con `query_type=vector_semantic_hybrid` + top_k=6, instructions extensas con reglas de citación, honestidad, filtros por inmueble, distinción vigente/vencido, tono en español mexicano
- [x] **2026-04-15** — Validación end-to-end con 4 queries invocando el agent programáticamente via `openai.responses.create(agent_reference=...)`:
  - **R-05 Contratos RA03** → Respuesta perfecta: BANCO ACTINVER + SUPPLIER'S CITY, 10,121 m², $70,713.50 USD/mes, URL real clickeable
  - **R-04 Licencias RE05A** → Respuesta perfecta: Municipio de Reynosa, fechas 2022-06-29 a 2024-06-29, **"actualmente vencida y no vigente"** (respeta `es_vigente=false`), URL real clickeable
  - **R-14 RFC Maquimex** → `MOP210705IC6` con URL real + cita también la segunda constancia con el mismo RFC
  - **R-17 negativa honesta (RA99)** → "No encontré información", sin alucinar

**Entregable**: índice `roca-contracts-v1` poblado con 38 docs (543 chunks) + agente `roca-copilot` funcional validado end-to-end. Costo total Fase 4B: **~$0.02 USD** (embeddings + queries de validación, OCR reutilizado).

#### Resultados Fase 4B (2026-04-15)

**Recursos finales de producción (smoke validado)**:

| Recurso                    | Nombre                                                                                    | Estado                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| AI Search index            | `roca-contracts-v1`                                                                       | 32 campos + integrated vectorizer, 543 chunks indexados |
| Foundry project connection | `roca-search-prod`                                                                        | authType=AAD, apunta a `srch-roca-copilot-prod`         |
| Foundry agent              | `roca-copilot` v1                                                                         | gpt-4.1-mini + AI Search tool, status active            |
| OpenAI deployments         | `gpt-5-mini` + `gpt-4.1-mini` + `text-embedding-3-small`                                  | Todos `Succeeded`                                       |
| Sample físico              | 45 PDFs en `contratosdemo_real/` (38 únicos por hash)                                     | Evidencia forense                                       |
| OCR cache                  | 45 JSONs en `contratosdemo_real/ocr_raw/` + `strocacopilotprod/ocr-raw/sample_discovery/` | Reutilizable sin re-pagar OCR                           |
| Discovery output           | 38 JSONs en `contratosdemo_real/discovery/`                                               | Reutilizable                                            |
| SharePoint metadata        | `contratosdemo_real/_sharepoint_metadata.json`                                            | webUrl real + itemId + driveId                          |
| Dedup map                  | `contratosdemo_real/_content_hash_dedup.json`                                             | 5 grupos de duplicados detectados                       |

**Scripts de Fase 4A + 4B (todos idempotentes, one-shot)**:

- `scripts/ingestion/download_sample_pdfs.py`
- `scripts/ingestion/run_ocr_sample.py`
- `scripts/ingestion/run_discovery.py` (con dedup por hash)
- `scripts/ingestion/aggregate_discovery.py`
- `scripts/ingestion/explore_sharepoint_folders.py`
- `scripts/ingestion/backfill_sharepoint_metadata.py` _(nuevo 4B)_
- `scripts/ingestion/create_prod_index.py` _(nuevo 4B)_
- `scripts/ingestion/ingest_prod.py` _(nuevo 4B, con metadata header embebido)_
- `scripts/ingestion/create_smoke_index.py` + `smoke_ingest.py` _(obsoletos tras cleanup, quedan de referencia)_

**Hallazgos sorprendentes de Fase 4B (importantes para Fase 5 y 6)**:

1. **`gpt-5-mini` NO es compatible con tool Azure AI Search en Foundry v2** — la doc oficial confirma que GPT-5 family solo soporta `file_search` + `code_interpreter`, no `azure_ai_search`. Workaround: desplegar `gpt-4.1-mini` como modelo específico del agente (pay-per-use, $0 recurrente). `gpt-5-mini` se sigue usando para el discovery pipeline donde es más barato. Memoria `feedback_foundry_gpt5_no_aisearch_tool.md`.
2. **Foundry v2 tiene 3 identidades jerárquicas** (AIServices account MI, Project MI, Agent Identity). La doc oficial dice asignar RBAC al **Project MI** con `Search Index Data Contributor` + `Search Service Contributor`. No al agent identity. Memoria `feedback_foundry_agent_mi_is_parent_account.md`.
3. **El tool `azure_ai_search` con `vector_semantic_hybrid` requiere integrated vectorizer en el índice** — sin vectorizer, el agent falla con un error genérico "Access denied" que enmascara el error real del schema. Memoria `feedback_foundry_vectorizer_required.md`.
4. **El tool `azure_ai_search` solo expone el campo `content` al modelo por default**, no los demás campos tipados. Sin prepender metadata al `content`, el modelo alucina URLs y no respeta valores calculados como `es_vigente`. Fix aplicado: metadata header en cada chunk durante ingesta.
5. **El agent identity ID del plan original (`asst_I1unL8WG7qDjaz8nNJ0PCkkw`) era un fantasma** de la API legacy OpenAI Assistants que no existe en Foundry v2. El único agente real del project era un placeholder vacío `Agent932` que el usuario borró. El agente actual es `roca-copilot` v1 creado desde cero con todas las lecciones aprendidas.

**Deudas técnicas nuevas abiertas en Fase 4B**:

- **D-7**: Security trimming vacío en `roca-contracts-v1` — los campos `group_ids` / `user_ids` están declarados pero sin poblar. Se poblarán automáticamente en Fase 5 cuando el Logic App lea las ACLs de SharePoint para cada archivo. **NO publicar a Teams hasta que esto esté hecho.**
- **D-8**: Role assignments redundantes sobre `srch-roca-copilot-prod` (agent identity `8043efd9-...`, AIServices account MI `0a7473b6-...`, user `1254a9b5-...`) no se pudieron borrar por el CanNotDelete lock del RG. Son aditivos, no causan daño, pero hay que limpiarlos manualmente removiendo el lock temporalmente en un mantenimiento futuro.

---

### Fase 5 — Automatización production (Azure Durable Functions) ✅ COMPLETA 2026-04-15

> **Pivot arquitectural**: el plan original especificaba Logic App Standard. Se pivotó a Azure Durable Functions por 3 hard-blockers documentados en `FASE_5_DESIGN_DECISIONS.md`. Microsoft valida este patrón con el sample oficial `Azure-Samples/MicrosoftGraphShadow`.

- [x] **2026-04-15** — Crear Function App `func-roca-copilot-sync` (Y1 Consumption Linux Python 3.11) con SystemAssigned MI
- [x] **2026-04-15** — Asignar 6 roles RBAC al MI: Search Index Data Contributor, Storage Blob Data Contributor (account), Storage Queue Data Contributor (account), Cognitive Services User, Key Vault Secrets User
- [x] **2026-04-15** — Crear índice `roca-contracts-v1-staging` para testing (35 campos, integrated vectorizer)
- [x] **2026-04-15** — Escribir y desplegar código Durable Functions (658 líneas `function_app.py` + 11 módulos `shared/`)
- [x] **2026-04-15** — Configurar 4 triggers: `timer_sync_delta` (5 min), `timer_acl_refresh` (1h), `timer_full_resync` (dom 3am), `http_manual_process` (on-demand)
- [x] **2026-04-15** — Implementar pipeline: download Graph → MD5 hash → dedup check → ACL extraction → Document Intelligence OCR → gpt-4.1-mini extraction → chunking con metadata header → embeddings → upsert con group_ids/user_ids
- [x] **2026-04-15** — Crear DLQ storage queue `roca-dlq` con logging `[ROCA-DLQ-WRITE]`
- [x] **2026-04-15** — Retry policies explícitas con `df.RetryOptions` en todos los `call_activity_with_retry`
- [x] **2026-04-15** — Crear `deploy.sh` helper para futuros updates de código
- [x] **2026-04-15** — Validar pipeline end-to-end: 572 chunks en staging → promover a prod → 1370 chunks en prod
- [x] **2026-04-15** — D-9 aplicado: todo el código usa `gpt-4.1-mini` + `max_completion_tokens=4000`
- [x] **2026-04-15** — D-7 parcial: pipeline SÍ puebla `group_ids`/`user_ids` via Graph API

**Pipeline en producción**:

```
func-roca-copilot-sync (corriendo 24/7 en Azure, $0/mes)
├── timer_sync_delta       (cada 5 min)  → Graph delta query → fan-out process_item_activity
├── timer_acl_refresh      (cada 1 hora) → refresca permisos de docs indexados
├── timer_full_resync      (dom 3am UTC) → safety net: enumera TODO y sincroniza diferencias
├── http_manual_process    (POST)        → dispatch manual para testing/operaciones
├── http_health            (GET)         → smoke test del estado del app
└── 4 orchestrators + 7 activities + delta token state en blob
```

**Para actualizar el código del pipeline**:

```bash
cd function_app/
# editar archivos Python
./deploy.sh                    # deploy normal (reusa deps existentes)
./deploy.sh --refresh-deps     # si cambias requirements.txt
```

**Para encender/apagar el pipeline** (ej: evitar 429 mientras usas el playground):

```bash
az functionapp stop --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
az functionapp start --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
```

**Entregable**: sync automático 24/7 con dedup por hash + security trimming + metadata extraction con gpt-4.1-mini. Costo: $0/mes fijo (Consumption free tier). ~$1-2 USD por corrida completa de re-ingesta (~76 docs).

---

### Fase 6 — Conectar agente + iteración completa en Foundry Playground `~3-5 horas` _(Claude ejecuta, usuario valida)_

⚠️ **ESTA FASE NO TOCA TEAMS NI M365 COPILOT**. Todo sucede dentro de `https://ai.azure.com` en el Playground del agente.

**Paso 6.1 — Conexión técnica** (~30 min):

- [x] **2026-04-15** — Crear connection "Azure AI Search" en Foundry project `rocadesarrollo` — **`roca-search-smoke`** creada vía ARM API (`Microsoft.CognitiveServices/accounts/projects/connections`, api-version `2025-12-01`). **Nota importante**: el SDK `azure-ai-projects` v2 solo expone `get/list` de connections — NO tiene `create`. Para Fase 6 real, crear la connection de producción via ARM PUT o vía portal.
- [x] **2026-04-15** — Crear agente nuevo `roca-copilot-smoke` con `gpt-4o-mini` + `AzureAISearchTool` → índice `roca-contracts-smoke`, query_type=`vector_semantic_hybrid`, top_k=5, instructions específicas del dominio inmobiliario ROCA. **Descubrimiento clave**: `gpt-5-mini` NO es compatible con el tool nativo `Azure AI Search` en Foundry (Microsoft doc oficial confirma que "GPT-5 models cannot be used in Azure OpenAI for 'add your own data' scenario"). Workaround: desplegamos `gpt-4o-mini` en el mismo AIServices account (pay-per-use, $0 recurrente) específicamente para agentes. `gpt-5-mini` se sigue usando para discovery/extracción en ingesta.
- [ ] Fase 6 real: validar en playground con R-01..R-19 y decidir si se mantiene `gpt-4o-mini` o se evalúa Claude (via MCP/function calling custom, opción premium)

**Paso 6.1b — Custom function tool para security filter** (~3 horas):

- [ ] Crear custom function tool `build_security_filter(user_id)` en el agente:
  - Input: `user_id` del contexto de la conversación
  - Implementación: llama Graph API `GET /users/{user_id}/transitiveMemberOf?$select=id,displayName` con el Project MI
  - Output: string con filtro OData `"(group_ids/any(g:search.in(g, 'grp1,grp2,...')) or user_ids/any(u:search.in(u, 'userId')))"`
  - Caching: cachear resultado por usuario por 5 minutos para reducir llamadas a Graph
  - Fail-closed: si Graph API falla, retornar filtro vacío que matchea 0 docs (NUNCA retornar "todos los docs")
- [ ] Registrar el tool en el agente
- [ ] Test manual: invocar con 2 user IDs distintos y verificar que retornan filtros diferentes

**Paso 6.2 — System prompt del agente** (~1 hora):

- [ ] Escribir instrucciones base del agente:
  - Rol: asistente de gestión documental de inmuebles ROCA
  - **Security enforcement**: _"ANTES de cualquier query a AzureAISearchTool, DEBES llamar `build_security_filter` con el user_id del contexto. Usa el filtro retornado como parte del query filter. JAMÁS hagas queries sin el security filter."_
  - Reglas de respuesta: **SOLO texto plano, sin tablas markdown ni citations complejas** (restricción Teams ya bakeada desde el inicio)
  - Formato de respuestas para R-05, R-11, R-14, R-19: lista línea-por-línea con `Campo: valor`
  - Instrucción de citar URL de SharePoint en cada respuesta
  - Variable dinámica `{today}` para R-12
  - Prompt de "si no encuentras info, dilo explícitamente" (para R-04) — esto también cubre el caso "no tienes permiso" sin leakear info
  - Placeholder para checklist maestro de permisos para R-11 (si ya se tiene)
- [ ] Guardar versión inicial del prompt en el repo (`agents/contratos_rocka/prompts/system_v1.md`)

**Paso 6.3 — Ejecución de matriz de pruebas en Playground** (~3 horas):

- [ ] Correr los 19 casos R-01 a R-19 uno por uno en el Foundry Playground
- [ ] Por cada caso documentar: query exacta, respuesta recibida, PASS/FAIL, comentarios
- [ ] Capturar screenshots del Playground para evidencia

**Paso 6.3b — Tests de seguridad con múltiples usuarios** (~2 horas):

- [ ] Crear/identificar al menos 3 usuarios de prueba en el tenant con diferentes membresías de grupos:
  - Usuario A: miembro de grupo con acceso a TODOS los docs (equivalente a Moisés director)
  - Usuario B: miembro de grupo con acceso a SOLO inmuebles específicos (equivalente a gerente de zona)
  - Usuario C: miembro de grupo sin acceso a docs sensibles (equivalente a becario)
- [ ] Por cada usuario, correr una batería de queries incluyendo:
  - Pregunta "inofensiva" (info pública) → debe retornar
  - Pregunta sensible (contrato de arrendamiento que NO le corresponde ver) → debe retornar "no encontré información" SIN leakear
  - Pregunta "¿cuáles son todos los inmuebles?" → cada usuario debe ver solo los suyos
- [ ] Documentar los resultados en una tabla: usuario × pregunta × docs retornados × esperado × PASS/FAIL
- [ ] Verificar con elevated-read header que el filtro sí se está aplicando (para debugging)
- [ ] **Criterio de éxito**: 0 leaks entre usuarios. Si un usuario ve algo que no debería, NO SE PUBLICA.

**Paso 6.4 — Iteración del prompt y el agente** (~1-2 horas, iterativo):

- [ ] Por cada caso que FALLE, diagnosticar:
  - ¿El índice tiene la data pero el agente no la encuentra? → ajustar el system prompt con ejemplos few-shot
  - ¿Falta un campo en el schema? → volver a Fase 4B, agregar campo, reindexar
  - ¿El retrieval trae chunks irrelevantes? → ajustar parámetros del AzureAISearchTool (`top_k`, `query_type`)
  - ¿Las respuestas traen tablas markdown a pesar del prompt? → reforzar instrucciones
- [ ] Re-correr los casos que fallaron después de cada ajuste
- [ ] Loop hasta tener **19/19 en verde**

**Paso 6.5 — Review con stakeholders ROCA** (~1 hora):

- [ ] Sesión de demo con Moisés Rodriguez y Omar Villa **en el Foundry Playground** (pantalla compartida)
- [ ] Correr los 19 casos frente a ellos
- [ ] Capturar feedback / casos edge que ellos quieran probar
- [ ] Iterar si hay ajustes solicitados
- [ ] Obtener aprobación explícita por escrito para pasar al deploy

**Entregable**:

- Agente validado end-to-end en Foundry Playground
- Reporte PASS/FAIL de los 19 casos
- Aprobación de ROCA para proceder al deploy
- Snapshot del system prompt aprobado

**REGLA**: esta fase NO termina hasta que los 19 casos están en PASS y ROCA da el OK. **Fase 7 (publicación) NO arranca hasta entonces.**

---

### Fase 7 — Publicación a Teams ✅ COMPLETA 2026-04-16

#### Arquitectura final implementada

**Flujo confirmado en producción** (logs de App Insights 2026-04-16):

```
Teams → Azure Bot Service (roca-copilot-bot) → POST /api/messages
     → CloudAdapter valida JWT inbound (SingleTenant)
     → http_bot_messages() extrae Activity
     → _bot_turn() extrae user_text
     → ask_roca_copilot() → Foundry Responses API (MSI token)
     → _bot_send_reply() → requests.post token → requests.post serviceUrl
     → Teams muestra respuesta
```

Traza de logs confirmada:

```
[BOT-HTTP] POST /api/messages recibido
[BOT-HTTP] activity type=message
[BOT] type=message channelId=msteams
[BOT] user_text='<pregunta del usuario>'
[BOT] llamando a ask_roca_copilot
[BOT] respuesta len=160
[BOT-REPLY] HTTP 200 → https://smba.trafficmanager.net/.../v3/conversations/...
[BOT] respuesta enviada OK
```

#### Configuración del Bot Service

- **Nombre**: `roca-copilot-bot`
- **Tipo**: Azure Bot Service F0 Free (global, costo $0)
- **msaAppType**: `SingleTenant`
- **msaAppId**: `0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44` (App Registration `roca-teams-bot-auth`)
- **msaTenantId**: `9015a126-356b-4c63-9d1f-d2138ca83176`
- **Messaging Endpoint**: `https://func-roca-copilot-sync.azurewebsites.net/api/messages`
- **Canal Teams**: habilitado en Bot Service → Channels → Microsoft Teams

#### App Registration para el Bot

| Campo             | Valor                                                       |
| ----------------- | ----------------------------------------------------------- |
| Nombre            | `roca-teams-bot-auth`                                       |
| appId (client_id) | `0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44`                      |
| Tenant            | `9015a126-356b-4c63-9d1f-d2138ca83176` (ROCA TEAM SA DE CV) |
| Secret name       | `roca-teams-bot-secret`                                     |
| Secret value      | `<SECRET-EN-KEYVAULT-kv-roca-copilot-prod>` (40 chars)       |
| Permisos Graph    | **Ninguno** — solo autenticación Bot Framework              |
| Scope usado       | `https://api.botframework.com/.default`                     |

#### App Settings de la Function App (Fase 7)

Agregados a `func-roca-copilot-sync` → Configuration → Application settings:

| Setting            | Valor                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------- |
| `BOT_APP_ID`       | `0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44`                                                 |
| `BOT_APP_PASSWORD` | `<SECRET-EN-KEYVAULT-kv-roca-copilot-prod>` (**40 chars exactos — verificar longitud**) |

```bash
# Cómo setear correctamente (SIEMPRE verificar longitud después):
az functionapp config appsettings set \
  --name func-roca-copilot-sync \
  --resource-group rg-roca-copilot-prod \
  --settings "BOT_APP_ID=0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44" \
             "BOT_APP_PASSWORD=<SECRET-EN-KEYVAULT-kv-roca-copilot-prod>"

# Verificar que BOT_APP_PASSWORD no tenga prefijos (debe ser 40-41 chars):
az functionapp config appsettings list \
  --name func-roca-copilot-sync \
  --resource-group rg-roca-copilot-prod \
  --query "[?name=='BOT_APP_PASSWORD'].value" -o tsv | wc -c
```

#### Código del middleware — dónde está

- **`function_app/function_app.py`**: trigger `http_bot_messages` (route=`messages`), funciones `_bot_turn`, `_bot_send_reply`, instancia `_BOT_ADAPTER` y warmup timer `timer_bot_warmup`.
- **`function_app/shared/bot.py`**: función `ask_roca_copilot()` — pre-search server-side por código de inmueble + llamada a Foundry Agent Service con MSI (`DefaultAzureCredential`, scope `https://ai.azure.com/.default`).

**Endpoint Foundry Agent Service** (actualizado 2026-04-22 — endpoint moderno con `agent_reference`):

```
POST https://rocadesarrollo-resource.services.ai.azure.com
     /api/projects/rocadesarrollo/openai/v1/responses

Body:
{
  "agent_reference": {"type": "agent_reference", "name": "roca-copilot"},
  "input": "<user_text + pre-search context>"
}
```

**Por qué este endpoint y no el legacy `/applications/.../protocols/openai/responses`**: el legacy NO respeta `agent_endpoint.version_selector` (siempre resuelve a una version pinned histórica). El moderno SÍ lo respeta, así que publicar nueva versión del agente con `PATCH agent_endpoint` redirige el tráfico sin redeploy del bot. Ver sección 10.6 para procedimiento.

#### Teams App Manifest

- **Archivo**: `ROCA-Copilot-v2.zip` (en `/Users/datageni/Downloads/`)
- **manifestVersion**: `1.22`, **version**: `2.0.0`
- **botId**: `0bfce6c7-7d2f-4d95-8d9d-bb5b8f03af44`
- **NO tiene** sección `copilotAgents` — se eliminó para evitar el popup de M365 Copilot (requiere licencia M365 Copilot)
- **validDomains**: `func-roca-copilot-sync.azurewebsites.net`
- **Instalación**: Teams → Apps → Manage your apps → Upload an app → Upload a custom app → seleccionar el zip

#### Cómo deployar la Function App

```bash
cd /Users/datageni/Documents/ai_azure/azure-ai-contract-analysis/function_app

# Deploy sin reinstalar deps (lo más común):
bash deploy.sh

# Deploy reinstalando todas las dependencias Linux x86_64 (si se agregan packages nuevos a requirements.txt):
bash deploy.sh --refresh-deps
```

El script:

1. Instala deps con `pip install --platform=manylinux2014_x86_64 --python-version=3.11 --only-binary=:all:` (binarios Linux para Azure, no los del Mac local)
2. Crea un ZIP del directorio `function_app/`
3. Sube via `az functionapp deployment source config-zip` (Run From Package)
4. La Function App reinicia automáticamente

**Nota**: después de cada deploy, esperar ~60 seg antes de mandar un mensaje a Teams (cold start). El warmup timer (`timer_bot_warmup`) se ejecuta cada 4 minutos para mantener la instancia caliente.

#### Errores encontrados y sus causas raíz

| Error                                                 | Causa raíz                                                                                | Solución                                                                                           |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Teams no recibe respuesta (Activity Protocol)         | Bug de plataforma MS: agente con AI Search tool no procesa mensajes vía Activity Protocol | Reemplazar con Python middleware + Foundry Responses API                                           |
| `PermissionError: Unauthorized Access` en JWT         | `BotFrameworkAdapter` (legacy) no maneja SingleTenant correctamente                       | Cambiar a `CloudAdapter` + `ConfigurationBotFrameworkAuthentication` con `APP_TYPE="SingleTenant"` |
| `KeyError: 'access_token'` en MSAL outbound           | MSAL falla silenciosamente en el contexto de asyncio + Azure Functions                    | Bypass completo: `requests.post` directo al endpoint de token                                      |
| `BOT_APP_PASSWORD` de 271 chars → token rechazado     | Azure CLI warning text se concatenó al secret en el App Setting                           | Re-setear `BOT_APP_PASSWORD` con el secret exacto (40 chars) vía Portal o CLI con comillas         |
| URL `/api/api/messages` → 404                         | `route="api/messages"` en Azure Functions duplica el prefijo `/api/`                      | Usar `route="messages"`                                                                            |
| `CloudAdapter.process()` espera `aiohttp.web.Request` | API incorrecta para Azure Functions                                                       | Usar `process_activity(auth_header, activity, callback)`                                           |

#### Monitoreo del bot en producción

```bash
# Ver logs del bot en tiempo real (App Insights):
az monitor app-insights query \
  --app appi-roca-copilot-prod \
  --resource-group rg-roca-copilot-prod \
  --analytics-query "traces | where message startswith '[BOT' | order by timestamp desc | take 50"
```

**Importante**: el pipeline de ingesta y el agente comparten el deployment `gpt-4.1-mini` (50K TPM). Si el pipeline genera 429 mientras el equipo usa el agente:

```bash
# Parar pipeline temporalmente:
az functionapp stop --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
# Volver a encender:
az functionapp start --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
```

#### Edge cases del bot

| Caso                                          | Comportamiento actual                                                                                                                                                                |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cold start (primera request tras inactividad) | Function App tarda 3-8 seg en arrancar. Bot devuelve respuesta tarde pero correctamente. Timer warmup cada 4 min mitiga esto.                                                        |
| Timeout de Foundry > 55 seg                   | `ask_roca_copilot()` tiene `timeout=55`. Si Foundry no responde, el bot devuelve "Error al consultar el agente. Intenta de nuevo en un momento."                                     |
| `conversationUpdate` activity                 | Teams envía este evento al añadir el bot a una conversación. `_bot_turn()` lo ignora (`if act.type != ActivityTypes.message: return`).                                               |
| Mensaje vacío o solo espacios                 | `_bot_turn()` retorna silenciosamente (`if not user_text: return`). Teams no muestra nada al usuario.                                                                                |
| Bot Service JWT expirado                      | `CloudAdapter` valida JWTs por expiración. Si el clock de la Function App tiene drift, puede rechazar JWTs válidos. En Azure Functions serverless esto no ocurre (NTP sincronizado). |
| `BOT_APP_PASSWORD` rotado                     | Re-setear App Setting + confirmar longitud 40 chars. No requiere redesploy del código.                                                                                               |

---

## 6.8 — Impacto del security trimming en tiempos totales

Agregar security trimming production-grade añade ~8-10 horas de trabajo total al proyecto:

- **Fase 2**: +30 min (permisos Graph adicionales + Project MI setup)
- **Fase 3**: +15 min (configurar MI del Foundry agent)
- **Fase 5**: +4-6 horas (Logic App captura ACLs + resuelve grupos + indexa campos)
- **Fase 6**: +5 horas (custom function tool + tests con múltiples usuarios)

Total original: ~1.5 días de trabajo efectivo
Total con security trimming: ~2.5 días de trabajo efectivo
**Justificación**: es obligatorio para production con docs de inmuebles sensibles y SharePoint con ACLs diferenciadas.

---

## 7. Costos estimados (producción) — actualizado 2026-04-29

### 💰 Resumen ejecutivo para el cliente

**Costo mensual total estimado: ~$90–130 USD/mes** para mantener el agente ROCA Copilot operando 24/7 con pipeline queue-based, sincronización automática de SharePoint y Agentic Retrieval para queries de detalle.

### Desglose por servicio

| Servicio                         | Recurso Azure                                        | Tier / SKU             | Qué hace                                                                                      | Costo mensual USD                                                                              |
| -------------------------------- | ---------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Azure AI Search**              | `srch-roca-copilot-prod`                             | Basic                  | Almacena y busca los documentos indexados. Semantic ranking + vector search.                  | **~$75** (fijo)                                                                                |
| **Azure OpenAI — gpt-4.1-mini**  | `rocadesarrollo-resource` / `gpt-4.1-mini`           | GlobalStandard 50K TPM | Modelo que responde las preguntas del agente + extrae metadata de docs nuevos en el pipeline. | **~$5–15** (pay-per-token, depende del volumen de queries del equipo + docs nuevos procesados) |
| **Azure OpenAI — embeddings**    | `rocadesarrollo-resource` / `text-embedding-3-small` | Standard 100K TPM      | Genera vectores de búsqueda para cada chunk de documento.                                     | **~$0.50–1** (pay-per-token, solo cuando se procesan docs nuevos)                              |
| **Azure Document Intelligence**  | `rocadesarrollo-resource`                            | Incluido en AIServices | OCR inteligente: extrae texto de PDFs escaneados (tablas, layouts).                           | **~$1–3** (solo docs nuevos: $1.50/1000 páginas)                                               |
| **Azure Blob Storage** (×2)      | `strocacopilotprod` (bot+ocr) + `stroingest` (queues+tables) | Hot LRS         | Cache de OCR + queues + tables + Durable task hub.                                            | **~$2–3**                                                                                      |
| **Function App bot (legacy)**    | `func-roca-copilot-sync`                             | Y1 Consumption Linux   | Bot Teams (`http_bot_messages`). Timers Durable disabled post-F9.                            | **$0** (free tier)                                                                             |
| **Function App ingest (F9)**     | `func-roca-ingest-prod`                              | Flex Consumption Linux | Pipeline queue-based: 10 handlers (3 queue workers, 3 timers, webhook, status, read_document, full-resync). | **$0** (free tier 1M ejec + 400K GB-s/mes — ROCA usa ~10% del grant) |
| **Log Analytics + App Insights** | `log-roca-copilot-prod` + `appi-roca-copilot-prod` + `func-roca-ingest-prod` | Pay-as-you-go | Monitoreo, logs, diagnósticos.                                                                | **~$2–8**                                                                                      |
| **Key Vault**                    | `kv-roca-copilot-prod`                               | Standard               | Almacena los secretos: sync robot + bot Framework auth.                                      | **~$0.03**                                                                                     |
| **Azure Bot Service**            | `roca-copilot-bot`                                   | F0 Free                | Puente entre el agente y Microsoft Teams.                                                     | **$0**                                                                                         |
| **Action Group**                 | `ag-roca-copilot-prod`                               | —                      | Envía emails de alerta cuando algo falla.                                                     | **$0**                                                                                         |
| **Agentic Retrieval (Knowledge Base)** | `roca-knowledge-base` en `srch-roca-copilot-prod` | preview, free tier 50M tokens/mes | Pipeline multi-query del agente: descompone query en subqueries paralelas, semantic reranking, answer synthesis. Cubre el caso "detalles del contenido del documento". | **~$0–5** (free tier 50M agentic reasoning tokens cubre ~250 queries de detalle/mes; pay-as-you-go después) |
| **Tokens de query planning + answer synthesis (gpt-4.1-mini)** | mismo deployment AOAI | — | Costos de LLM para planeación de subqueries y síntesis de respuesta en Agentic Retrieval. Se cobran como tokens normales del deployment `gpt-4.1-mini`. | **~$0.50–3** (incluido en línea de gpt-4.1-mini arriba — ~$0.005/query con detalle) |

### Costos que NO son recurrentes (ya pagados)

| Concepto                                                    | Costo único       | Nota                                                                          |
| ----------------------------------------------------------- | ----------------- | ----------------------------------------------------------------------------- |
| Ingesta inicial de ~76 PDFs (OCR + extraction + embeddings) | ~$2-3 USD         | Ya pagado 2026-04-15. Re-procesamiento de docs existentes $0 (cache en blob). |
| Desarrollo + debugging del pipeline                         | ~$5 USD en tokens | Sesión de implementación 2026-04-15.                                          |

### Escenarios de costo según uso (post Fase 8 — Agentic Retrieval)

| Escenario                                      | Queries/día del equipo | Queries de detalle/mes | Docs nuevos/mes | Costo mensual estimado |
| ---------------------------------------------- | ---------------------- | ---------------------- | --------------- | ---------------------- |
| **Bajo** (equipo de 3-5 personas, uso casual)  | 20-50                  | 50-150                 | 10-20           | **~$90/mes** (free tier agentic cubre)  |
| **Medio** (equipo de 10+ personas, uso diario) | 100-300                | 300-800                | 50-100          | **~$100/mes** (free tier agentic cubre) |
| **Alto** (toda la empresa, uso intensivo)      | 500+                   | 1000+                  | 200+            | **~$115-135/mes** (puede rebasar 50M tokens free → ~$3-10 extra) |

> **Nota**: el costo está dominado por Azure AI Search Basic ($75 fijo). Si el volumen de queries es muy bajo, se puede considerar bajar a AI Search Free tier ($0) pero pierde semantic ranking y se limita a 50MB de almacenamiento. No recomendado para producción.

### Comparación con el plan original

| Concepto               | Plan original                     | Implementación real                 | Ahorro                |
| ---------------------- | --------------------------------- | ----------------------------------- | --------------------- |
| Orquestador de ingesta | Logic App Standard WS1 ($176/mes) | Azure Durable Functions Y1 ($0/mes) | **$176/mes**          |
| Modelo chat            | gpt-4o ($$$) → gpt-5-mini ($$)    | gpt-4.1-mini ($)                    | **~50-70%** en tokens |
| **Total mensual**      | **~$120–220/mes**                 | **~$85–110/mes**                    | **~$35-110/mes**      |

---

## 8. Blockers y dependencias

### Bloqueantes críticos (sin esto no arranca)

1. **Permisos Entra ID**: necesitamos Global Admin para hacer admin consent del App Registration. Si el usuario no lo es, esperar a IT. _(Bloquea Fase 2)_
2. **Acceso del usuario a los 2 SharePoint sites**: confirmar que puede bajar archivos manualmente. _(Bloquea Fase 4A)_
3. **Confirmación de borrado de cuenta personal**: necesita OK explícito del usuario. _(Bloquea Fase 1)_

### Bloqueantes tardíos (necesitarán resolverse antes de fases correspondientes)

4. **Definición de "vigente"** (antes de Fase 5): ¿es estrictamente `fecha_vencimiento > today`? ¿hay período de gracia? ¿hay docs vigentes indefinidos? Ver Recomendación 3 para ROCA.
5. **Usuarios de prueba para tests de seguridad** (antes de Fase 6.3b): mínimo 3 usuarios con distintos perfiles de permisos. Ver Recomendación 4 para ROCA.
6. **Lista maestra de permisos obligatorios R-11** (antes de Fase 6.2): regla de negocio que debe definir Legal/Operaciones. Ver Recomendación 2 para ROCA.
7. **Contacto decisor para iteración de matriz** (antes de Fase 6.5): quién aprueba fix vs accept cuando un caso no da 100%. Ver Recomendación 5 para ROCA.
8. **Aprobación escrita de ROCA tras Fase 6** (antes de Fase 7): sin OK de Moisés/Omar, no se publica a Teams ni M365 Copilot.

### No-bloqueantes pero altamente recomendados

9. **ROCA reestructura permisos SharePoint a grupos Entra** (Recomendación 1): el sistema funciona sin esto, pero queda sub-óptimo. Idealmente se hace durante Fase 2 para que la Fase 5 ya vea grupos Entra limpios.

### Riesgos conocidos

- Foundry agent + Teams tiene issues documentados de rendering. Mitigación: respuestas en texto plano (ya incorporado en el plan).
- Publicación Organization scope falla reportadamente. Mitigación: usar Shared scope (ya incorporado).
- Logic Apps Standard wizard de AI Search puede no soportar versionado SharePoint custom. Mitigación: workflow custom si el wizard falla.

---

## 8.4 — Procedimiento: cambiar los sites de SharePoint que el pipeline sincroniza

Si los sites actuales (`ROCA-IAInmuebles` y `ROCAIA-INMUEBLESV2`) son entornos de prueba y se necesita apuntar a los sites de producción real, seguir estos 4 pasos:

### Paso 1 — Otorgar `Sites.Selected` al sync robot sobre los sites nuevos (~5 min)

El App Registration `roca-copilot-sync-agent` (`appId: 18884cef-ace3-4899-9a54-be7eb66587b7`) tiene `Sites.Selected` — solo puede acceder a sites explícitamente autorizados. Para cada site nuevo:

```bash
# 1. Obtener el site_id del nuevo site
SITE_ID=$(az rest --method get \
  --url "https://graph.microsoft.com/v1.0/sites/rocadesarrollos1.sharepoint.com:/sites/NOMBRE_DEL_SITE_NUEVO" \
  --query id -o tsv)

# 2. Otorgar permiso write al sync robot sobre ese site
az rest --method post \
  --url "https://graph.microsoft.com/v1.0/sites/$SITE_ID/permissions" \
  --body '{
    "roles": ["write"],
    "grantedToIdentities": [{
      "application": {
        "id": "18884cef-ace3-4899-9a54-be7eb66587b7",
        "displayName": "roca-copilot-sync-agent"
      }
    }]
  }'
```

Repetir para cada site nuevo. Requiere permisos de **SharePoint Admin** o **Sites.FullControl.All** temporal del usuario que ejecuta el comando (el mismo bootstrap de Fase 2).

### Paso 2 — Actualizar la lista de sites en el código (~2 min)

Editar `function_app/shared/config.py`:

```python
# ANTES:
SP_SITES = [
    "ROCA-IAInmuebles",
    "ROCAIA-INMUEBLESV2",
]

# DESPUÉS (ejemplo):
SP_SITES = [
    "ROCA-Produccion-Site1",
    "ROCA-Produccion-Site2",
]
```

Luego desplegar:

```bash
cd function_app/
./deploy.sh
```

### Paso 3 — Limpiar el índice y re-ingestar (~1-2h automático)

Si quieres que el índice SOLO tenga docs de los sites nuevos (sin datos de los sites viejos):

```bash
# Opción A: borrar y recrear el índice (pierde TODO, re-ingesta desde cero)
cd /Users/datageni/Documents/ai_azure/azure-ai-contract-analysis
source venv/bin/activate
python -c "
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
import subprocess
key = subprocess.check_output(['az','search','admin-key','show','--service-name','srch-roca-copilot-prod','--resource-group','rg-roca-copilot-prod','--query','primaryKey','-o','tsv'], text=True).strip()
c = SearchIndexClient(endpoint='https://srch-roca-copilot-prod.search.windows.net', credential=AzureKeyCredential(key))
c.delete_index('roca-contracts-v1')
print('Borrado')
"
python scripts/ingestion/create_prod_index.py  # Recrea con schema de 35 campos

# Borrar delta tokens para forzar re-ingesta completa
az storage blob delete-batch --account-name strocacopilotprod --source ocr-raw --pattern "delta-tokens/*" --auth-mode login

# Restart del Function App → el timer de 5 min dispara automáticamente
az functionapp restart --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
```

El pipeline re-ingesta todos los PDFs de los sites nuevos en ~1-2 horas automáticamente.

```bash
# Opción B: mantener datos viejos + agregar los nuevos (si ambos son relevantes)
# Solo borrar delta tokens para que el pipeline explore los drives nuevos:
az storage blob delete-batch --account-name strocacopilotprod --source ocr-raw --pattern "delta-tokens/*" --auth-mode login
az functionapp restart --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod
```

### Paso 4 — Verificar (~5 min)

```bash
# Verificar que el índice crece
az rest --method get \
  --uri "https://srch-roca-copilot-prod.search.windows.net/indexes/roca-contracts-v1/stats?api-version=2024-07-01" \
  --resource "https://search.azure.com/" \
  --query documentCount -o tsv

# Verificar que el agente responde con datos de los sites nuevos
# (abrir Foundry Playground y hacer una query)
```

### Notas importantes

- **El agente `roca-copilot` NO necesita cambios** — sigue apuntando a `roca-contracts-v1` via la connection `roca-search-prod`. Solo cambia el contenido del índice.
- **Si cambias el hostname de SharePoint** (no solo el site name), actualizar también `SP_HOSTNAME` en los app settings del Function App: `az functionapp config appsettings set --name func-roca-copilot-sync --resource-group rg-roca-copilot-prod --settings "SP_HOSTNAME=nuevo-hostname.sharepoint.com"`
- **Si los sites nuevos están en otro tenant**, cambiar `SP_TENANT_ID` en app settings y re-crear el App Registration en el nuevo tenant.
- **Tiempo total del cambio**: ~10 min de setup + ~1-2h de re-ingesta automática.

---

## 8.5 — Recomendaciones formales para ROCA (best practices)

Estas son recomendaciones que el equipo técnico (Abraham) debe comunicar formalmente a ROCA (Moisés Rodriguez, Omar Villa) en paralelo al proyecto. No bloquean el avance técnico, pero son necesarias para que el sistema funcione al 100% en producción y sea mantenible a largo plazo.

### Recomendación 1 — Usar grupos Entra ID (M365 Groups) para permisos de SharePoint

**Qué**: Reestructurar los permisos de los 2 sites de SharePoint (`ROCA-IAInmuebles` y `ROCAIA-INMUEBLESV2`) para que todas las asignaciones de permiso sean a **grupos Entra ID** (creados en Azure AD), en lugar de a usuarios individuales o a grupos SharePoint nativos.

**Por qué**:

1. **Auditable**: cambiar membresía de un grupo Entra queda en Audit Log de Azure AD
2. **Escalable**: agregar/quitar personas de un rol es 1 click, no actualizar decenas de documentos
3. **Onboarding automático**: nuevo empleado → agregarlo a grupo → acceso inmediato a todos los docs relevantes
4. **Offboarding limpio**: remover de grupo → pierde acceso en todo el sistema al mismo tiempo
5. **Compatibilidad con el agente**: el security trimming es más rápido y confiable con grupos Entra que con asignaciones individuales
6. **Evita el límite de 1000**: con grupos, es imposible llegar al límite de permission entries por archivo
7. **Estándar Microsoft**: es literalmente lo que Microsoft recomienda como best practice desde hace años

**Cómo se vería la estructura recomendada**:

```
Grupo Entra "ROCA-Directivos"         → acceso a TODO
Grupo Entra "ROCA-Legal"              → acceso a contratos, CSF, estudios ambientales
Grupo Entra "ROCA-Operaciones"        → acceso a planos, permisos, licencias
Grupo Entra "ROCA-GerenteZona-Norte"  → acceso solo a inmuebles RA01-RA10
Grupo Entra "ROCA-GerenteZona-Sur"    → acceso solo a inmuebles RA20-RA30
Grupo Entra "ROCA-Empleados-General"  → acceso solo a docs marcados públicos
```

**Quién lo hace**: el admin de SharePoint/M365 de ROCA (puede ser IT). Es una refactorización one-time de permisos.

**Timing**: debería hacerse **antes** o **durante** la Fase 2. Si no está listo, el sistema técnicamente funciona igual (el Logic App resuelve grupos SharePoint nativos a miembros individuales), pero queda sub-óptimo.

**Qué pasa si no se hace**: el sistema SIGUE FUNCIONANDO, pero:

- Permisos individuales masivos (anti-pattern) podrían llegar al límite de 1000 entries en algún doc raro
- La auditabilidad es más complicada
- Reindex on permission change es más frecuente (cada vez que alguien cambia a un grupo SP)

### Recomendación 2 — Definir la lista maestra de permisos obligatorios (para R-11)

**Qué**: Legal u Operaciones de ROCA debe entregar una lista formal y versionada de **qué permisos DEBE tener todo inmueble del portafolio** (ej: licencia de uso de suelo, permiso ambiental, permiso de construcción, etc.).

**Por qué**: R-11 de la matriz de pruebas pide que el agente genere un "checklist de permisos requeridos para RA03". Eso no sale de los documentos — es una regla de negocio que alguien debe declarar.

**Cómo**: formato JSON versionado en un path conocido (ver sección 5, R-11).

**Quién lo hace**: Legal/Operaciones de ROCA.

**Timing**: necesario **antes** de Fase 6 (validation de la matriz). No bloquea fases tempranas.

### Recomendación 3 — Definir la regla exacta de "vigente"

**Qué**: ROCA debe confirmar por escrito la definición de "documento vigente":

- ¿Es estrictamente `fecha_vencimiento > today`?
- ¿Hay un período de gracia (ej: un permiso vence hoy pero sigue siendo "vigente" por 30 días)?
- ¿Hay documentos que son "vigentes indefinidos" sin fecha de vencimiento?
- ¿Pólizas de seguro se consideran vigentes por hasta X días después de expiración?

**Por qué**: R-05, R-12, R-19 dependen de este cálculo. Una definición ambigua → resultados inconsistentes.

**Quién lo hace**: Legal/Operaciones de ROCA.

**Timing**: necesario **antes** de Fase 5 (Logic App calcula `es_vigente` durante ingest).

### Recomendación 4 — Definir los usuarios de prueba para tests de seguridad

**Qué**: ROCA debe identificar o crear al menos 3 usuarios representativos en el tenant para los tests de Fase 6.3b (tests de security trimming):

- Usuario "Directivo": acceso a todo (test baseline)
- Usuario "Gerente de zona": acceso solo a ciertos inmuebles
- Usuario "Empleado general" o "becario": acceso limitado

**Por qué**: sin múltiples usuarios con distintos perfiles de permisos, no podemos validar que el security trimming funciona correctamente.

**Quién lo hace**: IT + Operaciones de ROCA.

**Timing**: necesario **antes** de Fase 6.3b (~2 días antes de la validación).

### Recomendación 5 — Proceso para cuando la matriz de pruebas falle

**Qué**: ROCA debe definir QUIÉN decide el "fix vs accept" cuando un caso de R-01 a R-19 no pase con calidad 100%.

**Por qué**: es posible que algún caso de uso (ej: R-08 comparación de versiones) no dé el 100% de precisión desde el inicio y requiera iteración. Necesitamos un contacto que apruebe iteraciones o decida "esto es suficiente para v1".

**Quién**: probablemente Moisés Rodriguez como stakeholder técnico.

**Timing**: antes de Fase 6.5 (demo con stakeholders).

---

## 9. Constraints importantes grabadas en el diseño

Para que el usuario (y cualquier futuro colaborador) las vea de un vistazo:

1. **🚨 Publicación a Teams/M365 = ÚLTIMO PASO, siempre.** Validación completa de la matriz R-01 a R-19 en Foundry Playground primero. Ver "Regla de Oro del Deployment" al inicio.
2. **🔐 Security trimming production-grade desde el día 1.** Paridad con permisos SharePoint usando Security Filter Pattern (GA). Ver sección "Security Trimming" en decisiones arquitectónicas.
3. **Respuestas del agente en Teams = texto plano**. No tablas markdown. No citations con formato complejo. Listas línea-por-línea con `Campo: valor`.
4. **Publicación a Teams = Shared scope**, nunca Organization scope (workaround oficial).
5. **Auth a SharePoint = App permissions (Sites.Selected + Group.Read.All)**. El Project MI del Foundry agent tiene `GroupMember.Read.All + User.Read.All` para resolver grupos de usuarios en query time.
6. **Fail closed**: si Graph API falla al resolver grupos del usuario, el filtro retorna 0 docs. JAMÁS retornar "todos los docs" como fallback.
7. **`group_ids` y `user_ids` son `retrievable=false`**: nunca salen en resultados, solo filtran internamente. Defense in depth.
8. **Cache de security filter por usuario = 5 min máximo**: balance entre performance y frescura de grupos dinámicos Entra.
9. **Versiones históricas se conservan** en el índice (no se sobrescriben) para soportar R-08.
10. **Schema en 3 capas**: núcleo inmutable + metadata común extensible + JSON flexible. Nunca campos obligatorios que bloqueen ingesta de docs nuevos.
11. **Raw text en Blob Storage**: para poder reindexar en el futuro sin re-OCR (el OCR es el paso más caro).
12. **Rollback disponible post-deploy**: si un smoke test falla después de publicar, despublicamos inmediatamente y volvemos a Fase 6. Nunca dejamos al cliente ver un agente roto.
13. **Reindex on permission change**: el Logic App escucha cambios de ACLs en SharePoint y reindexa los docs afectados. Mantiene paridad con SharePoint.

---

## 10. Fase 8 — Agentic Retrieval con MCP (✅ COMPLETA 2026-04-22)

**Estado**: en producción y validada en Teams. El agente ahora responde correctamente a queries de detalle (firmantes, notaría, fechas) sobre documentos ya identificados — caso del título de propiedad RA03 resuelto end-to-end.

### 10.1 Qué problema resolvió

El RAG single-shot del agente (tool `azure_ai_search` con `query_type=vector_semantic_hybrid`, top_k=6) encontraba el documento correcto en una primera query, pero al pedir detalles específicos (*"¿quién firmó? ¿qué notaría? ¿qué fechas?"*) BM25 reranqueaba globalmente sin "memoria" del documento original y traía chunks de OTROS docs con coincidencias léxicas (caso reproducido: confundía `258,154 PRIMER TESTIMONIO RA03` con `DISEÑO DE PAVIMENTOS RA-03`).

### 10.2 Por qué Agentic Retrieval (y no `read_document` custom)

Antes de implementar consideramos un OpenAPI tool custom `read_document(content_hash)` que leyera del cache de chunks. Lo descartamos porque:

1. **Anthropic explícitamente desaconseja** el patrón "search + read separados". Recomienda tools compuestos que retornen información completa en una sola llamada (`Writing tools for agents`).
2. **Microsoft sacó Agentic Retrieval** (Azure AI Search, public preview, marzo 2026) que resuelve el problema a nivel arquitectónico: un LLM descompone la pregunta en subqueries paralelas, cada una con semantic reranking, y sintetiza una respuesta unificada con citaciones.
3. La conexión Foundry agent ↔ Knowledge Base usa **MCP** (Model Context Protocol) nativo. No hay que mantener Function App custom, ni OpenAPI specs, ni bridges de auth.

Referencia oficial: [Connect Agents to Foundry IQ Knowledge Bases](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect).

### 10.3 Arquitectura resultante

```
Bot middleware (function_app/shared/bot.py)
  │ POST {endpoint}/openai/v1/responses
  │ body: {agent_reference: {name: "roca-copilot"}, input: ...}
  ▼
Foundry Agent Service
  agent.agent_endpoint.version_selector → 100% traffic a v11
  ▼
roca-copilot:11
  ├── tool 1: azure_ai_search   (descubrimiento — "¿qué docs hay sobre X?")
  └── tool 2: mcp                (detalles — firmantes/fechas/notaría/cláusulas)
                │
                ▼ MCP (allowed_tools: knowledge_base_retrieve)
        Project Connection: roca-knowledge-mcp
        target: srch-…/knowledgebases/roca-knowledge-base/mcp
                │
                ▼
        Azure AI Search Knowledge Base: roca-knowledge-base
          └── Knowledge Source: roca-knowledge-source
                └── Index: roca-contracts-v1 (9038 chunks, sin re-indexar)
```

### 10.4 Recursos Azure creados/modificados (2026-04-22)

| Recurso | Acción | Notas |
|---|---|---|
| `roca-knowledge-source` (AI Search) | Creado | Wrapper sobre `roca-contracts-v1`, expone 8 sourceDataFields incluyendo `nombre_archivo`, `sharepoint_url`, `inmueble_codigo_principal`, `content` |
| `roca-knowledge-base` (AI Search) | Creado | LLM gpt-4.1-mini para query planning, `outputMode=answerSynthesis`, `retrievalReasoningEffort=low` |
| `roca-knowledge-mcp` (Project Connection) | Creado | Tipo `RemoteTool`, auth `ProjectManagedIdentity`, audience `https://search.azure.com/`, target apunta al endpoint MCP del knowledge base |
| `roca-copilot:11` (Foundry agent version) | Creada | Mismo system prompt que v10 + sección 9 nueva ("HERRAMIENTA SECUNDARIA — agentic retrieval"). Tools: `[azure_ai_search, mcp]` |
| `roca-copilot.agent_endpoint` | Patched | `version_selector` → 100% traffic a v11 |
| Search Service `srch-roca-copilot-prod` | Patched | `index.semantic.defaultConfiguration = "default-semantic-config"` (requerido por Agentic Retrieval) |
| Search MI `c9181743…` | RBAC | `Cognitive Services OpenAI User` en `rocadesarrollo-resource` (para que el knowledge base llame al LLM) — ya existía |
| Project MI `8117b1a5…` | RBAC | `Search Index Data Reader` en search service (asignado hoy) |
| `text-embedding-3-small` deployment | Recreado | Bug recurrente `OperationNotSupported` (3ª vez: 2026-04-17, 2026-04-20, 2026-04-22). Fix conocido: delete + recreate |
| `function_app/shared/bot.py` | Editado + deploy | Endpoint `/applications/roca-copilot/protocols/openai/responses` → `/openai/v1/responses`, body `model` → `agent_reference`. lastModifiedTimeUtc del Function App: 2026-04-22T04:58:19 |

### 10.5 Cambios al bot (3 líneas)

`function_app/shared/bot.py`:
- `_RESPONSES_ENDPOINT` ahora apunta al endpoint moderno `/openai/v1/responses` (sin api-version pinned)
- `_MODEL = "gpt-4.1-mini"` → `_AGENT_NAME = "roca-copilot"`
- Body de `requests.post`: `{"model": ..., "input": ...}` → `{"agent_reference": {"type": "agent_reference", "name": _AGENT_NAME}, "input": ...}`

**Por qué este cambio fue necesario** (descubrimiento durante la migración): el endpoint legacy `/applications/{name}/protocols/openai/responses` NO respeta `agent_endpoint.version_selector` — siempre resuelve a una version pinned histórica. Solo el endpoint moderno `/openai/v1/responses` con `agent_reference` honra el version selector. A partir de ahora, futuras versiones del agente se publican con `PATCH agent_endpoint` y el bot las consume sin redeploy.

### 10.6 Cómo publicar una nueva versión del agente sin tocar el bot

```bash
TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)

# 1. Crear nueva version (ej. v12) via SDK o REST
curl -X POST "https://rocadesarrollo-resource.services.ai.azure.com/api/projects/rocadesarrollo/agents/roca-copilot/versions?api-version=v1" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"roca-copilot","definition":{ ... }}'

# 2. Probar v12 aislada SIN tocar producción
curl -X POST "https://rocadesarrollo-resource.services.ai.azure.com/api/projects/rocadesarrollo/openai/v1/responses" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"input":"...","agent_reference":{"type":"agent_reference","name":"roca-copilot","version":"12"}}'

# 3. Si OK → publish v12 (redirige 100% del tráfico, el bot lo usa al instante)
curl -X PATCH "https://rocadesarrollo-resource.services.ai.azure.com/api/projects/rocadesarrollo/agents/roca-copilot?api-version=v1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Foundry-Features: AgentEndpoints=V1Preview" \
  -H "Content-Type: application/json" \
  -d '{"agent_endpoint":{"version_selector":{"version_selection_rules":[{"type":"FixedRatio","agent_version":"12","traffic_percentage":100}]}}}'
```

Rollback: el mismo PATCH con `agent_version: "<version_anterior>"` (5 segundos).

### 10.7 Costos delta de Agentic Retrieval

| Concepto | Costo |
|---|---|
| AI Search agentic reasoning tokens (free tier) | 50M tokens/mes incluidos en cualquier tier — actualmente cubre el uso ROCA (~170k tokens/query × ~100 queries/mes ≈ 17M) |
| Query planning (gpt-4.1-mini) | ~$0.0009/query (1500 input + 170 output tokens) |
| Answer synthesis (gpt-4.1-mini) | ~$0.0040/query (~7500 input + 600 output tokens) |
| **Costo por query con detalle** | **~$0.005 USD** |
| **Latencia adicional** | **+15-20 seg vs single-shot RAG** (aceptable para queries jurídicas) |

Costo total ROCA post-Agentic Retrieval: **~$95-125/mes** (delta ~$0-5 sobre la base actual; no rebasa free tier en uso interno típico).

### 10.8 Pendientes de limpieza (no bloqueantes — se cierran en próxima sesión)

- 🧹 **Eliminar agente legacy `asst_kcEoctliYHmRCg235fRXdXYo`**. Quedó pospuesto hasta validar 24-48h que v11 funciona limpio en Teams. **Validar primero** con `GET /assistants/asst_…?api-version=2025-05-15-preview` que sigue existiendo y NO está vinculado a `roca-copilot:N` antes de borrar.
- 🧹 **Eliminar `function_app/ingest/`** (código de la Fase 8 vieja del plan, donde habíamos diseñado migración Durable→Queue + tool `read_document`). Agentic Retrieval reemplaza esa arquitectura. El Function App `func-roca-ingest-prod` y la infra del DIA2 (`stroingest`, `evgt-roca-graph`, queues, tablas) **se pueden eliminar** porque ya no se usan. Backup: `DIA2_RESULTADOS.md`, `DESIGN_ROCA_INGEST.md`, `PLAN_MIGRACION_DURABLE_TO_QUEUE.md` documentan ese diseño abandonado — mover a `docs/archive/` o eliminar.
- 🧹 **Eliminar tool custom `read_document`** y sus artefactos: `scripts/openapi_read_document.json`, `scripts/register_read_document_tool.py`. Documentación previa (Fase 8B en este plan) ya fue eliminada.

### 10.9 Pendientes que aún NO se resuelven con esta migración

El bug Durable de la ingesta (incidente 2026-04-19) **sigue abierto**. Los timers `timer_sync_delta`, `timer_acl_refresh`, `timer_full_resync` siguen `Disabled=true` para evitar costos en loop. Consecuencia operativa:
- Archivos NUEVOS subidos a SharePoint **NO se indexan automáticamente**.
- Edits / renames / moves / deletes en SharePoint **NO se reflejan en el índice**.
- Indexación manual vía `scripts/bypass_ingest_one.py` sigue siendo el workaround.

**Roadmap para resolver**: separar en sesión propia. Opciones (mismo análisis que el Plan de migración descartado, pero ahora SIN componente `read_document` porque ya no se necesita):
1. Investigar si existe un fix nuevo para el bug `Non-Deterministic` en versiones más recientes del SDK `azure-functions-durable` Python (último intento: 1.5.0).
2. Migrar SOLO la pipeline de ingesta a queue-triggered stateless (sin tocar el bot ni el agente — esos ya están en su forma final).
3. Evaluar Foundry IQ con knowledge source de tipo `Indexed SharePoint` o `Remote SharePoint` (preview), que automatiza la sincronización SharePoint↔índice y eliminaría el código de ingesta custom completamente.

### 10.10 Deuda histórica que sigue abierta

- **D-1 Budget MCA**: requiere asignar `Cost Management Contributor` al admin MCA de ROCA TEAM o que esa persona cree Budget `$150-300/mes` vinculado a `ag-roca-copilot-prod`
- **D-2 `build_security_filter`**: security trimming basado en permisos SharePoint del usuario, diferido desde Fase 6 — bloquea exposición a usuarios externos
- **D-3 Lista maestra de permisos por tipo de inmueble** (R-11): requiere input de Legal/Operaciones ROCA

---

## 11. Fase 9 — Pipeline queue-based + cutover + reconciliación (✅ COMPLETA 2026-04-29)

### 11.1 Motivación

El pipeline F5 (Durable Functions en `func-roca-copilot-sync`) había sufrido el incidente non-deterministic de 2026-04-19 (~26h de pipeline caído). Aunque se mitigó con orchestration versioning y predeploy gates, persistían 2 problemas estructurales:

1. **Indexación automática frágil**: nuevos PDFs en SharePoint requerían que el orchestrator estuviera 100% sano. Cualquier deploy mal coordinado → caída silente.
2. **Sin recovery granular**: si un PDF fallaba, había que re-correr todo el `full_resync_orchestrator` (cara, lenta, no idempotente).

Plan B-Final adoptado 2026-04-23: **migrar a patrón `gpt-rag-ingestion` adaptado a Function App existente** (reference flagship MS, 176 stars). 88% confianza.

### 11.2 Arquitectura final

Nueva Function App **`func-roca-ingest-prod`** (Flex Consumption Linux Python 3.11) separada del bot. 10 handlers:

| # | Handler | Trigger | Función |
|---|---|---|---|
| 1 | `timer_sync_sharepoint` | cron `0 */5 * * * *` | Polling Graph delta cada 5 min, encola a `delta-sync-queue` |
| 2 | `delta_worker` | queue `delta-sync-queue` | Clasifica evento (upsert/rename/move/delete/folder_rename) y encola al `file-process-queue` |
| 3 | `enumeration_worker` | queue `enumeration-queue` | Full enum de un drive vía Graph, encola UN upsert por archivo |
| 4 | `file_worker` | queue `file-process-queue` (batchSize=4) | Dispatcher por action (ver `shared/file_actions.py`) |
| 5 | `subscription_renewer` | cron `0 0 3 * * *` | Crea + renueva Graph subscriptions cada 3 días, expiration target = +60h |
| 6 | `timer_purger` | cron `0 0 * * * *` | Reconcilia índice vs SP, batch DELETE huérfanos. Guardrails: skip si itemsindex vacío o >50% sería huérfano |
| 7 | `webhook_handler` | HTTP `/api/webhook/graph` | Validación + ingesta de notifications de Graph |
| 8 | `http_status` | HTTP `/api/status` | Telemetría: `target_index`, queue depths, delta tokens |
| 9 | `http_read_document` | HTTP `/api/read_document/{hash}` | Reconstruye texto completo de un doc desde sus chunks (sin re-OCR) |
| 10 | `http_full_resync` | HTTP `/api/admin/full-resync` | ⚠ Bug abierto D-23 (404). Workaround documentado en runbook |

Storage account separado **`stroingest`** con 6 queues + 3 tables (`deltatokens`, `folderpaths`, `itemsindex`).

### 11.3 Timeline de eventos

| Fecha UTC | Evento |
|---|---|
| 2026-04-21 | Diseño inicial (`DESIGN_ROCA_INGEST.md`, 62 KB) |
| 2026-04-23 | Decisión arquitectural Plan B-Final adoptado tras investigar 3 alternativas (webhooks+EventGrid descartado por `60min latency` Graph + `no captura deletes`) |
| 2026-04-24 (Day 3) | 6 handlers nuevos deployados, 10/10 funciones live. Backfill al `roca-contracts-v1-shadow` con 8,851 docs (`TARGET_INDEX_NAME` apuntaba a shadow como guardrail) |
| 2026-04-24 cierre | Sesión cerró con drenaje OK al shadow. Cutover a prod **NO** se ejecutó (descuido humano) |
| 2026-04-24 → 2026-04-28 | Cliente subió ~84 PDFs nuevos a SP. **Todos procesados al shadow** (correcto por la queue, pero al índice equivocado) |
| **2026-04-28 21:05 UTC** | **Cutover ejecutado**: `TARGET_INDEX_NAME` cambiado de `roca-contracts-v1-shadow` → `roca-contracts-v1`. Restart aplicado |
| 2026-04-28 21:15-21:21 | Backfill de `itemsindex` table: 1,588 entries actualizadas, 84 huérfanos identificados |
| 2026-04-28 22:43 | Encolados 2 enumeration messages para reconciliar 84 huérfanos |
| 2026-04-28 23:08 | Drenaje completo: 1,588 dedup hits + 83 huérfanos OK con vectores + 1 archivo defectuoso (0 bytes) en poison |
| 2026-04-29 | Limpieza poison queue + verificación funcional + actualización plan |

### 11.4 Bugs descubiertos durante el cutover

#### Bug A — Shadow index sin vectores (causa raíz del cutover bloqueado)

**Síntoma**: `roca-contracts-v1-shadow` tenía 8,851 docs pero `vectorIndexSize: 0`.

**Causa raíz**: el script `scripts/rehydrate_shadow_from_prod.py:195` hace `prod.search(search_text="*", top=None)` SIN parámetro `select=`. El SDK de `azure-search-documents` no retorna campos con `retrievable: false` en queries `search()` sin select explícito. El campo `content_vector` en prod tiene `retrievable: false` (best practice MS para ahorrar bandwidth, los vectores existen internamente con `vectorIndexSize: 58 MB`). Resultado: el upload al shadow incluyó `content_vector: None` para los 9,038 chunks.

**Decisión**: NO arreglar el shadow. Cutover directo al prod (que ya tenía vectores buenos). Shadow queda zombie (D-24).

#### Bug B — 84 archivos huérfanos en el índice equivocado

**Síntoma**: 84 PDFs subidos por el cliente entre 04-24 y 04-28 estaban en SP + shadow pero NO en prod.

**Causa raíz**: `TARGET_INDEX_NAME=roca-contracts-v1-shadow` durante 4 días post-Day 3. El delta sync detectó los uploads, los procesó correctamente, pero los escribió al shadow inservible.

**Resolución**: re-enumeración full de los 2 drives → `handle_upsert` con dedup por `content_hash`. Los 1,588 archivos ya en prod hicieron dedup_hit (~5s c/u), los 84 huérfanos pasaron por full path (download → OCR → embed → indexa). Total ~25 min, costo ~$3-4 USD.

**Patrón Microsoft canónico aplicado**: re-enumeración full con dedup idempotente. Documentado en [GPT-RAG SharePoint connector](https://azure.github.io/GPT-RAG/ingestion_sharepoint_source/) como el patrón oficial para reconciliación.

### 11.5 Estado final del índice prod

| Métrica | Pre-cutover (2026-04-28) | Post-reconciliación (2026-04-29) | Δ |
|---|---|---|---|
| Doc count | 9,038 | **11,232** | **+2,194 chunks** |
| Storage size | 290 MB | 323 MB | +33 MB |
| Vector index size | 58 MB | **87 MB** | **+29 MB** |
| Archivos únicos | ~1,030 | **1,114** | +84 archivos |

### 11.6 Confianza por escenario (verificado 2026-04-29)

| Escenario | Confianza | Validación |
|---|---|---|
| **Subir PDF nuevo** | **90-95%** | 83/84 huérfanos procesados OK con vectores end-to-end. Falta validación con un PDF nuevo subido por el cliente en tiempo real |
| **Renombrar PDF existente** | **75-85%** | Validado solo por código + backfill `itemsindex` con 1,588 entries. **NO probado en vivo** |
| **Mover PDF existente** | **75-85%** | Mismo caveat |
| **Borrar PDF existente** | **75-85%** | Mismo caveat. Hay fallback `timer_purger` cada hora pero **NO testeado en prod** |
| Vector search funcional | **100%** | Verificado vivo: query "vigencia RA03" devuelve `RA03_Contrato_v1.pdf` con score |

**Para llegar a 95%+ en los 4 escenarios destructivos**, falta una prueba real de los 4 casos (upload + rename + move + delete) con un PDF de test. Pendiente que el cliente ejecute en SP.

### 11.7 Archivos del repo nuevos (F9)

- `function_app/ingest/` — completo, nueva Function App ingest
- `function_app/ingest/function_app.py` — 10 handlers
- `function_app/ingest/shared/file_actions.py` — handlers `upsert/rename/move/delete/folder_rename`
- `function_app/ingest/shared/embeddings.py` — `embed_batch` (idéntico a legacy para parity)
- `function_app/ingest/shared/search_client.py` — `upsert_documents`, `delete_by_content_hash`, `patch_document_fields`, `find_by_content_hash`, `read_chunks_by_hash`
- `function_app/ingest/shared/queue_storage.py` — `enqueue_upsert`, `enqueue_enumeration`, etc.
- `function_app/ingest/shared/table_storage.py` — `upsert_item_index`, `get_item_index`, `delete_item_index`, `list_descendant_items`
- `function_app/ingest/shared/graph_client.py` — `iter_delta_changes`, `list_drive_items_recursive`, `stream_download_to_temp`
- `function_app/ingest/host.json` — `functionTimeout: 30 min`, `batchSize: 4`, `maxDequeueCount: 5`
- `scripts/backfill_itemsindex_from_prod.py` — script F9 para backfill `itemsindex` desde prod (no shadow). Idempotente
- `scripts/deploy_ingest.sh` — deploy con `func azure functionapp publish --python --build remote`

### 11.8 Pendientes post-F9 (no bloqueantes)

1. **D-23 — Bug `http_full_resync` 404**: investigar conflict con reserved path `/api/admin/*`. Workaround documentado: encolar manualmente a `enumeration-queue`.
2. **D-24 — Shadow index cleanup**: borrar `roca-contracts-v1-shadow` después de 1-2 semanas de validación. Cero costo extra, pero ocupa storage.
3. **D-26 — `acta-entrega-trabajo.pdf` 0 bytes**: cliente debe re-subir o borrar el archivo.
4. **Validación end-to-end con cliente**: que el cliente suba un PDF de prueba a SP, espere ≤5 min, y pregunte sobre él en Teams. Si lo encuentra → cierre 100%.

---

## 12. Referencias / sources de la investigación

### Microsoft docs oficial

- [Use SharePoint content with agent API — Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/sharepoint)
- [Connect to Azure Logic Apps — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-how-to-index-logic-apps)
- [SharePoint in Microsoft 365 Indexer (preview) — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-how-to-index-sharepoint-online)
- [Data Sources Gallery — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-data-sources-gallery)
- [Publish agents to Microsoft 365 Copilot and Teams — Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot)

### Evidencia de que el stack funciona (confirmaciones y casos reales)

- [Q&A #5816041: Published Foundry Agent + AI Search tool working in Teams (Microsoft Moderator response)](https://learn.microsoft.com/en-us/answers/questions/5816041/published-azure-ai-foundry-agent-not-working-in-te)
- [TechCommunity discussion: Foundry agents in Teams/M365 — known limitations and workarounds](https://techcommunity.microsoft.com/discussions/azure-ai-foundry-discussions/published-agent-from-foundry-doesnt-work-at-all-in-teams-and-m365/4485341)
- [Origin Digital: Microsoft Foundry SharePoint Knowledge Integration — Part 4: Azure AI Search Tool](https://www.origindigital.com/insights/microsoft-foundry-sharepoint-knowledge-integration-part-4-azure-ai-search-tool)
- [CloudFronts: Automating Document Vectorization from SharePoint Using Logic Apps + AI Search](https://www.cloudfronts.com/azure/azure-blob-storage/automating-document-vectorization-from-sharepoint-using-azure-logic-apps-and-azure-ai-search/)

### Implementaciones de referencia (repos)

- [liamca/sharepoint-indexing-azure-cognitive-search](https://github.com/liamca/sharepoint-indexing-azure-cognitive-search) — ex-Microsoft, SharePoint → AI Search en Python
- [digvijay-msft/SharePoint-OpenWebUI](https://github.com/digvijay-msft/SharePoint-OpenWebUI) — Microsoft employee, Foundry + SharePoint + Teams
- [DEV.to: Syncing SharePoint with Blob Storage using Logic Apps + Azure Functions](https://dev.to/imdj/syncing-sharepoint-with-azure-blob-storage-using-logic-apps-azure-functions-for-azure-ai-search-250j)

---

## 13. Matriz de pruebas — resumen ejecutivo

| Categoría            | Cuántos | Casos                                                                              |
| -------------------- | ------- | ---------------------------------------------------------------------------------- |
| ✅ Out-of-the-box    | 14      | R-01, R-02, R-03, R-04, R-05, R-06, R-09, R-10, R-14, R-15, R-16, R-17, R-18, R-19 |
| ⚠️ Diseño especial   | 4       | R-07, R-08, R-12, R-13                                                             |
| ❗ Input del negocio | 1       | R-11 (lista maestra de permisos requeridos)                                        |

**Cobertura técnica**: 19/19 (100%) — todos los casos son viables con la arquitectura propuesta.

---

## 14. Flujo end-to-end — cómo funciona el sistema en operación

Esta sección cuenta narrativamente cómo el sistema opera una vez desplegado, con ejemplos concretos. Es el documento de referencia conceptual para cualquiera que quiera entender el proyecto sin leer código.

### Los 5 actores del sistema

1. **Usuario ROCA** (ej: Moisés, Omar) — persona que consulta el agente desde Teams
2. **Microsoft Teams** — la "cara" del sistema, donde el usuario interactúa
3. **Azure AI Foundry Agent** (`roca-copilot-smoke` v1 en Fase 4A smoke, nombre final por definir en Fase 6) — el "cerebro" corriendo `gpt-4o-mini` con tool `Azure AI Search`
4. **Azure AI Search** (`roca-contracts-smoke` en smoke, `roca-contracts-v1` en producción tras Fase 4B) — la biblioteca indexada, búsqueda híbrida semántica
5. **Azure Logic App** (`logic-roca-copilot-sync`) — el "mayordomo" que vigila SharePoint 24/7

### Historia A — La vida de una pregunta

**Escenario**: Moisés quiere saber los permisos vigentes del inmueble RA03.

1. **Moisés escribe en Teams**: _"dame los permisos vigentes de RA03"_
2. **Teams envía el mensaje** al Foundry agent con metadata (usuario, conversación, fecha `today=2026-04-14`)
3. **gpt-4o procesa la pregunta** siguiendo las instrucciones del system prompt: "usa `AzureAISearchTool` para permisos". Invoca la tool con una query estructurada:
   ```
   filter: inmueble_codigo eq 'RA03' and es_vigente eq true
           and doc_type eq 'permiso_construccion'
   search: permisos vigentes
   top: 10
   ```
4. **Azure AI Search ejecuta hybrid search**: combina filtro + búsqueda semántica por vector + semantic ranking. Retorna los top 10 chunks más relevantes con todos sus campos (content, sharepoint_url, fechas, autoridad, etc.)
5. **gpt-4o lee los chunks** y redacta respuesta en formato texto plano (sin tablas markdown, línea-por-línea con `Campo: valor`):

   ```
   Permisos vigentes del inmueble RA03:

   1. Permiso de construcción
      Autoridad: Municipio de Querétaro
      Emisión: 2024-05-20
      Vencimiento: 2027-05-20
      Fuente: https://rocadesarrollos1.sharepoint.com/.../RA03/Permisos/permiso_construccion_2024.pdf

   2. Licencia de uso de suelo
      Autoridad: Municipio de Querétaro
      Emisión: 2023-11-15
      Vencimiento: 2028-11-15
      Fuente: https://rocadesarrollos1.sharepoint.com/.../RA03/Permisos/licencia_uso_suelo.pdf
   ```

6. **Teams renderiza el texto** en el chat. Moisés hace click en los URLs si quiere ver los PDFs originales en SharePoint.

**Tiempo total**: ~3–5 segundos end-to-end.

### Historia B — La vida de un documento nuevo

**Escenario**: Omar sube un nuevo permiso ambiental al inmueble RA04 en SharePoint.

1. **Omar arrastra el PDF** `permiso_ambiental_RA04_2026.pdf` a la carpeta `/sites/ROCA-IAInmuebles/Shared Documents/RA04/Permisos/`
2. **Logic App detecta el cambio** vía su trigger "When a file is created or modified in SharePoint" (dentro de 30s–2 min)
3. **Pipeline automático se ejecuta** sin intervención humana:
   - a. Descarga el PDF via Graph API con el App Registration `roca-copilot-sync-agent` (permisos Sites.Selected)
   - b. Copia a Azure Blob Storage (backup para reindex futuro sin re-OCR)
   - c. Llama a Document Intelligence (prebuilt-layout) → extrae texto + páginas + párrafos
   - d. Llama a gpt-4o con prompt discovery → extrae metadata Capa 2 (doc_type, inmueble, fechas, autoridad) + Capa 3 (cualquier campo extra que detecte):
     ```json
     {
       "doc_type": "permiso_ambiental",
       "inmueble_codigo": "RA04",
       "fecha_emision": "2026-04-10",
       "fecha_vencimiento": "2031-04-10",
       "autoridad_emisora": "SEMARNAT",
       "es_vigente": true,
       "extracted_metadata": {
         "numero_oficio": "SEMARNAT-2026-4821",
         "area_impactada_m2": 1200,
         "tipo_impacto": "bajo"
       }
     }
     ```
   - e. Chunking semántico (~1024 tokens, preserva estructura)
   - f. Embeddings con `text-embedding-3-small` (1536D por chunk)
   - g. Upsert al índice Azure AI Search con merge semantics
   - h. Log a Application Insights
4. **Listo**: si Moisés pregunta _"permisos vigentes de RA04"_ 3 minutos después, el agente YA encuentra el nuevo permiso.

**Tiempo total**: 1–3 minutos desde upload hasta query-able.

### Las dos historias corren en paralelo, todo el tiempo

```
 SharePoint ─────► Logic App ─────► Azure AI Search ◄───── Agente Foundry ◄───── Teams
     ▲                │                    ▲                      ▲                  ▲
     │                │                    │                      │                  │
  Omar sube        OCR+meta+            Se indexa              Responde            Moisés
  un PDF           embed+chunk         en segundos             preguntas           pregunta
```

- **Historia B (sync)** ocurre cada vez que SharePoint cambia → mantiene la biblioteca actualizada
- **Historia A (query)** ocurre cada vez que alguien pregunta en Teams → usa la biblioteca
- **Azure AI Search es el punto de encuentro** entre ambas

### Defensas y manejo de errores

| Escenario                        | Defensa automática                                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| SharePoint no responde           | Logic App reintenta con backoff exponencial (5 veces), alerta por email si falla                                           |
| Document Intelligence falla      | Retry automático, el PDF queda en Blob Storage para reprocesar manualmente                                                 |
| gpt-4o no puede extraer metadata | Schema de 3 capas permite indexar con solo Capa 1 — sigue siendo findable por semantic search                              |
| Query retorna 0 resultados       | System prompt instruye: _"responde explícitamente 'No encontré información sobre X en los documentos disponibles'"_ (R-04) |
| Smoke test falla post-deploy     | Rollback inmediato, despublicar de Teams, regresar a Fase 6                                                                |

### Cómo cambia el día a día con el sistema en producción

| Escenario                          | Antes (manual)                                     | Después (con el agente)                  |
| ---------------------------------- | -------------------------------------------------- | ---------------------------------------- |
| Consultar permisos vigentes        | Abrir SharePoint, navegar, abrir PDFs, leer fechas | Teams → 1 pregunta → respuesta en 3s     |
| Nuevo doc legal sube a SharePoint  | Avisar equipo, actualizar registro manual          | Automático, query-able en 1–3 min        |
| Comparar dos versiones de contrato | Abrir ambos PDFs, leer párrafo por párrafo         | Agente devuelve diferencias clave (R-08) |
| Saber qué permisos faltan          | Checklist Excel manual vs. realidad                | Agente cruza automáticamente (R-11)      |
| Onboarding de nuevo empleado       | Días explorando carpetas SharePoint                | Pregúntale al agente                     |

### Quién hace qué una vez en producción

- **Abraham (dueño técnico)**: casi nada en día a día. Revisa alertas de Application Insights cuando llegan. Cada trimestre revisa logs para detectar tipos de documentos nuevos que podrían beneficiarse de promoción Capa 3 → Capa 2.
- **Moisés, Omar, usuarios ROCA**: usan Teams para preguntar. Suben docs a SharePoint como siempre. **El agente es transparente** para ellos.
- **Sistema**: todo lo demás, automáticamente.

---

## 15. Fase 10 — Welcome UX con Adaptive Cards (✅ COMPLETA 2026-04-29)

### 15.1 Origen del requerimiento

Iván (cliente ROCA) compartió screenshots de **Microsoft 365 Copilot Studio** mostrando "indicaciones sugeridas" amarradas a "temas" (chips clickeables al abrir el chat). Pregunta literal: *"¿Esto es viable en Foundry?"*. Implícito: ¿se puede dar la misma UX guiada en Teams sin migrar el agente fuera de Foundry?

Mapeo de terminología Copilot Studio → Bot Framework Teams:

| Lo que Iván llamó | Nombre técnico real | Mecanismo en Teams |
|---|---|---|
| "Indicaciones sugeridas" (chips iniciales) | Suggested prompts / Conversation starters | Adaptive Card con `Action.Submit` |
| "Tema" | Topic con trigger phrases | System prompt branching del agente Foundry |
| "Instrucción" estructurada (`Si existe X / Si NO existe Y`) | Custom Instructions por topic | Instructions del agente Foundry |

### 15.2 Validación contra docs oficiales Microsoft

Tres patrones candidatos investigados antes de elegir:

| Patrón | Veredicto | Por qué |
|---|---|---|
| **Suggested Actions** del Bot Framework SDK | ❌ Descartado | Cita Microsoft Learn: *"Card actions are different than suggested actions in Bot Framework or Azure Bot Service. Teams does not support `potentialActions` property."* Render inconsistente, chips se borran tras click |
| **`commandLists` en manifest de Teams** | ⚠️ Implementado pero NO satisfactorio en Teams Web 2026 | Es el patrón documentado pero la new UI (`teams.cloud.microsoft`) no los renderiza donde la doc clásica decía. El menú `/` que el usuario ve son comandos GLOBALES de Teams, no del bot |
| **Adaptive Card con `Action.Submit` + `msteams.type=imBack`** | ✅ Elegido y deployado | Cita: *"Adaptive Cards are the recommended card type for new Teams development"* + *"Teams platform supports v1.5 or earlier of Adaptive Card features for bot sent cards"*. Va por API del bot, sin caché de Teams ni dependencia de propagación de catálogo |

Validación que ES requisito oficial Microsoft (no opcional): para validation de bots en Teams, [Microsoft Q&A 5742278](https://learn.microsoft.com/en-ca/answers/questions/5742278/teams-bot-app-validation-fails-bot-must-send-a-pro) exige *"Bot must send a proactive welcome message in personal scope"*.

### 15.3 Arquitectura de 3 capas (planeada)

| Capa | Mecanismo | Estado |
|---|---|---|
| **Capa 1** | `commandLists` en manifest Teams | ⚠️ Implementada, manifest 2.1.0 publicado, pero no se renderiza visualmente en Teams Web 2026. Queda versionada por si Microsoft arregla la UX |
| **Capa 2** | Adaptive Card de welcome al primer mensaje del usuario | ✅ Implementada + deployada |
| **Capa 3** | Adaptive Card con follow-ups al final de cada respuesta del agente | ⏳ Pendiente, opcional según feedback de Iván |

### 15.4 Capa 1 — manifest 2.1.0 con commandLists (intentada)

Generado en `teams_bot/manifest.json` (versionado en repo) y zip `teams_bot/ROCA-Copilot-v2.1.zip`. Subido a Teams Admin Center → Manage apps → ROCA Copilot → Update. **Published version: 2.1.0** confirmado. App siguiendo configuración pre-existente: Available to Everyone (org-wide default), Status Unblocked, scope Personal/Team/GroupChat.

Bloque agregado al manifest:

```json
"commandLists": [{
  "scopes": ["personal"],
  "commands": [
    { "title": "Ver contrato de inmueble", "description": "Muéstrame el contrato vigente del inmueble RA03" },
    { "title": "Estudio de impacto ambiental", "description": "¿Hay estudio de impacto ambiental para el inmueble SL02?" },
    { "title": "Próximos vencimientos", "description": "Lista los contratos que vencen en los próximos 90 días" },
    { "title": "Resumen ejecutivo", "description": "Genera un resumen ejecutivo del expediente del inmueble GU01A" },
    { "title": "Cláusula específica", "description": "¿Qué dice la cláusula de vigencia del contrato más reciente?" },
    { "title": "Documentos del inmueble", "description": "Lista todos los documentos disponibles del inmueble CJ03" },
    { "title": "Ayuda", "description": "¿Qué tipos de preguntas puedo hacerte?" }
  ]
}]
```

**Resultado en Teams Web new UI**: el menú `/` muestra comandos globales de Teams (ausente, configuración, silenciar) pero NO los del bot. Microsoft no documenta consistentemente dónde renderiza los `commandLists` del bot en la new UI 2026. Por eso pivoteamos a Capa 2.

### 15.5 Capa 2 — Adaptive Card welcome (deployada)

Adaptive Card v1.5 con título, descripción y 7 botones `Action.Submit`. Cada botón lleva `msteams.type=imBack`: al click, Teams pone el texto del prompt en el chat como si el usuario lo hubiera tipeado y reentra al pipeline normal `_bot_turn` → `ask_roca_copilot()`. **Cero modificaciones al bridge a Foundry, cero a la lógica del agente**.

### 15.6 Cambios al código

Solo `function_app/function_app.py`. Adiciones:

1. **`_WELCOME_TRIGGERS`** (set) — palabras que disparan la welcome card cuando llegan como mensaje normal: `hola`, `buenas`, `buenos días`, `ayuda`, `help`, `comandos`, `inicio`, `start`, `menú`, `qué puedes hacer`, `cómo te uso`. Normalización: lowercase, strip de `/`, `?`, `¿`.
2. **`_WELCOME_PROMPTS`** (list) — los 7 chips, mismos textos del manifest (consistencia).
3. **`_build_welcome_card()`** — genera JSON Adaptive Card v1.5.
4. **`_bot_send_welcome_card()`** — POST a `{service_url}/v3/conversations/{id}/activities` con el card como `attachment`. Mismo patrón HTTP-directo que `_bot_send_reply` (bypass de MSAL outbound).
5. **Branch nuevo en `_bot_turn`**:
   - Si `act.type == conversation_update` con `members_added`, filtra al bot mismo y manda welcome card.
   - Si `act.type == message` y `user_text` normalizado está en `_WELCOME_TRIGGERS`, manda welcome card en lugar de pegarle al agente.
   - Cualquier otro mensaje: pipeline existente sin cambios.

Tres rutas redundantes para garantizar que el usuario eventualmente vea los chips, mitigando el [timing issue documentado](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages) donde a veces el welcome proactivo no llega aunque el código corra sin error.

### 15.7 Deploy y validación post-deploy (2026-04-29)

```bash
cd function_app && ./deploy.sh
```

Predeploy gate pasó (0 orquestaciones vivas), zip 16 MB subido a `func-roca-copilot-sync`, health check OK:

```json
{
  "status": "ok",
  "target_index": "roca-contracts-v1",
  "is_staging": false,
  "discovery_model": "gpt-4.1-mini",
  "embed_model": "text-embedding-3-small"
}
```

Validación funcional pendiente de confirmar visualmente en Teams (escribir `hola` en el chat de ROCA Copilot debe devolver la card con los 7 botones).

### 15.8 Archivos modificados/creados en F10

- `function_app/function_app.py` — ~80 líneas agregadas (helpers + branches)
- `teams_bot/manifest.json` — bump 2.0.0 → 2.1.0 + bloque `commandLists`
- `teams_bot/ROCA-Copilot-v2.1.zip` — paquete listo para Teams Admin Center
- `teams_bot/default-color-icon.png` + `default-outline-icon.png` — copiados desde el zip original

### 15.9 Pendientes post-F10 (no bloqueantes)

- ⏳ Validar visualmente que la Adaptive Card aparece al escribir "hola" en Teams Web (Ruta 2) y al reinstalar fresco la app (Ruta 1).
- ⏳ Demo a Iván con el flujo completo: instala fresco → ve la card → click en chip → ve respuesta.
- ⏳ **Capa 3** (Adaptive Card con follow-ups al final de cada respuesta del agente). Solo si Iván lo pide. Implementación: modificar `_bot_send_reply` para devolver `attachments` con card en lugar de `text` plano. El agente puede devolver `{"answer": "...", "follow_ups": [...]}` para chips dinámicos.
- ⏳ Telemetría de qué chips se clickean más (App Insights custom event `welcome_chip_click` con `chip_title` como dimension). Permite priorizar prompts en la próxima iteración.
- ⏳ Si en 30 días Microsoft no fixea el rendering de `commandLists` en Teams new UI, considerar borrarlos del manifest para reducir confusión (queda solo Capa 2).

### 15.10 Sources de la investigación F10

- [Designing your bot - Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/design/bots) — UX Kit oficial Microsoft
- [Add card actions in a bot - Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-actions) — diferencia card actions vs suggested actions
- [Cards reference - Teams supports Adaptive Cards v1.5](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-reference)
- [Send proactive messages - Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages) — patrón conversationUpdate + welcome
- [bot-conversation Python sample (OfficeDev)](https://github.com/OfficeDev/Microsoft-Teams-Samples/blob/main/samples/bot-conversation/python/bots/teams_conversation_bot.py)
- [App Manifest Schema 1.22+](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)
- [Microsoft Q&A: validation requires welcome message](https://learn.microsoft.com/en-ca/answers/questions/5742278/teams-bot-app-validation-fails-bot-must-send-a-pro)
- [PnP Blog: Welcome new employee using Adaptive card](https://pnp.github.io/blog/post/welcome-new-employee-in-teams-using-adaptive-card/)

---

_Documento vivo. Se actualiza conforme avanzamos por las fases. Última revisión: 2026-04-29._
