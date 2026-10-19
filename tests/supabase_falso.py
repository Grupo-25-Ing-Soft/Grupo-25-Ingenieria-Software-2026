"""Supabase simulado en memoria para probar la app sin conectarse a la base real.

Imita lo que usa realFlask.py: consultas a tablas (select/insert/update/delete
con filtros), la vista v_codigos_ean y las funciones (rpc) que las pruebas
necesitan. La lógica replica la de las funciones SQL de supabase/, pero no
las reemplaza: las reglas reales viven en la base.
"""
import re

from postgrest.exceptions import APIError

import ean13

# Clave primaria de cada tabla: se asigna sola al insertar, como una identity.
CLAVES_AUTOINCREMENTALES = {
    'roles': 'id_rol', 'usuarios': 'id_usuario',
    'productos': 'id_producto', 'colores': 'id_color', 'tallas': 'id_talla',
    'producto_variantes': 'id_variante', 'clientes': 'id_cliente', 'bodegas': 'id_bodega',
    'vendedores': 'id_vendedor', 'zona_venta': 'id_zona_venta', 'pedidos': 'id_pedido',
    'detalle_pedidos': 'id_detalle_pedido', 'facturas': 'id_factura',
    'notas_credito': 'id_nota_credito', 'pagos': 'id_pago', 'pago_facturas': 'id_pago_factura',
    'despachos': 'id_despacho', 'detalle_despachos': 'id_detalle_despacho', 'inventario': 'id_inventario',
}
# Columnas identity que no son la clave primaria (pagos.folio en pagos.sql).
IDENTIDADES_EXTRA = {'pagos': 'folio'}
FORMATO_EAN = {'prefijo': '99', 'producto': 3, 'color': 4, 'talla': 3}


def error(mensaje, codigo='P0001'):
    return APIError({'message': mensaje, 'code': codigo, 'hint': None, 'details': None})


class RespuestaFalsa:
    def __init__(self, data):
        self.data = data


class ConsultaFalsa:
    def __init__(self, db, nombre):
        self.db = db
        self.nombre = nombre
        self.filtros = []
        self.operacion = 'select'
        self.valores = None
        self.orden = []
        self.limite = None
        self._negar = False

    # ---------------------------------------------------- construcción (como supabase-py)
    def select(self, *args, **kwargs):
        return self

    def insert(self, valores):
        self.operacion, self.valores = 'insert', valores
        return self

    def update(self, valores):
        self.operacion, self.valores = 'update', valores
        return self

    def delete(self):
        self.operacion = 'delete'
        return self

    def _filtro(self, condicion):
        if self._negar:
            self._negar = False
            self.filtros.append(lambda fila: not condicion(fila))
        else:
            self.filtros.append(condicion)
        return self

    @property
    def not_(self):
        self._negar = True
        return self

    def eq(self, columna, valor):
        return self._filtro(lambda f: str(f.get(columna)) == str(valor))

    def neq(self, columna, valor):
        return self._filtro(lambda f: str(f.get(columna)) != str(valor))

    def _comparar(self, columna, valor, operador):
        def condicion(fila):
            actual = fila.get(columna)
            if actual is None:
                return False
            try:
                return operador(float(actual), float(valor))
            except (TypeError, ValueError):
                return operador(str(actual), str(valor))
        return self._filtro(condicion)

    def gt(self, columna, valor):
        return self._comparar(columna, valor, lambda a, b: a > b)

    def gte(self, columna, valor):
        return self._comparar(columna, valor, lambda a, b: a >= b)

    def lt(self, columna, valor):
        return self._comparar(columna, valor, lambda a, b: a < b)

    def lte(self, columna, valor):
        return self._comparar(columna, valor, lambda a, b: a <= b)

    def in_(self, columna, valores):
        valores = {str(v) for v in valores}
        return self._filtro(lambda f: str(f.get(columna)) in valores)

    def is_(self, columna, valor):
        esperado = None if str(valor).lower() == 'null' else valor
        return self._filtro(lambda f: f.get(columna) is esperado if esperado is None else f.get(columna) == esperado)

    def ilike(self, columna, patron):
        regex = re.compile('^' + re.escape(patron).replace('%', '.*') + '$', re.I)
        return self._filtro(lambda f: bool(regex.match(str(f.get(columna) or ''))))

    def order(self, columna, desc=False):
        self.orden.append((columna, desc))
        return self

    def limit(self, cantidad):
        self.limite = cantidad
        return self

    def execute(self):
        return RespuestaFalsa(self.db.ejecutar(self))


class SupabaseFalso:
    def __init__(self, tablas=None):
        self.tablas = tablas if tablas is not None else {}
        self.llamadas = []

    def table(self, nombre):
        return ConsultaFalsa(self, nombre)

    def _siguiente(self, filas, columna):
        return max([f.get(columna) or 0 for f in filas], default=0) + 1

    def ejecutar(self, consulta):
        if consulta.nombre == 'v_codigos_ean':
            filas = self._vista_codigos_ean()
        else:
            filas = self.tablas.setdefault(consulta.nombre, [])

        if consulta.operacion == 'insert':
            nuevas = consulta.valores if isinstance(consulta.valores, list) else [consulta.valores]
            creadas = []
            for valores in nuevas:
                fila = dict(valores)
                self._validar(consulta.nombre, fila)
                for columna in (CLAVES_AUTOINCREMENTALES.get(consulta.nombre),
                                IDENTIDADES_EXTRA.get(consulta.nombre)):
                    if columna:
                        fila.setdefault(columna, self._siguiente(filas, columna))
                filas.append(fila)
                creadas.append(fila)
            self._recalcular_ean()
            return [dict(f) for f in creadas]

        coincidentes = [f for f in filas if all(filtro(f) for filtro in consulta.filtros)]
        if consulta.operacion == 'update':
            for fila in coincidentes:
                self._validar(consulta.nombre, {**fila, **consulta.valores})
            for fila in coincidentes:
                fila.update(consulta.valores)
            self._recalcular_ean()
            return [dict(f) for f in coincidentes]
        if consulta.operacion == 'delete':
            self.tablas[consulta.nombre] = [f for f in filas if f not in coincidentes]
            return [dict(f) for f in coincidentes]

        for columna, desc in reversed(consulta.orden):
            coincidentes = sorted(coincidentes, key=lambda f: (f.get(columna) is None, str(f.get(columna) or '')),
                                  reverse=desc)
        if consulta.limite is not None:
            coincidentes = coincidentes[:consulta.limite]
        return [dict(f) for f in coincidentes]

    def _validar(self, tabla, fila):
        # Equivale a los check de supabase/incremento3_ean.sql.
        if tabla in ('productos', 'colores', 'tallas'):
            codigo = fila.get('codigo_ean')
            if codigo is not None and not re.fullmatch(r'[0-9]+', str(codigo)):
                raise error('new row violates check constraint', '23514')
            largo = FORMATO_EAN[{'productos': 'producto', 'colores': 'color', 'tallas': 'talla'}[tabla]]
            if codigo and len(str(codigo)) > largo:
                raise error(f'El código EAN de {tabla[:-1]} {codigo} tiene más de {largo} dígitos')
        if tabla == 'producto_variantes' and fila.get('ean_manual'):
            if not re.fullmatch(r'[0-9]{13}', str(fila.get('codigo_ean') or '')):
                raise error('El código EAN manual debe tener 13 dígitos')

    # ------------------------------------------------------------ EAN (incremento3_ean.sql)
    def _codigo(self, tabla, pk, id_):
        fila = next((f for f in self.tablas.get(tabla, []) if str(f.get(pk)) == str(id_)), None)
        return fila and fila.get('codigo_ean')

    def generar_ean(self, id_producto, id_color, id_talla):
        partes = (self._codigo('productos', 'id_producto', id_producto),
                  self._codigo('colores', 'id_color', id_color),
                  self._codigo('tallas', 'id_talla', id_talla))
        if not all(partes):
            return None
        base = (FORMATO_EAN['prefijo'] + str(partes[0]).zfill(FORMATO_EAN['producto'])
                + str(partes[1]).zfill(FORMATO_EAN['color']) + str(partes[2]).zfill(FORMATO_EAN['talla']))
        return base + ean13.digito_verificador(base)

    def _recalcular_ean(self):
        for v in self.tablas.get('producto_variantes', []):
            if not v.get('ean_manual') and v.get('id_producto') is not None:
                v['codigo_ean'] = self.generar_ean(v['id_producto'], v.get('id_color'), v.get('id_talla'))

    def _vista_codigos_ean(self):
        filas = []
        for v in self.tablas.get('producto_variantes', []):
            p = next((f for f in self.tablas.get('productos', []) if f['id_producto'] == v['id_producto']), {})
            c = next((f for f in self.tablas.get('colores', []) if f['id_color'] == v.get('id_color')), {})
            t = next((f for f in self.tablas.get('tallas', []) if f['id_talla'] == v.get('id_talla')), {})
            filas.append({
                'id_variante': v['id_variante'], 'id_producto': v['id_producto'],
                'codigo_articulo': p.get('codigo') or str(p.get('id_producto')), 'descripcion': p.get('descripcion'),
                'id_color': v.get('id_color'), 'color': c.get('descripcion'),
                'id_talla': v.get('id_talla'), 'talla': t.get('nombre') or str(t.get('talla')),
                'codigo_ean': v.get('codigo_ean'), 'ean_manual': bool(v.get('ean_manual')),
                'activo': v.get('activo', True),
            })
        return filas

    # ------------------------------------------------------------ rpc
    def rpc(self, nombre, params=None):
        params = params or {}
        self.llamadas.append((nombre, params))
        metodo = getattr(self, 'rpc_' + nombre, None)
        return ConsultaRpc(metodo(**params) if metodo else None)

    def rpc_obtener_variante(self, p_id_producto, p_id_color, p_id_talla):
        variantes = self.tablas.setdefault('producto_variantes', [])
        v = next((x for x in variantes if (x['id_producto'], x.get('id_color'), x.get('id_talla'))
                  == (p_id_producto, p_id_color, p_id_talla)), None)
        if v is None:
            producto = next(f for f in self.tablas['productos'] if f['id_producto'] == p_id_producto)
            self.table('producto_variantes').insert({
                'id_producto': p_id_producto, 'id_color': p_id_color, 'id_talla': p_id_talla,
                'precio_venta': producto.get('precio') or 0, 'descripcion': producto['descripcion'],
                'ean_manual': False, 'codigo_ean': None, 'activo': True,
            }).execute()
            v = variantes[-1]
        return [dict(v)]


class ConsultaRpc:
    # supabase.rpc(...).execute() devuelve el resultado de la función.
    def __init__(self, data):
        self.data = data

    def execute(self):
        return RespuestaFalsa(self.data)


ADMIN_DE_PRUEBA = {
    'id_usuario': 1, 'nombre_usuario': 'admin', 'nombre': 'Admin', 'password_hash': '',
    'id_rol': None, 'es_superusuario': True, 'activo': True,
}


def con_datos_de_ejemplo():
    """Base simulada con los productos, colores y tallas de las etiquetas reales,
    y un superusuario (id 1) para entrar a todas las pantallas."""
    db = SupabaseFalso({'usuarios': [dict(ADMIN_DE_PRUEBA)], 'roles': [], 'rol_permisos': []})
    for codigo, descripcion in [('412', 'Tanga Algodon Spandex'), ('414', 'Cuadro algodon spandex'),
                                ('415', 'Hikini ALG'), ('425', 'Hikini con pretina')]:
        db.table('productos').insert({'codigo': codigo, 'codigo_ean': codigo, 'descripcion': descripcion,
                                      'abreviacion': codigo, 'precio': 2990}).execute()
    for descripcion, codigo_color, codigo_ean in [('BLANCO', 'BL', '0001'), ('NEGRO', 'NE', '0003'),
                                                  ('BEIGE', 'BG', '0397')]:
        db.table('colores').insert({'descripcion': descripcion, 'codigo_color': codigo_color,
                                    'codigo_ean': codigo_ean}).execute()
    for talla, nombre, codigo_ean in [(1, 'S', '010'), (2, 'M', '011'), (3, 'L', None)]:
        db.table('tallas').insert({'talla': talla, 'nombre': nombre, 'codigo_ean': codigo_ean}).execute()
    return db
