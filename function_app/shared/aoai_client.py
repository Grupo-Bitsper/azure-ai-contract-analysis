"""Azure OpenAI client — AAD via Function App MI.

A single AzureOpenAI instance is used for both discovery (gpt-4.1-mini) and
embeddings (text-embedding-3-small). Token refresh is handled by the SDK's
`azure_ad_token_provider` callback which delegates to our MI credential.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from openai import AzureOpenAI

from . import auth, config

_client: Optional[AzureOpenAI] = None
_client_lock = Lock()


def get_aoai_client() -> AzureOpenAI:
    global _client
    with _client_lock:
        if _client is None:
            _client = AzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_version=config.AZURE_OPENAI_API_VERSION,
                azure_ad_token_provider=auth.get_aoai_token,
            )
        return _client
