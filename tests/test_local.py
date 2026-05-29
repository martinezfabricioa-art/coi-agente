# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

"""
Probá a El Tibu sin necesitar WhatsApp.
Simula una conversación en la terminal como si fueras un cliente de Pescadería Rincón.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial

TELEFONO_TEST = "test-local-001"


async def main():
    """Loop principal del chat de prueba."""
    # Configurar encoding a UTF-8 para emojis
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    await inicializar_db()

    print()
    print("=" * 55)
    print("   AgentKit — Test Local | Pescadería Rincón")
    print("   Chateando con: El Tibu")
    print("=" * 55)
    print()
    print("  Escribí mensajes como si fueras un cliente de la pescadería.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    while True:
        try:
            mensaje = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        # Obtener historial ANTES de guardar (brain.py agrega el mensaje actual)
        historial = await obtener_historial(TELEFONO_TEST)

        # Generar respuesta
        print("\nEl Tibu: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial, TELEFONO_TEST)
        print(respuesta)
        print()

        # Guardar mensaje del usuario y respuesta del agente
        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
