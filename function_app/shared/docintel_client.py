"""Document Intelligence client — prebuilt-layout, AAD via Function App MI."""

from __future__ import annotations

from threading import Lock
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from . import auth, config

_client: Optional[DocumentIntelligenceClient] = None
_client_lock = Lock()


def get_docintel_client() -> DocumentIntelligenceClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = DocumentIntelligenceClient(
                endpoint=config.DOC_INTEL_ENDPOINT,
                credential=auth.get_mi_credential(),
            )
        return _client


def analyze_pdf_bytes(pdf_bytes: bytes) -> dict:
    client = get_docintel_client()
    poller = client.begin_analyze_document(
        model_id=config.DOC_INTEL_MODEL,
        body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    )
    result = poller.result()
    if hasattr(result, "as_dict"):
        return result.as_dict()
    import json as _json
    return _json.loads(_json.dumps(result, default=lambda o: o.__dict__))
