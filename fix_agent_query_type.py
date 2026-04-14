"""
Actualiza el agente para usar SEMANTIC query en lugar de VECTOR_SEMANTIC_HYBRID
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType
)
from azure.identity import DefaultAzureCredential

load_dotenv()

project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
credential = DefaultAzureCredential()
project = AIProjectClient(endpoint=project_endpoint, credential=credential)

print("🔧 Actualizando query type del agente...")

instructions = """
Eres el Asistente Inteligente de Contratos para Grupo Rocka.

TU ROL:
- Ayudar a empleados de Grupo Rocka (Betterware y Jafra) a encontrar información en contratos
- Responder preguntas sobre fechas, montos, proveedores, clientes, y cláusulas
- Proporcionar información precisa y verificable de los documentos

TU COMPORTAMIENTO:
- SIEMPRE cita la fuente del contrato cuando respondas (nombre del archivo o título)
- Si encuentras información en múltiples contratos, menciónalos todos
- Si NO encuentras información, di claramente: "No encontré esa información en los contratos disponibles"
- NO inventes información - solo usa lo que está en los documentos indexados
- Si la pregunta es ambigua, pide aclaración
- Para comparaciones, usa formato de tabla o bullet points
- Incluye detalles relevantes como fechas, montos, y nombres completos

TONO:
- Profesional pero accesible
- Claro y conciso
- Orientado a la acción

RESTRICCIONES:
- SOLO responde preguntas sobre contratos
- NO respondas preguntas personales, técnicas generales, o fuera del scope
"""

try:
    # Configurar con SEMANTIC query (sin vector híbrido)
    search_tool = AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[
                AISearchIndexResource(
                    project_connection_id="contratos-search",
                    index_name="contratos-rocka-index",
                    query_type=AzureAISearchQueryType.SEMANTIC,  # Cambio aquí
                    top_k=5
                )
            ]
        )
    )
    
    print(f"   ✅ Query type cambiado a SEMANTIC")
    
    # Crear nueva versión
    agent = project.agents.create_version(
        agent_name="AsistenteContratos-GrupoRocka",
        definition=PromptAgentDefinition(
            model="gpt-5.4-mini",
            instructions=instructions,
            tools=[search_tool]
        )
    )
    
    print(f"\n✅ Agente actualizado!")
    print(f"   Versión: {agent.version}")
    print(f"   Query type: SEMANTIC (compatible con nuestro índice)")
    print(f"\n🎯 Prueba de nuevo en la UI!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
