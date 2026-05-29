#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test personalizado: carga casos de prueba y valida cálculos."""

import asyncio
import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
os.chdir(root_dir)

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial


async def test_caso_personalizado():
    """Test interactivo con casos personalizados."""
    await inicializar_db()

    print("\n" + "="*70)
    print("  TEST PERSONALIZADO - PESCADERÍA RINCÓN")
    print("="*70)
    print("\nEscribí tus casos de prueba. Comandos:")
    print("  - 'nuevo'   → Inicia nueva conversación")
    print("  - 'limpiar' → Borra historial actual")
    print("  - 'salir'   → Termina el test")
    print()

    telefono = "test-custom-001"
    historial_activo = False

    while True:
        try:
            mensaje = input("\nVos: ").strip()
        except EOFError:
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "nuevo":
            await limpiar_historial(telefono)
            historial_activo = False
            print("[Nueva conversación iniciada]")
            continue

        if mensaje.lower() == "limpiar":
            await limpiar_historial(telefono)
            print("[Historial borrado]")
            continue

        # Generar respuesta
        historial = await obtener_historial(telefono)
        historial_activo = True

        print("\nEl Tibu: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial, telefono)
        print(respuesta)

        # Guardar en historial
        await guardar_mensaje(telefono, "user", mensaje)
        await guardar_mensaje(telefono, "assistant", respuesta)

        # Validaciones útiles
        if "$" in respuesta:
            print("\n✓ Contiene precio/total")
        if "confirmado" in respuesta.lower():
            print("✓ Pedido registrado")
        if "pescaderia.rincon22" in respuesta:
            print("✓ Alias visible")


if __name__ == "__main__":
    asyncio.run(test_caso_personalizado())
