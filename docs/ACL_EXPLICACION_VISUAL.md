# ¿Qué son los ACLs? - Explicación Visual

## 🎯 Definición Simple

**ACL = Access Control List = Lista de Control de Acceso**

Es una lista que dice **quién puede** ver/usar algo.

---

## 📝 Ejemplos del Mundo Real

### Ejemplo 1: Netflix 🎬

```
🏠 Cuenta de Netflix de la Familia Pérez

👤 Perfil "Papá"
   ACL: Puede ver TODO (incluyendo contenido para adultos)

👤 Perfil "Mamá"
   ACL: Puede ver TODO

👤 Perfil "Hijo (8 años)"
   ACL: Solo contenido infantil
   ❌ NO puede ver contenido +18
   ❌ NO puede ver terror
```

**Netflix guarda un ACL para cada perfil.**

### Ejemplo 2: WhatsApp Grupos 💬

```
Grupo: "Familia Pérez"
ACL (quién puede ver mensajes):
  ✅ Papá
  ✅ Mamá
  ✅ Hijos
  ❌ Primos (no están en el grupo)
  ❌ Amigos (no están en el grupo)

Grupo: "Trabajo - Proyecto X"
ACL (quién puede ver mensajes):
  ✅ Juan (Legal)
  ✅ María (IT)
  ✅ Carlos (PM)
  ❌ Pedro (no está en el proyecto)
```

**WhatsApp verifica el ACL antes de mostrar cada mensaje.**

### Ejemplo 3: Banco Online 🏦

```
Cuenta Bancaria #12345

ACL (quién puede ver saldo):
  ✅ Juan Pérez (titular)
  ✅ María López (cotitular)
  ❌ Pedro García (NO tiene acceso)
  ❌ Banco ejecutivo (solo si Juan autoriza)
```

---

## 💼 En el Mundo Enterprise: SharePoint

### SharePoint SIN ACLs explícitos (todos ven todo)

```
📁 Carpeta: Contratos

📄 Todos los PDFs están aquí
   ❌ No hay restricciones
   ❌ Cualquier empleado puede abrir cualquier contrato

   Juan (Legal) → Ve 100% de contratos ❌
   María (IT) → Ve 100% de contratos ❌
   Pedro (HR) → Ve 100% de contratos ❌

   Problema: Violaciones de confidencialidad
```

### SharePoint CON ACLs (permisos granulares)

```
📁 Carpeta: Contratos

📄 Contrato_Betterware.pdf
   ACL:
     ✅ Legal Team
     ✅ CFO
     ✅ CEO
     ❌ IT Team
     ❌ HR Team

📄 Contrato_Proveedor_Software.pdf
   ACL:
     ✅ IT Team
     ✅ CFO
     ❌ Legal Team
     ❌ HR Team

📄 Contrato_Empleado_Juan.pdf
   ACL:
     ✅ HR Team
     ✅ Juan Pérez (el empleado)
     ✅ CEO
     ❌ Legal Team
     ❌ IT Team
```

**Resultado:**
```
Juan (Legal) → Solo ve: Contrato_Betterware.pdf ✅
María (IT) → Solo ve: Contrato_Proveedor_Software.pdf ✅
Pedro (HR) → Solo ve: Contrato_Empleado_Juan.pdf ✅
Carlos (CFO) → Ve: Betterware + Software ✅
```

---

## 🤖 ACLs en tu Agente de Contratos

### Escenario Actual (SIN ACL)

```
┌─────────────────────────────────────────────────┐
│  Azure AI Search Index                          │
│  contratos-rocka-index                          │
│                                                 │
│  228 chunks indexados                           │
│  ❌ SIN ACLs                                    │
└─────────────────────────────────────────────────┘

Usuario: Juan (Legal)
Pregunta: "¿Cuál es el precio del contrato?"

Agente busca en índice:
  → Encuentra: Chunk 1 (Betterware)
  → Encuentra: Chunk 2 (Software IT)
  → Encuentra: Chunk 3 (Empleado)
  → Retorna TODOS los chunks ❌

Juan ve información de:
  ✅ Contratos legales (correcto)
  ❌ Contratos de IT (no debería ver)
  ❌ Contratos de empleados (no debería ver)
```

### Escenario Futuro (CON ACL)

```
┌─────────────────────────────────────────────────┐
│  Azure AI Search Index                          │
│  contratos-rocka-index                          │
│                                                 │
│  228 chunks indexados                           │
│  ✅ CON ACLs en cada chunk                     │
└─────────────────────────────────────────────────┘

Chunk 1 (Betterware):
{
  "content": "Precio: $2,000,000 MXN...",
  "acl_read": ["Legal", "CFO"]  ← ACL
}

Chunk 2 (Software IT):
{
  "content": "Precio: $500,000 MXN...",
  "acl_read": ["IT", "CFO"]  ← ACL
}

Chunk 3 (Empleado):
{
  "content": "Salario: $15,000 MXN...",
  "acl_read": ["HR", "CEO", "juan.perez@gruporocka.com"]  ← ACL
}

---

Usuario: Juan (Legal)
Pregunta: "¿Cuál es el precio?"

Sistema verifica:
  1. Juan pertenece a grupo: "Legal"
  2. Identidades permitidas: ["juan.perez@gruporocka.com", "Legal"]

Agente busca con filtro de seguridad:
  → Chunk 1: ¿"Legal" en acl_read? SÍ ✅ → Incluir
  → Chunk 2: ¿"Legal" en acl_read? NO ❌ → Excluir
  → Chunk 3: ¿"Legal" en acl_read? NO ❌ → Excluir

Juan solo ve:
  ✅ Chunk 1 (Betterware)
  ❌ Chunk 2 bloqueado
  ❌ Chunk 3 bloqueado
```

---

## 🔒 Tipos de ACLs

### ACL de LECTURA (Read)

```
Archivo: Contrato_Betterware.pdf
acl_read: ["Legal", "CFO", "CEO"]

Permite:
  ✅ Ver el documento
  ✅ Buscar dentro del documento
  ✅ Copiar texto
  ❌ NO permite editar
  ❌ NO permite eliminar
```

### ACL de ESCRITURA (Write)

```
Archivo: Contrato_Betterware.pdf
acl_write: ["Legal", "CEO"]

Permite:
  ✅ Editar el documento
  ✅ Modificar contenido
  ✅ Guardar cambios
  ❌ NO todos los que leen pueden escribir
```

### ACL de CONTROL TOTAL (Full Control)

```
Archivo: Contrato_Betterware.pdf
acl_full_control: ["CEO"]

Permite:
  ✅ Todo lo de Read
  ✅ Todo lo de Write
  ✅ Cambiar permisos (modificar el ACL)
  ✅ Eliminar archivo
```

---

## 📊 Comparación Detallada

### Sistema SIN ACL

| Aspecto | Comportamiento |
|---------|----------------|
| **Seguridad** | ❌ Todos ven todo |
| **Privacidad** | ❌ Sin control |
| **Compliance** | ❌ No cumple GDPR/ISO |
| **Auditoría** | ⚠️ Difícil rastrear quién vio qué |
| **Simplicidad** | ✅ Muy simple |
| **Costo** | ✅ Bajo ($0 extra) |

**Ejemplo:**
```
10 usuarios en la empresa
100 contratos en el sistema

Resultado:
  Cada usuario puede buscar y ver los 100 contratos
  No hay restricciones
```

### Sistema CON ACL

| Aspecto | Comportamiento |
|---------|----------------|
| **Seguridad** | ✅ Granular por documento |
| **Privacidad** | ✅ Solo ven lo permitido |
| **Compliance** | ✅ Cumple GDPR/ISO/SOC2 |
| **Auditoría** | ✅ Rastreo completo |
| **Simplicidad** | ⚠️ Más complejo |
| **Costo** | ⚠️ Desarrollo $2,000 |

**Ejemplo:**
```
10 usuarios en la empresa
100 contratos en el sistema

Resultado:
  Usuario Legal: Ve 30 contratos (solo legales)
  Usuario IT: Ve 20 contratos (solo IT)
  Usuario HR: Ve 40 contratos (solo HR)
  CFO: Ve 90 contratos (tiene más acceso)

  Total: Control granular
```

---

## 🎓 Caso de Estudio: Grupo Rocka

### Situación Actual

```
Grupo Rocka tiene:
  - 500 empleados
  - 1,000 contratos en SharePoint
  - Departamentos: Legal, IT, HR, Finanzas, Operaciones

❌ PROBLEMA SIN ACL:
  Cualquier empleado que acceda al agente puede:
    - Buscar "salarios" → Ve TODOS los salarios
    - Buscar "precio proveedor" → Ve TODOS los contratos
    - Buscar "cláusula confidencial" → Ve TODO

  Riesgos:
    - Empleado de IT ve salarios de HR
    - Vendedor ve precios de proveedores
    - Temporal ve contratos estratégicos
```

### Solución CON ACL

```
✅ IMPLEMENTAR ACLs:

Contratos Legales (200 contratos):
  acl_read: ["Legal Team", "CFO", "CEO"]
  → Solo 15 personas tienen acceso

Contratos IT (150 contratos):
  acl_read: ["IT Team", "CTO", "CFO"]
  → Solo 20 personas tienen acceso

Contratos HR (400 contratos):
  acl_read: ["HR Team", "CEO"]
  → Solo 5 personas tienen acceso

Contratos Finanzas (250 contratos):
  acl_read: ["Finance Team", "CFO", "CEO"]
  → Solo 10 personas tienen acceso

Resultado:
  - Cada empleado solo ve sus contratos relevantes
  - CFO y CEO tienen vista completa (por rol)
  - Compliance garantizado
  - Auditoría completa de accesos
```

---

## 🛠️ Implementación Técnica

### Paso 1: Extraer ACLs de SharePoint

```python
# Archivo en SharePoint
file = "Contrato_Betterware.pdf"

# Obtener permisos del archivo
permissions = sharepoint.get_file_permissions(file)

# Extraer ACL
acl_read = []
for permission in permissions:
    if permission.role == "Read" or "Contribute":
        if permission.user:
            acl_read.append(permission.user.email)
        if permission.group:
            acl_read.append(permission.group.name)

# Resultado:
acl_read = [
    "legal@gruporocka.com",
    "cfo@gruporocka.com",
    "Legal Team",
    "Executives"
]
```

### Paso 2: Indexar con ACL

```python
# Crear chunk con ACL
chunk = {
    "id": "001_chunk_0",
    "content": "CLÁUSULA PRIMERA - Objeto del contrato...",
    "content_vector": [0.234, 0.891, ...],
    "acl_read": [
        "legal@gruporocka.com",
        "cfo@gruporocka.com",
        "Legal Team"
    ]  ← ACL incluido en el índice
}

# Indexar
search_client.upload_documents([chunk])
```

### Paso 3: Buscar con Security Filter

```python
# Usuario hace búsqueda
user = "juan.perez@gruporocka.com"
user_groups = ["Legal Team", "Contratos Readers"]

# Construir filtro
allowed = [user] + user_groups
filter = " or ".join([
    f"acl_read/any(acl: acl eq '{identity}')"
    for identity in allowed
])

# Buscar con filtro de seguridad
results = search_client.search(
    search_text="objeto del contrato",
    filter=filter  ← Solo retorna chunks donde user tiene permiso
)
```

---

## ✅ Checklist de Seguridad con ACL

Antes de implementar ACLs, verifica:

- [ ] **Todos los archivos en SharePoint tienen permisos configurados**
  - Si un archivo no tiene permisos explícitos, hereda de la carpeta

- [ ] **Los grupos de Azure AD están bien definidos**
  - "Legal Team" incluye a todos los de legal
  - "CFO" es un grupo o usuario individual

- [ ] **El script de sync extrae ACLs correctamente**
  - Prueba con 1 archivo primero
  - Verifica que los emails/grupos sean correctos

- [ ] **El índice tiene campo `acl_read`**
  - Tipo: Collection(String)
  - Filterable: True

- [ ] **Las búsquedas aplican security filter**
  - Obtiene grupos del usuario desde Azure AD
  - Construye filtro OData correcto

- [ ] **Testing con múltiples usuarios**
  - Usuario A ve solo sus documentos
  - Usuario B ve solo sus documentos
  - Usuario con múltiples grupos ve más documentos

---

## 🎯 Resumen Ejecutivo

**¿Qué es un ACL?**
- Lista de quién puede ver/usar algo
- Como una lista de invitados en la puerta de una fiesta

**¿Por qué son importantes?**
- Protegen información confidencial
- Cumplen con regulaciones (GDPR, ISO, SOC2)
- Permiten auditoría completa
- Control granular (documento por documento)

**¿Cómo se implementan en tu agente?**
1. Extraer permisos de SharePoint
2. Agregar campo `acl_read` al índice
3. Aplicar security filter en búsquedas
4. Solo retornar resultados permitidos

**¿Cuánto cuesta implementarlo?**
- Desarrollo: $2,000 USD (2 semanas)
- Operación: $0 extra (mismo costo mensual)
- Valor: Seguridad enterprise garantizada

---

<p align="center">
  <strong>📖 ACLs explicados para Grupo Rocka</strong><br>
  Sistema de Análisis de Contratos con Azure AI
</p>
