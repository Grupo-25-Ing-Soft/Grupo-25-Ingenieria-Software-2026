# Casos de uso extendidos

Fuente: **Documento 0** (versión corregida, octubre 2026), capítulo 7, Tablas 7.1 a 7.79.
Es la referencia principal de los casos de uso. Para los CU que el Documento 0 no detalla
(facturas, notas de crédito, listas, costos, configuración, interfaz) y para versiones más
detalladas de los CU del Incremento 2, ver [casos-de-uso-incremento-2.md](casos-de-uso-incremento-2.md).
La relación RF → CU está en [matriz-rf-cu.md](matriz-rf-cu.md).

**Numeración.** El número del caso de uso corresponde al número del requerimiento funcional
que implementa (CU-13 para RF-013). Cuando un requerimiento gestiona una entidad con operaciones
independientes, el caso de uso se subdivide en el orden registrar, consultar, modificar y eliminar
(CU-03.1 a CU-03.4 para colores). Los comportamientos complementarios de un mismo requerimiento
continúan la numeración correlativa (CU-01.5: Validando RUT de cliente).

Cada caso indica: actores, resumen, frecuencia, precondiciones, descripción (flujo, con las
excepciones referenciadas entre corchetes), excepciones, postcondición y dependencias.

## Clientes (RF-001, RF-002)

### CU-01.1: Registrando cliente
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite al administrador ingresar un nuevo cliente al sistema con todos sus datos comerciales y de contacto, asegurando que la información sea válida y completa.
- **Frecuencia:** Cada vez que se requiera registrar un nuevo cliente en la base de datos.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. El administrador debe tener permisos de rol adecuados.
- **Descripción:** 1. El usuario accede al módulo de Archivos Maestros > Clientes. 2. Selecciona la opción 'Nuevo cliente'. 3. El sistema despliega el formulario de registro. 4. El usuario ingresa: código de cliente, RUT, dígito verificador, nombre completo, abreviación, dirección, comuna, ciudad, hasta 2 teléfonos, giro, zona, código de vendedor, vía de despacho, condiciones de venta, hasta 3 descuentos en porcentaje, porcentaje de comisión, porcentaje de cobranza y observaciones [Excepción 1, 2, 3 y 4]. 5. El usuario selecciona el número de lista de precios asociado. 6. El usuario confirma el registro. 7. El sistema valida los datos ingresados. 8. El sistema guarda el registro y muestra confirmación.
- **Excepciones:** Excepción 1: Si el RUT ingresado ya existe, el sistema muestra un mensaje de error y no permite guardar. Excepción 2: Si faltan datos obligatorios, el sistema solicita completar los campos antes de continuar. Excepción 3: Si el formato del RUT es incorrecto, el sistema muestra un mensaje de error y solicita corrección. Excepción 4: Si el código de vendedor ingresado no existe, el sistema informa que el vendedor no está registrado. Retorna al paso 4.
- **Postcondición:** El cliente queda registrado en la base de datos con un RUT válido.
- **Dependencias:** CU-01.5: Validando RUT de cliente. CU-02: Buscando y visualizando lista de clientes.

### CU-01.2: Consultando cliente
- **Actores:** Administrador.
- **Resumen:** Permite buscar un cliente existente para consultar sus datos.
- **Frecuencia:** Cada vez que se requiere revisar información de clientes.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener rol de administrador. 3. Debe existir al menos un cliente registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Archivos Maestros > Clientes. 2. El sistema muestra la lista completa de clientes con barra de scroll y barra de búsqueda por nombre. 3. El usuario localiza al cliente por nombre o código [Excepción 1]. 4. El usuario selecciona el cliente y el sistema muestra todos sus datos en modo lectura.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún cliente con ese criterio.
- **Postcondición:** El registro del cliente queda consultado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.5: Validando RUT de cliente. CU-02: Buscando y visualizando lista de clientes.

### CU-01.3: Modificando cliente
- **Actores:** Administrador.
- **Resumen:** Permite buscar un cliente existente para modificar sus datos.
- **Frecuencia:** Cada vez que se requiere actualizar información de clientes.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener rol de administrador. 3. Debe existir al menos un cliente registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Archivos Maestros > Clientes. 2. El sistema muestra la lista completa de clientes con barra de scroll y barra de búsqueda por nombre. 3. El usuario localiza al cliente por nombre o código [Excepción 1]. 4. El usuario selecciona el cliente, edita los campos deseados y confirma. 5. El sistema valida y guarda los cambios.
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún cliente con ese criterio.
- **Postcondición:** El registro del cliente queda modificado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.5: Validando RUT de cliente. CU-02: Buscando y visualizando lista de clientes.

### CU-01.4: Eliminando cliente
- **Actores:** Administrador.
- **Resumen:** Permite buscar un cliente existente para eliminarlo del sistema.
- **Frecuencia:** Cada vez que se requiere eliminar información de clientes.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El usuario debe tener rol de administrador. 3. Debe existir al menos un cliente registrado en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Archivos Maestros > Clientes. 2. El sistema muestra la lista completa de clientes con barra de scroll y barra de búsqueda por nombre. 3. El usuario localiza al cliente por nombre o código [Excepción 1]. 4. El usuario selecciona el cliente y elige 'Eliminar'. 5. El sistema solicita confirmación explícita antes de proceder [Excepción 2].
- **Excepciones:** Excepción 1: Si la búsqueda no arroja resultados, el sistema informa que no existe ningún cliente con ese criterio. Excepción 2: Si el cliente tiene pedidos activos o pendientes, el sistema impide la eliminación e informa al usuario.
- **Postcondición:** El registro del cliente queda eliminado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.5: Validando RUT de cliente. CU-02: Buscando y visualizando lista de clientes.

### CU-01.5: Validando RUT de cliente
- **Actores:** Administrador, Sistema.
- **Resumen:** El sistema valida el RUT ingresado por el administrador al registrar o modificar un cliente, asegurando que cumpla con el formato correcto y que no existan los mismos datos en el sistema.
- **Frecuencia:** Cada vez que se ingresa o modifica un registro de cliente.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. El administrador debe tener los permisos adecuados.
- **Descripción:** 1. El administrador ingresa el RUT del cliente en el formulario de registro. 2. El sistema verifica que el RUT tenga el formato válido xx.xxx.xxx-x [Excepción 1 y 2]. 3. El sistema calcula y valida el dígito verificador ingresado. 4. El sistema consulta la base de datos para comprobar que no exista el RUT [Excepción 3]. 5. Si el RUT es válido y único, el sistema permite continuar con el registro.
- **Excepciones:** Excepción 1: Si el dígito verificador no coincide, el sistema muestra un mensaje de error descriptivo indicando que el RUT no es válido. Excepción 2: Si el RUT contiene caracteres no numéricos sin incluir K, el sistema indica el formato correcto. Excepción 3: Si el RUT ingresado ya existe en la base de datos, el sistema informa que ya existe registro del RUT para evitar duplicidad.
- **Postcondición:** El RUT queda marcado como válido o inválido, desbloqueando o bloqueando el guardado del registro.
- **Dependencias:** CU-01.1: Registrando cliente. CU-03.1 a CU-11.4: Registros maestros simples (colores, bodegas, vendedores, zonas de venta y tallas).

### CU-02: Buscando y visualizando lista de clientes
- **Actores:** Administrador / Vendedor.
- **Resumen:** Permite al usuario consultar la lista completa de clientes registrados en el sistema, visualizar sus datos y realizar búsquedas específicas por nombre, RUT, zona de venta, vendedor asociado.
- **Frecuencia:** Cada vez que se requiere consultar la información del cliente para gestión administrativa o comercial.
- **Precondiciones:** El administrador/vendedor debe estar autenticado en el sistema. Debe existir registro de clientes previamente ingresados.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Clientes. 2. El sistema muestra la lista completa de clientes con barra de scroll. 3. El usuario puede ingresar texto en la barra de búsqueda para filtrar por nombre [Excepción 1]. 4. La lista se actualiza dinámicamente mostrando solo los clientes que coinciden. 5. El usuario puede seleccionar cualquier cliente para ver su detalle.
- **Excepciones:** Excepción 1: Si no existe ningún cliente que coincida con el criterio de búsqueda, el sistema muestra el mensaje 'No se encontraron resultados'.
- **Postcondición:** El usuario visualiza el listado filtrado o completo de clientes.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.5: Validando RUT de cliente. CU-03.1 a CU-11.4: Registros maestros simples (colores, bodegas, vendedores, zonas de venta y tallas).

## Colores (RF-003, RF-004)

### CU-03.1: Registrando color
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite crear registros de colores utilizados en los productos.
- **Frecuencia:** Cada vez que se requiera crear información de colores.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Colores. 2. El sistema muestra la lista de colores con barra de scroll. 3. El usuario ingresa código de color de máx. 8 caracteres alfanuméricos y descripción de máx. 32 caracteres y confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: Si el código ya existe, el sistema rechaza e informa. Excepción 2: Si un campo obligatorio está vacío, el sistema indica el campo faltante.
- **Postcondición:** El registro de color queda creado.
- **Dependencias:** No registra dependencias.

### CU-03.2: Consultando color
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite consultar registros de colores utilizados en los productos.
- **Frecuencia:** Cada vez que se requiera consultar información de colores.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Colores. 2. El sistema muestra la lista de colores con barra de scroll. 3. El usuario selecciona el registro de color y ejecuta la consulta.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de color queda consultado.
- **Dependencias:** CU-03.1: Registrando color.

### CU-03.3: Modificando color
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite modificar registros de colores utilizados en los productos.
- **Frecuencia:** Cada vez que se requiera modificar información de colores.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Colores. 2. El sistema muestra la lista de colores con barra de scroll. 3. El usuario selecciona el registro de color, edita los campos y confirma.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de color queda modificado.
- **Dependencias:** CU-03.1: Registrando color.

### CU-03.4: Eliminando color
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite eliminar registros de colores utilizados en los productos.
- **Frecuencia:** Cada vez que se requiera eliminar información de colores.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Colores. 2. El sistema muestra la lista de colores con barra de scroll. 3. El usuario selecciona el registro de color y confirma la eliminación en el diálogo de confirmación [Excepción 1].
- **Excepciones:** Excepción 1: Si el color está asociado a un producto activo, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de color queda eliminado.
- **Dependencias:** CU-03.1: Registrando color.

## Bodegas (RF-005, RF-006)

### CU-05.1: Registrando bodega
- **Actores:** Administrador.
- **Resumen:** Permite crear registros de bodegas donde se almacenan los productos.
- **Frecuencia:** Cada vez que se requiera crear información de bodegas.
- **Precondiciones:** El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Bodegas. 2. El sistema muestra la lista de bodegas con barra de scroll. 3. El usuario ingresa código y descripción de bodega y confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: Si el código ya existe, el sistema rechaza e informa. Excepción 2: Si un campo obligatorio está vacío, el sistema indica el campo faltante.
- **Postcondición:** El registro de bodega queda creado.
- **Dependencias:** CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-05.2: Consultando bodega
- **Actores:** Administrador.
- **Resumen:** Permite consultar registros de bodegas donde se almacenan los productos.
- **Frecuencia:** Cada vez que se requiera consultar información de bodegas.
- **Precondiciones:** El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Bodegas. 2. El sistema muestra la lista de bodegas con barra de scroll. 3. El usuario selecciona la bodega y ejecuta la consulta.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de bodega queda consultado.
- **Dependencias:** CU-05.1: Registrando bodega. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-05.3: Modificando bodega
- **Actores:** Administrador.
- **Resumen:** Permite modificar registros de bodegas donde se almacenan los productos.
- **Frecuencia:** Cada vez que se requiera modificar información de bodegas.
- **Precondiciones:** El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Bodegas. 2. El sistema muestra la lista de bodegas con barra de scroll. 3. El usuario selecciona la bodega, edita los campos y confirma.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de bodega queda modificado.
- **Dependencias:** CU-05.1: Registrando bodega. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-05.4: Eliminando bodega
- **Actores:** Administrador.
- **Resumen:** Permite eliminar registros de bodegas donde se almacenan los productos.
- **Frecuencia:** Cada vez que se requiera eliminar información de bodegas.
- **Precondiciones:** El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Bodegas. 2. El sistema muestra la lista de bodegas con barra de scroll. 3. El usuario selecciona la bodega y confirma la eliminación en el diálogo de confirmación [Excepción 1].
- **Excepciones:** Excepción 1: Si la bodega tiene stock asociado, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de bodega queda eliminado.
- **Dependencias:** CU-05.1: Registrando bodega. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

## Vendedores (RF-007, RF-008)

### CU-07.1: Registrando vendedor
- **Actores:** Administrador.
- **Resumen:** Permite crear registros de vendedores, asegurando que cada código y RUT sean únicos y válidos.
- **Frecuencia:** Cada vez que se requiera crear información de vendedores.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El administrador selecciona la opción Archivos maestros > Vendedores. 2. El sistema despliega la lista de vendedores. 3. El usuario ingresa código de máx. 3 caracteres, RUT con dígito verificador separado, nombre y porcentaje de comisión; confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El administrador intenta crear un vendedor con un código ya existente, un RUT inválido o un dígito verificador incorrecto; el sistema informa que los datos son inválidos y solicita corrección. Excepción 2: Si un campo obligatorio está vacío, el sistema indica el campo faltante.
- **Postcondición:** El registro de vendedor queda creado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-07.2: Consultando vendedor
- **Actores:** Administrador.
- **Resumen:** Permite consultar registros de vendedores, asegurando que cada código y RUT sean únicos y válidos.
- **Frecuencia:** Cada vez que se requiera consultar información de vendedores.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El administrador selecciona la opción Archivos maestros > Vendedores. 2. El sistema despliega la lista de vendedores. 3. El usuario selecciona el vendedor y ejecuta la consulta [Excepción 1].
- **Excepciones:** Excepción 1: El administrador consulta o intenta eliminar un vendedor existente; el sistema informa que no se encontraron registros.
- **Postcondición:** El registro de vendedor queda consultado.
- **Dependencias:** CU-07.1: Registrando vendedor. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-07.3: Modificando vendedor
- **Actores:** Administrador.
- **Resumen:** Permite modificar registros de vendedores, asegurando que cada código y RUT sean únicos y válidos.
- **Frecuencia:** Cada vez que se requiera modificar información de vendedores.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El administrador selecciona la opción Archivos maestros > Vendedores. 2. El sistema despliega la lista de vendedores. 3. El usuario selecciona el vendedor, edita los campos y confirma.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de vendedor queda modificado.
- **Dependencias:** CU-07.1: Registrando vendedor. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-07.4: Eliminando vendedor
- **Actores:** Administrador.
- **Resumen:** Permite eliminar registros de vendedores, asegurando que cada código y RUT sean únicos y válidos.
- **Frecuencia:** Cada vez que se requiera eliminar información de vendedores.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El administrador selecciona la opción Archivos maestros > Vendedores. 2. El sistema despliega la lista de vendedores. 3. El usuario selecciona el vendedor y confirma la eliminación en el diálogo de confirmación [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El administrador consulta o intenta eliminar un vendedor existente; el sistema informa que no se encontraron registros. Excepción 2: Si el registro está siendo referenciado por productos, clientes o pedidos, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de vendedor queda eliminado.
- **Dependencias:** CU-07.1: Registrando vendedor. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

## Zonas de venta (RF-009, RF-010)

### CU-09.1: Registrando zona de venta
- **Actores:** Administrador.
- **Resumen:** Permite crear registros de zonas de venta.
- **Frecuencia:** Cada vez que se requiera crear información de zonas de venta.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Zonas de venta. 2. El sistema muestra la lista de zonas con barra de scroll. 3. El usuario ingresa código de máx. 3 caracteres y descripción de máx. 64 caracteres y confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El administrador intenta crear una zona de venta con un código ya existente; el sistema informa duplicidad y solicita ingresar un código nuevo. Excepción 2: La descripción no fue ingresada; el sistema informa que existen campos incompletos.
- **Postcondición:** El registro de zona de venta queda creado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-09.2: Consultando zona de venta
- **Actores:** Administrador.
- **Resumen:** Permite consultar registros de zonas de venta.
- **Frecuencia:** Cada vez que se requiera consultar información de zonas de venta.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Zonas de venta. 2. El sistema muestra la lista de zonas con barra de scroll. 3. El usuario selecciona la zona de venta y ejecuta la consulta [Excepción 1].
- **Excepciones:** Excepción 1: El administrador consulta o intenta eliminar una zona de venta inexistente; el sistema informa que no se encontraron registros.
- **Postcondición:** El registro de zona de venta queda consultado.
- **Dependencias:** CU-09.1: Registrando zona de venta. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-09.3: Modificando zona de venta
- **Actores:** Administrador.
- **Resumen:** Permite modificar registros de zonas de venta.
- **Frecuencia:** Cada vez que se requiera modificar información de zonas de venta.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Zonas de venta. 2. El sistema muestra la lista de zonas con barra de scroll. 3. El usuario selecciona la zona de venta, edita los campos y confirma.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de zona de venta queda modificado.
- **Dependencias:** CU-09.1: Registrando zona de venta. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

### CU-09.4: Eliminando zona de venta
- **Actores:** Administrador.
- **Resumen:** Permite eliminar registros de zonas de venta.
- **Frecuencia:** Cada vez que se requiera eliminar información de zonas de venta.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Zonas de venta. 2. El sistema muestra la lista de zonas con barra de scroll. 3. El usuario selecciona la zona de venta y confirma la eliminación en el diálogo de confirmación [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El administrador consulta o intenta eliminar una zona de venta inexistente; el sistema informa que no se encontraron registros. Excepción 2: Si el registro está siendo referenciado por productos, clientes o pedidos, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de zona de venta queda eliminado.
- **Dependencias:** CU-09.1: Registrando zona de venta. CU-01.1: Registrando cliente. CU-01.2 a CU-01.4: Consultando, modificando y eliminando cliente.

## Tallas (RF-011, RF-012)

### CU-11.1: Registrando talla
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite crear registros de tallas, asegurando que cada talla esté correctamente definida y disponible para asociarse a productos.
- **Frecuencia:** Cada vez que se requiera crear información de tallas.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Tallas. 2. El sistema muestra la lista de tallas con barra de scroll. 3. El usuario ingresa código de talla de máx. 2 caracteres alfanuméricos y confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El código ingresado ya existe en la base de datos; el sistema informa duplicidad y solicita corrección. Excepción 2: Si un campo obligatorio está vacío, el sistema indica el campo faltante.
- **Postcondición:** El registro de talla queda creado.
- **Dependencias:** CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-11.2: Consultando talla
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite consultar registros de tallas, asegurando que cada talla esté correctamente definida y disponible para asociarse a productos.
- **Frecuencia:** Cada vez que se requiera consultar información de tallas.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Tallas. 2. El sistema muestra la lista de tallas con barra de scroll. 3. El usuario selecciona la talla y ejecuta la consulta [Excepción 1].
- **Excepciones:** Excepción 1: El registro consultado o eliminado no existe; el sistema informa que no se encontraron datos.
- **Postcondición:** El registro de talla queda consultado.
- **Dependencias:** CU-11.1: Registrando talla. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-11.3: Modificando talla
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite modificar registros de tallas, asegurando que cada talla esté correctamente definida y disponible para asociarse a productos.
- **Frecuencia:** Cada vez que se requiera modificar información de tallas.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Tallas. 2. El sistema muestra la lista de tallas con barra de scroll. 3. El usuario selecciona la talla, edita los campos y confirma.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de talla queda modificado.
- **Dependencias:** CU-11.1: Registrando talla. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-11.4: Eliminando talla
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite eliminar registros de tallas, asegurando que cada talla esté correctamente definida y disponible para asociarse a productos.
- **Frecuencia:** Cada vez que se requiera eliminar información de tallas.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Tallas. 2. El sistema muestra la lista de tallas con barra de scroll. 3. El usuario selecciona la talla y confirma la eliminación en el diálogo de confirmación [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El registro consultado o eliminado no existe; el sistema informa que no se encontraron datos. Excepción 2: Si el registro está siendo referenciado por productos, clientes o pedidos, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de talla queda eliminado.
- **Dependencias:** CU-11.1: Registrando talla. CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

## Productos (RF-013, RF-014)

### CU-13.1: Registrando producto
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite al administrador crear registros de productos, asegurando que los productos queden correctamente definidos.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar la información de productos en el sistema.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir registros maestros de colores, tallas y bodegas previamente definidos.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Productos. 2. Selecciona 'Nuevo producto'. 3. El usuario ingresa: código de producto, descripción, abreviación, código de talla asociado, número de procesos y número de consumos [Excepción 1, 2 y 3]. 4. El usuario asocia los colores disponibles para el producto. 5. El usuario define los precios (precio costo, precio detalle, precio mayor, precio liquidación) y los ajusta por talla y color según corresponda. 6. El usuario confirma el registro. 7. El sistema valida los datos y guarda el producto.
- **Excepciones:** Excepción 1: El usuario no ingresa todos los campos obligatorios; el sistema informa que existen campos incompletos. Excepción 2: El código de producto ya existe; el sistema informa duplicidad y solicita ingresar un código único. Excepción 3: El código de talla no existe; el sistema informa que debe ingresar un código existente.
- **Postcondición:** El producto queda creado.
- **Dependencias:** CU-03.1 a CU-03.4 (color). CU-05.1 a CU-05.4 (bodega). CU-11.1 a CU-11.4 (talla).

### CU-13.2: Consultando producto
- **Actores:** Administrador.
- **Resumen:** Permite al administrador buscar un producto existente para consultar sus datos.
- **Frecuencia:** Cada vez que se está requiriendo revisar información de productos en el sistema.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Debe existir al menos un producto registrado.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Productos. 2. El sistema muestra la lista de productos con barra de scroll. 3. El usuario localiza el producto. 4. El usuario selecciona el producto y ejecuta la consulta.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El producto queda consultado.
- **Dependencias:** CU-13.1: Registrando producto. CU-03.1 a CU-03.4 (color). CU-05.1 a CU-05.4 (bodega). CU-11.1 a CU-11.4 (talla).

### CU-13.3: Modificando producto
- **Actores:** Administrador.
- **Resumen:** Permite al administrador buscar un producto existente para modificar sus datos.
- **Frecuencia:** Cada vez que se está requiriendo actualizar información de productos en el sistema.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Debe existir al menos un producto registrado.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Productos. 2. El sistema muestra la lista de productos con barra de scroll. 3. El usuario localiza el producto. 4. El usuario selecciona el producto, edita los campos y confirma [Excepción 1].
- **Excepciones:** Excepción 1: El usuario no ingresa todos los campos obligatorios al modificar; el sistema informa que existen campos incompletos.
- **Postcondición:** El producto queda modificado.
- **Dependencias:** CU-13.1: Registrando producto. CU-03.1 a CU-03.4 (color). CU-05.1 a CU-05.4 (bodega). CU-11.1 a CU-11.4 (talla).

### CU-13.4: Eliminando producto
- **Actores:** Administrador.
- **Resumen:** Permite al administrador buscar un producto existente para eliminar su registro.
- **Frecuencia:** Cada vez que se está requiriendo eliminar información de productos en el sistema.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Debe existir al menos un producto registrado.
- **Descripción:** 1. El usuario accede a Archivos Maestros > Productos. 2. El sistema muestra la lista de productos con barra de scroll. 3. El usuario localiza el producto. 4. El usuario selecciona el producto y ejecuta la eliminación [Excepción 1].
- **Excepciones:** Excepción 1: El producto a eliminar está asociado a pedidos activos; el sistema impide la eliminación e informa.
- **Postcondición:** El producto queda eliminado.
- **Dependencias:** CU-13.1: Registrando producto. CU-03.1 a CU-03.4 (color). CU-05.1 a CU-05.4 (bodega). CU-11.1 a CU-11.4 (talla).

### CU-13.5: Definiendo precios de producto por talla y color
- **Actores:** Administrador.
- **Resumen:** Permite al administrador definir precios de productos diferenciados por talla y color, asegurando que cada combinación tenga un valor único y válido en la base de datos para su correcta gestión.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar los precios de productos según talla y color.
- **Precondiciones:** El administrador debe estar autenticado en el sistema.
- **Descripción:** 1. El sistema muestra una grilla de precios con filas por talla y columnas por tipo de precio (costo, detalle, mayor, liquidación). 2. El usuario ingresa el valor de cada precio por talla [Excepción 1]. 3. El usuario puede marcar si aplica precio de liquidación. 4. El usuario confirma los precios.
- **Excepciones:** Excepción 1: La cantidad ingresada no es válida (valor nulo, negativo o formato incorrecto); el sistema informa que los datos son inválidos y solicita corrección.
- **Postcondición:** El precio queda definido, modificado o eliminado según la acción realizada.
- **Dependencias:** CU-03.1 a CU-03.4 (color). CU-11.1 a CU-11.4 (talla).

## Códigos EAN (RF-015 a RF-017)

### CU-15.1: Registrando código EAN
- **Actores:** Administrador.
- **Resumen:** Permite al administrador crear códigos EAN asociados a los productos, asegurando que cada código sea único y válido.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar los códigos EAN de los productos.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir productos previamente registrados para asociar códigos EAN.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Códigos EAN. 2. El sistema muestra la lista de registros: código de artículo, descripción, código EAN generado, talla y color. 3. El usuario ingresa el código del producto asociado; el sistema genera automáticamente el código EAN-13 y guarda el registro [Excepción 1 y 2].
- **Excepciones:** Excepción 1: El usuario intenta crear un código existente; el sistema informa duplicidad y solicita intentar de nuevo. Excepción 2: El usuario ingresa un código EAN inválido (formato); el sistema informa que los datos son inválidos.
- **Postcondición:** El código EAN queda creado.
- **Dependencias:** CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-15.2: Consultando código EAN
- **Actores:** Administrador.
- **Resumen:** Permite al administrador consultar códigos EAN asociados a los productos, asegurando que cada código sea único y válido.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar los códigos EAN de los productos.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir productos previamente registrados para asociar códigos EAN.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Códigos EAN. 2. El sistema muestra la lista de registros: código de artículo, descripción, código EAN generado, talla y color. 3. El usuario selecciona el registro y ejecuta la consulta [Excepción 1].
- **Excepciones:** Excepción 1: El usuario no ingresa todos los campos obligatorios; el sistema pedirá que se ingresen todos los datos.
- **Postcondición:** El código EAN queda consultado.
- **Dependencias:** CU-15.1: Registrando código EAN. CU-13.1 a CU-13.4 (producto).

### CU-15.3: Modificando código EAN
- **Actores:** Administrador.
- **Resumen:** Permite al administrador modificar códigos EAN asociados a los productos, asegurando que cada código sea único y válido.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar los códigos EAN de los productos.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir productos previamente registrados para asociar códigos EAN.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Códigos EAN. 2. El sistema muestra la lista de registros: código de artículo, descripción, código EAN generado, talla y color. 3. El usuario selecciona el registro y ejecuta la modificación [Excepción 1].
- **Excepciones:** Excepción 1: El usuario no ingresa todos los campos obligatorios; el sistema pedirá que se ingresen todos los datos.
- **Postcondición:** El código EAN queda modificado.
- **Dependencias:** CU-15.1: Registrando código EAN. CU-13.1 a CU-13.4 (producto).

### CU-15.4: Eliminando código EAN
- **Actores:** Administrador.
- **Resumen:** Permite al administrador eliminar códigos EAN asociados a los productos, asegurando que cada código sea único y válido.
- **Frecuencia:** Cada vez que se está requiriendo actualizar o administrar los códigos EAN de los productos.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir productos previamente registrados para asociar códigos EAN.
- **Descripción:** 1. El usuario accede al módulo Archivos Maestros > Códigos EAN. 2. El sistema muestra la lista de registros: código de artículo, descripción, código EAN generado, talla y color. 3. El usuario selecciona el registro y ejecuta la eliminación [Excepción 1].
- **Excepciones:** Excepción 1: El usuario no ingresa todos los campos obligatorios; el sistema pedirá que se ingresen todos los datos.
- **Postcondición:** El código EAN queda eliminado.
- **Dependencias:** CU-15.1: Registrando código EAN. CU-13.1 a CU-13.4 (producto).

### CU-15.5: Generando código EAN-13 automáticamente
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite al sistema generar automáticamente códigos EAN-13 válidos para los productos, asegurando que cada código sea único y cumpla con el estándar internacional de identificación.
- **Frecuencia:** Cada vez que se está requiriendo asignar un nuevo código EAN-13 a un producto.
- **Precondiciones:** El administrador debe estar autenticado en el sistema. Deben existir productos previamente registrados para asociarlos al código EAN-13.
- **Descripción:** 1. El sistema recibe código de producto, color y talla. 2. El sistema construye los primeros 12 dígitos del EAN según la combinación. 3. Calcula el dígito de control mediante el algoritmo EAN estándar. 4. Genera el código EAN-13 completo (13 dígitos numéricos). 5. Verifica que el código generado no exista ya en la base de datos [Excepción 1]. 6. Guarda el registro con el código generado.
- **Excepciones:** Excepción 1: El código EAN-13 generado ya existe en la base de datos; el sistema informa duplicidad y genera un nuevo código.
- **Postcondición:** El producto queda registrado con un código EAN-13 único y válido.
- **Dependencias:** CU-13.1 a CU-13.4: Registrando, consultando, modificando y eliminando producto.

### CU-17: Enviando solicitud de impresión de etiquetas EAN
- **Actores:** Administrador, Sistema, Impresora.
- **Resumen:** Permite al administrador emitir etiquetas EAN-13 desde el sistema hacia la impresora, asegurando que cada etiqueta corresponde a un producto válido y que el código sea legible para procesos de identificación y control.
- **Frecuencia:** Cada vez que se está requiriendo imprimir etiquetas EAN para productos registrados.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir códigos EAN registrados para el producto. 3. La impresora de etiquetas debe estar conectada.
- **Descripción:** 1. El usuario accede a la sección de emisión de EAN. 2. Ingresa el código de producto y código de color [Excepción 1]. 3. Ingresa la cantidad de etiquetas a imprimir por cada talla [Excepción 2]. 4. Confirma la impresión. 5. El sistema formatea la solicitud según el protocolo de la impresora. 6. El sistema envía la solicitud de impresión [Excepción 3]. 7. El sistema confirma el envío exitoso.
- **Excepciones:** Excepción 1: El producto seleccionado no tiene código EAN-13 asignado; el sistema informa que no se puede emitir la etiqueta. Excepción 2: El administrador no ingresa la cantidad de etiquetas a imprimir; el sistema informa que existen campos incompletos y solicita completarlos. Excepción 3: La impresora no responde o presenta un error de conexión; el sistema informa que no se puede continuar con la operación.
- **Postcondición:** Las etiquetas EAN-13 quedan emitidas en la impresora, listas para ser utilizadas.
- **Dependencias:** CU-13.1 a CU-13.4 (producto). CU-15.1 a CU-15.4 (código EAN). CU-15.5: Generando código EAN-13 automáticamente.

## Cortes y guía de cortes (RF-018 a RF-020)

### CU-18.1: Registrando corte
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite crear órdenes de corte de tela.
- **Frecuencia:** Cada vez que se está requiriendo organizar o actualizar la información de cortes de producción en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir productos registrados.
- **Descripción:** 1. El usuario accede al módulo de Producción > Cortes. 2. El sistema muestra el registro de cortes. 3. El usuario ingresa código de corte, fecha, nombre del cortador y observaciones; confirma [Excepción 1].
- **Excepciones:** Excepción 1: Si el código ya existe, el sistema rechaza e informa.
- **Postcondición:** El registro de corte queda creado.
- **Dependencias:** CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4: Consultando, modificando y eliminando pedido.

### CU-18.2: Consultando corte
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite consultar órdenes de corte de tela.
- **Frecuencia:** Cada vez que se está requiriendo organizar o actualizar la información de cortes de producción en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir productos registrados.
- **Descripción:** 1. El usuario accede al módulo de Producción > Cortes. 2. El sistema muestra el registro de cortes. 3. El usuario selecciona el corte y ejecuta la consulta.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de corte queda consultado.
- **Dependencias:** CU-18.1: Registrando corte. CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido).

### CU-18.3: Modificando corte
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite modificar órdenes de corte de tela.
- **Frecuencia:** Cada vez que se está requiriendo organizar o actualizar la información de cortes de producción en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir productos registrados.
- **Descripción:** 1. El usuario accede al módulo de Producción > Cortes. 2. El sistema muestra el registro de cortes. 3. El usuario selecciona el corte y ejecuta la modificación.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El registro de corte queda modificado.
- **Dependencias:** CU-18.1: Registrando corte. CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido).

### CU-18.4: Eliminando corte
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite eliminar órdenes de corte de tela.
- **Frecuencia:** Cada vez que se está requiriendo organizar o actualizar la información de cortes de producción en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir productos registrados.
- **Descripción:** 1. El usuario accede al módulo de Producción > Cortes. 2. El sistema muestra el registro de cortes. 3. El usuario selecciona el corte y ejecuta la eliminación [Excepción 1].
- **Excepciones:** Excepción 1: Si el corte ya tiene producción ingresada, el sistema impide la eliminación e informa.
- **Postcondición:** El registro de corte queda eliminado.
- **Dependencias:** CU-18.1: Registrando corte. CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido).

### CU-18.5: Registrando detalle de corte
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite ingresar el detalle de materiales usados y productos a cortar en una orden de corte.
- **Frecuencia:** Cada vez que se está requiriendo ingresar o modificar los detalles de un corte de producción.
- **Precondiciones:** 1. Debe existir un corte registrado. 2. Deben existir productos, colores y tallas registrados.
- **Descripción:** 1. El usuario accede al detalle del corte seleccionado. 2. Ingresa el tipo, color y cantidad de materia prima utilizada. 3. Ingresa el código del producto a cortar, su color y la cantidad por talla [Excepción 1]. 4. El usuario puede agregar múltiples líneas de materia prima y producción [Excepción 2]. 5. Confirma el detalle.
- **Excepciones:** Excepción 1: Si el producto no existe, el sistema informa y no agrega la línea. Excepción 2: Si la cantidad es cero o negativa, el sistema no permite agregar la línea.
- **Postcondición:** El detalle del corte queda registrado con los materiales y productos asociados.
- **Dependencias:** CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido.

### CU-18.6: Generando informe de cortes
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite generar el informe de los cortes de producción.
- **Frecuencia:** Cada vez que se está requiriendo organizar o actualizar la información de cortes de producción en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir productos registrados.
- **Descripción:** 1. El usuario accede al módulo de Producción > Cortes. 2. El sistema muestra el registro de cortes. 3. El usuario solicita el informe de cortes para un rango de fechas. 4. El sistema genera el informe exportable en PDF o Excel.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El informe de cortes queda disponible para impresión o exportación.
- **Dependencias:** CU-11.1 a CU-11.4 (talla). CU-03.1 a CU-03.4 (color). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido).

### CU-20: Generando guía de cortes
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Genera automáticamente la guía de corte en formato PDF para ser enviada al taller, con toda la información del corte y su detalle.
- **Frecuencia:** Cada vez que se está requiriendo emitir una guía de corte para un pedido o lote de producción.
- **Precondiciones:** 1. Debe existir un corte con detalle registrado. 2. El usuario debe estar autenticado.
- **Descripción:** 1. El usuario selecciona el corte. 2. Selecciona la opción 'Generar guía de corte'. 3. El sistema compila toda la información del corte: código, fecha, cortador, materiales, productos, tallas, cantidades. 4. El sistema genera el documento en formato PDF [Excepción 1]. 5. El usuario puede imprimir o guardar la guía. 6. Si se realizan cambios al corte, la guía se puede regenerar actualizada.
- **Excepciones:** Excepción 1: Si ocurre un error al generar el PDF, el sistema informa el error y sugiere reintentar.
- **Postcondición:** La guía de corte queda disponible en formato PDF para impresión o envío al taller.
- **Dependencias:** CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-18.1 a CU-18.4 (corte). CU-18.5: Registrando detalle de corte.

## Ingreso de producción a bodega (RF-021)

### CU-21: Ingresando productos a bodega desde guía de cortes
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite registrar los productos fabricados a partir de un corte e ingresarlos al stock de bodega.
- **Frecuencia:** Cada vez que se está requiriendo ingresar producción terminada a la bodega.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir un corte registrado previamente. 3. Deben existir bodegas registradas.
- **Descripción:** 1. El usuario accede a Producción > Ingreso de producción. 2. Selecciona el corte al que corresponde la producción [Excepción 1]. 3. El usuario ingresa los productos fabricados: código de producto, color, talla y cantidad [Excepción 2]. 4. Selecciona la bodega de destino. 5. Confirma el ingreso. 6. El sistema actualiza el stock de la bodega seleccionada.
- **Excepciones:** Excepción 1: Si el corte no existe, el sistema informa que el corte no existe y solicita corrección. Excepción 2: Si la cantidad ingresada es menor o igual a cero, el sistema no permite continuar y solicita corrección.
- **Postcondición:** El stock de la bodega queda incrementado con las unidades producidas registradas.
- **Dependencias:** CU-05.1 a CU-05.4 (bodega). CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-18.1 a CU-18.4 (corte). CU-18.5: Registrando detalle de corte.

## Pedidos (RF-022 a RF-027)

### CU-22.1: Registrando pedido
- **Actores:** Vendedor.
- **Resumen:** Permite al usuario registrar pedidos de clientes en el sistema, ingresando los datos del cliente, productos, cantidades y condiciones comerciales, asegurando que el pedido quede correctamente almacenado y disponible.
- **Frecuencia:** Cada vez que se está requiriendo ingresar un nuevo pedido de cliente.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir clientes y productos registrados en el sistema.
- **Descripción:** 1. El usuario accede al módulo de Producción > Pedidos. 2. Selecciona 'Nuevo pedido'. 3. El sistema asigna un número de pedido automáticamente. 4. El usuario selecciona el cliente, ingresa la fecha del pedido, el código de vendedor y la fecha de entrega estimada [Excepción 1]. 5. El usuario agrega el detalle del pedido: para cada línea, selecciona producto, color, talla y cantidad [Excepción 2]. 6. El sistema calcula automáticamente el monto total del pedido según precios y cantidades [Excepción 3]. 7. El sistema indica el porcentaje del pedido que puede cumplirse con el stock actual. 8. El usuario confirma y guarda el pedido.
- **Excepciones:** Excepción 1: El cliente seleccionado no existe en la base de datos; el sistema informa que el cliente es inválido y solicita corrección. Excepción 2: El producto seleccionado no existe o no tiene stock disponible; el sistema informa que el producto es inválido o no disponible. Excepción 3: La cantidad ingresada no es válida (valor nulo, negativo o formato incorrecto); el sistema informa que los datos son inválidos y solicita corrección.
- **Postcondición:** El pedido queda registrado en la base de datos, disponible para consultas, modificaciones y procesos posteriores (facturación y despacho).
- **Dependencias:** CU-01.1: Registrando cliente. CU-13.1 a CU-13.4 (producto).

### CU-22.2: Consultando pedido
- **Actores:** Vendedor / Administrador.
- **Resumen:** Permite consultar pedidos ya registrados en el sistema, asegurando que la operación mantenga la integridad de los datos.
- **Frecuencia:** Cada vez que se está requiriendo revisar un pedido previamente registrado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir al menos un pedido ya registrado en el sistema.
- **Descripción:** 1. El usuario accede a Producción > Pedidos. 2. El sistema muestra la lista de pedidos con sus estados. 3. El usuario localiza el pedido por número, cliente o fecha. 4. El usuario visualiza el detalle completo del pedido en modo lectura.
- **Excepciones:** No se registran excepciones.
- **Postcondición:** El pedido queda consultado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-01.1: Registrando cliente. CU-13.1 a CU-13.4 (producto). CU-24.1: Registrando detalle de pedido. CU-27: Calculando porcentaje de cumplimiento del pedido.

### CU-22.3: Modificando pedido
- **Actores:** Vendedor / Administrador.
- **Resumen:** Permite modificar pedidos ya registrados en el sistema, asegurando que la operación mantenga la integridad de los datos.
- **Frecuencia:** Cada vez que se está requiriendo actualizar un pedido previamente registrado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir al menos un pedido ya registrado en el sistema.
- **Descripción:** 1. El usuario accede a Producción > Pedidos. 2. El sistema muestra la lista de pedidos con sus estados. 3. El usuario localiza el pedido por número, cliente o fecha. 4. El usuario edita los campos del encabezado o el detalle de productos y confirma [Excepción 1].
- **Excepciones:** Excepción 1: Si el pedido está en estado 'Despachado' o 'Anulado', el sistema no permite modificarlo e informa al usuario.
- **Postcondición:** El pedido queda modificado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-01.1: Registrando cliente. CU-13.1 a CU-13.4 (producto). CU-24.1: Registrando detalle de pedido. CU-27: Calculando porcentaje de cumplimiento del pedido.

### CU-22.4: Eliminando pedido
- **Actores:** Vendedor / Administrador.
- **Resumen:** Permite eliminar pedidos ya registrados en el sistema, asegurando que la operación mantenga la integridad de los datos.
- **Frecuencia:** Cada vez que se está requiriendo eliminar un pedido previamente registrado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir al menos un pedido ya registrado en el sistema.
- **Descripción:** 1. El usuario accede a Producción > Pedidos. 2. El sistema muestra la lista de pedidos con sus estados. 3. El usuario localiza el pedido por número, cliente o fecha. 4. El usuario selecciona 'Eliminar' y confirma en el diálogo explícito [Excepción 1].
- **Excepciones:** Excepción 1: Si el pedido tiene pagos o abonos asociados, el sistema impide la eliminación e informa.
- **Postcondición:** El pedido queda eliminado.
- **Dependencias:** CU-22.1: Registrando pedido. CU-01.1: Registrando cliente. CU-13.1 a CU-13.4 (producto). CU-24.1: Registrando detalle de pedido. CU-27: Calculando porcentaje de cumplimiento del pedido.

### CU-24.1: Registrando detalle de pedido
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite al administrador agregar líneas de detalle a un pedido, especificando productos, cantidades, precios y condiciones comerciales, asegurando que cada línea quede correctamente registrada.
- **Frecuencia:** Cada vez que se está requiriendo ingresar o modificar las líneas de detalle de un pedido.
- **Precondiciones:** 1. El administrador debe estar autenticado. 2. Debe existir un pedido en proceso de creación o edición. 3. Deben existir productos registrados.
- **Descripción:** 1. El usuario selecciona la opción de agregar línea en el detalle del pedido. 2. Ingresa o busca el código de producto [Excepción 1]. 3. Selecciona el color y talla del producto. 4. Ingresa la cantidad por talla [Excepción 2]. 5. El sistema consulta el precio según la lista de precios del cliente. 6. El sistema actualiza el subtotal de la línea y el monto total del pedido. 7. El usuario puede repetir para agregar más líneas.
- **Excepciones:** Excepción 1: El código de producto ingresado no existe; el sistema informa que el código es inválido y solicita corrección. Excepción 2: La cantidad ingresada es cero o negativa; el sistema solicita corrección.
- **Postcondición:** Las líneas de detalle quedan registradas en el pedido, disponibles para consultas y modificaciones.
- **Dependencias:** CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido.

### CU-25: Anulando pedido existente
- **Actores:** Administrador.
- **Resumen:** Permite al administrador anular un pedido previamente registrado en el sistema, asegurando que la operación quede registrada.
- **Frecuencia:** Cada vez que se está requiriendo anular un pedido existente por errores, cambios en condiciones comerciales o solicitud del cliente.
- **Precondiciones:** 1. El usuario debe estar autenticado con rol de administrador. 2. El pedido debe estar en estado 'Pendiente' o 'En proceso'.
- **Descripción:** 1. El usuario accede a Producción > Pedidos. 2. Localiza y selecciona el pedido a anular [Excepción 1]. 3. Elige la opción 'Anular pedido'. 4. El sistema solicita confirmación y muestra el número de pedido y cliente afectado [Excepción 2]. 5. El usuario confirma. 6. El sistema cambia el estado del pedido a 'Anulado' y registra la fecha y usuario de la anulación.
- **Excepciones:** Excepción 1: Si el pedido ya está 'Anulado' o 'Despachado', el sistema informa que no es posible anular y cancela la operación. Excepción 2: Si el usuario cancela en el diálogo de confirmación, no se realiza ningún cambio.
- **Postcondición:** El pedido queda en estado 'Anulado'. El registro permanece en la base de datos para historial.
- **Dependencias:** CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido).

### CU-27: Calculando porcentaje de cumplimiento del pedido
- **Actores:** Administrador, Sistema.
- **Resumen:** Permite calcular el porcentaje de cumplimiento de un pedido en función del stock actual disponible, identificando qué parte del pedido puede ser atendida y qué parte queda pendiente.
- **Frecuencia:** Cada vez que se está requiriendo validar la disponibilidad de stock para un pedido registrado.
- **Precondiciones:** 1. El pedido debe tener al menos una línea de detalle. 2. Deben existir registros de stock en bodega.
- **Descripción:** 1. Para cada línea del pedido, el sistema consulta el stock disponible por producto, color y talla [Excepción 1]. 2. Calcula la cantidad que puede ser satisfecha: el mínimo entre cantidad pedida y stock disponible. 3. Suma las unidades satisfechas sobre las unidades totales pedidas. 4. Muestra el porcentaje resultante en el formulario del pedido.
- **Excepciones:** Excepción 1: Si no hay stock registrado para algún producto, el sistema considera 0 unidades disponibles para ese ítem.
- **Postcondición:** El porcentaje de cumplimiento del pedido queda calculado y registrado, permitiendo gestionar pedidos pendientes y planificar reposición de stock.
- **Dependencias:** CU-13.1 a CU-13.4 (producto). CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido.

## Cobranza y pagos (RF-031, RF-032, RF-034)

### CU-31: Generando informe de cobranza
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite generar un informe detallado del estado de cobranzas por cliente, mostrando pedidos, pagos realizados y saldos pendientes.
- **Frecuencia:** Cada vez que se está requiriendo revisar el estado de cobranza de clientes y pedidos.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de pedidos y pagos.
- **Descripción:** 1. El usuario accede a Informes > Cobranzas. 2. Define el rango de fechas y opcionalmente filtra por cliente o vendedor. 3. El sistema genera el informe con: cliente, pedidos asociados, montos, pagos recibidos, saldos pendientes y porcentaje de cobranza [Excepción 1]. 4. El usuario puede exportar el informe en PDF o Excel.
- **Excepciones:** Excepción 1: Si no existen datos para los filtros ingresados, el sistema informa que no hay registros para este criterio.
- **Postcondición:** El informe de cobranzas queda generado y disponible para exportación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido). CU-34: Automatizando la asignación de pagos a pedidos pendientes. CU-32.1: Registrando pago o depósito de cliente.

### CU-32.1: Registrando pago o depósito de cliente
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite ingresar un monto depositado por un cliente que quedará disponible para aplicarse a pedidos pendientes.
- **Frecuencia:** Cada vez que se está requiriendo ingresar un depósito de cliente en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir el cliente en el sistema.
- **Descripción:** 1. El usuario accede a Ventas > Cobranza > Depósitos. 2. Selecciona el cliente. 3. Ingresa el monto del depósito, la fecha y una referencia, como el número de transferencia o cheque [Excepción 1 y 2]. 4. Confirma el registro. 5. El sistema guarda el depósito y lo deja disponible para asignación a pedidos.
- **Excepciones:** Excepción 1: Si el monto es cero o negativo, el sistema no permite continuar. Excepción 2: Si el cliente no tiene pedidos pendientes, el sistema informa, pero permite registrar el depósito de todas formas.
- **Postcondición:** El depósito queda registrado y disponible para ser aplicado a pedidos del cliente.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido). CU-34: Automatizando la asignación de pagos a pedidos pendientes.

### CU-34: Automatizando la asignación de pagos a pedidos pendientes
- **Actores:** Administrador / Asistente de finanzas.
- **Resumen:** Permite registrar pagos o depósitos de clientes y aplicarlos a pedidos pendientes, con determinación automática de los pedidos cubiertos por el monto disponible.
- **Frecuencia:** Cada vez que se requiera registrar un pago, consultar el estado de cobranza o actualizar información financiera de un pedido.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir al menos un cliente con pedidos pendientes de pago.
- **Descripción:** 1. El usuario accede al módulo de Ventas > Cobranza. 2. Selecciona el cliente. 3. Ingresa el monto del depósito o pago recibido [Excepción 1]. 4. El sistema determina automáticamente qué pedidos pendientes pueden ser pagados total o parcialmente con el monto disponible [Excepción 2]. 5. El usuario revisa la asignación propuesta y confirma [Excepción 3]. 6. El sistema actualiza el estado de los pedidos afectados (pagados o parcialmente pagados) y registra el saldo.
- **Excepciones:** Excepción 1: Si el monto ingresado es cero o negativo, el sistema no permite continuar. Excepción 2: Si el monto no alcanza para cubrir ningún pedido, el sistema informa el saldo pendiente mínimo requerido. Excepción 3: El usuario puede ajustar manualmente la asignación antes de confirmar.
- **Postcondición:** Los pedidos afectados quedan con su estado de pago actualizado y el registro de cobranza queda guardado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).

## Inventario y stock (RF-037 a RF-039)

### CU-38: Visualizando stock actual con filtros de búsqueda
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite visualizar el stock disponible de un producto en todas sus variantes de talla y color, en cada bodega.
- **Frecuencia:** Cada vez que se está requiriendo verificar la disponibilidad de un producto en particular.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de stock.
- **Descripción:** 1. El usuario accede a Inventario > Consulta de stock. 2. Ingresa o busca el código de producto [Excepción 1]. 3. El sistema muestra una tabla con columnas por talla y filas por color, con las unidades disponibles en cada combinación. 4. El usuario puede filtrar por bodega específica.
- **Excepciones:** Excepción 1: Si el producto no tiene stock registrado, el sistema muestra la tabla con valores cero.
- **Postcondición:** El usuario visualiza el stock actualizado del producto.
- **Dependencias:** CU-11.1 a CU-11.4 (talla). CU-09.1 a CU-09.4 (zona de venta). CU-13.1 a CU-13.4 (producto). CU-21: Ingresando productos a bodega desde guía de cortes. CU-52: Generando informe de inventario.

### CU-39: Actualizando stock automáticamente
- **Actores:** Sistema.
- **Resumen:** Subproceso que actualiza el inventario en la bodega correspondiente al confirmar un ingreso de producción.
- **Frecuencia:** Cada vez que se está registrando un ingreso de producción a la bodega.
- **Precondiciones:** 1. Debe existir un ingreso de producción confirmado. 2. La bodega de destino debe estar registrada.
- **Descripción:** 1. El sistema recibe los productos ingresados con código, color, talla y cantidad. 2. Para cada línea, busca el registro de stock en la bodega de destino. 3. Si existe el registro, suma la cantidad ingresada al stock actual [Excepción 1]. 4. Si no existe el registro, crea uno nuevo con la cantidad ingresada. 5. Registra la operación con fecha, hora y usuario responsable.
- **Excepciones:** Excepción 1: Si ocurre un error de concurrencia (dos ingresos simultáneos), el sistema usa transacciones para garantizar la integridad.
- **Postcondición:** El inventario de la bodega queda actualizado con las unidades ingresadas.
- **Dependencias:** CU-05.1 a CU-05.4 (bodega). CU-13.1 a CU-13.4 (producto). CU-21: Ingresando productos a bodega desde guía de cortes.

## Resúmenes de pedido (RF-040, RF-041)

### CU-40: Generando resumen de pedido
- **Actores:** Administrador.
- **Resumen:** Muestra para un pedido seleccionado el detalle de productos, colores, tallas, cantidades, costos, precios, fechas de despacho y pago.
- **Frecuencia:** Cada vez que se está requiriendo obtener un resumen de pedidos para análisis o gestión.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir pedidos registrados.
- **Descripción:** 1. El usuario accede a Informes > Resumen de pedidos. 2. Ingresa criterios de búsqueda: por pedido, por cliente, por vendedor, o por producto incluido [Excepción 1]. 3. El sistema muestra un listado resumido de los pedidos que coinciden. 4. El usuario puede seleccionar un pedido para ver el detalle completo. 5. El detalle muestra: productos, color, talla, cantidad, costo de realización, precio a pagar, fecha límite de despacho y pago. 6. El usuario puede exportar el resumen o el detalle en PDF o Excel.
- **Excepciones:** Excepción 1: Si no hay pedidos que coincidan con el criterio, el sistema informa que no hay resultados.
- **Postcondición:** El resumen o detalle del pedido queda disponible para la visualización y exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-24.1: Registrando detalle de pedido. CU-22.2 a CU-22.4 (pedido). CU-34: Automatizando la asignación de pagos a pedidos pendientes.

## Informes de despacho (RF-042 a RF-046)

> Estos casos de uso fueron revisados en el Documento 0 de octubre y traen una fila
> **Requerimientos** explícita. El registro de despachos que los alimenta (tabla `despachos`)
> no tiene caso de uso propio; su CRUD está planificado para el Incremento 4.

### CU-42: Generando informe de productos pendientes de despacho
- **Actores:** Administrador.
- **Resumen:** Detalla los productos ya fabricados que aún no han sido despachados, dentro de un rango de fechas ingresado por el usuario.
- **Frecuencia:** Cada vez que se requiere revisar el estado de los pedidos y productos pendientes de despacho.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir pedidos con productos fabricados no despachados.
- **Descripción:** 1. El usuario accede a Informes > Productos pendientes de despacho. 2. El usuario ingresa el rango de fechas [Excepción 1]. 3. El sistema muestra los productos fabricados pendientes de despacho dentro del rango, con su información. 4. El sistema puede mostrar la comparativa de productos pedidos versus despachados definida en RF-044; no forma parte de los requerimientos de este caso y se planifica para el Incremento 4. 5. Si el usuario requiere buscar o agrupar el resultado por pedido, cliente o vendedor, continúa en CU-43. 6. El usuario puede exportar el informe (CU-59: Exportando datos y listas).
- **Excepciones:** Excepción 1 (paso 2): si no hay productos pendientes de despacho en el rango dado, el sistema informa el resultado vacío.
- **Postcondición:** El informe de productos pendientes de despacho queda generado y disponible para su consulta y exportación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).
- **Requerimientos:** RF-042
- **Observaciones:** La exportación depende de CU-59 (RF-059), planificado para el Incremento 4.

### CU-43: Buscando informe de productos pendientes de despacho
- **Actores:** Administrador.
- **Resumen:** Permite buscar y agrupar los productos ya fabricados que aún no han sido despachados, según rango de fechas y filtros por pedido, cliente o vendedor.
- **Frecuencia:** Cada vez que se requiere revisar los pendientes de despacho de un pedido, cliente o vendedor determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir pedidos con productos fabricados no despachados.
- **Descripción:** 1. El usuario accede a Informes > Productos pendientes de despacho. 2. El usuario ingresa el rango de fechas [Excepción 1]. 3. El usuario ingresa uno o más filtros: pedido, cliente o vendedor [Excepción 2]. 4. El sistema muestra los productos pendientes de despacho que coinciden con los parámetros, con su información. 5. El sistema puede mostrar la comparativa de RF-044, planificada para el Incremento 4. 6. El usuario puede exportar el resultado (CU-59).
- **Excepciones:** Excepción 1 (paso 2): si no hay productos pendientes en el rango dado, el sistema informa el resultado vacío. Excepción 2 (paso 3): si no hay productos dentro de los parámetros dados, el sistema informa que no hay resultados.
- **Postcondición:** El informe de pendientes, acotado según los parámetros ingresados, queda disponible para su consulta y exportación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4. CU-42: Generando informe de productos pendientes de despacho.
- **Requerimientos:** RF-043
- **Observaciones:** La exportación depende de CU-59 (RF-059), planificado para el Incremento 4.

### CU-45: Generando informe de productos despachados
- **Actores:** Administrador.
- **Resumen:** Detalla los productos despachados y sus pedidos correspondientes dentro de las fechas elegidas por el usuario.
- **Frecuencia:** Cada vez que se requiere revisar el historial de productos despachados para control, auditoría o análisis de cumplimiento.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos.
- **Descripción:** 1. El usuario accede a Informes > Productos despachados. 2. El usuario define el rango de fechas [Excepción 1]. 3. El sistema muestra los despachos realizados en el rango, con el detalle de productos y pedidos correspondientes. 4. Si el usuario requiere buscar o agrupar el resultado por pedido, cliente, factura o producto, continúa en CU-46. 5. El usuario puede exportar el informe en PDF o Excel (CU-59).
- **Excepciones:** Excepción 1 (paso 2): si no hay despachos en el periodo dado, el sistema informa que no se encuentran registros.
- **Postcondición:** El informe de despachos queda generado y disponible para su consulta y exportación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4. CU-42: Generando informe de productos pendientes de despacho.
- **Requerimientos:** RF-045
- **Observaciones:** La exportación depende de CU-59 (RF-059), planificado para el Incremento 4. El registro de despachos que alimenta este caso no tiene caso de uso propio.

### CU-46: Buscando informe de productos despachados
- **Actores:** Administrador.
- **Resumen:** Permite buscar y agrupar los productos despachados y sus pedidos correspondientes, según rango de fechas y filtros por pedido, cliente, factura o producto.
- **Frecuencia:** Cada vez que se requiere localizar despachos de un pedido, cliente, factura o producto determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos.
- **Descripción:** 1. El usuario accede a Informes > Productos despachados. 2. El usuario define el rango de fechas [Excepción 1]. 3. El usuario ingresa uno o más filtros: pedido, cliente, factura o producto [Excepción 2]. 4. El sistema muestra los despachos que coinciden con los parámetros, con el detalle de productos y pedidos correspondientes. 5. El usuario puede exportar el resultado en PDF o Excel (CU-59).
- **Excepciones:** Excepción 1 (paso 2): si no hay despachos en el periodo dado, el sistema informa que no se encuentran registros. Excepción 2 (paso 3): si no hay despachos con los parámetros dados, el sistema informa que no se encuentran registros.
- **Postcondición:** El informe de productos despachados, acotado según los parámetros ingresados, queda disponible para su consulta y exportación.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4. CU-45: Generando informe de productos despachados.
- **Requerimientos:** RF-046
- **Observaciones:** La exportación depende de CU-59 (RF-059), planificado para el Incremento 4.

## Análisis de ventas y despachos (RF-047 a RF-051)

### CU-47: Generando análisis de ventas y descuentos
- **Actores:** Administrador.
- **Resumen:** Permite generar análisis cruzados de ventas, descuentos y despachos desde distintas perspectivas: por factura, cliente, producto y vendedor.
- **Frecuencia:** Cada vez que se requiere evaluar el desempeño de ventas y despachos en un período determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos y ventas.
- **Descripción:** 1. El usuario accede a Informes > Análisis de ventas y despachos. 2. El usuario selecciona el tipo de análisis: ventas y descuentos (RF-047), despachos según factura y cliente (RF-048), despachos a cliente por producto (RF-049), despachos por vendedor y producto (RF-050) o pedidos y despachos mensuales (RF-051). 3. El usuario define los parámetros de filtro según el tipo de análisis [Excepción 1]. 4. El sistema genera el análisis solicitado. 5. El usuario puede exportar el resultado (CU-59).
- **Excepciones:** Excepción 1 (paso 3): si no hay datos para los parámetros ingresados, el sistema informa que no hay resultados.
- **Postcondición:** El análisis queda generado y disponible para exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-22.2 a CU-22.4. CU-40: Generando resumen de pedido. CU-42: Generando informe de productos pendientes de despacho. CU-45: Generando informe de productos despachados.
- **Requerimientos:** RF-047
- **Observaciones:** La exportación depende de CU-59 (RF-059), planificado para el Incremento 4. Los registros de ventas se obtienen de pedidos, facturas y despachos; las tablas `ventas` y `detalle_ventas` no se usan.

### CU-48: Generando análisis de despachos según factura y cliente
- **Actores:** Administrador.
- **Resumen:** Permite generar análisis de despachos realizados a cierto cliente, y sus facturas asociadas.
- **Frecuencia:** Cada vez que se está requiriendo evaluar la cantidad y monto asociado de los despachos a un cliente en un período determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos, clientes y facturas.
- **Descripción:** 1. El usuario accede a Informes > Análisis de despachos según factura y cliente. 2. Define el cliente y/o facturas que buscar [Excepción 1]. 3. El sistema genera el análisis solicitado. 4. El usuario puede exportar el resultado.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros ingresados, el sistema informa que no hay resultados.
- **Postcondición:** El análisis queda generado y disponible para exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).
- **Requerimientos:** RF-048

### CU-49: Generando análisis de despachos a cliente por producto
- **Actores:** Administrador.
- **Resumen:** Permite generar análisis de los despachos realizados a un cliente, detallándolos por producto.
- **Frecuencia:** Cada vez que se está requiriendo evaluar la cantidad de ciertos productos despachada a cierto cliente en un período determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos, clientes y productos.
- **Descripción:** 1. El usuario accede a Informes > Análisis de despachos a cliente por producto. 2. Define el cliente y/o producto que buscar [Excepción 1]. 3. El sistema genera el análisis solicitado. 4. El usuario puede exportar el resultado.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros ingresados, el sistema informa que no hay resultados.
- **Postcondición:** El análisis queda generado y disponible para exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).
- **Requerimientos:** RF-049

### CU-50: Generando análisis de despachos por vendedor y producto
- **Actores:** Administrador.
- **Resumen:** Permite generar análisis de despachos asociados a cierto vendedor y/o cierto producto.
- **Frecuencia:** Cada vez que se está requiriendo evaluar el desempeño de ventas y despachos en un período determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos, vendedores y productos.
- **Descripción:** 1. El usuario accede a Informes > Análisis de ventas y despachos. 2. Define el vendedor y/o producto que buscar [Excepción 1]. 3. El sistema genera el análisis solicitado. 4. El usuario puede exportar el resultado.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros ingresados, el sistema informa que no hay resultados.
- **Postcondición:** El análisis queda generado y disponible para exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).
- **Requerimientos:** RF-050

### CU-51: Generando análisis de pedidos y despachos mensuales
- **Actores:** Administrador.
- **Resumen:** Permite generar un análisis de los pedidos ingresados y despachos realizados por mes.
- **Frecuencia:** Cada vez que se está requiriendo evaluar la cantidad de trabajo que se está encargando versus la que se está completando en un mes determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de despachos y pedidos.
- **Descripción:** 1. El usuario accede a Informes > Análisis de pedidos y despachos mensuales. 2. Define los meses que analizar [Excepción 1]. 3. El sistema genera el análisis solicitado. 4. El usuario puede exportar el resultado.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros ingresados, el sistema informa que no hay resultados.
- **Postcondición:** El análisis queda generado y disponible para exportación.
- **Dependencias:** CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido).
- **Requerimientos:** RF-051

## Informes de inventario (RF-052, RF-053)

### CU-52: Generando informe de inventario de productos terminados
- **Actores:** Administrador.
- **Resumen:** Muestra los productos terminados entre fechas elegidas por talla y color, detallando productos con defectos y asociación a pedidos.
- **Frecuencia:** Cada vez que se está requiriendo revisar el estado del inventario en la bodega.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de inventario.
- **Descripción:** 1. El usuario accede a Informes > Inventario. 2. Define el rango de fechas [Excepción 1]. 3. El sistema realiza y muestra el informe con los datos entre las fechas ingresadas. 4. El usuario puede exportar el informe.
- **Excepciones:** Excepción 1: Si no hay registros de inventario dentro del rango dado, el sistema informa que no hay resultados.
- **Postcondición:** El informe de productos terminados queda generado y disponible para exportación.
- **Dependencias:** CU-05.1 a CU-05.4 (bodega). CU-13.1 a CU-13.4 (producto). CU-21: Ingresando productos a bodega desde guía de cortes. CU-39: Actualizando stock automáticamente.
- **Requerimientos:** RF-052

### CU-53: Generando análisis de inventario
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite generar y consultar un análisis del inventario, mostrando los productos en stock, los productos con defectos y si los productos están asociados a pedidos.
- **Frecuencia:** Cada vez que se requiera revisar el estado actual del inventario.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de inventario y stock en bodega.
- **Descripción:** 1. El usuario accede a Informes > Inventario. 2. Selecciona la opción análisis de inventario. 3. El sistema muestra los productos en stock, los productos con defectos y la información sobre si los productos están asociados a pedidos [Excepción 1]. 4. El usuario puede exportar el resultado del análisis a PDF o imprimirlo.
- **Excepciones:** Excepción 1: Si no existen registros de stock o información de inventario para realizar el análisis, el sistema informa que no existen resultados disponibles.
- **Postcondición:** El análisis de inventario queda generado y disponible para consulta y exportación.
- **Dependencias:** CU-05.1 a CU-05.4 (bodega). CU-13.1 a CU-13.4 (producto). CU-21: Ingresando productos a bodega desde guía de cortes. CU-39: Actualizando stock automáticamente.
- **Requerimientos:** RF-053

## Informes de producción (RF-054, RF-055)

### CU-54: Generando informe de productos en proceso
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite generar y consultar informes de productos presentes en cortes, pero todavía no fabricados.
- **Frecuencia:** Cada vez que se está requiriendo revisar el estado de la producción en un periodo determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de cortes.
- **Descripción:** 1. El usuario accede a Informes > Informe de Productos en Proceso. 2. Define los parámetros de filtro, tales como fechas, producto, cliente [Excepción 1]. 3. El sistema genera el informe solicitado. 4. El usuario puede exportar la guía en PDF o el informe en Excel.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros dados, el sistema informa el resultado vacío.
- **Postcondición:** El informe de producción queda generado y disponible para exportación o impresión.
- **Dependencias:** CU-18.1 a CU-18.4 (corte). CU-18.5: Registrando detalle de corte. CU-21: Ingresando productos a bodega desde guía de cortes. CU-39: Actualizando stock automáticamente.
- **Requerimientos:** RF-054

### CU-55: Generando resumen de producción
- **Actores:** Administrador / Jefa de taller.
- **Resumen:** Permite generar y consultar resúmenes sobre los productos producidos en un período determinado.
- **Frecuencia:** Cada vez que se está requiriendo revisar el estado de la producción en un periodo determinado.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Deben existir registros de cortes ya ingresados a bodega.
- **Descripción:** 1. El usuario accede a Informes > Resumen de producción. 2. Define los parámetros de filtro, tales como fechas, producto, cliente [Excepción 1]. 3. El sistema genera el informe solicitado. 4. El usuario puede exportar la guía en PDF o el informe en Excel.
- **Excepciones:** Excepción 1: Si no hay datos para los parámetros dados, el sistema informa el resultado vacío.
- **Postcondición:** El informe de producción queda generado y disponible para exportación o impresión.
- **Dependencias:** CU-18.1 a CU-18.4 (corte). CU-18.5: Registrando detalle de corte. CU-21: Ingresando productos a bodega desde guía de cortes. CU-39: Actualizando stock automáticamente.
- **Requerimientos:** RF-055

## Usuarios y acceso (RF-057, RF-058)

### CU-57.1: Registrando usuario
- **Actores:** Administrador.
- **Resumen:** Permite crear cuentas de usuario del sistema, asignando roles y niveles de acceso.
- **Frecuencia:** Cada vez que se está requiriendo crear, actualizar o administrar cuentas de usuarios en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede al módulo de Configuración > Usuarios. 2. El sistema muestra la lista de usuarios registrados. 3. El usuario ingresa nombre de usuario, contraseña y rol asignado; confirma [Excepción 1 y 2].
- **Excepciones:** Excepción 1: Si el nombre de usuario ya existe, el sistema rechaza la creación e informa. Excepción 2: Si la contraseña no cumple el mínimo de seguridad (4 dígitos numéricos), el sistema indica el requisito.
- **Postcondición:** El registro de usuario queda creado.
- **Dependencias:** CU-01.1: Registrando cliente. CU-03.1 a CU-11.4: Registros maestros simples. CU-18.1 a CU-18.4 (corte). CU-34: Automatizando la asignación de pagos a pedidos pendientes.

### CU-57.2: Modificando usuario
- **Actores:** Administrador.
- **Resumen:** Permite modificar cuentas de usuario del sistema, asignando roles y niveles de acceso.
- **Frecuencia:** Cada vez que se está requiriendo crear, actualizar o administrar cuentas de usuarios en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede al módulo de Configuración > Usuarios. 2. El sistema muestra la lista de usuarios registrados. 3. El usuario selecciona un usuario, edita los campos (incluyendo cambio de contraseña o rol) y confirma [Excepción 1].
- **Excepciones:** Excepción 1: Si la contraseña no cumple el mínimo de seguridad (4 dígitos numéricos), el sistema indica el requisito.
- **Postcondición:** El registro de usuario queda modificado.
- **Dependencias:** CU-57.1: Registrando usuario. CU-01.1: Registrando cliente. CU-03.1 a CU-11.4: Registros maestros simples. CU-18.1 a CU-18.4 (corte). CU-34.

### CU-57.3: Eliminando usuario
- **Actores:** Administrador.
- **Resumen:** Permite eliminar cuentas de usuario del sistema.
- **Frecuencia:** Cada vez que se está requiriendo crear, actualizar o administrar cuentas de usuarios en el sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado con el rol de administrador.
- **Descripción:** 1. El usuario accede al módulo de Configuración > Usuarios. 2. El sistema muestra la lista de usuarios registrados. 3. El usuario selecciona el usuario y confirma en el diálogo explícito [Excepción 1].
- **Excepciones:** Excepción 1: Si el usuario intenta eliminar su propia cuenta, el sistema lo impide e informa.
- **Postcondición:** El registro de usuario queda eliminado.
- **Dependencias:** CU-57.1: Registrando usuario. CU-01.1: Registrando cliente. CU-03.1 a CU-11.4: Registros maestros simples. CU-18.1 a CU-18.4 (corte). CU-34.

### CU-57.4: Autenticando usuario
- **Actores:** Usuario / Sistema.
- **Resumen:** Permite al usuario iniciar sesión en el sistema ingresando su nombre de usuario y contraseña.
- **Frecuencia:** Cada vez que un usuario está intentando ingresar al sistema.
- **Precondiciones:** 1. El sistema debe estar en ejecución. 2. El usuario debe tener una cuenta activa registrada.
- **Descripción:** 1. El usuario abre el sistema y accede a la pantalla de inicio de sesión. 2. Ingresa su nombre de usuario y contraseña. 3. Confirma con el botón 'Ingresar'. 4. El sistema verifica las credenciales contra la base de datos con la contraseña hasheada [Excepción 1 y 2]. 5. Si son válidas, el sistema carga la interfaz correspondiente al rol del usuario.
- **Excepciones:** Excepción 1: Si las credenciales son incorrectas, el sistema muestra un mensaje de error genérico ("Usuario o contraseña incorrectos") sin indicar cuál de los dos falló. Excepción 2: Si el usuario no tiene cuenta, el mensaje es el mismo para no revelar información.
- **Postcondición:** El usuario queda autenticado y accede a los módulos permitidos por su rol.
- **Dependencias:** CU-18.1 a CU-18.4 (corte). CU-34. CU-58: Controlando acceso por rol (RBAC).

### CU-58: Controlando acceso por rol (RBAC)
- **Actores:** Sistema.
- **Resumen:** El sistema aplica el control de acceso basado en roles, limitando la disponibilidad de módulos y operaciones según los permisos de usuario.
- **Frecuencia:** Cada vez que un usuario está intentando acceder a funcionalidades del sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. El sistema debe tener definidos los roles y sus permisos.
- **Descripción:** 1. Al navegar el sistema, el usuario intenta acceder a un módulo o ejecutar una operación. 2. El sistema verifica el rol del usuario activo. 3. Si el rol tiene permiso para la acción, el sistema la permite [Excepción 1]. 4. Si el rol no tiene permiso, el sistema oculta o deshabilita la opción correspondiente.
- **Excepciones:** Excepción 1: Si un usuario sin rol de administrador intenta acceder a un módulo restringido, el sistema no muestra la opción o muestra un mensaje de acceso denegado.
- **Postcondición:** El acceso a módulos y operaciones queda restringido según el rol asignado al usuario.
- **Dependencias:** CU-18.1 a CU-18.4 (corte). CU-34. CU-31, CU-40, CU-42, CU-45, CU-47, CU-52 y CU-54: Informes del sistema. CU-57.1 a CU-57.3 (usuario). CU-57.4: Autenticando usuario.

## Exportación y migración (RF-059, RF-060)

### CU-59: Exportando datos y listas
- **Actores:** Administrador.
- **Resumen:** Permite exportar listados de registros del sistema en formato PDF o Excel.
- **Frecuencia:** Cada vez que se está requiriendo obtener información del sistema en un formato externo para compartir, analizar o respaldar.
- **Precondiciones:** 1. El usuario debe estar autenticado. 2. Debe existir al menos un registro en el listado a exportar.
- **Descripción:** 1. El usuario accede al listado que desea exportar. 2. Selecciona la opción 'Exportar'. 3. Elige el formato: PDF o Excel. 4. El sistema genera el archivo con el contenido completo del listado filtrado visible en pantalla [Excepción 1 y 2]. 5. El archivo queda disponible para descarga o impresión.
- **Excepciones:** Excepción 1: Si el listado está vacío, el sistema informa que no hay datos para exportar. Excepción 2: Si ocurre un error en la generación, el sistema muestra el mensaje de error correspondiente.
- **Postcondición:** El archivo exportado está disponible en el formato seleccionado con los datos listados.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido). CU-21: Ingresando productos a bodega desde guía de cortes. CU-34. CU-31, CU-40, CU-42, CU-45, CU-47, CU-52 y CU-54: Informes del sistema.

### CU-60: Traspasando información desde el sistema original
- **Actores:** Administrador.
- **Resumen:** Permite migrar la información existente en el sistema legacy al nuevo sistema, preservando la integridad de los datos.
- **Frecuencia:** Cada vez que se está requiriendo migrar información desde el sistema original al nuevo sistema.
- **Precondiciones:** 1. El usuario debe estar autenticado con rol de Administrador. 2. El sistema original debe estar disponible o sus datos exportados en un formato compatible.
- **Descripción:** 1. El usuario accede a Configuración > Migración de datos. 2. Selecciona el tipo de datos a importar (clientes, productos, pedidos históricos, etc.). 3. Carga el archivo o señala la fuente de datos del sistema original. 4. El sistema valida la estructura y consistencia de los datos [Excepción 1]. 5. El sistema muestra un resumen de registros a importar y los posibles conflictos [Excepción 2]. 6. El usuario confirma la importación. 7. El sistema ejecuta la migración y reporta resultados [Excepción 3].
- **Excepciones:** Excepción 1: Si el formato del archivo no es compatible, el sistema informa y cancela. Excepción 2: Si existen conflictos de código duplicado, el sistema lista los conflictos y permite al usuario decidir si sobreescribir o ignorar. Excepción 3: Si la migración falla parcialmente, el sistema revierte los cambios parciales para mantener la integridad.
- **Postcondición:** Los datos migrados quedan disponibles en el nuevo sistema. Se genera un reporte de migración con los resultados.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido). CU-21. CU-34. CU-31, CU-40, CU-42, CU-45, CU-47, CU-52 y CU-54: Informes del sistema.

### CU-60.1: Validando datos antes de la migración
- **Actores:** Sistema.
- **Resumen:** Subproceso que valida la estructura y consistencia de los datos a importar antes de ejecutar la migración al nuevo sistema.
- **Frecuencia:** Cada vez que se está requiriendo preparar datos para el proceso de migración.
- **Precondiciones:** 1. El archivo de datos debe haber sido cargado en el sistema. 2. El sistema debe tener acceso al formato esperado de los datos.
- **Descripción:** 1. El sistema lee el archivo de datos. 2. Verifica la estructura de cada tipo de registro. 3. Detecta campos obligatorios faltantes, formatos inválidos y códigos duplicados [Excepción 1]. 4. Genera un reporte de errores y advertencias. 5. Si hay errores críticos, cancela la importación e informa al usuario [Excepción 2]. 6. Si solo hay advertencias, permite continuar con la confirmación del usuario.
- **Excepciones:** Excepción 1: Si el formato del archivo no coincide con ningún formato compatible, el sistema cancela inmediatamente. Excepción 2: Si hay más de un 20% de registros con errores, el sistema recomienda revisar el archivo antes de continuar.
- **Postcondición:** El sistema genera un reporte de validación indicando registros válidos, advertencias y errores críticos.
- **Dependencias:** CU-01.1: Registrando cliente. CU-22.1: Registrando pedido. CU-22.2 a CU-22.4 (pedido). CU-21. CU-34. CU-60: Traspasando información desde el sistema original.
