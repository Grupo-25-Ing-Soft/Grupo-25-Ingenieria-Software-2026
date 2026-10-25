"""Los códigos de negocio se muestran y buscan sin reemplazar las claves de las relaciones."""
import pytest

import realFlask


@pytest.fixture
def documentos(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda'}],
        'vendedores': [{'id_vendedor': 1, 'nombre': 'Ana'}],
        'productos': [{'id_producto': 2, 'descripcion': 'Polera', 'codigo': '123'}],
        'pedidos': [{'id_pedido': 71, 'codigo': 'PED-007', 'numero_pedido': 'PED-000071',
                     'cliente_asociado': 1, 'vendedor_asociado': 1, 'estado': 'pendiente',
                     'fecha_pedido': '2026-10-01', 'fecha_entrega': None}],
        'facturas': [], 'cortes': [], 'detalle_pedidos': [], 'despachos': [],
        'pagos': [], 'pago_facturas': [], 'notas_credito': [],
    })
    return db


def formulario(tabla, sufijo='Crear'):
    campos = {
        'pedidos': {'IDCliente': 1, 'IDVendedor': 1, 'fechaPedido': '2026-10-25'},
        'facturas': {'folio': 900, 'pedido': 71, 'fechaEmision': '2026-10-25', 'montoNeto': 100},
        'cortes': {'fechaCorte': '2026-10-25', 'cortador': 'Ana', 'cantidad': 5, 'IdProducto': 2},
    }
    return {k + sufijo: v for k, v in campos[tabla].items()}


@pytest.mark.parametrize('tabla,clave', [('pedidos', 'id_pedido'), ('facturas', 'id_factura'),
                                       ('cortes', 'id_corte')])
def test_crear_editar_buscar_y_rechazar_codigo_duplicado(admin, documentos, tabla, clave):
    url = f'/{tabla}.html'
    datos = {'_method': 'post', 'codigoCrear': ' 000A-07 ', **formulario(tabla)}
    admin.post(url, data=datos)
    nuevo = documentos.tablas[tabla][-1]
    if tabla == 'cortes':
        nuevo.setdefault('estado', 'pendiente')  # DEFAULT de la tabla real.
    assert nuevo['codigo'] == '000A-07'
    assert nuevo[clave] != nuevo['codigo']
    if tabla == 'facturas':
        assert nuevo['pedido_asociado'] == 71 and nuevo['folio'] == 900
    html = admin.get(url).get_data(as_text=True)
    assert '<td>000A-07</td>' in html

    cantidad = len(documentos.tablas[tabla])
    r = admin.post(url, data=datos, follow_redirects=True)
    assert 'Ya existe un registro con el código 000A-07' in r.get_data(as_text=True)
    assert len(documentos.tablas[tabla]) == cantidad

    campo_id = {'pedidos': 'IdPedidoActualizar', 'facturas': 'idFacturaActualizar',
                'cortes': 'IdCorteActualizar'}[tabla]
    datos_editar = {'_method': 'put', campo_id: nuevo[clave], **formulario(tabla, 'Actualizar')}
    admin.post(url, data=datos_editar)  # Un formulario antiguo conserva el código.
    assert documentos.tablas[tabla][-1]['codigo'] == '000A-07'
    admin.post(url, data={**datos_editar, 'codigoActualizar': '000B-08'})
    assert documentos.tablas[tabla][-1]['codigo'] == '000B-08'
    if tabla == 'cortes':
        html = admin.post(url, data={'_method': 'buscarCodigo', 'codigoBuscar': '000B-08'}).get_data(as_text=True)
    else:
        html = admin.get(url + '?codigo=000B-08').get_data(as_text=True)
    assert '<td>000B-08</td>' in html
    if tabla == 'pedidos':
        assert '<td>PED-007</td>' not in html


def test_codigo_igual_al_id_no_busca_por_id(admin, documentos):
    documentos.tablas['cortes'] = [{'id_corte': 8, 'codigo': 'OTRO', 'estado': 'pendiente',
                                  'fecha_corte': '2026-10-25', 'cantidad': 5, 'producto_asociado': 2}]
    r = admin.post('/cortes.html', data={'_method': 'buscarCodigo', 'codigoBuscar': '8'},
                   follow_redirects=True)
    assert 'No se encontró ningún corte con el código 8' in r.get_data(as_text=True)


def test_codigo_faltante_no_muestra_id_y_cache_se_renueva_por_peticion(documentos):
    with realFlask.app.test_request_context():
        assert realFlask.codigo_registro(71, 'pedidos') == 'PED-007'
        assert realFlask.codigo_registro(71, 'pedidos') == 'PED-007'
    documentos.tablas['pedidos'][0]['codigo'] = None
    with realFlask.app.test_request_context():
        assert realFlask.codigo_registro(71, 'pedidos') == 'Sin código'


def test_ingreso_mantiene_separados_codigo_corte_y_codigo_producto(admin, documentos):
    documentos.tablas['cortes'] = [{'id_corte': 8, 'codigo': 'COR-008', 'estado': 'pendiente',
                                  'producto_asociado': 2, 'cantidad': 5, 'fecha_corte': '2026-10-25'}]
    html = admin.get('/ingresoBodega.html').get_data(as_text=True)
    assert 'Guía COR-008 · 123 Polera' in html
    assert '<option value="8"' in html  # La relación conserva la clave de Supabase.
