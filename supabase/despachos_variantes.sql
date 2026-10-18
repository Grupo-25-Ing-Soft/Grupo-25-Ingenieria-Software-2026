-- =====================================================================
-- Despachos con inventario por variante (CRUD de despachos.html).
--
-- incremento3_despachos.sql buscaba el stock por inventario.id_producto,
-- pero la tabla inventario de Supabase ahora se identifica por id_variante
-- (id_producto ya no existe), así que registrar_despacho fallaba con
-- 'column "id_producto" does not exist'. Este script reemplaza solo las dos
-- funciones; no toca tablas ni datos.
--
-- Los estados de pedido siguen el glosario del Documento 0 (tt): un pedido
-- despachado, pagado, anulado o finalizado ya no se despacha, y al anular su
-- despacho vuelve a 'pendiente'. Los mensajes de error nombran el producto y
-- la bodega en vez de ids internos (RNF-006).
--
-- Se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

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
  if v_pedido.estado in ('despachado', 'pagado', 'anulado', 'finalizado') then
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
    where id_factura = p_id_factura and id_pedido = p_id_pedido and estado <> 'anulada'
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

commit;
