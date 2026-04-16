"""
Smoke test (mini-Fase 4B) — crea un índice provisional `roca-contracts-smoke` en
`srch-roca-copilot-prod` con el schema v2 simplificado para validar el pipeline
end-to-end antes de ingestar los 38 docs completos.

Omisiones intencionales vs schema v2 completo:
- `group_ids` / `user_ids` NO incluidos (smoke test sin security trimming).
- `version_number` / `is_latest_version` NO incluidos (todos los smoke docs son v1).
- Solo campos mínimos necesarios para validar las queries R-02, R-04, R-05, R-14.

Idempotente: si el índice ya existe, lo borra y lo recrea.
"""

from __future__ import annotations

import os
import subprocess
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

SEARCH_ENDPOINT = "https://srch-roca-copilot-prod.search.windows.net"
SEARCH_SERVICE_NAME = "srch-roca-copilot-prod"
SEARCH_RG = "rg-roca-copilot-prod"
INDEX_NAME = "roca-contracts-smoke"
EMBEDDING_DIM = 1536

VECTOR_ALGO = "hnsw-default"
VECTOR_PROFILE = "vector-profile-default"
SEMANTIC_CONFIG = "default-semantic-config"


def get_search_admin_key() -> str:
    env_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    if env_key and not env_key.startswith("__"):
        return env_key
    return subprocess.check_output(
        [
            "az",
            "search",
            "admin-key",
            "show",
            "--service-name",
            SEARCH_SERVICE_NAME,
            "--resource-group",
            SEARCH_RG,
            "--query",
            "primaryKey",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()


def build_index() -> SearchIndex:
    fields = [
        # --- Capa 1: núcleo ---
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="parent_document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="content_hash", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_id", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="total_chunks", type=SearchFieldDataType.Int32),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="es.microsoft",
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIM,
            vector_search_profile_name=VECTOR_PROFILE,
            hidden=True,  # NO retrievable
        ),
        SimpleField(name="sharepoint_url", type=SearchFieldDataType.String, filterable=True),
        SimpleField(
            name="alternative_urls",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
        SearchField(
            name="nombre_archivo",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
            analyzer_name="es.microsoft",
        ),
        SimpleField(name="site_origen", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(
            name="folder_path",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            analyzer_name="es.microsoft",
        ),
        SimpleField(name="fecha_procesamiento", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="extraction_confidence", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="extraction_notes", type=SearchFieldDataType.String),
        # --- Capa 2: metadata común ---
        SimpleField(name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(
            name="inmueble_codigos",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="inmueble_codigo_principal", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(
            name="doc_title",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="es.microsoft",
        ),
        SearchField(
            name="arrendador_nombre",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            analyzer_name="es.microsoft",
        ),
        SearchField(
            name="arrendatario_nombre",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            analyzer_name="es.microsoft",
        ),
        SimpleField(name="contribuyente_rfc", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="propietario_nombre",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            analyzer_name="es.microsoft",
        ),
        SimpleField(name="fecha_emision", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="fecha_vencimiento", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="es_vigente", type=SearchFieldDataType.Boolean, filterable=True),
        SearchField(
            name="autoridad_emisora",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
            analyzer_name="es.microsoft",
        ),
        # --- Capa 3: JSON flexible ---
        SearchField(
            name="extracted_metadata",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGO,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(name=VECTOR_PROFILE, algorithm_configuration_name=VECTOR_ALGO),
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="doc_title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="doc_type"),
                        SemanticField(field_name="inmueble_codigos"),
                        SemanticField(field_name="autoridad_emisora"),
                        SemanticField(field_name="folder_path"),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def main() -> int:
    key = get_search_admin_key()
    client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(key))

    existing = [i.name for i in client.list_indexes()]
    if INDEX_NAME in existing:
        print(f"[reset] Borrando índice existente '{INDEX_NAME}'...")
        client.delete_index(INDEX_NAME)

    index = build_index()
    print(f"[create] Creando índice '{INDEX_NAME}' con {len(index.fields)} campos...")
    client.create_index(index)
    print("✓ Índice creado")
    print(f"  endpoint: {SEARCH_ENDPOINT}")
    print(f"  index:    {INDEX_NAME}")
    print(f"  fields:   {len(index.fields)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
