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


def test_lineas_sin_precio_propio_y_total_del_pedido(admin, base):
    # Feedback Inc. 4: detalle_pedidos no guarda precio; el subtotal usa el precio de la variante.
    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post', 'idVarianteCrear': 5, 'cantidadCrear': '3'})
    linea = base.tablas['detalle_pedidos'][0]
    assert linea['cantidad'] == 3 and linea['id_pedido'] == 1
    assert 'precio_unitario' not in linea and 'subtotal' not in linea
    html = admin.get('/pedidos.html').get_data(as_text=True)
    assert '$8.970' in html and 'Tienda Sur' in html and 'Ana Vendedora' in html

    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'put', 'idDetalleActualizar': 1,
                                                            'cantidadActualizar': '4'})
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert 'Cuadro algodon' in detalle and '$11.960' in detalle
    assert 'name="precioUnitario' not in detalle  # el precio no se edita en el detalle

    admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'delete', 'idDetalleBorrar': 1})
    assert base.tablas['detalle_pedidos'] == []


def test_cambiar_el_precio_de_la_variante_cambia_el_total(admin, base):
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 2,
                                           'cantidad_anulada': 0})
    assert '$5.980' in admin.get('/pedidos.html').get_data(as_text=True)
    base.tablas['producto_variantes'][0]['precio_venta'] = 3500
    assert '$7.000' in admin.get('/pedidos.html').get_data(as_text=True)


def test_no_se_repite_la_variante_ni_se_baja_de_lo_despachado(admin, base):
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 5,
                                           'cantidad_anulada': 0})
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post', 'idVarianteCrear': 5,
                                                                'cantidadCrear': '1'},
                   follow_redirects=True)
    assert 'ya está en el pedido' in r.get_data(as_text=True)

    base.tablas['despachos'].append({'id_despacho': 1, 'id_pedido': 1, 'estado': 'emitido'})
    base.tablas['detalle_despachos'].append({'id_detalle_despacho': 1, 'id_despacho': 1, 'id_detalle_pedido': 1, 'cantidad': 4})
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'put', 'idDetalleActualizar': 1,
                                                                'cantidadActualizar': '3'},
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


def test_precio_sugerido_segun_lista_del_cliente(admin, base):
    # CU-24.1 paso 5: lista 1 = precio mayor; otra lista usa su precio; liquidación manda.
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '$2.990' in detalle and 'lista de precios 1' in detalle

    base.tablas['clientes'][0]['lista_precios'] = 2
    base.tablas['variante_precios_lista'] = [{'id_variante': 5, 'lista_precios': 2, 'precio': 2500}]
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '$2.500' in detalle and 'lista de precios 2' in detalle

    base.tablas['producto_variantes'][0].update({'en_liquidacion': True, 'precio_liquidacion': 1990})
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '$1.990 (liquidación)' in detalle


def test_vendedor_del_cliente_en_el_formulario(admin, base):
    base.tablas['clientes'][0]['id_vendedor'] = 1
    assert 'data-vendedor="1"' in admin.get('/pedidos.html').get_data(as_text=True)


@pytest.mark.parametrize('estado,texto', [('finalizado', 'finalizado'), ('pagado', 'pagado'),
                                          ('despachado', 'despachado')])
def test_pedidos_cerrados(admin, base, estado, texto):
    # Despachado, pagado, finalizado y anulado ya no se modifican, anulan ni despachan.
    base.tablas['pedidos'][0]['estado'] = estado
    r = admin.post('/pedidos.html', data={'_method': 'anular', 'idPedidoAnular': 1, 'motivoAnulacion': 'x'},
                   follow_redirects=True)
    assert f'ya está {texto}: no se puede anular' in r.get_data(as_text=True)
    r = admin.post('/crudDetallePedido.html?id_pedido=1', data={'_method': 'post', 'idVarianteCrear': 5,
                                                                'cantidadCrear': '1'},
                   follow_redirects=True)
    assert 'su detalle no se puede modificar' in r.get_data(as_text=True) and base.tablas['detalle_pedidos'] == []
    assert f'El pedido está {texto}: su detalle es solo de consulta' in \
        admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)


def test_filtro_con_los_estados_del_documento_0(admin, base):
    base.tablas['pedidos'][0]['estado'] = 'listo_para_despacho'
    html = admin.get('/pedidos.html').get_data(as_text=True)
    for texto in ('Registrado', 'Pendiente', 'En producción', 'Listo para despacho', 'Despachado', 'Pagado',
                  'Anulado', 'Finalizado'):
        assert f'>{texto}</option>' in html
    assert '>Listo para despacho</span>' in html  # la etiqueta, no el código
    assert 'PED-000001' in admin.get('/pedidos.html?estado=listo_para_despacho').get_data(as_text=True)
    assert 'PED-000001' in admin.get('/pedidos.html?estado=confirmado').get_data(as_text=True)  # ya no existe: se ignora


def test_crear_y_editar_con_todos_los_campos(admin, base):
    admin.post('/pedidos.html', data={'_method': 'post', 'IDClienteCrear': 1, 'IDVendedorCrear': 1,
                                      'fechaPedidoCrear': '2026-10-05', 'fechaLimiteCrear': '2026-10-20',
                                      'estadoCrear': 'registrado', 'codigoCrear': 'A-77',
                                      'observacionesCrear': 'Entregar en bodega 2'})
    nuevo = base.tablas['pedidos'][-1]
    assert (nuevo['estado'], nuevo['codigo'], nuevo['observaciones']) == ('registrado', 'A-77', 'Entregar en bodega 2')
    admin.post('/pedidos.html', data={'_method': 'put', 'IdPedidoActualizar': nuevo['id_pedido'], 'IDClienteActualizar': 1,
                                      'IDVendedorActualizar': 1, 'fechaPedidoActualizar': '2026-10-05',
                                      'estadoActualizar': 'en_produccion', 'observacionesActualizar': ''})
    assert (nuevo['estado'], nuevo['observaciones']) == ('en_produccion', None)
    html = admin.get('/pedidos.html').get_data(as_text=True)
    for columna in ('Neto', 'Descuento', 'Impuesto', 'Total', 'Observaciones'):
        assert f'>{columna}</th>' in html
    assert 'name="montoTotalActualizar" disabled' in html  # los montos se muestran, no se editan


@pytest.mark.parametrize('estado', ['despachado', 'anulado', 'entregado'])
def test_el_formulario_no_acepta_estados_del_sistema(admin, base, estado):
    r = admin.post('/pedidos.html', data={'_method': 'put', 'IdPedidoActualizar': 1, 'IDClienteActualizar': 1,
                                          'IDVendedorActualizar': 1, 'fechaPedidoActualizar': '2026-10-01',
                                          'estadoActualizar': estado}, follow_redirects=True)
    assert 'El estado elegido no es válido' in r.get_data(as_text=True)
    assert base.tablas['pedidos'][0]['estado'] == 'pendiente'


def test_lista_y_detalle_muestran_el_mismo_total_sin_anuladas(admin, base):
    # AUD-019: el detalle sumaba cantidad x precio sin restar las unidades anuladas.
    base.tablas['producto_variantes'][0]['precio_venta'] = 1000
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 10,
                                           'cantidad_anulada': 4})
    lista = admin.get('/pedidos.html').get_data(as_text=True)
    detalle = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '$6.000' in lista and '$10.000' not in lista
    assert detalle.count('$6.000') == 3 and '$10.000' not in detalle  # línea, neto y total (sin descuento ni impuesto)


def test_montos_con_descuentos_del_cliente_e_impuesto(admin, base):
    # 10 % y 5 % en cascada = 14,50 % (igual que registrar_despacho): sobre $6.000 se descuentan $870.
    # Impuesto 19 % sobre $5.130 = $975 (redondeado); total $6.105.
    base.tablas['parametros_sistema'] = [{'id': 1, 'porcentaje_impuesto': 19}]
    base.tablas['clientes'][0].update({'descuento_1': 10, 'descuento_2': 5, 'descuento_3': 0})
    base.tablas['producto_variantes'][0]['precio_venta'] = 1000
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 10,
                                           'cantidad_anulada': 4})
    html = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '10.00 % · 5.00 % · 0.00 % = 14.50 %' in html
    assert '−$870' in html and 'Impuesto (19 %)' in html and '$975' in html and '$6.105' in html
    lista = admin.get('/pedidos.html').get_data(as_text=True)
    assert all(monto in lista for monto in ('$6.000', '−$870', '$975', '$6.105'))


def test_detalle_sin_descuentos_resta_cero(admin, base):
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_pedido': 1, 'id_variante': 5, 'cantidad': 2,
                                           'cantidad_anulada': 0})
    html = admin.get('/crudDetallePedido.html?id_pedido=1').get_data(as_text=True)
    assert '= 0.00 %' in html and '−$0' in html and html.count('$5.980') == 3
