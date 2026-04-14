# 🎯 Siguiente Paso - Desplegar GPT-4o-mini

**Última actualización**: 13 abril 2026, 8:10pm

---

## ✅ Lo que descubrimos

**¡BUENAS NOTICIAS!** No necesitas llenar el formulario de registro.

Muchos modelos están disponibles **inmediatamente sin aprobación**:
- ✅ GPT-4o-mini (RECOMENDADO para tu agente)
- ✅ GPT-5-mini
- ✅ GPT-5-nano
- ✅ Llama 3.1, Mistral (open source)

**Evita estos** (requieren registro):
- ❌ GPT-5.4, GPT-5.4-pro
- ❌ GPT-5.3-codex
- ❌ O3, O3-pro
- ❌ GPT-image-1, Sora 2

---

## 🚀 Acción AHORA (5 minutos)

### Paso 1: Ir a Azure AI Studio

1. Abre: **https://ai.azure.com**
2. Login con: `miguelaor681@outlook.com`

### Paso 2: Abrir tu proyecto

1. Click en **"Projects"** en el menú izquierdo
2. Selecciona: **`miguelaor681-2681`**

### Paso 3: Crear deployment

1. Busca **"Deployments"** o **"Model deployments"** en el menú
2. Click **"Create deployment"** o **"+ Create"**
3. Configuración:
   - **Select a model**: Busca y selecciona **`gpt-4o-mini`**
   - **Deployment name**: **`gpt-4o-mini`** (usa exactamente este nombre)
   - **Model version**: Selecciona la más reciente
   - **Deployment type**: Standard
   - **Region**: **Sweden Central** (si está disponible, sino East US)
   - **Tokens per Minute Rate Limit (thousands)**: 10 (o lo máximo que permita)
4. Click **"Deploy"** o **"Create"**

### Paso 4: Esperar deployment (1-2 minutos)

Verás el status cambiando:
- Creating → Succeeded

Cuando veas **"Succeeded"**, ¡ya está listo!

### Paso 5: Verificar el deployment

Abre una terminal y ejecuta:

```bash
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
python list_deployments.py
```

Deberías ver algo como:

```
📋 Deployments disponibles:

Total: 1 deployment(s)

1. gpt-4o-mini
   Modelo: gpt-4o-mini
   Status: Succeeded
```

### Paso 6: Probar el agente

```bash
python agents/hr_policies/hr_agent.py
```

Si todo funciona, verás el agente respondiendo preguntas en español.

---

## ⚠️ Si encuentras problemas

### Problema: "No capacity in region"

**Solución**: Intenta otra región
- Sweden Central
- West US 3
- East US

### Problema: "Insufficient quota"

**Solución 1**: Reduce el TPM a 1K en el deployment

**Solución 2**: Prueba con **gpt-5-nano** (más barato, menor cuota)

**Solución 3**: Usa modelo open source
1. Ve a **"Model catalog"** en ai.azure.com
2. Busca **"Llama 3.1 8B"**
3. Deploy como **Serverless API** (no requiere cuota)

### Problema: "Deployment takes too long"

Si después de 5 minutos sigue en "Creating":
- Refresca la página
- O cancela y prueba otra región

---

## 📋 Checklist

- [ ] Ir a https://ai.azure.com
- [ ] Abrir proyecto `miguelaor681-2681`
- [ ] Crear deployment de `gpt-4o-mini`
- [ ] Nombre del deployment: `gpt-4o-mini`
- [ ] Esperar "Succeeded"
- [ ] Ejecutar `python list_deployments.py`
- [ ] Ejecutar `python agents/hr_policies/hr_agent.py`

---

## 🎉 Cuando funcione

Tu agente de HR estará listo con:
- ✅ GPT-4o-mini (rápido, económico, sin registro)
- ✅ Respuestas en español
- ✅ Tono profesional de RH
- ✅ Contexto de conversación

**Para la junta de mañana:**
- Puedes demostrar el agente funcionando
- Explicas que vas a migrar a Claude cuando tengas cuota
- Muestras toda la arquitectura de Foundry + SharePoint

---

## 🚀 Después de la junta

**Mejoras a largo plazo:**

1. **Solicitar cuota para Claude** (mejor para español)
   - portal.azure.com → Quotas
   - Solicitar Claude Sonnet 4.5
   - Cambiar modelo en el código cuando se apruebe

2. **Conectar SharePoint** de Vidanta
   - Configurar Foundry IQ
   - RAG sobre documentos de políticas

3. **Dashboard de admin**
   - Métricas de uso
   - Preguntas frecuentes
   - Satisfacción de usuarios

---

## ⏱️ Tiempo total estimado

- **Crear deployment**: 3-5 minutos
- **Verificar**: 1 minuto
- **Probar agente**: 2 minutos

**Total: 10 minutos máximo** 🚀

---

## 💡 Siguiente comando

```bash
# Después de crear el deployment en ai.azure.com, ejecuta:
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
python list_deployments.py
```

**¡Avísame cuando hayas creado el deployment!** 🎯
