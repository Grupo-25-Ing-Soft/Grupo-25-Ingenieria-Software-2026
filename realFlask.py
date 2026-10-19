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

# Estados en que un pedido ya no se modifica (CU-22.3) ni se anula (CU-25).
ESTADOS_PEDIDO_CERRADOS = ('despachado', 'anulado')


def _pedido_o_none(id_pedido):
    filas = supabase.table('pedidos').select('*').eq('id_pedido', id_pedido).execute().data if id_pedido else []
    return filas[0] if filas else None


def _nombre_pedido(pedido):
    return pedido.get('numero_pedido') or f"#{pedido.get('id_pedido')}"


def _leer_pedido_formulario(sufijo):
    """Valida cliente, vendedor y fechas del modal de pedidos. Devuelve (datos, error)."""
    cliente = _entero_positivo(request.form.get('IDCliente' + sufijo))
    vendedor = _entero_positivo(request.form.get('IDVendedor' + sufijo))
    if not cliente or not vendedor:
        return None, 'Seleccione el cliente y el vendedor del pedido.'
    fecha_pedido = (request.form.get('fechaPedido' + sufijo) or '').strip()
    fecha_entrega = (request.form.get('fechaLimite' + sufijo) or '').strip() or None
    if not fecha_pedido:
        return None, 'Ingrese la fecha del pedido.'
    if fecha_entrega and fecha_entrega < fecha_pedido:
        return None, 'La fecha de entrega no puede ser anterior a la fecha del pedido.'
    return {'cliente_asociado': cliente, 'vendedor_asociado': vendedor,
            'fecha_pedido': fecha_pedido, 'fecha_entrega': fecha_entrega}, None


@app.route('/pedidos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def pedidos():
    # RF-022/023/025/026 y CU-22.1 a CU-22.4, CU-25. Un pedido con despachos o
    # facturas no se elimina: se anula (queda en la base como historial).
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == 'post':
            datos, error = _leer_pedido_formulario('Crear')
            if error:
                flash(error, 'error')
                return redirect(url_for('pedidos'))
            try:
                creado = supabase.table('pedidos').insert(datos).execute().data
            except APIError:
                creado = None
            if creado:
                flash(f"Pedido {_nombre_pedido(creado[0])} creado. Agrega sus productos en el detalle.", 'success')
                return redirect(url_for('crudDetallePedido', id_pedido=creado[0]['id_pedido']))
            flash('No se pudo crear el pedido. Revisa el cliente y vendedor seleccionados', 'error')
            return redirect(url_for('pedidos'))

        pedido = _pedido_o_none(_entero_positivo(request.form.get('IdPedidoActualizar')
                                                 or request.form.get('idPedidoBorrar')
                                                 or request.form.get('idPedidoAnular')))
        if pedido is None:
            flash('El pedido no existe', 'error')
            return redirect(url_for('pedidos'))
        nombre = _nombre_pedido(pedido)

        if metodo == 'put':
            if pedido.get('estado') in ESTADOS_PEDIDO_CERRADOS:
                flash(f"El pedido {nombre} está {pedido['estado']} y no se puede modificar", 'error')
                return redirect(url_for('pedidos'))
            datos, error = _leer_pedido_formulario('Actualizar')
            if error:
                flash(error, 'error')
                return redirect(url_for('pedidos'))
            supabase.table('pedidos').update(datos).eq('id_pedido', pedido['id_pedido']).execute()
            flash(f'Pedido {nombre} actualizado exitosamente', 'success')

        elif metodo == 'anular':
            motivo = (request.form.get('motivoAnulacion') or '').strip()
            if pedido.get('estado') in ESTADOS_PEDIDO_CERRADOS:
                flash(f"El pedido {nombre} ya está {pedido['estado']}: no se puede anular", 'error')
            elif not motivo:
                flash('Indique el motivo de la anulación', 'error')
            elif supabase.table('despachos').select('id_despacho').eq('id_pedido', pedido['id_pedido']) \
                    .eq('estado', 'emitido').limit(1).execute().data:
                flash(f'El pedido {nombre} tiene despachos emitidos: anúlalos primero en Despachos', 'error')
            else:
                supabase.table('pedidos').update({
                    'estado': 'anulado', 'motivo_anulacion': motivo,
                    'fecha_anulacion': datetime.now(timezone.utc).isoformat(),
                    'usuario_anulacion': g.usuario.get('nombre_usuario') or 'Admin',
                }).eq('id_pedido', pedido['id_pedido']).execute()
                facturado = supabase.table('facturas').select('id_factura').eq('pedido_asociado', pedido['id_pedido']) \
                    .neq('estado', 'anulada').limit(1).execute().data
                flash(f'Pedido {nombre} anulado' + ('. Tiene facturas vigentes: emite la nota de crédito '
                                                     'correspondiente.' if facturado else ''), 'success')

        elif metodo == 'delete':
            asociados = [nombre_tabla for nombre_tabla, tabla, columna in (
                ('despachos', 'despachos', 'id_pedido'), ('facturas', 'facturas', 'pedido_asociado'),
                ('cortes', 'cortes', 'id_pedido'))
                if supabase.table(tabla).select(columna).eq(columna, pedido['id_pedido']).limit(1).execute().data]
            if asociados:
                flash(f"El pedido {nombre} tiene {', '.join(asociados)} asociados: no se puede eliminar, solo anular",
                      'error')
                return redirect(url_for('pedidos'))
            supabase.table('detalle_pedidos').delete().eq('id_pedido', pedido['id_pedido']).execute()
            supabase.table('pedidos').delete().eq('id_pedido', pedido['id_pedido']).execute()
            flash(f'Pedido {nombre} borrado exitosamente', 'success')
        return redirect(url_for('pedidos'))

    # select('*'): clientes.id_vendedor existe solo después de incremento4_campos_documento0.sql.
    clientes = supabase.table('clientes').select('*').order('nombre').execute().data or []
    vendedores = supabase.table('vendedores').select('id_vendedor, nombre').order('nombre').execute().data or []
    nombre_cliente = {c['id_cliente']: c.get('nombre') for c in clientes}
    nombre_vendedor = {v['id_vendedor']: v.get('nombre') for v in vendedores}

    # RF-023: filtros por cliente y fecha (y estado).
    filtros = {campo: request.args.get(campo, '').strip() for campo in ('cliente', 'desde', 'hasta', 'estado')}
    query = supabase.table('pedidos').select('*')
    if filtros['desde']:
        query = query.gte('fecha_pedido', filtros['desde'])
    if filtros['hasta']:
        query = query.lte('fecha_pedido', filtros['hasta'])
    if filtros['estado']:
        query = query.eq('estado', filtros['estado'])
    filas = query.order('id_pedido', desc=True).execute().data or []

    # RF-026: monto total de cada pedido = suma de cantidad x precio de sus líneas.
    lineas = supabase.table('detalle_pedidos').select('id_pedido, cantidad, cantidad_anulada, precio_unitario') \
        .in_('id_pedido', [p['id_pedido'] for p in filas]).execute().data if filas else []
    totales, unidades = {}, {}
    for linea in lineas or []:
        cantidad = int(linea.get('cantidad') or 0) - int(linea.get('cantidad_anulada') or 0)
        totales[linea['id_pedido']] = totales.get(linea['id_pedido'], 0) + cantidad * int(linea.get('precio_unitario') or 0)
        unidades[linea['id_pedido']] = unidades.get(linea['id_pedido'], 0) + cantidad

    datos = []
    for pedido in filas:
        cliente = nombre_cliente.get(pedido.get('cliente_asociado'), 'Sin cliente')
        if filtros['cliente'] and filtros['cliente'].lower() not in (cliente or '').lower():
            continue
        datos.append({**pedido, 'cliente': cliente, 'vendedor': nombre_vendedor.get(pedido.get('vendedor_asociado'), ''),
                      'total': totales.get(pedido['id_pedido'], 0), 'unidades': unidades.get(pedido['id_pedido'], 0)})

    return render_template('pedidos.html', datos=datos, filtros=filtros, clientes=clientes, vendedores=vendedores,
                           estados_cerrados=ESTADOS_PEDIDO_CERRADOS)


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
    # RF-029: fecha límite de pago (opcional; no puede ser anterior a la emisión).
    vencimiento = (request.form.get('fechaVencimiento' + sufijo) or '').strip()
    if vencimiento and vencimiento < fecha:
        return None, 'La fecha límite de pago no puede ser anterior a la fecha de emisión.'
    neto = _numero_positivo(request.form.get('montoNeto' + sufijo), permitir_cero=True)
    if neto is None:
        return None, 'El monto neto debe ser un número mayor o igual a cero.'
    # El impuesto sale del porcentaje configurado en Configuración (RF-056).
    impuesto = round(neto * obtener_porcentaje_impuesto() / 100, 2)
    datos = {
        'folio': folio,
        'pedido_asociado': id_pedido,
        # El cliente es el del pedido, para que no puedan quedar distintos.
        'cliente_asociado': pedido[0].get('cliente_asociado'),
        'fecha_emision': fecha,
        'monto_neto': neto,
        'monto_impuesto': impuesto,
        'monto_total': round(neto + impuesto, 2),
    }
    if ('fechaVencimiento' + sufijo) in request.form:
        datos['fecha_vencimiento'] = vencimiento or None
    return datos, None


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


def _leer_linea_formulario(sufijo):
    """Cantidad, precio y observación de una línea de detalle (CU-24.1). Devuelve (datos, error)."""
    cantidad = _entero_positivo(request.form.get('cantidad' + sufijo))
    if cantidad is None:
        return None, 'La cantidad debe ser un número entero mayor que cero.'
    try:
        precio = int(request.form.get('precioUnitario' + sufijo, ''))
        if precio < 0:
            raise ValueError
    except ValueError:
        return None, 'El precio unitario debe ser un número entero mayor o igual a cero.'
    observacion = _texto_o_nulo(request.form.get('observacion' + sufijo))
    if observacion and len(observacion) > 256:
        return None, 'La observación admite hasta 256 caracteres.'
    # Números, no texto: antes el subtotal multiplicaba los valores del formulario como cadenas.
    return {'cantidad': cantidad, 'precio_unitario': precio, 'subtotal': cantidad * precio,
            'observacion': observacion}, None


def _precios_de_lista(lista):
    """Precio mayor de cada variante en una lista de precios distinta de la 1."""
    if lista <= 1:
        return {}
    try:
        return {f['id_variante']: f['precio'] for f in supabase.table('variante_precios_lista').select('*')
                .eq('lista_precios', lista).execute().data or []}
    except APIError:
        return {}  # incremento4_campos_documento0.sql todavía no se ejecuta


def _precio_sugerido(variante, lista, precios_lista):
    """CU-24.1 paso 5: precio según la lista de precios del cliente. Si la variante está
    en liquidación se propone su precio de liquidación (CU-13.5); si no, el de la lista
    del cliente y, si esa lista no tiene precio propio, el precio mayor (lista 1)."""
    if variante.get('en_liquidacion') and variante.get('precio_liquidacion'):
        return variante['precio_liquidacion']
    return precios_lista.get(variante['id_variante'], variante.get('precio_venta') or 0)


@app.route('/crudDetallePedido.html', methods=['GET', 'POST'])
def crudDetallePedido():
    # RF-024/026 y CU-24.1: líneas (producto + color + talla) de un pedido.
    id_pedido = _entero_positivo(request.values.get('id_pedido'))
    pedido = _pedido_o_none(id_pedido)
    if pedido is None:
        flash('Seleccione un pedido para ver su detalle', 'error')
        return redirect(url_for('pedidos'))
    nombre = _nombre_pedido(pedido)

    if request.method == 'POST':
        metodo = request.form.get('_method')
        if pedido.get('estado') in ESTADOS_PEDIDO_CERRADOS:
            flash(f"El pedido {nombre} está {pedido['estado']}: su detalle no se puede modificar", 'error')
            return redirect(url_for('crudDetallePedido', id_pedido=id_pedido))

        if metodo == 'post':
            id_variante = _entero_positivo(request.form.get('idVarianteCrear'))
            variante = supabase.table('producto_variantes').select('id_variante, activo') \
                .eq('id_variante', id_variante).execute().data if id_variante else []
            datos, error = _leer_linea_formulario('Crear')
            if not variante:
                error = 'Seleccione el producto, color y talla de la línea.'
            elif variante[0].get('activo') is False:
                error = 'La variante seleccionada está desactivada.'
            elif supabase.table('detalle_pedidos').select('id_detalle_pedido').eq('id_pedido', id_pedido) \
                    .eq('id_variante', id_variante).execute().data:
                error = 'Esa variante ya está en el pedido: edita su cantidad en la línea existente.'
            if error:
                flash(error, 'error')
            else:
                supabase.table('detalle_pedidos').insert({**datos, 'id_pedido': id_pedido, 'id_variante': id_variante,
                                                          'cantidad_anulada': 0}).execute()
                flash('Línea agregada al pedido', 'success')
            return redirect(url_for('crudDetallePedido', id_pedido=id_pedido))

        id_linea = _entero_positivo(request.form.get('idDetalleActualizar') or request.form.get('idDetalleBorrar'))
        linea = supabase.table('detalle_pedidos').select('*').eq('id_detalle_pedido', id_linea) \
            .eq('id_pedido', id_pedido).execute().data if id_linea else []
        if not linea:
            flash('La línea no existe en este pedido', 'error')
            return redirect(url_for('crudDetallePedido', id_pedido=id_pedido))
        linea = linea[0]
        en_despachos = supabase.table('detalle_despachos').select('cantidad, id_despacho') \
            .eq('id_detalle_pedido', id_linea).execute().data or []
        emitidos = {d['id_despacho'] for d in supabase.table('despachos').select('id_despacho, estado')
                    .in_('id_despacho', [d['id_despacho'] for d in en_despachos]).execute().data or []
                    if d.get('estado') == 'emitido'} if en_despachos else set()
        despachado = sum(int(d.get('cantidad') or 0) for d in en_despachos if d['id_despacho'] in emitidos)

        if metodo == 'put':
            datos, error = _leer_linea_formulario('Actualizar')
            if not error and datos['cantidad'] < despachado + int(linea.get('cantidad_anulada') or 0):
                error = f'Ya se despacharon {despachado} unidades de esta línea: la cantidad no puede ser menor.'
            if error:
                flash(error, 'error')
            else:
                supabase.table('detalle_pedidos').update(datos).eq('id_detalle_pedido', id_linea).execute()
                flash('Línea actualizada', 'success')
        elif metodo == 'delete':
            # Aunque el despacho esté anulado, detalle_despachos referencia la línea.
            if en_despachos:
                flash('La línea tiene despachos registrados: no se puede quitar del pedido', 'error')
            else:
                # Columna correcta: id_detalle_pedido (antes se usaba id_detalle_pedidos).
                supabase.table('detalle_pedidos').delete().eq('id_detalle_pedido', id_linea).execute()
                flash('Línea quitada del pedido', 'success')
        return redirect(url_for('crudDetallePedido', id_pedido=id_pedido))

    lineas = supabase.table('detalle_pedidos').select('*').eq('id_pedido', id_pedido) \
        .order('id_detalle_pedido').execute().data or []
    variantes_activas = supabase.table('producto_variantes').select('*').execute().data or []
    cliente_pedido = supabase.table('clientes').select('*').eq('id_cliente', pedido.get('cliente_asociado')) \
        .execute().data or [{}]
    lista_cliente = int(cliente_pedido[0].get('lista_precios') or 1)
    descripcion = _variantes_por_id({v['id_variante'] for v in variantes_activas} | {l['id_variante'] for l in lineas})
    for linea in lineas:
        linea.update(descripcion.get(linea['id_variante'], {}))
        linea['subtotal'] = int(linea.get('cantidad') or 0) * int(linea.get('precio_unitario') or 0)
    precios_lista = _precios_de_lista(lista_cliente)
    opciones = sorted(
        ({'id_variante': v['id_variante'], 'precio_venta': _precio_sugerido(v, lista_cliente, precios_lista),
          'en_liquidacion': bool(v.get('en_liquidacion')),
          **descripcion.get(v['id_variante'], {})} for v in variantes_activas if v.get('activo') is not False),
        key=lambda v: (str(v.get('producto') or ''), str(v.get('color') or ''), str(v.get('talla') or '')))
    clientes = _obtener_clientes_map()
    return render_template('crudDetallePedido.html', pedido=pedido, nombre=nombre,
                           cliente=clientes.get(pedido.get('cliente_asociado'), 'Sin cliente'),
                           lineas=lineas, variantes=opciones, lista_cliente=lista_cliente,
                           total=sum(l['subtotal'] for l in lineas),
                           editable=pedido.get('estado') not in ESTADOS_PEDIDO_CERRADOS)


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
                # El número de guía lo asigna la base (secuencia despachos_numero_guia_seq).
                guia = supabase.table('despachos').select('numero_guia').eq('id_despacho', id_despacho) \
                    .execute().data if id_despacho else []
                flash(f"Despacho {guia[0]['numero_guia'] if guia else ''} registrado exitosamente".replace('  ', ' '),
                      "success")
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
                        .eq('id_factura', id_factura).eq('pedido_asociado', despacho['id_pedido']) \
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
    facturas = supabase.table('facturas').select('id_factura, folio, pedido_asociado') \
        .neq('estado', 'anulada').not_.is_('pedido_asociado', 'null').execute().data or []

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
                'facturas': [f for f in facturas if f['pedido_asociado'] == id_pedido_nuevo],
            }

    # Listado con filtros.
    query = supabase.table('despachos').select(
        '*, pedidos(numero_pedido, clientes(nombre)), bodegas(descripcion), facturas(folio), '
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
            'folio_factura': (fila.get('facturas') or {}).get('folio'),
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
                '*, pedidos(numero_pedido, clientes(nombre)), bodegas(descripcion), facturas(folio)'
            ).eq('id_despacho', id_ver).execute().data
            if filas:
                pedido = filas[0].get('pedidos') or {}
                despacho = {**filas[0], 'numero_pedido': pedido.get('numero_pedido'),
                            'cliente': (pedido.get('clientes') or {}).get('nombre'),
                            'bodega': (filas[0].get('bodegas') or {}).get('descripcion'),
                            'folio_factura': (filas[0].get('facturas') or {}).get('folio')}
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


def _facturas_pendientes(cliente_id=None):
    """Facturas no anuladas con saldo por cobrar (de un cliente o de todos), por fecha y folio."""
    query = supabase.table('facturas').select(
        'id_factura, folio, cliente_asociado, fecha_emision, monto_total, saldo_pendiente, estado')
    if cliente_id is not None:
        query = query.eq('cliente_asociado', cliente_id)
    try:
        rows = query.execute().data or []
    except Exception:
        rows = []
    pendientes = [{**row, 'monto_total': float(row.get('monto_total') or 0),
                   'saldo_pendiente': float(row.get('saldo_pendiente') or 0)}
                  for row in rows
                  if float(row.get('saldo_pendiente') or 0) > 0 and row.get('estado') != 'anulada']
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


def _leer_pago_formulario(sufijo):
    """Campos del modal de pagos. sufijo '' para crear y '_actualizar' para editar.
    Devuelve (datos, ids de facturas elegidas, error)."""
    cliente_id = _entero_positivo(request.form.get('cliente' + sufijo))
    monto = (request.form.get('monto' + sufijo) or '').strip()
    fecha_pago = (request.form.get('fecha_pago' + sufijo) or '').strip()
    medio_pago = (request.form.get('medio_pago' + sufijo) or '').strip()
    if not cliente_id or not monto or not fecha_pago or not medio_pago:
        return None, [], 'Faltan campos obligatorios: cliente, monto, fecha y medio de pago.'
    monto_valor = _numero_positivo(monto)
    if monto_valor is None:
        return None, [], 'El monto del pago debe ser un número mayor a cero.'
    ids = [int(i) for i in request.form.getlist('facturas' + sufijo) if str(i).isdigit()]
    if not ids:
        return None, [], 'Debes seleccionar al menos una factura pendiente para aplicar el pago.'
    return {'cliente_asociado': cliente_id, 'fecha_pago': fecha_pago, 'monto': monto_valor,
            'medio_pago': medio_pago, 'referencia': _texto_o_nulo(request.form.get('referencia' + sufijo))}, ids, None


def _aplicar_pago(pago_id, cliente_id, monto, ids_facturas):
    """Reparte el monto entre las facturas elegidas (en ese orden, hasta su saldo),
    guarda pago_facturas y recalcula cada factura. Devuelve el saldo a favor que sobra.
    Lanza ValueError si alguna factura no es del cliente o no tiene saldo."""
    facturas = {f['id_factura']: f for f in _facturas_pendientes(cliente_id)}
    elegidas = [facturas[i] for i in ids_facturas if i in facturas]
    if len(elegidas) != len(ids_facturas):
        raise ValueError('Las facturas elegidas deben ser del cliente del pago y tener saldo pendiente.')
    restante = monto
    for factura in elegidas:
        asignado = round(min(factura['saldo_pendiente'], restante), 2)
        if asignado <= 0:
            continue
        supabase.table('pago_facturas').insert({'id_pago': pago_id, 'id_factura': factura['id_factura'],
                                                'monto_aplicado': asignado}).execute()
        _recalcular_factura(factura['id_factura'])
        restante = round(restante - asignado, 2)
    return restante


def _facturas_del_pago(pago_id):
    return supabase.table('pago_facturas').select('id_factura, monto_aplicado').eq('id_pago', pago_id).execute().data or []


@app.route('/pagos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def pagos():
    # RF-032/033/034. Esquema de supabase/pagos.sql: el folio es identity (lo asigna la
    # base) y cada pago se reparte entre facturas en pago_facturas. Al registrar,
    # editar o anular, las facturas tocadas se recalculan con _recalcular_factura()
    # (saldo_pendiente y estado vía _estado_para_saldo()).
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if not _pago_facturas_disponible():
            flash('La tabla de detalle de pagos (pago_facturas) aún no está creada en la base de datos.', 'error')
            return redirect(url_for('pagos'))

        if metodo == 'post':
            datos, ids, error = _leer_pago_formulario('')
            if error:
                flash(error, 'error')
                return redirect(url_for('pagos'))
            pendientes = {f['id_factura'] for f in _facturas_pendientes(datos['cliente_asociado'])}
            if not pendientes:
                flash('El cliente no tiene facturas con saldo pendiente.', 'error')
                return redirect(url_for('pagos'))
            # Se valida antes de insertar para no gastar un folio (identity) en un pago rechazado.
            if not set(ids) <= pendientes:
                flash('Las facturas elegidas deben ser del cliente del pago y tener saldo pendiente.', 'error')
                return redirect(url_for('pagos'))
            try:
                creado = supabase.table('pagos').insert({
                    **datos, 'estado': 'vigente', 'usuario_creacion': g.usuario.get('nombre_usuario') or 'Admin',
                }).execute().data
            except APIError:
                creado = None
            if not creado:
                flash('No se pudo registrar el pago.', 'error')
                return redirect(url_for('pagos'))
            pago = creado[0]
            try:
                sobrante = _aplicar_pago(pago['id_pago'], datos['cliente_asociado'], datos['monto'], ids)
            except ValueError as error:
                supabase.table('pagos').delete().eq('id_pago', pago['id_pago']).execute()
                flash(str(error), 'error')
                return redirect(url_for('pagos'))
            flash(f"Pago N° {pago.get('folio') or pago['id_pago']} registrado exitosamente.", 'success')
            if sobrante > 0:
                flash(f'Quedó un saldo a favor del cliente de {formatear_moneda(sobrante)}.', 'warning')
            return redirect(url_for('pagos'))

        pago_id = _entero_positivo(request.form.get('id_pago_actualizar') or request.form.get('id_pago_anular'))
        actual = supabase.table('pagos').select('*').eq('id_pago', pago_id).execute().data if pago_id else []
        if not actual:
            flash('No existe el pago seleccionado.', 'error')
            return redirect(url_for('pagos'))
        actual = actual[0]
        numero = actual.get('folio') or actual['id_pago']
        if (actual.get('estado') or '').lower() == 'anulada':
            flash(f'El pago N° {numero} está anulado y no se puede modificar.', 'error')
            return redirect(url_for('pagos'))

        if metodo == 'put':
            datos, ids, error = _leer_pago_formulario('_actualizar')
            if error:
                flash(error, 'error')
                return redirect(url_for('pagos'))
            anteriores = _facturas_del_pago(pago_id)
            # Se quita la aplicación anterior, se recalculan esas facturas y se vuelve a repartir.
            supabase.table('pago_facturas').delete().eq('id_pago', pago_id).execute()
            for detalle in anteriores:
                _recalcular_factura(detalle['id_factura'])
            try:
                sobrante = _aplicar_pago(pago_id, datos['cliente_asociado'], datos['monto'], ids)
            except ValueError as error:
                for detalle in anteriores:  # se restaura la aplicación anterior
                    supabase.table('pago_facturas').insert({'id_pago': pago_id, **detalle}).execute()
                    _recalcular_factura(detalle['id_factura'])
                flash(str(error), 'error')
                return redirect(url_for('pagos'))
            supabase.table('pagos').update(datos).eq('id_pago', pago_id).execute()
            flash(f'Pago N° {numero} actualizado exitosamente.', 'success')
            if sobrante > 0:
                flash(f'Quedó un saldo a favor del cliente de {formatear_moneda(sobrante)}.', 'warning')

        elif metodo == 'delete':
            motivo = (request.form.get('motivo_anulacion') or '').strip()
            if not motivo:
                flash('Debes indicar el motivo de anulación.', 'error')
                return redirect(url_for('pagos'))
            supabase.table('pagos').update({'estado': 'anulada', 'motivo_anulacion': motivo}) \
                .eq('id_pago', pago_id).execute()
            # Las filas de pago_facturas quedan como historial; un pago anulado ya no cuenta en el saldo.
            for detalle in _facturas_del_pago(pago_id):
                _recalcular_factura(detalle['id_factura'])
            flash(f'Pago N° {numero} anulado: su monto volvió al saldo de las facturas.', 'success')
        return redirect(url_for('pagos'))

    cliente_filter = (request.args.get('cliente') or '').strip()
    fecha_desde = (request.args.get('fecha_desde') or '').strip()
    fecha_hasta = (request.args.get('fecha_hasta') or '').strip()
    referencia_filter = (request.args.get('referencia') or '').strip()

    try:
        pagos_rows = supabase.table('pagos').select('*').execute().data or []
    except Exception:
        flash('No se pudo cargar el listado de pagos.', 'error')
        pagos_rows = []

    clientes_map = _obtener_clientes_map()
    facturas_rows = supabase.table('facturas').select('id_factura, folio, saldo_pendiente').execute().data or []
    folio_factura = {f['id_factura']: f.get('folio') for f in facturas_rows}
    aplicaciones = supabase.table('pago_facturas').select('id_pago, id_factura, monto_aplicado').execute().data \
        if _pago_facturas_disponible() else []
    por_pago = {}
    for aplicacion in aplicaciones or []:
        por_pago.setdefault(aplicacion['id_pago'], []).append({
            'id_factura': aplicacion['id_factura'], 'folio': folio_factura.get(aplicacion['id_factura']),
            'monto_aplicado': float(aplicacion.get('monto_aplicado') or 0)})

    datos = []
    for pago in pagos_rows:
        cliente_id = pago.get('cliente_asociado')
        cliente_nombre = clientes_map.get(int(cliente_id), 'Sin cliente') if cliente_id is not None else 'Sin cliente'
        fecha_pago = pago.get('fecha_pago') or ''
        if cliente_filter and cliente_filter.lower() not in cliente_nombre.lower():
            continue
        if fecha_desde and fecha_pago < fecha_desde:
            continue
        if fecha_hasta and fecha_pago > fecha_hasta:
            continue
        if referencia_filter and referencia_filter.lower() not in (pago.get('referencia') or '').lower():
            continue
        datos.append({
            'id_pago': pago.get('id_pago'), 'folio': pago.get('folio'), 'cliente': cliente_nombre,
            'cliente_id': cliente_id, 'fecha_pago': fecha_pago, 'monto': float(pago.get('monto') or 0),
            'medio_pago': pago.get('medio_pago'), 'referencia': pago.get('referencia'),
            'estado': pago.get('estado') or 'vigente', 'motivo_anulacion': pago.get('motivo_anulacion'),
            'detalle_facturas': por_pago.get(pago.get('id_pago'), []),
        })
    datos.sort(key=lambda p: p.get('folio') or 0, reverse=True)

    if request.args and not datos:
        flash('No se encontraron pagos para los filtros aplicados.', 'warning')

    clientes = supabase.table('clientes').select('id_cliente, nombre').order('nombre').execute().data or []
    return render_template(
        'pagos.html',
        datos=datos,
        clientes=clientes,
        # Todas las facturas con saldo; el modal muestra solo las del cliente elegido.
        facturas=_facturas_pendientes(),
        cliente_filter=cliente_filter,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        referencia_filter=referencia_filter,
    )



def obtener_informe_cobranza(request_args):
    """RF-031 / CU-31: facturas con saldo pendiente, con el esquema de facturas.sql y pagos.sql.

    Pagos aplicados = pago_facturas.monto_aplicado de pagos no anulados; notas = notas de
    crédito vigentes. El saldo es facturas.saldo_pendiente, que la app recalcula en cada
    pago o nota (monto_total - pagos - notas)."""
    cliente_filter = (request_args.get('cliente') or '').strip()
    fecha_desde = (request_args.get('fecha_desde') or '').strip()
    fecha_hasta = (request_args.get('fecha_hasta') or '').strip()
    dias_min_raw = (request_args.get('dias_morosidad_min') or '').strip()

    try:
        dias_min = int(dias_min_raw) if dias_min_raw else None
    except ValueError:
        dias_min = None

    # select('*'): fecha_vencimiento existe solo después de incremento4_campos_documento0.sql.
    facturas = supabase.table('facturas').select('*').gt('saldo_pendiente', 0).neq('estado', 'anulada').execute().data or []
    clientes = _obtener_clientes_map()

    ids_factura = [f['id_factura'] for f in facturas]
    aplicaciones = supabase.table('pago_facturas').select('id_pago, id_factura, monto_aplicado') \
        .in_('id_factura', ids_factura).execute().data if ids_factura else []
    ids_pago = list({a['id_pago'] for a in aplicaciones or []})
    pagos_vigentes = {p['id_pago'] for p in supabase.table('pagos').select('id_pago, estado')
                      .in_('id_pago', ids_pago).execute().data or []
                      if (p.get('estado') or 'vigente') != 'anulada'} if ids_pago else set()
    pagos_por_factura = {}
    for aplicacion in aplicaciones or []:
        if aplicacion['id_pago'] in pagos_vigentes:
            pagos_por_factura[aplicacion['id_factura']] = (pagos_por_factura.get(aplicacion['id_factura'], 0.0)
                                                          + float(aplicacion.get('monto_aplicado') or 0))
    notas_por_factura = {}
    for nota in (supabase.table('notas_credito').select('factura_referencia, monto_total, estado')
                 .in_('factura_referencia', ids_factura).execute().data if ids_factura else []) or []:
        if (nota.get('estado') or 'vigente') == 'vigente':
            notas_por_factura[nota['factura_referencia']] = (notas_por_factura.get(nota['factura_referencia'], 0.0)
                                                            + float(nota.get('monto_total') or 0))

    rows = []
    hoy = datetime.now(timezone.utc).date()
    for factura in facturas:
        cliente_id = factura.get('cliente_asociado')
        cliente_nombre = clientes.get(cliente_id, 'Sin cliente') if cliente_id is not None else 'Sin cliente'
        if cliente_filter and cliente_filter.lower() not in cliente_nombre.lower():
            continue

        fecha_factura = (factura.get('fecha_emision') or '').strip()
        if fecha_desde and fecha_factura < fecha_desde:
            continue
        if fecha_hasta and fecha_factura > fecha_hasta:
            continue

        # RF-029: la mora se cuenta desde la fecha límite de pago; si la factura no
        # la tiene, desde la emisión (como antes). Antes del vencimiento es 0.
        vencimiento = (factura.get('fecha_vencimiento') or '').strip()
        dias_morosidad = 0
        if vencimiento or fecha_factura:
            try:
                desde = datetime.strptime((vencimiento or fecha_factura)[:10], '%Y-%m-%d').date()
                dias_morosidad = max((hoy - desde).days, 0)
            except ValueError:
                dias_morosidad = 0
        if dias_min is not None and dias_morosidad < dias_min:
            continue

        factura_id = factura.get('id_factura')
        rows.append({
            'id_factura': factura_id,
            'cliente': cliente_nombre,
            'folio': factura.get('folio'),
            'fecha': fecha_factura,
            'vencimiento': vencimiento,
            'monto': float(factura.get('monto_total') or 0),
            'pagos_aplicados': pagos_por_factura.get(factura_id, 0.0),
            'notas_credito': notas_por_factura.get(factura_id, 0.0),
            'saldo': float(factura.get('saldo_pendiente') or 0),
            'dias_morosidad': dias_morosidad,
        })

    return sorted(rows, key=lambda item: ((item.get('cliente') or '').lower(), -item['dias_morosidad']))


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
        generated = Paragraph(f'Generado: {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")}', styles['BodyText'])

        table_data = [[
            'Cliente', 'Folio', 'Fecha emisión', 'Vencimiento', 'Monto', 'Pagos aplicados', 'Notas de crédito',
            'Saldo', 'Días de mora'
        ]]
        for row in rows:
            table_data.append([
                row.get('cliente') or 'Sin cliente',
                str(row.get('folio') or ''),
                formatear_fecha(row.get('fecha')),
                formatear_fecha(row.get('vencimiento')) if row.get('vencimiento') else '-',
                formatear_moneda(row.get('monto', 0)),
                formatear_moneda(row.get('pagos_aplicados', 0)),
                formatear_moneda(row.get('notas_credito', 0)),
                formatear_moneda(row.get('saldo', 0)),
                str(row.get('dias_morosidad', 0)),
            ])
        table_data.append(['Total', '', '', '', '', '', '',
                           formatear_moneda(sum(r.get('saldo', 0) for r in rows)), ''])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf4ef')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.7, colors.grey),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
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

def digito_verificador_rut(numero):
    """Dígito verificador de un RUT chileno (módulo 11): '0'-'9' o 'K'."""
    suma, factor = 0, 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: '0', 10: 'K'}.get(resto, str(resto))


def _porcentaje(valor, nombre, obligatorio=False):
    """Porcentaje 0-100 con dos decimales (formato llll/mmmm/nnnn del Documento 0)."""
    texto = (valor or '').strip().replace(',', '.')
    if not texto:
        return (0 if obligatorio else None), None
    try:
        numero = round(float(texto), 2)
    except ValueError:
        return None, f'{nombre} debe ser un número entre 0 y 100.'
    if not 0 <= numero <= 100:
        return None, f'{nombre} debe estar entre 0 y 100.'
    return numero, None


def _leer_cliente_formulario(sufijo, id_cliente=None):
    """Valida el modal de clientes (RF-001, CU-01.1 y CU-01.5). Devuelve (datos, error)."""
    form = lambda campo: request.form.get(campo + sufijo)
    nombre = (form('nombre') or '').strip()
    if not nombre:
        return None, 'El nombre del cliente es obligatorio.'
    rut = re.sub(r'[.\s-]', '', form('rut') or '')
    dv = (form('digVer') or '').strip().upper()
    if not rut.isdigit():
        return None, 'El RUT debe tener solo números (sin puntos ni dígito verificador).'
    if not re.fullmatch(r'[0-9K]', dv):
        return None, 'El dígito verificador debe ser un número del 0 al 9 o la letra K.'
    if digito_verificador_rut(rut) != dv:
        return None, f'El RUT {rut}-{dv} no es válido: el dígito verificador no coincide.'
    repetidos = supabase.table('clientes').select('id_cliente').eq('rut', rut).execute().data or []
    if any(str(c['id_cliente']) != str(id_cliente) for c in repetidos):
        return None, f'Ya existe un cliente con el RUT {rut}-{dv}.'
    codigo = _texto_o_nulo(form('codigo'))
    if codigo:
        mismos = supabase.table('clientes').select('id_cliente').eq('codigo', codigo).execute().data or []
        if any(str(c['id_cliente']) != str(id_cliente) for c in mismos):
            return None, f'Ya existe un cliente con el código {codigo}.'
    datos = {
        'codigo': codigo, 'rut': rut, 'digito_verificador': dv, 'nombre': nombre,
        'abreviacion': _texto_o_nulo(form('abreviacion')), 'correo': _texto_o_nulo(form('correo')),
        'telefono': _texto_o_nulo(form('telefono')), 'direccion': _texto_o_nulo(form('direccion')),
        'comuna': _texto_o_nulo(form('comuna')), 'ciudad': _texto_o_nulo(form('ciudad')),
        'condiciones_venta': _texto_o_nulo(form('condicionesVenta')),
        'via_despacho': _texto_o_nulo(form('viaDespacho')),
        'observaciones': _texto_o_nulo(form('observaciones')),
        'id_zona_venta': _entero_positivo(form('idZonaVenta')),
        'giro': _texto_o_nulo(form('giro')),
        'telefono_2': _texto_o_nulo(form('telefono2')),
        'id_vendedor': _entero_positivo(form('idVendedor')),
    }
    if datos['observaciones'] and len(datos['observaciones']) > 256:
        return None, 'Las observaciones admiten hasta 256 caracteres.'
    lista = (form('listaPrecios') or '1').strip()
    if not lista.isdigit() or int(lista) < 1:
        return None, 'El número de lista de precios debe ser un entero mayor o igual a 1.'
    datos['lista_precios'] = int(lista)
    # CU-01.1 excepción 4: el vendedor asociado debe existir.
    if datos['id_vendedor'] and not supabase.table('vendedores').select('id_vendedor') \
            .eq('id_vendedor', datos['id_vendedor']).execute().data:
        return None, 'El vendedor seleccionado no está registrado.'
    for campo, etiqueta, columna, obligatorio in (
            ('descuento1', 'El descuento 1', 'descuento_1', True),
            ('descuento2', 'El descuento 2', 'descuento_2', True),
            ('descuento3', 'El descuento 3', 'descuento_3', True),
            ('porComision', 'El porcentaje de comisión', 'porcentaje_comision', False),
            ('porCobranza', 'El porcentaje de cobranza', 'porcentaje_cobranza', False)):
        valor, error = _porcentaje(form(campo), etiqueta, obligatorio)
        if error:
            return None, error
        datos[columna] = valor
    return datos, None


@app.route('/clientes.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def clientes():
    # RF-001/002, CU-01.1 a CU-01.5 y CU-02. Mismo patrón que colores: _method
    # post/put/delete, modales crear/actualizar/borrar y avisos con flash.
    zonas = supabase.table("zona_venta").select("id_zona_venta, nombre, descripcion").execute().data or []
    vendedores = supabase.table("vendedores").select("id_vendedor, nombre, codigo").order("nombre").execute().data or []
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == "post":
            datos, error = _leer_cliente_formulario('Crear')
            if error:
                flash(error, "error")
            elif supabase.table("clientes").insert(datos).execute().data:
                flash(f"Cliente {datos['nombre']} creado exitosamente", "success")
            else:
                flash("Error creando cliente", "error")
            return redirect(url_for('clientes'))
        if metodo in ("put", "delete"):
            id_cliente = _entero_positivo(request.form.get('idClienteActualizar') or request.form.get('idClienteBorrar'))
            actual = supabase.table("clientes").select("id_cliente, nombre").eq("id_cliente", id_cliente) \
                .execute().data if id_cliente else []
            if not actual:
                flash("El cliente no existe", "error")
                return redirect(url_for('clientes'))
            if metodo == "put":
                datos, error = _leer_cliente_formulario('Actualizar', id_cliente)
                if error:
                    flash(error, "error")
                else:
                    supabase.table("clientes").update(datos).eq("id_cliente", id_cliente).execute()
                    flash(f"Cliente {datos['nombre']} actualizado exitosamente", "success")
            else:
                # CU-01.4 excepción 2: no se elimina un cliente con pedidos, facturas o pagos.
                asociados = [texto for texto, tabla, columna in (
                    ('pedidos', 'pedidos', 'cliente_asociado'), ('facturas', 'facturas', 'cliente_asociado'),
                    ('pagos', 'pagos', 'cliente_asociado'))
                    if supabase.table(tabla).select(columna).eq(columna, id_cliente).limit(1).execute().data]
                if asociados:
                    flash(f"El cliente {actual[0]['nombre']} tiene {', '.join(asociados)} asociados y no se puede eliminar",
                          "error")
                else:
                    supabase.table("clientes").delete().eq("id_cliente", id_cliente).execute()
                    flash(f"Cliente {actual[0]['nombre']} borrado exitosamente", "success")
            return redirect(url_for('clientes'))
        # Búsquedas antiguas por función de la base (se mantienen por compatibilidad).
        busquedas = {'buscarID': ('buscarclienteid', 'idBuscar'), 'buscarNombre': ('buscarclientenombre', 'nombreBuscar'),
                     'buscarAbreviacion': ('buscarclienteabreviacion', 'abreviacionBuscar')}
        if metodo in busquedas:
            funcion, campo = busquedas[metodo]
            datos = supabase.rpc(funcion, {'textobusqueda': request.form.get(campo, '')}).execute().data or []
            if not datos:
                flash("No se encontraron clientes con ese criterio", "warning")
            return render_template('clientes.html', datos=datos, zonasVenta=zonas, vendedores=vendedores, busqueda='')
        return redirect(url_for('clientes'))

    # RF-002 / CU-02: barra de búsqueda por nombre (también busca en RUT y abreviación).
    busqueda = request.args.get('q', '').strip()
    datos = supabase.table("clientes").select("*").order("nombre").execute().data or []
    if busqueda:
        texto = busqueda.lower()
        datos = [c for c in datos if texto in ' '.join(str(c.get(k) or '') for k in ('nombre', 'rut', 'abreviacion', 'codigo')).lower()]
    return render_template('clientes.html', datos=datos, zonasVenta=zonas, vendedores=vendedores, busqueda=busqueda)


@app.route('/colores.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def colores():
    # RF-003/004, CU-03.1 a CU-03.4.
    return _crud_maestro('colores')


def _cantidad_inventario(valor, etiqueta):
    texto = (valor or '').strip()
    if not texto:
        return 0, None
    if not texto.isdigit():
        return None, f'{etiqueta} debe ser un número entero mayor o igual a cero.'
    return int(texto), None


def _inventario_de_bodega(bodegas):
    """Existencias de la bodega elegida (?bodega=, por defecto la primera) con nombres
    de producto, talla y color. Talla y color salen de las columnas de inventario."""
    id_bodega = _entero_positivo(request.args.get('bodega'))
    if id_bodega is None and bodegas:
        id_bodega = bodegas[0]['id_bodega']
    try:
        filas = supabase.table('inventario').select('*').eq('id_bodega', id_bodega).execute().data or [] \
            if id_bodega else []
        disponible = True
    except APIError as error:
        if 'PGRST205' not in str(error):
            raise
        filas, disponible = [], False
    tallas = {t['id_talla']: t.get('nombre') or str(t.get('talla'))
              for t in supabase.table('tallas').select('id_talla, talla, nombre').execute().data or []}
    colores = {c['id_color']: c.get('descripcion')
               for c in supabase.table('colores').select('id_color, descripcion').execute().data or []}
    variantes = supabase.table('producto_variantes').select('id_variante, activo').execute().data or []
    descripcion = _variantes_por_id({v['id_variante'] for v in variantes} | {f.get('id_variante') for f in filas} - {None})
    for fila in filas:
        fila['producto'] = descripcion.get(fila.get('id_variante'), {}).get('producto') or f"Variante {fila.get('id_variante')}"
        fila['talla'] = tallas.get(fila.get('id_talla'), '')
        fila['color'] = colores.get(fila.get('id_color'), '')
    filas.sort(key=lambda f: (str(f['producto']), str(f['color']), str(f['talla'])))
    opciones = sorted(({'id_variante': v['id_variante'], **descripcion.get(v['id_variante'], {})}
                       for v in variantes if v.get('activo') is not False),
                      key=lambda v: (str(v.get('producto') or ''), str(v.get('color') or ''), str(v.get('talla') or '')))
    return {'inventario': filas, 'inventario_disponible': disponible, 'bodega_actual': id_bodega,
            'variantes': opciones,
            'total_unidades': sum(int(f.get('cantidad') or 0) for f in filas),
            'total_defectuosas': sum(int(f.get('cantidad_defectuosa') or 0) for f in filas)}


@app.route('/bodegas.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def bodegas():
    # RF-005/006 (CU-05.1 a 05.4) con el CRUD de maestros simples, y RF-037: inventario
    # de la bodega elegida (tabla inventario: id_bodega, id_variante, id_talla, id_color,
    # cantidad, cantidad_defectuosa).
    if request.method == 'POST' and (request.form.get('_method') or '').startswith('inventario_'):
        metodo = request.form['_method']
        usuario = g.usuario.get('nombre_usuario') or 'Admin'
        id_bodega = _entero_positivo(request.form.get('idBodegaInventario'))
        volver = redirect(url_for('bodegas', bodega=id_bodega) if id_bodega else url_for('bodegas'))
        cantidad, error = _cantidad_inventario(request.form.get('cantidadInventario'), 'La cantidad')
        defectuosa, error_def = _cantidad_inventario(request.form.get('cantidadDefectuosaInventario'),
                                                     'La cantidad defectuosa')
        if metodo == 'inventario_post':
            id_variante = _entero_positivo(request.form.get('idVarianteInventario'))
            variante = supabase.table('producto_variantes').select('id_variante, id_talla, id_color') \
                .eq('id_variante', id_variante).execute().data if id_variante else []
            if not id_bodega or not variante:
                error = 'Seleccione la bodega y el producto (color y talla).'
            elif supabase.table('inventario').select('id_inventario').eq('id_bodega', id_bodega) \
                    .eq('id_variante', id_variante).execute().data:
                error = 'Ese producto ya tiene existencias en la bodega: edita su fila.'
            if error or error_def:
                flash(error or error_def, 'error')
                return volver
            # Talla y color se toman de la variante, para que coincidan con ella.
            supabase.table('inventario').insert({
                'id_bodega': id_bodega, 'id_variante': id_variante, 'id_talla': variante[0].get('id_talla'),
                'id_color': variante[0].get('id_color'), 'cantidad': cantidad, 'cantidad_defectuosa': defectuosa,
                'usuario_actualizacion': usuario,
            }).execute()
            flash('Existencias registradas en la bodega', 'success')
            return volver
        id_inventario = _entero_positivo(request.form.get('idInventario'))
        fila = supabase.table('inventario').select('id_inventario, id_bodega').eq('id_inventario', id_inventario) \
            .execute().data if id_inventario else []
        if not fila:
            flash('El registro de inventario no existe', 'error')
            return volver
        volver = redirect(url_for('bodegas', bodega=fila[0]['id_bodega']))
        if metodo == 'inventario_put':
            if error or error_def:
                flash(error or error_def, 'error')
                return volver
            supabase.table('inventario').update({'cantidad': cantidad, 'cantidad_defectuosa': defectuosa,
                                                 'usuario_actualizacion': usuario}) \
                .eq('id_inventario', id_inventario).execute()
            flash('Existencias actualizadas', 'success')
        elif metodo == 'inventario_delete':
            supabase.table('inventario').delete().eq('id_inventario', id_inventario).execute()
            flash('Registro de inventario borrado', 'success')
        return volver
    return _crud_maestro('bodegas', contexto=_inventario_de_bodega)


@app.route('/vendedores.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def vendedores():
    # RF-007/008, CU-07.1 a CU-07.4.
    return _crud_maestro('vendedores')


def _validar_rut_vendedor(datos):
    # CU-07.1 excepción 1: RUT con dígito verificador correcto (módulo 11).
    if datos.get('digito_verificador') and digito_verificador_rut(datos['rut']) != datos['digito_verificador']:
        return f"El RUT {datos['rut']}-{datos['digito_verificador']} no es válido: el dígito verificador no coincide."
    return None


MAESTROS_SIMPLES = {
    'colores': {
        'tabla': 'colores', 'clave': 'id_color', 'endpoint': 'colores', 'modulo': 'colores',
        'plantilla': 'colores.html', 'singular': 'color', 'plural': 'colores', 'articulo': 'el',
        'id_form': 'idColor', 'principal': 'descripcion',
        'campos': [
            {'columna': 'descripcion', 'form': 'descripcion', 'etiqueta': 'Descripción', 'obligatorio': True, 'max': 32},
            {'columna': 'codigo_color', 'form': 'codigo', 'etiqueta': 'Código de color', 'max': 8, 'unico': True,
             'ayuda': 'Hasta 8 caracteres (glosario dddd)'},
            {'columna': 'codigo_ean', 'form': 'codigoEan', 'etiqueta': 'Código EAN del color', 'max': 4,
             'numerico': True, 'ean_parte': 'color', 'ayuda': 'Solo números, hasta 4 dígitos (ej. 0001); único'},
        ],
        'en_uso': [('producto_variantes', 'id_color', 'variantes de producto'), ('productos', 'color', 'productos'),
                   ('inventario', 'id_color', 'inventario')],
    },
    'vendedores': {
        'tabla': 'vendedores', 'clave': 'id_vendedor', 'endpoint': 'vendedores', 'modulo': 'vendedores',
        'plantilla': 'vendedores.html', 'singular': 'vendedor', 'plural': 'vendedores', 'articulo': 'el',
        'id_form': 'idVendedor', 'principal': 'nombre', 'validar': _validar_rut_vendedor,
        'campos': [
            {'columna': 'nombre', 'form': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True, 'max': 64},
            {'columna': 'codigo', 'form': 'codigo', 'etiqueta': 'Código de vendedor', 'max': 3, 'unico': True,
             'ayuda': 'Hasta 3 caracteres (glosario ffff)'},
            {'columna': 'rut', 'form': 'rut', 'etiqueta': 'RUT', 'obligatorio': True, 'max': 9, 'numerico': True,
             'rut': True, 'unico': True, 'ayuda': 'Sin puntos ni dígito verificador'},
            {'columna': 'digito_verificador', 'form': 'digVer', 'etiqueta': 'Dígito verificador', 'obligatorio': True,
             'max': 1, 'mayusculas': True},
            {'columna': 'porcentaje_comision', 'form': 'porComi', 'etiqueta': 'Comisión', 'porcentaje': True},
        ],
        'en_uso': [('pedidos', 'vendedor_asociado', 'pedidos')],
    },
    'tallas': {
        'tabla': 'tallas', 'clave': 'id_talla', 'endpoint': 'tallas', 'modulo': 'tallas',
        'plantilla': 'tallas.html', 'singular': 'talla', 'plural': 'tallas', 'articulo': 'la',
        'id_form': 'idTalla', 'principal': 'talla',
        'campos': [
            {'columna': 'talla', 'form': 'talla', 'etiqueta': 'Código de talla', 'obligatorio': True, 'max': 2,
             'unico': True, 'ayuda': 'Hasta 2 caracteres, por ejemplo S, M, 38'},
            {'columna': 'nombre', 'form': 'nombre', 'etiqueta': 'Nombre en la etiqueta', 'max': 16,
             'ayuda': 'Lo que se imprime en la etiqueta EAN (S, M, L, 38...)'},
            {'columna': 'codigo_ean', 'form': 'codigoEan', 'etiqueta': 'Código EAN de la talla', 'max': 3,
             'numerico': True, 'ean_parte': 'talla', 'ayuda': 'Solo números, hasta 3 dígitos (ej. 010); único'},
        ],
        'en_uso': [('producto_variantes', 'id_talla', 'variantes de producto'), ('productos', 'talla', 'productos'),
                   ('inventario', 'id_talla', 'inventario')],
    },
    'zonas_venta': {
        'tabla': 'zona_venta', 'clave': 'id_zona_venta', 'endpoint': 'zonasVenta', 'modulo': 'zonas_venta',
        'plantilla': 'zonasVenta.html', 'singular': 'zona de venta', 'plural': 'zonas de venta', 'articulo': 'la',
        'id_form': 'idZonaVenta', 'principal': 'nombre',
        'campos': [
            {'columna': 'nombre', 'form': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True, 'max': 64},
            {'columna': 'codigo', 'form': 'codigo', 'etiqueta': 'Código', 'max': 3, 'unico': True,
             'ayuda': 'Hasta 3 caracteres (glosario gggg)'},
            {'columna': 'descripcion', 'form': 'descripcion', 'etiqueta': 'Descripción', 'obligatorio': True, 'max': 64,
             'ayuda': 'Regiones o comunas que abarca'},
        ],
        'en_uso': [('clientes', 'id_zona_venta', 'clientes')],
    },
    'bodegas': {
        'tabla': 'bodegas', 'clave': 'id_bodega', 'endpoint': 'bodegas', 'modulo': 'bodegas',
        'plantilla': 'bodegas.html', 'singular': 'bodega', 'plural': 'bodegas', 'articulo': 'la',
        'id_form': 'idBodega', 'principal': 'descripcion',
        'campos': [
            {'columna': 'descripcion', 'form': 'descripcion', 'etiqueta': 'Descripción', 'obligatorio': True, 'max': 64},
            {'columna': 'codigo', 'form': 'codigo', 'etiqueta': 'Código de bodega', 'max': 16, 'unico': True},
        ],
        # CU-05.4 excepción 1: no se elimina una bodega con stock (ni con despachos).
        'en_uso': [('inventario', 'id_bodega', 'inventario'), ('despachos', 'id_bodega', 'despachos')],
    },
}


def _digitos_ean(parte):
    """Largo máximo del código EAN de un maestro ('producto', 'color' o 'talla'), según el
    formato configurado en parametros_sistema (incremento3_ean.sql: 3, 4 y 3 por defecto)."""
    defecto = {'producto': 3, 'color': 4, 'talla': 3}[parte]
    try:
        return int(obtener_parametros_sistema().get(f'ean_digitos_{parte}') or defecto)
    except (APIError, TypeError, ValueError):
        return defecto


def _validar_codigo_ean_maestro(tabla, clave, parte, codigo, id_registro=None):
    """Código EAN de producto, color o talla: solo números, largo del formato y único en su
    maestro; si dos registros comparten código, sus variantes tendrían el mismo EAN (CU-15.5)."""
    if not codigo.isdigit():
        return 'El código EAN solo puede tener números.'
    largo = _digitos_ean(parte)
    if len(codigo) > largo:
        return f'El código EAN del {parte} admite hasta {largo} dígitos.'
    mismos = supabase.table(tabla).select(clave).eq('codigo_ean', codigo).execute().data or []
    if any(str(f[clave]) != str(id_registro) for f in mismos):
        otro = 'otra' if parte == 'talla' else 'otro'
        return f'Ya hay {otro} {parte} con el código EAN {codigo}: sus variantes tendrían el mismo código de barras.'
    return None


def _leer_maestro_formulario(maestro, sufijo, id_registro=None):
    """Valida los campos de un maestro simple. Devuelve (datos, error)."""
    datos = {}
    for campo in maestro['campos']:
        valor = (request.form.get(campo['form'] + sufijo) or '').strip()
        if campo.get('rut'):
            valor = re.sub(r'[.\s-]', '', valor)
        if campo.get('mayusculas'):
            valor = valor.upper()
        etiqueta = campo['etiqueta']
        if not valor:
            if campo.get('obligatorio'):
                return None, f'Complete el campo «{etiqueta}».'
            datos[campo['columna']] = None
            continue
        if campo.get('ean_parte'):
            error = _validar_codigo_ean_maestro(maestro['tabla'], maestro['clave'], campo['ean_parte'], valor, id_registro)
            if error:
                return None, error
            datos[campo['columna']] = valor
            continue
        if campo.get('max') and len(valor) > campo['max']:
            return None, f'«{etiqueta}» admite hasta {campo["max"]} caracteres.'
        if campo.get('numerico') and not valor.isdigit():
            return None, f'«{etiqueta}» solo puede tener números.'
        if campo.get('porcentaje'):
            valor, error = _porcentaje(valor, f'«{etiqueta}»')
            if error:
                return None, error
        if campo.get('unico'):
            mismos = supabase.table(maestro['tabla']).select(maestro['clave']) \
                .eq(campo['columna'], valor).execute().data or []
            if any(str(f[maestro['clave']]) != str(id_registro) for f in mismos):
                return None, f'Ya existe {maestro["articulo"]} {maestro["singular"]} con {etiqueta.lower()} {valor}.'
        datos[campo['columna']] = valor
    if maestro.get('validar'):
        error = maestro['validar'](datos)
        if error:
            return None, error
    return datos, None


def _mensaje_error_maestro(maestro, error):
    if error.code == '23505':
        return f'Ya existe {maestro["articulo"]} {maestro["singular"]} con esos datos.'
    if error.code == '23514':
        return 'Hay un campo con un formato no permitido (los códigos EAN solo admiten números).'
    if error.code == '23503':
        return f'{maestro["articulo"].capitalize()} {maestro["singular"]} está en uso y no se puede eliminar.'
    return error.message or 'No se pudo guardar el registro.'


def _crud_maestro(nombre, contexto=None):
    maestro = MAESTROS_SIMPLES[nombre]
    tabla, clave, singular = maestro['tabla'], maestro['clave'], maestro['singular']
    sufijo = 'a' if maestro['articulo'] == 'la' else 'o'  # creada / creado
    if request.method == 'POST':
        metodo = request.form.get('_method', '')
        if metodo.startswith('buscar'):
            # Las búsquedas antiguas por POST pasan a la barra de búsqueda (GET ?q=).
            texto = next((v for k, v in request.form.items() if k.endswith('Buscar')), '')
            return redirect(url_for(maestro['endpoint'], q=texto))
        try:
            if metodo == 'post':
                datos, error = _leer_maestro_formulario(maestro, 'Crear')
                if error:
                    flash(error, 'error')
                elif supabase.table(tabla).insert(datos).execute().data:
                    flash(f'{singular.capitalize()} {datos[maestro["principal"]]} cread{sufijo} exitosamente', 'success')
                else:
                    flash(f'Error creando {singular}', 'error')
                return redirect(url_for(maestro['endpoint']))
            id_registro = _entero_positivo(request.form.get(maestro['id_form'] + 'Actualizar')
                                           or request.form.get(maestro['id_form'] + 'Borrar'))
            actual = supabase.table(tabla).select('*').eq(clave, id_registro).execute().data if id_registro else []
            if metodo not in ('put', 'delete'):
                return redirect(url_for(maestro['endpoint']))
            if not actual:
                flash(f'{maestro["articulo"].capitalize()} {singular} no existe', 'error')
                return redirect(url_for(maestro['endpoint']))
            nombre_registro = actual[0].get(maestro['principal'])
            if metodo == 'put':
                datos, error = _leer_maestro_formulario(maestro, 'Actualizar', id_registro)
                if error:
                    flash(error, 'error')
                else:
                    supabase.table(tabla).update(datos).eq(clave, id_registro).execute()
                    flash(f'{singular.capitalize()} {datos[maestro["principal"]]} actualizad{sufijo} exitosamente', 'success')
            else:
                en_uso = [texto for t, columna, texto in maestro['en_uso']
                          if supabase.table(t).select(columna).eq(columna, id_registro).limit(1).execute().data]
                if en_uso:
                    flash(f'{maestro["articulo"].capitalize()} {singular} {nombre_registro} está en uso en '
                          f'{", ".join(en_uso)} y no se puede eliminar', 'error')
                else:
                    supabase.table(tabla).delete().eq(clave, id_registro).execute()
                    flash(f'{singular.capitalize()} {nombre_registro} borrad{sufijo} exitosamente', 'success')
        except APIError as error:
            flash(_mensaje_error_maestro(maestro, error), 'error')
        return redirect(url_for(maestro['endpoint']))

    busqueda = request.args.get('q', '').strip()
    datos = supabase.table(tabla).select('*').order(maestro['principal']).execute().data or []
    if busqueda:
        texto = busqueda.lower()
        datos = [f for f in datos if any(texto in str(f.get(c['columna']) or '').lower() for c in maestro['campos'])]
    return render_template(maestro['plantilla'], datos=datos, maestro=maestro, busqueda=busqueda,
                           **(contexto(datos) if contexto else {}))


@app.route('/zonasVenta.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def zonasVenta():
    # RF-009/010, CU-09.1 a CU-09.4. La columna nombre se muestra primero.
    return _crud_maestro('zonas_venta')


@app.route('/tallas.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def tallas():
    # RF-011/012, CU-11.1 a CU-11.4.
    return _crud_maestro('tallas')


def _mensaje_error_producto(error, accion):
    return {
        "23503": "El color o talla seleccionado no existe",
        "22P02": "El color o talla seleccionado no es válido",
        "23505": "Ya existe un producto con ese código de artículo",
        "23514": "El código EAN del producto solo puede tener números",
    }.get(error.code, error.message if error.code == "P0001" else f"No se pudo {accion} el producto")


def _leer_producto_formulario(sufijo, id_producto=None):
    codigo_ean = _texto_o_nulo(request.form.get('codigoEan' + sufijo))
    if codigo_ean:
        error = _validar_codigo_ean_maestro('productos', 'id_producto', 'producto', codigo_ean, id_producto)
        if error:
            return None, error
    descripcion = (request.form.get('descripcion' + sufijo) or '').strip()
    if not descripcion:
        return None, 'La descripción del producto es obligatoria.'
    if len(descripcion) > 64:
        return None, 'La descripción admite hasta 64 caracteres.'
    precio = (request.form.get('precio' + sufijo) or '').strip()
    if precio and (not precio.isdigit()):
        return None, 'El precio debe ser un número entero mayor o igual a cero.'
    codigo = _texto_o_nulo(request.form.get('codigo' + sufijo))
    if codigo and len(codigo) > 16:
        return None, 'El código de producto admite hasta 16 caracteres.'
    return {
        'descripcion': descripcion,
        'abreviacion': _texto_o_nulo(request.form.get('abreviacion' + sufijo)),
        'color': _entero_positivo(request.form.get('idColor' + sufijo)),
        'talla': _entero_positivo(request.form.get('idTalla' + sufijo)),
        'precio': int(precio) if precio else None,
        'codigo': codigo,
        'codigo_ean': codigo_ean,
    }, None


def _combinaciones_marcadas(prefijo):
    """Combinaciones color-talla marcadas en la grilla (checkbox prefijo con valor
    'idColor-idTalla') con su precio (campo 'precio' + prefijo + '_idColor-idTalla')."""
    combinaciones = []
    for valor in request.form.getlist(prefijo):
        partes = valor.split('-')
        if len(partes) != 2 or not all(p.isdigit() for p in partes):
            continue
        precio = (request.form.get(f'precio{prefijo.capitalize()}_{valor}') or '').strip()
        if precio and not precio.isdigit():
            raise ValueError('El precio de cada variante debe ser un número entero mayor o igual a cero.')
        combinaciones.append((int(partes[0]), int(partes[1]), int(precio) if precio else None))
    return combinaciones


def _crear_variantes(id_producto, combinaciones, precio_base):
    """Crea (o reactiva) cada variante con obtener_variante(), que es la que le asigna
    el código EAN (trigger fn_variante_ean / fn_generar_ean, incremento3_ean.sql)."""
    for id_color, id_talla, precio in combinaciones:
        variante = supabase.rpc('obtener_variante', {
            'p_id_producto': id_producto, 'p_id_color': id_color, 'p_id_talla': id_talla,
        }).execute().data or []
        if variante:
            supabase.table('producto_variantes').update({
                'precio_venta': precio if precio is not None else (precio_base or 0), 'activo': True,
            }).eq('id_variante', variante[0]['id_variante']).execute()
    return len(combinaciones)


@app.route('/productos.html', methods=['GET', 'POST', 'DELETE', 'PUT'])
def productos():
    # RF-013/014 y CU-13.1 a CU-13.5. Cada combinación talla/color con su precio es
    # una fila de producto_variantes; las variantes no se borran, se desactivan.
    if request.method == 'POST':
        metodo = request.form.get('_method')
        if metodo == "post":
            datos, error = _leer_producto_formulario('Crear')
            try:
                combinaciones = _combinaciones_marcadas('variante')
            except ValueError as e:
                error = error or str(e)
            if error:
                flash(error, "error")
                return redirect(url_for('productos'))
            try:
                creado = supabase.table("productos").insert(datos).execute().data
            except APIError as e:
                flash(_mensaje_error_producto(e, 'crear'), "error")
                return redirect(url_for('productos'))
            if not creado:
                flash("Error creando producto", "error")
                return redirect(url_for('productos'))
            n = _crear_variantes(creado[0]['id_producto'], combinaciones, datos['precio'])
            flash(f"Producto creado exitosamente{f' con {n} variante' + ('s' if n != 1 else '') if n else ''}", "success")
            return redirect(url_for('productos'))

        id_producto = _entero_positivo(request.form.get('IdProductoActualizar') or request.form.get('idProductoBorrar')
                                       or request.form.get('idProductoVariantes'))
        actual = supabase.table("productos").select("id_producto, descripcion, precio") \
            .eq("id_producto", id_producto).execute().data if id_producto else []
        if metodo in ("put", "delete", "variantes") and not actual:
            flash("El producto no existe", "error")
            return redirect(url_for('productos'))

        if metodo == "put":
            datos, error = _leer_producto_formulario('Actualizar', id_producto)
            if error:
                flash(error, "error")
                return redirect(url_for('productos'))
            try:
                supabase.table("productos").update(datos).eq("id_producto", id_producto).execute()
            except APIError as e:
                flash(_mensaje_error_producto(e, 'actualizar'), "error")
                return redirect(url_for('productos'))
            flash("Producto actualizado exitosamente", "success")
            return redirect(url_for('productos'))

        if metodo == "variantes":
            # CU-13.5: precios de cada variante (talla y color) y estado, más combinaciones nuevas.
            # precio_<id> es el precio mayor de la lista 1 (precio_venta); costo, detalle y
            # liquidación son los otros tipos de precio (RNF-004). La "lista adicional" guarda
            # el precio mayor de otra lista de precios para todas las variantes a la vez.
            existentes = supabase.table('producto_variantes').select('id_variante') \
                .eq('id_producto', id_producto).execute().data or []
            lista_extra = (request.form.get('listaExtra') or '').strip()
            if lista_extra and (not lista_extra.isdigit() or int(lista_extra) < 2):
                flash('La lista de precios adicional debe ser un número entero desde 2 (la lista 1 es el precio mayor).',
                      'error')
                return redirect(url_for('productos'))
            cambios = []
            for v in existentes:
                id_v = v['id_variante']
                valores = {'activo': request.form.get(f'activo_{id_v}') == 'on',
                           'en_liquidacion': request.form.get(f'enLiquidacion_{id_v}') == 'on'}
                for campo, columna in (('precio', 'precio_venta'), ('costo', 'precio_costo'),
                                       ('detalle', 'precio_detalle'), ('liquidacion', 'precio_liquidacion')):
                    texto = (request.form.get(f'{campo}_{id_v}') or '').strip()
                    if texto and not texto.isdigit():
                        flash('Los precios deben ser números enteros mayores o iguales a cero.', 'error')
                        return redirect(url_for('productos'))
                    if texto:
                        valores[columna] = int(texto)
                precio_lista = (request.form.get(f'precioLista_{id_v}') or '').strip()
                if precio_lista and not precio_lista.isdigit():
                    flash('Los precios de la lista adicional deben ser números enteros.', 'error')
                    return redirect(url_for('productos'))
                cambios.append((id_v, valores, int(precio_lista) if precio_lista else None))
            try:
                nuevas = _combinaciones_marcadas('nueva')
            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('productos'))
            for id_variante, valores, precio_lista in cambios:
                supabase.table('producto_variantes').update(valores).eq('id_variante', id_variante).execute()
                if lista_extra:
                    # Vacío = esa variante no tiene precio propio en la lista (usa el precio mayor).
                    supabase.table('variante_precios_lista').delete().eq('id_variante', id_variante) \
                        .eq('lista_precios', int(lista_extra)).execute()
                    if precio_lista is not None:
                        supabase.table('variante_precios_lista').insert({
                            'id_variante': id_variante, 'lista_precios': int(lista_extra), 'precio': precio_lista,
                        }).execute()
            _crear_variantes(id_producto, nuevas, actual[0].get('precio'))
            desactivadas = sum(1 for _, valores, _ in cambios if not valores['activo'])
            flash(f"Variantes de {actual[0]['descripcion']} actualizadas: {len(nuevas)} nueva(s), "
                  f"{desactivadas} desactivada(s)" + (f", precios de la lista {lista_extra} guardados" if lista_extra else ''),
                  "success")
            return redirect(url_for('productos'))

        if metodo == "delete":
            # CU-13.4: no se elimina un producto con pedidos, inventario o cortes asociados.
            variantes = [v['id_variante'] for v in supabase.table('producto_variantes').select('id_variante')
                         .eq('id_producto', id_producto).execute().data or []]
            en_uso = []
            if variantes and supabase.table('detalle_pedidos').select('id_detalle_pedido') \
                    .in_('id_variante', variantes).limit(1).execute().data:
                en_uso.append('pedidos')
            if variantes and supabase.table('inventario').select('id_inventario') \
                    .in_('id_variante', variantes).limit(1).execute().data:
                en_uso.append('inventario')
            if supabase.table('cortes').select('id_corte').eq('producto_asociado', id_producto).limit(1).execute().data:
                en_uso.append('cortes')
            if en_uso:
                flash(f"El producto {actual[0]['descripcion']} tiene {', '.join(en_uso)} asociados: no se puede "
                      "eliminar. Desactiva sus variantes.", "error")
                return redirect(url_for('productos'))
            if variantes:
                supabase.table('producto_variantes').delete().eq('id_producto', id_producto).execute()
            supabase.table("productos").delete().eq("id_producto", id_producto).execute()
            flash(f"Producto {actual[0]['descripcion']} borrado exitosamente", "success")
            return redirect(url_for('productos'))

        # Búsquedas antiguas por función de la base (se mantienen por compatibilidad).
        busquedas = {'buscarID': ('buscarproductoid', 'idBuscar'),
                     'buscarDescripcion': ('buscarproductodescripcion', 'descripcionBuscar'),
                     'buscarAbreviacion': ('buscarproductoabreviacion', 'abreviacionBuscar')}
        if metodo in busquedas:
            funcion, campo = busquedas[metodo]
            texto = request.form.get(campo, '')
            return redirect(url_for('productos', q=texto))
        return redirect(url_for('productos'))

    busqueda = request.args.get('q', '').strip()
    datos = supabase.table("productos").select("*").order("descripcion").execute().data or []
    if busqueda:
        texto = busqueda.lower()
        datos = [p for p in datos if texto in ' '.join(str(p.get(k) or '') for k in ('descripcion', 'abreviacion', 'codigo')).lower()]
    colores = supabase.table("colores").select("*").order("descripcion").execute().data or []
    tallas = supabase.table("tallas").select("*").order("talla").execute().data or []
    nombre_color = {c['id_color']: c.get('descripcion') for c in colores}
    nombre_talla = {t['id_talla']: t.get('nombre') or str(t.get('talla')) for t in tallas}
    variantes = supabase.table('producto_variantes').select('*').execute().data or []
    listas = {}
    try:
        for fila in supabase.table('variante_precios_lista').select('*').execute().data or []:
            listas.setdefault(fila['id_variante'], {})[str(fila['lista_precios'])] = fila['precio']
    except APIError:
        pass  # incremento4_campos_documento0.sql todavía no se ejecuta
    por_producto = {}
    for v in sorted(variantes, key=lambda v: (str(nombre_color.get(v.get('id_color')) or ''), str(nombre_talla.get(v.get('id_talla')) or ''))):
        por_producto.setdefault(v['id_producto'], []).append({
            'id_variante': v['id_variante'], 'id_color': v.get('id_color'), 'id_talla': v.get('id_talla'),
            'codigo_ean': v.get('codigo_ean'), 'precio_venta': v.get('precio_venta') or 0,
            'precio_costo': v.get('precio_costo') or 0, 'precio_detalle': v.get('precio_detalle') or 0,
            'precio_liquidacion': v.get('precio_liquidacion') or 0, 'en_liquidacion': bool(v.get('en_liquidacion')),
            'listas': listas.get(v['id_variante'], {}),
            'color': nombre_color.get(v.get('id_color'), ''), 'talla': nombre_talla.get(v.get('id_talla'), ''),
            'activo': v.get('activo') is not False})
    for producto in datos:
        producto['variantes'] = por_producto.get(producto['id_producto'], [])
        producto['color_nombre'] = nombre_color.get(producto.get('color'), '')
        producto['talla_nombre'] = nombre_talla.get(producto.get('talla'), '')
    return render_template('productos.html', datos=datos, colores=colores, tallas=tallas, busqueda=busqueda)


def _ean_en_otra_variante(codigo, id_variante):
    return any(str(v['id_variante']) != str(id_variante) for v in supabase.table('producto_variantes')
               .select('id_variante').eq('codigo_ean', codigo).execute().data or [])


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
                # CU-15.1 excepción 2: el dígito 13 debe ser el verificador EAN-13.
                if ean13.digito_verificador(codigo[:12]) != codigo[12]:
                    flash(f"El código {codigo} no es un EAN-13 válido: el dígito verificador debería ser "
                          f"{ean13.digito_verificador(codigo[:12])}", "error")
                    return redirect(url_for('codigosEAN'))
                if _ean_en_otra_variante(codigo, idVariante):
                    flash("Ese código EAN ya está asignado a otra variante", "error")
                    return redirect(url_for('codigosEAN'))
                supabase.table("producto_variantes").update({"ean_manual": True, "codigo_ean": codigo}) \
                    .eq("id_variante", idVariante).execute()
                flash("Código manual guardado", "success")
            elif metodo == "automatico":
                # CU-15.5: el código que generaría la base no puede estar ya en otra variante.
                variante = supabase.table("producto_variantes").select("id_producto, id_color, id_talla") \
                    .eq("id_variante", idVariante).execute().data
                automatico = supabase.rpc('fn_generar_ean', {
                    'p_id_producto': variante[0]['id_producto'], 'p_id_color': variante[0]['id_color'],
                    'p_id_talla': variante[0]['id_talla']}).execute().data if variante else None
                if automatico and _ean_en_otra_variante(automatico, idVariante):
                    flash(f"El código automático {automatico} ya está asignado a otra variante: revisa los códigos "
                          "EAN del producto, color y talla", "error")
                    return redirect(url_for('codigosEAN'))
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