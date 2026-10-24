-- =====================================================================
-- Incremento 4: despachos con inventario por variante.
--
-- Reúne lo que antes estaba en despachos_variantes.sql y
-- vista_pendientes_despacho.sql, y corrige v_inventario_analisis:
--
--   1. registrar_despacho y anular_despacho (como en despachos_variantes.sql,
--      que ya se ejecutó en Supabase). La tabla
--      inventario se identifica por id_variante: las versiones de
--      incremento3_despachos.sql usaban inventario.id_producto y fallaban.
--      Un pedido despachado, entregado o anulado ya no se despacha (antes la lista
--      decía 'pagado' y 'finalizado', que pedidos_estado_check no admite, y no
--      incluía 'entregado'); al anular su despacho vuelve a 'pendiente'. Los mensajes de error nombran el producto y
--      la bodega en vez de ids internos (RNF-006). La factura opcional se valida
--      con facturas.pedido_asociado (incremento4_feedback.sql).
--
--   2. v_pendientes_despacho (la usan despachos() y verDetalle()). La versión
--      que tenía Supabase (exportada el 21/10/2026 con pg_get_viewdef) buscaba el
--      stock con producto_variantes.id_producto = inventario.id_variante (un id de
--      producto contra un id de variante) y no excluía los pedidos anulados.
--
--   3. v_inventario_analisis (RF-053). Tenía el mismo error: unía
--      productos.id_producto = inventario.id_variante y comparaba las unidades
--      pendientes por id_producto contra inventario.id_variante.
--
-- Las dos vistas conservan sus columnas (nombres, tipos y orden), así que la app
-- no cambia; v_inventario_analisis agrega id_variante al final. Se mantienen
-- las opciones que tuviera cada vista (por ejemplo security_invoker).
--
-- Se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada. Volver
-- a ejecutarlo no cambia nada.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- 1. Funciones de despacho
-- ---------------------------------------------------------------------
-- Registra un despacho completo: valida cantidades pendientes y stock,
-- descuenta inventario (queda en movimientos_inventario como 'despacho')
-- y marca el pedido como 'despachado' cuando no le queda nada pendiente.
--
-- p_lineas: [{"id_detalle_pedido": 1, "cantidad": 5, "descuento": 10}, ...]
--   "descuento" es opcional; por defecto se usan los descuentos del cliente
--   aplicados en cascada.
create or replace function public.registrar_despacho(
  p_id_pedido    bigint,
  p_id_bodega    bigint,
  p_lineas       jsonb,
  p_id_factura   bigint default null,
  p_via_despacho text   default null,
  p_observacion  text   default null,
  p_usuario      text   default 'Admin'
) returns bigint
language plpgsql
set search_path to 'public'
as $$
declare
  v_pedido      pedidos%rowtype;
  v_desc_client numeric(5,2);
  v_id_despacho bigint;
  v_guia        text;
  v_linea       jsonb;
  v_detalle     record;
  v_cantidad    integer;
  v_pendiente   integer;
  v_stock       integer;
  v_restante    integer;
  v_fila        record;
  v_descuento   integer;
  v_bodega      text;
begin
  select * into v_pedido from pedidos where id_pedido = p_id_pedido for update;
  if not found then
    raise exception 'No existe el pedido %', p_id_pedido;
  end if;
  if v_pedido.estado in ('despachado', 'entregado', 'anulado') then
    raise exception 'El pedido % está %, no se puede despachar', v_pedido.numero_pedido, v_pedido.estado;
  end if;
  select descripcion into v_bodega from bodegas where id_bodega = p_id_bodega;
  if not found then
    raise exception 'La bodega seleccionada no existe';
  end if;

  if p_lineas is null or jsonb_typeof(p_lineas) <> 'array' or jsonb_array_length(p_lineas) = 0 then
    raise exception 'El despacho debe tener al menos una línea';
  end if;

  if p_id_factura is not null and not exists (
    select 1 from facturas
    where id_factura = p_id_factura and pedido_asociado = p_id_pedido and estado <> 'anulada'
  ) then
    raise exception 'La factura % no corresponde al pedido % o está anulada', p_id_factura, v_pedido.numero_pedido;
  end if;

  select round(100 * (1 - (1 - coalesce(descuento_1, 0) / 100)
                         * (1 - coalesce(descuento_2, 0) / 100)
                         * (1 - coalesce(descuento_3, 0) / 100)), 2)
    into v_desc_client
    from clientes where id_cliente = v_pedido.cliente_asociado;

  insert into despachos (id_pedido, id_factura, id_bodega, via_despacho, observacion, usuario_creacion)
  values (p_id_pedido, p_id_factura, p_id_bodega, p_via_despacho, p_observacion, p_usuario)
  returning id_despacho, numero_guia into v_id_despacho, v_guia;

  perform set_config('app.tipo_movimiento', 'despacho', true);
  perform set_config('app.observacion', 'Despacho ' || v_guia, true);

  for v_linea in select * from jsonb_array_elements(p_lineas) loop
    v_cantidad := (v_linea ->> 'cantidad')::integer;
    if v_cantidad is null or v_cantidad <= 0 then
      raise exception 'Cantidad inválida en la línea %', v_linea;
    end if;

    select d.id_detalle_pedido, d.id_pedido, d.cantidad, d.cantidad_anulada, d.precio_unitario, d.id_variante,
           coalesce(pv.descripcion, 'variante ' || d.id_variante) as producto
      into v_detalle
      from detalle_pedidos d
      left join producto_variantes pv on pv.id_variante = d.id_variante
     where d.id_detalle_pedido = (v_linea ->> 'id_detalle_pedido')::bigint
       for update of d;
    if not found or v_detalle.id_pedido <> p_id_pedido then
      raise exception 'Uno de los productos indicados no pertenece al pedido %', v_pedido.numero_pedido;
    end if;

    select v_detalle.cantidad - v_detalle.cantidad_anulada - coalesce(sum(dd.cantidad), 0)
      into v_pendiente
      from detalle_despachos dd
      join despachos de on de.id_despacho = dd.id_despacho
     where dd.id_detalle_pedido = v_detalle.id_detalle_pedido and de.estado = 'emitido';
    if v_cantidad > v_pendiente then
      raise exception 'Del producto "%" quedan % unidades pendientes y se intentan despachar %',
        v_detalle.producto, v_pendiente, v_cantidad;
    end if;

    -- Una variante puede tener más de una fila en la bodega; se suma todo su stock.
    select coalesce(sum(cantidad), 0) into v_stock
      from inventario
     where id_bodega = p_id_bodega and id_variante = v_detalle.id_variante;
    if v_stock < v_cantidad then
      raise exception 'No hay stock suficiente de "%" en la bodega % (hay %, se piden %)',
        v_detalle.producto, v_bodega, v_stock, v_cantidad;
    end if;

    -- Descuenta fila por fila hasta completar la cantidad.
    v_restante := v_cantidad;
    for v_fila in
      select id_inventario, cantidad from inventario
       where id_bodega = p_id_bodega and id_variante = v_detalle.id_variante and cantidad > 0
       order by id_inventario
         for update
    loop
      exit when v_restante = 0;
      v_descuento := least(v_fila.cantidad, v_restante);
      update inventario
         set cantidad = cantidad - v_descuento, usuario_actualizacion = p_usuario
       where id_inventario = v_fila.id_inventario;
      v_restante := v_restante - v_descuento;
    end loop;

    insert into detalle_despachos (id_despacho, id_detalle_pedido, cantidad, precio_unitario, descuento_porcentaje)
    values (v_id_despacho, v_detalle.id_detalle_pedido, v_cantidad, v_detalle.precio_unitario,
            coalesce((v_linea ->> 'descuento')::numeric, v_desc_client, 0));
  end loop;

  perform set_config('app.tipo_movimiento', '', true);
  perform set_config('app.observacion', '', true);

  if not exists (
    select 1 from detalle_pedidos d
     where d.id_pedido = p_id_pedido
       and d.cantidad - d.cantidad_anulada > coalesce((
             select sum(dd.cantidad) from detalle_despachos dd
               join despachos de on de.id_despacho = dd.id_despacho
              where dd.id_detalle_pedido = d.id_detalle_pedido and de.estado = 'emitido'), 0)
  ) then
    update pedidos set estado = 'despachado' where id_pedido = p_id_pedido;
  end if;

  return v_id_despacho;
end $$;

-- Anula un despacho y devuelve las unidades a la bodega de origen.
-- Si el pedido había quedado 'despachado', vuelve a 'pendiente'.
create or replace function public.anular_despacho(
  p_id_despacho bigint,
  p_motivo      text,
  p_usuario     text default 'Admin'
) returns void
language plpgsql
set search_path to 'public'
as $$
declare
  v_despacho despachos%rowtype;
  v_linea    record;
  v_id_inv   bigint;
begin
  select * into v_despacho from despachos where id_despacho = p_id_despacho for update;
  if not found then
    raise exception 'No existe el despacho %', p_id_despacho;
  end if;
  if v_despacho.estado = 'anulado' then
    raise exception 'El despacho % ya está anulado', v_despacho.numero_guia;
  end if;
  if coalesce(trim(p_motivo), '') = '' then
    raise exception 'Debe indicar el motivo de la anulación';
  end if;

  perform set_config('app.tipo_movimiento', 'anulacion_despacho', true);
  perform set_config('app.observacion', 'Anulación despacho ' || v_despacho.numero_guia, true);

  for v_linea in
    select dd.cantidad, pv.id_variante, pv.id_talla, pv.id_color
      from detalle_despachos dd
      join detalle_pedidos d on d.id_detalle_pedido = dd.id_detalle_pedido
      join producto_variantes pv on pv.id_variante = d.id_variante
     where dd.id_despacho = p_id_despacho
  loop
    select id_inventario into v_id_inv
      from inventario
     where id_bodega = v_despacho.id_bodega and id_variante = v_linea.id_variante
     order by id_inventario
     limit 1
       for update;
    if found then
      update inventario
         set cantidad = cantidad + v_linea.cantidad, usuario_actualizacion = p_usuario
       where id_inventario = v_id_inv;
    else
      insert into inventario (id_bodega, id_variante, id_talla, id_color, cantidad, usuario_actualizacion)
      values (v_despacho.id_bodega, v_linea.id_variante, v_linea.id_talla, v_linea.id_color, v_linea.cantidad, p_usuario);
    end if;
  end loop;

  perform set_config('app.tipo_movimiento', '', true);
  perform set_config('app.observacion', '', true);

  update despachos
     set estado = 'anulado', motivo_anulacion = p_motivo, fecha_anulacion = now()
   where id_despacho = p_id_despacho;

  update pedidos set estado = 'pendiente'
   where id_pedido = v_despacho.id_pedido and estado = 'despachado';
end $$;

-- ---------------------------------------------------------------------
-- 2 y 3. Vistas. create or replace view deja la vista sin opciones: se guardan
-- antes y se restauran después. to_regclass da null si la vista aún no existe.
-- ---------------------------------------------------------------------
create temp table opciones_vistas on commit drop as
  select c.relname, c.reloptions
    from pg_class c
   where c.oid in (to_regclass('public.v_pendientes_despacho'), to_regclass('public.v_inventario_analisis'));

-- 2. Líneas de pedidos no anulados con unidades pendientes de despacho y el stock
-- de su variante en todas las bodegas, con el mismo criterio que
-- registrar_despacho (suma por id_variante). stock_bodega conserva su nombre por
-- compatibilidad, pero es el total de todas las bodegas.
create or replace view public.v_pendientes_despacho as
select p.id_pedido,
       p.numero_pedido,
       p.fecha_pedido,
       p.estado            as estado_pedido,
       c.id_cliente,
       c.nombre            as nombre_cliente,
       v.id_vendedor,
       v.nombre            as nombre_vendedor,
       dp.id_detalle_pedido,
       dp.id_variante,
       dp.cantidad         as cantidad_pedida,
       dp.cantidad_anulada,
       coalesce(desp.total_despachado, 0::bigint) as cantidad_despachada,
       dp.cantidad - dp.cantidad_anulada - coalesce(desp.total_despachado, 0::bigint) as cantidad_pendiente,
       coalesce(inv.stock_disponible, 0::bigint)  as stock_bodega
  from pedidos p
  join detalle_pedidos dp on p.id_pedido = dp.id_pedido
  left join clientes c    on p.cliente_asociado = c.id_cliente
  left join vendedores v  on p.vendedor_asociado = v.id_vendedor
  left join (
    select dd.id_detalle_pedido, sum(dd.cantidad) as total_despachado
      from detalle_despachos dd
      join despachos d on dd.id_despacho = d.id_despacho
     where d.estado = 'emitido'::text
     group by dd.id_detalle_pedido
  ) desp on dp.id_detalle_pedido = desp.id_detalle_pedido
  left join (
    select i.id_variante, sum(i.cantidad) as stock_disponible
      from inventario i
     group by i.id_variante
  ) inv on dp.id_variante = inv.id_variante
 where p.estado <> 'anulado'
   and (dp.cantidad - dp.cantidad_anulada - coalesce(desp.total_despachado, 0::bigint)) > 0;

-- 3. Stock, defectuosos y unidades comprometidas en pedidos de cada fila de
-- inventario. id_producto es el producto de la variante (antes era el id de la
-- variante); unidades_comprometidas es lo pendiente de esa variante en todos los
-- pedidos, sin distinguir bodega.
create or replace view public.v_inventario_analisis as
select i.id_inventario,
       i.id_bodega,
       b.descripcion          as bodega,
       pv.id_producto,
       pr.descripcion         as producto,
       i.id_talla,
       t.talla,
       i.id_color,
       co.descripcion         as color,
       i.cantidad             as stock_disponible,
       i.cantidad_defectuosa,
       coalesce(pp.pendiente, 0::numeric)              as unidades_comprometidas,
       coalesce(pp.pendiente, 0::numeric) > 0::numeric as asociado_a_pedidos,
       i.fecha_actualizacion,
       i.id_variante
  from inventario i
  left join producto_variantes pv on pv.id_variante = i.id_variante
  left join bodegas b    on b.id_bodega = i.id_bodega
  left join productos pr on pr.id_producto = pv.id_producto
  left join tallas t     on t.id_talla = i.id_talla
  left join colores co   on co.id_color = i.id_color
  left join (
    select id_variante, sum(cantidad_pendiente) as pendiente
      from v_detalle_pedido_pendiente
     where cantidad_pendiente > 0
     group by id_variante
  ) pp on pp.id_variante = i.id_variante;

do $$
declare
  v_fila record;
begin
  for v_fila in select relname, reloptions from opciones_vistas where reloptions is not null loop
    execute format('alter view public.%I set (%s)', v_fila.relname, array_to_string(v_fila.reloptions, ', '));
  end loop;
end $$;

commit;

-- Comprobación (es lo que muestra el SQL Editor): la columna "coincide" debe ser
-- true en todas las filas.
select 'v_pendientes_despacho' as vista, 'línea ' || vp.id_detalle_pedido as fila,
       vp.stock_bodega::text as valor_vista,
       coalesce((select sum(i.cantidad) from public.inventario i where i.id_variante = vp.id_variante), 0)::text as esperado,
       vp.stock_bodega = coalesce((select sum(i.cantidad) from public.inventario i where i.id_variante = vp.id_variante), 0) as coincide
  from public.v_pendientes_despacho vp
union all
select 'v_inventario_analisis', 'inventario ' || ia.id_inventario,
       ia.id_producto::text, pv.id_producto::text, ia.id_producto is not distinct from pv.id_producto
  from public.v_inventario_analisis ia
  left join public.producto_variantes pv on pv.id_variante = ia.id_variante
 order by 1, 2;
