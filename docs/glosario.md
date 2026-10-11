# Glosario y formatos de datos

Fuente: **Documento 0**, sección 6.2 (Terminología / glosario).

## Registros maestros

- **Cliente:** persona o entidad que compra artículos a Comercial D Nix.
- **Registro de cliente:** conjunto de datos asociados a un cliente dentro del sistema. Incluye información de identificación, contacto, ubicación, condiciones comerciales, vendedor asociado, descuentos, cobranza y observaciones.
- **Producto:** artículo de ropa manufacturado por la empresa.
- **Bodega:** lugar físico donde los productos son almacenados.
- **Vendedor:** empleado que vende un producto de Comercial D Nix.
- **Zona de venta:** conjunto geográfico de regiones de Chile en donde se vendió el producto o se realizó el pedido.
- **Color:** atributo visual de la materia prima y de los productos que se fabrican a partir de ella.
- **Talla:** tamaño estandarizado de algún producto.
- **Proveedor:** persona o empresa externa que suministra materias primas a Comercial D Nix para la fabricación de sus productos.
- **Código EAN:** formato de código de barras estándar. Se utiliza EAN-13, compuesto por 13 dígitos numéricos.

## Datos de identificación y ubicación

- **Código:** identificador único utilizado por el sistema para reconocer un registro en específico.
- **Código de cliente / producto / bodega / vendedor / zona de venta:** identificador único asociado a esa entidad en el sistema.
- **Nombre de cliente:** nombre completo del cliente registrado en el sistema, con formato apellido/s-nombre/s.
- **Abreviación:** versión resumida de un dato, utilizada para facilitar su visualización.
- **RUT:** Rol Único Tributario utilizado para identificar personas naturales o jurídicas en Chile, compuesto por números y un dígito verificador.
- **Dígito verificador:** carácter asociado al RUT que permite validar su consistencia.
- **Giro:** actividad económica o comercial asociada a un cliente.
- **Dirección:** ubicación física o comercial asociada a un cliente, bodega u otro registro.
- **Comuna:** división territorial asociada a una dirección.
- **Teléfono:** número de contacto asociado a un cliente, vendedor u otra entidad registrada.
- **Fax:** medio de comunicación utilizado para enviar documentos vía línea telefónica.
- **Observaciones:** campo destinado a registrar comentarios adicionales sobre clientes, productos, pedidos, cortes u otros registros.

## Condiciones comerciales y precios

- **Condiciones de venta:** reglas comerciales pactadas con un cliente, tales como la forma de pago, plazo de pago y descuentos aplicables.
- **Lista de precios:** clasificación comercial utilizada para determinar los precios aplicables a un cliente.
- **Descuento:** rebaja porcentual aplicada a un cliente, producto o pedido.
- **Comisión:** porcentaje asociado al vendedor por las ventas realizadas o gestionadas.
- **Cobranza:** proceso mediante el cual se realiza el seguimiento de pagos pendientes, montos recibidos y saldos asociados a clientes o pedidos.
- **Porcentaje de cobranza:** porcentaje asociado a la gestión de cobranza de un cliente o venta, según las reglas comerciales definidas por la empresa.
- **Precio:** valor monetario asociado a un producto, pedido o transacción comercial.
- **Precio costo:** valor asociado al costo de producción o adquisición de un producto.
- **Precio detalle:** valor de venta aplicado a ventas al detalle, si corresponde.
- **Precio mayor:** valor de venta aplicado a ventas al por mayor, si corresponde.
- **Depósito:** monto pagado por un cliente que puede ser utilizado para cubrir total o parcialmente uno o más pedidos.
- **Pago:** monto de dinero recibido por la empresa de parte de un cliente, en concepto de cancelación total o parcial de un pedido o saldo pendiente.
- **Saldo:** diferencia entre el monto total adeudado por un cliente y los pagos o depósitos ya aplicados. Representa el monto pendiente por cobrar en un momento determinado.
- **Factura:** documento tributario que acredita la venta de productos al cliente, indicando detalles de artículos, precios, descuentos y monto total a cancelar.
- **Nota de crédito:** documento contable emitido al cliente cuando se realiza una devolución parcial o total de un pedido anulado, con el fin de rectificar la factura y ajustar su saldo.

## Producción, pedidos y stock

- **Pedido:** solicitud realizada por un cliente, a través de un vendedor, mediante la cual se pide una cierta cantidad de algún producto.
- **Registro de pedido:** conjunto de datos asociados a una solicitud realizada por un cliente dentro del sistema. Incluye el número de pedido, cliente asociado, fecha del pedido, vendedor responsable, fecha de entrega y estado del pedido.
- **Detalle de pedido:** información específica asociada a un pedido, donde se registran los productos solicitados por el cliente, indicando código de producto, color, talla, cantidad por talla, precio unitario y monto correspondiente.
- **Monto total de pedido:** cantidad de dinero total que debe pagar el cliente por haber recibido todos los artículos solicitados.
- **Estado de pedido:** condición actual en la que se encuentra un pedido dentro del sistema. Puede ser: registrado, pendiente, en producción, listo para despacho, despachado, pagado, anulado o finalizado.
- **Anulación de pedido:** proceso mediante el cual un cliente cancela parcial o totalmente un pedido, generando la emisión de una nota de crédito para rectificar la factura correspondiente.
- **Corte:** proceso de fabricación mediante el cual se transforma la materia prima en artículos de ropa.
- **Registro de corte:** conjunto de datos asociados al proceso de corte de materiales para la fabricación de productos. Incluye el código de corte, fecha, responsable del corte, observaciones y el detalle de los productos a fabricar, considerando color, talla, cantidad y materiales utilizados.
- **Guía de cortes:** documento enviado al taller para fabricación de las prendas según las indicaciones de los cortes incluidos en la guía.
- **Guía de despachos:** documento que acompaña la entrega de productos al cliente, indicando artículos, cantidades, tallas y colores despachados en esa operación.
- **Producción:** proceso mediante el cual la materia prima es transformada en productos terminados por el taller, comprendiendo desde la emisión de guías de corte hasta el ingreso de los artículos a bodega.
- **Ingreso de producción a bodega:** una vez los productos se han elaborado, se ingresan a bodega los datos respectivos a su producción, para que conste en el sistema que se han creado.
- **Stock:** cantidad de unidades disponibles de un producto en bodega, clasificadas por talla y color. Se actualiza automáticamente al ingresar producción y al registrar despachos.
- **Despacho:** entrega física de los productos de un pedido al cliente o transportista correspondiente, quedando registrado en el sistema con fechas, productos, tallas, colores y cantidades.
- **Inventario:** conjunto de productos que se encuentran almacenados físicamente en la empresa en un momento determinado.
- **Materia prima:** materiales base (telas, elásticos, etc.) a partir de los cuales se fabrican los productos.

## Usuarios, documentos y sistemas

- **Usuario:** persona que hace uso del sistema y tiene asociada una cuenta de acceso.
- **Cuenta de usuario:** conjunto de credenciales, como nombre de usuario y contraseña, que permiten autenticarse y acceder al sistema.
- **Nivel de acceso:** determinante que indica qué acciones puede realizar un usuario del sistema en base a su autorización.
- **Rol:** nivel de acceso asignado al usuario por el administrador del sistema.
- **Administrador:** usuario principal que tiene control total sobre el software y puede gestionar los accesos del resto de usuarios.
- **Autenticación:** proceso mediante el cual el sistema verifica la identidad de un usuario a través de sus credenciales antes de permitir el ingreso.
- **Control de acceso basado en roles (RBAC):** mecanismo de seguridad que restringe el acceso a módulos y funciones del sistema según el rol asignado al usuario.
- **Exportación:** proceso de crear un documento digital (archivo de texto, PDF o Excel) que contenga cierta información incluida en la base de datos.
- **Resumen de pedido:** informe que muestra de manera simplificada la cantidad de productos incluidos en los pedidos según color, talla y producto.
- **Informe de cobranza:** reporte que detalla el estado de pagos y saldos de uno o más clientes, indicando montos cobrados, depósitos aplicados y saldos pendientes en un periodo determinado.
- **Migración de datos:** proceso de traslado de información desde el sistema anterior al nuevo sistema, preservando la integridad y consistencia de los registros históricos.
- **Sistema legacy:** sistema informático anterior que la empresa utilizaba para gestionar sus operaciones, desde el cual se extraen los datos a migrar.
- **Base de datos:** repositorio digital organizado que permite almacenar, gestionar y recuperar grandes volúmenes de información.
- **Base de datos relacional:** colección de información que organiza datos en relaciones predefinidas.

## Acrónimos

- **BPMN:** Business Process Model and Notation, diagrama que representa los procedimientos internos de una empresa.
- **CRUD:** create, read, update, delete (crear, leer, actualizar, borrar).
- **RF:** requerimiento funcional.
- **RNF:** requerimiento no funcional.
- **UR:** user requirement, requerimiento de usuario.
- **ESA:** formato de especificación de requerimientos utilizado para organizar, clasificar y evaluar los requerimientos de usuario.
- **RBAC:** role-based access control.
- **EAN:** European Article Number. Se utiliza EAN-13 (13 dígitos numéricos).
- **PDF:** Portable Document Format.
- **Excel:** aplicación de Microsoft para trabajar con tablas de datos, con formato propio.

## Formatos y restricciones de datos

| Dato | Formato |
| --- | --- |
| Código de color | 8 caracteres alfanuméricos |
| Código de producto | 16 caracteres alfanuméricos |
| Código de vendedor | 3 caracteres alfanuméricos |
| Código de zona de venta | 3 caracteres alfanuméricos |
| Código EAN | 13 caracteres numéricos |
| Descripción de color | 32 caracteres alfanuméricos |
| Descripción de producto | 64 caracteres alfanuméricos |
| Descripción de zona de venta | 64 caracteres alfanuméricos |
| Descuento | número entre 0 y 100 con dos decimales (X.xx%) |
| Comisión | X.xx% |
| Porcentaje de cobranza | X.xx% |
| Fecha | dd/mm/yyyy |
| Observaciones | 256 caracteres alfanuméricos |
| Precio | $ seguido de hasta 9 caracteres numéricos |
| Talla | 2 caracteres alfanuméricos (XX) |
| Nombre de cliente | apellido/s-nombre/s |
