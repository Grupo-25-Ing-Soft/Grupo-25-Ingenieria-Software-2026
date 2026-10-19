-- =====================================================================
-- Incremento 4 (feedback): alinea las tablas reales de Supabase con
-- supabase/facturas.sql, notas_credito.sql y pagos.sql.
--
-- Esos scripts usan "create table if not exists" y las tablas ya existían
-- con otras columnas (numero_factura, total, saldo, numero_nota, total_nota...),
-- así que nunca se aplicaron. La app ahora usa los nombres de los scripts.
-- Este script:
--   1. Agrega las columnas de los scripts y copia los datos de las antiguas.
--   2. No borra ninguna columna ni fila. Las columnas antiguas quedan opcionales
--      y, en facturas, se siguen llenando con un trigger para que los informes
--      del Incremento 3 (que leen numero_factura, razon_social, id_cliente)
--      sigan funcionando.
--   3. Recalcula facturas.saldo_pendiente = monto_total - pagos aplicados
--      vigentes - notas de crédito vigentes, y su estado.
--   4. Crea índices únicos para los códigos EAN (variantes y maestros).
--
-- Es idempotente: se puede ejecutar más de una vez. Se ejecuta completo en el
-- SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- Utilidad: deja opcionales las columnas obligatorias que la app ya no usa.
-- ---------------------------------------------------------------------
create or replace function pg_temp.opcionales_salvo(p_tabla text, p_columnas text[])
returns void language plpgsql as $$
declare
  c record;
begin
  for c in
    select column_name from information_schema.columns
     where table_schema = 'public' and table_name = p_tabla
       and is_nullable = 'NO' and column_default is null and is_identity = 'NO'
       and column_name <> all (p_columnas)
  loop
    execute format('alter table public.%I alter column %I drop not null', p_tabla, c.column_name);
  end loop;
end $$;

-- Exige "not null" solo si ninguna fila quedó vacía (si no, avisa y sigue).
create or replace function pg_temp.exigir_si_completa(p_tabla text, p_columna text)
returns void language plpgsql as $$
declare
  v_nulos bigint;
begin
  execute format('select count(*) from public.%I where %I is null', p_tabla, p_columna) into v_nulos;
  if v_nulos = 0 then
    execute format('alter table public.%I alter column %I set not null', p_tabla, p_columna);
  else
    raise notice '%.% tiene % filas vacías: se deja opcional. Complétalas y vuelve a ejecutar.',
      p_tabla, p_columna, v_nulos;
  end if;
end $$;

-- Reemplaza el check de "estado" que tuviera la tabla por el de los scripts.
create or replace function pg_temp.reemplazar_check_estado(p_tabla text, p_nombre text, p_valores text)
returns void language plpgsql as $$
declare
  r record;
begin
  for r in
    select conname from pg_constraint
     where conrelid = format('public.%I', p_tabla)::regclass and contype = 'c'
       and pg_get_constraintdef(oid) ilike '%estado%'
  loop
    execute format('alter table public.%I drop constraint %I', p_tabla, r.conname);
  end loop;
  execute format('alter table public.%I add constraint %I check (estado in (%s))', p_tabla, p_nombre, p_valores);
end $$;

-- Columna "existe" (para copiar datos solo desde columnas antiguas presentes).
create or replace function pg_temp.existe(p_tabla text, p_columna text)
returns boolean language sql as $$
  select exists (select 1 from information_schema.columns
                  where table_schema = 'public' and table_name = p_tabla and column_name = p_columna)
$$;

-- =====================================================================
-- 1. FACTURAS
-- =====================================================================
alter table public.facturas
  add column if not exists folio            bigint,
  add column if not exists pedido_asociado  bigint references public.pedidos (id_pedido),
  add column if not exists cliente_asociado bigint references public.clientes (id_cliente),
  add column if not exists fecha_emision    date not null default current_date,
  add column if not exists monto_neto       numeric(12,2) not null default 0,
  add column if not exists monto_impuesto   numeric(12,2) not null default 0,
  add column if not exists monto_total      numeric(12,2) not null default 0,
  add column if not exists saldo_pendiente  numeric(12,2) not null default 0,
  add column if not exists estado           text not null default 'vigente',
  add column if not exists fecha_creacion   timestamptz not null default now(),
  add column if not exists usuario_creacion text not null default 'Admin';

-- Copia desde las columnas antiguas, solo donde la nueva sigue vacía o en cero.
do $$
begin
  if pg_temp.existe('facturas', 'numero_factura') then
    update public.facturas set folio = numero_factura::bigint
     where folio is null and numero_factura ~ '^[0-9]+$'
       and not exists (select 1 from public.facturas f2 where f2.folio = numero_factura::bigint);
  end if;
  if pg_temp.existe('facturas', 'id_pedido') then
    update public.facturas set pedido_asociado = id_pedido where pedido_asociado is null and id_pedido is not null;
  end if;
  if pg_temp.existe('facturas', 'id_cliente') then
    update public.facturas set cliente_asociado = id_cliente where cliente_asociado is null and id_cliente is not null;
  end if;
  if pg_temp.existe('facturas', 'fecha') then
    -- Después de la primera ejecución el trigger mantiene fecha = fecha_emision.
    update public.facturas set fecha_emision = fecha where fecha is not null and fecha_emision is distinct from fecha;
  end if;
  if pg_temp.existe('facturas', 'total') then
    update public.facturas
       set monto_neto = coalesce(neto, 0), monto_impuesto = coalesce(iva, 0), monto_total = coalesce(total, 0)
     where monto_total = 0 and coalesce(total, 0) <> 0;
  end if;
  if pg_temp.existe('facturas', 'creado_en') then
    update public.facturas set fecha_creacion = creado_en
     where creado_en is not null and fecha_creacion is distinct from creado_en;
  end if;
end $$;

-- El cliente también se puede deducir del pedido asociado.
update public.facturas f set cliente_asociado = p.cliente_asociado
  from public.pedidos p
 where f.cliente_asociado is null and f.pedido_asociado = p.id_pedido;

-- Folio para las facturas cuyo número antiguo no era numérico (ej. 'F-TEST-001').
with sin_folio as (
  select id_factura, row_number() over (order by id_factura) as n
    from public.facturas where folio is null
)
update public.facturas f
   set folio = (select coalesce(max(folio), 0) from public.facturas) + s.n
  from sin_folio s
 where f.id_factura = s.id_factura;

alter table public.facturas alter column folio set not null;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'facturas_folio_unico') then
    alter table public.facturas add constraint facturas_folio_unico unique (folio);
  end if;
end $$;
select pg_temp.exigir_si_completa('facturas', 'pedido_asociado');
select pg_temp.exigir_si_completa('facturas', 'cliente_asociado');

-- Estados: el antiguo 'emitida' pasa a los de facturas.sql (se recalcula en la sección 4).
update public.facturas set estado = 'vigente'
 where estado not in ('vigente', 'pagada', 'parcialmente_pagada', 'anulada');
select pg_temp.reemplazar_check_estado('facturas', 'facturas_estado_check',
  $v$'vigente','pagada','parcialmente_pagada','anulada'$v$);

select pg_temp.opcionales_salvo('facturas', array['id_factura', 'folio', 'fecha_emision', 'monto_neto',
  'monto_impuesto', 'monto_total', 'saldo_pendiente', 'estado', 'fecha_creacion', 'usuario_creacion',
  'pedido_asociado', 'cliente_asociado']);

create index if not exists facturas_cliente_asociado_idx on public.facturas (cliente_asociado);
create index if not exists facturas_pedido_asociado_idx on public.facturas (pedido_asociado);

-- Las columnas antiguas se llenan desde las nuevas (las leen los informes del
-- Incremento 3 y la vista v_despachos_detalle). Solo si existen.
do $$
begin
  if pg_temp.existe('facturas', 'numero_factura') then
    create or replace function public.fn_facturas_columnas_antiguas()
    returns trigger language plpgsql set search_path to 'public' as $f$
    begin
      new.numero_factura := new.folio::text;
      new.id_pedido      := new.pedido_asociado;
      new.id_cliente     := new.cliente_asociado;
      new.fecha          := new.fecha_emision;
      new.neto           := new.monto_neto;
      new.iva            := new.monto_impuesto;
      new.total          := new.monto_total;
      new.saldo          := new.saldo_pendiente;
      if new.cliente_asociado is not null then
        select c.nombre, nullif(concat_ws('-', c.rut, c.digito_verificador), '')
          into new.razon_social, new.rut
          from clientes c where c.id_cliente = new.cliente_asociado;
      end if;
      return new;
    end $f$;
    drop trigger if exists trg_facturas_columnas_antiguas on public.facturas;
    create trigger trg_facturas_columnas_antiguas
      before insert or update on public.facturas
      for each row execute function public.fn_facturas_columnas_antiguas();
  end if;
end $$;

-- =====================================================================
-- 2. NOTAS DE CRÉDITO
-- =====================================================================
do $$
begin
  if pg_temp.existe('notas_credito', 'id_nota') and not pg_temp.existe('notas_credito', 'id_nota_credito') then
    alter table public.notas_credito rename column id_nota to id_nota_credito;
  end if;
end $$;

alter table public.notas_credito
  add column if not exists folio              bigint,
  add column if not exists factura_referencia bigint references public.facturas (id_factura),
  add column if not exists cliente_asociado   bigint references public.clientes (id_cliente),
  add column if not exists fecha              date not null default current_date,
  add column if not exists monto_neto         numeric(12,2) not null default 0,
  add column if not exists monto_impuesto     numeric(12,2) not null default 0,
  add column if not exists monto_total        numeric(12,2) not null default 0,
  add column if not exists motivo             text,
  add column if not exists estado             text not null default 'vigente',
  add column if not exists fecha_creacion     timestamptz not null default now(),
  add column if not exists usuario_creacion   text not null default 'Admin';

do $$
begin
  if pg_temp.existe('notas_credito', 'numero_nota') then
    update public.notas_credito n set folio = numero_nota::bigint
     where folio is null and numero_nota::text ~ '^[0-9]+$'
       and not exists (select 1 from public.notas_credito n2 where n2.folio = n.numero_nota::bigint);
  end if;
  if pg_temp.existe('notas_credito', 'id_factura') then
    update public.notas_credito set factura_referencia = id_factura
     where factura_referencia is null and id_factura is not null;
  end if;
  if pg_temp.existe('notas_credito', 'id_cliente') then
    update public.notas_credito set cliente_asociado = id_cliente
     where cliente_asociado is null and id_cliente is not null;
  end if;
  if pg_temp.existe('notas_credito', 'total_nota') then
    update public.notas_credito
       set monto_neto = coalesce(total_neto, 0), monto_impuesto = coalesce(total_iva, 0),
           monto_total = coalesce(total_nota, 0)
     where monto_total = 0 and coalesce(total_nota, 0) <> 0;
  end if;
  if pg_temp.existe('notas_credito', 'creado_en') then
    update public.notas_credito set fecha_creacion = creado_en
     where creado_en is not null and fecha_creacion is distinct from creado_en;
  end if;
end $$;

-- Cliente desde la factura de referencia.
update public.notas_credito n set cliente_asociado = f.cliente_asociado
  from public.facturas f
 where n.cliente_asociado is null and n.factura_referencia = f.id_factura;

with sin_folio as (
  select id_nota_credito, row_number() over (order by id_nota_credito) as n
    from public.notas_credito where folio is null
)
update public.notas_credito nc
   set folio = (select coalesce(max(folio), 0) from public.notas_credito) + s.n
  from sin_folio s
 where nc.id_nota_credito = s.id_nota_credito;

update public.notas_credito set motivo = 'Sin motivo registrado' where motivo is null or trim(motivo) = '';

alter table public.notas_credito alter column folio set not null;
alter table public.notas_credito alter column motivo set not null;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'notas_credito_folio_unico') then
    alter table public.notas_credito add constraint notas_credito_folio_unico unique (folio);
  end if;
end $$;
select pg_temp.exigir_si_completa('notas_credito', 'factura_referencia');
select pg_temp.exigir_si_completa('notas_credito', 'cliente_asociado');

update public.notas_credito set estado = 'vigente' where estado not in ('vigente', 'anulada', 'aplicada');
select pg_temp.reemplazar_check_estado('notas_credito', 'notas_credito_estado_check',
  $v$'vigente','anulada','aplicada'$v$);

select pg_temp.opcionales_salvo('notas_credito', array['id_nota_credito', 'folio', 'fecha', 'monto_neto',
  'monto_impuesto', 'monto_total', 'motivo', 'estado', 'fecha_creacion', 'usuario_creacion',
  'factura_referencia', 'cliente_asociado']);

create index if not exists notas_credito_factura_referencia_idx on public.notas_credito (factura_referencia);
create index if not exists notas_credito_cliente_asociado_idx on public.notas_credito (cliente_asociado);

-- =====================================================================
-- 3. PAGOS
-- =====================================================================
do $$
begin
  if not pg_temp.existe('pagos', 'folio') then
    -- Las filas existentes reciben folio de la secuencia de la identidad.
    alter table public.pagos add column folio bigint generated by default as identity;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'pagos_folio_key') then
    alter table public.pagos add constraint pagos_folio_key unique (folio);
  end if;
end $$;

alter table public.pagos
  add column if not exists fecha_creacion   timestamptz not null default now(),
  add column if not exists usuario_creacion text not null default 'Admin',
  add column if not exists motivo_anulacion text;

do $$
begin
  if pg_temp.existe('pagos', 'created_at') then
    update public.pagos set fecha_creacion = created_at
     where created_at is not null and fecha_creacion is distinct from created_at;
  end if;
  -- El pago antiguo apuntaba a una sola factura (pagos.id_factura): pasa a pago_facturas.
  if pg_temp.existe('pagos', 'id_factura') then
    insert into public.pago_facturas (id_pago, id_factura, monto_aplicado)
    select p.id_pago, p.id_factura, p.monto
      from public.pagos p
     where p.id_factura is not null
       and not exists (select 1 from public.pago_facturas pf
                        where pf.id_pago = p.id_pago and pf.id_factura = p.id_factura);
  end if;
end $$;

update public.pagos set estado = 'vigente' where estado not in ('vigente', 'anulada');
select pg_temp.reemplazar_check_estado('pagos', 'pagos_estado_check', $v$'vigente','anulada'$v$);
select pg_temp.opcionales_salvo('pagos', array['id_pago', 'cliente_asociado', 'fecha_pago', 'monto',
  'medio_pago', 'estado', 'fecha_creacion', 'usuario_creacion']);

create index if not exists pagos_cliente_asociado_idx on public.pagos (cliente_asociado);
create index if not exists pagos_fecha_pago_idx on public.pagos (fecha_pago);
create index if not exists pago_facturas_id_pago_idx on public.pago_facturas (id_pago);
create index if not exists pago_facturas_id_factura_idx on public.pago_facturas (id_factura);

-- =====================================================================
-- 4. SALDO Y ESTADO DE CADA FACTURA (misma regla que la app)
--    saldo = total - pagos aplicados (pagos vigentes) - notas de crédito vigentes
-- =====================================================================
update public.facturas f
   set saldo_pendiente = greatest(f.monto_total
         - coalesce((select sum(pf.monto_aplicado) from public.pago_facturas pf
                       join public.pagos p on p.id_pago = pf.id_pago
                      where pf.id_factura = f.id_factura and p.estado = 'vigente'), 0)
         - coalesce((select sum(nc.monto_total) from public.notas_credito nc
                      where nc.factura_referencia = f.id_factura and nc.estado = 'vigente'), 0), 0)
 where f.estado <> 'anulada';

update public.facturas
   set estado = case when saldo_pendiente <= 0 then 'pagada'
                     when saldo_pendiente >= monto_total then 'vigente'
                     else 'parcialmente_pagada' end
 where estado <> 'anulada';

-- =====================================================================
-- 5. UNICIDAD DE LOS CÓDIGOS EAN (CU-15.5)
--    incremento3_ean.sql no tenía índices únicos: dos colores (o tallas o
--    productos) con el mismo código EAN daban el mismo EAN-13 a variantes
--    distintas. Si ya hay repetidos, se avisa y no se crea ese índice.
-- =====================================================================
create or replace function pg_temp.indice_ean_unico(p_tabla text, p_indice text)
returns void language plpgsql as $$
declare
  v_repetidos boolean;
begin
  execute format('select exists (select 1 from public.%I where codigo_ean is not null
                                  group by codigo_ean having count(*) > 1)', p_tabla) into v_repetidos;
  if v_repetidos then
    raise notice '%: hay códigos EAN repetidos; corrígelos y vuelve a ejecutar para crear el índice único.', p_tabla;
  else
    execute format('create unique index if not exists %I on public.%I (codigo_ean) where codigo_ean is not null',
                   p_indice, p_tabla);
  end if;
end $$;

select pg_temp.indice_ean_unico('producto_variantes', 'producto_variantes_codigo_ean_uk');
select pg_temp.indice_ean_unico('productos', 'productos_codigo_ean_uk');
select pg_temp.indice_ean_unico('colores', 'colores_codigo_ean_uk');
select pg_temp.indice_ean_unico('tallas', 'tallas_codigo_ean_uk');

commit;

-- Comprobación (opcional): las tres tablas con las columnas de los scripts.
select id_factura, folio, pedido_asociado, cliente_asociado, fecha_emision, monto_total, saldo_pendiente, estado
  from public.facturas order by id_factura;
select id_nota_credito, folio, factura_referencia, cliente_asociado, fecha, monto_total, motivo, estado
  from public.notas_credito order by id_nota_credito;
select id_pago, folio, cliente_asociado, fecha_pago, monto, medio_pago, estado from public.pagos order by id_pago;
