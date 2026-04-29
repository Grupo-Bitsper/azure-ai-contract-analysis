"""Runtime config for func-roca-ingest-prod.

All values come from Function App Application Settings. Deploy script sets these
via `az functionapp config appsettings set`. See DIA2_RESULTADOS.md for resource IDs.
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
TARGET_INDEX_NAME = _opt("TARGET_INDEX_NAME", "roca-contracts-v1-shadow")  # shadow until cutover

# --- Azure OpenAI ---
AZURE_OPENAI_ENDPOINT = _req("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = _opt("AZURE_OPENAI_API_VERSION", "2024-10-21")
DISCOVERY_DEPLOYMENT = _opt("DISCOVERY_DEPLOYMENT", "gpt-4.1-mini")
EMBED_DEPLOYMENT = _opt("EMBED_DEPLOYMENT", "text-embedding-3-small")
MAX_COMPLETION_TOKENS = int(_opt("MAX_COMPLETION_TOKENS", "4000"))

# --- Document Intelligence ---
DOC_INTEL_ENDPOINT = _req("DOC_INTEL_ENDPOINT")
DOC_INTEL_MODEL = _opt("DOC_INTEL_MODEL", "prebuilt-layout")

# --- Key Vault ---
KV_URL = _req("KV_URL")
KV_SECRET_NAME = _opt("KV_SECRET_NAME", "roca-copilot-sync-agent-secret")

# --- Microsoft Graph (sync robot) ---
SP_APP_ID = _req("SP_APP_ID")         # 18884cef-...
SP_TENANT_ID = _req("SP_TENANT_ID")   # 9015a126-...
SP_HOSTNAME = _opt("SP_HOSTNAME", "rocadesarrollos1.sharepoint.com")

# --- Storage: existing (blob cache de PDFs) ---
STORAGE_ACCOUNT = _opt("STORAGE_ACCOUNT", "strocacopilotprod")
OCR_CONTAINER = _opt("OCR_CONTAINER", "ocr-raw")

# --- Storage: nuevo (queues + tables del pipeline) ---
INGEST_STORAGE_ACCOUNT = _opt("INGEST_STORAGE_ACCOUNT", "stroingest")

# --- Queue names ---
DELTA_SYNC_QUEUE = _opt("DELTA_SYNC_QUEUE", "delta-sync-queue")
FILE_PROCESS_QUEUE = _opt("FILE_PROCESS_QUEUE", "file-process-queue")
ENUMERATION_QUEUE = _opt("ENUMERATION_QUEUE", "enumeration-queue")

# --- Table names (sin guiones — Azure Table Storage constraint) ---
TABLE_DELTATOKENS = _opt("TABLE_DELTATOKENS", "deltatokens")
TABLE_FOLDERPATHS = _opt("TABLE_FOLDERPATHS", "folderpaths")
TABLE_ITEMSINDEX  = _opt("TABLE_ITEMSINDEX",  "itemsindex")

# --- Graph webhook security ---
CLIENT_STATE = _opt("CLIENT_STATE", "roca-ingest-v1")

# --- SharePoint sites monitoreados (Decisión 12.1 del DESIGN: 2 sites) ---
SP_SITES = ["ROCAIA-INMUEBLESV2", "ROCA-IAInmuebles"]

# --- Chunking (mismo que pipeline viejo — no cambiar o los chunks no matchean) ---
CHUNK_SIZE_CHARS   = int(_opt("CHUNK_SIZE_CHARS",   "2000"))
CHUNK_OVERLAP_CHARS = int(_opt("CHUNK_OVERLAP_CHARS", "200"))
MAX_CHUNKS_PER_DOC  = int(_opt("MAX_CHUNKS_PER_DOC",  "60"))
EMBED_BATCH_SIZE    = int(_opt("EMBED_BATCH_SIZE",    "16"))

# --- Preflight limits (EC-09) ---
PREFLIGHT_MAX_SIZE_MB = int(_opt("PREFLIGHT_MAX_SIZE_MB", "80"))
PREFLIGHT_MAX_PAGES   = int(_opt("PREFLIGHT_MAX_PAGES",   "150"))

# --- Enumeration ---
MAX_ENUM_ITEMS = int(_opt("MAX_ENUM_ITEMS", "10000"))

# --- Kill-switch por tipo de acción (rollback parcial, sección 7.2 del plan) ---
DISABLE_ACTIONS = set(_opt("DISABLE_ACTIONS", "").split(",")) - {""}
