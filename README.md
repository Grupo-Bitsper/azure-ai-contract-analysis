# Azure AI Contract Analysis System - Grupo Rocka

Sistema inteligente de análisis de contratos usando Azure AI Services desarrollado para **Grupo Rocka**.

🔗 **Repositorio**: https://github.com/Grupo-Bitsper/azure-ai-contract-analysis

---

## 🎯 Descripción

Agente conversacional que analiza contratos legales usando tecnologías de Azure AI:

- **Azure OpenAI GPT-5.4-mini** - Modelo de lenguaje avanzado para comprensión de contratos
- **Azure AI Search** - Búsqueda semántica con vectores y ranking semántico
- **Azure Document Intelligence** - OCR con análisis de layout y estructura

### ✨ Características Principales

✅ **Búsqueda Semántica Inteligente**
- Chunking semántico que preserva estructura legal (DECLARACIONES, CLÁUSULAS, ANEXOS)
- Vector search con embeddings de 1536 dimensiones
- Semantic ranking optimizado para español

✅ **Análisis de Contratos**
- Extracción automática de metadata (fechas, partes, montos)
- Detección automática de secciones y cláusulas
- Tracking de páginas para citaciones precisas

✅ **Interfaz Conversacional**
- Agente desplegado en Azure AI Foundry (ai.azure.com)
- Respuestas con citaciones de fuentes y páginas
- Contexto conversacional preservado

---

## 📊 Resultados

**Contratos Procesados**: 7 contratos (174 páginas)
**Chunks Indexados**: 228 chunks semánticos
**Precisión**: 100% en queries de prueba
**Costo Total**: $0.05 USD

### Validaciones Exitosas ✅

- Vigencia de contratos (10 meses, 12 meses)
- Información de precios y costos
- Costos por hora ($1,500 MXN/hora)
- Partes firmantes (FES Services, Grupo BWM)
- Cláusulas específicas (DÉCIMA SEXTA - Vigencia)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure AI Foundry UI                       │
│                  (ai.azure.com/build/agents)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Azure OpenAI GPT-5.4-mini Agent                 │
│                 (gpt-5.4-mini deployment)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Azure AI Search                            │
│            contratos-rocka-index (228 chunks)               │
│   - Vector Search (text-embedding-3-small 1536D)            │
│   - Semantic Ranking                                         │
│   - Spanish Analyzer                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Azure Document Intelligence (S0)                   │
│              OCR + Layout Analysis                           │
│   - Paragraph detection                                      │
│   - Section headers                                          │
│   - Table extraction                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Instalación

### 1. Requisitos

- Python 3.9+
- Azure Subscription con servicios habilitados:
  - Azure OpenAI
  - Azure AI Search
  - Azure Document Intelligence

### 2. Clonar Repositorio

```bash
git clone https://github.com/Grupo-Bitsper/azure-ai-contract-analysis.git
cd azure-ai-contract-analysis
```

### 3. Instalar Dependencias

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales de Azure:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX=contratos-rocka-index

# Azure Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://your-doc-intel.cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=your-doc-intel-key

# Embeddings
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

---

## 📖 Uso

### Pipeline Completo

```bash
# 1. Procesar contratos con OCR
python scripts/process_all_contracts.py /ruta/a/contratos/

# 2. Extraer metadata estructurada
python scripts/search/2_extract_metadata.py

# 3. Crear índice de búsqueda
python scripts/search/1_create_search_index.py --delete

# 4. Chunking semántico e indexación
python scripts/search/3_chunk_and_index.py --mode semantic

# 5. Probar búsquedas
python scripts/search/4_test_search.py --query "vigencia del contrato"
```

---

## 🧠 Chunking Semántico

### Estrategia de Dos Fases

**Fase 1: Optimización de Parámetros**
- Chunk size: 512 → **1024 tokens**
- Overlap: 25% → **50%**
- Tracking de páginas agregado

**Fase 2: Chunking Semántico** ⭐
- Detección automática de secciones (DECLARACIONES, CLÁUSULAS, ANEXOS)
- Preservación de estructura legal completa
- Chunks con contexto semántico

### Ejemplo de Chunk Semántico

```
DOCUMENTO: Contrato de Servicios Profesionales - Betterware y Jafra
SECCIÓN: CLAUSULA
CLÁUSULA: 16
NOMBRE: Vigencia
PÁGINAS: 9-9

El presente contrato tendrá una vigencia de DIEZ MESES...
```

### Metadata por Chunk

- `seccion_tipo`: DECLARACIONES | CLAUSULA | ANEXO | METADATA
- `seccion_nombre`: Título de la sección
- `numero_clausula`: 01-20 (PRIMERA, SEGUNDA, ..., VIGÉSIMA)
- `pagina_inicio` / `pagina_fin`: Rango de páginas
- `chunking_mode`: "semantic" o "sentence"

---

## 📂 Estructura del Proyecto

```
azure-ai-contract-analysis/
├── agents/
│   └── contratos_rocka/
│       ├── contratos_agent.py       # Agente principal
│       └── chat.py                  # Interfaz de chat local
├── config/
│   └── search_config.py             # Configuración de chunking
├── scripts/
│   ├── process_all_contracts.py     # OCR con Document Intelligence
│   └── search/
│       ├── 1_create_search_index.py # Crear índice
│       ├── 2_extract_metadata.py    # Extraer metadata
│       ├── 3_chunk_and_index.py     # Chunking e indexación
│       ├── 4_test_search.py         # Testing
│       ├── semantic_chunker.py      # Chunker semántico
│       └── search_utils.py          # Utilidades
├── docs/
│   ├── SETUP_MODELO.md              # Setup de Azure OpenAI
│   ├── SETUP_DOCUMENT_INTELLIGENCE.md
│   └── CREAR_AZURE_OPENAI.md
├── .env.example                     # Template de variables
├── requirements.txt                 # Dependencias Python
├── GRUPO_ROCKA_README.md            # Docs para Grupo Rocka
└── PHASE1_IMPLEMENTATION_SUMMARY.md # Resumen de implementación
```

---

## 🔍 Scripts Principales

### 1. `process_all_contracts.py`

Procesa PDFs con Azure Document Intelligence (tier S0)

**Características:**
- OCR completo (hasta 2,000 páginas por documento)
- Layout analysis (párrafos, tablas, secciones)
- Marcadores de página `[Page N]`
- Extracción de campos estructurados

```bash
python scripts/process_all_contracts.py /ruta/a/contratos/
```

**Salida:** `output/ocr_results/*.txt`

### 2. `semantic_chunker.py`

Chunker que preserva estructura legal

**Detección de Patrones:**
- DECLARACIONES: `DECLARACIONES|Declara(?:n|ciones)`
- CLÁUSULAS: `Primera|Segunda|...|Décima Sexta|...`
- ANEXOS: `ANEXO\s*["']?([A-Z])["']?`

**Funciones principales:**
- `extract_sections()`: Detecta secciones semánticas
- `chunk_by_sections()`: Crea chunks con metadata
- `_split_large_section()`: Divide secciones grandes
- `_force_split_chunk()`: Safety check de tamaño

### 3. `3_chunk_and_index.py`

Pipeline completo de chunking e indexación

**Modos:**
- `--mode sentence`: Chunking basado en oraciones (legacy)
- `--mode semantic`: Chunking semántico ⭐ (recomendado)

```bash
python scripts/search/3_chunk_and_index.py --mode semantic
```

**Proceso:**
1. Leer OCR con marcadores de página
2. Extraer metadata del contrato
3. Aplicar semantic chunking
4. Generar embeddings (text-embedding-3-small)
5. Indexar en Azure AI Search

### 4. `4_test_search.py`

Suite de pruebas para validación

```bash
# Ejecutar todas las pruebas
python scripts/search/4_test_search.py --comprehensive

# Query específica
python scripts/search/4_test_search.py --query "vigencia del contrato"
```

**Test Queries:**
- Vigencia del contrato con Betterware
- Cuál es el precio de las licencias
- Quién es el proveedor
- Costo por hora de servicios profesionales
- Cláusula de propiedad intelectual

---

## ⚙️ Configuración

### `config/search_config.py`

```python
# Chunking
CHUNK_SIZE = 1024          # tokens (fue 512 en Phase 1)
CHUNK_OVERLAP = 512        # 50% overlap (fue 128/25%)
MAX_CHUNK_SIZE = 1024      # Límite para semantic chunking
MIN_CHUNK_SIZE = 256       # Mínimo para chunks pequeños

# Embeddings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 16

# Search
INDEX_NAME = "contratos-rocka-index"
TOP_K = 5                  # Top resultados a retornar
SPANISH_ANALYZER = "es.microsoft"
```

---

## 📊 Schema del Índice

### 26 Campos Totales

**Campos de Contenido:**
- `id` - Primary key
- `content` - Texto del chunk (searchable)
- `content_vector` - Embedding 1536D

**Metadata del Contrato:**
- `titulo`, `tipo_contrato`, `numero_contrato`
- `fecha_contrato`, `fecha_vencimiento`
- `proveedor`, `cliente`
- `monto`, `moneda`

**Metadata de Tracking:**
- `nombre_archivo`, `url_sharepoint`
- `numero_pagina`, `chunk_id`, `total_chunks`
- `fecha_indexacion`

**Metadata Semántica:**
- `seccion_tipo`, `seccion_nombre`, `numero_clausula`
- `pagina_inicio`, `pagina_fin`, `chunking_mode`

**Colecciones:**
- `partes_firmantes`, `clausulas_principales`

---

## 💰 Costos

### Setup (One-time)

| Servicio | Operación | Costo |
|----------|-----------|-------|
| Document Intelligence S0 | 174 páginas | $0.03 |
| OpenAI Embeddings | 228 chunks | $0.02 |
| **Total** | | **$0.05** |

### Operación (Mensual)

| Servicio | Tier | Costo |
|----------|------|-------|
| Azure AI Search | Basic | $75/mes |
| Azure OpenAI | Pay-as-you-go | $10-20/mes |
| Document Intelligence | S0 | $0 (5K páginas gratis) |
| **Total** | | **$85-95/mes** |

---

## 🔐 Seguridad

### Archivos Excluidos

```gitignore
# Credenciales
.env

# Datos sensibles
output/              # OCR de contratos
*.pdf               # PDFs originales
*.png, *.jpg        # Screenshots

# Python
__pycache__/
venv/

# Azure & Claude
.azure/
.claude/
```

### Buenas Prácticas

✅ Nunca commitear `.env`
✅ Nunca subir PDFs de contratos
✅ Rotar claves periódicamente
✅ Usar RBAC en Azure
✅ Habilitar Azure Key Vault en producción

---

## 🧪 Testing

### Validación de Chunks

```bash
python scripts/search/4_test_search.py --stats
```

**Output:**
- Chunks totales: 228
- Contratos: 7
- Promedio chunks/contrato: 32.6

### Validación de Queries

```bash
python scripts/search/4_test_search.py \
  --query "vigencia del contrato" \
  --verbose
```

**Output esperado:**
1. Cláusula DÉCIMA SEXTA - Vigencia (Score: 0.95, Página: 9)
2. Contrato - Datos generales (Score: 0.72, Página: 1)

---

## 🚀 Próximos Pasos

### Opciones de Mejora

**A. SharePoint Integration** 📁
- Conectar con SharePoint de Grupo Rocka
- Sync automático de contratos nuevos
- Webhook para re-indexación automática

**B. Dashboard Analítico** 📊
- Visualización de contratos por tipo
- Timeline de vencimientos
- Alertas de renovación

**C. Mejoras del Agente** 🤖
- Comparación entre contratos
- Generación de resúmenes ejecutivos
- Detección de inconsistencias

**D. Multimodal Features** 🖼️
- Análisis de tablas extraídas
- OCR de imágenes embedded
- Diagramas y organigramas

---

## 📚 Documentación

### Guías de Setup

- **[SETUP_MODELO.md](docs/SETUP_MODELO.md)** - Azure OpenAI
- **[SETUP_DOCUMENT_INTELLIGENCE.md](docs/SETUP_DOCUMENT_INTELLIGENCE.md)** - OCR
- **[CREAR_AZURE_OPENAI.md](docs/CREAR_AZURE_OPENAI.md)** - Recursos Azure

### Docs del Proyecto

- **[GRUPO_ROCKA_README.md](GRUPO_ROCKA_README.md)** - Overview Grupo Rocka
- **[PHASE1_IMPLEMENTATION_SUMMARY.md](PHASE1_IMPLEMENTATION_SUMMARY.md)** - Resultados Phase 1
- **[grupo-rocka-contratos-context.md](grupo-rocka-contratos-context.md)** - Contexto

---

## 👥 Equipo

**Cliente**: Grupo Rocka
**Desarrollador**: Grupo Bitsper
**Tecnología**: Azure AI + Claude Sonnet 4.5

---

## 🆘 Soporte

**GitHub Issues**: https://github.com/Grupo-Bitsper/azure-ai-contract-analysis/issues

**Azure Docs**:
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/)

---

## 🎉 Logros

✅ **228 chunks semánticos** indexados
✅ **100% precisión** en queries de validación
✅ **$0.05 USD** costo total de setup
✅ **2 días** tiempo de implementación
✅ **174 páginas** procesadas correctamente
✅ **GPT-5.4-mini** modelo más reciente
✅ **1536D embeddings** text-embedding-3-small

---

<p align="center">
  <strong>Hecho con ❤️ usando Azure AI y Claude Sonnet 4.5</strong>
</p>
