#!/bin/bash
# ROCA Copilot sync Function App — deploy helper.
#
# What it does:
#   1. (Optional) Refreshes .python_packages from requirements.txt — only if
#      --refresh-deps is passed or .python_packages doesn't exist.
#   2. Creates a zip with function_app.py + host.json + requirements.txt +
#      shared/ + .python_packages/.
#   3. Uploads via `az functionapp deployment source config-zip` (Run From
#      Package path for Linux Consumption Y1).
#
# Usage:
#   ./deploy.sh                 # deploy, skip deps install if already present
#   ./deploy.sh --refresh-deps  # reinstall deps first (use after editing requirements.txt)
#
# Requires:
#   - `az` CLI logged in as admin.copilot@rocadesarrollos.com
#   - Python 3.11 with pip installed (for --target install)
#   - zip (macOS/Linux default)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RG="rg-roca-copilot-prod"
APP="func-roca-copilot-sync"
ZIP_PATH="/tmp/function_app.zip"

REFRESH_DEPS=false
SKIP_GATE=false
for arg in "$@"; do
    case "$arg" in
        --refresh-deps) REFRESH_DEPS=true ;;
        --skip-gate)    SKIP_GATE=true ;;  # emergencia/dev — NO usar en prod
    esac
done

# =================================================================
# OBLIGATORIO: predeploy gate bloquea si hay orquestaciones vivas.
# Deployar con orquestaciones Running = Non-Deterministic garantizado.
# Ver incidente 2026-04-19 en PLAN_ROCA_COPILOT.md.
# =================================================================
if [[ "$SKIP_GATE" == "false" ]]; then
    GATE="$SCRIPT_DIR/../scripts/predeploy_gate.sh"
    if [[ -x "$GATE" ]]; then
        echo "[0/3] Pre-deploy gate..."
        if ! "$GATE"; then
            echo ""
            echo "✗ Deploy ABORTADO por el gate. Si es emergencia, usa --skip-gate."
            exit 1
        fi
    else
        echo "⚠  scripts/predeploy_gate.sh no encontrado o no ejecutable — saltando gate."
    fi
fi

if [[ "$REFRESH_DEPS" == "true" ]] || [[ ! -d ".python_packages" ]]; then
    echo "[1/3] Installing Python deps for Linux x86_64 Python 3.11..."
    rm -rf .python_packages
    pip install \
        --target=.python_packages/lib/site-packages \
        --platform=manylinux2014_x86_64 \
        --python-version=3.11 \
        --only-binary=:all: \
        --upgrade \
        -r requirements.txt
else
    echo "[1/3] Skipping deps install (.python_packages already present — pass --refresh-deps to force)"
fi

echo "[2/3] Creating deployment zip..."
rm -f "$ZIP_PATH"
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
zip -rq "$ZIP_PATH" . \
    -x '*.pyc' \
    -x '**/__pycache__/*' \
    -x '.DS_Store' \
    -x '.venv/*' \
    -x 'deploy.sh' \
    -x '*.full' \
    -x '*.bak'
echo "   zip size: $(du -h "$ZIP_PATH" | cut -f1)"

echo "[3/3] Uploading to func-roca-copilot-sync (Run From Package)..."
az functionapp deployment source config-zip \
    --resource-group "$RG" \
    --name "$APP" \
    --src "$ZIP_PATH"

echo ""
echo "✓ Deploy complete. Wait ~60s for triggers to register, then:"
echo "  curl https://${APP}.azurewebsites.net/api/health"
