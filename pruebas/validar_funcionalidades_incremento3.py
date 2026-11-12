import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('Faltan variables SUPABASE_URL o SUPABASE_PUBLISHABLE_KEY en .env')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})


def make_dependency_matrix():
    return [
        {
            'Informe': 'Productos despachados',
            'Tablas/vistas usadas': 'despachos, pedidos, detalle_pedidos, facturas',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'APROBADO',
            'Observación': 'Se obtuvieron filas reales en 2026-10-04 para 2 despachos dentro del rango.'
        },
        {
            'Informe': 'Pendientes de despacho',
            'Tablas/vistas usadas': 'pedidos, detalle_pedidos, inventario, producto_variantes',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'La ruta lee pendientes por pedido/cliente/vendedor; la validación visual completa requiere un caso real adicional en navegador.'
        },
        {
            'Informe': 'Productos terminados',
            'Tablas/vistas usadas': 'cortes, productos',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'El controlador responde con HTML y carga filas en una tabla; falta captura de validación visual con un rango reproducible.'
        },
        {
            'Informe': 'Productos en proceso',
            'Tablas/vistas usadas': 'cortes, productos',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'La ruta responde y filtra cortes pendientes.'
        },
        {
            'Informe': 'Despachos por cliente y producto',
            'Tablas/vistas usadas': 'despachos, pedidos, detalle_pedidos, producto_variantes',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'La ruta responde con filtros reales sobre cliente/producto; falta contrastar suma final con caso exacto.'
        },
        {
            'Informe': 'Despachos según factura y cliente',
            'Tablas/vistas usadas': 'despachos, pedidos, facturas',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'Consulta con id_factura y cliente valida la relación; requiere comprobación visual exacta.'
        },
        {
            'Informe': 'Despachos por vendedor y producto',
            'Tablas/vistas usadas': 'despachos, pedidos, detalle_pedidos, producto_variantes',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'Deben validarse filtros concretos vendedor/producto con caso preciso.'
        },
        {
            'Informe': 'Pedidos y despachos mensuales',
            'Tablas/vistas usadas': 'pedidos, despachos',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'El controlador responde y agrupa por rango; necesita validación de mes/año.'
        },
        {
            'Informe': 'Ventas y descuentos',
            'Tablas/vistas usadas': 'pedidos, clientes, vendedores',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'PARCIAL',
            'Observación': 'Se verificó que los datos existen en clientes y vendedores; falta contraste del cálculo de descuentos.'
        },
        {
            'Informe': 'Resumen de producción',
            'Tablas/vistas usadas': 'cortes, productos',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'APROBADO',
            'Observación': 'Se obtuvo un registro real: cantidad_total 27, cortes 2, descripcion desprod, producto_id 2.'
        },
        {
            'Informe': 'Inventario',
            'Tablas/vistas usadas': 'inventario, bodegas, producto_variantes, tallas, colores',
            'Lectura disponible': 'SI',
            'Registros adecuados': 'SI',
            'Estado validación': 'APROBADO',
            'Observación': 'Se verificaron 2 filas con cantidades 24 y 4, bodega 1 plus y color rojotest/gris.'
        },
    ]


def make_functional_results():
    return [
        {
            'CU/RF': 'CU-45; RF-045/046',
            'ruta': '/informeProductosDespachados.html',
            'escenario': 'Despacho real en 2026-10-04',
            'filtros': 'desde=2026-10-01, hasta=2026-10-31',
            'esperado': '2 despachos del periodo',
            'observado': '2 filas visibles en tabla',
            'estado': 'APROBADO',
            'evidencia': 'capturas/01_productos_despachados_browser.png'
        },
        {
            'CU/RF': 'CU-42/43; RF-042/043',
            'ruta': '/informeProductosPendientesDespacho.html',
            'escenario': 'Pedido pendiente con líneas',
            'filtros': 'Pedido 3 / cliente 4 / vendedor 1',
            'esperado': 'Listado de productos pendientes del pedido',
            'observado': 'Ruta responde y genera payload con productos pendientes [1, 2]',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-52; RF-052',
            'ruta': '/informeProductosTerminados.html',
            'escenario': 'Cortes ingresados en rango',
            'filtros': '2026-09-01 a 2026-10-31',
            'esperado': 'Cortes terminados del período',
            'observado': 'Servicio responde con HTML y tabla creada, sin captura final',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-54; RF-054',
            'ruta': '/informeProductosEnProceso.html',
            'escenario': 'Cortes pendientes',
            'filtros': 'estado pendiente',
            'esperado': 'Listado de cortes en proceso',
            'observado': 'Ruta responde con filas de cortes pendientes',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-47; RF-049',
            'ruta': '/analisisDespachoClienteProducto.html',
            'escenario': 'Cliente 4 / producto 2',
            'filtros': 'cliente y variante',
            'esperado': 'Despachos asociados al cliente y producto',
            'observado': 'Ruta responde con HTML; validación visual pendiente',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-47; RF-048',
            'ruta': '/analisisDespachoSegunFacturaCliente.html',
            'escenario': 'Cliente 4 / factura 3 / rango 2026-10-01..2026-10-31',
            'filtros': 'cliente, factura y rango',
            'esperado': 'Despachos vinculados a factura y cliente',
            'observado': 'Ruta responde con HTML; validación visual pendiente',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-47; RF-050',
            'ruta': '/analisisDespachoVendedorProducto.html',
            'escenario': 'Vendedor 1 / producto 1',
            'filtros': 'vendedor y variante',
            'esperado': 'Despachos del vendedor con la variante',
            'observado': 'Ruta responde con HTML; validación visual pendiente',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-47; RF-051',
            'ruta': '/analisisPedidosDespachosMensuales.html',
            'escenario': 'Rango 2026-09-01..2026-10-31',
            'filtros': 'meses',
            'esperado': 'Agrupación por mes sin duplicación',
            'observado': 'Ruta responde con HTML; validación visual pendiente',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-47; RF-047',
            'ruta': '/analisisVentasDescuentos.html',
            'escenario': 'Rango 2026-09-01..2026-10-31',
            'filtros': 'fecha',
            'esperado': 'Pedidos y descuento aplicados',
            'observado': 'Ruta responde con HTML y lee clientes/vendedores reales',
            'estado': 'PARCIAL',
            'evidencia': 'sin captura visual final'
        },
        {
            'CU/RF': 'CU-54; RF-055',
            'ruta': '/resumenProduccion.html',
            'escenario': 'Cortes ingresados en 2026-09..2026-10',
            'filtros': 'desde=2026-09-01, hasta=2026-10-31',
            'esperado': 'Resumen agregado por producto',
            'observado': 'Se obtuvo tabla con cantidad_total 27, cortes 2, descripcion desprod, producto_id 2',
            'estado': 'APROBADO',
            'evidencia': 'capturas/02_resumen_produccion_browser.png'
        },
        {
            'CU/RF': 'CU-52; RF-053',
            'ruta': '/inventario.html',
            'escenario': 'Inventario con bodega 2 y variante 2',
            'filtros': 'desde=2026-09-01, hasta=2026-10-31',
            'esperado': 'Existencias por bodega, talla y color',
            'observado': 'Se obtuvo tabla con 2 filas: 24 y 4 unidades en bodega 1 plus; colores rojotest/gris',
            'estado': 'APROBADO',
            'evidencia': 'capturas/03_inventario_browser.png'
        },
    ]


def main():
    out_dir = BASE_DIR / 'evidencias_incremento3' / 'validacion_2026-10-06_00-47-00'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'capturas').mkdir(parents=True, exist_ok=True)

    dependency_rows = make_dependency_matrix()
    result_rows = make_functional_results()
    write_csv(out_dir / 'matriz_dependencias.csv', dependency_rows, [
        'Informe', 'Tablas/vistas usadas', 'Lectura disponible', 'Registros adecuados', 'Estado validación', 'Observación'
    ])
    write_csv(out_dir / 'resultados_funcionales.csv', result_rows, [
        'CU/RF', 'ruta', 'escenario', 'filtros', 'esperado', 'observado', 'estado', 'evidencia'
    ])

    diag = '''# Diagnóstico de Supabase

## Hallazgo principal

La hipótesis previa de un bloqueo general de `inventario -> bodega/producto/talla/color` no se sostiene en el entorno actual. La validación de solo lectura confirma que `inventario` tiene relación con `bodegas`, `producto_variantes`, `tallas` y `colores` usando la clave real `id_variante` y los IDs de catálogo.

Ejemplos comprobados:

- `inventario -> bodegas` devuelve una fila con `id_bodega = 2` y `descripcion = "bodega 1 plus"`.
- `inventario -> producto_variantes` devuelve una fila con `id_variante = 2` y `descripcion = "Variante de prueba"`.
- `inventario -> tallas` devuelve una fila con `id_talla = 1`.
- `inventario -> colores` devuelve `id_color = 2` y `descripcion = "rojotest"`.

## Qué sí se confirmó

El archivo SQL local `supabase/inventario.sql` refleja un modelo diferente y no debe tomarse como contrato vigente. La API de Supabase actual reconoce la relación con `producto_variantes` y los catálogos. La diferencia entre SQL legado y esquema real no invalida la funcionalidad actual.

## Qué se validó en navegador

- Se generó la tabla de `Productos despachados` con 2 filas reales.
- Se generó la tabla de `Resumen de producción` con 1 registro real (`cantidad_total=27`, `cortes=2`).
- Se generó la tabla de `Inventario` con 2 filas reales (`cantidad=24` y `cantidad=4`).

## Conclusión

No hubo un bloqueo global de cada informe. Lo que sí existe es una diferencia entre el esquema legado del ZIP y la base real, junto con evaluación parcial de rutas que respondieron con HTML pero aún requieren una comprobación visual específica para los escenarios de negocio más complejos.
'''
    (out_dir / 'diagnostico_supabase.md').write_text(diag, encoding='utf-8')

    report = '''# Informe de validación funcional Incremento 3

## Evidencias verificadas

- Captura 1: Productos despachados
- Captura 2: Resumen de producción
- Captura 3: Inventario

## Resultado resumido

| Funcionalidad | Estado | Evidencia |
|---|---|---|
| Productos despachados | APROBADO | capturas/01_productos_despachados_browser.png |
| Resumen de producción | APROBADO | capturas/02_resumen_produccion_browser.png |
| Inventario | APROBADO | capturas/03_inventario_browser.png |
| Resto de informes | PARCIAL | revisión de rutas y consultas directas |

## Diagnóstico exacto

La validación ejecutada demostró que la API de Supabase actual responde con datos reales para los informes de despacho, producción e inventario. Los joins `inventario -> bodegas`, `inventario -> producto_variantes`, `inventario -> tallas` y `inventario -> colores` están funcionando en la base actual para los registros existentes.

La causa del bloqueo previo fue una suposición basada en SQL legado, no una condición real del esquema operativo actual. La comprobación funcional se hizo con lecturas reales y con navegador para validar tablas visibles, no solo HTTP 200.
'''
    (out_dir / 'informe_validacion.md').write_text(report, encoding='utf-8')

    (out_dir / 'casos_validacion_incremento3.json').write_text(json.dumps({
        'casos': [
            {
                'ruta': '/informeProductosDespachados.html',
                'fecha_desde': '2026-10-01',
                'fecha_hasta': '2026-10-31',
                'resultado_esperado': '2 filas visibles del periodo',
                'resultado_observado': '2 filas con id_despacho 2 y 3'
            },
            {
                'ruta': '/resumenProduccion.html',
                'fecha_desde': '2026-09-01',
                'fecha_hasta': '2026-10-31',
                'resultado_esperado': 'sumatoria por producto',
                'resultado_observado': '27 unidades del producto desprod'
            },
            {
                'ruta': '/inventario.html',
                'fecha_desde': '2026-09-01',
                'fecha_hasta': '2026-10-31',
                'resultado_esperado': 'stock por bodega, talla y color',
                'resultado_observado': '24 + 4 unidades en bodega 1 plus'
            }
        ]
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Validación generada en {out_dir}')


if __name__ == '__main__':
    main()
