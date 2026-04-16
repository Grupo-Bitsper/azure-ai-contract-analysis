"""
Fase 4A.2a — OCR con Azure Document Intelligence (prebuilt-layout) sobre la muestra.

Recorre todos los PDFs en contratosdemo_real/, los procesa con el modelo
`prebuilt-layout` (tablas + bounding boxes + selection marks) y guarda el JSON
crudo en dos lugares:

1. Blob: `strocacopilotprod/ocr-raw/sample_discovery/{stem}.json` — fuente de
   verdad reusable por Fase 4B para re-indexar sin repagar OCR.
2. Local: `contratosdemo_real/ocr_raw/{stem}.json` — copia para inspección rápida.

Idempotente: si el JSON ya existe (blob o local), skip. Auth del
Document Intelligence account es por key (leída con `az` + env) y auth del
storage es AAD con `DefaultAzureCredential` (el usuario tiene Storage Blob Data
Contributor autoasignado desde los smoke tests de Fase 3).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# --- Constants ---------------------------------------------------------------

DOCINTEL_ENDPOINT = "https://rocadesarrollo-resource.cognitiveservices.azure.com/"
DOCINTEL_MODEL = "prebuilt-layout"
DOCINTEL_ACCOUNT_NAME = "rocadesarrollo-resource"
DOCINTEL_ACCOUNT_RG = "rg-admin.copilot-9203"

STORAGE_ACCOUNT = "strocacopilotprod"
STORAGE_CONTAINER = "ocr-raw"
BLOB_PREFIX = "sample_discovery"

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
LOCAL_OCR_DIR = SAMPLE_DIR / "ocr_raw"

# --- Auth helpers ------------------------------------------------------------


def get_docintel_key() -> str:
    """Lee la key del AIServices account via `az` CLI."""
    env_key = os.environ.get("DOCINTEL_KEY")
    if env_key:
        return env_key
    out = subprocess.check_output(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--name",
            DOCINTEL_ACCOUNT_NAME,
            "--resource-group",
            DOCINTEL_ACCOUNT_RG,
            "--query",
            "key1",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()
    return out


# --- Main --------------------------------------------------------------------


def main() -> int:
    pdfs = sorted(
        [
            p
            for p in SAMPLE_DIR.iterdir()
            if p.is_file() and p.suffix.lower() == ".pdf"
        ]
    )
    if not pdfs:
        print(f"⚠ No hay PDFs en {SAMPLE_DIR}", file=sys.stderr)
        return 1
    print(f"Fase 4A.2a — OCR sobre {len(pdfs)} PDFs")

    LOCAL_OCR_DIR.mkdir(parents=True, exist_ok=True)

    print("[init] Conectando a Document Intelligence + Blob Storage...")
    key = get_docintel_key()
    di_client = DocumentIntelligenceClient(
        endpoint=DOCINTEL_ENDPOINT, credential=AzureKeyCredential(key)
    )

    cred = DefaultAzureCredential()
    blob_service = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=cred
    )
    container = blob_service.get_container_client(STORAGE_CONTAINER)

    processed = 0
    skipped = 0
    failed: list[str] = []

    for i, pdf in enumerate(pdfs, start=1):
        stem = pdf.stem
        local_json = LOCAL_OCR_DIR / f"{stem}.json"
        blob_name = f"{BLOB_PREFIX}/{stem}.json"

        # Idempotencia: local O blob ya existe
        blob_exists = False
        try:
            blob_exists = container.get_blob_client(blob_name).exists()
        except Exception as e:
            print(f"  [{i}/{len(pdfs)}] [warn] blob exists check falló: {e}")

        if local_json.exists() and blob_exists:
            print(f"  [{i}/{len(pdfs)}] [skip] {stem} (local+blob ya existen)")
            skipped += 1
            continue

        print(f"  [{i}/{len(pdfs)}] [OCR] {stem} ({pdf.stat().st_size/1024/1024:.1f} MB)")
        try:
            with open(pdf, "rb") as fh:
                poller = di_client.begin_analyze_document(
                    model_id=DOCINTEL_MODEL,
                    body=AnalyzeDocumentRequest(bytes_source=fh.read()),
                )
            result = poller.result()
            # Normalizar a dict serializable
            if hasattr(result, "as_dict"):
                payload = result.as_dict()
            else:
                payload = json.loads(json.dumps(result, default=lambda o: o.__dict__))
        except Exception as e:
            print(f"      ! OCR falló: {e}")
            failed.append(stem)
            continue

        raw_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # Local copy
        local_json.write_text(raw_json, encoding="utf-8")

        # Upload to blob (overwrite=True — si ya estaba parcial, lo sustituimos)
        try:
            container.upload_blob(
                name=blob_name,
                data=raw_json.encode("utf-8"),
                overwrite=True,
                content_settings=None,
            )
        except Exception as e:
            print(f"      ! Upload blob falló: {e}")
            failed.append(stem)
            continue

        processed += 1
        num_pages = len(payload.get("pages", []))
        num_tables = len(payload.get("tables", []))
        print(f"      ✓ pages={num_pages} tables={num_tables}")

    print("\n=== Resumen OCR ===")
    print(f"  procesados esta corrida: {processed}")
    print(f"  skipped (ya existían):   {skipped}")
    print(f"  fallidos:                {len(failed)}")
    if failed:
        for f in failed:
            print(f"    - {f}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
