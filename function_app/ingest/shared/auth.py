"""Authentication helpers.

Two credentials coexist in the Function App:

1. **Function App System-Assigned MI** — used for Azure control plane
   (Search, Storage, Key Vault, Cognitive Services, Document Intelligence,
   Azure OpenAI). Accessed via `DefaultAzureCredential`, which in a
   Function App resolves the MI automatically.

2. **Sync-robot App Registration (`roca-copilot-sync-agent`)** — used for
   Microsoft Graph calls into SharePoint (Sites.Selected app-only). The
   client secret lives in Key Vault as `roca-copilot-sync-agent-secret`,
   and is fetched with the MI's Key Vault Secrets User role.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Optional

import msal
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from . import config

_mi_credential: Optional[DefaultAzureCredential] = None
_mi_lock = Lock()


def get_mi_credential() -> DefaultAzureCredential:
    """Returns a cached DefaultAzureCredential instance that resolves to the
    Function App System-Assigned Managed Identity at runtime."""
    global _mi_credential
    with _mi_lock:
        if _mi_credential is None:
            _mi_credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_shared_token_cache_credential=True,
            )
        return _mi_credential


_sync_secret_cache: dict[str, tuple[str, float]] = {}
_sync_secret_lock = Lock()
_SYNC_SECRET_TTL_S = 15 * 60  # refetch from KV every 15 min


def get_sync_agent_secret() -> str:
    """Fetches the sync-robot client_secret from Key Vault using the Function
    App MI. Cached in-memory for 15 min to avoid hammering KV."""
    now = time.time()
    with _sync_secret_lock:
        cached = _sync_secret_cache.get("secret")
        if cached and cached[1] > now:
            return cached[0]

        client = SecretClient(vault_url=config.KV_URL, credential=get_mi_credential())
        secret_value = client.get_secret(config.KV_SECRET_NAME).value
        _sync_secret_cache["secret"] = (secret_value, now + _SYNC_SECRET_TTL_S)
        return secret_value


_graph_token_cache: dict[str, tuple[str, float]] = {}
_graph_token_lock = Lock()


def get_graph_token() -> str:
    """Returns an app-only access token for Microsoft Graph using the sync
    robot App Registration + client_credentials flow. Cached in-memory until
    60s before expiry."""
    now = time.time()
    with _graph_token_lock:
        cached = _graph_token_cache.get("token")
        if cached and cached[1] > now + 60:
            return cached[0]

        secret = get_sync_agent_secret()
        authority = f"https://login.microsoftonline.com/{config.SP_TENANT_ID}"
        app = msal.ConfidentialClientApplication(
            client_id=config.SP_APP_ID,
            client_credential=secret,
            authority=authority,
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise RuntimeError(
                f"MSAL failed to acquire Graph token: {result.get('error_description') or result}"
            )
        token = result["access_token"]
        exp = now + int(result.get("expires_in", 3600))
        _graph_token_cache["token"] = (token, exp)
        return token


def generate_blob_read_sas(blob_name: str, expiry_minutes: int = 120) -> str:
    """Generates a read-only SAS URL for a blob using a user delegation key.
    Requires Storage Blob Delegator RBAC on the Function App MI.
    Raises RuntimeError with a clear message if the role is not assigned."""
    from datetime import datetime, timezone, timedelta
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from . import config

    account_url = f"https://{config.STORAGE_ACCOUNT}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=get_mi_credential())

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=expiry_minutes)

    try:
        delegation_key = service_client.get_user_delegation_key(
            key_start_time=now,
            key_expiry_time=expiry,
        )
    except Exception as exc:
        raise RuntimeError(
            f"generate_blob_read_sas: get_user_delegation_key failed — "
            f"assign 'Storage Blob Delegator' role to the Function App MI on "
            f"storage account {config.STORAGE_ACCOUNT}. Detail: {exc}"
        ) from exc

    sas_token = generate_blob_sas(
        account_name=config.STORAGE_ACCOUNT,
        container_name=config.OCR_CONTAINER,
        blob_name=blob_name,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"{account_url}/{config.OCR_CONTAINER}/{blob_name}?{sas_token}"


def get_aoai_token() -> str:
    """Returns an AAD bearer token for the Azure OpenAI data plane
    (Cognitive Services User)."""
    cred = get_mi_credential()
    return cred.get_token("https://cognitiveservices.azure.com/.default").token
