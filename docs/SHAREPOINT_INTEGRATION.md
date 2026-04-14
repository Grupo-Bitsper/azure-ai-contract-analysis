# SharePoint Integration - Arquitectura y Seguridad

Guía completa sobre cómo funciona el sistema actual y cómo se integra con SharePoint para empresas enterprise.

---

## 🏗️ Arquitectura Actual (Sin SharePoint)

### Flujo de Datos Actual

```
┌─────────────────────────────────────────────────────────────────┐
│  PASO 1: PDFs Locales                                           │
│  /Users/miguelordonez/Documents/contratosdemo/*.pdf             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 2: Azure Document Intelligence (OCR)                      │
│  - Procesa cada PDF página por página                           │
│  - Extrae texto con marcadores [Page N]                         │
│  - Detecta layout (párrafos, tablas, secciones)                 │
│  - Output: output/ocr_results/*.txt                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 3: Semantic Chunking                                      │
│  - Lee OCR con marcadores de página                             │
│  - Detecta secciones (DECLARACIONES, CLÁUSULAS, ANEXOS)         │
│  - Crea chunks de 1024 tokens con 50% overlap                   │
│  - Preserva estructura legal completa                           │
│  - Output: 228 chunks con metadata semántica                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 4: Embeddings (Azure OpenAI)                              │
│  - text-embedding-3-small (1536 dimensiones)                    │
│  - Convierte cada chunk en vector                               │
│  - Permite búsqueda semántica (no solo keywords)                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 5: Azure AI Search Index                                  │
│  contratos-rocka-index                                          │
│  - 228 documentos indexados                                     │
│  - 26 campos (content, content_vector, metadata)                │
│  - Vector search + Semantic ranking                             │
│  - Spanish analyzer                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 6: Azure OpenAI Agent (GPT-5.4-mini)                      │
│  - Query del usuario: "¿Cuál es la vigencia del contrato?"     │
│  - Búsqueda en índice (vector + semantic)                       │
│  - Retorna top 5 chunks más relevantes                          │
│  - GPT genera respuesta con citaciones                          │
│  - Output: "DIEZ MESES según Cláusula 16, página 9"            │
└─────────────────────────────────────────────────────────────────┘
```

### ⚠️ Limitación Actual: SEGURIDAD

**Problema**: El índice actual **NO tiene control de acceso por usuario**

```
┌─────────────────────────────────────────┐
│  Azure AI Search Index                  │
│  contratos-rocka-index                  │
│                                         │
│  ❌ Sin ACLs (Access Control Lists)    │
│  ❌ Sin row-level security              │
│  ❌ Todos ven todos los contratos       │
└─────────────────────────────────────────┘
```

**Escenario actual:**
- Usuario A pregunta: "¿Cuál es el precio del contrato con Betterware?"
- Usuario B pregunta: "¿Cuál es el precio del contrato con Betterware?"
- **Ambos obtienen la misma información** (aunque Usuario B no debería tener acceso)

**Esto funciona para:**
✅ Casos donde todos los usuarios tienen acceso a todos los contratos
✅ Equipos pequeños con confianza total
✅ Prototipos y POCs

**Esto NO funciona para:**
❌ Empresas con departamentos separados
❌ Contratos confidenciales por área
❌ Compliance (ISO, SOC2, GDPR)
❌ Multi-tenant scenarios

---

## 🔐 Seguridad en SharePoint

### Cómo Funciona SharePoint

SharePoint tiene **seguridad granular a nivel de documento**:

```
SharePoint Site: Grupo Rocka Contratos
├── Library: Contratos Legales
│   ├── 📄 Contrato_Betterware.pdf
│   │   ├── ✅ Puede leer: Legal Team, CFO, CEO
│   │   └── ❌ NO puede leer: HR Team, IT Team
│   ├── 📄 Contrato_Proveedor_IT.pdf
│   │   ├── ✅ Puede leer: IT Team, CFO, CEO
│   │   └── ❌ NO puede leer: Legal Team, HR Team
│   └── 📄 Contrato_Empleado_Juan.pdf
│       ├── ✅ Puede leer: HR Team, CEO, Juan
│       └── ❌ NO puede leer: Legal Team, IT Team
```

**Permisos heredados de Azure AD (Entra ID):**
- Usuario: juan.perez@gruporocka.com
- Grupos: Legal Team, Contratos Readers
- SharePoint verifica permisos en cada acceso

---

## 🏗️ Arquitectura con SharePoint (4 Opciones)

### Opción 1: Índice Centralizado SIN Seguridad (Actual)

**Arquitectura:**

```
SharePoint Online                Azure AI Search
┌──────────────────┐            ┌──────────────────┐
│ Contratos/       │            │ contratos-index  │
│  ├── Legal/      │  Sync      │                  │
│  ├── HR/         │  ═════>    │ ❌ Sin ACLs      │
│  └── IT/         │  Manual    │ ❌ Todos ven todo│
└──────────────────┘            └──────────────────┘
```

**Pros:**
✅ Simple de implementar (ya está hecho)
✅ Búsqueda rápida y potente
✅ Bajo costo

**Contras:**
❌ Sin control de acceso por usuario
❌ Violaciones de seguridad potenciales
❌ No cumple compliance enterprise

**Cuándo usar:**
- Equipos pequeños (5-10 personas)
- Todos tienen acceso a todo
- Contratos no confidenciales

---

### Opción 2: Azure AI Search con ACLs (Security Trimming) ⭐ RECOMENDADO

**Arquitectura:**

```
SharePoint Online
┌───────────────────────────────────────┐
│ Contrato_Betterware.pdf               │
│ Permisos: Legal, CFO                  │
└────────────┬──────────────────────────┘
             │
             ▼
      Microsoft Graph API
   (lee documento + permisos)
             │
             ▼
Azure AI Search Index
┌───────────────────────────────────────┐
│ Document ID: 001                       │
│ Content: "Contrato Betterware..."     │
│ Content_vector: [0.234, 0.891, ...]   │
│ acl_read: ["Legal", "CFO", "CEO"]     │  ← ACL FIELD
└────────────┬──────────────────────────┘
             │
             ▼
       Usuario hace query
┌───────────────────────────────────────┐
│ Usuario: juan.perez@gruporocka.com    │
│ Grupos: ["Legal", "Contratos Readers"]│
└────────────┬──────────────────────────┘
             │
             ▼
    Azure AI Search filtra resultados
┌───────────────────────────────────────┐
│ SELECT * FROM index                    │
│ WHERE content_vector MATCH query       │
│ AND acl_read OVERLAPS user.groups  ← Security Filter
└───────────────────────────────────────┘
```

**Flujo Completo:**

1. **Indexación (Sync desde SharePoint)**
   ```python
   # Para cada archivo en SharePoint
   file = graph_client.get("/sites/{site-id}/drive/items/{file-id}")
   permissions = graph_client.get(f"/sites/{site-id}/drive/items/{file-id}/permissions")

   # Extraer ACLs
   acl_read = []
   for permission in permissions:
       if permission.roles.contains("read"):
           acl_read.append(permission.grantedTo.user.email)
           # O grupo: permission.grantedTo.group.displayName

   # Indexar con ACLs
   document = {
       "id": file.id,
       "content": ocr_text,
       "content_vector": embedding,
       "acl_read": acl_read,  # ["Legal@gruporocka.com", "CFO@gruporocka.com"]
       "sharepoint_url": file.webUrl
   }
   ```

2. **Búsqueda (Con Security Filtering)**
   ```python
   # Usuario hace query
   user_email = "juan.perez@gruporocka.com"
   user_groups = get_user_groups(user_email)  # ["Legal", "Contratos Readers"]

   # Búsqueda con filtro de seguridad
   results = search_client.search(
       search_text="vigencia del contrato",
       filter=f"search.in(acl_read, '{user_email},{','.join(user_groups)}', ',')"
   )

   # Solo retorna documentos donde el usuario tiene permiso
   ```

**Schema del Índice Actualizado:**

```python
# Agregar campo ACL al schema existente
SearchField(
    name="acl_read",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    filterable=True,
    facetable=False,
),
SearchField(
    name="acl_write",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    filterable=True,
    facetable=False,
),
SearchField(
    name="sharepoint_permissions_hash",
    type=SearchFieldDataType.String,
    filterable=True,
),
```

**Pros:**
✅ Seguridad granular por usuario
✅ Hereda permisos de SharePoint
✅ Búsqueda potente (vector + semantic)
✅ Compatible con compliance
✅ Control total del índice

**Contras:**
❌ Implementación más compleja
❌ Sync de permisos necesario
❌ Costo de desarrollo ~20 horas

**Cuándo usar:**
- Empresas enterprise (50+ usuarios)
- Contratos confidenciales por área
- Compliance obligatorio
- Multi-departamento

---

### Opción 3: Microsoft Graph Connectors (Managed Service)

**Arquitectura:**

```
SharePoint Online
┌──────────────────┐
│ Contratos/       │
│  ├── Legal/      │
│  ├── HR/         │
│  └── IT/         │
└────────┬─────────┘
         │
         ▼
Microsoft Graph Connector
┌──────────────────────────────┐
│ - Auto-sync permisos          │
│ - ACLs heredadas automático   │
│ - Indexación incremental      │
└────────┬─────────────────────┘
         │
         ▼
Microsoft Search (M365)
┌──────────────────────────────┐
│ - Búsqueda nativa de M365     │
│ - Permisos automáticos        │
│ - NO soporta embeddings custom│
│ - NO semantic chunking custom │
└──────────────────────────────┘
```

**Pros:**
✅ Permisos automáticos (managed)
✅ No código de sync necesario
✅ Integración nativa M365

**Contras:**
❌ **NO soporta vector search custom**
❌ **NO soporta semantic chunking custom**
❌ **NO soporta Azure OpenAI embeddings**
❌ Búsqueda limitada (solo keywords)
❌ No control del ranking

**Cuándo usar:**
- Solo necesitas búsqueda básica (keywords)
- No necesitas RAG avanzado
- No necesitas semantic chunking
- **NO recomendado para este proyecto**

---

### Opción 4: Hybrid (SharePoint + Azure AI Search)

**Arquitectura:**

```
┌────────────────────────────────────────────────────────────┐
│  SharePoint Online (Source of Truth)                       │
│  - Contratos almacenados                                   │
│  - Permisos gestionados                                    │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
      Azure Logic App / Function
┌────────────────────────────────────────────────────────────┐
│  Trigger: Cuando archivo se crea/modifica en SharePoint    │
│  1. Descargar PDF desde SharePoint                         │
│  2. Leer permisos del archivo (Graph API)                  │
│  3. Enviar a Document Intelligence (OCR)                   │
│  4. Semantic chunking                                      │
│  5. Generar embeddings                                     │
│  6. Indexar en Azure AI Search con ACLs                    │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
    Azure AI Search (con ACLs)
┌────────────────────────────────────────────────────────────┐
│  - Vector search                                           │
│  - Semantic ranking                                        │
│  - Security trimming                                       │
│  - Spanish analyzer                                        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
    Azure OpenAI Agent (GPT-5.4-mini)
┌────────────────────────────────────────────────────────────┐
│  - Recibe query del usuario                                │
│  - Búsqueda con filtro de seguridad                        │
│  - Genera respuesta con citaciones                         │
│  - Retorna link a SharePoint original                      │
└────────────────────────────────────────────────────────────┘
```

**Pros:**
✅ Mejor de ambos mundos
✅ SharePoint = source of truth (permisos)
✅ Azure AI Search = potencia de búsqueda
✅ Sync automático

**Contras:**
❌ Más complejo de implementar
❌ Costo de Logic App/Functions

**Cuándo usar:**
- Proyectos enterprise grandes
- Necesitas mejor UX posible
- Presupuesto disponible

---

## 🔒 Seguridad: Comparación Detallada

### Escenario de Prueba

**SharePoint tiene:**
- Contrato A: Puede leer: Legal, CFO
- Contrato B: Puede leer: IT, CFO
- Contrato C: Puede leer: HR, CFO

**Usuarios:**
- Juan (Legal Team): debería ver solo A
- María (IT Team): debería ver solo B
- Carlos (CFO): debería ver A, B, C

### Opción 1: Sin ACLs (Actual)

```
Juan pregunta: "¿Cuánto cuesta el contrato?"
  → Índice retorna: A, B, C  ❌ PROBLEMA
  → Juan ve información de B y C (no debería)

María pregunta: "¿Cuánto cuesta el contrato?"
  → Índice retorna: A, B, C  ❌ PROBLEMA
  → María ve información de A y C (no debería)

Carlos pregunta: "¿Cuánto cuesta el contrato?"
  → Índice retorna: A, B, C  ✅ CORRECTO
```

### Opción 2: Con ACLs (Recomendado)

```python
# Índice tiene:
{
  "id": "A",
  "content": "Contrato A...",
  "acl_read": ["Legal@gruporocka.com", "CFO@gruporocka.com"]
},
{
  "id": "B",
  "content": "Contrato B...",
  "acl_read": ["IT@gruporocka.com", "CFO@gruporocka.com"]
},
{
  "id": "C",
  "content": "Contrato C...",
  "acl_read": ["HR@gruporocka.com", "CFO@gruporocka.com"]
}
```

```
Juan (Legal) pregunta: "¿Cuánto cuesta el contrato?"
  → Filter: acl_read contains "Legal@gruporocka.com"
  → Índice retorna: A  ✅ CORRECTO
  → Juan solo ve información de A

María (IT) pregunta: "¿Cuánto cuesta el contrato?"
  → Filter: acl_read contains "IT@gruporocka.com"
  → Índice retorna: B  ✅ CORRECTO
  → María solo ve información de B

Carlos (CFO) pregunta: "¿Cuánto cuesta el contrato?"
  → Filter: acl_read contains "CFO@gruporocka.com"
  → Índice retorna: A, B, C  ✅ CORRECTO
  → Carlos ve todo
```

---

## 💼 Recomendación para Grupo Rocka

### Fase 1: POC Actual (Ya completado ✅)
- Índice sin ACLs
- Equipo pequeño (Legal team)
- Validar funcionalidad del agente

### Fase 2: Implementar ACLs (Recomendado - 2 semanas)
- Agregar campo `acl_read` al índice
- Script de sync desde SharePoint
- Security filtering en queries

### Fase 3: Automatización (Futuro - 1 mes)
- Logic App para sync automático
- Webhook de SharePoint
- Re-indexación incremental

---

## 📋 Implementación Práctica: Opción 2 con ACLs

### Paso 1: Actualizar Schema del Índice

```python
# scripts/search/1_create_search_index.py

# Agregar campos de seguridad
SearchField(
    name="acl_read",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    filterable=True,
),
SearchField(
    name="acl_write",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    filterable=True,
),
SearchField(
    name="sharepoint_file_id",
    type=SearchFieldDataType.String,
    filterable=True,
),
```

### Paso 2: Script de Sync con SharePoint

```python
# scripts/sharepoint/sync_contracts.py

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
from azure.search.documents import SearchClient

def get_sharepoint_files_with_permissions(site_url, client_id, client_secret):
    """
    Obtiene archivos de SharePoint con sus permisos
    """
    # Conectar a SharePoint
    ctx = ClientContext(site_url).with_credentials(
        ClientCredential(client_id, client_secret)
    )

    # Obtener biblioteca de documentos
    library = ctx.web.lists.get_by_title("Contratos")
    items = library.items.get().execute_query()

    files_with_permissions = []

    for item in items:
        # Obtener archivo
        file = item.file.get().execute_query()

        # Obtener permisos
        role_assignments = item.role_assignments.get().execute_query()

        acl_read = []
        acl_write = []

        for role in role_assignments:
            member = role.member
            role_defs = role.role_definition_bindings.get().execute_query()

            for role_def in role_defs:
                if role_def.name in ["Read", "Contribute", "Full Control"]:
                    # Es un usuario
                    if hasattr(member, 'email'):
                        acl_read.append(member.email)
                    # Es un grupo
                    elif hasattr(member, 'title'):
                        acl_read.append(member.title)

                if role_def.name in ["Contribute", "Full Control"]:
                    if hasattr(member, 'email'):
                        acl_write.append(member.email)
                    elif hasattr(member, 'title'):
                        acl_write.append(member.title)

        files_with_permissions.append({
            'file': file,
            'acl_read': acl_read,
            'acl_write': acl_write,
            'sharepoint_file_id': item.id,
            'sharepoint_url': file.serverRelativeUrl
        })

    return files_with_permissions

def sync_to_search_index(files_with_permissions):
    """
    Sincroniza archivos con Azure AI Search incluyendo ACLs
    """
    from scripts.search.search_utils import get_search_client

    search_client = get_search_client()

    for file_info in files_with_permissions:
        file = file_info['file']

        # Descargar PDF
        file_content = file.get_content().execute_query()

        # OCR con Document Intelligence
        ocr_text = process_with_document_intelligence(file_content)

        # Semantic chunking
        chunks = semantic_chunker.chunk_text_semantic(ocr_text)

        # Indexar cada chunk con ACLs
        for i, chunk in enumerate(chunks):
            # Generar embedding
            embedding = generate_embedding(chunk['text'])

            # Crear documento con ACLs
            document = {
                'id': f"{file_info['sharepoint_file_id']}_{i}",
                'content': chunk['text'],
                'content_vector': embedding,
                'acl_read': file_info['acl_read'],  # ← ACLs de SharePoint
                'acl_write': file_info['acl_write'],
                'sharepoint_file_id': file_info['sharepoint_file_id'],
                'sharepoint_url': file_info['sharepoint_url'],
                # ... otros campos de metadata
            }

            search_client.upload_documents([document])
```

### Paso 3: Búsqueda con Security Filtering

```python
# agents/contratos_rocka/contratos_agent.py

def search_with_security(query: str, user_email: str) -> List[Dict]:
    """
    Búsqueda con filtro de seguridad basado en usuario
    """
    from scripts.search.search_utils import get_search_client
    import requests

    # Obtener grupos del usuario desde Azure AD
    user_groups = get_user_groups_from_azure_ad(user_email)

    # Construir lista de identidades permitidas
    allowed_identities = [user_email] + user_groups

    # Crear filtro OData para Azure Search
    # Busca documentos donde acl_read contenga al menos una identidad del usuario
    security_filter = " or ".join([
        f"acl_read/any(acl: acl eq '{identity}')"
        for identity in allowed_identities
    ])

    # Generar embedding del query
    query_vector = generate_embedding(query)

    # Búsqueda con filtro de seguridad
    search_client = get_search_client()
    results = search_client.search(
        search_text=query,
        vector_queries=[{
            "vector": query_vector,
            "k_nearest_neighbors": 5,
            "fields": "content_vector"
        }],
        filter=security_filter,  # ← Security trimming
        select=["id", "content", "sharepoint_url", "pagina_inicio"],
        top=5
    )

    return list(results)

def get_user_groups_from_azure_ad(user_email: str) -> List[str]:
    """
    Obtiene grupos del usuario desde Azure AD (Graph API)
    """
    import requests

    # Autenticación con Microsoft Graph
    token = get_graph_api_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # Obtener grupos del usuario
    response = requests.get(
        f'https://graph.microsoft.com/v1.0/users/{user_email}/memberOf',
        headers=headers
    )

    groups = response.json().get('value', [])

    return [group['displayName'] for group in groups]
```

### Paso 4: Automatización con Logic App

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "When_a_file_is_created_or_modified": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['sharepointonline']['connectionId']"
            }
          },
          "method": "get",
          "path": "/datasets/@{encodeURIComponent('https://gruporocka.sharepoint.com/sites/contratos')}/triggers/onupdatedfile",
          "queries": {
            "folderId": "Contratos"
          }
        }
      }
    },
    "actions": {
      "Get_file_content": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['sharepointonline']['connectionId']"
            }
          },
          "method": "get",
          "path": "/datasets/@{encodeURIComponent('https://gruporocka.sharepoint.com/sites/contratos')}/files/@{encodeURIComponent(triggerBody()?['{Identifier}'])}/content"
        }
      },
      "Call_Azure_Function_for_OCR_and_Indexing": {
        "type": "Function",
        "inputs": {
          "function": {
            "id": "/subscriptions/.../functions/ProcessContractFunction"
          },
          "body": {
            "fileContent": "@base64(body('Get_file_content'))",
            "fileName": "@triggerBody()?['{Name}']",
            "fileId": "@triggerBody()?['{Identifier}']",
            "siteUrl": "https://gruporocka.sharepoint.com/sites/contratos"
          }
        }
      }
    }
  }
}
```

---

## 💰 Costos de Implementación

### Opción 2: ACLs Manual Sync

| Componente | Esfuerzo | Costo Dev |
|------------|----------|-----------|
| Actualizar schema índice | 2 horas | $200 |
| Script sync SharePoint | 8 horas | $800 |
| Security filtering en queries | 4 horas | $400 |
| Testing y validación | 6 horas | $600 |
| **Total** | **20 horas** | **$2,000** |

**Costos operacionales:**
- Azure AI Search: $75/mes (sin cambio)
- Microsoft Graph API: Gratis (incluido en M365)
- **Total mensual: $75/mes**

### Opción 4: Hybrid con Logic App

| Componente | Esfuerzo | Costo Dev |
|------------|----------|-----------|
| Todo de Opción 2 | 20 horas | $2,000 |
| Logic App workflow | 8 horas | $800 |
| Azure Function (processing) | 8 horas | $800 |
| Testing extremo a extremo | 4 horas | $400 |
| **Total** | **40 horas** | **$4,000** |

**Costos operacionales:**
- Azure AI Search: $75/mes
- Logic App: ~$10/mes (1,000 ejecuciones)
- Azure Functions: ~$5/mes (Consumption plan)
- **Total mensual: $90/mes**

---

## 🎯 Recomendación Final

### Para Grupo Rocka

**Fase 1 (Ya hecho):** ✅
- POC sin ACLs
- Validar funcionalidad
- Equipo pequeño confiable

**Fase 2 (Próximo):** ⭐ **Opción 2 - Manual Sync con ACLs**
- Implementar ACLs en índice
- Script manual de sync
- Security filtering
- **Esfuerzo: 2 semanas, $2,000**

**Fase 3 (Futuro):** **Opción 4 - Automatización**
- Logic App para sync automático
- Webhook en SharePoint
- Zero-touch operation
- **Esfuerzo: 1 mes, $4,000**

---

## 📚 Recursos

**Microsoft Graph API:**
- https://learn.microsoft.com/graph/api/driveitem-list-permissions

**Azure AI Search Security:**
- https://learn.microsoft.com/azure/search/search-security-trimming-for-azure-search

**SharePoint SDK Python:**
- https://github.com/vgrem/Office365-REST-Python-Client

---

## ✅ Checklist de Seguridad

Antes de ir a producción con ACLs:

- [ ] Schema de índice incluye `acl_read` y `acl_write`
- [ ] Script de sync extrae permisos correctamente
- [ ] Security filtering funciona en queries
- [ ] Testing con múltiples usuarios
- [ ] Testing con múltiples grupos
- [ ] Manejo de usuarios sin permisos
- [ ] Logging de accesos
- [ ] Auditoría de queries
- [ ] Documentación para ops team
- [ ] Plan de rollback

---

<p align="center">
  <strong>📖 Documento creado para Grupo Rocka - Sistema de Contratos</strong>
</p>
