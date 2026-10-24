"""Cliente de la API REST de la tienda online.

Toda la comunicacion con el servidor se hace mediante peticiones HTTP con requests:
no se importa nada del proyecto Tienda_online.

Antes de ejecutarlo hay que arrancar la API (desde Tienda_online): uvicorn main:app --reload

Uso:
    python cliente.py                            -> usa la API local (localhost)
    python cliente.py http://192.168.1.34:8000   -> usa la API de otro equipo de la red
"""

import sys

import requests

# Direccion de la API: por defecto la local. Para probar entre dos ordenadores se puede
# cambiar aqui por la IP del equipo servidor o pasarla al ejecutar el script.
BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    BASE_URL = sys.argv[1].rstrip("/")

# Segundos maximos de espera por respuesta, para no quedarse colgado si el servidor no contesta
TIMEOUT = 5


def comprobar(respuesta, codigo_esperado, accion):
    """Comprueba el codigo HTTP; si es el esperado devuelve el JSON, si no muestra el error."""
    if respuesta.status_code == codigo_esperado:
        return respuesta.json()
    print(f"Error al {accion}: {respuesta.status_code} {respuesta.json()}")
    return None


# 0. Comprobar que la API esta encendida y es accesible
print(f"Conectando con la API en {BASE_URL}\n")
try:
    requests.get(f"{BASE_URL}/usuarios", timeout=TIMEOUT)
except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
    print(f"No se puede conectar con la API en {BASE_URL}.")
    print("Comprueba que el servidor esta arrancado, que la IP y el puerto son correctos")
    print("y, si es otro equipo, que lo arrancaste con --host 0.0.0.0 y que su firewall lo permite.")
    raise SystemExit(1)


# 1. Crear varios usuarios
print("=== Creando usuarios ===")
clientes = [
    {"nombre": "Juan", "email": "juan@example.com", "tipo": "cliente", "direccion": "Calle Mayor 1"},
    {"nombre": "Ana", "email": "ana@example.com", "tipo": "cliente", "direccion": "Calle Sol 5"},
    {"nombre": "Luis", "email": "luis@example.com", "tipo": "cliente", "direccion": "Avenida Luna 9"},
]

usuarios_creados = []
for datos in clientes:
    respuesta = requests.post(f"{BASE_URL}/usuarios", json=datos, timeout=TIMEOUT)
    if respuesta.status_code == 409:
        # El email ya estaba registrado (por ejemplo, al ejecutar el cliente dos veces):
        # se busca ese usuario en la lista para poder seguir usandolo
        existentes = requests.get(f"{BASE_URL}/usuarios", timeout=TIMEOUT).json()
        usuario = next(u for u in existentes if u["email"] == datos["email"])
        usuarios_creados.append(usuario)
        print("Ya existia:", usuario["nombre"], usuario["id"])
        continue
    usuario = comprobar(respuesta, 201, f"crear el usuario {datos['nombre']}")
    if usuario is not None:
        usuarios_creados.append(usuario)
        print("Creado:", usuario["nombre"], usuario["id"])


# 2. Consultar la lista de usuarios
print("\n=== Lista de usuarios ===")
usuarios = comprobar(requests.get(f"{BASE_URL}/usuarios", timeout=TIMEOUT), 200, "listar los usuarios")
if usuarios is not None:
    for u in usuarios:
        tipo = "administrador" if u["es_admin"] else "cliente"
        print(f"- {u['nombre']} ({u['email']}) - {tipo}")


# 3. Crear varios productos
print("\n=== Creando productos ===")
productos = [
    {"tipo": "electronico", "nombre": "Smartphone", "precio": 599.99, "stock": 10, "meses_garantia": 24},
    {"tipo": "electronico", "nombre": "Auriculares", "precio": 79.99, "stock": 20, "meses_garantia": 12},
    {"tipo": "ropa", "nombre": "Camiseta", "precio": 19.99, "stock": 50, "talla": "M", "color": "Negro"},
    {"tipo": "generico", "nombre": "Taza", "precio": 5.50, "stock": 30},
]

productos_creados = []
for datos in productos:
    respuesta = requests.post(f"{BASE_URL}/productos", json=datos, timeout=TIMEOUT)
    producto = comprobar(respuesta, 201, f"crear el producto {datos['nombre']}")
    if producto is not None:
        productos_creados.append(producto)
        print("Creado:", producto["nombre"], producto["id"])


# 4. Consultar la lista de productos
print("\n=== Lista de productos ===")
lista_productos = comprobar(requests.get(f"{BASE_URL}/productos", timeout=TIMEOUT), 200, "listar los productos")
if lista_productos is not None:
    for p in lista_productos:
        print(f"- {p['nombre']} ({p['tipo']}): {p['precio']:.2f}€ - stock {p['stock']}")


# Sin al menos un usuario y dos productos creados no se puede hacer el pedido
if not usuarios_creados or len(productos_creados) < 2:
    print("\nNo hay usuarios o productos suficientes para crear el pedido.")
    raise SystemExit(1)


# 5. Crear un pedido para el primer usuario creado
cliente = usuarios_creados[0]
print(f"\n=== Creando pedido para {cliente['nombre']} ===")
pedido_nuevo = {
    "cliente_id": cliente["id"],
    "items": [
        {"producto_id": productos_creados[0]["id"], "cantidad": 1},
        {"producto_id": productos_creados[1]["id"], "cantidad": 2},
    ],
}
pedido = comprobar(requests.post(f"{BASE_URL}/pedidos", json=pedido_nuevo, timeout=TIMEOUT), 201, "crear el pedido")
if pedido is not None:
    for item in pedido["items"]:
        print(f"- {item['cantidad']}x {item['nombre']}: {item['subtotal']:.2f}€")
    print(f"Total: {pedido['total']:.2f}€")


# 6. Consultar los pedidos de ese usuario
print(f"\n=== Pedidos de {cliente['nombre']} ===")
pedidos = comprobar(
    requests.get(f"{BASE_URL}/usuarios/{cliente['id']}/pedidos", timeout=TIMEOUT), 200, "consultar los pedidos"
)
if pedidos is not None:
    for p in pedidos:
        print(f"- Pedido {p['id']} del {p['fecha'][:10]}: {len(p['items'])} productos, total {p['total']:.2f}€")
