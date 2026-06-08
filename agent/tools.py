# agent/tools.py — Herramientas del agente Pescadería Rincón
# Generado por AgentKit

"""
Herramientas específicas para Pescadería Rincón.
Casos de uso: Menú de productos, toma de pedidos, notificación al dueño.
"""

import os
import yaml
import logging
from datetime import datetime
from agent.memory import guardar_pedido

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención de Pescadería Rincón y si está abierto ahora."""
    info = cargar_info_negocio()
    ahora = datetime.now()
    dia_semana = ahora.weekday()  # 0=Lunes, 6=Domingo
    hora_actual = ahora.hour

    # Determinar si está abierto según el horario
    # Lunes a Sábado: 10:00-13:30 y 16:00-22:30
    if dia_semana < 6:  # Lunes a Sábado
        esta_abierto = (10 <= hora_actual < 13) or (16 <= hora_actual < 22)
    else:  # Domingo
        esta_abierto = False

    return {
        "horario": info.get("negocio", {}).get("horario", "Lunes a Sábado 10:00-13:30 y 16:00-22:30"),
        "esta_abierto": esta_abierto,
        "dia_actual": ahora.strftime("%A"),
        "hora_actual": ahora.strftime("%H:%M"),
    }


async def buscar_producto(nombre_producto: str) -> dict:
    """
    Busca productos en knowledge/productos.txt y retorna todos los que coinciden.

    Args:
        nombre_producto: Nombre del producto a buscar

    Returns:
        Dict con lista de productos si encuentra, o mensaje de no disponible
    """
    try:
        # Probar múltiples rutas (local, Docker, etc)
        possible_paths = [
            "knowledge/productos.txt",
            "/app/knowledge/productos.txt",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge", "productos.txt")
        ]

        knowledge_file = None
        for path in possible_paths:
            if os.path.exists(path):
                knowledge_file = path
                break

        if not knowledge_file:
            logger.error(f"Archivo de productos no encontrado. Rutas buscadas: {possible_paths}")
            return {"error": "Archivo de productos no encontrado"}

        with open(knowledge_file, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        # Buscar el producto en el contenido
        producto_lower = nombre_producto.lower()
        palabras_clave = producto_lower.split()  # Split por espacios: ["merluza", "fresca"]

        productos_encontrados = []

        # Primera pasada: buscar coincidencia exacta (todas las palabras clave)
        for line in lineas:
            line_lower = line.lower()
            if "-$" in line:
                # Si todas las palabras clave están en la línea
                if all(palabra in line_lower for palabra in palabras_clave):
                    try:
                        partes = line.split("-$")
                        if len(partes) >= 2:
                            precio_str = partes[-1].strip()
                            precio = "$" + precio_str
                            nombre_extraido = partes[0].replace("_", "").strip()
                            productos_encontrados.append({
                                "nombre": nombre_extraido,
                                "precio": precio
                            })
                    except:
                        continue

        # Si encontró coincidencias exactas, retornarlas
        if productos_encontrados:
            return {
                "disponible": True,
                "cantidad": len(productos_encontrados),
                "productos": productos_encontrados
            }

        # Segunda pasada: buscar por palabra principal (primera palabra)
        if palabras_clave:
            palabra_principal = palabras_clave[0]
            for line in lineas:
                line_lower = line.lower()
                if "-$" in line and palabra_principal in line_lower:
                    try:
                        partes = line.split("-$")
                        if len(partes) >= 2:
                            precio_str = partes[-1].strip()
                            precio = "$" + precio_str
                            nombre_extraido = partes[0].replace("_", "").strip()
                            productos_encontrados.append({
                                "nombre": nombre_extraido,
                                "precio": precio
                            })
                    except:
                        continue

        if productos_encontrados:
            return {
                "disponible": True,
                "cantidad": len(productos_encontrados),
                "productos": productos_encontrados
            }

        return {
            "disponible": False,
            "producto": nombre_producto,
            "mensaje": f"'{nombre_producto}' no está disponible en este momento"
        }
    except Exception as e:
        logger.error(f"Error buscando producto: {e}")
        return {"error": str(e)}


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                # Búsqueda simple por coincidencia de texto
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


async def registrar_pedido(telefono: str, items: str, total: str, tipo_entrega: str = "retiro_sucursal", comprobante_id: str = None) -> dict:
    """
    Registra un pedido en la BD y notifica al dueño vía WhatsApp.

    Args:
        telefono: Número de teléfono del cliente
        items: Descripción de items (ej: "2x Merluza fresca, 1x Camarones")
        total: Total del pedido (ej: "$5400")
        tipo_entrega: "retiro_sucursal" o "envio_domicilio"
        comprobante_id: ID de la imagen del comprobante de pago (obligatorio si es envío)

    Returns:
        Dict con pedido_id y estado
    """
    try:
        from agent.memory import Pedido, async_session

        # Determinar estado según tipo de entrega
        if tipo_entrega == "retiro_sucursal":
            estado = "confirmado_retiro"
        elif comprobante_id:
            estado = "pagado"
        else:
            estado = "pendiente_pago"

        async with async_session() as session:
            pedido = Pedido(
                telefono=telefono,
                items=items,
                total=total,
                comprobante_id=comprobante_id or f"retiro_sucursal",
                estado=estado,
                timestamp=datetime.utcnow()
            )
            session.add(pedido)
            await session.commit()
            pedido_id = pedido.id

        await notificar_dueno(telefono, items, total, pedido_id, tipo_entrega, comprobante_id)
        logger.info(f"Pedido #{pedido_id} ({tipo_entrega}) registrado para {telefono}")
        return {"pedido_id": pedido_id, "tipo_entrega": tipo_entrega, "estado": estado}
    except Exception as e:
        logger.error(f"Error al registrar pedido: {e}")
        return {"error": str(e), "estado": "fallo"}


async def notificar_dueno(telefono_cliente: str, items: str, total: str, pedido_id: int, tipo_entrega: str = "retiro_sucursal", comprobante_id: str = None):
    """
    Envía una notificación al dueño del negocio con el resumen del pedido.
    """
    try:
        from agent.providers import obtener_proveedor
        proveedor = obtener_proveedor()
        dueno_telefono = os.getenv("DUENO_TELEFONO")

        if not dueno_telefono:
            logger.warning("DUENO_TELEFONO no configurado — notificación no enviada")
            return

        # Determinar estado de pago y entrega
        if tipo_entrega == "retiro_sucursal":
            entrega_info = "RETIRO EN SUCURSAL (Mendoza 1700)"
            pago_info = "Sin pago previo"
        else:
            entrega_info = "ENVIO A DOMICILIO ($8.000)"
            pago_info = "PAGADO" if comprobante_id else "Pendiente de pago"

        mensaje_dueno = (
            f"Nuevo Pedido #{pedido_id}\n\n"
            f"Cliente: {telefono_cliente}\n"
            f"Items: {items}\n"
            f"Total: {total}\n"
            f"Entrega: {entrega_info}\n"
            f"Pago: {pago_info}\n"
        )

        if tipo_entrega == "envio_domicilio" and comprobante_id:
            mensaje_dueno += f"Comprobante: Recibido\n"

        await proveedor.enviar_mensaje(dueno_telefono, mensaje_dueno)
        logger.info(f"Notificación enviada al dueño para pedido #{pedido_id}")
    except Exception as e:
        logger.error(f"Error notificando al dueño: {e}")


async def procesar_comando_admin(mensaje: str) -> dict:
    """
    Procesa comandos administrativos.
    Formato: #admin [contraseña] [comando]

    Comandos disponibles:
    - sin stock [producto]
    - con stock [producto]
    - agregar [producto] $[precio]
    - modificar [producto] $[precio]
    """
    from agent.memory import agregar_producto_custom, marcar_sin_stock, reactivar_producto

    partes = mensaje.split(maxsplit=2)

    if len(partes) < 3:
        return {"exito": False, "error": "Formato: #admin [contraseña] [comando]"}

    comando_tag = partes[0]  # #admin
    contrasena = partes[1]
    resto = " ".join(partes[2:])

    # Validar contraseña
    PASSWORD = os.getenv("ADMIN_PASSWORD", "Tibu#2025")
    if contrasena != PASSWORD:
        logger.warning(f"Intento de acceso admin con contraseña incorrecta")
        return {"exito": False, "error": "Contraseña incorrecta"}

    # Procesar comando
    try:
        if resto.startswith("sin stock "):
            producto = resto.replace("sin stock ", "").strip()
            resultado = await marcar_sin_stock(producto)
            return {"exito": True, "tipo": "sin_stock", "producto": producto, "mensaje": f"✅ {producto} marcado como sin stock"}

        elif resto.startswith("con stock "):
            producto = resto.replace("con stock ", "").strip()
            resultado = await reactivar_producto(producto)
            return {"exito": True, "tipo": "con_stock", "producto": producto, "mensaje": f"✅ {producto} reactivado como con stock"}

        elif resto.startswith("agregar "):
            parte = resto.replace("agregar ", "").strip()
            if "$" not in parte:
                return {"exito": False, "error": "Formato: agregar [producto] $[precio]"}

            partes_agregar = parte.split("$")
            nombre = partes_agregar[0].strip()
            precio = "$" + partes_agregar[1].strip()

            resultado = await agregar_producto_custom(nombre, precio)
            return {"exito": True, "tipo": "agregar", "producto": nombre, "precio": precio, "mensaje": f"✅ {nombre} agregado a ${precio}"}

        elif resto.startswith("modificar "):
            parte = resto.replace("modificar ", "").strip()
            if "$" not in parte:
                return {"exito": False, "error": "Formato: modificar [producto] $[precio]"}

            partes_mod = parte.split("$")
            nombre = partes_mod[0].strip()
            precio = "$" + partes_mod[1].strip()

            resultado = await agregar_producto_custom(nombre, precio)
            return {"exito": True, "tipo": "modificar", "producto": nombre, "precio": precio, "mensaje": f"✅ Precio de {nombre} modificado a ${precio}"}

        else:
            return {"exito": False, "error": "Comando no reconocido. Usa: sin stock, con stock, agregar, o modificar"}

    except Exception as e:
        logger.error(f"Error procesando comando admin: {e}")
        return {"exito": False, "error": str(e)}
