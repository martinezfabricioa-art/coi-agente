# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

"""
Servidor principal del agente de WhatsApp.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (se configura en .env con WHATSAPP_PROVIDER)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — COI WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "agentkit-coi", "agente": "Anto"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para otros)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook/messages")
async def webhook_messages_handler(request: Request):
    """Mensajes entrantes de Whapi.cloud (path estándar)."""
    return await _procesar_webhook(request)


@app.post("/v1/webhook/messages")
async def webhook_v1_messages_handler(request: Request):
    """Mensajes entrantes de Whapi.cloud (path v1)."""
    return await _procesar_webhook(request)


@app.post("/v1/webhook/statuses")
async def webhook_v1_statuses_handler(request: Request):
    """Actualizaciones de estado de Whapi.cloud (leídos, entregados, etc.)."""
    return {"status": "ok"}  # Solo confirmamos recepción, no procesamos


@app.post("/webhook/statuses")
async def webhook_statuses_handler(request: Request):
    """Actualizaciones de estado de Whapi.cloud."""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via el proveedor configurado.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    """
    return await _procesar_webhook(request)


async def _procesar_webhook(request: Request):
    """Lógica central de procesamiento de mensajes entrantes."""
    try:
        # Log del payload crudo para debugging
        body_raw = await request.body()
        logger.info(f"Payload recibido: {body_raw.decode('utf-8', errors='replace')[:500]}")

        # Parsear webhook — el proveedor normaliza el formato
        from starlette.requests import Request as StarletteRequest
        import json
        # Recrear el request con el body ya leído
        async def receive():
            return {"type": "http.request", "body": body_raw}
        request._receive = receive

        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            # Ignorar mensajes propios o vacíos
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            # Obtener historial ANTES de guardar el mensaje actual
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude
            respuesta = await generar_respuesta(msg.texto, historial)

            # Guardar mensaje del usuario Y respuesta del agente en memoria
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via el proveedor
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
