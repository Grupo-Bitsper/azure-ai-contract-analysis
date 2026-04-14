# Foundry Development Context — Miguel / Grupo Bitsper

## Quién soy
- 24 años, co-founder de BitsPerFoods (SaaS POS para restaurantes) y ByMike (canal YouTube/TikTok)
- Stack actual: Supabase, React Native/Expo, MCP servers en producción, Claude Code de la A a la Z
- Construí un SaaS en producción en 4 meses con app nativa + web app
- Uso AI de forma seria hace 7 meses — no soy principiante

## Por qué estoy aquí ahora
Mi papá es Microsoft Partner — implementa Dynamics 365, M365, CRM para clientes enterprise en México.
Su cliente más grande: **Vidanta** (cadena hotelera).
Mi socio y yo queremos ser el **brazo pro-code de Foundry** dentro del negocio de mi papá.
Tenemos junta mañana para proponer esto formalmente.

## El negocio que queremos construir
- Construir agentes en Microsoft Foundry para los clientes enterprise de mi papá
- Ellos ya tienen: Dynamics 365, M365, SharePoint, Azure
- Nosotros aportamos: arquitectura, código, MCP servers custom, Claude Code
- Mi papá aporta: relación con el cliente, confianza, canal de ventas
- Modelo: proyecto inicial ($10k-$20k USD) + retainer mensual ($1.5k-$2.5k USD)

## Insight clave del negocio
> "AI sin contexto no es nada. El valor está en construir AI sobre software operativo que ya acumula datos."
- BitsPerFoods: agente sobre POS (datos de ventas, clientes, lealtad en Supabase)
- Clientes de mi papá: agente sobre Dynamics/M365 (datos ERP ya existentes)
- Microsoft ya resuelve permisos/seguridad automáticamente via Entra ID — ventaja enorme vs agencias random

---

## Microsoft Foundry — Lo que necesito saber

### Qué es
- PaaS de Microsoft para construir agentes AI pro-code
- Foundry Agent Service: **gratis** como plataforma, pagas por tokens y conexiones
- Copilot Studio corre ENCIMA de Foundry (es el low-code layer)
- Portal en: `ai.azure.com`

### Las 3 capas de inteligencia
- **Work IQ** → contexto de empleados (emails, Teams, calendar de M365)
- **Fabric IQ** → contexto del negocio (Power BI, Dynamics, Azure SQL)
- **Foundry IQ** → RAG sobre todo el conocimiento (SharePoint, docs, web) — respeta permisos automáticamente

### Modelos disponibles
- Claude Opus 4.6 y Sonnet 4.6 disponibles en Foundry (1M token context, adaptive thinking)
- GPT-4, GPT-5.4, Llama, Mistral, Grok, DeepSeek — más de 11,000 modelos
- Prefiero usar Claude (ya conozco su comportamiento, Claude Code lo domina)

### Tipos de agentes en Foundry
1. **Prompt agents** — solo configuración, sin código. Para prototipos rápidos
2. **Workflow agents** — YAML o visual builder, multi-step, human-in-the-loop
3. **Hosted agents** — código real en contenedor, cualquier framework. AQUÍ es donde trabajo yo

### Frameworks soportados
- Microsoft Agent Framework (nativo)
- LangGraph
- Tu propio código en contenedor
- Todos los MCP servers — con OAuth passthrough y private networking

### Seguridad automática (ventaja de venta)
- Hereda permisos de Entra ID (Active Directory)
- Usuario solo ve lo que ya podía ver en SharePoint/Dynamics
- Sin código extra — automático
- Auditoría completa de cada query
- Compliance ISO/SOC2 ya incluido en Azure

---

## Stack para este proyecto

### Para clientes de mi papá (enterprise)
```
Claude en Foundry (modelo preferido)
+ MCP servers custom a sistemas del cliente
+ Foundry IQ para RAG sobre SharePoint/Dynamics
+ Permisos heredados de Entra ID automáticamente
+ Agent 365 para gobernanza ($15/user/mes — GA mayo 2026)
+ Dashboard custom de administración (lo construimos nosotros)
```

### Para BitsPerFoods (mi SaaS propio) — NO usar Foundry
```
API de Anthropic directo
+ Supabase como contexto operativo
+ MCP servers propios
+ LangChain o directo API Anthropic
```
Foundry no tiene sentido para SaaS propio — vendor lock-in, costo innecesario, clientes SMB sin Azure.

---

## Setup inicial que necesito hacer

### 1. Azure account
```bash
# Ir a portal.azure.com
# Crear cuenta — $200 USD crédito gratis 30 días
# Crear Azure subscription
```

### 2. Instalar SDK
```bash
pip install azure-ai-projects
pip install azure-ai-agents
pip install azure-identity
```

### 3. Portal de Foundry
```
ai.azure.com → crear Foundry project
```

### 4. Autenticación
```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

credential = DefaultAzureCredential()
client = AIProjectClient(
    endpoint="https://<your-project>.services.ai.azure.com",
    credential=credential
)
```

---

## Caso de uso piloto (primer proyecto para Vidanta)

**Agente de políticas HR para empleados**
- Fuente: documentos de políticas en SharePoint de Vidanta
- Usuarios: empleados internos via Teams
- Integración: solo SharePoint + Teams
- Tiempo estimado: 3 semanas
- Riesgo: mínimo
- Precio sugerido: $10,000-$15,000 USD + retainer $2,000/mes

Por qué este primero:
- Simple técnicamente
- ROI obvio para el cliente
- Sin integraciones complejas
- Construye caso de éxito con logo Vidanta
- Demuestra la seguridad automática de permisos

---

## Flujo de trabajo con Claude Code

```
1. UI de Foundry (yo manualmente):
   → Conectar SharePoint del cliente (punto y click)
   → Configurar Foundry IQ knowledge base
   → Configurar permisos y conexiones

2. Claude Code (el trabajo pesado):
   → Lógica del agente en SDK
   → MCP servers custom si se necesitan
   → Dashboard de administración
   → Tests y deployment

3. Cliente ve:
   → Agente funcionando en Teams
   → Dashboard custom para IT
   → Métricas en portal de Foundry
```

---

## Recursos clave
- Portal Foundry: `ai.azure.com`
- Docs: `learn.microsoft.com/azure/foundry`
- SDK docs: `learn.microsoft.com/azure/ai-foundry-agent-service`
- Pricing Foundry: `azure.microsoft.com/pricing/details/foundry-agent-service`

---

## Notas importantes
- Foundry Agent Service es GA desde marzo 2026
- Claude Sonnet 4.6 disponible en Foundry (Global Standard, East US 2 y Sweden Central)
- PromptFlow se depreca — migrar a Microsoft Framework Workflows antes de enero 2027
- Agent 365 GA el 1 de mayo 2026 a $15/user/mes
- Microsoft 365 E7 disponible mayo 2026 a $99/user/mes (incluye Copilot + Agent 365)
