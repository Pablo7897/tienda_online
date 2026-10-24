"""Capa de servicios de la tienda online."""

from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.Pedido import Pedido
from models.Producto import Producto
from models.Usuario import Administrador, Cliente, Usuario


class TiendaService:
    """Servicio centralizado que gestiona usuarios, productos y pedidos de la tienda.

    Los datos se guardan en la base de datos a traves de la sesion `db` de SQLAlchemy.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def registrar_usuario(self, tipo: str, **atributos) -> Usuario:
        """Registra un nuevo usuario.

        Args:
            tipo: "cliente" o "administrador".
            atributos: atributos requeridos por el constructor del tipo de usuario elegido.
        """
        if tipo == "cliente":
            usuario: Usuario = Cliente(**atributos)
        elif tipo == "administrador":
            usuario = Administrador(**atributos)
        else:
            raise ValueError(f"Tipo de usuario desconocido: {tipo}")

        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """Devuelve el usuario con ese identificador, o None si no existe."""
        return self.db.get(Usuario, usuario_id)

    def buscar_usuario_por_email(self, email: str) -> Optional[Usuario]:
        """Devuelve el usuario registrado con ese email, o None si no hay ninguno."""
        return (
            self.db.query(Usuario)
            .filter(func.lower(Usuario.email) == email.lower())
            .first()
        )

    def listar_usuarios(
        self, nombre: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[Usuario]:
        """Devuelve los usuarios registrados, opcionalmente filtrados por nombre."""
        query = self.db.query(Usuario)
        if nombre is not None:
            query = query.filter(Usuario.nombre.ilike(f"%{nombre}%"))
        return query.offset(skip).limit(limit).all()

    def obtener_producto(self, producto_id: str) -> Optional[Producto]:
        """Devuelve el producto con ese identificador, o None si no existe."""
        return self.db.get(Producto, producto_id)

    def anadir_producto(self, producto: Producto) -> Producto:
        """Añade un producto (de cualquier categoria) al inventario."""
        self.db.add(producto)
        self.db.commit()
        self.db.refresh(producto)
        return producto

    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto del inventario a partir de su identificador."""
        producto = self.obtener_producto(producto_id)
        if producto is None:
            return False
        self.db.delete(producto)
        self.db.commit()
        return True

    def listar_productos(
        self,
        tipo: Optional[str] = None,
        nombre: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Producto]:
        """Devuelve los productos de la tienda, opcionalmente filtrados por tipo y nombre."""
        query = self.db.query(Producto)
        if tipo is not None:
            query = query.filter(Producto.tipo == tipo)
        if nombre is not None:
            query = query.filter(Producto.nombre.ilike(f"%{nombre}%"))
        return query.offset(skip).limit(limit).all()

    def realizar_pedido(self, usuario_id: str, lineas: Dict[str, int]) -> Optional[Pedido]:
        """Realiza un pedido para un usuario cliente.

        Args:
            usuario_id: id del usuario que solicita el pedido.
            lineas: diccionario {producto_id: cantidad} solicitado.

        Returns:
            El pedido creado, o None si el usuario no existe, no es cliente,
            o no hay stock suficiente de alguno de los productos solicitados.
        """
        usuario = self.obtener_usuario(usuario_id)
        if usuario is None or not isinstance(usuario, Cliente):
            return None

        productos_solicitados: Dict[Producto, int] = {}
        for producto_id, cantidad in lineas.items():
            producto = self.obtener_producto(producto_id)
            if producto is None or not producto.hay_stock(cantidad):
                return None
            productos_solicitados[producto] = cantidad

        for producto, cantidad in productos_solicitados.items():
            producto.actualizar_stock(-cantidad)

        # El pedido y la bajada de stock se guardan juntos en un unico commit
        pedido = Pedido(usuario, productos_solicitados)
        self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def listar_pedidos_usuario(self, usuario_id: str) -> List[Pedido]:
        """Lista todos los pedidos de un usuario ordenados por fecha."""
        return (
            self.db.query(Pedido)
            .filter(Pedido.cliente_id == usuario_id)
            .order_by(Pedido.fecha)
            .all()
        )
