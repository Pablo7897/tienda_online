"""Modelo de producto de la tienda online."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Column, Float, Integer, String

from database import Base


class Producto(Base):
    """Clase base que representa un producto generico de la tienda.

    Todos los productos se guardan en la tabla "productos"; la columna `tipo` indica
    si cada fila es un producto generico, electronico o de ropa (herencia de tabla unica).
    """

    __tablename__ = "productos"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    tipo = Column(String, nullable=False)

    __mapper_args__ = {"polymorphic_on": tipo, "polymorphic_identity": "generico"}

    def __init__(self, nombre: str, precio: float, stock: int) -> None:
        self.id = str(uuid.uuid4())  # Genera un ID único para cada producto
        self.nombre = nombre
        self.precio = precio
        self.stock = stock

    def hay_stock(self, cantidad: int) -> bool:
        """Comprueba si hay stock suficiente para la cantidad solicitada."""
        return self.stock >= cantidad

    def actualizar_stock(self, cantidad: int) -> None:
        """Suma `cantidad` al stock (negativa para compras, positiva para reposiciones)."""
        nuevo_stock = self.stock + cantidad
        if nuevo_stock < 0:
            raise ValueError("El stock no puede quedar por debajo de 0.")
        self.stock = nuevo_stock

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} - {self.precio:.2f}€ (stock: {self.stock})"


class ProductoElectronico(Producto):
    """Producto electronico, con meses de garantia."""

    meses_garantia = Column(Integer)

    __mapper_args__ = {"polymorphic_identity": "electronico"}

    def __init__(self, nombre: str, precio: float, stock: int, meses_garantia: int) -> None:
        super().__init__(nombre, precio, stock)
        self.meses_garantia = meses_garantia

    def __str__(self) -> str:
        return (
            f"[{self.id}] {self.nombre} - {self.precio:.2f}€ (stock: {self.stock}) "
            f" Garantia: {self.meses_garantia} meses"
        )


class ProductoRopa(Producto):
    """Producto de ropa, con talla y color."""

    talla = Column(String)
    color = Column(String)

    __mapper_args__ = {"polymorphic_identity": "ropa"}

    def __init__(self, nombre: str, precio: float, stock: int, talla: str, color: str) -> None:
        super().__init__(nombre, precio, stock)
        self.talla = talla
        self.color = color

    def __str__(self) -> str:
        return (
            f"[{self.id}] {self.nombre} - {self.precio:.2f}€ (stock: {self.stock}) "
            f"- Talla: {self.talla}, Color: {self.color}"
        )


# Esquemas Pydantic: datos de entrada (Create) y de salida (Read) de la API

class ProductoBase(BaseModel):
    tipo: Literal["generico", "electronico", "ropa"]
    nombre: str = Field(min_length=1)
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)
    meses_garantia: int | None = Field(default=None, ge=0)
    talla: str | None = None
    color: str | None = None


class ProductoCreate(ProductoBase):

    @model_validator(mode="after")
    def validar_atributos_por_tipo(self):
        """Comprueba que se envian los atributos propios del tipo y solo esos."""
        if self.tipo == "electronico":
            if self.meses_garantia is None:
                raise ValueError("Un producto electronico necesita meses_garantia.")
            if self.talla is not None or self.color is not None:
                raise ValueError("Un producto electronico no tiene talla ni color.")
        elif self.tipo == "ropa":
            if not self.talla or not self.color:
                raise ValueError("Un producto de ropa necesita talla y color.")
            if self.meses_garantia is not None:
                raise ValueError("Un producto de ropa no tiene meses_garantia.")
        elif self.meses_garantia is not None or self.talla is not None or self.color is not None:
            raise ValueError("Un producto generico no tiene meses_garantia, talla ni color.")
        return self


class ProductoRead(ProductoBase):
    id: str

    # Permite crear el esquema directamente a partir de un objeto de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
