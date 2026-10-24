"""Punto de entrada de la API REST de la tienda online.

Ejecucion desde la carpeta del proyecto: uvicorn main:app --reload
"""

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models.Pedido import PedidoCreate, PedidoRead
from models.Producto import (
    Producto,
    ProductoCreate,
    ProductoElectronico,
    ProductoRead,
    ProductoRopa,
)
from models.Usuario import Cliente, UsuarioCreate, UsuarioRead
from Services.Tienda_service import TiendaService

# Crear las tablas de la base de datos (tienda.db) si todavia no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tienda online")

# CORS: permite que el frontend, que el navegador abre desde otra direccion,
# pueda hacer peticiones a la API (sin esto el navegador las bloquea)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencia para la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependencia que crea el servicio de la tienda con la sesion de cada peticion
def get_servicio(db: Session = Depends(get_db)) -> TiendaService:
    return TiendaService(db)


# Endpoints de usuarios

@app.post("/usuarios", response_model=UsuarioRead, status_code=201)
def create_usuario(usuario: UsuarioCreate, servicio: TiendaService = Depends(get_servicio)):
    if servicio.buscar_usuario_por_email(usuario.email) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

    atributos = {"nombre": usuario.nombre, "email": usuario.email}
    if usuario.tipo == "cliente":
        atributos["direccion"] = usuario.direccion

    try:
        return servicio.registrar_usuario(usuario.tipo, **atributos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/usuarios", response_model=list[UsuarioRead])
def read_usuarios(
    skip: int = 0,
    limit: int = 100,
    nombre: str | None = None,
    servicio: TiendaService = Depends(get_servicio),
):
    return servicio.listar_usuarios(nombre=nombre, skip=skip, limit=limit)


@app.get("/usuarios/{usuario_id}", response_model=UsuarioRead)
def read_usuario(usuario_id: str, servicio: TiendaService = Depends(get_servicio)):
    usuario = servicio.obtener_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


# Endpoints de productos

@app.post("/productos", response_model=ProductoRead, status_code=201)
def create_producto(producto: ProductoCreate, servicio: TiendaService = Depends(get_servicio)):
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

    return servicio.anadir_producto(nuevo_producto)


@app.get("/productos", response_model=list[ProductoRead])
def read_productos(
    skip: int = 0,
    limit: int = 100,
    tipo: Literal["generico", "electronico", "ropa"] | None = None,
    nombre: str | None = None,
    servicio: TiendaService = Depends(get_servicio),
):
    return servicio.listar_productos(tipo=tipo, nombre=nombre, skip=skip, limit=limit)


@app.get("/productos/{producto_id}", response_model=ProductoRead)
def read_producto(producto_id: str, servicio: TiendaService = Depends(get_servicio)):
    producto = servicio.obtener_producto(producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@app.delete("/productos/{producto_id}")
def delete_producto(producto_id: str, servicio: TiendaService = Depends(get_servicio)):
    result = servicio.eliminar_producto(producto_id)
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado correctamente"}


# Endpoints de pedidos

def get_cliente(cliente_id: str, servicio: TiendaService) -> Cliente:
    """Devuelve el cliente indicado o lanza el error HTTP que corresponda."""
    usuario = servicio.obtener_usuario(cliente_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not isinstance(usuario, Cliente):
        raise HTTPException(status_code=400, detail="El usuario no es un cliente")
    return usuario


@app.post("/pedidos", response_model=PedidoRead, status_code=201)
def create_pedido(pedido: PedidoCreate, servicio: TiendaService = Depends(get_servicio)):
    cliente = get_cliente(pedido.cliente_id, servicio)

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
    return nuevo_pedido


@app.get("/usuarios/{cliente_id}/pedidos", response_model=list[PedidoRead])
def read_pedidos_cliente(cliente_id: str, servicio: TiendaService = Depends(get_servicio)):
    cliente = get_cliente(cliente_id, servicio)
    return servicio.listar_pedidos_usuario(cliente.id)
