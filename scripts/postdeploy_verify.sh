#!/bin/bash
# postdeploy_verify.sh — valida que la primera orquestación post-deploy haya
# completado sin error de "Non-Deterministic workflow detected".
#
# Uso (correr justo después de deploy.sh):
#   ./scripts/postdeploy_verify.sh
#
# Qué hace:
#   1. Captura timestamp actual como "deploy time".
#   2. Re-habilita los timers si estaban deshabilitados.
#   3. Espera hasta 10 min a que arranque la primera orquestación (timer cada 5 min).
#   4. Confirma que su runtimeStatus sea Completed (NO Failed).
#   5. Si es Failed → exit 1 (el operador debería rollback).

set -euo pipefail

APP="func-roca-copilot-sync"
RG="rg-roca-copilot-prod"
HUB="RocaCopilotHub"

MASTER_KEY=$(az functionapp keys list --name "$APP" --resource-group "$RG" \
  --query masterKey -o tsv 2>/dev/null)
BASE="https://${APP}.azurewebsites.net/runtime/webhooks/durabletask/instances"
PARAMS="taskHub=${HUB}&connection=Storage&code=${MASTER_KEY}"

DEPLOY_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
echo "Deploy timestamp: $DEPLOY_TIME"

echo ""
echo "[1/3] Re-habilitando timers..."
az functionapp config appsettings set \
  --name "$APP" --resource-group "$RG" \
  --settings \
    "AzureWebJobs.timer_sync_delta.Disabled=false" \
    "AzureWebJobs.timer_acl_refresh.Disabled=false" \
    "AzureWebJobs.timer_full_resync.Disabled=false" \
  --output none

echo "[2/3] Esperando 6 min a que arranque el primer timer_sync_delta..."
sleep 360

echo "[3/3] Validando primera orquestación post-deploy..."
RESPONSE=$(curl -s "${BASE}?${PARAMS}&createdTimeFrom=${DEPLOY_TIME}&top=10")
FIRST_STATUS=$(echo "$RESPONSE" | python3 -c "
import json,sys
data = json.load(sys.stdin)
if not data:
    print('NONE')
else:
    by_name = {}
    for x in data:
        by_name.setdefault(x['name'], []).append(x)
    for name, instances in by_name.items():
        latest = max(instances, key=lambda x: x['createdTime'])
        print(f\"{name}|{latest['runtimeStatus']}|{latest.get('createdTime','?')}\")
" 2>&1)

if [ "$FIRST_STATUS" = "NONE" ]; then
  echo "⚠  No hay orquestaciones post-deploy todavía. Re-corre en 5 min."
  exit 2
fi

echo ""
echo "Resultados:"
echo "$FIRST_STATUS" | while IFS='|' read -r name status created; do
  echo "  $name | $status | $created"
done

# Si alguna está Failed → alerta
if echo "$FIRST_STATUS" | grep -q "Failed"; then
  echo ""
  echo "🚨 ALERTA: primera orquestación post-deploy está Failed."
  echo "   Razón probable: Non-Deterministic workflow si el orchestrator cambió."
  echo "   Acción: revisar App Insights → trazas DurableTask.Core y considerar rollback."
  exit 1
fi

echo ""
echo "✅ Primera orquestación post-deploy Completed/Running limpia."
exit 0
