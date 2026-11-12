"""El usuario no ve referencias a requerimientos o casos de uso (RF-001, CU-25...)."""
import re

import pytest

PANTALLAS = ['/pedidos.html', '/analisisDespachoSegunFacturaCliente.html', '/analisisVentasDescuentos.html',
             '/inventario.html', '/ingresoBodega.html', '/informeProductosTerminados.html',
             '/informeProductosEnProceso.html', '/resumenProduccion.html']


@pytest.mark.parametrize('ruta', PANTALLAS)
def test_sin_referencias_a_rf_ni_cu(admin, db, ruta):
    respuesta = admin.get(ruta)
    assert respuesta.status_code == 200
    # Los comentarios de los <script> no se ven en la pantalla.
    visible = re.sub(r'<script.*?</script>', '', respuesta.get_data(as_text=True), flags=re.S)
    assert not re.search(r'\b(RF|RNF|CU)-\d', visible)
