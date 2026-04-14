"""
Script de prueba para conectar a SharePoint y listar archivos
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

try:
    from office365.sharepoint.client_context import ClientContext
    from office365.runtime.auth.client_credential import ClientCredential
except ImportError:
    print("❌ Office365-REST-Python-Client no instalado")
    print("   Ejecuta: pip install Office365-REST-Python-Client")
    sys.exit(1)


def test_sharepoint_connection():
    """
    Prueba conexión a SharePoint y lista contenido
    """
    print("="*70)
    print("🔗 Prueba de Conexión a SharePoint")
    print("="*70)

    # Cargar credenciales
    site_url = os.getenv("SHAREPOINT_SITE_URL")
    client_id = os.getenv("SHAREPOINT_CLIENT_ID")
    client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
    library_name = os.getenv("SHAREPOINT_LIBRARY", "Contratos")

    # Validar configuración
    if not all([site_url, client_id, client_secret]):
        print("\n❌ ERROR: Faltan credenciales de SharePoint en .env")
        print("\nAgrega las siguientes variables:")
        print("SHAREPOINT_SITE_URL=https://tuempresa.sharepoint.com/sites/contratos")
        print("SHAREPOINT_CLIENT_ID=your-app-id")
        print("SHAREPOINT_CLIENT_SECRET=your-app-secret")
        print("SHAREPOINT_LIBRARY=Contratos")
        return False

    print(f"\n📋 Configuración:")
    print(f"   Sitio: {site_url}")
    print(f"   Biblioteca: {library_name}")

    try:
        print(f"\n🔐 Autenticando...")
        credentials = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(credentials)

        # Obtener información del sitio
        print(f"   ⏳ Cargando información del sitio...")
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()

        print(f"\n✅ Conexión exitosa!")
        print(f"   Título: {web.properties['Title']}")
        print(f"   URL: {web.properties['Url']}")
        print(f"   Descripción: {web.properties.get('Description', 'N/A')}")

        # Listar bibliotecas de documentos
        print(f"\n📚 Bibliotecas de documentos disponibles:")
        lists = ctx.web.lists
        ctx.load(lists)
        ctx.execute_query()

        doc_libraries = []
        for lst in lists:
            if lst.properties['BaseTemplate'] == 101:  # Document Library
                doc_libraries.append(lst.properties['Title'])
                print(f"   • {lst.properties['Title']}")

        if library_name not in doc_libraries:
            print(f"\n⚠️  ADVERTENCIA: Biblioteca '{library_name}' no encontrada")
            print(f"   Bibliotecas disponibles: {', '.join(doc_libraries)}")
            return False

        # Listar archivos en la biblioteca
        print(f"\n📄 Archivos en biblioteca '{library_name}':")
        try:
            library = ctx.web.lists.get_by_title(library_name)
            items = library.items.get().execute_query()

            if len(items) == 0:
                print(f"   (vacía - sin archivos)")
            else:
                for item in items:
                    file = item.file
                    ctx.load(file)
                    ctx.execute_query()

                    file_name = file.properties['Name']
                    file_size = file.properties['Length']
                    file_url = file.properties['ServerRelativeUrl']

                    print(f"\n   📎 {file_name}")
                    print(f"      Tamaño: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                    print(f"      Ruta: {file_url}")

        except Exception as e:
            print(f"   ❌ Error listando archivos: {str(e)}")
            return False

        print(f"\n{'='*70}")
        print(f"✅ Prueba de conexión completada")
        print(f"{'='*70}")

        return True

    except Exception as e:
        print(f"\n❌ Error de conexión: {str(e)}")
        print(f"\n💡 Posibles causas:")
        print(f"   1. Client ID o Secret incorrectos")
        print(f"   2. App no tiene permisos en SharePoint")
        print(f"   3. URL del sitio incorrecta")
        print(f"   4. Tenant ID incorrecto")

        print(f"\n🔧 Pasos para resolver:")
        print(f"   1. Verificar credenciales en .env")
        print(f"   2. Azure Portal → App registrations → Permisos API")
        print(f"   3. SharePoint → Sites.Read.All → Grant admin consent")

        import traceback
        print(f"\n📋 Error detallado:")
        traceback.print_exc()

        return False


if __name__ == "__main__":
    success = test_sharepoint_connection()
    sys.exit(0 if success else 1)
