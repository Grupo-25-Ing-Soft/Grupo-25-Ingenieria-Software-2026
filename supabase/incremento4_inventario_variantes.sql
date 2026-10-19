-- =====================================================================
-- Incremento 4: funciones de inventario por variante.
--
-- La tabla inventario se identifica por id_variante (ya no tiene id_producto),
-- pero tres funciones de la base seguían usando inventario.id_producto y fallan
-- al ejecutarse (plpgsql guarda el código como texto; renombrar la columna no
-- las actualiza):
--   * fn_inventario_movimiento: trigger que registra cada cambio de stock en
--     movimientos_inventario (old.id_producto / new.id_producto).
--   * ingresar_guia_corte: ingreso de producción a bodega (RF-021).
--   * registrar_defectuosos: productos con defectos (RF-053).
-- Este script las reemplaza con la misma lógica, usando la variante. No borra
-- columnas ni datos. Se puede ejecutar más de una vez; si algo falla, no se
-- aplica nada.
-- =====================================================================
begin;

-- movimientos_inventario.id_producto es obligatorio y lo usan las vistas de
-- producción; se mantiene y se agrega también la variante del movimiento.
alter table public.movimientos_inventario
  add column if not exists id_variante bigint references public.producto_variantes (id_variante);

-- ---------------------------------------------------------------------
-- 1. Trigger de movimientos: misma lógica, comparando por variante.
-- ---------------------------------------------------------------------
create or replace function public.fn_inventario_movimiento()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  v_tipo  text   := nullif(current_setting('app.tipo_movimiento', true), '');
  v_corte bigint := nullif(current_setting('app.id_corte', true), '')::bigint;
  v_obs   text   := nullif(current_setting('app.observacion', true), '');
  v_producto_old bigint;
  v_producto_new bigint;
begin
  if tg_op in ('UPDATE', 'DELETE') then
    select id_producto into v_producto_old from producto_variantes where id_variante = old.id_variante;
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    select id_producto into v_producto_new from producto_variantes where id_variante = new.id_variante;
  end if;

  if tg_op = 'DELETE'
     or (tg_op = 'UPDATE' and (old.id_bodega, old.id_variante, old.id_talla, old.id_color)
                   is distinct from (new.id_bodega, new.id_variante, new.id_talla, new.id_color)) then
    if old.cantidad <> 0 then
      insert into movimientos_inventario
        (tipo, id_bodega, id_producto, id_variante, id_talla, id_color, cantidad,
         stock_anterior, stock_resultante, id_corte, observacion)
      values
        (coalesce(v_tipo, case when tg_op = 'DELETE' then 'baja' else 'ajuste' end),
         old.id_bodega, v_producto_old, old.id_variante, old.id_talla, old.id_color, -old.cantidad,
         old.cantidad, 0, v_corte, v_obs);
    end if;
    if tg_op = 'DELETE' then
      return old;
    end if;
  end if;

  if tg_op = 'INSERT'
     or (old.id_bodega, old.id_variante, old.id_talla, old.id_color)
        is distinct from (new.id_bodega, new.id_variante, new.id_talla, new.id_color) then
    if new.cantidad <> 0 then
      insert into movimientos_inventario
        (tipo, id_bodega, id_producto, id_variante, id_talla, id_color, cantidad,
         stock_anterior, stock_resultante, id_corte, observacion, usuario)
      values
        (coalesce(v_tipo, case when tg_op = 'INSERT' then 'inicial' else 'ajuste' end),
         new.id_bodega, v_producto_new, new.id_variante, new.id_talla, new.id_color, new.cantidad,
         0, new.cantidad, v_corte, v_obs, new.usuario_actualizacion);
    end if;
    return new;
  end if;

  if new.cantidad <> old.cantidad then
    insert into movimientos_inventario
      (tipo, id_bodega, id_producto, id_variante, id_talla, id_color, cantidad,
       stock_anterior, stock_resultante, id_corte, observacion, usuario)
    values
      (coalesce(v_tipo, 'ajuste'),
       new.id_bodega, v_producto_new, new.id_variante, new.id_talla, new.id_color, new.cantidad - old.cantidad,
       old.cantidad, new.cantidad, v_corte, v_obs, new.usuario_actualizacion);
  end if;
  return new;
end $$;

-- ---------------------------------------------------------------------
-- 2. Ingreso de una guía de cortes a bodega (RF-021).
--    El corte apunta a un producto con su color y talla; se usa (o crea) la
--    variante con obtener_variante() y se suma a su fila de inventario.
-- ---------------------------------------------------------------------
create or replace function public.ingresar_guia_corte(p_id_corte bigint, p_id_bodega bigint,
                                                      p_usuario text default 'Admin')
returns integer
language plpgsql
set search_path to 'public'
as $$
declare
  v_corte    cortes%rowtype;
  v_producto productos%rowtype;
  v_variante bigint;
  v_id_inv   bigint;
begin
  select * into v_corte from cortes where id_corte = p_id_corte for update;
  if not found then
    raise exception 'No existe la guía de cortes %', p_id_corte;
  end if;
  if v_corte.estado <> 'pendiente' then
    raise exception 'La guía de cortes % ya fue ingresada o está anulada', p_id_corte;
  end if;
  if coalesce(v_corte.cantidad, 0) <= 0 then
    raise exception 'La guía de cortes % no tiene cantidad para ingresar', p_id_corte;
  end if;
  if not exists (select 1 from bodegas where id_bodega = p_id_bodega) then
    raise exception 'La bodega seleccionada no existe';
  end if;

  select * into v_producto from productos where id_producto = v_corte.producto_asociado;
  if not found then
    raise exception 'La guía de cortes % no tiene un producto asociado válido', p_id_corte;
  end if;
  if v_producto.color is null or v_producto.talla is null then
    raise exception 'El producto % de la guía no tiene color o talla definidos', v_producto.descripcion;
  end if;

  select id_variante into v_variante
    from obtener_variante(v_producto.id_producto, v_producto.color, v_producto.talla);

  perform set_config('app.tipo_movimiento', 'entrada_corte', true);
  perform set_config('app.id_corte', p_id_corte::text, true);
  perform set_config('app.observacion', 'Ingreso guía de cortes ' || p_id_corte, true);

  select id_inventario into v_id_inv
    from inventario
   where id_bodega = p_id_bodega and id_variante = v_variante
   order by id_inventario
   limit 1
     for update;
  if found then
    update inventario
       set cantidad = cantidad + v_corte.cantidad, usuario_actualizacion = p_usuario
     where id_inventario = v_id_inv;
  else
    insert into inventario (id_bodega, id_variante, id_talla, id_color, cantidad, usuario_actualizacion)
    values (p_id_bodega, v_variante, v_producto.talla, v_producto.color, v_corte.cantidad, p_usuario);
  end if;

  update cortes
     set estado = 'ingresado', fecha_ingreso = now(), id_bodega_ingreso = p_id_bodega
   where id_corte = p_id_corte;

  perform set_config('app.tipo_movimiento', '', true);
  perform set_config('app.id_corte', '', true);
  perform set_config('app.observacion', '', true);

  return v_corte.cantidad;
end $$;

-- ---------------------------------------------------------------------
-- 3. Productos con defectos (RF-053): mismos parámetros que antes; se busca la
--    variante del producto + color + talla y se mueven unidades de disponibles
--    a defectuosas en esa bodega.
-- ---------------------------------------------------------------------
create or replace function public.registrar_defectuosos(
  p_id_bodega   bigint,
  p_id_producto bigint,
  p_id_talla    bigint,
  p_id_color    bigint,
  p_cantidad    integer,
  p_observacion text default null,
  p_usuario     text default 'Admin'
) returns void
language plpgsql
set search_path to 'public'
as $$
declare
  v_variante  bigint;
  v_stock     integer;
  v_restante  integer;
  v_descuento integer;
  v_fila      record;
  v_primera   bigint;
begin
  if p_cantidad is null or p_cantidad <= 0 then
    raise exception 'La cantidad debe ser mayor que cero';
  end if;

  select id_variante into v_variante
    from producto_variantes
   where id_producto = p_id_producto and id_color = p_id_color and id_talla = p_id_talla;
  if not found then
    raise exception 'No existe la variante de ese producto, color y talla';
  end if;

  select coalesce(sum(cantidad), 0) into v_stock
    from inventario where id_bodega = p_id_bodega and id_variante = v_variante;
  if v_stock < p_cantidad then
    raise exception 'Stock insuficiente (hay %, se marcan %)', v_stock, p_cantidad;
  end if;

  perform set_config('app.tipo_movimiento', 'defecto', true);
  perform set_config('app.observacion', coalesce(p_observacion, 'Productos con defectos'), true);

  v_restante := p_cantidad;
  for v_fila in
    select id_inventario, cantidad from inventario
     where id_bodega = p_id_bodega and id_variante = v_variante and cantidad > 0
     order by id_inventario
       for update
  loop
    exit when v_restante = 0;
    v_descuento := least(v_fila.cantidad, v_restante);
    v_primera := coalesce(v_primera, v_fila.id_inventario);
    update inventario
       set cantidad = cantidad - v_descuento, usuario_actualizacion = p_usuario
     where id_inventario = v_fila.id_inventario;
    v_restante := v_restante - v_descuento;
  end loop;

  -- Las unidades defectuosas quedan en la primera fila de esa variante en la bodega.
  update inventario
     set cantidad_defectuosa = cantidad_defectuosa + p_cantidad
   where id_inventario = v_primera;

  perform set_config('app.tipo_movimiento', '', true);
  perform set_config('app.observacion', '', true);
end $$;

commit;

-- Comprobación: triggers de inventario y su estado (es lo que muestra el SQL Editor).
select c.relname as tabla, t.tgname as trigger, t.tgfoid::regproc::text as funcion,
       case when t.tgenabled = 'D' then 'desactivado' else 'activo' end as estado
  from pg_trigger t join pg_class c on c.oid = t.tgrelid
 where not t.tgisinternal and c.relname in ('inventario', 'movimientos_inventario')
 order by 1, 2;
