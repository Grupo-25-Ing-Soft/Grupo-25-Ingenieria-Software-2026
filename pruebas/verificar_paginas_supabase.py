"""Safe, fail-closed verification of report pages against the configured Supabase."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from realFlask import app, supabase  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TEST_DIR = Path(__file__).resolve().parent
LAST_RUN_FILE = TEST_DIR / "ultimo_run.json"


class VerificationError(RuntimeError):
    """An error with a deliberately sanitized, script-generated message."""


TABLES = (
    "zona_venta",
    "clientes",
    "vendedores",
    "colores",
    "tallas",
    "productos",
    "producto_variantes",
    "bodegas",
    "pedidos",
    "detalle_pedidos",
    "cortes",
    "despachos",
    "inventario",
    "facturas",
)

PRIMARY_KEYS = {
    "zona_venta": "id_zona_venta",
    "clientes": "id_cliente",
    "vendedores": "id_vendedor",
    "colores": "id_color",
    "tallas": "id_talla",
    "productos": "id_producto",
    "producto_variantes": "id_variante",
    "bodegas": "id_bodega",
    "pedidos": "id_pedido",
    "detalle_pedidos": "id_detalle_pedido",
    "despachos": "id_despacho",
    "cortes": "id_corte",
    "inventario": "id_inventario",
    "facturas": "id_factura",
}

MARKER_COLUMNS = {
    "zona_venta": "descripcion",
    "clientes": "nombre",
    "vendedores": "nombre",
    "colores": "descripcion",
    "tallas": "nombre",
    "productos": "descripcion",
    "producto_variantes": "descripcion",
    "bodegas": "descripcion",
    "pedidos": "motivo_anulacion",
    "detalle_pedidos": "observacion",
    "cortes": "observaciones",
    "despachos": "observacion",
    "inventario": "usuario_actualizacion",
    "facturas": "razon_social",
}

SEEDED_TABLES = (
    "zona_venta",
    "clientes",
    "vendedores",
    "colores",
    "tallas",
    "productos",
    "producto_variantes",
    "bodegas",
    "pedidos",
    "detalle_pedidos",
    "cortes",
    "despachos",
    "inventario",
)

# Mandatory fields and relationships below are taken from the DDL supplied
# by the user for detalle_pedidos and despachos. Their PKs have no DEFAULT.
SUPPLIED_DDL_COLUMNS = {
    "detalle_pedidos": {
        "id_detalle_pedido", "id_pedido", "id_variante", "cantidad",
        "precio_unitario", "subtotal", "observacion", "cantidad_anulada",
    },
    "despachos": {
        "id_despacho", "numero_guia", "fecha", "id_pedido", "id_factura",
        "id_bodega", "via_despacho", "observacion", "estado",
        "motivo_anulacion", "fecha_anulacion", "usuario_creacion", "creado_en",
    },
}

PAGES = (
    ("/informeProductosTerminados.html", True),
    ("/informeProductosEnProceso.html", True),
    ("/informeProductosPendientesDespacho.html", True),
    ("/informeProductosDespachados.html", True),
    ("/analisisDespachoClienteProducto.html", True),
    ("/analisisDespachoVendedorProducto.html", True),
    ("/analisisPedidosDespachosMensuales.html", True),
    ("/analisisDespachoSegunFacturaCliente.html", True),
    ("/analisisVentasDescuentos.html", True),
    ("/analisisProductosPedidosDespachados.html", False),
    ("/resumenProduccion.html", True),
    ("/inventario.html", True),
    ("/reportes.html", False),
    ("/facturas.html", True),
    ("/crudDetallePedido.html", True),
    ("/verDetalle.html", False),
)

DEVELOPMENT_POSTS = {
    "/informeProductosDespachados.html",
    "/analisisDespachoSegunFacturaCliente.html",
    "/analisisVentasDescuentos.html",
    "/resumenProduccion.html",
    "/inventario.html",
}

RELATION_PROBES = (
    ("pedidos", "*, detalle_pedidos!inner(id_variante)", "pedidos -> detalle_pedidos"),
    ("despachos", "*, pedidos!inner(id_pedido)", "despachos -> pedidos"),
    (
        "cortes",
        "producto_asociado, cantidad, productos(descripcion, color(descripcion), talla(talla))",
        "cortes -> productos -> color/talla",
    ),
    ("clientes", "*, zona_venta!inner(id_zona_venta)", "clientes -> zona_venta"),
    ("productos", "*, colores!inner(id_color), tallas!inner(id_talla)", "productos -> color/talla"),
    (
        "detalle_pedidos",
        "*, producto_variantes!inner(id_variante)",
        "detalle_pedidos -> producto_variantes",
    ),
    (
        "inventario",
        "*, bodegas!inner(id_bodega), productos!inner(id_producto), "
        "tallas!inner(id_talla), colores!inner(id_color)",
        "inventario -> bodega/producto/talla/color",
    ),
    (
        "pedidos",
        "*, clientes!inner(id_cliente), vendedores!inner(id_vendedor)",
        "pedidos -> cliente/vendedor",
    ),
)


def safe_error(exc: Exception) -> str:
    if isinstance(exc, VerificationError):
        return f"{type(exc).__name__}: {exc}"
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    code = getattr(exc, "code", None)
    parts = [type(exc).__name__]
    if status is not None:
        parts.append(f"HTTP {status}")
    if code:
        parts.append(f"código {code}")
    return ", ".join(parts)


def parse_sql_columns() -> dict[str, set[str]]:
    sql_dir = PROJECT_ROOT / "supabase"
    table_columns: dict[str, set[str]] = {}
    create_table = re.compile(
        r"create\s+table\s+if\s+not\s+exists\s+public\.(\w+)\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    column_line = re.compile(r"^\s*([a-zA-Z_]\w*)\s+(?:bigint|smallint|integer|"
                             r"text|varchar|numeric|date|timestamptz|boolean)\b",
                             re.IGNORECASE)
    for sql_path in sql_dir.glob("*.sql"):
        source = sql_path.read_text(encoding="utf-8")
        for match in create_table.finditer(source):
            table_name, declaration = match.groups()
            columns = set()
            for line in declaration.splitlines():
                column_match = column_line.match(line)
                if column_match:
                    columns.add(column_match.group(1))
            table_columns[table_name] = columns
    return table_columns


def discover_schema() -> tuple[dict[str, set[str]], list[str], list[str]]:
    live_columns: dict[str, set[str]] = {}
    findings: list[str] = []
    blockers: list[str] = []
    sql_columns = parse_sql_columns()

    print("ESQUEMA (SELECT * LIMIT 1; no se imprimen valores de registros)")
    for table in TABLES:
        try:
            response = supabase.table(table).select("*").limit(1).execute()
        except Exception as exc:
            findings.append(f"{table}: lectura de esquema falló ({safe_error(exc)})")
            blockers.append(f"No se pudo descubrir el esquema de {table}.")
            print(f"- {table}: ERROR {safe_error(exc)}")
            continue

        rows = response.data or []
        if rows:
            live_columns[table] = set(rows[0].keys())
            print(f"- {table}: columnas visibles={', '.join(sorted(live_columns[table]))}")
        elif table in SUPPLIED_DDL_COLUMNS:
            live_columns[table] = SUPPLIED_DDL_COLUMNS[table]
            print(f"- {table}: sin filas visibles; columnas derivadas del DDL proporcionado")
        elif table in sql_columns:
            live_columns[table] = sql_columns[table]
            print(f"- {table}: sin filas visibles; columnas derivadas del SQL local")
        else:
            findings.append(f"{table}: no hay fila visible ni DDL local")
            print(f"- {table}: sin filas visibles y sin definición SQL local")

    for table, ddl_set in sql_columns.items():
        if table in live_columns and live_columns[table] and live_columns[table] != ddl_set:
            only_live = sorted(live_columns[table] - ddl_set)
            only_ddl = sorted(ddl_set - live_columns[table])
            if only_live or only_ddl:
                findings.append(
                    f"{table}: esquema Supabase difiere de supabase/{table}.sql "
                    f"(solo live: {only_live}; solo SQL: {only_ddl})"
                )

    print("RELACIONES (consultas PostgREST con limit(0))")
    for table, projection, label in RELATION_PROBES:
        try:
            supabase.table(table).select(projection).limit(0).execute()
            print(f"- {label}: confirmada")
        except Exception as exc:
            message = f"{label}: no confirmada ({safe_error(exc)})"
            findings.append(message)
            print(f"- {message}")
            blockers.append(f"No se confirmó la relación {label}.")

    for table, expected_columns in SUPPLIED_DDL_COLUMNS.items():
        actual_columns = live_columns.get(table, set())
        if actual_columns and not expected_columns.issubset(actual_columns):
            blockers.append(
                f"{table}: las columnas vivas no coinciden con el DDL proporcionado."
            )

    for table in SEEDED_TABLES:
        if not live_columns.get(table):
            blockers.append(f"{table}: no se confirmaron columnas antes de sembrar.")

    if blockers:
        print("HALLAZGOS DE ESQUEMA")
        for finding in findings:
            print(f"- {finding}")
        print("BLOQUEOS PREVIOS A ESCRITURA")
        for blocker in dict.fromkeys(blockers):
            print(f"- {blocker}")

    return live_columns, findings, list(dict.fromkeys(blockers))


def route_methods() -> dict[str, set[str]]:
    methods: dict[str, set[str]] = {}
    for rule in app.url_map.iter_rules():
        methods.setdefault(rule.rule, set()).update(rule.methods - {"HEAD", "OPTIONS"})
    return methods


def next_explicit_id(table: str, primary_key: str, run_id: str, offset: int) -> int:
    candidate = int(run_id) * 100000 + offset
    if candidate > 9_223_372_036_854_775_807:
        raise VerificationError(f"El ID de prueba para {table} excede bigint.")
    existing = (
        supabase.table(table)
        .select(primary_key)
        .eq(primary_key, candidate)
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing:
        raise VerificationError(f"El ID candidato para {table} ya existe; no se reintentará.")
    return candidate


def insert_tracked(
    table: str,
    payload: dict[str, Any],
    marker_column: str,
    live_columns: dict[str, set[str]],
    records: list[dict[str, Any]],
    explicit_id: int | None = None,
) -> dict[str, Any]:
    primary_key = PRIMARY_KEYS[table]
    if marker_column not in payload or not str(payload[marker_column]).startswith("ZZTEST_"):
        raise VerificationError(f"{table}: cada inserción debe incluir su marcador ZZTEST.")
    unavailable = set(payload) - live_columns.get(table, set())
    if unavailable:
        raise VerificationError(
            f"{table}: columnas de inserción no confirmadas: {sorted(unavailable)}."
        )
    if explicit_id is not None:
        if primary_key in payload:
            raise VerificationError(f"{table}: ID explícito duplicado en payload.")
        payload[primary_key] = explicit_id

    try:
        response = supabase.table(table).insert(payload).select(primary_key).execute()
    except Exception as exc:
        raise VerificationError(f"INSERT {table} falló ({safe_error(exc)}).") from None
    rows = response.data or []
    if len(rows) != 1 or rows[0].get(primary_key) is None:
        raise VerificationError(f"INSERT {table} no devolvió exactamente un {primary_key}.")
    record_id = rows[0][primary_key]
    records.append(
        {
            "tabla": table,
            "columna_pk": primary_key,
            "id": record_id,
            "columna_marcador": marker_column,
            "marcador": payload[marker_column],
        }
    )
    return rows[0]


def verify_insert(
    table: str, primary_key: str, record_id: Any, marker_column: str, marker: str
) -> dict[str, Any]:
    rows = (
        supabase.table(table)
        .select(f"{primary_key},{marker_column}")
        .eq(primary_key, record_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if len(rows) != 1 or rows[0].get(marker_column) != marker:
        raise VerificationError(f"Verificación directa de {table} id={record_id} no coincidió.")
    return rows[0]


def seed_data(
    run_id: str,
    live_columns: dict[str, set[str]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    marker = f"ZZTEST_{run_id}"
    today = date.today().isoformat()
    ids: dict[str, Any] = {}

    def create(table: str, payload: dict[str, Any], marker_column: str, offset: int | None = None):
        explicit = (
            next_explicit_id(table, PRIMARY_KEYS[table], run_id, offset)
            if offset is not None
            else None
        )
        result = insert_tracked(
            table, payload, marker_column, live_columns, records, explicit_id=explicit
        )
        record_id = result[PRIMARY_KEYS[table]]
        verify_insert(table, PRIMARY_KEYS[table], record_id, marker_column, payload[marker_column])
        print(f"INSERT confirmado: {table} id={record_id}")
        return record_id

    ids["zona"] = create(
        "zona_venta", {"descripcion": f"{marker}_ZONA"}, "descripcion"
    )
    ids["cliente"] = create(
        "clientes",
        {
            "rut": f"9{run_id[-8:]}",
            "nombre": f"{marker}_CLIENTE",
            "correo": f"{run_id}@example.invalid",
            "telefono": "000000000",
            "direccion": f"{marker}_DIRECCION",
            "digito_verificador": "0",
            "abreviacion": f"Z{run_id[-7:]}",
            "ciudad": f"{marker}_CIUDAD",
            "comuna": f"{marker}_COMUNA",
            "condiciones_venta": f"{marker}_CONDICIONES",
            "via_despacho": f"{marker}_VIA",
            "porcentaje_comision": 0,
            "porcentaje_cobranza": 0,
            "observaciones": f"{marker}_CLIENTE",
            "id_zona_venta": ids["zona"],
        },
        "nombre",
    )
    ids["vendedor"] = create(
        "vendedores",
        {
            "rut": f"8{run_id[-8:]}",
            "nombre": f"{marker}_VENDEDOR",
            "digito_verificador": "0",
            "porcentaje_comision": 0,
        },
        "nombre",
    )
    ids["color"] = create(
        "colores",
        {"codigo_color": f"C{run_id[-9:]}", "descripcion": f"{marker}_COLOR"},
        "descripcion",
    )
    talla_numero = 900000 + int(run_id[-6:])
    if (
        supabase.table("tallas")
        .select("id_talla")
        .eq("talla", talla_numero)
        .limit(1)
        .execute()
        .data
    ):
        raise VerificationError(
            "El valor numérico candidato para talla ya existe; no se reintentará."
        )
    ids["talla"] = create(
        "tallas",
        {"talla": talla_numero, "nombre": f"{marker}_TALLA"},
        "nombre",
    )

    ids["productos"] = []
    ids["variantes"] = []
    for line_number in (1, 2):
        product_id = create(
            "productos",
            {
                "abreviacion": f"P{run_id[-7:]}{line_number}",
                "descripcion": f"{marker}_PRODUCTO_{line_number}",
                "color": ids["color"],
                "precio": 100 * line_number,
                "talla": ids["talla"],
            },
            "descripcion",
        )
        ids["productos"].append(product_id)
        variants = (
            supabase.table("producto_variantes")
            .select("id_variante, descripcion")
            .eq("id_producto", product_id)
            .execute()
            .data
            or []
        )
        if len(variants) != 1:
            raise VerificationError(
                f"El alta del producto id={product_id} no produjo exactamente una variante; "
                "se detiene la siembra sin crear detalles ni asumir otra forma de inserción."
            )
        variant = variants[0]
        variant_marker = variant.get("descripcion")
        if not isinstance(variant_marker, str) or not variant_marker.startswith(marker):
            raise VerificationError(
                f"La variante del producto id={product_id} no conserva el marcador de prueba."
            )
        records.append(
            {
                "tabla": "producto_variantes",
                "columna_pk": "id_variante",
                "id": variant["id_variante"],
                "columna_marcador": "descripcion",
                "marcador": variant_marker,
            }
        )
        ids["variantes"].append(variant["id_variante"])
        print(f"Variante derivada confirmada: id_variante={variant['id_variante']}")

    ids["bodega"] = create(
        "bodegas", {"descripcion": f"{marker}_BODEGA"}, "descripcion"
    )
    ids["pedido"] = create(
        "pedidos",
        {
            "cliente_asociado": ids["cliente"],
            "fecha_pedido": today,
            "fecha_entrega": today,
            "vendedor_asociado": ids["vendedor"],
            "estado": "pendiente",
            "motivo_anulacion": marker,
        },
        "motivo_anulacion",
    )

    ids["detalles"] = []
    for line_number, variant_id in enumerate(ids["variantes"], start=1):
        detail_id = create(
            "detalle_pedidos",
            {
                "id_pedido": ids["pedido"],
                "id_variante": variant_id,
                "cantidad": line_number,
                "precio_unitario": 100 * line_number,
                "subtotal": 100 * line_number * line_number,
                "observacion": f"{marker}_DETALLE_{line_number}",
                "cantidad_anulada": 0,
            },
            "observacion",
            offset=line_number,
        )
        ids["detalles"].append(detail_id)

    ids["corte"] = create(
        "cortes",
        {
            "fecha_corte": today,
            "fecha_ingreso": today,
            "cantidad": 7,
            "cortador": f"{marker}_CORTADOR",
            "observaciones": marker,
            "material_usado": f"{marker}_MATERIAL",
            "producto_asociado": ids["productos"][0],
            "id_bodega_ingreso": ids["bodega"],
            "estado": "pendiente",
        },
        "observaciones",
    )
    ids["despacho"] = create(
        "despachos",
        {
            "fecha": today,
            "id_pedido": ids["pedido"],
            "id_bodega": ids["bodega"],
            "observacion": marker,
            "via_despacho": f"{marker}_VIA",
            "estado": "emitido",
        },
        "observacion",
        offset=3,
    )
    ids["inventario"] = create(
        "inventario",
        {
            "id_bodega": ids["bodega"],
            "id_producto": ids["productos"][0],
            "id_talla": ids["talla"],
            "id_color": ids["color"],
            "cantidad": 20,
            "usuario_actualizacion": marker,
        },
        "usuario_actualizacion",
    )
    return {
        "ids": ids,
        "marker": marker,
        "date": today,
        "forms": {
            "/informeProductosTerminados.html": {
                "desdeFecha": today,
                "hastaFecha": today,
            },
            "/informeProductosEnProceso.html": {},
            "/informeProductosPendientesDespacho.html": {},
            "/analisisDespachoClienteProducto.html": {
                "IDCliente": str(ids["cliente"]),
                "IDProducto": str(ids["variantes"][0]),
            },
            "/analisisDespachoVendedorProducto.html": {
                "IDVendedor": str(ids["vendedor"]),
                "IDProducto": str(ids["variantes"][0]),
            },
            "/analisisPedidosDespachosMensuales.html": {
                "desdeFecha": today,
                "hastaFecha": today,
            },
        },
        "select_checks": {
            "/analisisDespachoClienteProducto.html": [
                ("cliente", f"{marker}_CLIENTE"),
                ("producto", f"{marker}_PRODUCTO_1"),
            ],
            "/analisisDespachoVendedorProducto.html": [
                ("vendedor", f"{marker}_VENDEDOR"),
                ("producto", f"{marker}_PRODUCTO_1"),
            ],
        },
    }


def check_pages(
    run_id: str,
    blockers: list[str],
    fixture: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    methods = route_methods()
    today = date.today().isoformat()
    results: list[dict[str, Any]] = []

    with app.test_client() as client:
        for path, accepts_post in PAGES:
            detail = ""
            allowed = methods.get(path)
            if not allowed or "GET" not in allowed:
                results.append(
                    {
                        "ruta": path,
                        "get": "— (sin ruta)",
                        "post": "—",
                        "datos": "No sembrados",
                        "resultado": "OMITIDA",
                        "detalle": "No existe ruta Flask para esta URL.",
                    }
                )
                continue

            try:
                get_response = client.get(path)
                html = get_response.get_data(as_text=True)
                get_ok = get_response.status_code == 200 and 'class="shared-sidebar"' in html
                get_status = str(get_response.status_code)
                if get_response.status_code == 200 and 'class="shared-sidebar"' not in html:
                    get_status += " (sidebar ausente)"
            except Exception as exc:
                get_ok = False
                html = ""
                get_status = f"ERROR ({safe_error(exc)})"

            post_status = "No aplica"
            dev_result = False
            if accepts_post and "POST" in allowed and path in DEVELOPMENT_POSTS:
                form_data = {"desdeFecha": today, "hastaFecha": today} if (
                    path == "/informeProductosDespachados.html"
                ) else {}
                try:
                    post_response = client.post(path, data=form_data)
                    post_html = post_response.get_data(as_text=True)
                    dev_result = (
                        post_response.status_code == 200
                        and "Este informe aún está en desarrollo." in post_html
                    )
                    post_status = str(post_response.status_code)
                    if dev_result:
                        post_status += " (flash de desarrollo)"
                except Exception as exc:
                    post_status = f"ERROR ({safe_error(exc)})"
            elif accepts_post and "POST" in allowed and not blockers and fixture:
                form_data = fixture.get("forms", {}).get(path)
                if form_data is None:
                    post_status = "No aplica"
                else:
                    try:
                        post_response = client.post(path, data=form_data)
                        post_html = post_response.get_data(as_text=True)
                        visible = f"ZZTEST_{run_id}" in post_html
                        post_status = str(post_response.status_code)
                        if not visible:
                            post_status += " (marcador ausente)"
                        elif post_response.status_code == 200:
                            post_status += " (marcador visible)"
                        if post_response.status_code != 200 or not visible:
                            detail = (
                                "POST no devolvió 200."
                                if post_response.status_code != 200
                                else "La respuesta no contiene el marcador de prueba esperado."
                            )
                        else:
                            detail = "GET y POST correctos; el marcador aparece en la respuesta."
                        if path in {
                            "/analisisDespachoClienteProducto.html",
                            "/analisisDespachoVendedorProducto.html",
                        }:
                            select_checks = fixture.get("select_checks", {}).get(path, [])
                            missing = [
                                label for label, text in select_checks if text not in html
                            ]
                            if missing:
                                detail += f" Opciones de prueba ausentes en GET: {', '.join(missing)}."
                                post_status += " (opciones select ausentes)"
                                if post_response.status_code == 200 and visible:
                                    post_status = post_status.replace(
                                        "(marcador visible)", "(marcador visible; opciones select ausentes)"
                                    )
                    except Exception as exc:
                        post_status = f"ERROR ({safe_error(exc)})"
            elif accepts_post and "POST" in allowed:
                post_status = (
                    "Omitido por bloqueo previo a la siembra; no se envió POST con datos"
                    if blockers
                    else "Omitido: datos de formulario no disponibles"
                )
            elif path == "/analisisProductosPedidosDespachados.html":
                post_status = "No admite POST"

            if not get_ok:
                result = "FALLA"
                detail = "GET no devolvió 200 con .shared-sidebar."
            elif dev_result:
                result = "EN DESARROLLO"
                detail = "POST seguro mostró el flash previsto; no se consultó una tabla de resultados."
            elif path == "/analisisProductosPedidosDespachados.html" and (
                "Este análisis está en desarrollo" in html
            ):
                result = "EN DESARROLLO"
                detail = "GET muestra el empty-state previsto."
            elif path == "/reportes.html":
                result = "OK"
                detail = "GET 200 y sidebar presente."
            elif post_status.startswith("ERROR") or "marcador ausente" in post_status or "select ausentes" in post_status:
                result = "FALLA"
                detail = detail or "La prueba POST falló."
            elif "(marcador visible)" in post_status and "opciones select ausentes" not in post_status:
                result = "OK"
                detail = detail or "GET y POST 200; respuesta contiene datos con el marcador de prueba."
            else:
                result = "OMITIDA"
                detail = (
                    "GET comprobado; POST con datos omitido. "
                    f"Bloqueo: {blockers[0]}"
                    if blockers and "POST" in allowed
                    else "GET comprobado; no hay consulta POST que probar."
                )

            results.append(
                {
                    "ruta": path,
                    "get": get_status,
                    "post": post_status,
                    "datos": (
                        f"ZZTEST_{run_id}" if fixture and not blockers
                        else f"Sin semilla ZZTEST_{run_id}"
                    ),
                    "resultado": result,
                    "detalle": detail,
                }
            )

    return results


def print_report(results: list[dict[str, Any]]) -> None:
    print("\nREPORTE POR PÁGINA")
    headers = ("ruta", "GET", "POST", "datos de prueba visibles", "resultado", "detalle del error")
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for result in results:
        row = (
            result["ruta"],
            result["get"],
            result["post"],
            result["datos"],
            result["resultado"],
            result["detalle"],
        )
        print("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")


def save_keep_file(run_id: str, records: list[dict[str, Any]], blockers: list[str]) -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    LAST_RUN_FILE.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "prefix": f"ZZTEST_{run_id}",
                "records": records,
                "schema_blockers": blockers,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def cleanup_records(run_id: str, records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in reversed(records):
        table = record.get("tabla")
        primary_key = record.get("columna_pk")
        record_id = record.get("id")
        marker_column = record.get("columna_marcador")
        marker = record.get("marcador")
        prefix = f"ZZTEST_{run_id}"

        if (
            table not in PRIMARY_KEYS
            or primary_key != PRIMARY_KEYS.get(table)
            or marker_column != MARKER_COLUMNS.get(table)
            or not isinstance(marker, str)
            or not marker.startswith(prefix)
            or record_id is None
        ):
            errors.append(f"{table} id={record_id}: registro de limpieza no válido; no se borró.")
            continue

        try:
            existing = (
                supabase.table(table)
                .select(f"{primary_key},{marker_column}")
                .eq(primary_key, record_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if not existing:
                print(f"LIMPIEZA {table} id={record_id}: ya no existe.")
                continue
            if existing[0].get(marker_column) != marker:
                errors.append(
                    f"{table} id={record_id}: el marcador exacto no coincide; no se borró."
                )
                continue

            (
                supabase.table(table)
                .delete()
                .eq(primary_key, record_id)
                .eq(marker_column, marker)
                .execute()
            )
            remaining = (
                supabase.table(table)
                .select(primary_key)
                .eq(primary_key, record_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if remaining:
                errors.append(f"{table} id={record_id}: sigue presente tras borrar.")
            else:
                print(f"LIMPIEZA {table} id={record_id}: eliminado.")
        except Exception as exc:
            errors.append(f"{table} id={record_id}: borrado falló ({safe_error(exc)}).")

    return errors


def load_last_run() -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
    run_id = payload.get("run_id")
    records = payload.get("records")
    if not isinstance(run_id, str) or not re.fullmatch(r"\d{12}", run_id):
        raise ValueError("run_id inválido en ultimo_run.json.")
    if not isinstance(records, list):
        raise ValueError("records inválido en ultimo_run.json.")
    return run_id, records


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--keep", action="store_true", help="Conserva registros creados y guarda sus IDs.")
    mode.add_argument("--cleanup", action="store_true", help="Borra solo los IDs exactos de ultimo_run.json.")
    args = parser.parse_args()

    if args.cleanup:
        if not LAST_RUN_FILE.exists():
            print("LIMPIEZA: no existe pruebas/ultimo_run.json; no se borró ningún registro.")
            return 0
        try:
            run_id, records = load_last_run()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"LIMPIEZA: no se pudo validar ultimo_run.json ({type(exc).__name__}).")
            return 1
        errors = cleanup_records(run_id, records)
        print("LIMPIEZA: todos los IDs registrados fueron borrados o ya no existían." if not errors else "LIMPIEZA: hubo registros que no se pudieron borrar.")
        for error in errors:
            print(f"- {error}")
        if not errors:
            LAST_RUN_FILE.unlink(missing_ok=True)
        return 0 if not errors else 1

    run_id = datetime.now().strftime("%y%m%d%H%M%S")
    records: list[dict[str, Any]] = []
    cleanup_errors: list[str] = []
    exit_code = 0
    blockers: list[str] = []
    fixture: dict[str, Any] | None = None
    page_results: list[dict[str, Any]] = []
    try:
        live_columns, _, blockers = discover_schema()
        if blockers:
            print(
                "\nSEMBRADO ABORTADO antes de cualquier INSERT: no se confirmó el esquema "
                "obligatorio. No se intentará inferir columnas ni eludir permisos."
            )
        else:
            try:
                fixture = seed_data(run_id, live_columns, records)
                print(f"\nDatos de prueba sembrados para {fixture['marker']}.")
                print(f"Rango de fechas usado: {fixture['date']}.")
            except Exception as exc:
                blockers.append(f"Siembra abortada ({safe_error(exc)}).")
                print(f"\nSEMBRADO ABORTADO: {safe_error(exc)}.")
        page_results = check_pages(run_id, blockers, fixture)
    except Exception as exc:
        print(f"ERROR DE VERIFICACIÓN: {safe_error(exc)}")
        exit_code = 1
    finally:
        print_report(page_results)
        print("\nLIMPIEZA")
        if args.keep:
            save_keep_file(run_id, records, blockers)
            print(f"Archivo de IDs: {LAST_RUN_FILE}; registros conservados: {len(records)}.")
            if records:
                for record in records:
                    print(
                        f"CONSERVADO {record['tabla']} "
                        f"{record['columna_pk']}={record['id']}"
                    )
        elif records:
            cleanup_errors = cleanup_records(run_id, records)
            if not cleanup_errors:
                print(f"Limpieza confirmada: {len(records)} registros creados fueron eliminados.")
        else:
            print("Limpieza confirmada: no se insertaron registros.")
    if cleanup_errors:
        print("REGISTROS NO LIMPIADOS")
        for error in cleanup_errors:
            print(f"- {error}")
        exit_code = 1
    if blockers:
        exit_code = max(exit_code, 2)
    if any(result["resultado"] == "FALLA" for result in page_results):
        exit_code = max(exit_code, 1)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
