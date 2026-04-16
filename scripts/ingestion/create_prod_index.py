"""
Fase 4B — Crear índice de producción `roca-contracts-v1` en `srch-roca-copilot-prod`.

Schema v2 completo (32 campos) + integrated vectorizer + semantic config + HNSW.

Diferencias vs smoke:
- **Integrated vectorizer** apuntando a text-embedding-3-small (habilita vector_semantic_hybrid)
- Campos `group_ids` / `user_ids` para security trimming (vacíos en 4B, poblados en Fase 5)
- Versionado (`version_number`, `is_latest_version`)
- `alternative_urls` como Collection

Idempotente: si el índice ya existe, lo borra y lo recrea.
"""

from __future__ import annotations

import os
import subprocess
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
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
INDEX_NAME = "roca-contracts-v1"
EMBEDDING_DIM = 1536

AOAI_RESOURCE_URL = "https://rocadesarrollo-resource.openai.azure.com"
AOAI_EMBED_DEPLOYMENT = "text-embedding-3-small"
AOAI_EMBED_MODEL = "text-embedding-3-small"

VECTOR_ALGO = "hnsw-default"
VECTOR_PROFILE = "vector-profile-default"
VECTORIZER_NAME = "aoai-vectorizer"
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
        # --- Capa 1: núcleo inmutable (17 campos) ---
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="parent_document_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        # v2: content_hash — identificador canónico del documento físico
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
            hidden=True,
        ),
        SimpleField(name="sharepoint_url", type=SearchFieldDataType.String, filterable=True),
        # v2: alternative_urls — lista de URLs adicionales del mismo archivo físico
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
        # Security trimming — poblados en Fase 5, vacíos en 4B
        SimpleField(
            name="group_ids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            hidden=True,  # retrievable=false
        ),
        SimpleField(
            name="user_ids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            hidden=True,
        ),
        # SharePoint identity refs — poblados en Fase 5 por el Function App.
        # Permiten al timer_acl_refresh de Durable Functions mapear
        # content_hash → Graph API lookup de permisos sin almacenar la URL canónica.
        # NOT hidden: Azure AI Search no permite $select sobre campos hidden,
        # y el acl_refresh_orchestrator necesita leer estos campos via search query.
        # Son IDs opacos GUID — no contienen info sensitive ni revelan permisos.
        SimpleField(
            name="sp_site_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="sp_list_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="sp_list_item_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        # Versionado
        SimpleField(name="version_number", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="is_latest_version", type=SearchFieldDataType.Boolean, filterable=True),
        # Diagnóstico de pipeline
        SimpleField(name="extraction_confidence", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="extraction_notes", type=SearchFieldDataType.String),
        # --- Capa 2: metadata común (12 campos) ---
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

    # Vector search con integrated vectorizer — CRÍTICO para que Foundry agent pueda
    # hacer vector_semantic_hybrid sin pre-computar vectors
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
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name=VECTORIZER_NAME,
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=AOAI_RESOURCE_URL,
                    deployment_name=AOAI_EMBED_DEPLOYMENT,
                    model_name=AOAI_EMBED_MODEL,
                    # auth_identity=None → usa el System-Assigned MI del search service
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE,
                algorithm_configuration_name=VECTOR_ALGO,
                vectorizer_name=VECTORIZER_NAME,  # link al vectorizer
            ),
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
    print(f"[create] Creando índice '{INDEX_NAME}' con {len(index.fields)} campos + integrated vectorizer...")
    client.create_index(index)
    print("✓ Índice creado")
    print(f"  endpoint: {SEARCH_ENDPOINT}")
    print(f"  index:    {INDEX_NAME}")
    print(f"  fields:   {len(index.fields)}")
    print(f"  vectorizer: {VECTORIZER_NAME} → {AOAI_EMBED_DEPLOYMENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
