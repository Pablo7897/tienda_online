"""Modelo de pedido de la tienda online."""

import uuid
from datetime import datetime
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from models.Producto import Producto
from models.Usuario import Cliente


class LineaPedido(Base):
    """Linea de un pedido: que producto, cuantas unidades y a que precio se compro.

    Se guardan el nombre y el precio del momento de la compra para que el historico
    del pedido no cambie si despues se modifica o se elimina el producto.
    """

    __tablename__ = "lineas_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(String, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    cantidad = Column(Integer, nullable=False)

    @property
    def subtotal(self) -> float:
        return round(self.precio_unitario * self.cantidad, 2)


class Pedido(Base):
    """Pedido de un cliente sobre una serie de productos con sus cantidades."""

    __tablename__ = "pedidos"

    id = Column(String, primary_key=True, index=True)
    cliente_id = Column(String, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False)

    cliente = relationship("Usuario")
    lineas = relationship("LineaPedido", cascade="all, delete-orphan")

    def __init__(self, cliente: Cliente, lineas: Dict[Producto, int]) -> None:
        """Crea el pedido con `cliente` y un diccionario {producto: cantidad}."""
        self.id = str(uuid.uuid4())
        self.cliente = cliente
        self.fecha = datetime.now()
        self.lineas = [
            LineaPedido(
                producto_id=producto.id,
                nombre=producto.nombre,
                precio_unitario=producto.precio,
                cantidad=cantidad,
            )
            for producto, cantidad in lineas.items()
        ]

    def calcular_total(self) -> float:
        """Calcula el importe total segun precios y cantidades."""
        return sum(linea.precio_unitario * linea.cantidad for linea in self.lineas)

    @property
    def total(self) -> float:
        """Total redondeado a dos decimales, usado por el esquema PedidoRead."""
        return round(self.calcular_total(), 2)

    def __str__(self) -> str:
        resumen_lineas = ", ".join(f"{linea.cantidad}x {linea.nombre}" for linea in self.lineas)
        return (
            f"Pedido [{self.id}] de {self.cliente.nombre} el {self.fecha:%Y-%m-%d %H:%M} "
            f"- Productos: {resumen_lineas} - Total: {self.calcular_total():.2f}€"
        )


# Esquemas Pydantic: datos de entrada (Create) y de salida (Read) de la API

class PedidoItemCreate(BaseModel):
    producto_id: str
    cantidad: int = Field(gt=0)


class PedidoCreate(BaseModel):
    cliente_id: str
    items: list[PedidoItemCreate] = Field(min_length=1)


class PedidoItemRead(BaseModel):
    producto_id: str
    nombre: str
    precio_unitario: float
    cantidad: int
    subtotal: float

    model_config = ConfigDict(from_attributes=True)


class PedidoRead(BaseModel):
    id: str
    fecha: datetime
    cliente_id: str
    total: float
    # En la API se llaman "items"; en el modelo de SQLAlchemy, "lineas"
    items: list[PedidoItemRead] = Field(validation_alias="lineas")

    model_config = ConfigDict(from_attributes=True)
