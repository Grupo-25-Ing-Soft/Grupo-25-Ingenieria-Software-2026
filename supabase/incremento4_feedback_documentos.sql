-- =====================================================================
-- Incremento 4 (feedback del cliente): facturas, pedidos y detalle de pedidos.
--
--   1. FACTURAS: se eliminan los datos que ya se obtienen por FK.
--      * Las copias antiguas que llenaba trg_facturas_columnas_antiguas
--        (numero_factura, id_pedido, id_cliente, fecha, neto, iva, total, saldo,
--        creado_en, rut) y el trigger con su función.
--      * direccion, giro, codigo, detalle y forma_pago (la app no las usa;
--        dirección y giro son del cliente).
--      * cliente_asociado: el cliente es el del pedido (pedido_asociado ->
--        pedidos.cliente_asociado). Nombre y RUT se muestran desde clientes.
--      Se conserva razon_social: ya no la copia el trigger, se ingresa al crear o
--      editar la factura (en una base nueva se crea la columna).
--      Se conservan monto_neto, monto_impuesto y monto_total (valor histórico
--      emitido: el % de impuesto y el pedido pueden cambiar) y saldo_pendiente
--      (lo mantiene trg_factura_calcular_saldo y lo usa el informe de cobranza).
--      La factura sin pedido se borra solo si no tiene pagos, notas ni despachos.
--   2. NOTAS DE CRÉDITO: se elimina cliente_asociado (sale de la factura).
--   3. PEDIDOS: columna observaciones y los estados del Documento 0: registrado,
--      pendiente, en_produccion, listo_para_despacho, despachado, pagado, anulado
--      y finalizado. 'confirmado' pasa a 'registrado' y 'entregado' a 'finalizado'.
--      Los montos (neto, descuento, impuesto y total) no se guardan: la app los
--      calcula desde las líneas.
--   4. DETALLE DE PEDIDOS: se eliminan precio_unitario y subtotal (columna
--      generada a partir de precio_unitario). El precio sale de la variante
--      (producto + color + talla) según la lista de precios del cliente.
--      producto_variantes ya tiene sus precios (incremento4_campos_documento0.sql).
--   5. registrar_despacho: recibe el precio de cada línea desde la app (el que
--      muestra el pedido) y lo guarda en detalle_despachos.precio_unitario, que
--      queda como precio histórico del despacho. Los pedidos cerrados son
--      despachado, pagado, finalizado y anulado.
--
-- Va después de incremento4_cortes_cantidades.sql. No volver a ejecutar
-- facturas.sql, notas_credito.sql, incremento4_feedback.sql ni
-- incremento4_despachos.sql después de este script: vuelven a crear las columnas
-- y la versión anterior de registrar_despacho.
--
-- Es idempotente. Se ejecuta completo en el SQL Editor; si algo falla, no se
-- aplica nada. Si una vista propia de la base usa alguna de las columnas que se
-- eliminan, PostgreSQL rechaza el script (no se usa cascade).
-- =====================================================================
begin;

-- =====================================================================
-- 1. FACTURAS
-- =====================================================================
drop trigger if exists trg_facturas_columnas_antiguas on public.facturas;
drop function if exists public.fn_facturas_columnas_antiguas();

-- notas_credito.id_factura y pagos.id_factura son columnas antiguas que pueden
-- seguir apuntando a la factura: también se revisan, si existen.
do $$
declare
  v_extra text := '';
begin
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'notas_credito' and column_name = 'id_factura') then
    v_extra := v_extra || ' and not exists (select 1 from public.notas_credito nc where nc.id_factura = f.id_factura)';
  end if;
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'pagos' and column_name = 'id_factura') then
    v_extra := v_extra || ' and not exists (select 1 from public.pagos p where p.id_factura = f.id_factura)';
  end if;
  execute 'delete from public.facturas f
            where f.pedido_asociado is null
              and not exists (select 1 from public.pago_facturas pf where pf.id_factura = f.id_factura)
              and not exists (select 1 from public.notas_credito nc where nc.factura_referencia = f.id_factura)
              and not exists (select 1 from public.despachos d where d.id_factura = f.id_factura)' || v_extra;
end $$;

alter table public.facturas
  drop column if exists numero_factura,
  drop column if exists id_pedido,
  drop column if exists id_cliente,
  drop column if exists fecha,
  drop column if exists neto,
  drop column if exists iva,
  drop column if exists total,
  drop column if exists saldo,
  drop column if exists creado_en,
  drop column if exists rut,
  drop column if exists direccion,
  drop column if exists giro,
  drop column if exists codigo,
  drop column if exists detalle,
  drop column if exists forma_pago,
  drop column if exists cliente_asociado;

-- Razón social de la factura: se ingresa al crearla (no sale de clientes).
alter table public.facturas add column if not exists razon_social text;

-- pedido_asociado es obligatorio si ya no quedan facturas sin pedido.
do $$
begin
  if exists (select 1 from public.facturas where pedido_asociado is null) then
    raise notice 'Quedan facturas sin pedido (tienen pagos, notas o despachos): pedido_asociado sigue opcional';
  else
    alter table public.facturas alter column pedido_asociado set not null;
  end if;
end $$;

-- =====================================================================
-- 2. NOTAS DE CRÉDITO
-- =====================================================================
alter table public.notas_credito drop column if exists cliente_asociado;

-- =====================================================================
-- 3. PEDIDOS
-- =====================================================================
alter table public.pedidos add column if not exists observaciones text;

do $$
declare
  r record;
begin
  for r in select conname from pg_constraint
            where conrelid = 'public.pedidos'::regclass and contype = 'c'
              and pg_get_constraintdef(oid) like '%estado%' loop
    execute format('alter table public.pedidos drop constraint %I', r.conname);
  end loop;
end $$;

update public.pedidos set estado = 'registrado' where estado = 'confirmado';
update public.pedidos set estado = 'finalizado' where estado = 'entregado';

alter table public.pedidos alter column estado set default 'registrado';
alter table public.pedidos add constraint pedidos_estado_check check (estado in (
  'registrado', 'pendiente', 'en_produccion', 'listo_para_despacho',
  'despachado', 'pagado', 'anulado', 'finalizado'));

-- =====================================================================
-- 4. DETALLE DE PEDIDOS
-- =====================================================================
alter table public.detalle_pedidos
  drop column if exists subtotal,
  drop column if exists precio_unitario;

-- =====================================================================
-- 5. registrar_despacho (reemplaza la de incremento4_despachos.sql)
-- =====================================================================
-- p_lineas: [{"id_detalle_pedido": 1, "cantidad": 5, "precio": 5990, "descuento": 10}, ...]
--   "precio" es el precio unitario de la variante según la lista del cliente (lo
--   calcula la app); si falta, se usa producto_variantes.precio_venta.
--   "descuento" es opcional; por defecto, los descuentos del cliente en cascada.
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
  v_precio      integer;
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
  if v_pedido.estado in ('despachado', 'pagado', 'finalizado', 'anulado') then
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

    select d.id_detalle_pedido, d.id_pedido, d.cantidad, d.cantidad_anulada, d.id_variante,
           pv.precio_venta,
           coalesce(pv.descripcion, 'variante ' || d.id_variante) as producto
      into v_detalle
      from detalle_pedidos d
      left join producto_variantes pv on pv.id_variante = d.id_variante
     where d.id_detalle_pedido = (v_linea ->> 'id_detalle_pedido')::bigint
       for update of d;
    if not found or v_detalle.id_pedido <> p_id_pedido then
      raise exception 'Uno de los productos indicados no pertenece al pedido %', v_pedido.numero_pedido;
    end if;

    v_precio := coalesce((v_linea ->> 'precio')::integer, v_detalle.precio_venta, 0);
    if v_precio < 0 then
      raise exception 'Precio inválido en la línea %', v_linea;
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
    values (v_id_despacho, v_detalle.id_detalle_pedido, v_cantidad, v_precio,
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

commit;

-- Comprobación (es lo que muestra el SQL Editor): columnas que quedan en las
-- tablas modificadas y estados de los pedidos.
select table_name as tabla, string_agg(column_name, ', ' order by ordinal_position) as columnas
  from information_schema.columns
 where table_schema = 'public' and table_name in ('facturas', 'notas_credito', 'pedidos', 'detalle_pedidos')
 group by table_name
union all
select 'pedidos (estados)', string_agg(distinct estado, ', ') from public.pedidos
 order by 1;
