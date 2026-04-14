# agent/tools.py — Herramientas del agente COI
# Generado por AgentKit

"""
Herramientas específicas para el COI — Centro Oftalmológico Integral.
Casos de uso: FAQ y orientación para sacar turnos.
"""

import os
import yaml
import logging
from datetime import datetime

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
    """Retorna el horario de atención del COI y si está abierto ahora."""
    info = cargar_info_negocio()
    ahora = datetime.now()
    dia_semana = ahora.weekday()  # 0=Lunes, 6=Domingo
    hora_actual = ahora.hour

    # Determinar si está abierto según el horario
    if dia_semana < 5:  # Lunes a Viernes
        esta_abierto = 8 <= hora_actual < 18
    elif dia_semana == 5:  # Sábado
        esta_abierto = 9 <= hora_actual < 13
    else:  # Domingo
        esta_abierto = False

    return {
        "horario": info.get("negocio", {}).get("horario", "Lunes a Viernes 08-18hs, Sábados 09-13hs"),
        "esta_abierto": esta_abierto,
        "dia_actual": ahora.strftime("%A"),
        "hora_actual": ahora.strftime("%H:%M"),
    }


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


def verificar_cobertura_obra_social(obra_social: str) -> dict:
    """
    Verifica si una obra social es atendida en el COI
    y qué médicos tienen restricciones con ella.
    """
    obra_social_upper = obra_social.upper().strip()

    # Obras sociales que NO se atienden
    no_atendidas = ["IPROS"]

    # Restricciones por médico
    restricciones = {
        "IOSE": [
            "Dr. Morgillo Antonio (no atiende IOSE)",
            "Dr. Aringoli Juan (no atiende IOSE)",
            "Dra. Muller Lucrecia (no atiende IOSE)",
        ],
        "OSPERYHRA": [
            "Dra. Muller Lucrecia (no atiende OSPERYHRA)",
        ],
        "SWISS MEDICAL": [
            "Dra. Doro Jimena Paola (no trabaja con Swiss Medical)",
        ],
        "SCIS": [
            "Dra. Doro Jimena Paola (no trabaja con SCIS)",
        ],
    }

    if obra_social_upper in no_atendidas:
        return {
            "atendida": False,
            "mensaje": f"Lo siento, el COI no atiende la obra social {obra_social}.",
        }

    if obra_social_upper in restricciones:
        medicos_con_restriccion = restricciones[obra_social_upper]
        return {
            "atendida": True,
            "tiene_restricciones": True,
            "mensaje": f"La obra social {obra_social} es atendida en el COI, pero con algunas restricciones:",
            "restricciones": medicos_con_restriccion,
        }

    return {
        "atendida": True,
        "tiene_restricciones": False,
        "mensaje": f"La obra social {obra_social} es atendida en el COI sin restricciones conocidas.",
    }


def obtener_pasos_para_turno() -> str:
    """Retorna los pasos para sacar turno online."""
    return (
        "Para sacar turno en el COI seguí estos pasos:\n"
        "1️⃣ Ingresá a http://coineuquen.com.ar/\n"
        "2️⃣ Hacé clic en *REGISTRARSE* (si es la primera vez)\n"
        "3️⃣ Ingresá con tu *USUARIO = DNI* y tu *CLAVE*\n"
        "4️⃣ Buscá el turno con el profesional que querés y reservalo ✅"
    )
