"""Supabase simulado en memoria para probar la app sin conectarse a la base real.

Imita lo que usa realFlask.py: consultas a tablas (select/insert/update/delete
con filtros) y las funciones (rpc) de las migraciones
supabase/incremento3_ean.sql y supabase/incremento4_usuarios.sql.
La lógica replica la de esas funciones SQL, pero no las reemplaza: las reglas
reales viven en la base.
"""
import re
import secrets

from postgrest.exceptions import APIError
from werkzeug.security import check_password_hash, generate_password_hash

import ean13

MODULOS = [
    ('maestros', 'Datos maestros (clientes, productos, colores, tallas, bodegas, vendedores, zonas)'),
    ('codigos_ean', 'Códigos EAN y emisión de etiquetas'),
    ('pedidos', 'Pedidos'),
    ('produccion', 'Producción (cortes e ingreso a bodega)'),
    ('finanzas', 'Finanzas (pagos, notas de crédito, cobranza)'),
    ('informes', 'Informes'),
    ('configuracion', 'Configuración del sistema'),
]
ROLES = ['administrador', 'vendedor', 'jefa de taller', 'asistente de finanzas']
PERMISOS_ROL = {
    'vendedor': {'maestros': 'ver', 'pedidos': 'editar', 'informes': 'ver'},
    'jefa de taller': {'maestros': 'ver', 'codigos_ean': 'editar', 'pedidos': 'ver',
                       'produccion': 'editar', 'informes': 'ver'},
    'asistente de finanzas': {'maestros': 'ver', 'pedidos': 'ver', 'finanzas': 'editar', 'informes': 'ver'},
}
CLAVES_PRIMARIAS = {
    'productos': 'id_producto', 'colores': 'id_color', 'tallas': 'id_talla',
    'producto_variantes': 'id_variante', 'clientes': 'id_cliente', 'bodegas': 'id_bodega',
    'vendedores': 'id_vendedor', 'zona_venta': 'id_zona_venta', 'pedidos': 'id_pedido',
}
FORMATO_EAN = {'prefijo': '99', 'producto': 3, 'color': 4, 'talla': 3}


def error(mensaje, codigo='P0001'):
    return APIError({'message': mensaje, 'code': codigo, 'hint': None, 'details': None})


class Respuesta:
    def __init__(self, data):
        self.data = data


class Consulta:
    def __init__(self, db, tabla):
        self.db, self.tabla = db, tabla
        self.operacion, self.valores = 'select', None
        self.filtros, self.orden, self.limite = [], [], None

    # Construcción de la consulta (mismos nombres que supabase-py)
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

    def eq(self, col, val):
        self.filtros.append(lambda f: str(f.get(col)) == str(val))
        return self

    def in_(self, col, valores):
        valores = {str(v) for v in valores}
        self.filtros.append(lambda f: str(f.get(col)) in valores)
        return self

    def gt(self, col, val):
        self.filtros.append(lambda f: f.get(col) is not None and f.get(col) > val)
        return self

    def ilike(self, col, patron):
        regex = re.compile('^' + re.escape(patron).replace('%', '.*') + '$', re.I)
        self.filtros.append(lambda f: bool(regex.match(str(f.get(col) or ''))))
        return self

    def order(self, col, desc=False):
        self.orden.append((col, desc))
        return self

    def limit(self, n):
        self.limite = n
        return self

    def __getattr__(self, nombre):
        # Filtros que la app usa pero que no importan para las pruebas.
        return lambda *a, **k: self

    def execute(self):
        return Respuesta(self.db.ejecutar(self))


class SupabaseFalso:
    def __init__(self):
        self.tablas = {nombre: [] for nombre in CLAVES_PRIMARIAS}
        self.secuencias = {}
        self.usuarios, self.sesiones, self.permisos_usuario, self.auditoria = [], {}, {}, []
        self.llamadas = []

    # ------------------------------------------------------------ tablas
    def table(self, nombre):
        return Consulta(self, nombre)

    def _nuevo_id(self, tabla):
        self.secuencias[tabla] = self.secuencias.get(tabla, 0) + 1
        return self.secuencias[tabla]

    def ejecutar(self, c):
        if c.tabla == 'v_codigos_ean':
            filas = self._vista_codigos_ean()
        else:
            filas = self.tablas.setdefault(c.tabla, [])
        seleccion = [f for f in filas if all(filtro(f) for filtro in c.filtros)]

        if c.operacion == 'insert':
            nuevas = c.valores if isinstance(c.valores, list) else [c.valores]
            creadas = []
            for valores in nuevas:
                fila = dict(valores)
                self._validar(c.tabla, fila)
                pk = CLAVES_PRIMARIAS.get(c.tabla, 'id')
                fila.setdefault(pk, self._nuevo_id(c.tabla))
                filas.append(fila)
                creadas.append(fila)
            self._recalcular_ean()
            return creadas
        if c.operacion == 'update':
            for fila in seleccion:
                self._validar(c.tabla, {**fila, **c.valores})
            for fila in seleccion:
                fila.update(c.valores)
            self._recalcular_ean()
            return seleccion
        if c.operacion == 'delete':
            for fila in seleccion:
                filas.remove(fila)
            return seleccion

        for col, desc in reversed(c.orden):
            seleccion = sorted(seleccion, key=lambda f: (f.get(col) is None, str(f.get(col) or '')), reverse=desc)
        return [dict(f) for f in seleccion[:c.limite]]

    def _validar(self, tabla, fila):
        # Equivale a los check y unique de las migraciones.
        if tabla in ('productos', 'colores', 'tallas'):
            codigo = fila.get('codigo_ean')
            if codigo is not None and not re.fullmatch(r'[0-9]+', str(codigo)):
                raise error('new row violates check constraint', '23514')
            largo = FORMATO_EAN[{'productos': 'producto', 'colores': 'color', 'tallas': 'talla'}[tabla]]
            if codigo and len(codigo) > largo:
                raise error(f'El código EAN de {tabla[:-1]} {codigo} tiene más de {largo} dígitos')
        if tabla == 'producto_variantes' and fila.get('ean_manual'):
            if not re.fullmatch(r'[0-9]{13}', str(fila.get('codigo_ean') or '')):
                raise error('El código EAN manual debe tener 13 dígitos')

    # ------------------------------------------------------------ EAN
    def _codigo(self, tabla, pk, id_):
        fila = next((f for f in self.tablas[tabla] if f[pk] == id_), None)
        return fila and fila.get('codigo_ean')

    def generar_ean(self, id_producto, id_color, id_talla):
        partes = (self._codigo('productos', 'id_producto', id_producto),
                  self._codigo('colores', 'id_color', id_color),
                  self._codigo('tallas', 'id_talla', id_talla))
        if not all(partes):
            return None
        base = (FORMATO_EAN['prefijo'] + partes[0].zfill(FORMATO_EAN['producto'])
                + partes[1].zfill(FORMATO_EAN['color']) + partes[2].zfill(FORMATO_EAN['talla']))
        return base + ean13.digito_verificador(base)

    def _recalcular_ean(self):
        for v in self.tablas['producto_variantes']:
            if not v.get('ean_manual'):
                v['codigo_ean'] = self.generar_ean(v['id_producto'], v['id_color'], v['id_talla'])

    def _vista_codigos_ean(self):
        filas = []
        for v in self.tablas['producto_variantes']:
            p = next(f for f in self.tablas['productos'] if f['id_producto'] == v['id_producto'])
            c = next((f for f in self.tablas['colores'] if f['id_color'] == v['id_color']), {})
            t = next((f for f in self.tablas['tallas'] if f['id_talla'] == v['id_talla']), {})
            filas.append({
                'id_variante': v['id_variante'], 'id_producto': v['id_producto'],
                'codigo_articulo': p.get('codigo') or str(p['id_producto']), 'descripcion': p['descripcion'],
                'id_color': v['id_color'], 'color': c.get('descripcion'),
                'id_talla': v['id_talla'], 'talla': t.get('nombre') or str(t.get('talla')),
                'codigo_ean': v.get('codigo_ean'), 'ean_manual': bool(v.get('ean_manual')), 'activo': True,
            })
        return filas

    # ------------------------------------------------------------ usuarios
    def _usuario(self, id_usuario):
        return next((u for u in self.usuarios if u['id_usuario'] == id_usuario), None)

    def _usuario_de_sesion(self, token):
        id_usuario = self.sesiones.get(token)
        u = self._usuario(id_usuario)
        return u if u and u['activo'] else None

    def _rol(self, u):
        return ROLES[u['id_tipo_usuario'] - 1]

    def _permisos(self, u):
        if self._rol(u) == 'administrador':
            return {m: 'editar' for m, _ in MODULOS}
        propios = self.permisos_usuario.get(u['id_usuario'], {})
        rol = PERMISOS_ROL.get(self._rol(u), {})
        return {m: propios.get(m) or rol.get(m, 'ninguno') for m, _ in MODULOS}

    def _datos(self, u):
        return {'id_usuario': u['id_usuario'], 'usuario': u['usuario'], 'nombre': u['nombre'],
                'rol': self._rol(u), 'es_admin': self._rol(u) == 'administrador', 'permisos': self._permisos(u)}

    def _exigir_admin(self, token):
        u = self._usuario_de_sesion(token)
        if u is None:
            raise error('La sesión expiró. Vuelva a iniciar sesión.')
        if self._rol(u) != 'administrador':
            raise error('Solo un administrador puede realizar esta acción.')
        return u

    @staticmethod
    def _validar_password(password):
        if not password or len(password) < 8:
            raise error('La contraseña debe tener al menos 8 caracteres.')

    def crear_usuario(self, usuario, password, rol='administrador', nombre=None, correo=None, activo=True):
        if any(u['usuario'].lower() == usuario.strip().lower() for u in self.usuarios):
            raise error('duplicate key value violates unique constraint "usuarios_usuario_uk"', '23505')
        u = {'id_usuario': self._nuevo_id('usuarios'), 'usuario': usuario.strip(), 'nombre': nombre,
             'correo': correo, 'id_tipo_usuario': ROLES.index(rol) + 1, 'activo': activo,
             'password_hash': generate_password_hash(password), 'ultimo_acceso': None}
        self.usuarios.append(u)
        return u

    def _hay_admin_activo(self):
        return any(u['activo'] and self._rol(u) == 'administrador' for u in self.usuarios)

    # ------------------------------------------------------------ rpc
    def rpc(self, nombre, params=None):
        params = params or {}
        self.llamadas.append((nombre, params))
        metodo = getattr(self, 'rpc_' + nombre, None)
        return Consulta_rpc(metodo(**params) if metodo else None)

    def rpc_hay_usuarios(self):
        return bool(self.usuarios)

    def rpc_crear_primer_administrador(self, p_usuario, p_nombre, p_password):
        if self.usuarios:
            raise error('Ya existen usuarios; el administrador debe crear los demás.')
        if not (p_usuario or '').strip():
            raise error('Debe indicar un nombre de usuario.')
        self._validar_password(p_password)
        self.crear_usuario(p_usuario, p_password, 'administrador', p_nombre)

    def rpc_iniciar_sesion(self, p_usuario, p_password):
        u = next((x for x in self.usuarios if x['usuario'].lower() == (p_usuario or '').strip().lower()), None)
        if not u or not u['activo'] or not check_password_hash(u['password_hash'], p_password or ''):
            self.auditoria.append(('login_fallido', p_usuario))
            return None
        token = secrets.token_hex(32)
        self.sesiones[token] = u['id_usuario']
        u['ultimo_acceso'] = '2026-10-04T12:00:00+00:00'
        self.auditoria.append(('login', u['usuario']))
        return {**self._datos(u), 'token': token}

    def rpc_datos_sesion(self, p_token):
        u = self._usuario_de_sesion(p_token)
        return self._datos(u) if u else None

    def rpc_cerrar_sesion(self, p_token):
        self.sesiones.pop(p_token, None)

    def rpc_cambiar_password(self, p_token, p_actual, p_nueva):
        u = self._usuario_de_sesion(p_token)
        if u is None:
            raise error('La sesión expiró. Vuelva a iniciar sesión.')
        if not check_password_hash(u['password_hash'], p_actual or ''):
            raise error('La contraseña actual no es correcta.')
        self._validar_password(p_nueva)
        u['password_hash'] = generate_password_hash(p_nueva)
        for t in [t for t, i in self.sesiones.items() if i == u['id_usuario'] and t != p_token]:
            del self.sesiones[t]

    def rpc_admin_listar_usuarios(self, p_token):
        self._exigir_admin(p_token)
        return {
            'usuarios': [{**{k: u[k] for k in ('id_usuario', 'usuario', 'nombre', 'correo', 'id_tipo_usuario', 'activo', 'ultimo_acceso')},
                          'rol': self._rol(u), 'permisos_propios': len(self.permisos_usuario.get(u['id_usuario'], {}))}
                         for u in sorted(self.usuarios, key=lambda x: x['usuario'].lower())],
            'roles': [{'id_tipo_usuario': i + 1, 'tipo_usuario': r} for i, r in enumerate(ROLES)],
        }

    def rpc_admin_guardar_usuario(self, p_token, p_id_usuario, p_usuario, p_nombre, p_correo,
                                  p_id_tipo_usuario, p_activo, p_password=None):
        self._exigir_admin(p_token)
        if not (p_usuario or '').strip():
            raise error('Debe indicar un nombre de usuario.')
        if not 1 <= p_id_tipo_usuario <= len(ROLES):
            raise error('El rol seleccionado no existe.')
        if p_id_usuario is None:
            self._validar_password(p_password)
            u = self.crear_usuario(p_usuario, p_password, ROLES[p_id_tipo_usuario - 1], p_nombre, p_correo, p_activo)
        else:
            u = self._usuario(p_id_usuario)
            if u is None:
                raise error('El usuario no existe.')
            anterior = dict(u)
            u.update(usuario=p_usuario.strip(), nombre=p_nombre, correo=p_correo,
                     id_tipo_usuario=p_id_tipo_usuario, activo=p_activo)
            if not self._hay_admin_activo():
                u.update(anterior)
                raise error('Debe quedar al menos un administrador activo.')
            if p_password:
                self._validar_password(p_password)
                u['password_hash'] = generate_password_hash(p_password)
            if p_password or not p_activo:
                for t in [t for t, i in self.sesiones.items() if i == u['id_usuario']]:
                    del self.sesiones[t]
        return u['id_usuario']

    def rpc_admin_permisos_usuario(self, p_token, p_id_usuario):
        self._exigir_admin(p_token)
        u = self._usuario(p_id_usuario)
        propios = self.permisos_usuario.get(p_id_usuario, {})
        rol = PERMISOS_ROL.get(self._rol(u), {})
        efectivos = self._permisos(u)
        return [{'modulo': m, 'nombre': n, 'nivel_rol': rol.get(m, 'ninguno'),
                 'nivel_usuario': propios.get(m), 'nivel': efectivos[m]} for m, n in MODULOS]

    def rpc_admin_guardar_permisos(self, p_token, p_id_usuario, p_permisos):
        self._exigir_admin(p_token)
        propios = self.permisos_usuario.setdefault(p_id_usuario, {})
        for modulo, nivel in (p_permisos or {}).items():
            if modulo not in dict(MODULOS):
                raise error(f'Módulo desconocido: {modulo}')
            if nivel is None or nivel == 'rol':
                propios.pop(modulo, None)
            else:
                propios[modulo] = nivel

    def rpc_obtener_variante(self, p_id_producto, p_id_color, p_id_talla):
        variantes = self.tablas['producto_variantes']
        v = next((x for x in variantes if (x['id_producto'], x['id_color'], x['id_talla'])
                  == (p_id_producto, p_id_color, p_id_talla)), None)
        if v is None:
            producto = next(f for f in self.tablas['productos'] if f['id_producto'] == p_id_producto)
            self.table('producto_variantes').insert({
                'id_producto': p_id_producto, 'id_color': p_id_color, 'id_talla': p_id_talla,
                'precio_venta': producto.get('precio') or 0, 'descripcion': producto['descripcion'],
                'ean_manual': False, 'codigo_ean': None,
            }).execute()
            v = variantes[-1]
        return [dict(v)]


class Consulta_rpc:
    # supabase.rpc(...).execute() devuelve el resultado de la función.
    def __init__(self, data):
        self.data = data

    def execute(self):
        return Respuesta(self.data)


def con_datos_de_ejemplo():
    """Base simulada con los productos, colores y tallas de las etiquetas reales."""
    db = SupabaseFalso()
    for codigo, descripcion in [('412', 'Tanga Algodon Spandex'), ('414', 'Cuadro algodon spandex'),
                                ('415', 'Hikini ALG'), ('425', 'Hikini con pretina')]:
        db.table('productos').insert({'codigo': codigo, 'codigo_ean': codigo, 'descripcion': descripcion,
                                      'abreviacion': codigo, 'precio': 2990}).execute()
    for descripcion, codigo_color, codigo_ean in [('BLANCO', 'BL', '0001'), ('NEGRO', 'NE', '0003'), ('BEIGE', 'BG', '0397')]:
        db.table('colores').insert({'descripcion': descripcion, 'codigo_color': codigo_color, 'codigo_ean': codigo_ean}).execute()
    for talla, nombre, codigo_ean in [(1, 'S', '010'), (2, 'M', '011'), (3, 'L', None)]:
        db.table('tallas').insert({'talla': talla, 'nombre': nombre, 'codigo_ean': codigo_ean}).execute()
    return db
