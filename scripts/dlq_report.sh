#!/bin/bash
# dlq_report.sh — reporta mensajes en la DLQ de ROCA Copilot.
#
# Correr manualmente cuando recibas la alerta de DLQ, o agendarlo diario:
#   # macOS launchd / Linux cron:
#   0 8 * * * /Users/datageni/Documents/ai_azure/azure-ai-contract-analysis/scripts/dlq_report.sh
#
# Produce un resumen: cantidad, top eventos, primer y último timestamp.

set -euo pipefail

STORAGE="strocacopilotprod"
RG="rg-roca-copilot-prod"
QUEUE="roca-dlq"

STG_KEY=$(az storage account keys list \
  --account-name "$STORAGE" --resource-group "$RG" \
  --query "[0].value" -o tsv 2>/dev/null)

COUNT=$(az storage queue stats --queue-name "$QUEUE" \
  --account-name "$STORAGE" --account-key "$STG_KEY" \
  --query approximateMessageCount -o tsv 2>/dev/null || echo "0")

echo "=== ROCA DLQ report — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo "Cola: $QUEUE"
echo "Mensajes aproximados: $COUNT"
echo ""

if [ "${COUNT:-0}" = "0" ] || [ -z "${COUNT:-}" ]; then
  echo "✅ DLQ vacía. Nada que reportar."
  exit 0
fi

echo "=== Peek de hasta 32 mensajes (NO los consume) ==="
az storage message peek \
  --queue-name "$QUEUE" \
  --account-name "$STORAGE" \
  --account-key "$STG_KEY" \
  --num-messages 32 \
  --query "[].content" -o tsv 2>/dev/null | while read -r b64; do
    echo "$b64" | base64 -d 2>/dev/null | python3 -c "
import json,sys
try:
    m = json.load(sys.stdin)
    print(f\"  [{m.get('timestamp','?')}] event={m.get('event_type','?'):15} item_id={(m.get('item_id') or '-')[:30]:30} err={(m.get('error') or '')[:120]}\")
except Exception as e:
    print(f\"  (parse error: {e})\")
"
done

echo ""
echo "Para inspeccionar un item específico en SharePoint:"
echo "  curl -X GET 'https://graph.microsoft.com/v1.0/drives/<drive_id>/items/<item_id>'"
