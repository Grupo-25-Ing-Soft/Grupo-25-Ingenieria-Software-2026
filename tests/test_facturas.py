"""Facturas (RF-029/030) con el esquema de supabase/facturas.sql."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'parametros_sistema': [{'id': 1, 'porcentaje_impuesto': 19}],
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}, {'id_cliente': 2, 'nombre': 'Outlet Norte'}],
        'pedidos': [{'id_pedido': 10, 'numero_pedido': 'PED-000010', 'cliente_asociado': 1, 'estado': 'pendiente'},
                    {'id_pedido': 11, 'numero_pedido': 'PED-000011', 'cliente_asociado': 2, 'estado': 'anulado'}],
        'facturas': [], 'pagos': [], 'pago_facturas': [], 'notas_credito': [], 'despachos': [],
    })
    return db


def crear(admin, folio=100, pedido=10, neto='10000'):
    return admin.post('/facturas.html', data={'_method': 'post', 'folioCrear': folio, 'pedidoCrear': pedido,
                                              'fechaEmisionCrear': '2026-10-01', 'montoNetoCrear': neto},
                      follow_redirects=True)


def test_crear_calcula_impuesto_y_toma_el_cliente_del_pedido(admin, base):
    r = crear(admin)
    assert 'Factura 100 creada' in r.get_data(as_text=True)
    f = base.tablas['facturas'][0]
    assert (f['monto_neto'], f['monto_impuesto'], f['monto_total']) == (10000, 1900, 11900)
    assert f['saldo_pendiente'] == 11900 and f['estado'] == 'vigente'
    assert f['cliente_asociado'] == 1 and f['pedido_asociado'] == 10
    html = admin.get('/facturas.html').get_data(as_text=True)
    assert 'Tienda Sur' in html and 'PED-000010' in html and '$11.900' in html and '01/10/2026' in html


@pytest.mark.parametrize('datos,mensaje', [
    ({'folio': 'abc'}, 'El folio debe ser un número'),
    ({'pedido': 11}, 'pedido anulado'),
    ({'neto': '-5'}, 'monto neto'),
])
def test_crear_valida(admin, base, datos, mensaje):
    assert mensaje in crear(admin, **datos).get_data(as_text=True)
    assert base.tablas['facturas'] == []


def test_folio_repetido(admin, base):
    crear(admin)
    assert 'Ya existe una factura con el folio 100' in crear(admin).get_data(as_text=True)
    assert len(base.tablas['facturas']) == 1


def test_editar_recalcula_saldo_con_pagos(admin, base):
    crear(admin)
    base.tablas['pagos'].append({'id_pago': 1, 'estado': 'vigente'})
    base.tablas['pago_facturas'].append({'id_pago_factura': 1, 'id_pago': 1, 'id_factura': 1, 'monto_aplicado': 5000})
    admin.post('/facturas.html', data={'_method': 'put', 'idFacturaActualizar': 1, 'folioActualizar': 100,
                                       'pedidoActualizar': 10, 'fechaEmisionActualizar': '2026-10-01',
                                       'montoNetoActualizar': '20000'})
    f = base.tablas['facturas'][0]
    assert f['monto_total'] == 23800 and f['saldo_pendiente'] == 18800 and f['estado'] == 'parcialmente_pagada'


def test_no_se_elimina_con_pagos_solo_se_anula(admin, base):
    crear(admin)
    base.tablas['pago_facturas'].append({'id_pago_factura': 1, 'id_pago': 1, 'id_factura': 1, 'monto_aplicado': 1})
    r = admin.post('/facturas.html', data={'_method': 'delete', 'idFacturaBorrar': 1}, follow_redirects=True)
    assert 'no se puede eliminar, solo anular' in r.get_data(as_text=True)
    assert base.tablas['facturas']

    admin.post('/facturas.html', data={'_method': 'anular', 'idFacturaAnular': 1})
    assert base.tablas['facturas'][0]['estado'] == 'anulada'
    r = admin.post('/facturas.html', data={'_method': 'put', 'idFacturaActualizar': 1, 'folioActualizar': 100,
                                           'pedidoActualizar': 10, 'fechaEmisionActualizar': '2026-10-01',
                                           'montoNetoActualizar': '1'}, follow_redirects=True)
    assert 'está anulada' in r.get_data(as_text=True)


def anular(admin):
    return admin.post('/facturas.html', data={'_method': 'anular', 'idFacturaAnular': 1},
                      follow_redirects=True).get_data(as_text=True)


def test_no_se_anula_con_pagos_vigentes(admin, base):
    # AUD-022: el pago quedaba aplicado a una factura anulada, que ya no se recalcula.
    crear(admin)
    base.tablas['pagos'].append({'id_pago': 1, 'folio': 1, 'estado': 'vigente'})
    base.tablas['pago_facturas'].append({'id_pago_factura': 1, 'id_pago': 1, 'id_factura': 1, 'monto_aplicado': 5000})
    html = anular(admin)
    assert 'tiene pagos vigentes por $5.000: anúlalos primero en Pagos' in html
    assert base.tablas['facturas'][0]['estado'] != 'anulada'

    base.tablas['pagos'][0]['estado'] = 'anulada'  # con el pago anulado ya se puede
    assert 'Factura 100 anulada' in anular(admin)
    assert base.tablas['facturas'][0]['estado'] == 'anulada'


def test_no_se_anula_con_notas_de_credito_vigentes(admin, base):
    crear(admin)
    base.tablas['notas_credito'].append({'id_nota_credito': 1, 'folio': 1, 'factura_referencia': 1,
                                         'monto_total': 2000, 'estado': 'vigente'})
    html = anular(admin)
    assert 'tiene notas de crédito vigentes por $2.000: anúlalos primero en Notas de crédito' in html
    assert base.tablas['facturas'][0]['estado'] != 'anulada'

    base.tablas['notas_credito'][0]['estado'] = 'anulada'
    anular(admin)
    assert base.tablas['facturas'][0]['estado'] == 'anulada'


def test_eliminar_sin_asociados(admin, base):
    crear(admin)
    admin.post('/facturas.html', data={'_method': 'delete', 'idFacturaBorrar': 1})
    assert base.tablas['facturas'] == []


def test_filtro_por_cliente(admin, base):
    crear(admin)
    assert 'No hay facturas para los filtros aplicados' in admin.get('/facturas.html?cliente=norte').get_data(as_text=True)
    assert '<td>Tienda Sur</td>' in admin.get('/facturas.html?cliente=sur').get_data(as_text=True)


def test_facturas_en_la_barra_lateral(admin, base):
    html = admin.get('/facturas.html').get_data(as_text=True)
    assert 'href="/facturas.html" class="active"' in html and 'href="/despachos.html"' in html


def test_fecha_limite_de_pago(admin, base):
    # RF-029: fecha límite de pago opcional, no anterior a la emisión.
    datos = {'_method': 'post', 'folioCrear': 200, 'pedidoCrear': 10, 'fechaEmisionCrear': '2026-10-01',
             'montoNetoCrear': '1000'}
    r = admin.post('/facturas.html', data={**datos, 'fechaVencimientoCrear': '2026-09-30'}, follow_redirects=True)
    assert 'no puede ser anterior a la fecha de emisión' in r.get_data(as_text=True) and base.tablas['facturas'] == []
    admin.post('/facturas.html', data={**datos, 'fechaVencimientoCrear': '2026-10-31'})
    assert base.tablas['facturas'][0]['fecha_vencimiento'] == '2026-10-31'
    assert '31/10/2026' in admin.get('/facturas.html').get_data(as_text=True)


def editar_pedido(admin, pedido):
    return admin.post('/facturas.html', data={'_method': 'put', 'idFacturaActualizar': 1, 'folioActualizar': 100,
                                              'pedidoActualizar': pedido, 'fechaEmisionActualizar': '2026-10-01',
                                              'montoNetoActualizar': '10000'}, follow_redirects=True)


@pytest.mark.parametrize('asociado', ['pago', 'nota', 'despacho'])
def test_no_se_cambia_el_pedido_con_registros_asociados(admin, base, asociado):
    # AUD-023: el cliente sale del pedido; los pagos de Tienda Sur quedaban en una factura de Outlet Norte.
    base.tablas['pedidos'].append({'id_pedido': 12, 'numero_pedido': 'PED-000012', 'cliente_asociado': 2,
                                   'estado': 'pendiente'})
    crear(admin)
    if asociado == 'pago':
        base.tablas['pagos'].append({'id_pago': 1, 'estado': 'vigente'})
        base.tablas['pago_facturas'].append({'id_pago_factura': 1, 'id_pago': 1, 'id_factura': 1, 'monto_aplicado': 500})
    elif asociado == 'nota':
        base.tablas['notas_credito'].append({'id_nota_credito': 1, 'factura_referencia': 1, 'monto_total': 500,
                                             'estado': 'vigente'})
    else:
        base.tablas['despachos'].append({'id_despacho': 1, 'id_factura': 1, 'id_pedido': 10, 'estado': 'emitido'})
    html = editar_pedido(admin, 12).get_data(as_text=True)
    assert 'no se puede cambiar su pedido' in html
    factura = base.tablas['facturas'][0]
    assert factura['pedido_asociado'] == 10 and factura['cliente_asociado'] == 1
    # Sin cambiar el pedido, la factura se sigue pudiendo editar.
    assert 'Factura 100 actualizada' in editar_pedido(admin, 10).get_data(as_text=True)


def test_sin_asociados_se_puede_cambiar_el_pedido(admin, base):
    base.tablas['pedidos'].append({'id_pedido': 12, 'numero_pedido': 'PED-000012', 'cliente_asociado': 2,
                                   'estado': 'pendiente'})
    crear(admin)
    assert 'Factura 100 actualizada' in editar_pedido(admin, 12).get_data(as_text=True)
    factura = base.tablas['facturas'][0]
    assert factura['pedido_asociado'] == 12 and factura['cliente_asociado'] == 2
