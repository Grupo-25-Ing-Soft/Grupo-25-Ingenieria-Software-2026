"""Pagos (RF-032 a RF-034) con el esquema de supabase/pagos.sql."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}, {'id_cliente': 2, 'nombre': 'Outlet Norte'}],
        'facturas': [
            {'id_factura': 1, 'folio': 100, 'cliente_asociado': 1, 'fecha_emision': '2026-09-01',
             'monto_total': 1000, 'saldo_pendiente': 1000, 'estado': 'vigente'},
            {'id_factura': 2, 'folio': 101, 'cliente_asociado': 1, 'fecha_emision': '2026-09-05',
             'monto_total': 500, 'saldo_pendiente': 500, 'estado': 'vigente'},
            {'id_factura': 3, 'folio': 102, 'cliente_asociado': 2, 'fecha_emision': '2026-09-05',
             'monto_total': 700, 'saldo_pendiente': 700, 'estado': 'vigente'},
        ],
        'pagos': [], 'pago_facturas': [], 'notas_credito': [],
    })
    return db


def factura(base, id_factura):
    return next(f for f in base.tablas['facturas'] if f['id_factura'] == id_factura)


def registrar(admin, monto='1200', facturas=(1, 2), cliente=1):
    return admin.post('/pagos.html', data={'_method': 'post', 'cliente': cliente, 'monto': monto,
                                           'fecha_pago': '2026-10-01', 'medio_pago': 'transferencia',
                                           'facturas': list(facturas)}, follow_redirects=True)


def test_registrar_reparte_y_actualiza_saldo_y_estado(admin, base):
    html = registrar(admin).get_data(as_text=True)
    assert 'Pago N° 1 registrado' in html
    assert base.tablas['pagos'][0]['folio'] == 1  # lo asigna la base (identity), no el usuario
    assert [(p['id_factura'], p['monto_aplicado']) for p in base.tablas['pago_facturas']] == [(1, 1000), (2, 200)]
    assert (factura(base, 1)['saldo_pendiente'], factura(base, 1)['estado']) == (0, 'pagada')
    assert (factura(base, 2)['saldo_pendiente'], factura(base, 2)['estado']) == (300, 'parcialmente_pagada')
    listado = admin.get('/pagos.html').get_data(as_text=True)
    assert '<td>1</td>' in listado and 'Factura 100: $1.000' in listado and 'name="folio' not in listado


def test_saldo_a_favor_y_factura_de_otro_cliente(admin, base):
    r = registrar(admin, monto='100', facturas=(3,))
    assert 'deben ser del cliente del pago' in r.get_data(as_text=True)
    assert base.tablas['pagos'] == [] and factura(base, 3)['saldo_pendiente'] == 700
    assert 'saldo a favor del cliente de $300' in registrar(admin, monto='1800').get_data(as_text=True)
    assert 'no tiene facturas con saldo pendiente' in registrar(admin, monto='1').get_data(as_text=True)


def test_editar_reaplica_el_pago(admin, base):
    registrar(admin)
    admin.post('/pagos.html', data={'_method': 'put', 'id_pago_actualizar': 1, 'cliente_actualizar': 1,
                                    'monto_actualizar': '400', 'fecha_pago_actualizar': '2026-10-02',
                                    'medio_pago_actualizar': 'cheque', 'facturas_actualizar': ['2']})
    assert [(p['id_factura'], p['monto_aplicado']) for p in base.tablas['pago_facturas']] == [(2, 400)]
    assert (factura(base, 1)['saldo_pendiente'], factura(base, 1)['estado']) == (1000, 'vigente')
    assert factura(base, 2)['saldo_pendiente'] == 100
    assert base.tablas['pagos'][0]['monto'] == 400 and base.tablas['pagos'][0]['folio'] == 1


def test_anular_devuelve_el_saldo_y_conserva_el_historial(admin, base):
    registrar(admin)
    r = admin.post('/pagos.html', data={'_method': 'delete', 'id_pago_anular': 1, 'motivo_anulacion': 'Cheque rebotado'},
                   follow_redirects=True)
    assert 'Pago N° 1 anulado' in r.get_data(as_text=True)
    assert base.tablas['pagos'][0]['estado'] == 'anulada'
    assert len(base.tablas['pago_facturas']) == 2  # historial
    assert (factura(base, 1)['saldo_pendiente'], factura(base, 1)['estado']) == (1000, 'vigente')
    assert factura(base, 2)['saldo_pendiente'] == 500
    r = admin.post('/pagos.html', data={'_method': 'put', 'id_pago_actualizar': 1}, follow_redirects=True)
    assert 'está anulado' in r.get_data(as_text=True)


def test_la_nota_de_credito_tambien_cuenta_en_el_saldo(admin, base):
    base.tablas['notas_credito'].append({'id_nota_credito': 1, 'factura_referencia': 2, 'monto_total': 100,
                                         'estado': 'vigente'})
    registrar(admin, monto='1000', facturas=(1,))
    admin.post('/pagos.html', data={'_method': 'delete', 'id_pago_anular': 1, 'motivo_anulacion': 'x'})
    assert factura(base, 1)['saldo_pendiente'] == 1000
