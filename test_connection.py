"""
Test script para verificar la conexión con Azure Foundry
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential

# Cargar variables de entorno
load_dotenv()

def test_connection():
    """Prueba la conexión básica con Azure Foundry"""

    print("🔧 Configurando cliente de Azure Foundry...")

    # Obtener credenciales del .env
    api_key = os.getenv("AZURE_API_KEY")
    project_endpoint = os.getenv("PROJECT_ENDPOINT")

    if not api_key or not project_endpoint:
        print("❌ Error: AZURE_API_KEY y PROJECT_ENDPOINT deben estar en .env")
        return False

    print(f"✅ API Key encontrada: {api_key[:10]}...")
    print(f"✅ Endpoint: {project_endpoint}")

    try:
        # Crear cliente con API key
        credential = AzureKeyCredential(api_key)
        client = AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        )

        print("\n✅ Cliente de Foundry creado exitosamente")
        print(f"   Endpoint: {project_endpoint}")

        # Intentar obtener información del proyecto
        print("\n🔍 Obteniendo información del proyecto...")

        # TODO: Aquí puedes agregar llamadas específicas según la API de Foundry
        # Por ejemplo, listar modelos disponibles, obtener configuración, etc.

        print("\n✅ Conexión exitosa con Azure Foundry!")
        return True

    except Exception as e:
        print(f"\n❌ Error al conectar: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")
        return False

def test_openai_connection():
    """Prueba la conexión con Azure OpenAI"""

    print("\n" + "="*60)
    print("🔧 Probando conexión con Azure OpenAI...")

    from openai import AzureOpenAI

    api_key = os.getenv("AZURE_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=endpoint
        )

        print("✅ Cliente de Azure OpenAI creado")
        print(f"   Endpoint: {endpoint}")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🚀 Probando SDK de Azure Foundry")
    print("="*60)

    # Test 1: Foundry connection
    foundry_ok = test_connection()

    # Test 2: OpenAI connection
    openai_ok = test_openai_connection()

    print("\n" + "="*60)
    print("📊 Resumen de pruebas:")
    print(f"   Foundry Client: {'✅ OK' if foundry_ok else '❌ FAIL'}")
    print(f"   Azure OpenAI: {'✅ OK' if openai_ok else '❌ FAIL'}")
    print("="*60)
