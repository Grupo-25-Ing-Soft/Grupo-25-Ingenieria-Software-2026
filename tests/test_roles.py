import os

os.environ['SUPABASE_URL'] = 'https://supabase-falso.invalid'
os.environ['SUPABASE_PUBLISHABLE_KEY'] = 'clave-de-prueba'

from postgrest.exceptions import APIError
from werkzeug.security import generate_password_hash

import realFlask
from tests.supabase_falso import SupabaseFalso


def usuario(id_usuario, nombre_usuario, id_rol=None, es_superusuario=False, activo=True, password='clave-segura'):
    return {
        'id_usuario': id_usuario, 'nombre_usuario': nombre_usuario, 'nombre': nombre_usuario.title(),
        'password_hash': generate_password_hash(password), 'id_rol': id_rol,
        'es_superusuario': es_superusuario, 'activo': activo,
    }


def preparar(tablas, id_usuario=None):
    base = SupabaseFalso(tablas)
    realFlask.supabase = base
    realFlask.app.config.update(TESTING=True, SECRET_KEY='test-secret')
    cliente = realFlask.app.test_client()
    if id_usuario is not None:
        with cliente.session_transaction() as sesion:
            sesion['id_usuario'] = id_usuario
    return cliente, base.tablas


def tablas_con_rol_vendedor():
    # Rol creado por el usuario: ve clientes, edita colores y no tiene acceso a pagos.
    return {
        'roles': [{'id_rol': 7, 'nombre': 'Vendedor', 'descripcion': None}],
        'rol_permisos': [
            {'id_rol': 7, 'modulo': 'clientes', 'puede_ver': True, 'puede_editar': False},
            {'id_rol': 7, 'modulo': 'colores', 'puede_ver': False, 'puede_editar': True},
        ],
        'usuarios': [usuario(1, 'jefa', es_superusuario=True), usuario(2, 'ana', id_rol=7)],
        'clientes': [], 'colores': [],
    }


def test_sin_usuarios_lleva_a_crear_el_primero():
    cliente, _ = preparar({'usuarios': []})
    respuesta = cliente.get('/clientes.html')
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/primerUsuario.html')


def test_primer_usuario_queda_como_superusuario_con_sesion():
    cliente, tablas = preparar({'usuarios': [], 'roles': [], 'rol_permisos': []})
    respuesta = cliente.post('/primerUsuario.html', data={
        'nombre': 'Jefa', 'nombre_usuario': 'Jefa', 'password': 'clave-segura', 'password_confirmacion': 'clave-segura',
    })
    assert respuesta.headers['Location'].endswith('/roles.html')
    creado = tablas['usuarios'][0]
    assert creado['nombre_usuario'] == 'jefa' and creado['es_superusuario'] is True
    assert creado['password_hash'] != 'clave-segura'
    # Ya existe un usuario: la pantalla de primer usuario deja de estar disponible.
    assert cliente.get('/primerUsuario.html').headers['Location'].endswith('/login.html')
    assert cliente.get('/roles.html').status_code == 200


def test_sin_sesion_redirige_al_login_conservando_el_destino():
    cliente, _ = preparar(tablas_con_rol_vendedor())
    respuesta = cliente.get('/clientes.html')
    assert '/login.html?next=/clientes.html' in respuesta.headers['Location']


def test_login_correcto_e_incorrecto():
    cliente, _ = preparar(tablas_con_rol_vendedor())
    fallido = cliente.post('/login.html', data={'nombre_usuario': 'ana', 'password': 'otra-clave'})
    assert fallido.status_code == 200
    assert 'Usuario o contraseña incorrectos' in fallido.get_data(as_text=True)

    correcto = cliente.post('/login.html', data={'nombre_usuario': 'ANA', 'password': 'clave-segura', 'next': '/clientes.html'})
    assert correcto.headers['Location'] == '/clientes.html'


def test_login_no_redirige_fuera_del_sitio():
    cliente, _ = preparar(tablas_con_rol_vendedor())
    respuesta = cliente.post('/login.html', data={'nombre_usuario': 'ana', 'password': 'clave-segura', 'next': '//malicioso.example'})
    assert respuesta.headers['Location'] == '/'


def test_usuario_desactivado_no_puede_entrar_ni_seguir_con_sesion():
    tablas = tablas_con_rol_vendedor()
    tablas['usuarios'][1]['activo'] = False
    cliente, _ = preparar(tablas, id_usuario=2)
    assert '/login.html' in cliente.get('/clientes.html').headers['Location']
    respuesta = cliente.post('/login.html', data={'nombre_usuario': 'ana', 'password': 'clave-segura'})
    assert respuesta.status_code == 200


def test_permiso_ver_permite_abrir_y_buscar_pero_no_modificar():
    cliente, _ = preparar(tablas_con_rol_vendedor(), id_usuario=2)
    assert cliente.get('/clientes.html').status_code == 200

    busqueda = cliente.get('/clientes.html?q=x')
    assert busqueda.status_code == 200

    modificacion = cliente.post('/clientes.html', data={'_method': 'delete', 'idClienteBorrar': '1'})
    assert modificacion.status_code == 302
    assert modificacion.headers['Location'] == '/clientes.html'


def test_permiso_editar_incluye_ver():
    cliente, _ = preparar(tablas_con_rol_vendedor(), id_usuario=2)
    assert cliente.get('/colores.html').status_code == 200


def test_seccion_sin_permiso_vuelve_al_panel_y_oculta_su_enlace():
    cliente, _ = preparar(tablas_con_rol_vendedor(), id_usuario=2)
    respuesta = cliente.get('/pagos.html')
    assert respuesta.headers['Location'] == '/'

    panel = cliente.get('/', follow_redirects=True).get_data(as_text=True)
    assert 'Tu rol no tiene permiso para ver esa sección.' in panel
    rutas_ocultas = panel.split('new Set(')[1].split(')')[0]
    assert '"/pagos.html"' in rutas_ocultas
    assert '"/clientes.html"' not in rutas_ocultas


def test_crear_rol_guarda_los_permisos_elegidos():
    cliente, tablas = preparar(tablas_con_rol_vendedor(), id_usuario=1)
    cliente.post('/roles.html', data={
        '_method': 'post', 'nombre': 'Bodega', 'descripcion': '',
        'ver_inventario': 'on', 'editar_bodegas': 'on',
    })
    rol = next(r for r in tablas['roles'] if r['nombre'] == 'Bodega')
    permisos = {p['modulo']: p for p in tablas['rol_permisos'] if p['id_rol'] == rol['id_rol']}
    assert set(permisos) == {'inventario', 'bodegas'}
    assert permisos['inventario']['puede_editar'] is False
    assert permisos['bodegas']['puede_ver'] is True and permisos['bodegas']['puede_editar'] is True


def test_editar_rol_reemplaza_sus_permisos_y_no_permite_nombres_repetidos():
    cliente, tablas = preparar(tablas_con_rol_vendedor(), id_usuario=1)
    cliente.post('/roles.html', data={'_method': 'put', 'id_rol': '7', 'nombre': 'Vendedor', 'ver_pagos': 'on'})
    assert [p['modulo'] for p in tablas['rol_permisos'] if str(p['id_rol']) == '7'] == ['pagos']

    cliente.post('/roles.html', data={'_method': 'post', 'nombre': 'Vendedor'})
    assert len([r for r in tablas['roles'] if r['nombre'] == 'Vendedor']) == 1


def test_no_se_elimina_un_rol_con_usuarios():
    cliente, tablas = preparar(tablas_con_rol_vendedor(), id_usuario=1)
    cliente.post('/roles.html', data={'_method': 'delete', 'id_rol': '7'})
    assert tablas['roles']


def test_solo_quien_tiene_permiso_administra_roles():
    cliente, _ = preparar(tablas_con_rol_vendedor(), id_usuario=2)
    assert cliente.get('/roles.html').headers['Location'] == '/'


def test_crear_usuario_y_reglas_sobre_la_propia_cuenta():
    cliente, tablas = preparar(tablas_con_rol_vendedor(), id_usuario=1)
    cliente.post('/usuarios.html', data={
        '_method': 'post', 'nombre': 'Luis', 'nombre_usuario': 'luis', 'id_rol': '7',
        'password': 'clave-segura', 'password_confirmacion': 'clave-segura',
    })
    assert any(u['nombre_usuario'] == 'luis' and str(u['id_rol']) == '7' for u in tablas['usuarios'])

    # Nombre repetido, contraseña corta y usuario sin rol se rechazan.
    antes = len(tablas['usuarios'])
    for datos in (
        {'nombre_usuario': 'luis', 'id_rol': '7', 'password': 'clave-segura'},
        {'nombre_usuario': 'pedro', 'id_rol': '7', 'password': 'corta'},
        {'nombre_usuario': 'pedro', 'id_rol': '', 'password': 'clave-segura'},
    ):
        cliente.post('/usuarios.html', data={'_method': 'post', 'nombre': 'X', 'password_confirmacion': datos['password'], **datos})
    assert len(tablas['usuarios']) == antes

    cliente.post('/usuarios.html', data={'_method': 'delete', 'id_usuario': '1'})
    cliente.post('/usuarios.html', data={'_method': 'put', 'id_usuario': '1', 'nombre': 'Jefa'})
    jefa = next(u for u in tablas['usuarios'] if u['id_usuario'] == 1)
    assert jefa['activo'] is True


def test_sin_tablas_de_roles_muestra_instrucciones():
    class SinTablas(SupabaseFalso):
        def table(self, nombre):
            raise APIError({'message': 'Could not find the table', 'code': 'PGRST205'})

    realFlask.supabase = SinTablas()
    cliente = realFlask.app.test_client()
    respuesta = cliente.get('/clientes.html')
    assert respuesta.status_code == 503
    assert 'supabase/roles.sql' in respuesta.get_data(as_text=True)


def tablas_con_encargada():
    """Marta (rol Encargado) administra roles y usuarios y ve clientes. Pablo (rol Gerente)
    tiene además Pagos, que el rol de Marta no tiene."""
    tablas = tablas_con_rol_vendedor()
    tablas['roles'] += [{'id_rol': 8, 'nombre': 'Encargado', 'descripcion': None},
                        {'id_rol': 9, 'nombre': 'Gerente', 'descripcion': None}]
    tablas['rol_permisos'] += [
        {'id_rol': 8, 'modulo': 'roles_usuarios', 'puede_ver': True, 'puede_editar': True},
        {'id_rol': 8, 'modulo': 'clientes', 'puede_ver': True, 'puede_editar': False},
        {'id_rol': 9, 'modulo': 'pagos', 'puede_ver': True, 'puede_editar': True},
    ]
    tablas['usuarios'] += [usuario(3, 'marta', id_rol=8), usuario(4, 'pablo', id_rol=9)]
    return tablas


def permisos_de(tablas, id_rol):
    return sorted((p['modulo'], p['puede_editar']) for p in tablas['rol_permisos'] if str(p['id_rol']) == str(id_rol))


def test_no_se_otorgan_permisos_que_el_propio_rol_no_tiene():
    # AUD-017 (CU-57, CU-58): antes podía crear un rol con todo y asignárselo a otra cuenta.
    cliente, tablas = preparar(tablas_con_encargada(), id_usuario=3)
    r = cliente.post('/roles.html', data={'_method': 'post', 'nombre': 'Todo', 'editar_pagos': 'on'},
                     follow_redirects=True)
    assert 'Tu rol no tiene esos permisos' in r.get_data(as_text=True) and 'Pagos' in r.get_data(as_text=True)
    assert not any(r['nombre'] == 'Todo' for r in tablas['roles'])
    cliente.post('/roles.html', data={'_method': 'post', 'nombre': 'Consulta', 'ver_clientes': 'on'})
    assert any(r['nombre'] == 'Consulta' for r in tablas['roles'])


def test_no_se_modifica_el_propio_rol_ni_uno_con_mas_permisos():
    cliente, tablas = preparar(tablas_con_encargada(), id_usuario=3)
    antes = permisos_de(tablas, 8)
    r = cliente.post('/roles.html', data={'_method': 'put', 'id_rol': '8', 'nombre': 'Encargado',
                                          'editar_roles_usuarios': 'on', 'editar_clientes': 'on'}, follow_redirects=True)
    assert 'No puedes modificar ni eliminar tu propio rol' in r.get_data(as_text=True)
    assert permisos_de(tablas, 8) == antes
    cliente.post('/roles.html', data={'_method': 'put', 'id_rol': '9', 'nombre': 'Gerente', 'ver_clientes': 'on'})
    assert permisos_de(tablas, 9) == [('pagos', True)]
    html = cliente.get('/roles.html').get_data(as_text=True)
    assert '<span class="text-muted small">Tu rol</span>' in html
    assert 'aria-label="Ver Pagos" disabled' in html and 'aria-label="Ver Clientes" disabled' not in html


def test_no_se_asignan_roles_con_mas_permisos_ni_se_toma_otra_cuenta():
    cliente, tablas = preparar(tablas_con_encargada(), id_usuario=3)
    datos = {'_method': 'post', 'nombre': 'Otra', 'nombre_usuario': 'otra', 'id_rol': '9',
             'password': 'clave-segura', 'password_confirmacion': 'clave-segura'}
    r = cliente.post('/usuarios.html', data=datos, follow_redirects=True)
    assert 'No puedes asignar un rol con permisos que tu rol no tiene' in r.get_data(as_text=True)
    assert not any(u['nombre_usuario'] == 'otra' for u in tablas['usuarios'])

    # Cambiarle la contraseña a Pablo (más permisos) permitiría entrar con su cuenta.
    hash_pablo = next(u for u in tablas['usuarios'] if u['id_usuario'] == 4)['password_hash']
    r = cliente.post('/usuarios.html', data={'_method': 'put', 'id_usuario': '4', 'nombre': 'Pablo', 'id_rol': '9',
                                             'activo': 'on', 'password': 'otra-clave-1', 'password_confirmacion': 'otra-clave-1'},
                     follow_redirects=True)
    assert 'solo un superusuario puede modificarlo' in r.get_data(as_text=True)
    assert next(u for u in tablas['usuarios'] if u['id_usuario'] == 4)['password_hash'] == hash_pablo

    # Tampoco se cambia el rol propio.
    r = cliente.post('/usuarios.html', data={'_method': 'put', 'id_usuario': '3', 'nombre': 'Marta', 'id_rol': '9',
                                             'activo': 'on'}, follow_redirects=True)
    assert 'No puedes cambiar tu propio rol' in r.get_data(as_text=True)
    assert next(u for u in tablas['usuarios'] if u['id_usuario'] == 3)['id_rol'] == 8


def test_el_superusuario_sigue_administrando_todo():
    cliente, tablas = preparar(tablas_con_encargada(), id_usuario=1)
    cliente.post('/roles.html', data={'_method': 'put', 'id_rol': '8', 'nombre': 'Encargado', 'editar_pagos': 'on'})
    assert permisos_de(tablas, 8) == [('pagos', True)]


def test_inventario_de_bodegas_usa_el_permiso_de_inventario():
    # AUD-016 (RF-037, CU-58): antes las existencias se editaban con el permiso de Bodegas.
    tablas = tablas_con_rol_vendedor()
    tablas['roles'].append({'id_rol': 10, 'nombre': 'Bodeguero', 'descripcion': None})
    tablas['rol_permisos'].append({'id_rol': 10, 'modulo': 'bodegas', 'puede_ver': True, 'puede_editar': True})
    tablas['usuarios'].append(usuario(5, 'bruno', id_rol=10))
    tablas.update(bodegas=[{'id_bodega': 1, 'descripcion': 'Central'}], tallas=[], producto_variantes=[],
                  inventario=[{'id_inventario': 1, 'id_bodega': 1, 'id_variante': 3, 'cantidad': 5}])
    cliente, tablas = preparar(tablas, id_usuario=5)
    cliente.post('/bodegas.html', data={'_method': 'inventario_put', 'idInventario': 1, 'cantidadInventario': '50'})
    assert tablas['inventario'][0]['cantidad'] == 5
    assert 'Inventario por bodega' not in cliente.get('/bodegas.html').get_data(as_text=True)

    tablas['rol_permisos'].append({'id_rol': 10, 'modulo': 'inventario', 'puede_ver': True, 'puede_editar': True})
    cliente.post('/bodegas.html', data={'_method': 'inventario_put', 'idInventario': 1, 'cantidadInventario': '50'})
    assert tablas['inventario'][0]['cantidad'] == 50
