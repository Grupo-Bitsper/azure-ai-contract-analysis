"""
ROCA Copilot — Teams bot bridge.

Llama al Agent Application endpoint (Responses API) de Foundry.
Stateless: cada mensaje es independiente (apropiado para Q&A de contratos).
"""
from __future__ import annotations

import logging
import os

import requests
from azure.identity import DefaultAzureCredential

log = logging.getLogger("roca-bot")

_RESPONSES_ENDPOINT = (
    "https://rocadesarrollo-resource.services.ai.azure.com"
    "/api/projects/rocadesarrollo/applications/roca-copilot"
    "/protocols/openai/responses?api-version=2025-11-15-preview"
)
_MODEL = "gpt-4.1-mini"
_TOKEN_SCOPE = "https://ai.azure.com/.default"
_TIMEOUT = 55  # Bot Framework corta a 60s


def _get_token() -> str:
    cred = DefaultAzureCredential()
    return cred.get_token(_TOKEN_SCOPE).token


def ask_roca_copilot(user_text: str) -> str:
    """Envía una pregunta al agente y devuelve el texto de la respuesta."""
    token = _get_token()
    resp = requests.post(
        _RESPONSES_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"model": _MODEL, "input": user_text},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    return block.get("text", "").strip()

    log.warning("Respuesta vacía del agente. Payload: %s", str(data)[:300])
    return "No obtuve respuesta del agente. Intenta de nuevo."
