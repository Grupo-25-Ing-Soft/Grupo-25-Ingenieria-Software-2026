# Casos de uso del Incremento 2

Fuente: **documento del Incremento 2**, capítulo 4 (Tabla 4.1).

Este archivo complementa [casos-de-uso.md](casos-de-uso.md) (Documento 0) y sirve para dos cosas:

1. **CU que el Documento 0 no detalla.** La Tabla 8.2 del Documento 0 remite al Incremento 2
   para CU-28, CU-29.1 a CU-29.4, CU-30, CU-33, CU-35.1 a CU-35.4, CU-36, CU-56 y CU-61. Aquí
   también están CU-24.2 a CU-24.4, CU-26, CU-32.2 a CU-32.4, CU-37.1 a CU-37.4 y CU-41.
2. **Versiones más detalladas** de CU que también aparecen en el Documento 0 (CU-17, CU-20,
   CU-21, CU-24.1, CU-25, CU-27, CU-31, CU-32.1, CU-34, CU-38, CU-39, CU-40). Están marcadas
   con *(también en Documento 0)*. Las dos versiones no siempre coinciden (por ejemplo, el
   menú de navegación o si la anulación genera nota de crédito). Si la diferencia importa
   para lo que se está implementando, hay que señalarla en vez de elegir una en silencio.

## Producción

### CU-17: Enviando solicitud de impresión de etiquetas EAN *(también en Documento 0)*
- **Actores:** Administrador, jefa de taller.
- **Resumen:** Permite enviar a la impresora conectada la solicitud de impresión de las etiquetas con los códigos EAN generados para un producto.
- **Frecuencia:** Cada vez que se requiere imprimir las etiquetas de un producto.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir el código EAN generado para el producto. 4. Debe haber una impresora configurada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Archivos Maestros > Códigos EAN. 2. El sistema muestra la lista completa de códigos con barra de scroll y barra de búsqueda. 3. El usuario localiza el producto e indica la cantidad de etiquetas a imprimir [Excepción 1]. 4. Selecciona la impresora y confirma. El sistema genera el archivo de etiquetas y envía la solicitud a la impresora conectada [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados o el producto no tiene código EAN generado, el sistema informa la situación e impide continuar. Excepción 2: Si la impresora no responde o no se encuentra configurada, el sistema informa el error y conserva la solicitud en cola.
- **Postcondición:** La solicitud de impresión queda enviada a la impresora y registrada con su fecha, cantidad y usuario responsable.
- **Dependencias:** CU-13.1: Registrando producto. CU-15.1: Registrando código EAN. CU-16: Buscando y visualizando lista de códigos EAN.

### CU-20: Generando guía de cortes *(también en Documento 0)*
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite generar automáticamente el documento de guía de cortes a partir de un corte registrado, con el detalle de productos, colores, tallas y cantidades a confeccionar, quedando disponible para su impresión y entrega al taller.
- **Frecuencia:** Cada vez que se está requiriendo enviar un corte a producción.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir un corte registrado con su detalle. 3. Los productos, colores y tallas del corte deben estar registrados.
- **Descripción:** 1. El usuario accede al módulo Producción > Cortes. 2. Selecciona el corte al que corresponde la guía [Excepción 1]. 3. Solicita la opción Generar guía de cortes. 4. El sistema recupera el detalle del corte: productos, colores, tallas y cantidades [Excepción 2]. 5. El sistema asigna un código correlativo único a la guía. 6. El sistema arma el documento con su encabezado (código de guía, fecha, corte asociado y responsable) y el detalle por línea. 7. El sistema muestra la guía en pantalla y habilita su impresión o exportación a PDF [Excepción 3]. 8. El usuario confirma y la guía queda registrada.
- **Excepciones:** Excepción 1: Si el corte ya tiene una guía generada, el sistema informa la situación y ofrece consultar la existente en lugar de duplicarla. Excepción 2: Si el corte no tiene líneas de detalle, el sistema informa que no es posible generar la guía. Excepción 3: Si falla la generación del documento, el sistema informa el error y conserva el corte sin guía asociada.
- **Postcondición:** La guía de cortes queda registrada con su código único y disponible para impresión y para el ingreso posterior de producción a bodega.
- **Dependencias:** CU-13.1: Registrando producto. CU-18.1: Registrando corte. CU-19: Buscando y visualizando lista de cortes.

### CU-21: Ingresando productos a bodega desde guía de cortes *(también en Documento 0)*
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite registrar los productos fabricados a partir de un corte e ingresarlos al stock de una bodega, identificando la producción mediante el código de la guía de cortes correspondiente.
- **Frecuencia:** Cada vez que se está requiriendo ingresar producción terminada a la bodega.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir una guía de cortes generada. 3. Deben existir bodegas registradas.
- **Descripción:** 1. El usuario accede al módulo Producción > Ingreso de producción. 2. Ingresa el código de la guía de cortes correspondiente [Excepción 1]. 3. El sistema recupera el detalle de la guía y precarga los productos, colores, tallas y cantidades esperadas. 4. El usuario ajusta las cantidades efectivamente producidas [Excepción 2]. 5. Selecciona la bodega de destino. 6. Confirma el ingreso. 7. El sistema actualiza el stock de la bodega seleccionada y marca la guía como ingresada [Excepción 3].
- **Excepciones:** Excepción 1: Si la guía de cortes no existe o ya fue ingresada, el sistema informa la situación y solicita corrección. Excepción 2: Si la cantidad ingresada es menor o igual a cero, el sistema no permite continuar y solicita corrección. Excepción 3: Si la cantidad producida difiere de la esperada según la guía, el sistema registra la diferencia como merma y solicita confirmación del usuario.
- **Postcondición:** El stock de la bodega queda incrementado con las unidades producidas y la guía de cortes queda marcada como ingresada.
- **Dependencias:** CU-05.1: Registrando bodega. CU-13.1: Registrando producto. CU-18.1: Registrando corte. CU-20: Generando guía de cortes. CU-39: Actualizando stock automáticamente.

## Detalle y gestión de pedidos

### CU-24.1: Registrando detalle de pedido *(también en Documento 0)*
- **Actores:** Administrador, vendedor.
- **Resumen:** Permite agregar una línea de detalle a un pedido, indicando producto, color, talla, cantidad y precio unitario.
- **Frecuencia:** Cada vez que se requiere incorporar productos a un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir el pedido en estado editable. 4. Deben existir productos, colores y tallas registrados en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Pedidos y selecciona el pedido. 2. El sistema muestra la pestaña Detalle con las líneas ya registradas. 3. El usuario selecciona producto, color y talla, e ingresa cantidad y precio unitario [Excepción 1]. 4. Confirma el registro. El sistema valida los datos, agrega la línea y recalcula el monto total del pedido [Excepción 2].
- **Excepciones:** Excepción 1: Si la combinación de producto, color y talla ya existe en el detalle, el sistema informa duplicidad y ofrece sumar la cantidad a la línea existente. Excepción 2: Si la cantidad es cero o negativa, o faltan campos obligatorios, el sistema no permite continuar y solicita corrección.
- **Postcondición:** La línea de detalle queda registrada en la base de datos y el monto total del pedido actualizado.
- **Dependencias:** CU-13.1: Registrando producto. CU-22.1: Registrando pedido. CU-26: Calculando monto total del pedido.

### CU-24.2: Consultando detalle de pedido
- **Actores:** Administrador, vendedor.
- **Resumen:** Permite extraer de la base de datos las líneas de detalle asociadas a un pedido.
- **Frecuencia:** Cada vez que se requiere revisar el contenido de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una línea de detalle registrada para el pedido.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Pedidos. 2. El sistema muestra la lista completa de pedidos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pedido por número o cliente [Excepción 1]. 4. Selecciona el pedido e ingresa a la pestaña Detalle. El sistema muestra las líneas con producto, color, talla, cantidad, precio unitario y subtotal en modo lectura.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pedido con ese criterio.
- **Postcondición:** El detalle del pedido se muestra al usuario incluyendo todas sus líneas y subtotales.
- **Dependencias:** CU-22.1: Registrando pedido. CU-23: Buscando y visualizando lista de pedidos. CU-24.1: Registrando detalle de pedido.

### CU-24.3: Modificando detalle de pedido
- **Actores:** Administrador, vendedor.
- **Resumen:** Permite modificar la cantidad o el precio unitario de una línea de detalle existente.
- **Frecuencia:** Cada vez que se requiere ajustar el contenido de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una línea de detalle registrada para el pedido.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Pedidos. 2. El sistema muestra la lista completa de pedidos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pedido por número o cliente [Excepción 1]. 4. Selecciona la línea del detalle, edita la cantidad o el precio unitario y confirma. El sistema valida, guarda los cambios y recalcula el monto total del pedido [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pedido con ese criterio. Excepción 2: Si el pedido ya fue facturado o anulado, el sistema impide la modificación e informa al usuario.
- **Postcondición:** La línea de detalle queda modificada en la base de datos y el monto total del pedido recalculado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-23: Buscando y visualizando lista de pedidos. CU-24.1: Registrando detalle de pedido. CU-26: Calculando monto total del pedido.

### CU-24.4: Eliminando detalle de pedido
- **Actores:** Administrador, vendedor.
- **Resumen:** Permite eliminar una línea de detalle de un pedido.
- **Frecuencia:** Cada vez que se requiere retirar un producto de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una línea de detalle registrada para el pedido.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Pedidos. 2. El sistema muestra la lista completa de pedidos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pedido por número o cliente [Excepción 1]. 4. Selecciona la línea y elige Eliminar. El sistema solicita confirmación explícita antes de proceder [Excepción 2]. Al confirmar, elimina la línea y recalcula el monto total del pedido.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pedido con ese criterio. Excepción 2: Si el pedido ya fue facturado o tiene despachos asociados, el sistema impide la eliminación e informa al usuario.
- **Postcondición:** La línea de detalle queda eliminada de la base de datos y el monto total del pedido recalculado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-23: Buscando y visualizando lista de pedidos. CU-24.1: Registrando detalle de pedido. CU-26: Calculando monto total del pedido.

### CU-25: Anulando pedido existente *(también en Documento 0)*
- **Actores:** Administrador.
- **Resumen:** Permite anular total o parcialmente un pedido existente, generando la nota de crédito correspondiente cuando el pedido ya fue facturado y liberando las unidades comprometidas en el inventario.
- **Frecuencia:** Cada vez que un cliente desiste de un pedido o se requiere revertir una venta ya registrada.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir el pedido en el sistema. 3. El pedido no debe encontrarse previamente anulado en su totalidad.
- **Descripción:** 1. El usuario accede al módulo Ventas > Pedidos y selecciona el pedido. 2. Elige la opción Anular e indica si la anulación es total o parcial [Excepción 1]. 3. Si es parcial, selecciona las líneas y las cantidades a anular [Excepción 2]. 4. Ingresa el motivo de la anulación [Excepción 3]. 5. El sistema verifica si el pedido tiene factura asociada. 6. Si la tiene, genera la nota de crédito por el monto anulado. 7. El sistema libera las unidades comprometidas y actualiza el inventario. 8. El sistema marca el pedido como anulado o parcialmente anulado y registra fecha, hora y usuario responsable.
- **Excepciones:** Excepción 1: Si el pedido ya fue despachado en su totalidad, el sistema advierte la situación y exige confirmación explícita del administrador. Excepción 2: Si la cantidad a anular supera la cantidad pedida en la línea, el sistema no permite continuar. Excepción 3: Si no se ingresa el motivo de la anulación, el sistema solicita completarlo.
- **Postcondición:** El pedido queda anulado total o parcialmente, con su nota de crédito asociada cuando corresponde, y el inventario queda actualizado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-24: Gestionando detalle de pedido. CU-29: Gestionando facturas. CU-35: Gestionando notas de crédito. CU-39: Actualizando stock automáticamente.

### CU-26: Calculando monto total del pedido
- **Actores:** Sistema.
- **Resumen:** Subproceso que calcula automáticamente el monto total de un pedido a partir de sus líneas de detalle, aplicando los descuentos e impuestos vigentes en los parámetros del sistema.
- **Frecuencia:** Cada vez que se está agregando, modificando o eliminando una línea del detalle del pedido.
- **Precondiciones:** 1. Debe existir el pedido con al menos una línea de detalle. 2. Los parámetros de impuesto deben estar configurados en el sistema.
- **Descripción:** 1. El sistema recibe las líneas del detalle con su cantidad y precio unitario. 2. Calcula el subtotal de cada línea multiplicando cantidad por precio unitario. 3. Suma los subtotales para obtener el monto neto del pedido. 4. Aplica el descuento del cliente o del pedido cuando corresponde [Excepción 1]. 5. Aplica el porcentaje de impuesto definido en los parámetros del sistema [Excepción 2]. 6. Obtiene el monto total. 7. Actualiza el encabezado del pedido con el neto, el descuento, el impuesto y el total resultantes.
- **Excepciones:** Excepción 1: Si el descuento supera el cien por ciento del monto neto, el sistema lo rechaza y mantiene el valor anterior. Excepción 2: Si no existe un porcentaje de impuesto configurado, el sistema aplica el valor por defecto y advierte al usuario.
- **Postcondición:** El pedido queda con su monto neto, descuento, impuesto y total actualizados.
- **Dependencias:** CU-22.1: Registrando pedido. CU-24: Gestionando detalle de pedido. CU-56: Configurando parámetros del sistema.

### CU-27: Calculando porcentaje de cumplimiento del pedido *(también en Documento 0)*
- **Actores:** Administrador / Vendedor / Sistema.
- **Resumen:** Permite conocer qué proporción de un pedido puede cubrirse con el stock disponible, comparando línea a línea las unidades solicitadas con las existencias actuales en bodega.
- **Frecuencia:** Cada vez que se está requiriendo evaluar la factibilidad de despacho de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir el pedido con su detalle. 3. Deben existir registros de inventario.
- **Descripción:** 1. El usuario accede al módulo Ventas > Pedidos, selecciona el pedido y solicita el porcentaje de cumplimiento. 2. El sistema recorre cada línea del detalle del pedido. 3. Para cada combinación de producto, color y talla consulta el stock disponible en las bodegas [Excepción 1]. 4. Determina las unidades cubiertas como el mínimo entre lo solicitado y lo disponible. 5. Suma las unidades cubiertas y las divide por el total de unidades solicitadas. 6. Expresa el resultado como porcentaje y lo muestra junto al detalle línea a línea, destacando las que no tienen cobertura [Excepción 2]. 7. El usuario puede exportar el resultado.
- **Excepciones:** Excepción 1: Si una combinación de producto, color y talla no tiene registro de inventario, el sistema la considera con stock cero e informa la situación. Excepción 2: Si el pedido no tiene líneas de detalle, el sistema informa que no es posible efectuar el cálculo.
- **Postcondición:** El porcentaje de cumplimiento queda calculado y visible para el usuario, sin alterar el stock ni el estado del pedido.
- **Dependencias:** CU-22.1: Registrando pedido. CU-24: Gestionando detalle de pedido. CU-37: Gestionando inventario por producto, talla y color. CU-38: Visualizando stock actual con filtros de búsqueda.

### CU-28: Calculando costos según compras, producción y ventas
- **Actores:** Administrador / Sistema.
- **Resumen:** Calcula automáticamente el costo asociado a cada producto, consolidando el costo de las materias primas compradas, el costo de producción del corte y el costo imputado a las unidades vendidas.
- **Frecuencia:** Cada vez que se registra una compra, un ingreso de producción o una venta, y cada vez que se consulta el informe de costos.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de compras, cortes con producción ingresada y pedidos.
- **Descripción:** 1. El sistema recopila el costo de las materias primas asociadas al corte. 2. Agrega los costos de producción registrados para ese corte. 3. Divide el costo total del corte entre las unidades efectivamente ingresadas a bodega para obtener el costo unitario [Excepción 1]. 4. Al registrarse una venta, imputa el costo unitario vigente a las unidades vendidas. 5. Calcula el margen como la diferencia entre el precio de venta y el costo unitario. 6. Consolida los resultados por producto, por corte y por período [Excepción 2]. 7. El usuario accede a Informes > Costos y visualiza el resultado, pudiendo exportarlo.
- **Excepciones:** Excepción 1: Si el corte no tiene unidades ingresadas a bodega, el sistema no calcula el costo unitario e informa la situación. Excepción 2: Si faltan costos de materia prima para alguna línea, el sistema calcula con la información disponible y marca el resultado como parcial.
- **Postcondición:** Los costos unitarios y los márgenes quedan calculados y disponibles para consulta y exportación.
- **Dependencias:** CU-13.1: Registrando producto. CU-18.1: Registrando corte. CU-21: Ingresando productos a bodega desde guía de cortes. CU-22.1: Registrando pedido. CU-26: Calculando monto total del pedido.

## Facturas (RF-029, RF-030)

### CU-29.1: Registrando factura
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite emitir una factura asociada a un pedido, con su folio, fecha, cliente, detalle y montos.
- **Frecuencia:** Cada vez que se requiere facturar un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir el pedido a facturar. 4. El cliente del pedido debe estar registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Facturación. 2. El sistema muestra el registro de facturas con barra de scroll. 3. El usuario selecciona el pedido a facturar; el sistema hereda cliente, detalle y montos, y asigna el folio correlativo [Excepción 1]. 4. El usuario ajusta la fecha de emisión y confirma. El sistema valida y guarda la factura [Excepción 2].
- **Excepciones:** Excepción 1: Si el pedido ya fue facturado, el sistema informa la situación y ofrece consultar la factura existente. Excepción 2: Si faltan campos obligatorios o el folio correlativo ya existe, el sistema informa y asigna el siguiente folio disponible.
- **Postcondición:** La factura queda registrada en la base de datos y el pedido actualiza su estado de facturación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-26: Calculando monto total del pedido.

### CU-29.2: Consultando factura
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite extraer de la base de datos la información de una factura emitida.
- **Frecuencia:** Cada vez que se requiere revisar información de facturas.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una factura registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Facturación. 2. El sistema muestra el registro completo de facturas con barra de scroll y barra de búsqueda. 3. El usuario localiza la factura por folio, cliente o fecha [Excepción 1]. 4. Selecciona la factura y el sistema muestra todos sus datos en modo lectura, incluyendo detalle, montos, pagos aplicados y saldo pendiente.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna factura con ese criterio.
- **Postcondición:** El registro de la factura se muestra al usuario incluyendo todos sus datos.
- **Dependencias:** CU-29.1: Registrando factura. CU-30: Buscando y visualizando lista de facturas.

### CU-29.3: Modificando factura
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite modificar los datos editables de una factura ya emitida.
- **Frecuencia:** Cada vez que se requiere corregir información de una factura.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una factura registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Facturación. 2. El sistema muestra el registro completo de facturas con barra de scroll y barra de búsqueda. 3. El usuario localiza la factura por folio, cliente o fecha [Excepción 1]. 4. Selecciona la factura, edita los campos habilitados y confirma. El sistema valida y guarda los cambios [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna factura con ese criterio. Excepción 2: Si la factura tiene pagos o notas de crédito asociadas, el sistema impide la modificación e informa al usuario.
- **Postcondición:** El registro de la factura queda modificado en la base de datos según la operación ejecutada.
- **Dependencias:** CU-29.1: Registrando factura. CU-30: Buscando y visualizando lista de facturas.

### CU-29.4: Eliminando factura
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite eliminar del sistema el registro de una factura emitida.
- **Frecuencia:** Cada vez que se requiere eliminar una factura emitida por error.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una factura registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Facturación. 2. El sistema muestra el registro completo de facturas con barra de scroll y barra de búsqueda. 3. El usuario localiza la factura por folio, cliente o fecha [Excepción 1]. 4. Selecciona la factura y elige Eliminar. El sistema solicita confirmación explícita antes de proceder [Excepción 2]. Al confirmar, elimina el registro y revierte el estado de facturación del pedido.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna factura con ese criterio. Excepción 2: Si la factura tiene pagos o notas de crédito asociadas, el sistema impide la eliminación e informa al usuario.
- **Postcondición:** El registro de la factura queda eliminado de la base de datos y el pedido vuelve a su estado no facturado.
- **Dependencias:** CU-29.1: Registrando factura. CU-30: Buscando y visualizando lista de facturas.

### CU-30: Buscando y visualizando lista de facturas
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite recorrer el registro completo de facturas mediante una tabla con barra de scroll vertical y filtros de búsqueda.
- **Frecuencia:** Cada vez que se está requiriendo revisar o localizar una factura.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir facturas registradas en el sistema.
- **Descripción:** 1. El usuario accede al módulo Ventas > Facturación. 2. El sistema carga la lista de facturas en una tabla con barra de scroll vertical [Excepción 1]. 3. La tabla muestra folio, fecha, cliente, pedido asociado, monto total y estado. 4. El usuario puede filtrar por folio, cliente, rango de fechas o estado [Excepción 2]. 5. Puede ordenar el resultado por cualquier columna. 6. Al seleccionar una fila, el sistema despliega el detalle de la factura.
- **Excepciones:** Excepción 1: Si no existen facturas registradas, el sistema muestra la tabla vacía con el mensaje correspondiente. Excepción 2: Si ningún registro coincide con el filtro aplicado, el sistema informa que no hay resultados para ese criterio.
- **Postcondición:** El usuario visualiza el registro de facturas según los filtros aplicados, sin modificar los datos.
- **Dependencias:** CU-29: Gestionando facturas.

## Cobranza y pagos (RF-031 a RF-034)

### CU-31: Generando informe de cobranza *(también en Documento 0)*
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite generar un informe que muestra las facturas pendientes de pago agrupadas por cliente, con sus montos, saldos y días de morosidad.
- **Frecuencia:** Cada vez que se requiere revisar el estado de cobranza de los clientes.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una factura emitida con saldo pendiente.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza > Informe de cobranza. 2. El sistema recopila las facturas con saldo pendiente y las agrupa por cliente [Excepción 1]. 3. El usuario puede filtrar por cliente, rango de fechas o días de morosidad. 4. El sistema muestra el informe con folio, fecha de emisión, monto, pagos aplicados, saldo y días transcurridos, y habilita su exportación a PDF o Excel [Excepción 2].
- **Excepciones:** Excepción 1: Si no existen facturas con saldo pendiente, el sistema informa que no hay cobranza pendiente para el criterio seleccionado. Excepción 2: Si falla la generación del documento, el sistema informa el error sin alterar los registros.
- **Postcondición:** El informe de cobranza queda generado y disponible para consulta y exportación, sin modificar los registros.
- **Dependencias:** CU-01.1: Registrando cliente. CU-29.1: Registrando factura. CU-32.1: Registrando pago o depósito de cliente.

### CU-32.1: Registrando pago o depósito de cliente *(también en Documento 0)*
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite registrar un pago o depósito recibido de un cliente y aplicarlo a una o varias facturas pendientes.
- **Frecuencia:** Cada vez que se recibe un pago o depósito de un cliente.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir el cliente registrado en el sistema. 4. Deben existir facturas emitidas con saldo pendiente.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza > Pagos. 2. El sistema muestra el registro de pagos con barra de scroll. 3. El usuario selecciona el cliente e ingresa monto, fecha, medio de pago y referencia [Excepción 1]. 4. Asigna el pago a una o varias facturas o solicita la asignación automática, y confirma. El sistema valida, guarda el registro y actualiza el saldo de las facturas afectadas [Excepción 2].
- **Excepciones:** Excepción 1: Si el monto es cero o negativo, o faltan campos obligatorios, el sistema no permite continuar y solicita corrección. Excepción 2: Si el monto asignado supera el saldo de las facturas seleccionadas, el sistema informa la situación y deja la diferencia como saldo a favor del cliente.
- **Postcondición:** El pago queda registrado en la base de datos y los saldos de las facturas afectadas actualizados.
- **Dependencias:** CU-01.1: Registrando cliente. CU-29.1: Registrando factura. CU-34: Automatizando la asignación de pagos a pedidos pendientes.

### CU-32.2: Consultando pago
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite extraer de la base de datos la información de un pago recibido y las facturas a las que fue aplicado.
- **Frecuencia:** Cada vez que se requiere revisar información de pagos.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un pago registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza > Pagos. 2. El sistema muestra el registro completo de pagos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pago por cliente, fecha o referencia [Excepción 1]. 4. Selecciona el pago y el sistema muestra todos sus datos en modo lectura, incluyendo monto, medio de pago y las facturas a las que fue aplicado.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pago con ese criterio.
- **Postcondición:** El registro del pago se muestra al usuario incluyendo todos sus datos y su aplicación a facturas.
- **Dependencias:** CU-32.1: Registrando pago o depósito de cliente. CU-33: Buscando y visualizando lista de pagos.

### CU-32.3: Modificando pago
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite modificar los datos de un pago o su asignación a las facturas del cliente.
- **Frecuencia:** Cada vez que se requiere corregir un pago o reasignarlo a otra factura.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un pago registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza > Pagos. 2. El sistema muestra el registro completo de pagos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pago por cliente, fecha o referencia [Excepción 1]. 4. Selecciona el pago, edita el monto, la referencia o la asignación a facturas y confirma. El sistema valida, guarda los cambios y actualiza los saldos de las facturas afectadas [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pago con ese criterio. Excepción 2: Si el pago ya fue conciliado o el monto asignado supera el saldo de la factura, el sistema impide la modificación e informa al usuario.
- **Postcondición:** El registro del pago queda modificado en la base de datos y los saldos de las facturas afectadas actualizados.
- **Dependencias:** CU-29.1: Registrando factura. CU-32.1: Registrando pago o depósito de cliente. CU-33: Buscando y visualizando lista de pagos.

### CU-32.4: Anulando pago
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite anular un pago registrado, revirtiendo su aplicación a las facturas correspondientes.
- **Frecuencia:** Cada vez que se requiere revertir un pago registrado por error o rechazado por el banco.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un pago registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza > Pagos. 2. El sistema muestra el registro completo de pagos con barra de scroll y barra de búsqueda. 3. El usuario localiza el pago por cliente, fecha o referencia [Excepción 1]. 4. Selecciona el pago, elige Anular e ingresa el motivo. El sistema solicita confirmación explícita, revierte los saldos de las facturas afectadas y marca el pago como anulado [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún pago con ese criterio. Excepción 2: Si no se ingresa el motivo de la anulación, el sistema no permite continuar y solicita completarlo.
- **Postcondición:** El pago queda marcado como anulado y los saldos de las facturas afectadas quedan revertidos.
- **Dependencias:** CU-29.1: Registrando factura. CU-32.1: Registrando pago o depósito de cliente. CU-33: Buscando y visualizando lista de pagos.

### CU-33: Buscando y visualizando lista de pagos
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite recorrer el registro completo de pagos recibidos mediante una tabla con barra de scroll vertical y filtros de búsqueda.
- **Frecuencia:** Cada vez que se está requiriendo revisar o localizar un pago.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir pagos registrados en el sistema.
- **Descripción:** 1. El usuario accede al módulo Ventas > Cobranza > Pagos. 2. El sistema carga la lista de pagos en una tabla con barra de scroll vertical [Excepción 1]. 3. La tabla muestra fecha, cliente, monto, medio de pago, referencia, facturas aplicadas y estado. 4. El usuario puede filtrar por cliente, rango de fechas, medio de pago o estado [Excepción 2]. 5. Puede ordenar el resultado por cualquier columna. 6. Al seleccionar una fila, el sistema despliega el detalle del pago y su aplicación a facturas.
- **Excepciones:** Excepción 1: Si no existen pagos registrados, el sistema muestra la tabla vacía con el mensaje correspondiente. Excepción 2: Si ningún registro coincide con el filtro aplicado, el sistema informa que no hay resultados para ese criterio.
- **Postcondición:** El usuario visualiza el registro de pagos según los filtros aplicados, sin modificar los datos.
- **Dependencias:** CU-32: Gestionando pagos asociados a facturas.

### CU-34: Automatizando la asignación de pagos a pedidos pendientes *(también en Documento 0)*
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite determinar automáticamente qué pedidos pendientes pueden cubrirse con el monto pagado por un cliente, según los montos adeudados.
- **Frecuencia:** Cada vez que se registra un pago o depósito de un cliente.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir el cliente con pedidos pendientes de pago.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza y selecciona el pago registrado. 2. El sistema recupera los pedidos pendientes del cliente ordenados por antigüedad [Excepción 1]. 3. El sistema compara el monto disponible con el monto adeudado de cada pedido y determina cuáles quedan cubiertos por completo y cuál queda parcialmente cubierto. 4. Muestra la propuesta de asignación y el usuario la confirma o la ajusta manualmente [Excepción 2].
- **Excepciones:** Excepción 1: Si el cliente no tiene pedidos pendientes, el sistema informa que no hay deuda que asignar. Excepción 2: Si el monto del pago es inferior al del pedido más antiguo, el sistema lo registra como abono parcial e informa al usuario.
- **Postcondición:** Los pedidos cubiertos quedan marcados como pagados y el saldo remanente queda disponible para futuras asignaciones.
- **Dependencias:** CU-22.1: Registrando pedido. CU-26: Calculando monto total del pedido. CU-32.1: Registrando pago o depósito de cliente.

## Notas de crédito (RF-035, RF-036)

### CU-35.1: Registrando nota de crédito
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite emitir una nota de crédito que rebaja total o parcialmente el monto de una factura emitida.
- **Frecuencia:** Cada vez que se requiere corregir, descontar o anular el monto de una factura.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir la factura de referencia registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Notas de crédito. 2. El sistema muestra el registro de notas con barra de scroll. 3. El usuario selecciona la factura de referencia, indica si la nota es total o parcial y, si es parcial, las líneas y montos a rebajar [Excepción 1]. 4. Ingresa el motivo y confirma. El sistema asigna el folio correlativo, calcula neto, impuesto y total, y rebaja el saldo de la factura [Excepción 2].
- **Excepciones:** Excepción 1: Si el monto de la nota supera el saldo de la factura, el sistema no permite continuar y solicita corrección. Excepción 2: Si la factura ya está completamente cubierta por notas de crédito, el sistema impide la emisión e informa al usuario.
- **Postcondición:** La nota de crédito queda registrada en la base de datos y el saldo de la factura de referencia rebajado.
- **Dependencias:** CU-25: Anulando pedido existente. CU-29.1: Registrando factura.

### CU-35.2: Consultando nota de crédito
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite extraer de la base de datos la información de una nota de crédito emitida.
- **Frecuencia:** Cada vez que se requiere revisar información de notas de crédito.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una nota de crédito registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Notas de crédito. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza la nota por folio, cliente o factura de referencia [Excepción 1]. 4. Selecciona la nota y el sistema muestra todos sus datos en modo lectura, incluyendo la factura asociada, el motivo y los montos.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna nota de crédito con ese criterio.
- **Postcondición:** El registro de la nota de crédito se muestra al usuario incluyendo todos sus datos.
- **Dependencias:** CU-35.1: Registrando nota de crédito. CU-36: Buscando y visualizando lista de notas de crédito.

### CU-35.3: Modificando nota de crédito
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite modificar los datos editables de una nota de crédito emitida.
- **Frecuencia:** Cada vez que se requiere corregir información de una nota de crédito.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una nota de crédito registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Notas de crédito. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza la nota por folio, cliente o factura de referencia [Excepción 1]. 4. Selecciona la nota, edita el motivo o los montos y confirma. El sistema valida, guarda los cambios y recalcula el saldo de la factura de referencia [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna nota de crédito con ese criterio. Excepción 2: Si existen pagos registrados con posterioridad a la nota, el sistema impide la modificación e informa al usuario.
- **Postcondición:** El registro de la nota de crédito queda modificado en la base de datos y el saldo de la factura recalculado.
- **Dependencias:** CU-29.1: Registrando factura. CU-35.1: Registrando nota de crédito. CU-36: Buscando y visualizando lista de notas de crédito.

### CU-35.4: Eliminando nota de crédito
- **Actores:** Administrador, asistente de finanzas.
- **Resumen:** Permite eliminar del sistema el registro de una nota de crédito emitida.
- **Frecuencia:** Cada vez que se requiere eliminar una nota de crédito emitida por error.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos una nota de crédito registrada en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Notas de crédito. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza la nota por folio, cliente o factura de referencia [Excepción 1]. 4. Selecciona la nota y elige Eliminar. El sistema solicita confirmación explícita antes de proceder [Excepción 2]. Al confirmar, elimina el registro y restituye el saldo de la factura de referencia.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ninguna nota de crédito con ese criterio. Excepción 2: Si existen pagos registrados con posterioridad a la nota, el sistema impide la eliminación e informa al usuario.
- **Postcondición:** El registro de la nota de crédito queda eliminado de la base de datos y el saldo de la factura restituido.
- **Dependencias:** CU-29.1: Registrando factura. CU-35.1: Registrando nota de crédito. CU-36: Buscando y visualizando lista de notas de crédito.

### CU-36: Buscando y visualizando lista de notas de crédito
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite recorrer el registro completo de notas de crédito mediante una tabla con barra de scroll vertical y filtros de búsqueda.
- **Frecuencia:** Cada vez que se está requiriendo revisar o localizar una nota de crédito.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir notas de crédito registradas en el sistema.
- **Descripción:** 1. El usuario accede al módulo Ventas > Notas de crédito. 2. El sistema carga la lista en una tabla con barra de scroll vertical [Excepción 1]. 3. La tabla muestra folio, fecha, cliente, factura de referencia, monto, motivo y estado. 4. El usuario puede filtrar por folio, cliente, factura de referencia o rango de fechas [Excepción 2]. 5. Puede ordenar el resultado por cualquier columna. 6. Al seleccionar una fila, el sistema despliega el detalle de la nota de crédito.
- **Excepciones:** Excepción 1: Si no existen notas de crédito registradas, el sistema muestra la tabla vacía con el mensaje correspondiente. Excepción 2: Si ningún registro coincide con el filtro aplicado, el sistema informa que no hay resultados para ese criterio.
- **Postcondición:** El usuario visualiza el registro de notas de crédito según los filtros aplicados, sin modificar los datos.
- **Dependencias:** CU-35: Gestionando notas de crédito.

## Inventario (RF-037 a RF-039)

### CU-37.1: Registrando inventario
- **Actores:** Administrador, jefa de taller.
- **Resumen:** Permite dar de alta un registro de inventario que asocia una combinación de producto, color y talla a una cantidad de existencias en una bodega.
- **Frecuencia:** Cada vez que se requiere incorporar una nueva combinación de existencias a una bodega.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Deben existir productos, colores, tallas y bodegas registrados en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Inventario > Existencias. 2. El sistema muestra el registro de existencias con barra de scroll. 3. El usuario selecciona bodega, producto, color y talla, e ingresa la cantidad inicial [Excepción 1]. 4. Confirma el registro. El sistema valida que la combinación no exista ya en esa bodega, guarda el registro y deja trazado el movimiento con fecha, hora y usuario [Excepción 2].
- **Excepciones:** Excepción 1: Si la combinación de producto, color y talla ya existe en esa bodega, el sistema informa duplicidad y ofrece ajustar el registro existente. Excepción 2: Si la cantidad ingresada es negativa o faltan campos obligatorios, el sistema no permite continuar y solicita corrección.
- **Postcondición:** El registro de inventario queda creado en la base de datos con su movimiento trazado.
- **Dependencias:** CU-03.1: Registrando color. CU-05.1: Registrando bodega. CU-11.1: Registrando talla. CU-13.1: Registrando producto.

### CU-37.2: Consultando inventario
- **Actores:** Administrador, jefa de taller.
- **Resumen:** Permite extraer de la base de datos la información de un registro de inventario y su historial de movimientos.
- **Frecuencia:** Cada vez que se requiere revisar información de existencias.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un registro de inventario en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Inventario > Existencias. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza el registro por bodega, producto, color o talla [Excepción 1]. 4. Selecciona el registro y el sistema muestra su cantidad actual, fecha de última actualización, usuario responsable y el historial de movimientos en modo lectura.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún registro de inventario con ese criterio.
- **Postcondición:** El registro de inventario se muestra al usuario incluyendo su cantidad actual y su historial de movimientos.
- **Dependencias:** CU-37.1: Registrando inventario. CU-38: Visualizando stock actual con filtros de búsqueda.

### CU-37.3: Modificando inventario
- **Actores:** Administrador, jefa de taller.
- **Resumen:** Permite ajustar la cantidad de un registro de inventario existente dejando constancia del motivo.
- **Frecuencia:** Cada vez que se requiere corregir las existencias tras un inventario físico o una merma.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un registro de inventario en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Inventario > Existencias. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza el registro por bodega, producto, color o talla [Excepción 1]. 4. Selecciona el registro, ingresa la nueva cantidad y el motivo del ajuste, y confirma. El sistema valida, guarda el cambio y deja trazado el movimiento [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún registro de inventario con ese criterio. Excepción 2: Si no se ingresa el motivo del ajuste o la cantidad resultante es negativa, el sistema no permite continuar y solicita corrección.
- **Postcondición:** El registro de inventario queda modificado en la base de datos con su movimiento de ajuste trazado.
- **Dependencias:** CU-37.1: Registrando inventario. CU-38: Visualizando stock actual con filtros de búsqueda. CU-39: Actualizando stock automáticamente.

### CU-37.4: Eliminando inventario
- **Actores:** Administrador, jefa de taller.
- **Resumen:** Permite dar de baja del sistema un registro de inventario sin existencias.
- **Frecuencia:** Cada vez que se requiere retirar de la bodega una combinación de producto que ya no se maneja.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener permisos adecuados. 3. Debe existir al menos un registro de inventario en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Inventario > Existencias. 2. El sistema muestra el registro completo con barra de scroll y barra de búsqueda. 3. El usuario localiza el registro por bodega, producto, color o talla [Excepción 1]. 4. Selecciona el registro y elige Eliminar. El sistema solicita confirmación explícita antes de proceder [Excepción 2]. Al confirmar, da de baja el registro conservando su historial de movimientos.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún registro de inventario con ese criterio. Excepción 2: Si el registro tiene una cantidad distinta de cero, el sistema impide la eliminación e informa al usuario.
- **Postcondición:** El registro de inventario queda dado de baja en la base de datos, conservando su historial de movimientos.
- **Dependencias:** CU-37.1: Registrando inventario. CU-38: Visualizando stock actual con filtros de búsqueda.

### CU-38: Visualizando stock actual con filtros de búsqueda *(también en Documento 0)*
- **Actores:** Administrador / Jefa de taller / Vendedor.
- **Resumen:** Permite consultar el stock disponible por producto, color, talla y bodega, aplicando filtros de búsqueda y recorriendo el resultado mediante barra de scroll.
- **Frecuencia:** Cada vez que se está requiriendo conocer la disponibilidad de existencias.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de inventario.
- **Descripción:** 1. El usuario accede al módulo Inventario > Consulta de stock. 2. El sistema carga la tabla de existencias con barra de scroll vertical [Excepción 1]. 3. La tabla muestra bodega, producto, color, talla, cantidad disponible y fecha de última actualización. 4. El usuario aplica filtros por bodega, producto, color, talla o rango de cantidad [Excepción 2]. 5. Puede agrupar el resultado por producto o por bodega para visualizar totales consolidados. 6. Puede ordenar por cualquier columna. 7. Puede exportar el resultado a PDF o Excel.
- **Excepciones:** Excepción 1: Si no existen registros de inventario, el sistema muestra la tabla vacía con el mensaje correspondiente. Excepción 2: Si ningún registro coincide con los filtros aplicados, el sistema informa que no hay resultados para ese criterio.
- **Postcondición:** El usuario visualiza el stock actual según los filtros aplicados, sin modificar el inventario.
- **Dependencias:** CU-37: Gestionando inventario por producto, talla y color. CU-39: Actualizando stock automáticamente.

### CU-39: Actualizando stock automáticamente *(también en Documento 0)*
- **Actores:** Sistema.
- **Resumen:** Subproceso que actualiza las existencias de una bodega de forma automática cada vez que se registra una producción, un despacho o una recepción.
- **Frecuencia:** Cada vez que se registra un movimiento de producción, despacho o recepción.
- **Precondiciones:** 1. Debe existir el registro de inventario correspondiente a la combinación de producto, color y talla en la bodega afectada. 2. El movimiento debe encontrarse registrado en el sistema.
- **Descripción:** 1. El sistema detecta el registro de un movimiento de producción, despacho o recepción. 2. Identifica la bodega y las combinaciones de producto, color y talla involucradas [Excepción 1]. 3. Incrementa las existencias en los ingresos por producción o recepción, y las descuenta en los despachos [Excepción 2]. 4. Guarda la nueva cantidad y deja trazado el movimiento con su origen, fecha, hora y usuario responsable.
- **Excepciones:** Excepción 1: Si no existe registro de inventario para alguna combinación, el sistema lo crea con cantidad cero antes de aplicar el movimiento. Excepción 2: Si el descuento deja la existencia en negativo, el sistema impide la operación e informa al usuario.
- **Postcondición:** Las existencias de la bodega quedan actualizadas y el movimiento trazado en el historial de inventario.
- **Dependencias:** CU-21: Ingresando productos a bodega desde guía de cortes. CU-37.1: Registrando inventario. CU-37.3: Modificando inventario.

## Resúmenes de pedido (RF-040, RF-041)

### CU-40: Generando resumen de pedido *(también en Documento 0)*
- **Actores:** Administrador / Vendedor.
- **Resumen:** Permite generar el documento de resumen de un pedido, con el encabezado del cliente, el detalle por producto, color y talla, los montos y el estado de cumplimiento, listo para impresión o exportación.
- **Frecuencia:** Cada vez que se está requiriendo entregar o archivar el resumen de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir el pedido con al menos una línea de detalle.
- **Descripción:** 1. El usuario accede al módulo Ventas > Pedidos, selecciona el pedido y solicita generar el resumen. 2. El sistema recupera el encabezado: número de pedido, fecha, cliente, vendedor y zona de venta [Excepción 1]. 3. Recupera el detalle agrupado por producto, con sus colores, tallas, cantidades y subtotales. 4. Incorpora el monto neto, el descuento, el impuesto y el total. 5. Agrega el estado de cumplimiento y de facturación del pedido. 6. Muestra el resumen en pantalla y habilita su impresión o exportación a PDF [Excepción 2]. 7. El resumen queda registrado con su fecha de generación.
- **Excepciones:** Excepción 1: Si el pedido no tiene vendedor o zona de venta asignada, el sistema genera el resumen dejando esos campos en blanco y advierte al usuario. Excepción 2: Si falla la generación del documento, el sistema informa el error sin alterar el pedido.
- **Postcondición:** El resumen de pedido queda generado y disponible para impresión, exportación y consulta posterior.
- **Dependencias:** CU-01.1: Registrando cliente. CU-07.1: Registrando vendedor. CU-09.1: Registrando zona de venta. CU-22.1: Registrando pedido. CU-24: Gestionando detalle de pedido. CU-26: Calculando monto total del pedido. CU-27: Calculando porcentaje de cumplimiento del pedido.

### CU-41: Buscando y agrupando resúmenes de pedido
- **Actores:** Administrador / Vendedor.
- **Resumen:** Permite localizar resúmenes de pedido y agruparlos según fecha, producto, cliente o vendedor, obteniendo una vista consolidada de las ventas del período.
- **Frecuencia:** Cada vez que se está requiriendo analizar o localizar pedidos según un criterio determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir resúmenes de pedido generados.
- **Descripción:** 1. El usuario accede al módulo Informes > Resúmenes de pedido. 2. Define el rango de fechas a considerar [Excepción 1]. 3. Selecciona el criterio de agrupación: por fecha, por producto, por cliente o por vendedor. 4. Aplica filtros adicionales opcionales. 5. El sistema recupera los resúmenes que cumplen el criterio y los consolida, mostrando cantidad de pedidos, unidades y montos por grupo [Excepción 2]. 6. El usuario puede expandir un grupo para visualizar los pedidos individuales que lo componen. 7. Puede exportar el resultado a PDF o Excel.
- **Excepciones:** Excepción 1: Si la fecha de inicio es posterior a la fecha de término, el sistema no permite continuar. Excepción 2: Si no existen resúmenes para el criterio seleccionado, el sistema informa que no hay registros para ese criterio.
- **Postcondición:** El resultado agrupado queda disponible en pantalla y para exportación, sin alterar los pedidos ni sus resúmenes.
- **Dependencias:** CU-01.1: Registrando cliente. CU-07.1: Registrando vendedor. CU-13.1: Registrando producto. CU-22.1: Registrando pedido. CU-40: Generando resumen de pedido.

## Configuración e interfaz (RF-056, RF-061)

### CU-56: Configurando parámetros del sistema
- **Actores:** Administrador.
- **Resumen:** Permite definir y mantener los parámetros generales del sistema (datos de la empresa, moneda, impuestos y logotipo), evitando que su modificación requiera intervenir el código de la aplicación.
- **Frecuencia:** Ocasional: en la puesta en marcha del sistema y cada vez que cambia un dato institucional o tributario.
- **Precondiciones:** 1. El usuario debe estar autenticado con perfil de administrador.
- **Descripción:** 1. El usuario accede al módulo Configuración > Parámetros del sistema. 2. El sistema muestra los parámetros vigentes agrupados en empresa, moneda, impuestos e imagen institucional. 3. El usuario modifica razón social, RUT, giro, dirección, teléfono y correo de la empresa [Excepción 1]. 4. Define la moneda y su formato de presentación. 5. Define el porcentaje de impuesto aplicable a las ventas [Excepción 2]. 6. Carga el logotipo institucional [Excepción 3]. 7. Confirma los cambios. 8. El sistema guarda la nueva configuración, registra fecha, hora y usuario responsable, y la aplica a los documentos que se emitan desde ese momento.
- **Excepciones:** Excepción 1: Si el RUT ingresado no es válido, el sistema informa la situación y no permite guardar. Excepción 2: Si el porcentaje de impuesto es negativo o superior a cien, el sistema no permite continuar. Excepción 3: Si el archivo del logotipo excede el tamaño o el formato permitido, el sistema informa la situación y conserva el logotipo anterior.
- **Postcondición:** Los parámetros quedan actualizados y se aplican a los documentos emitidos con posterioridad, sin afectar los ya emitidos.
- **Dependencias:** CU-26: Calculando monto total del pedido. CU-29: Gestionando facturas. CU-35: Gestionando notas de crédito. CU-40: Generando resumen de pedido.

### CU-61: Mejorando la interfaz de usuario del sistema
- **Actores:** Administrador / Vendedor / Bodeguero.
- **Resumen:** Permite a los usuarios interactuar con una interfaz más eficiente en los distintos módulos del sistema, reduciendo la cantidad de clics y el tiempo requerido para completar tareas mediante atajos de navegación y mejoras visuales basadas en los mock-ups validados por el equipo.
- **Frecuencia:** Continua: se aplica en cada interacción del usuario con cualquier módulo del sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado en el sistema. 2. Deben existir los mock-ups de interfaz revisados y validados por el equipo.
- **Descripción:** 1. El usuario ingresa a un módulo del sistema (clientes, productos, pedidos, inventario, vendedores, etc.). 2. El sistema presenta la interfaz mejorada, con iconografía clara y un menú lateral y barra superior consistentes entre módulos [Excepción 1]. 3. El usuario ejecuta una acción común (crear, editar, buscar o eliminar un registro) utilizando campos de selección en vez de digitar identificadores y formularios agrupados, reduciendo la cantidad de clics respecto a la versión anterior [Excepción 2]. 4. El sistema confirma la acción realizada mediante un aviso breve en la misma pantalla, sin redirigir a una página en blanco. 5. El usuario continúa su flujo de trabajo sin perder el contexto de la pantalla en la que se encontraba.
- **Excepciones:** Excepción 1: Si el módulo aún no cuenta con la interfaz mejorada implementada, el sistema mantiene la interfaz anterior sin interrumpir la operación del usuario. Excepción 2: Si el usuario ingresa datos inválidos en un campo con lista desplegable o validación, el sistema informa el error mediante un aviso breve y no ejecuta la acción.
- **Postcondición:** La interacción del usuario con el sistema se realiza en menos pasos y con retroalimentación visual inmediata, sin afectar la lógica ni los datos gestionados por cada módulo.
- **Dependencias:** CU-01.1: Registrando cliente. CU-07.1: Registrando vendedor. CU-13.1: Registrando producto. CU-22.1: Registrando pedido. CU-37: Gestionando inventario por producto, talla y color. CU-56: Configurando parámetros del sistema.
