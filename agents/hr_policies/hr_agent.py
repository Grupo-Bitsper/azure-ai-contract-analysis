"""
Agente de Políticas HR para Vidanta
Responde preguntas de empleados sobre políticas de RH usando SharePoint como fuente
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from typing import Optional

load_dotenv()


class VidantaHRAgent:
    """
    Agente especializado en políticas de HR para Vidanta

    Características:
    - RAG sobre documentos de SharePoint (via Foundry IQ)
    - Respuestas en español
    - Tono profesional y empático
    - Respeta permisos de Entra ID automáticamente
    """

    def __init__(self, agent_name: Optional[str] = None):
        """
        Inicializa el agente de HR

        Args:
            agent_name: Nombre del agente existente. Si None, crea uno nuevo.
        """
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT requerido en .env")

        # Usar DefaultAzureCredential para autenticación OAuth
        # Requiere haber ejecutado: az login
        credential = DefaultAzureCredential()

        self.project = AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        )

        # Obtener cliente OpenAI para ejecutar agente
        self.openai = self.project.get_openai_client()

        self.agent = None
        self.agent_name = agent_name or "AsistenteRH-Vidanta"

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

    def _create_agent(self):
        """Crea el agente con configuración específica para HR"""

        instructions = """
        Eres el Asistente de Recursos Humanos de Vidanta.

        TU ROL:
        - Ayudar a empleados de Vidanta a entender las políticas de RH
        - Responder preguntas sobre beneficios, vacaciones, horarios, código de conducta, etc.
        - Proporcionar información clara y precisa basada en los documentos oficiales

        TU COMPORTAMIENTO:
        - Siempre responde en español
        - Sé profesional pero amigable y empático
        - Si no tienes la información en los documentos, di "No encontré esa información en las políticas disponibles. Te sugiero contactar directamente a RH."
        - No inventes información - solo usa lo que está en los documentos
        - Si la pregunta es ambigua, pide aclaración
        - Proporciona la fuente del documento cuando sea posible

        TONO:
        - Formal pero cercano
        - Empático con las preocupaciones de los empleados
        - Claro y conciso

        SCOPE:
        - SOLO responde preguntas relacionadas con políticas de RH de Vidanta
        - No respondas preguntas personales, técnicas de IT, o fuera del scope de RH
        - Si te preguntan algo fuera de scope, redirige educadamente
        """

        print(f"\n🤖 Creando agente '{self.agent_name}'...")

        try:
            # Crear agente con GPT-4o-mini (disponible sin registro)
            # Cambiar a "claude-sonnet-4-5-20250929" cuando tengas cuota aprobada
            self.agent = self.project.agents.create_version(
                agent_name=self.agent_name,
                definition=PromptAgentDefinition(
                    model="gpt-4o-mini",  # Disponible sin registro
                    instructions=instructions,
                    # tools=[
                    #     # Aquí se agregaría la configuración de Foundry IQ
                    #     # para conectar con SharePoint cuando esté configurado
                    #     {
                    #         "type": "foundry_search",
                    #         "foundry_search": {
                    #             "knowledge_base_id": "SHAREPOINT_KB_ID"
                    #         }
                    #     }
                    # ]
                )
            )

            print(f"✅ Agente creado exitosamente")
            print(f"   Nombre: {self.agent.name}")
            print(f"   Versión: {self.agent.version}")
            print(f"   ID: {self.agent.id}")

        except Exception as e:
            print(f"❌ Error al crear agente: {str(e)}")
            raise

    def ask(self, question: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
        """
        Hace una pregunta al agente

        Args:
            question: Pregunta del empleado
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

            # Enviar mensaje y obtener respuesta
            response = self.openai.responses.create(
                conversation=conversation_id,
                extra_body={
                    "agent_reference": {
                        "name": self.agent_name,
                        "type": "agent_reference"
                    }
                },
                input=question
            )

            answer = response.output_text

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

        print("\n" + "="*60)
        print("💼 Asistente de RH - Vidanta")
        print("="*60)
        print("Haz preguntas sobre políticas de recursos humanos.")
        print("Escribe 'salir' para terminar.\n")

        conversation_id = None  # Mantener contexto de conversación

        while True:
            try:
                question = input("👤 Tu pregunta: ").strip()

                if question.lower() in ['salir', 'exit', 'quit']:
                    print("\n👋 ¡Hasta luego!")
                    break

                if not question:
                    continue

                response, conversation_id = self.ask(question, conversation_id)
                print()  # Línea en blanco

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


def demo_hr_agent():
    """Demo del agente de HR"""

    print("="*60)
    print("🚀 Demo: Agente de Políticas HR - Vidanta")
    print("="*60)

    # Crear agente
    agent = VidantaHRAgent()

    # Preguntas de prueba
    preguntas = [
        "¿Cuántos días de vacaciones tengo al año?",
        "¿Cuál es la política de home office?",
        "¿Qué beneficios médicos ofrece la empresa?",
    ]

    print("\n📋 Probando con preguntas de ejemplo:\n")

    conversation_id = None  # Mantener contexto entre preguntas
    for pregunta in preguntas:
        print("-" * 60)
        _, conversation_id = agent.ask(pregunta, conversation_id)
        print()

    # Opción de chat interactivo
    print("\n¿Quieres hacer más preguntas? (s/n): ", end="")
    respuesta = input().strip().lower()

    if respuesta == 's':
        agent.chat_session()

    # Cleanup
    agent.cleanup()

    print("\n" + "="*60)
    print("✅ Demo completada")
    print("="*60)


if __name__ == "__main__":
    try:
        demo_hr_agent()
    except Exception as e:
        print(f"\n❌ Error en la demo: {str(e)}")
        import traceback
        traceback.print_exc()
