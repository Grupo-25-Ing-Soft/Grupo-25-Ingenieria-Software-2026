-- =====================================================================
-- Incremento 4: campos del Documento 0 que faltaban en la base.
--
--   RF-001  clientes: giro, segundo teléfono, número de lista de precios y
--           vendedor asociado (código de vendedor).
--   RF-013 / CU-13.5  precios por talla y color (en cada variante):
--           precio costo, precio detalle, precio liquidación y si aplica la
--           liquidación. producto_variantes.precio_venta es el precio mayor de
--           la lista 1; los precios mayores de otras listas ("cantidad
--           virtualmente ilimitada") van en variante_precios_lista.
--   RF-029  facturas: fecha límite de pago.
--
-- Solo agrega columnas y una tabla; no borra ni cambia datos. Es idempotente y
-- se ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- RF-001: clientes
-- ---------------------------------------------------------------------
alter table public.clientes
  add column if not exists giro          text,
  add column if not exists telefono_2    text,
  add column if not exists lista_precios smallint not null default 1 check (lista_precios >= 1),
  add column if not exists id_vendedor   bigint references public.vendedores (id_vendedor);

create index if not exists clientes_id_vendedor_idx on public.clientes (id_vendedor);

-- ---------------------------------------------------------------------
-- RF-013 / CU-13.5: precios de cada variante (producto + color + talla)
-- ---------------------------------------------------------------------
alter table public.producto_variantes
  add column if not exists precio_costo       integer not null default 0 check (precio_costo >= 0),
  add column if not exists precio_detalle     integer not null default 0 check (precio_detalle >= 0),
  add column if not exists precio_liquidacion integer not null default 0 check (precio_liquidacion >= 0),
  add column if not exists en_liquidacion     boolean not null default false;

comment on column public.producto_variantes.precio_venta is
  'Precio mayor de la lista de precios 1 (las demás listas están en variante_precios_lista).';

create table if not exists public.variante_precios_lista (
  id_variante   bigint   not null references public.producto_variantes (id_variante) on delete cascade,
  lista_precios smallint not null check (lista_precios >= 2),
  precio        integer  not null check (precio >= 0),
  primary key (id_variante, lista_precios)
);

-- Mismas políticas abiertas que el resto de las tablas: la publishable key solo
-- vive en el servidor Flask (.env), que es quien aplica los permisos.
alter table public.variante_precios_lista enable row level security;
drop policy if exists "Enable all access for all users" on public.variante_precios_lista;
create policy "Enable all access for all users" on public.variante_precios_lista
  for all using (true) with check (true);

-- ---------------------------------------------------------------------
-- RF-029: fecha límite de pago de la factura
-- ---------------------------------------------------------------------
alter table public.facturas
  add column if not exists fecha_vencimiento date;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'facturas_vencimiento_check') then
    alter table public.facturas add constraint facturas_vencimiento_check
      check (fecha_vencimiento is null or fecha_vencimiento >= fecha_emision);
  end if;
end $$;

commit;

-- Comprobación: columnas nuevas (es lo que muestra el SQL Editor).
select table_name as tabla, column_name as columna, data_type as tipo
  from information_schema.columns
 where table_schema = 'public'
   and ((table_name = 'clientes' and column_name in ('giro', 'telefono_2', 'lista_precios', 'id_vendedor'))
     or (table_name = 'producto_variantes' and column_name in ('precio_costo', 'precio_detalle', 'precio_liquidacion', 'en_liquidacion'))
     or (table_name = 'variante_precios_lista')
     or (table_name = 'facturas' and column_name = 'fecha_vencimiento'))
 order by 1, 2;
