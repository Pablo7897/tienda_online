# Práctica 2 – Tienda online con FastAPI

```text
P2/
├── Tienda_online/          API REST con FastAPI y base de datos SQLite
├── Tienda_online_memoria/  La misma API, con los datos en memoria
├── cliente/                Cliente Python que usa la API con requests
└── frontend/               Frontend web (HTML + JavaScript) que usa la API
```

Las partes están separadas: el cliente y el frontend no importan nada del servidor
y se comunican con él solo mediante peticiones HTTP. Funcionan igual con cualquiera
de las dos versiones de la API.

## 1. API

Hay dos versiones con los mismos endpoints. Solo hay que arrancar una de ellas.

### Con base de datos (Tienda_online)

```bash
cd Tienda_online
pip install -r requirements.txt
uvicorn main:app --reload
```

Los datos se guardan en SQLite con SQLAlchemy. El fichero `tienda.db` se crea solo al
arrancar el servidor, en la carpeta desde la que se lanza, y los datos se mantienen
entre reinicios.

### En memoria (Tienda_online_memoria)

```bash
cd Tienda_online_memoria
pip install -r requirements.txt
uvicorn main:app --reload
```

Los datos se guardan en memoria, en `TiendaService`, y se pierden al reiniciar el servidor.

### Para las dos

Documentación interactiva: http://127.0.0.1:8000/docs

Para aceptar conexiones de otros equipos de la red:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 2. Cliente Python (cliente)

Con la API arrancada:

```bash
pip install requests
python cliente/cliente.py                            # API local (http://localhost:8000)
python cliente/cliente.py http://192.168.1.34:8000   # API de otro equipo
```

Crea usuarios y productos, los lista, hace un pedido y consulta los pedidos del usuario,
comprobando el código HTTP de cada respuesta.

## 3. Frontend (frontend)

Con la API arrancada, abrir `frontend/index.html` en el navegador. En la cabecera se puede
cambiar la dirección de la API para usar la de otro equipo.

Todas las peticiones a la API están en `frontend/app.js`: la función `api()` hace las
llamadas con `fetch` y el objeto `Api` tiene un método por endpoint.
