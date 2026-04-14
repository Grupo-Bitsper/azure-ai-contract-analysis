#!/usr/bin/env python3
"""
Interfaz de chat interactiva para el Agente de Contratos de Grupo Rocka
Ejecuta: python agents/contratos_rocka/chat.py
"""
from contratos_agent import ContratosRockaAgent


def main():
    """Inicia sesión de chat con el agente de contratos"""

    print("\n" + "="*70)
    print("📄 Asistente Inteligente de Contratos - Grupo Rocka")
    print("="*70)
    print("\nConectando con Azure AI Search...")

    try:
        # Crear instancia del agente
        agent = ContratosRockaAgent()

        print("\n✅ Agente listo para responder preguntas sobre contratos")
        print("\n" + "-"*70)
        print("Ejemplos de preguntas:")
        print("  • ¿Cuándo vence el contrato con Betterware?")
        print("  • ¿Cuál es el monto del contrato de Microsoft Dynamics?")
        print("  • ¿Quién es el proveedor de servicios?")
        print("  • ¿Qué cláusulas tiene el contrato sobre propiedad intelectual?")
        print("  • Compara los montos de los contratos de Jafra y Betterware")
        print("-"*70)

        # Iniciar chat interactivo
        agent.chat_session()

    except KeyboardInterrupt:
        print("\n\n👋 Sesión terminada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("✅ Sesión finalizada")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
