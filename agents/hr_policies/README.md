# Agente de Políticas HR - Vidanta

Agente especializado para responder preguntas de empleados sobre políticas de Recursos Humanos.

## 🎯 Objetivo

Proporcionar a los empleados de Vidanta acceso 24/7 a información sobre:
- Políticas de vacaciones y permisos
- Beneficios médicos y seguros
- Código de conducta
- Horarios y asistencia
- Desarrollo profesional
- Nómina y compensaciones

## 🏗️ Arquitectura

```
Employee (Teams)
    ↓
Agente de HR (Claude Sonnet 4.5)
    ↓
Foundry IQ (RAG)
    ↓
SharePoint (Documentos de políticas)
    ↓
Entra ID (Control de permisos)
```

## 🔐 Seguridad

- **Permisos automáticos**: El agente solo muestra información que el empleado ya puede ver en SharePoint
- **Herencia de Entra ID**: Sin configuración manual de permisos
- **Auditoría**: Todas las consultas quedan registradas
- **Compliance**: ISO/SOC2 incluido vía Azure

## 📊 Casos de Uso

### ✅ Casos Soportados
- "¿Cuántos días de vacaciones tengo?"
- "¿Cuál es la política de trabajo remoto?"
- "¿Qué beneficios médicos tengo?"
- "¿Cómo solicito un permiso?"
- "¿Cuál es el proceso de evaluación de desempeño?"

### ❌ Fuera de Scope
- Información personal de nómina (privada)
- Solicitudes de permisos (debe hacerse en el sistema oficial)
- Quejas de RH (canal oficial)
- Información técnica de IT

## 🚀 Uso

### Básico
```python
from agents.hr_policies.hr_agent import VidantaHRAgent

# Crear agente
agent = VidantaHRAgent()

# Hacer pregunta
respuesta = agent.ask("¿Cuántos días de vacaciones tengo al año?")
print(respuesta)

# Cleanup
agent.cleanup()
```

### Sesión Interactiva
```bash
python agents/hr_policies/hr_agent.py
```

## 📝 Configuración de SharePoint

1. **En Azure Portal** (`ai.azure.com`):
   - Ir a Foundry project
   - Conectar SharePoint del cliente
   - Configurar Foundry IQ knowledge base
   - Seleccionar carpetas con documentos de políticas

2. **Actualizar código**:
   ```python
   tools=[
       {
           "type": "foundry_search",
           "foundry_search": {
               "knowledge_base_id": "SHAREPOINT_KB_ID_AQUI"
           }
       }
   ]
   ```

3. **Probar**:
   ```bash
   python agents/hr_policies/hr_agent.py
   ```

## 📈 Métricas de Éxito

- **Tiempo de respuesta**: < 5 segundos
- **Precisión**: > 95% (respuestas correctas basadas en docs)
- **Satisfacción**: > 4.5/5 (feedback de empleados)
- **Adopción**: > 60% empleados activos en primer mes

## 💰 Pricing

- **Proyecto inicial**: $10,000 - $15,000 USD
  - Setup de infraestructura
  - Integración con SharePoint
  - Configuración de permisos
  - Training del agente
  - Dashboard de admin
  - 2 semanas de soporte

- **Retainer mensual**: $2,000 USD
  - Mantenimiento y actualizaciones
  - Soporte técnico
  - Mejoras al agente
  - Reportes mensuales

## 📅 Timeline

- **Semana 1**: Setup de infraestructura + integración SharePoint
- **Semana 2**: Training del agente + testing
- **Semana 3**: UAT con equipo de RH + ajustes finales
- **Go-live**: Fin de semana 3

## 🎓 Próximos Pasos

1. ✅ Setup inicial de Foundry (COMPLETO)
2. ⏳ Conectar SharePoint de Vidanta
3. ⏳ Configurar Foundry IQ knowledge base
4. ⏳ Training con documentos reales
5. ⏳ Testing con equipo de RH
6. ⏳ Deployment a Teams
7. ⏳ Dashboard de administración
8. ⏳ Go-live

---

**Status**: 🟡 En desarrollo (setup completado, pendiente SharePoint del cliente)
**Owner**: Miguel + socio
**Cliente**: Vidanta
