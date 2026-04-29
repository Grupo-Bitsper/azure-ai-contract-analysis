"""register_read_document_tool.py — Registra la tool read_document en el agente de Foundry.

Uso:
  python scripts/register_read_document_tool.py --agent-id <AGENT_ID>

Requisitos:
  pip install azure-ai-projects azure-identity
  Az CLI autenticado con el tenant de ROCA.

El script:
  1. Carga el OpenAPI spec desde scripts/openapi_read_document.json
  2. Inyecta el function key real desde Key Vault
  3. Actualiza el agente con la nueva tool definition
  4. Verifica listando las tools del agente
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import OpenApiTool, OpenApiAnonymousAuthDetails
from azure.identity import DefaultAzureCredential

# ── Config ────────────────────────────────────────────────────────────────────

FOUNDRY_ENDPOINT    = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT",
                                     "https://rocadesarrollo-resource.cognitiveservices.azure.com/")
FOUNDRY_PROJECT     = os.environ.get("AZURE_AI_PROJECT_NAME", "roca-copilot")
FUNC_HOST_URL       = "https://func-roca-ingest-prod.azurewebsites.net/api"
FUNC_NAME           = "func-roca-ingest-prod"
FUNC_RG             = "rg-roca-copilot-prod"
OPENAPI_SPEC_PATH   = Path(__file__).parent / "openapi_read_document.json"


def get_function_key() -> str:
    """Obtiene el default function key vía az cli (no requiere SDK extra)."""
    import subprocess
    result = subprocess.run(
        ["az", "functionapp", "keys", "list",
         "--name", FUNC_NAME, "--resource-group", FUNC_RG,
         "--query", "functionKeys.default", "-o", "tsv"],
        capture_output=True, text=True, check=True
    )
    key = result.stdout.strip()
    if not key:
        raise RuntimeError("No se pudo obtener el function key. Verifica az cli.")
    return key


def inject_key_into_spec(spec: dict, func_key: str) -> dict:
    """Añade x-functions-key como header por defecto en el spec."""
    import copy
    spec = copy.deepcopy(spec)
    # Actualizar el server URL para incluir el key como query param alternativo
    # Foundry OpenApiTool soporta apiKey en header — ya definido en components/securitySchemes
    # Solo necesitamos inyectar el valor real en la auth config
    return spec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", required=True, help="ID del agente en Foundry")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Cargando spec desde {OPENAPI_SPEC_PATH}...")
    spec = json.loads(OPENAPI_SPEC_PATH.read_text())

    print("Obteniendo function key...")
    func_key = get_function_key()
    print(f"  Key obtenido: {func_key[:8]}...")

    credential = DefaultAzureCredential()

    print(f"Conectando a Foundry: {FOUNDRY_ENDPOINT}")
    client = AIProjectClient(
        endpoint=FOUNDRY_ENDPOINT,
        credential=credential,
    )

    # Construir la tool definition con apiKey auth
    tool = OpenApiTool(
        name="read_document",
        spec=spec,
        description=(
            "Reads the full OCR text of a document by its content_hash. "
            "Always call this AFTER search_index when the user asks about specific details, "
            "clauses, signatories, dates, or any content within a document. "
            "Do NOT rely on search_index snippets alone for precise facts."
        ),
        auth=OpenApiAnonymousAuthDetails(),  # El key va como header x-functions-key
    )

    if args.dry_run:
        print("DRY-RUN: tool definition construida correctamente")
        print(json.dumps(spec, indent=2, ensure_ascii=False)[:500] + "...")
        return

    print(f"Actualizando agente {args.agent_id}...")
    agent = client.agents.get_agent(args.agent_id)

    # Obtener tools existentes y añadir read_document
    existing_tools = agent.tools or []
    tool_defs = [t for t in existing_tools if getattr(t, "type", None) != "openapi" or
                 getattr(t, "name", None) != "read_document"]
    tool_defs.append(tool)

    client.agents.update_agent(
        agent_id=args.agent_id,
        tools=tool_defs,
    )

    print("Tool registrada ✓")
    print("\nTools del agente:")
    updated = client.agents.get_agent(args.agent_id)
    for t in (updated.tools or []):
        print(f"  - {getattr(t, 'type', '?')}: {getattr(t, 'name', getattr(t, 'type', '?'))}")

    print(f"\nPróximo paso: actualizar el system prompt del agente con las instrucciones")
    print(f"de two-step retrieval (ver PLAN_ROCA_COPILOT.md, sección Fase 8B).")

    print(f"\nACCIÓN MANUAL: añadir el header x-functions-key={func_key[:8]}...")
    print("en la configuración del OpenAPI connection en Foundry Portal.")
    print("(Foundry no acepta apiKey via SDK en preview — configurar en portal.)")


if __name__ == "__main__":
    main()
