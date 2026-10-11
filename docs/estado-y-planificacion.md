# Estado del proyecto y planificación

Fuentes: Documento 0 (Tabla 10.1), documento del Incremento 3 (Tablas 2.1, 3.1, 4.1, 7.2, 7.3,
8.3 y 9.1) y Sprint Backlog del Incremento 4 (planilla `Sprint Backlog Grupo 25 I. Software inc 4.xlsx`).

Metodología: **Scrum++**, con entregas por incrementos. Según el Documento 0, el Incremento 1
cubre alrededor del 30% de los requerimientos, el 2 llega al 70%, el 3 al 95% y el 4 al 100%.

## Calendario general (Documento 0, Tabla 10.1)

| Actividad | Inicio | Término |
| --- | --- | --- |
| Documento 0 | 14/04/2026 | 19/04/2026 |
| Presentación Documento 0 | 21/04/2026 | 21/04/2026 |
| Incremento 1 | 21/04/2026 | 14/06/2026 |
| Presentación Incremento 1 | 17/06/2026 | 17/06/2026 |
| Incremento 2 | 17/06/2026 | 13/09/2026 |
| Presentación Incremento 2 | 26/09/2026 | 26/09/2026 |
| Incremento 3 | 26/09/2026 | 25/10/2026 |
| Presentación Incremento 3 | 28/10/2026 | 28/10/2026 |
| Incremento 4 | 28/10/2026 | 15/11/2026 |
| Presentación Incremento 4 | 18/11/2026 | 18/11/2026 |

El documento del Incremento 3 registra otras fechas para su sprint: del 26/09/2026 al
04/10/2026, con presentación el 05/10/2026. La planilla del Incremento 4 indica término el 15/11/2026.

## Requerimientos por incremento

| Incremento | Requerimientos | Estado |
| --- | --- | --- |
| 1 (20 RF) | RF-001 a RF-016, RF-018, RF-019, RF-022, RF-023 | Completado |
| 2 (23 RF) | RF-017, RF-020, RF-021, RF-024 a RF-041, RF-056, RF-061 | Completado |
| 3 (13 RF) | RF-042, RF-043, RF-045 a RF-055 | Completado según el Sprint Backlog (04/10/2026) |
| 4 (5 RF) | RF-044, RF-057, RF-058, RF-059, RF-060 | Pendiente |

Con el Incremento 3, el proyecto cubre 56 de 61 RF (91,8%).

## Incremento 3: módulo de informes

### Cambios al modelo de datos (Tabla 7.2)

| Elemento | Tipo de cambio | Descripción | RF |
| --- | --- | --- | --- |
| `despachos` | Tabla nueva | Encabezado de cada despacho: número de guía correlativo (GD-000001), fecha, pedido, factura asociada (opcional), bodega de origen, vía de despacho, estado (emitido o anulado) y datos de anulación. El cliente y el vendedor se obtienen del pedido. | RF-042 a RF-051, RF-054 |
| `detalle_despachos` | Tabla nueva | Productos de cada despacho: línea del pedido despachada, cantidad, precio unitario y porcentaje de descuento aplicado. | RF-045 a RF-050 |
| `inventario.cantidad_defectuosa` | Columna nueva | Unidades con defectos por producto, talla, color y bodega, separadas del stock disponible. | RF-053 |
| `clientes.descuento_1`, `descuento_2`, `descuento_3` | Columnas nuevas | Hasta tres descuentos porcentuales por cliente (RF-001), que se aplican en cascada al despachar. | RF-047 |
| `cortes.id_pedido` | Columna nueva (opcional) | Pedido para el cual se realiza un corte, para relacionar la producción en proceso con los pedidos. | RF-054 |
| `movimientos_inventario.tipo` | Valores nuevos | `despacho`, `anulacion_despacho` y `defecto`, para que cada salida o cambio de stock quede registrado con su origen. | RF-039, RF-053 |

Las tablas `ventas` y `detalle_ventas` (del Incremento 1) **no se usan**: no se relacionan con
pedidos ni facturas y no permiten saber qué parte de un pedido fue despachada. Los datos de
venta se obtienen de pedidos, facturas y despachos.

### Funciones de base de datos

Las operaciones de despacho se implementaron como funciones de la base de datos, para que las
validaciones y la actualización del inventario ocurran en una sola transacción (RNF-012):

- `registrar_despacho`: valida que la cantidad despachada no supere lo pendiente del pedido ni
  el stock de la bodega, descuenta el inventario y marca el pedido como despachado cuando se
  entrega por completo.
- `anular_despacho`: devuelve las unidades a la bodega de origen y deja el pedido nuevamente
  disponible para despacho.
- `registrar_defectuosos`: traslada unidades del stock disponible al stock con defectos.

Cada operación queda registrada en `movimientos_inventario`. La cantidad pendiente de cada línea
de pedido se calcula como lo pedido menos lo anulado y lo despachado; no se almacena.

### Vistas SQL por informe (Tabla 7.3)

| RF | Vista |
| --- | --- |
| RF-042, RF-043 | `v_pendientes_despacho` (detalle de pedidos, despachos e inventario) |
| RF-045, RF-046 | `v_despachos_detalle` |
| RF-047 | `v_despachos_detalle` (precio de venta, descuento y subtotal neto por despacho) |
| RF-048 a RF-050 | `v_despachos_detalle` (factura, cliente, producto y vendedor) |
| RF-051 | `v_pedidos_despachos_mensual` |
| RF-052 | `v_produccion_terminada` |
| RF-053 | `v_inventario_analisis` (stock disponible, unidades con defectos y unidades comprometidas en pedidos) |
| RF-054 | `v_productos_en_proceso` (cortes aún no ingresados a bodega) |
| RF-055 | `v_produccion_terminada` |

La aplicación solo aplica sobre cada vista los filtros que indica el usuario (fechas, cliente,
vendedor, etc.). El SQL está en `supabase/incremento3_despachos.sql`.

### Códigos EAN con formato propio (RF-015 a RF-017)

Durante el Incremento 3 se incorporó la generación de códigos EAN con el formato de la empresa.
Cada código tiene 13 dígitos: un prefijo, el código del producto, el del color y el de la talla,
más el dígito verificador de EAN-13. El prefijo y la cantidad de dígitos de cada parte se
configuran en `parametros_sistema` (`ean_prefijo`, `ean_digitos_producto`, `ean_digitos_color`,
`ean_digitos_talla`). A una variante que no siga el formato general se le puede asignar un código manual; la marca
booleana `producto_variantes.ean_manual` hace que ese código se conserve aunque cambien los
códigos del producto, el color o la talla. SQL en `supabase/incremento3_ean.sql`; lógica en `ean13.py`; pruebas en
`tests/test_ean.py`.

### Componentes (Tabla 8.3)

| RF | CU | Pantalla |
| --- | --- | --- |
| RF-042, RF-043 | CU-42 (y CU-43) | Informe de productos pendientes de despacho |
| RF-045, RF-046 | CU-45 (y CU-46) | Informe de productos despachados |
| RF-047 a RF-051 | CU-47 (y CU-48 a CU-51) | Análisis de ventas y despachos |
| RF-052, RF-053 | CU-52 (y CU-53) | Informe de inventario |
| RF-054, RF-055 | CU-54 (y CU-55) | Informes de producción |

La exportación a PDF y Excel corresponde a RF-059 (Incremento 4); en el Incremento 3 la
interfaz quedó preparada para incorporarla.

### Pruebas funcionales (Tabla 9.1)

Precondición común: el usuario está autenticado con permisos sobre el módulo de informes y
existen registros en las tablas relevantes a cada informe.

| ID | RF / CU | Pasos | Resultado esperado |
| --- | --- | --- | --- |
| PR-01 | RF-042 / CU-42 | Informes > Productos pendientes de despacho; definir rango de fechas y aplicar filtros. | Se detallan los productos ya fabricados que aún no se han despachado, entre las fechas ingresadas. |
| PR-02 | RF-043 / CU-42 | Igual que PR-01. | Se puede buscar por pedidos, por clientes y por vendedor. |
| PR-03 | RF-045 / CU-45 | Informes > Productos despachados; definir rango de fechas y aplicar filtros. | Se detallan los productos despachados y sus pedidos, entre las fechas elegidas. |
| PR-04 | RF-046 / CU-45 | Igual que PR-03. | Se puede buscar por pedido, por cliente, por factura y por producto. |
| PR-05 | RF-047 / CU-47 | Informes > Análisis de ventas y despachos; elegir tipo de análisis y filtros. | Se detalla el precio de venta y los descuentos de cierto despacho. |
| PR-06 | RF-048 / CU-47 | Igual que PR-05. | Se detalla el número y detalle de los despachos hechos a cierto cliente. |
| PR-07 | RF-049 / CU-47 | Igual que PR-05. | Se detalla cuántos y qué productos se despachan según cliente. |
| PR-08 | RF-050 / CU-47 | Igual que PR-05. | Se detalla cuántos y qué productos se despachan según vendedor. |
| PR-09 | RF-051 / CU-47 | Igual que PR-05. | Se detallan los pedidos y despachos realizados según mes. |
| PR-10 | RF-052 / CU-52 | Informes > Inventario; elegir tipo de informe y parámetros. | Se detallan los productos terminados entre fechas elegidas. |
| PR-11 | RF-053 / CU-52 | Igual que PR-10. | Se detalla el inventario según stock, productos con defectos y asociación a pedidos. |
| PR-12 | RF-054 / CU-54 | Informes > Producción; elegir tipo de informe y filtros. | Se detallan los productos en proceso según cortes, pedidos y despachos. |
| PR-13 | RF-055 / CU-54 | Igual que PR-12. | Se detalla la cantidad de productos, tipo, color y talla realizados entre fechas elegidas. |

El documento del Incremento 3 marca estas pruebas como completadas, pero su matriz de
trazabilidad (Tabla 12.1) todavía tiene implementación y evidencia como "Pendiente". Varias
evidencias usaron datos de demostración.

## Incremento 4: Sprint Backlog

Fuente: planilla `Sprint Backlog Grupo 25 I. Software inc 4.xlsx`. Término previsto: 15/11/2026.
Ninguna tarea tiene responsable asignado todavía.

| Tarea | HH est. | Estado | Objetivo |
| --- | --- | --- | --- |
| Calcular porcentaje de un pedido que se puede cumplir con el inventario actual | 3 | Por empezar | Calcular y mostrar, en porcentaje y números absolutos, la porción de un pedido que se puede cumplir según el inventario actual. |
| Generar análisis comparativo de productos pedidos versus despachados entre fechas escogidas (RF-044) | 2 | Progresado en incremento anterior | Calcular y mostrar los productos pedidos y los despachados, mostrando información relevante como el cambio en productos pendientes neto. |
| Soportar múltiples usuarios con distintos niveles de acceso y control (RF-057) | 2 | Por empezar | Que distintos usuarios puedan tener distintos niveles de acceso a la base de datos. |
| Permitir la limitación y autorización del resto de usuarios por parte del administrador (RF-058) | 2 | Por empezar | Que el administrador pueda crear nuevos usuarios y personalizar sus permisos. |
| Asegurar el formato de los informes | 5 | Por empezar | Una vez se confirme con el usuario, asegurar que el formato de los informes sea el correcto. |
| Exportar documentos y listas en formatos Excel y PDF (RF-059) | 2 | Por empezar | Que todos los informes relevantes se puedan exportar en Excel, PDF y/o imprimir según corresponda. |
| Permitir traspaso de información desde el sistema original (RF-060) | 3 | Por empezar | Luego de confirmar el formato de los datos con el usuario, permitir su traspaso al sistema actual. |
| Cambiar precios para que se puedan tener por talla y color además de producto | 4 | Por empezar | El usuario quiere poder darle un precio distinto a un producto según su talla y color. |
| Actualizar CRUD anteriores para tomar en cuenta campos añadidos | 3 | Por empezar | Campos nuevos, como los descuentos de los clientes, dejaron los módulos CRUD desactualizados. |
| Arreglar redundancia, como las tablas producto y producto_variantes | 4 | Por empezar | La distinción entre producto y producto variante causa confusión e inconsistencia y no es necesaria; quitarla. |
| Mover el sistema a una base de datos local | 5 | Por empezar | Que el sistema ya no use Supabase, sino que sea local y no requiera conexión a internet (RNF-011). |
| Probar que todo el sistema funciona, tomando capturas de evidencia | 5 | Por empezar | Asegurar que todo funcione y tomar capturas para el manual. |
| Crear el manual de usuario | 5 | Por empezar | Que toda la documentación que un usuario pueda necesitar esté en el manual de forma clara. |
| Guiar al usuario para que grabe el video donde se muestra cada función del sistema | 6 | Por empezar | Video de demostración de cada parte del sistema. |
| Ayudar al usuario a grabar el video de aceptación | 1 | Por empezar | Guion que el usuario pueda practicar y seguir para el video de aceptación. |
| Calcular automáticamente los costos según compras, producción y ventas (RF-028) | 2 | Por empezar | Luego de preguntarle al usuario por los costos, calcularlos automáticamente y mostrárselos. |
| Implementar CRUD de despachos | 2 | Por empezar | Creación, lectura, actualización y eliminación de los despachos. |
