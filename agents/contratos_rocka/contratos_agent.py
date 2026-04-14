"""
Agente de Contratos para Grupo Rocka
Búsqueda inteligente de contratos usando Azure AI Search con búsqueda directa
"""
import os
import json
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from typing import Optional, List, Dict, Any

load_dotenv()


class ContratosRockaAgent:
    """
    Agente especializado en búsqueda de contratos para Grupo Rocka

    Características:
    - RAG sobre contratos con Azure AI Search (búsqueda directa)
    - Hybrid search (keyword + semantic ranking)
    - Respuestas con citación de fuentes
    - Respuestas en español profesional
    """

    def __init__(self, agent_name: Optional[str] = None):
        """
        Inicializa el agente de contratos

        Args:
            agent_name: Nombre del agente existente. Si None, crea uno nuevo.
        """
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "contratos-rocka-index")

        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT requerido en .env")

        if not search_endpoint:
            raise ValueError("AZURE_SEARCH_ENDPOINT requerido en .env")

        if not search_key:
            raise ValueError("AZURE_SEARCH_KEY requerido en .env")

        # Usar DefaultAzureCredential para autenticación OAuth del proyecto
        credential = DefaultAzureCredential()

        self.project = AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        )

        # Obtener cliente OpenAI para ejecutar agente
        self.openai = self.project.get_openai_client()

        # Cliente de búsqueda directo
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )

        self.index_name = index_name
        self.agent = None
        self.agent_name = agent_name or "AsistenteContratos-GrupoRocka"

        if agent_name:
            try:
                # Intentar obtener agente existente
                self.agent = self.project.agents.get(agent_name=self.agent_name)
                print(f"✅ Usando agente existente: {self.agent_name} (v{self.agent.version})")
            except:
                # Si no existe, crear uno nuevo
                self._create_agent()
        else:
            self._create_agent()

    def search_contracts(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Busca en el índice de contratos

        Args:
            query: Query de búsqueda
            top_k: Número máximo de resultados

        Returns:
            Lista de resultados con contenido y metadata
        """
        try:
            # Búsqueda híbrida (texto + semántica)
            results = self.search_client.search(
                search_text=query,
                select=[
                    "id", "content", "titulo", "tipo_contrato",
                    "proveedor", "cliente", "fecha_contrato",
                    "monto", "moneda", "nombre_archivo"
                ],
                top=top_k,
            )

            # Formatear resultados
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "titulo": result.get("titulo", ""),
                    "tipo_contrato": result.get("tipo_contrato", ""),
                    "proveedor": result.get("proveedor", ""),
                    "cliente": result.get("cliente", ""),
                    "fecha_contrato": result.get("fecha_contrato", ""),
                    "monto": result.get("monto"),
                    "moneda": result.get("moneda", ""),
                    "nombre_archivo": result.get("nombre_archivo", ""),
                    "score": result.get("@search.score", 0)
                })

            return formatted_results

        except Exception as e:
            print(f"❌ Error en búsqueda: {str(e)}")
            return []

    def _create_agent(self):
        """Crea el agente con configuración específica para contratos"""

        instructions = """
Eres el Asistente Inteligente de Contratos para Grupo Rocka.

TU ROL:
- Ayudar a empleados de Grupo Rocka (Betterware y Jafra) a encontrar información en contratos
- Responder preguntas sobre fechas, montos, proveedores, clientes, y cláusulas
- Proporcionar información precisa y verificable de los documentos

CÓMO BUSCAR INFORMACIÓN:
- Tienes acceso a una función `buscar_contratos` que busca en el índice de contratos
- SIEMPRE usa esta función cuando te pregunten sobre contratos
- Pasa la pregunta del usuario directamente a la función

TU COMPORTAMIENTO:
- SIEMPRE cita la fuente del contrato cuando respondas (nombre del archivo o título)
- Si encuentras información en múltiples contratos, menciónalos todos
- Si NO encuentras información, di claramente: "No encontré esa información en los contratos disponibles"
- NO inventes información - solo usa lo que devuelve la función de búsqueda
- Si la pregunta es ambigua, pide aclaración
- Para comparaciones, usa formato de tabla o bullet points
- Incluye detalles relevantes como fechas, montos, y nombres completos

FORMATO DE RESPUESTAS:
- Empieza con la respuesta directa
- Luego agrega los detalles y contexto
- Termina con "Fuente: [nombre del contrato]"

TONO:
- Profesional pero accesible
- Claro y conciso
- Orientado a la acción

RESTRICCIONES:
- SOLO responde preguntas sobre contratos
- NO respondas preguntas personales, técnicas generales, o fuera del scope
- Si te preguntan algo fuera de scope, redirige educadamente
"""

        print(f"\n🤖 Creando agente '{self.agent_name}'...")

        try:
            # Crear agente con GPT-5.4-mini sin tools personalizadas
            # La búsqueda se hará pre-procesando la query del usuario
            self.agent = self.project.agents.create_version(
                agent_name=self.agent_name,
                definition=PromptAgentDefinition(
                    model="gpt-5.4-mini",
                    instructions=instructions
                )
            )

            print(f"✅ Agente creado exitosamente")
            print(f"   Nombre: {self.agent.name}")
            print(f"   Versión: {self.agent.version}")
            print(f"   ID: {self.agent.id}")
            print(f"   Modelo: gpt-5.4-mini")
            print(f"   Índice: {self.index_name}")
            print(f"   🔍 Búsqueda directa configurada")

        except Exception as e:
            print(f"❌ Error al crear agente: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _handle_function_calls(self, run_result) -> Optional[Dict[str, Any]]:
        """
        Procesa las llamadas a funciones del agente

        Args:
            run_result: Resultado de la ejecución del agente

        Returns:
            Resultados de las funciones ejecutadas
        """
        if not hasattr(run_result, 'required_action') or not run_result.required_action:
            return None

        tool_calls = run_result.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "buscar_contratos":
                # Ejecutar búsqueda
                query = function_args.get("query", "")
                print(f"   🔍 Buscando: {query}")

                results = self.search_contracts(query)

                # Formatear resultados para el agente
                if results:
                    formatted = []
                    for idx, r in enumerate(results, 1):
                        monto_str = f"${r['monto']:,.2f} {r['moneda']}" if r['monto'] else "No especificado"
                        formatted.append(f"""
Resultado {idx}:
- Título: {r['titulo']}
- Tipo: {r['tipo_contrato']}
- Proveedor: {r['proveedor']}
- Cliente: {r['cliente']}
- Fecha: {r['fecha_contrato']}
- Monto: {monto_str}
- Archivo: {r['nombre_archivo']}
- Contenido: {r['content'][:300]}...
- Relevancia: {r['score']:.2f}
""")
                    output = "\n".join(formatted)
                else:
                    output = "No se encontraron resultados para esta búsqueda."

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": output
                })

        return {"tool_outputs": tool_outputs} if tool_outputs else None

    def ask(self, question: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
        """
        Hace una pregunta al agente sobre contratos con RAG

        Args:
            question: Pregunta sobre contratos
            conversation_id: ID de conversación existente (para mantener contexto)

        Returns:
            Tuple de (respuesta, conversation_id)
        """
        print(f"\n💬 Pregunta: {question}")

        try:
            # Crear conversación si no existe
            if not conversation_id:
                conversation = self.openai.conversations.create()
                conversation_id = conversation.id
                print(f"   Nueva conversación: {conversation_id}")
            else:
                print(f"   Usando conversación existente: {conversation_id}")

            # Buscar en el índice primero (RAG pattern)
            print(f"   🔍 Buscando en contratos...")
            search_results = self.search_contracts(question, top_k=3)

            # Construir contexto con resultados
            if search_results:
                context = "\n\n=== INFORMACIÓN DE CONTRATOS ===\n\n"
                for idx, r in enumerate(search_results, 1):
                    monto_str = f"${r['monto']:,.2f} {r['moneda']}" if r['monto'] else "No especificado"
                    context += f"""
Documento {idx}: {r['nombre_archivo']}
- Título: {r['titulo']}
- Tipo: {r['tipo_contrato']}
- Proveedor: {r['proveedor']}
- Cliente: {r['cliente']}
- Fecha: {r['fecha_contrato']}
- Monto: {monto_str}

Contenido relevante:
{r['content'][:500]}...

---
"""
                # Agregar contexto a la pregunta
                augmented_question = f"""{context}

=== PREGUNTA DEL USUARIO ===
{question}

Instrucciones: Responde la pregunta usando SOLO la información de los contratos arriba. Si la información no está disponible, dilo claramente."""

                print(f"   ✅ {len(search_results)} resultados encontrados")
            else:
                augmented_question = f"""No se encontraron contratos relevantes para esta pregunta.

PREGUNTA: {question}

Instrucciones: Informa al usuario que no encontraste información sobre esto en los contratos disponibles."""
                print(f"   ⚠️  No se encontraron resultados")

            # Enviar a agente con contexto
            response = self.openai.responses.create(
                conversation=conversation_id,
                extra_body={
                    "agent_reference": {
                        "name": self.agent_name,
                        "type": "agent_reference"
                    }
                },
                input=augmented_question
            )

            answer = response.output_text if hasattr(response, 'output_text') else str(response)

            print(f"\n🤖 Respuesta:\n{answer}")

            return answer, conversation_id

        except Exception as e:
            error_msg = f"Error al procesar pregunta: {str(e)}"
            print(f"\n❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg, conversation_id or ""

    def chat_session(self):
        """Inicia una sesión de chat interactiva con el agente"""

        print("\n" + "="*70)
        print("📄 Asistente de Contratos - Grupo Rocka")
        print("="*70)
        print("Haz preguntas sobre los contratos de Betterware y Jafra.")
        print("Comandos: 'salir' = terminar | '/clear' = nueva conversación\n")

        conversation_id = None

        while True:
            try:
                question = input("👤 Tu pregunta: ").strip()

                if question.lower() in ['salir', 'exit', 'quit']:
                    print("\n👋 ¡Hasta luego!")
                    break

                if question.lower() == '/clear':
                    conversation_id = None
                    print("   🔄 Nueva conversación iniciada\n")
                    continue

                if not question:
                    continue

                response, conversation_id = self.ask(question, conversation_id)
                print()

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")

    def cleanup(self):
        """Elimina el agente"""
        if self.agent_name:
            print(f"\n🗑️  Eliminando agente {self.agent_name}...")
            try:
                self.project.agents.delete(agent_name=self.agent_name)
                print(f"✅ Agente eliminado")
            except Exception as e:
                print(f"❌ Error al eliminar agente: {str(e)}")


def demo_contratos_agent():
    """Demo del agente de contratos"""

    print("="*70)
    print("🚀 Demo: Agente de Contratos - Grupo Rocka")
    print("="*70)

    # Crear agente
    agent = ContratosRockaAgent()

    # Preguntas de prueba
    preguntas = [
        "¿Cuándo vence el contrato con Betterware?",
        "¿Cuál es el monto del contrato de Microsoft Dynamics?",
        "¿Quién es el proveedor de servicios?",
    ]

    print("\n📋 Probando con preguntas de ejemplo:\n")

    conversation_id = None
    for pregunta in preguntas:
        print("-" * 70)
        _, conversation_id = agent.ask(pregunta, conversation_id)
        print()

    # Opción de chat interactivo
    print("\n¿Quieres hacer más preguntas? (s/n): ", end="")
    try:
        respuesta = input().strip().lower()
        if respuesta == 's':
            agent.chat_session()
    except EOFError:
        print("(modo no interactivo)")

    print("\n" + "="*70)
    print("✅ Demo completada")
    print("="*70)


if __name__ == "__main__":
    try:
        demo_contratos_agent()
    except Exception as e:
        print(f"\n❌ Error en la demo: {str(e)}")
        import traceback
        traceback.print_exc()
