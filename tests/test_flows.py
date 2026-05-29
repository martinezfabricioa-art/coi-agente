#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test automático de flujos de retiro y envío."""

import asyncio
import sys
import os
import io

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
os.chdir(root_dir)

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial


async def test_flujo_retiro():
    """Simula flujo de retiro en sucursal."""
    print("\n" + "="*60)
    print("FLUJO 1: RETIRO EN SUCURSAL (sin pago previo)")
    print("="*60 + "\n")

    telefono = "test-retiro-001"
    await limpiar_historial(telefono)

    # Paso 1: Cliente pide productos
    msg1 = "Quiero 2 merluzas frescas y 1 camarones congelados"
    print(f"Cliente: {msg1}")
    historial = await obtener_historial(telefono)
    resp1 = await generar_respuesta(msg1, historial, telefono)
    print(f"El Tibu: {resp1}\n")
    await guardar_mensaje(telefono, "user", msg1)
    await guardar_mensaje(telefono, "assistant", resp1)

    # Paso 2: Cliente confirma
    msg2 = "Sí, confirmo"
    print(f"Cliente: {msg2}")
    historial = await obtener_historial(telefono)
    resp2 = await generar_respuesta(msg2, historial, telefono)
    print(f"El Tibu: {resp2}\n")
    await guardar_mensaje(telefono, "user", msg2)
    await guardar_mensaje(telefono, "assistant", resp2)

    # Paso 3: Cliente elige retiro
    msg3 = "Retiro en sucursal"
    print(f"Cliente: {msg3}")
    historial = await obtener_historial(telefono)
    resp3 = await generar_respuesta(msg3, historial, telefono)
    print(f"El Tibu: {resp3}\n")
    await guardar_mensaje(telefono, "user", msg3)
    await guardar_mensaje(telefono, "assistant", resp3)

    # Validar que aparezca el alias en respuesta
    if "pescaderia.rincon22" in resp3:
        print("✓ ALIAS VISIBLE EN RETIRO\n")
    else:
        print("✗ ADVERTENCIA: Alias no aparece en respuesta de retiro\n")


async def test_flujo_envio():
    """Simula flujo de envío a domicilio."""
    print("\n" + "="*60)
    print("FLUJO 2: ENVÍO A DOMICILIO (con pago previo)")
    print("="*60 + "\n")

    telefono = "test-envio-001"
    await limpiar_historial(telefono)

    # Paso 1: Cliente pide productos
    msg1 = "Quiero 1 merluza congelada y 1 atún en lata"
    print(f"Cliente: {msg1}")
    historial = await obtener_historial(telefono)
    resp1 = await generar_respuesta(msg1, historial, telefono)
    print(f"El Tibu: {resp1}\n")
    await guardar_mensaje(telefono, "user", msg1)
    await guardar_mensaje(telefono, "assistant", resp1)

    # Paso 2: Cliente confirma
    msg2 = "Sí, confirmo"
    print(f"Cliente: {msg2}")
    historial = await obtener_historial(telefono)
    resp2 = await generar_respuesta(msg2, historial, telefono)
    print(f"El Tibu: {resp2}\n")
    await guardar_mensaje(telefono, "user", msg2)
    await guardar_mensaje(telefono, "assistant", resp2)

    # Paso 3: Cliente elige envío
    msg3 = "Envío a domicilio"
    print(f"Cliente: {msg3}")
    historial = await obtener_historial(telefono)
    resp3 = await generar_respuesta(msg3, historial, telefono)
    print(f"El Tibu: {resp3}\n")
    await guardar_mensaje(telefono, "user", msg3)
    await guardar_mensaje(telefono, "assistant", resp3)

    # Validar que aparezca el alias y pida comprobante
    checks = []
    if "pescaderia.rincon22" in resp3:
        checks.append("✓ ALIAS VISIBLE EN ENVÍO")
    else:
        checks.append("✗ ADVERTENCIA: Alias no aparece en envío")

    if "comprobante" in resp3.lower():
        checks.append("✓ PIDE COMPROBANTE")
    else:
        checks.append("✗ ADVERTENCIA: No pide comprobante")

    for check in checks:
        print(check)
    print()


async def test_buscar_precio():
    """Simula búsqueda de precio de un producto."""
    print("\n" + "="*60)
    print("FLUJO 3: BUSCAR PRECIO")
    print("="*60 + "\n")

    telefono = "test-precio-001"
    await limpiar_historial(telefono)

    # Paso 1: Cliente pregunta por múltiples opciones (merluza sin especificar)
    msg1 = "Cuanto cuesta la merluza?"
    print(f"Cliente: {msg1}")
    historial = await obtener_historial(telefono)
    resp1 = await generar_respuesta(msg1, historial, telefono)
    print(f"El Tibu: {resp1}\n")
    await guardar_mensaje(telefono, "user", msg1)
    await guardar_mensaje(telefono, "assistant", resp1)

    # Paso 2: Cliente pregunta por variante específica
    msg2 = "Cuanto cuesta la merluza fresca?"
    print(f"Cliente: {msg2}")
    historial = await obtener_historial(telefono)
    resp2 = await generar_respuesta(msg2, historial, telefono)
    print(f"El Tibu: {resp2}\n")
    await guardar_mensaje(telefono, "user", msg2)
    await guardar_mensaje(telefono, "assistant", resp2)

    # Paso 3: Cliente pregunta por producto que no existe
    msg3 = "Tienen langostinos?"
    print(f"Cliente: {msg3}")
    historial = await obtener_historial(telefono)
    resp3 = await generar_respuesta(msg3, historial, telefono)
    print(f"El Tibu: {resp3}\n")
    await guardar_mensaje(telefono, "user", msg3)
    await guardar_mensaje(telefono, "assistant", resp3)

    # Validaciones
    checks = []
    resp1_lower = resp1.lower()
    if ("fresca" in resp1_lower or "fresco" in resp1_lower) and ("congelada" in resp1_lower or "congelado" in resp1_lower):
        checks.append("✓ MUESTRA MÚLTIPLES OPCIONES")
    else:
        checks.append("✗ ADVERTENCIA: No muestra múltiples opciones")

    if "$" in resp2:
        checks.append("✓ RETORNA PRECIO CUANDO EXISTE")
    else:
        checks.append("✗ ADVERTENCIA: No retorna precio")

    if "stock" in resp3.lower() or "disponible" in resp3.lower():
        checks.append("✓ INDICA NO DISPONIBLE CUANDO FALTA")
    else:
        checks.append("✗ ADVERTENCIA: No indica producto no disponible")

    for check in checks:
        print(check)
    print()


async def main():
    await inicializar_db()
    await test_flujo_retiro()
    await test_flujo_envio()
    await test_buscar_precio()

    print("\n" + "="*60)
    print("Tests completados")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
