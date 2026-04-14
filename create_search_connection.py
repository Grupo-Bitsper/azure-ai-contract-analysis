"""
Crea conexión de Azure AI Search en el proyecto de Foundry
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_KEY")

credential = DefaultAzureCredential()
project = AIProjectClient(endpoint=project_endpoint, credential=credential)

print("🔗 Creando conexión a Azure AI Search...")
print(f"   Endpoint: {search_endpoint}")

try:
    # Intentar crear la conexión
    connection = project.connections.create_or_update(
        connection_name="contratos-search",
        properties={
            "category": "CognitiveSearch",
            "target": search_endpoint,
            "authType": "ApiKey",
            "credentials": {
                "key": search_key
            },
            "isSharedToAll": True,
            "metadata": {
                "ApiVersion": "2023-11-01",
                "ApiType": "Azure",
                "ResourceId": f"/subscriptions/c64a5525-5e9a-46c3-a4f5-7ce393623fb2/resourceGroups/rg-miguelaor681-2681/providers/Microsoft.Search/searchServices/aisearchrgmiguelaor6812681c64a55"
            }
        }
    )
    
    print(f"✅ Conexión creada exitosamente!")
    print(f"   ID: {connection.id}")
    print(f"   Nombre: {connection.name}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\nIntentando método alternativo...")
    
    # Listar conexiones existentes
    print("\n📋 Conexiones existentes:")
    try:
        connections = project.connections.list()
        for conn in connections:
            print(f"   - {conn.id}: {conn.connection_type if hasattr(conn, 'connection_type') else 'N/A'}")
    except Exception as e2:
        print(f"   Error listando: {str(e2)}")
