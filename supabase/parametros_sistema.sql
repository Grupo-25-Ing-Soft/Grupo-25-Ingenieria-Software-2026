create table if not exists public.parametros_sistema (
  id smallint primary key default 1 check (id = 1),
  razon_social text not null default '',
  rut text not null default '',
  giro text not null default '',
  direccion text not null default '',
  telefono text not null default '',
  correo text not null default '',
  moneda varchar(10) not null default 'CLP',
  formato_moneda varchar(40) not null default '$#,##0',
  porcentaje_impuesto numeric(5, 2) not null default 0 check (porcentaje_impuesto between 0 and 100),
  logotipo text not null default 'img/logo.png',
  fecha_actualizacion timestamptz not null default now(),
  usuario_actualizacion text not null default 'Admin'
);

insert into public.parametros_sistema (id)
values (1)
on conflict (id) do nothing;
