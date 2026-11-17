-- =====================================================================
-- Datos iniciales (DML). Obligatorio en una base nueva.
--
-- Se ejecuta después de todos los scripts de base_de_datos/DDL/.
-- Volver a ejecutarlo no cambia nada.
--
-- parametros_sistema tiene una sola fila (id = 1) con los datos de la empresa,
-- la moneda, el impuesto y el formato de los códigos EAN. Las columnas toman sus
-- valores por defecto y se editan después en la pantalla Configuración.
-- Sin esta fila no se pueden generar códigos EAN (fn_generar_ean la lee).
--
-- No hay más datos iniciales: el primer usuario se crea en la pantalla de
-- inicio de sesión y queda como superusuario; los roles, las tallas, los
-- colores y el resto de los maestros se ingresan desde la aplicación.
-- =====================================================================

insert into public.parametros_sistema (id)
values (1)
on conflict (id) do nothing;
