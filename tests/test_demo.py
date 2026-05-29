#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test de demostración con conversación completa."""

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


async def demo():
    """Demostración de conversación completa."""
    await inicializar_db()

    print("\n" + "="*70)
    print("  PESCADERÍA RINCÓN - DEMO DEL AGENTE EL TIBU")
    print("="*70 + "\n")

    telefono = "demo-cliente"
    await limpiar_historial(telefono)

    conversacion = [
        ("Hola, quiero hacer un pedido", "Saludo inicial"),
        ("Cuanto cuesta la merluza?", "Busca producto con múltiples opciones"),
        ("La fresca está bien", "Elige opción"),
        ("Dame 2 merluza fresca y 1 camarones", "Pide productos específicos"),
        ("Sí, confirmá", "Confirma pedido"),
        ("Retiro en sucursal", "Elige tipo de entrega (sin pago)"),
    ]

    for i, (mensaje, descripcion) in enumerate(conversacion, 1):
        print(f"\n{'-'*70}")
        print(f"PASO {i}: {descripcion}")
        print(f"{'-'*70}\n")

        print(f"Cliente: {mensaje}")

        historial = await obtener_historial(telefono)
        respuesta = await generar_respuesta(mensaje, historial, telefono)

        print(f"\nEl Tibu: {respuesta}\n")

        await guardar_mensaje(telefono, "user", mensaje)
        await guardar_mensaje(telefono, "assistant", respuesta)

    print("\n" + "="*70)
    print("  DEMO COMPLETADA")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo())
