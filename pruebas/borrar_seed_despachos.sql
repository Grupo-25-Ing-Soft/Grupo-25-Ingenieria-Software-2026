-- =====================================================================
-- Borra los datos de prueba de despachos que inserta pruebas/seed_despachos.sql.
--
-- Solo toca filas marcadas como SEED:
--   clientes.observaciones = 'SEED', vendedores.codigo 'SEED-…', productos.codigo
--   'SEED-…', colores.codigo_color 'SEED-…', tallas.nombre 'SEED-…', bodegas.codigo
--   'SEED-…', pedidos.observaciones = 'SEED', despachos.observacion = 'SEED' y las
--   facturas de esos pedidos.
-- Es idempotente: si no hay datos SEED, no borra nada. Se ejecuta completo en el SQL
-- Editor; si algo falla, no se aplica nada.
-- (El mismo bloque está al inicio de seed_despachos.sql.)
-- =====================================================================
begin;

delete from public.detalle_despachos
 where id_despacho in (select id_despacho from public.despachos
                        where observacion = 'SEED'
                           or id_pedido in (select id_pedido from public.pedidos where observaciones = 'SEED'));
delete from public.despachos
 where observacion = 'SEED'
    or id_pedido in (select id_pedido from public.pedidos where observaciones = 'SEED');
delete from public.facturas
 where pedido_asociado in (select id_pedido from public.pedidos where observaciones = 'SEED');
-- detalle_pedidos se borra en cascada con su pedido.
delete from public.pedidos where observaciones = 'SEED';
-- producto_variantes se borra en cascada con su producto.
delete from public.productos where codigo like 'SEED-%';
delete from public.colores where codigo_color like 'SEED-%';
delete from public.tallas where nombre like 'SEED-%';
delete from public.bodegas where codigo like 'SEED-%';
delete from public.clientes where observaciones = 'SEED';
delete from public.vendedores where codigo like 'SEED-%';

commit;

-- Comprobación (es lo que muestra el SQL Editor): todo debe quedar en 0.
select 'pedidos' as tabla, count(*) as filas_seed from public.pedidos where observaciones = 'SEED'
union all select 'despachos', count(*) from public.despachos where observacion = 'SEED'
union all select 'clientes', count(*) from public.clientes where observaciones = 'SEED'
union all select 'productos', count(*) from public.productos where codigo like 'SEED-%';
