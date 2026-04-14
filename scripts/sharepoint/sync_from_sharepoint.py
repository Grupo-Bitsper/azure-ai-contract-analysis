"""
Script para sincronizar contratos desde SharePoint a Azure AI Search
Incluye extracción de permisos (ACLs) para security trimming
"""
import os
import sys
from pathlib import Path
from typing import List, Dict
import json
from dotenv import load_dotenv

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

# SharePoint dependencies
try:
    from office365.sharepoint.client_context import ClientContext
    from office365.runtime.auth.client_credential import ClientCredential
except ImportError:
    print("❌ Office365-REST-Python-Client no instalado")
    print("   Ejecuta: pip install Office365-REST-Python-Client")
    sys.exit(1)


class SharePointContractSync:
    """
    Sincroniza contratos desde SharePoint a Azure AI Search
    con permisos (ACLs) para security trimming
    """

    def __init__(
        self,
        site_url: str,
        client_id: str,
        client_secret: str,
        library_name: str = "Contratos"
    ):
        """
        Args:
            site_url: URL del sitio de SharePoint (ej: https://gruporocka.sharepoint.com/sites/contratos)
            client_id: App ID registrada en Azure AD
            client_secret: Secret de la app
            library_name: Nombre de la biblioteca de documentos
        """
        self.site_url = site_url
        self.library_name = library_name

        # Conectar a SharePoint
        credentials = ClientCredential(client_id, client_secret)
        self.ctx = ClientContext(site_url).with_credentials(credentials)

    def get_contracts_with_permissions(self) -> List[Dict]:
        """
        Obtiene todos los contratos de SharePoint con sus permisos

        Returns:
            Lista de diccionarios con archivo, contenido y permisos
        """
        print(f"\n📂 Obteniendo contratos de SharePoint...")
        print(f"   Sitio: {self.site_url}")
        print(f"   Biblioteca: {self.library_name}")

        # Obtener biblioteca de documentos
        library = self.ctx.web.lists.get_by_title(self.library_name)
        items = library.items.get().execute_query()

        print(f"   Encontrados: {len(items)} archivos")

        contracts = []

        for item in items:
            try:
                # Obtener archivo
                file = item.file.get().execute_query()

                # Solo procesar PDFs
                if not file.name.lower().endswith('.pdf'):
                    print(f"   ⏭️  Omitiendo {file.name} (no es PDF)")
                    continue

                print(f"\n   📄 Procesando: {file.name}")

                # Obtener contenido del archivo
                file_content = file.get_content().execute_query()

                # Obtener permisos del archivo
                role_assignments = item.role_assignments.get().execute_query()

                acl_read = set()
                acl_write = set()

                for role in role_assignments:
                    member = role.member.get().execute_query()
                    role_defs = role.role_definition_bindings.get().execute_query()

                    for role_def in role_defs:
                        # Roles con permiso de lectura
                        if role_def.name in ["Read", "Contribute", "Edit", "Full Control"]:
                            # Usuario individual
                            if hasattr(member, 'email') and member.email:
                                acl_read.add(member.email)
                            # Grupo de SharePoint/Azure AD
                            elif hasattr(member, 'title') and member.title:
                                acl_read.add(member.title)

                        # Roles con permiso de escritura
                        if role_def.name in ["Contribute", "Edit", "Full Control"]:
                            if hasattr(member, 'email') and member.email:
                                acl_write.add(member.email)
                            elif hasattr(member, 'title') and member.title:
                                acl_write.add(member.title)

                print(f"      Permisos READ: {len(acl_read)} identidades")
                print(f"      Permisos WRITE: {len(acl_write)} identidades")

                contracts.append({
                    'file_name': file.name,
                    'file_content': file_content.value,
                    'sharepoint_file_id': str(item.id),
                    'sharepoint_url': file.serverRelativeUrl,
                    'sharepoint_web_url': file.linkingUrl,
                    'file_size': file.length,
                    'last_modified': str(file.time_last_modified),
                    'acl_read': list(acl_read),
                    'acl_write': list(acl_write),
                })

                print(f"      ✅ Archivo procesado")

            except Exception as e:
                print(f"      ❌ Error procesando archivo: {str(e)}")
                continue

        print(f"\n✅ Total de contratos obtenidos: {len(contracts)}")
        return contracts

    def process_and_index_contracts(self, contracts: List[Dict]):
        """
        Procesa contratos con OCR, chunking y los indexa en Azure AI Search

        Args:
            contracts: Lista de contratos obtenidos de SharePoint
        """
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
        from scripts.search.semantic_chunker import chunk_text_semantic
        from scripts.search.search_utils import get_search_client, generate_embedding
        import tiktoken

        print(f"\n🔧 Procesando {len(contracts)} contratos...")

        # Cliente de Document Intelligence
        doc_intel_client = DocumentIntelligenceClient(
            endpoint=os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_DOC_INTELLIGENCE_KEY"))
        )

        # Cliente de Azure AI Search
        search_client = get_search_client()

        # Tokenizer para contar tokens
        encoding = tiktoken.get_encoding("cl100k_base")
        def count_tokens(text: str) -> int:
            return len(encoding.encode(text))

        all_chunks_indexed = 0

        for idx, contract in enumerate(contracts, 1):
            print(f"\n[{idx}/{len(contracts)}] 📄 {contract['file_name']}")

            try:
                # PASO 1: OCR con Document Intelligence
                print("   ⏳ Ejecutando OCR...")
                poller = doc_intel_client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=contract['file_content'],
                    content_type="application/octet-stream"
                )
                result = poller.result()

                # Extraer texto con marcadores de página
                texto_completo = []
                for page in result.pages:
                    texto_completo.append(f"[Page {page.page_number}]")
                    for line in page.lines:
                        texto_completo.append(line.content)

                texto = "\n".join(texto_completo)
                print(f"      ✅ OCR completado: {len(result.pages)} páginas")

                # PASO 2: Semantic Chunking
                print("   ⏳ Aplicando semantic chunking...")
                chunks = chunk_text_semantic(
                    text=texto,
                    count_tokens_fn=count_tokens,
                    max_chunk_size=1024,
                    min_chunk_size=256
                )
                print(f"      ✅ Generados {len(chunks)} chunks semánticos")

                # PASO 3: Generar embeddings e indexar
                print("   ⏳ Generando embeddings e indexando...")
                documents_to_index = []

                for chunk_idx, chunk in enumerate(chunks):
                    # Generar embedding
                    embedding = generate_embedding(chunk['text'])

                    # Crear documento con ACLs
                    document = {
                        'id': f"{contract['sharepoint_file_id']}_{chunk_idx}",
                        'content': chunk['text'],
                        'content_vector': embedding,

                        # Metadata del contrato
                        'titulo': contract['file_name'].replace('.pdf', ''),
                        'nombre_archivo': contract['file_name'],
                        'sharepoint_url': contract['sharepoint_web_url'],
                        'sharepoint_file_id': contract['sharepoint_file_id'],

                        # Metadata semántica
                        'seccion_tipo': chunk.get('seccion_tipo'),
                        'seccion_nombre': chunk.get('seccion_nombre'),
                        'numero_clausula': chunk.get('numero_clausula'),
                        'pagina_inicio': chunk.get('pagina_inicio'),
                        'pagina_fin': chunk.get('pagina_fin'),
                        'chunking_mode': 'semantic',

                        # Security (ACLs)
                        'acl_read': contract['acl_read'],  # ← Permisos de SharePoint
                        'acl_write': contract['acl_write'],

                        # Tracking
                        'chunk_id': chunk_idx,
                        'total_chunks': len(chunks),
                    }

                    documents_to_index.append(document)

                # Indexar en batch
                result = search_client.upload_documents(documents_to_index)
                all_chunks_indexed += len(chunks)

                print(f"      ✅ Indexados {len(chunks)} chunks")

            except Exception as e:
                print(f"      ❌ Error procesando contrato: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n{'='*70}")
        print(f"✅ Sincronización completada")
        print(f"   Contratos procesados: {len(contracts)}")
        print(f"   Total chunks indexados: {all_chunks_indexed}")
        print(f"{'='*70}")


def main():
    """
    Función principal de sincronización
    """
    print("="*70)
    print("🔄 SharePoint → Azure AI Search Sync (con ACLs)")
    print("="*70)

    # Configuración de SharePoint
    SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
    SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
    SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
    SHAREPOINT_LIBRARY = os.getenv("SHAREPOINT_LIBRARY", "Contratos")

    # Validar configuración
    if not all([SHAREPOINT_SITE_URL, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET]):
        print("\n❌ ERROR: Faltan variables de entorno de SharePoint en .env")
        print("\nAgrega las siguientes variables a tu archivo .env:")
        print("SHAREPOINT_SITE_URL=https://gruporocka.sharepoint.com/sites/contratos")
        print("SHAREPOINT_CLIENT_ID=your-app-id")
        print("SHAREPOINT_CLIENT_SECRET=your-app-secret")
        print("SHAREPOINT_LIBRARY=Contratos")
        return False

    try:
        # Crear sincronizador
        syncer = SharePointContractSync(
            site_url=SHAREPOINT_SITE_URL,
            client_id=SHAREPOINT_CLIENT_ID,
            client_secret=SHAREPOINT_CLIENT_SECRET,
            library_name=SHAREPOINT_LIBRARY
        )

        # Obtener contratos con permisos
        contracts = syncer.get_contracts_with_permissions()

        if not contracts:
            print("\n⚠️  No se encontraron contratos en SharePoint")
            return False

        # Preguntar confirmación
        print(f"\n¿Deseas procesar e indexar estos {len(contracts)} contratos? (s/n): ", end="")
        response = input().strip().lower()

        if response != 's':
            print("❌ Operación cancelada")
            return False

        # Procesar e indexar
        syncer.process_and_index_contracts(contracts)

        return True

    except Exception as e:
        print(f"\n❌ Error en sincronización: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
