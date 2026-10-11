# Matriz de requerimientos versus casos de uso

Fuente: **Documento 0**, Tablas 8.1 y 8.2.

Los requerimientos de visualización de listas (por ejemplo, RF-004) se cubren con el caso de
uso de consulta de la entidad correspondiente, que incluye la lista con barra de scroll.

## Tabla 8.1

| RF | Descripción | Casos de uso |
| --- | --- | --- |
| RF-001 | Gestionar registros de clientes | CU-01.1 a CU-01.5 |
| RF-002 | Visualizar y navegar la lista completa de clientes con barra de scroll | CU-02 |
| RF-003 | Gestionar registros de colores | CU-03.1 a CU-03.4 |
| RF-004 | Visualizar y navegar el registro de colores con barra de scroll | CU-03.2 |
| RF-005 | Gestionar registros de bodegas | CU-05.1 a CU-05.4 |
| RF-006 | Visualizar y navegar el registro de bodegas con barra de scroll | CU-05.2 |
| RF-007 | Gestionar registros de vendedores | CU-07.1 a CU-07.4 |
| RF-008 | Visualizar y navegar el registro de vendedores con barra de scroll | CU-07.2 |
| RF-009 | Gestionar registros de zonas de venta | CU-09.1 a CU-09.4 |
| RF-010 | Visualizar y navegar el registro de zonas de venta con barra de scroll | CU-09.2 |
| RF-011 | Gestionar registros de tallas | CU-11.1 a CU-11.4 |
| RF-012 | Visualizar y navegar el registro de tallas con barra de scroll | CU-11.2 |
| RF-013 | Gestionar registros de productos | CU-13.1 a CU-13.5 |
| RF-014 | Visualizar y navegar el registro de productos con barra de scroll | CU-13.2 |
| RF-015 | Gestionar registros de códigos EAN con datos del artículo asociado, talla y color | CU-15.1 a CU-15.5 |
| RF-016 | Visualizar y navegar el registro de códigos EAN | CU-15.2 |
| RF-017 | Enviar solicitud de impresión a la máquina conectada al generar códigos EAN | CU-17 |
| RF-018 | Gestionar registros de cortes | CU-18.1 a CU-18.6 |
| RF-019 | Visualizar y navegar el registro de cortes con barra de scroll | CU-18.2 |
| RF-020 | Generar guía de cortes automáticamente | CU-20 |
| RF-021 | Ingresar productos a bodega tras ingresar código de guía de cortes | CU-21 |
| RF-022 | Gestionar registros de pedidos | CU-22.1 a CU-22.4 |
| RF-023 | Visualizar y navegar el registro de pedidos con barra de scroll | CU-22.2 |
| RF-024 | Por cada pedido, gestionar detalle de pedidos | CU-22.1, CU-24.1 |
| RF-025 | Anular un pedido existente | CU-25 |
| RF-026 | Calcular el monto total de un pedido automáticamente | CU-22.1, CU-24.1 |
| RF-027 | Calcular porcentaje de un pedido que se puede cumplir con el inventario actual | CU-27 |
| RF-028 | Calcular automáticamente los costos según compras, producción, y ventas | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-029 | Gestionar registros de facturas asociadas a pedidos | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-030 | Visualizar y navegar el registro de facturas con barra de scroll | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-031 | Generar informe de cobranza, mostrando facturas pendientes por cliente | CU-31 |
| RF-032 | Gestionar pagos asociados a facturas | CU-32.1 |
| RF-033 | Visualizar y navegar el registro de pagos con barra de scroll | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-034 | Automatizar los pedidos que se pueden pagar en base a los montos pagados y debidos | CU-34 |
| RF-035 | Gestionar notas de crédito | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-036 | Visualizar y navegar el registro de notas de crédito con barra de scroll | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-037 | Gestionar registros de inventario por producto, talla y color en cada bodega | CU-38 |
| RF-038 | Visualizar stock actual por producto, talla, color y bodega con filtros | CU-38 |
| RF-039 | Actualizar automáticamente el inventario al registrar producción, despacho o recepción | CU-39 |
| RF-040 | Generar resumen de pedido | CU-40 |
| RF-041 | Buscar y agrupar resúmenes de pedido | CU-40 |
| RF-042 | Generar informe de productos pendientes de despacho | CU-42 |
| RF-043 | Buscar y agrupar informes de productos pendientes de despacho | CU-42 |
| RF-044 | Generar análisis comparativo de productos pedidos versus despachados | Sin CU (Incremento 4) |
| RF-045 | Generar informe de productos despachados | CU-45 |
| RF-046 | Buscar y agrupar informes de productos despachados | CU-45 |
| RF-047 | Análisis de ventas y descuentos | CU-47 |
| RF-048 | Análisis de despachos según factura y cliente | CU-47 |
| RF-049 | Análisis de despachos a cliente por producto | CU-47 |
| RF-050 | Análisis de despachos por vendedor y producto | CU-47 |
| RF-051 | Análisis de pedidos y despachos mensuales | CU-47 |
| RF-052 | Inventario de productos terminados entre fechas | CU-52 |
| RF-053 | Análisis de inventario | CU-52 |
| RF-054 | Informe de productos en proceso | CU-54 |
| RF-055 | Resumen de producción | CU-54 |
| RF-056 | Permitir configuración de parámetros del sistema | Sin CU en el Documento 0 (ver Tabla 8.2) |
| RF-057 | Soportar múltiples usuarios con distintos niveles de acceso y control | CU-57.1 a CU-57.4 |
| RF-058 | Permitir la limitación y autorización del resto de usuarios por parte del administrador | CU-58 |
| RF-059 | Exportar documentos y listas en formatos Excel y PDF | CU-59 |
| RF-060 | Permitir traspaso de información desde el sistema original | CU-60, CU-60.1 |
| RF-061 | Cambiar la interfaz mejorada (reducir clics, incluir atajos) | Sin CU en el Documento 0 (ver Tabla 8.2) |

## Tabla 8.2: requerimientos con su caso de uso en el Incremento 2

Estos casos de uso están en [casos-de-uso-incremento-2.md](casos-de-uso-incremento-2.md).

| RF | Caso de uso en el Incremento 2 |
| --- | --- |
| RF-028 | CU-28 |
| RF-029 | CU-29.1 a CU-29.4 |
| RF-030 | CU-30 |
| RF-033 | CU-33 |
| RF-035 | CU-35.1 a CU-35.4 |
| RF-036 | CU-36 |
| RF-056 | CU-56 |
| RF-061 | CU-61 |

## Inconsistencias conocidas entre documentos

Estas diferencias están en los documentos originales. No están corregidas aquí; sirven para no
confundirse al buscar un CU.

- **Informes (RF-042 a RF-055).** La Tabla 8.1 agrupa varios RF bajo CU-42, CU-45, CU-47, CU-52
  y CU-54, pero el capítulo 7 del Documento 0 ya tiene un CU por RF: CU-43 (RF-043), CU-46
  (RF-046), CU-48 a CU-51 (RF-048 a RF-051), CU-53 (RF-053) y CU-55 (RF-055). Para implementar,
  usar el CU específico del capítulo 7.
- **Incremento 3.** Su documento usa la agrupación de la Tabla 8.1 (CU-42, CU-45, CU-47, CU-52,
  CU-54) y sus pruebas PR-01 a PR-13 están escritas sobre esa agrupación.
- **Incremento 1.** Su matriz usa números de RF desplazados (RF-019 a RF-022 para cortes y
  pedidos) y CU de lista separados (CU-04, CU-06, CU-08, CU-10, CU-12, CU-14, CU-16, CU-19,
  CU-23). El Documento 0 corregido reemplazó esa numeración; usar la de este archivo.
- **CU-24.1 / CU-24.2 a CU-24.4.** El Documento 0 solo tiene CU-24.1; consultar, modificar y
  eliminar detalle de pedido están en el Incremento 2.
