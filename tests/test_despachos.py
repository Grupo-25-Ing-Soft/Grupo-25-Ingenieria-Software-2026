"""Despachos: número de guía y cantidades no editables (feedback punto 4)."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur', 'via_despacho': 'Starken'}],
        'bodegas': [{'id_bodega': 1, 'descripcion': 'Central'}],
        'pedidos': [{'id_pedido': 1, 'numero_pedido': 'PED-000001', 'cliente_asociado': 1, 'estado': 'pendiente'},
                    {'id_pedido': 2, 'numero_pedido': 'PED-000002', 'cliente_asociado': 1, 'estado': 'pendiente'}],
        'facturas': [{'id_factura': 1, 'folio': 900, 'pedido_asociado': 2, 'estado': 'vigente'}],
        'despachos': [], 'detalle_despachos': [], 'v_pendientes_despacho': [], 'inventario': [],
    })

    def registrar(p_id_pedido, p_id_bodega, p_lineas, p_id_factura=None, p_via_despacho=None,
                  p_observacion=None, p_usuario='Admin'):
        # Como la función de la base: la guía sale de la secuencia.
        numero = len(db.tablas['despachos']) + 7
        db.tablas['despachos'].append({'id_despacho': numero, 'numero_guia': f'GD-{numero:06d}', 'fecha': '2026-10-10',
                                       'id_pedido': p_id_pedido, 'id_factura': p_id_factura, 'id_bodega': p_id_bodega,
                                       'via_despacho': p_via_despacho, 'observacion': p_observacion,
                                       'estado': 'emitido', 'usuario_creacion': p_usuario})
        return numero

    db.rpc_registrar_despacho = registrar
    db.rpc_anular_despacho = lambda p_id_despacho, p_motivo, p_usuario: None
    return db


def test_crear_muestra_el_numero_de_guia(admin, base):
    r = admin.post('/despachos.html', data={'_method': 'post', 'idPedido': 1, 'idBodega': 1, 'cantidad_3': '2'},
                   follow_redirects=True)
    html = r.get_data(as_text=True)
    assert 'Despacho GD-000007 registrado exitosamente' in html and 'Guía GD-000007' in html
    assert 'Para cambiar cantidades, anula el despacho y crea uno nuevo' in html
    assert 'GD-000007' in admin.get('/despachos.html?guia=000007').get_data(as_text=True)
    assert 'No hay despachos para los filtros' in admin.get('/despachos.html?guia=GD-999').get_data(as_text=True)


def test_editar_solo_datos_informativos_y_factura_del_mismo_pedido(admin, base):
    admin.post('/despachos.html', data={'_method': 'post', 'idPedido': 1, 'idBodega': 1, 'cantidad_3': '2'})
    r = admin.post('/despachos.html', data={'_method': 'put', 'idDespacho': 7, 'idFactura': 1, 'viaDespacho': 'x'},
                   follow_redirects=True)
    assert 'no corresponde al pedido' in r.get_data(as_text=True)
    admin.post('/despachos.html', data={'_method': 'put', 'idDespacho': 7, 'idFactura': '', 'viaDespacho': 'Chilexpress',
                                        'observacion': 'Caja 2', 'cantidad_3': '99'})
    despacho = base.tablas['despachos'][0]
    assert despacho['via_despacho'] == 'Chilexpress' and despacho['observacion'] == 'Caja 2'
    assert not base.tablas['detalle_despachos']  # las cantidades no se tocan al editar
    lista = admin.get('/despachos.html').get_data(as_text=True)
    assert 'Para cambiar cantidades, anula el despacho y crea uno nuevo' in lista


def test_anular_informa_la_guia(admin, base):
    admin.post('/despachos.html', data={'_method': 'post', 'idPedido': 1, 'idBodega': 1, 'cantidad_3': '2'})
    r = admin.post('/despachos.html', data={'_method': 'anular', 'idDespacho': 7, 'motivo': 'Error de bodega'},
                   follow_redirects=True)
    assert 'Despacho GD-000007 anulado' in r.get_data(as_text=True)
    assert ('anular_despacho', {'p_id_despacho': 7, 'p_motivo': 'Error de bodega', 'p_usuario': 'admin'}) in base.llamadas
