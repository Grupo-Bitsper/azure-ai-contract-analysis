# 🚨 Proyecto Urgente: Agente de Contratos - Grupo Rocka

**Status**: 🔴 URGENTE - Equipo de choque/salvación
**Timeline**: 3-5 días para MVP demo
**Deadline del cliente**: Ya están 2 semanas atrasados

---

## 🎯 Situación Actual

### El Problema
- ✅ Grupo Rocka tiene contratos en SharePoint (implementado por tu papá)
- ❌ PDFs son **escaneados** (imágenes, no texto)
- ❌ Agente en **Copilot Studio NO funciona** (no puede leer PDFs escaneados)
- ❌ Consultores de tu papá **2 semanas atrasados** del deadline
- ❌ No pueden comparar contratos ni extraer metadata real

### Por Qué Están Atorados
```
Copilot Studio (low-code):
├─ MCP descarga PDF de SharePoint
├─ PDF escaneado = imagen JPG
├─ No hay texto que leer
└─ ❌ NO permite meter OCR en el pipeline

= Bloqueante técnico sin solución en Copilot Studio
```

### Tu Misión (Equipo de Salvación)
- Resolver en **3-5 días** lo que no pudieron en 2 semanas
- Usar **Foundry pro-code** + Document Intelligence
- Demostrar valor del pro-code sobre low-code
- **Salvar el proyecto**

---

## 🏗️ La Solución (Pro-code con Foundry)

### Stack Técnico
```
1. Azure Document Intelligence → OCR + extracción metadata
2. Azure AI Search            → Índice vectorial con metadata REAL
3. Claude Sonnet 4.6 (Foundry) → Análisis de contratos (1M contexto)
4. Logic Apps                 → Automatización contratos nuevos
```

### Arquitectura
```
FASE 1 - Ingesta (UNA VEZ):
PDFs escaneados → Document Intelligence (OCR)
                → Extrae texto + metadata (fecha real, proveedor, monto)
                → Indexa en AI Search

FASE 2 - Automatización:
Nuevo PDF → Logic Apps → Mismo pipeline OCR → Auto-indexado

FASE 3 - Agente:
Pregunta → Busca en AI Search (metadata REAL)
        → Claude analiza → Respuesta precisa
```

---

## 📋 Plan de Trabajo (3-5 días)

### **Día 1 (HOY)** ✅
- [x] Validar tesis con contratos de tu papá
- [ ] Crear Document Intelligence resource en Azure
- [ ] Probar OCR con 1 contrato
- [ ] Validar que extrae metadata correctamente

### **Día 2 (MAÑANA)**
- [ ] Conseguir 5-10 contratos reales de Grupo Rocka
- [ ] Procesar todos con el pipeline OCR
- [ ] Guardar resultados (texto + metadata)
- [ ] Crear Azure AI Search index

### **Día 3**
- [ ] Indexar contratos procesados en AI Search
- [ ] Crear agente básico en Foundry
- [ ] Conectar agente al índice
- [ ] Probar queries críticas

### **Día 4**
- [ ] Refinar system prompt
- [ ] Probar casos de uso reales de Grupo Rocka:
  - "¿Cuándo vence el contrato con Proveedor X?"
  - "Compara contrato 2023 vs 2024 con Proveedor Z"
  - "¿Qué contratos vencen en 3 meses?"
- [ ] Ajustar búsqueda/filtros

### **Día 5**
- [ ] Demo al equipo de tu papá
- [ ] Demo a Grupo Rocka (si posible)
- [ ] Documentar el approach
- [ ] Propuesta de pricing + siguiente fase

---

## 🚀 Getting Started (AHORA)

### Paso 1: Setup Document Intelligence (5 mins)

📄 **Guía**: `docs/SETUP_DOCUMENT_INTELLIGENCE.md`

```bash
1. Ve a portal.azure.com
2. Create resource → "Document Intelligence"
3. Tier: Free F0 (500 páginas/mes gratis)
4. Copia endpoint + key
5. Agrégalos a .env
```

### Paso 2: Instalar SDK

```bash
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
pip install azure-ai-documentintelligence
```

### Paso 3: Probar OCR con contratos de tu papá

```bash
python scripts/test_ocr.py
```

**Si funciona**: ✅ La tesis es válida, el approach funciona

**Mañana**: Aplicar mismo proceso a contratos de Grupo Rocka

---

## 📁 Contratos de Prueba

### Disponibles HOY (contratos de tu papá):
```
/Users/miguelordonez/Documents/contratosdemo/
├── Contrato de Servicios_Licencias_BETTERWARE...pdf (605KB)
├── Anexo A - firmado.pdf (513KB)
├── Anexo C - firmado.pdf (525KB)
├── Anexo D - Alcance Servicios_BETTERWARE...pdf (2.4MB)
├── CSF BWM_24.pdf (151KB)
└── ... (7 PDFs total)
```

**Perfecto para validar**:
- ✅ Contratos reales (Dynamics 365)
- ✅ Tienen fechas, montos, firmantes
- ✅ Algunos firmados (posiblemente escaneados)

### Necesarios MAÑANA (Grupo Rocka):
- 5-10 contratos reales del cliente
- Pedir a tu papá acceso
- Procesar con el mismo pipeline

---

## 💰 Pricing (con Premium de Urgencia)

### Desarrollo
```
Proyecto urgente:    $20,000 - $25,000 USD
                     (vs $15k normal - hay premium por urgencia)

Timeline:            1-2 semanas (vs 3 semanas normal)

Justificación:
├─ Urgencia (2 semanas atrasados)
├─ Complejidad técnica (OCR + AI Search + Foundry)
├─ Riesgo del cliente (deadline perdido)
└─ Valor demostrado (días vs semanas)
```

### Operación Mensual
```
Retainer:                $2,500 USD/mes
Azure (Document Intelligence + AI Search + Claude):
                         ~$150-450 USD/mes
```

### ROI para Grupo Rocka
```
Costo:               ~$3,000/mes total
Tiempo ahorrado:     3-5 horas/semana búsqueda manual
Valor de ese tiempo: ~$1,500-2,000 USD/mes
ROI:                 Break-even + prevención de multas

1 error evitado:     $25,000 USD (multa típica)
                     = Proyecto se paga 5 años
```

---

## 🎯 Queries de Prueba (Validar el Agente)

Una vez funcionando, probar con:

```python
# Búsqueda simple
"¿Cuándo vence el contrato con [Proveedor X]?"

# Búsqueda por fecha
"¿Qué contratos vencen en los próximos 3 meses?"

# Cláusulas específicas
"¿Cuáles son las cláusulas de penalización del contrato con [Proveedor Y]?"

# Comparación (el caso difícil)
"Compara las condiciones de pago del contrato 2023 vs 2024 con [Proveedor Z]"

# El caso que los tenía atorados
"¿Cuál es el contrato más reciente con [Proveedor X]?"
# (basado en fecha DENTRO del contrato, no en fecha de upload de SharePoint)

# Resumen
"Dame un resumen de todos los contratos activos de suministro"
```

---

## 📊 Estructura del Proyecto

```
grupo-rocka-agente/
├── ingesta/
│   ├── ocr_pipeline.py          # Pipeline principal OCR
│   ├── sharepoint_downloader.py # Descarga PDFs SharePoint
│   ├── document_intelligence.py # Wrapper Document Intelligence
│   └── indexer.py               # Sube a AI Search
├── agente/
│   ├── agent.py                 # Agente en Foundry
│   ├── search_tool.py           # Tool de búsqueda
│   ├── prompts.py               # System prompts
│   └── config.py                # Config
├── scripts/
│   ├── test_ocr.py              # ✅ YA CREADO
│   └── process_all_contracts.py # TODO: procesar batch
├── docs/
│   ├── SETUP_DOCUMENT_INTELLIGENCE.md # ✅ YA CREADO
│   └── ARQUITECTURA.md          # TODO: documentar
└── output/
    └── ocr_results/             # Resultados guardados
```

---

## 🔥 El Pitch (Cuando Tengas la Demo)

**Para tu papá:**
> "El equipo lleva 2 semanas atorado porque Copilot Studio no puede hacer OCR. Es un límite técnico del low-code.
>
> **Nosotros lo resolvimos en 3 días con Foundry pro-code.**
>
> Aquí está funcionando con contratos reales. ¿Quieren que terminemos el proyecto?"

**Para Grupo Rocka:**
> "Los consultores están atorados porque Copilot Studio no puede procesar PDFs escaneados.
>
> **Nosotros construimos la solución en Foundry:**
> - ✅ OCR automático de todos los contratos
> - ✅ Metadata REAL (fecha del contrato, no de upload)
> - ✅ Búsqueda precisa y comparación
> - ✅ Aquí está funcionando
>
> ¿Quieren que lo implementemos en producción?"

---

## ⚡ Siguiente Acción (AHORA)

```bash
# 1. Setup Document Intelligence
#    → Sigue: docs/SETUP_DOCUMENT_INTELLIGENCE.md

# 2. Instala el SDK
pip install azure-ai-documentintelligence

# 3. Prueba con tus contratos
python scripts/test_ocr.py

# 4. Si funciona ✅
#    → Mañana pides contratos de Grupo Rocka
#    → Aplicas el mismo pipeline
#    → Demo en 3-5 días
```

---

## 📞 Contactos Clave

- **Tu papá**: Acceso a contratos Grupo Rocka, context del cliente
- **Grupo Rocka**: Usuario final, define queries críticas
- **Consultores**: Handoff para deployment final

---

**Status**: 🟡 En progreso - validando tesis HOY
**Next Milestone**: Demo funcionando en 3-5 días
**Riesgo**: Bajo (solo 1 semana invertida vs alto reward)

🚀 **¡Vamos a salvar este proyecto!**
