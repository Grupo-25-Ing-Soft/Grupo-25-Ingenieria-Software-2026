"""Seguridad y manejo de errores (AUD-004, 005, 007/042, 008, 018, 021, 040)."""
import io

import pytest

import realFlask
from tests.supabase_falso import error


@pytest.fixture
def csrf_activo():
    realFlask.app.config['PROBAR_CSRF'] = True
    yield
    realFlask.app.config['PROBAR_CSRF'] = False


def test_post_sin_token_csrf_se_rechaza(admin, db, csrf_activo):
    # AUD-005: otra página no puede enviar formularios con la sesión del usuario.
    db.tablas['colores'] = []
    r = admin.post('/colores.html', data={'_method': 'post', 'descripcionCrear': 'Rojo'}, follow_redirects=True)
    assert 'El formulario venció o no es válido' in r.get_data(as_text=True)
    assert db.tablas['colores'] == []


def test_post_con_token_csrf_se_acepta(admin, db, csrf_activo):
    db.tablas['colores'] = []
    html = admin.get('/colores.html').get_data(as_text=True)
    assert 'campo.name = \'_csrf\'' in html  # el script agrega el token a los formularios
    with admin.session_transaction() as sesion:
        token = sesion['csrf']
    admin.post('/colores.html', data={'_method': 'post', 'descripcionCrear': 'Rojo', '_csrf': token})
    assert [c['descripcion'] for c in db.tablas['colores']] == ['Rojo']


def test_login_se_bloquea_tras_cinco_intentos_fallidos(cliente, db):
    # AUD-018
    realFlask.INTENTOS_LOGIN.clear()
    for _ in range(5):
        cliente.post('/login.html', data={'nombre_usuario': 'admin', 'password': 'mala'})
    r = cliente.post('/login.html', data={'nombre_usuario': 'admin', 'password': 'mala'})
    assert 'Demasiados intentos fallidos' in r.get_data(as_text=True)
    realFlask.INTENTOS_LOGIN.clear()


def test_error_de_base_en_get_muestra_la_pagina_de_error(admin, db):
    # AUD-007: antes se veía «Error de base de datos: ...» en texto plano.
    original = db.ejecutar

    def ejecutar(consulta):
        if consulta.nombre == 'colores':
            raise error('canceling statement due to statement timeout', '57014')
        return original(consulta)
    db.ejecutar = ejecutar
    r = admin.get('/colores.html')
    html = r.get_data(as_text=True)
    assert r.status_code == 500 and 'No se pudo cargar la página' in html and 'statement timeout' in html


def test_error_de_base_no_capturado_en_post(admin, db):
    original = db.ejecutar

    def ejecutar(consulta):
        if consulta.nombre == 'facturas' and consulta.operacion == 'insert':
            raise error('new row violates check constraint', '23514')
        return original(consulta)
    db.ejecutar = ejecutar
    db.tablas.update(pedidos=[{'id_pedido': 1, 'cliente_asociado': 1, 'estado': 'pendiente'}], facturas=[],
                     parametros_sistema=[{'id': 1, 'porcentaje_impuesto': 19}])
    r = admin.post('/facturas.html', data={'_method': 'post', 'folioCrear': 1, 'pedidoCrear': 1,
                                           'fechaEmisionCrear': '2026-10-01', 'montoNetoCrear': '100'},
                   follow_redirects=True)
    assert 'No se pudo guardar: algún dato no cumple las reglas de la base' in r.get_data(as_text=True)


@pytest.mark.parametrize('contenido,aceptado', [
    (b'\x89PNG\r\n\x1a\n' + b'0' * 20, True),
    (b'<script>alert(1)</script>', False),
])
def test_logotipo_debe_ser_una_imagen(admin, db, contenido, aceptado, tmp_path, monkeypatch):
    # AUD-008: antes bastaba con la extensión .png.
    monkeypatch.setattr(realFlask.app, 'static_folder', str(tmp_path))
    db.tablas['parametros_sistema'] = [{'id': 1}]
    datos = {'razon_social': 'D Nix', 'rut': '12345678-5', 'correo': 'a@b.cl', 'moneda': 'CLP',
             'formato_moneda': '$#,##0', 'porcentaje_impuesto': '19',
             'logotipo': (io.BytesIO(contenido), 'logo.png')}
    r = admin.post('/configuracion.html', data=datos, content_type='multipart/form-data', follow_redirects=True)
    assert ('Configuración guardada' in r.get_data(as_text=True)) is aceptado
    assert (tmp_path / 'img' / 'logo-configurado.png').exists() is aceptado


@pytest.mark.parametrize('rut,guardado', [('12345678', '12.345.678-5'), ('12.345.678-9', '12.345.678-5'),
                                          ('76.543.210', '76.543.210-3'), ('12a', None)])
def test_configuracion_calcula_el_dv_del_rut(admin, db, rut, guardado):
    db.tablas['parametros_sistema'] = [{'id': 1}]
    datos = {'razon_social': 'D Nix', 'rut': rut, 'correo': 'a@b.cl', 'moneda': 'CLP',
             'formato_moneda': '$#,##0', 'porcentaje_impuesto': '19'}
    html = admin.post('/configuracion.html', data=datos, follow_redirects=True).get_data(as_text=True)
    assert db.tablas['parametros_sistema'][0].get('rut') == guardado
    assert ('Configuración guardada' in html) is (guardado is not None)


def test_clave_secreta_se_genera_una_vez(tmp_path, monkeypatch):
    # AUD-004: sin FLASK_SECRET_KEY, cada reinicio cerraba todas las sesiones.
    monkeypatch.delenv('FLASK_SECRET_KEY', raising=False)
    monkeypatch.setattr(realFlask, 'BASE_DIR', str(tmp_path))
    primera = realFlask._clave_secreta()
    assert len(primera) == 64 and realFlask._clave_secreta() == primera
    assert (tmp_path / '.flask_secret_key').read_text(encoding='utf-8') == primera


def test_borrar_pedido_borra_sus_lineas_en_cascada(admin, db):
    # AUD-021: la base borra detalle_pedidos en cascada; la app ya no hace dos borrados.
    db.tablas.update(pedidos=[{'id_pedido': 1, 'numero_pedido': 'PED-1', 'estado': 'pendiente'}],
                     detalle_pedidos=[{'id_detalle_pedido': 1, 'id_pedido': 1}], despachos=[], facturas=[], cortes=[])
    admin.post('/pedidos.html', data={'_method': 'delete', 'idPedidoBorrar': 1})
    assert db.tablas['pedidos'] == [] and db.tablas['detalle_pedidos'] == []


def test_vendedor_asignado_a_clientes_no_se_elimina(admin, db):
    # AUD-040
    db.tablas.update(vendedores=[{'id_vendedor': 1, 'nombre': 'Ana', 'rut': '1', 'digito_verificador': '9'}],
                     pedidos=[], clientes=[{'id_cliente': 1, 'nombre': 'Tienda', 'id_vendedor': 1}])
    r = admin.post('/vendedores.html', data={'_method': 'delete', 'idVendedorBorrar': 1}, follow_redirects=True)
    assert 'está en uso en clientes' in r.get_data(as_text=True) and db.tablas['vendedores']
