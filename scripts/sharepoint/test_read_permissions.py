"""
Prueba lectura de permisos (ACLs) de archivos en SharePoint
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


def test_read_permissions():
    """
    Lee y muestra permisos de archivos en SharePoint
    """
    print("="*70)
    print("🔐 Prueba: Lectura de Permisos (ACLs) en SharePoint")
    print("="*70)

    # Cargar credenciales
    site_url = os.getenv("SHAREPOINT_SITE_URL")
    client_id = os.getenv("SHAREPOINT_CLIENT_ID")
    client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
    library_name = os.getenv("SHAREPOINT_LIBRARY", "Contratos")

    if not all([site_url, client_id, client_secret]):
        print("\n❌ ERROR: Faltan credenciales en .env")
        return False

    print(f"\n📋 Configuración:")
    print(f"   Sitio: {site_url}")
    print(f"   Biblioteca: {library_name}")

    try:
        # Conectar a SharePoint
        print(f"\n🔗 Conectando a SharePoint...")
        credentials = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(credentials)

        # Obtener biblioteca
        print(f"📚 Obteniendo biblioteca '{library_name}'...")
        library = ctx.web.lists.get_by_title(library_name)
        items = library.items.get().execute_query()

        if len(items) == 0:
            print(f"\n⚠️  La biblioteca está vacía")
            print(f"\n💡 Sube algunos PDFs primero:")
            print(f"   python scripts/sharepoint/generar_pdfs_prueba.py")
            return False

        print(f"✅ Encontrados {len(items)} archivos\n")

        # Procesar cada archivo
        for idx, item in enumerate(items, 1):
            try:
                # Obtener archivo
                file = item.file.get().execute_query()
                file_name = file.properties['Name']

                print(f"{'='*70}")
                print(f"📄 [{idx}/{len(items)}] {file_name}")
                print(f"{'='*70}")

                # Obtener permisos del archivo
                role_assignments = item.role_assignments.get().execute_query()

                if len(role_assignments) == 0:
                    print(f"   ℹ️  Heredando permisos de carpeta padre")
                    continue

                print(f"\n🔐 Permisos configurados:")

                acl_read = set()
                acl_write = set()
                acl_full = set()

                for role in role_assignments:
                    # Obtener miembro (usuario o grupo)
                    member = role.member.get().execute_query()

                    # Obtener roles
                    role_defs = role.role_definition_bindings.get().execute_query()

                    # Identificar tipo de miembro
                    member_name = None
                    member_type = None

                    if hasattr(member, 'email') and member.email:
                        member_name = member.email
                        member_type = "👤 Usuario"
                    elif hasattr(member, 'title') and member.title:
                        member_name = member.title
                        member_type = "👥 Grupo"
                    else:
                        member_name = str(member.properties.get('Title', 'Unknown'))
                        member_type = "❓ Otro"

                    # Procesar cada rol
                    for role_def in role_defs:
                        role_name = role_def.properties['Name']

                        # Clasificar por tipo de permiso
                        if role_name in ["Read", "Limited Access"]:
                            acl_read.add(member_name)
                            print(f"\n   📖 READ: {member_type} {member_name}")
                            print(f"      Rol: {role_name}")

                        elif role_name in ["Contribute", "Edit"]:
                            acl_read.add(member_name)
                            acl_write.add(member_name)
                            print(f"\n   ✏️  WRITE: {member_type} {member_name}")
                            print(f"      Rol: {role_name}")

                        elif role_name == "Full Control":
                            acl_read.add(member_name)
                            acl_write.add(member_name)
                            acl_full.add(member_name)
                            print(f"\n   🔓 FULL CONTROL: {member_type} {member_name}")
                            print(f"      Rol: {role_name}")

                # Resumen de ACLs
                print(f"\n📊 Resumen de ACLs:")
                print(f"   Pueden VER (Read): {len(acl_read)}")
                if acl_read:
                    for identity in sorted(acl_read):
                        print(f"      • {identity}")

                print(f"\n   Pueden EDITAR (Write): {len(acl_write)}")
                if acl_write:
                    for identity in sorted(acl_write):
                        print(f"      • {identity}")

                print(f"\n   Control TOTAL (Full): {len(acl_full)}")
                if acl_full:
                    for identity in sorted(acl_full):
                        print(f"      • {identity}")

                # ACL para nuestro índice
                print(f"\n🔍 ACL para Azure AI Search:")
                acl_for_index = list(acl_read)
                print(f"   acl_read = {acl_for_index}")

                print()

            except Exception as e:
                print(f"   ❌ Error procesando archivo: {str(e)}")
                continue

        print(f"{'='*70}")
        print(f"✅ Prueba de permisos completada")
        print(f"{'='*70}")

        print(f"\n💡 Próximos pasos:")
        print(f"   1. Verifica que los permisos son correctos")
        print(f"   2. Ejecuta sync para copiar ACLs al índice:")
        print(f"      python scripts/sharepoint/sync_from_sharepoint.py")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_read_permissions()
    sys.exit(0 if success else 1)
