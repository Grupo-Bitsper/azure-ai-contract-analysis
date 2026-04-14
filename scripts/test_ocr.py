"""
Script de prueba para Azure Document Intelligence
Procesa un PDF y extrae texto + metadata usando OCR
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def test_document_intelligence():
    """Prueba básica de Document Intelligence con un PDF"""

    print("="*60)
    print("🧪 Probando Azure Document Intelligence (OCR)")
    print("="*60)

    # Verificar configuración
    endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

    print(f"\n📋 Configuración:")
    print(f"   Endpoint: {endpoint if endpoint else '❌ NO configurado'}")
    print(f"   API Key: {'✅ Configurada' if key else '❌ NO configurada'}")

    if not endpoint or not key:
        print("\n❌ ERROR: Faltan credenciales en .env")
        print("\n💡 Sigue estos pasos:")
        print("   1. Ve a portal.azure.com")
        print("   2. Crea recurso 'Document Intelligence'")
        print("   3. Copia endpoint + key")
        print("   4. Agrégalos a .env")
        print("\n📄 Guía completa: docs/SETUP_DOCUMENT_INTELLIGENCE.md")
        return False

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        print("\n❌ ERROR: SDK no instalado")
        print("\n💡 Ejecuta:")
        print("   pip install azure-ai-documentintelligence")
        return False

    # Seleccionar PDF de prueba
    contratos_dir = Path("/Users/miguelordonez/Documents/contratosdemo")

    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        # Usar el primer PDF que encuentre
        pdfs = list(contratos_dir.glob("*.pdf"))
        if not pdfs:
            print(f"\n❌ No se encontraron PDFs en {contratos_dir}")
            return False
        pdf_path = pdfs[0]

    if not pdf_path.exists():
        print(f"\n❌ PDF no encontrado: {pdf_path}")
        return False

    print(f"\n📄 Procesando: {pdf_path.name}")
    print(f"   Tamaño: {pdf_path.stat().st_size / 1024:.1f} KB")

    try:
        # Crear cliente
        print("\n🔧 Creando cliente de Document Intelligence...")
        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        # Procesar documento
        print("📤 Enviando PDF para análisis...")
        print("   Modelo: prebuilt-contract (optimizado para contratos)")

        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-contract",
                body=f,
                content_type="application/octet-stream"
            )

        print("⏳ Procesando... (puede tomar 10-30 segundos)")
        result = poller.result()

        print(f"\n✅ Análisis completado")
        print(f"   Páginas procesadas: {len(result.pages)}")

        # Extraer texto completo
        texto_completo = []
        for page in result.pages:
            for line in page.lines:
                texto_completo.append(line.content)

        texto = "\n".join(texto_completo)

        print(f"\n📝 Texto extraído:")
        print("   " + "-"*56)
        # Mostrar primeras 20 líneas
        lineas = texto.split("\n")[:20]
        for linea in lineas:
            print(f"   {linea[:60]}...")
        if len(texto.split("\n")) > 20:
            print(f"   ... ({len(texto.split('\n')) - 20} líneas más)")
        print("   " + "-"*56)

        # Extraer campos estructurados
        print(f"\n🔍 Metadata extraída:")

        if result.documents:
            doc = result.documents[0]
            print(f"   Tipo de documento: {doc.doc_type}")
            print(f"   Confidence: {doc.confidence:.2%}")
            print(f"\n   Campos detectados:")

            campos_importantes = [
                "ContractDate",
                "ExpirationDate",
                "Parties",
                "TotalAmount",
                "Currency",
                "ContractType"
            ]

            for nombre in campos_importantes:
                if nombre in doc.fields:
                    campo = doc.fields[nombre]
                    valor = campo.content or campo.value_string or "N/A"
                    confidence = campo.confidence if hasattr(campo, 'confidence') and campo.confidence is not None else 0
                    print(f"      • {nombre}: {valor} (confidence: {confidence:.2%})")

            # Mostrar todos los campos encontrados
            print(f"\n   Total de campos encontrados: {len(doc.fields)}")
            otros_campos = [k for k in doc.fields.keys() if k not in campos_importantes]
            if otros_campos:
                print(f"   Otros campos: {', '.join(otros_campos[:10])}")

        else:
            print("   ⚠️  No se detectaron campos estructurados")
            print("   (El PDF puede ser muy diferente a un contrato estándar)")

        # Guardar resultado para inspección
        output_dir = Path("output/ocr_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{pdf_path.stem}_ocr.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Archivo: {pdf_path.name}\n")
            f.write(f"Páginas: {len(result.pages)}\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"TEXTO COMPLETO:\n")
            f.write(f"{'='*60}\n\n")
            f.write(texto)

            if result.documents:
                f.write(f"\n\n{'='*60}\n")
                f.write(f"METADATA:\n")
                f.write(f"{'='*60}\n\n")
                for nombre, campo in result.documents[0].fields.items():
                    valor = campo.content or campo.value_string or "N/A"
                    f.write(f"{nombre}: {valor}\n")

        print(f"\n💾 Resultado guardado en: {output_file}")

        print("\n" + "="*60)
        print("✅ Prueba exitosa - OCR funcionando correctamente")
        print("="*60)
        print("\n🎯 Siguiente paso:")
        print("   1. Revisa el archivo guardado para ver toda la metadata")
        print("   2. Procesa más contratos con:")
        print(f"      python scripts/process_all_contracts.py")

        return True

    except Exception as e:
        print(f"\n❌ Error al procesar PDF:")
        print(f"   {str(e)}")

        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n💡 La API key es incorrecta")
        elif "404" in str(e):
            print("\n💡 El endpoint es incorrecto")
        elif "quota" in str(e).lower():
            print("\n💡 Cuota excedida - verifica tu tier en Azure")

        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_document_intelligence()
