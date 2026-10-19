"""Pedidos y su detalle (RF-022 a RF-026, CU-22.1 a CU-22.4, CU-24.1 y CU-25)."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}],
        'vendedores': [{'id_vendedor': 1, 'nombre': 'Ana Vendedora'}],
        'pedidos': [{'id_pedido': 1, 'numero_pedido': 'PED-000001', 'cliente_asociado': 1, 'vendedor_asociado': 1,
                     'fecha_pedido': '2026-10-01', 'fecha_entrega': None, 'estado': 'pendiente'}],
        'producto_variantes': [{'id_variante': 5, 'id_producto': 2, 'id_color': 1, 'id_talla': 1,
                                'descripcion': 'Cuadro algodon', 'precio_venta': 2990, 'activo': True,
                                'ean_manual': True, 'codigo_ean': '9900000000001'}],
        'detalle_pedidos': [], 'despachos': [], 'detalle_despachos': [], 'facturas': [], 'cortes': [],
    })
    return db


def test_crear_pedido_lleva_al_detalle(admin, base):
    r = admin.post('/pedidos.html', data={'_method': 'post', 'IDClienteCrear': 1, 'IDVendedorCrear': 1,
                                          'fechaPedidoCrear': '2026-10-05', 'fechaLimiteCrear': '2026-10-20'})
    assert r.headers['Location'].endswith('/crudDetallePedido.html?id_pedido=2')
    assert base.tablas['pedidos'][-1]['cliente_asociado'] == 1


def test_fecha_de_entrega_anterior_se_rechaza(admin, base):
    r = admin.post('/pedidos.html', data={'_method': 'post', 'IDClienteCrear': 1, 'IDVendedorCrear': 1,
                                          'fechaPedidoCrear': '2026-10-05', 'fechaLimiteCrear': '2026-10-01'},
                   follow_redirects=True)
    assert 'no puede ser anterior' in r.get_data(as_text=True) and len(base.tablas['pedidos']) == 1


def test_lineas_con_subtotal_numerico_y_total_del_pedido(admin, base):
    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post', 'idVarianteCrear': 5,
                                                            'cantidadCrear': '3', 'precioUnitarioCrear': '2990'})
    linea = base.tablas['detalle_pedidos'][0]
    assert linea['subtotal'] == 8970 and linea['cantidad'] == 3 and linea['id_pedido'] == 1
    html = admin.get('/pedidos.html').get_data(as_text=True)
    assert '$8.970' in html and 'Tienda Sur' in html and 'Ana Vendedora' in html

    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'put', 'idDetalleActualizar': 1,
                                                            'cantidadActualizar': '4', 'precioUnitarioActualizar': '3000'})
    assert base.tablas['detalle_pedidos'][0]['subtotal'] == 12000
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert 'Cuadro algodon' in detalle and '$12.000' in detalle

    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'delete', 'idDetalleBorrar': 1})
    assert base.tablas['detalle_pedidos'] == []


def test_no_se_repite_la_variante_ni_se_baja_de_lo_despachado(admin, base):
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 5,
                                           'cantidad_anulada': 0, 'precio_unitario': 100, 'subtotal': 500})
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post', 'idVarianteCrear': 5,
                                                                'cantidadCrear': '1', 'precioUnitarioCrear': '1'},
                   follow_redirects=True)
    assert 'ya está en el pedido' in r.get_data(as_text=True)

    base.tablas['despachos'].append({'id_despacho': 1, 'id_pedido': 1, 'estado': 'emitido'})
    base.tablas['detalle_despachos'].append({'id_detalle_despacho': 1, 'id_despacho': 1, 'id_detalle_pedido': 1, 'cantidad': 4})
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'put', 'idDetalleActualizar': 1,
                                                                'cantidadActualizar': '3', 'precioUnitarioActualizar': '100'},
                   follow_redirects=True)
    assert 'Ya se despacharon 4 unidades' in r.get_data(as_text=True)
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'delete', 'idDetalleBorrar': 1},
                   follow_redirects=True)
    assert 'tiene despachos registrados' in r.get_data(as_text=True) and base.tablas['detalle_pedidos']


def test_pedido_con_despacho_no_se_elimina_ni_se_anula(admin, base):
    base.tablas['despachos'].append({'id_despacho': 1, 'id_pedido': 1, 'estado': 'emitido'})
    r = admin.post('/pedidos.html', data={'_method': 'delete', 'idPedidoBorrar': 1}, follow_redirects=True)
    assert 'no se puede eliminar, solo anular' in r.get_data(as_text=True)
    r = admin.post('/pedidos.html', data={'_method': 'anular', 'idPedidoAnular': 1, 'motivoAnulacion': 'x'},
                   follow_redirects=True)
    assert 'tiene despachos emitidos' in r.get_data(as_text=True)
    assert base.tablas['pedidos'][0]['estado'] == 'pendiente'


def test_anular_y_luego_no_se_edita(admin, base):
    admin.post('/pedidos.html', data={'_method': 'anular', 'idPedidoAnular': 1, 'motivoAnulacion': 'Cliente desiste'})
    pedido = base.tablas['pedidos'][0]
    assert pedido['estado'] == 'anulado' and pedido['motivo_anulacion'] == 'Cliente desiste'
    assert pedido['usuario_anulacion'] == 'admin' and pedido['fecha_anulacion']
    r = admin.post('/pedidos.html', data={'_method': 'put', 'IdPedidoActualizar': 1, 'IDClienteActualizar': 1,
                                          'IDVendedorActualizar': 1, 'fechaPedidoActualizar': '2026-10-01'},
                   follow_redirects=True)
    assert 'no se puede modificar' in r.get_data(as_text=True)
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post'}, follow_redirects=True)
    assert 'su detalle no se puede modificar' in r.get_data(as_text=True)


def test_eliminar_pedido_sin_asociados_borra_sus_lineas(admin, base):
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 1})
    admin.post('/pedidos.html', data={'_method': 'delete', 'idPedidoBorrar': 1})
    assert base.tablas['pedidos'] == [] and base.tablas['detalle_pedidos'] == []


def test_filtros_por_cliente_y_fecha(admin, base):
    assert 'PED-000001' in admin.get('/pedidos.html?cliente=sur&desde=2026-10-01').get_data(as_text=True)
    assert 'No hay pedidos para los filtros aplicados' in admin.get('/pedidos.html?desde=2026-11-01').get_data(as_text=True)
