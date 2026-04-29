"""Runtime configuration for ROCA Copilot sync Function App.

All values come from Function App Application Settings (env vars), which
were pre-configured via `az functionapp config appsettings set`. See
FASE_5_DESIGN_DECISIONS.md for the full list and their intended values.
"""

from __future__ import annotations

import os


def _req(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Required env var {key} is missing")
    return val


def _opt(key: str, default: str) -> str:
    return os.environ.get(key) or default


# --- Azure AI Search ---
SEARCH_ENDPOINT = _req("SEARCH_ENDPOINT")
TARGET_INDEX_NAME = _req("TARGET_INDEX_NAME")  # staging vs prod toggle lives here

# --- Azure OpenAI ---
AZURE_OPENAI_ENDPOINT = _req("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = _opt("AZURE_OPENAI_API_VERSION", "2024-10-21")
DISCOVERY_DEPLOYMENT = _req("DISCOVERY_DEPLOYMENT")  # gpt-4.1-mini (D-9)
EMBED_DEPLOYMENT = _req("EMBED_DEPLOYMENT")  # text-embedding-3-small
MAX_COMPLETION_TOKENS = int(_opt("MAX_COMPLETION_TOKENS", "4000"))

# --- Document Intelligence ---
DOC_INTEL_ENDPOINT = _req("DOC_INTEL_ENDPOINT")
DOC_INTEL_MODEL = _opt("DOC_INTEL_MODEL", "prebuilt-layout")

# --- Key Vault ---
KV_URL = _req("KV_URL")
KV_SECRET_NAME = _req("KV_SECRET_NAME")  # roca-copilot-sync-agent-secret

# --- Sync robot (Microsoft Graph via MSAL client_credentials) ---
SP_APP_ID = _req("SP_APP_ID")  # 18884cef-... App Registration
SP_TENANT_ID = _req("SP_TENANT_ID")  # 9015a126-... ROCA TEAM tenant
SP_HOSTNAME = _req("SP_HOSTNAME")  # rocadesarrollos1.sharepoint.com

# --- Storage account (reused) ---
STORAGE_ACCOUNT = _req("STORAGE_ACCOUNT")
OCR_CONTAINER = _opt("OCR_CONTAINER", "ocr-raw")
DLQ_QUEUE = _opt("DLQ_QUEUE", "roca-dlq")

# --- Chunking parameters (match ingest_prod.py validated in F4B) ---
CHUNK_SIZE_CHARS = int(_opt("CHUNK_SIZE_CHARS", "2000"))
CHUNK_OVERLAP_CHARS = int(_opt("CHUNK_OVERLAP_CHARS", "200"))
MAX_CHUNKS_PER_DOC = int(_opt("MAX_CHUNKS_PER_DOC", "60"))
EMBED_BATCH_SIZE = int(_opt("EMBED_BATCH_SIZE", "16"))

# --- SharePoint sites to sync ---
SP_SITES = [
    "ROCAIA-INMUEBLESV2",
]


def target_is_staging() -> bool:
    """Safety check used by orchestrators: is the current target the staging index?"""
    return TARGET_INDEX_NAME.endswith("-staging")
