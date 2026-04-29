#!/usr/bin/env bash
# deploy_ingest.sh — Configura App Settings y despliega func-roca-ingest-prod
#
# Uso:
#   ./scripts/deploy_ingest.sh [--settings-only] [--code-only]
#
# Requiere: az cli autenticado
# Ejecutar desde la raíz del repo: azure-ai-contract-analysis/

set -euo pipefail

FUNC_NAME="func-roca-ingest-prod"
RG="rg-roca-copilot-prod"
INGEST_DIR="function_app/ingest"

SETTINGS_ONLY=false
CODE_ONLY=false

for arg in "$@"; do
  case $arg in
    --settings-only) SETTINGS_ONLY=true ;;
    --code-only)     CODE_ONLY=true ;;
  esac
done

log() { echo "[$(date -u +%H:%M:%S)] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# ── Pre-checks ────────────────────────────────────────────────────────────────

log "Verificando prerequisitos..."
az account show -o none 2>/dev/null || die "az cli no autenticado. Ejecuta: az login"
[[ -f "$INGEST_DIR/function_app.py" ]] || die "No se encuentra $INGEST_DIR/function_app.py"

log "Subscription: $(az account show --query id -o tsv)"

# ── App Settings ──────────────────────────────────────────────────────────────

if ! $CODE_ONLY; then
  log "Configurando App Settings en $FUNC_NAME..."

  az functionapp config appsettings set \
    --name "$FUNC_NAME" \
    --resource-group "$RG" \
    -o none \
    --settings \
      "SEARCH_ENDPOINT=https://srch-roca-copilot-prod.search.windows.net" \
      "TARGET_INDEX_NAME=roca-contracts-v1-shadow" \
      "AZURE_OPENAI_ENDPOINT=https://rocadesarrollo-resource.cognitiveservices.azure.com/" \
      "AZURE_OPENAI_API_VERSION=2024-10-21" \
      "DISCOVERY_DEPLOYMENT=gpt-4.1-mini" \
      "EMBED_DEPLOYMENT=text-embedding-3-small" \
      "MAX_COMPLETION_TOKENS=4000" \
      "DOC_INTEL_ENDPOINT=https://rocadesarrollo-resource.cognitiveservices.azure.com/" \
      "DOC_INTEL_MODEL=prebuilt-layout" \
      "KV_URL=https://kv-roca-copilot-prod.vault.azure.net/" \
      "KV_SECRET_NAME=roca-copilot-sync-agent-secret" \
      "SP_APP_ID=18884cef-ace3-4899-9a54-be7eb66587b7" \
      "SP_TENANT_ID=9015a126-356b-4c63-9d1f-d2138ca83176" \
      "SP_HOSTNAME=rocadesarrollos1.sharepoint.com" \
      "STORAGE_ACCOUNT=strocacopilotprod" \
      "OCR_CONTAINER=ocr-raw" \
      "INGEST_STORAGE_ACCOUNT=stroingest" \
      "INGEST_STORAGE_CONNECTION__queueServiceUri=https://stroingest.queue.core.windows.net/" \
      "DELTA_SYNC_QUEUE=delta-sync-queue" \
      "FILE_PROCESS_QUEUE=file-process-queue" \
      "ENUMERATION_QUEUE=enumeration-queue" \
      "TABLE_DELTATOKENS=deltatokens" \
      "TABLE_FOLDERPATHS=folderpaths" \
      "TABLE_ITEMSINDEX=itemsindex" \
      "CLIENT_STATE=roca-ingest-v1" \
      "CHUNK_SIZE_CHARS=2000" \
      "CHUNK_OVERLAP_CHARS=200" \
      "MAX_CHUNKS_PER_DOC=60" \
      "EMBED_BATCH_SIZE=16" \
      "PREFLIGHT_MAX_SIZE_MB=80" \
      "PREFLIGHT_MAX_PAGES=150" \
      "MAX_ENUM_ITEMS=10000" \
      "DISABLE_ACTIONS="

  # App Insights por separado (el valor tiene ";" que confunde --settings si no se separa)
  az functionapp config appsettings set \
    --name "$FUNC_NAME" \
    --resource-group "$RG" \
    -o none \
    --settings "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=2a7c7622-1eea-476e-86ca-5c9d08e86626;IngestionEndpoint=https://eastus2-3.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus2.livediagnostics.monitor.azure.com/;ApplicationId=732d89e9-8f2d-4eae-a9c1-cd31fb66c9c0"

  log "App Settings configurados ✓"
fi

# ── Code Deploy ───────────────────────────────────────────────────────────────

if ! $SETTINGS_ONLY; then
  log "Empaquetando $INGEST_DIR/..."

  ZIP_FILE="$(mktemp -t ingest-deploy).zip"
  rm -f "$ZIP_FILE"
  (cd "$INGEST_DIR" && zip -qr "$ZIP_FILE" . \
    --exclude "*.pyc" \
    --exclude "__pycache__/*" \
    --exclude ".git/*" \
    --exclude "local.settings.json")

  ZIP_SIZE=$(du -sh "$ZIP_FILE" | cut -f1)
  log "Zip creado: $ZIP_FILE ($ZIP_SIZE)"

  log "Desplegando a $FUNC_NAME via Run-From-Package..."
  az functionapp deployment source config-zip \
    --name "$FUNC_NAME" \
    --resource-group "$RG" \
    --src "$ZIP_FILE" \
    --build-remote true \
    -o none

  rm -f "$ZIP_FILE"
  log "Deploy completado ✓"

  log "Esperando 30s para que la Function App arranque..."
  sleep 30

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://func-roca-ingest-prod.azurewebsites.net/api/status" 2>/dev/null || echo "000")

  if [[ "$STATUS" == "200" ]]; then
    log "Smoke test /api/status → HTTP 200 ✓"
  else
    log "WARN: /api/status → HTTP $STATUS (la Function App puede estar aún calentando)"
  fi

  log "Funciones registradas:"
  az functionapp function list \
    --name "$FUNC_NAME" \
    --resource-group "$RG" \
    --query "[].name" \
    -o tsv 2>/dev/null || log "(esperar 1-2 min para que aparezcan)"
fi

FUNC_ID=$(az functionapp show --name "$FUNC_NAME" --resource-group "$RG" --query id -o tsv 2>/dev/null)
log "========================================"
log "Deploy Día 3 — DONE"
log "  URL    : https://func-roca-ingest-prod.azurewebsites.net"
log "  Portal : https://portal.azure.com/#resource${FUNC_ID}"
log "========================================"
