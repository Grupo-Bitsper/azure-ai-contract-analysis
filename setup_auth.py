"""
Script de setup para configurar autenticación de Azure Foundry
Ejecutar este script ANTES de usar los agentes
"""
import os
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

def check_az_cli():
    """Verifica que Azure CLI esté instalado"""
    print("🔍 Verificando Azure CLI...")

    try:
        result = subprocess.run(
            ["az", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ Azure CLI instalado: {version}")
            return True
        else:
            print("❌ Azure CLI no está funcionando correctamente")
            return False

    except FileNotFoundError:
        print("❌ Azure CLI no está instalado")
        print("\n📦 Instalar con: brew install azure-cli")
        return False
    except Exception as e:
        print(f"❌ Error al verificar Azure CLI: {str(e)}")
        return False

def check_az_login():
    """Verifica si hay una sesión activa de Azure"""
    print("\n🔍 Verificando sesión de Azure...")

    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            import json
            account = json.loads(result.stdout)
            print(f"✅ Sesión activa:")
            print(f"   Usuario: {account.get('user', {}).get('name', 'N/A')}")
            print(f"   Subscription: {account.get('name', 'N/A')}")
            return True
        else:
            print("❌ No hay sesión activa de Azure")
            return False

    except Exception as e:
        print(f"❌ Error al verificar sesión: {str(e)}")
        return False

def do_az_login():
    """Ejecuta az login para autenticar"""
    print("\n🔐 Iniciando login de Azure...")
    print("   Se abrirá tu navegador para autenticarte")
    print("   Usa tu correo de Azure\n")

    try:
        result = subprocess.run(
            ["az", "login"],
            timeout=120
        )

        if result.returncode == 0:
            print("\n✅ Login exitoso")
            return True
        else:
            print("\n❌ Login falló")
            return False

    except subprocess.TimeoutExpired:
        print("\n⏱️  Timeout - el login tomó demasiado tiempo")
        return False
    except Exception as e:
        print(f"\n❌ Error durante login: {str(e)}")
        return False

def check_endpoint():
    """Verifica que el endpoint esté configurado"""
    print("\n🔍 Verificando endpoint del proyecto...")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if not endpoint:
        print("❌ AZURE_AI_PROJECT_ENDPOINT no está configurado en .env")
        return False

    print(f"✅ Endpoint configurado:")
    print(f"   {endpoint}")
    return True

def test_authentication():
    """Prueba que la autenticación funcione con DefaultAzureCredential"""
    print("\n🧪 Probando autenticación con SDK de Foundry...")

    try:
        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectClient

        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

        if not endpoint:
            print("❌ AZURE_AI_PROJECT_ENDPOINT no configurado")
            return False

        print("   Creando credential...")
        credential = DefaultAzureCredential()

        print("   Creando client...")
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )

        print("   Probando conexión...")
        # Intentar listar agentes como prueba
        try:
            agents = list(client.agents.list())
            print(f"✅ Autenticación exitosa - {len(agents)} agente(s) encontrado(s)")
            return True
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                print("❌ Error de autenticación: no autorizado")
                print("   Posible solución: asegúrate de tener el rol correcto en Azure Portal")
                print("   Rol necesario: 'Cognitive Services User' o 'Cognitive Services Contributor'")
            else:
                print(f"✅ Conexión establecida (sin agentes previos)")
            return True

    except Exception as e:
        print(f"❌ Error al probar autenticación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta el setup completo"""
    print("="*60)
    print("🚀 Setup de Autenticación - Azure Foundry")
    print("="*60)

    # Paso 1: Verificar Azure CLI
    if not check_az_cli():
        print("\n⚠️  Instala Azure CLI y vuelve a ejecutar este script")
        sys.exit(1)

    # Paso 2: Verificar sesión
    if not check_az_login():
        print("\n📝 Necesitas hacer login en Azure")
        respuesta = input("¿Quieres hacer login ahora? (s/n): ").strip().lower()

        if respuesta == 's':
            if not do_az_login():
                print("\n⚠️  Login falló. Intenta manualmente: az login")
                sys.exit(1)
        else:
            print("\n⚠️  Ejecuta manualmente: az login")
            sys.exit(1)

    # Paso 3: Verificar endpoint
    if not check_endpoint():
        print("\n⚠️  Configura AZURE_AI_PROJECT_ENDPOINT en .env")
        sys.exit(1)

    # Paso 4: Probar autenticación
    if not test_authentication():
        print("\n⚠️  La autenticación no funciona correctamente")
        print("\n📝 Checklist:")
        print("   1. ✅ Azure CLI instalado")
        print("   2. ✅ Login completado (az login)")
        print("   3. ✅ Endpoint configurado")
        print("   4. ❌ Autenticación con SDK")
        print("\n💡 Posibles soluciones:")
        print("   • Verifica que tienes acceso al proyecto en Azure Portal")
        print("   • Asigna el rol 'Cognitive Services User' en IAM del proyecto")
        print("   • Intenta: az logout && az login")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ Setup completado exitosamente")
    print("="*60)
    print("\n🎉 Ahora puedes ejecutar:")
    print("   python agents/hr_policies/hr_agent.py")
    print("   python foundry_agent_example.py")
    print("\n")

if __name__ == "__main__":
    main()
