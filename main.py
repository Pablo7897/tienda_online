"""Punto de entrada de la API REST de la tienda online.

Ejecucion desde la carpeta del proyecto: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException

from models.Pedido import Pedido, PedidoCreate, PedidoItemRead, PedidoRead
from models.Producto import (
    Producto,
    ProductoCreate,
    ProductoElectronico,
    ProductoRead,
    ProductoRopa,
)
from models.Usuario import Cliente, Usuario, UsuarioCreate, UsuarioRead
from Services.Tienda_service import TiendaService

app = FastAPI(title="Tienda online")

# Los datos se guardan en memoria: se pierden al reiniciar el servidor
servicio = TiendaService()


# Conversion de las clases de dominio a los esquemas de salida

def usuario_a_schema(usuario: Usuario) -> UsuarioRead:
    return UsuarioRead(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        es_admin=usuario.is_admin(),
    )


def producto_a_schema(producto: Producto) -> ProductoRead:
    if isinstance(producto, ProductoElectronico):
        tipo = "electronico"
    elif isinstance(producto, ProductoRopa):
        tipo = "ropa"
    else:
        tipo = "generico"
    return ProductoRead(
        id=producto.id,
        tipo=tipo,
        nombre=producto.nombre,
        precio=producto.precio,
        stock=producto.stock,
        meses_garantia=getattr(producto, "meses_garantia", None),
        talla=getattr(producto, "talla", None),
        color=getattr(producto, "color", None),
    )


def pedido_a_schema(pedido: Pedido) -> PedidoRead:
    items = [
        PedidoItemRead(
            producto_id=producto.id,
            nombre=producto.nombre,
            precio_unitario=producto.precio,
            cantidad=cantidad,
            subtotal=round(producto.precio * cantidad, 2),
        )
        for producto, cantidad in pedido.lineas.items()
    ]
    return PedidoRead(
        id=pedido.id,
        fecha=pedido.fecha,
        cliente_id=pedido.cliente.id,
        total=round(pedido.calcular_total(), 2),
        items=items,
    )


# Endpoints de usuarios

@app.post("/usuarios", response_model=UsuarioRead, status_code=201)
def create_usuario(usuario: UsuarioCreate):
    if servicio.buscar_usuario_por_email(usuario.email) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

    atributos = {"nombre": usuario.nombre, "email": usuario.email}
    if usuario.tipo == "cliente":
        atributos["direccion"] = usuario.direccion

    try:
        nuevo_usuario = servicio.registrar_usuario(usuario.tipo, **atributos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return usuario_a_schema(nuevo_usuario)


@app.get("/usuarios", response_model=list[UsuarioRead])
def read_usuarios():
    return [usuario_a_schema(usuario) for usuario in servicio.listar_usuarios()]


@app.get("/usuarios/{usuario_id}", response_model=UsuarioRead)
def read_usuario(usuario_id: str):
    usuario = servicio.obtener_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario_a_schema(usuario)


# Endpoints de productos

@app.post("/productos", response_model=ProductoRead, status_code=201)
def create_producto(producto: ProductoCreate):
    if producto.tipo == "electronico":
        nuevo_producto = ProductoElectronico(
            producto.nombre, producto.precio, producto.stock,
            meses_garantia=producto.meses_garantia,
        )
    elif producto.tipo == "ropa":
        nuevo_producto = ProductoRopa(
            producto.nombre, producto.precio, producto.stock,
            talla=producto.talla, color=producto.color,
        )
    else:
        nuevo_producto = Producto(producto.nombre, producto.precio, producto.stock)

    servicio.anadir_producto(nuevo_producto)
    return producto_a_schema(nuevo_producto)


@app.get("/productos", response_model=list[ProductoRead])
def read_productos():
    return [producto_a_schema(producto) for producto in servicio.listar_productos()]


@app.get("/productos/{producto_id}", response_model=ProductoRead)
def read_producto(producto_id: str):
    producto = servicio.obtener_producto(producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto_a_schema(producto)


@app.delete("/productos/{producto_id}")
def delete_producto(producto_id: str):
    result = servicio.eliminar_producto(producto_id)
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado correctamente"}


# Endpoints de pedidos

def get_cliente(cliente_id: str) -> Cliente:
    """Devuelve el cliente indicado o lanza el error HTTP que corresponda."""
    usuario = servicio.obtener_usuario(cliente_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not isinstance(usuario, Cliente):
        raise HTTPException(status_code=400, detail="El usuario no es un cliente")
    return usuario


@app.post("/pedidos", response_model=PedidoRead, status_code=201)
def create_pedido(pedido: PedidoCreate):
    cliente = get_cliente(pedido.cliente_id)

    # Si un producto viene repetido en varias lineas se suman sus cantidades
    lineas: dict[str, int] = {}
    for item in pedido.items:
        lineas[item.producto_id] = lineas.get(item.producto_id, 0) + item.cantidad

    for producto_id, cantidad in lineas.items():
        producto = servicio.obtener_producto(producto_id)
        if producto is None:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
        if not producto.hay_stock(cantidad):
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente de {producto.nombre} (disponible: {producto.stock})",
            )

    nuevo_pedido = servicio.realizar_pedido(cliente.id, lineas)
    if nuevo_pedido is None:
        raise HTTPException(status_code=400, detail="No se ha podido realizar el pedido")
    return pedido_a_schema(nuevo_pedido)


@app.get("/usuarios/{cliente_id}/pedidos", response_model=list[PedidoRead])
def read_pedidos_cliente(cliente_id: str):
    cliente = get_cliente(cliente_id)
    return [pedido_a_schema(pedido) for pedido in servicio.listar_pedidos_usuario(cliente.id)]
