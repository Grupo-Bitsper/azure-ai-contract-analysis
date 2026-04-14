# Guía: Desplegar Claude en Azure Foundry

## Estado actual

✅ **Completado:**
- Autenticación configurada (`az login`)
- SDK de Foundry funcionando
- Agente creado exitosamente

❌ **Pendiente:**
- Desplegar un modelo (Claude Sonnet 4.5) en tu proyecto

## Error actual

```
DeploymentNotFound: The API deployment for this resource does not exist
```

Esto significa que el modelo `claude-sonnet-4-5-20250929` no está desplegado en tu proyecto.

---

## Solución: Desplegar Claude en Azure AI Studio

### Paso 1: Ir a Azure AI Studio

1. Abre tu navegador y ve a: **https://ai.azure.com**
2. Inicia sesión con tu cuenta: `miguelaor681@outlook.com`

### Paso 2: Abrir tu proyecto

1. En el panel izquierdo, busca **"Projects"** o **"Proyectos"**
2. Selecciona tu proyecto: **`miguelaor681-2681`**

### Paso 3: Ir a Deployments

Busca una de estas opciones en el menú:
- **"Deployments"**
- **"Models + endpoints"**
- **"Model catalog"**

### Paso 4: Desplegar Claude Sonnet 4.5

#### Opción A: Si ves "Create deployment" o "Deploy model"

1. Click en **"Create deployment"** o **"Deploy model"**
2. Busca en el catálogo: **"Claude Sonnet 4.5"** o **"claude-sonnet-4-5"**
3. Selecciona el modelo
4. Configura el deployment:
   - **Deployment name**: `claude-sonnet-4-5` (puedes usar cualquier nombre)
   - **Model version**: Selecciona la versión más reciente
   - **Region**: Selecciona tu región (East US 2 o Sweden Central tienen Claude)
5. Click en **"Deploy"** o **"Create"**

#### Opción B: Si Claude no aparece en el catálogo

Puede que Claude no esté disponible en tu región o suscripción. En ese caso:

**Alternativa 1: Usar GPT-4**
1. Busca **"GPT-4"** o **"GPT-4o"** en el catálogo
2. Despliega GPT-4o (es más barato y rápido)
3. Anota el **deployment name** que uses

**Alternativa 2: Solicitar acceso a Claude**
1. En Azure Portal, ve a **"Quotas"** o **"Model access"**
2. Solicita acceso a modelos de Anthropic (Claude)
3. Puede tomar 1-2 días hábiles

### Paso 5: Verificar el deployment

Una vez desplegado, deberías ver algo como:

```
Deployment name: claude-sonnet-4-5
Model: claude-sonnet-4-5-20250929
Status: Succeeded
Region: East US 2
```

**IMPORTANTE:** Anota el **nombre del deployment** exacto que creaste.

---

## Paso 6: Actualizar el código con el deployment correcto

Una vez que tengas el deployment, necesitamos actualizar el código del agente.

### Si desplegaste Claude:

El código actual ya usa `claude-sonnet-4-5-20250929`, así que debería funcionar directamente.

### Si desplegaste GPT-4 o otro modelo:

Edita el archivo `agents/hr_policies/hr_agent.py` y cambia la línea:

```python
# Línea ~95
model="claude-sonnet-4-5-20250929",  # ← Cambiar este valor
```

Por el nombre de tu deployment, por ejemplo:

```python
model="gpt-4o",  # o el nombre que hayas usado
```

---

## Paso 7: Verificar que funciona

Ejecuta este comando para listar los deployments:

```bash
cd /Users/miguelordonez/Desktop/foundary
source venv/bin/activate
python list_deployments.py
```

Deberías ver tu deployment listado.

---

## Paso 8: Probar el agente

```bash
python agents/hr_policies/hr_agent.py
```

Si todo está bien, el agente debería responder a las preguntas.

---

## Troubleshooting

### Error: "Region not supported"

Claude solo está disponible en algunas regiones:
- **East US 2**
- **Sweden Central**
- **West US 3**

Si tu proyecto está en otra región, usa GPT-4o en su lugar.

### Error: "Quota exceeded" o "Insufficient quota"

1. Ve a **"Quotas"** en Azure AI Studio
2. Solicita aumento de quota para el modelo
3. O usa un modelo con quota disponible

### Error: "Model not available"

Tu suscripción puede no tener acceso a Claude. Opciones:
1. Solicitar acceso en Azure Portal
2. Usar GPT-4o mientras tanto
3. Contactar soporte de Azure

---

## Modelos recomendados para el agente de HR

| Modelo | Ventajas | Desventajas |
|--------|----------|-------------|
| **Claude Sonnet 4.5** | 1M tokens contexto, excelente español, barato | Requiere acceso especial |
| **Claude Opus 4.6** | Más inteligente, mejor razonamiento | Más caro, más lento |
| **GPT-4o** | Disponible inmediatamente, rápido | Menos contexto (128k tokens) |
| **GPT-4** | Buena calidad, familiar | Más caro que GPT-4o |

Para el agente de HR, **Claude Sonnet 4.5** o **GPT-4o** son las mejores opciones.

---

## Siguiente paso

**➡️ Ve a https://ai.azure.com y despliega un modelo**

Cuando termines, avísame y seguimos con las pruebas del agente. 🚀
