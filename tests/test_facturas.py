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
