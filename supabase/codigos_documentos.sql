-- Soporte del campo de negocio usado por la interfaz de cortes, pedidos y facturas.
-- Idempotente. Conserva ids, folios, números y códigos existentes. No rellena datos.
BEGIN;
ALTER TABLE public.cortes ADD COLUMN IF NOT EXISTS codigo text;
ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS codigo text;
ALTER TABLE public.facturas ADD COLUMN IF NOT EXISTS codigo text;
COMMIT;
