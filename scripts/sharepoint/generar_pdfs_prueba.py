"""
Genera PDFs de prueba para simular contratos
Útil para testing sin datos reales
"""
import os
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
except ImportError:
    print("❌ reportlab no instalado")
    print("   Ejecuta: pip install reportlab")
    exit(1)


def crear_contrato_prueba(
    output_dir: str,
    nombre_archivo: str,
    tipo: str,
    proveedor: str,
    cliente: str,
    monto: str,
    vigencia: str
):
    """
    Crea un PDF de contrato de prueba con contenido realista

    Args:
        output_dir: Directorio de salida
        nombre_archivo: Nombre del archivo PDF
        tipo: Tipo de contrato (Servicios, Licencias, etc.)
        proveedor: Nombre del proveedor
        cliente: Nombre del cliente
        monto: Monto del contrato
        vigencia: Duración del contrato
    """
    output_path = Path(output_dir) / nombre_archivo
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 1*inch, f"CONTRATO DE {tipo.upper()}")

    # Fecha
    c.setFont("Helvetica", 10)
    fecha = datetime.now().strftime("%d de %B de %Y")
    c.drawCentredString(width/2, height - 1.3*inch, f"Fecha: {fecha}")

    # Línea separadora
    c.line(1*inch, height - 1.5*inch, width - 1*inch, height - 1.5*inch)

    # DECLARACIONES
    y = height - 2*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "DECLARACIONES")

    y -= 0.4*inch
    c.setFont("Helvetica", 11)

    c.drawString(1*inch, y, f"I. Declara el PROVEEDOR, {proveedor}, que:")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, "a) Es una sociedad legalmente constituida conforme a las leyes mexicanas")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "b) Cuenta con la capacidad técnica y recursos para prestar los servicios")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "c) Su representante legal tiene facultades suficientes")

    y -= 0.4*inch
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, y, f"II. Declara el CLIENTE, {cliente}, que:")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, "a) Es una sociedad legalmente constituida conforme a las leyes mexicanas")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "b) Requiere los servicios que el PROVEEDOR se compromete a prestar")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "c) Cuenta con los recursos necesarios para cumplir sus obligaciones")

    # Nueva página para CLÁUSULAS
    c.showPage()
    y = height - 1*inch

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "CLÁUSULAS")

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "PRIMERA - Objeto del Contrato")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    texto = f"El PROVEEDOR se obliga a proporcionar al CLIENTE servicios de {tipo.lower()}, "
    texto += "en los términos y condiciones establecidos en el presente contrato."
    c.drawString(1.3*inch, y, texto[:80])
    if len(texto) > 80:
        y -= 0.2*inch
        c.drawString(1.3*inch, y, texto[80:])

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "SEGUNDA - Precio")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, f"El precio total de los servicios es de {monto}, más IVA.")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "El pago se realizará en 3 parcialidades durante la vigencia del contrato.")

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "TERCERA - Vigencia")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, f"El presente contrato tendrá una vigencia de {vigencia},")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, f"contados a partir de la fecha de firma.")

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "CUARTA - Obligaciones del PROVEEDOR")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, "a) Prestar los servicios con la calidad y profesionalismo esperados")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "b) Mantener confidencialidad sobre la información del CLIENTE")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "c) Cumplir con los tiempos de entrega acordados")

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "QUINTA - Obligaciones del CLIENTE")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, "a) Realizar los pagos en tiempo y forma")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "b) Proporcionar la información necesaria para la prestación del servicio")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "c) Designar un responsable de coordinación")

    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "SEXTA - Propiedad Intelectual")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1.3*inch, y, "Los derechos de propiedad intelectual generados permanecerán")
    y -= 0.2*inch
    c.drawString(1.3*inch, y, "propiedad del PROVEEDOR, otorgando licencia de uso al CLIENTE.")

    # Firmas
    y = 2*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1.5*inch, y, proveedor)
    c.drawString(width - 3.5*inch, y, cliente)

    y -= 0.2*inch
    c.setFont("Helvetica", 9)
    c.drawString(1.5*inch, y, "PROVEEDOR")
    c.drawString(width - 3.5*inch, y, "CLIENTE")

    y -= 0.3*inch
    c.line(1.2*inch, y, 3.5*inch, y)
    c.line(width - 4*inch, y, width - 1.2*inch, y)

    c.save()

    return output_path


def generar_suite_contratos_prueba():
    """
    Genera una suite completa de contratos de prueba
    """
    print("="*70)
    print("📄 Generando PDFs de Prueba para SharePoint")
    print("="*70)

    output_dir = "output/contratos_prueba"

    contratos = [
        {
            "nombre": "Contrato_Legal_ABC.pdf",
            "tipo": "Servicios Legales",
            "proveedor": "Bufete Legal ABC, S.C.",
            "cliente": "Grupo Bitsper, S.A. de C.V.",
            "monto": "$150,000 MXN",
            "vigencia": "DOCE MESES"
        },
        {
            "nombre": "Contrato_IT_Software.pdf",
            "tipo": "Licencias de Software",
            "proveedor": "Microsoft Corporation",
            "cliente": "Grupo Bitsper, S.A. de C.V.",
            "monto": "$250,000 MXN",
            "vigencia": "DOCE MESES"
        },
        {
            "nombre": "Contrato_IT_Consultoria.pdf",
            "tipo": "Consultoría en TI",
            "proveedor": "Tech Solutions, S.A. de C.V.",
            "cliente": "Grupo Bitsper, S.A. de C.V.",
            "monto": "$500,000 MXN",
            "vigencia": "SEIS MESES"
        },
        {
            "nombre": "Contrato_HR_Empleado_Juan.pdf",
            "tipo": "Relación Laboral",
            "proveedor": "Grupo Bitsper, S.A. de C.V.",
            "cliente": "Juan Pérez López",
            "monto": "$25,000 MXN/mes",
            "vigencia": "INDEFINIDO"
        },
        {
            "nombre": "Contrato_HR_Empleado_Maria.pdf",
            "tipo": "Relación Laboral",
            "proveedor": "Grupo Bitsper, S.A. de C.V.",
            "cliente": "María González Sánchez",
            "monto": "$30,000 MXN/mes",
            "vigencia": "INDEFINIDO"
        },
        {
            "nombre": "Contrato_Finanzas_Credito.pdf",
            "tipo": "Crédito Empresarial",
            "proveedor": "Banco Nacional, S.A.",
            "cliente": "Grupo Bitsper, S.A. de C.V.",
            "monto": "$2,000,000 MXN",
            "vigencia": "VEINTICUATRO MESES"
        }
    ]

    print(f"\n📁 Directorio de salida: {output_dir}\n")

    for i, contrato in enumerate(contratos, 1):
        print(f"[{i}/{len(contratos)}] Generando: {contrato['nombre']}")

        output_path = crear_contrato_prueba(
            output_dir=output_dir,
            nombre_archivo=contrato['nombre'],
            tipo=contrato['tipo'],
            proveedor=contrato['proveedor'],
            cliente=contrato['cliente'],
            monto=contrato['monto'],
            vigencia=contrato['vigencia']
        )

        print(f"            ✅ Creado: {output_path}")
        print(f"            Tipo: {contrato['tipo']}")
        print(f"            Monto: {contrato['monto']}")
        print()

    print("="*70)
    print(f"✅ {len(contratos)} contratos de prueba generados")
    print("="*70)

    print(f"\n📋 Próximos pasos:")
    print(f"   1. Sube estos PDFs a SharePoint en carpetas separadas:")
    print(f"      • {output_dir}/Contrato_Legal_*.pdf → /Contratos/Legal/")
    print(f"      • {output_dir}/Contrato_IT_*.pdf → /Contratos/IT/")
    print(f"      • {output_dir}/Contrato_HR_*.pdf → /Contratos/HR/")
    print(f"      • {output_dir}/Contrato_Finanzas_*.pdf → /Contratos/Finanzas/")
    print(f"\n   2. Configura permisos en cada carpeta:")
    print(f"      • Legal/ → Legal Team, Executives")
    print(f"      • IT/ → IT Team, Executives")
    print(f"      • HR/ → HR Team, CEO")
    print(f"      • Finanzas/ → Finance Team, CFO")
    print(f"\n   3. Ejecuta el script de sync:")
    print(f"      python scripts/sharepoint/sync_from_sharepoint.py")


if __name__ == "__main__":
    generar_suite_contratos_prueba()
