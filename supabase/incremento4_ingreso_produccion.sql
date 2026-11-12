-- =====================================================================
-- Incremento 4: ingreso de producción a bodega por color, talla y cantidad (CU-21).
--
-- CU-21 paso 3: el usuario ingresa los productos fabricados de una guía de cortes
-- (color, talla y cantidad de cada uno). La versión anterior de ingresar_guia_corte
-- (incremento4_inventario_variantes.sql) ingresaba la cantidad completa del corte con
-- el color y la talla base del producto, y fallaba si el producto no los tenía.
--
-- La nueva función recibe una línea por producto fabricado:
--   p_lineas = [{"id_color": 2, "id_talla": 1, "cantidad": 12}, ...]
-- El producto es el de la guía de cortes (cortes.producto_asociado). Cada línea suma
-- stock a su variante en la bodega (la crea con obtener_variante() si no existe) y
-- queda en movimientos_inventario como 'entrada_corte' con el usuario responsable
-- (CU-39, paso 5). La guía queda 'ingresada'. Devuelve el total de unidades.
--
-- Excepciones de CU-21: 1) la guía no existe; 2) una cantidad es menor o igual a cero.
--
-- Se elimina la versión anterior (p_id_corte, p_id_bodega, p_usuario) para que la API
-- no tenga dos funciones con el mismo nombre. La app (realFlask.py) ya llama a esta.
-- Es idempotente y se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

drop function if exists public.ingresar_guia_corte(bigint, bigint, text);

create or replace function public.ingresar_guia_corte(p_id_corte  bigint,
                                                      p_id_bodega bigint,
                                                      p_lineas    jsonb,
                                                      p_usuario   text default 'Admin')
returns integer
language plpgsql
set search_path to 'public'
as $$
declare
  v_corte    cortes%rowtype;
  v_linea    jsonb;
  v_color    bigint;
  v_talla    bigint;
  v_cantidad integer;
  v_variante bigint;
  v_id_inv   bigint;
  v_total    integer := 0;
begin
  select * into v_corte from cortes where id_corte = p_id_corte for update;
  if not found then
    raise exception 'No existe la guía de cortes %', p_id_corte;
  end if;
  if v_corte.estado <> 'pendiente' then
    raise exception 'La guía de cortes % ya fue ingresada o está anulada', p_id_corte;
  end if;
  if v_corte.producto_asociado is null
     or not exists (select 1 from productos where id_producto = v_corte.producto_asociado) then
    raise exception 'La guía de cortes % no tiene un producto asociado válido', p_id_corte;
  end if;
  if not exists (select 1 from bodegas where id_bodega = p_id_bodega) then
    raise exception 'La bodega seleccionada no existe';
  end if;
  if p_lineas is null or jsonb_typeof(p_lineas) <> 'array' or jsonb_array_length(p_lineas) = 0 then
    raise exception 'Ingrese al menos un producto fabricado (color, talla y cantidad)';
  end if;

  perform set_config('app.tipo_movimiento', 'entrada_corte', true);
  perform set_config('app.id_corte', p_id_corte::text, true);
  perform set_config('app.observacion', 'Ingreso guía de cortes ' || p_id_corte, true);

  for v_linea in select * from jsonb_array_elements(p_lineas) loop
    v_color    := (v_linea ->> 'id_color')::bigint;
    v_talla    := (v_linea ->> 'id_talla')::bigint;
    v_cantidad := (v_linea ->> 'cantidad')::integer;
    if v_cantidad is null or v_cantidad <= 0 then
      raise exception 'La cantidad de cada producto fabricado debe ser mayor que cero';
    end if;
    if not exists (select 1 from colores where id_color = v_color) then
      raise exception 'Uno de los colores seleccionados no existe';
    end if;
    if not exists (select 1 from tallas where id_talla = v_talla) then
      raise exception 'Una de las tallas seleccionadas no existe';
    end if;

    select id_variante into v_variante
      from obtener_variante(v_corte.producto_asociado, v_color, v_talla);

    select id_inventario into v_id_inv
      from inventario
     where id_bodega = p_id_bodega and id_variante = v_variante
     order by id_inventario
     limit 1
       for update;
    if found then
      update inventario
         set cantidad = cantidad + v_cantidad, usuario_actualizacion = p_usuario
       where id_inventario = v_id_inv;
    else
      insert into inventario (id_bodega, id_variante, id_talla, id_color, cantidad, usuario_actualizacion)
      values (p_id_bodega, v_variante, v_talla, v_color, v_cantidad, p_usuario);
    end if;
    v_total := v_total + v_cantidad;
  end loop;

  update cortes
     set estado = 'ingresado', fecha_ingreso = now(), id_bodega_ingreso = p_id_bodega
   where id_corte = p_id_corte;

  perform set_config('app.tipo_movimiento', '', true);
  perform set_config('app.id_corte', '', true);
  perform set_config('app.observacion', '', true);

  return v_total;
end $$;

commit;

-- Comprobación (es lo que muestra el SQL Editor): debe quedar una sola versión, con p_lineas.
select p.proname as funcion, pg_get_function_identity_arguments(p.oid) as argumentos
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public' and p.proname = 'ingresar_guia_corte';
