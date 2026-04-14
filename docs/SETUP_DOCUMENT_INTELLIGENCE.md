# Setup: Azure Document Intelligence

## 🎯 Objetivo
Configurar Azure Document Intelligence para hacer OCR de contratos (PDFs escaneados).

---

## 📝 Paso 1: Crear el recurso en Azure Portal

### 1.1 Ir a Azure Portal
1. Ve a: **https://portal.azure.com**
2. Login con tu cuenta

### 1.2 Crear recurso
1. Click **"Create a resource"** (+ en esquina superior izquierda)
2. Busca: **"Document Intelligence"** o **"Form Recognizer"** (es el mismo servicio)
3. Click **"Create"**

### 1.3 Configuración
**Basics:**
- **Subscription**: bitsper demo (o la que uses)
- **Resource group**: Usa `rg-foundry` o crea uno nuevo: `rg-contratos`
- **Region**: **East US** o **Sweden Central** (donde tienes Foundry)
- **Name**: `doc-intelligence-contratos` (o el nombre que quieras)
- **Pricing tier**:
  - ✅ **Free F0** - 500 páginas/mes gratis (suficiente para testing)
  - O **Standard S0** - $1.50 por 1000 páginas

Click **"Review + Create"** → **"Create"**

⏱️ Espera 1-2 minutos

### 1.4 Obtener credenciales
1. Cuando termine, click **"Go to resource"**
2. En el menú izquierdo, ve a **"Keys and Endpoint"**
3. Copia:
   - **KEY 1** (la API key)
   - **Endpoint** (la URL)

---

## 📝 Paso 2: Actualizar .env

Agrega estas líneas a tu `.env`:

```bash
# Azure Document Intelligence (para OCR de contratos)
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://tu-recurso.cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=tu_key_aqui
```

---

## 📝 Paso 3: Instalar SDK

```bash
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
pip install azure-ai-documentintelligence
```

---

## 📝 Paso 4: Probar OCR

Ejecuta el script de prueba:

```bash
python scripts/test_ocr.py
```

Si todo funciona, verás:
- ✅ Texto extraído del PDF
- ✅ Metadata detectada (fechas, montos, etc.)
- ✅ Confidence scores

---

## 🎯 Modelos disponibles en Document Intelligence

### **prebuilt-contract** ⭐ RECOMENDADO para contratos
Extrae automáticamente:
- Fecha del contrato
- Partes involucradas (firmantes)
- Montos
- Fecha de vencimiento
- Términos principales

### **prebuilt-read**
Solo OCR básico (texto plano)

### **prebuilt-layout**
Extrae estructura (tablas, títulos, etc.)

**Para Grupo Rocka: usa `prebuilt-contract`**

---

## 💰 Costo

**Free tier:**
- 500 páginas/mes gratis
- Suficiente para todos tus contratos de prueba

**Standard tier:**
- $1.50 por 1000 páginas
- Ejemplo: 100 contratos × 10 páginas = 1000 páginas = $1.50

**Para producción con Grupo Rocka:**
- Si tienen 500 contratos × 15 páginas = 7,500 páginas
- OCR UNA VEZ: $11.25 total
- Contratos nuevos: ~10/mes = $0.15/mes

---

## 🚀 Siguiente paso

Una vez configurado, ejecuta:

```bash
python scripts/test_ocr.py /Users/miguelordonez/Documents/contratosdemo/
```

Esto procesará todos los contratos y te mostrará qué metadata extrae.
