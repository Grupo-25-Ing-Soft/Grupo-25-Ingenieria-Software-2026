"""Presets de tallas (feedback de productos): se gestionan en Tallas y se aplican en Productos."""
import pytest

from tests.supabase_falso import error


def crear(admin, nombre='Línea adulto', tallas=('2', '1'), **extra):
    return admin.post('/tallas.html', data={'_method': 'preset_post', 'nombrePreset': nombre,
                                            'tallasPreset': list(tallas), **extra}, follow_redirects=True)


def test_crear_editar_y_eliminar(admin, db):
    r = crear(admin)
    assert 'Preset «Línea adulto» guardado con 2 tallas' in r.get_data(as_text=True)
    # Las tallas quedan en el orden del listado (S antes que M), no en el que llegaron.
    assert [(d['id_talla'], d['orden']) for d in db.tablas['presets_talla_detalle']] == [(1, 1), (2, 2)]
    assert 'S · M' in admin.get('/tallas.html').get_data(as_text=True)

    id_preset = db.tablas['presets_talla'][0]['id_preset']
    admin.post('/tallas.html', data={'_method': 'preset_put', 'idPreset': id_preset, 'nombrePreset': 'Adulto',
                                     'tallasPreset': ['3']})
    assert db.tablas['presets_talla'][0]['nombre'] == 'Adulto'
    assert [d['id_talla'] for d in db.tablas['presets_talla_detalle']] == [3]

    admin.post('/tallas.html', data={'_method': 'preset_delete', 'idPreset': id_preset})
    assert db.tablas['presets_talla'] == [] and db.tablas['presets_talla_detalle'] == []


@pytest.mark.parametrize('nombre,tallas,mensaje', [
    ('', ('1',), 'Ingresa el nombre del preset'),
    ('Sin tallas', (), 'Marca al menos una talla'),
    ('Talla borrada', ('99',), 'ya no existe'),
])
def test_validaciones(admin, db, nombre, tallas, mensaje):
    assert mensaje in crear(admin, nombre, tallas).get_data(as_text=True)
    assert not db.tablas.get('presets_talla')


def test_nombre_repetido(admin, db):
    crear(admin)
    assert 'Ya existe un preset llamado «Línea adulto»' in crear(admin, tallas=('1',)).get_data(as_text=True)
    assert len(db.tablas['presets_talla']) == 1


def test_productos_ofrece_aplicar_preset(admin, db):
    crear(admin)
    html = admin.get('/productos.html').get_data(as_text=True)
    assert 'Aplicar preset de tallas' in html and "data-tallas='[1, 2]'>Línea adulto (S, M)</option>" in html


def test_solo_lectura_no_gestiona_presets(cliente, db):
    db.tablas['roles'].append({'id_rol': 5, 'nombre': 'Consulta'})
    db.tablas['rol_permisos'].append({'id_rol': 5, 'modulo': 'tallas', 'puede_ver': True, 'puede_editar': False})
    db.tablas['usuarios'].append({'id_usuario': 5, 'nombre_usuario': 'lector', 'nombre': 'Lector', 'id_rol': 5,
                                  'es_superusuario': False, 'activo': True})
    with cliente.session_transaction() as sesion:
        sesion['id_usuario'] = 5
    r = crear(cliente)
    assert 'solo permite consultar' in r.get_data(as_text=True) and not db.tablas.get('presets_talla')
    assert 'Nuevo preset' not in cliente.get('/tallas.html').get_data(as_text=True)


def test_sin_el_script_sql_avisa(admin, db):
    original = db.ejecutar

    def ejecutar(consulta):
        if consulta.nombre.startswith('presets_talla'):
            raise error('Could not find the table public.presets_talla', 'PGRST205')
        return original(consulta)
    db.ejecutar = ejecutar
    assert 'Falta ejecutar supabase/incremento4_feedback_productos.sql' in admin.get('/tallas.html').get_data(as_text=True)
    assert admin.get('/productos.html').status_code == 200
    assert 'Falta ejecutar supabase/incremento4_feedback_productos.sql' in crear(admin).get_data(as_text=True)
