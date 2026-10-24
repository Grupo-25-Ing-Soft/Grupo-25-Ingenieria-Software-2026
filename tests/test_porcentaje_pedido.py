import os

os.environ['SUPABASE_URL'] = 'https://supabase-falso.invalid'
os.environ['SUPABASE_PUBLISHABLE_KEY'] = 'clave-de-prueba'

import realFlask
from tests.supabase_falso import SupabaseFalso


def fila_pendiente(pedido, pendiente, stock, **extras):
    # Columnas de la vista real v_pendientes_despacho en Supabase (sin producto,
    # color ni talla; el stock viene en stock_bodega).
    return {
        'id_pedido': pedido,
        'numero_pedido': f'PED-{pedido:06d}',
        'estado_pedido': 'pendiente',
        'fecha_pedido': '2026-10-01',
        'id_cliente': 1,
        'nombre_cliente': 'Tienda Sur',
        'id_vendedor': 1,
        'nombre_vendedor': 'Ana',
        'id_detalle_pedido': 1,
        'id_variante': 7,
        'cantidad_pedida': pendiente,
        'cantidad_anulada': 0,
        'cantidad_despachada': 0,
        'cantidad_pendiente': pendiente,
        'stock_bodega': stock,
        **extras,
    }


def fila_detalle(pedido, pedida, despachada):
    # Columnas de la vista real v_detalle_pedido_pendiente (sí trae producto, color y talla).
    return {
        'id_pedido': pedido, 'numero_pedido': f'PED-{pedido:06d}', 'estado': 'pendiente',
        'id_detalle_pedido': 1, 'id_variante': 7, 'producto': 'Polera', 'color': 'Azul', 'talla': 'M',
        'cantidad_pedida': pedida, 'cantidad_anulada': 0, 'cantidad_despachada': despachada,
        'cantidad_pendiente': pedida - despachada,
    }


def preparar_cliente(tablas):
    # Las rutas exigen sesión: se entra como superusuario para probar solo el cálculo.
    tablas.setdefault('usuarios', [{
        'id_usuario': 1, 'nombre_usuario': 'admin', 'nombre': 'Admin',
        'id_rol': None, 'es_superusuario': True, 'activo': True,
    }])
    # Variante 7 tal como la devuelve PostgREST con los embeds colores(...) y tallas(...).
    tablas.setdefault('producto_variantes', [{
        'id_variante': 7, 'descripcion': 'Polera', 'colores': {'descripcion': 'Azul'},
        'tallas': {'talla': 'M', 'nombre': None},
    }])
    realFlask.supabase = SupabaseFalso(tablas)
    realFlask.app.config.update(TESTING=True, SECRET_KEY='test-secret')
    cliente = realFlask.app.test_client()
    with cliente.session_transaction() as sesion:
        sesion['id_usuario'] = 1
    return cliente


def test_cumplimiento_total():
    cliente = preparar_cliente({
        'v_pendientes_despacho': [fila_pendiente(10, 5, 8)],
    })

    respuesta = cliente.get('/verDetalle.html?id_pedido=10')

    assert respuesta.status_code == 200
    assert b'5 de 5 unidades pendientes se pueden cumplir (100.0 %)' in respuesta.data
    assert b'El stock se comparte entre pedidos pendientes' in respuesta.data
    assert b'Faltante' in respuesta.data


def test_muestra_producto_color_talla_y_stock_de_la_variante():
    # La vista real no trae los nombres: antes la tabla mostraba «—» en producto, color,
    # talla y stock, y 0 unidades cumplibles aunque hubiera stock.
    cliente = preparar_cliente({
        'v_pendientes_despacho': [fila_pendiente(15, 12, 24)],
    })

    html = cliente.get('/verDetalle.html?id_pedido=15').get_data(as_text=True)

    assert '<td>Polera</td>' in html and '<td>Azul</td>' in html and '<td>M</td>' in html
    assert '<td>24</td>' in html
    assert '12 de 12 unidades pendientes se pueden cumplir (100.0 %)' in html


def test_cumplimiento_parcial():
    cliente = preparar_cliente({
        'v_pendientes_despacho': [fila_pendiente(11, 8, 3)],
    })

    respuesta = cliente.get('/verDetalle.html?id_pedido=11')

    assert respuesta.status_code == 200
    assert b'3 de 8 unidades pendientes se pueden cumplir (37.5 %)' in respuesta.data
    assert b'<td>5</td>' in respuesta.data


def test_stock_cero_da_cumplimiento_cero():
    cliente = preparar_cliente({
        'v_pendientes_despacho': [fila_pendiente(12, 4, 0)],
    })

    respuesta = cliente.get('/verDetalle.html?id_pedido=12')

    assert respuesta.status_code == 200
    assert b'0 de 4 unidades pendientes se pueden cumplir (0.0 %)' in respuesta.data


def test_pedido_completo_sin_unidades_pendientes():
    cliente = preparar_cliente({
        'v_detalle_pedido_pendiente': [fila_detalle(13, 5, 5)],
    })

    respuesta = cliente.get('/verDetalle.html?id_pedido=13')

    assert respuesta.status_code == 200
    assert b'100 % \xe2\x80\x93 pedido completo' in respuesta.data
    assert b'aria-valuenow="100.0"' in respuesta.data
    assert b'<td>Polera</td>' in respuesta.data


def test_pedido_inexistente_muestra_aviso_y_vuelve_a_pedidos():
    cliente = preparar_cliente({})

    respuesta = cliente.get('/verDetalle.html?id_pedido=999', follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'No se encontr\xc3\xb3 el pedido' in respuesta.data
    assert b'Listado de pedidos' in respuesta.data


def test_pedido_anulado_muestra_aviso_y_vuelve_a_pedidos():
    cliente = preparar_cliente({
        'pedidos': [{'id_pedido': 14, 'estado': 'anulado'}],
    })

    respuesta = cliente.get('/verDetalle.html?id_pedido=14', follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'El pedido est\xc3\xa1 anulado' in respuesta.data


def test_id_no_numerico_no_rompe_y_vuelve_a_pedidos():
    cliente = preparar_cliente({})

    respuesta = cliente.get('/verDetalle.html?id_pedido=no-es-numero', follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'El identificador del pedido no es v\xc3\xa1lido' in respuesta.data
