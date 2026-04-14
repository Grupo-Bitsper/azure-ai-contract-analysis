# Azure Foundry - Agentes Enterprise

Proyecto de agentes AI sobre Microsoft Foundry para clientes enterprise.

## 🎯 Objetivo

Construir agentes custom en Microsoft Foundry que se integran con el ecosistema Microsoft 365 de clientes enterprise (Dynamics 365, SharePoint, Teams).

## 🏗️ Stack Técnico

- **Plataforma**: Azure Foundry Agent Service
- **Modelo**: Claude Sonnet/Opus 4.6 (1M token context)
- **SDK**: `azure-ai-projects` + `azure-ai-agents`
- **Integraciones**: SharePoint, Dynamics 365, Teams vía Foundry IQ
- **Seguridad**: Permisos automáticos vía Entra ID

## 📁 Estructura del Proyecto

```
foundary/
├── agents/              # Agentes específicos por caso de uso
│   ├── hr_policies/     # Agente de políticas HR (piloto Vidanta)
│   └── templates/       # Templates reutilizables
├── config/              # Configuraciones
├── docs/                # Documentación
├── examples/            # Ejemplos de uso
├── .env                 # Variables de entorno (NO commitear)
└── foundry-context.md   # Contexto del negocio
```

## 🚀 Setup

1. **Instalar dependencias**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configurar credenciales**:
```bash
cp .env.example .env
# Editar .env con tus credenciales de Azure
```

3. **Probar conexión**:
```bash
python test_connection.py
```

4. **Ejecutar ejemplo básico**:
```bash
python foundry_agent_example.py
```

## 🎯 Proyecto Piloto: Agente de Políticas HR (Vidanta)

**Objetivo**: Agente que responde preguntas de empleados sobre políticas de HR usando documentos de SharePoint.

**Entregables**:
- Agente funcionando en Teams
- Dashboard de administración
- Métricas en portal de Foundry
- Documentación de uso

**Timeline**: 3 semanas

**Pricing**: $10k-$15k USD + $2k/mes retainer

## 📚 Recursos

- Portal Foundry: [ai.azure.com](https://ai.azure.com)
- Docs oficiales: [learn.microsoft.com/azure/foundry](https://learn.microsoft.com/azure/foundry)
- SDK Python: [azure-ai-projects](https://pypi.org/project/azure-ai-projects/)

## 🔐 Seguridad

- ✅ Credenciales en `.env` (git ignored)
- ✅ Permisos heredados de Entra ID automáticamente
- ✅ Auditoría completa de queries
- ✅ Compliance ISO/SOC2 incluido en Azure

## 💼 Modelo de Negocio

- **Proyecto inicial**: $10k-$20k USD
- **Retainer mensual**: $1.5k-$2.5k USD
- **Valor agregado**: Seguridad enterprise + integración nativa con M365

---

**Co-founders**: Miguel + socio (Grupo Bitsper)
**Partner**: Microsoft Partner (implementaciones Dynamics 365)
**Cliente piloto**: Vidanta
