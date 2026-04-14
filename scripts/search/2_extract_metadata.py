"""
Extrae metadata estructurada de archivos OCR usando GPT-4o
Procesa todos los contratos en output/ocr_results/
"""
import sys
import json
from pathlib import Path
from typing import Dict, Optional

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.search.search_utils import get_openai_client, extract_ocr_text, get_ocr_filename


EXTRACTION_PROMPT_TEMPLATE = """Eres un experto en análisis de contratos legales mexicanos.

Tu tarea es extraer información estructurada del siguiente contrato.

IMPORTANTE:
- Si NO encuentras un campo, devuelve null
- Sé preciso con fechas y montos
- Usa formato de fecha: YYYY-MM-DD
- Para montos, solo el número (sin símbolos ni comas)

CONTRATO:
{ocr_text}

Extrae la información en el siguiente formato JSON exacto:
{{
    "titulo": "Título o descripción corta del contrato",
    "tipo_contrato": "Tipo (ej: Prestación de Servicios, Licencias, Compraventa, Fiscal)",
    "numero_contrato": "Número o identificador del contrato",
    "fecha_contrato": "YYYY-MM-DD o null",
    "fecha_vencimiento": "YYYY-MM-DD o null",
    "proveedor": "Nombre del proveedor/prestador (empresa que provee el servicio)",
    "cliente": "Nombre del cliente (empresa que recibe el servicio)",
    "monto": número sin comas ni símbolos o null,
    "moneda": "MXN, USD, EUR, etc. o null",
    "partes_firmantes": ["Lista de empresas/personas que firman el contrato"],
    "clausulas_principales": ["Lista de 3-5 cláusulas o temas principales del contrato"]
}}

Devuelve SOLO el JSON, sin texto adicional."""


def extract_metadata_from_text(ocr_text: str, filename: str) -> Optional[Dict]:
    """
    Extrae metadata de un texto usando GPT-4o

    Args:
        ocr_text: Texto del contrato extraído por OCR
        filename: Nombre del archivo para logging

    Returns:
        Dict con metadata extraída o None si falla
    """
    print(f"\n📄 Procesando: {filename}")

    # Truncar texto si es muy largo (GPT-4o tiene límite de contexto)
    max_chars = 50000  # ~12K tokens
    if len(ocr_text) > max_chars:
        print(f"   ⚠️  Texto muy largo ({len(ocr_text)} chars), truncando a {max_chars}")
        ocr_text = ocr_text[:max_chars] + "\n\n[... texto truncado ...]"

    try:
        client = get_openai_client()

        # Preparar prompt
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(ocr_text=ocr_text)

        # Llamar a GPT con JSON mode
        print(f"   🤖 Extrayendo metadata con GPT-5.4-mini...")
        response = client.chat.completions.create(
            model="gpt-5.4-mini",  # Usar el deployment disponible
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de contratos legales. Respondes SOLO con JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Baja temperatura para mayor precisión
            max_completion_tokens=1000,
            response_format={"type": "json_object"}  # Forzar respuesta JSON
        )

        # Parsear respuesta
        metadata_json = response.choices[0].message.content
        metadata = json.loads(metadata_json)

        # Validar que tenga los campos requeridos
        required_fields = ["titulo", "tipo_contrato", "proveedor", "cliente"]
        missing_fields = [f for f in required_fields if not metadata.get(f)]

        if missing_fields:
            print(f"   ⚠️  Faltan campos: {', '.join(missing_fields)}")

        # Mostrar resumen
        print(f"   ✅ Extraído:")
        print(f"      Título: {metadata.get('titulo', 'N/A')}")
        print(f"      Tipo: {metadata.get('tipo_contrato', 'N/A')}")
        print(f"      Proveedor: {metadata.get('proveedor', 'N/A')}")
        print(f"      Cliente: {metadata.get('cliente', 'N/A')}")
        if metadata.get('monto'):
            print(f"      Monto: ${metadata['monto']:,.2f} {metadata.get('moneda', '')}")
        if metadata.get('fecha_contrato'):
            print(f"      Fecha: {metadata['fecha_contrato']}")

        return metadata

    except json.JSONDecodeError as e:
        print(f"   ❌ Error al parsear JSON: {str(e)}")
        print(f"   Respuesta: {response.choices[0].message.content[:200]}...")
        return None
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def process_all_ocr_files(
    ocr_dir: str = "output/ocr_results",
    output_dir: str = "output/metadata"
):
    """
    Procesa todos los archivos OCR y extrae metadata

    Args:
        ocr_dir: Directorio con archivos OCR
        output_dir: Directorio para guardar metadata JSON
    """
    print("=" * 70)
    print("📊 Extrayendo metadata de contratos con GPT-4o")
    print("=" * 70)

    ocr_path = Path(ocr_dir)
    output_path = Path(output_dir)

    # Crear directorio de salida
    output_path.mkdir(parents=True, exist_ok=True)

    # Encontrar archivos OCR
    ocr_files = sorted(ocr_path.glob("*_ocr.txt"))

    if not ocr_files:
        print(f"\n❌ No se encontraron archivos OCR en {ocr_dir}")
        return

    print(f"\n📁 Encontrados: {len(ocr_files)} archivos OCR")
    print("-" * 70)

    # Procesar cada archivo
    results = []
    successful = 0
    failed = 0

    for idx, ocr_file in enumerate(ocr_files, 1):
        print(f"\n[{idx}/{len(ocr_files)}] {ocr_file.name}")

        try:
            # Extraer texto
            ocr_text = extract_ocr_text(str(ocr_file))
            original_filename = get_ocr_filename(str(ocr_file))

            # Extraer metadata
            metadata = extract_metadata_from_text(ocr_text, original_filename)

            if metadata:
                # Agregar metadata adicional
                metadata["nombre_archivo"] = original_filename
                metadata["ocr_file"] = ocr_file.name

                # Guardar a JSON
                output_file = output_path / f"{ocr_file.stem}_metadata.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                print(f"   💾 Guardado en: {output_file.name}")

                results.append({
                    "file": original_filename,
                    "status": "success",
                    "metadata": metadata
                })
                successful += 1
            else:
                results.append({
                    "file": original_filename,
                    "status": "failed",
                    "error": "No se pudo extraer metadata"
                })
                failed += 1

        except Exception as e:
            print(f"   ❌ Error procesando archivo: {str(e)}")
            results.append({
                "file": ocr_file.name,
                "status": "error",
                "error": str(e)
            })
            failed += 1

    # Guardar reporte completo
    report_file = output_path / "extraction_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_files": len(ocr_files),
            "successful": successful,
            "failed": failed,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    # Resumen final
    print("\n" + "=" * 70)
    print("📊 Reporte Final")
    print("=" * 70)
    print(f"\n✅ Exitosos: {successful}/{len(ocr_files)}")
    if failed > 0:
        print(f"❌ Fallidos: {failed}/{len(ocr_files)}")

    print(f"\n💾 Metadata guardada en: {output_dir}/")
    print(f"📄 Reporte completo: {report_file}")

    print("\n" + "=" * 70)
    print("✅ Proceso completado")
    print("=" * 70)
    print(f"\n🎯 Siguiente paso:")
    print(f"   python scripts/search/3_chunk_and_index.py")


if __name__ == "__main__":
    process_all_ocr_files()
