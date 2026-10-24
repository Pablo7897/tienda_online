"use strict";

// ===========================================================================
// 1. CONFIGURACION: direccion de la API
// ===========================================================================
// Por defecto se usa la API local. Desde la cabecera de la pagina se puede cambiar
// por la IP de otro equipo (por ejemplo http://192.168.1.34:8000). La ultima
// direccion usada se recuerda en el navegador.

const URL_POR_DEFECTO = "http://localhost:8000";
let BASE_URL = leerUrlGuardada();

function leerUrlGuardada() {
  try {
    return localStorage.getItem("tienda_base_url") || URL_POR_DEFECTO;
  } catch {
    return URL_POR_DEFECTO;
  }
}

function guardarUrl(url) {
  try {
    localStorage.setItem("tienda_base_url", url);
  } catch {
    // Si el navegador no deja guardar, simplemente no se recuerda
  }
}


// ===========================================================================
// 2. PETICIONES A LA API
// ===========================================================================
// TODAS las peticiones HTTP del frontend pasan por la funcion api(). Usa fetch(),
// que es el equivalente en el navegador a requests en Python:
//   - metodo: "GET", "POST" o "DELETE"
//   - ruta:   el endpoint, por ejemplo "/productos"
//   - cuerpo: (opcional) objeto que se envia como JSON en los POST
// Si la API responde con un codigo de error (4xx/5xx) lanza una excepcion con el
// mensaje "detail" que devuelve FastAPI; si todo va bien devuelve el JSON recibido.

async function api(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(BASE_URL + ruta, opciones);
  } catch {
    // fetch solo falla asi cuando no hay conexion: servidor apagado, IP mal puesta...
    throw new Error(`No se puede conectar con la API en ${BASE_URL}. ¿Está arrancado el servidor?`);
  }

  // La API siempre responde en JSON, tambien cuando hay un error
  const datos = await respuesta.json().catch(() => null);

  // respuesta.ok es true para los codigos 200-299 (200, 201...)
  if (!respuesta.ok) {
    throw new Error(`Error ${respuesta.status}: ${textoDelError(datos)}`);
  }
  return datos;
}

// Convierte el "detail" de un error de FastAPI en un texto legible
function textoDelError(datos) {
  if (!datos || datos.detail === undefined) {
    return "respuesta inesperada del servidor";
  }
  // Errores lanzados en main.py con HTTPException (404, 409, 400): detail es un texto
  if (typeof datos.detail === "string") {
    return datos.detail;
  }
  // Errores de validacion de Pydantic (422): detail es una lista, un mensaje por campo
  return datos.detail
    .map((error) => {
      const campo = error.loc.filter((parte) => parte !== "body").join(".");
      const mensaje = error.msg.replace(/^Value error, /, "");
      return campo ? `${campo}: ${mensaje}` : mensaje;
    })
    .join(" · ");
}

// Un metodo por cada endpoint de la API que usa el frontend
const Api = {
  listarProductos: () => api("GET", "/productos"),
  crearProducto: (datos) => api("POST", "/productos", datos),
  eliminarProducto: (id) => api("DELETE", `/productos/${encodeURIComponent(id)}`),
  listarUsuarios: () => api("GET", "/usuarios"),
  crearUsuario: (datos) => api("POST", "/usuarios", datos),
  crearPedido: (datos) => api("POST", "/pedidos", datos),
  pedidosDeUsuario: (id) => api("GET", `/usuarios/${encodeURIComponent(id)}/pedidos`),
};


// ===========================================================================
// 3. UTILIDADES PARA LA INTERFAZ
// ===========================================================================

// Ultimos datos recibidos de la API, para rellenar tablas y desplegables
let productos = [];
let usuarios = [];

const $ = (id) => document.getElementById(id);

const formatoEuros = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });
const formatoFecha = new Intl.DateTimeFormat("es-ES", { dateStyle: "short", timeStyle: "short" });

function mostrarMensaje(id, texto, tipo) {
  const elemento = $(id);
  elemento.textContent = texto;
  elemento.className = `mensaje ${tipo || ""}`;
}

// Crea un elemento HTML con su texto. Se usa textContent (y no innerHTML) para que
// los datos que vienen de la API se muestren como texto y nunca se ejecuten como HTML.
function crear(etiqueta, texto, clase) {
  const elemento = document.createElement(etiqueta);
  if (texto !== undefined) elemento.textContent = texto;
  if (clase) elemento.className = clase;
  return elemento;
}

function filaTabla(celdas) {
  const fila = document.createElement("tr");
  for (const celda of celdas) {
    const td = document.createElement("td");
    if (celda instanceof Node) td.append(celda);
    else td.textContent = celda;
    fila.append(td);
  }
  return fila;
}

// Rellena un <select> conservando la opcion elegida si sigue existiendo
function rellenarSelect(select, opciones, textoVacio) {
  const elegido = select.value;
  select.replaceChildren();
  if (opciones.length === 0) {
    select.append(new Option(textoVacio, ""));
    select.disabled = true;
    return;
  }
  for (const { valor, texto } of opciones) {
    select.append(new Option(texto, valor));
  }
  select.disabled = false;
  if (opciones.some((o) => o.valor === elegido)) select.value = elegido;
}

const clientes = () => usuarios.filter((u) => !u.es_admin);

const NOMBRE_TIPO = { generico: "Genérico", electronico: "Electrónico", ropa: "Ropa" };


// ===========================================================================
// 4. PRODUCTOS
// ===========================================================================

// GET /productos -> pinta la tabla de productos
async function cargarProductos() {
  try {
    productos = await Api.listarProductos();
    mostrarMensaje("msg-lista-productos", "");
  } catch (error) {
    productos = [];
    mostrarMensaje("msg-lista-productos", error.message, "error");
  }
  pintarProductos();
  actualizarSelectsProductos();
}

function pintarProductos() {
  const tabla = $("tabla-productos");
  tabla.replaceChildren();
  $("vacio-productos").hidden = productos.length > 0;

  for (const p of productos) {
    let detalles = "—";
    if (p.tipo === "electronico") detalles = `Garantía: ${p.meses_garantia} meses`;
    if (p.tipo === "ropa") detalles = `Talla ${p.talla} · ${p.color}`;

    const botonEliminar = crear("button", "Eliminar", "peligro");
    botonEliminar.addEventListener("click", () => eliminarProducto(p));

    tabla.append(filaTabla([
      p.nombre,
      crear("span", NOMBRE_TIPO[p.tipo], `etiqueta-tipo ${p.tipo}`),
      formatoEuros.format(p.precio),
      String(p.stock),
      detalles,
      botonEliminar,
    ]));
  }
}

// DELETE /productos/{producto_id}
async function eliminarProducto(producto) {
  if (!confirm(`¿Eliminar el producto "${producto.nombre}"?`)) return;
  try {
    await Api.eliminarProducto(producto.id);
    mostrarMensaje("msg-lista-productos", `Producto "${producto.nombre}" eliminado.`, "ok");
  } catch (error) {
    mostrarMensaje("msg-lista-productos", error.message, "error");
  }
  await cargarProductos();
}

// Muestra solo los campos propios del tipo de producto elegido
function actualizarCamposProducto() {
  const tipo = $("producto-tipo").value;
  for (const campo of document.querySelectorAll(".solo-electronico")) campo.hidden = tipo !== "electronico";
  for (const campo of document.querySelectorAll(".solo-ropa")) campo.hidden = tipo !== "ropa";
  $("producto-garantia").required = tipo === "electronico";
  $("producto-talla").required = tipo === "ropa";
  $("producto-color").required = tipo === "ropa";
}

// POST /productos con los datos del formulario
async function crearProducto(evento) {
  evento.preventDefault();
  const tipo = $("producto-tipo").value;
  const datos = {
    tipo,
    nombre: $("producto-nombre").value.trim(),
    precio: Number($("producto-precio").value),
    stock: Number($("producto-stock").value),
  };
  // Solo se envian los atributos del tipo elegido, igual que espera ProductoCreate
  if (tipo === "electronico") datos.meses_garantia = Number($("producto-garantia").value);
  if (tipo === "ropa") {
    datos.talla = $("producto-talla").value.trim();
    datos.color = $("producto-color").value.trim();
  }

  try {
    const producto = await Api.crearProducto(datos);
    mostrarMensaje("msg-producto", `Producto "${producto.nombre}" creado.`, "ok");
    evento.target.reset();
    $("producto-tipo").value = tipo;
    await cargarProductos();
  } catch (error) {
    mostrarMensaje("msg-producto", error.message, "error");
  }
}


// ===========================================================================
// 5. USUARIOS
// ===========================================================================

// GET /usuarios -> pinta la tabla de usuarios
async function cargarUsuarios() {
  try {
    usuarios = await Api.listarUsuarios();
    mostrarMensaje("msg-lista-usuarios", "");
  } catch (error) {
    usuarios = [];
    mostrarMensaje("msg-lista-usuarios", error.message, "error");
  }
  pintarUsuarios();
  actualizarSelectsClientes();
}

function pintarUsuarios() {
  const tabla = $("tabla-usuarios");
  tabla.replaceChildren();
  $("vacio-usuarios").hidden = usuarios.length > 0;

  for (const u of usuarios) {
    tabla.append(filaTabla([
      u.nombre,
      u.email,
      u.es_admin ? "Administrador" : "Cliente",
      crear("code", u.id),
    ]));
  }
}

function actualizarCamposUsuario() {
  const esCliente = $("usuario-tipo").value === "cliente";
  for (const campo of document.querySelectorAll(".solo-cliente")) campo.hidden = !esCliente;
  $("usuario-direccion").required = esCliente;
}

// POST /usuarios con los datos del formulario
async function crearUsuario(evento) {
  evento.preventDefault();
  const tipo = $("usuario-tipo").value;
  const datos = {
    tipo,
    nombre: $("usuario-nombre").value.trim(),
    email: $("usuario-email").value.trim(),
  };
  // Los administradores no tienen direccion: la API la rechaza si se envia
  if (tipo === "cliente") datos.direccion = $("usuario-direccion").value.trim();

  try {
    const usuario = await Api.crearUsuario(datos);
    mostrarMensaje("msg-usuario", `Usuario "${usuario.nombre}" creado.`, "ok");
    evento.target.reset();
    $("usuario-tipo").value = tipo;
    await cargarUsuarios();
  } catch (error) {
    mostrarMensaje("msg-usuario", error.message, "error");
  }
}


// ===========================================================================
// 6. PEDIDOS
// ===========================================================================

// Solo los clientes pueden hacer pedidos (para un administrador la API devuelve 400)
function actualizarSelectsClientes() {
  const opciones = clientes().map((c) => ({ valor: c.id, texto: `${c.nombre} (${c.email})` }));
  rellenarSelect($("pedido-cliente"), opciones, "— No hay clientes —");
  rellenarSelect($("historial-cliente"), opciones, "— No hay clientes —");
}

function opcionesProductos() {
  return productos.map((p) => ({
    valor: p.id,
    texto: `${p.nombre} — ${formatoEuros.format(p.precio)} (stock: ${p.stock})`,
  }));
}

function actualizarSelectsProductos() {
  for (const select of document.querySelectorAll("#pedido-lineas select")) {
    rellenarSelect(select, opcionesProductos(), "— No hay productos —");
  }
}

// Añade una linea al formulario del pedido: un producto y su cantidad
function anadirLinea() {
  const linea = crear("div", undefined, "linea");

  const select = document.createElement("select");
  select.setAttribute("aria-label", "Producto");
  rellenarSelect(select, opcionesProductos(), "— No hay productos —");

  const cantidad = document.createElement("input");
  cantidad.type = "number";
  cantidad.min = "1";
  cantidad.step = "1";
  cantidad.value = "1";
  cantidad.required = true;
  cantidad.setAttribute("aria-label", "Cantidad");

  const quitar = crear("button", "Quitar", "secundario");
  quitar.type = "button";
  quitar.addEventListener("click", () => linea.remove());

  linea.append(select, cantidad, quitar);
  $("pedido-lineas").append(linea);
}

// POST /pedidos con el cliente y las lineas elegidas
async function crearPedido(evento) {
  evento.preventDefault();
  const items = [...document.querySelectorAll("#pedido-lineas .linea")]
    .map((linea) => ({
      producto_id: linea.querySelector("select").value,
      cantidad: Number(linea.querySelector("input").value),
    }))
    .filter((item) => item.producto_id);

  if (items.length === 0) {
    mostrarMensaje("msg-pedido", "Añade al menos un producto al pedido.", "error");
    return;
  }

  const datos = { cliente_id: $("pedido-cliente").value, items };
  $("resultado-pedido").replaceChildren();
  try {
    const pedido = await Api.crearPedido(datos);
    mostrarMensaje("msg-pedido", "Pedido creado correctamente.", "ok");
    $("resultado-pedido").append(tarjetaPedido(pedido));
    await cargarProductos(); // el stock ha cambiado
  } catch (error) {
    mostrarMensaje("msg-pedido", error.message, "error");
  }
}

// GET /usuarios/{cliente_id}/pedidos
async function consultarPedidos(evento) {
  evento.preventDefault();
  const clienteId = $("historial-cliente").value;
  const lista = $("lista-pedidos");
  lista.replaceChildren();
  try {
    const pedidos = await Api.pedidosDeUsuario(clienteId);
    const cliente = usuarios.find((u) => u.id === clienteId);
    const nombre = cliente ? cliente.nombre : "este cliente";
    if (pedidos.length === 0) {
      mostrarMensaje("msg-historial", `${nombre} todavía no ha hecho ningún pedido.`);
      return;
    }
    mostrarMensaje("msg-historial", `${nombre} tiene ${pedidos.length} pedido(s).`, "ok");
    for (const pedido of pedidos) lista.append(tarjetaPedido(pedido));
  } catch (error) {
    mostrarMensaje("msg-historial", error.message, "error");
  }
}

// Muestra un pedido recibido de la API (esquema PedidoRead)
function tarjetaPedido(pedido) {
  const tarjeta = crear("article", undefined, "pedido");

  const cabecera = crear("div", undefined, "pedido-cabecera");
  cabecera.append(
    crear("span", formatoFecha.format(new Date(pedido.fecha))),
    crear("strong", formatoEuros.format(pedido.total)),
  );

  const lineas = document.createElement("ul");
  for (const item of pedido.items) {
    lineas.append(crear(
      "li",
      `${item.cantidad} × ${item.nombre} (${formatoEuros.format(item.precio_unitario)}) = ${formatoEuros.format(item.subtotal)}`,
    ));
  }

  tarjeta.append(cabecera, lineas, crear("small", `Pedido ${pedido.id}`));
  return tarjeta;
}


// ===========================================================================
// 7. CONEXION, PESTAÑAS E INICIO
// ===========================================================================

// Comprueba que la API responde y carga todos los datos
async function conectar() {
  const estado = $("estado-servidor");
  estado.textContent = "Conectando…";
  estado.className = "estado";
  try {
    await Api.listarUsuarios();
    estado.textContent = "Conectado";
    estado.className = "estado ok";
  } catch (error) {
    estado.textContent = "Sin conexión";
    estado.className = "estado error";
    estado.title = error.message;
  }
  await Promise.all([cargarProductos(), cargarUsuarios()]);
}

function cambiarServidor(evento) {
  evento.preventDefault();
  BASE_URL = $("input-servidor").value.trim().replace(/\/+$/, "");
  $("input-servidor").value = BASE_URL;
  guardarUrl(BASE_URL);
  conectar();
}

function mostrarPestana(nombre) {
  for (const boton of document.querySelectorAll(".pestana")) {
    boton.classList.toggle("activa", boton.dataset.pestana === nombre);
  }
  for (const seccion of document.querySelectorAll(".seccion")) {
    seccion.hidden = seccion.id !== `pestana-${nombre}`;
  }
}

function iniciar() {
  $("input-servidor").value = BASE_URL;
  $("form-servidor").addEventListener("submit", cambiarServidor);

  for (const boton of document.querySelectorAll(".pestana")) {
    boton.addEventListener("click", () => mostrarPestana(boton.dataset.pestana));
  }

  $("btn-recargar-productos").addEventListener("click", cargarProductos);
  $("producto-tipo").addEventListener("change", actualizarCamposProducto);
  $("form-producto").addEventListener("submit", crearProducto);

  $("btn-recargar-usuarios").addEventListener("click", cargarUsuarios);
  $("usuario-tipo").addEventListener("change", actualizarCamposUsuario);
  $("form-usuario").addEventListener("submit", crearUsuario);

  $("btn-anadir-linea").addEventListener("click", anadirLinea);
  $("form-pedido").addEventListener("submit", crearPedido);
  $("form-historial").addEventListener("submit", consultarPedidos);

  actualizarCamposProducto();
  actualizarCamposUsuario();
  anadirLinea();
  conectar();
}

iniciar();
