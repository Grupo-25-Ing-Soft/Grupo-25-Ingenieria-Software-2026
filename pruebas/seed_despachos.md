# Datos de prueba de despachos (SEED)

Scripts:

- [seed_despachos.sql](seed_despachos.sql) inserta los datos. Primero borra los datos SEED anteriores, así que se puede ejecutar más de una vez.
- [borrar_seed_despachos.sql](borrar_seed_despachos.sql) los borra.

Requisito: haber ejecutado `supabase/incremento4_feedback_documentos.sql` antes.

Los datos van marcados así:

| Tabla | Marca |
|---|---|
| pedidos, clientes | `observaciones = 'SEED'` |
| despachos | `observacion = 'SEED'` |
| vendedores, productos, colores, bodegas | código `SEED-…` |
| tallas | nombre `SEED-…` |
| facturas | folio `990001`, del pedido `SEED-0001` |

Los despachos se insertan directo en las tablas, sin pasar por `registrar_despacho`. Por eso no mueven inventario y las variantes SEED tienen stock 0.

## Datos

**Clientes** (todos con lista de precios 1)

| Cliente | Descuentos | % en cascada | Vendedor asignado |
|---|---|---|---|
| SEED Comercial Norte | 10 | 10,00 % | Ana |
| SEED Tienda Sur | — | 0 % | Luis |
| SEED Boutique Centro | 5 y 5 | 9,75 % | Ana |

**Vendedores:** SEED Vendedora Ana y SEED Vendedor Luis, ambos con 5 % de comisión.

**Variantes (precio por talla y color)**

| Producto | Color | Talla | Precio |
|---|---|---|---|
| SEED Calzón clásico | SEED Negro | 9901 (SEED-S) | $2.000 |
| SEED Calzón clásico | SEED Negro | 9902 (SEED-M) | $2.000 |
| SEED Calzón clásico | SEED Blanco | 9903 (SEED-L) | $2.200 |
| SEED Sostén básico | SEED Negro | 9902 (SEED-M) | $5.000 |
| SEED Sostén básico | SEED Blanco | 9903 (SEED-L) | $5.500 |

Los informes muestran el número de talla (`tallas.talla`), no su nombre.

**Pedidos**

| Pedido | Fecha | Cliente | Vendedor | Estado | Líneas (pedido → despachado) | Caso |
|---|---|---|---|---|---|---|
| SEED-0001 | 10/07/2026 | Norte | Ana | despachado | Calzón Negro S 10 → 10 · Sostén Negro M 5 → 5 | Despachado completo, con factura |
| SEED-0002 | 05/08/2026 | Sur | Luis | pendiente | Calzón Negro M 20 → 15 · Sostén Blanco L 8 → 8 | Despachado en parte, en dos guías |
| SEED-0003 | 12/09/2026 | Centro | Ana | en_produccion | Calzón Blanco L 6 → 0 · Sostén Negro M 4 → 0 | Sin despachar |
| SEED-0004 | 02/10/2026 | Norte | Luis | listo_para_despacho | Calzón Negro S 5 → 0 · Calzón Blanco L 2 → 0 | Su única guía está anulada |

**Despachos**

| Guía | Fecha | Pedido | Factura | Estado | Líneas |
|---|---|---|---|---|---|
| SEED-GD-0001 | 15/07/2026 | SEED-0001 | 990001 | emitido | Calzón Negro S 10 · Sostén Negro M 5 (desc. 10 %) |
| SEED-GD-0002 | 20/08/2026 | SEED-0002 | — | emitido | Calzón Negro M 12 · Sostén Blanco L 8 |
| SEED-GD-0003 | 03/09/2026 | SEED-0002 | — | emitido | Calzón Negro M 3 |
| SEED-GD-0004 | 05/10/2026 | SEED-0004 | — | **anulado** | Calzón Negro S 5. No debe aparecer en ningún informe |

**Factura 990001** (pedido SEED-0001, emitida el 15/07/2026, razón social «SEED COMERCIAL NORTE LIMITADA»)

- Neto: $40.500. Es $45.000 menos el 10 % de descuento.
- Impuesto (19 %): $7.695.
- Total: $48.195.

## Resultado esperado de cada informe

Para ver solo los datos SEED, filtra por los clientes, vendedores o productos SEED. Sin filtros, estas cifras se suman a los datos reales.

### Productos despachados (RF-045/046)

Muestra 6 líneas de 3 guías: 38 unidades, por un neto de $114.500.

| Guía | Producto | Cant. | Precio | Desc. | Neto |
|---|---|---|---|---|---|
| SEED-GD-0003 | Calzón Negro 9902 | 3 | $2.000 | 0 % | $6.000 |
| SEED-GD-0002 | Calzón Negro 9902 | 12 | $2.000 | 0 % | $24.000 |
| SEED-GD-0002 | Sostén Blanco 9903 | 8 | $5.500 | 0 % | $44.000 |
| SEED-GD-0001 | Calzón Negro 9901 | 10 | $2.000 | 10 % | $18.000 |
| SEED-GD-0001 | Sostén Negro 9902 | 5 | $5.000 | 10 % | $22.500 |

- Con el filtro de factura 990001 aparece solo SEED-GD-0001: 15 unidades, $40.500.
- SEED-GD-0004 (anulada) no aparece.

### Pendientes de despacho (RF-042/043)

Muestra 22 unidades pendientes. El stock es 0 y lo cumplible también es 0.

| Pedido | Producto | Pedida | Despachada | Pendiente |
|---|---|---|---|---|
| SEED-0002 | Calzón Negro 9902 | 20 | 15 | 5 |
| SEED-0003 | Calzón Blanco 9903 | 6 | 0 | 6 |
| SEED-0003 | Sostén Negro 9902 | 4 | 0 | 4 |
| SEED-0004 | Calzón Negro 9901 | 5 | 0 | 5 |
| SEED-0004 | Calzón Blanco 9903 | 2 | 0 | 2 |

- SEED-0001 no aparece porque está completo.
- En SEED-0004, la guía anulada no descuenta unidades.

### Despachos por cliente y producto (RF-049)

| Cliente | Producto | Unidades | Guías | Neto |
|---|---|---|---|---|
| SEED Comercial Norte | Calzón Negro 9901 | 10 | 1 | $18.000 |
| SEED Comercial Norte | Sostén Negro 9902 | 5 | 1 | $22.500 |
| SEED Tienda Sur | Calzón Negro 9902 | 15 | 2 | $30.000 |
| SEED Tienda Sur | Sostén Blanco 9903 | 8 | 1 | $44.000 |

SEED Boutique Centro no aparece porque no tiene despachos.

### Despachos por vendedor y producto (RF-050)

El vendedor que cuenta es el del pedido, no el asignado al cliente.

| Vendedor | Producto | Unidades | Guías | Neto |
|---|---|---|---|---|
| SEED Vendedora Ana | Calzón Negro 9901 | 10 | 1 | $18.000 |
| SEED Vendedora Ana | Sostén Negro 9902 | 5 | 1 | $22.500 |
| SEED Vendedor Luis | Calzón Negro 9902 | 15 | 2 | $30.000 |
| SEED Vendedor Luis | Sostén Blanco 9903 | 8 | 1 | $44.000 |

Luis no suma nada por SEED-0004, porque su guía está anulada.

### Despachos según factura y cliente (RF-048)

Muestra 3 guías y aparece «2 sin factura».

| Fecha | Guía | Cliente | Pedido | Factura | Unidades | Neto |
|---|---|---|---|---|---|---|
| 03/09/2026 | SEED-GD-0003 | SEED Tienda Sur | SEED-0002 | — | 3 | $6.000 |
| 20/08/2026 | SEED-GD-0002 | SEED Tienda Sur | SEED-0002 | — | 20 | $68.000 |
| 15/07/2026 | SEED-GD-0001 | SEED Comercial Norte | SEED-0001 | 990001 | 15 | $40.500 |

### Pedidos vs despachos mensuales (RF-051)

Esta vista no tiene filtro por cliente, así que estas cifras **se suman** a las de los datos reales de cada mes. Sobre una base sin otros datos, se vería así:

| Mes | Pedidos | Unid. pedidas | Despachos | Unid. despachadas | % |
|---|---|---|---|---|---|
| 2026-07 | 1 | 15 | 1 | 15 | 100,0 |
| 2026-08 | 1 | 28 | 1 | 20 | 71,4 |
| 2026-09 | 1 | 10 | 1 | 3 | 30,0 |
| 2026-10 | 1 | 7 | 0 | 0 | 0,0 |

### Productos pedidos vs despachados (RF-044)

Total: 60 unidades pedidas, 38 despachadas y 22 pendientes.

| Producto | Pedidos | Pedida | Despachada | Pendiente | % |
|---|---|---|---|---|---|
| Calzón Blanco 9903 | 2 | 8 | 0 | 8 | 0,0 |
| Calzón Negro 9901 | 2 | 15 | 10 | 5 | 66,7 |
| Calzón Negro 9902 | 1 | 20 | 15 | 5 | 75,0 |
| Sostén Blanco 9903 | 1 | 8 | 8 | 0 | 100,0 |
| Sostén Negro 9902 | 2 | 9 | 5 | 4 | 55,6 |

### Ventas y descuentos (RF-047), por cliente

| Cliente | Bruto | Descuento | % | Neto | Comisión (5 %) |
|---|---|---|---|---|---|
| SEED Comercial Norte | $45.000 | $4.500 | 10,00 | $40.500 | $2.025 |
| SEED Tienda Sur | $74.000 | $0 | 0,00 | $74.000 | $3.700 |

### Pantalla de pedidos (montos calculados con el precio de cada variante)

Supone un impuesto de 19 % en Configuración.

| Pedido | Neto | Descuento | Impuesto | Total |
|---|---|---|---|---|
| SEED-0001 | $45.000 | −$4.500 | $7.695 | $48.195 (igual que la factura 990001) |
| SEED-0002 | $84.000 | −$0 | $15.960 | $99.960 |
| SEED-0003 | $33.200 | −$3.237 | $5.693 | $35.656 |
| SEED-0004 | $14.400 | −$1.440 | $2.462 | $15.422 |
