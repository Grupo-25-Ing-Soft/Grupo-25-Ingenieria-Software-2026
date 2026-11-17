-- =====================================================================
-- Incremento 4: cantidades de los cortes.
--
-- En la base real, cortes.cantidad pasó a llamarse cantidad_producto y se agregó
-- cantidad_material. El cambio se hizo directo en Supabase, sin script, y además se
-- perdió la vista v_productos_en_proceso (RF-054), que dependía de esa columna: la
-- pantalla Productos en proceso no funciona hasta recrearla.
--
-- Este script deja escrito ese cambio y recrea la vista. En la base real no renombra ni
-- agrega nada, porque las columnas ya existen. La vista conserva el nombre «cantidad»
-- para el informe y ya no une productos.color ni productos.talla: un corte no tiene color
-- ni talla (se eligen al ingresarlo a bodega, CU-21).
--
-- Es idempotente y se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

do $$
begin
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'cortes' and column_name = 'cantidad')
     and not exists (select 1 from information_schema.columns
                      where table_schema = 'public' and table_name = 'cortes' and column_name = 'cantidad_producto') then
    alter table public.cortes rename column cantidad to cantidad_producto;
  end if;
end $$;

-- Tipo confirmado en la base real (integer not null para cantidad_producto, bigint para esta).
alter table public.cortes add column if not exists cantidad_material bigint;

-- RF-054: productos en proceso = cortes aún no ingresados a bodega.
drop view if exists public.v_productos_en_proceso;
create view public.v_productos_en_proceso
with (security_invoker = true) as
select co.id_corte,
       co.fecha_corte,
       co.cortador,
       co.material_usado,
       co.cantidad_producto as cantidad,
       co.observaciones,
       co.producto_asociado as id_producto,
       pr.descripcion       as producto,
       co.id_pedido,
       p.numero_pedido,
       c.nombre             as cliente,
       (current_date - co.fecha_corte) as dias_en_proceso
  from cortes co
  left join productos pr on pr.id_producto = co.producto_asociado
  left join pedidos p    on p.id_pedido = co.id_pedido
  left join clientes c   on c.id_cliente = p.cliente_asociado
 where co.estado = 'pendiente';

commit;

-- Comprobación (es lo que muestra el SQL Editor): las columnas de cantidad de cortes, con
-- su tipo, y cuántas guías hay en proceso.
select column_name as columna, data_type as tipo, is_nullable as admite_vacio,
       (select count(*) from public.v_productos_en_proceso) as guias_en_proceso
  from information_schema.columns
 where table_schema = 'public' and table_name = 'cortes' and column_name like 'cantidad%'
 order by 1;
