"""
Test rápido del deployment de GPT-5.4-mini
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

def test_gpt54():
    """Prueba básica del modelo GPT-5.4-mini"""

    print("="*60)
    print("🧪 Probando GPT-5.4-mini")
    print("="*60)

    # Cargar configuración
    api_key = os.getenv("AZURE_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    print(f"\n📋 Configuración:")
    print(f"   Endpoint: {endpoint}")
    print(f"   Deployment: {deployment}")
    print(f"   API Version: {api_version}")
    print(f"   API Key: {'✅ Configurada' if api_key else '❌ Falta'}")

    if not api_key:
        print("\n❌ ERROR: AZURE_API_KEY no está configurada en .env")
        print("\n💡 Solución:")
        print("   1. Ve a Azure AI Studio")
        print("   2. Abre tu proyecto")
        print("   3. Ve a 'Modelos + puntos de conexión'")
        print("   4. Click en tu deployment 'gpt-5.4-mini'")
        print("   5. Copia la 'KEY 1'")
        print("   6. Pégala en .env en la línea AZURE_API_KEY=...")
        return False

    try:
        # Crear cliente
        print("\n🔧 Creando cliente...")
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )

        # Hacer una pregunta de prueba
        print("\n💬 Enviando mensaje de prueba...")
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente útil que responde en español."
                },
                {
                    "role": "user",
                    "content": "Hola, ¿puedes confirmar que estás funcionando? Responde en español."
                }
            ],
            max_completion_tokens=100,
            model=deployment
        )

        respuesta = response.choices[0].message.content

        print(f"\n🤖 Respuesta del modelo:")
        print(f"   {respuesta}")

        print("\n" + "="*60)
        print("✅ ¡GPT-5.4-mini funciona perfectamente!")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n❌ Error al probar el modelo:")
        print(f"   {str(e)}")

        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n💡 La API key es incorrecta o ha expirado")
            print("   Verifica que copiaste la key completa desde Azure Portal")

        elif "404" in str(e) or "DeploymentNotFound" in str(e):
            print("\n💡 El deployment no existe o el nombre es incorrecto")
            print(f"   Verifica que el deployment se llama exactamente: {deployment}")

        return False

if __name__ == "__main__":
    test_gpt54()
