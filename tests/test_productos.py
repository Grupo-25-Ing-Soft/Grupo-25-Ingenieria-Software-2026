"""Productos y variantes (RF-013/014, CU-13.1 a CU-13.5)."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.setdefault('producto_variantes', [])
    db.tablas.update({'detalle_pedidos': [], 'inventario': [], 'cortes': []})
    return db


def test_crear_con_variantes_genera_ean_y_precio(admin, base):
    # Colores BLANCO(1)/NEGRO(2); tallas S(1)/M(2) de con_datos_de_ejemplo().
    r = admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'Colaless', 'codigoCrear': '430',
                                            'codigoEanCrear': '430', 'precioCrear': '2990',
                                            'variante': ['1-1', '2-2'], 'precioVariante_1-1': '3190',
                                            'precioVariante_2-2': ''}, follow_redirects=True)
    assert 'Producto creado exitosamente con 2 variantes' in r.get_data(as_text=True)
    producto = base.tablas['productos'][-1]
    variantes = [v for v in base.tablas['producto_variantes'] if v['id_producto'] == producto['id_producto']]
    assert [(v['id_color'], v['id_talla'], v['precio_venta']) for v in variantes] == [(1, 1, 3190), (2, 2, 2990)]
    # EAN de la variante: 99 + 430 + 0001 + 010 + verificador (fn_generar_ean).
    assert variantes[0]['codigo_ean'].startswith('994300001010') and len(variantes[0]['codigo_ean']) == 13
    html = admin.get('/productos.html').get_data(as_text=True)
    assert 'BLANCO · S · $3.190' in html and 'NEGRO · M · $2.990' in html


def test_editar_variantes_agrega_desactiva_y_cambia_precio(admin, base):
    admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'Colaless', 'precioCrear': '2990',
                                        'variante': ['1-1']})
    producto = base.tablas['productos'][-1]['id_producto']
    variante = base.tablas['producto_variantes'][-1]['id_variante']
    r = admin.post('/productos.html', data={'_method': 'variantes', 'idProductoVariantes': producto,
                                            f'precio_{variante}': '3500',  # sin activo_ => se desactiva
                                            'nueva': ['3-2'], 'precioNueva_3-2': '4000'}, follow_redirects=True)
    assert '1 nueva(s), 1 desactivada(s)' in r.get_data(as_text=True)
    variantes = {v['id_variante']: v for v in base.tablas['producto_variantes'] if v['id_producto'] == producto}
    assert variantes[variante]['activo'] is False and variantes[variante]['precio_venta'] == 3500
    nueva = [v for v in variantes.values() if v['id_variante'] != variante][0]
    assert (nueva['id_color'], nueva['id_talla'], nueva['precio_venta'], nueva['activo']) == (3, 2, 4000, True)

    # Reactivar la variante.
    admin.post('/productos.html', data={'_method': 'variantes', 'idProductoVariantes': producto,
                                        f'activo_{variante}': 'on', f'activo_{nueva["id_variante"]}': 'on'})
    assert all(v['activo'] for v in base.tablas['producto_variantes'] if v['id_producto'] == producto)


def test_no_se_elimina_un_producto_con_pedidos(admin, base):
    admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'Colaless', 'variante': ['1-1']})
    producto = base.tablas['productos'][-1]['id_producto']
    variante = base.tablas['producto_variantes'][-1]['id_variante']
    base.tablas['detalle_pedidos'].append({'id_detalle_pedido': 1, 'id_variante': variante})
    r = admin.post('/productos.html', data={'_method': 'delete', 'idProductoBorrar': producto}, follow_redirects=True)
    assert 'tiene pedidos asociados' in r.get_data(as_text=True)
    base.tablas['detalle_pedidos'].clear()
    admin.post('/productos.html', data={'_method': 'delete', 'idProductoBorrar': producto})
    assert not any(p['id_producto'] == producto for p in base.tablas['productos'])
    assert not any(v['id_producto'] == producto for v in base.tablas['producto_variantes'])


def test_validaciones(admin, base):
    r = admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': ' '}, follow_redirects=True)
    assert 'descripción del producto es obligatoria' in r.get_data(as_text=True)
    r = admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'X', 'variante': ['1-1'],
                                            'precioVariante_1-1': '-3'}, follow_redirects=True)
    assert 'precio de cada variante' in r.get_data(as_text=True)
