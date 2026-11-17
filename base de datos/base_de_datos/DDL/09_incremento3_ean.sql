-- =====================================================================
-- Códigos EAN propios de Comercial D Nix (RF-015, RF-016, RF-017).
--
-- Estructura observada en las etiquetas reales (13 dígitos):
--   99      414       0001    010     1
--   prefijo producto  color   talla   dígito verificador (EAN-13)
-- Ej.: 414 Blanco S = 9941400010101, 425 Beige M = 9942503970118.
--
-- El EAN de cada variante (producto + color + talla) se arma solo a partir
-- de los códigos de cada maestro. El prefijo y el largo de cada parte se
-- configuran en parametros_sistema. Si un producto usa otra lógica, la
-- variante puede tener un código manual (ean_manual = true) que se respeta.
--
-- Se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- 1. Códigos en los maestros
-- ---------------------------------------------------------------------
alter table public.productos
  add column if not exists codigo     text,  -- código del artículo impreso en la etiqueta (414, C259)
  add column if not exists codigo_ean text check (codigo_ean ~ '^[0-9]+$');

alter table public.colores
  add column if not exists codigo_ean text check (codigo_ean ~ '^[0-9]+$');

alter table public.tallas
  add column if not exists nombre     text,  -- lo que se imprime: S, M, L, 38...
  add column if not exists codigo_ean text check (codigo_ean ~ '^[0-9]+$');

create unique index if not exists productos_codigo_uk on public.productos (codigo) where codigo is not null;

-- ---------------------------------------------------------------------
-- 2. Formato del EAN en parámetros del sistema (prefijo + partes = 12)
-- ---------------------------------------------------------------------
alter table public.parametros_sistema
  add column if not exists ean_prefijo          text     not null default '99' check (ean_prefijo ~ '^[0-9]*$'),
  add column if not exists ean_digitos_producto smallint not null default 3 check (ean_digitos_producto > 0),
  add column if not exists ean_digitos_color    smallint not null default 4 check (ean_digitos_color > 0),
  add column if not exists ean_digitos_talla    smallint not null default 3 check (ean_digitos_talla > 0);

alter table public.parametros_sistema
  drop constraint if exists parametros_sistema_ean_largo_check;
alter table public.parametros_sistema
  add constraint parametros_sistema_ean_largo_check
  check (length(ean_prefijo) + ean_digitos_producto + ean_digitos_color + ean_digitos_talla = 12);

-- ---------------------------------------------------------------------
-- 3. Variantes: código automático o manual
-- ---------------------------------------------------------------------
alter table public.producto_variantes
  add column if not exists ean_manual boolean not null default false;

-- Los códigos que ya existen se conservan tal cual.
update public.producto_variantes set ean_manual = true where codigo_ean is not null;

-- ---------------------------------------------------------------------
-- 4. Funciones
-- ---------------------------------------------------------------------

-- Dígito verificador EAN-13 a partir de los primeros 12 dígitos.
create or replace function public.fn_ean13_digito_verificador(p_codigo12 text)
returns text
language plpgsql
immutable
set search_path to 'public'
as $$
declare
  v_suma integer := 0;
  i      integer;
begin
  if p_codigo12 !~ '^[0-9]{12}$' then
    raise exception 'Se esperaban 12 dígitos para calcular el verificador: %', p_codigo12;
  end if;
  for i in 1..12 loop
    v_suma := v_suma + substr(p_codigo12, i, 1)::integer * (case when i % 2 = 0 then 3 else 1 end);
  end loop;
  return ((10 - v_suma % 10) % 10)::text;
end $$;

-- EAN de una combinación producto + color + talla. Devuelve null si a algún
-- maestro le falta su código EAN.
create or replace function public.fn_generar_ean(p_id_producto bigint, p_id_color bigint, p_id_talla bigint)
returns text
language plpgsql
stable
set search_path to 'public'
as $$
declare
  v_par   parametros_sistema%rowtype;
  v_prod  text;
  v_color text;
  v_talla text;
  v_base  text;
begin
  select * into v_par from parametros_sistema where id = 1;
  select codigo_ean into v_prod  from productos where id_producto = p_id_producto;
  select codigo_ean into v_color from colores   where id_color    = p_id_color;
  select codigo_ean into v_talla from tallas    where id_talla    = p_id_talla;

  if v_prod is null or v_color is null or v_talla is null then
    return null;
  end if;
  if length(v_prod) > v_par.ean_digitos_producto then
    raise exception 'El código EAN de producto % tiene más de % dígitos', v_prod, v_par.ean_digitos_producto;
  end if;
  if length(v_color) > v_par.ean_digitos_color then
    raise exception 'El código EAN de color % tiene más de % dígitos', v_color, v_par.ean_digitos_color;
  end if;
  if length(v_talla) > v_par.ean_digitos_talla then
    raise exception 'El código EAN de talla % tiene más de % dígitos', v_talla, v_par.ean_digitos_talla;
  end if;

  v_base := v_par.ean_prefijo
         || lpad(v_prod,  v_par.ean_digitos_producto, '0')
         || lpad(v_color, v_par.ean_digitos_color,    '0')
         || lpad(v_talla, v_par.ean_digitos_talla,    '0');
  return v_base || fn_ean13_digito_verificador(v_base);
end $$;

-- Asigna el EAN a la variante al crearla o modificarla.
create or replace function public.fn_variante_ean()
returns trigger
language plpgsql
set search_path to 'public'
as $$
begin
  if new.ean_manual then
    if new.codigo_ean is null or new.codigo_ean !~ '^[0-9]{13}$' then
      raise exception 'El código EAN manual debe tener 13 dígitos';
    end if;
  else
    new.codigo_ean := fn_generar_ean(new.id_producto, new.id_color, new.id_talla);
  end if;
  return new;
end $$;

drop trigger if exists trg_variante_ean on public.producto_variantes;
create trigger trg_variante_ean
  before insert or update on public.producto_variantes
  for each row execute function public.fn_variante_ean();

-- Al cambiar un código en un maestro o el formato, se recalculan las
-- variantes automáticas afectadas (el update dispara trg_variante_ean).
create or replace function public.fn_regenerar_ean_maestro()
returns trigger
language plpgsql
set search_path to 'public'
as $$
begin
  if tg_table_name = 'productos' then
    update producto_variantes set ean_manual = false where not ean_manual and id_producto = new.id_producto;
  elsif tg_table_name = 'colores' then
    update producto_variantes set ean_manual = false where not ean_manual and id_color = new.id_color;
  elsif tg_table_name = 'tallas' then
    update producto_variantes set ean_manual = false where not ean_manual and id_talla = new.id_talla;
  else
    update producto_variantes set ean_manual = false where not ean_manual;
  end if;
  return new;
end $$;

drop trigger if exists trg_productos_ean on public.productos;
create trigger trg_productos_ean
  after update of codigo_ean on public.productos
  for each row when (old.codigo_ean is distinct from new.codigo_ean)
  execute function public.fn_regenerar_ean_maestro();

drop trigger if exists trg_colores_ean on public.colores;
create trigger trg_colores_ean
  after update of codigo_ean on public.colores
  for each row when (old.codigo_ean is distinct from new.codigo_ean)
  execute function public.fn_regenerar_ean_maestro();

drop trigger if exists trg_tallas_ean on public.tallas;
create trigger trg_tallas_ean
  after update of codigo_ean on public.tallas
  for each row when (old.codigo_ean is distinct from new.codigo_ean)
  execute function public.fn_regenerar_ean_maestro();

drop trigger if exists trg_parametros_ean on public.parametros_sistema;
create trigger trg_parametros_ean
  after update of ean_prefijo, ean_digitos_producto, ean_digitos_color, ean_digitos_talla on public.parametros_sistema
  for each row execute function public.fn_regenerar_ean_maestro();

-- Devuelve la variante de producto + color + talla, creándola si no existe
-- (para poder emitir etiquetas de tallas que aún no tienen variante).
create or replace function public.obtener_variante(p_id_producto bigint, p_id_color bigint, p_id_talla bigint)
returns setof public.producto_variantes
language plpgsql
set search_path to 'public'
as $$
begin
  insert into producto_variantes (id_producto, id_color, id_talla, precio_venta, descripcion)
  select p.id_producto, p_id_color, p_id_talla, coalesce(p.precio, 0)::integer, p.descripcion
    from productos p
   where p.id_producto = p_id_producto
  on conflict (id_producto, id_color, id_talla) do nothing;

  return query
    select * from producto_variantes
     where id_producto = p_id_producto and id_color = p_id_color and id_talla = p_id_talla;
end $$;

-- ---------------------------------------------------------------------
-- 5. Vista para el registro de códigos EAN (RF-016)
-- ---------------------------------------------------------------------
create or replace view public.v_codigos_ean
with (security_invoker = true) as
select pv.id_variante,
       pv.id_producto,
       coalesce(p.codigo, p.id_producto::text) as codigo_articulo,
       p.descripcion,
       pv.id_color,
       c.descripcion                           as color,
       pv.id_talla,
       coalesce(t.nombre, t.talla::text)       as talla,
       pv.codigo_ean,
       pv.ean_manual,
       pv.activo
  from producto_variantes pv
  join productos p     on p.id_producto = pv.id_producto
  left join colores c  on c.id_color = pv.id_color
  left join tallas t   on t.id_talla = pv.id_talla;

commit;
