# Base de datos

Scripts SQL de la base PostgreSQL del sistema (alojada en Supabase).

- `DDL/` (lenguaje de definición de datos): crean y modifican la estructura. Tablas, columnas,
  restricciones, índices, vistas, funciones, triggers y políticas de acceso.
- `DML/` (lenguaje de manipulación de datos): insertan y borran datos. Datos iniciales y datos de prueba.

## Cómo crear la base desde cero

En el SQL Editor de Supabase, cada archivo completo y en este orden:

1. Los 18 scripts de `DDL/`, por su número.
2. `DML/01_datos_iniciales.sql`.
3. Opcional, solo en bases de prueba: `DML/02_datos_prueba.sql`.

Los scripts posteriores reemplazan funciones y vistas de los anteriores. Sobre la base actual no
se vuelve a ejecutar uno antiguo.

## DDL

| Script | Qué define |
|---|---|
| `01_esquema_base.sql` | Tablas que existían antes de los scripts: bodegas, clientes, colores, tallas, vendedores, zona_venta, productos, producto_variantes, pedidos, detalle_pedidos, cortes y movimientos_inventario. |
| `02_inventario.sql` | Tabla inventario y su trigger de fecha. |
| `03_facturas.sql` | Tabla facturas. |
| `04_notas_credito.sql` | Tabla notas_credito. |
| `05_pagos.sql` | Tablas pagos y pago_facturas. |
| `06_parametros_sistema.sql` | Tabla parametros_sistema (configuración general). |
| `07_roles.sql` | Tablas usuarios, roles y rol_permisos. |
| `08_incremento3_despachos.sql` | Tablas despachos y detalle_despachos, y vistas de los informes. |
| `09_incremento3_ean.sql` | Códigos EAN: columnas, funciones y triggers. |
| `10_incremento4_campos_documento0.sql` | Campos del Documento 0 en clientes, variantes de producto y facturas; tabla variante_precios_lista. |
| `11_incremento4_feedback.sql` | Cambios del feedback en facturas, notas de crédito y pagos, con el cálculo del saldo. |
| `12_incremento4_despachos.sql` | Funciones registrar_despacho y anular_despacho; vistas v_pendientes_despacho y v_inventario_analisis. |
| `13_incremento4_inventario_variantes.sql` | Inventario por variante (color y talla) y sus funciones. |
| `14_incremento4_limpieza.sql` | Elimina funciones sin uso. Opcional. |
| `15_incremento4_ingreso_produccion.sql` | Función ingresar_guia_corte (ingreso de producción a bodega). |
| `16_incremento4_feedback_productos.sql` | EAN con el código del producto; tablas presets_talla y presets_talla_detalle. |
| `17_incremento4_cortes_cantidades.sql` | Cantidades de cortes y vista v_productos_en_proceso. |
| `18_incremento4_feedback_documentos.sql` | Facturas, estados y observaciones de pedidos, detalle de pedidos sin precio propio. |

Los scripts 08 en adelante son migraciones: junto con el cambio de estructura traen las sentencias
`UPDATE` que adaptan los datos ya existentes a ese cambio (por ejemplo, el nuevo nombre de un
estado). Van en el mismo archivo porque se aplican en una sola transacción con el cambio de estructura.

## DML

| Script | Qué hace |
|---|---|
| `01_datos_iniciales.sql` | Inserta la fila única de parametros_sistema. Obligatorio en una base nueva. |
| `02_datos_prueba.sql` | Inserta datos de prueba marcados con SEED: clientes, vendedores, productos, pedidos, despachos y una factura. Lo que debe mostrar cada informe está en `pruebas/seed_despachos.md`. |
| `03_borrar_datos_prueba.sql` | Borra los datos de prueba SEED. |

Los datos reales de la empresa no están en el repositorio.

## Cómo opera la aplicación sobre los datos

La aplicación no envía texto SQL: usa la librería de Supabase para Python, que traduce cada llamada
a la sentencia DML equivalente. Por ejemplo, en `realFlask.py`:

```python
supabase.table("colores").insert({"codigo_color": codigo, "descripcion": descripcion}).execute()
```

equivale a:

```sql
INSERT INTO colores (codigo_color, descripcion)
VALUES ('<codigo>', '<descripcion>');
```

| Llamada en Python | Sentencia SQL |
|---|---|
| `.select()` | `SELECT` |
| `.insert()` | `INSERT` |
| `.update()` | `UPDATE` |
| `.delete()` | `DELETE` |
| `.rpc("nombre")` | Llamada a una función definida en `DDL/` |
