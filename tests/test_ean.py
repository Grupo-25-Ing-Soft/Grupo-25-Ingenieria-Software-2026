"""Códigos EAN propios de la empresa y emisión de etiquetas (RF-015, RF-016, RF-017)."""
import pytest

import ean13

# Códigos leídos de etiquetas reales: (artículo, color, talla, EAN impreso)
ETIQUETAS_REALES = [
    ('414', 'BLANCO', 'S', '9941400010101'),
    ('414', 'NEGRO', 'S', '9941400030109'),
    ('414', 'BEIGE', 'S', '9941403970105'),
    ('412', 'NEGRO', 'S', '9941200030101'),
    ('415', 'BLANCO', 'M', '9941500010117'),
    ('425', 'BEIGE', 'M', '9942503970118'),
]


def ids(db, articulo, color, talla):
    p = next(f['id_producto'] for f in db.tablas['productos'] if f['codigo'] == articulo)
    c = next(f['id_color'] for f in db.tablas['colores'] if f['descripcion'] == color)
    t = next(f['id_talla'] for f in db.tablas['tallas'] if f['nombre'] == talla)
    return p, c, t


# ---------------------------------------------------------------- dibujo del código

@pytest.mark.parametrize('ean', [e for *_, e in ETIQUETAS_REALES] + ['4006381333931'])
def test_digito_verificador(ean):
    assert ean13.digito_verificador(ean[:12]) == ean[12]


def test_estructura_de_barras():
    barras = ean13.modulos('9941400010101')
    assert len(barras) == 95
    assert barras.startswith('101') and barras.endswith('101') and barras[45:50] == '01010'
    # Ejemplo de la norma EAN-13 (4006381333931), verificado contra reportlab.
    assert ean13.modulos('4006381333931') == (
        '10100011010100111010111101111010001001011001101010100001010000101000010111010010000101100110101')


def test_svg_tiene_30_barras():
    # Todo EAN-13 tiene exactamente 30 barras negras.
    assert ean13.svg('9941400010101').count('<rect') == 30


def test_codigo_invalido():
    with pytest.raises(ValueError):
        ean13.modulos('123')


# ---------------------------------------------------------------- generación

@pytest.mark.parametrize('articulo,color,talla,esperado', ETIQUETAS_REALES)
def test_genera_los_codigos_de_las_etiquetas_reales(db, articulo, color, talla, esperado):
    assert db.generar_ean(*ids(db, articulo, color, talla)) == esperado


def test_talla_sin_codigo_no_genera(db):
    assert db.generar_ean(*ids(db, '414', 'BLANCO', 'L')) is None


# ---------------------------------------------------------------- pantallas

def test_emision_imprime_cantidad_por_talla(admin, db):
    p, c, s = ids(db, '414', 'BLANCO', 'S')
    _, _, m = ids(db, '414', 'BLANCO', 'M')
    r = admin.post('/emisionEAN.html', data={'idProducto': p, 'idColor': c, f'cantidad_{s}': '4', f'cantidad_{m}': '2'})
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert html.count('class="etiqueta"') == 6
    assert html.count('9 941400 010101') == 4 and html.count('9 941400 010118') == 2
    assert html.count('class="fila"') == 2      # 3 etiquetas por fila
    assert 'T:S' in html and 'BLANCO' in html and '414' in html


def test_emision_crea_las_variantes(admin, db):
    p, c, s = ids(db, '425', 'BEIGE', 'M')
    admin.post('/emisionEAN.html', data={'idProducto': p, 'idColor': c, f'cantidad_{s}': '1'})
    variante = db.tablas['producto_variantes'][-1]
    assert variante['codigo_ean'] == '9942503970118'


def test_emision_rechaza_talla_sin_codigo(admin, db):
    p, c, l = ids(db, '414', 'BLANCO', 'L')
    r = admin.post('/emisionEAN.html', data={'idProducto': p, 'idColor': c, f'cantidad_{l}': '3'}, follow_redirects=True)
    assert 'Falta el código EAN' in r.get_data(as_text=True) and 'L' in r.get_data(as_text=True)


@pytest.mark.parametrize('datos,mensaje', [
    ({}, 'Seleccione un producto y un color'),
    ({'idProducto': '1', 'idColor': '1'}, 'al menos una talla'),
    ({'idProducto': '1', 'idColor': '1', 'cantidad_1': '-2'}, 'no pueden ser negativas'),
    ({'idProducto': '1', 'idColor': '1', 'cantidad_1': 'abc'}, 'números enteros'),
    ({'idProducto': '1', 'idColor': '1', 'cantidad_1': '2001'}, 'No se pueden emitir más de 2000'),
])
def test_emision_valida_el_formulario(admin, datos, mensaje):
    r = admin.post('/emisionEAN.html', data=datos, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True)


def test_listado_de_codigos(admin, db):
    p, c, s = ids(db, '414', 'NEGRO', 'S')
    db.rpc_obtener_variante(p, c, s)
    html = admin.get('/codigosEAN.html').get_data(as_text=True)
    assert '9941400030109' in html and 'Automático' in html
    assert '9941400030109' not in admin.get('/codigosEAN.html?q=hikini').get_data(as_text=True)


def test_codigo_manual_y_volver_a_automatico(admin, db):
    p, c, s = ids(db, '414', 'BLANCO', 'S')
    v = db.rpc_obtener_variante(p, c, s)[0]
    admin.post('/codigosEAN.html', data={'_method': 'manual', 'idVariante': v['id_variante'], 'codigoManual': '9900525927233'})
    assert db.tablas['producto_variantes'][0]['codigo_ean'] == '9900525927233'

    r = admin.post('/codigosEAN.html', data={'_method': 'manual', 'idVariante': v['id_variante'], 'codigoManual': '123'},
                   follow_redirects=True)
    assert '13 dígitos' in r.get_data(as_text=True)

    admin.post('/codigosEAN.html', data={'_method': 'automatico', 'idVariante': v['id_variante']})
    assert db.tablas['producto_variantes'][0]['codigo_ean'] == '9941400010101'


def test_cambiar_codigo_de_color_recalcula(admin, db):
    p, c, s = ids(db, '414', 'BLANCO', 'S')
    db.rpc_obtener_variante(p, c, s)
    admin.post('/colores.html', data={'_method': 'put', 'idColorActualizar': c, 'codigoActualizar': 'BL',
                                      'descripcionActualizar': 'BLANCO', 'codigoEanActualizar': '0002'})
    assert db.tablas['producto_variantes'][0]['codigo_ean'].startswith('994140002010')


def test_guarda_codigos_desde_los_maestros(admin, db):
    admin.post('/tallas.html', data={'_method': 'post', 'tallaCrear': '4', 'nombreCrear': 'XL', 'codigoEanCrear': '013'})
    assert db.tablas['tallas'][-1] == {'id_talla': 4, 'talla': '4', 'nombre': 'XL', 'codigo_ean': '013'}
    admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'Leggins', 'abreviacionCrear': 'LEG',
                                        'idColorCrear': '1', 'precioCrear': '5990', 'idTallaCrear': '1',
                                        'codigoCrear': 'C259', 'codigoEanCrear': ''})
    assert db.tablas['productos'][-1]['codigo'] == 'C259' and db.tablas['productos'][-1]['codigo_ean'] is None


def test_codigo_ean_con_letras_se_rechaza(admin, db):
    r = admin.post('/productos.html', data={'_method': 'post', 'descripcionCrear': 'X', 'abreviacionCrear': 'X',
                                            'idColorCrear': '1', 'precioCrear': '1', 'idTallaCrear': '1',
                                            'codigoEanCrear': '41A'}, follow_redirects=True)
    assert 'solo puede tener números' in r.get_data(as_text=True)
