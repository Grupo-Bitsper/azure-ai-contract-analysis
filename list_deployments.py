"""
Lista todos los deployments (modelos) disponibles en tu proyecto de Foundry
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

def list_deployments():
    """Lista todos los deployments disponibles"""

    print("="*60)
    print("🔍 Listando deployments en tu proyecto de Foundry")
    print("="*60)

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if not endpoint:
        print("❌ AZURE_AI_PROJECT_ENDPOINT no configurado")
        return

    try:
        credential = DefaultAzureCredential()
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )

        print("\n📋 Deployments disponibles:\n")

        deployments = list(client.deployments.list())

        if not deployments:
            print("⚠️  No hay deployments configurados aún")
            print("\n💡 Para usar Claude, necesitas:")
            print("   1. Ir a https://ai.azure.com")
            print("   2. Abrir tu proyecto")
            print("   3. Ir a 'Deployments' o 'Models'")
            print("   4. Desplegar Claude Sonnet 4.5 o Claude Opus 4.6")
            print("\n   O usar cualquier modelo GPT si ya tienes uno desplegado")
        else:
            print(f"Total: {len(deployments)} deployment(s)\n")

            for i, deployment in enumerate(deployments, 1):
                print(f"{i}. {deployment.name}")
                print(f"   Modelo: {deployment.model}")
                print(f"   Status: {deployment.provisioning_state}")
                if hasattr(deployment, 'sku'):
                    print(f"   SKU: {deployment.sku.name}")
                print()

        return deployments

    except Exception as e:
        print(f"❌ Error al listar deployments: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    list_deployments()
