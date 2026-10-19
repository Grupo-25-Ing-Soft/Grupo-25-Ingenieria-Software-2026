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
