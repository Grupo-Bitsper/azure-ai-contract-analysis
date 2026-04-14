"""
Ejemplo básico de agente en Azure Foundry usando Claude
Este ejemplo muestra cómo crear un agente simple y hacerle preguntas
"""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.projects.models import Agent, AgentThread, AgentRun

# Cargar variables de entorno
load_dotenv()

class FoundryAgent:
    """Clase wrapper para manejar agentes de Foundry"""

    def __init__(self):
        """Inicializa el cliente de Foundry"""
        api_key = os.getenv("AZURE_API_KEY")
        project_endpoint = os.getenv("PROJECT_ENDPOINT")

        if not api_key or not project_endpoint:
            raise ValueError("AZURE_API_KEY y PROJECT_ENDPOINT requeridos en .env")

        self.client = AIProjectClient(
            endpoint=project_endpoint,
            credential=AzureKeyCredential(api_key)
        )

        print("✅ Cliente de Foundry inicializado")

    def list_models(self):
        """Lista los modelos disponibles en el proyecto"""
        print("\n🔍 Listando modelos disponibles...")

        try:
            # Esta API puede variar según la versión del SDK
            # Consulta la documentación actualizada de Azure AI Projects
            models = self.client.agents.list_models()

            print("\n📋 Modelos disponibles:")
            for model in models:
                print(f"   • {model.id}")

            return models

        except Exception as e:
            print(f"⚠️  No se pudieron listar los modelos: {str(e)}")
            print("   (Esto es normal si la API aún no está disponible)")
            return []

    def create_agent(
        self,
        name: str,
        instructions: str,
        model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        Crea un agente en Foundry

        Args:
            name: Nombre del agente
            instructions: Instrucciones del sistema para el agente
            model: ID del modelo a usar (default: Claude Sonnet 4.5)

        Returns:
            Agent object
        """
        print(f"\n🤖 Creando agente '{name}'...")

        try:
            agent = self.client.agents.create_agent(
                model=model,
                name=name,
                instructions=instructions
            )

            print(f"✅ Agente creado exitosamente")
            print(f"   ID: {agent.id}")
            print(f"   Modelo: {agent.model}")

            return agent

        except Exception as e:
            print(f"❌ Error al crear agente: {str(e)}")
            raise

    def create_thread(self):
        """Crea un thread (conversación) para el agente"""
        print("\n💬 Creando thread...")

        try:
            thread = self.client.agents.create_thread()
            print(f"✅ Thread creado: {thread.id}")
            return thread

        except Exception as e:
            print(f"❌ Error al crear thread: {str(e)}")
            raise

    def send_message(self, thread_id: str, message: str):
        """Envía un mensaje a un thread"""
        print(f"\n📤 Enviando mensaje: '{message[:50]}...'")

        try:
            msg = self.client.agents.create_message(
                thread_id=thread_id,
                role="user",
                content=message
            )

            print(f"✅ Mensaje enviado")
            return msg

        except Exception as e:
            print(f"❌ Error al enviar mensaje: {str(e)}")
            raise

    def run_agent(self, thread_id: str, agent_id: str):
        """Ejecuta el agente en un thread"""
        print(f"\n▶️  Ejecutando agente...")

        try:
            run = self.client.agents.create_run(
                thread_id=thread_id,
                assistant_id=agent_id
            )

            # Esperar a que termine
            while run.status in ["queued", "in_progress"]:
                import time
                time.sleep(1)
                run = self.client.agents.get_run(
                    thread_id=thread_id,
                    run_id=run.id
                )
                print(f"   Status: {run.status}")

            print(f"✅ Agente terminó con status: {run.status}")
            return run

        except Exception as e:
            print(f"❌ Error al ejecutar agente: {str(e)}")
            raise

    def get_messages(self, thread_id: str):
        """Obtiene todos los mensajes de un thread"""
        print(f"\n📥 Obteniendo mensajes...")

        try:
            messages = self.client.agents.list_messages(thread_id=thread_id)

            print(f"✅ {len(messages.data)} mensajes obtenidos")
            return messages.data

        except Exception as e:
            print(f"❌ Error al obtener mensajes: {str(e)}")
            raise

    def cleanup_agent(self, agent_id: str):
        """Elimina un agente"""
        print(f"\n🗑️  Eliminando agente {agent_id}...")

        try:
            self.client.agents.delete_agent(agent_id=agent_id)
            print(f"✅ Agente eliminado")

        except Exception as e:
            print(f"❌ Error al eliminar agente: {str(e)}")


def demo_basic_agent():
    """Demo de un agente básico"""

    print("="*60)
    print("🚀 Demo: Agente Básico en Azure Foundry")
    print("="*60)

    # Inicializar
    foundry = FoundryAgent()

    # Crear agente
    agent = foundry.create_agent(
        name="Asistente de Prueba",
        instructions="""
        Eres un asistente útil que responde preguntas de forma concisa.
        Responde siempre en español.
        Sé amigable y profesional.
        """
    )

    # Crear conversación
    thread = foundry.create_thread()

    # Enviar mensaje
    foundry.send_message(
        thread_id=thread.id,
        message="Hola, ¿qué es Azure Foundry y para qué sirve?"
    )

    # Ejecutar agente
    foundry.run_agent(
        thread_id=thread.id,
        agent_id=agent.id
    )

    # Obtener respuesta
    messages = foundry.get_messages(thread_id=thread.id)

    print("\n" + "="*60)
    print("💬 Conversación:")
    print("="*60)

    for msg in reversed(messages):
        role = "🧑 Usuario" if msg.role == "user" else "🤖 Agente"
        content = msg.content[0].text.value if msg.content else ""
        print(f"\n{role}:\n{content}")

    # Cleanup
    foundry.cleanup_agent(agent.id)

    print("\n" + "="*60)
    print("✅ Demo completada")
    print("="*60)


if __name__ == "__main__":
    try:
        demo_basic_agent()
    except Exception as e:
        print(f"\n❌ Error en la demo: {str(e)}")
        import traceback
        traceback.print_exc()
