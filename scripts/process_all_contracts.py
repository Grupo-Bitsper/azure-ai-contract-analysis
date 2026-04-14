"""
Script para procesar TODOS los contratos con Azure Document Intelligence
Genera un reporte completo de resultados
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()


def process_all_contracts(contracts_dir: str):
    """Procesa todos los PDFs en el directorio especificado"""

    print("="*70)
    print("📚 Procesando TODOS los contratos con Document Intelligence")
    print("="*70)

    # Verificar configuración
    endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

    if not endpoint or not key:
        print("\n❌ ERROR: Faltan credenciales en .env")
        return False

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        print("\n❌ ERROR: SDK no instalado")
        print("   Ejecuta: pip install azure-ai-documentintelligence")
        return False

    # Crear cliente
    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )

    # Encontrar todos los PDFs
    contracts_path = Path(contracts_dir)
    pdfs = sorted(contracts_path.glob("*.pdf"))

    if not pdfs:
        print(f"\n❌ No se encontraron PDFs en {contracts_dir}")
        return False

    print(f"\n📄 Encontrados: {len(pdfs)} contratos")
    print("-"*70)

    # Resultados
    results = []
    total_pages = 0
    total_fields = 0

    # Procesar cada PDF
    for idx, pdf_path in enumerate(pdfs, 1):
        print(f"\n[{idx}/{len(pdfs)}] 📄 {pdf_path.name}")
        print(f"    Tamaño: {pdf_path.stat().st_size / 1024:.1f} KB")

        try:
            # Procesar documento
            with open(pdf_path, "rb") as f:
                poller = client.begin_analyze_document(
                    model_id="prebuilt-contract",
                    body=f,
                    content_type="application/octet-stream"
                )

            print("    ⏳ Procesando...")
            result = poller.result()

            # Extraer texto completo con marcadores de página
            texto_completo = []
            for page in result.pages:
                # Agregar marcador de página
                texto_completo.append(f"[Page {page.page_number}]")

                # Agregar contenido de la página
                for line in page.lines:
                    texto_completo.append(line.content)

            texto = "\n".join(texto_completo)

            # Extraer campos estructurados
            campos = {}
            doc_type = None
            confidence = 0

            if result.documents:
                doc = result.documents[0]
                doc_type = doc.doc_type
                confidence = doc.confidence if doc.confidence else 0

                for nombre, campo in doc.fields.items():
                    valor = campo.content or campo.value_string or ""
                    if valor:  # Solo guardar campos con valor
                        campos[nombre] = valor

            # Guardar resultado
            output_dir = Path("output/ocr_results")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{pdf_path.stem}_ocr.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Archivo: {pdf_path.name}\n")
                f.write(f"Páginas: {len(result.pages)}\n")
                f.write(f"Tipo: {doc_type}\n")
                f.write(f"Confidence: {confidence:.2%}\n")
                f.write(f"Campos detectados: {len(campos)}\n")
                f.write(f"\n{'='*60}\n")
                f.write(f"TEXTO COMPLETO:\n")
                f.write(f"{'='*60}\n\n")
                f.write(texto)

                if campos:
                    f.write(f"\n\n{'='*60}\n")
                    f.write(f"METADATA:\n")
                    f.write(f"{'='*60}\n\n")
                    for nombre, valor in campos.items():
                        f.write(f"{nombre}: {valor}\n")

            # Estadísticas
            total_pages += len(result.pages)
            total_fields += len(campos)

            results.append({
                "nombre": pdf_path.name,
                "paginas": len(result.pages),
                "tipo": doc_type,
                "confidence": confidence,
                "campos": len(campos),
                "campos_detectados": list(campos.keys()),
                "tamaño_kb": pdf_path.stat().st_size / 1024,
                "output": str(output_file)
            })

            print(f"    ✅ OK - {len(result.pages)} páginas, {len(campos)} campos")

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            results.append({
                "nombre": pdf_path.name,
                "error": str(e)
            })

    # Generar reporte final
    print("\n" + "="*70)
    print("📊 REPORTE FINAL")
    print("="*70)

    print(f"\n✅ Contratos procesados: {len([r for r in results if 'error' not in r])}/{len(pdfs)}")
    print(f"📄 Total de páginas procesadas: {total_pages}")
    print(f"🔍 Total de campos detectados: {total_fields}")

    print(f"\n📋 Detalle por contrato:\n")

    for r in results:
        if 'error' not in r:
            print(f"   • {r['nombre']}")
            print(f"     Páginas: {r['paginas']} | Campos: {r['campos']} | Confidence: {r['confidence']:.1%}")
            if r['campos'] > 0:
                print(f"     Campos: {', '.join(r['campos_detectados'][:5])}")
        else:
            print(f"   ❌ {r['nombre']}")
            print(f"     Error: {r['error']}")

    # Guardar reporte JSON
    report_file = Path("output/ocr_results/reporte_completo.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "fecha_proceso": datetime.now().isoformat(),
            "total_contratos": len(pdfs),
            "procesados_ok": len([r for r in results if 'error' not in r]),
            "total_paginas": total_pages,
            "total_campos": total_fields,
            "contratos": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados guardados en: output/ocr_results/")
    print(f"📄 Reporte JSON: {report_file}")

    print("\n" + "="*70)
    print("✅ Procesamiento completado")
    print("="*70)

    return True


if __name__ == "__main__":
    contracts_dir = "/Users/miguelordonez/Documents/contratosdemo"

    if len(sys.argv) > 1:
        contracts_dir = sys.argv[1]

    process_all_contracts(contracts_dir)
