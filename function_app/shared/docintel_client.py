"""Document Intelligence client — prebuilt-layout, AAD via Function App MI."""

from __future__ import annotations

import io
from threading import Lock
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from pypdf import PdfReader, PdfWriter

from . import auth, config

_client: Optional[DocumentIntelligenceClient] = None
_client_lock = Lock()

# PDFs with more pages than this threshold are split before OCR to avoid the
# 10-minute Function App timeout. Each chunk is analyzed independently and
# results are merged. Works for scanned PDFs (image-only pages) too — pypdf
# splits at the page structure level regardless of content type.
_PAGE_SPLIT_THRESHOLD = 50
_PAGES_PER_CHUNK = 50


def get_docintel_client() -> DocumentIntelligenceClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = DocumentIntelligenceClient(
                endpoint=config.DOC_INTEL_ENDPOINT,
                credential=auth.get_mi_credential(),
            )
        return _client


def _analyze_bytes(pdf_bytes: bytes) -> dict:
    """Sends a single PDF byte payload to Document Intelligence and returns the raw dict."""
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


def _split_pdf_chunks(pdf_bytes: bytes, pages_per_chunk: int) -> list[bytes]:
    """Splits a PDF into byte chunks of at most pages_per_chunk pages each."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total = len(reader.pages)
    chunks: list[bytes] = []
    for start in range(0, total, pages_per_chunk):
        writer = PdfWriter()
        for page in reader.pages[start : start + pages_per_chunk]:
            writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        chunks.append(buf.getvalue())
    return chunks


def _merge_ocr_results(parts: list[dict]) -> dict:
    """Concatenates content strings and table lists from multiple OCR results."""
    if len(parts) == 1:
        return parts[0]
    combined_content = "\n\n".join(p.get("content") or "" for p in parts)
    combined_tables: list[dict] = []
    for p in parts:
        combined_tables.extend(p.get("tables") or [])
    base = parts[0].copy()
    base["content"] = combined_content
    base["tables"] = combined_tables
    return base


def analyze_pdf_bytes(pdf_bytes: bytes) -> dict:
    """Analyzes a PDF with Document Intelligence. Large PDFs (> _PAGE_SPLIT_THRESHOLD
    pages) are split into chunks first to stay within the 10-minute timeout."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    if total_pages <= _PAGE_SPLIT_THRESHOLD:
        return _analyze_bytes(pdf_bytes)

    chunks = _split_pdf_chunks(pdf_bytes, _PAGES_PER_CHUNK)
    parts = [_analyze_bytes(chunk) for chunk in chunks]
    return _merge_ocr_results(parts)
