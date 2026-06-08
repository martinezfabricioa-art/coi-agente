# agent/brain.py — Cerebro del agente: conexión con Claude API
# Generado por AgentKit

"""
Lógica de IA del agente. Lee el system prompt de prompts.yaml
y genera respuestas usando la API de Anthropic Claude.
"""

import os
import yaml
import logging
import json
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

TOOLS = [
    {
        "name": "registrar_pedido",
        "description": "Registra un pedido confirmado del cliente y notifica al dueño del negocio",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "string",
                    "description": "Descripción de los items del pedido. Ej: '2x Merluza fresca, 1x Camarones congelados'"
                },
                "total": {
                    "type": "string",
                    "description": "Total del pedido con símbolo de pesos. Ej: '$6400' (si es retiro) o '$14400' (si es envío con $8000 de envío)"
                },
                "tipo_entrega": {
                    "type": "string",
                    "enum": ["retiro_sucursal", "envio_domicilio"],
                    "description": "Tipo de entrega elegida por el cliente"
                },
                "comprobante_id": {
                    "type": "string",
                    "description": "ID/referencia del comprobante de pago. OBLIGATORIO solo si tipo_entrega='envio_domicilio'. Para retiro, puede ser null."
                }
            },
            "required": ["items", "total", "tipo_entrega"]
        }
    },
    {
        "name": "buscar_producto",
        "description": "Busca un producto en el catálogo y retorna su precio",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_producto": {
                    "type": "string",
                    "description": "Nombre del producto a buscar. Ej: 'merluza fresca', 'camarones', 'salmon'"
                }
            },
            "required": ["nombre_producto"]
        }
    }
]


def obtener_cliente() -> AsyncAnthropic:
    """Crea el cliente de Anthropic con la API key cargada desde .env."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no está configurada en .env")
    return AsyncAnthropic(api_key=api_key)


def cargar_config_prompts() -> dict:
    """Lee toda la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_productos_desde_knowledge() -> str:
    """Lee productos desde knowledge/productos.txt y formatea para el prompt."""
    try:
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
            return ""

        with open(knowledge_file, "r", encoding="utf-8") as f:
            contenido = f.read()

        # Retornar el contenido completo del archivo para incluir en el prompt
        return f"\n**Catálogo completo de productos:**\n\n{contenido}"
    except Exception as e:
        logger.error(f"Error cargando productos: {e}")
        return ""


def cargar_system_prompt() -> str:
    """Lee el system prompt desde config/prompts.yaml e incluye productos actualizados."""
    config = cargar_config_prompts()
    system_prompt = config.get("system_prompt", "Sos un asistente útil. Respondé en español.")

    # Agregar productos actualizados del archivo knowledge
    productos = cargar_productos_desde_knowledge()
    if productos:
        system_prompt = system_prompt.replace(
            "**Nota:** Los precios pueden variar según disponibilidad.",
            f"{productos}\n\n**Nota:** Los precios pueden variar según disponibilidad."
        )

    return system_prompt


def obtener_mensaje_error() -> str:
    """Retorna el mensaje de error configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo un problemita técnico. Por favor intentá de nuevo en unos minutos 🙏")


def obtener_mensaje_fallback() -> str:
    """Retorna el mensaje de fallback configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("fallback_message", "¡Disculpá, no entendí bien tu mensaje! ¿Me lo podés reformular? 😊")


async def generar_respuesta(mensaje: str, historial: list[dict], telefono: str) -> str:
    """
    Genera una respuesta usando Claude API con soporte para tool_use.

    Args:
        mensaje: El mensaje nuevo del usuario
        historial: Lista de mensajes anteriores [{"role": "user/assistant", "content": "..."}]
        telefono: Número de teléfono del cliente (para tools)

    Returns:
        La respuesta generada por Claude
    """
    # Si el mensaje es muy corto o vacío, usar fallback
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    # Detectar si es comando admin
    if mensaje.strip().startswith("#admin "):
        from agent.tools import procesar_comando_admin
        resultado = await procesar_comando_admin(mensaje.strip())
        if resultado["exito"]:
            return resultado.get("mensaje", "✅ Comando ejecutado")
        else:
            return f"❌ {resultado.get('error', 'Error en comando')}"

    system_prompt = cargar_system_prompt()

    # Construir mensajes para la API
    mensajes = []
    for msg in historial:
        mensajes.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Agregar el mensaje actual
    mensajes.append({
        "role": "user",
        "content": mensaje
    })

    try:
        client = obtener_cliente()
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=TOOLS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=mensajes
        )

        # Si Claude quiere usar una tool
        if response.stop_reason == "tool_use":
            tool_result = None
            tool_use_block = None

            # Buscar el bloque de tool_use
            for block in response.content:
                if block.type == "tool_use":
                    tool_use_block = block

                    if block.name == "registrar_pedido":
                        # Ejecutar registrar_pedido
                        from agent.tools import registrar_pedido
                        result = await registrar_pedido(
                            telefono=telefono,
                            items=block.input["items"],
                            total=block.input["total"],
                            tipo_entrega=block.input.get("tipo_entrega", "retiro_sucursal"),
                            comprobante_id=block.input.get("comprobante_id")
                        )
                        tool_result = json.dumps(result)

                    elif block.name == "buscar_producto":
                        # Ejecutar buscar_producto
                        from agent.tools import buscar_producto
                        result = await buscar_producto(
                            nombre_producto=block.input["nombre_producto"]
                        )
                        tool_result = json.dumps(result)

                    break

            # Si se ejecutó una tool, hacer una segunda llamada para obtener la respuesta final
            if tool_use_block and tool_result:
                # Agregar el tool_use al historial
                mensajes.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_use_block.id,
                            "name": tool_use_block.name,
                            "input": tool_use_block.input
                        }
                    ]
                })
                # Agregar el resultado de la tool
                mensajes.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": tool_result
                        }
                    ]
                })

                # Llamar de nuevo para obtener la respuesta final
                response = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    tools=TOOLS,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                    messages=mensajes
                )

        # Extraer el texto de la respuesta
        respuesta = ""
        for block in response.content:
            if hasattr(block, "text"):
                respuesta = block.text
                break

        logger.info(f"Respuesta generada ({response.usage.input_tokens} in / {response.usage.output_tokens} out)")
        return respuesta if respuesta else obtener_mensaje_error()

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error()
