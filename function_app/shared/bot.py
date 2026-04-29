"""
ROCA Copilot — Teams bot bridge.

Llama al Agent Application endpoint (Responses API) de Foundry.
Stateless: cada mensaje es independiente (apropiado para Q&A de contratos).

Diseño 2026-04-22 — sin middleware:
El bot pasa el texto del usuario tal cual al agente. El retrieval lo hace
el agente vía su tool azure_ai_search (query_type=vector_semantic_hybrid,
top_k=20) que recupera mejor que el middleware lexical anterior.

Best practice MS + Anthropic: el modelo decide qué tool invocar (just-in-time
retrieval); no inyectar contexto pre-cargado con instrucción "exclusivamente"
porque suprime la tool del agente y crea doble retrieval con context bloat.

extract_codes() y pre_search_by_codes() se mantienen como utilidades para un
futuro Function tool (patrón oficial MS para filtros dinámicos), pero NO se
invocan desde ask_roca_copilot.
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import List

import requests
from azure.identity import DefaultAzureCredential

from . import config, search_client

log = logging.getLogger("roca-bot")

# Endpoint moderno /openai/v1/responses + agent_reference. Respeta el
# agent_endpoint.version_selector del agente, así que publicar nueva versión
# desde Foundry redirige el tráfico sin redeploy del bot.
_RESPONSES_ENDPOINT = (
    "https://rocadesarrollo-resource.services.ai.azure.com"
    "/api/projects/rocadesarrollo/openai/v1/responses"
)
_AGENT_NAME = "roca-copilot"
_TOKEN_SCOPE = "https://ai.azure.com/.default"
_TIMEOUT = 55  # Bot Framework corta a 60s

# Foundry agrega anotaciones inline de citaciones cuando el agente usa la tool
# azure_ai_search, en formato 【N:N†source】. No se pueden suprimir desde el
# system prompt (son post-procesado del backend). Las strippeamos para UX
# limpia en Teams. Patrón: corchetes japoneses + dígitos + colon + dígitos +
# opcional †source + corchete cerrado.
_CITATION_PATTERN = re.compile(r"【\d+:\d+(?:†[^】]*)?】")


def strip_citations(text: str) -> str:
    """Elimina anotaciones inline 【4:1†source】 del texto del agente."""
    cleaned = _CITATION_PATTERN.sub("", text)
    # Elimina espacios múltiples y trailing whitespace que quedan tras el strip
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# ============================================================================
# Code extraction + pre-search
# ============================================================================

# Lista curada de códigos conocidos. Editar este set cuando se agreguen nuevos
# inmuebles al portafolio ROCA. El regex genérico de abajo es un fallback para
# códigos que sigan la convención pero que aún no se hayan agregado aquí.
KNOWN_CODES: set[str] = {
    "RA03", "GU01A", "GU01-TEN", "CJ03", "CJ03B",
    "RE05", "RE05A", "SL02", "SHELL-SLP02",
}

# Patrón genérico: 2-5 letras + opcional guión + 2-3 dígitos + opcional letra
# + opcional -sufijo alfanumérico. Cubre: RA03, GU01A, GU01-TEN, CJ03B,
# SHELL-SLP02. Case-insensitive en la búsqueda; normaliza a upper.
_CODE_PATTERN = re.compile(
    r"\b[A-Z]{2,5}(?:-?[A-Z0-9]{1,5})?\d{2,3}[A-Z]?(?:-[A-Z0-9]{1,8})?\b",
    re.IGNORECASE,
)


def extract_codes(user_text: str) -> List[str]:
    """Detecta códigos de inmueble en el texto del usuario.

    Estrategia en 2 capas:
    1. Match contra lista curada KNOWN_CODES (normalizando spaces/guiones).
    2. Regex genérico para capturar patrones que parecen códigos pero aún no
       están en la lista curada (útil cuando agregan un inmueble nuevo).
    """
    text_upper = user_text.upper()
    found: list[str] = []

    # 1. Lista curada — acepta variaciones ("RA 03", "RA-03" → "RA03")
    for code in KNOWN_CODES:
        variations = {code, code.replace("-", " "), code.replace("-", "")}
        for v in variations:
            if re.search(rf"\b{re.escape(v)}\b", text_upper):
                if code not in found:
                    found.append(code)
                break

    # 2. Regex genérico — solo si la lista curada no encontró nada
    if not found:
        for match in _CODE_PATTERN.findall(text_upper):
            if match not in found:
                found.append(match)

    return found


def pre_search_by_codes(user_text: str, codes: List[str], top: int = 5) -> str:
    """Hace hybrid search filtrado por los códigos detectados y devuelve un
    bloque de contexto formateado para inyectar al agente.

    Usa el pattern oficial de MS `search.in(c, 'v1,v2', ',')` dentro de
    `any(...)` para el campo colection `inmueble_codigos`.
    """
    if not codes:
        return ""

    codes_csv = ",".join(codes)
    filter_expr = f"inmueble_codigos/any(c: search.in(c, '{codes_csv}', ','))"

    try:
        client = search_client.get_search_client()
        results = list(client.search(
            search_text=user_text,
            filter=filter_expr,
            top=top,
            query_type="semantic",
            semantic_configuration_name="default-semantic-config",
            select=[
                "nombre_archivo",
                "folder_path",
                "doc_type",
                "inmueble_codigo_principal",
                "inmueble_codigos",
                "doc_title",
                "sharepoint_url",
                "fecha_emision",
                "fecha_vencimiento",
                "es_vigente",
                "autoridad_emisora",
                "arrendador_nombre",
                "arrendatario_nombre",
                "propietario_nombre",
                "content",
            ],
        ))
    except Exception as exc:
        log.warning("[PRE-SEARCH] failed (%s) — falling back sin contexto", exc)
        return ""

    if not results:
        return ""

    lines = [
        f"[CONTEXTO PRE-FILTRADO POR CÓDIGO(S): {', '.join(codes)}]",
        f"Se encontraron {len(results)} resultados relevantes server-side.",
        "",
    ]
    for i, r in enumerate(results, 1):
        snippet = (r.get("content") or "").replace("\n", " ")[:400]
        lines.extend([
            f"--- Resultado {i} ---",
            f"Archivo: {r.get('nombre_archivo', '?')}",
            f"Folder: {r.get('folder_path', '')}",
            f"Tipo: {r.get('doc_type', '?')}",
            f"Código principal: {r.get('inmueble_codigo_principal', '?')}",
            f"Todos los códigos: {', '.join(r.get('inmueble_codigos') or [])}",
            f"URL: {r.get('sharepoint_url', '')}",
            f"Extracto: {snippet}",
            "",
        ])
    return "\n".join(lines)


# ============================================================================
# Bot entry point
# ============================================================================


def _get_token() -> str:
    cred = DefaultAzureCredential()
    return cred.get_token(_TOKEN_SCOPE).token


def ask_roca_copilot(user_text: str) -> str:
    """Envía una pregunta al agente y devuelve el texto de la respuesta.

    El agente recupera por sí mismo vía su tool azure_ai_search
    (vector_semantic_hybrid + top_k=20). No se hace pre-search ni se inyecta
    contexto desde el bot.
    """
    token = _get_token()
    resp = requests.post(
        _RESPONSES_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "agent_reference": {"type": "agent_reference", "name": _AGENT_NAME},
            "input": user_text,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    raw = block.get("text", "").strip()
                    return strip_citations(raw)

    log.warning("Respuesta vacía del agente. Payload: %s", str(data)[:300])
    return "No obtuve respuesta del agente. Intenta de nuevo."
