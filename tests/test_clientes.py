"""Clientes (RF-001/002, CU-01.1 a CU-01.5, CU-02)."""
import pytest

import realFlask


@pytest.fixture
def base(db):
    db.tablas.update({
        'zona_venta': [{'id_zona_venta': 3, 'nombre': 'Zona Sur', 'descripcion': 'Regiones del sur'}],
        'clientes': [], 'pedidos': [], 'facturas': [], 'pagos': [],
    })
    return db


def datos(sufijo='Crear', **cambios):
    base = {'nombre': 'Tienda Sur', 'codigo': 'CLI1', 'rut': '12.345.678', 'abreviacion': 'TS',
            'telefono': '+56911111111', 'correo': 'tienda@sur.cl', 'direccion': 'Hostos 1452', 'comuna': 'Quinta Normal',
            'ciudad': 'Santiago', 'idZonaVenta': '3', 'descuento1': '10', 'descuento2': '5.5', 'descuento3': '',
            'porComision': '3', 'porCobranza': '1.25', 'viaDespacho': 'Starken', 'condicionesVenta': '30 días',
            'observaciones': 'Cliente antiguo'}
    base.update(cambios)
    return {'_method': 'post' if sufijo == 'Crear' else 'put', **{k + sufijo: v for k, v in base.items()}}


@pytest.mark.parametrize('rut,dv', [('12345678', '5'), ('11111111', '1'), ('10000013', 'K'), ('7654321', '6'), ('17222333', '8')])
def test_digito_verificador(rut, dv):
    assert realFlask.digito_verificador_rut(rut) == dv


def test_crear_guarda_todos_los_campos(admin, base):
    r = admin.post('/clientes.html', data=datos(), follow_redirects=True)
    assert 'Cliente Tienda Sur creado' in r.get_data(as_text=True)
    c = base.tablas['clientes'][0]
    assert (c['rut'], c['digito_verificador'], c['codigo'], c['id_zona_venta']) == ('12345678', '5', 'CLI1', 3)
    assert (c['descuento_1'], c['descuento_2'], c['descuento_3']) == (10, 5.5, 0)
    assert (c['porcentaje_comision'], c['porcentaje_cobranza']) == (3, 1.25)
    html = admin.get('/clientes.html').get_data(as_text=True)
    assert '12.345.678-5' in html and 'Zona Sur' in html and '10.00% / 5.50% / 0.00%' in html
    assert 'data-modal="#actualizarModal"' in html and 'data-modal="#borrarModal"' in html  # botones por fila
    assert 'name="digVerCrear"' not in html  # el dígito verificador ya no se ingresa


@pytest.mark.parametrize('rut,numero', [('12.345.678', '12345678'), ('12345678-5', '12345678'),
                                        ('12.345.678-K', '12345678'), (' 7654321 ', '7654321')])
def test_dv_se_calcula_aunque_lo_peguen_con_guion(admin, base, rut, numero):
    admin.post('/clientes.html', data=datos(rut=rut))
    c = base.tablas['clientes'][0]
    assert (c['rut'], c['digito_verificador']) == (numero, realFlask.digito_verificador_rut(numero))


@pytest.mark.parametrize('cambios,mensaje', [
    ({'rut': '12a45'}, 'Ingrese el número del RUT'),
    ({'rut': '0'}, 'Ingrese el número del RUT'),
    ({'rut': ''}, 'Ingrese el número del RUT'),
    ({'nombre': ' '}, 'razón social es obligatoria'),
    ({'nombre': 'X' * 101}, 'admite hasta 100 caracteres'),
    ({'descuento1': '120'}, 'entre 0 y 100'),
])
def test_validaciones(admin, base, cambios, mensaje):
    assert mensaje in admin.post('/clientes.html', data=datos(**cambios), follow_redirects=True).get_data(as_text=True)
    assert base.tablas['clientes'] == []


def test_rut_repetido_y_editar(admin, base):
    admin.post('/clientes.html', data=datos())
    r = admin.post('/clientes.html', data=datos(codigo='CLI2'), follow_redirects=True)
    assert 'Ya existe un cliente con el RUT' in r.get_data(as_text=True)
    admin.post('/clientes.html', data={**datos('Actualizar', nombre='Tienda Sur Ltda', descuento3='2'), 'idClienteActualizar': 1})
    c = base.tablas['clientes'][0]
    assert c['nombre'] == 'Tienda Sur Ltda' and c['descuento_3'] == 2 and len(base.tablas['clientes']) == 1


def test_no_se_elimina_con_pedidos(admin, base):
    admin.post('/clientes.html', data=datos())
    base.tablas['pedidos'].append({'id_pedido': 1, 'cliente_asociado': 1})
    r = admin.post('/clientes.html', data={'_method': 'delete', 'idClienteBorrar': 1}, follow_redirects=True)
    assert 'tiene pedidos asociados' in r.get_data(as_text=True) and base.tablas['clientes']
    base.tablas['pedidos'].clear()
    admin.post('/clientes.html', data={'_method': 'delete', 'idClienteBorrar': 1})
    assert base.tablas['clientes'] == []


def test_busqueda_por_nombre(admin, base):
    admin.post('/clientes.html', data=datos())
    assert 'Tienda Sur' in admin.get('/clientes.html?q=tienda').get_data(as_text=True)
    assert 'No se encontraron resultados' in admin.get('/clientes.html?q=zzz').get_data(as_text=True)


def test_campos_rf001_giro_telefono2_vendedor_y_lista(admin, base):
    base.tablas['vendedores'] = [{'id_vendedor': 7, 'nombre': 'Ana Vendedora'}]
    r = admin.post('/clientes.html', data=datos(giro='Venta de ropa', telefono2='+56922222222', idVendedor='7',
                                                 listaPrecios='2'), follow_redirects=True)
    assert 'Cliente Tienda Sur creado' in r.get_data(as_text=True)
    c = base.tablas['clientes'][0]
    assert (c['giro'], c['telefono_2'], c['id_vendedor'], c['lista_precios']) == ('Venta de ropa', '+56922222222', 7, 2)
    html = admin.get('/clientes.html').get_data(as_text=True)
    assert 'Venta de ropa' in html and 'Ana Vendedora' in html and '+56922222222' in html
    # Sin lista de precios se usa la 1.
    admin.post('/clientes.html', data={**datos('Actualizar', listaPrecios=''), 'idClienteActualizar': 1})
    assert base.tablas['clientes'][0]['lista_precios'] == 1


@pytest.mark.parametrize('cambios,mensaje', [
    ({'listaPrecios': '0'}, 'lista de precios debe ser un entero'),
    ({'idVendedor': '99'}, 'vendedor seleccionado no está registrado'),
])
def test_validaciones_rf001(admin, base, cambios, mensaje):
    base.tablas['vendedores'] = []
    assert mensaje in admin.post('/clientes.html', data=datos(**cambios), follow_redirects=True).get_data(as_text=True)
    assert base.tablas['clientes'] == []


@pytest.mark.parametrize('escrita,guardada', [
    ('COMERCIAL D NIX LIMITADA', 'COMERCIAL D NIX LIMITADA'),
    ('Confecciones Ñuble SpA', 'Confecciones Ñuble SpA'),   # no se pasa a mayúsculas ni se expande SpA
    ('  Tienda   Sur  Ltda. ', 'Tienda Sur Ltda.'),        # solo se quitan los espacios sobrantes
])
def test_razon_social_tal_como_la_registra_el_sii(admin, base, escrita, guardada):
    admin.post('/clientes.html', data=datos(nombre=escrita))
    assert base.tablas['clientes'][0]['nombre'] == guardada
