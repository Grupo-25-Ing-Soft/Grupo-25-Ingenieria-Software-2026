"""Migración de datos desde archivos CSV y Excel (RF-060)."""
import io
import zipfile

import pytest

import realFlask


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Ya Cargado', 'rut': '11111111', 'digito_verificador': '1', 'codigo': 'C1'}],
        'vendedores': [{'id_vendedor': 4, 'nombre': 'Ana', 'rut': '22222222', 'codigo': 'V1'}],
        'zona_venta': [{'id_zona_venta': 7, 'nombre': 'Sur', 'codigo': 'ZS', 'descripcion': 'Sur'}],
        'bodegas': [],
    })
    return db


def subir(admin, tipo, contenido, nombre='datos.csv', accion='importar'):
    if isinstance(contenido, str):
        contenido = contenido.encode('utf-8')
    return admin.post('/migracion.html', data={'tipo': tipo, 'accion': accion, 'archivo': (io.BytesIO(contenido), nombre)},
                      content_type='multipart/form-data', follow_redirects=True).get_data(as_text=True)


CLIENTES = ('Razón Social;RUT;Codigo;COMUNA;Descuento 1;Zona;Vendedor;Columna rara\n'
            'Tienda Norte Ltda.;76.123.456-0;C2;Iquique;10%;zs;v1;x\n'      # nueva, con zona y vendedor
            'Repetido;11.111.111-1;C9;;;;;\n'                               # el RUT ya existe: se omite
            'Sin rut;;C3;;;;;\n'                                            # falta el RUT
            'Zona mala;12345678;C4;;;NOEXISTE;;\n'                          # zona inexistente
            'Descuento malo;87654321;C5;;150;;;\n'                          # porcentaje fuera de rango
            'Otra vez;76123456;C6;;;;;\n'                                   # RUT repetido en el archivo
            ';;;;;;;\n')                                                    # fila vacía: se ignora


def test_importa_clientes_y_explica_cada_fila(admin, base):
    html = subir(admin, 'clientes', CLIENTES)
    clientes = base.tablas['clientes']
    assert len(clientes) == 2
    nuevo = clientes[1]
    assert (nuevo['nombre'], nuevo['rut'], nuevo['digito_verificador']) == ('Tienda Norte Ltda.', '76123456', '0')
    assert (nuevo['comuna'], nuevo['descuento_1'], nuevo['descuento_2'], nuevo['lista_precios']) == ('Iquique', 10, 0, 1)
    assert (nuevo['id_zona_venta'], nuevo['id_vendedor']) == (7, 4)
    assert 'Se crearon <strong>1</strong> registros' in html and 'Columna rara' in html
    for motivo in ('ya existe (RUT 11111111)', 'falta «RUT»', 'no existe una zona de venta con el código NOEXISTE',
                   'debe estar entre 0 y 100', 'RUT 76123456 está repetido en el archivo (fila 2)'):
        assert motivo in html
    # El mismo archivo se puede subir de nuevo: no duplica.
    subir(admin, 'clientes', CLIENTES)
    assert len(base.tablas['clientes']) == 2


def test_validar_no_guarda(admin, base):
    html = subir(admin, 'clientes', CLIENTES, accion='validar')
    assert len(base.tablas['clientes']) == 1
    assert 'Todavía no se guardó nada' in html and 'Hay <strong>1</strong> filas listas' in html


def test_csv_con_comas_y_windows_1252(admin, base):
    contenido = 'descripcion,codigo de bodega\nBodega Ñuñoa,B1\n'.encode('cp1252')
    subir(admin, 'bodegas', contenido)
    assert [(b['descripcion'], b['codigo']) for b in base.tablas['bodegas']] == [('Bodega Ñuñoa', 'B1')]


def xlsx(filas):
    """Libro mínimo como los de Excel: textos compartidos, números y celdas vacías omitidas."""
    textos, celdas_xml = [], []
    for n, fila in enumerate(filas, start=1):
        celdas = ''
        for letra, valor in zip('ABCDEFGH', fila):
            if valor is None:
                continue
            if isinstance(valor, str):
                textos.append(valor)
                celdas += f'<c r="{letra}{n}" t="s"><v>{len(textos) - 1}</v></c>'
            else:
                celdas += f'<c r="{letra}{n}"><v>{valor}</v></c>'
        celdas_xml.append(f'<row r="{n}">{celdas}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, 'w') as libro:
        libro.writestr('xl/sharedStrings.xml', f'<sst {ns}>' + ''.join(f'<si><t>{t}</t></si>' for t in textos) + '</sst>')
        libro.writestr('xl/worksheets/sheet1.xml', f'<worksheet {ns}><sheetData>{"".join(celdas_xml)}</sheetData></worksheet>')
    return salida.getvalue()


def test_importa_productos_desde_excel(admin, base):
    antes = len(base.tablas['productos'])
    libro = xlsx([['Código', 'Descripción', 'Abreviación', 'Precio'],
                  [430, 'Colaless algodón', None, 2990.0],          # código y precio numéricos, celda vacía
                  ['C259', 'Sostén deportivo', 'SOS', '$ 5.990'],
                  [412, 'Ya existe', None, 1],                      # el código 412 ya está
                  [99999, 'Código largo', None, 1]])                # más dígitos que el formato EAN
    html = subir(admin, 'productos', libro, nombre='Productos.XLSX')
    nuevos = base.tablas['productos'][antes:]
    assert [(p['codigo'], p['descripcion'], p['abreviacion'], p['precio']) for p in nuevos] == [
        ('430', 'Colaless algodón', None, 2990), ('C259', 'Sostén deportivo', 'SOS', 5990)]
    assert 'ya existe (Código 412)' in html and 'admite hasta 3 caracteres (99999)' in html


@pytest.mark.parametrize('tipo,nombre,contenido,mensaje', [
    ('clientes', 'datos.csv', 'Nombre;Comuna\nA;B\n', 'faltan las columnas obligatorias: RUT'),
    ('clientes', 'datos.csv', 'Nombre;RUT\n', 'al menos una fila de datos'),
    ('clientes', 'datos.xls', 'x', 'El formato .xls antiguo no se admite'),
    ('clientes', 'datos.pdf', 'x', 'Formato no admitido'),
    ('clientes', 'datos.html', '<html><body><p>Sin tablas</p></body></html>', 'no tiene ninguna tabla con datos'),
    ('clientes', 'datos.xlsx', 'esto no es un excel', 'No se pudo leer el archivo Excel'),
    ('otra_cosa', 'datos.csv', 'Nombre;RUT\nA;1\n', 'Elige qué datos trae el archivo'),
])
def test_archivos_que_no_sirven(admin, base, tipo, nombre, contenido, mensaje):
    assert mensaje in subir(admin, tipo, contenido, nombre=nombre)
    assert len(base.tablas['clientes']) == 1


def test_si_la_base_rechaza_una_fila_se_informa_y_sigue(admin, base, monkeypatch):
    original = base._validar

    def validar(tabla, fila):
        if tabla == 'bodegas' and fila.get('codigo') == 'MALA':
            raise realFlask.APIError({'message': 'x', 'code': '23514', 'hint': None, 'details': None})
        return original(tabla, fila)

    monkeypatch.setattr(base, '_validar', validar)
    html = subir(admin, 'bodegas', 'Descripción;Código\nUno;B1\nDos;MALA\nTres;B3\n')
    assert [b['codigo'] for b in base.tablas['bodegas']] == ['B1', 'B3']
    assert 'la base la rechazó' in html and 'Se crearon <strong>2</strong>' in html


def test_plantilla_y_permisos(admin, base):
    r = admin.get('/migracionPlantilla.csv?tipo=vendedores')
    assert r.status_code == 200 and 'plantilla_vendedores.csv' in r.headers['Content-Disposition']
    assert r.data.decode('utf-8-sig').strip() == 'Nombre;Código de vendedor;RUT;Comisión'
    pagina = admin.get('/migracion.html').get_data(as_text=True)
    assert 'Migración de datos' in pagina and 'href="/migracionPlantilla.csv?tipo=clientes"' in pagina
    # Un rol sin el módulo «Migración de datos» no entra.
    base.tablas['roles'] = [{'id_rol': 5, 'nombre': 'Ventas'}]
    base.tablas['rol_permisos'] = [{'id_rol': 5, 'modulo': 'clientes', 'puede_ver': True, 'puede_editar': True}]
    base.tablas['usuarios'].append({'id_usuario': 2, 'nombre_usuario': 'eva', 'nombre': 'Eva', 'password_hash': '',
                                    'id_rol': 5, 'es_superusuario': False, 'activo': True})
    with admin.session_transaction() as sesion:
        sesion['id_usuario'] = 2
    assert admin.get('/migracion.html').headers['Location'] == '/'
    subir(admin, 'clientes', CLIENTES)
    assert len(base.tablas['clientes']) == 1


PAGINA = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>td { color: red }</style>
<script>var x = "<td>no es una celda</td>";</script></head><body>
<table><tr><td>Menú</td></tr></table>
<h1>Listado de colores</h1>
<table border="1">
  <thead><tr><th>Descripci&oacute;n</th><th>C&oacute;digo de color</th><th>C&oacute;digo EAN del color</th></tr></thead>
  <tbody>
    <tr><td><b>Rojo</b> <br>italiano</td><td> RJ </td><td>0100</td></tr>
    <tr><td>Azul &amp; blanco</td><td>AZ</td><td></td></tr>
    <tr><td>BLANCO</td><td>BL</td><td>0001</td></tr>
    <tr><td></td><td></td><td></td></tr>
  </tbody>
</table></body></html>"""


@pytest.mark.parametrize('nombre', ['colores.html', 'COLORES.HTM', 'exportado.xls'])
def test_importa_una_tabla_html(admin, base, nombre):
    # Se lee la tabla con más datos (no el menú); un .xls que en realidad es HTML también sirve.
    antes = len(base.tablas['colores'])
    html = subir(admin, 'colores', PAGINA, nombre=nombre)
    nuevos = [(c['descripcion'], c['codigo_color'], c['codigo_ean']) for c in base.tablas['colores'][antes:]]
    assert nuevos == [('Rojo italiano', 'RJ', '0100'), ('Azul & blanco', 'AZ', None)]
    assert 'Se crearon <strong>2</strong>' in html and 'ya existe' in html  # BLANCO ya estaba


def test_html_en_windows_1252(admin, base):
    pagina = '<table><tr><th>Descripción</th><th>Código</th></tr><tr><td>Bodega Ñuñoa</td><td>B1</td></tr></table>'
    subir(admin, 'bodegas', pagina.encode('cp1252'), nombre='bodegas.html')
    assert [(b['descripcion'], b['codigo']) for b in base.tablas['bodegas']] == [('Bodega Ñuñoa', 'B1')]
