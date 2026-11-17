-- =====================================================================
-- Incremento 4: elimina las funciones antiguas de búsqueda buscar*.
--
-- Eran la búsqueda del Incremento 1 (supabase.rpc('buscarclienteid', ...)). La app ya
-- no usa ninguna: cada pantalla filtra con su barra de búsqueda. Las que buscan por un
-- id o una fecha aplican to_tsvector() a una columna bigint o date y fallan siempre;
-- las demás funcionan, pero tampoco se usan.
--
-- Definiciones exportadas de Supabase el 21/10/2026. Es idempotente ("if exists") y se
-- ejecuta completo en el SQL Editor; si algo falla, no se aplica nada.
-- =====================================================================
begin;

drop function if exists public.buscarbodegadescripcion(text);
drop function if exists public.buscarbodegaid(text);
drop function if exists public.buscarclienteabreviacion(text);
drop function if exists public.buscarclienteid(text);
drop function if exists public.buscarclientenombre(text);
drop function if exists public.buscarcolorcodigo(text);
drop function if exists public.buscarcolordescripcion(text);
drop function if exists public.buscarcolorid(text);
drop function if exists public.buscarcorteid(text);
drop function if exists public.buscarpedidoid(text);
drop function if exists public.buscarpedidoporcliente(text);
drop function if exists public.buscarpedidoporfecha(text);
drop function if exists public.buscarpedidoporfecha(date);
drop function if exists public.buscarpedidoporfechaentrega(text);
drop function if exists public.buscarpedidoporfechaentrega(date);
drop function if exists public.buscarpedidoporvendedor(text);
drop function if exists public.buscarproductoabreviacion(text);
drop function if exists public.buscarproductodescripcion(text);
drop function if exists public.buscarproductoid(text);
drop function if exists public.buscartallaid(text);
drop function if exists public.buscartallanumerotalla(text);
drop function if exists public.buscarvendedorid(text);
drop function if exists public.buscarvendedornombre(text);
drop function if exists public.buscarzonaventadescripcion(text);
drop function if exists public.buscarzonaventaid(text);

commit;

-- Comprobación (es lo que muestra el SQL Editor): no debe quedar ninguna fila.
select p.proname as funcion, pg_get_function_identity_arguments(p.oid) as argumentos
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public' and p.proname like 'buscar%';
