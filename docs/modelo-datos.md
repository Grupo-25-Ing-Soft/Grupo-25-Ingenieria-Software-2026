# Modelo de datos

Base de datos relacional PostgreSQL alojada en Supabase. La aplicación no ejecuta SQL directo:
usa el cliente Python de Supabase (`supabase.table("colores").insert({...}).execute()`); ver el
archivo `Instrucciones SQL` en la raíz del repo.

**Fuente de verdad:** los scripts de `supabase/` y la base real. El modelo de abajo viene de los
documentos (3FN del Incremento 2 más los cambios del Incremento 3) y puede estar atrasado
respecto del código. Si no coinciden, manda el SQL.

## Scripts en `supabase/`

| Archivo | Contenido |
| --- | --- |
| `facturas.sql` | Tabla `facturas` |
| `notas_credito.sql` | Tabla `notas_credito` |
| `pagos.sql` | Tablas `pagos` y `pago_facturas` |
| `inventario.sql` | Tabla `inventario` |
| `parametros_sistema.sql` | Tabla `parametros_sistema` |
| `incremento3_despachos.sql` | Tablas `despachos` y `detalle_despachos`; columnas nuevas del Incremento 3; funciones `registrar_despacho`, `anular_despacho`, `registrar_defectuosos`, `obtener_variante`; vistas `v_pendientes_despacho`, `v_despachos_detalle`, `v_detalle_pedido_pendiente`, `v_pedidos_despachos_mensual`, `v_produccion_terminada`, `v_inventario_analisis`, `v_productos_en_proceso` |
| `incremento3_ean.sql` | Columnas para el formato EAN propio; funciones `fn_ean`, `fn_generar_ean`, `fn_variante_ean`, `fn_regenerar_ean_maestro`; vista `v_codigos_ean` |

Las tablas maestras del Incremento 1 (clientes, colores, tallas, etc.) se crearon directamente
en Supabase y no tienen script en el repo.

## Modelo relacional (3FN)

Notación: **clave primaria** en negrita, `#` marca clave foránea. Fuente: Incremento 2 (3FN),
con las columnas agregadas en el Incremento 3 señaladas con *(Inc. 3)*.

### Maestros
- colores(**id_color**, descripcion, codigo_color, codigo_ean *(Inc. 3)*)
- tallas(**id_talla**, talla, test, nombre *(Inc. 3)*, codigo_ean *(Inc. 3)*)
- zona_venta(**id_zona_venta**, descripcion)
- bodegas(**id_bodega**, descripcion)
- vendedores(**id_vendedor**, rut, nombre, digito_verificador, porcentaje_comision)
- clientes(**id_cliente**, rut, nombre, correo, telefono, giro, direccion, digito_verificador, abreviacion, ciudad, comuna, condiciones_venta, via_despacho, porcentaje_comision, porcentaje_cobranza, observaciones, #id_zona_venta, descuento_1 *(Inc. 3)*, descuento_2 *(Inc. 3)*, descuento_3 *(Inc. 3)*)
- productos(**id_producto**, descripcion, abreviacion, precio, #color, #talla, codigo *(Inc. 3: código del artículo impreso en la etiqueta)*, codigo_ean *(Inc. 3)*)
- producto_variantes(**id_variante**, #id_producto, #id_color, #id_talla, codigo_ean, precio_venta, activo, creado_en, descripcion, ean_manual *(Inc. 3: booleano; si es verdadero, el código EAN de la variante se conserva aunque cambien los códigos de producto, color o talla)*)
- codigos_EAN(**id_codigo_EAN**, #producto_asociado, temp_codigo)

### Usuarios y configuración
- tipo_usuario(**id_tipo_usuario**, tipo_usuario)
- usuarios(**id_usuario**, #tipo_usuario, auth_user_id, nombre, correo, activo, creado_en)
- parametros_sistema(**id**, razon_social, rut, digito_verificador, giro, direccion, telefono, correo, moneda, formato_moneda, porcentaje_impuesto, logotipo, fecha_actualizacion, usuario_actualizacion, ean_prefijo *(Inc. 3)*, ean_digitos_producto *(Inc. 3)*, ean_digitos_color *(Inc. 3)*, ean_digitos_talla *(Inc. 3)*)

### Producción e inventario
- cortes(**id_corte**, fecha_corte, cantidad, observaciones, material, cortador, #producto_asociado, estado, fecha_ingreso, #id_bodega_ingreso, #id_pedido *(Inc. 3, opcional)*)
- inventario(**id_inventario**, #id_bodega, #id_producto, #id_talla, #id_color, cantidad, cantidad_defectuosa *(Inc. 3)*, fecha_actualizacion, usuario_actualizacion)
- movimientos_inventario(**id_movimiento**, fecha, tipo, #id_producto, cantidad, #id_corte, observacion, #id_bodega, #id_talla, #id_color, stock_anterior, usuario). Valores de `tipo` agregados en el Inc. 3: `despacho`, `anulacion_despacho`, `defecto`.

### Pedidos, facturación y cobranza
- pedidos(**id_pedido**, #cliente_asociado, fecha_pedido, fecha_entrega, #vendedor_asociado, numero_pedido, estado, motivo_anulacion, fecha_anulacion, usuario_anulacion)
- detalle_pedidos(**id_detalle_pedido**, #id_pedido, #id_variante, cantidad, precio_unitario, observacion, cantidad_anulada). Una misma variante no se repite dentro de un pedido.
- facturas(**id_factura**, numero_factura, fecha, detalle, #id_pedido, #id_cliente, forma_pago, neto, iva, saldo, estado, creado_en)
- notas_credito(**id_nota**, numero_nota, fecha, #id_factura, #id_bodega, lista_precios, total_descuento, total_neto, iva_porcentaje, tipo, observacion, creado_en, motivo, estado)
- notas_credito_descuentos(**#id_nota**, **orden**, porcentaje)
- pagos(**id_pago**, fecha_pago, monto, medio_pago, referencia, observacion, created_at, #cliente_asociado, estado, usuario_creacion, motivo_anulacion)
- pago_facturas(**id_pago_factura**, #id_pago, #id_factura, monto_aplicado, fecha_creacion)

### Despachos (Incremento 3)
- despachos(**id_despacho**, numero_guia, fecha, #id_pedido, #id_factura, #id_bodega, via_despacho, observacion, estado, motivo_anulacion, fecha_anulacion, usuario_creacion, creado_en). El cliente y el vendedor se obtienen del pedido.
- detalle_despachos(**id_detalle_despacho**, #id_despacho, #id_detalle_pedido, cantidad, precio_unitario, descuento_porcentaje)

### Sin uso
- ventas(**id_venta**, numero_venta, #id_cliente, #id_vendedor, fecha, total, estado)
- detalle_ventas(**id_detalle**, #id_venta, #id_variante, cantidad, precio_unitario)

Estas dos tablas existen desde el Incremento 1 pero no se usan (ver
[estado-y-planificacion.md](estado-y-planificacion.md)).

## Pendientes de modelo (Incremento 4)

- Eliminar la redundancia entre `productos` y `producto_variantes`.
- Precios por talla y color además de por producto (CU-13.5).
- Migrar de Supabase a una base de datos local (RNF-011).
