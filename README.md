# Sistema administrativo Comercial D Nix — Grupo 25

Sistema web para la confección y venta al por mayor de ropa interior: archivos maestros,
producción (cortes e ingreso a bodega), ventas (pedidos, facturas, notas de crédito y pagos),
inventario por bodega, despachos, informes, y usuarios con permisos por rol.

Hecho con Python y Flask (toda la lógica está en `realFlask.py`), plantillas Jinja en
`templates/` y una base PostgreSQL en Supabase.

## Requisitos

- Python 3.12 o superior.
- Un proyecto de Supabase. **La base está en la nube: el equipo que ejecuta el sistema
  necesita conexión a internet.** Bootstrap y los íconos se sirven desde `static/vendor`, así
  que las pantallas cargan sin internet; solo los datos dependen de la conexión con Supabase.

## Instalación

```
python -m venv .venv
.venv\Scripts\activate        (Windows)   o   source .venv/bin/activate   (Linux/macOS)
pip install -r requirements.txt
```

Copia `env.example` como `.env` y completa:

| Variable | Para qué sirve |
|---|---|
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | Conexión con Supabase. |
| `FLASK_SECRET_KEY` | Firma las sesiones. Si falta, la app genera una y la guarda en `.flask_secret_key` (no se versiona). |
| `FLASK_DEBUG` | `1` solo en equipos de desarrollo (activa el depurador). Vacío en el equipo de la empresa. |

`.env`, `env.env` y `.flask_secret_key` no se suben al repositorio.

## Base de datos

El esquema son los scripts de `supabase/`. En una base nueva se ejecutan en el SQL Editor de
Supabase en este orden (el detalle está al inicio de `supabase/00_esquema_base.sql`):

1. `00_esquema_base.sql`
2. `inventario.sql`
3. `facturas.sql`, `notas_credito.sql`, `pagos.sql`, `parametros_sistema.sql`, `roles.sql`
4. `incremento3_despachos.sql`
5. `incremento3_ean.sql`
6. `incremento4_campos_documento0.sql`
7. `incremento4_feedback.sql`
8. `incremento4_despachos.sql`
9. `incremento4_inventario_variantes.sql`
10. `incremento4_limpieza.sql` (opcional)
11. `incremento4_ingreso_produccion.sql`

Los scripts posteriores reemplazan funciones y vistas de los anteriores: sobre la base
actual no se vuelve a ejecutar uno antiguo.

## Ejecutar

```
python realFlask.py
```

Abre http://127.0.0.1:5000. La primera vez, el sistema pide crear el primer usuario, que queda
como superusuario y puede crear los roles y usuarios.

## Pruebas

```
python -m pytest tests
```

Las pruebas usan `tests/supabase_falso.py`, que simula Supabase en memoria: no tocan la base
real. `python tests/servidor_prueba.py` levanta la app con esos datos en http://127.0.0.1:5050.

## Estructura

- `realFlask.py`: rutas, control de acceso y lógica.
- `templates/`: pantallas (`_sidebar.html` es el menú; `_informe_base.html`, la base de los informes).
- `static/`: estilos, scripts y `vendor/` (Bootstrap 5.3.8 y Bootstrap Icons 1.13.1).
- `supabase/`: scripts del esquema.
- `tests/`: pruebas automáticas; `pruebas/`: scripts y lista de chequeo manuales.
- `backend/`: prototipo antiguo en Node.js y MongoDB. El sistema no lo usa.
