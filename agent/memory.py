# agent/memory.py — Memoria de conversaciones con SQLite
# Generado por AgentKit

"""
Sistema de memoria del agente. Guarda el historial de conversaciones
por número de teléfono usando SQLite (local) o PostgreSQL (producción).
"""

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select, Integer, Boolean
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Si es PostgreSQL en producción, ajustar el esquema de URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Modelo de mensaje en la base de datos."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" o "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    """Crea las tablas si no existen."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def guardar_mensaje(telefono: str, role: str, content: str):
    """Guarda un mensaje en el historial de conversación."""
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 10) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.

    Args:
        telefono: Número de teléfono del cliente
        limite: Máximo de mensajes a recuperar (default: 20)

    Returns:
        Lista de diccionarios con role y content
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

        # Invertir para orden cronológico (los más recientes están primero)
        mensajes.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in mensajes
        ]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        result = await session.execute(query)
        mensajes = result.scalars().all()
        for msg in mensajes:
            await session.delete(msg)
        await session.commit()


class ProductoCustom(Base):
    """Modelo para productos agregados/modificados por admin."""
    __tablename__ = "productos_custom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    precio: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockProducto(Base):
    """Modelo para marcar productos sin stock."""
    __tablename__ = "stock_productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    en_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Pedido(Base):
    """Modelo de pedido en la base de datos."""
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    items: Mapped[str] = mapped_column(Text)
    total: Mapped[str] = mapped_column(String(100))
    comprobante_id: Mapped[str] = mapped_column(String(255), nullable=True)  # ID de imagen del comprobante
    estado: Mapped[str] = mapped_column(String(20), default="pendiente_pago")  # pendiente_pago → pagado → completado
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def guardar_pedido(telefono: str, items: str, total: str) -> int:
    """Inserta un pedido y retorna su ID."""
    async with async_session() as session:
        pedido = Pedido(
            telefono=telefono,
            items=items,
            total=total,
            estado="pendiente",
            timestamp=datetime.utcnow()
        )
        session.add(pedido)
        await session.commit()
        return pedido.id


async def obtener_pedidos(telefono: str) -> list[dict]:
    """Retorna todos los pedidos de un número de teléfono."""
    async with async_session() as session:
        query = (
            select(Pedido)
            .where(Pedido.telefono == telefono)
            .order_by(Pedido.timestamp.desc())
        )
        result = await session.execute(query)
        pedidos = result.scalars().all()

        return [
            {
                "id": p.id,
                "items": p.items,
                "total": p.total,
                "estado": p.estado,
                "timestamp": p.timestamp.isoformat()
            }
            for p in pedidos
        ]


async def agregar_producto_custom(nombre: str, precio: str):
    """Agrega o actualiza un producto personalizado."""
    async with async_session() as session:
        query = select(ProductoCustom).where(ProductoCustom.nombre == nombre.lower())
        result = await session.execute(query)
        producto = result.scalars().first()

        if producto:
            producto.precio = precio
        else:
            producto = ProductoCustom(nombre=nombre.lower(), precio=precio)
            session.add(producto)

        await session.commit()
        return {"exito": True, "nombre": nombre, "precio": precio}


async def marcar_sin_stock(nombre: str):
    """Marca un producto como sin stock."""
    async with async_session() as session:
        query = select(StockProducto).where(StockProducto.nombre == nombre.lower())
        result = await session.execute(query)
        stock = result.scalars().first()

        if stock:
            stock.en_stock = False
        else:
            stock = StockProducto(nombre=nombre.lower(), en_stock=False)
            session.add(stock)

        await session.commit()
        return {"exito": True, "producto": nombre, "estado": "sin stock"}


async def reactivar_producto(nombre: str):
    """Marca un producto como con stock nuevamente."""
    async with async_session() as session:
        query = select(StockProducto).where(StockProducto.nombre == nombre.lower())
        result = await session.execute(query)
        stock = result.scalars().first()

        if stock:
            stock.en_stock = True
        else:
            stock = StockProducto(nombre=nombre.lower(), en_stock=True)
            session.add(stock)

        await session.commit()
        return {"exito": True, "producto": nombre, "estado": "con stock"}


async def obtener_productos_sin_stock() -> list[str]:
    """Retorna lista de productos sin stock."""
    async with async_session() as session:
        query = select(StockProducto).where(StockProducto.en_stock == False)
        result = await session.execute(query)
        stocks = result.scalars().all()
        return [s.nombre for s in stocks]
