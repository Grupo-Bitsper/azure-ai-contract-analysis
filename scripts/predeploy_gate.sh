#!/bin/bash
# predeploy_gate.sh — BLOQUEA el deploy si hay orquestaciones Running/Pending.
#
# Por qué existe:
#   Deployar código del Function App mientras hay una orquestación viva corrompe
#   la history en Azure Table Storage y produce "Non-Deterministic workflow
#   detected" en cada replay posterior. El incidente 2026-04-19 y el stop
#   manual del 2026-04-12 son ejemplos del mismo antipatrón.
#
# Uso (obligatorio antes de deploy.sh):
#   ./scripts/predeploy_gate.sh && ./function_app/deploy.sh
#
# Exit codes:
#   0 — seguro para deploy (0 instancias vivas)
#   1 — hay instancias vivas, NO DEPLOYEAR

set -euo pipefail

APP="func-roca-copilot-sync"
RG="rg-roca-copilot-prod"
HUB="RocaCopilotHub"

MASTER_KEY=$(az functionapp keys list --name "$APP" --resource-group "$RG" \
  --query masterKey -o tsv 2>/dev/null)
BASE="https://${APP}.azurewebsites.net/runtime/webhooks/durabletask/instances"
PARAMS="taskHub=${HUB}&connection=Storage&code=${MASTER_KEY}"

BLOCKING_TOTAL=0
for rs in Running Pending ContinuedAsNew; do
  COUNT=$(curl -s "${BASE}?${PARAMS}&runtimeStatus=${rs}&top=100" 2>/dev/null \
    | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
  echo "  $rs: $COUNT"
  if [ "$COUNT" -gt 0 ]; then
    BLOCKING_TOTAL=$((BLOCKING_TOTAL + COUNT))
    echo "  → instancias en $rs:"
    curl -s "${BASE}?${PARAMS}&runtimeStatus=${rs}&top=5" 2>/dev/null \
      | python3 -c "
import json,sys
for x in json.load(sys.stdin)[:5]:
    print(f\"     {x.get('instanceId','?')[:16]}... | {x.get('name','?'):30} | created={x.get('createdTime','?')}\")
"
  fi
done

if [ "$BLOCKING_TOTAL" -gt 0 ]; then
  echo ""
  echo "❌ BLOQUEADO — hay $BLOCKING_TOTAL orquestaciones vivas."
  echo "   Opciones:"
  echo "   1. Esperar a que terminen (status HTTP /api/status/<instanceId>)"
  echo "   2. Deshabilitar timers + esperar drain:"
  echo "      az functionapp config appsettings set --name $APP --resource-group $RG \\"
  echo "        --settings AzureWebJobs.timer_sync_delta.Disabled=true \\"
  echo "                   AzureWebJobs.timer_acl_refresh.Disabled=true \\"
  echo "                   AzureWebJobs.timer_full_resync.Disabled=true"
  echo "   3. (Último recurso) Terminar + purgar huérfanas via HTTP DELETE."
  exit 1
fi

echo ""
echo "✅ Seguro para deploy: 0 orquestaciones vivas."
exit 0
