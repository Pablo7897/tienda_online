"""Modelo de usuario de la tienda online."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import Column, String

from database import Base


class Usuario(Base):
    """Clase base que representa a cualquier persona que interactua con la tienda.

    Clientes y administradores se guardan en la misma tabla "usuarios"; la columna
    `tipo` indica de que clase es cada fila (herencia de tabla unica).
    """

    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    tipo = Column(String, nullable=False)

    __mapper_args__ = {"polymorphic_on": tipo, "polymorphic_identity": "usuario"}

    def __init__(self, nombre: str, email: str) -> None:
        self.id = str(uuid.uuid4())
        self.nombre = nombre
        self.email = email

    def is_admin(self) -> bool:
        """Indica si el usuario es administrador."""
        return False

    @property
    def es_admin(self) -> bool:
        """Version como atributo de is_admin(), usada por el esquema UsuarioRead."""
        return self.is_admin()

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} ({self.email})"


class Cliente(Usuario):
    """Usuario cliente de la tienda, con direccion postal."""

    direccion = Column(String)

    __mapper_args__ = {"polymorphic_identity": "cliente"}

    def __init__(self, nombre: str, email: str, direccion: str) -> None:
        super().__init__(nombre, email)
        self.direccion = direccion

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} ({self.email}) - Direccion: {self.direccion}"


class Administrador(Usuario):
    """Usuario gestor de la tienda."""

    __mapper_args__ = {"polymorphic_identity": "administrador"}

    def is_admin(self) -> bool:
        """Los administradores siempre devuelven True."""
        return True

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} ({self.email}) - Administrador"


# Esquemas Pydantic: datos de entrada (Create) y de salida (Read) de la API

class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=1)
    email: EmailStr


class UsuarioCreate(UsuarioBase):
    tipo: Literal["cliente", "administrador"]
    direccion: str | None = None

    @model_validator(mode="after")
    def validar_direccion(self):
        """Los clientes necesitan direccion postal; los administradores no la tienen."""
        if self.tipo == "cliente" and not self.direccion:
            raise ValueError("Un cliente debe indicar su direccion postal.")
        if self.tipo == "administrador" and self.direccion is not None:
            raise ValueError("Un administrador no tiene direccion postal.")
        return self


class UsuarioRead(UsuarioBase):
    id: str
    es_admin: bool

    # Permite crear el esquema directamente a partir de un objeto de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
