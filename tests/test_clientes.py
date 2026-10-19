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
    base = {'nombre': 'Tienda Sur', 'codigo': 'CLI1', 'rut': '12.345.678', 'digVer': '5', 'abreviacion': 'TS',
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
    assert '12345678-5' in html and 'Zona Sur' in html and '10.00% / 5.50% / 0.00%' in html
    assert 'data-modal="#actualizarModal"' in html and 'data-modal="#borrarModal"' in html  # botones por fila


@pytest.mark.parametrize('cambios,mensaje', [
    ({'digVer': '4'}, 'el dígito verificador no coincide'),
    ({'rut': '12a45'}, 'solo números'),
    ({'nombre': ' '}, 'nombre del cliente es obligatorio'),
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
