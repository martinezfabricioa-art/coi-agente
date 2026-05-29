#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Casos de prueba predefinidos para validar cálculos."""

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


# Casos de prueba: (nombre, pasos de conversación)
CASOS = [
    (
        "CASO 1: Retiro simple (1 producto)",
        [
            "Quiero 1 merluza fresca",
            "Sí, confirmo",
            "Retiro en sucursal"
        ]
    ),
    (
        "CASO 2: Retiro múltiple (3 productos)",
        [
            "Dame 2 merluza fresca, 1 camarones y 1 atún en lata",
            "Sí",
            "Retiro"
        ]
    ),
    (
        "CASO 3: Envío a domicilio (con pago)",
        [
            "Quiero 1 salmón fresco y 1 vieiras",
            "Confirmo",
            "Envío a domicilio"
        ]
    ),
    (
        "CASO 4: Buscar múltiples opciones",
        [
            "Cuanto cuesta la merluza?",
            "Quiero 3 merluza fresca",
            "Confirmo",
            "Retiro"
        ]
    ),
    (
        "CASO 5: Producto no disponible",
        [
            "Tienen langostinos?",
            "Dame 2 camarones en su lugar",
            "Confirmo",
            "Retiro"
        ]
    ),
]


async def ejecutar_caso(nombre, pasos):
    """Ejecuta un caso de prueba."""
    print("\n" + "="*70)
    print(f"  {nombre}")
    print("="*70)

    telefono = f"test-caso-{nombre.split(':')[0].lower().replace(' ', '-')}"
    await limpiar_historial(telefono)

    for i, paso in enumerate(pasos, 1):
        print(f"\n[Paso {i}]")
        print(f"Cliente: {paso}")

        historial = await obtener_historial(telefono)
        respuesta = await generar_respuesta(paso, historial, telefono)

        # Truncar respuesta si es muy larga
        if len(respuesta) > 500:
            print(f"El Tibu: {respuesta[:500]}...\n[respuesta truncada]")
        else:
            print(f"El Tibu: {respuesta}")

        await guardar_mensaje(telefono, "user", paso)
        await guardar_mensaje(telefono, "assistant", respuesta)

        # Validaciones
        validaciones = []
        if "$" in respuesta:
            validaciones.append("✓ Precio/total")
        if "confirmado" in respuesta.lower():
            validaciones.append("✓ Pedido confirmado")
        if "pescaderia.rincon22" in respuesta:
            validaciones.append("✓ Alias")
        if "stock" in respuesta.lower():
            validaciones.append("✓ Producto no disponible")

        if validaciones:
            print(f"\nValidaciones: {', '.join(validaciones)}")


async def main():
    await inicializar_db()

    print("\n" + "="*70)
    print("  EJECUCIÓN DE CASOS DE PRUEBA")
    print("="*70)

    for nombre, pasos in CASOS:
        try:
            await ejecutar_caso(nombre, pasos)
        except Exception as e:
            print(f"\n✗ ERROR en {nombre}: {e}")

    print("\n\n" + "="*70)
    print("  TODOS LOS CASOS COMPLETADOS")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
