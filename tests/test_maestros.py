"""Archivos maestros simples con el patrón de colores (feedback puntos 9, 10 y 13)."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({'producto_variantes': [], 'inventario': [], 'clientes': [], 'zona_venta': []})
    return db


# ------------------------------------------------------------------ tallas
def test_tallas_crear_editar_y_mensajes(admin, base):
    r = admin.post('/tallas.html', data={'_method': 'post', 'tallaCrear': 'XL', 'nombreCrear': 'XL', 'codigoEanCrear': '014'},
                   follow_redirects=True)
    assert 'Talla XL creada exitosamente' in r.get_data(as_text=True)
    nueva = base.tablas['tallas'][-1]
    r = admin.post('/tallas.html', data={'_method': 'put', 'idTallaActualizar': nueva['id_talla'], 'tallaActualizar': 'XG',
                                         'nombreActualizar': 'XG', 'codigoEanActualizar': '015'}, follow_redirects=True)
    assert 'Talla XG actualizada exitosamente' in r.get_data(as_text=True)
    assert base.tablas['tallas'][-1]['codigo_ean'] == '015'
    html = admin.get('/tallas.html').get_data(as_text=True)
    assert 'data-modal="#actualizarModal"' in html and 'Nueva talla' in html


@pytest.mark.parametrize('datos,mensaje', [
    ({'tallaCrear': ''}, 'Complete el campo «Código de talla»'),
    ({'tallaCrear': 'XXL'}, 'admite hasta 2 caracteres'),
    ({'tallaCrear': '1'}, 'Ya existe la talla con código de talla 1'),
    ({'tallaCrear': 'XS', 'codigoEanCrear': '1A'}, 'solo puede tener números'),
])
def test_tallas_validaciones(admin, base, datos, mensaje):
    antes = len(base.tablas['tallas'])
    r = admin.post('/tallas.html', data={'_method': 'post', **datos}, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True) and len(base.tablas['tallas']) == antes


def test_tallas_en_uso_no_se_eliminan(admin, base):
    base.tablas['producto_variantes'].append({'id_variante': 1, 'id_producto': 1, 'id_color': 1, 'id_talla': 1,
                                              'ean_manual': True, 'codigo_ean': '9900000000001'})
    r = admin.post('/tallas.html', data={'_method': 'delete', 'idTallaBorrar': 1}, follow_redirects=True)
    assert 'está en uso en variantes de producto y no se puede eliminar' in r.get_data(as_text=True)
    admin.post('/tallas.html', data={'_method': 'delete', 'idTallaBorrar': 3})
    assert [t['id_talla'] for t in base.tablas['tallas']] == [1, 2]


def test_tallas_busqueda(admin, base):
    assert '<td>M</td>' in admin.get('/tallas.html?q=m').get_data(as_text=True)
    assert 'No se encontraron resultados' in admin.get('/tallas.html?q=zz').get_data(as_text=True)


# ------------------------------------------------------------------ zonas de venta
def zona(admin, **cambios):
    datos = {'_method': 'post', 'nombreCrear': 'Zona Sur', 'codigoCrear': 'SUR', 'descripcionCrear': 'Regiones VIII a X'}
    datos.update(cambios)
    return admin.post('/zonasVenta.html', data=datos, follow_redirects=True)


def test_zonas_crear_con_nombre_primero(admin, base):
    assert 'Zona de venta Zona Sur creada exitosamente' in zona(admin).get_data(as_text=True)
    assert base.tablas['zona_venta'][0] == {'id_zona_venta': 1, 'nombre': 'Zona Sur', 'codigo': 'SUR',
                                            'descripcion': 'Regiones VIII a X'}
    html = admin.get('/zonasVenta.html').get_data(as_text=True)
    encabezados = html.split('<thead>')[1].split('</thead>')[0]
    assert encabezados.index('Nombre') < encabezados.index('Código') < encabezados.index('Descripción')


@pytest.mark.parametrize('cambios,mensaje', [
    ({'descripcionCrear': ''}, 'Complete el campo «Descripción»'),
    ({'codigoCrear': 'NORT'}, 'admite hasta 3 caracteres'),
])
def test_zonas_validaciones(admin, base, cambios, mensaje):
    assert mensaje in zona(admin, **cambios).get_data(as_text=True) and base.tablas['zona_venta'] == []


def test_zonas_codigo_unico_editar_y_en_uso(admin, base):
    zona(admin)
    assert 'Ya existe la zona de venta con código SUR' in zona(admin, nombreCrear='Otra').get_data(as_text=True)
    admin.post('/zonasVenta.html', data={'_method': 'put', 'idZonaVentaActualizar': 1, 'nombreActualizar': 'Sur',
                                         'codigoActualizar': 'SUR', 'descripcionActualizar': 'VIII a XII'})
    assert base.tablas['zona_venta'][0]['descripcion'] == 'VIII a XII'
    base.tablas['clientes'].append({'id_cliente': 1, 'id_zona_venta': 1})
    r = admin.post('/zonasVenta.html', data={'_method': 'delete', 'idZonaVentaBorrar': 1}, follow_redirects=True)
    assert 'está en uso en clientes y no se puede eliminar' in r.get_data(as_text=True) and base.tablas['zona_venta']
    base.tablas['clientes'].clear()
    admin.post('/zonasVenta.html', data={'_method': 'delete', 'idZonaVentaBorrar': 1})
    assert base.tablas['zona_venta'] == []


# ------------------------------------------------------------------ bodegas e inventario
@pytest.fixture
def bodegas(base):
    base.tablas.update({
        'bodegas': [{'id_bodega': 1, 'descripcion': 'Central', 'codigo': 'B01'},
                    {'id_bodega': 2, 'descripcion': 'Taller', 'codigo': 'B02'}],
        'despachos': [],
        'producto_variantes': [{'id_variante': 7, 'id_producto': 2, 'id_color': 1, 'id_talla': 2,
                                'descripcion': 'Cuadro algodon', 'activo': True, 'ean_manual': True,
                                'codigo_ean': '9900000000017'}],
        'inventario': [{'id_inventario': 1, 'id_bodega': 1, 'id_variante': 7, 'id_talla': 2, 'id_color': 1,
                        'cantidad': 24, 'cantidad_defectuosa': 3, 'fecha_actualizacion': '2026-10-01T10:00:00+00:00'},
                       {'id_inventario': 2, 'id_bodega': 2, 'id_variante': 7, 'id_talla': 2, 'id_color': 1,
                        'cantidad': 5, 'cantidad_defectuosa': 0}],
    })
    return base


def test_sin_resultados_solo_cuando_no_hay_bodegas(admin, base):
    base.tablas['bodegas'] = []
    assert 'Sin resultados todavía' in admin.get('/bodegas.html').get_data(as_text=True)
    base.tablas['bodegas'] = [{'id_bodega': 1, 'descripcion': 'Central'}]
    assert 'Sin resultados todavía' not in admin.get('/bodegas.html').get_data(as_text=True)


def test_inventario_de_la_bodega_seleccionada(admin, bodegas):
    html = admin.get('/bodegas.html').get_data(as_text=True)  # por defecto la primera bodega
    tabla = html.split('Inventario por bodega')[1]
    assert 'Cuadro algodon' in tabla and '<td>M</td>' in tabla and '<td>BLANCO</td>' in tabla
    assert '<td class="text-end">24</td>' in tabla and '<td class="text-end">3</td>' in tabla
    assert '24 unidades disponibles · 3 defectuosas' in tabla and '01/10/2026' in tabla
    otra = admin.get('/bodegas.html?bodega=2').get_data(as_text=True).split('Inventario por bodega')[1]
    assert '<td class="text-end">5</td>' in otra and '<td class="text-end">24</td>' not in otra


def test_registrar_editar_y_borrar_existencias(admin, bodegas):
    r = admin.post('/bodegas.html', data={'_method': 'inventario_post', 'idBodegaInventario': 1, 'idVarianteInventario': 7,
                                          'cantidadInventario': '1'}, follow_redirects=True)
    assert 'ya tiene existencias en la bodega' in r.get_data(as_text=True)
    base_inv = bodegas.tablas['inventario']
    bodegas.tablas['inventario'] = [f for f in base_inv if f['id_bodega'] != 2]
    admin.post('/bodegas.html', data={'_method': 'inventario_post', 'idBodegaInventario': 2, 'idVarianteInventario': 7,
                                      'cantidadInventario': '10', 'cantidadDefectuosaInventario': '2'})
    nueva = bodegas.tablas['inventario'][-1]
    assert (nueva['id_bodega'], nueva['id_talla'], nueva['id_color'], nueva['cantidad'], nueva['cantidad_defectuosa']) == (2, 2, 1, 10, 2)
    r = admin.post('/bodegas.html', data={'_method': 'inventario_put', 'idInventario': 1, 'cantidadInventario': 'x'},
                   follow_redirects=True)
    assert 'número entero' in r.get_data(as_text=True)
    admin.post('/bodegas.html', data={'_method': 'inventario_put', 'idInventario': 1, 'cantidadInventario': '20',
                                      'cantidadDefectuosaInventario': '4'})
    assert (bodegas.tablas['inventario'][0]['cantidad'], bodegas.tablas['inventario'][0]['cantidad_defectuosa']) == (20, 4)
    admin.post('/bodegas.html', data={'_method': 'inventario_delete', 'idInventario': 1})
    assert [f['id_inventario'] for f in bodegas.tablas['inventario']] == [2]


def test_bodega_con_stock_no_se_elimina(admin, bodegas):
    r = admin.post('/bodegas.html', data={'_method': 'delete', 'idBodegaBorrar': 1}, follow_redirects=True)
    assert 'está en uso en inventario y no se puede eliminar' in r.get_data(as_text=True)
    assert 'Ya existe la bodega con código de bodega B02' in admin.post('/bodegas.html', data={
        '_method': 'post', 'descripcionCrear': 'Otra', 'codigoCrear': 'B02'}, follow_redirects=True).get_data(as_text=True)


# ------------------------------------------------------------------ colores y vendedores
def test_colores_con_flash_y_codigo_unico(admin, base):
    r = admin.post('/colores.html', data={'_method': 'post', 'descripcionCrear': 'ROJO', 'codigoCrear': 'RO',
                                          'codigoEanCrear': '0005'}, follow_redirects=True)
    assert 'Color ROJO creado exitosamente' in r.get_data(as_text=True)  # antes devolvía texto plano
    assert 'Ya existe el color con código de color BL' in admin.post('/colores.html', data={
        '_method': 'post', 'descripcionCrear': 'Otro', 'codigoCrear': 'BL'}, follow_redirects=True).get_data(as_text=True)
    assert 'Ya hay otro color con el código EAN 0001' in admin.post('/colores.html', data={
        '_method': 'post', 'descripcionCrear': 'Otro', 'codigoEanCrear': '0001'}, follow_redirects=True).get_data(as_text=True)
    base.tablas['inventario'].append({'id_inventario': 1, 'id_color': 1})
    r = admin.post('/colores.html', data={'_method': 'delete', 'idColorBorrar': 1}, follow_redirects=True)
    assert 'está en uso en inventario y no se puede eliminar' in r.get_data(as_text=True)


def test_vendedores_rut_valido_y_en_uso(admin, base):
    base.tablas.update({'vendedores': [], 'pedidos': []})
    datos = {'_method': 'post', 'nombreCrear': 'Ana Pérez', 'codigoCrear': 'V01', 'rutCrear': '12.345.678',
             'digVerCrear': '5', 'porComiCrear': '4.5'}
    assert 'no es válido' in admin.post('/vendedores.html', data={**datos, 'digVerCrear': '4'},
                                        follow_redirects=True).get_data(as_text=True)
    assert 'entre 0 y 100' in admin.post('/vendedores.html', data={**datos, 'porComiCrear': '120'},
                                         follow_redirects=True).get_data(as_text=True)
    assert 'Vendedor Ana Pérez creado exitosamente' in admin.post('/vendedores.html', data=datos,
                                                                 follow_redirects=True).get_data(as_text=True)
    assert base.tablas['vendedores'][0] == {'id_vendedor': 1, 'nombre': 'Ana Pérez', 'codigo': 'V01', 'rut': '12345678',
                                            'digito_verificador': '5', 'porcentaje_comision': 4.5}
    assert 'Ya existe el vendedor con rut 12345678' in admin.post('/vendedores.html', data={**datos, 'codigoCrear': 'V02'},
                                                                  follow_redirects=True).get_data(as_text=True)
    base.tablas['pedidos'].append({'id_pedido': 1, 'vendedor_asociado': 1})
    r = admin.post('/vendedores.html', data={'_method': 'delete', 'idVendedorBorrar': 1}, follow_redirects=True)
    assert 'está en uso en pedidos' in r.get_data(as_text=True)
    assert '4.5%' in admin.get('/vendedores.html').get_data(as_text=True)


@pytest.mark.parametrize('url', ['/colores.html', '/tallas.html', '/zonasVenta.html', '/vendedores.html', '/bodegas.html',
                                 '/clientes.html', '/productos.html'])
def test_todos_los_maestros_tienen_el_mismo_patron(admin, base, url):
    base.tablas.setdefault('vendedores', [{'id_vendedor': 1, 'nombre': 'Ana', 'rut': '1', 'digito_verificador': '9'}])
    base.tablas.setdefault('bodegas', [{'id_bodega': 1, 'descripcion': 'Central'}])
    base.tablas['zona_venta'] = [{'id_zona_venta': 1, 'nombre': 'Sur', 'descripcion': 'Sur'}]
    base.tablas['clientes'] = [{'id_cliente': 1, 'nombre': 'Tienda', 'rut': '1', 'digito_verificador': '9'}]
    html = admin.get(url).get_data(as_text=True)
    for parte in ('id="crearModal"', 'id="actualizarModal"', 'id="borrarModal"', 'data-modal="#actualizarModal"',
                  'data-modal="#borrarModal"', 'name="q"'):
        assert parte in html, (url, parte)
