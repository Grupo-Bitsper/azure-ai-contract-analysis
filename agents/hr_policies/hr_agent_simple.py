"""
Versión simplificada del agente de HR usando OpenAI SDK directamente
(mientras se aprueba la cuota en Foundry)
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


class SimpleHRAgent:
    """Versión simple del agente de HR usando Azure OpenAI directo"""

    def __init__(self):
        """Inicializa el cliente de OpenAI"""

        api_key = os.getenv("AZURE_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        if not api_key or not endpoint:
            raise ValueError("AZURE_API_KEY y AZURE_OPENAI_ENDPOINT requeridos")

        # Cliente de Azure OpenAI
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )

        self.system_prompt = """
        Eres el Asistente de Recursos Humanos de Vidanta.

        TU ROL:
        - Ayudar a empleados de Vidanta a entender las políticas de RH
        - Responder preguntas sobre beneficios, vacaciones, horarios, código de conducta, etc.
        - Proporcionar información clara y precisa

        TU COMPORTAMIENTO:
        - Siempre responde en español
        - Sé profesional pero amigable y empático
        - Si no tienes la información, di "No tengo esa información específica. Te sugiero contactar directamente a RH."
        - Sé claro y conciso

        SCOPE:
        - SOLO responde preguntas relacionadas con políticas de RH de Vidanta
        - Si te preguntan algo fuera de scope, redirige educadamente
        """

        self.conversation_history = []

        print("✅ Cliente de Azure OpenAI inicializado")
        print(f"   Endpoint: {endpoint}")

    def ask(self, question: str, model: str = None) -> str:
        """
        Hace una pregunta al agente

        Args:
            question: Pregunta del empleado
            model: Deployment name del modelo (default: usa AZURE_OPENAI_DEPLOYMENT del .env)

        Returns:
            Respuesta del agente
        """
        # Usar deployment del .env si no se especifica
        if model is None:
            model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")

        print(f"\n💬 Pregunta: {question}")

        # Agregar pregunta al historial
        self.conversation_history.append({
            "role": "user",
            "content": question
        })

        try:
            # Crear mensajes con system prompt + historial
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history

            # Llamar a Azure OpenAI
            response = self.client.chat.completions.create(
                model=model,  # Deployment name
                messages=messages,
                temperature=0.7,
                max_completion_tokens=800  # GPT-5.4 usa max_completion_tokens
            )

            answer = response.choices[0].message.content

            # Agregar respuesta al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": answer
            })

            print(f"\n🤖 Respuesta:\n{answer}")

            return answer

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"\n❌ {error_msg}")

            if "DeploymentNotFound" in str(e):
                print("\n💡 El modelo especificado no existe.")
                print("   Necesitas crear un deployment en Azure OpenAI primero:")
                print("   1. Ve a https://portal.azure.com")
                print("   2. Busca 'Azure OpenAI'")
                print("   3. Abre tu recurso de OpenAI")
                print("   4. Ve a 'Model deployments'")
                print("   5. Crea un deployment con GPT-3.5-turbo")

            return error_msg

    def chat(self):
        """Sesión de chat interactiva"""

        print("\n" + "="*60)
        print("💼 Asistente de RH - Vidanta (Versión Simple)")
        print("="*60)
        print("Haz preguntas sobre políticas de recursos humanos.")
        print("Escribe 'salir' para terminar.\n")

        while True:
            try:
                question = input("👤 Tu pregunta: ").strip()

                if question.lower() in ['salir', 'exit', 'quit']:
                    print("\n👋 ¡Hasta luego!")
                    break

                if not question:
                    continue

                self.ask(question)
                print()

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break


def demo():
    """Demo básico"""

    print("="*60)
    print("🚀 Demo: Agente de HR Simple (Azure OpenAI directo)")
    print("="*60)
    print("\nℹ️  Esta versión usa Azure OpenAI directamente")
    print("   No requiere Foundry ni cuotas especiales")
    print("")

    try:
        agent = SimpleHRAgent()

        # Preguntas de prueba
        preguntas = [
            "¿Cuántos días de vacaciones tengo al año?",
            "¿Cuál es la política de home office?",
        ]

        print("\n📋 Probando con preguntas de ejemplo:\n")

        for pregunta in preguntas:
            print("-" * 60)
            agent.ask(pregunta)  # Usa el deployment del .env automáticamente
            print()

        # Chat interactivo
        print("\n¿Quieres continuar con chat interactivo? (s/n): ", end="")
        try:
            respuesta = input().strip().lower()
            if respuesta == 's':
                agent.chat()
        except:
            pass

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo()
