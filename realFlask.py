import os
import re
import io
import json
from datetime import datetime, timezone
from flask import Flask, jsonify
from flask import flash
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import send_file
from flask import session
from flask import g
from markupsafe import Markup
from supabase import create_client, Client
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

import ean13

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# Hasta aquí es solo formato.
# Esto es para conectarse a la base de datos en supabase.
# La carpeta .env contiene la supabase url y la publishable key.
# Eso lo tendremos que quitar del git luego, se supone que es privado. 
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_PUBLISHABLE_KEY")
)

SYSTEM_PARAMETER_DEFAULTS = {
    "id": 1,
    "razon_social": "",
    "rut": "",
    "giro": "",
    "direccion": "",
    "telefono": "",
    "correo": "",
    "moneda": "CLP",
    "formato_moneda": "$#,##0",
    "porcentaje_impuesto": 0,
    "logotipo": "img/logo.png",
    "fecha_actualizacion": None,
    "usuario_actualizacion": "Admin"
}
ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_LOGO_SIZE = 2 * 1024 * 1024


# El rollo de la impresora SATO trae 3 etiquetas por fila.
ETIQUETAS_POR_FILA = 3


@app.errorhandler(APIError)
def error_base_datos(error):
    # Errores de Supabase que ninguna ruta capturó (por ejemplo, un código EAN
    # más largo de lo permitido): se muestra el mensaje en vez de un error 500.
    return f"Error de base de datos: {error.message}", 400


def _texto_o_nulo(valor):
    # Los campos opcionales vacíos se guardan como NULL (los códigos EAN tienen check de solo dígitos).
    valor = (valor or '').strip()
    return valor or None


def obtener_parametros_sistema():
    """Returns the singleton configuration, or defaults if it is not configured yet."""
    response = supabase.table("parametros_sistema").select("*").eq("id", 1).execute()
    if not response.data:
        return SYSTEM_PARAMETER_DEFAULTS.copy()
    return {**SYSTEM_PARAMETER_DEFAULTS, **response.data[0]}


def obtener_porcentaje_impuesto():
    """Shared accessor for future order/document amount calculations."""
    return float(obtener_parametros_sistema().get("porcentaje_impuesto", 0))


def obtener_moneda_sistema():
    """Shared accessor for future amount formatting and generated documents."""
    parametros = obtener_parametros_sistema()
    return parametros.get("moneda", "CLP"), parametros.get("formato_moneda", "$#,##0")


def obtener_url_logotipo():
    """Builds the static URL for the configured logo, with the current logo as fallback."""
    parametros = obtener_parametros_sistema()
    return url_for("static", filename=parametros.get("logotipo", "img/logo.png"))


# ---------------------------------------------------------------------
# Usuarios, roles y permisos (RF-057/058). Las tablas están en supabase/roles.sql.
# No hay roles predefinidos: se crean en roles.html eligiendo, por módulo, si el
# rol puede "ver" (abrir la pantalla, buscar y filtrar) y/o "editar" (crear,
# modificar o borrar). El primer usuario se crea como superusuario (acceso total).

# (código guardado en rol_permisos.modulo, nombre visible, endpoints que cubre)
MODULOS_SISTEMA = [
    ('pedidos', 'Pedidos', ['pedidos', 'verDetalle', 'crudDetallePedido']),
    ('despachos', 'Despachos', ['despachos']),
    ('facturas', 'Facturas', ['facturas']),
    ('notas_credito', 'Notas de crédito', ['notasCredito']),
    ('pagos', 'Pagos', ['pagos']),
    ('cobranza', 'Informe de cobranza', ['informeCobranza', 'informeCobranzaPDF']),
    ('reportes', 'Reportes, informes y análisis', [
        'reportes', 'informeProductosDespachados', 'informeProductosEnProceso',
        'informeProductosPendientesDespacho', 'informeProductosTerminados',
        'analisisDespachoClienteProducto', 'analisisDespachoSegunFacturaCliente',
        'analisisDespachoVendedorProducto', 'analisisPedidosDespachosMensuales',
        'analisisVentasDescuentos', 'analisisProductosPedidosDespachados',
    ]),
    ('produccion', 'Producción y cortes', ['produccion', 'cortes', 'resumenProduccion']),
    ('inventario', 'Inventario e ingreso a bodega', ['inventario', 'ingresoBodega']),
    ('clientes', 'Clientes', ['clientes']),
    ('productos', 'Productos', ['productos']),
    ('vendedores', 'Vendedores', ['vendedores']),
    ('bodegas', 'Bodegas', ['bodegas']),
    ('colores', 'Colores', ['colores']),
    ('tallas', 'Tallas', ['tallas']),
    ('zonas_venta', 'Zonas de venta', ['zonasVenta']),
    ('codigos_ean', 'Códigos EAN y etiquetas', ['codigosEAN', 'emisionEAN']),
    ('configuracion', 'Configuración', ['configuracion']),
    ('roles_usuarios', 'Roles y usuarios', ['roles', 'usuarios']),
]
CODIGOS_MODULO = [codigo for codigo, _, _ in MODULOS_SISTEMA]
MODULO_POR_ENDPOINT = {
    endpoint: codigo for codigo, _, endpoints in MODULOS_SISTEMA for endpoint in endpoints
}

# Se abren sin sesión / basta con tener sesión. Cualquier otro endpoint que no esté
# en MODULOS_SISTEMA queda solo para superusuarios hasta que se le asigne un módulo.
ENDPOINTS_PUBLICOS = {'static', 'login', 'primerUsuario'}
ENDPOINTS_SOLO_SESION = {'index', 'archivosMaestros', 'logout'}

# En estas pantallas el POST solo filtra o arma una vista, no modifica datos.
ENDPOINTS_POST_LECTURA = set(dict((c, e) for c, _, e in MODULOS_SISTEMA)['reportes']) | {
    'resumenProduccion', 'inventario', 'emisionEAN',
}


def _es_tabla_faltante(error):
    # PGRST205: la tabla no existe. 42703: existe pero le falta una columna
    # (supabase/roles.sql todavía no se ejecutó sobre la tabla "usuarios" que ya había).
    return 'PGRST205' in str(error) or '42703' in str(error)


def _peticion_es_lectura():
    if request.method in ('GET', 'HEAD', 'OPTIONS') or request.endpoint in ENDPOINTS_POST_LECTURA:
        return True
    # Los CRUD hacen sus búsquedas por POST con _method=buscar..., verDetalle o get.
    metodo = request.form.get('_method', '')
    return metodo.startswith('buscar') or metodo in ('verDetalle', 'get')


def cargar_usuario_sesion():
    """Deja en g.usuario el usuario con sesión (o None) y en g.permisos sus permisos por módulo."""
    g.usuario, g.permisos = None, {}
    id_usuario = session.get('id_usuario')
    if not id_usuario:
        return
    filas = supabase.table('usuarios').select(
        'id_usuario, nombre_usuario, nombre, id_rol, es_superusuario, activo'
    ).eq('id_usuario', id_usuario).execute().data
    if not filas or not filas[0].get('activo'):
        session.pop('id_usuario', None)
        return
    usuario = filas[0]
    usuario['rol'] = None
    if usuario.get('es_superusuario'):
        g.permisos = {codigo: {'ver': True, 'editar': True} for codigo in CODIGOS_MODULO}
    elif usuario.get('id_rol'):
        rol = supabase.table('roles').select('nombre').eq('id_rol', usuario['id_rol']).execute().data
        usuario['rol'] = rol[0]['nombre'] if rol else None
        permisos = supabase.table('rol_permisos').select(
            'modulo, puede_ver, puede_editar'
        ).eq('id_rol', usuario['id_rol']).execute().data
        for fila in permisos:
            # Editar implica ver.
            g.permisos[fila['modulo']] = {
                'ver': bool(fila.get('puede_ver') or fila.get('puede_editar')),
                'editar': bool(fila.get('puede_editar')),
            }
    g.usuario = usuario


def usuario_puede(modulo, accion='ver'):
    return bool(g.get('permisos', {}).get(modulo, {}).get(accion))


def _existen_usuarios():
    # Pide las columnas y tablas que agrega supabase/roles.sql, para avisar si falta ejecutarlo.
    supabase.table('roles').select('id_rol').limit(1).execute()
    supabase.table('rol_permisos').select('id_rol').limit(1).execute()
    return bool(supabase.table('usuarios').select(
        'id_usuario, nombre_usuario, password_hash, id_rol, es_superusuario'
    ).limit(1).execute().data)


def _pantalla_sin_tablas():
    return render_template('login.html', modo='sin_tablas'), 503


def _destino_seguro(destino):
    # Solo rutas internas, para que ?next= no pueda redirigir a otro sitio.
    if destino and destino.startswith('/') and not destino.startswith('//') and '\\' not in destino:
        return destino
    return url_for('index')


@app.before_request
def verificar_acceso():
    if request.endpoint is None or request.endpoint in ENDPOINTS_PUBLICOS:
        return None
    try:
        cargar_usuario_sesion()
        if g.usuario is None:
            if not _existen_usuarios():
                return redirect(url_for('primerUsuario'))
            destino = request.full_path if request.query_string else request.path
            return redirect(url_for('login', next=destino))
    except APIError as error:
        if _es_tabla_faltante(error):
            return _pantalla_sin_tablas()
        raise

    modulo = MODULO_POR_ENDPOINT.get(request.endpoint)
    if modulo is None:
        if request.endpoint in ENDPOINTS_SOLO_SESION or g.usuario.get('es_superusuario'):
            return None
        flash('Esta sección todavía no tiene permisos configurables; solo un superusuario puede abrirla.', 'error')
        return redirect(url_for('index'))
    if _peticion_es_lectura():
        if not usuario_puede(modulo, 'ver'):
            flash('Tu rol no tiene permiso para ver esa sección.', 'error')
            return redirect(url_for('index'))
    elif not usuario_puede(modulo, 'editar'):
        if usuario_puede(modulo, 'ver'):
            flash('Tu rol solo permite consultar esta sección, no modificarla.', 'error')
            return redirect(request.path)
        flash('Tu rol no tiene permiso para modificar esa sección.', 'error')
        return redirect(url_for('index'))
    return None


@app.context_processor
def datos_sesion_plantillas():
    usuario = g.get('usuario')
    # Rutas de las secciones que el rol no puede ver, para ocultar sus enlaces.
    rutas_bloqueadas = []
    if usuario and not usuario.get('es_superusuario'):
        for codigo, _, endpoints in MODULOS_SISTEMA:
            if not usuario_puede(codigo, 'ver'):
                rutas_bloqueadas += [url_for(e) for e in endpoints if e in app.view_functions]
    return {'usuario_actual': usuario, 'puede': usuario_puede, 'rutas_bloqueadas': rutas_bloqueadas}


def _leer_usuario_formulario(nuevo):
    """Valida el formulario de usuario. Devuelve (datos, mensaje_de_error)."""
    nombre_usuario = request.form.get('nombre_usuario', '').strip().lower()
    nombre = request.form.get('nombre', '').strip()
    password = request.form.get('password', '')
    datos = {'nombre': nombre, 'correo': _texto_o_nulo(request.form.get('correo'))}
    if nuevo:
        if not re.fullmatch(r'[a-z0-9._-]{3,40}', nombre_usuario):
            return None, 'El nombre de usuario debe tener entre 3 y 40 caracteres: letras, números, punto, guion o guion bajo.'
        datos['nombre_usuario'] = nombre_usuario
    if not nombre:
        return None, 'Ingresa el nombre de la persona.'
    # Al editar, la contraseña solo cambia si se escribe una nueva.
    if nuevo or password:
        if len(password) < 8:
            return None, 'La contraseña debe tener al menos 8 caracteres.'
        if password != request.form.get('password_confirmacion', ''):
            return None, 'Las contraseñas no coinciden.'
        datos['password_hash'] = generate_password_hash(password)
    return datos, None


@app.route('/login.html', methods=['GET', 'POST'])
def login():
    try:
        if not _existen_usuarios():
            return redirect(url_for('primerUsuario'))
    except APIError as error:
        if _es_tabla_faltante(error):
            return _pantalla_sin_tablas()
        raise
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario', '').strip().lower()
        filas = supabase.table('usuarios').select(
            'id_usuario, password_hash, activo'
        ).eq('nombre_usuario', nombre_usuario).execute().data
        if filas and filas[0].get('activo') and check_password_hash(filas[0]['password_hash'], request.form.get('password', '')):
            session.clear()
            session['id_usuario'] = filas[0]['id_usuario']
            return redirect(_destino_seguro(request.form.get('next')))
        flash('Usuario o contraseña incorrectos, o la cuenta está desactivada.', 'error')
    return render_template('login.html', modo='login', siguiente=request.values.get('next', ''))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Sesión cerrada.')
    return redirect(url_for('login'))


@app.route('/primerUsuario.html', methods=['GET', 'POST'])
def primerUsuario():
    # Solo existe mientras no haya ningún usuario: crea el superusuario inicial.
    try:
        if _existen_usuarios():
            return redirect(url_for('login'))
    except APIError as error:
        if _es_tabla_faltante(error):
            return _pantalla_sin_tablas()
        raise
    if request.method == 'POST':
        datos, error = _leer_usuario_formulario(nuevo=True)
        if error:
            flash(error, 'error')
        else:
            datos.update(es_superusuario=True, activo=True)
            fila = supabase.table('usuarios').insert(datos).execute().data
            session.clear()
            session['id_usuario'] = fila[0]['id_usuario']
            flash('Cuenta de superusuario creada. Ahora crea los roles y usuarios del sistema.')
            return redirect(url_for('roles'))
    return render_template('login.html', modo='primer_usuario')


def _leer_permisos_formulario():
    permisos = []
    for codigo in CODIGOS_MODULO:
        editar = request.form.get(f'editar_{codigo}') == 'on'
        ver = editar or request.form.get(f'ver_{codigo}') == 'on'
        if ver:
            permisos.append({'modulo': codigo, 'puede_ver': True, 'puede_editar': editar})
    return permisos


@app.route('/roles.html', methods=['GET', 'POST'])
def roles():
    if request.method == 'POST':
        metodo = request.form.get('_method')
        id_rol = request.form.get('id_rol')
        if metodo in ('post', 'put'):
            nombre = request.form.get('nombre', '').strip()
            datos_rol = {'nombre': nombre, 'descripcion': _texto_o_nulo(request.form.get('descripcion'))}
            repetidos = supabase.table('roles').select('id_rol').eq('nombre', nombre).execute().data
            if not nombre:
                flash('El rol necesita un nombre.', 'error')
            elif any(str(fila['id_rol']) != str(id_rol) for fila in repetidos):
                flash(f'Ya existe un rol llamado "{nombre}".', 'error')
            else:
                if metodo == 'post':
                    id_rol = supabase.table('roles').insert(datos_rol).execute().data[0]['id_rol']
                    flash(f'Rol "{nombre}" creado.')
                else:
                    supabase.table('roles').update(datos_rol).eq('id_rol', id_rol).execute()
                    supabase.table('rol_permisos').delete().eq('id_rol', id_rol).execute()
                    flash(f'Rol "{nombre}" actualizado.')
                permisos = _leer_permisos_formulario()
                if permisos:
                    supabase.table('rol_permisos').insert(
                        [{**permiso, 'id_rol': id_rol} for permiso in permisos]
                    ).execute()
        elif metodo == 'delete':
            if supabase.table('usuarios').select('id_usuario').eq('id_rol', id_rol).execute().data:
                flash('No se puede eliminar un rol con usuarios asignados; asígnales otro rol primero.', 'error')
            else:
                supabase.table('roles').delete().eq('id_rol', id_rol).execute()
                flash('Rol eliminado.')
        return redirect(url_for('roles'))

    lista_roles = supabase.table('roles').select('*').order('nombre').execute().data
    permisos = supabase.table('rol_permisos').select('*').execute().data
    usuarios_con_rol = supabase.table('usuarios').select('id_usuario, id_rol').execute().data
    for rol in lista_roles:
        rol['permisos'] = {
            p['modulo']: {'ver': bool(p['puede_ver'] or p['puede_editar']), 'editar': bool(p['puede_editar'])}
            for p in permisos if p['id_rol'] == rol['id_rol']
        }
        rol['cantidad_usuarios'] = sum(1 for u in usuarios_con_rol if u['id_rol'] == rol['id_rol'])
    return render_template('roles.html', roles=lista_roles, modulos=MODULOS_SISTEMA)


@app.route('/usuarios.html', methods=['GET', 'POST'])
def usuarios():
    if request.method == 'POST':
        metodo = request.form.get('_method')
        id_rol = request.form.get('id_rol') or None
        if metodo == 'post':
            datos, error = _leer_usuario_formulario(nuevo=True)
            if not error and not id_rol:
                error = 'Asigna un rol al usuario.'
            if not error and supabase.table('usuarios').select('id_usuario').eq('nombre_usuario', datos['nombre_usuario']).execute().data:
                error = 'Ese nombre de usuario ya está en uso.'
            if error:
                flash(error, 'error')
            else:
                supabase.table('usuarios').insert({**datos, 'id_rol': id_rol, 'activo': True}).execute()
                flash(f'Usuario "{datos["nombre_usuario"]}" creado.')
        elif metodo in ('put', 'delete'):
            id_usuario = request.form.get('id_usuario')
            filas = supabase.table('usuarios').select(
                'id_usuario, nombre_usuario, es_superusuario'
            ).eq('id_usuario', id_usuario).execute().data
            es_propio = str(id_usuario) == str(g.usuario['id_usuario'])
            if not filas:
                flash('El usuario ya no existe.', 'error')
            elif filas[0]['es_superusuario'] and not g.usuario.get('es_superusuario'):
                flash('Solo un superusuario puede modificar a otro superusuario.', 'error')
            elif metodo == 'delete':
                if es_propio:
                    flash('No puedes eliminar tu propia cuenta.', 'error')
                else:
                    supabase.table('usuarios').delete().eq('id_usuario', id_usuario).execute()
                    flash(f'Usuario "{filas[0]["nombre_usuario"]}" eliminado.')
            else:
                datos, error = _leer_usuario_formulario(nuevo=False)
                if not error:
                    datos['activo'] = request.form.get('activo') == 'on'
                    if es_propio and not datos['activo']:
                        error = 'No puedes desactivar tu propia cuenta.'
                    elif not filas[0]['es_superusuario']:
                        # El superusuario no usa rol; el resto siempre necesita uno.
                        if not id_rol:
                            error = 'Asigna un rol al usuario.'
                        datos['id_rol'] = id_rol
                if error:
                    flash(error, 'error')
                else:
                    supabase.table('usuarios').update(datos).eq('id_usuario', id_usuario).execute()
                    flash(f'Usuario "{filas[0]["nombre_usuario"]}" actualizado.')
        return redirect(url_for('usuarios'))

    lista_roles = supabase.table('roles').select('id_rol, nombre').order('nombre').execute().data
    nombres_rol = {rol['id_rol']: rol['nombre'] for rol in lista_roles}
    lista_usuarios = supabase.table('usuarios').select(
        'id_usuario, nombre_usuario, nombre, correo, id_rol, es_superusuario, activo'
    ).order('nombre').execute().data
    for usuario in lista_usuarios:
        usuario['rol'] = nombres_rol.get(usuario['id_rol'])
    return render_template('usuarios.html', usuarios=lista_usuarios, roles=lista_roles)

# NOTA: las páginas html tienen que estar dentro de templates

@app.route('/pedidos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def pedidos():
    clientes_response = supabase.table("clientes").select("id_cliente, nombre").execute()
    vendedores_response = supabase.table("vendedores").select("id_vendedor, nombre").execute()
    productos_response = supabase.table("producto_variantes").select("id_variante, descripcion").execute()
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            cliente = request.form['IDClienteCrear']
            fechaPedido = request.form['fechaPedidoCrear']
            fechaLimite = request.form['fechaLimiteCrear']
            vendedor = request.form['IDVendedorCrear']

            try:
                cliente = int(cliente)
                vendedor = int(vendedor)
            except ValueError:
                flash("El cliente o vendedor seleccionado no es válido", "error")
                return redirect(url_for('pedidos'))

            try:
                response = (
                    supabase.table("pedidos").insert({"cliente_asociado": cliente, "fecha_pedido": fechaPedido,
                            "fecha_entrega": fechaLimite, "vendedor_asociado": vendedor
                            }).execute()
                )
            except APIError:
                flash("No se pudo crear el pedido. Revisa el cliente y vendedor seleccionados", "error")
                return redirect(url_for('pedidos'))
            if response.data:
                flash("Pedido creado exitosamente", "success")
                return redirect(url_for('pedidos'))
            else:
                flash("Error creando pedido", "error")
                return redirect(url_for('pedidos'))
        if (metodo == "put"):
            idAACtualizar = request.form['IdPedidoActualizar']
            cliente = request.form['IDClienteActualizar']
            fechaPedido = request.form['fechaPedidoActualizar']
            fechaLimite = request.form['fechaLimiteActualizar']
            vendedor = request.form['IDVendedorActualizar']
            try:
                cliente = int(cliente)
                vendedor = int(vendedor)
            except ValueError:
                flash("El cliente o vendedor seleccionado no es válido", "error")
                return redirect(url_for('pedidos'))
            response = (
                
                supabase.table("pedidos").update({"cliente_asociado": cliente, "fecha_pedido": fechaPedido,
                        "fecha_entrega": fechaLimite, "vendedor_asociado": vendedor
                        }).eq("id_pedido", idAACtualizar).select("id_pedido").execute()
            )
            if response.data:
                flash("Pedido actualizado exitosamente", "success")
                return redirect(url_for('pedidos'))
            else:
                flash("Error actualizando pedido", "error")
                return redirect(url_for('pedidos'))
        if (metodo == "delete"):
            idABorrar = request.form['idPedidoBorrar']
            response = (
                supabase.table("pedidos").delete()
                .eq("id_pedido", idABorrar)
                .execute()
            )
            if response.data:
                flash("Pedido borrado exitosamente", "success")
                return redirect(url_for('pedidos'))
            else:
                flash("Error borrando pedido", "error")
                return redirect(url_for('pedidos'))
        if (metodo == "buscarFechaPedido"):
            texto = request.form["fechaPedidoBuscar"]
            response = (supabase.table("pedidos").select("*").eq("fecha_pedido", texto).execute())
            #response = supabase.rpc('buscarpedidoporfecha', { 'fechabusqueda': texto }).execute()
            if response.data:
                return render_template('pedidos.html', datos = response.data,clientes=clientes_response.data,
                            vendedores=vendedores_response.data,
                            productos=productos_response.data)
            else:
                return "No se ha encontrado ningún pedido con la fecha buscada"
        if (metodo == "buscarFechaEntrega"):
                    texto = request.form["fechaEntregaBuscar"]
                    response = (supabase.table("pedidos").select("*").eq("fecha_entrega", texto).execute())
                    #response = supabase.rpc('buscarpedidoporfechaentrega', { 'fechabusqueda': texto }).execute()
                    if response.data:
                        return render_template('pedidos.html', datos = response.data,clientes=clientes_response.data,
                                    vendedores=vendedores_response.data,
                                    productos=productos_response.data)
                    else:
                        return "No se ha encontrado ningún pedido con la fecha buscada"
        if (metodo == "buscarProductos"):
            texto = request.form["ProductoBuscarn"]
            #aux = supabase.table("detalle_pedidos").select("id_pedido").eq("id_variante", texto)
            #aux3 = supabase.table("pedidos").select("*").eq("id_pedido", aux)
            response = (supabase.table("pedidos").select("*, detalle_pedidos!inner(id_variante)")
                        .eq("detalle_pedidos.id_variante", texto)
                        .execute())
            #response = supabase.rpc('buscarpedidosporproducto', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('pedidos.html', datos = response.data,clientes=clientes_response.data,
                            vendedores=vendedores_response.data,
                            productos=productos_response.data)
            else:
                return "No se ha encontrado ningún pedido con el producto buscado"
        if (metodo == "buscarClientes"):
            texto = request.form["ClienteBuscarn"]
            response = (supabase.table("pedidos").select("*").eq("cliente_asociado", texto).execute())
            #response = supabase.rpc('buscarpedidoporcliente', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('pedidos.html', datos = response.data,clientes=clientes_response.data,
                            vendedores=vendedores_response.data,
                            productos=productos_response.data)
            else:
                return "No se ha encontrado ningún pedido con el cliente buscado"
        if (metodo == "buscarVendedores"):
            texto = request.form["VendedorBuscarn"]
            response = (supabase.table("pedidos").select("*").eq("vendedor_asociado", texto).execute())
            #response = supabase.rpc('buscarpedidoporvendedor', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('pedidos.html', datos = response.data,clientes=clientes_response.data,
                            vendedores=vendedores_response.data,
                            productos=productos_response.data)
            else:
                return "No se ha encontrado ningún pedido con el vendedor buscado"           
    else:
        response =(
            supabase.table("pedidos").select("*").execute()
        )
        clientes_response = supabase.table("clientes").select("id_cliente, nombre").execute()
        vendedores_response = supabase.table("vendedores").select("id_vendedor, nombre").execute()
            
        return render_template(
            'pedidos.html',
            datos=response.data,
            clientes=clientes_response.data,
            vendedores=vendedores_response.data
        )


@app.route('/verDetalle.html', methods=['GET'])
def verDetalle():
    id_pedido = request.args.get('id_pedido', '').strip()
    try:
        id_pedido = int(id_pedido)
        if id_pedido <= 0:
            raise ValueError
    except ValueError:
        flash("El identificador del pedido no es válido", "error")
        return redirect(url_for('pedidos'))

    response = (
        supabase.table('v_pendientes_despacho')
        .select('*')
        .eq('id_pedido', id_pedido)
        .execute()
    )
    filas = response.data or []

    # La vista de pendientes no incluye líneas completamente despachadas.
    if not filas:
        detalle_response = (
            supabase.table('v_detalle_pedido_pendiente')
            .select('*')
            .eq('id_pedido', id_pedido)
            .execute()
        )
        filas = detalle_response.data or []
        if not filas:
            pedido_response = (
                supabase.table('pedidos')
                .select('id_pedido, estado')
                .eq('id_pedido', id_pedido)
                .execute()
            )
            pedido = next(iter(pedido_response.data or []), None)
            if pedido and pedido.get('estado') == 'anulado':
                flash("El pedido está anulado y no tiene detalle disponible", "error")
            else:
                flash("No se encontró el pedido o no tiene líneas disponibles", "error")
            return redirect(url_for('pedidos'))

    detalle = []
    unidades_pendientes = 0
    unidades_cumplibles = 0
    for fila in filas:
        pendiente = int(fila.get('cantidad_pendiente') or 0)
        cumplible = int(fila.get('cantidad_lista_para_despacho') or 0)
        faltante = max(pendiente - cumplible, 0)
        porcentaje_linea = round(cumplible / pendiente * 100, 1) if pendiente else 100.0
        detalle.append({
            **fila,
            'cantidad_pendiente': pendiente,
            'stock_disponible': fila.get('stock_disponible'),
            'cantidad_cumplible': cumplible,
            'cantidad_faltante': faltante,
            'porcentaje_cumplible': porcentaje_linea,
        })
        unidades_pendientes += pendiente
        unidades_cumplibles += cumplible

    unidades_faltantes = max(unidades_pendientes - unidades_cumplibles, 0)
    pedido_completo = unidades_pendientes == 0
    porcentaje_cumplible = (
        100.0 if pedido_completo
        else round(unidades_cumplibles / unidades_pendientes * 100, 1)
    )

    return render_template(
        'verDetalle.html',
        id_pedido=id_pedido,
        detalle=detalle,
        unidades_pendientes=unidades_pendientes,
        unidades_cumplibles=unidades_cumplibles,
        unidades_faltantes=unidades_faltantes,
        porcentaje_cumplible=porcentaje_cumplible,
        pedido_completo=pedido_completo,
    )


@app.template_filter('moneda')
def formatear_moneda(valor):
    """Monto en pesos con separador de miles: $12.500 (formato qqqq del Documento 0)."""
    try:
        return '$' + f'{float(valor or 0):,.0f}'.replace(',', '.')
    except (TypeError, ValueError):
        return valor


def _numero_positivo(valor, permitir_cero=False):
    """Monto escrito por el usuario (acepta coma decimal). None si no es válido."""
    try:
        numero = float(str(valor).strip().replace(',', '.'))
    except (TypeError, ValueError):
        return None
    if numero < 0 or (numero == 0 and not permitir_cero):
        return None
    return round(numero, 2)


def _descuentos_factura(id_factura):
    """Lo que ya rebaja la factura: pagos vigentes aplicados y notas de crédito vigentes."""
    aplicaciones = supabase.table('pago_facturas').select('id_pago, monto_aplicado') \
        .eq('id_factura', id_factura).execute().data or []
    ids_pago = {a['id_pago'] for a in aplicaciones}
    vigentes = {p['id_pago'] for p in supabase.table('pagos').select('id_pago, estado')
                .in_('id_pago', list(ids_pago)).execute().data or []
                if (p.get('estado') or 'vigente') == 'vigente'} if ids_pago else set()
    pagado = sum(float(a.get('monto_aplicado') or 0) for a in aplicaciones if a['id_pago'] in vigentes)
    notas = sum(float(n.get('monto_total') or 0) for n in supabase.table('notas_credito')
                .select('monto_total, estado').eq('factura_referencia', id_factura).execute().data or []
                if (n.get('estado') or 'vigente') == 'vigente')
    return pagado, notas


def _recalcular_factura(id_factura):
    """saldo_pendiente = monto_total - pagos aplicados - notas de crédito (mismo criterio
    que supabase/incremento4_feedback.sql), y su estado con _estado_para_saldo()."""
    filas = supabase.table('facturas').select('id_factura, monto_total, estado') \
        .eq('id_factura', id_factura).execute().data
    if not filas or filas[0].get('estado') == 'anulada':
        return
    pagado, notas = _descuentos_factura(id_factura)
    saldo = max(round(float(filas[0].get('monto_total') or 0) - pagado - notas, 2), 0)
    supabase.table('facturas').update({
        'saldo_pendiente': saldo,
        'estado': _estado_para_saldo(filas[0].get('monto_total'), saldo),
    }).eq('id_factura', id_factura).execute()


def _leer_factura_formulario(sufijo):
    """Valida el modal de facturas ("Crear" o "Actualizar"). Devuelve (datos, error)."""
    try:
        folio = int(request.form.get('folio' + sufijo, ''))
        if folio <= 0:
            raise ValueError
    except ValueError:
        return None, 'El folio debe ser un número entero mayor que cero.'
    id_pedido = _entero_positivo(request.form.get('pedido' + sufijo))
    if not id_pedido:
        return None, 'Seleccione el pedido asociado a la factura.'
    pedido = supabase.table('pedidos').select('id_pedido, cliente_asociado, estado') \
        .eq('id_pedido', id_pedido).execute().data
    if not pedido:
        return None, 'El pedido seleccionado no existe.'
    if pedido[0].get('estado') == 'anulado':
        return None, 'No se puede facturar un pedido anulado.'
    fecha = (request.form.get('fechaEmision' + sufijo) or '').strip()
    if not fecha:
        return None, 'Ingrese la fecha de emisión.'
    neto = _numero_positivo(request.form.get('montoNeto' + sufijo), permitir_cero=True)
    if neto is None:
        return None, 'El monto neto debe ser un número mayor o igual a cero.'
    # El impuesto sale del porcentaje configurado en Configuración (RF-056).
    impuesto = round(neto * obtener_porcentaje_impuesto() / 100, 2)
    return {
        'folio': folio,
        'pedido_asociado': id_pedido,
        # El cliente es el del pedido, para que no puedan quedar distintos.
        'cliente_asociado': pedido[0].get('cliente_asociado'),
        'fecha_emision': fecha,
        'monto_neto': neto,
        'monto_impuesto': impuesto,
        'monto_total': round(neto + impuesto, 2),
    }, None


def _folio_repetido(tabla, clave, folio, id_actual=None):
    filas = supabase.table(tabla).select(f'{clave}, folio').eq('folio', folio).execute().data or []
    return any(str(f.get(clave)) != str(id_actual) for f in filas)


@app.route('/facturas.html', methods=['GET', 'POST', 'PUT', 'DELETE'])
def facturas():
    # RF-029/030. Esquema de supabase/facturas.sql. Una factura con pagos, notas de
    # crédito o despachos no se elimina: se anula (estado 'anulada').
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == 'post':
            datos, error = _leer_factura_formulario('Crear')
            if not error and _folio_repetido('facturas', 'id_factura', datos['folio']):
                error = f"Ya existe una factura con el folio {datos['folio']}."
            if error:
                flash(error, 'error')
                return redirect(url_for('facturas'))
            # Una factura nueva parte con todo su total pendiente de pago.
            datos.update(saldo_pendiente=datos['monto_total'], estado='vigente',
                         usuario_creacion=g.usuario.get('nombre_usuario') or 'Admin')
            response = supabase.table('facturas').insert(datos).execute()
            if response.data:
                flash(f"Factura {datos['folio']} creada exitosamente", 'success')
            else:
                flash('Error creando factura', 'error')
            return redirect(url_for('facturas'))

        id_factura = _entero_positivo(request.form.get('idFacturaActualizar')
                                      or request.form.get('idFacturaBorrar')
                                      or request.form.get('idFacturaAnular'))
        actual = supabase.table('facturas').select('id_factura, folio, estado') \
            .eq('id_factura', id_factura).execute().data if id_factura else []
        if not actual:
            flash('La factura no existe', 'error')
            return redirect(url_for('facturas'))
        actual = actual[0]

        if metodo == 'put':
            if actual.get('estado') == 'anulada':
                flash(f"La factura {actual['folio']} está anulada y no se puede modificar", 'error')
                return redirect(url_for('facturas'))
            datos, error = _leer_factura_formulario('Actualizar')
            if not error and _folio_repetido('facturas', 'id_factura', datos['folio'], id_factura):
                error = f"Ya existe otra factura con el folio {datos['folio']}."
            if not error:
                pagado, notas = _descuentos_factura(id_factura)
                if datos['monto_total'] < pagado + notas:
                    error = ('El nuevo total es menor que lo ya pagado y abonado con notas de crédito '
                             f'({formatear_moneda(pagado + notas)}).')
            if error:
                flash(error, 'error')
                return redirect(url_for('facturas'))
            supabase.table('facturas').update(datos).eq('id_factura', id_factura).execute()
            _recalcular_factura(id_factura)
            flash(f"Factura {datos['folio']} actualizada exitosamente", 'success')

        elif metodo == 'delete':
            tiene_pagos = supabase.table('pago_facturas').select('id_pago_factura') \
                .eq('id_factura', id_factura).limit(1).execute().data
            tiene_notas = supabase.table('notas_credito').select('id_nota_credito') \
                .eq('factura_referencia', id_factura).limit(1).execute().data
            tiene_despachos = supabase.table('despachos').select('id_despacho') \
                .eq('id_factura', id_factura).limit(1).execute().data
            if tiene_pagos or tiene_notas or tiene_despachos:
                asociados = ', '.join(nombre for nombre, hay in (
                    ('pagos', tiene_pagos), ('notas de crédito', tiene_notas), ('despachos', tiene_despachos)) if hay)
                flash(f"La factura {actual['folio']} tiene {asociados} asociados: no se puede eliminar, solo anular.",
                      'error')
                return redirect(url_for('facturas'))
            supabase.table('facturas').delete().eq('id_factura', id_factura).execute()
            flash(f"Factura {actual['folio']} borrada exitosamente", 'success')

        elif metodo == 'anular':
            if actual.get('estado') == 'anulada':
                flash(f"La factura {actual['folio']} ya está anulada", 'error')
            else:
                supabase.table('facturas').update({'estado': 'anulada'}).eq('id_factura', id_factura).execute()
                flash(f"Factura {actual['folio']} anulada", 'success')
        return redirect(url_for('facturas'))

    clientes = _obtener_clientes_map()
    pedidos = supabase.table('pedidos').select('id_pedido, numero_pedido, cliente_asociado, estado') \
        .order('id_pedido').execute().data or []
    numero_pedido = {p['id_pedido']: p.get('numero_pedido') or str(p['id_pedido']) for p in pedidos}

    filtros = {campo: request.args.get(campo, '').strip() for campo in ('cliente', 'desde', 'hasta', 'estado')}
    query = supabase.table('facturas').select('*')
    if filtros['desde']:
        query = query.gte('fecha_emision', filtros['desde'])
    if filtros['hasta']:
        query = query.lte('fecha_emision', filtros['hasta'])
    if filtros['estado']:
        query = query.eq('estado', filtros['estado'])
    datos = []
    for fila in query.order('folio', desc=True).execute().data or []:
        cliente = clientes.get(fila.get('cliente_asociado'), 'Sin cliente') if fila.get('cliente_asociado') else 'Sin cliente'
        if filtros['cliente'] and filtros['cliente'].lower() not in cliente.lower():
            continue
        datos.append({**fila, 'cliente': cliente, 'numero_pedido': numero_pedido.get(fila.get('pedido_asociado'), '')})

    folios = [f.get('folio') or 0 for f in supabase.table('facturas').select('folio').execute().data or []]
    return render_template('facturas.html', datos=datos, filtros=filtros,
                           pedidos=[p for p in pedidos if p.get('estado') != 'anulado'],
                           clientes=clientes, siguiente_folio=max(folios, default=0) + 1,
                           porcentaje_impuesto=obtener_porcentaje_impuesto())


@app.route('/crudDetallePedido.html', methods=['GET', 'POST'])
def crudDetallePedido():
    if request.method == 'POST':
        # Los formularios de esta plantilla todavía son una copia de los de bodegas.
        flash('La edición de detalles de pedido aún no está disponible desde esta pantalla.', 'error')
        return redirect(url_for('crudDetallePedido'))
    response = supabase.table("detalle_pedidos").select("*").order("id_detalle_pedido").execute()
    return render_template('crudDetallePedido.html', datos=response.data)


# Estados de pedido del glosario del Documento 0 (tt) en los que ya no se despacha.
ESTADOS_PEDIDO_NO_DESPACHABLES = ('despachado', 'pagado', 'anulado', 'finalizado')


@app.template_filter('fecha')
def formatear_fecha(valor):
    """Fecha en formato dd/mm/yyyy (Documento 0, formato oooo)."""
    if not valor:
        return ''
    try:
        return datetime.fromisoformat(str(valor)[:10]).strftime('%d/%m/%Y')
    except ValueError:
        return valor


def _entero_positivo(valor):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def _variantes_por_id(ids_variante):
    """Descripción, color y talla de cada variante, para mostrar las líneas."""
    if not ids_variante:
        return {}
    filas = supabase.table('producto_variantes').select(
        'id_variante, descripcion, colores(descripcion), tallas(talla, nombre)'
    ).in_('id_variante', list(ids_variante)).execute().data or []
    variantes = {}
    for fila in filas:
        color = fila.get('colores') or {}
        talla = fila.get('tallas') or {}
        variantes[fila['id_variante']] = {
            'producto': fila.get('descripcion'),
            'color': color.get('descripcion'),
            'talla': talla.get('nombre') or talla.get('talla'),
        }
    return variantes


@app.route('/despachos.html', methods=['GET', 'POST'])
def despachos():
    # RF-039 y RF-042 a RF-051. Crear y anular pasan por las funciones de la base
    # (supabase/despachos_variantes.sql), que validan pendientes y stock y mueven
    # el inventario. Un despacho no se borra: se anula y el stock vuelve a la bodega.
    if request.method == 'POST':
        metodo = request.form.get('_method')
        usuario = g.usuario.get('nombre_usuario') or 'Admin'
        try:
            if metodo == 'post':
                id_pedido = _entero_positivo(request.form.get('idPedido'))
                id_bodega = _entero_positivo(request.form.get('idBodega'))
                if not id_pedido or not id_bodega:
                    flash("Seleccione el pedido y la bodega de origen", "error")
                    return redirect(url_for('despachos', pedido=request.form.get('idPedido', '')))
                lineas = []
                for clave, valor in request.form.items():
                    if not clave.startswith('cantidad_') or not valor.strip():
                        continue
                    cantidad = _entero_positivo(valor)
                    if cantidad is None:
                        if valor.strip() != '0':
                            flash("Las cantidades deben ser números enteros positivos", "error")
                            return redirect(url_for('despachos', pedido=id_pedido))
                        continue
                    lineas.append({'id_detalle_pedido': int(clave.removeprefix('cantidad_')), 'cantidad': cantidad})
                if not lineas:
                    flash("Ingrese la cantidad a despachar de al menos una línea", "error")
                    return redirect(url_for('despachos', pedido=id_pedido))
                id_despacho = supabase.rpc('registrar_despacho', {
                    'p_id_pedido': id_pedido,
                    'p_id_bodega': id_bodega,
                    'p_lineas': lineas,
                    'p_id_factura': _entero_positivo(request.form.get('idFactura')),
                    'p_via_despacho': _texto_o_nulo(request.form.get('viaDespacho')),
                    'p_observacion': _texto_o_nulo(request.form.get('observacion')),
                    'p_usuario': usuario,
                }).execute().data
                flash("Despacho registrado exitosamente", "success")
                return redirect(url_for('despachos', ver=id_despacho))

            id_despacho = _entero_positivo(request.form.get('idDespacho'))
            filas = supabase.table('despachos').select('id_despacho, id_pedido, estado, numero_guia') \
                .eq('id_despacho', id_despacho).execute().data if id_despacho else []
            if not filas:
                flash("El despacho no existe", "error")
                return redirect(url_for('despachos'))
            despacho = filas[0]

            if metodo == 'put':
                # Solo se corrigen los datos informativos; las cantidades no se editan
                # (para cambiarlas se anula el despacho y se registra otro).
                if despacho['estado'] == 'anulado':
                    flash("Un despacho anulado no se puede modificar", "error")
                    return redirect(url_for('despachos'))
                id_factura = _entero_positivo(request.form.get('idFactura'))
                if id_factura and not supabase.table('facturas').select('id_factura') \
                        .eq('id_factura', id_factura).eq('id_pedido', despacho['id_pedido']) \
                        .neq('estado', 'anulada').execute().data:
                    flash("La factura no corresponde al pedido del despacho o está anulada", "error")
                    return redirect(url_for('despachos'))
                supabase.table('despachos').update({
                    'id_factura': id_factura,
                    'via_despacho': _texto_o_nulo(request.form.get('viaDespacho')),
                    'observacion': _texto_o_nulo(request.form.get('observacion')),
                }).eq('id_despacho', id_despacho).execute()
                flash(f"Despacho {despacho['numero_guia']} actualizado", "success")

            elif metodo == 'anular':
                motivo = (request.form.get('motivo') or '').strip()
                if not motivo:
                    flash("Indique el motivo de la anulación", "error")
                    return redirect(url_for('despachos'))
                supabase.rpc('anular_despacho', {
                    'p_id_despacho': id_despacho, 'p_motivo': motivo, 'p_usuario': usuario,
                }).execute()
                flash(f"Despacho {despacho['numero_guia']} anulado; el stock volvió a la bodega", "success")
        except APIError as error:
            flash(error.message or "No se pudo guardar el despacho", "error")
            if metodo == 'post':
                return redirect(url_for('despachos', pedido=request.form.get('idPedido', '')))
        return redirect(url_for('despachos'))

    bodegas = supabase.table('bodegas').select('id_bodega, descripcion').order('descripcion').execute().data or []
    facturas = supabase.table('facturas').select('id_factura, numero_factura, id_pedido') \
        .neq('estado', 'anulada').not_.is_('id_pedido', 'null').execute().data or []

    # Pedidos que todavía tienen unidades por despachar (para "Nuevo despacho").
    pendientes = supabase.table('v_pendientes_despacho').select(
        'id_pedido, numero_pedido, estado_pedido, nombre_cliente'
    ).gt('cantidad_pendiente', 0).execute().data or []
    pedidos_pendientes = {}
    for fila in pendientes:
        if fila.get('estado_pedido') not in ESTADOS_PEDIDO_NO_DESPACHABLES:
            pedidos_pendientes[fila['id_pedido']] = fila
    pedidos_pendientes = sorted(pedidos_pendientes.values(), key=lambda p: p['numero_pedido'] or '')

    # Formulario de nuevo despacho para el pedido elegido.
    nuevo = None
    id_pedido_nuevo = _entero_positivo(request.args.get('pedido'))
    if id_pedido_nuevo:
        lineas = supabase.table('v_pendientes_despacho').select(
            'id_pedido, numero_pedido, estado_pedido, id_cliente, nombre_cliente, id_detalle_pedido, id_variante, '
            'cantidad_pedida, cantidad_despachada, cantidad_pendiente'
        ).eq('id_pedido', id_pedido_nuevo).gt('cantidad_pendiente', 0) \
            .order('id_detalle_pedido').execute().data or []
        if not lineas:
            flash("Ese pedido no tiene unidades pendientes de despacho", "error")
        elif lineas[0].get('estado_pedido') in ESTADOS_PEDIDO_NO_DESPACHABLES:
            flash(f"El pedido está {lineas[0]['estado_pedido']} y no se puede despachar", "error")
        else:
            variantes = _variantes_por_id({l['id_variante'] for l in lineas})
            for linea in lineas:
                linea.update(variantes.get(linea['id_variante'], {}))
            # Stock por bodega y variante, para mostrarlo al elegir la bodega.
            stock = {}
            for fila in supabase.table('inventario').select('id_bodega, id_variante, cantidad') \
                    .in_('id_variante', list({l['id_variante'] for l in lineas})).execute().data or []:
                clave = f"{fila['id_bodega']}-{fila['id_variante']}"
                stock[clave] = stock.get(clave, 0) + (fila.get('cantidad') or 0)
            # La vía de despacho se propone desde la ficha del cliente (RF-001).
            cliente = supabase.table('clientes').select('via_despacho') \
                .eq('id_cliente', lineas[0]['id_cliente']).execute().data if lineas[0].get('id_cliente') else []
            nuevo = {
                'id_pedido': id_pedido_nuevo,
                'numero_pedido': lineas[0]['numero_pedido'],
                'cliente': lineas[0]['nombre_cliente'],
                'via_despacho': (cliente[0].get('via_despacho') if cliente else None) or '',
                'lineas': lineas,
                'stock': stock,
                'facturas': [f for f in facturas if f['id_pedido'] == id_pedido_nuevo],
            }

    # Listado con filtros.
    query = supabase.table('despachos').select(
        '*, pedidos(numero_pedido, clientes(nombre)), bodegas(descripcion), facturas(numero_factura), '
        'detalle_despachos(cantidad)'
    )
    filtros = {campo: request.args.get(campo, '').strip() for campo in ('guia', 'pedido_numero', 'estado', 'desde', 'hasta')}
    if filtros['guia']:
        query = query.ilike('numero_guia', f"%{filtros['guia']}%")
    if filtros['estado'] in ('emitido', 'anulado'):
        query = query.eq('estado', filtros['estado'])
    if filtros['desde']:
        query = query.gte('fecha', filtros['desde'])
    if filtros['hasta']:
        query = query.lte('fecha', filtros['hasta'])
    datos = []
    for fila in query.order('id_despacho', desc=True).execute().data or []:
        pedido = fila.get('pedidos') or {}
        if filtros['pedido_numero'] and filtros['pedido_numero'].lower() not in (pedido.get('numero_pedido') or '').lower():
            continue
        lineas = fila.get('detalle_despachos') or []
        datos.append({
            **fila,
            'numero_pedido': pedido.get('numero_pedido'),
            'cliente': (pedido.get('clientes') or {}).get('nombre'),
            'bodega': (fila.get('bodegas') or {}).get('descripcion'),
            'numero_factura': (fila.get('facturas') or {}).get('numero_factura'),
            'lineas': len(lineas),
            'unidades': sum(l.get('cantidad') or 0 for l in lineas),
        })

    # Detalle de un despacho.
    detalle = None
    id_ver = _entero_positivo(request.args.get('ver'))
    if id_ver:
        despacho = next((d for d in datos if d['id_despacho'] == id_ver), None)
        if despacho is None:
            filas = supabase.table('despachos').select(
                '*, pedidos(numero_pedido, clientes(nombre)), bodegas(descripcion), facturas(numero_factura)'
            ).eq('id_despacho', id_ver).execute().data
            if filas:
                pedido = filas[0].get('pedidos') or {}
                despacho = {**filas[0], 'numero_pedido': pedido.get('numero_pedido'),
                            'cliente': (pedido.get('clientes') or {}).get('nombre'),
                            'bodega': (filas[0].get('bodegas') or {}).get('descripcion'),
                            'numero_factura': (filas[0].get('facturas') or {}).get('numero_factura')}
        if despacho:
            lineas = supabase.table('detalle_despachos').select(
                'id_detalle_despacho, cantidad, precio_unitario, descuento_porcentaje, detalle_pedidos(id_variante)'
            ).eq('id_despacho', id_ver).order('id_detalle_despacho').execute().data or []
            variantes = _variantes_por_id({(l.get('detalle_pedidos') or {}).get('id_variante') for l in lineas} - {None})
            for linea in lineas:
                linea.update(variantes.get((linea.get('detalle_pedidos') or {}).get('id_variante'), {}))
                bruto = linea['cantidad'] * linea['precio_unitario']
                linea['subtotal'] = bruto - round(bruto * float(linea['descuento_porcentaje'] or 0) / 100)
            detalle = {'despacho': despacho, 'lineas': lineas,
                       'total': sum(l['subtotal'] for l in lineas)}
        else:
            flash("El despacho no existe", "error")

    return render_template('despachos.html', datos=datos, filtros=filtros, bodegas=bodegas,
                           facturas=facturas, pedidos_pendientes=pedidos_pendientes,
                           nuevo=nuevo, detalle=detalle)


def _leer_nota_formulario(sufijo, id_nota=None):
    """Valida el modal de notas de crédito. Devuelve (datos, error).

    La nota rebaja el saldo de su factura (glosario oo: "rectificar la factura y
    ajustar su saldo"), igual que un pago, así que no puede superar lo que queda
    por cobrar de la factura (sin contar lo que esta misma nota ya rebajaba)."""
    try:
        folio = int(request.form.get('folio' + sufijo, ''))
        if folio <= 0:
            raise ValueError
    except ValueError:
        return None, 'El folio debe ser un número entero mayor que cero.'
    if _folio_repetido('notas_credito', 'id_nota_credito', folio, id_nota):
        return None, f'Ya existe una nota de crédito con el folio {folio}.'
    id_factura = _entero_positivo(request.form.get('factura' + sufijo))
    factura = supabase.table('facturas').select('id_factura, folio, cliente_asociado, saldo_pendiente, estado') \
        .eq('id_factura', id_factura).execute().data if id_factura else []
    if not factura:
        return None, 'Seleccione la factura de referencia.'
    factura = factura[0]
    if factura.get('estado') == 'anulada':
        return None, f"La factura {factura['folio']} está anulada: no admite notas de crédito."
    fecha = (request.form.get('fecha' + sufijo) or '').strip()
    if not fecha:
        return None, 'Ingrese la fecha de emisión de la nota.'
    neto = _numero_positivo(request.form.get('montoNeto' + sufijo))
    if neto is None:
        return None, 'El monto neto debe ser un número mayor que cero.'
    motivo = (request.form.get('motivo' + sufijo) or '').strip()
    if not motivo:
        return None, 'Indique el motivo de la nota de crédito (devolución o ajuste).'
    impuesto = round(neto * obtener_porcentaje_impuesto() / 100, 2)
    total = round(neto + impuesto, 2)

    disponible = float(factura.get('saldo_pendiente') or 0)
    if id_nota:
        anterior = supabase.table('notas_credito').select('factura_referencia, monto_total, estado') \
            .eq('id_nota_credito', id_nota).execute().data or []
        if anterior and str(anterior[0].get('factura_referencia')) == str(id_factura) \
                and anterior[0].get('estado') == 'vigente':
            disponible += float(anterior[0].get('monto_total') or 0)
    if total > disponible + 0.005:
        return None, (f"La nota ({formatear_moneda(total)}) supera el saldo pendiente de la factura "
                      f"{factura['folio']} ({formatear_moneda(disponible)}).")
    return {
        'folio': folio, 'factura_referencia': id_factura, 'cliente_asociado': factura.get('cliente_asociado'),
        'fecha': fecha, 'monto_neto': neto, 'monto_impuesto': impuesto, 'monto_total': total, 'motivo': motivo,
    }, None


@app.route('/notasCredito.html', methods=['GET', 'POST', 'PUT', 'DELETE'])
def notasCredito():
    # RF-035/036. Esquema de supabase/notas_credito.sql.
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == 'post':
            datos, error = _leer_nota_formulario('Crear')
            if error:
                flash(error, 'error')
                return redirect(url_for('notasCredito'))
            datos.update(estado='vigente', usuario_creacion=g.usuario.get('nombre_usuario') or 'Admin')
            if supabase.table('notas_credito').insert(datos).execute().data:
                _recalcular_factura(datos['factura_referencia'])
                flash(f"Nota de crédito {datos['folio']} creada exitosamente", 'success')
            else:
                flash('Error creando nota de crédito', 'error')
            return redirect(url_for('notasCredito'))

        id_nota = _entero_positivo(request.form.get('idNotaActualizar') or request.form.get('idNotaBorrar')
                                   or request.form.get('idNotaAnular'))
        actual = supabase.table('notas_credito').select('id_nota_credito, folio, factura_referencia, estado') \
            .eq('id_nota_credito', id_nota).execute().data if id_nota else []
        if not actual:
            flash('La nota de crédito no existe', 'error')
            return redirect(url_for('notasCredito'))
        actual = actual[0]

        if metodo == 'put':
            if actual.get('estado') != 'vigente':
                flash(f"La nota de crédito {actual['folio']} está {actual.get('estado')} y no se puede modificar", 'error')
                return redirect(url_for('notasCredito'))
            datos, error = _leer_nota_formulario('Actualizar', id_nota)
            if error:
                flash(error, 'error')
                return redirect(url_for('notasCredito'))
            supabase.table('notas_credito').update(datos).eq('id_nota_credito', id_nota).execute()
            # Si cambió la factura, se recalculan la anterior y la nueva.
            for id_factura in {actual.get('factura_referencia'), datos['factura_referencia']}:
                _recalcular_factura(id_factura)
            flash(f"Nota de crédito {datos['folio']} actualizada exitosamente", 'success')
        elif metodo == 'anular':
            if actual.get('estado') == 'anulada':
                flash(f"La nota de crédito {actual['folio']} ya está anulada", 'error')
            else:
                supabase.table('notas_credito').update({'estado': 'anulada'}).eq('id_nota_credito', id_nota).execute()
                _recalcular_factura(actual.get('factura_referencia'))
                flash(f"Nota de crédito {actual['folio']} anulada: su monto vuelve al saldo de la factura", 'success')
        elif metodo == 'delete':
            supabase.table('notas_credito').delete().eq('id_nota_credito', id_nota).execute()
            _recalcular_factura(actual.get('factura_referencia'))
            flash(f"Nota de crédito {actual['folio']} borrada exitosamente", 'success')
        return redirect(url_for('notasCredito'))

    allowed_sort = {
        'folio': lambda item: item.get('folio') or '',
        'fecha': lambda item: item.get('fecha') or '0000-00-00',
        'cliente': lambda item: (item.get('cliente') or '').lower(),
        'factura_referencia': lambda item: item.get('factura_referencia_folio') or '',
        'monto': lambda item: float(item.get('monto_total', 0) or 0),
        'motivo': lambda item: (item.get('motivo') or '').lower(),
        'estado': lambda item: (item.get('estado') or '').lower(),
    }
    sort_field = request.args.get('orden_por', 'fecha')
    sort_dir = request.args.get('orden_dir', 'desc')
    if sort_field not in allowed_sort:
        sort_field = 'fecha'
    if sort_dir not in {'asc', 'desc'}:
        sort_dir = 'desc'

    try:
        rows = supabase.table('notas_credito').select('*').execute().data or []
        facturas_rows = supabase.table('facturas').select(
            'id_factura, folio, cliente_asociado, saldo_pendiente, estado').execute().data or []
    except Exception:
        flash("No se pudo cargar el listado de notas de crédito. Intenta nuevamente.", "error")
        rows, facturas_rows = [], []
    clientes_map = _obtener_clientes_map()
    folio_factura = {f['id_factura']: f.get('folio') for f in facturas_rows}

    normalized = []
    for row in rows:
        cliente_id = row.get('cliente_asociado')
        normalized.append({
            'id_nota_credito': row.get('id_nota_credito'),
            'folio': row.get('folio'),
            'factura_referencia': row.get('factura_referencia'),
            'factura_referencia_folio': folio_factura.get(row.get('factura_referencia')),
            'cliente_asociado': cliente_id,
            'cliente': clientes_map.get(cliente_id, 'Sin cliente') if cliente_id is not None else 'Sin cliente',
            'fecha': row.get('fecha'),
            'monto_neto': row.get('monto_neto', 0),
            'monto_impuesto': row.get('monto_impuesto', 0),
            'monto_total': row.get('monto_total', 0),
            'motivo': row.get('motivo'),
            'estado': row.get('estado'),
        })

    folio_filter = request.args.get('folio', '').strip()
    cliente_filter = request.args.get('cliente', '').strip()
    factura_filter = request.args.get('factura_referencia', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()

    if folio_filter:
        normalized = [item for item in normalized if str(item.get('folio', '')) == folio_filter]
    if cliente_filter:
        normalized = [item for item in normalized if cliente_filter.lower() in (item.get('cliente') or '').lower()]
    if factura_filter:
        normalized = [
            item for item in normalized
            if str(item.get('factura_referencia', '')) == factura_filter
            or str(item.get('factura_referencia_folio', '')) == factura_filter
        ]
    if fecha_desde:
        normalized = [item for item in normalized if (item.get('fecha') or '') >= fecha_desde]
    if fecha_hasta:
        normalized = [item for item in normalized if (item.get('fecha') or '') <= fecha_hasta]

    reverse = sort_dir == 'desc'
    normalized = sorted(normalized, key=allowed_sort.get(sort_field, allowed_sort['fecha']), reverse=reverse)

    folios = [n.get('folio') or 0 for n in rows]
    facturas_disponibles = [
        {**f, 'cliente': clientes_map.get(f.get('cliente_asociado'), 'Sin cliente')}
        for f in sorted(facturas_rows, key=lambda f: f.get('folio') or 0)
        if f.get('estado') != 'anulada'
    ]
    return render_template('notasCredito.html', datos=normalized, facturas=facturas_disponibles,
                           siguiente_folio=max(folios, default=0) + 1,
                           porcentaje_impuesto=obtener_porcentaje_impuesto())


def _obtener_clientes_map():
    try:
        response = supabase.table('clientes').select('id_cliente, nombre').execute()
        rows = response.data or []
    except Exception:
        rows = []
    return {int(row.get('id_cliente')): (row.get('nombre') or 'Sin cliente') for row in rows if row.get('id_cliente') is not None}


def _obtener_facturas_pendientes(cliente_id):
    try:
        response = supabase.table('facturas').select(
            'id_factura, folio, cliente_asociado, fecha_emision, monto_total, saldo_pendiente, estado'
        ).eq('cliente_asociado', cliente_id).execute()
        rows = response.data or []
    except Exception:
        rows = []
    pendientes = []
    for row in rows:
        saldo = float(row.get('saldo_pendiente') or 0)
        if saldo > 0:
            pendientes.append({
                'id_factura': row.get('id_factura'),
                'folio': row.get('folio'),
                'fecha_emision': row.get('fecha_emision'),
                'monto_total': float(row.get('monto_total') or 0),
                'saldo_pendiente': saldo,
                'estado': row.get('estado') or 'vigente',
            })
    pendientes.sort(key=lambda item: (item.get('fecha_emision') or '9999-12-31', item.get('folio') or 0))
    return pendientes


def _estado_para_saldo(monto_total, saldo_pendiente):
    monto_total = float(monto_total or 0)
    saldo_pendiente = float(saldo_pendiente or 0)
    if saldo_pendiente <= 0:
        return 'pagada'
    if saldo_pendiente >= monto_total:
        return 'vigente'
    return 'parcialmente_pagada'


def _pago_facturas_disponible():
    try:
        supabase.table('pago_facturas').select('id_pago_factura').limit(1).execute()
        return True
    except Exception:
        return False


def _obtener_detalle_pago(pago_id):
    if not _pago_facturas_disponible():
        return []
    try:
        response = supabase.table('pago_facturas').select(
            '*, facturas(id_factura, folio, saldo_pendiente)'
        ).eq('id_pago', pago_id).execute()
        return response.data or []
    except Exception:
        return []


@app.route('/pagos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def pagos():
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == 'post':
            if not _pago_facturas_disponible():
                flash('La tabla de detalle de pagos aún no está creada en la base de datos. Activa el esquema de pagos para registrar movimientos.', 'error')
                return redirect(url_for('pagos'))
            cliente_id = request.form.get('cliente')
            monto = request.form.get('monto', '').strip()
            fecha_pago = request.form.get('fecha_pago', '').strip()
            medio_pago = request.form.get('medio_pago', '').strip()
            referencia = request.form.get('referencia', '').strip()
            facturas_seleccionadas = request.form.getlist('facturas')

            if not cliente_id or not monto or not fecha_pago or not medio_pago:
                flash('Faltan campos obligatorios para registrar el pago.', 'error')
                return redirect(url_for('pagos'))

            try:
                monto_valor = float(monto)
            except ValueError:
                flash('El monto del pago debe ser numérico.', 'error')
                return redirect(url_for('pagos'))

            if monto_valor <= 0:
                flash('El monto del pago debe ser mayor a cero.', 'error')
                return redirect(url_for('pagos'))

            if not facturas_seleccionadas:
                flash('Debes seleccionar al menos una factura pendiente para aplicar el pago.', 'error')
                return redirect(url_for('pagos'))

            facturas = []
            for factura_id in facturas_seleccionadas:
                factura_row = supabase.table('facturas').select(
                    'id_factura, folio, saldo_pendiente, monto_total'
                ).eq('id_factura', factura_id).execute()
                if not factura_row.data:
                    continue
                factura_data = factura_row.data[0]
                saldo = float(factura_data.get('saldo_pendiente') or 0)
                if saldo <= 0:
                    continue
                facturas.append(factura_data)

            if not facturas:
                flash('Las facturas seleccionadas no tienen saldo pendiente.', 'error')
                return redirect(url_for('pagos'))

            total_saldos = sum(float(factura.get('saldo_pendiente') or 0) for factura in facturas)
            asignaciones = []
            monto_restante = monto_valor
            for factura in facturas:
                factura_id = factura.get('id_factura')
                saldo = float(factura.get('saldo_pendiente') or 0)
                if saldo <= 0:
                    continue
                asignado = min(saldo, monto_restante) if monto_restante > 0 else 0
                asignaciones.append((factura_id, asignado))
                monto_restante -= asignado

            if monto_restante > 0:
                flash(f'Se registró el pago con un saldo a favor de $ {monto_restante:,.2f} para el cliente.', 'warning')

            try:
                pago_response = supabase.table('pagos').insert({
                    'cliente_asociado': int(cliente_id),
                    'fecha_pago': fecha_pago,
                    'monto': monto_valor,
                    'medio_pago': medio_pago,
                    'referencia': referencia or None,
                    'estado': 'vigente',
                    'usuario_creacion': 'Admin',
                }).execute()
            except Exception:
                flash('No se pudo registrar el pago.', 'error')
                return redirect(url_for('pagos'))

            if not pago_response.data:
                flash('No se pudo registrar el pago.', 'error')
                return redirect(url_for('pagos'))

            pago_id = pago_response.data[0].get('id_pago')
            for factura_id, asignado in asignaciones:
                if asignado <= 0:
                    continue
                try:
                    factura_row = supabase.table('facturas').select(
                        'id_factura, saldo_pendiente, monto_total'
                    ).eq('id_factura', factura_id).execute().data or []
                    if not factura_row:
                        continue
                    factura_data = factura_row[0]
                    saldo_actual = float(factura_data.get('saldo_pendiente') or 0)
                    nuevo_saldo = max(saldo_actual - asignado, 0)
                    supabase.table('pago_facturas').insert({
                        'id_pago': pago_id,
                        'id_factura': factura_id,
                        'monto_aplicado': asignado,
                    }).execute()
                    supabase.table('facturas').update({
                        'saldo_pendiente': nuevo_saldo,
                        'estado': _estado_para_saldo(factura_data.get('monto_total'), nuevo_saldo),
                    }).eq('id_factura', factura_id).execute()
                except Exception:
                    continue

            flash('Pago registrado exitosamente.', 'success')
            return redirect(url_for('pagos'))

        if metodo == 'put':
            if not _pago_facturas_disponible():
                flash('La tabla de detalle de pagos aún no está creada en la base de datos. Activa el esquema de pagos para actualizar movimientos.', 'error')
                return redirect(url_for('pagos'))
            pago_id = request.form.get('id_pago_actualizar')
            cliente_id = request.form.get('cliente_actualizar')
            monto = request.form.get('monto_actualizar', '').strip()
            fecha_pago = request.form.get('fecha_pago_actualizar', '').strip()
            medio_pago = request.form.get('medio_pago_actualizar', '').strip()
            referencia = request.form.get('referencia_actualizar', '').strip()
            facturas_seleccionadas = request.form.getlist('facturas_actualizar')

            if not pago_id or not cliente_id or not monto or not fecha_pago or not medio_pago:
                flash('Faltan campos obligatorios para actualizar el pago.', 'error')
                return redirect(url_for('pagos'))

            try:
                pago_actual = supabase.table('pagos').select('*').eq('id_pago', pago_id).execute().data or []
                if not pago_actual:
                    flash('No existe el pago que intentas actualizar.', 'error')
                    return redirect(url_for('pagos'))
                pago_data = pago_actual[0]
                if (pago_data.get('estado') or '').lower() == 'anulada':
                    flash('No se puede modificar un pago anulado.', 'error')
                    return redirect(url_for('pagos'))
                monto_valor = float(monto)
            except ValueError:
                flash('El monto del pago debe ser numérico.', 'error')
                return redirect(url_for('pagos'))

            if monto_valor <= 0:
                flash('El monto del pago debe ser mayor a cero.', 'error')
                return redirect(url_for('pagos'))

            asignaciones = []
            if facturas_seleccionadas:
                for factura_id in facturas_seleccionadas:
                    factura_row = supabase.table('facturas').select('id_factura, folio, saldo_pendiente, monto_total').eq('id_factura', factura_id).execute().data or []
                    if not factura_row:
                        continue
                    factura_data = factura_row[0]
                    saldo = float(factura_data.get('saldo_pendiente') or 0)
                    if saldo <= 0:
                        continue
                    asignaciones.append(factura_id)
                if not asignaciones:
                    flash('Las facturas seleccionadas no tienen saldo pendiente.', 'error')
                    return redirect(url_for('pagos'))

            pagos_facturas_actuales = supabase.table('pago_facturas').select('*').eq('id_pago', pago_id).execute().data or []
            for detalle in pagos_facturas_actuales:
                factura_id = detalle.get('id_factura')
                monto_aplicado = float(detalle.get('monto_aplicado') or 0)
                factura_row = supabase.table('facturas').select('id_factura, saldo_pendiente, monto_total').eq('id_factura', factura_id).execute().data or []
                if not factura_row:
                    continue
                factura_data = factura_row[0]
                nuevo_saldo = float(factura_data.get('saldo_pendiente') or 0) + monto_aplicado
                supabase.table('facturas').update({
                    'saldo_pendiente': nuevo_saldo,
                    'estado': _estado_para_saldo(factura_data.get('monto_total'), nuevo_saldo),
                }).eq('id_factura', factura_id).execute()

            supabase.table('pago_facturas').delete().eq('id_pago', pago_id).execute()

            monto_restante = monto_valor
            nueva_asignacion = []
            if facturas_seleccionadas:
                for factura_id in facturas_seleccionadas:
                    factura_row = supabase.table('facturas').select('id_factura, folio, saldo_pendiente, monto_total').eq('id_factura', factura_id).execute().data or []
                    if not factura_row:
                        continue
                    factura_data = factura_row[0]
                    saldo = float(factura_data.get('saldo_pendiente') or 0)
                    if saldo <= 0:
                        continue
                    asignado = min(saldo, monto_restante) if monto_restante > 0 else 0
                    nueva_asignacion.append((factura_id, asignado))
                    monto_restante -= asignado

            if monto_restante > 0:
                flash(f'Se actualizó el pago con un saldo a favor de $ {monto_restante:,.2f} para el cliente.', 'warning')

            try:
                supabase.table('pagos').update({
                    'cliente_asociado': int(cliente_id),
                    'fecha_pago': fecha_pago,
                    'monto': monto_valor,
                    'medio_pago': medio_pago,
                    'referencia': referencia or None,
                }).eq('id_pago', pago_id).execute()
            except Exception:
                flash('No se pudo actualizar el pago.', 'error')
                return redirect(url_for('pagos'))

            for factura_id, asignado in nueva_asignacion:
                if asignado <= 0:
                    continue
                factura_data = supabase.table('facturas').select('id_factura, saldo_pendiente, monto_total').eq('id_factura', factura_id).execute().data or []
                if not factura_data:
                    continue
                factura_row = factura_data[0]
                saldo_actual = float(factura_row.get('saldo_pendiente') or 0)
                nuevo_saldo = max(saldo_actual - asignado, 0)
                supabase.table('pago_facturas').insert({
                    'id_pago': pago_id,
                    'id_factura': factura_id,
                    'monto_aplicado': asignado,
                }).execute()
                supabase.table('facturas').update({
                    'saldo_pendiente': nuevo_saldo,
                    'estado': _estado_para_saldo(factura_row.get('monto_total'), nuevo_saldo),
                }).eq('id_factura', factura_id).execute()

            flash('Pago actualizado exitosamente.', 'success')
            return redirect(url_for('pagos'))

        if metodo == 'delete':
            if not _pago_facturas_disponible():
                flash('La tabla de detalle de pagos aún no está creada en la base de datos. Activa el esquema de pagos para anular movimientos.', 'error')
                return redirect(url_for('pagos'))
            pago_id = request.form.get('id_pago_anular')
            motivo = request.form.get('motivo_anulacion', '').strip()
            if not pago_id:
                flash('Debes seleccionar un pago para anular.', 'error')
                return redirect(url_for('pagos'))
            if not motivo:
                flash('Debes indicar el motivo de anulación.', 'error')
                return redirect(url_for('pagos'))

            pago_response = supabase.table('pagos').select('*').eq('id_pago', pago_id).execute().data or []
            if not pago_response:
                flash('No existe el pago que intentas anular.', 'error')
                return redirect(url_for('pagos'))
            pago_data = pago_response[0]
            if (pago_data.get('estado') or '').lower() == 'anulada':
                flash('El pago ya está anulado.', 'error')
                return redirect(url_for('pagos'))

            detalles = supabase.table('pago_facturas').select('*').eq('id_pago', pago_id).execute().data or []
            for detalle in detalles:
                factura_id = detalle.get('id_factura')
                monto_aplicado = float(detalle.get('monto_aplicado') or 0)
                factura_rows = supabase.table('facturas').select('id_factura, saldo_pendiente, monto_total').eq('id_factura', factura_id).execute().data or []
                if not factura_rows:
                    continue
                factura_data = factura_rows[0]
                nuevo_saldo = float(factura_data.get('saldo_pendiente') or 0) + monto_aplicado
                supabase.table('facturas').update({
                    'saldo_pendiente': nuevo_saldo,
                    'estado': _estado_para_saldo(factura_data.get('monto_total'), nuevo_saldo),
                }).eq('id_factura', factura_id).execute()

            supabase.table('pagos').update({
                'estado': 'anulada',
                'motivo_anulacion': motivo,
            }).eq('id_pago', pago_id).execute()
            supabase.table('pago_facturas').delete().eq('id_pago', pago_id).execute()
            flash('Pago anulado correctamente.', 'success')
            return redirect(url_for('pagos'))

    cliente_filter = (request.args.get('cliente') or '').strip()
    fecha_desde = (request.args.get('fecha_desde') or '').strip()
    fecha_hasta = (request.args.get('fecha_hasta') or '').strip()
    referencia_filter = (request.args.get('referencia') or '').strip()

    try:
        response = supabase.table('pagos').select('*').execute()
        pagos_rows = response.data or []
    except Exception:
        flash('No se pudo cargar el listado de pagos.', 'error')
        pagos_rows = []

    clientes_map = _obtener_clientes_map()
    datos = []
    for pago in pagos_rows:
        pago_id = pago.get('id_pago')
        cliente_id = pago.get('cliente_asociado')
        cliente_nombre = clientes_map.get(int(cliente_id), 'Sin cliente') if cliente_id is not None else 'Sin cliente'
        fecha_pago = pago.get('fecha_pago') or ''
        if cliente_filter and cliente_filter.lower() not in cliente_nombre.lower():
            continue
        if fecha_desde and fecha_pago < fecha_desde:
            continue
        if fecha_hasta and fecha_pago > fecha_hasta:
            continue
        if referencia_filter and (pago.get('referencia') or '').lower() not in referencia_filter.lower():
            continue

        detalle_rows = _obtener_detalle_pago(pago_id)
        facturas = []
        for detalle in detalle_rows:
            factura = detalle.get('facturas') or {}
            if isinstance(factura, dict):
                facturas.append({
                    'id_factura': factura.get('id_factura'),
                    'folio': factura.get('folio'),
                    'monto_aplicado': detalle.get('monto_aplicado'),
                    'saldo_pendiente': factura.get('saldo_pendiente'),
                })

        datos.append({
            'id_pago': pago_id,
            'folio': pago.get('folio'),
            'cliente': cliente_nombre,
            'cliente_id': cliente_id,
            'fecha_pago': fecha_pago,
            'monto': float(pago.get('monto') or 0),
            'medio_pago': pago.get('medio_pago'),
            'referencia': pago.get('referencia'),
            'estado': pago.get('estado') or 'vigente',
            'motivo_anulacion': pago.get('motivo_anulacion'),
            'detalle_facturas': facturas,
        })

    if request.args:
        if not datos:
            flash('No se encontraron pagos para los filtros aplicados.', 'warning')

    clientes = supabase.table('clientes').select('id_cliente, nombre').execute().data or []
    facturas = []
    if request.args.get('cliente'):
        cliente_id = next((item.get('id_cliente') for item in clientes if str(item.get('id_cliente')) == str(request.args.get('cliente'))), None)
        if cliente_id is not None:
            facturas = _obtener_facturas_pendientes(cliente_id)

    return render_template(
        'pagos.html',
        datos=datos,
        clientes=clientes,
        facturas=facturas,
        cliente_filter=cliente_filter,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        referencia_filter=referencia_filter,
    )


def obtener_informe_cobranza(request_args):
    cliente_filter = (request_args.get('cliente') or '').strip()
    fecha_desde = (request_args.get('fecha_desde') or '').strip()
    fecha_hasta = (request_args.get('fecha_hasta') or '').strip()
    dias_min_raw = (request_args.get('dias_morosidad_min') or '').strip()

    try:
        dias_min = int(dias_min_raw) if dias_min_raw else None
    except ValueError:
        dias_min = None

    try:
        facturas_response = supabase.table('facturas').select('*').gt('saldo', 0).execute()
        facturas = facturas_response.data or []
    except Exception:
        facturas = []

    pagos_response = supabase.table('pagos').select('id_factura, monto').execute()
    pagos = pagos_response.data or []
    pagos_por_factura = {}
    for pago in pagos:
        factura_id = pago.get('id_factura')
        if factura_id is None:
            continue
        monto = float(pago.get('monto') or 0)
        pagos_por_factura[factura_id] = pagos_por_factura.get(factura_id, 0.0) + monto

    rows = []
    for factura in facturas:
        cliente_nombre = (factura.get('razon_social') or '').strip()
        if cliente_filter and cliente_filter.lower() not in cliente_nombre.lower():
            continue

        fecha_factura = (factura.get('fecha') or '').strip()
        if fecha_desde and fecha_factura < fecha_desde:
            continue
        if fecha_hasta and fecha_factura > fecha_hasta:
            continue

        dias_morosidad = 0
        if fecha_factura:
            try:
                dias_morosidad = (datetime.utcnow().date() - datetime.strptime(fecha_factura, '%Y-%m-%d').date()).days
            except ValueError:
                dias_morosidad = 0

        if dias_min is not None and dias_morosidad < dias_min:
            continue

        factura_id = factura.get('id_factura')
        pagos_aplicados = pagos_por_factura.get(factura_id, 0.0)
        rows.append({
            'id_factura': factura_id,
            'cliente': cliente_nombre or 'Sin cliente',
            'folio': factura.get('numero_factura'),
            'fecha': fecha_factura,
            'monto': float(factura.get('total') or 0),
            'pagos_aplicados': pagos_aplicados,
            'saldo': float(factura.get('saldo') or 0),
            'dias_morosidad': dias_morosidad,
        })

    return sorted(rows, key=lambda item: (item.get('cliente') or '').lower())

@app.route('/informeProductosDespachados.html', methods=['GET', 'POST'])
def informeProductosDespachados():
    productos_response = supabase.table('producto_variantes').select('id_variante, descripcion').execute()
    if request.method == 'POST':
        metodo = (request.form.get('_method') or 'get').strip()
        fechaDesde = (request.form.get('desdeFecha') or '').strip()
        fechaHasta = (request.form.get('hastaFecha') or '').strip()

        query = supabase.table('despachos').select(
            'id_despacho, numero_guia, fecha, id_pedido, id_factura, id_bodega, estado, observacion, '
            'pedidos!inner(id_pedido, cliente_asociado, vendedor_asociado), '
            'facturas!left(id_factura, numero_factura, razon_social)'
        ).eq('estado', 'emitido')  # Solo despachos vigentes: los anulados no cuentan como despachados (nueva-interfaz)

        if fechaDesde:
            query = query.gte('fecha', fechaDesde)
        if fechaHasta:
            query = query.lte('fecha', fechaHasta)

        if metodo == 'buscarClientes':
            cliente_abuscar = (request.form.get('ClienteBuscarn') or '').strip()
            if cliente_abuscar:
                pedido_ids = [
                    row.get('id_pedido') for row in (
                        supabase.table('pedidos').select('id_pedido').eq('cliente_asociado', cliente_abuscar).execute().data or []
                    ) if row.get('id_pedido') is not None
                ]
                if pedido_ids:
                    query = query.in_('id_pedido', pedido_ids)
                else:
                    return render_template(
                        'informeProductosDespachados.html',
                        datos=[],
                        detallePedidos=[],
                        productos=productos_response.data or [],
                    )

        if metodo in ('buscarFactura', 'buscarFacturas'):  # el formulario envía 'buscarFacturas'
            factura_abuscar = (request.form.get('FacturaBuscarn') or '').strip()
            if factura_abuscar:
                query = query.eq('id_factura', factura_abuscar)

        response_despachos = query.execute()
        despachos = response_despachos.data or []
        pedido_ids = [despacho.get('id_pedido') for despacho in despachos if despacho.get('id_pedido') is not None]

        detalle_query = supabase.table('detalle_pedidos').select(
            'id_detalle_pedido, id_pedido, id_variante, cantidad, precio_unitario, subtotal, '
            'producto_variantes!inner(id_variante, descripcion)'
        )
        if pedido_ids:
            detalle_query = detalle_query.in_('id_pedido', pedido_ids)

        producto_abuscar = (request.form.get('ProductoBuscarn') or '').strip()
        producto_abuscar_int = None
        if metodo in ('buscarProducto', 'buscarProductos') and producto_abuscar:  # el formulario envía 'buscarProductos'
            try:
                producto_abuscar_int = int(producto_abuscar)
            except ValueError:
                producto_abuscar_int = None
            if producto_abuscar_int is not None:
                detalle_query = detalle_query.eq('id_variante', producto_abuscar_int)

        if pedido_ids or (metodo in ('buscarProducto', 'buscarProductos') and producto_abuscar_int is not None):
            response_detalle = detalle_query.execute()
            detalle_rows = response_detalle.data if hasattr(response_detalle, 'data') else response_detalle.get('data', [])
        else:
            detalle_rows = []

        return render_template(
            'informeProductosDespachados.html',
            datos=response_despachos.data or [],
            detallePedidos=detalle_rows,
            productos=productos_response.data or [],
        )

    return render_template('informeProductosDespachados.html', productos=productos_response.data or [])

@app.route('/informeProductosEnProceso.html', methods=['GET', 'POST'])
def informeProductosEnProceso():
    if request.method == 'POST' or 'GET':
        #Buscar los productos presentes en corte pero no ingresados a bodega
        #TODO: cambiar referencias a producto variantes una vez los consolidemos
        #y luego poner los detalles de producto variantes, como talla y color
        responseProductos = (
            supabase.table('productos')
            .select('id_producto, descripcion')
            .execute()
        )
        response = (
                    supabase.table('cortes')
                    .select('id_corte, producto_asociado, cantidad')
                    .eq('estado', 'pendiente')
                    .execute()
                )
        return render_template('informeProductosEnProceso.html', datos = response.data, productos = responseProductos.data)
    else:
        return render_template('informeProductosEnProceso.html')

@app.route('/informeProductosPendientesDespacho.html', methods=['GET', 'POST'])
def informeProductosPendientesDespacho():
    #Buscar los productos que estén en bodega y falta despachar
    responseClientes = (
                    supabase.table('clientes')
                    .select("id_cliente, nombre")
                    .execute()
                    )
    responseIDPedidos = (
                    supabase.table('pedidos')
                    .select("id_pedido")
                    .execute()
    )
    responseVendedores = (
                    supabase.table('vendedores')
                    .select("id_vendedor, nombre")
                    .execute()
    )
    if request.method == 'POST':
        metodo = request.form['_method']
        if metodo == 'get':
            responsePedidos = (
                supabase.table('pedidos')
                .select("id_pedido, detalle_pedidos!inner(id_variante)")
                .eq('estado', 'pendiente')
                .execute()
            )
        if metodo == 'buscarPedidos':
            pedidoABuscar = request.form['PedidoBuscarn']
            responsePedidos = (
                            supabase.table('pedidos')
                            .select("id_pedido, detalle_pedidos!inner(id_variante)")
                            .eq('estado', 'pendiente')
                            .eq('id_pedido', pedidoABuscar)
                            .execute()
                        )
        if metodo == 'buscarClientes':
            clienteABuscar = request.form['ClienteBuscarn']
            responsePedidos = (
                            supabase.table('pedidos')
                            .select("id_pedido, detalle_pedidos!inner(id_variante)")
                            .eq('estado', 'pendiente')
                            .eq('cliente_asociado', clienteABuscar)
                            .execute()
                        )
        if metodo == 'buscarVendedores':
            vendedorABuscar = request.form['VendedorBuscarn']
            responsePedidos = (
                            supabase.table('pedidos')
                            .select("id_pedido, detalle_pedidos!inner(id_variante)")
                            .eq('estado', 'pendiente')
                            .eq('vendedor_asociado', vendedorABuscar)
                            .execute()
                        )
        rp = responsePedidos.data
        productosPendientes = []
        for x in range(len(rp)):
                    for y in range(len(rp[x]['detalle_pedidos'])):
                        productosPendientes.append(rp[x]['detalle_pedidos'][y]['id_variante'])
        print(productosPendientes)
        responseInventario = (
            supabase.table('inventario')
            .select('*')
            .in_('id_variante', productosPendientes)
            .execute()
        )
        #TODO: Cambiar inventario una vez se consolide producto y producto_variante
        responseProductos = (
            supabase.table('producto_variantes')
            .select('*')
            .in_('id_variante', productosPendientes)
            .execute()
        )
        return render_template('informeProductosPendientesDespacho.html', datosPedidos = responsePedidos.data,
                                datosInventario = responseInventario.data, datosProductos = responseProductos.data,
                                clientes = responseClientes.data, vendedores = responseVendedores.data, pedidos = responseIDPedidos.data)   
    else:
        return render_template('informeProductosPendientesDespacho.html',
                                clientes = responseClientes.data, vendedores = responseVendedores.data, pedidos = responseIDPedidos.data)  

@app.route('/informeProductosTerminados.html', methods=['GET', 'POST'])
def informeProductosTerminados():
    if request.method == 'POST':
        #TODO: cambiar referencias de productos a producto variante una vez arreglemos eso
        #print("hola")
        fechaDesde = request.form['desdeFecha']
        fechaHasta = request.form['hastaFecha']
        desdeST = datetime.strptime(fechaDesde, "%Y-%m-%d")
        #print(desdeST)
        desdeTZ = desdeST.replace(tzinfo=timezone.utc)
        #print(desdeTZ)
        hastaST = datetime.strptime(fechaHasta, "%Y-%m-%d")
        hastaTZ = hastaST.replace(tzinfo=timezone.utc)
        response = (
            supabase.table('cortes').select('producto_asociado, cantidad, productos(descripcion, color(descripcion), talla(talla))')
            .gte('fecha_ingreso', desdeTZ)
            .lte('fecha_ingreso', hastaTZ)
            .execute()
        )

        return render_template('informeProductosTerminados.html', datos = response.data)
    else:
        return render_template('informeProductosTerminados.html')

@app.route('/analisisDespachoClienteProducto.html', methods=['GET', 'POST'])
def analisisDespachoClienteProducto():
    responseProductos = supabase.table('producto_variantes').select('id_variante, descripcion').execute()
    responseClientes = supabase.table('clientes').select('id_cliente, nombre').execute()
    responseVendedores = supabase.table('vendedores').select('id_vendedor, nombre').execute()
    if request.method == 'POST':
        #Despachos a cliente por producto.
        #TODO: Clarificar con el usuario si cada producto cuenta como su propio despacho,
        #o si varios caben en uno.
        cliente = request.form['IDCliente']
        producto = request.form['IDProducto']
        response = (
            supabase.table('despachos').select('*, pedidos!inner(id_pedido), facturas!left(id_factura, numero_factura)')
            .eq('pedidos.cliente_asociado', cliente)
            .execute()
        )
        responsePedidos = (
            supabase.table("pedidos").select("*, detalle_pedidos!inner(id_variante, cantidad, producto_variantes!inner(id_variante, descripcion))")
            .eq("detalle_pedidos.id_variante", producto)
            .execute()
        )
        return render_template('analisisDespachoClienteProducto.html', clientes=responseClientes.data, vendedores=responseVendedores.data, productos=responseProductos.data, datos=response.data, datosPedidos=responsePedidos.data)
    else:
        return render_template('analisisDespachoClienteProducto.html', clientes=responseClientes.data, vendedores=responseVendedores.data, productos=responseProductos.data)

@app.route('/analisisDespachoSegunFacturaCliente.html', methods=['GET', 'POST'])
def analisisDespachoSegunFacturaCliente():
    responseClientes = supabase.table('clientes').select('id_cliente, nombre').execute()
    responseFacturas = supabase.table('facturas').select('id_factura, numero_factura, razon_social, id_cliente').execute()
    responseVendedores = supabase.table('vendedores').select('id_vendedor, nombre').execute()
    if request.method == 'POST':
        fechaDesde = (request.form.get('desdeFecha') or '').strip()
        fechaHasta = (request.form.get('hastaFecha') or '').strip()
        cliente = request.form.get('IDCliente')
        factura = request.form.get('IDFactura')

        query = supabase.table('despachos').select(
            'id_despacho, numero_guia, fecha, id_pedido, id_factura, id_bodega, estado, observacion, '
            'pedidos!inner(id_pedido, cliente_asociado, vendedor_asociado), '
            'facturas!left(id_factura, numero_factura, razon_social)'
        )
        if fechaDesde:
            query = query.gte('fecha', fechaDesde)
        if fechaHasta:
            query = query.lte('fecha', fechaHasta)
        if cliente:
            pedido_ids = [
                row.get('id_pedido') for row in (
                    supabase.table('pedidos').select('id_pedido').eq('cliente_asociado', cliente).execute().data or []
                ) if row.get('id_pedido') is not None
            ]
            if pedido_ids:
                query = query.in_('id_pedido', pedido_ids)
            else:
                return render_template(
                    'analisisDespachosSegunFacturaCliente.html',
                    clientes=responseClientes.data or [],
                    facturas=responseFacturas.data or [],
                    vendedores=responseVendedores.data or [],
                    datos=[],
                )
        if factura:
            query = query.eq('id_factura', factura)

        response = query.execute()
        return render_template(
            'analisisDespachosSegunFacturaCliente.html',
            clientes=responseClientes.data or [],
            facturas=responseFacturas.data or [],
            vendedores=responseVendedores.data or [],
            datos=response.data or [],
        )

    return render_template(
        'analisisDespachosSegunFacturaCliente.html',
        clientes=responseClientes.data or [],
        facturas=responseFacturas.data or [],
        vendedores=responseVendedores.data or [],
    )

@app.route('/analisisDespachoVendedorProducto.html', methods=['GET', 'POST'])
def analisisDespachoVendedorProducto():
    responseProductos = supabase.table('producto_variantes').select('id_variante, descripcion').execute()
    responseVendedores = supabase.table('vendedores').select('id_vendedor, nombre').execute()
    responseClientes = supabase.table('clientes').select('id_cliente, nombre').execute()
    if request.method == 'POST':
        #Despachos por vendedor y producto; cuantos productos y de qué tipo se enviaron
        #a qué vendedor.
        vendedor = request.form['IDVendedor']
        producto = request.form['IDProducto']
        response = (
            supabase.table('despachos').select('*, pedidos!inner(id_pedido), facturas!left(id_factura, numero_factura)')
            .eq('pedidos.vendedor_asociado', vendedor)
            .execute()
        )
        responsePedidos = (
            supabase.table("pedidos").select("*, detalle_pedidos!inner(id_variante, cantidad, producto_variantes!inner(id_variante, descripcion))")
            .eq("detalle_pedidos.id_variante", producto)
            .execute())

        return render_template('analisisDespachoVendedorProducto.html', vendedores=responseVendedores.data, clientes=responseClientes.data, productos=responseProductos.data, datos=response.data, datosPedidos=responsePedidos.data)
    else:
        return render_template('analisisDespachoVendedorProducto.html', vendedores=responseVendedores.data, clientes=responseClientes.data, productos=responseProductos.data)

@app.route('/analisisPedidosDespachosMensuales.html', methods=['GET', 'POST'])
def analisisPedidosDespachosMensuales():
    if request.method == 'POST':
        #TODO: Clarificar si los pedidos son creados, cumplidos, o vencen en un mes específico
        #Aparte de eso, debería ser autoexplicativo, sacar los pedidos
        fechaDesde = request.form['desdeFecha']
        fechaHasta = request.form['hastaFecha']
        responsePedidos = (
            supabase.table('pedidos').select('*')
            .gte('fecha_pedido', fechaDesde)
            .lte('fecha_pedido',fechaHasta)
            .execute()
        )
        responseDespachos = (
                    supabase.table('despachos').select('*')
                    .gte('fecha', fechaDesde)
                    .lte('fecha',fechaHasta)
                    .execute()
                )

        return render_template('analisisPedidosDespachosMensuales.html', pedidos = responsePedidos.data, despachos = responseDespachos.data)
    else:
        return render_template('analisisPedidosDespachosMensuales.html')

@app.route('/analisisVentasDescuentos.html', methods=['GET', 'POST'])
def analisisVentasDescuentos():
    if request.method == 'POST':
        fechaDesde = (request.form.get('desdeFecha') or '').strip()
        fechaHasta = (request.form.get('hastaFecha') or '').strip()

        query = supabase.table('pedidos').select(
            'id_pedido, fecha_pedido, fecha_entrega, estado, cliente_asociado, vendedor_asociado'
        )
        if fechaDesde:
            query = query.gte('fecha_pedido', fechaDesde)
        if fechaHasta:
            query = query.lte('fecha_pedido', fechaHasta)

        responsePedidos = query.execute()
        responseClientes = (
            supabase.table('clientes')
            .select('id_cliente, descuento_1, descuento_2, descuento_3, nombre')
            .execute()
        )
        responseVendedores = (
            supabase.table('vendedores')
            .select('id_vendedor, porcentaje_comision, nombre')
            .execute()
        )

        return render_template(
            'analisisVentasDescuentos.html',
            datosPedidos=responsePedidos.data or [],
            datosClientes=responseClientes.data or [],
            datosVendedores=responseVendedores.data or [],
        )
    return render_template('analisisVentasDescuentos.html')

@app.route('/resumenProduccion.html', methods=['GET', 'POST'])
def resumenProduccion():
    if request.method == 'POST':
        fechaDesde = (request.form.get('desdeFecha') or '').strip()
        fechaHasta = (request.form.get('hastaFecha') or '').strip()
        query = supabase.table('cortes').select(
            'id_corte, fecha_corte, fecha_ingreso, cantidad, producto_asociado, estado, '
            'productos!inner(id_producto, descripcion)'
        )
        if fechaDesde:
            query = query.gte('fecha_ingreso', fechaDesde)
        if fechaHasta:
            query = query.lte('fecha_ingreso', fechaHasta)

        rows = query.execute().data or []
        resumen = {}
        for row in rows:
            producto_id = row.get('producto_asociado')
            producto_desc = None
            producto_rel = row.get('productos')
            if isinstance(producto_rel, dict):
                producto_desc = producto_rel.get('descripcion')
            key = (producto_id, producto_desc)
            if key not in resumen:
                resumen[key] = {
                    'producto_id': producto_id,
                    'descripcion': producto_desc or 'Sin descripción',
                    'cantidad_total': 0,
                    'cortes': 0,
                }
            resumen[key]['cantidad_total'] += int(row.get('cantidad') or 0)
            resumen[key]['cortes'] += 1

        return render_template('resumenProduccion.html', datos=list(resumen.values()))
    return render_template('resumenProduccion.html')

@app.route('/inventario.html', methods=['GET', 'POST'])
def inventario():
    if request.method == 'POST':
        query = supabase.table('inventario').select(
            'id_inventario, id_bodega, id_variante, id_talla, id_color, cantidad, cantidad_defectuosa, '
            'usuario_actualizacion, '
            'bodegas!inner(id_bodega, descripcion), '
            'producto_variantes!inner(id_variante, descripcion), '
            'tallas!inner(id_talla, nombre), '
            'colores!inner(id_color, descripcion)'
        )
        if request.form.get('desdeFecha'):
            query = query.gte('fecha_actualizacion', request.form['desdeFecha'])
        if request.form.get('hastaFecha'):
            query = query.lte('fecha_actualizacion', request.form['hastaFecha'])

        rows = query.execute().data or []
        datos = []
        for row in rows:
            bodega = row.get('bodegas') if isinstance(row.get('bodegas'), dict) else {}
            variante = row.get('producto_variantes') if isinstance(row.get('producto_variantes'), dict) else {}
            talla = row.get('tallas') if isinstance(row.get('tallas'), dict) else {}
            color = row.get('colores') if isinstance(row.get('colores'), dict) else {}
            datos.append({
                'id_inventario': row.get('id_inventario'),
                'bodega': bodega.get('descripcion') if isinstance(bodega, dict) else row.get('id_bodega'),
                'producto': variante.get('descripcion') if isinstance(variante, dict) else row.get('id_variante'),
                'talla': talla.get('nombre') if isinstance(talla, dict) else row.get('id_talla'),
                'color': color.get('descripcion') if isinstance(color, dict) else row.get('id_color'),
                'cantidad': row.get('cantidad') or 0,
                'cantidad_defectuosa': row.get('cantidad_defectuosa') or 0,
                'usuario_actualizacion': row.get('usuario_actualizacion'),
            })

        return render_template('inventario.html', datos=datos)
    return render_template('inventario.html')

@app.route('/informeCobranza.html', methods=['GET'])
def informeCobranza():
    cliente_filter = (request.args.get('cliente') or '').strip()
    fecha_desde = (request.args.get('fecha_desde') or '').strip()
    fecha_hasta = (request.args.get('fecha_hasta') or '').strip()
    dias_min_raw = (request.args.get('dias_morosidad_min') or '').strip()

    try:
        rows = obtener_informe_cobranza(request.args)
    except Exception:
        flash("No se pudo cargar el informe de cobranza. Intenta nuevamente.", "error")
        rows = []

    return render_template(
        'informeCobranza.html',
        datos=rows,
        cliente_filter=cliente_filter,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        dias_morosidad_min=dias_min_raw,
    )


@app.route('/informeCobranza.pdf', methods=['GET'])
def informeCobranzaPDF():
    try:
        rows = obtener_informe_cobranza(request.args)
        if not rows:
            flash("No hay cobranza pendiente para el criterio seleccionado.", "warning")
            return redirect(url_for('informeCobranza', **request.args))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=28,
            leftMargin=28,
            topMargin=32,
            bottomMargin=28,
        )
        styles = getSampleStyleSheet()
        title = Paragraph('Informe de cobranza', styles['Title'])
        generated = Paragraph(f'Generado: {datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S UTC")}', styles['BodyText'])

        table_data = [[
            'Cliente', 'Folio', 'Fecha emisión', 'Monto', 'Pagos aplicados', 'Saldo', 'Días transcurridos'
        ]]
        for row in rows:
            table_data.append([
                row.get('cliente') or 'Sin cliente',
                row.get('folio') or '',
                row.get('fecha') or '',
                f"${row.get('monto', 0):,.2f}",
                f"${row.get('pagos_aplicados', 0):,.2f}",
                f"${row.get('saldo', 0):,.2f}",
                str(row.get('dias_morosidad', 0)),
            ])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf4ef')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.7, colors.grey),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        doc.build([title, generated, table])
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='informe_cobranza.pdf')
    except Exception:
        flash("No se pudo generar el PDF. Intenta nuevamente.", "error")
        return redirect(url_for('informeCobranza', **request.args))


@app.route('/cortes.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def cortes():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            fecha = request.form['fechaCorteCrear']
            cortador = request.form['cortadorCrear']
            cantidad = request.form['cantidadCrear']
            observaciones = request.form['observacionesCrear']
            material = request.form['materialCrear']
            idProducto = request.form['IdProductoCrear']
            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("cortes").insert({"fecha_corte": fecha, "cantidad": cantidad,
                        "cortador": cortador, "observaciones": observaciones, "material_usado": material, 
                        "producto_asociado": idProducto
                        }).execute()
            )
            if response.data:
                return "Corte creado exitosamente"
            else:
                return "Error creando corte", 500
        if (metodo == "put"):
            idAACtualizar = request.form['IdCorteActualizar']
            fecha = request.form['fechaCorteActualizar']
            cortador = request.form['cortadorActualizar']
            cantidad = request.form['cantidadActualizar']
            observaciones = request.form['observacionesActualizar']
            material = request.form['materialActualizar']
            idProducto = request.form['IdProductoActualizar'] 
            response = (
                
                supabase.table("cortes").update({"fecha_corte": fecha, "cantidad": cantidad,
                        "cortador": cortador, "observaciones": observaciones, "material_usado": material, 
                        "producto_asociado": idProducto
                        }).eq("id_corte", idAACtualizar).select("id_corte").execute()
            )
            if response.data:
                return "Corte actualizado exitosamente"
            else:
                return "Error actualizando corte", 500
        if (metodo == "delete"):
            idABorrar = request.form['idCorteBorrar']
            try:
                response = (
                    supabase.table("cortes").delete()
                    .eq("id_corte", idABorrar)
                    .execute()
                )
            except APIError:
                return "No se puede borrar: esta guía de cortes ya fue ingresada a bodega", 400
            if response.data:
                return "Corte borrado exitosamente"
            else:
                return "Error borrando corte", 500
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarcorteid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('cortes.html', datos = response.data)
            else:
                return "No se ha encontrado ningún corte con la ID buscada" 
    else:
        response =(
            supabase.table("cortes").select("*").execute()
        )
            
        return render_template('cortes.html', datos = response.data)

@app.route('/clientes.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def clientes():
    zonaVenta_response = supabase.table("zona_venta").select("id_zona_venta, descripcion").execute()
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            rut = request.form['rut']
            nom = request.form['nombre']
            correo = request.form['correo']
            tf = request.form['telefono']
            direccion = request.form['direccion']
            digVer = request.form['digVer']
            abreviacion = request.form['abreviacion']
            ciudad = request.form['ciudad']
            comuna = request.form['comuna']
            condVenta = request.form['condicionesVenta']
            viaDes = request.form['viaDespacho']
            porComi = request.form['porComision']
            porCobra = request.form['porCobranza']
            obs = request.form['observaciones']
            idZona = request.form.get('idZonaVentaForm')
            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("clientes").insert({"rut": rut, "nombre": nom,
                        "correo": correo, "telefono": tf, "direccion": direccion, 
                        "digito_verificador": digVer,
                        "abreviacion": abreviacion,"ciudad": ciudad,
                        "comuna": comuna, "condiciones_venta": condVenta,
                        "via_despacho": viaDes,"porcentaje_comision": porComi,
                        "porcentaje_cobranza": porCobra,"observaciones": obs,
                        "id_zona_venta": idZona
                        }).execute()
            )
            if response.data:
                flash("Cliente creado exitosamente", "success")
                return redirect(url_for('clientes'))
            else:
                flash("Error creando cliente", "error")
                return redirect(url_for('clientes'))
        if (metodo == "put"):
            idAACtualizar = request.form['idClienteActualizar']
            rut = request.form['rutActualizar']
            nom = request.form['nombreActualizar']
            correo = request.form['correoActualizar']
            tf = request.form['telefonoActualizar']
            direccion = request.form['direccionActualizar']
            digVer = request.form['digVerActualizar']
            abreviacion = request.form['abreviacionActualizar']
            ciudad = request.form['ciudadActualizar']
            comuna = request.form['comunaActualizar']
            condVenta = request.form['condicionesVentaActualizar']
            viaDes = request.form['viaDespachoActualizar']
            porComi = request.form['porComisionActualizar']
            porCobra = request.form['porCobranzaActualizar']
            obs = request.form['observacionesActualizar']
            idZona = request.form.get('idZonaVentaActualizar')  
            response = (
                
                supabase.table("clientes").update({"rut": rut, "nombre": nom,
                        "correo": correo, "telefono": tf, "direccion": direccion, 
                        "digito_verificador": digVer,
                        "abreviacion": abreviacion,"ciudad": ciudad,
                        "comuna": comuna, "condiciones_venta": condVenta,
                        "via_despacho": viaDes,"porcentaje_comision": porComi,
                        "porcentaje_cobranza": porCobra,"observaciones": obs,
                        "id_zona_venta": idZona
                        }).eq("id_cliente", idAACtualizar).select("id_cliente").execute()
            )
            if response.data:
                flash("Cliente actualizado exitosamente", "success")
                return redirect(url_for('clientes'))
            else:
                flash("Error actualizando cliente", "error")
                return redirect(url_for('clientes'))
        if (metodo == "delete"):
            idABorrar = request.form['idClienteBorrar']
            response = (
                supabase.table("clientes").delete()
                .eq("id_cliente", idABorrar)
                .execute()
            )
            if response.data:
                flash("Cliente borrado exitosamente", "success")
                return redirect(url_for('clientes'))
            else:
                flash("Error borrando cliente", "error")
                return redirect(url_for('clientes'))
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarclienteid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('clientes.html', datos = response.data, zonasVenta = zonaVenta_response.data)
            else:
                return "No se ha encontrado ningún cliente con la id buscada"
        if (metodo == "buscarNombre"):
            texto = request.form["nombreBuscar"]
            response = supabase.rpc('buscarclientenombre', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('clientes.html', datos = response.data, zonasVenta = zonaVenta_response.data)
            else:
                return "No se ha encontrado ningún cliente con el nombre buscado"
        if (metodo == "buscarAbreviacion"):
            texto = request.form["abreviacionBuscar"]
            response = supabase.rpc('buscarclienteabreviacion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('clientes.html', datos = response.data, zonasVenta = zonaVenta_response.data)
            else:
                return "No se ha encontrado ningún cliente con la abreviacion buscada" 
    else:
        response =(
            supabase.table("clientes").select("*").execute()
        )
            
        return render_template('clientes.html', datos = response.data, zonasVenta = zonaVenta_response.data)

@app.route('/colores.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def colores():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            codigo = request.form['codigoCrear']
            descripcion = request.form['descripcionCrear']
            codigoEan = _texto_o_nulo(request.form.get('codigoEanCrear'))

            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("colores").insert({"codigo_color": codigo, "descripcion": descripcion,
                        "codigo_ean": codigoEan
                        }).execute()
            )
            if response.data:
                return "Color creado exitosamente"
            else:
                return "Error creando color", 500
        if (metodo == "put"):
            idColor = request.form['idColorActualizar']
            codigo = request.form['codigoActualizar']
            descripcion = request.form['descripcionActualizar']
            codigoEan = _texto_o_nulo(request.form.get('codigoEanActualizar'))
            response = (

                supabase.table("colores").update({"codigo_color": codigo, "descripcion": descripcion,
                        "codigo_ean": codigoEan
                        }).eq("id_color", idColor).select("id_color").execute()
            )
            if response.data:
                return "Color actualizado exitosamente"
            else:
                return "Error actualizando color", 500
        if (metodo == "delete"):
            idABorrar = request.form['idColorBorrar']
            response = (
                supabase.table("colores").delete()
                .eq("id_color", idABorrar)
                .execute()
            )
            if response.data:
                return "Color borrado exitosamente"
            else:
                return "Error borrando color", 500
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarcolorid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('colores.html', datos = response.data)
            else:
                return "No se ha encontrado ningún color con la id buscada"
        if (metodo == "buscarDescripcion"):
            texto = request.form["descripcionBuscar"]
            response = supabase.rpc('buscarcolordescripcion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('colores.html', datos = response.data)
            else:
                return "No se ha encontrado ningún color con la descrpición buscada"
        if (metodo == "buscarCodigo"):
            texto = request.form["codigoBuscar"]
            response = supabase.rpc('buscarcolorcodigo', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('colores.html', datos = response.data)
            else:
                return "No se ha encontrado ningún color con el código buscado"
    else:
        response =(
            supabase.table("colores").select("*").execute()
        )
            
        return render_template('colores.html', datos = response.data)
    
@app.route('/bodegas.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def bodegas():
    if request.method == 'POST':
        metodo = request.form['_method']
        if metodo == "inventario_post":
            response = supabase.table("inventario").insert({
                "id_bodega": request.form['idBodegaInventario'],
                "id_producto": request.form['idProductoInventario'],
                "id_talla": request.form['idTallaInventario'],
                "id_color": request.form['idColorInventario'],
                "cantidad": request.form['cantidadInventario']
            }).execute()
            if response.data:
                return redirect(url_for('bodegas'))
            return "Error creando registro de inventario", 500
        if metodo == "inventario_put":
            idInventario = request.form['idInventarioActualizar']
            response = supabase.table("inventario").update({
                "id_bodega": request.form['idBodegaInventarioActualizar'],
                "id_producto": request.form['idProductoInventarioActualizar'],
                "id_talla": request.form['idTallaInventarioActualizar'],
                "id_color": request.form['idColorInventarioActualizar'],
                "cantidad": request.form['cantidadInventarioActualizar']
            }).eq("id_inventario", idInventario).select("id_inventario").execute()
            if response.data:
                return redirect(url_for('bodegas'))
            return "Error actualizando registro de inventario", 500
        if metodo == "inventario_delete":
            response = supabase.table("inventario").delete().eq(
                "id_inventario", request.form['idInventarioBorrar']
            ).execute()
            if response.data:
                return redirect(url_for('bodegas'))
            return "Error borrando registro de inventario", 500
        if (metodo == "post"):
            descripcion = request.form['descripcionCrear']

            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("bodegas").insert({"descripcion": descripcion
                        }).execute()
            )
            if response.data:
                flash("Bodega creada exitosamente", "success")
                return redirect(url_for('bodegas'))
            else:
                flash("Error creando bodega", "error")
                return redirect(url_for('bodegas'))
        if (metodo == "put"):
            idBodega = request.form['IdBodegaActualizar']
            descripcion = request.form['descripcionActualizar'] 
            response = (
                
                supabase.table("bodegas").update({"descripcion": descripcion
                        }).eq("id_bodega", idBodega).select("id_bodega").execute()
            )
            if response.data:
                flash("Bodega actualizada exitosamente", "success")
                return redirect(url_for('bodegas'))
            else:
                flash("Error actualizando bodega", "error")
                return redirect(url_for('bodegas'))
        if (metodo == "delete"):
            idABorrar = request.form['idBodegaBorrar']
            response = (
                supabase.table("bodegas").delete()
                .eq("id_bodega", idABorrar)
                .execute()
            )
            if response.data:
                flash("Bodega borrada exitosamente", "success")
                return redirect(url_for('bodegas'))
            else:
                flash("Error borrando bodega", "error")
                return redirect(url_for('bodegas'))
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarbodegaid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('bodegas.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna bodega con la id buscada"
        if (metodo == "buscarDescripcion"):
            texto = request.form["descripcionBuscar"]
            response = supabase.rpc('buscarbodegadescripcion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('bodegas.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna bodega con la descrpición buscada"
    else:
        bodegas_response = supabase.table("bodegas").select("*").execute()
        inventario_disponible = True
        try:
            inventario_response = supabase.table("inventario").select("*").execute()
        except APIError as error:
            if "PGRST205" not in str(error):
                raise
            inventario_data = []
            inventario_disponible = False
        else:
            inventario_data = inventario_response.data
        productos_response = supabase.table("productos").select("*").execute()
        tallas_response = supabase.table("tallas").select("*").execute()
        colores_response = supabase.table("colores").select("*").execute()

        return render_template(
            'bodegas.html',
            datos=bodegas_response.data,
            inventario=inventario_data,
            inventario_disponible=inventario_disponible,
            productos=productos_response.data,
            tallas=tallas_response.data,
            colores=colores_response.data
        )

@app.route('/vendedores.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def vendedores():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            nombre = request.form['nombreCrear']
            rut = request.form['rutCrear']
            digVer = request.form['digVerCrear']
            porComi = request.form['porComiCrear']
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("vendedores").insert({"rut": rut, "nombre": nombre,
                        "digito_verificador": digVer, "porcentaje_comision": porComi
                        }).execute()
            )
            if response.data:
                flash("Vendedor creado exitosamente", "success")
                return redirect(url_for('vendedores'))
            else:
                flash("Error creando vendedor", "error")
                return redirect(url_for('vendedores'))
        if (metodo == "put"):
            idVendedor = request.form['IdVendedorActualizar']
            nombre = request.form['nombreActualizar']
            rut = request.form['rutActualizar']
            digVer = request.form['digVerActualizar']
            porComi = request.form['porComiActualizar']
            response = (
                
                supabase.table("vendedores").update({"rut": rut, "nombre": nombre,
                        "digito_verificador": digVer, "porcentaje_comision": porComi
                        }).eq("id_vendedor", idVendedor).select("id_vendedor").execute()
            )
            if response.data:
                flash("Vendedor actualizado exitosamente", "success")
                return redirect(url_for('vendedores'))
            else:
                flash("Error actualizando vendedor", "error")
                return redirect(url_for('vendedores'))
        if (metodo == "delete"):
            idABorrar = request.form['idVendedorBorrar']
            response = (
                supabase.table("vendedores").delete()
                .eq("id_vendedor", idABorrar)
                .execute()
            )
            if response.data:
                flash("Vendedor borrado exitosamente", "success")
                return redirect(url_for('vendedores'))
            else:
                flash("Error borrando vendedor", "error")
                return redirect(url_for('vendedores'))
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarvendedorid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('vendedores.html', datos = response.data)
            else:
                return "No se ha encontrado ningún vendedor con la id buscada"
        if (metodo == "buscarNombre"):
            texto = request.form["nombreBuscar"]
            response = supabase.rpc('buscarvendedornombre', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('vendedores.html', datos = response.data)
            else:
                return "No se ha encontrado ningún vendedor con el nombre buscado"
    else:
        response =(
            supabase.table("vendedores").select("*").execute()
        )
            
        return render_template('vendedores.html', datos = response.data)

@app.route('/zonasVenta.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def zonasVenta():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            nombre = request.form['nombreCrear'].strip()
            descripcion = request.form['descripcionCrear']

            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("zona_venta").insert({"nombre": nombre,
                        "descripcion": descripcion
                        }).execute()
            )
            if response.data:
                flash("Zona de venta creada exitosamente", "success")
                return redirect(url_for('zonasVenta'))
            else:
                flash("Error creando zona de venta", "error")
                return redirect(url_for('zonasVenta'))
        if (metodo == "put"):
            idZonaVenta = request.form['IdZonaVentaActualizar']
            nombre = request.form['nombreActualizar'].strip()
            descripcion = request.form['descripcionActualizar']
            response = (

                supabase.table("zona_venta").update({"nombre": nombre,
                        "descripcion": descripcion
                        }).eq("id_zona_venta", idZonaVenta).select("id_zona_venta").execute()
            )
            if response.data:
                flash("Zona de venta actualizada exitosamente", "success")
                return redirect(url_for('zonasVenta'))
            else:
                flash("Error actualizando zona de venta", "error")
                return redirect(url_for('zonasVenta'))
        if (metodo == "delete"):
            idABorrar = request.form['idZonaVentaBorrar']
            response = (
                supabase.table("zona_venta").delete()
                .eq("id_zona_venta", idABorrar)
                .execute()
            )
            if response.data:
                flash("Zona de venta borrada exitosamente", "success")
                return redirect(url_for('zonasVenta'))
            else:
                flash("Error borrando zona de venta", "error")
                return redirect(url_for('zonasVenta'))
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarzonaventaid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('zonasVenta.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna zona de venta con la id buscada"
        if (metodo == "buscarDescripcion"):
            texto = request.form["descripcionBuscar"]
            response = supabase.rpc('buscarzonaventadescripcion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('zonasVenta.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna zona de venta con la descripción buscada"
    else:
        response =(
            supabase.table("zona_venta").select("*").execute()
        )
            
        return render_template('zonasVenta.html', datos = response.data)

@app.route('/tallas.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def tallas():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            talla = request.form['tallaCrear']
            nombre = _texto_o_nulo(request.form.get('nombreCrear'))
            codigoEan = _texto_o_nulo(request.form.get('codigoEanCrear'))

            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("tallas").insert({"talla": talla, "nombre": nombre, "codigo_ean": codigoEan
                        }).execute()
            )
            if response.data:
                return "Talla creada exitosamente"
            else:
                return "Error creando talla", 500
        if (metodo == "put"):
            idTalla = request.form['IdTallaActualizar']
            talla = request.form['tallaActualizar']
            nombre = _texto_o_nulo(request.form.get('nombreActualizar'))
            codigoEan = _texto_o_nulo(request.form.get('codigoEanActualizar'))
            response = (

                supabase.table("tallas").update({"talla": talla, "nombre": nombre, "codigo_ean": codigoEan
                        }).eq("id_talla", idTalla).select("id_talla").execute()
            )
            if response.data:
                return "Talla actualizada exitosamente"
            else:
                return "Error actualizando talla", 500
        if (metodo == "delete"):
            idABorrar = request.form['idTallaBorrar']
            response = (
                supabase.table("tallas").delete()
                .eq("id_talla", idABorrar)
                .execute()
            )
            if response.data:
                return "Talla borrada exitosamente"
            else:
                return "Error borrando talla", 500
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscartallaid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('tallas.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna talla con la id buscada"
        if (metodo == "buscarNTalla"):
            texto = request.form["nTallaBuscar"]
            response = supabase.rpc('buscartallanumerotalla', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('tallas.html', datos = response.data)
            else:
                return "No se ha encontrado ninguna talla con el número de talla buscado"
    else:
        response =(
            supabase.table("tallas").select("*").execute()
        )
            
        return render_template('tallas.html', datos = response.data)

@app.route('/productos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def productos():
    if request.method == 'POST':
        metodo = request.form['_method']
        if (metodo == "post"):
            descripcion = request.form['descripcionCrear']
            abreviacion = request.form['abreviacionCrear']
            idColor = request.form['idColorCrear']
            precio = request.form['precioCrear']
            idTalla = request.form['idTallaCrear']
            codigo = _texto_o_nulo(request.form.get('codigoCrear'))
            codigoEan = _texto_o_nulo(request.form.get('codigoEanCrear'))

            try:
                response = (
                    supabase.table("productos").insert({"abreviacion": abreviacion, "descripcion": descripcion,
                            "color": idColor, "precio": precio, "talla": idTalla,
                            "codigo": codigo, "codigo_ean": codigoEan
                            }).execute()
                )
            except APIError as error:
                if error.code == "23503":
                    mensaje = "El color o talla seleccionado no existe"
                elif error.code == "22P02":
                    mensaje = "El color o talla seleccionado no es válido"
                elif error.code == "23505":
                    mensaje = "Ya existe un producto con ese código de artículo"
                elif error.code == "23514":
                    mensaje = "El código EAN del producto solo puede tener números"
                else:
                    mensaje = "No se pudo crear el producto"
                flash(mensaje, "error")
                return redirect(url_for('productos'))
            if response.data:
                flash("Producto creado exitosamente", "success")
                return redirect(url_for('productos'))
            else:
                flash("Error creando producto", "error")
                return redirect(url_for('productos'))
        if (metodo == "put"):
            idProducto = request.form['IdProductoActualizar']
            descripcion = request.form['descripcionActualizar']
            abreviacion = request.form['abreviacionActualizar']
            idColor = request.form['idColorActualizar']
            precio = request.form['precioActualizar']
            idTalla = request.form['idTallaActualizar']
            codigo = _texto_o_nulo(request.form.get('codigoActualizar'))
            codigoEan = _texto_o_nulo(request.form.get('codigoEanActualizar'))
            try:
                response = (
                    supabase.table("productos").update({"abreviacion": abreviacion, "descripcion": descripcion,
                            "color": idColor, "precio": precio, "talla": idTalla,
                            "codigo": codigo, "codigo_ean": codigoEan}).eq("id_producto", idProducto).select("id_producto").execute()
                )
            except APIError as error:
                if error.code == "23503":
                    mensaje = "El color o talla seleccionado no existe"
                elif error.code == "22P02":
                    mensaje = "El color o talla seleccionado no es válido"
                elif error.code == "23505":
                    mensaje = "Ya existe un producto con ese código de artículo"
                elif error.code == "23514":
                    mensaje = "El código EAN del producto solo puede tener números"
                elif error.code == "P0001":
                    mensaje = error.message
                else:
                    mensaje = "No se pudo actualizar el producto"
                flash(mensaje, "error")
                return redirect(url_for('productos'))
            if response.data:
                flash("Producto actualizado exitosamente", "success")
                return redirect(url_for('productos'))
            else:
                flash("Error actualizando producto", "error")
                return redirect(url_for('productos'))
        if (metodo == "delete"):
            idABorrar = request.form['idProductoBorrar']
            response = (
                supabase.table("productos").delete()
                .eq("id_producto", idABorrar)
                .execute()
            )
            if response.data:
                flash("Producto borrado exitosamente", "success")
                return redirect(url_for('productos'))
            else:
                flash("Error borrando producto", "error")
                return redirect(url_for('productos'))
        if (metodo == "buscarID"):
            texto = request.form["idBuscar"]
            response = supabase.rpc('buscarproductoid', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('productos.html', datos = response.data)
            else:
                return "No se ha encontrado ningún producto con la id buscada"
        if (metodo == "buscarDescripcion"):
            texto = request.form["descripcionBuscar"]
            response = supabase.rpc('buscarproductodescripcion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('productos.html', datos = response.data)
            else:
                return "No se ha encontrado ningún producto con la descripción buscada"
        if (metodo == "buscarAbreviacion"):
            texto = request.form["abreviacionBuscar"]
            response = supabase.rpc('buscarproductoabreviacion', { 'textobusqueda': texto }).execute()
            if response.data:
                return render_template('productos.html', datos = response.data)
            else:
                return "No se ha encontrado ningún producto con la abreviación buscada"
    else:
        response =(
            supabase.table("productos").select("*").execute()
        )
        colores_response = supabase.table("colores").select("*").execute()
        tallas_response = supabase.table("tallas").select("*").execute()
            
        return render_template(
            'productos.html',
            datos=response.data,
            colores=colores_response.data,
            tallas=tallas_response.data
        )

@app.route('/codigosEAN.html', methods=['GET', 'POST'])
def codigosEAN():
    # RF-015/016: el EAN de cada variante (producto + color + talla) lo arma la
    # base de datos con los códigos de cada maestro (fn_generar_ean). Aquí se
    # consulta, y se puede fijar un código manual o volver al automático.
    if request.method == 'POST':
        metodo = request.form.get('_method')
        idVariante = request.form.get('idVariante', '')
        try:
            if metodo == "manual":
                codigo = (request.form.get('codigoManual') or '').strip()
                if len(codigo) != 13 or not codigo.isdigit():
                    flash("El código manual debe tener 13 dígitos", "error")
                    return redirect(url_for('codigosEAN'))
                supabase.table("producto_variantes").update({"ean_manual": True, "codigo_ean": codigo}) \
                    .eq("id_variante", idVariante).execute()
                flash("Código manual guardado", "success")
            elif metodo == "automatico":
                supabase.table("producto_variantes").update({"ean_manual": False}) \
                    .eq("id_variante", idVariante).execute()
                flash("La variante vuelve a usar el código automático", "success")
        except APIError as error:
            if error.code == "23505":
                flash("Ese código EAN ya está asignado a otra variante", "error")
            else:
                flash(error.message or "No se pudo actualizar el código EAN", "error")
        return redirect(url_for('codigosEAN'))

    texto = request.args.get('q', '').strip()
    query = supabase.table("v_codigos_ean").select("*").order("codigo_articulo").order("color").order("id_talla")
    if texto:
        query = query.ilike("descripcion", f"%{texto}%")
    datos = query.execute().data or []
    return render_template('codigosEAN.html', datos=datos, busqueda=texto)


MAX_ETIQUETAS_POR_EMISION = 2000


@app.route('/emisionEAN.html', methods=['GET', 'POST'])
def emisionEAN():
    # RF-017: se elige producto y color, se indica cuántas etiquetas por talla
    # y se genera la hoja para imprimir en la impresora de etiquetas.
    if request.method == 'GET':
        productos = supabase.table("productos").select("id_producto, codigo, descripcion, codigo_ean") \
            .order("codigo").execute().data or []
        colores = supabase.table("colores").select("id_color, descripcion, codigo_ean") \
            .order("descripcion").execute().data or []
        tallas = supabase.table("tallas").select("id_talla, talla, nombre, codigo_ean") \
            .order("talla").execute().data or []
        return render_template('emisionEAN.html', productos=productos, colores=colores, tallas=tallas)

    try:
        idProducto = int(request.form.get('idProducto', ''))
        idColor = int(request.form.get('idColor', ''))
    except ValueError:
        flash("Seleccione un producto y un color", "error")
        return redirect(url_for('emisionEAN'))

    cantidades = {}
    for clave, valor in request.form.items():
        if not clave.startswith('cantidad_') or not valor.strip():
            continue
        try:
            idTalla = int(clave.removeprefix('cantidad_'))
            cantidad = int(valor)
        except ValueError:
            flash("Las cantidades deben ser números enteros", "error")
            return redirect(url_for('emisionEAN'))
        if cantidad < 0:
            flash("Las cantidades no pueden ser negativas", "error")
            return redirect(url_for('emisionEAN'))
        if cantidad > 0:
            cantidades[idTalla] = cantidad

    if not cantidades:
        flash("Ingrese la cantidad de etiquetas de al menos una talla", "error")
        return redirect(url_for('emisionEAN'))
    if sum(cantidades.values()) > MAX_ETIQUETAS_POR_EMISION:
        flash(f"No se pueden emitir más de {MAX_ETIQUETAS_POR_EMISION} etiquetas a la vez", "error")
        return redirect(url_for('emisionEAN'))

    producto = supabase.table("productos").select("id_producto, codigo, descripcion") \
        .eq("id_producto", idProducto).execute().data
    color = supabase.table("colores").select("descripcion").eq("id_color", idColor).execute().data
    tallas = supabase.table("tallas").select("id_talla, talla, nombre") \
        .in_("id_talla", list(cantidades)).order("talla").execute().data or []
    if not producto or not color or len(tallas) != len(cantidades):
        flash("El producto, color o talla seleccionado no existe", "error")
        return redirect(url_for('emisionEAN'))
    producto = producto[0]

    etiquetas = []
    sin_codigo = []
    for talla in tallas:
        nombreTalla = talla.get('nombre') or str(talla['talla'])
        try:
            variante = supabase.rpc('obtener_variante', {
                'p_id_producto': idProducto,
                'p_id_color': idColor,
                'p_id_talla': talla['id_talla']
            }).execute().data
        except APIError as error:
            flash(error.message or "No se pudo generar el código EAN", "error")
            return redirect(url_for('emisionEAN'))
        codigo = variante[0]['codigo_ean'] if variante else None
        if not codigo:
            sin_codigo.append(nombreTalla)
            continue
        etiqueta = {
            'articulo': producto.get('codigo') or str(producto['id_producto']),
            'descripcion': producto['descripcion'],
            'color': color[0]['descripcion'],
            'talla': nombreTalla,
            'ean': codigo,
            'barras': Markup(ean13.svg(codigo)),
        }
        etiquetas.extend([etiqueta] * cantidades[talla['id_talla']])

    if sin_codigo:
        flash("Falta el código EAN del producto, del color o de la talla para: "
              + ", ".join(sin_codigo) + ". Complételo en los datos maestros.", "error")
        return redirect(url_for('emisionEAN'))

    filas = [etiquetas[i:i + ETIQUETAS_POR_FILA] for i in range(0, len(etiquetas), ETIQUETAS_POR_FILA)]
    return render_template('etiquetasEAN.html', filas=filas, total=len(etiquetas))


@app.route('/archivosMaestros.html', methods=['GET'])
def archivosMaestros():
        return render_template('archivosMaestros.html')

@app.route('/configuracion.html', methods=['GET', 'POST'])
def configuracion():
    if request.method == 'GET':
        try:
            parametros = obtener_parametros_sistema()
        except APIError:
            parametros = SYSTEM_PARAMETER_DEFAULTS.copy()
            flash("No se pudo cargar la configuración desde Supabase", "error")
        return render_template('configuracion.html', parametros=parametros)

    campos = {
        "razon_social": request.form.get("razon_social", "").strip(),
        "rut": request.form.get("rut", "").strip(),
        "giro": request.form.get("giro", "").strip(),
        "direccion": request.form.get("direccion", "").strip(),
        "telefono": request.form.get("telefono", "").strip(),
        "correo": request.form.get("correo", "").strip(),
        "moneda": request.form.get("moneda", "").strip().upper(),
        "formato_moneda": request.form.get("formato_moneda", "").strip(),
        "porcentaje_impuesto": request.form.get("porcentaje_impuesto", "").strip()
    }
    monedas_permitidas = {"CLP", "USD", "EUR"}
    rut_valido = re.fullmatch(r"(?:\d{7,8}-[\dkK]|\d{1,2}(?:\.\d{3}){2}-[\dkK])", campos["rut"])
    correo_valido = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", campos["correo"])

    try:
        impuesto = float(campos["porcentaje_impuesto"])
    except (TypeError, ValueError):
        impuesto = None

    if not campos["razon_social"]:
        flash("La razón social es obligatoria", "error")
        return redirect(url_for('configuracion'))
    if not rut_valido:
        flash("El RUT no tiene un formato válido", "error")
        return redirect(url_for('configuracion'))
    if not correo_valido:
        flash("El correo electrónico no tiene un formato válido", "error")
        return redirect(url_for('configuracion'))
    if campos["moneda"] not in monedas_permitidas:
        flash("Selecciona una moneda válida", "error")
        return redirect(url_for('configuracion'))
    if not campos["formato_moneda"]:
        flash("El formato de moneda es obligatorio", "error")
        return redirect(url_for('configuracion'))
    if impuesto is None or not 0 <= impuesto <= 100:
        flash("El impuesto debe ser un valor entre 0 y 100", "error")
        return redirect(url_for('configuracion'))

    logo = request.files.get("logotipo")
    logo_path = None
    if logo and logo.filename:
        nombre_seguro = secure_filename(logo.filename)
        extension = nombre_seguro.rsplit(".", 1)[-1].lower() if "." in nombre_seguro else ""
        if not nombre_seguro or extension not in ALLOWED_LOGO_EXTENSIONS:
            flash("El archivo de logotipo no está permitido", "error")
            return redirect(url_for('configuracion'))
        logo.stream.seek(0, os.SEEK_END)
        tamano_logo = logo.stream.tell()
        logo.stream.seek(0)
        if tamano_logo > MAX_LOGO_SIZE:
            flash("El logotipo no puede superar los 2 MB", "error")
            return redirect(url_for('configuracion'))
        nombre_logo = f"logo-configurado.{extension}"
        carpeta_logo = os.path.join(app.static_folder, "img")
        os.makedirs(carpeta_logo, exist_ok=True)
        logo.save(os.path.join(carpeta_logo, nombre_logo))
        logo_path = f"img/{nombre_logo}"

    payload = {
        **campos,
        "porcentaje_impuesto": impuesto,
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
        "usuario_actualizacion": os.environ.get("SYSTEM_USER", "Admin")
    }
    if logo_path:
        payload["logotipo"] = logo_path

    try:
        existente = supabase.table("parametros_sistema").select("id").eq("id", 1).execute()
        if existente.data:
            response = (
                supabase.table("parametros_sistema").update(payload)
                .eq("id", 1).select("id").execute()
            )
        else:
            response = supabase.table("parametros_sistema").insert({"id": 1, **payload}).execute()
        if not response.data:
            flash("No se pudo guardar la configuración", "error")
            return redirect(url_for('configuracion'))
    except (APIError, OSError):
        flash("No se pudo guardar la configuración", "error")
        return redirect(url_for('configuracion'))

    flash("Configuración guardada correctamente", "success")
    return redirect(url_for('configuracion'))

@app.route('/ingresoBodega.html', methods=['GET', 'POST'])
def ingresoBodega():
    if request.method == 'GET':
        try:
            bodegas_response = supabase.table("bodegas").select("*").execute()
        except APIError:
            flash("No se pudieron cargar las bodegas disponibles", "error")
            return redirect(url_for('ingresoBodega'))
        return render_template('ingresoBodega.html', bodegas=bodegas_response.data)

    codigo_corte = request.form.get('codigoCorte', '')
    id_bodega = request.form.get('idBodega', '')
    try:
        codigo_corte = int(codigo_corte)
        id_bodega = int(id_bodega)
    except (TypeError, ValueError):
        flash("El código de corte o la bodega seleccionada no es válido", "error")
        return redirect(url_for('ingresoBodega'))

    try:
        response = supabase.rpc('ingresar_guia_corte', {
            'p_id_corte': codigo_corte,
            'p_id_bodega': id_bodega,
            'p_usuario': 'Admin'
        }).execute()
    except APIError as error:
        flash(error.message or "No se pudo ingresar la guía de cortes a la bodega", "error")
        return redirect(url_for('ingresoBodega'))

    flash(
        f"Se ingresaron {response.data} unidades de la guía {codigo_corte} en la bodega {id_bodega}",
        "success"
    )
    return redirect(url_for('ingresoBodega'))

@app.route('/produccion.html', methods=['GET'])      
def produccion():
        return render_template('produccion.html')

@app.route('/reportes.html', methods=['GET'])
def reportes():
        return render_template('reportes.html')

@app.route('/analisisProductosPedidosDespachados.html', methods=['GET'])
def analisisProductosPedidosDespachados():
        # TODO
        return render_template('analisisProductosPedidosDespachados.html')

@app.route('/', methods=['GET'])
def index():
        return render_template('index.html')

#Esto simplemente lo corre en debug mode
if __name__ == '__main__':
    app.run(debug=True)