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
from markupsafe import Markup
from supabase import create_client, Client
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from werkzeug.utils import secure_filename
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

# index() es básicamente lo que se carga inicialmente. Por ahora,
# está puesto que cargue el cliente.html automáticamente,
# pero eso lo cambiaremos a un menú principal y lo dividiremos
# cuando tengamos las otras páginas.

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
            response = (supabase.table("pedidos").select("*, detalle_pedidos!inner(id_variante)").eq("detalle_pedidos.id_variante", texto).execute())
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


@app.route('/notasCredito.html', methods=['GET'])
def notasCredito():
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
        query = supabase.table('notas_credito').select(
            '*, facturas(numero_factura, razon_social)'
        ).execute()
        rows = query.data or []
    except Exception:
        flash("No se pudo cargar el listado de notas de crédito. Intenta nuevamente.", "error")
        rows = []

    normalized = []
    for row in rows:
        factura_row = row.get('facturas') or {}
        factura_numero = factura_row.get('numero_factura') if isinstance(factura_row, dict) else None
        cliente_nombre = factura_row.get('razon_social') if isinstance(factura_row, dict) else ''
        normalized.append({
            'id_nota_credito': row.get('id_nota'),
            'folio': row.get('numero_nota'),
            'factura_referencia': row.get('id_factura'),
            'factura_referencia_folio': factura_numero,
            'cliente_asociado': row.get('id_cliente'),
            'cliente': cliente_nombre,
            'fecha': row.get('fecha'),
            'monto_neto': row.get('total_neto', 0),
            'monto_impuesto': row.get('total_iva', 0),
            'monto_total': row.get('total_nota', 0),
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

    return render_template('notasCredito.html', datos=normalized)


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
    if request.method == 'POST':
        #Buscar los productos despachados entre tal y tal fecha
        #Para ello necesitamos un campo o tabla con fechas de despacho
        fechaDesde = request.form['desdeFecha']
        fechaHasta = request.form['hastaFecha']
        return 'placeholder'
    else:
        return render_template('informeProductosDespachados.html')

@app.route('/informeProductosEnProceso.html', methods=['GET', 'POST'])
def informeProductosEnProceso():
    if request.method == 'POST':
        #Buscar los productos presentes en corte pero no ingresados a bodega
        return 'placeholder'
    else:
        return render_template('informeProductosEnProceso.html')

@app.route('/informeProductosPendientesDespacho.html', methods=['GET', 'POST'])
def informeProductosPendientesDespacho():
    if request.method == 'POST':
        #Buscar los productos que estén en bodega y falta despachar
        return 'placeholder'
    else:
        return render_template('informeProductosPendientesDespacho.html')

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
            descripcion = request.form['descripcionCrear'] 

            #Hasta aquí toma los datos que se enviaron desde cliente.html cuando
            #se pulsó el botón con submit.

            #Esto se encapsula en response para poder detectar y loggear errores.
            response = (

                #Este es el comando para insertar los datos a la base de datos.
                supabase.table("zona_venta").insert({"descripcion": descripcion
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
            descripcion = request.form['descripcionActualizar'] 
            response = (
                
                supabase.table("zona_venta").update({"descripcion": descripcion
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

@app.route('/', methods=['GET'])
def index():
        return render_template('index.html')

#Esto simplemente lo corre en debug mode
if __name__ == '__main__':
    app.run(debug=True)