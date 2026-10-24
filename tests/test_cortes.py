"""Cortes: búsqueda por ID (la función buscarcorteid de la base fallaba con to_tsvector(bigint))
y CRUD que solo modifica guías pendientes (AUD-027)."""
import pytest

from tests.supabase_falso import error


@pytest.fixture
def base(db):
    db.tablas['productos'] = [
        {'id_producto': 2, 'descripcion': 'Polera piqué', 'color': 1, 'talla': 1},
        {'id_producto': 6, 'descripcion': 'Polera sin base', 'color': None, 'talla': None},
    ]
    db.tablas['bodegas'] = [{'id_bodega': 2, 'descripcion': 'Central'}]
    db.tablas['cortes'] = [
        {'id_corte': 4, 'fecha_corte': '2026-10-01', 'cortador': 'Juan', 'cantidad': 10, 'producto_asociado': 2,
         'estado': 'ingresado', 'fecha_ingreso': '2026-10-03T10:00:00+00:00', 'id_bodega_ingreso': 2},
        {'id_corte': 8, 'fecha_corte': '2026-10-02', 'cortador': 'Rosa', 'cantidad': 20, 'producto_asociado': 2,
         'estado': 'pendiente'},
    ]
    return db


def corte(id_corte, base):
    return next(c for c in base.tablas['cortes'] if c['id_corte'] == id_corte)


def formulario(sufijo, **cambios):
    datos = {'fechaCorte': '2026-10-05', 'cortador': 'Ana', 'cantidad': '15', 'IdProducto': '2',
             'material': 'Algodón', 'observaciones': ''}
    datos.update(cambios)
    return {clave + sufijo: valor for clave, valor in datos.items()}


def test_buscar_por_id(admin, base):
    html = admin.post('/cortes.html', data={'_method': 'buscarID', 'idBuscar': ' 8 '}).get_data(as_text=True)
    assert 'Rosa' in html and 'Juan' not in html


@pytest.mark.parametrize('texto,mensaje', [('99', 'No se encontró ningún corte con el ID 99'),
                                           ('abc', 'Ingrese un ID de corte numérico')])
def test_buscar_sin_resultado_o_invalido(admin, base, texto, mensaje):
    r = admin.post('/cortes.html', data={'_method': 'buscarID', 'idBuscar': texto}, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True)


def test_listado_con_producto_y_bodega_sin_acciones_en_ingresados(admin, base):
    html = admin.get('/cortes.html').get_data(as_text=True)
    assert '<td>Polera piqué</td>' in html and '03/10/2026 · Central' in html
    assert '"idCorteBorrar": 8' in html and '"idCorteBorrar": 4' not in html


def test_crear(admin, base):
    r = admin.post('/cortes.html', data={'_method': 'post', **formulario('Crear')}, follow_redirects=True)
    assert 'Guía de cortes 9 creada exitosamente' in r.get_data(as_text=True)
    nuevo = corte(9, base)
    assert (nuevo['cantidad'], nuevo['producto_asociado'], nuevo['observaciones']) == (15, 2, None)


@pytest.mark.parametrize('cambios,mensaje', [
    ({'cantidad': 'diez'}, 'La cantidad debe ser un número entero mayor que cero'),
    ({'cantidad': '0'}, 'La cantidad debe ser un número entero mayor que cero'),
    ({'fechaCorte': ''}, 'Ingrese la fecha del corte'),
    ({'cortador': ' '}, 'Ingrese el nombre del cortador'),
    ({'IdProducto': '99'}, 'Seleccione el producto del corte'),
])
def test_crear_valida(admin, base, cambios, mensaje):
    r = admin.post('/cortes.html', data={'_method': 'post', **formulario('Crear', **cambios)}, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True)
    assert len(base.tablas['cortes']) == 2


def test_editar_pendiente(admin, base):
    r = admin.post('/cortes.html', data={'_method': 'put', 'IdCorteActualizar': 8, **formulario('Actualizar')},
                   follow_redirects=True)
    assert 'Guía de cortes 8 actualizada' in r.get_data(as_text=True)
    assert corte(8, base)['cantidad'] == 15 and corte(8, base)['cortador'] == 'Ana'


def test_no_se_edita_ni_borra_un_corte_ingresado(admin, base):
    # AUD-027: su cantidad ya está en el inventario y en movimientos_inventario.
    r = admin.post('/cortes.html', data={'_method': 'put', 'IdCorteActualizar': 4, **formulario('Actualizar')},
                   follow_redirects=True)
    assert 'La guía de cortes 4 está ingresado: solo se modifican o eliminan' in r.get_data(as_text=True)
    assert corte(4, base)['cantidad'] == 10
    r = admin.post('/cortes.html', data={'_method': 'delete', 'idCorteBorrar': 4}, follow_redirects=True)
    assert 'solo se modifican o eliminan' in r.get_data(as_text=True)
    assert corte(4, base)


def test_borrar_pendiente(admin, base):
    r = admin.post('/cortes.html', data={'_method': 'delete', 'idCorteBorrar': 8}, follow_redirects=True)
    assert 'Guía de cortes 8 borrada' in r.get_data(as_text=True)
    assert [c['id_corte'] for c in base.tablas['cortes']] == [4]


def test_sin_campos_no_da_error(admin, base):
    r = admin.post('/cortes.html', data={}, follow_redirects=True)
    assert r.status_code == 200 and 'La guía de cortes no existe' in r.get_data(as_text=True)


# ------------------------------------------------------------------ ingreso a bodega (CU-21)
@pytest.fixture
def ingreso(base):
    """Simula ingresar_guia_corte() de incremento4_ingreso_produccion.sql: suma cada línea
    y deja la guía ingresada."""
    def ingresar(p_id_corte, p_id_bodega, p_lineas, p_usuario='Admin'):
        guia = corte(p_id_corte, base)
        guia.update(estado='ingresado', id_bodega_ingreso=p_id_bodega)
        return sum(linea['cantidad'] for linea in p_lineas)
    base.rpc_ingresar_guia_corte = ingresar
    base.tablas['productos'][0].update(codigo='414')
    base.tablas['colores'] = [{'id_color': 1, 'descripcion': 'Blanco'}, {'id_color': 2, 'descripcion': 'Negro'}]
    base.tablas['tallas'] = [{'id_talla': 1, 'talla': 1, 'nombre': 'S'}, {'id_talla': 2, 'talla': 2, 'nombre': 'M'}]
    base.tablas['cortes'].append({'id_corte': 9, 'fecha_corte': '2026-10-03', 'cortador': 'Ana', 'cantidad': 5,
                                  'producto_asociado': 6, 'estado': 'pendiente'})
    return base


def llamadas_ingreso(base):
    return [params for nombre, params in base.llamadas if nombre == 'ingresar_guia_corte']


def test_ingreso_lista_guias_pendientes(admin, ingreso):
    html = admin.get('/ingresoBodega.html').get_data(as_text=True)
    assert 'Guía 8 · 414 Polera piqué · 20 unidades cortadas · 02/10/2026' in html
    # El producto ya no tiene color ni talla base: se propone solo la cantidad cortada.
    assert 'data-cantidad="20"' in html and 'data-color=' not in html
    assert 'Guía 4 ·' not in html  # ya ingresada: aparece en «Ingresos realizados», con su bodega
    realizados = html.split('Ingresos realizados')[1]
    assert '<td>4</td>' in realizados and '<td>03/10/2026</td>' in realizados and '<td>Central</td>' in realizados
    # El color y la talla se eligen en cada línea.
    assert '<option value="9" data-cantidad="5"' in html
    assert '>Negro</option>' in html and '>M</option>' in html


def test_ingreso_por_color_talla_y_cantidad(admin, ingreso):
    # CU-21 paso 3: varios productos fabricados de una misma guía.
    r = admin.post('/ingresoBodega.html', data={'codigoCorte': 8, 'idBodega': 2, 'color': ['1', '2', '2'],
                                                'talla': ['1', '1', '2'], 'cantidad': ['8', '7', '4']},
                   follow_redirects=True)
    assert 'Se ingresaron 19 unidades de la guía de cortes 8 en la bodega Central' in r.get_data(as_text=True)
    assert llamadas_ingreso(ingreso) == [{
        'p_id_corte': 8, 'p_id_bodega': 2, 'p_usuario': 'admin',  # CU-39 paso 5: usuario responsable
        'p_lineas': [{'id_color': 1, 'id_talla': 1, 'cantidad': 8}, {'id_color': 2, 'id_talla': 1, 'cantidad': 7},
                     {'id_color': 2, 'id_talla': 2, 'cantidad': 4}]}]


@pytest.mark.parametrize('datos,mensaje', [
    ({'codigoCorte': '', 'idBodega': 2}, 'Seleccione la guía de cortes y la bodega de destino'),
    ({'codigoCorte': 8, 'idBodega': 2, 'color': ['1'], 'talla': ['1'], 'cantidad': ['0']},
     'debe ser un número entero mayor que cero'),  # CU-21, excepción 2
    ({'codigoCorte': 8, 'idBodega': 2, 'color': [''], 'talla': ['1'], 'cantidad': ['3']},
     'Seleccione el color y la talla de cada producto fabricado'),
    ({'codigoCorte': 8, 'idBodega': 2, 'color': [''], 'talla': [''], 'cantidad': ['']},
     'Ingrese al menos un producto fabricado'),
])
def test_ingreso_valida_antes_de_llamar_a_la_base(admin, ingreso, datos, mensaje):
    r = admin.post('/ingresoBodega.html', data=datos, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True)
    assert llamadas_ingreso(ingreso) == []


def test_ingreso_avisa_si_falta_el_script_sql(admin, ingreso):
    def sin_funcion(**_):
        raise error('Could not find the function public.ingresar_guia_corte', 'PGRST202')
    ingreso.rpc_ingresar_guia_corte = sin_funcion
    r = admin.post('/ingresoBodega.html', data={'codigoCorte': 8, 'idBodega': 2, 'color': ['1'], 'talla': ['1'],
                                                'cantidad': ['3']}, follow_redirects=True)
    assert 'Falta ejecutar supabase/incremento4_ingreso_produccion.sql' in r.get_data(as_text=True)


def test_ingreso_si_la_base_falla_muestra_la_pantalla(admin, ingreso):
    # AUD-029: antes redirigía a sí misma en bucle.
    original = ingreso.ejecutar

    def ejecutar(consulta):
        if consulta.nombre == 'bodegas':
            raise error('fallo simulado de la base', '57014')
        return original(consulta)
    ingreso.ejecutar = ejecutar
    r = admin.get('/ingresoBodega.html')
    assert r.status_code == 200 and 'No se pudieron cargar las guías de cortes y las bodegas' in r.get_data(as_text=True)
