"""Cortes: búsqueda por ID (la función buscarcorteid de la base fallaba con to_tsvector(bigint))."""
import pytest


@pytest.fixture
def base(db):
    db.tablas['cortes'] = [
        {'id_corte': 4, 'fecha_corte': '2026-10-01', 'cortador': 'Juan', 'cantidad': 10, 'estado': 'pendiente'},
        {'id_corte': 8, 'fecha_corte': '2026-10-02', 'cortador': 'Rosa', 'cantidad': 20, 'estado': 'pendiente'},
    ]
    return db


def test_buscar_por_id(admin, base):
    html = admin.post('/cortes.html', data={'_method': 'buscarID', 'idBuscar': ' 8 '}).get_data(as_text=True)
    assert 'Rosa' in html and 'Juan' not in html


@pytest.mark.parametrize('texto,mensaje', [('99', 'No se encontró ningún corte con el ID 99'),
                                           ('abc', 'Ingrese un ID de corte numérico')])
def test_buscar_sin_resultado_o_invalido(admin, base, texto, mensaje):
    r = admin.post('/cortes.html', data={'_method': 'buscarID', 'idBuscar': texto}, follow_redirects=True)
    assert mensaje in r.get_data(as_text=True)
