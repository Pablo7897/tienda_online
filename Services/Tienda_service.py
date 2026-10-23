"""Capa de servicios de la tienda online."""

from typing import Dict, List, Optional

from models.Pedido import Pedido
from models.Producto import Producto
from models.Usuario import Administrador, Cliente, Usuario


class TiendaService:
    """Servicio centralizado que gestiona usuarios, productos y pedidos de la tienda."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Usuario] = {}
        self.productos: Dict[str, Producto] = {}
        self.pedidos: List[Pedido] = []

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

        self.usuarios[usuario.id] = usuario
        return usuario

    def obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """Devuelve el usuario con ese identificador, o None si no existe."""
        return self.usuarios.get(usuario_id)

    def buscar_usuario_por_email(self, email: str) -> Optional[Usuario]:
        """Devuelve el usuario registrado con ese email, o None si no hay ninguno."""
        for usuario in self.usuarios.values():
            if usuario.email.lower() == email.lower():
                return usuario
        return None

    def listar_usuarios(self) -> List[Usuario]:
        """Devuelve la lista de todos los usuarios registrados."""
        return list(self.usuarios.values())

    def obtener_producto(self, producto_id: str) -> Optional[Producto]:
        """Devuelve el producto con ese identificador, o None si no existe."""
        return self.productos.get(producto_id)

    def anadir_producto(self, producto: Producto) -> Producto:
        """Añade un producto (de cualquier categoria) al inventario."""
        self.productos[producto.id] = producto
        return producto

    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto del inventario a partir de su identificador."""
        if producto_id in self.productos:
            del self.productos[producto_id]
            return True
        return False

    def listar_productos(self) -> List[Producto]:
        """Devuelve la lista de todos los productos disponibles en la tienda."""
        return list(self.productos.values())

    def realizar_pedido(self, usuario_id: str, lineas: Dict[str, int]) -> Optional[Pedido]:
        """Realiza un pedido para un usuario cliente.

        Args:
            usuario_id: id del usuario que solicita el pedido.
            lineas: diccionario {producto_id: cantidad} solicitado.

        Returns:
            El pedido creado, o None si el usuario no existe, no es cliente,
            o no hay stock suficiente de alguno de los productos solicitados.
        """
        usuario = self.usuarios.get(usuario_id)
        if usuario is None or not isinstance(usuario, Cliente):
            return None

        productos_solicitados: Dict[Producto, int] = {}
        for producto_id, cantidad in lineas.items():
            producto = self.productos.get(producto_id)
            if producto is None or not producto.hay_stock(cantidad):
                return None
            productos_solicitados[producto] = cantidad

        for producto, cantidad in productos_solicitados.items():
            producto.actualizar_stock(-cantidad)

        pedido = Pedido(usuario, productos_solicitados)
        self.pedidos.append(pedido)
        return pedido

    def listar_pedidos_usuario(self, usuario_id: str) -> List[Pedido]:
        """Lista todos los pedidos de un usuario ordenados por fecha."""
        pedidos_usuario = [p for p in self.pedidos if p.cliente.id == usuario_id]
        return sorted(pedidos_usuario, key=lambda p: p.fecha)
