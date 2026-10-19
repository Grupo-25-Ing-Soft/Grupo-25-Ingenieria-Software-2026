"""Informe de cobranza (RF-031, CU-31) con el esquema real de facturas, pagos y pago_facturas."""
import pytest


@pytest.fixture
def base(db):
    db.tablas.update({
        'clientes': [{'id_cliente': 1, 'nombre': 'Tienda Sur'}, {'id_cliente': 2, 'nombre': 'Outlet Norte'}],
        'facturas': [
            {'id_factura': 1, 'folio': 100, 'cliente_asociado': 1, 'fecha_emision': '2026-09-01',
             'monto_total': 1000, 'saldo_pendiente': 1000, 'estado': 'vigente'},
            {'id_factura': 2, 'folio': 101, 'cliente_asociado': 2, 'fecha_emision': '2026-09-05',
             'monto_total': 500, 'saldo_pendiente': 500, 'estado': 'vigente'},
            {'id_factura': 3, 'folio': 102, 'cliente_asociado': 2, 'fecha_emision': '2026-09-05',
             'monto_total': 700, 'saldo_pendiente': 700, 'estado': 'anulada'},
        ],
        'pagos': [], 'pago_facturas': [], 'notas_credito': [],
    })
    return db


def test_el_saldo_cambia_con_los_pagos_aplicados(admin, base):
    html = admin.get('/informeCobranza.html').get_data(as_text=True)
    assert 'Tienda Sur' in html and 'Outlet Norte' in html and '<td>102</td>' not in html  # anulada fuera
    assert '01/09/2026' in html and '$1.500' in html  # total por cobrar

    admin.post('/pagos.html', data={'_method': 'post', 'cliente': 1, 'monto': '400', 'fecha_pago': '2026-10-01',
                                    'medio_pago': 'cheque', 'facturas': ['1']})
    admin.post('/pagos.html', data={'_method': 'post', 'cliente': 2, 'monto': '500', 'fecha_pago': '2026-10-01',
                                    'medio_pago': 'cheque', 'facturas': ['2']})
    filas = realFlask_informe()
    assert [(f['folio'], f['pagos_aplicados'], f['saldo']) for f in filas] == [(100, 400, 600)]

    # Un pago anulado deja de contar en el informe.
    admin.post('/pagos.html', data={'_method': 'delete', 'id_pago_anular': 1, 'motivo_anulacion': 'x'})
    assert [(f['folio'], f['pagos_aplicados'], f['saldo']) for f in realFlask_informe()] == [(100, 0, 1000)]


def test_filtros_y_pdf(admin, base):
    assert 'Outlet Norte' not in admin.get('/informeCobranza.html?cliente=sur').get_data(as_text=True).split('<tbody>')[-1]
    r = admin.get('/informeCobranza.pdf')
    assert r.status_code == 200 and r.mimetype == 'application/pdf' and r.data.startswith(b'%PDF')


def test_acceso_desde_reportes_y_barra_lateral(admin, base):
    reportes = admin.get('/reportes.html').get_data(as_text=True)
    assert 'href="/informeCobranza.html" class="dashboard-link"' in reportes
    barra = reportes.split('<div class="shared-caption">Ventas</div>')
    assert 'href="/informeCobranza.html"' in barra[0] and 'href="/informeCobranza.html"' not in barra[1].split('Archivos maestros')[0]


def realFlask_informe():
    import realFlask
    return realFlask.obtener_informe_cobranza({})


def test_mora_desde_la_fecha_limite_de_pago(admin, base):
    # RF-029: con fecha límite la mora se cuenta desde ella; antes de vencer es 0.
    from datetime import datetime, timedelta, timezone
    hoy = datetime.now(timezone.utc).date()  # el informe calcula con la fecha UTC
    base.tablas['facturas'][0]['fecha_vencimiento'] = (hoy - timedelta(days=10)).isoformat()
    base.tablas['facturas'][1]['fecha_vencimiento'] = (hoy + timedelta(days=5)).isoformat()
    mora = {f['folio']: f['dias_morosidad'] for f in realFlask_informe()}
    assert mora == {100: 10, 101: 0}
    assert 'Días de mora' in admin.get('/informeCobranza.html').get_data(as_text=True)
