import uuid
from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field

from models.Producto import Producto
from models.Usuario import Cliente


class Pedido:
    """Pedido de un cliente sobre una serie de productos con sus cantidades."""
    def __init__(self, cliente: Cliente, lineas: Dict[Producto, int]) -> None:
        """Crea el pedido con `cliente` y un diccionario {producto: cantidad}."""
        self.id: str = str(uuid.uuid4())
        self.cliente: Cliente = cliente
        self.lineas: Dict[Producto, int] = lineas
        self.fecha: datetime = datetime.now()

    def calcular_total(self) -> float:
        """Calcula el importe total segun precios y cantidades."""
        return sum(producto.precio * cantidad for producto, cantidad in self.lineas.items())

    def __str__(self) -> str:
        resumen_lineas = ", ".join(
            f"{cantidad}x {producto.nombre}" for producto, cantidad in self.lineas.items()
        )
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


class PedidoRead(BaseModel):
    id: str
    fecha: datetime
    cliente_id: str
    total: float
    items: list[PedidoItemRead]
