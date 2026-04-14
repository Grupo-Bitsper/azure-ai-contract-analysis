# Guía: Crear Azure OpenAI Resource (Alternativa a Foundry)

## Por qué esta alternativa

Foundry requiere cuotas específicas que pueden tomar días en aprobarse.

Azure OpenAI Service es más simple y **suele tener cuota por defecto** para GPT-3.5-turbo.

---

## Opción A: Crear Azure OpenAI Resource (Recomendado ahora)

### Paso 1: Ir a Azure Portal

1. Ve a **https://portal.azure.com**
2. Login con `miguelaor681@outlook.com`

### Paso 2: Crear recurso de Azure OpenAI

1. Click en **"Create a resource"** (botón + en la esquina superior izquierda)
2. Busca: **"Azure OpenAI"**
3. Click en **"Azure OpenAI"** y luego **"Create"**

### Paso 3: Configurar el recurso

**Basics:**
- **Subscription**: bitsper demo
- **Resource group**: Crea uno nuevo o usa existente (ejemplo: `rg-foundry`)
- **Region**: **Sweden Central** (mejor disponibilidad) o **East US**
- **Name**: `openai-vidanta-hr` (o el nombre que quieras)
- **Pricing tier**: **Standard S0**

Click **"Next"**

**Network:**
- Deja los defaults
Click **"Next"**

**Tags:** (opcional)
- Skip
Click **"Next"**

**Review + create:**
- Click **"Create"**

Espera 2-3 minutos mientras se crea el recurso.

### Paso 4: Abrir el recurso

1. Cuando termine, click **"Go to resource"**
2. Deberías ver el Overview del recurso

### Paso 5: Obtener las credenciales

1. En el menú izquierdo, ve a **"Keys and Endpoint"**
2. Copia:
   - **KEY 1** (la API key)
   - **Endpoint** (la URL)

### Paso 6: Crear un deployment de GPT-3.5

1. En el menú izquierdo, click en **"Model deployments"**
2. Click **"Manage Deployments"** - esto te lleva a Azure OpenAI Studio
3. En OpenAI Studio, click **"Create new deployment"**
4. Configuración:
   - **Model**: **gpt-35-turbo** (este suele tener cuota por defecto)
   - **Model version**: Selecciona la más reciente
   - **Deployment name**: `gpt-35-turbo` (importante: anota este nombre)
   - **Deployment type**: Standard
   - **Tokens per Minute Rate Limit**: 10K (o lo que permita)
5. Click **"Create"**

### Paso 7: Actualizar .env

Edita tu archivo `.env` y actualiza estas líneas:

```bash
# Usa las credenciales del recurso de Azure OpenAI que acabas de crear
AZURE_API_KEY=tu-nueva-key-aqui
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com/
```

### Paso 8: Probar

```bash
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
python agents/hr_policies/hr_agent_simple.py
```

---

## Opción B: Solicitar cuota para Foundry (largo plazo)

Mientras tanto, solicita cuota para Foundry (para usar en el futuro):

### Paso 1: Ir a Quotas en Foundry

1. Ve a **https://ai.azure.com**
2. Abre tu proyecto
3. Ve a **"Settings"** → **"Quotas"**

### Paso 2: Solicitar cuota

1. Busca los modelos que quieres:
   - GPT-4o
   - Claude Sonnet 4.5
2. Click **"Request quota"**
3. Llena:
   - **Tokens per minute**: 10000 (para empezar)
   - **Justification**: "Development of HR chatbot for enterprise client (Vidanta). Need quota for testing and production deployment."
4. Submit

### Paso 3: Esperar aprobación

- **GPT-4o**: 1-24 horas
- **Claude**: 1-2 días hábiles

Cuando se apruebe, podrás volver a usar el código original de Foundry.

---

## Comparación: Azure OpenAI vs Foundry

| Característica | Azure OpenAI (ahora) | Foundry (después) |
|----------------|----------------------|-------------------|
| **Setup** | 10 minutos | Requiere cuota |
| **Cuota** | Suele estar disponible | Requiere solicitud |
| **Modelos** | GPT-3.5, GPT-4 | GPT + Claude + más |
| **Integración** | Manual | Automática con M365 |
| **SharePoint** | Requiere código custom | Foundry IQ automático |
| **Para MVP** | ✅ Perfecto | ❌ Espera cuota |
| **Para producción** | ⚠️ OK | ✅ Ideal |

---

## Recomendación

**Para hoy:**
1. ✅ Crea Azure OpenAI resource
2. ✅ Despliega GPT-3.5-turbo
3. ✅ Usa `hr_agent_simple.py` para testear

**Para la semana:**
1. ⏳ Solicita cuota en Foundry para GPT-4o y Claude
2. ⏳ Cuando se apruebe, migra a Foundry
3. ⏳ Configura Foundry IQ con SharePoint

**Para la junta de mañana:**
- ✅ Puedes demostrar el agente funcionando con GPT-3.5
- ✅ Explicas que vas a usar Claude en producción
- ✅ Muestras la arquitectura de Foundry

---

## Siguiente paso

➡️ **Crea el recurso de Azure OpenAI ahora** (10 minutos)

Cuando termines, avísame y probamos el agente. 🚀
