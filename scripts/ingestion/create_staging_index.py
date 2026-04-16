"""
Fase 5 — Crear índice staging `roca-contracts-v1-staging` idéntico al prod.

Wrapper thin sobre create_prod_index.py::build_index. NO destructivo:
si el índice ya existe, skip (el script prod lo borra y recrea).

Uso:
    python scripts/ingestion/create_staging_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import build_index from the validated prod script
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from create_prod_index import (
    SEARCH_ENDPOINT,
    VECTORIZER_NAME,
    AOAI_EMBED_DEPLOYMENT,
    build_index,
    get_search_admin_key,
)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

STAGING_INDEX_NAME = "roca-contracts-v1-staging"


def main() -> int:
    key = get_search_admin_key()
    client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(key))

    existing = [i.name for i in client.list_indexes()]
    if STAGING_INDEX_NAME in existing:
        print(f"[skip] Índice '{STAGING_INDEX_NAME}' ya existe — no se modifica")
        return 0

    index = build_index()
    index.name = STAGING_INDEX_NAME
    print(f"[create] Creando índice '{STAGING_INDEX_NAME}' con {len(index.fields)} campos + integrated vectorizer...")
    client.create_index(index)
    print("✓ Índice staging creado")
    print(f"  endpoint:   {SEARCH_ENDPOINT}")
    print(f"  index:      {STAGING_INDEX_NAME}")
    print(f"  fields:     {len(index.fields)}")
    print(f"  vectorizer: {VECTORIZER_NAME} → {AOAI_EMBED_DEPLOYMENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
