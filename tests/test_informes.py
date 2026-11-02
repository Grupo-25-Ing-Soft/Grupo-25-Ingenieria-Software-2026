"""Informes de despachos y pedidos sobre las vistas de incremento3_despachos.sql
(AUD-030 a AUD-035): solo guías emitidas, lo despachado y no lo pedido, y agrupaciones."""
import pytest

from tests.supabase_falso import error


def despacho(id_despacho, fecha, cliente, vendedor, cantidad, precio, descuento, estado='emitido', id_factura=None):
    bruto = cantidad * precio
    rebaja = round(bruto * descuento / 100)
    return {'id_despacho': id_despacho, 'numero_guia': f'GD-{id_despacho:06d}', 'fecha': fecha, 'estado': estado,
            'id_pedido': id_despacho, 'numero_pedido': f'PED-{id_despacho:06d}', 'id_factura': id_factura,
            'id_cliente': cliente[0], 'cliente': cliente[1], 'id_vendedor': vendedor[0], 'vendedor': vendedor[1],
            'id_detalle_despacho': id_despacho, 'id_variante': 7, 'id_producto': 2, 'producto': 'Polera',
            'color': 'Azul', 'talla': 'M', 'cantidad': cantidad, 'precio_unitario': precio,
            'descuento_porcentaje': descuento, 'subtotal_bruto': bruto, 'monto_descuento': rebaja,
            'subtotal_neto': bruto - rebaja}


def linea_pedido(id_pedido, fecha, cliente, variante, pedida, anulada, despachada):
    return {'id_pedido': id_pedido, 'numero_pedido': f'PED-{id_pedido:06d}', 'fecha_pedido': fecha,
            'fecha_entrega': None, 'estado': 'pendiente', 'id_cliente': cliente[0], 'cliente': cliente[1],
            'id_vendedor': 1, 'vendedor': 'Ana', 'id_detalle_pedido': id_pedido, 'id_variante': variante[0],
            'producto': variante[1], 'color': variante[2], 'talla': variante[3], 'cantidad_pedida': pedida,
            'cantidad_anulada': anulada, 'cantidad_despachada': despachada,
            'cantidad_pendiente': pedida - anulada - despachada}


SUR, NORTE = (1, 'Tienda Sur'), (2, 'Outlet Norte')
ANA, LUIS = (1, 'Ana'), (2, 'Luis')
POLERA, SHORT = (7, 'Polera', 'Azul', 'M'), (8, 'Short', 'Negro', 'S')


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}, {'id_cliente': 2, 'nombre': 'Outlet Norte'}],
        'vendedores': [{'id_vendedor': 1, 'nombre': 'Ana', 'porcentaje_comision': 5},
                       {'id_vendedor': 2, 'nombre': 'Luis', 'porcentaje_comision': 10}],
        'producto_variantes': [
            {'id_variante': 7, 'descripcion': 'Polera', 'colores': {'descripcion': 'Azul'}, 'tallas': {'talla': 'M'}},
            {'id_variante': 8, 'descripcion': 'Short', 'colores': {'descripcion': 'Negro'}, 'tallas': {'talla': 'S'}}],
        'facturas': [{'id_factura': 1, 'folio': 900}],
        'pedidos': [{'id_pedido': 1, 'numero_pedido': 'PED-000001', 'estado': 'pendiente'}],
        'v_despachos_detalle': [
            despacho(1, '2026-10-02', SUR, ANA, 5, 1000, 10, id_factura=1),
            despacho(2, '2026-10-05', SUR, ANA, 3, 1000, 10),
            despacho(3, '2026-10-06', SUR, ANA, 100, 1000, 0, estado='anulado'),
            despacho(4, '2026-09-20', NORTE, LUIS, 2, 2000, 0)],
        'v_detalle_pedido_pendiente': [
            linea_pedido(1, '2026-10-01', SUR, POLERA, 10, 0, 8),
            linea_pedido(2, '2026-09-15', NORTE, POLERA, 6, 1, 2),
            linea_pedido(3, '2026-09-10', SUR, SHORT, 4, 0, 4)],
        'inventario': [{'id_inventario': 1, 'id_bodega': 1, 'id_variante': 7, 'cantidad': 2},
                       {'id_inventario': 2, 'id_bodega': 2, 'id_variante': 7, 'cantidad': 1}],
        'v_pedidos_despachos_mensual': [
            {'mes': '2026-08-01', 'pedidos': 1, 'unidades_pedidas': 5, 'despachos': 0, 'unidades_despachadas': 0},
            {'mes': '2026-09-01', 'pedidos': 2, 'unidades_pedidas': 10, 'despachos': 1, 'unidades_despachadas': 2},
            {'mes': '2026-10-01', 'pedidos': 1, 'unidades_pedidas': 10, 'despachos': 2, 'unidades_despachadas': 8}],
    })
    return db


def test_productos_despachados_excluye_anulados_y_muestra_lo_despachado(admin, base):
    # AUD-030: antes mostraba lo pedido (detalle_pedidos) y contaba guías anuladas.
    html = admin.get('/informeProductosDespachados.html').get_data(as_text=True)
    assert '3 guías · 10 unidades · $11.200 neto' in html
    assert 'GD-000003' not in html and 'GD-000001' in html
    assert '<td>900</td>' in html  # folio de la factura, no el id


@pytest.mark.parametrize('filtros,resumen', [
    ({'cliente': 1}, '2 guías · 8 unidades'),
    ({'desde': '2026-10-03'}, '1 guía · 3 unidades'),
    ({'vendedor': 2, 'hasta': '2026-09-30'}, '1 guía · 2 unidades'),
    ({'factura': 1}, '1 guía · 5 unidades'),
])
def test_productos_despachados_filtra(admin, base, filtros, resumen):
    assert resumen in admin.get('/informeProductosDespachados.html', query_string=filtros).get_data(as_text=True)


def test_fecha_invalida_se_ignora_con_aviso(admin, base):
    html = admin.get('/informeProductosDespachados.html?desde=31-12-2026').get_data(as_text=True)
    assert 'no es válida y no se aplicó' in html and '3 guías' in html


def test_sigue_aceptando_post(admin, base):
    html = admin.post('/informeProductosDespachados.html', data={'cliente': 2}).get_data(as_text=True)
    assert '1 guía · 2 unidades' in html


def test_sin_resultados_para_los_filtros(admin, base):
    html = admin.get('/informeProductosDespachados.html?desde=2027-01-01').get_data(as_text=True)
    assert 'No hay resultados para los filtros aplicados' in html


def test_despachos_por_cliente_y_producto_agrupa(admin, base):
    # AUD-032: antes cruzaba despachos del cliente con pedidos de cualquier cliente.
    html = admin.get('/analisisDespachoClienteProducto.html').get_data(as_text=True)
    assert '2 combinaciones · 10 unidades' in html
    fila_sur = html.split('<td>Tienda Sur</td>')[1].split('</tr>')[0]
    assert '<td class="text-end">2</td>' in fila_sur and '<td class="text-end">8</td>' in fila_sur
    assert '$7.200' in fila_sur


def test_despachos_por_vendedor_y_producto_filtra(admin, base):
    html = admin.get('/analisisDespachoVendedorProducto.html?vendedor=2').get_data(as_text=True)
    assert '<td>Luis</td>' in html and '<td>Ana</td>' not in html and '1 combinación · 2 unidades' in html


def test_pedidos_y_despachos_mensuales(admin, base):
    # AUD-033: antes devolvía filas sueltas de pedidos y despachos, sin agrupar por mes.
    html = admin.get('/analisisPedidosDespachosMensuales.html?mes_desde=2026-09').get_data(as_text=True)
    assert '08/2026' not in html and '09/2026' in html and '10/2026' in html
    assert '20.0 %' in html and '80.0 %' in html
    html = admin.get('/analisisPedidosDespachosMensuales.html?mes_desde=sept').get_data(as_text=True)
    assert 'no es válido y no se aplicó' in html and '08/2026' in html


def test_ventas_y_descuentos_por_cliente_y_vendedor(admin, base):
    # AUD-034: los descuentos salían siempre en 0 (descuento1 en vez de descuento_1).
    html = admin.get('/analisisVentasDescuentos.html?agrupar=cliente').get_data(as_text=True)
    fila_sur = html.split('<td>Tienda Sur</td>')[1].split('</tr>')[0]
    assert '$8.000' in fila_sur and '$800' in fila_sur and '10.00 %' in fila_sur and '$7.200' in fila_sur
    assert '$360' in fila_sur  # 5 % de comisión de Ana sobre el neto
    assert '$11.200 neto · $800 en descuentos' in html


def test_pedidos_versus_despachados(admin, base):
    # AUD-035: antes la pantalla decía «en desarrollo».
    html = admin.get('/analisisProductosPedidosDespachados.html').get_data(as_text=True)
    fila_polera = html.split('<td>Polera · Azul · M</td>')[1].split('</tr>')[0]
    # 16 pedidas, 1 anulada, 10 despachadas, 5 pendientes: 10 / 15 = 66,7 %.
    for valor in ('16', '1', '10', '5'):
        assert f'<td class="text-end">{valor}</td>' in fila_polera
    assert '66.7 %' in fila_polera and 'Short · Negro · S' in html
    html = admin.get('/analisisProductosPedidosDespachados.html?desde=2026-10-01').get_data(as_text=True)
    assert 'Short' not in html.split('<tbody>')[1]


def test_pendientes_de_despacho_con_stock(admin, base):
    # AUD-031: antes listaba todo lo pedido sin restar lo despachado.
    html = admin.get('/informeProductosPendientesDespacho.html').get_data(as_text=True)
    assert '2 líneas · 5 unidades pendientes · 5 se pueden despachar' in html
    assert 'PED-000003' not in html.split('<tbody>')[1]  # ya despachado completo
    html = admin.get('/informeProductosPendientesDespacho.html?pedido=2').get_data(as_text=True)
    assert '1 línea · 3 unidades pendientes · 3 se pueden despachar' in html


def test_informes_cargan_sin_datos(admin, db):
    for ruta in ('/informeProductosDespachados.html', '/informeProductosPendientesDespacho.html',
                 '/analisisDespachoClienteProducto.html', '/analisisDespachoVendedorProducto.html',
                 '/analisisPedidosDespachosMensuales.html', '/analisisVentasDescuentos.html',
                 '/analisisProductosPedidosDespachados.html'):
        r = admin.get(ruta)
        assert r.status_code == 200 and 'No hay resultados' in r.get_data(as_text=True), ruta


def test_analisis_de_inventario_cu53(admin, base):
    # CU-53: stock, defectos y asociación a pedidos. La variante 7 tiene 5 unidades pendientes
    # en pedidos (2 + 3); la 8 ya se despachó completa.
    base.tablas['bodegas'] = [{'id_bodega': 1, 'descripcion': 'Central'}, {'id_bodega': 2, 'descripcion': 'Sur'}]
    base.tablas['inventario'][0]['cantidad_defectuosa'] = 1
    base.tablas['inventario'].append({'id_inventario': 3, 'id_bodega': 1, 'id_variante': 8, 'cantidad': 9})
    html = admin.get('/inventario.html').get_data(as_text=True)
    assert '3 registros · 12 unidades disponibles · 1 con defectos' in html
    fila_central = html.split('<td>Central</td>')[1].split('</tr>')[0]
    assert 'Polera · Azul · M' in fila_central and '<td class="text-end">5</td>' in fila_central and '>Sí<' in fila_central
    assert '1 registro · 9 unidades' in admin.get('/inventario.html?situacion=libres').get_data(as_text=True)
    assert '1 registro · 2 unidades' in admin.get('/inventario.html?situacion=defectos').get_data(as_text=True)
    assert '1 registro · 1 unidad disponible' in admin.get('/inventario.html?bodega=2').get_data(as_text=True)
    html = admin.get('/inventario.html?bodega=2&situacion=defectos').get_data(as_text=True)
    assert 'No existen resultados disponibles para los filtros aplicados' in html


def test_productos_terminados_cu52(admin, base):
    # CU-52: terminados entre fechas, por talla y color, con defectos y asociación a pedidos.
    # Antes daba error 500 con fechas vacías y la fecha «hasta» excluía el último día.
    base.tablas['bodegas'] = [{'id_bodega': 1, 'descripcion': 'Central'}]
    base.tablas['tallas'] = [{'id_talla': 1, 'talla': 2, 'nombre': 'M'}, {'id_talla': 2, 'talla': 1, 'nombre': 'S'}]
    base.tablas['producto_variantes'][0].update(id_producto=2, id_color=1, id_talla=1)
    base.tablas['producto_variantes'][1].update(id_producto=3, id_color=2, id_talla=2)
    base.tablas['inventario'][0]['cantidad_defectuosa'] = 1
    movimiento = {'id_bodega': 1, 'bodega': 'Central', 'id_producto': 2, 'producto': 'Polera', 'id_color': 1,
                  'color': 'Azul', 'id_talla': 1, 'talla': 2}
    base.tablas['v_produccion_terminada'] = [
        {**movimiento, 'id_movimiento': 1, 'id_corte': 4, 'dia': '2026-10-01', 'cantidad': 10},
        {**movimiento, 'id_movimiento': 2, 'id_corte': 5, 'dia': '2026-10-05', 'cantidad': 6},
        {**movimiento, 'id_movimiento': 3, 'id_corte': 6, 'dia': '2026-10-05', 'cantidad': 3, 'id_producto': 3,
         'producto': 'Short', 'id_color': 2, 'color': 'Negro', 'id_talla': 2, 'talla': 1}]
    html = admin.get('/informeProductosTerminados.html').get_data(as_text=True)
    assert '2 productos · 19 unidades terminadas' in html
    fila = html.split('<td>Polera</td>')[1].split('</tr>')[0]
    assert '<td>M</td>' in fila and '<td class="text-end">16</td>' in fila and '>Sí<' in fila
    assert '<td class="text-end">5</td>' in fila  # 5 unidades pendientes en pedidos
    html = admin.get('/informeProductosTerminados.html?desde=2026-10-05&hasta=2026-10-05').get_data(as_text=True)
    assert '2 productos · 9 unidades terminadas' in html  # «hasta» incluye el día completo
    html = admin.get('/informeProductosTerminados.html?desde=&hasta=').get_data(as_text=True)
    assert '19 unidades' in html
    html = admin.get('/informeProductosTerminados.html?desde=2027-01-01').get_data(as_text=True)
    assert 'no se ingresaron guías de cortes a bodega en ese periodo' in html


def test_productos_despachados_filtra_por_pedido(admin, base):
    # CU-46: búsqueda por pedido, cliente, factura o producto.
    assert '1 guía · 3 unidades' in admin.get('/informeProductosDespachados.html?pedido=2').get_data(as_text=True)


def test_despachos_segun_factura_y_cliente_cu48(admin, base):
    html = admin.get('/analisisDespachoSegunFacturaCliente.html?cliente=1').get_data(as_text=True)
    assert '2 despachos · 8 unidades · $7.200 neto · 1 sin factura' in html
    assert 'GD-000003' not in html  # anulada
    assert '<td>900</td>' in html and '<td>Sin factura</td>' in html
    html = admin.get('/analisisDespachoSegunFacturaCliente.html?factura=1').get_data(as_text=True)
    assert '1 despacho · 5 unidades' in html


@pytest.mark.parametrize('agrupar,fila,esperado', [
    ('vendedor', '<td>Luis</td>', '$4.000'),
    ('producto', '<td>Polera · Azul · M</td>', '$11.200'),
    ('factura', '<td>900</td>', '$4.500'),
    ('guia', '<td>GD-000002 · 05/10/2026 · Tienda Sur</td>', '$2.700'),
])
def test_ventas_y_descuentos_por_perspectiva_cu47(admin, base, agrupar, fila, esperado):
    html = admin.get(f'/analisisVentasDescuentos.html?agrupar={agrupar}').get_data(as_text=True)
    assert esperado in html.split(fila)[1].split('</tr>')[0]


def test_resumen_de_produccion_cu55(admin, base):
    base.tablas['productos'] = [{'id_producto': 2, 'descripcion': 'Polera'}, {'id_producto': 3, 'descripcion': 'Short'}]
    base.tablas['tallas'] = [{'id_talla': 1, 'talla': 2, 'nombre': 'M'}, {'id_talla': 2, 'talla': 1, 'nombre': 'S'}]
    base.tablas['cortes'] = [{'id_corte': 4, 'id_pedido': 1}, {'id_corte': 5, 'id_pedido': None}, {'id_corte': 6, 'id_pedido': 2}]
    base.tablas['pedidos'] = [{'id_pedido': 1, 'cliente_asociado': 1}, {'id_pedido': 2, 'cliente_asociado': 2}]
    movimiento = {'id_bodega': 1, 'id_producto': 2, 'producto': 'Polera', 'id_color': 1, 'color': 'Azul',
                  'id_talla': 1, 'talla': 2}
    base.tablas['v_produccion_terminada'] = [
        {**movimiento, 'id_corte': 4, 'dia': '2026-10-01', 'cantidad': 10},
        {**movimiento, 'id_corte': 5, 'dia': '2026-10-05', 'cantidad': 6},
        {**movimiento, 'id_corte': 6, 'dia': '2026-10-05', 'cantidad': 3, 'id_producto': 3, 'producto': 'Short',
         'id_color': 2, 'color': 'Negro', 'id_talla': 2}]
    html = admin.get('/resumenProduccion.html').get_data(as_text=True)
    assert '3 guías de cortes · 19 unidades producidas' in html
    assert '<td>M</td>' in html.split('<td>Polera</td>')[1].split('</tr>')[0]
    assert '1 guía de cortes · 10 unidades' in admin.get('/resumenProduccion.html?cliente=1').get_data(as_text=True)
    assert '2 guías de cortes · 9 unidades' in admin.get('/resumenProduccion.html?desde=2026-10-05').get_data(as_text=True)
    assert '1 guía de cortes · 3 unidades' in admin.get('/resumenProduccion.html?articulo=3').get_data(as_text=True)
    html = admin.get('/resumenProduccion.html?cliente=2&articulo=2').get_data(as_text=True)
    assert 'No hay resultados para los filtros aplicados' in html


def test_productos_en_proceso_sin_la_vista_avisa(admin, base):
    # La vista se perdió en la base al cambiar cortes.cantidad: no debe dar error 500.
    original = base.ejecutar

    def ejecutar(consulta):
        if consulta.nombre == 'v_productos_en_proceso':
            raise error('Could not find the table public.v_productos_en_proceso', 'PGRST205')
        return original(consulta)
    base.ejecutar = ejecutar
    r = admin.get('/informeProductosEnProceso.html')
    assert r.status_code == 200 and 'Falta ejecutar supabase/incremento4_cortes_cantidades.sql' in r.get_data(as_text=True)


def test_productos_en_proceso_cu54(admin, base):
    # CU-54: cortes aún no ingresados, con pedido, cliente y lo que el pedido tiene pendiente.
    base.tablas['productos'] = [{'id_producto': 2, 'descripcion': 'Polera'}]
    base.tablas['pedidos'] = [{'id_pedido': 1, 'cliente_asociado': 1}, {'id_pedido': 2, 'cliente_asociado': 2}]
    for linea in base.tablas['v_detalle_pedido_pendiente']:
        linea['id_producto'] = 2 if linea['id_variante'] == 7 else 3
    corte = {'id_producto': 2, 'producto': 'Polera', 'color': 'Azul', 'talla': 2, 'cortador': 'Ana',
             'material_usado': 'Algodón', 'dias_en_proceso': 3}
    base.tablas['v_productos_en_proceso'] = [
        {**corte, 'id_corte': 8, 'fecha_corte': '2026-10-02', 'cantidad': 20, 'id_pedido': 1,
         'numero_pedido': 'PED-000001', 'cliente': 'Tienda Sur'},
        {**corte, 'id_corte': 9, 'fecha_corte': '2026-10-06', 'cantidad': 5, 'id_pedido': None,
         'numero_pedido': None, 'cliente': None}]
    html = admin.get('/informeProductosEnProceso.html').get_data(as_text=True)
    assert '2 guías de cortes en proceso · 25 unidades' in html
    fila = html.split('<td>8</td>')[1].split('</tr>')[0]
    # El corte es de un producto, sin color ni talla (se eligen al ingresarlo a bodega).
    assert 'Azul' not in fila and 'Polera' in fila and 'PED-000001' in fila and '<td class="text-end">2</td>' in fila  # 10 - 8 despachadas
    assert 'Sin pedido' in html.split('<td>9</td>')[1].split('</tr>')[0]
    assert '1 guía de cortes en proceso · 20 unidades' in \
        admin.get('/informeProductosEnProceso.html?cliente=1').get_data(as_text=True)
    assert '1 guía de cortes en proceso · 5 unidades' in \
        admin.get('/informeProductosEnProceso.html?desde=2026-10-05').get_data(as_text=True)
    html = admin.get('/informeProductosEnProceso.html?cliente=2').get_data(as_text=True)
    assert 'No hay resultados para los filtros aplicados' in html
