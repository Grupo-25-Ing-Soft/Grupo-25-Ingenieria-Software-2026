-- =====================================================================
-- Datos de prueba para los informes de despachos (Incremento 4).
--
-- Casos: pedido despachado completo, pedido despachado parcialmente (en dos guías),
-- pedido sin despachar, pedido con un despacho anulado, 3 clientes, 2 vendedores,
-- pedidos y despachos en julio, agosto, septiembre y octubre de 2026, 2 productos
-- en 5 variantes (tallas y colores) con precios distintos y un despacho asociado a
-- una factura. Lo que debe mostrar cada informe está en pruebas/seed_despachos.md.
--
-- Requisito: haber ejecutado supabase/incremento4_feedback_documentos.sql
-- (pedidos.observaciones; detalle_pedidos sin precio_unitario).
--
-- Marcas para identificar y borrar los datos (pruebas/borrar_seed_despachos.sql):
--   pedidos.observaciones = 'SEED', despachos.observacion = 'SEED',
--   clientes.observaciones = 'SEED', códigos 'SEED-…' en vendedores, productos,
--   colores, bodegas y nombre 'SEED-…' en tallas.
--
-- Idempotente: primero borra los datos SEED anteriores y después los vuelve a
-- insertar (los id cambian en cada ejecución). Los despachos se insertan directo en
-- despachos y detalle_despachos, sin registrar_despacho: no mueven inventario. Por eso
-- las variantes SEED no tienen stock.
--
-- No ejecutar contra la base de producción sin acordarlo con el equipo.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- 0. Borra los datos SEED anteriores (igual que borrar_seed_despachos.sql)
-- ---------------------------------------------------------------------
delete from public.detalle_despachos
 where id_despacho in (select id_despacho from public.despachos
                        where observacion = 'SEED'
                           or id_pedido in (select id_pedido from public.pedidos where observaciones = 'SEED'));
delete from public.despachos
 where observacion = 'SEED'
    or id_pedido in (select id_pedido from public.pedidos where observaciones = 'SEED');
delete from public.facturas
 where pedido_asociado in (select id_pedido from public.pedidos where observaciones = 'SEED');
delete from public.pedidos where observaciones = 'SEED';
delete from public.productos where codigo like 'SEED-%';
delete from public.colores where codigo_color like 'SEED-%';
delete from public.tallas where nombre like 'SEED-%';
delete from public.bodegas where codigo like 'SEED-%';
delete from public.clientes where observaciones = 'SEED';
delete from public.vendedores where codigo like 'SEED-%';

-- ---------------------------------------------------------------------
-- 1. Maestros
-- ---------------------------------------------------------------------
insert into public.vendedores (rut, digito_verificador, nombre, codigo, porcentaje_comision) values
  ('90000101', '0', 'SEED Vendedora Ana',  'SEED-V1', 5),
  ('90000102', '9', 'SEED Vendedor Luis',  'SEED-V2', 5);

-- Descuentos en cascada: Norte 10 %; Sur sin descuento; Centro 5 % y 5 % = 9,75 %.
insert into public.clientes (rut, digito_verificador, nombre, ciudad, lista_precios,
                             descuento_1, descuento_2, descuento_3, id_vendedor, observaciones) values
  ('90000001', '4', 'SEED Comercial Norte', 'Antofagasta', 1, 10, 0, 0,
   (select id_vendedor from public.vendedores where codigo = 'SEED-V1'), 'SEED'),
  ('90000002', '2', 'SEED Tienda Sur',      'Puerto Montt', 1, 0, 0, 0,
   (select id_vendedor from public.vendedores where codigo = 'SEED-V2'), 'SEED'),
  ('90000003', '0', 'SEED Boutique Centro', 'Santiago',     1, 5, 5, 0,
   (select id_vendedor from public.vendedores where codigo = 'SEED-V1'), 'SEED');

insert into public.bodegas (descripcion, codigo) values ('SEED Bodega central', 'SEED-B1');

insert into public.colores (descripcion, codigo_color) values
  ('SEED Negro',  'SEED-NE'),
  ('SEED Blanco', 'SEED-BL');

insert into public.tallas (talla, nombre) values
  (9901, 'SEED-S'),
  (9902, 'SEED-M'),
  (9903, 'SEED-L');

-- Código con letras: la variante queda sin EAN automático (fn_generar_ean devuelve null).
insert into public.productos (descripcion, abreviacion, codigo, precio) values
  ('SEED Calzón clásico', 'SEED CAL', 'SEED-P1', 2000),
  ('SEED Sostén básico',  'SEED SOS', 'SEED-P2', 5000);

-- Precio por talla y color: la talla L cuesta más que el precio base del producto.
insert into public.producto_variantes (id_producto, id_color, id_talla, descripcion, precio_venta)
select p.id_producto, c.id_color, t.id_talla, v.descripcion, v.precio
  from (values
    ('SEED-P1', 'SEED-NE', 'SEED-S', 'SEED Calzón clásico Negro S', 2000),
    ('SEED-P1', 'SEED-NE', 'SEED-M', 'SEED Calzón clásico Negro M', 2000),
    ('SEED-P1', 'SEED-BL', 'SEED-L', 'SEED Calzón clásico Blanco L', 2200),
    ('SEED-P2', 'SEED-NE', 'SEED-M', 'SEED Sostén básico Negro M',  5000),
    ('SEED-P2', 'SEED-BL', 'SEED-L', 'SEED Sostén básico Blanco L', 5500)
  ) as v (producto, color, talla, descripcion, precio)
  join public.productos p on p.codigo = v.producto
  join public.colores   c on c.codigo_color = v.color
  join public.tallas    t on t.nombre = v.talla;

-- ---------------------------------------------------------------------
-- 2. Pedidos y su detalle
-- ---------------------------------------------------------------------
insert into public.pedidos (numero_pedido, cliente_asociado, vendedor_asociado, fecha_pedido, fecha_entrega,
                            estado, observaciones)
select v.numero, c.id_cliente, ve.id_vendedor, v.fecha::date, v.entrega::date, v.estado, 'SEED'
  from (values
    ('SEED-0001', '90000001', 'SEED-V1', '2026-07-10', '2026-07-20', 'despachado'),          -- A: completo
    ('SEED-0002', '90000002', 'SEED-V2', '2026-08-05', '2026-08-25', 'pendiente'),           -- B: parcial
    ('SEED-0003', '90000003', 'SEED-V1', '2026-09-12', '2026-10-01', 'en_produccion'),       -- C: sin despachar
    ('SEED-0004', '90000001', 'SEED-V2', '2026-10-02', '2026-10-15', 'listo_para_despacho')  -- D: despacho anulado
  ) as v (numero, rut, vendedor, fecha, entrega, estado)
  join public.clientes   c  on c.rut = v.rut
  join public.vendedores ve on ve.codigo = v.vendedor;

insert into public.detalle_pedidos (id_pedido, id_variante, cantidad, cantidad_anulada, observacion)
select p.id_pedido, pv.id_variante, v.cantidad, 0, 'SEED'
  from (values
    ('SEED-0001', 'SEED Calzón clásico Negro S', 10),
    ('SEED-0001', 'SEED Sostén básico Negro M',   5),
    ('SEED-0002', 'SEED Calzón clásico Negro M', 20),
    ('SEED-0002', 'SEED Sostén básico Blanco L',  8),
    ('SEED-0003', 'SEED Calzón clásico Blanco L', 6),
    ('SEED-0003', 'SEED Sostén básico Negro M',   4),
    ('SEED-0004', 'SEED Calzón clásico Negro S',  5),
    ('SEED-0004', 'SEED Calzón clásico Blanco L', 2)
  ) as v (pedido, variante, cantidad)
  join public.pedidos p             on p.numero_pedido = v.pedido
  join public.producto_variantes pv on pv.descripcion = v.variante;

-- ---------------------------------------------------------------------
-- 3. Factura del pedido A (la que se asocia al despacho GD A)
--    Neto = (10 x 2.000 + 5 x 5.000) - 10 % = 40.500; impuesto 19 % = 7.695.
--    trg_factura_calcular_saldo recalcula saldo_pendiente y estado al insertar.
-- ---------------------------------------------------------------------
insert into public.facturas (folio, pedido_asociado, razon_social, fecha_emision, fecha_vencimiento,
                             monto_neto, monto_impuesto, monto_total, saldo_pendiente, estado, usuario_creacion)
select 990001, id_pedido, 'SEED COMERCIAL NORTE LIMITADA', '2026-07-15', '2026-08-14',
       40500, 7695, 48195, 48195, 'vigente', 'SEED'
  from public.pedidos where numero_pedido = 'SEED-0001';

-- ---------------------------------------------------------------------
-- 4. Despachos y su detalle (precio = precio de la variante; descuento = el del
--    cliente en cascada, como lo guarda registrar_despacho)
-- ---------------------------------------------------------------------
insert into public.despachos (numero_guia, fecha, id_pedido, id_factura, id_bodega, via_despacho,
                              observacion, estado, motivo_anulacion, fecha_anulacion, usuario_creacion)
select v.guia, v.fecha::date, p.id_pedido,
       case when v.con_factura then (select id_factura from public.facturas where folio = 990001) end,
       b.id_bodega, v.via, 'SEED', v.estado,
       case when v.estado = 'anulado' then 'SEED: guía con error' end,
       case when v.estado = 'anulado' then timestamptz '2026-10-06 10:00:00-03' end,
       'SEED'
  from (values
    ('SEED-GD-0001', '2026-07-15', 'SEED-0001', true,  'Starken',     'emitido'),  -- A completo, con factura
    ('SEED-GD-0002', '2026-08-20', 'SEED-0002', false, 'Chilexpress', 'emitido'),  -- B primera parte
    ('SEED-GD-0003', '2026-09-03', 'SEED-0002', false, 'Chilexpress', 'emitido'),  -- B segunda parte
    ('SEED-GD-0004', '2026-10-05', 'SEED-0004', false, 'Retiro',      'anulado')   -- D anulado (no cuenta)
  ) as v (guia, fecha, pedido, con_factura, via, estado)
  join public.pedidos p on p.numero_pedido = v.pedido
  join public.bodegas b on b.codigo = 'SEED-B1';

insert into public.detalle_despachos (id_despacho, id_detalle_pedido, cantidad, precio_unitario, descuento_porcentaje)
select d.id_despacho, dp.id_detalle_pedido, v.cantidad, pv.precio_venta, v.descuento
  from (values
    ('SEED-GD-0001', 'SEED-0001', 'SEED Calzón clásico Negro S', 10, 10.00),
    ('SEED-GD-0001', 'SEED-0001', 'SEED Sostén básico Negro M',   5, 10.00),
    ('SEED-GD-0002', 'SEED-0002', 'SEED Calzón clásico Negro M', 12,  0.00),
    ('SEED-GD-0002', 'SEED-0002', 'SEED Sostén básico Blanco L',  8,  0.00),
    ('SEED-GD-0003', 'SEED-0002', 'SEED Calzón clásico Negro M',  3,  0.00),
    ('SEED-GD-0004', 'SEED-0004', 'SEED Calzón clásico Negro S',  5, 10.00)
  ) as v (guia, pedido, variante, cantidad, descuento)
  join public.despachos d          on d.numero_guia = v.guia
  join public.pedidos p            on p.numero_pedido = v.pedido
  join public.producto_variantes pv on pv.descripcion = v.variante
  join public.detalle_pedidos dp   on dp.id_pedido = p.id_pedido and dp.id_variante = pv.id_variante;

commit;

-- Comprobación (es lo que muestra el SQL Editor): lo pedido, despachado y pendiente
-- de cada línea SEED. Debe coincidir con la tabla de pruebas/seed_despachos.md.
select numero_pedido, cliente, vendedor, producto, color, talla,
       cantidad_pedida, cantidad_despachada, cantidad_pendiente
  from public.v_detalle_pedido_pendiente
 where numero_pedido like 'SEED-%'
 order by numero_pedido, producto, color, talla;
