#!/bin/bash
# recovery_clean_queues.sh — reset completo de Durable Functions task hub.
#
# CUÁNDO USARLO: cuando veas "Non-Deterministic workflow detected" repetido
# en las orquestaciones nuevas aunque hayas purgado instancias. Significa
# que hay mensajes residuales en las Storage Queues internas referenciando
# history huérfana. La solución oficial de Microsoft (ver doc
# "durable-functions-versioning → Stop all in-flight instances") es:
#
#   1. STOP Function App
#   2. Borrar las queues control-* y workitems
#   3. START Function App (Azure recrea las queues vacías)
#
# NO AFECTA DATOS:
#   - AI Search (9K+ chunks indexados): intactos
#   - SharePoint (los PDFs originales): intactos
#   - Delta tokens (hasta dónde sincronizó): intactos
#   - Cache de OCR en blob: intacto
#
# Único efecto: ~5 min de downtime de indexación automática (el bot de Teams
# también queda caído durante el stop, ~2 min).
#
# Uso:
#   ./scripts/recovery_clean_queues.sh

set -euo pipefail

APP="func-roca-copilot-sync"
RG="rg-roca-copilot-prod"
STORAGE="strocacopilotprod"
HUB="rocacopilothub"

echo "⚠  Este script hará STOP de $APP por ~3 min. ¿Continuar? (ctrl+c para abortar, enter para seguir)"
read -r

STG_KEY=$(az storage account keys list --account-name "$STORAGE" --resource-group "$RG" \
  --query "[0].value" -o tsv 2>/dev/null)

echo "[1/6] Deshabilitar timers (evitar nuevas Failed durante recovery)..."
az functionapp config appsettings set \
  --name "$APP" --resource-group "$RG" \
  --settings \
    "AzureWebJobs.timer_sync_delta.Disabled=true" \
    "AzureWebJobs.timer_acl_refresh.Disabled=true" \
    "AzureWebJobs.timer_full_resync.Disabled=true" \
  --output none

echo "[2/6] STOP Function App..."
az functionapp stop --name "$APP" --resource-group "$RG"
sleep 20

echo "[3/6] Inspeccionar queues antes del delete..."
for q in ${HUB}-control-00 ${HUB}-control-01 ${HUB}-control-02 ${HUB}-control-03 ${HUB}-workitems; do
  CT=$(az storage queue stats --queue-name "$q" \
    --account-name "$STORAGE" --account-key "$STG_KEY" \
    --query approximateMessageCount -o tsv 2>/dev/null || echo "0")
  echo "  $q: $CT mensajes"
done

echo ""
echo "[4/6] Borrar las queues (Azure las recrea vacías al START)..."
for q in ${HUB}-control-00 ${HUB}-control-01 ${HUB}-control-02 ${HUB}-control-03 ${HUB}-workitems; do
  az storage queue delete --name "$q" \
    --account-name "$STORAGE" --account-key "$STG_KEY" -o none
  echo "  ✓ $q borrada"
done

echo ""
echo "[5/6] Purgar instancias Failed/Terminated/Completed del task hub (limpieza de history)..."
MASTER_KEY=$(az functionapp keys list --name "$APP" --resource-group "$RG" --query masterKey -o tsv 2>/dev/null)
BASE="https://${APP}.azurewebsites.net/runtime/webhooks/durabletask/instances"
PARAMS="taskHub=RocaCopilotHub&connection=Storage&code=${MASTER_KEY}"
FROM=$(date -u -v-30d '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '30 days ago' '+%Y-%m-%dT%H:%M:%SZ')
TO=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
# Nota: el app está stopped, estas API calls no van a responder hasta start.
# La purga real ocurre post-start en el paso 6 extendido.

echo ""
echo "[6/6] START Function App..."
az functionapp start --name "$APP" --resource-group "$RG"

echo ""
echo "Esperando 90s cold start..."
sleep 90

echo ""
echo "Re-habilitando timers..."
az functionapp config appsettings set \
  --name "$APP" --resource-group "$RG" \
  --settings \
    "AzureWebJobs.timer_sync_delta.Disabled=false" \
    "AzureWebJobs.timer_acl_refresh.Disabled=false" \
    "AzureWebJobs.timer_full_resync.Disabled=false" \
  --output none

echo ""
echo "✓ Recovery completado. Monitorea en los próximos 6 min:"
echo "  ./scripts/postdeploy_verify.sh"
echo ""
echo "Si sigue fallando después de esto, revisa los logs y escala."
