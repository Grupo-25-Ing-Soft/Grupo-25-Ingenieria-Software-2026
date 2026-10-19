"""Notas de crédito (RF-035/036) con el esquema de supabase/notas_credito.sql."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'parametros_sistema': [{'id': 1, 'porcentaje_impuesto': 19}],
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}],
        'facturas': [{'id_factura': 1, 'folio': 500, 'cliente_asociado': 1, 'pedido_asociado': 10,
                      'monto_total': 11900, 'saldo_pendiente': 11900, 'estado': 'vigente'},
                     {'id_factura': 2, 'folio': 501, 'cliente_asociado': 1, 'pedido_asociado': 10,
                      'monto_total': 1190, 'saldo_pendiente': 1190, 'estado': 'anulada'}],
        'notas_credito': [{'id_nota_credito': 1, 'folio': 7, 'factura_referencia': 1, 'cliente_asociado': 1,
                           'fecha': '2026-09-01', 'monto_neto': 0, 'monto_impuesto': 0, 'monto_total': 0,
                           'motivo': 'Antigua', 'estado': 'anulada'}],
        'pagos': [], 'pago_facturas': [],
    })
    return db


def crear(admin, **cambios):
    datos = {'_method': 'post', 'folioCrear': 8, 'facturaCrear': 1, 'fechaCrear': '2026-10-02',
             'montoNetoCrear': '5000', 'motivoCrear': 'Devolución'}
    datos.update(cambios)
    return admin.post('/notasCredito.html', data=datos, follow_redirects=True)


def factura(base):
    return base.tablas['facturas'][0]


def test_lee_las_columnas_del_script_y_propone_folio(admin, base):
    html = admin.get('/notasCredito.html').get_data(as_text=True)
    assert '<td>7</td>' in html and 'Tienda Sur' in html and '01/09/2026' in html
    assert 'name="folioCrear" min="1" value="8"' in html


def test_crear_rebaja_el_saldo_de_la_factura(admin, base):
    assert 'Nota de crédito 8 creada' in crear(admin).get_data(as_text=True)
    nota = base.tablas['notas_credito'][-1]
    assert (nota['monto_impuesto'], nota['monto_total'], nota['cliente_asociado']) == (950, 5950, 1)
    assert factura(base)['saldo_pendiente'] == 5950 and factura(base)['estado'] == 'parcialmente_pagada'


@pytest.mark.parametrize('cambios,mensaje', [
    ({'folioCrear': 7}, 'Ya existe una nota de crédito con el folio 7'),
    ({'facturaCrear': 2}, 'está anulada'),
    ({'montoNetoCrear': '20000'}, 'supera el saldo pendiente'),
    ({'motivoCrear': ' '}, 'Indique el motivo'),
])
def test_crear_valida(admin, base, cambios, mensaje):
    assert mensaje in crear(admin, **cambios).get_data(as_text=True)
    assert len(base.tablas['notas_credito']) == 1


def test_editar_anular_y_eliminar_ajustan_el_saldo(admin, base):
    crear(admin)
    # La propia nota no cuenta contra el saldo al editarla: puede subir hasta el total.
    admin.post('/notasCredito.html', data={'_method': 'put', 'idNotaActualizar': 2, 'folioActualizar': 8,
                                           'facturaActualizar': 1, 'fechaActualizar': '2026-10-02',
                                           'montoNetoActualizar': '10000', 'motivoActualizar': 'Total'})
    assert factura(base)['saldo_pendiente'] == 0 and factura(base)['estado'] == 'pagada'

    admin.post('/notasCredito.html', data={'_method': 'anular', 'idNotaAnular': 2})
    assert factura(base)['saldo_pendiente'] == 11900 and factura(base)['estado'] == 'vigente'

    crear(admin, folioCrear=9)
    admin.post('/notasCredito.html', data={'_method': 'delete', 'idNotaBorrar': 3})
    assert factura(base)['saldo_pendiente'] == 11900
    assert [n['folio'] for n in base.tablas['notas_credito']] == [7, 8]


def test_no_se_edita_una_nota_anulada(admin, base):
    r = admin.post('/notasCredito.html', data={'_method': 'put', 'idNotaActualizar': 1}, follow_redirects=True)
    assert 'no se puede modificar' in r.get_data(as_text=True)
