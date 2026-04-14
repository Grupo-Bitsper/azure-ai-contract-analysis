"""
Crea el índice de Azure AI Search con schema optimizado para contratos
Incluye: vector search, semantic ranking, y Spanish analyzer
"""
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.search_config import (
    INDEX_NAME, EMBEDDING_DIMENSIONS, VECTOR_PROFILE,
    SEMANTIC_CONFIG, SPANISH_ANALYZER
)
from scripts.search.search_utils import get_search_index_client
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
)


def create_index_schema() -> SearchIndex:
    """
    Crea el schema del índice de contratos

    Returns:
        SearchIndex configurado con todos los campos y configuraciones
    """
    # Definir campos del índice
    fields = [
        # Campo primario
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
            sortable=True,
        ),

        # Campos de contenido
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=SPANISH_ANALYZER,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE,
        ),

        # Campos de metadata
        SearchableField(
            name="titulo",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
            analyzer_name=SPANISH_ANALYZER,
        ),
        SimpleField(
            name="tipo_contrato",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="numero_contrato",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="fecha_contrato",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="fecha_vencimiento",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="proveedor",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
            analyzer_name=SPANISH_ANALYZER,
        ),
        SearchableField(
            name="cliente",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True,
            analyzer_name=SPANISH_ANALYZER,
        ),
        SimpleField(
            name="monto",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="moneda",
            type=SearchFieldDataType.String,
            filterable=True,
        ),

        # Campos de tracking
        SimpleField(
            name="nombre_archivo",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="url_sharepoint",
            type=SearchFieldDataType.String,
            retrievable=True,
        ),
        SimpleField(
            name="numero_pagina",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="total_chunks",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
        SimpleField(
            name="fecha_indexacion",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),

        # Campos adicionales
        SearchField(
            name="partes_firmantes",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
        ),
        SearchField(
            name="clausulas_principales",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
        ),

        # Campos semánticos (Phase 2)
        SimpleField(
            name="seccion_tipo",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="seccion_nombre",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name=SPANISH_ANALYZER,
        ),
        SimpleField(
            name="numero_clausula",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="pagina_inicio",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="pagina_fin",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="chunking_mode",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
    ]

    # Configuración de vector search
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE,
                algorithm_configuration_name="hnsw-algorithm",
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-algorithm",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine",
                }
            )
        ],
    )

    # Configuración semántica
    semantic_config = SemanticConfiguration(
        name=SEMANTIC_CONFIG,
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="titulo"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[
                SemanticField(field_name="tipo_contrato"),
                SemanticField(field_name="proveedor"),
                SemanticField(field_name="cliente"),
            ],
        ),
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Crear el índice
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    return index


def create_search_index(force_delete: bool = False):
    """Crea el índice de Azure AI Search

    Args:
        force_delete: Si True, elimina el índice existente sin preguntar
    """

    print("=" * 70)
    print("🔧 Creando índice de Azure AI Search para contratos")
    print("=" * 70)

    try:
        # Obtener cliente
        print(f"\n📡 Conectando a Azure AI Search...")
        index_client = get_search_index_client()

        # Crear schema
        print(f"📋 Creando schema del índice: {INDEX_NAME}")
        index = create_index_schema()

        # Verificar si el índice ya existe
        try:
            existing_index = index_client.get_index(INDEX_NAME)
            print(f"\n⚠️  El índice '{INDEX_NAME}' ya existe")

            if force_delete:
                print(f"🗑️  Eliminando índice existente (--delete)...")
                index_client.delete_index(INDEX_NAME)
                print(f"✅ Índice eliminado")
            else:
                print(f"   ¿Deseas eliminarlo y recrearlo? (s/n): ", end="")
                response = input().strip().lower()

                if response == 's':
                    print(f"🗑️  Eliminando índice existente...")
                    index_client.delete_index(INDEX_NAME)
                    print(f"✅ Índice eliminado")
                else:
                    print(f"⏭️  Manteniendo índice existente")
                    return
        except:
            # El índice no existe, continuar
            pass

        # Crear índice
        print(f"\n🔨 Creando índice...")
        result = index_client.create_index(index)

        print(f"\n✅ Índice creado exitosamente!")
        print(f"\n📊 Detalles del índice:")
        print(f"   Nombre: {result.name}")
        print(f"   Campos: {len(result.fields)}")
        print(f"   Vector dimensions: {EMBEDDING_DIMENSIONS}")
        print(f"   Spanish analyzer: {SPANISH_ANALYZER}")
        print(f"   Semantic config: {SEMANTIC_CONFIG}")
        print(f"   Vector profile: {VECTOR_PROFILE}")

        # Listar algunos campos importantes
        print(f"\n📝 Campos principales:")
        important_fields = [
            "id", "content", "content_vector", "titulo",
            "fecha_contrato", "proveedor", "cliente", "monto"
        ]
        for field_name in important_fields:
            field = next((f for f in result.fields if f.name == field_name), None)
            if field:
                print(f"   • {field.name} ({field.type})")

        print("\n" + "=" * 70)
        print("✅ Proceso completado")
        print("=" * 70)
        print(f"\n🎯 Siguiente paso:")
        print(f"   python scripts/search/2_extract_metadata.py")

    except Exception as e:
        print(f"\n❌ Error al crear índice: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create Azure AI Search index')
    parser.add_argument('--delete', action='store_true', help='Force delete existing index without prompting')

    args = parser.parse_args()

    create_search_index(force_delete=args.delete)
