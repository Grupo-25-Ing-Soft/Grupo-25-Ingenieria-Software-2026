# CLAUDE.md: Sistema administrativo Comercial D Nix (Grupo 25)

Proyecto de Ingeniería de Software (UNAB, 2026) del Grupo 25. Es un sistema administrativo para
**Comercial D Nix**, una empresa que confecciona ropa interior femenina y la vende al por mayor.
Reemplaza un sistema de escritorio de ~2001 sin base de datos. Cubre archivos maestros,
producción (cortes, ingreso a bodega), pedidos, facturación, cobranza, inventario e informes.

Se desarrolla con **Scrum++** en 4 incrementos. Los incrementos 1 a 3 están entregados y el
**Incremento 4** está en curso (término previsto: 15/11/2026).

Responde y escribe en **español**: código nuevo, mensajes al usuario, comentarios y commits.

## Documentación funcional: léela antes de implementar

La especificación está en `docs/`. **No** se carga sola: abre el archivo que corresponda cuando
lo necesites.

| Archivo | Qué contiene | Cuándo leerlo |
| --- | --- | --- |
| `docs/casos-de-uso.md` | 79 casos de uso del Documento 0 (CU-01.1 a CU-60.1): actores, precondiciones, flujo, excepciones, postcondición | Antes de implementar o modificar cualquier funcionalidad |
| `docs/casos-de-uso-incremento-2.md` | 38 CU del Incremento 2: facturas, notas de crédito, pagos, inventario, costos, configuración, interfaz, más versiones detalladas de otros | Cuando el CU no está en el archivo anterior o necesitas más detalle |
| `docs/requerimientos.md` | RF-001 a RF-061, RNF-001 a RNF-015, tabla ESA, usuarios | Para saber qué exige un RF o un RNF |
| `docs/matriz-rf-cu.md` | Relación RF → CU e inconsistencias conocidas entre documentos | Para encontrar el CU de un RF |
| `docs/glosario.md` | Términos del negocio y **formatos de datos** (largos de códigos, fechas, porcentajes) | Al validar campos o nombrar cosas |
| `docs/modelo-datos.md` | Modelo relacional y qué crea cada script de `supabase/` | Al tocar consultas o tablas |
| `docs/estado-y-planificacion.md` | RF por incremento, cambios del Incremento 3, pruebas PR-01 a PR-13, **backlog del Incremento 4** | Para saber qué está hecho y qué falta |

Busca por código: `grep -n "### CU-22.3" docs/*.md` o `grep -n "RF-046" docs/*.md`.

### Cómo usar los casos de uso

- La **numeración** sigue al RF: CU-13 implementa RF-013. Los sufijos .1 a .4 son registrar,
  consultar, modificar y eliminar. Los siguientes son comportamientos complementarios
  (CU-01.5: validar RUT).
- Implementa el **flujo y todas las excepciones** del CU. Cada `[Excepción N]` es un caso que
  la interfaz tiene que manejar con un mensaje claro (RNF-006).
- Si el Documento 0 y el Incremento 2 describen distinto el mismo CU, o si el CU contradice el
  código o el modelo de datos, **señálalo** antes de decidir. No elijas una versión en silencio.
- Cita el RF y el CU en los commits y PR (por ejemplo, "RF-046 / CU-46: filtro por factura").

### RNF que aplican a todo

- **RNF-006:** los errores de validación nombran el campo y explican el criterio, sin tecnicismos.
- **RNF-007:** toda eliminación pide confirmación y muestra qué registro se va a borrar.
- **RNF-003/004:** la interfaz se usa con mouse salvo para escribir, y cada campo y botón tiene
  etiqueta clara. Los tipos de precio (costo, detalle, mayor, liquidación) se nombran explícitamente.
- **RNF-005:** los listados tienen scroll vertical.
- **RNF-012:** las operaciones que tocan varias tablas (despachos, stock) van en una transacción.
  Por eso se implementan como funciones SQL (`registrar_despacho`, `anular_despacho`, `registrar_defectuosos`).

## Stack y estructura

- **Backend:** Flask, todo en `realFlask.py`. Rutas con sufijo `.html` (`/clientes.html`) y
  sin blueprints.
- **BD:** PostgreSQL en **Supabase**, accedido con el cliente Python
  (`supabase.table("x").select(...).eq(...).execute()`). No hay SQL directo en la app (ver
  `Instrucciones SQL`). Las migraciones están en `supabase/*.sql`.
- **Vistas:** plantillas Jinja en `templates/`, Bootstrap 5.3.8 y Bootstrap Icons por CDN, más
  `static/app.css`. **No hay plantilla base:** cada página repite la barra lateral
  (`shared-sidebar`) y la superior. Si agregas una página o un enlace al menú, actualiza todas.
  Los avisos usan `{% include '_flash_toast.html' %}`.
- **Tablas de informes:** `static/report_helpers.js` (`renderReportTable`, `flatten*`). La ruta
  pasa los datos como JSON en un `<input type="hidden">` y el JS dibuja la tabla.
- **Formularios:** casi todos son POST con un campo oculto `_method` que indica la operación
  (`get`, `buscarClientes`, `buscarFacturas`, ...). La ruta hace `if metodo == ...`. Los valores
  del formulario y de la ruta tienen que coincidir exactamente.
- **EAN-13:** `ean13.py`, más las funciones `fn_*ean*` en `supabase/incremento3_ean.sql`.
- **PDF:** reportlab (por ejemplo, `/informeCobranza.pdf`).
- `backend/`: prototipo antiguo en Node/Express + Mongo. **No es la app activa**; no lo modifiques salvo que te lo pidan.

## Cómo correr

```bash
pip install -r requirements.txt
# .env en la raíz (no se versiona): SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY
# opcionales: FLASK_SECRET_KEY, SYSTEM_USER
python realFlask.py                 # http://127.0.0.1:5000 (debug)
```

Sin acceso a Supabase:

```bash
python -m pytest                    # pruebas con Supabase simulado (tests/supabase_falso.py)
python tests/servidor_prueba.py     # app completa con datos falsos en http://127.0.0.1:5050
```

- `tests/supabase_falso.py` implementa en memoria solo lo que usan las pruebas. Si una prueba
  nueva necesita otra tabla u operador, agrégalo ahí.
- `pruebas/verificar_paginas_supabase.py` y `pruebas/validar_funcionalidades_incremento3.py`
  corren contra la **base real**. `pruebas/checklist_navegador.md` es la lista de verificación manual.
- Después de cambiar una ruta o plantilla, corre `pytest` y abre la página en el servidor de prueba.

## Convenciones del repo

- Las ramas son líneas de trabajo o versiones del programa (`nueva-interfaz`, `incremento-3-bd`,
  `integracion-final`, ...). No todo se fusiona en `main`. Trabaja en una rama y no hagas push a
  `main` sin que te lo pidan.
- **Nunca** versiones `.env` ni credenciales. El `.gitignore` ya lo excluye.
- **Finales de línea:** muchas plantillas usan CRLF (Windows) y otras LF. Respeta el que ya tiene
  cada archivo. Si cambias el archivo entero de formato, el diff ensucia las fusiones.
- Al fusionar ramas, revisa si la subida de un lado partió de una copia antigua: ya pasó que un
  "Add files via upload" revirtiera informes que estaban implementados.

## Estado conocido del código (octubre 2026)

- Las plantillas `facturas.html`, `crudDetallePedido.html`, `verDetalle.html` y
  `notascredito.html` (minúscula) **no tienen ruta**. La de notas de crédito activa es
  `notasCredito.html`. Las dos difieren solo en mayúsculas, así que chocan en Windows y macOS.
- `informeProductosDespachados`: la columna "facturas" muestra la razón social en vez del número
  de factura (`readTextValue` prefiere `razon_social`).
- `analisisProductosPedidosDespachados.html` (RF-044) está en desarrollo y es parte del Incremento 4.
- Las tablas `ventas` y `detalle_ventas` no se usan.
- No hay autenticación ni roles todavía (RF-057, RF-058; Incremento 4).
- El backlog del Incremento 4 incluye migrar de Supabase a una base local (RNF-011), unificar
  `productos`/`producto_variantes` y el CRUD de despachos. Ver `docs/estado-y-planificacion.md`.
