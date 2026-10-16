# Checklist manual de verificación en navegador

## Preparación

Ejecuta `python pruebas/verificar_paginas_supabase.py --keep` y continúa solo si el reporte dice que la siembra terminó y `pruebas/ultimo_run.json` contiene los IDs. El script valida columnas/relaciones antes de insertar y, si una inserción o permiso falla, detiene la siembra y limpia en orden inverso los registros que alcanzó a crear. En la última ejecución observada, crear un producto no generó automáticamente ninguna fila en `producto_variantes`; el script se detuvo y limpió los registros. No intentes insertar manualmente una variante sin un contrato de columnas/FK confirmado ni sortear RLS. Se necesita el DDL vigente de `producto_variantes` para continuar de forma segura.

Al ejecutar el script, anota el prefijo `ZZTEST_<run_id>` y la fecha que imprime. Luego:

1. Inicia la aplicación con el entorno elegido y abre `http://127.0.0.1:5000/`.
2. Abre cada ruta de la tabla siguiente. Usa el rango de fechas impreso por el script si el script lo informa; para informes de fechas, usa el mismo día del pedido/corte/ despacho de prueba.
3. Comprueba la fila que contiene `ZZTEST_<run_id>` en la tabla renderizada. El HTML de `test_client` solo confirma los datos del JSON oculto; esta revisión confirma además el renderizado JavaScript.
4. Abre las herramientas de desarrollador y confirma que la consola no tenga excepciones de `renderTabla` ni errores de carga de datos.
5. Al terminar, ejecuta `python pruebas/verificar_paginas_supabase.py --cleanup`. Confirma que indique que se borraron los IDs guardados. No borres datos manualmente usando filtros generales.

| Página | Acción/filtros | Fila o estado esperado |
|---|---|---|
| `/reportes.html` | Abrir menú | Tarjetas de informes; no requiere semilla |
| `/informeProductosTerminados.html` | Desde/hasta: fecha de `fecha_ingreso` del corte | Producto de prueba con `ZZTEST_<run_id>` y su cantidad |
| `/informeProductosEnProceso.html` | Pulsar **Generar informe** | Corte con `estado = pendiente` y observaciones `ZZTEST_<run_id>` |
| `/informeProductosPendientesDespacho.html` | Pulsar **Generar informe** | Pedido pendiente y detalles de prueba en “Pedidos pendientes”; la ruta devuelve `datosInventario` vacío por la consulta actual con `productosPendientes=[]` |
| `/informeProductosDespachados.html` | Ingresar ambas fechas y buscar | Fila de despacho con los datos del pedido o factura filtrada por fecha; no se espera flash de desarrollo |
| `/analisisDespachoClienteProducto.html` | Seleccionar cliente y variante de prueba; buscar | Despacho asociado al cliente y pedido que incluye la variante; buscar el prefijo en ambas tarjetas |
| `/analisisDespachoVendedorProducto.html` | Seleccionar vendedor y variante de prueba; buscar | Despacho asociado al vendedor y pedido que incluye la variante |
| `/analisisPedidosDespachosMensuales.html` | Desde/hasta cubriendo pedido y despacho | Una fila `ZZTEST_<run_id>` en cada período, pedidos y despachos |
| `/analisisDespachoSegunFacturaCliente.html` | Seleccionar cliente/factura y rango de fechas; buscar | Filas de despachos relacionadas con la factura o el cliente dentro del rango |
| `/analisisVentasDescuentos.html` | Ingresar rango de fechas y buscar | Tabla con pedidos, clientes y vendedores; sin flash de desarrollo |
| `/analisisProductosPedidosDespachados.html` | Abrir la página | Estado “Este análisis está en desarrollo” |
| `/resumenProduccion.html` | Ingresar rango de fechas y buscar | Resumen agrupado por producto con cantidad total y número de cortes |
| `/inventario.html` | Ingresar rango de fechas y buscar | Tabla con bodega, producto, talla, color, cantidad y defectuosos |
| `/facturas.html` | Abrir si se incorpora una ruta Flask | Actualmente omitida: no existe esa ruta |
| `/crudDetallePedido.html` | Abrir si se incorpora una ruta Flask | Actualmente omitida: no existe esa ruta |
| `/verDetalle.html?id_pedido=<id>` | Abrir con el pedido de prueba si se incorpora una ruta Flask | Actualmente omitida: no existe esa ruta |

Las páginas “en desarrollo” no deben mostrar un error 500 al enviar su formulario. `/facturas.html`, `/crudDetallePedido.html` y `/verDetalle.html` no tienen rutas Flask actualmente, por lo que no se pueden revisar desde la aplicación. Para terminar la revisión, usa `python pruebas/verificar_paginas_supabase.py --cleanup` aunque cierres el navegador antes; comprueba que no queden IDs pendientes en el reporte.
