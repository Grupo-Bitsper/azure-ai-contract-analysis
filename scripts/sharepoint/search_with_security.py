"""
Ejemplo de búsqueda con Security Trimming
Filtra resultados basándose en permisos del usuario
"""
import os
import sys
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()


def get_user_groups_from_azure_ad(user_email: str) -> List[str]:
    """
    Obtiene los grupos del usuario desde Azure AD usando Microsoft Graph API

    Args:
        user_email: Email del usuario (ej: juan.perez@gruporocka.com)

    Returns:
        Lista de nombres de grupos a los que pertenece el usuario
    """
    import requests
    from azure.identity import ClientSecretCredential

    # Credenciales de Azure AD
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    # Obtener token de acceso
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

    token = credential.get_token("https://graph.microsoft.com/.default")

    # Headers para Graph API
    headers = {
        'Authorization': f'Bearer {token.token}',
        'Content-Type': 'application/json'
    }

    try:
        # Obtener grupos del usuario
        response = requests.get(
            f'https://graph.microsoft.com/v1.0/users/{user_email}/memberOf',
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print(f"⚠️  Error obteniendo grupos: {response.status_code}")
            return []

        groups_data = response.json().get('value', [])

        # Extraer nombres de grupos
        group_names = []
        for group in groups_data:
            if group.get('@odata.type') == '#microsoft.graph.group':
                group_names.append(group.get('displayName'))

        return group_names

    except Exception as e:
        print(f"❌ Error llamando Graph API: {str(e)}")
        return []


def search_contracts_with_security(
    query: str,
    user_email: str,
    top_k: int = 5
) -> List[Dict]:
    """
    Búsqueda de contratos con security trimming

    Args:
        query: Texto de búsqueda (ej: "vigencia del contrato")
        user_email: Email del usuario que hace la búsqueda
        top_k: Número de resultados a retornar

    Returns:
        Lista de chunks relevantes (filtrados por permisos)
    """
    from scripts.search.search_utils import get_search_client, generate_embedding

    print(f"\n🔍 Búsqueda con Security Trimming")
    print(f"   Query: {query}")
    print(f"   Usuario: {user_email}")

    # PASO 1: Obtener grupos del usuario
    print(f"\n   🔐 Obteniendo permisos del usuario...")
    user_groups = get_user_groups_from_azure_ad(user_email)

    # El usuario tiene acceso si su email O cualquiera de sus grupos están en acl_read
    allowed_identities = [user_email] + user_groups

    print(f"      Usuario pertenece a {len(user_groups)} grupos:")
    for group in user_groups:
        print(f"        • {group}")

    # PASO 2: Construir filtro de seguridad (OData syntax)
    # El filtro permite documentos donde acl_read contiene al menos UNA identidad del usuario
    security_filter_parts = [
        f"acl_read/any(acl: acl eq '{identity}')"
        for identity in allowed_identities
    ]
    security_filter = " or ".join(security_filter_parts)

    print(f"\n   🔒 Aplicando security filter...")
    print(f"      Identidades permitidas: {len(allowed_identities)}")

    # PASO 3: Generar embedding del query
    print(f"\n   🧮 Generando embedding del query...")
    query_vector = generate_embedding(query)

    # PASO 4: Búsqueda híbrida (vector + keyword) con security filter
    print(f"\n   🔎 Ejecutando búsqueda con filtros de seguridad...")
    search_client = get_search_client()

    try:
        results = search_client.search(
            search_text=query,
            vector_queries=[{
                "vector": query_vector,
                "k_nearest_neighbors": top_k * 2,  # Pedimos más porque el filtro reducirá resultados
                "fields": "content_vector"
            }],
            filter=security_filter,  # ← SECURITY TRIMMING
            select=[
                "id",
                "content",
                "titulo",
                "seccion_tipo",
                "seccion_nombre",
                "numero_clausula",
                "pagina_inicio",
                "sharepoint_url",
                "acl_read"  # Para debugging
            ],
            top=top_k
        )

        results_list = list(results)

        print(f"\n   ✅ Encontrados {len(results_list)} resultados (con permisos de acceso)")

        return results_list

    except Exception as e:
        print(f"\n   ❌ Error en búsqueda: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def search_without_security(query: str, top_k: int = 5) -> List[Dict]:
    """
    Búsqueda SIN security trimming (para comparación)

    ADVERTENCIA: Retorna TODOS los resultados sin filtrar por permisos
    """
    from scripts.search.search_utils import get_search_client, generate_embedding

    print(f"\n🔍 Búsqueda SIN Security Trimming (INSEGURA)")
    print(f"   Query: {query}")
    print(f"   ⚠️  Esta búsqueda NO respeta permisos de usuario")

    query_vector = generate_embedding(query)
    search_client = get_search_client()

    results = search_client.search(
        search_text=query,
        vector_queries=[{
            "vector": query_vector,
            "k_nearest_neighbors": top_k,
            "fields": "content_vector"
        }],
        # ❌ SIN FILTRO DE SEGURIDAD
        select=[
            "id",
            "content",
            "titulo",
            "seccion_nombre",
            "pagina_inicio",
            "sharepoint_url",
            "acl_read"
        ],
        top=top_k
    )

    results_list = list(results)
    print(f"\n   ⚠️  Encontrados {len(results_list)} resultados (SIN filtrar por permisos)")

    return results_list


def compare_secure_vs_insecure_search(query: str, user_email: str):
    """
    Comparación lado a lado de búsqueda segura vs insegura
    """
    print("="*70)
    print("🔐 COMPARACIÓN: Búsqueda Segura vs Insegura")
    print("="*70)

    # Búsqueda SEGURA (con security trimming)
    secure_results = search_contracts_with_security(query, user_email, top_k=5)

    print("\n" + "-"*70)

    # Búsqueda INSEGURA (sin security trimming)
    insecure_results = search_without_security(query, top_k=5)

    # Comparar resultados
    print("\n" + "="*70)
    print("📊 COMPARACIÓN DE RESULTADOS")
    print("="*70)

    print(f"\n🔒 Búsqueda SEGURA (con permisos):")
    print(f"   Resultados: {len(secure_results)}")
    for i, result in enumerate(secure_results, 1):
        print(f"\n   [{i}] {result.get('titulo', 'Sin título')}")
        print(f"       Sección: {result.get('seccion_nombre', 'N/A')}")
        print(f"       Página: {result.get('pagina_inicio', 'N/A')}")
        print(f"       ACLs: {', '.join(result.get('acl_read', [])[:3])}...")

    print(f"\n⚠️  Búsqueda INSEGURA (sin permisos):")
    print(f"   Resultados: {len(insecure_results)}")
    for i, result in enumerate(insecure_results, 1):
        print(f"\n   [{i}] {result.get('titulo', 'Sin título')}")
        print(f"       Sección: {result.get('seccion_nombre', 'N/A')}")
        print(f"       Página: {result.get('pagina_inicio', 'N/A')}")
        print(f"       ACLs: {', '.join(result.get('acl_read', [])[:3])}...")

    # Identificar documentos bloqueados por security trimming
    secure_ids = {r['id'] for r in secure_results}
    insecure_ids = {r['id'] for r in insecure_results}
    blocked_ids = insecure_ids - secure_ids

    if blocked_ids:
        print(f"\n🚫 Documentos BLOQUEADOS por security trimming: {len(blocked_ids)}")
        print(f"   El usuario NO tiene permisos para ver estos resultados")
    else:
        print(f"\n✅ El usuario tiene permisos para todos los resultados relevantes")


def main():
    """
    Demostración de búsqueda con security trimming
    """
    print("="*70)
    print("🔐 Demostración: Security Trimming en Azure AI Search")
    print("="*70)

    # Configuración de ejemplo
    QUERY = "vigencia del contrato"
    USER_EMAIL = "legal@gruporocka.com"  # Usuario de ejemplo

    print(f"\nEscenario:")
    print(f"  • Usuario: {USER_EMAIL}")
    print(f"  • Query: {QUERY}")

    # Opción 1: Búsqueda segura solamente
    print("\n\n" + "="*70)
    print("OPCIÓN 1: Búsqueda con Security Trimming")
    print("="*70)
    results = search_contracts_with_security(QUERY, USER_EMAIL, top_k=5)

    if results:
        print(f"\n📄 Top {len(results)} Resultados:")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.get('titulo', 'Sin título')}")
            print(f"    Sección: {result.get('seccion_tipo')} - {result.get('seccion_nombre')}")
            if result.get('numero_clausula'):
                print(f"    Cláusula: {result.get('numero_clausula')}")
            print(f"    Página: {result.get('pagina_inicio')}")
            print(f"    SharePoint: {result.get('sharepoint_url')}")
            print(f"    Permisos: {', '.join(result.get('acl_read', [])[:5])}")
            print(f"    Contenido: {result.get('content', '')[:200]}...")

    # Opción 2: Comparación segura vs insegura
    print("\n\n¿Deseas comparar búsqueda SEGURA vs INSEGURA? (s/n): ", end="")
    response = input().strip().lower()

    if response == 's':
        print("\n")
        compare_secure_vs_insecure_search(QUERY, USER_EMAIL)

    print("\n" + "="*70)
    print("✅ Demostración completada")
    print("="*70)


if __name__ == "__main__":
    # Validar que tenemos las credenciales necesarias
    required_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_KEY"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ ERROR: Faltan variables de entorno:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\nConfigura tu archivo .env")
        sys.exit(1)

    main()
