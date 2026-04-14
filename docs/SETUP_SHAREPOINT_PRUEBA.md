# Setup: SharePoint de Prueba para Desarrollo

Guía completa para crear un entorno de prueba de SharePoint y validar el sistema de ACLs antes de conectar con el cliente real.

---

## 🎯 Objetivo

Crear un SharePoint de prueba donde puedas:
- ✅ Subir contratos de prueba
- ✅ Configurar permisos diferentes (ACLs)
- ✅ Desarrollar script de sync
- ✅ Validar búsquedas con security trimming
- ✅ Todo sin depender de acceso de Grupo Rocka

---

## 📋 Opciones de SharePoint de Prueba

### Opción 1: Microsoft 365 Trial (Recomendado) ⭐

**Características:**
- ✅ 30 días gratis (o $6/mes después)
- ✅ SharePoint completo
- ✅ Azure AD con grupos
- ✅ Todas las features enterprise

**Pasos:**
1. Ir a: https://www.microsoft.com/microsoft-365/business/compare-all-microsoft-365-business-products
2. Elegir "Microsoft 365 Business Basic" → Try free for 1 month
3. Crear cuenta: `miguelordonez@tuempresa.onmicrosoft.com`
4. Acceder a SharePoint Online

**Costo:**
- Primer mes: Gratis
- Después: $6 USD/usuario/mes (puedes cancelar antes)

---

### Opción 2: OneDrive Personal (Más Simple)

**Características:**
- ✅ Gratis (5GB) o $2/mes (100GB)
- ✅ Permisos individuales (no grupos)
- ✅ Más simple de configurar
- ⚠️ Sin Azure AD groups (solo emails)

**Pasos:**
1. Usar cuenta de Microsoft existente
2. Ir a: https://onedrive.live.com
3. Crear carpeta "Contratos"
4. Compartir archivos individualmente

**Limitación:**
- No puedes crear "grupos" (Legal Team, IT Team)
- Solo permisos por email individual

---

### Opción 3: SharePoint Developer Program (Mejor para Desarrollo) 🏆

**Características:**
- ✅ 90 días gratis (renovable)
- ✅ SharePoint + Azure AD completo
- ✅ Puedes crear grupos de usuarios
- ✅ Datos de prueba automáticos
- ✅ Perfecto para desarrollo

**Pasos:**
1. Ir a: https://developer.microsoft.com/microsoft-365/dev-program
2. Crear cuenta de desarrollador
3. Configura tenant instantáneo
4. Acceder a SharePoint

**Recomendación:** Esta es la mejor opción para ti 🎯

---

## 🚀 Setup Completo: Opción 3 (Developer Program)

### Paso 1: Crear cuenta de desarrollador

```bash
1. Ir a: https://developer.microsoft.com/microsoft-365/dev-program
2. Click: "Join now" (gratis)
3. Sign in con tu cuenta de Microsoft
4. Completar perfil de desarrollador

Información a llenar:
  - País: México
  - Empresa: Bitsper
  - Propósito: Development and testing
  - Área: Independent developer
```

### Paso 2: Crear tenant de prueba

```bash
1. Dashboard → "Set up E5 subscription"
2. Crear username: admin@tuempresa.onmicrosoft.com
   (Ejemplo: admin@bitsper-dev.onmicrosoft.com)
3. Contraseña: [Elige una segura]
4. Esperar ~2 minutos mientras se crea el tenant
```

### Paso 3: Acceder a SharePoint

```bash
1. Ir a: https://admin.microsoft.com
2. Login: admin@bitsper-dev.onmicrosoft.com
3. Left menu → "SharePoint" → "Active sites"
4. Click: "Create site" → "Team site"

Configuración del sitio:
  - Site name: Contratos
  - Site address: /sites/contratos
  - Language: Spanish
  - Privacy: Private
```

### Paso 4: Crear usuarios de prueba

Vamos a simular los departamentos de Grupo Rocka:

```bash
Microsoft 365 Admin Center → Users → Active users → Add user

Crear usuarios:

1. Juan Pérez (Legal)
   Email: juan.perez@bitsper-dev.onmicrosoft.com
   Password: [Auto-generate]
   Licenses: ✅ Microsoft 365 E5 Developer

2. María González (IT)
   Email: maria.gonzalez@bitsper-dev.onmicrosoft.com
   Password: [Auto-generate]
   Licenses: ✅ Microsoft 365 E5 Developer

3. Pedro Rodríguez (HR)
   Email: pedro.rodriguez@bitsper-dev.onmicrosoft.com
   Password: [Auto-generate]
   Licenses: ✅ Microsoft 365 E5 Developer

4. Carlos López (CFO)
   Email: carlos.lopez@bitsper-dev.onmicrosoft.com
   Password: [Auto-generate]
   Licenses: ✅ Microsoft 365 E5 Developer
```

### Paso 5: Crear grupos de Azure AD

```bash
Microsoft 365 Admin Center → Teams & groups → Active teams & groups

Crear grupos:

1. Legal Team
   Type: Security group
   Members: juan.perez@bitsper-dev.onmicrosoft.com

2. IT Team
   Type: Security group
   Members: maria.gonzalez@bitsper-dev.onmicrosoft.com

3. HR Team
   Type: Security group
   Members: pedro.rodriguez@bitsper-dev.onmicrosoft.com

4. Executives
   Type: Security group
   Members: carlos.lopez@bitsper-dev.onmicrosoft.com
```

### Paso 6: Crear estructura de carpetas en SharePoint

```bash
Ir a: https://bitsper-dev.sharepoint.com/sites/contratos

Crear carpetas:
  📁 Contratos/
    ├── 📁 Legal/
    ├── 📁 IT/
    ├── 📁 HR/
    └── 📁 Finanzas/
```

### Paso 7: Subir contratos de prueba

Necesitamos PDFs de prueba. Voy a darte 3 opciones:

**Opción A: Usar tus contratos reales (si no son confidenciales)**
```bash
Subir a /Contratos/Legal/:
  - Contrato_Betterware.pdf (el que ya procesaste)
```

**Opción B: Crear PDFs de prueba con Word**
```bash
1. Crear documento en Word:
   Título: "CONTRATO DE SERVICIOS LEGALES"
   Contenido: Lorem ipsum con cláusulas ficticias

2. Guardar como PDF
3. Subir a SharePoint
```

**Opción C: Generar PDFs de prueba con Python**
```python
# script para crear contratos de prueba
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def crear_contrato_prueba(nombre, tipo, monto):
    c = canvas.Canvas(f"{nombre}.pdf", pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"CONTRATO DE {tipo.upper()}")

    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "DECLARACIONES")
    c.drawString(100, 680, "I. El PROVEEDOR declara...")
    c.drawString(100, 660, "II. El CLIENTE declara...")

    c.drawString(100, 600, "CLÁUSULAS")
    c.drawString(100, 580, f"PRIMERA - Objeto: Servicios de {tipo}")
    c.drawString(100, 560, f"SEGUNDA - Precio: {monto}")
    c.drawString(100, 540, "TERCERA - Vigencia: 12 meses")

    c.save()

# Crear contratos de prueba
crear_contrato_prueba("Contrato_Legal_ABC", "Servicios Legales", "$50,000 MXN")
crear_contrato_prueba("Contrato_IT_Software", "Licencias de Software", "$100,000 MXN")
crear_contrato_prueba("Contrato_HR_Empleado", "Relación Laboral", "$25,000 MXN/mes")
```

### Paso 8: Configurar permisos por carpeta

```bash
En SharePoint:

📁 /Contratos/Legal/
  1. Click derecho → "Manage access"
  2. Click "Advanced"
  3. Click "Stop inheriting permissions"
  4. Remove: "Everyone"
  5. Add: "Legal Team" (Read)
  6. Add: "Executives" (Read)
  7. Click "OK"

📁 /Contratos/IT/
  1. Click derecho → "Manage access"
  2. Click "Advanced"
  3. Click "Stop inheriting permissions"
  4. Remove: "Everyone"
  5. Add: "IT Team" (Read)
  6. Add: "Executives" (Read)

📁 /Contratos/HR/
  1. Click derecho → "Manage access"
  2. Click "Advanced"
  3. Click "Stop inheriting permissions"
  4. Remove: "Everyone"
  5. Add: "HR Team" (Read)
  6. Add: "Executives" (Full Control)
```

---

## 🔑 Registrar App en Azure AD

Para que tu script pueda leer SharePoint, necesitas registrar una aplicación:

### Paso 1: Azure Portal

```bash
1. Ir a: https://portal.azure.com
2. Login con: admin@bitsper-dev.onmicrosoft.com
3. Buscar: "Azure Active Directory"
4. Click: "App registrations" → "New registration"

Configuración:
  - Name: ContratosSyncApp
  - Supported account types: "Single tenant"
  - Redirect URI: (dejar en blanco)
  - Click: "Register"
```

### Paso 2: Configurar permisos

```bash
En la app recién creada:

1. Left menu → "API permissions"
2. Click "Add a permission"
3. Select: "SharePoint"
4. Select: "Application permissions"
5. Check:
   ✅ Sites.Read.All
   ✅ Sites.FullControl.All
6. Click "Add permissions"
7. Click "Grant admin consent for [tenant]"
8. Click "Yes"
```

### Paso 3: Crear Client Secret

```bash
1. Left menu → "Certificates & secrets"
2. Click "New client secret"
3. Description: "Contratos Sync Secret"
4. Expires: 24 months
5. Click "Add"
6. ⚠️ COPIAR el "Value" inmediatamente (solo se muestra una vez)
```

### Paso 4: Obtener credenciales

```bash
Overview tab:
  - Application (client) ID: abc-123-def-456
  - Directory (tenant) ID: xyz-789-ghi-012

Certificates & secrets:
  - Client secret value: [El que copiaste]
```

---

## 🔧 Configurar .env local

Actualiza tu `.env` con las credenciales:

```env
# SharePoint de PRUEBA
SHAREPOINT_SITE_URL=https://bitsper-dev.sharepoint.com/sites/contratos
SHAREPOINT_CLIENT_ID=abc-123-def-456
SHAREPOINT_CLIENT_SECRET=tu-secret-aqui
SHAREPOINT_LIBRARY=Contratos

# Azure AD
AZURE_TENANT_ID=xyz-789-ghi-012
AZURE_CLIENT_ID=abc-123-def-456
AZURE_CLIENT_SECRET=tu-secret-aqui
```

---

## 🧪 Probar Conexión a SharePoint

Script de prueba rápida:

```python
# scripts/sharepoint/test_connection.py

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
import os
from dotenv import load_dotenv

load_dotenv()

def test_sharepoint_connection():
    """Prueba conexión a SharePoint de prueba"""

    site_url = os.getenv("SHAREPOINT_SITE_URL")
    client_id = os.getenv("SHAREPOINT_CLIENT_ID")
    client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")

    print(f"🔗 Conectando a SharePoint...")
    print(f"   Sitio: {site_url}")

    try:
        # Autenticar
        credentials = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(credentials)

        # Obtener información del sitio
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()

        print(f"✅ Conexión exitosa!")
        print(f"   Título del sitio: {web.properties['Title']}")
        print(f"   URL: {web.properties['Url']}")

        # Listar bibliotecas de documentos
        print(f"\n📚 Bibliotecas de documentos:")
        lists = ctx.web.lists
        ctx.load(lists)
        ctx.execute_query()

        for lst in lists:
            if lst.properties['BaseTemplate'] == 101:  # Document Library
                print(f"   • {lst.properties['Title']}")

        # Listar archivos en biblioteca "Contratos"
        library_name = os.getenv("SHAREPOINT_LIBRARY", "Contratos")
        print(f"\n📄 Archivos en '{library_name}':")

        library = ctx.web.lists.get_by_title(library_name)
        items = library.items.get().execute_query()

        for item in items:
            file = item.file
            ctx.load(file)
            ctx.execute_query()
            print(f"   • {file.properties['Name']} ({file.properties['Length']} bytes)")

        return True

    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_sharepoint_connection()
```

Ejecutar:
```bash
python scripts/sharepoint/test_connection.py
```

---

## 🧪 Escenarios de Prueba

### Escenario 1: Usuario Legal (Juan)

```bash
Usuario: juan.perez@bitsper-dev.onmicrosoft.com
Grupo: Legal Team

Debe ver:
  ✅ Archivos en /Contratos/Legal/
  ❌ Archivos en /Contratos/IT/
  ❌ Archivos en /Contratos/HR/
```

### Escenario 2: Usuario IT (María)

```bash
Usuario: maria.gonzalez@bitsper-dev.onmicrosoft.com
Grupo: IT Team

Debe ver:
  ❌ Archivos en /Contratos/Legal/
  ✅ Archivos en /Contratos/IT/
  ❌ Archivos en /Contratos/HR/
```

### Escenario 3: Ejecutivo (Carlos)

```bash
Usuario: carlos.lopez@bitsper-dev.onmicrosoft.com
Grupo: Executives

Debe ver:
  ✅ Archivos en /Contratos/Legal/
  ✅ Archivos en /Contratos/IT/
  ✅ Archivos en /Contratos/HR/
```

---

## ✅ Validación Completa

### Checklist de pruebas:

**1. Conexión básica**
```bash
- [ ] Script conecta a SharePoint
- [ ] Lista bibliotecas de documentos
- [ ] Lista archivos en biblioteca "Contratos"
```

**2. Lectura de permisos**
```bash
- [ ] Lee permisos de archivo en /Legal/
- [ ] Identifica "Legal Team" en ACL
- [ ] Identifica "Executives" en ACL
- [ ] NO incluye otros grupos
```

**3. Sync a Azure AI Search**
```bash
- [ ] Procesa PDF con Document Intelligence
- [ ] Aplica semantic chunking
- [ ] Indexa con acl_read heredado
- [ ] Verifica en índice que ACL está presente
```

**4. Búsqueda con security trimming**
```bash
- [ ] Usuario "juan.perez" solo ve chunks de Legal
- [ ] Usuario "maria.gonzalez" solo ve chunks de IT
- [ ] Usuario "carlos.lopez" ve chunks de todos
```

---

## 🎯 Plan de Desarrollo (2 semanas)

### Semana 1: Setup y Conexión

**Día 1-2: SharePoint de prueba**
- [ ] Crear tenant de Microsoft 365 Developer
- [ ] Crear usuarios de prueba (Juan, María, Pedro, Carlos)
- [ ] Crear grupos (Legal Team, IT Team, HR Team, Executives)
- [ ] Crear estructura de carpetas

**Día 3-4: Contenido de prueba**
- [ ] Generar o subir PDFs de prueba
- [ ] Configurar permisos en cada carpeta
- [ ] Validar acceso con cada usuario

**Día 5: Integración**
- [ ] Registrar App en Azure AD
- [ ] Configurar permisos de la app
- [ ] Probar script de conexión
- [ ] Listar archivos con permisos

### Semana 2: Sync y Validación

**Día 1-2: Script de sync**
- [ ] Implementar lectura de ACLs
- [ ] Procesar PDFs con Document Intelligence
- [ ] Indexar con ACLs heredados

**Día 3-4: Security trimming**
- [ ] Implementar búsqueda con filtros
- [ ] Obtener grupos de usuario desde Azure AD
- [ ] Validar filtrado correcto

**Día 5: Testing extremo a extremo**
- [ ] Simular 3 usuarios diferentes
- [ ] Cada uno busca la misma query
- [ ] Validar que ven resultados diferentes
- [ ] Documentar resultados

---

## 🔄 Migración a Grupo Rocka (Futuro)

Cuando tengas acceso a SharePoint de Grupo Rocka:

**Solo necesitas cambiar 3 variables:**

```env
# Antes (prueba):
SHAREPOINT_SITE_URL=https://bitsper-dev.sharepoint.com/sites/contratos
SHAREPOINT_CLIENT_ID=abc-123-def-456
SHAREPOINT_CLIENT_SECRET=tu-secret-prueba

# Después (producción):
SHAREPOINT_SITE_URL=https://gruporocka.sharepoint.com/sites/contratos
SHAREPOINT_CLIENT_ID=xyz-789-ghi-012
SHAREPOINT_CLIENT_SECRET=tu-secret-produccion
```

**El resto del código es IDÉNTICO** ✅

---

## 📚 Recursos

**Microsoft 365 Developer Program:**
https://developer.microsoft.com/microsoft-365/dev-program

**SharePoint REST API:**
https://learn.microsoft.com/sharepoint/dev/sp-add-ins/get-to-know-the-sharepoint-rest-service

**Office365-REST-Python-Client:**
https://github.com/vgrem/Office365-REST-Python-Client

**Azure AD App Registration:**
https://learn.microsoft.com/azure/active-directory/develop/quickstart-register-app

---

## 🆘 Troubleshooting

### Error: "Access denied"

```bash
Causa: La app no tiene permisos en SharePoint

Solución:
1. Azure Portal → App registrations → Tu app
2. API permissions → Add permission
3. SharePoint → Application permissions
4. Sites.Read.All ✅
5. Grant admin consent
```

### Error: "Tenant not found"

```bash
Causa: URL de SharePoint incorrecta

Solución:
Verificar formato:
  ✅ https://tuempresa.sharepoint.com/sites/contratos
  ❌ https://tuempresa.sharepoint.com/contratos
  ❌ https://sharepoint.com/sites/contratos
```

### Error: "Library not found"

```bash
Causa: Nombre de biblioteca incorrecto

Solución:
Verificar nombre exacto en SharePoint:
  - Puede ser "Documents" en inglés
  - O "Documentos" en español
  - O "Contratos" si lo creaste custom
```

---

## ✅ Siguiente Paso

Una vez que tengas el SharePoint de prueba configurado:

```bash
# 1. Probar conexión
python scripts/sharepoint/test_connection.py

# 2. Probar lectura de permisos
python scripts/sharepoint/test_read_permissions.py

# 3. Ejecutar sync completo
python scripts/sharepoint/sync_from_sharepoint.py

# 4. Probar búsqueda con security
python scripts/sharepoint/search_with_security.py
```

---

<p align="center">
  <strong>🧪 Entorno de Prueba Completo para SharePoint + ACLs</strong><br>
  Desarrolla y valida sin depender de acceso del cliente
</p>
