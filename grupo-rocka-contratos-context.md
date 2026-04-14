# Proyecto: Agente de Contratos — Grupo Rocka
# Builder: Miguel (Grupo Bitsper) + Socio

---

## Contexto del proyecto

### ¿Qué es Grupo Rocka?
- Cliente enterprise de mi papá (Microsoft Partner)
- Ya tienen implementado Microsoft 365 + SharePoint
- Tienen contratos almacenados en SharePoint como PDFs

### El problema actual
- Tienen un agente en **Copilot Studio** que NO funciona bien
- El MCP de SharePoint les regresa el PDF pero no puede leer el contenido
- Los PDFs son **escaneados** (imágenes, no texto) — nadie les hizo OCR
- No pueden comparar contratos ni saber cuál es más reciente
- La fecha de upload de SharePoint NO es confiable — la fecha real está dentro del documento
- Los consultores de mi papá están atorados — no han podido resolverlo

### Lo que queremos construir nosotros
Un agente en **Microsoft Foundry** (pro-code) que resuelva lo que Copilot Studio no pudo:
- Leer PDFs escaneados correctamente
- Extraer metadata real del contenido (fecha, proveedor, monto, vencimiento)
- Responder preguntas sobre contratos específicos
- Comparar contratos entre sí
- Buscar cláusulas y términos específicos
- Saber cuál contrato es más reciente basado en la fecha DENTRO del documento

### Usuarios del agente
- Equipo legal / administrativo de Grupo Rocka
- Preguntas típicas:
  - "¿Cuándo vence el contrato con Proveedor X?"
  - "¿Cuáles son las cláusulas de penalización del contrato Y?"
  - "Compara el contrato 2023 vs 2024 con proveedor Z"
  - "¿Qué contratos vencen en los próximos 3 meses?"

---

## Por qué fallaron con Copilot Studio

```
Copilot Studio usa MCP de SharePoint
        ↓
MCP descarga el PDF
        ↓
PDF escaneado = imagen JPG dentro de PDF
        ↓
No hay texto que leer
        ↓
Agente no puede responder nada útil
```

Copilot Studio no permite meter un paso de OCR en el pipeline — 
no tienen control sobre la ingesta. Ese es el bloqueante real.

---

## Nuestra solución — Stack técnico

### Herramientas principales
```
Azure Document Intelligence  → OCR de PDFs escaneados
Azure AI Search              → Índice vectorial de contratos
Claude Sonnet 4.6 en Foundry → LLM del agente (1M contexto)
Microsoft Foundry            → Plataforma del agente
Azure Logic Apps             → Automatización para contratos nuevos
SharePoint                   → Fuente de los PDFs
```

### Por qué Claude Sonnet 4.6
- Contexto de 1M tokens — puede leer contratos completos sin chunking agresivo
- Excelente en análisis de documentos legales
- Ya disponible en Foundry (East US 2, Sweden Central)
- Ya conocemos su comportamiento — Claude Code lo domina
- Precio: $3/M input, $15/M output — razonable para enterprise

---

## Arquitectura de la solución

### FASE 1 — Pipeline de ingesta (resuelve el problema raíz)

```
PDF escaneado en SharePoint
        ↓
[Script Python — se corre UNA VEZ para todos los PDFs existentes]
        ↓
Azure Document Intelligence (prebuilt-contract)
→ OCR del contenido escaneado
→ Extracción de campos estructurados:
   - fecha_contrato (del texto, no del upload)
   - proveedor
   - monto
   - fecha_vencimiento
   - tipo_contrato
   - clausulas principales
        ↓
Resultado guardado como JSON con texto + metadata
        ↓
Indexado en Azure AI Search con metadata completa
```

### FASE 2 — Automatización para contratos nuevos

```
Nuevo PDF llega a SharePoint
        ↓
Azure Logic Apps lo detecta automáticamente
        ↓
Dispara el mismo pipeline de OCR
        ↓
Indexado automáticamente antes de que alguien pregunte
```

### FASE 3 — El agente en Foundry

```
Usuario pregunta sobre contratos
        ↓
Agente busca en Azure AI Search
→ Filtra por metadata REAL (fecha_contrato, proveedor)
→ No por fecha de upload
        ↓
Trae chunks o documentos relevantes
        ↓
Claude Sonnet 4.6 analiza y responde
        ↓
Usuario recibe respuesta precisa con fuente
```

---

## Estructura del proyecto en código

```
grupo-rocka-agente/
├── ingesta/
│   ├── ocr_pipeline.py          # Script principal de OCR
│   ├── sharepoint_downloader.py # Descarga PDFs de SharePoint
│   ├── document_intelligence.py # Wrapper de Azure Doc Intelligence
│   └── indexer.py               # Sube texto + metadata a AI Search
├── agente/
│   ├── agent.py                 # Agente principal en Foundry SDK
│   ├── search_tool.py           # Tool de búsqueda en AI Search
│   ├── prompts.py               # System prompt del agente
│   └── config.py                # Variables de entorno y configuración
├── automatizacion/
│   └── logic_app_trigger.py     # Webhook para contratos nuevos
├── tests/
│   └── test_queries.py          # Preguntas de prueba sobre contratos
├── .env                         # Keys y endpoints (no commitear)
└── README.md
```

---

## Variables de entorno necesarias

```env
# Azure Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com
AZURE_DOC_INTELLIGENCE_KEY=<key>

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<resource>.search.windows.net
AZURE_SEARCH_KEY=<key>
AZURE_SEARCH_INDEX_NAME=contratos-grupo-rocka

# Microsoft Foundry
AZURE_FOUNDRY_ENDPOINT=https://<project>.services.ai.azure.com
AZURE_FOUNDRY_PROJECT=<project-name>

# SharePoint (via Microsoft Graph API)
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
SHAREPOINT_SITE_URL=https://<tenant>.sharepoint.com/sites/<site>
SHAREPOINT_FOLDER_PATH=/Contratos

# Modelo
MODEL_NAME=claude-sonnet-4-6
```

---

## Esquema de metadata por contrato

Cada contrato indexado debe tener esta estructura:

```json
{
  "id": "contrato_proveedor_xyz_2024",
  "nombre_archivo": "contrato_proveedor_xyz_2024.pdf",
  "texto_completo": "CONTRATO DE SUMINISTRO...",
  "metadata": {
    "fecha_contrato": "2024-03-15",
    "fecha_vencimiento": "2025-03-15",
    "proveedor": "Proveedor XYZ S.A. de C.V.",
    "monto": "500000",
    "moneda": "MXN",
    "tipo_contrato": "suministro",
    "status": "activo",
    "procesado_en": "2026-04-13T10:00:00",
    "confidence_score": 0.95
  }
}
```

---

## El script de ingesta — código base

```python
# ingesta/ocr_pipeline.py

import os
import json
from pathlib import Path
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime

def procesar_contrato(pdf_path: str) -> dict:
    """
    Recibe un PDF (escaneado o nativo) y regresa texto + metadata estructurada.
    """
    client = DocumentIntelligenceClient(
        endpoint=os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_DOC_INTELLIGENCE_KEY"))
    )
    
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-contract",
            analyze_request=f,
            content_type="application/octet-stream"
        )
    
    result = poller.result()
    
    # Extraer texto completo de todas las páginas
    texto = "\n".join(
        line.content
        for page in result.pages
        for line in page.lines
    )
    
    # Extraer campos estructurados del contrato
    campos = {}
    if result.documents:
        for nombre, campo in result.documents[0].fields.items():
            campos[nombre] = campo.value_string or ""
    
    metadata = {
        "fecha_contrato": campos.get("ContractDate", ""),
        "proveedor": campos.get("Parties", ""),
        "monto": campos.get("TotalAmount", ""),
        "fecha_vencimiento": campos.get("ExpirationDate", ""),
        "tipo_contrato": campos.get("ContractType", ""),
        "procesado_en": datetime.now().isoformat(),
        "confidence_score": result.documents[0].confidence if result.documents else 0
    }
    
    return {
        "texto_completo": texto,
        "metadata": metadata,
        "paginas": len(result.pages)
    }
```

---

## El agente — código base

```python
# agente/agent.py

import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

def crear_agente():
    client = AIProjectClient(
        endpoint=os.getenv("AZURE_FOUNDRY_ENDPOINT"),
        credential=DefaultAzureCredential()
    )
    
    agente = client.agents.create_agent(
        model=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
        name="Agente de Contratos — Grupo Rocka",
        instructions="""
        Eres un asistente especializado en contratos de Grupo Rocka.
        
        Tu trabajo:
        - Responder preguntas sobre contratos específicos
        - Comparar condiciones entre contratos
        - Identificar cláusulas relevantes
        - Alertar sobre contratos próximos a vencer
        
        Reglas importantes:
        - Siempre cita el nombre del contrato y su fecha cuando respondas
        - Si no encuentras información suficiente, dilo claramente
        - No inventes cláusulas ni fechas — solo lo que está en los documentos
        - Para comparaciones, presenta la información en formato tabla cuando sea posible
        """,
        tools=[{"type": "azure_ai_search"}]  # conectado al índice de contratos
    )
    
    return agente, client
```

---

## Plan de trabajo — semana a semana

### Semana 1 — Pipeline de ingesta
```
Día 1-2:
✅ Crear Azure account + activar Document Intelligence
✅ Conseguir 5-10 PDFs de contratos de prueba de Grupo Rocka
✅ Correr script de OCR sobre los PDFs de prueba
✅ Verificar que extrae texto y metadata correctamente

Día 3:
✅ Crear Azure AI Search index
✅ Indexar los contratos procesados con metadata
✅ Hacer búsquedas de prueba directas al índice

Día 4-5:
✅ Crear Foundry project
✅ Crear agente básico conectado al índice
✅ Pruebas con preguntas reales de contratos
```

### Semana 2 — Agente completo + automatización
```
Día 1-2:
✅ Conectar SharePoint via Microsoft Graph API
✅ Descargar contratos directamente desde SharePoint
✅ Procesar todos los contratos existentes

Día 3:
✅ Logic Apps para automatizar contratos nuevos
✅ Webhook que dispara pipeline automáticamente

Día 4-5:
✅ Refinar system prompt con casos de uso reales
✅ Pruebas con usuarios de Grupo Rocka
✅ Fix de issues encontrados
```

### Semana 3 — Demo + entrega
```
✅ Demo funcionando con contratos reales
✅ Documentación de uso para Grupo Rocka
✅ Handoff a los consultores de mi papá para deployment
✅ Propuesta de retainer para mantenimiento
```

---

## Queries de prueba para validar el agente

Una vez que esté funcionando, probar con estas queries:

```python
queries_prueba = [
    # Búsqueda simple
    "¿Cuándo vence el contrato con [Proveedor X]?",
    
    # Búsqueda por fecha
    "¿Qué contratos vencen en los próximos 3 meses?",
    
    # Cláusulas específicas  
    "¿Cuáles son las cláusulas de penalización del contrato con [Proveedor Y]?",
    
    # Comparación
    "Compara las condiciones de pago del contrato 2023 vs 2024 con [Proveedor Z]",
    
    # El caso que tenían atorado
    "¿Cuál es el contrato más reciente con [Proveedor X]?",
    
    # Resumen
    "Dame un resumen de todos los contratos activos de suministro"
]
```

---

## Costo estimado del proyecto

### Desarrollo (lo que cobramos nosotros)
```
Proyecto de desarrollo:     $15,000 - $20,000 USD
Tiempo estimado:            2-3 semanas
Retainer mensual:           $2,000 - $2,500 USD
```

### Costo operativo mensual para Grupo Rocka (pagan directo a Azure)
```
Document Intelligence:      ~$5 USD (contratos nuevos)
Azure AI Search:            ~$25 USD
Claude Sonnet 4.6 tokens:   ~$100-400 USD según uso
Logic Apps:                 ~$10 USD
─────────────────────────────────────
Total mensual Azure:        ~$150-450 USD
```

### ROI para Grupo Rocka
```
Costo mensual agente:       ~$400 USD
Tiempo ahorrado:            3-5 horas/semana de búsqueda manual
Valor de ese tiempo:        ~$1,500-2,000 USD/mes
ROI:                        4-5x mensual

Un error evitado en cláusula de contrato:
→ Multa típica: $500,000 MXN (~$25,000 USD)
→ El agente se paga 5 años con ese solo caso
```

---

## Notas importantes

- **Foundry Agent Service GA desde marzo 2026** — producción lista
- **Claude Sonnet 4.6 en Foundry** — disponible en East US 2 y Sweden Central (Global Standard)
- **prebuilt-contract de Document Intelligence** — modelo preentrenado para contratos, extrae campos automáticamente
- **500 páginas/mes gratis** en Document Intelligence — la ingesta inicial probablemente entra en el free tier
- Los contratos procesados se guardan permanentemente en AI Search — el OCR solo se hace una vez por documento
- Si hay PDFs nativos (no escaneados) Document Intelligence también los procesa correctamente — el mismo pipeline funciona para ambos tipos

---

## Recursos y documentación

- Portal Foundry: `ai.azure.com`
- Document Intelligence: `learn.microsoft.com/azure/ai-services/document-intelligence`
- Azure AI Search: `learn.microsoft.com/azure/search`
- Foundry Agent SDK: `learn.microsoft.com/azure/foundry/agents`
- Microsoft Graph API (SharePoint): `learn.microsoft.com/graph/api/resources/sharepoint`
- Claude en Foundry: `devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-feb-2026`
