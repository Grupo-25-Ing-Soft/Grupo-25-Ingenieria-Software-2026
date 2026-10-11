# Requerimientos del sistema

Fuente: **Documento 0** (versión corregida, octubre 2026), secciones 6.1, 6.3, 6.4 y Tabla 6.1.
Hay 61 requerimientos funcionales (RF-001 a RF-061) y 15 no funcionales (RNF-001 a RNF-015).

## Usuarios (6.1)

- **Administrador:** usuario con control completo del sistema. Tiene acceso a todas las funciones y puede dar o quitar acceso de cualquier parte del sistema al resto de usuarios.
- **Asistente:** cualquier usuario no administrador. Su acceso al sistema queda limitado a lo que permita el administrador.

Los casos de uso también nombran a los roles **vendedor**, **jefa de taller** y **asistente de finanzas**.

## Requerimientos funcionales (6.3)

### Archivos maestros

Los archivos maestros son una colección de registros con información relevante a la producción.

**Clientes**
- **RF-001:** Manipulación de registros. Se debe poder crear, modificar, consultar y eliminar registros de clientes. Cada registro consiste del código del cliente, el rut del cliente con el dígito verificador separado, el número de lista de precios, el nombre completo del cliente, abreviación del nombre, dirección del cliente, comuna, ciudad, hasta 2 números de teléfono, giro, zona, código de vendedor, vía de despacho, condiciones de venta, hasta 3 descuentos por cliente en porcentaje, porcentaje de comisión, porcentaje de cobranza, y observaciones.
- **RF-002:** Vista de los clientes. Se debe poder ver la lista de los clientes, en la que deben aparecer todos los datos ingresados. Debe poder manejarse con una barra de scroll, e incluir una barra de búsqueda por nombre.

**Colores**
- **RF-003:** Se debe poder crear, modificar, consultar, y eliminar registros de colores. Cada registro consiste del código del color, y su descripción.
- **RF-004:** Vista de colores. Lista de colores con todos los datos ingresados, barra de scroll y barra de búsqueda por descripción.

**Bodegas**
- **RF-005:** Se debe poder crear, modificar, consultar, y eliminar registros de bodegas. Cada registro consiste del código y descripción de cada bodega.
- **RF-006:** Vista de bodegas. Lista de bodegas con todos los datos ingresados, barra de scroll y barra de búsqueda por descripción.

**Vendedores**
- **RF-007:** Se debe poder crear, modificar, consultar, y eliminar registros de vendedores. Cada registro consiste del código del vendedor, su rut, su dígito verificador en un campo aparte, el nombre del vendedor, y el porcentaje de comisión.
- **RF-008:** Vista de vendedores. Lista de vendedores con todos los datos ingresados, barra de scroll y barra de búsqueda por nombre.

**Zonas de venta**
- **RF-009:** Se debe poder crear, modificar, consultar, y eliminar registros de zonas de venta. Cada registro consiste del código y la descripción de zona.
- **RF-010:** Vista de zonas de venta. Lista de zonas de venta con todos los datos ingresados, barra de scroll y barra de búsqueda por descripción.

**Tallas**
- **RF-011:** Se debe poder crear, modificar, consultar, y eliminar registros de tallas. Cada registro consiste de una cantidad virtualmente ilimitada de tallas.
- **RF-012:** Vista de tallas. Lista de tallas con todos los datos ingresados y barra de scroll.

**Productos**
- **RF-013:** Se debe poder crear, modificar, consultar, y eliminar registros de productos. Cada registro consiste del código de producto, una cantidad virtualmente ilimitada de colores, la descripción y abreviación, una cantidad virtualmente ilimitada de precios mayores, el precio costo, el precio liquidación, el precio detalle, el código de talla asociado. Los precios deben ser ajustables por cada talla y color.
- **RF-014:** Vista de productos. Lista de productos con todos los datos ingresados, barra de scroll y barra de búsqueda por descripción.

**Códigos EAN**
- **RF-015:** Se debe poder crear, modificar, consultar, y eliminar registros de códigos EAN. Cada registro consiste del código del artículo asociado.
- **RF-016:** Vista de códigos EAN. Lista con el código del artículo, su descripción, el código EAN generado, talla, y color. Barra de scroll y barra de búsqueda por descripción del artículo.
- **RF-017:** Emisión de códigos EAN. Se debe poder ingresar el código del producto, su código de color, y la cantidad de códigos por cada talla. Al aceptar, se enviará una solicitud de impresión a la máquina conectada.

### Producción

**Cortes**
- **RF-018:** Se debe poder crear, editar, consultar y eliminar registros de cortes. Cada registro consiste del código de corte, fecha de corte, cortador, tela a cortar, color, cantidad, y observaciones.
- **RF-019:** Vista de cortes. Lista de cortes con todos los datos ingresados, barra de scroll, y filtros por fecha y cortador.
- **RF-020:** Al ingresar un registro de corte, se debe generar automáticamente una guía de cortes, que ha de actualizarse si se realiza algún cambio al corte. La guía de cortes posee toda la información previamente ingresada, y debe poder imprimirse en formato PDF para enviárselo al taller.

**Ingreso de producción a bodega**
- **RF-021:** Se debe poder ingresar el código de una guía de cortes, a continuación de lo cuál se considerará enviado a taller, y los productos fabricados entrarán a inventario.

**Pedidos**
- **RF-022:** Se debe poder crear, editar, consultar y eliminar registros de pedidos. Cada registro consiste del número de pedido asociado, código cliente, fecha del pedido, código del vendedor, y fecha de entrega.
- **RF-023:** Vista de pedidos. Lista de pedidos con todos los datos ingresados, barra de scroll, y filtros por cliente y fecha.
- **RF-024:** Se debe poder realizar un detalle de pedido, en el que se pueda asociar un pedido a uno o más códigos de producto, color, y tallas, con diferentes cantidades de producto por tallas.
- **RF-025:** Se debe poder anular pedidos.
- **RF-026:** Se debe calcular automáticamente el monto total de un pedido.
- **RF-027:** Debe calcularse automáticamente el porcentaje de un pedido que puede ser completado con el inventario actual.

### Ventas

- **RF-028:** En el módulo de finanzas, se debe obtener el cálculo automático de costos según compras, producción, y ventas.

**Facturas**
- **RF-029:** Se debe poder crear, editar, consultar y eliminar registros de facturas. Cada registro consiste del número de factura, código del cliente asociado, fecha de emisión de la factura, fecha límite de pago de la factura, monto a pagar, y si está pagada o no.
- **RF-030:** Vista de facturas. Lista de facturas con todos los datos ingresados, barra de scroll, y filtros por cliente y fecha.

**Informe de cobranzas**
- **RF-031:** El sistema debe permitir generar un informe de cobranzas, que debe incluir todas las facturas por pagar de un cliente específico.

**Pagos de facturas**
- **RF-032:** Se debe poder crear, editar, consultar y eliminar registros de pagos. Cada registro consiste del código de pago, número de factura o facturas asociadas, código del cliente asociado, fecha de emisión del pago, monto a pagar, y método de pago.
- **RF-033:** Vista de pagos. Lista de pagos con todos los datos ingresados, barra de scroll, y filtros por cliente y fecha.
- **RF-034:** Se debe automatizar las facturas disponibles a cancelar con cierto pago en base a los montos del pago y las facturas.

**Notas de crédito**
- **RF-035:** Se debe poder generar, modificar, ver, y eliminar notas de crédito asociadas a devoluciones y ajustes. Cada registro contiene el código de la nota de crédito, monto, cliente asociado, y fecha de emisión.
- **RF-036:** Vista de notas de crédito. Lista de notas de crédito con todos los datos ingresados, barra de scroll, y filtros por cliente, monto, y fecha.

### Informes

**Inventario**
- **RF-037:** Se debe poder ver los productos en inventario y su talla, color, y bodega, además de añadir, modificar, y eliminar dichos productos del inventario.
- **RF-038:** Se debe poder filtrar el stock actual por producto, talla, color, y bodega.
- **RF-039:** El inventario debe actualizarse automáticamente en base a la producción, despacho, y recepción de productos.

**Resúmenes de pedido**
- **RF-040:** Para un pedido seleccionado, se detalla en una tabla los productos, su color, talla, cantidad, costo de realización, precio a pagar por el cliente, fecha límite de despacho, y fecha límite de pago.
- **RF-041:** Se debe poder buscar pedidos por productos incluídos, por clientes, y por vendedor, de forma resumida en una sola pantalla, y de forma detallada mostrando toda la información del pedido.

**Informe de productos pendientes de despacho**
- **RF-042:** Se detallan los productos ya fabricados que aún no se han despachado, entre fechas imputadas por el usuario.
- **RF-043:** Se debe poder buscar por pedidos, por clientes, y por vendedor.
- **RF-044:** Se debe poder ver una comparativa que muestre los productos pedidos versus los despachos entre fechas elegidas por el usuario.

**Informe de productos despachados**
- **RF-045:** Se detallan los productos despachados, y sus pedidos correspondientes, entre las fechas que elija el usuario.
- **RF-046:** Se debe poder buscar por pedido, por cliente, por factura, y por producto.

**Análisis**
- **RF-047:** Análisis de ventas y descuentos. Se detalla el precio de venta y descuentos realizados en cierto despacho seleccionado.
- **RF-048:** Despachos según factura y cliente. Se detalla el número y detalles sobre los despachos hechos a cierto cliente.
- **RF-049:** Análisis de despachos a cliente por producto. Se detalla cuántos y qué productos se despachan según cliente.
- **RF-050:** Despachos por vendedor y producto. Se detalla cuántos y qué productos se despachan según vendedor.
- **RF-051:** Análisis de pedidos y despachos mensuales. Se detallan los pedidos y despachos realizados según mes.
- **RF-052:** Inventario de productos terminados. Se detallan los productos terminados entre fechas elegidas por el usuario.
- **RF-053:** Análisis de inventario. Se detalla el inventario según productos en stock, productos con defectos y si los productos están asociados a pedidos.

**Informes de producción**
- **RF-054:** Productos en proceso. Se detallan los productos en proceso según la información de los cortes, pedidos, y despachos.
- **RF-055:** Resumen de producción. Se detallan la cantidad de productos, tipo, color, y talla realizados entre fechas elegidas por el usuario.

### Misceláneos

- **RF-056:** El sistema debe permitir configurar los parámetros globales del nombre de la empresa, logotipo, y valores de impuestos.
- **RF-057:** El sistema debe permitir la existencia de usuarios con distintos niveles de control y acceso.
- **RF-058:** El usuario administrador debe poder limitar y autorizar a los demás usuarios a controlar y acceder a los módulos de su elección.
- **RF-059:** El sistema debe permitir la exportación de documentos y listas en formatos Excel y PDF.
- **RF-060:** El sistema debe permitir el traspaso de información desde el sistema original.
- **RF-061:** Cambiar la interfaz mejorada en pos de la eficiencia del programa y tiempo del usuario (reducir clics, incluir atajos). Incorporado durante el Incremento 2.

## Requerimientos no funcionales (6.4)

### Interfaz
- **RNF-001:** El registro de tallas, y cualquiera más que funcione con espacio variable, debe alinearse a las casillas correspondientes en los demás registros que los utilicen.
- **RNF-002:** Con el fin de future-proofing, cada elemento de la interfaz debe ser autoexplicativo. Por ejemplo, los distintos modificadores del precio no deben tener los mismos nombres, sino diferentes nombres que expliquen sus diferencias y función.
- **RNF-003:** Excepto los campos en que se debe ingresar datos mediante el teclado, la interfaz debe ser usable con solo el mouse.
- **RNF-004:** Cada campo, botón y sección de la interfaz deberá contar con un nombre o etiqueta clara y descriptiva que permita al usuario identificar fácilmente su función. Los distintos tipos de precio (costo, detalle, mayorista y liquidación) deberán estar correctamente diferenciados mediante denominaciones explícitas que reflejen su propósito.
- **RNF-005:** El sistema deberá implementar desplazamiento vertical continuo en todas las vistas del listado de registros (clientes, productos, pedidos, colores) mediante barra de scroll.
- **RNF-006:** Ante errores de validación (como RUT inválido, código duplicado o campos obligatorios vacíos), el sistema deberá mostrar un mensaje claro que identifique explícitamente el campo con problema y describa el criterio requerido en lenguaje comprensible para el usuario, evitando tecnicismos.
- **RNF-007:** El sistema deberá implementar un mecanismo de confirmación previa para cualquier acción de eliminación de registros (clientes, productos, pedidos, etc.), mediante un mensaje que identifique de forma explícita el registro afectado. La eliminación solo se ejecutará una vez que el usuario confirme la acción.

### Seguridad
- **RNF-008:** Autenticación basada en usuario y contraseña. Las contraseñas deberán almacenarse utilizando funciones de hash seguras y no reversibles, nunca en texto plano.
- **RNF-009:** Control de acceso basado en roles (RBAC), que limite la disponibilidad de módulos y operaciones según los permisos asignados a cada usuario. El administrador podrá autorizar o bloquear los campos a los que tienen acceso los demás tipos de usuario.
- **RNF-010:** Auditoría que registre todas las operaciones críticas (creación, modificación y eliminación de registros, y accesos al sistema). Cada registro deberá almacenar la identificación del usuario, la acción realizada, el tipo de entidad afectada y la fecha y hora exacta del evento.

### Disponibilidad
- **RNF-011:** El sistema deberá operar dentro de la red interna de la empresa sin requerir conexión a internet para la ejecución de sus funcionalidades.
- **RNF-012:** El sistema deberá utilizar transacciones en la base de datos para garantizar que, ante fallos inesperados, no se registren datos parciales que comprometan la integridad de la información.

### Compatibilidad
- **RNF-013:** El sistema deberá ejecutarse correctamente en Windows 10 y Windows 11, reemplazando la dependencia del sistema anterior basado en Windows 7.
- **RNF-014:** Integración del módulo de emisión de códigos EAN con la impresora de etiquetas instalada en el equipo de la empresa, utilizando el protocolo y formato de impresión soportado por el dispositivo.
- **RNF-015:** Archivos de exportación Excel compatibles con Microsoft Excel 2016 o superior. Archivos PDF 1.7 que cumplan el estándar y sean visualizables sin errores en cualquier visor de PDF compatible.

## Especificación ESA (Tabla 6.1)

Codificación:
- **Nec.** (necesidad): 1 = esencial, 2 = negociable
- **Prio.** (prioridad): número del incremento en que se aborda (1 a 4)
- **Estab.** (estabilidad): 1 = alta, 2 = media, 3 = baja
- **Clar.** (claridad): 1 = precisa, 2 = ambigua, 3 = no clara
- **Verif.** (verificabilidad): 1 = sí, 2 = no
- **Fuente:** 1 = requerimiento de usuario, 2 = equipo de proyecto

| ID | Descripción | Nec. | Prio. | Estab. | Clar. | Verif. | Fuente |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-001 | Gestionar registros de clientes (crear, modificar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 2 | 2 | 1 | 1 |
| RF-002 | Visualizar y navegar la lista completa de clientes con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-003 | Gestionar registros de colores (crear, modificar, consultar, eliminar) | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-004 | Visualizar y navegar el registro de colores con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-005 | Gestionar registros de bodegas (crear, modificar, consultar, eliminar) | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-006 | Visualizar y navegar el registro de bodegas con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-007 | Gestionar registros de vendedores (crear, modificar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-008 | Visualizar y navegar el registro de vendedores con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-009 | Gestionar registros de zonas de venta (crear, modificar, consultar, eliminar) | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-010 | Visualizar y navegar el registro de zonas de venta con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-011 | Gestionar registros de tallas (crear, modificar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 1 | 2 | 1 | 1 |
| RF-012 | Visualizar y navegar el registro de tallas con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-013 | Gestionar registros de productos (crear, modificar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 2 | 2 | 1 | 1 |
| RF-014 | Visualizar y navegar el registro de productos con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-015 | Gestionar registros de códigos EAN con datos del artículo asociado, talla y color | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-016 | Visualizar y navegar el registro de códigos EAN | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-017 | Enviar solicitud de impresión a la máquina conectada al generar códigos EAN | 1 | 2 | 2 | 2 | 1 | 1 |
| RF-018 | Gestionar registros de cortes (crear, editar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 1 | 2 | 1 | 1 |
| RF-019 | Visualizar y navegar el registro de cortes con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-020 | Generar guía de cortes automáticamente | 1 | 2 | 2 | 1 | 1 | 1 |
| RF-021 | Ingresar productos a bodega tras ingresar código de guía de cortes correspondiente | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-022 | Gestionar registros de pedidos (crear, editar, consultar, eliminar) con todos los campos requeridos | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-023 | Visualizar y navegar el registro de pedidos con barra de scroll | 1 | 1 | 1 | 1 | 1 | 1 |
| RF-024 | Por cada pedido, gestionar detalle de pedidos (crear, editar, consultar, eliminar), con todos lo campos requeridos | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-025 | Anular un pedido existente | 1 | 2 | 2 | 1 | 1 | 2 |
| RF-026 | Calcular el monto total de un pedido automáticamente | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-027 | Calcular porcentaje de un pedido que se puede cumplir con el inventario actual | 2 | 2 | 2 | 2 | 1 | 1 |
| RF-028 | Calcular automáticamente los costos según compras, producción, y ventas | 1 | 2 | 2 | 1 | 1 | 2 |
| RF-029 | Gestionar registros de facturas (crear, editar, consultar, eliminar) asociadas a pedidos | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-030 | Visualizar y navegar el registro de facturas con barra de scroll | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-031 | Generar informe de cobranza, mostrando facturas pendientes por cliente | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-032 | Gestionar pagos asociados a facturas (registrar, consultar, modificar, anular) | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-033 | Visualizar y navegar el registro de pagos con barra de scroll | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-034 | Automatizar los pedidos que se pueden pagar en base a los montos pagados y debidos | 1 | 2 | 1 | 2 | 1 | 1 |
| RF-035 | Gestionar notas de crédito (crear, modificar, consultar, eliminar) | 2 | 2 | 2 | 1 | 1 | 2 |
| RF-036 | Visualizar y navegar el registro de notas de crédito con barra de scroll | 2 | 2 | 2 | 1 | 1 | 2 |
| RF-037 | Gestionar registros de inventario por producto, talla y color en cada bodega | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-038 | Visualizar stock actual por producto, talla, color y bodega con filtros de búsqueda | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-039 | Actualizar automáticamente el inventario al registrar producción, despacho o recepción | 1 | 2 | 2 | 1 | 1 | 1 |
| RF-040 | Generar resumen de pedido | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-041 | Buscar y agrupar resúmenes de pedido según fecha, según productos, según clientes, y según vendedores | 1 | 2 | 1 | 1 | 1 | 1 |
| RF-042 | Generar informe de productos pendientes de despacho | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-043 | Buscar y agrupar informes de productos pendientes de despacho según fecha, pedidos, clientes, y vendedores. | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-044 | Generar análisis comparativo de productos pedidos versus despachados entre fechas escogidas | 1 | 4 | 1 | 1 | 1 | 1 |
| RF-045 | Generar informe de productos despachados | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-046 | Buscar y agrupar informes de productos despachados según fecha, producto, cliente, y factura | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-047 | Análisis de ventas y descuentos | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-048 | Análisis de despachos según factura y cliente | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-049 | Análisis de despachos a cliente por producto | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-050 | Análisis de despachos por vendedor y producto | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-051 | Análisis de pedidos y despachos mensuales | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-052 | Inventario de productos terminados entre fechas | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-053 | Análisis de inventario | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-054 | Informe de productos en proceso | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-055 | Resúmen de producción | 1 | 3 | 1 | 1 | 1 | 1 |
| RF-056 | Permitir configuración de parámetros del sistema (empresa, moneda, impuestos, logotipo) | 2 | 2 | 1 | 1 | 1 | 2 |
| RF-057 | Soportar múltiples usuarios con distintos niveles de acceso y control | 1 | 4 | 1 | 1 | 1 | 2 |
| RF-058 | Permitir la limitación y autorización del resto de usuarios por parte del administrador | 1 | 4 | 1 | 1 | 1 | 2 |
| RF-059 | Exportar documentos y listas en formatos Excel y PDF | 1 | 4 | 1 | 1 | 1 | 1 |
| RF-060 | Permitir traspaso de información desde el sistema original al nuevo sistema | 1 | 4 | 2 | 2 | 1 | 2 |
| RF-061 | Cambiar la interfaz mejorada en pos de la eficiencia del programa y tiempo del usuario (reducir clics, incluir atajos) | 2 | 2 | 1 | 2 | 1 | 1 |

Las prioridades de RF-027, RF-040, RF-041 y RF-056 se actualizaron al Incremento 2, y RF-061 se incorporó en ese incremento.
