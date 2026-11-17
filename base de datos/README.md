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

Los scripts están en `base_de_datos/`, separados en `DDL/` (estructura) y `DML/` (datos). El
detalle de cada uno está en `base_de_datos/README.md`.

En una base nueva se ejecutan en el SQL Editor de Supabase en este orden:

1. Los 18 scripts de `base_de_datos/DDL/`, por su número (`01_esquema_base.sql` a
   `18_incremento4_feedback_documentos.sql`). El 14 es opcional.
2. `base_de_datos/DML/01_datos_iniciales.sql`.
3. Opcional, solo para pruebas: `base_de_datos/DML/02_datos_prueba.sql`.

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

| Parte | Dónde está |
|---|---|
| Vistas | `templates/` (pantallas en Jinja; `_sidebar.html` es el menú e `_informe_base.html`, la base de los informes) y `static/` (estilos, scripts y `vendor/` con Bootstrap 5.3.8 y Bootstrap Icons 1.13.1). |
| Controladores | `realFlask.py`: rutas, control de acceso y lógica. `ean13.py`: cálculo de códigos EAN. |
| Base de datos | `base_de_datos/DDL/` y `base_de_datos/DML/`. |

Además:

- `tests/`: pruebas automáticas; `pruebas/`: scripts y lista de chequeo manuales.
- `launcher.py`, `ComercialDNix.spec`, `instalador.iss` e `instalador/`: empaquetado como aplicación de escritorio.
- `backend/`: prototipo antiguo en Node.js y MongoDB. El sistema no lo usa.
