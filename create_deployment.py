"""
Script para crear un deployment de GPT-4o-mini en Azure Foundry
Este modelo NO requiere registro y está disponible inmediatamente
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

def create_deployment():
    """Intenta crear un deployment de GPT-4o-mini"""

    print("="*60)
    print("🚀 Creando deployment de GPT-4o-mini")
    print("="*60)

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if not endpoint:
        print("❌ AZURE_AI_PROJECT_ENDPOINT no configurado")
        return False

    try:
        credential = DefaultAzureCredential()
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )

        print("\n📋 Modelos recomendados (sin registro):")
        print("   1. gpt-4o-mini (Recomendado)")
        print("   2. gpt-5-mini")
        print("   3. gpt-5-nano")
        print("   4. gpt-4o")
        print()

        # Intentar crear deployment
        deployment_name = "gpt-4o-mini"
        model_name = "gpt-4o-mini"

        print(f"🔧 Intentando crear deployment '{deployment_name}'...")
        print(f"   Modelo: {model_name}")
        print()

        # Nota: La API para crear deployments puede variar
        # Este es un ejemplo - puede necesitar ajustes según la API actual
        try:
            deployment = client.deployments.create(
                name=deployment_name,
                model=model_name,
                sku={
                    "name": "Standard",
                    "capacity": 10  # TPM en miles
                }
            )

            print("✅ Deployment creado exitosamente!")
            print(f"   Nombre: {deployment.name}")
            print(f"   Modelo: {deployment.model}")
            print(f"   Status: {deployment.provisioning_state}")

            return True

        except AttributeError as e:
            print("⚠️  La API de deployments puede no estar disponible en este SDK")
            print(f"   Error: {str(e)}")
            print()
            print("💡 Alternativa: Crear deployment manualmente en Azure Portal")
            print("   1. Ve a https://ai.azure.com")
            print("   2. Abre tu proyecto")
            print("   3. Ve a 'Deployments' → 'Create'")
            print("   4. Selecciona 'gpt-4o-mini'")
            print("   5. Deployment name: 'gpt-4o-mini'")
            print("   6. Click 'Deploy'")
            return False

        except Exception as e:
            print(f"❌ Error al crear deployment: {str(e)}")
            print()

            if "quota" in str(e).lower():
                print("💡 Problema de cuota detectado")
                print()
                print("   Solución 1: Solicitar cuota")
                print("   1. Ve a portal.azure.com → Quotas")
                print("   2. Busca 'Azure OpenAI'")
                print("   3. Solicita cuota para gpt-4o-mini (10K TPM)")
                print()
                print("   Solución 2: Usar modelo serverless")
                print("   1. Ve a ai.azure.com → Model Catalog")
                print("   2. Busca 'Llama 3.1' o 'Mistral'")
                print("   3. Deploy como serverless (sin cuota necesaria)")

            elif "region" in str(e).lower() or "capacity" in str(e).lower():
                print("💡 Problema de región/capacidad detectado")
                print()
                print("   Intenta en estas regiones:")
                print("   • Sweden Central")
                print("   • West US 3")
                print("   • East US")

            return False

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def list_available_models():
    """Lista modelos disponibles sin registro"""

    print("\n" + "="*60)
    print("📋 Modelos Disponibles SIN Registro/Aprobación")
    print("="*60)

    models = {
        "Recomendados para Chatbots": [
            "gpt-4o-mini (Mejor opción - rápido y económico)",
            "gpt-5-mini (Nuevo, potente)",
            "gpt-5-nano (Ultra económico)",
        ],
        "Premium (sin registro)": [
            "gpt-5 (Modelo completo GPT-5)",
            "gpt-4o (Vision + texto)",
            "o3-mini (Razonamiento avanzado)",
        ],
        "Open Source (vía Marketplace)": [
            "Llama 3.1 70B (Meta)",
            "Llama 3.1 8B (Meta - más rápido)",
            "Mistral Large (Mistral AI)",
            "Phi-4 (Microsoft)",
        ]
    }

    for category, model_list in models.items():
        print(f"\n{category}:")
        for model in model_list:
            print(f"  ✅ {model}")

    print("\n" + "="*60)
    print("❌ Evita estos (requieren registro):")
    print("="*60)
    print("  • GPT-5.4, GPT-5.4-pro")
    print("  • GPT-5.3-codex")
    print("  • O3, O3-pro (o3-mini SÍ está disponible)")
    print("  • GPT-image-1 (generación de imágenes)")
    print("  • Sora 2 (generación de videos)")
    print()

if __name__ == "__main__":
    list_available_models()

    print("\n" + "="*60)
    print("🎯 Acción Recomendada")
    print("="*60)
    print()
    print("Ve a https://ai.azure.com y crea manualmente:")
    print()
    print("  1. Abre tu proyecto: miguelaor681-2681")
    print("  2. Ve a 'Deployments' o 'Model deployments'")
    print("  3. Click 'Create deployment'")
    print("  4. Selecciona: gpt-4o-mini")
    print("  5. Deployment name: gpt-4o-mini")
    print("  6. Region: Sweden Central (si está disponible)")
    print("  7. Click 'Deploy'")
    print()
    print("⏱️  Tiempo estimado: 2-3 minutos")
    print()

    print("Después ejecuta:")
    print("  python list_deployments.py")
    print()
