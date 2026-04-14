"""
Prueba funcionalidad de búsqueda en Azure AI Search
Verifica que el índice esté funcionando correctamente antes de crear el agente
"""
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.search_config import INDEX_NAME
from scripts.search.search_utils import get_search_client


TEST_QUERIES = [
    "¿Cuándo vence el contrato con Betterware?",
    "¿Quién es el proveedor de servicios?",
    "¿Cuál es el monto del contrato de Microsoft Dynamics?",
    "RFC de Betterware",
    "¿Qué contratos involucran a Jafra Cosmetics?",
]

# Phase 1 test queries - testing vigencia/duration
TEST_QUERIES_PHASE1 = [
    "vigencia del contrato con Betterware",
    "cuándo vence el contrato",
    "duración de las licencias de Dynamics 365",
    "cláusula décima sexta",
    "10 meses o 12 meses"
]


def test_search(query: str, top_k: int = 5):
    """
    Prueba una búsqueda en el índice

    Args:
        query: Query de búsqueda
        top_k: Número de resultados a retornar
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 Query: \"{query}\"")
    print(f"{'=' * 70}")

    try:
        client = get_search_client(INDEX_NAME)

        # Búsqueda híbrida (vector + keyword)
        results = client.search(
            search_text=query,
            select=["id", "content", "titulo", "proveedor", "cliente", "fecha_contrato", "monto", "numero_pagina"],
            top=top_k,
        )

        # Mostrar resultados
        found_results = False
        for idx, result in enumerate(results, 1):
            found_results = True
            score = result.get('@search.score', 0)

            print(f"\n📄 Resultado {idx} (score: {score:.2f})")
            print(f"   ID: {result.get('id', 'N/A')}")

            if result.get('titulo'):
                print(f"   Título: {result['titulo']}")

            if result.get('proveedor'):
                print(f"   Proveedor: {result['proveedor']}")

            if result.get('cliente'):
                print(f"   Cliente: {result['cliente']}")

            if result.get('fecha_contrato'):
                print(f"   Fecha: {result['fecha_contrato']}")

            if result.get('monto'):
                print(f"   Monto: ${result['monto']:,.2f}")

            if result.get('numero_pagina'):
                print(f"   Página: {result['numero_pagina']}")

            # Mostrar preview del contenido
            content = result.get('content', '')
            if content:
                preview = content[:200].replace('\n', ' ')
                print(f"   Contenido: {preview}...")

        if not found_results:
            print(f"\n⚠️  No se encontraron resultados")

    except Exception as e:
        print(f"\n❌ Error en búsqueda: {str(e)}")
        import traceback
        traceback.print_exc()


def run_test_suite():
    """Ejecuta suite completa de pruebas"""

    print("=" * 70)
    print("🧪 Suite de Pruebas - Azure AI Search")
    print("=" * 70)
    print(f"\nÍndice: {INDEX_NAME}")

    # Verificar que el índice existe
    try:
        client = get_search_client(INDEX_NAME)

        # Obtener estadísticas del índice
        print(f"\n📊 Verificando índice...")
        stats = client.get_document_count()
        print(f"   ✅ Documentos en el índice: {stats}")

        if stats == 0:
            print(f"\n❌ El índice está vacío")
            print(f"   Ejecuta primero: python scripts/search/3_chunk_and_index.py")
            return

    except Exception as e:
        print(f"\n❌ Error al conectar con el índice: {str(e)}")
        print(f"   Verifica que el índice existe con: python scripts/search/1_create_search_index.py")
        return

    # Ejecutar queries de prueba
    print(f"\n🔍 Ejecutando {len(TEST_QUERIES)} queries de prueba...")

    for idx, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'─' * 70}")
        print(f"Prueba {idx}/{len(TEST_QUERIES)}")
        test_search(query, top_k=3)

    # Resumen
    print(f"\n{'=' * 70}")
    print(f"✅ Suite de pruebas completada")
    print(f"{'=' * 70}")
    print(f"\n🎯 Si las búsquedas funcionan correctamente, puedes crear el agente:")
    print(f"   python agents/contratos_rocka/contratos_agent.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test Azure AI Search')
    parser.add_argument('--query', type=str, help='Single query to test')
    parser.add_argument('--phase1', action='store_true', help='Run Phase 1 vigencia tests')
    parser.add_argument('--verbose', action='store_true', help='Show full content')

    args = parser.parse_args()

    if args.query:
        # Single query test
        test_search(args.query, top_k=5)
    elif args.phase1:
        # Phase 1 test suite
        print("=" * 70)
        print("🧪 Phase 1 Test Suite - Vigencia/Duration Queries")
        print("=" * 70)
        print(f"\nÍndice: {INDEX_NAME}")

        try:
            client = get_search_client(INDEX_NAME)
            stats = client.get_document_count()
            print(f"📊 Documentos en el índice: {stats}\n")
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")

        for idx, query in enumerate(TEST_QUERIES_PHASE1, 1):
            print(f"\n{'─' * 70}")
            print(f"Prueba Phase 1 - {idx}/{len(TEST_QUERIES_PHASE1)}")
            test_search(query, top_k=3)

        print(f"\n{'=' * 70}")
        print("✅ Phase 1 tests completed")
        print("=" * 70)
    else:
        # Default: run standard test suite
        run_test_suite()
